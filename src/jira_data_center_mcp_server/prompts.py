"""MCP Prompts — guided multi-step workflows."""

from .app import mcp


@mcp.prompt("create-and-assign", description="Guided workflow to create a Jira issue with assignment and enrichment")
def _prompt_create_and_assign(project_key: str = "VALIP") -> str:
    return (
        f"Create a new Jira issue in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: summary, description, issue type, priority, assignee, and any custom fields.\n"
        "2. Use the jira://projects/{project_key}/create-meta resource to check required fields.\n"
        "3. Present a summary table and get confirmation.\n"
        "4. Call create_and_enrich_issue with all collected data.\n"
        "5. Report the created issue key and URL."
    )


@mcp.prompt("close-issue", description="Guided workflow to close/resolve a Jira issue")
def _prompt_close_issue(issue_key: str = "") -> str:
    return (
        f"Close Jira issue {issue_key or '[ask user for issue key]'}. Follow these steps:\n\n"
        "1. Call get_issue to review current state.\n"
        "2. Read the jira://resolutions resource for available resolution values.\n"
        "3. Ask user for resolution and optional closing comment.\n"
        "4. Call close_issue with the collected data.\n"
        "5. Confirm the transition succeeded."
    )


@mcp.prompt("triage-issue", description="Guided workflow to triage an issue (priority, assign, label, sprint)")
def _prompt_triage_issue(issue_key: str = "") -> str:
    return (
        f"Triage Jira issue {issue_key or '[ask user for issue key]'}. Follow these steps:\n\n"
        "1. Call get_issue to understand the current state.\n"
        "2. Ask the user for: priority, assignee, labels, and target sprint (if applicable).\n"
        "3. Use update_issue to set priority, assignee, and labels.\n"
        "4. If a sprint was specified, call move_issues_to_sprint.\n"
        "5. Confirm all changes."
    )


@mcp.prompt("release-version", description="Guided workflow to release a project version")
def _prompt_release_version(project_key: str = "VALIP") -> str:
    return (
        f"Release a version in project {project_key}. Follow these steps:\n\n"
        f"1. Read the jira://projects/{project_key}/versions resource to list versions.\n"
        "2. Ask user which version to release and the release date.\n"
        "3. Call update_version with action='release'.\n"
        "4. Confirm the release."
    )
