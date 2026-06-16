"""Composite tools — multi-step workflows as single MCP calls."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import (
    JIRA_URL,
    SENSITIVE_DIR_NAMES,
    SENSITIVE_FILE_NAMES,
    _error,
    _find_transition_id,
    _get,
    _json_dumps,
    _normalize_issue_key,
    _object_to_dict,
    _parse_json_object,
    _post,
    _validate_issue_key,
    jira_client,
)
from .config import get_profile_status_payload, profiled_tool


@profiled_tool("COMPOSITE")
def preflight() -> str:
    """
    Session initialization check. Returns server info, authenticated user,
    active MCP profile, and available issue link types in a single call.

    Call this at the start of every MCP session to validate connectivity
    and discover configuration before performing any write operations.
    """
    result: Dict[str, Any] = {}

    try:
        if hasattr(jira_client, "server_info"):
            result["server_info"] = jira_client.server_info()
        else:
            result["server_info"] = _get("/rest/api/2/serverInfo")
    except Exception as exc:
        result["server_info"] = {"error": str(exc)}

    try:
        if hasattr(jira_client, "myself"):
            result["current_user"] = jira_client.myself()
        else:
            result["current_user"] = _get("/rest/api/2/myself")
    except Exception as exc:
        result["current_user"] = {"error": str(exc)}

    result["profile"] = get_profile_status_payload()

    try:
        if hasattr(jira_client, "issue_link_types"):
            result["link_types"] = [_object_to_dict(t) for t in jira_client.issue_link_types()]
        else:
            result["link_types"] = _get("/rest/api/2/issueLinkType")
    except Exception as exc:
        result["link_types"] = {"error": str(exc)}

    return _json_dumps(result)


@profiled_tool("COMPOSITE")
def create_and_enrich_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Story",
    priority: Optional[str] = None,
    fields_json: Optional[str] = None,
    assignee_username: Optional[str] = None,
    link_to_issue: Optional[str] = None,
    link_type: Optional[str] = None,
) -> str:
    """
    Create an issue, enrich it with custom fields, assign it, and link it — all in one call.

    DEPRECATED: Prefer the type-specific creation tools for better results:
      - create_story: Stories with user story format and Dev Notes
      - create_epic: Epics with Value Statement and PI auto-calculation
      - create_task: Tasks with objective/steps/verification structure
      - create_bug: Bugs with reproduction steps and [BUG] prefix
      - create_initiative: Initiatives with Lean UX problem statement

    This generic tool remains available for release chain workflows and issue
    types not covered by the type-specific tools.

    Args:
        project_key: Project key (e.g. "VALIP").
        summary: Issue summary.
        description: Issue description.
        issue_type: Issue type name (default "Story").
        priority: Priority name (e.g. "Medium", "High").
        fields_json: JSON object string of additional fields to set after creation.
            Example: '{"customfield_10001":"VALIP-100","components":[{"name":"FY26 Q3"}]}'
        assignee_username: Jira username to assign the issue to.
        link_to_issue: Issue key to link to (e.g. "VALIP-5000").
        link_type: Link type name (e.g. "Blocks"). Required if link_to_issue is provided.
            The new issue becomes the outward issue (e.g. "new issue blocks link_to_issue").
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not description or not description.strip():
        return "Error: description is required."
    if link_to_issue and not link_type:
        return "Error: link_type is required when link_to_issue is provided."

    result: Dict[str, Any] = {"steps": []}

    # Step 1: Create
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
        issue_key = new_issue.key
        result["key"] = issue_key
        result["url"] = f"{JIRA_URL}/browse/{issue_key}"
        result["steps"].append({"action": "create", "ok": True})
    except Exception as exc:
        return _error("Failed to create issue", exc)

    # Step 2: Enrich with custom fields
    if fields_json:
        try:
            fields = _parse_json_object(fields_json, "fields_json")
            if fields:
                issue = jira_client.issue(issue_key)
                issue.update(fields=fields)
                result["steps"].append({"action": "enrich", "ok": True, "fields_set": list(fields.keys())})
        except Exception as exc:
            result["steps"].append({"action": "enrich", "ok": False, "error": str(exc)})

    # Step 3: Assign
    if assignee_username:
        try:
            issue = jira_client.issue(issue_key)
            issue.update(fields={"assignee": {"name": assignee_username}})
            result["steps"].append({"action": "assign", "ok": True, "assignee": assignee_username})
        except Exception as exc:
            result["steps"].append({"action": "assign", "ok": False, "error": str(exc)})

    # Step 4: Link
    if link_to_issue:
        link_err = _validate_issue_key(link_to_issue)
        if link_err:
            result["steps"].append({"action": "link", "ok": False, "error": link_err})
        else:
            try:
                jira_client.create_issue_link(
                    type=link_type,
                    inwardIssue=_normalize_issue_key(link_to_issue),
                    outwardIssue=issue_key,
                )
                result["steps"].append({
                    "action": "link", "ok": True,
                    "link": f"{issue_key} {link_type} {_normalize_issue_key(link_to_issue)}",
                })
            except Exception as exc:
                result["steps"].append({"action": "link", "ok": False, "error": str(exc)})

    return _json_dumps(result)


