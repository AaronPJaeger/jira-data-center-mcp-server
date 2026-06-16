"""Write/mutation tools: issues, workflow, comments, links, properties,
attachments, worklogs, versions, admin, and bulk operations."""

import json
from datetime import date as _date
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import (
    JIRA_URL,
    SENSITIVE_DIR_NAMES,
    SENSITIVE_FILE_NAMES,
    _delete,
    _error,
    _find_transition_id,
    _get,
    _json_dumps,
    _normalize_issue_key,
    _normalize_issue_keys,
    _object_to_dict,
    _parse_json_array,
    _parse_json_object,
    _post,
    _put,
    _request,
    _validate_issue_key,
    _validate_issue_keys,
    jira_client,
)
from .config import profiled_tool


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
    """Create a new Jira issue (generic, type-agnostic).

    Prefer the type-specific tools for better results:
      - create_story: Stories with user story format and Dev Notes
      - create_epic: Epics with Value Statement and PI auto-calculation
      - create_task: Tasks with objective/steps/verification structure
      - create_bug: Bugs with reproduction steps and [BUG] prefix
      - create_initiative: Initiatives with Lean UX problem statement

    Use this generic tool only for issue types not covered above.
    """
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
        # Jira Data Center requires Epic Name (customfield_10003) for Epics
        if (issue_type or "").strip().lower() == "epic":
            issue_dict["customfield_10003"] = summary.strip()

        new_issue = jira_client.create_issue(fields=issue_dict)
        return _json_dumps({
            "key": new_issue.key,
            "url": f"{JIRA_URL}/browse/{new_issue.key}",
        })
    except Exception as exc:
        return _error("Failed to create issue", exc)


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
        return _json_dumps({
            "key": new_issue.key,
            "parent_key": parent.key,
            "url": f"{JIRA_URL}/browse/{new_issue.key}",
        })
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
def update_issue(
    issue_key: str,
    fields_json: Optional[str] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_username: Optional[str] = None,
    priority: Optional[str] = None,
    labels_json: Optional[str] = None,
    components_json: Optional[str] = None,
    fix_versions_json: Optional[str] = None,
) -> str:
    """
    Update fields on an existing Jira issue.

    Accepts named parameters for common fields AND/OR a raw fields_json escape
    hatch for custom fields, arrays, and anything not covered by named params.
    Named parameters are applied first; fields_json values override on conflict.

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
        fields_json: Raw JSON object string for arbitrary field updates.
            Example: '{"customfield_10001":"PROJ-100","customfield_22701":[{"name":"user@va.gov"}]}'
        summary: New summary text.
        description: New description text.
        assignee_username: Jira username to assign (pass empty string "" to unassign).
        priority: Priority name (e.g. "High", "Medium").
        labels_json: JSON array of labels. Example: '["backend","urgent"]'
        components_json: JSON array of components. Example: '[{"name":"API"}]'
        fix_versions_json: JSON array of fix versions. Example: '[{"name":"FY26 Q3"}]'

    Use get_issue_editmeta to discover which fields are editable and their formats.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"

    normalized_key = _normalize_issue_key(issue_key)

    try:
        fields: Dict[str, Any] = {}

        # Named params
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = description
        if assignee_username is not None:
            fields["assignee"] = {"name": assignee_username} if assignee_username else None
        if priority is not None:
            fields["priority"] = {"name": priority}
        if labels_json is not None:
            fields["labels"] = _parse_json_array(labels_json, "labels_json")
        if components_json is not None:
            fields["components"] = _parse_json_array(components_json, "components_json")
        if fix_versions_json is not None:
            fields["fixVersions"] = _parse_json_array(fix_versions_json, "fix_versions_json")

        # Raw JSON escape hatch — overrides named params on key conflict
        if fields_json is not None:
            fields.update(_parse_json_object(fields_json, "fields_json"))

        if not fields:
            return "Error: No fields provided. Supply named parameters and/or fields_json."

        issue = jira_client.issue(normalized_key)
        issue.update(fields=fields)
        return f"Success: Issue {normalized_key} updated."
    except Exception as exc:
        return _error(f"Unable to update issue {normalized_key}", exc)


@profiled_tool("ISSUE_WRITE")
def assign_issue(issue_key: str, assignee_username: str) -> str:
    """Assign a Jira issue to a user.

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
        assignee_username: Jira username to assign the issue to.
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    if not assignee_username or not assignee_username.strip():
        return "Error: assignee_username is required. Use unassign_issue to remove the assignee."
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields={"assignee": {"name": assignee_username.strip()}})
        return f"Success: {_normalize_issue_key(issue_key)} assigned to {assignee_username.strip()}."
    except Exception as exc:
        return _error(f"Unable to assign issue {issue_key}", exc)


