import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from jira import JIRA
from jira.exceptions import JIRAError
from mcp.server.fastmcp import FastMCP

# stdout is reserved for MCP stdio JSON-RPC framing. Keep logs on stderr.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("jira_mcp_server")

load_dotenv()

mcp = FastMCP(
    "Jira-Data-Center-v10",
    instructions=(
        "Enterprise-grade profile-aware MCP server exposing read, write, query, agile, metadata, "
        "audit, collaboration, workflow, and administration-safe Jira Data Center v10 operations."
    ),
)


# ---------------------------------------------------------------------------
# Profile-based tool registration
# ---------------------------------------------------------------------------

# Tool groups are intentionally operation-oriented. Profiles expose a curated subset
# of groups so MCP clients are not overloaded with every possible Jira operation.
ALL_TOOL_GROUPS = {
    "READONLY_CORE",
    "METADATA",
    "WORKFLOW_READ",
    "WORKFLOW_WRITE",
    "ISSUE_WRITE",
    "COMMENT_WRITE",
    "ASSIGNMENT_WRITE",
    "LINK_WRITE",
    "PROPERTY_WRITE",
    "ATTACHMENT_WRITE",
    "WORKLOG_WRITE",
    "AGILE_READ",
    "AGILE_WRITE",
    "ADMIN_READ",
    "ADMIN_WRITE",
    "BULK",
    "DESTRUCTIVE",
}

PROFILE_GROUPS = {
    # Safe default for discovery, triage, status checks, reporting, and planning.
    "readonly": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "AGILE_READ",
        "ADMIN_READ",
    },
    # Normal day-to-day Jira work, excluding explicitly destructive and bulk tools.
    "standard": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "ISSUE_WRITE",
        "COMMENT_WRITE",
        "ASSIGNMENT_WRITE",
        "LINK_WRITE",
        "PROPERTY_WRITE",
        "ATTACHMENT_WRITE",
        "WORKLOG_WRITE",
        "AGILE_READ",
        "ADMIN_READ",
    },
    # Backlog/sprint planning profile.
    "agile": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "COMMENT_WRITE",
        "ASSIGNMENT_WRITE",
        "AGILE_READ",
        "AGILE_WRITE",
        "ADMIN_READ",
    },
    # Metadata, permission, role, security, and configuration context.
    "admin": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "AGILE_READ",
        "ADMIN_READ",
        "ADMIN_WRITE",
    },
    # Everything except bulk and destructive tools.
    "full": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "ISSUE_WRITE",
        "COMMENT_WRITE",
        "ASSIGNMENT_WRITE",
        "LINK_WRITE",
        "PROPERTY_WRITE",
        "ATTACHMENT_WRITE",
        "WORKLOG_WRITE",
        "AGILE_READ",
        "AGILE_WRITE",
        "ADMIN_READ",
        "ADMIN_WRITE",
    },
    # Everything, including bulk and destructive tools. Individual destructive tools
    # still require confirm=True.
    "dangerous": set(ALL_TOOL_GROUPS),
}

DEFAULT_PROFILE = os.environ.get("JIRA_MCP_PROFILE", "standard").strip().lower()
EXPLICIT_GROUPS = {
    group.strip().upper()
    for group in os.environ.get("JIRA_MCP_ENABLED_GROUPS", "").split(",")
    if group.strip()
}

if EXPLICIT_GROUPS:
    ENABLED_TOOL_GROUPS = EXPLICIT_GROUPS
    ACTIVE_PROFILE_LABEL = "custom"
else:
    ENABLED_TOOL_GROUPS = PROFILE_GROUPS.get(DEFAULT_PROFILE, PROFILE_GROUPS["standard"])
    ACTIVE_PROFILE_LABEL = DEFAULT_PROFILE if DEFAULT_PROFILE in PROFILE_GROUPS else "standard"

logger.info(
    "Jira MCP profile active: %s | groups=%s",
    ACTIVE_PROFILE_LABEL,
    ",".join(sorted(ENABLED_TOOL_GROUPS)),
)


def group_enabled(group: str) -> bool:
    return group.upper() in ENABLED_TOOL_GROUPS


def profiled_tool(group: str):
    """
    Register an MCP tool only when its group is enabled by profile configuration.
    Disabled functions remain importable/testable but are not exposed to MCP clients.
    """
    normalized_group = group.upper()

    def decorator(fn):
        if group_enabled(normalized_group):
            logger.debug("Registering MCP tool %s in group %s", fn.__name__, normalized_group)
            return mcp.tool()(fn)
        logger.debug("Skipping MCP tool %s in disabled group %s", fn.__name__, normalized_group)
        return fn

    return decorator


def get_profile_status_payload() -> Dict[str, Any]:
    return {
        "active_profile": ACTIVE_PROFILE_LABEL,
        "enabled_groups": sorted(ENABLED_TOOL_GROUPS),
        "available_profiles": {name: sorted(groups) for name, groups in PROFILE_GROUPS.items()},
        "all_groups": sorted(ALL_TOOL_GROUPS),
    }


@profiled_tool("METADATA")
def get_mcp_profile_status() -> str:
    """Return the active Jira MCP profile and enabled tool groups."""
    return _json_dumps(get_profile_status_payload())



JIRA_URL = os.environ.get("JIRA_SERVER_URL", "").rstrip("/")
JIRA_PAT = os.environ.get("JIRA_PAT")


def _require_runtime_config() -> None:
    if not JIRA_URL or not JIRA_PAT:
        logger.critical(
            "Initialization failure: Missing JIRA_SERVER_URL or JIRA_PAT environment variables."
        )
        raise ValueError(
            "Missing runtime authentication configuration. "
            "Set JIRA_SERVER_URL and JIRA_PAT before launching the MCP server."
        )


def _connect_jira() -> JIRA:
    _require_runtime_config()
    try:
        logger.info("Connecting to Jira Data Center instance at: %s", JIRA_URL)
        client = JIRA(server=JIRA_URL, token_auth=JIRA_PAT)
        logger.info("Jira client connection interface successfully cached.")
        return client
    except Exception as exc:
        logger.critical("Fatal connection error during initialization: %s", str(exc))
        raise


jira_client = _connect_jira()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _validate_issue_key(issue_key: str) -> Optional[str]:
    if not issue_key or not isinstance(issue_key, str):
        return "Issue key is required."
    if not re.match(r"^[A-Z][A-Z0-9_]+-\d+$", issue_key.strip().upper()):
        return (
            "Issue key appears invalid. Expected a Jira key such as PROJ-123. "
            "Use the exact key from Jira."
        )
    return None


def _validate_issue_keys(issue_keys: Sequence[str]) -> Optional[str]:
    if not issue_keys:
        return "At least one issue key is required."
    for issue_key in issue_keys:
        err = _validate_issue_key(issue_key)
        if err:
            return f"{issue_key}: {err}"
    return None


def _normalize_issue_key(issue_key: str) -> str:
    return issue_key.strip().upper()


def _normalize_issue_keys(issue_keys: Sequence[str]) -> List[str]:
    return [_normalize_issue_key(key) for key in issue_keys]