@profiled_tool("COMPOSITE")
def complete_stage(
    issue_key: str,
    transition_name_or_id: str,
    comment: Optional[str] = None,
    attachment_path: Optional[str] = None,
    attachment_paths_json: Optional[str] = None,
    resolution: Optional[str] = None,
) -> str:
    """
    Complete a workflow stage: transition an issue, optionally attach evidence, and add a comment.

    Replaces the common 3-4 call sequence: get_available_transitions → transition_issue →
    add_attachment → add_comment. Ideal for release stage gate transitions.

    Args:
        issue_key: Jira issue key.
        transition_name_or_id: Target transition name or ID (e.g. "Done", "In Review").
        comment: Optional comment to add after transitioning.
        attachment_path: Optional single local file path to attach. For multiple files,
            use attachment_paths_json instead.
        attachment_paths_json: Optional JSON array of local file paths to attach.
            Example: '["C:/evidence/pre-impl-1.png","C:/evidence/pre-impl-2.png"]'
            When provided, attachment_path is ignored.
        resolution: Optional resolution name (e.g. "Done", "Fixed").
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not transition_name_or_id or not str(transition_name_or_id).strip():
        return "Error: transition_name_or_id is required."

    normalized_key = _normalize_issue_key(issue_key)
    result: Dict[str, Any] = {"issue_key": normalized_key, "steps": []}

    # Step 1: Transition
    try:
        transition_lookup = _find_transition_id(normalized_key, transition_name_or_id)
        target_id = transition_lookup["target_id"]
        if not target_id:
            options_block = ", ".join(f"'{o['name']}' (ID: {o['id']})" for o in transition_lookup["options"])
            return _json_dumps({
                "error": f"Transition '{transition_name_or_id}' not available.",
                "available_transitions": options_block,
            })

        fields: Dict[str, Any] = {}
        if resolution:
            fields["resolution"] = {"name": resolution}

        if fields:
            payload: Dict[str, Any] = {"transition": {"id": target_id}, "fields": fields}
            _post(f"/rest/api/2/issue/{normalized_key}/transitions", payload=payload)
        else:
            jira_client.transition_issue(normalized_key, target_id)

        result["steps"].append({"action": "transition", "ok": True, "transition": transition_name_or_id})
        result["new_status"] = transition_name_or_id
    except Exception as exc:
        result["steps"].append({"action": "transition", "ok": False, "error": str(exc)})
        return _json_dumps(result)

    # Step 2: Attach files (if provided)
    # Build list of paths to attach — prefer attachment_paths_json over attachment_path
    paths_to_attach: List[str] = []
    if attachment_paths_json:
        try:
            parsed = json.loads(attachment_paths_json)
            if isinstance(parsed, list):
                paths_to_attach = [str(p) for p in parsed if p]
            else:
                result["steps"].append({"action": "attach", "ok": False, "error": "attachment_paths_json must be a JSON array"})
        except (json.JSONDecodeError, TypeError) as parse_err:
            result["steps"].append({"action": "attach", "ok": False, "error": f"Invalid attachment_paths_json: {parse_err}"})
    elif attachment_path:
        paths_to_attach = [attachment_path]

    for file_path in paths_to_attach:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            result["steps"].append({"action": "attach", "ok": False, "error": f"File not found: {file_path}"})
        elif path.name.lower() in SENSITIVE_FILE_NAMES or path.name.lower().startswith(".env."):
            result["steps"].append({"action": "attach", "ok": False, "error": f"Sensitive file refused: {path.name}"})
        elif any(part.lower() in SENSITIVE_DIR_NAMES for part in path.parts):
            result["steps"].append({"action": "attach", "ok": False, "error": f"Sensitive directory refused: {file_path}"})
        else:
            try:
                attachment = jira_client.add_attachment(issue=normalized_key, attachment=str(path))
                result["steps"].append({"action": "attach", "ok": True, "file": path.name, "attachment": _object_to_dict(attachment)})
            except Exception as exc:
                result["steps"].append({"action": "attach", "ok": False, "file": path.name, "error": str(exc)})

    # Step 3: Add comment (if provided)
    if comment:
        try:
            comment_node = jira_client.add_comment(normalized_key, comment)
            result["steps"].append({"action": "comment", "ok": True, "comment_id": comment_node.id})
        except Exception as exc:
            result["steps"].append({"action": "comment", "ok": False, "error": str(exc)})

    return _json_dumps(result)


@profiled_tool("COMPOSITE")
def close_issue(
    issue_key: str,
    resolution: Optional[str] = None,
    comment: Optional[str] = None,
) -> str:
    """
    Close an issue by discovering and executing a done/closed transition, optionally
    setting a resolution and adding a comment.

    Automatically finds a transition whose name contains 'done', 'close', 'resolve',
    or 'complete'. If no matching transition is found, returns available options.

    Args:
        issue_key: Jira issue key.
        resolution: Resolution name (e.g. "Done", "Fixed", "Won't Do"). Optional.
        comment: Optional comment to add during the transition.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"

    normalized_key = _normalize_issue_key(issue_key)

    try:
        transitions = jira_client.transitions(normalized_key)
        close_keywords = ("done", "close", "resolve", "complete")
        target = None
        for t in transitions:
            name = str(t.get("name", "")).lower()
            if any(kw in name for kw in close_keywords):
                target = t
                break

        if not target:
            options_block = ", ".join(f"'{t['name']}' (ID: {t['id']})" for t in transitions)
            return _json_dumps({
                "error": "No done/close/resolve transition found.",
                "available_transitions": options_block,
                "hint": "Use transition_issue with the correct transition name.",
            })

        target_id = target["id"]
        fields: Dict[str, Any] = {}
        if resolution:
            fields["resolution"] = {"name": resolution}

        payload: Dict[str, Any] = {"transition": {"id": target_id}}
        if fields:
            payload["fields"] = fields
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}

        _post(f"/rest/api/2/issue/{normalized_key}/transitions", payload=payload)
        return _json_dumps({
            "issue_key": normalized_key,
            "transition": target.get("name"),
            "resolution": resolution,
            "comment_added": bool(comment),
        })
    except Exception as exc:
        return _error(f"Unable to close issue {issue_key}", exc)
