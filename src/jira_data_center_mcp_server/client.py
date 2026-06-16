"""Jira connection, REST wrappers, and shared validation/normalization utilities."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Sequence

from dotenv import load_dotenv
from jira import JIRA
from jira.exceptions import JIRAError

load_dotenv()

logger = logging.getLogger("jira_mcp_server")

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


# ---------------------------------------------------------------------------
# JSON / serialization
# ---------------------------------------------------------------------------

def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Issue key validation and normalization
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Object / field helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Error formatting
# ---------------------------------------------------------------------------

def _error(prefix: str, err: Exception) -> str:
    if isinstance(err, JIRAError):
        detail = getattr(err, "text", str(err))
        status_code = getattr(err, "status_code", None)
        return f"{prefix}: {detail}" + (f" (Status Code: {status_code})" if status_code else "")
    return f"{prefix}: {str(err)}"


# ---------------------------------------------------------------------------
# Direct REST wrappers (for endpoints python-jira doesn't expose)
# ---------------------------------------------------------------------------

def _resource_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def _request(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{JIRA_URL}{_resource_path(path)}"
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


# ---------------------------------------------------------------------------
# Workflow transition helper
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _parse_json_object(value: Optional[Union[str, dict]], field_name: str) -> Dict[str, Any]:
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


def _parse_json_array(value: Optional[Union[str, list]], field_name: str) -> List[Any]:
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
# Security constants (used by attachment tools and composite tools)
# ---------------------------------------------------------------------------

SENSITIVE_FILE_NAMES = {".env", ".env.local", ".env.production", ".env.development", ".env.staging"}
SENSITIVE_DIR_NAMES = {".ssh", ".gnupg", ".aws", ".azure"}