@profiled_tool("ISSUE_WRITE")
def unassign_issue(issue_key: str) -> str:
    """Remove the assignee from a Jira issue (set to Unassigned).

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
    """
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        issue = jira_client.issue(_normalize_issue_key(issue_key))
        issue.update(fields={"assignee": None})
        return f"Success: {_normalize_issue_key(issue_key)} unassigned."
    except Exception as exc:
        return _error(f"Unable to unassign issue {issue_key}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_issue(issue_key: str, confirm: bool = False, delete_subtasks: bool = False) -> str:
    """Delete an issue. Destructive operation requiring confirm=True."""
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
# Workflow transitions
# ---------------------------------------------------------------------------

@profiled_tool("WORKFLOW_WRITE")
def transition_issue(
    issue_key: str,
    transition_name_or_id: str,
    fields_json: Optional[str] = None,
    comment: Optional[str] = None,
    resolution: Optional[str] = None,
) -> str:
    """
    Transition an issue to a new workflow state, optionally setting fields and adding a comment.

    Args:
        issue_key: Jira issue key (e.g. PROJ-123).
        transition_name_or_id: Destination transition name (e.g. "Done") or numeric ID.
        fields_json: Optional JSON object of fields required by the transition.
            Example: '{"customfield_10500":"Verified in STG"}'
        comment: Optional comment to add during the transition.
        resolution: Optional resolution name (e.g. "Done", "Fixed", "Won't Do").

    Use get_available_transitions to discover valid transitions for the current state.
    """
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
                f"Transition Refused: '{transition_name_or_id}' is not valid from the current state "
                f"of {normalized_key}.\nAvailable transitions: {options_block}"
            )

        # If no optional params, use simple transition
        if not fields_json and not comment and not resolution:
            jira_client.transition_issue(normalized_key, target_id)
            return f"Success: {normalized_key} transitioned via '{transition_name_or_id}'."

        # Build rich transition payload
        fields = _parse_json_object(fields_json, "fields_json") if fields_json else {}
        if resolution:
            fields["resolution"] = {"name": resolution}

        payload: Dict[str, Any] = {"transition": {"id": target_id}}
        if fields:
            payload["fields"] = fields
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}

        _post(f"/rest/api/2/issue/{normalized_key}/transitions", payload=payload)
        return f"Success: {normalized_key} transitioned via '{transition_name_or_id}' with fields/comment."
    except Exception as exc:
        return _error("Workflow transition failed", exc)


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
    try:
        comment_node = jira_client.add_comment(_normalize_issue_key(issue_key), body)
        return f"Success: Comment posted successfully. Comment ID: {comment_node.id}"
    except Exception as exc:
        return _error("Error adding comment", exc)


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
# Watchers
# ---------------------------------------------------------------------------

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


