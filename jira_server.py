import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

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
    version="1.1.0",
    description=(
        "Enterprise-grade MCP server exposing core read, write, query, "
        "and workflow transition capabilities to Jira Data Center v10 "
        "instances using secure service-account or personal access tokens."
    ),
)

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


def _json_dumps(payload: Dict[str, Any]) -> str:
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


@mcp.tool()
def search_issues(jql_query: str, max_results: int = 50) -> str:
    """
    Query the Jira issue database using native Jira Query Language (JQL).

    Use this tool whenever the user wants to list, filter, find, or report on groups of issues.

    Args:
        jql_query: A well-formed JQL string.
        max_results: Hard upper limit of issues returned. Defaults to 50 and is capped at 100.

    Returns:
        A clean Markdown table for LLM or human consumption.
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


@mcp.tool()
def get_issue_details(issue_key: str) -> str:
    """
    Retrieve comprehensive structured metadata, descriptions, core fields, and comments for an issue.

    Use this tool before updating, commenting on, or resolving an issue.

    Args:
        issue_key: The alphanumeric issue signature, such as PROJ-1024.

    Returns:
        JSON formatted issue detail payload.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"

    normalized_key = issue_key.strip().upper()

    try:
        logger.info("Retrieving deep record tracking context for: %s", normalized_key)
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
            "comments": comments_payload,
        }

        return _json_dumps(issue_data)

    except Exception as exc:
        logger.error("Issue detail fetch failure for %s: %s", normalized_key, str(exc))
        return _error(f"Error: Unable to fetch issue tracking data for key '{normalized_key}'", exc)


@mcp.tool()
def create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Story",
    priority: Optional[str] = None,
) -> str:
    """
    Provision a new Jira tracking node directly into Jira Data Center.

    Args:
        project_key: Upper-case project shorthand key, such as API or FRONT.
        summary: Concise issue headline.
        description: Detailed body text with scope, constraints, and acceptance details.
        issue_type: Jira issue type. Defaults to Story. Common values: Story, Bug, Task, Epic.
        priority: Optional Jira priority name, such as Low, Medium, High, or Critical.

    Returns:
        Status declaration with the created issue key and URL.
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not description or not description.strip():
        return "Error: description is required."

    try:
        logger.info(
            "Formulating creation transaction in project [%s] for type [%s]",
            project_key,
            issue_type,
        )

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
        logger.error("Issue creation failure: %s", str(exc))
        return _error("Failed to execute node provisioning mutation", exc)


@mcp.tool()
def update_issue_fields(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    assignee_username: Optional[str] = None,
) -> str:
    """
    Mutate explicit operational properties of an existing Jira issue.

    Pass only parameters that require inline adjustments.

    Args:
        issue_key: Targeted issue key, such as OPS-431.
        summary: Optional replacement summary.
        description: Optional replacement description.
        assignee_username: Optional exact Jira username identifier for assignment.

    Returns:
        Status declaration describing whether the mutation was applied.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"

    normalized_key = issue_key.strip().upper()

    try:
        logger.info("Updating issue node: %s", normalized_key)
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
        logger.error("Issue field update failure for %s: %s", normalized_key, str(exc))
        return _error("Failure encountered writing issue field mutations", exc)


@mcp.tool()
def transition_issue(issue_key: str, transition_name_or_id: str) -> str:
    """
    Transition an issue from its current state to a target status state.

    If the requested transition is blocked or unavailable from the current workflow state,
    the tool returns the explicit valid options.

    Args:
        issue_key: The unique issue identifier, such as PROJ-123.
        transition_name_or_id: Destination transition name or numeric transition id.

    Returns:
        Status declaration or a list of currently valid transitions.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"
    if not transition_name_or_id or not str(transition_name_or_id).strip():
        return "Error: transition_name_or_id is required."

    normalized_key = issue_key.strip().upper()
    requested = str(transition_name_or_id).strip()

    try:
        logger.info("Triggering workflow transition on %s toward '%s'", normalized_key, requested)
        available_transitions = jira_client.transitions(normalized_key)

        target_id = None
        permissible_options = []

        for transition in available_transitions:
            transition_id = str(transition.get("id"))
            transition_name = str(transition.get("name"))
            permissible_options.append(f"'{transition_name}' (ID: {transition_id})")

            if requested.lower() == transition_name.lower() or requested == transition_id:
                target_id = transition_id
                break

        if not target_id:
            options_block = ", ".join(permissible_options) if permissible_options else "No transitions exposed by Jira."
            return (
                f"Transition Refused: '{requested}' is not a valid or reachable target from the "
                f"current workflow state of issue {normalized_key}.\n"
                f"Valid structural transitions available right now are: {options_block}"
            )

        jira_client.transition_issue(normalized_key, target_id)
        return f"Success: Target issue {normalized_key} transitioned via pipeline route '{requested}'."

    except Exception as exc:
        logger.error("Workflow transition failure for %s: %s", normalized_key, str(exc))
        return _error("Workflow Execution Fault", exc)


@mcp.tool()
def add_comment(issue_key: str, body: str) -> str:
    """
    Post a collaborative text note or progress ledger entry directly onto an issue thread.

    Args:
        issue_key: Target issue identifier, such as PROJ-12.
        body: Comment body to post.

    Returns:
        Status declaration with the new comment id.
    """
    validation_error = _validate_issue_key(issue_key)
    if validation_error:
        return f"Error: {validation_error}"
    if not body or not body.strip():
        return "Error: body is required."

    normalized_key = issue_key.strip().upper()

    try:
        logger.info("Appending comment to target issue thread: %s", normalized_key)
        comment_node = jira_client.add_comment(normalized_key, body)
        return f"Success: Comment posted successfully. Comment ID: {comment_node.id}"

    except Exception as exc:
        logger.error("Comment append failure for %s: %s", normalized_key, str(exc))
        return _error("Aborted: Error appending commentary timeline component", exc)


@mcp.tool()
def search_users(query: str) -> str:
    """
    Search user accounts inside Jira Data Center.

    Use this tool to find exact usernames needed to assign issues properly.

    Args:
        query: Display name, handle fragment, or identity keyword.

    Returns:
        Markdown table of matching users.
    """
    if not query or not query.strip():
        return "Error: query is required."

    try:
        logger.info("Interrogating Jira directory for query: '%s'", query)
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
        logger.error("Directory lookup failure: %s", str(exc))
        return _error("Directory Engine reported a lookup fault", exc)


if __name__ == "__main__":
    logger.info("Initializing Jira MCP server stdio runtime.")
    mcp.run(transport="stdio")
