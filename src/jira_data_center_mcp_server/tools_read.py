"""Read-only tools: search, issue inspection, metadata, changelog, activity."""

import logging
from typing import Any, Dict, List, Optional

from .client import (
    JIRA_URL,
    _error,
    _field_name,
    _get,
    _jira_user_to_dict,
    _json_dumps,
    _normalize_issue_key,
    _object_to_dict,
    _validate_issue_key,
    jira_client,
)
from .config import profiled_tool

logger = logging.getLogger("jira_mcp_server")


# ---------------------------------------------------------------------------
# Search, issue read, and validation
# ---------------------------------------------------------------------------

@profiled_tool("READONLY_CORE")
def search_issues(jql_query: str, max_results: int = 50) -> str:
    """
    Query Jira issues using JQL (Jira Query Language).

    Returns a markdown table of matching issues with key, summary, status,
    assignee, and priority. Use for listing, filtering, finding, or reporting
    on groups of issues.

    Examples:
        jql_query="project = PROJ AND status = Open"
        jql_query="assignee = currentUser() ORDER BY updated DESC"
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
def get_issue(issue_key: str, detail_level: str = "full", fields: Optional[str] = None) -> str:
    """
    Retrieve a Jira issue at the requested detail level.

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
        detail_level: One of 'summary', 'full', or 'raw'.
            - summary: Key fields only (key, status, assignee, summary, priority, type).
            - full: Structured view with comments, subtasks, links, versions (default).
            - raw: Complete raw JSON including all custom fields. Use to inspect
                   custom field values (epic link, collaborators, estimates, etc.).
        fields: For raw detail_level only — optional comma-separated field ids to return
                (e.g. "customfield_10001,customfield_22701"). If omitted, all fields returned.

    Use detail_level='full' before updating or resolving an issue.
    Use detail_level='raw' to inspect custom field values not surfaced in the full view.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"

    normalized_key = _normalize_issue_key(issue_key)
    level = (detail_level or "full").strip().lower()

    try:
        if level == "raw":
            params: Dict[str, Any] = {}
            if fields:
                params["fields"] = fields.strip()
            data = _get(f"/rest/api/2/issue/{normalized_key}", params=params if params else None)
            return _json_dumps(data)

        logger.info("Retrieving issue context for: %s (level=%s)", normalized_key, level)
        issue = jira_client.issue(normalized_key)
        f = issue.fields

        if level == "summary":
            return _json_dumps({
                "key": issue.key,
                "url": f"{JIRA_URL}/browse/{issue.key}",
                "summary": getattr(f, "summary", ""),
                "status": _field_name(getattr(f, "status", None)),
                "priority": _field_name(getattr(f, "priority", None)),
                "assignee": _jira_user_to_dict(getattr(f, "assignee", None)),
                "issue_type": _field_name(getattr(f, "issuetype", None)),
            })

        # detail_level == "full"
        comments_payload: List[Dict[str, Any]] = []
        if getattr(f, "comment", None):
            for comment in f.comment.comments:
                comments_payload.append({
                    "id": getattr(comment, "id", None),
                    "author": getattr(getattr(comment, "author", None), "displayName", None),
                    "username": getattr(getattr(comment, "author", None), "name", None),
                    "body": getattr(comment, "body", None),
                    "created": getattr(comment, "created", None),
                })

        return _json_dumps({
            "key": issue.key,
            "id": issue.id,
            "url": f"{JIRA_URL}/browse/{issue.key}",
            "summary": getattr(f, "summary", ""),
            "status": _field_name(getattr(f, "status", None)),
            "priority": _field_name(getattr(f, "priority", None)),
            "creator": _jira_user_to_dict(getattr(f, "creator", None)),
            "reporter": _jira_user_to_dict(getattr(f, "reporter", None)),
            "assignee": _jira_user_to_dict(getattr(f, "assignee", None)),
            "description": getattr(f, "description", ""),
            "created_at": getattr(f, "created", None),
            "updated_at": getattr(f, "updated", None),
            "labels": getattr(f, "labels", []),
            "components": [_object_to_dict(c) for c in getattr(f, "components", [])],
            "fix_versions": [_object_to_dict(v) for v in getattr(f, "fixVersions", [])],
            "versions": [_object_to_dict(v) for v in getattr(f, "versions", [])],
            "subtasks": [_object_to_dict(s) for s in getattr(f, "subtasks", [])],
            "comments": comments_payload,
        })
    except Exception as exc:
        logger.error("Issue fetch failure for %s: %s", normalized_key, str(exc))
        return _error(f"Unable to fetch issue {normalized_key}", exc)


