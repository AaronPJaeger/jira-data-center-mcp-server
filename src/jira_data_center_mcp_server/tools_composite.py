"""Composite tools — multi-step workflows as single MCP calls."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .client import (
    SENSITIVE_DIR_NAMES,
    SENSITIVE_FILE_NAMES,
    _error,
    _find_transition_id,
    _get,
    _json_dumps,
    _normalize_issue_key,
    _object_to_dict,
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
def complete_stage(
    issue_key: str,
    transition_name_or_id: str,
    comment: Optional[str] = None,
    attachment_path: Optional[str] = None,
    attachment_paths_json: Any = None,
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
            if isinstance(attachment_paths_json, list):
                parsed = attachment_paths_json
            else:
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