@profiled_tool("ISSUE_WRITE")
def watch_issue(issue_key: str, username: Optional[str] = None) -> str:
    """Watch an issue as current user or add username as watcher when supplied."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    try:
        if username:
            _request("POST", f"/rest/api/2/issue/{_normalize_issue_key(issue_key)}/watchers", json=username)
        else:
            jira_client.add_watcher(_normalize_issue_key(issue_key), jira_client.current_user())
        return f"Success: watcher added for {_normalize_issue_key(issue_key)}."
    except Exception as exc:
        return _error(f"Unable to watch issue {issue_key}", exc)


@profiled_tool("ISSUE_WRITE")
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


@profiled_tool("LINK_WRITE")
def create_issue_link(inward_issue_key: str, outward_issue_key: str, link_type: str, comment: Optional[str] = None) -> str:
    """Create an issue link between two issues.

    Use the jira://link-types resource to discover available link types.
    """
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


@profiled_tool("ATTACHMENT_WRITE")
def add_attachment(issue_key: str, file_path: str) -> str:
    """Attach a local file path to an issue."""
    err = _validate_issue_key(issue_key)
    if err:
        return f"Error: {err}"
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        return f"Error: file_path does not exist or is not a file: {file_path}"
    if path.name.lower() in SENSITIVE_FILE_NAMES or path.name.lower().startswith(".env."):
        return f"Error: Refusing to attach potentially sensitive file: {path.name}"
    if any(part.lower() in SENSITIVE_DIR_NAMES for part in path.parts):
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
# Versions and releases
# ---------------------------------------------------------------------------

@profiled_tool("VERSION_WRITE")
def create_version(
    project_key: str,
    name: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    release_date: Optional[str] = None,
    archived: bool = False,
    released: bool = False,
) -> str:
    """Create a new version/release in a Jira project.

    Args:
        project_key: The project key (e.g. "PROJ").
        name: Version name (e.g. "1.2.0").
        description: Optional description of the version.
        start_date: Optional start date in YYYY-MM-DD format.
        release_date: Optional release date in YYYY-MM-DD format.
        archived: Whether the version is archived. Default False.
        released: Whether the version is already released. Default False.
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not name or not name.strip():
        return "Error: name is required."
    try:
        payload: Dict[str, Any] = {
            "project": project_key.strip().upper(),
            "name": name.strip(),
            "archived": archived,
            "released": released,
        }
        if description is not None:
            payload["description"] = description
        if start_date is not None:
            payload["startDate"] = start_date.strip()
        if release_date is not None:
            payload["releaseDate"] = release_date.strip()
        data = _post("/rest/api/2/version", payload=payload)
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to create version '{name}' in {project_key}", exc)


