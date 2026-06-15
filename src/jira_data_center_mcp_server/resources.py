"""MCP Resources — static/semi-static metadata exposed as jira:// URIs."""

from typing import Any, Dict, Optional

from .app import mcp
from .client import (
    JIRA_URL,
    _get,
    _json_dumps,
    _object_to_dict,
    jira_client,
)
from .config import get_profile_status_payload


# ---------------------------------------------------------------------------
# Static resources
# ---------------------------------------------------------------------------

@mcp.resource("jira://profile", name="MCP Profile Status", description="Active Jira MCP profile and enabled tool groups")
def _resource_profile() -> str:
    return _json_dumps(get_profile_status_payload())


@mcp.resource("jira://server-info", name="Jira Server Info", description="Jira Data Center server version and configuration")
def _resource_server_info() -> str:
    try:
        if hasattr(jira_client, "server_info"):
            return _json_dumps(jira_client.server_info())
        return _json_dumps(_get("/rest/api/2/serverInfo"))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://me", name="Current User", description="Authenticated Jira user identity")
def _resource_me() -> str:
    try:
        if hasattr(jira_client, "myself"):
            return _json_dumps(jira_client.myself())
        return _json_dumps(_get("/rest/api/2/myself"))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://projects", name="Projects", description="Jira projects visible to the authenticated account")
def _resource_projects() -> str:
    try:
        projects = jira_client.projects()
        return _json_dumps([
            {
                "key": getattr(p, "key", None),
                "id": getattr(p, "id", None),
                "name": getattr(p, "name", None),
                "project_type_key": getattr(p, "projectTypeKey", None),
            }
            for p in projects
        ])
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://priorities", name="Priorities", description="Jira priority values")
def _resource_priorities() -> str:
    try:
        return _json_dumps([_object_to_dict(p) for p in jira_client.priorities()])
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://fields", name="Fields", description="Jira fields including custom fields")
def _resource_fields() -> str:
    try:
        return _json_dumps(jira_client.fields())
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://statuses", name="Statuses", description="Jira workflow statuses")
def _resource_statuses() -> str:
    try:
        return _json_dumps(_get("/rest/api/2/status"))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://resolutions", name="Resolutions", description="Jira issue resolutions")
def _resource_resolutions() -> str:
    try:
        return _json_dumps(_get("/rest/api/2/resolution"))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://link-types", name="Issue Link Types", description="Available Jira issue link types (Blocks, Relates, etc.)")
def _resource_link_types() -> str:
    try:
        if hasattr(jira_client, "issue_link_types"):
            return _json_dumps([_object_to_dict(t) for t in jira_client.issue_link_types()])
        return _json_dumps(_get("/rest/api/2/issueLinkType"))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Resource templates — parameterized metadata
# ---------------------------------------------------------------------------

@mcp.resource("jira://projects/{project_key}", name="Project Metadata", description="Metadata for a specific Jira project")
def _resource_project(project_key: str) -> str:
    try:
        project = jira_client.project(project_key.strip().upper())
        return _json_dumps(_object_to_dict(project))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://projects/{project_key}/issue-types", name="Issue Types", description="Issue types available in a project")
def _resource_issue_types(project_key: str) -> str:
    try:
        raw = _get_create_issue_metadata(project_key=project_key)
        issue_types = []
        for project in raw.get("projects", []):
            issue_types.extend(project.get("issuetypes", []))
        return _json_dumps(issue_types)
    except Exception:
        try:
            return _json_dumps([_object_to_dict(t) for t in jira_client.issue_types()])
        except Exception as exc:
            return _json_dumps({"error": str(exc)})


@mcp.resource("jira://projects/{project_key}/components", name="Components", description="Components for a Jira project")
def _resource_components(project_key: str) -> str:
    try:
        components = jira_client.project_components(project_key.strip().upper())
        return _json_dumps([_object_to_dict(c) for c in components])
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://projects/{project_key}/versions", name="Versions", description="Versions/releases for a Jira project")
def _resource_versions(project_key: str) -> str:
    try:
        versions = jira_client.project_versions(project_key.strip().upper())
        return _json_dumps([_object_to_dict(v) for v in versions])
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


@mcp.resource("jira://projects/{project_key}/create-meta", name="Create Metadata", description="Required/allowed fields for creating issues in a project")
def _resource_create_meta(project_key: str) -> str:
    try:
        return _json_dumps(_get_create_issue_metadata(project_key=project_key))
    except Exception as exc:
        return _json_dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Internal helper (also used by tools_read)
# ---------------------------------------------------------------------------

def _get_create_issue_metadata(project_key: Optional[str] = None, issue_type: Optional[str] = None) -> Dict[str, Any]:
    """Internal helper for create issue metadata."""
    kwargs: Dict[str, Any] = {}
    if project_key:
        kwargs["projectKeys"] = project_key.strip().upper()
    if issue_type:
        kwargs["issuetypeNames"] = issue_type
    if hasattr(jira_client, "createmeta"):
        return jira_client.createmeta(expand="projects.issuetypes.fields", **kwargs)
    params = {"expand": "projects.issuetypes.fields"}
    params.update(kwargs)
    return _get("/rest/api/2/issue/createmeta", params=params)
