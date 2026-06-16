"""MCP Prompts — guided multi-step workflows."""

from .app import mcp


@mcp.prompt("create-and-assign", description="Guided workflow to create a Jira issue with assignment and enrichment")
def _prompt_create_and_assign(project_key: str = "VALIP") -> str:
    return (
        f"Create a new Jira issue in project {project_key}. Follow these steps:\n\n"
        "1. Ask the user which issue type: Story, Epic, Task, Bug, or Initiative.\n"
        "2. Use the type-specific prompt (create-story, create-epic, create-task, create-bug, or create-initiative) for guided field collection.\n"
        "3. If the type doesn't match any of the above, fall back to the generic create_issue tool.\n"
    )


@mcp.prompt("create-story", description="Guided workflow to create a VALIP Story with user story format and Dev Notes")
def _prompt_create_story(project_key: str = "VALIP") -> str:
    return (
        f"Create a VALIP Story in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: platform (VALIP/4S2/VDM/SSDEV/Maximo Cloud), work type (DEV/SEC/OPS), "
        "summary text, role ('As a'), goal ('I want'), benefit ('So that').\n"
        "2. Ask for: epic key (or resolve from platform x work_type), priority, assignee, "
        "collaborators, SNOW ticket, estimate, target dates.\n"
        "3. Ask for implementation context: background, steps, affected systems, "
        "evidence to collect — this becomes Dev Notes, NOT description.\n"
        "4. Generate 2-5 Given/When/Then acceptance criteria.\n"
        "5. Present a summary table and confirm with the user.\n"
        "6. Call create_story with all collected fields.\n"
        "7. Report the issue key and URL.\n\n"
        "IMPORTANT: Story descriptions contain ONLY the user story statement. "
        "All implementation details go into the dev_notes parameter."
    )


@mcp.prompt("create-epic", description="Guided workflow to create a VALIP Epic with Value Statement format")
def _prompt_create_epic(project_key: str = "VALIP") -> str:
    return (
        f"Create a VALIP Epic in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: platform, work type, whether Planned or Unplanned, and epic title.\n"
        "2. Collect Value Statement fields:\n"
        "   - For (beneficiaries), Who (need), The (solution name),\n"
        "   - That (outcome), Unlike (current state), Our Process/Solution.\n"
        "3. Ask for In Scope items (at least 2 bullets).\n"
        "4. Ask for Out of Scope items (at least 2 bullets).\n"
        "5. Ask for Non-Functional requirements (optional).\n"
        "6. Ask for PI Objective component (optional), priority, assignee, labels.\n"
        "7. Generate high-level Given/When/Then acceptance criteria for the epic scope.\n"
        "8. Present a summary table and confirm.\n"
        "9. Call create_epic with all collected fields.\n"
        "10. Report the issue key and URL.\n\n"
        "Summary pattern: FY<YY> Q<N> <PLATFORM>: <WORK_TYPE> <Planned/Unplanned> - <Title>\n"
        "IMPORTANT: Epics do NOT get an Epic Link. They ARE the epic."
    )


@mcp.prompt("create-task", description="Guided workflow to create a VALIP Task with structured steps")
def _prompt_create_task(project_key: str = "VALIP") -> str:
    return (
        f"Create a VALIP Task in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: platform, summary, and epic key.\n"
        "2. Ask for the objective (what needs to be done and why).\n"
        "3. Ask for numbered implementation steps.\n"
        "4. Ask for verification method (how to confirm it's done).\n"
        "5. Optionally ask for: background, affected systems, dependencies.\n"
        "6. Generate checklist-style acceptance criteria.\n"
        "7. Ask for: priority, assignee, SNOW ticket, estimate, target dates.\n"
        "8. Present a summary table and confirm.\n"
        "9. Call create_task with all collected fields.\n"
        "10. Report the issue key and URL.\n\n"
        "IMPORTANT: Tasks use checklist-style AC, NOT Given/When/Then."
    )


@mcp.prompt("create-bug", description="Guided workflow to create a VALIP Bug with reproduction steps")
def _prompt_create_bug(project_key: str = "VALIP") -> str:
    return (
        f"Create a VALIP Bug in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: platform, short problem description, and epic key.\n"
        "2. Ask for the problem statement (what's broken and its impact).\n"
        "3. Ask for SPECIFIC numbered steps to reproduce — clarify if vague.\n"
        "4. Ask for expected behavior vs actual behavior.\n"
        "5. Ask for environment details (cluster, namespace, version).\n"
        "6. Ask for evidence (screenshots, log snippets, error messages).\n"
        "7. Ask for workaround (or 'None').\n"
        "8. Ask for SNOW ticket — bugs often originate from SNOW.\n"
        "9. Generate Given/When/Then acceptance criteria for fix verification.\n"
        "10. Present a summary table and confirm.\n"
        "11. Call create_bug with all collected fields.\n"
        "12. Report the issue key and URL.\n\n"
        "IMPORTANT: Bugs default to HIGH priority. Summary auto-prefixed with [BUG]."
    )


@mcp.prompt("create-initiative", description="Guided workflow to create a VALIP Initiative with Lean UX format")
def _prompt_create_initiative(project_key: str = "VALIP") -> str:
    return (
        f"Create a VALIP Initiative in project {project_key}. Follow these steps:\n\n"
        "1. Ask for: work type, whether Planned or Unplanned, and initiative title.\n"
        "2. Ask for the full Problem Statement with value proposition.\n"
        "3. Collect Lean UX value fields:\n"
        "   - For, Who, The, Is a, That, Unlike, Our solution.\n"
        "4. Ask for Problem Impact (scope of impact).\n"
        "5. Ask for Benefit Hypothesis (expected benefit and business justification).\n"
        "6. Ask for PI Objective component (optional), priority, assignee.\n"
        "7. Generate a high-level Given/When/Then for initiative success.\n"
        "8. Present a summary table and confirm.\n"
        "9. Call create_initiative with all collected fields.\n"
        "10. Report the issue key and URL.\n\n"
        "Summary pattern: FY<YY> Q<N> - <WORK_TYPE>: <Planned/Unplanned> <Title>\n"
        "IMPORTANT: Initiatives default to HIGH priority. They do NOT get an Epic Link."
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
