"""Jira Software Agile tools: boards, sprints, ranking."""

from typing import Any, Dict, List, Optional

from .client import (
    _error,
    _get,
    _json_dumps,
    _normalize_issue_key,
    _normalize_issue_keys,
    _post,
    _put,
    _validate_issue_key,
    _validate_issue_keys,
)
from .config import profiled_tool


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