def _jira_user_to_dict(user: Any) -> Optional[Dict[str, Any]]:
    if not user:
        return None
    return {
        "display_name": getattr(user, "displayName", None),
        "username": getattr(user, "name", None),
        "key": getattr(user, "key", None),
        "email": getattr(user, "emailAddress", None),
        "active": getattr(user, "active", None),
    }


def _field_name(value: Any) -> Optional[str]:
    return getattr(value, "name", None) if value else None


def _error(prefix: str, err: Exception) -> str:
    if isinstance(err, JIRAError):
        detail = getattr(err, "text", str(err))
        status_code = getattr(err, "status_code", None)
        return f"{prefix}: {detail}" + (f" (Status Code: {status_code})" if status_code else "")
    return f"{prefix}: {str(err)}"


def _resource(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def _request(method: str, path: str, **kwargs: Any) -> Any:
    """
    Thin wrapper around the underlying python-jira session.
    Useful for Jira Data Center REST resources not surfaced as first-class python-jira helpers.
    """
    url = f"{JIRA_URL}{_resource(path)}"
    response = jira_client._session.request(method.upper(), url, **kwargs)
    response.raise_for_status()
    if response.status_code == 204 or not response.text:
        return {"status": response.status_code, "ok": True}
    try:
        return response.json()
    except ValueError:
        return response.text


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    return _request("GET", path, params=params)


def _post(path: str, payload: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None, files: Any = None) -> Any:
    kwargs: Dict[str, Any] = {"params": params}
    if files is not None:
        kwargs["files"] = files
        kwargs["headers"] = {"X-Atlassian-Token": "no-check"}
    else:
        kwargs["json"] = {} if payload is None else payload
    return _request("POST", path, **kwargs)


def _put(path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    return _request("PUT", path, json={} if payload is None else payload)


def _delete(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    return _request("DELETE", path, params=params)


def _object_to_dict(obj: Any, keys: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if keys:
        return {key: getattr(obj, key, None) for key in keys}
    if hasattr(obj, "raw"):
        return obj.raw
    return {
        key: getattr(obj, key)
        for key in dir(obj)
        if not key.startswith("_") and not callable(getattr(obj, key))
    }


def _find_transition_id(issue_key: str, transition_name_or_id: str) -> Dict[str, Any]:
    transitions = jira_client.transitions(issue_key)
    requested = str(transition_name_or_id).strip()
    options = []
    for transition in transitions:
        transition_id = str(transition.get("id"))
        transition_name = str(transition.get("name"))
        options.append({"id": transition_id, "name": transition_name})
        if requested == transition_id or requested.lower() == transition_name.lower():
            return {"target_id": transition_id, "options": options}
    return {"target_id": None, "options": options}


def _parse_json_object(value: Optional[str], field_name: str) -> Dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a JSON object string. Error: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must decode to a JSON object.")
    return parsed


def _parse_json_array(value: Optional[str], field_name: str) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a JSON array string. Error: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{field_name} must decode to a JSON array.")
    return parsed


# ---------------------------------------------------------------------------
# Search, issue read, and validation
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def search_issues(jql_query: str, max_results: int = 50) -> str:
    """
    Query Jira issues using native Jira Query Language (JQL).

    Use this whenever the user wants to list, filter, find, or report on groups of issues.
    """
    if not jql_query or not jql_query.strip():
        return "Error: jql_query is required."

    try:
        bounded_max = max(1, min(int(max_results), 100))
    except (TypeError, ValueError):
        return "Error: max_results must be an integer between 1 and 100."

    try:
        logger.info("Executing JQL query: %s (max=%s)", jql_query, bounded_max)
        issues = jira_client.search_issues(jql_query, maxResults=bounded_max)

        if not issues:
            return f"### JQL Search Results\n\nNo issues found matching query: `{jql_query}`"

        markdown_output = [
            "### JQL Search Results\n",
            f"Query: `{jql_query}` | Results Found: {len(issues)}\n",
            "| Issue Key | Summary | Status | Assignee | Priority |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for issue in issues:
            fields = issue.fields
            key = issue.key
            summary = str(getattr(fields, "summary", "N/A")).replace("|", "\\|")
            status = _field_name(getattr(fields, "status", None)) or "N/A"
            assignee = (
                getattr(fields.assignee, "displayName", "Unassigned")
                if getattr(fields, "assignee", None)
                else "Unassigned"
            )
            priority = _field_name(getattr(fields, "priority", None)) or "N/A"
            markdown_output.append(
                f"| [{key}]({JIRA_URL}/browse/{key}) | {summary} | {status} | {assignee} | {priority} |"
            )

        return "\n".join(markdown_output)
    except Exception as exc:
        logger.error("JQL search failure: %s", str(exc))
        return _error("Error executing JQL query", exc)


@profiled_tool("READONLY_CORE")
def get_issue_details(issue_key: str) -> str:
    """
    Retrieve structured metadata, descriptions, core fields, and comments for an issue.
    Use before updating, commenting on, or resolving an issue.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"

    normalized_key = _normalize_issue_key(issue_key)

    try:
        logger.info("Retrieving issue context for: %s", normalized_key)
        issue = jira_client.issue(normalized_key)
        fields = issue.fields

        comments_payload: List[Dict[str, Any]] = []
        if getattr(fields, "comment", None):
            for comment in fields.comment.comments:
                comments_payload.append(
                    {
                        "id": getattr(comment, "id", None),
                        "author": getattr(getattr(comment, "author", None), "displayName", None),
                        "username": getattr(getattr(comment, "author", None), "name", None),
                        "body": getattr(comment, "body", None),
                        "created": getattr(comment, "created", None),
                    }
                )

        issue_data = {
            "key": issue.key,
            "id": issue.id,
            "url": f"{JIRA_URL}/browse/{issue.key}",
            "summary": getattr(fields, "summary", ""),
            "status": _field_name(getattr(fields, "status", None)),
            "priority": _field_name(getattr(fields, "priority", None)),
            "creator": _jira_user_to_dict(getattr(fields, "creator", None)),
            "reporter": _jira_user_to_dict(getattr(fields, "reporter", None)),
            "assignee": _jira_user_to_dict(getattr(fields, "assignee", None)),
            "description": getattr(fields, "description", ""),
            "created_at": getattr(fields, "created", None),
            "updated_at": getattr(fields, "updated", None),
            "labels": getattr(fields, "labels", []),
            "components": [_object_to_dict(c) for c in getattr(fields, "components", [])],
            "fix_versions": [_object_to_dict(v) for v in getattr(fields, "fixVersions", [])],
            "versions": [_object_to_dict(v) for v in getattr(fields, "versions", [])],
            "subtasks": [_object_to_dict(s) for s in getattr(fields, "subtasks", [])],
            "comments": comments_payload,
        }

        return _json_dumps(issue_data)
    except Exception as exc:
        logger.error("Issue detail fetch failure for %s: %s", normalized_key, str(exc))
        return _error(f"Error: Unable to fetch issue tracking data for key '{normalized_key}'", exc)


@profiled_tool("READONLY_CORE")
def get_issue_all_fields(issue_key: str, fields: Optional[str] = None) -> str:
    """
    Return the full raw JSON payload for an issue, including all custom fields.

    Use this to inspect custom field values (epic link, collaborators, estimates,
    start/target dates, story points, etc.) that get_issue_details does not surface.

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
        fields: Optional comma-separated list of field ids to return
                (e.g. "customfield_10001,customfield_22701,customfield_11712").
                If omitted, all fields are returned.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    normalized_key = _normalize_issue_key(issue_key)
    try:
        params: Dict[str, Any] = {}
        if fields:
            params["fields"] = fields.strip()
        data = _get(f"/rest/api/2/issue/{normalized_key}", params=params if params else None)
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to fetch full fields for {normalized_key}", exc)


@profiled_tool("READONLY_CORE")
def get_issue_editmeta(issue_key: str) -> str:
    """
    Return the edit metadata for an issue — which fields are editable and their
    allowed values/schemas. Use before updating custom fields to confirm they
    are settable and to discover accepted value formats.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    normalized_key = _normalize_issue_key(issue_key)
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{normalized_key}/editmeta"))
    except Exception as exc:
        return _error(f"Unable to fetch edit metadata for {normalized_key}", exc)


@profiled_tool("READONLY_CORE")
def validate_jql(jql_query: str, max_results: int = 1) -> str:
    """
    Validate a JQL query by executing a tiny bounded search.
    """
    if not jql_query or not jql_query.strip():
        return "Error: jql_query is required."
    try:
        jira_client.search_issues(jql_query, maxResults=max(1, min(int(max_results), 5)))
        return _json_dumps({"valid": True, "jql_query": jql_query})
    except Exception as exc:
        return _json_dumps({"valid": False, "jql_query": jql_query, "error": _error("JQL validation failed", exc)})


# ---------------------------------------------------------------------------
# Project, schema, and metadata discovery
# ---------------------------------------------------------------------------

@profiled_tool("METADATA")
def list_projects() -> str:
    """List Jira projects visible to the authenticated account."""
    try:
        projects = jira_client.projects()
        return _json_dumps([
            {
                "key": getattr(project, "key", None),
                "id": getattr(project, "id", None),
                "name": getattr(project, "name", None),
                "project_type_key": getattr(project, "projectTypeKey", None),
            }
            for project in projects
        ])
    except Exception as exc:
        return _error("Unable to list projects", exc)


@profiled_tool("METADATA")
def get_project_metadata(project_key: str) -> str:
    """Return project metadata for a Jira project key."""
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    try:
        project = jira_client.project(project_key.strip().upper())
        return _json_dumps(_object_to_dict(project))
    except Exception as exc:
        return _error(f"Unable to fetch project metadata for {project_key}", exc)


@profiled_tool("METADATA")
def get_create_issue_metadata(project_key: Optional[str] = None, issue_type: Optional[str] = None) -> str:
    """
    Return Jira create metadata, including required fields and allowed values when available.
    """
    try:
        kwargs: Dict[str, Any] = {}
        if project_key:
            kwargs["projectKeys"] = project_key.strip().upper()
        if issue_type:
            kwargs["issuetypeNames"] = issue_type
        # python-jira supports createmeta in many versions. Fall back to REST if absent.
        if hasattr(jira_client, "createmeta"):
            data = jira_client.createmeta(expand="projects.issuetypes.fields", **kwargs)
        else:
            params = {"expand": "projects.issuetypes.fields"}
            params.update(kwargs)
            data = _get("/rest/api/2/issue/createmeta", params=params)
        return _json_dumps(data)
    except Exception as exc:
        return _error("Unable to fetch create issue metadata", exc)


@profiled_tool("METADATA")
def list_issue_types(project_key: Optional[str] = None) -> str:
    """List issue types, optionally scoped through project create metadata."""
    try:
        if project_key:
            raw = get_create_issue_metadata(project_key=project_key)
            try:
                metadata = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw  # propagate upstream error as-is
            issue_types = []
            for project in metadata.get("projects", []):
                issue_types.extend(project.get("issuetypes", []))
            return _json_dumps(issue_types)
        issue_types = jira_client.issue_types()
        return _json_dumps([_object_to_dict(t) for t in issue_types])
    except Exception as exc:
        return _error("Unable to list issue types", exc)


@profiled_tool("METADATA")
def list_priorities() -> str:
    """List Jira priority values."""
    try:
        priorities = jira_client.priorities()
        return _json_dumps([_object_to_dict(p) for p in priorities])
    except Exception as exc:
        return _error("Unable to list priorities", exc)


@profiled_tool("METADATA")
def list_fields() -> str:
    """List Jira fields, including custom fields."""
    try:
        return _json_dumps(jira_client.fields())
    except Exception as exc:
        return _error("Unable to list fields", exc)


@profiled_tool("METADATA")
def get_custom_field_options(field_id: str, context_id: Optional[str] = None) -> str:
    """
    Return allowed options for a Jira custom field.

    Args:
        field_id: Custom field id such as customfield_10010, or numeric id such as 10010.
        context_id: Optional field context id. If omitted, the tool first attempts context
                    discovery where available, then returns legacy endpoint behavior.

    Notes:
        Jira custom field option APIs vary by Jira Data Center version and field type.
        This tool returns the raw REST payload so agents can inspect the exact option
        ids/values accepted by the instance.
    """
    if not field_id or not str(field_id).strip():
        return "Error: field_id is required."

    raw_field_id = str(field_id).strip()
    numeric_id = raw_field_id.replace("customfield_", "")
    canonical_field_id = raw_field_id if raw_field_id.startswith("customfield_") else f"customfield_{numeric_id}"

    try:
        if context_id:
            return _json_dumps(
                _get(f"/rest/api/2/field/{canonical_field_id}/context/{context_id}/option")
            )

        attempts: List[Dict[str, Any]] = []

        for candidate_field in (raw_field_id, canonical_field_id):
            context_path = f"/rest/api/2/field/{candidate_field}/context"
            try:
                contexts = _get(context_path)
                attempts.append({"path": context_path, "ok": True, "response": contexts})
                values = contexts.get("values", []) if isinstance(contexts, dict) else []
                options_by_context = []
                for context in values:
                    cid = context.get("id")
                    if cid:
                        option_path = f"/rest/api/2/field/{candidate_field}/context/{cid}/option"
                        options = _get(option_path)
                        options_by_context.append(
                            {"context": context, "options_path": option_path, "options": options}
                        )
                if options_by_context:
                    return _json_dumps(
                        {
                            "field_id": raw_field_id,
                            "canonical_field_id": canonical_field_id,
                            "contexts": options_by_context,
                        }
                    )
            except Exception as context_exc:
                attempts.append({"path": context_path, "ok": False, "error": str(context_exc)})

        for candidate_path in (
            f"/rest/api/2/customFieldOption/{raw_field_id}",
            f"/rest/api/2/customFieldOption/{numeric_id}",
        ):
            try:
                return _json_dumps(
                    {
                        "field_id": raw_field_id,
                        "canonical_field_id": canonical_field_id,
                        "legacy_endpoint": candidate_path,
                        "response": _get(candidate_path),
                        "context_discovery_attempts": attempts,
                    }
                )
            except Exception as legacy_exc:
                attempts.append({"path": candidate_path, "ok": False, "error": str(legacy_exc)})

        return _json_dumps(
            {
                "field_id": raw_field_id,
                "canonical_field_id": canonical_field_id,
                "found": False,
                "message": (
                    "Unable to discover options for this field through available Jira REST endpoints. "
                    "Use get_create_issue_metadata(project_key, issue_type) for screen-scoped allowed values, "
                    "or provide context_id if your Jira version exposes field context option APIs."
                ),
                "attempts": attempts,
            }
        )
    except Exception as exc:
        return _error(f"Unable to fetch custom field options for {raw_field_id}", exc)


@profiled_tool("METADATA")
def list_components(project_key: str) -> str:
    """List components for a project."""
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    try:
        components = jira_client.project_components(project_key.strip().upper())
        return _json_dumps([_object_to_dict(c) for c in components])
    except Exception as exc:
        return _error(f"Unable to list components for {project_key}", exc)


@profiled_tool("METADATA")
def list_versions(project_key: str) -> str:
    """List versions/releases for a project."""
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    try:
        versions = jira_client.project_versions(project_key.strip().upper())
        return _json_dumps([_object_to_dict(v) for v in versions])
    except Exception as exc:
        return _error(f"Unable to list versions for {project_key}", exc)


# ---------------------------------------------------------------------------
# Issue mutation
# ---------------------------------------------------------------------------

@profiled_tool("ISSUE_WRITE")
def create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Story",
    priority: Optional[str] = None,
) -> str:
    """Create a new Jira issue."""
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not description or not description.strip():
        return "Error: description is required."

    try:
        issue_dict: Dict[str, Any] = {
            "project": {"key": project_key.strip().upper()},
            "summary": summary.strip(),
            "description": description,
            "issuetype": {"name": issue_type or "Story"},
        }
        if priority:
            issue_dict["priority"] = {"name": priority}

        new_issue = jira_client.create_issue(fields=issue_dict)
        return f"Success: Tracking node mapped. Key: {new_issue.key} | URL: {JIRA_URL}/browse/{new_issue.key}"
    except Exception as exc:
        return _error("Failed to execute node provisioning mutation", exc)


@profiled_tool("ISSUE_WRITE")
def create_subtask(parent_issue_key: str, summary: str, description: str, issue_type: str = "Sub-task") -> str:
    """Create a subtask under an existing parent issue."""
    err = _validate_issue_key(parent_issue_key)
    if err:
        return f"Error: {err}"
    if not summary or not summary.strip():
        return "Error: summary is required."
    try:
        parent = jira_client.issue(_normalize_issue_key(parent_issue_key))
        project_key = parent.fields.project.key
        issue_dict = {
            "project": {"key": project_key},
            "parent": {"key": parent.key},
            "summary": summary.strip(),
            "description": description or "",
            "issuetype": {"name": issue_type},
        }
        new_issue = jira_client.create_issue(fields=issue_dict)
        return f"Success: Subtask created. Key: {new_issue.key} | Parent: {parent.key} | URL: {JIRA_URL}/browse/{new_issue.key}"
    except Exception as exc:
        return _error(f"Unable to create subtask under {parent_issue_key}", exc)


@profiled_tool("READONLY_CORE")
def list_subtasks(issue_key: str) -> str:
    """List subtasks under an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        subtasks = getattr(issue.fields, "subtasks", [])
        return _json_dumps([_object_to_dict(subtask) for subtask in subtasks])
    except Exception as exc:
        return _error(f"Unable to list subtasks for {issue_key}", exc)


@profiled_tool("ISSUE_WRITE")
def update_issue(issue_key: str, fields_json: str) -> str:
    """
    Update arbitrary Jira issue fields using a JSON object string.
    Example fields_json: {"labels":["triage"],"priority":{"name":"High"}}
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        fields = _parse_json_object(fields_json, "fields_json")
        if not fields:
            return "Execution short-circuited: fields_json is empty."
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields=fields)
        return f"Success: Issue fields updated for {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error("Unable to update issue fields", exc)


@profiled_tool("ISSUE_WRITE")
def update_issue_structured(
    issue_key: str,
    labels_json: Optional[str] = None,
    components_json: Optional[str] = None,
    fix_versions_json: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    parent_key: Optional[str] = None,
    epic_link: Optional[str] = None,
    story_points: Optional[float] = None,
    custom_fields_json: Optional[str] = None,
) -> str:
    """
    Structured issue update wrapper for common fields and custom fields.

    JSON args must be JSON arrays/objects:
    labels_json: ["backend","urgent"]
    components_json: [{"name":"API"}]
    fix_versions_json: [{"name":"1.2.0"}]
    custom_fields_json: {"customfield_10016": 5}
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"

    try:
        fields: Dict[str, Any] = {}
        if labels_json is not None:
            fields["labels"] = _parse_json_array(labels_json, "labels_json")
        if components_json is not None:
            fields["components"] = _parse_json_array(components_json, "components_json")
        if fix_versions_json is not None:
            fields["fixVersions"] = _parse_json_array(fix_versions_json, "fix_versions_json")
        if priority:
            fields["priority"] = {"name": priority}
        if due_date:
            fields["duedate"] = due_date
        if parent_key:
            fields["parent"] = {"key": _normalize_issue_key(parent_key)}
        if epic_link:
            # Common Jira Software Data Center epic link field; many instances use a custom field instead.
            fields["Epic Link"] = epic_link
        if story_points is not None:
            # Common but instance-dependent. Prefer custom_fields_json if your instance uses a custom field id.
            fields["Story Points"] = story_points
        if custom_fields_json:
            fields.update(_parse_json_object(custom_fields_json, "custom_fields_json"))

        if not fields:
            return "Execution short-circuited: No structured fields supplied."

        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields=fields)
        return f"Success: Structured issue update applied to {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error("Unable to apply structured issue update", exc)


@profiled_tool("ISSUE_WRITE")
def update_issue_fields(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_username: Optional[str] = None,
) -> str:
    """Update summary, description, or assignee on an existing issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"

    normalized_key = _normalize_issue_key(issue_key)

    try:
        issue = jira_client.issue(normalized_key)
        update_fields: Dict[str, Any] = {}
        if summary:
            update_fields["summary"] = summary
        if description:
            update_fields["description"] = description
        if assignee_username:
            update_fields["assignee"] = {"name": assignee_username}
        if not update_fields:
            return "Execution short-circuited: No active parameters passed for mutation processing."

        issue.update(fields=update_fields)
        return f"Success: Operational mutations applied cleanly to target issue: {normalized_key}."
    except Exception as exc:
        return _error("Failure encountered writing issue field mutations", exc)


@profiled_tool("DESTRUCTIVE")
def delete_issue(issue_key: str, confirm: bool = False, delete_subtasks: bool = False) -> str:
    """
    Delete an issue. Destructive operation requiring confirm=True.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not confirm:
        return "Refused: delete_issue requires confirm=True."
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.delete(deleteSubtasks=delete_subtasks)
        return f"Success: Issue {_normalize_issue_key(issue_key)} deleted."
    except Exception as exc:
        return _error(f"Unable to delete issue {issue_key}", exc)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@profiled_tool("WORKFLOW_READ")
def get_available_transitions(issue_key: str) -> str:
    """Return transitions currently available for an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(jira_client.transitions(_normalize_issue_key(issue_key)))
    except Exception as exc:
        return _error(f"Unable to fetch transitions for {issue_key}", exc)


@profiled_tool("WORKFLOW_WRITE")
def transition_issue(issue_key: str, transition_name_or_id: str) -> str:
    """Transition an issue by destination transition name or numeric id."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not transition_name_or_id or not str(transition_name_or_id).strip():
        return "Error: transition_name_or_id is required."

    normalized_key = _normalize_issue_key(issue_key)

    try:
        transition_lookup = _find_transition_id(normalized_key, transition_name_or_id)
        target_id = transition_lookup["target_id"]
        if not target_id:
            options_block = ", ".join(f"'{o['name']}' (ID: {o['id']})" for o in transition_lookup["options"])
            return (
                f"Transition Refused: '{transition_name_or_id}' is not a valid or reachable target from "
                f"the current workflow state of issue {normalized_key}.\n"
                f"Valid structural transitions available right now are: {options_block}"
            )
        jira_client.transition_issue(normalized_key, target_id)
        return f"Success: Target issue {normalized_key} transitioned via pipeline route '{transition_name_or_id}'."
    except Exception as exc:
        return _error("Workflow Execution Fault", exc)


@profiled_tool("WORKFLOW_WRITE")
def transition_issue_with_fields(
    issue_key: str,
    transition_name_or_id: str,
    fields_json: Optional[str] = None,
    comment: Optional[str] = None,
    resolution: Optional[str] = None,
) -> str:
    """
    Transition an issue and optionally supply required fields, resolution, and a transition comment.

    fields_json is a JSON object string merged into the transition fields payload.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    normalized_key = _normalize_issue_key(issue_key)

    try:
        transition_lookup = _find_transition_id(normalized_key, transition_name_or_id)
        target_id = transition_lookup["target_id"]
        if not target_id:
            options_block = ", ".join(f"'{o['name']}' (ID: {o['id']})" for o in transition_lookup["options"])
            return f"Transition Refused. Valid transitions: {options_block}"

        fields = _parse_json_object(fields_json, "fields_json") if fields_json else {}
        if resolution:
            fields["resolution"] = {"name": resolution}

        payload: Dict[str, Any] = {"transition": {"id": target_id}}
        if fields:
            payload["fields"] = fields
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}

        _post(f"/rest/api/2/issue/{normalized_key}/transitions", payload=payload)
        return f"Success: Issue {normalized_key} transitioned via '{transition_name_or_id}' with supplied fields."
    except Exception as exc:
        return _error("Workflow transition with fields failed", exc)


@profiled_tool("WORKFLOW_READ")
def list_statuses() -> str:
    """List Jira statuses."""
    try:
        return _json_dumps(_get("/rest/api/2/status"))
    except Exception as exc:
        return _error("Unable to list statuses", exc)


@profiled_tool("WORKFLOW_READ")
def list_resolutions() -> str:
    """List Jira resolutions."""
    try:
        return _json_dumps(_get("/rest/api/2/resolution"))
    except Exception as exc:
        return _error("Unable to list resolutions", exc)


@profiled_tool("WORKFLOW_READ")
def list_workflows(project_key: Optional[str] = None) -> str:
    """
    List workflows visible through REST. If project_key is supplied, returns workflow scheme/project related details when available.
    """
    try:
        if project_key:
            return _json_dumps(_get(f"/rest/api/2/project/{project_key.strip().upper()}/statuses"))
        return _json_dumps(_get("/rest/api/2/workflow"))
    except Exception as exc:
        return _error("Unable to list workflows/status workflow metadata", exc)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@profiled_tool("COMMENT_WRITE")
def add_comment(issue_key: str, body: str) -> str:
    """Add a comment to an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not body or not body.strip():
        return "Error: body is required."

    normalized_key = _normalize_issue_key(issue_key)
    try:
        comment_node = jira_client.add_comment(normalized_key, body)
        return f"Success: Comment posted successfully. Comment ID: {comment_node.id}"
    except Exception as exc:
        return _error("Aborted: Error appending commentary timeline component", exc)


@profiled_tool("READONLY_CORE")
def list_comments(issue_key: str) -> str:
    """List comments for an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        data = _get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/comment")
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to list comments for {issue_key}", exc)


@profiled_tool("COMMENT_WRITE")
def update_comment(issue_key: str, comment_id: str, body: str) -> str:
    """Update a comment body."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not comment_id or not body:
        return "Error: comment_id and body are required."
    try:
        data = _put(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/comment/{comment_id}", {"body": body})
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to update comment {comment_id}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_comment(issue_key: str, comment_id: str, confirm: bool = False) -> str:
    """Delete a comment. Destructive operation requiring confirm=True."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not confirm:
        return "Refused: delete_comment requires confirm=True."
    try:
        _delete(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/comment/{comment_id}")
        return f"Success: Comment {comment_id} deleted from {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to delete comment {comment_id}", exc)


# ---------------------------------------------------------------------------
# Assignment, watchers, users, permissions, server info
# ---------------------------------------------------------------------------

@profiled_tool("ASSIGNMENT_WRITE")
def assign_issue(issue_key: str, assignee_username: str) -> str:
    """Assign an issue to a Jira username."""
    return update_issue_fields(issue_key=issue_key, assignee_username=assignee_username)


@profiled_tool("ASSIGNMENT_WRITE")
def unassign_issue(issue_key: str) -> str:
    """Unassign an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields={"assignee": {"name": None}})
        return f"Success: Issue {_normalize_issue_key(issue_key)} unassigned."
    except Exception as exc:
        return _error(f"Unable to unassign issue {issue_key}", exc)


@profiled_tool("READONLY_CORE")
def list_watchers(issue_key: str) -> str:
    """List issue watchers."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/watchers"))
    except Exception as exc:
        return _error(f"Unable to list watchers for {issue_key}", exc)


@profiled_tool("ASSIGNMENT_WRITE")
def watch_issue(issue_key: str, username: Optional[str] = None) -> str:
    """Watch an issue as current user or add username as watcher when supplied."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        if username:
            # Jira watcher API expects a raw JSON string body, not a JSON object.
            _request("POST", f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/watchers", json=username)
        else:
            jira_client.add_watcher(_normalize_issue_key(issue_key), jira_client.current_user())
        return f"Success: watcher added for {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to watch issue {issue_key}", exc)


@profiled_tool("ASSIGNMENT_WRITE")
def unwatch_issue(issue_key: str, username: Optional[str] = None) -> str:
    """Remove current user or supplied username from issue watchers."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        watcher = username or jira_client.current_user()
        _delete(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/watchers", params={"username": watcher})
        return f"Success: watcher removed from {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to unwatch issue {issue_key}", exc)


@profiled_tool("METADATA")
def search_users(query: str) -> str:
    """Search Jira users."""
    if not query or not query.strip():
        return "Error: query is required."

    try:
        users = jira_client.search_users(query)
        if not users:
            return f"Directory Lookup Result: Zero target users mapped for query: '{query}'."

        lines = [
            "### Identity Mapping Query Matches\n",
            "| Display Name | Username / Key | Active State |",
            "| :--- | :--- | :--- |",
        ]
        for user in users:
            display_name = getattr(user, "displayName", "N/A")
            username = getattr(user, "name", None) or getattr(user, "key", "N/A")
            active = "Active" if getattr(user, "active", False) else "Inactive"
            lines.append(f"| {display_name} | `{username}` | {active} |")
        return "\n".join(lines)
    except Exception as exc:
        return _error("Directory Engine reported a lookup fault", exc)


@profiled_tool("METADATA")
def get_myself() -> str:
    """Return the authenticated Jira user."""
    try:
        if hasattr(jira_client, "myself"):
            return _json_dumps(jira_client.myself())
        return _json_dumps(_get("/rest/api/2/myself"))
    except Exception as exc:
        return _error("Unable to fetch authenticated Jira user", exc)


@profiled_tool("METADATA")
def get_my_permissions(project_key: Optional[str] = None, issue_key: Optional[str] = None) -> str:
    """Return permissions for the authenticated Jira user, optionally scoped to project or issue."""
    try:
        params = {}
        if project_key:
            params["projectKey"] = project_key.strip().upper()
        if issue_key:
            params["issueKey"] = _normalize_issue_key(issue_key)
        return _json_dumps(_get("/rest/api/2/mypermissions", params=params))
    except Exception as exc:
        return _error("Unable to fetch permissions", exc)


@profiled_tool("METADATA")
def get_server_info() -> str:
    """Return Jira server info."""
    try:
        if hasattr(jira_client, "server_info"):
            return _json_dumps(jira_client.server_info())
        return _json_dumps(_get("/rest/api/2/serverInfo"))
    except Exception as exc:
        return _error("Unable to fetch Jira server info", exc)


# ---------------------------------------------------------------------------
# Changelog/history/activity
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def get_issue_changelog(issue_key: str, max_results: int = 100) -> str:
    """Return issue changelog/history."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        data = _get(
            f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}",
            params={"expand": "changelog", "maxResults": max(1, min(int(max_results), 1000))},
        )
        return _json_dumps(data.get("changelog", data))
    except Exception as exc:
        return _error(f"Unable to fetch changelog for {issue_key}", exc)


@profiled_tool("READONLY_CORE")
def get_issue_activity(issue_key: str, max_results: int = 100) -> str:
    """
    Return a compact activity view from changelog plus comments.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue_data = _get(
            f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}",
            params={"expand": "changelog"},
        )
        comments = _get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/comment").get("comments", [])
        histories = issue_data.get("changelog", {}).get("histories", [])
        events = []
        for history in histories:
            events.append({
                "type": "change",
                "created": history.get("created"),
                "author": history.get("author", {}),
                "items": history.get("items", []),
            })
        for comment in comments:
            events.append({
                "type": "comment",
                "created": comment.get("created"),
                "author": comment.get("author", {}),
                "id": comment.get("id"),
                "body": comment.get("body"),
            })
        events.sort(key=lambda item: item.get("created") or "")
        return _json_dumps(events[-max(1, min(int(max_results), 1000)):])
    except Exception as exc:
        return _error(f"Unable to fetch activity for {issue_key}", exc)


# ---------------------------------------------------------------------------
# Links, remote links, and properties
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def list_issue_links(issue_key: str) -> str:
    """List issue links from an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        return _json_dumps([_object_to_dict(link) for link in getattr(issue.fields, "issuelinks", [])])
    except Exception as exc:
        return _error(f"Unable to list issue links for {issue_key}", exc)


@profiled_tool("READONLY_CORE")
def list_issue_link_types() -> str:
    """List available Jira issue link types."""
    try:
        if hasattr(jira_client, "issue_link_types"):
            return _json_dumps([_object_to_dict(t) for t in jira_client.issue_link_types()])
        return _json_dumps(_get("/rest/api/2/issueLinkType"))
    except Exception as exc:
        return _error("Unable to list issue link types", exc)


@profiled_tool("LINK_WRITE")
def create_issue_link(inward_issue_key: str, outward_issue_key: str, link_type: str, comment: Optional[str] = None) -> str:
    """Create an issue link between two issues."""
    err = _validate_issue_keys([inward_issue_key, outward_issue_key])
    if err:
        return f"Error: {err}"
    try:
        kwargs = {}
        if comment:
            kwargs["comment"] = {"body": comment}
        jira_client.create_issue_link(
            type=link_type,
            inwardIssue=_normalize_issue_key(inward_issue_key),
            outwardIssue=_normalize_issue_key(outward_issue_key),
            **kwargs,
        )
        return f"Success: Linked {_normalize_issue_key(inward_issue_key)} -> {_normalize_issue_key(outward_issue_key)} as {link_type}."
    except Exception as exc:
        return _error("Unable to create issue link", exc)


@profiled_tool("DESTRUCTIVE")
def delete_issue_link(link_id: str, confirm: bool = False) -> str:
    """Delete an issue link. Destructive operation requiring confirm=True."""
    if not confirm:
        return "Refused: delete_issue_link requires confirm=True."
    try:
        _delete(f"/rest/api/2/issueLink/{link_id}")
        return f"Success: Issue link {link_id} deleted."
    except Exception as exc:
        return _error(f"Unable to delete issue link {link_id}", exc)


@profiled_tool("READONLY_CORE")
def list_remote_links(issue_key: str) -> str:
    """List remote links for an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/remotelink"))
    except Exception as exc:
        return _error(f"Unable to list remote links for {issue_key}", exc)


@profiled_tool("LINK_WRITE")
def add_remote_link(issue_key: str, url: str, title: str, summary: Optional[str] = None, global_id: Optional[str] = None) -> str:
    """Add a remote web link to an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not url or not title:
        return "Error: url and title are required."
    try:
        payload: Dict[str, Any] = {"object": {"url": url, "title": title}}
        if summary:
            payload["object"]["summary"] = summary
        if global_id:
            payload["globalId"] = global_id
        data = _post(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/remotelink", payload=payload)
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to add remote link to {issue_key}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_remote_link(issue_key: str, link_id: str, confirm: bool = False) -> str:
    """Delete a remote link. Destructive operation requiring confirm=True."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not confirm:
        return "Refused: delete_remote_link requires confirm=True."
    try:
        _delete(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/remotelink/{link_id}")
        return f"Success: Remote link {link_id} deleted from {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to delete remote link {link_id}", exc)


@profiled_tool("READONLY_CORE")
def list_issue_properties(issue_key: str) -> str:
    """List issue property keys."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/properties"))
    except Exception as exc:
        return _error(f"Unable to list issue properties for {issue_key}", exc)


@profiled_tool("READONLY_CORE")
def get_issue_property(issue_key: str, property_key: str) -> str:
    """Get a Jira issue property value."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/properties/{property_key}"))
    except Exception as exc:
        return _error(f"Unable to get issue property {property_key}", exc)


@profiled_tool("PROPERTY_WRITE")
def set_issue_property(issue_key: str, property_key: str, value_json: str) -> str:
    """Set a Jira issue property value from JSON."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        try:
            value = json.loads(value_json)
        except (json.JSONDecodeError, TypeError) as parse_err:
            return f"Error: value_json must be valid JSON. {parse_err}"
        _put(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/properties/{property_key}", value)
        return f"Success: Issue property {property_key} set on {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to set issue property {property_key}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_issue_property(issue_key: str, property_key: str, confirm: bool = False) -> str:
    """Delete a Jira issue property. Destructive operation requiring confirm=True."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not confirm:
        return "Refused: delete_issue_property requires confirm=True."
    try:
        _delete(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/properties/{property_key}")
        return f"Success: Issue property {property_key} deleted from {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to delete issue property {property_key}", exc)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def list_attachments(issue_key: str) -> str:
    """List attachments on an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        attachments = getattr(issue.fields, "attachment", [])
        return _json_dumps([_object_to_dict(a) for a in attachments])
    except Exception as exc:
        return _error(f"Unable to list attachments for {issue_key}", exc)


_SENSITIVE_FILE_NAMES = {".env", ".env.local", ".env.production", ".env.development", ".env.staging"}
_SENSITIVE_DIR_NAMES = {".ssh", ".gnupg", ".aws", ".azure"}


@profiled_tool("ATTACHMENT_WRITE")
def add_attachment(issue_key: str, file_path: str) -> str:
    """Attach a local file path to an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        return f"Error: file_path does not exist or is not a file: {file_path}"
    if path.name.lower() in _SENSITIVE_FILE_NAMES or path.name.lower().startswith(".env."):
        return f"Error: Refusing to attach potentially sensitive file: {path.name}"
    if any(part.lower() in _SENSITIVE_DIR_NAMES for part in path.parts):
        return f"Error: Refusing to attach file from sensitive directory: {file_path}"
    try:
        attachment = jira_client.add_attachment(issue=_normalize_issue_key(issue_key), attachment=str(path))
        return _json_dumps(_object_to_dict(attachment))
    except Exception as exc:
        return _error(f"Unable to add attachment to {issue_key}", exc)


@profiled_tool("READONLY_CORE")
def download_attachment(attachment_id: str, output_path: str) -> str:
    """Download an attachment by id to a local output path."""
    if not attachment_id or not output_path:
        return "Error: attachment_id and output_path are required."
    try:
        output = Path(output_path).resolve()
        cwd = Path.cwd().resolve()
        if not output.is_relative_to(cwd):
            return f"Error: output_path must be within the current working directory: {cwd}"
        attachment = jira_client.attachment(attachment_id)
        data = attachment.get()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        return f"Success: Attachment {attachment_id} written to {output}."
    except Exception as exc:
        return _error(f"Unable to download attachment {attachment_id}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_attachment(attachment_id: str, confirm: bool = False) -> str:
    """Delete an attachment. Destructive operation requiring confirm=True."""
    if not confirm:
        return "Refused: delete_attachment requires confirm=True."
    try:
        _delete(f"/rest/api/2/attachment/{attachment_id}")
        return f"Success: Attachment {attachment_id} deleted."
    except Exception as exc:
        return _error(f"Unable to delete attachment {attachment_id}", exc)


# ---------------------------------------------------------------------------
# Worklogs
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def list_worklogs(issue_key: str) -> str:
    """List worklogs for an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/worklog"))
    except Exception as exc:
        return _error(f"Unable to list worklogs for {issue_key}", exc)


@profiled_tool("WORKLOG_WRITE")
def add_worklog(issue_key: str, time_spent: str, comment: Optional[str] = None, started: Optional[str] = None) -> str:
    """Add a worklog. time_spent examples: '1h', '30m', '2d 3h'."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not time_spent:
        return "Error: time_spent is required."
    try:
        payload: Dict[str, Any] = {"timeSpent": time_spent}
        if comment:
            payload["comment"] = comment
        if started:
            payload["started"] = started
        return _json_dumps(_post(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/worklog", payload=payload))
    except Exception as exc:
        return _error(f"Unable to add worklog to {issue_key}", exc)


@profiled_tool("WORKLOG_WRITE")
def update_worklog(issue_key: str, worklog_id: str, time_spent: Optional[str] = None, comment: Optional[str] = None, started: Optional[str] = None) -> str:
    """Update a worklog."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        payload: Dict[str, Any] = {}
        if time_spent:
            payload["timeSpent"] = time_spent
        if comment:
            payload["comment"] = comment
        if started:
            payload["started"] = started
        if not payload:
            return "Execution short-circuited: no worklog fields supplied."
        return _json_dumps(_put(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/worklog/{worklog_id}", payload))
    except Exception as exc:
        return _error(f"Unable to update worklog {worklog_id}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_worklog(issue_key: str, worklog_id: str, confirm: bool = False) -> str:
    """Delete a worklog. Destructive operation requiring confirm=True."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not confirm:
        return "Refused: delete_worklog requires confirm=True."
    try:
        _delete(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/worklog/{worklog_id}")
        return f"Success: Worklog {worklog_id} deleted from {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to delete worklog {worklog_id}", exc)


# ---------------------------------------------------------------------------
# Jira Software Agile
# ---------------------------------------------------------------------------

@profiled_tool("AGILE_READ")
def list_boards(project_key: Optional[str] = None, board_type: Optional[str] = None) -> str:
    """List Jira Software boards, optionally filtered by project key and board type."""
    try:
        params: Dict[str, Any] = {}
        if project_key:
            params["projectKeyOrId"] = project_key.strip().upper()
        if board_type:
            params["type"] = board_type
        return _json_dumps(_get("/rest/agile/1.0/board", params=params))
    except Exception as exc:
        return _error("Unable to list boards", exc)


@profiled_tool("AGILE_READ")
def get_board_configuration(board_id: int) -> str:
    """Get board configuration."""
    try:
        return _json_dumps(_get(f"/rest/agile/1.0/board/{board_id}/configuration"))
    except Exception as exc:
        return _error(f"Unable to fetch board configuration for {board_id}", exc)


@profiled_tool("AGILE_READ")
def list_sprints(board_id: int, state: Optional[str] = None) -> str:
    """List sprints for a board. state may be active, future, closed, or comma-separated."""
    try:
        params = {"state": state} if state else None
        return _json_dumps(_get(f"/rest/agile/1.0/board/{board_id}/sprint", params=params))
    except Exception as exc:
        return _error(f"Unable to list sprints for board {board_id}", exc)


@profiled_tool("AGILE_READ")
def get_sprint(sprint_id: int) -> str:
    """Get sprint details."""
    try:
        return _json_dumps(_get(f"/rest/agile/1.0/sprint/{sprint_id}"))
    except Exception as exc:
        return _error(f"Unable to fetch sprint {sprint_id}", exc)


@profiled_tool("AGILE_READ")
def list_sprint_issues(sprint_id: int, max_results: int = 50) -> str:
    """List issues in a sprint."""
    try:
        return _json_dumps(_get(f"/rest/agile/1.0/sprint/{sprint_id}/issue", params={"maxResults": max(1, min(int(max_results), 100))}))
    except Exception as exc:
        return _error(f"Unable to list issues for sprint {sprint_id}", exc)


@profiled_tool("AGILE_WRITE")
def move_issues_to_sprint(sprint_id: int, issue_keys: List[str]) -> str:
    """Move explicit issues to a sprint."""
    err = _validate_issue_keys(issue_keys)
    if err:
        return f"Error: {err}"
    try:
        payload = {"issues": _normalize_issue_keys(issue_keys)}
        _post(f"/rest/agile/1.0/sprint/{sprint_id}/issue", payload=payload)
        return f"Success: Moved {len(issue_keys)} issues to sprint {sprint_id}."
    except Exception as exc:
        return _error(f"Unable to move issues to sprint {sprint_id}", exc)


@profiled_tool("AGILE_WRITE")
def move_issues_to_backlog(issue_keys: List[str]) -> str:
    """Move explicit issues to backlog."""
    err = _validate_issue_keys(issue_keys)
    if err:
        return f"Error: {err}"
    try:
        _post("/rest/agile/1.0/backlog/issue", payload={"issues": _normalize_issue_keys(issue_keys)})
        return f"Success: Moved {len(issue_keys)} issues to backlog."
    except Exception as exc:
        return _error("Unable to move issues to backlog", exc)


@profiled_tool("AGILE_WRITE")
def rank_issue(issue_key: str, before_issue_key: Optional[str] = None, after_issue_key: Optional[str] = None) -> str:
    """Rank an issue before or after another issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not before_issue_key and not after_issue_key:
        return "Error: either before_issue_key or after_issue_key is required."
    if before_issue_key and after_issue_key:
        return "Error: provide only one of before_issue_key or after_issue_key."
    try:
        payload: Dict[str, Any] = {"issues": [_normalize_issue_key(issue_key)]}
        if before_issue_key:
            err = _validate_issue_key(before_issue_key)
            if err:
                return f"Error: before_issue_key: {err}"
            payload["rankBeforeIssue"] = _normalize_issue_key(before_issue_key)
        if after_issue_key:
            err = _validate_issue_key(after_issue_key)
            if err:
                return f"Error: after_issue_key: {err}"
            payload["rankAfterIssue"] = _normalize_issue_key(after_issue_key)
        _put("/rest/agile/1.0/issue/rank", payload)
        return f"Success: Ranked {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to rank issue {issue_key}", exc)


# ---------------------------------------------------------------------------
# Filters, roles, groups, security
# ---------------------------------------------------------------------------

@profiled_tool("ADMIN_READ")
def list_filters(favourite: bool = True) -> str:
    """List favorite filters by default, or all visible filters where supported."""
    try:
        path = "/rest/api/2/filter/favourite" if favourite else "/rest/api/2/filter"
        return _json_dumps(_get(path))
    except Exception as exc:
        return _error("Unable to list filters", exc)


@profiled_tool("ADMIN_READ")
def get_filter(filter_id: str) -> str:
    """Get a saved filter."""
    try:
        return _json_dumps(_get(f"/rest/api/2/filter/{filter_id}"))
    except Exception as exc:
        return _error(f"Unable to fetch filter {filter_id}", exc)


@profiled_tool("ADMIN_READ")
def run_filter(filter_id: str, max_results: int = 50) -> str:
    """Run a saved filter by id."""
    try:
        filter_data = _get(f"/rest/api/2/filter/{filter_id}")
        jql = filter_data.get("jql")
        if not jql:
            return f"Error: Filter {filter_id} has no JQL."
        return search_issues(jql, max_results=max_results)
    except Exception as exc:
        return _error(f"Unable to run filter {filter_id}", exc)


@profiled_tool("ADMIN_READ")
def list_project_roles(project_key: str) -> str:
    """List project roles for a project."""
    if not project_key:
        return "Error: project_key is required."
    try:
        return _json_dumps(_get(f"/rest/api/2/project/{project_key.strip().upper()}/role"))
    except Exception as exc:
        return _error(f"Unable to list roles for project {project_key}", exc)


@profiled_tool("ADMIN_READ")
def get_project_role_actors(project_key: str, role_id: str) -> str:
    """Get actors for a project role."""
    if not project_key or not role_id:
        return "Error: project_key and role_id are required."
    try:
        return _json_dumps(_get(f"/rest/api/2/project/{project_key.strip().upper()}/role/{role_id}"))
    except Exception as exc:
        return _error(f"Unable to fetch role actors for {project_key}/{role_id}", exc)


@profiled_tool("ADMIN_READ")
def list_groups(query: Optional[str] = None, max_results: int = 50) -> str:
    """List/search Jira groups."""
    try:
        params = {"maxResults": max(1, min(int(max_results), 100))}
        if query:
            params["query"] = query
        return _json_dumps(_get("/rest/api/2/groups/picker", params=params))
    except Exception as exc:
        return _error("Unable to list/search groups", exc)


@profiled_tool("ADMIN_READ")
def list_security_levels(project_key: Optional[str] = None) -> str:
    """List issue security levels available to the authenticated account where supported."""
    try:
        params = {"projectKey": project_key.strip().upper()} if project_key else None
        return _json_dumps(_get("/rest/api/2/issuesecurityschemes", params=params))
    except Exception as exc:
        return _error("Unable to list issue security levels/schemes", exc)


@profiled_tool("ADMIN_WRITE")
def set_issue_security_level(issue_key: str, security_level_id: str) -> str:
    """Set an issue security level by id."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not security_level_id:
        return "Error: security_level_id is required."
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields={"security": {"id": security_level_id}})
        return f"Success: Security level set on {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to set security level for {issue_key}", exc)


# ---------------------------------------------------------------------------
# Bulk operations. Explicit keys only; no broad JQL mutation.
# ---------------------------------------------------------------------------

@profiled_tool("BULK")
def bulk_update_issues(issue_keys: List[str], fields_json: str, confirm: bool = False) -> str:
    """Bulk update explicit issue keys. Requires confirm=True."""
    if not confirm:
        return "Refused: bulk_update_issues requires confirm=True."
    err = _validate_issue_keys(issue_keys)
    if err:
        return f"Error: {err}"
    try:
        fields = _parse_json_object(fields_json, "fields_json")
        results = []
        for key in _normalize_issue_keys(issue_keys):
            try:
                issue = jira_client.issue(key)
                issue.update(fields=fields)
                results.append({"key": key, "ok": True})
            except Exception as exc:
                results.append({"key": key, "ok": False, "error": str(exc)})
        return _json_dumps(results)
    except Exception as exc:
        return _error("Bulk update failed", exc)


@profiled_tool("BULK")
def bulk_transition_issues(issue_keys: List[str], transition_name_or_id: str, confirm: bool = False) -> str:
    """Bulk transition explicit issue keys. Requires confirm=True."""
    if not confirm:
        return "Refused: bulk_transition_issues requires confirm=True."
    err = _validate_issue_keys(issue_keys)
    if err:
        return f"Error: {err}"
    results = []
    for key in _normalize_issue_keys(issue_keys):
        outcome = transition_issue(key, transition_name_or_id)
        results.append({"key": key, "result": outcome})
    return _json_dumps(results)


@profiled_tool("BULK")
def bulk_add_comment(issue_keys: List[str], body: str, confirm: bool = False) -> str:
    """Bulk add the same comment to explicit issue keys. Requires confirm=True."""
    if not confirm:
        return "Refused: bulk_add_comment requires confirm=True."
    err = _validate_issue_keys(issue_keys)
    if err:
        return f"Error: {err}"
    if not body or not body.strip():
        return "Error: body is required."
    results = []
    for key in _normalize_issue_keys(issue_keys):
        outcome = add_comment(key, body)
        results.append({"key": key, "result": outcome})
    return _json_dumps(results)


def main():
    """Entry point for the console script and ``python -m`` invocation."""
    logger.info("Initializing Jira MCP server stdio runtime with profile %s.", ACTIVE_PROFILE_LABEL)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