@profiled_tool("VERSION_WRITE")
def get_or_create_version(
    project_key: str,
    name: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    release_date: Optional[str] = None,
) -> str:
    """Return an existing version by name, or create it if it does not exist.

    Idempotent — safe to call on workflow resume without risking duplicate versions.

    Args:
        project_key: Project key (e.g. "VALIP").
        name: Version name to find or create (e.g. "VALIP Platform 2.18.0.0").
        description: Description to set if the version is created. Ignored if it already exists.
        start_date: Start date (YYYY-MM-DD) to set if created. Ignored if it already exists.
        release_date: Release date (YYYY-MM-DD) to set if created. Ignored if it already exists.

    Returns:
        JSON with the version data and a "created" boolean indicating whether a new
        version was created (true) or an existing one was found (false).
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not name or not name.strip():
        return "Error: name is required."

    pk = project_key.strip().upper()
    target_name = name.strip()

    try:
        # Search existing versions by name
        versions = _get(f"/rest/api/2/project/{pk}/versions")
        for v in versions:
            if v.get("name", "").strip() == target_name:
                v["created"] = False
                return _json_dumps(v)

        # Not found — create it
        payload: Dict[str, Any] = {
            "project": pk,
            "name": target_name,
            "archived": False,
            "released": False,
        }
        if description is not None:
            payload["description"] = description
        if start_date is not None:
            payload["startDate"] = start_date.strip()
        if release_date is not None:
            payload["releaseDate"] = release_date.strip()

        data = _post("/rest/api/2/version", payload=payload)
        data["created"] = True
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to get or create version '{target_name}' in {pk}", exc)


@profiled_tool("VERSION_WRITE")
def update_version(
    version_id: str,
    action: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    release_date: Optional[str] = None,
) -> str:
    """Update a version's attributes or change its lifecycle state.

    Use the jira://projects/{project_key}/versions resource to discover version IDs.

    Args:
        version_id: The version ID to update.
        action: Optional lifecycle action — one of 'release', 'unrelease', 'archive',
                'unarchive'. If omitted, only the provided fields are updated.
        name: New version name.
        description: New description.
        start_date: New start date in YYYY-MM-DD format.
        release_date: New release date in YYYY-MM-DD format.

    Examples:
        update_version(version_id="10100", action="release")
        update_version(version_id="10100", action="release", release_date="2026-06-15")
        update_version(version_id="10100", name="2.0.1", description="Hotfix")
    """
    if not version_id or not str(version_id).strip():
        return "Error: version_id is required."

    vid = str(version_id).strip()
    payload: Dict[str, Any] = {}

    if action:
        act = action.strip().lower()
        if act == "release":
            payload["released"] = True
            if release_date:
                payload["releaseDate"] = release_date.strip()
            else:
                payload["releaseDate"] = _date.today().isoformat()
        elif act == "unrelease":
            payload["released"] = False
        elif act == "archive":
            payload["archived"] = True
        elif act == "unarchive":
            payload["archived"] = False
        else:
            return f"Error: Unknown action '{action}'. Use release, unrelease, archive, or unarchive."

    if name is not None:
        payload["name"] = name.strip()
    if description is not None:
        payload["description"] = description
    if start_date is not None:
        payload["startDate"] = start_date.strip()
    if release_date is not None and "releaseDate" not in payload:
        payload["releaseDate"] = release_date.strip()

    if not payload:
        return "Error: Provide an action and/or fields to update."

    try:
        data = _put(f"/rest/api/2/version/{vid}", payload=payload)
        return _json_dumps(data)
    except Exception as exc:
        return _error(f"Unable to update version {version_id}", exc)


@profiled_tool("DESTRUCTIVE")
def delete_version(
    version_id: str,
    move_fix_issues_to: Optional[str] = None,
    move_affected_issues_to: Optional[str] = None,
    confirm: bool = False,
) -> str:
    """Delete a project version. Requires confirm=True.

    Args:
        version_id: The version ID to delete.
        move_fix_issues_to: Version ID to reassign fixVersion issues to.
        move_affected_issues_to: Version ID to reassign affected-version issues to.
        confirm: Must be True to proceed. Safety gate.
    """
    if not confirm:
        return "Refused: delete_version requires confirm=True."
    if not version_id or not str(version_id).strip():
        return "Error: version_id is required."
    try:
        params: Dict[str, str] = {}
        if move_fix_issues_to is not None:
            params["moveFixIssuesTo"] = str(move_fix_issues_to).strip()
        if move_affected_issues_to is not None:
            params["moveAffectedIssuesTo"] = str(move_affected_issues_to).strip()
        data = _delete(f"/rest/api/2/version/{str(version_id).strip()}", params=params or None)
        return _json_dumps({"deleted": True, "version_id": version_id, "detail": data})
    except Exception as exc:
        return _error(f"Unable to delete version {version_id}", exc)


# ---------------------------------------------------------------------------
# Filters, roles, groups, security
# ---------------------------------------------------------------------------

@profiled_tool("ADMIN_READ")
def use_filter(filter_id: Optional[str] = None, favourite: bool = True, max_results: int = 50) -> str:
    """List saved filters, or get details and run a specific filter.

    Args:
        filter_id: If provided, returns the filter definition and executes its JQL.
                   If omitted, lists favourite (or all) filters.
        favourite: When listing (no filter_id), return only favourites (default True).
        max_results: Max issues to return when running a filter.

    Examples:
        use_filter()                        # list favourite filters
        use_filter(filter_id="12345")       # get filter + run its JQL
    """
    # Import here to avoid circular dependency (search_issues is in tools_read)
    from .tools_read import search_issues as _search_issues

    try:
        if filter_id:
            filter_data = _get(f"/rest/api/2/filter/{filter_id}")
            jql = filter_data.get("jql")
            if not jql:
                return _json_dumps({"filter": filter_data, "error": "Filter has no JQL."})
            issues_result = _search_issues(jql, max_results=max_results)
            return _json_dumps({"filter": filter_data, "results": issues_result})
        path = "/rest/api/2/filter/favourite" if favourite else "/rest/api/2/filter"
        return _json_dumps(_get(path))
    except Exception as exc:
        return _error("Unable to use filter", exc)


@profiled_tool("ADMIN_READ")
def get_project_roles(project_key: str, role_id: Optional[str] = None) -> str:
    """List project roles, or get actors for a specific role.

    Args:
        project_key: The project key.
        role_id: If provided, returns actors for that role. If omitted, lists all roles.
    """
    if not project_key:
        return "Error: project_key is required."
    try:
        pk = project_key.strip().upper()
        if role_id:
            return _json_dumps(_get(f"/rest/api/2/project/{pk}/role/{role_id}"))
        return _json_dumps(_get(f"/rest/api/2/project/{pk}/role"))
    except Exception as exc:
        return _error(f"Unable to fetch roles for {project_key}", exc)


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
    """List issue security levels available to the authenticated account."""
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