@profiled_tool("READONLY_CORE")
def get_issue_editmeta(issue_key: str) -> str:
    """
    Return which fields are editable on an issue and their allowed values/schemas.
    Use before updating custom fields to confirm they are settable.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        return _json_dumps(_get(f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/editmeta"))
    except Exception as exc:
        return _error(f"Unable to fetch edit metadata for {_normalize_issue_key(issue_key)}", exc)


@profiled_tool("READONLY_CORE")
def validate_jql(jql_query: str, max_results: int = 1) -> str:
    """Validate a JQL query by executing a tiny bounded search."""
    if not jql_query or not jql_query.strip():
        return "Error: jql_query is required."
    try:
        jira_client.search_issues(jql_query, maxResults=max(1, min(int(max_results), 5)))
        return _json_dumps({"valid": True, "jql_query": jql_query})
    except Exception as exc:
        return _json_dumps({"valid": False, "jql_query": jql_query, "error": _error("JQL validation failed", exc)})


# ---------------------------------------------------------------------------
# Changelog / history / activity
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
    """Return a compact activity view from changelog plus comments."""
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
# Metadata tools (dynamic input or complex logic — not suitable as resources)
# ---------------------------------------------------------------------------

@profiled_tool("METADATA")
def search_users(query: str) -> str:
    """
    Search Jira users by name, username, or email.

    Returns a markdown table of matches. Use to resolve display names to
    Jira usernames before assigning issues.
    """
    if not query or not query.strip():
        return "Error: query is required."

    try:
        users = jira_client.search_users(query)
        if not users:
            return f"No users found matching query: '{query}'."

        lines = [
            "### User Search Results\n",
            "| Display Name | Username / Key | Active |",
            "| :--- | :--- | :--- |",
        ]
        for user in users:
            display_name = getattr(user, "displayName", "N/A")
            username = getattr(user, "name", None) or getattr(user, "key", "N/A")
            active = "Active" if getattr(user, "active", False) else "Inactive"
            lines.append(f"| {display_name} | `{username}` | {active} |")
        return "\n".join(lines)
    except Exception as exc:
        return _error("Unable to search users", exc)


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
def get_custom_field_options(field_id: str, context_id: Optional[str] = None) -> str:
    """
    Return allowed options for a Jira custom field.

    Args:
        field_id: Custom field id such as customfield_10010, or numeric id such as 10010.
        context_id: Optional field context id.
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
                        options_by_context.append({"context": context, "options": options})
                if options_by_context:
                    return _json_dumps({
                        "field_id": raw_field_id,
                        "canonical_field_id": canonical_field_id,
                        "contexts": options_by_context,
                    })
            except Exception as context_exc:
                attempts.append({"path": context_path, "ok": False, "error": str(context_exc)})

        for candidate_path in (
            f"/rest/api/2/customFieldOption/{raw_field_id}",
            f"/rest/api/2/customFieldOption/{numeric_id}",
        ):
            try:
                return _json_dumps({
                    "field_id": raw_field_id,
                    "canonical_field_id": canonical_field_id,
                    "legacy_endpoint": candidate_path,
                    "response": _get(candidate_path),
                    "context_discovery_attempts": attempts,
                })
            except Exception as legacy_exc:
                attempts.append({"path": candidate_path, "ok": False, "error": str(legacy_exc)})

        return _json_dumps({
            "field_id": raw_field_id,
            "canonical_field_id": canonical_field_id,
            "found": False,
            "message": (
                "Unable to discover options through available REST endpoints. "
                "Use the jira://projects/{project_key}/create-meta resource for screen-scoped values, "
                "or provide context_id if your instance exposes field context option APIs."
            ),
            "attempts": attempts,
        })
    except Exception as exc:
        return _error(f"Unable to fetch custom field options for {raw_field_id}", exc)


@profiled_tool("METADATA")
def list_workflows(project_key: Optional[str] = None) -> str:
    """List workflows, optionally scoped to a project's workflow scheme."""
    try:
        if project_key:
            return _json_dumps(_get(f"/rest/api/2/project/{project_key.strip().upper()}/statuses"))
        return _json_dumps(_get("/rest/api/2/workflow"))
    except Exception as exc:
        return _error("Unable to list workflows", exc)


@profiled_tool("METADATA")
def get_version(version_id: str) -> str:
    """Get details of a specific project version by its ID."""
    if not version_id or not str(version_id).strip():
        return "Error: version_id is required."
    try:
        data = _get(f"/rest/api/2/version/{str(version_id).strip()}")
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to get version {version_id}", exc)


@profiled_tool("METADATA")
def get_version_related_issues(version_id: str) -> str:
    """Get counts of issues related to a version (fixed, affected, unresolved)."""
    if not version_id or not str(version_id).strip():
        return "Error: version_id is required."
    vid = str(version_id).strip()
    try:
        related = _get(f"/rest/api/2/version/{vid}/relatedIssueCounts")
        unresolved = _get(f"/rest/api/2/version/{vid}/unresolvedIssueCount")
        return _json_dumps({
            "version_id": vid,
            "related_issue_counts": related,
            "unresolved_issue_count": unresolved,
        })
    except Exception as exc:
        return _error(f"Unable to get related issues for version {version_id}", exc)


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
