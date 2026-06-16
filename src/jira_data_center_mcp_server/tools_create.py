"""Issue-type-specific creation tools.

Each tool encodes the field mappings, summary patterns, description templates,
and default values for a specific Jira issue type. This eliminates the need for
the calling LLM to independently know VALIP conventions — the tool itself
enforces them.
"""

from datetime import date as _date
from typing import Any, Dict, List, Optional

from .client import (
    JIRA_URL,
    _error,
    _json_dumps,
    _normalize_issue_key,
    _object_to_dict,
    _validate_issue_key,
    jira_client,
)
from .config import profiled_tool


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _va_fiscal_quarter(d: _date = None) -> dict:
    """Return VA fiscal year and quarter for the given date.

    VA fiscal calendar: Q1=Oct-Dec, Q2=Jan-Mar, Q3=Apr-Jun, Q4=Jul-Sep.
    Fiscal year starts in October of the prior calendar year.
    """
    if d is None:
        d = _date.today()
    month = d.month
    if month >= 10:
        fy = d.year + 1
        quarter = 1
    elif month >= 7:
        fy = d.year
        quarter = 4
    elif month >= 4:
        fy = d.year
        quarter = 3
    else:
        fy = d.year
        quarter = 2
    return {"fy": fy, "fy_short": fy % 100, "quarter": quarter}


def _pi_component(fy_short: int, quarter: int) -> str:
    """Format the PI component name: FY26Q3."""
    return f"FY{fy_short}Q{quarter}"


def _quarter_date_range(fy: int, quarter: int) -> dict:
    """Return the start and end dates for a VA fiscal quarter."""
    # VA FY starts Oct of prior calendar year
    calendar_year_start = fy - 1  # Oct of this year is Q1 of next FY
    ranges = {
        1: (f"{calendar_year_start}-10-01", f"{calendar_year_start}-12-31"),
        2: (f"{fy}-01-01", f"{fy}-03-31"),
        3: (f"{fy}-04-01", f"{fy}-06-30"),
        4: (f"{fy}-07-01", f"{fy}-09-30"),
    }
    start, end = ranges[quarter]
    return {"start": start, "end": end}


def _create_and_enrich(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str,
    priority: str,
    enrich_fields: Dict[str, Any],
    assignee_username: Optional[str] = None,
    link_to_issue: Optional[str] = None,
    link_type: Optional[str] = None,
) -> str:
    """Shared create → enrich → assign → link pipeline."""
    result: Dict[str, Any] = {"steps": []}

    # Step 1: Create
    try:
        issue_dict: Dict[str, Any] = {
            "project": {"key": project_key.strip().upper()},
            "summary": summary.strip(),
            "description": description,
            "issuetype": {"name": issue_type},
        }
        if priority:
            issue_dict["priority"] = {"name": priority}
        # Jira Data Center requires Epic Name (customfield_10003) for Epics
        if issue_type.strip().lower() == "epic":
            issue_dict["customfield_10003"] = summary.strip()
        new_issue = jira_client.create_issue(fields=issue_dict)
        issue_key = new_issue.key
        result["key"] = issue_key
        result["url"] = f"{JIRA_URL}/browse/{issue_key}"
        result["steps"].append({"action": "create", "ok": True})
    except Exception as exc:
        return _error("Failed to create issue", exc)

    # Step 2: Enrich
    if enrich_fields:
        try:
            issue = jira_client.issue(issue_key)
            issue.update(fields=enrich_fields)
            result["steps"].append({
                "action": "enrich",
                "ok": True,
                "fields_set": list(enrich_fields.keys()),
            })
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
                    type=link_type or "Relates",
                    inwardIssue=_normalize_issue_key(link_to_issue),
                    outwardIssue=issue_key,
                )
                result["steps"].append({
                    "action": "link",
                    "ok": True,
                    "link": f"{issue_key} {link_type or 'Relates'} {_normalize_issue_key(link_to_issue)}",
                })
            except Exception as exc:
                result["steps"].append({"action": "link", "ok": False, "error": str(exc)})

    return _json_dumps(result)


# ---------------------------------------------------------------------------
# create_story
# ---------------------------------------------------------------------------

@profiled_tool("COMPOSITE")
def create_story(
    project_key: str,
    summary: str,
    role: str,
    goal: str,
    benefit: str,
    epic_key: str,
    acceptance_criteria: str,
    platform: str = "VALIP",
    priority: str = "Medium",
    dev_notes: Optional[str] = None,
    assignee_username: Optional[str] = None,
    collaborators_json: Optional[str] = None,
    snow_ticket: Optional[str] = None,
    estimate: Optional[str] = None,
    target_start_date: Optional[str] = None,
    target_end_date: Optional[str] = None,
    fix_versions: Optional[str] = None,
) -> str:
    """Create a Jira Story with VALIP conventions.

    Stories use a strict format: the description contains ONLY the user story
    statement (As a / I want / So that). All implementation details go into
    Dev Notes (customfield_19701). Acceptance criteria go into customfield_10500
    as Given/When/Then blocks.

    Args:
        project_key: Project key (e.g. "VALIP").
        summary: Base summary text (auto-prefixed with platform).
        role: The "As a <role>" part of the user story.
        goal: The "I want <goal>" part.
        benefit: The "So that <benefit>" part.
        epic_key: Parent epic key (e.g. "VALIP-5135"). Required for stories.
        acceptance_criteria: Given/When/Then acceptance criteria text.
        platform: Platform name for summary prefix (default "VALIP").
        priority: Priority name (default "Medium").
        dev_notes: Background, implementation steps, affected systems, evidence
            to collect. Goes into Dev Notes (customfield_19701), NOT description.
        assignee_username: Jira username to assign.
        collaborators_json: JSON array of collaborator objects.
            Example: '[{"name":"user1"},{"name":"user2"}]'
        snow_ticket: SNOW/RITM/SCTASK ticket number (string, no URL).
        estimate: Time estimate in Jira format (e.g. "4h", "2d", "1w").
        target_start_date: Target start in YYYY-MM-DD format.
        target_end_date: Target end in YYYY-MM-DD format.
        fix_versions: Comma-separated version names (e.g. "FY26Q3" or
            "FY26Q3,VALIP Platform 2.18.0.0"). The PI quarter version is
            auto-calculated and prepended if omitted.
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not role or not goal or not benefit:
        return "Error: role, goal, and benefit are all required for a Story."
    if not epic_key or not epic_key.strip():
        return "Error: epic_key is required for stories."
    epic_err = _validate_issue_key(epic_key)
    if epic_err:
        return f"Error: invalid epic_key — {epic_err}"

    # Auto-prefix summary
    full_summary = f"{platform} - {summary.strip()}"

    # Build user story description
    description = f"*As a* {role},\n*I want* {goal},\n*So that* {benefit}."

    # Build fixVersions list from comma-separated string
    if fix_versions:
        version_names = [v.strip() for v in fix_versions.split(",") if v.strip()]
    else:
        version_names = []
    # Auto-add PI quarter if no version was provided
    if not version_names:
        fq = _va_fiscal_quarter()
        version_names.append(_pi_component(fq["fy_short"], fq["quarter"]))

    # Build enrichment fields
    enrich: Dict[str, Any] = {
        "customfield_10001": _normalize_issue_key(epic_key),  # Epic Link
        "fixVersions": [{"name": v} for v in version_names],
    }
    if acceptance_criteria:
        enrich["customfield_10500"] = acceptance_criteria
    if dev_notes:
        enrich["customfield_19701"] = dev_notes
    if snow_ticket:
        enrich["customfield_16316"] = snow_ticket
    if estimate:
        enrich["timetracking"] = {"originalEstimate": estimate}
    if target_start_date:
        enrich["customfield_11704"] = target_start_date
    if target_end_date:
        enrich["customfield_11705"] = target_end_date
    if collaborators_json:
        import json
        try:
            enrich["customfield_22701"] = json.loads(collaborators_json)
        except Exception:
            pass  # Skip invalid collaborators silently

    return _create_and_enrich(
        project_key=project_key,
        summary=full_summary,
        description=description,
        issue_type="Story",
        priority=priority,
        enrich_fields=enrich,
        assignee_username=assignee_username,
    )


# ---------------------------------------------------------------------------
# create_epic
# ---------------------------------------------------------------------------

@profiled_tool("COMPOSITE")
def create_epic(
    project_key: str,
    title: str,
    platform: str,
    work_type: str,
    planned_or_unplanned: str,
    value_statement_for: str,
    value_statement_who: str,
    value_statement_the: str,
    value_statement_that: str,
    value_statement_unlike: str,
    value_statement_our_solution: str,
    in_scope: str,
    out_of_scope: str,
    acceptance_criteria: str,
    role: Optional[str] = None,
    goal: Optional[str] = None,
    benefit: Optional[str] = None,
    non_functional: Optional[str] = None,
    priority: str = "Medium",
    assignee_username: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[int] = None,
    target_start_date: Optional[str] = None,
    target_end_date: Optional[str] = None,
    labels_json: Optional[str] = None,
    pi_objective_component: Optional[str] = None,
) -> str:
    """Create a Jira Epic with VALIP conventions.

    Epics use a specific summary pattern and a Value Statement description format.
    They do NOT get an Epic Link (they ARE the epic). They auto-calculate PI
    component, date range, and fiscal quarter from the current date.

    Summary pattern: FY<YY> Q<N> <PLATFORM>: <WORK_TYPE> <Planned/Unplanned> - <Title>
    Example: "FY26 Q3 VALIP: OPS Unplanned - Core Infrastructure Operations"

    Args:
        project_key: Project key (e.g. "VALIP").
        title: Epic title (the descriptive part after the prefix).
        platform: Platform name (e.g. "VALIP", "4S2", "VDM").
        work_type: Work type (e.g. "DEV", "SEC", "OPS").
        planned_or_unplanned: Either "Planned" or "Unplanned".
        value_statement_for: Primary beneficiaries.
        value_statement_who: Beneficiary need.
        value_statement_the: Solution name.
        value_statement_that: Solution description / outcome.
        value_statement_unlike: Current state or alternative.
        value_statement_our_solution: Differentiating approach.
        in_scope: Bulleted scope items (newline-separated).
        out_of_scope: Bulleted out-of-scope items (newline-separated).
        acceptance_criteria: High-level Given/When/Then for the entire epic.
        role: Optional "As a" role for the user story opener.
        goal: Optional "I want" goal for the user story opener.
        benefit: Optional "So that" benefit for the user story opener.
        non_functional: Non-functional requirements (newline-separated). Optional.
        priority: Priority name (default "Medium").
        assignee_username: Jira username to assign.
        fiscal_year: Full fiscal year (e.g. 2026). Auto-calculated if omitted.
        fiscal_quarter: Fiscal quarter (1-4). Auto-calculated if omitted.
        target_start_date: YYYY-MM-DD override. Auto-calculated if omitted.
        target_end_date: YYYY-MM-DD override. Auto-calculated if omitted.
        labels_json: JSON array of label strings. Default: ["VALIP-PLATFORM-&-[Technical_Support]"].
        pi_objective_component: Optional PI Objective component name
            (e.g. "FY26Q3 - OPS Platform Objective").
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not title or not title.strip():
        return "Error: title is required."
    if not platform or not platform.strip():
        return "Error: platform is required."
    if not work_type or not work_type.strip():
        return "Error: work_type is required."
    if planned_or_unplanned not in ("Planned", "Unplanned"):
        return "Error: planned_or_unplanned must be 'Planned' or 'Unplanned'."

    # Fiscal calendar
    if fiscal_year and fiscal_quarter:
        fy = fiscal_year
        fy_short = fy % 100
        quarter = fiscal_quarter
    else:
        fq = _va_fiscal_quarter()
        fy = fq["fy"]
        fy_short = fq["fy_short"]
        quarter = fq["quarter"]

    # Summary
    full_summary = f"FY{fy_short} Q{quarter} {platform.upper()}: {work_type.upper()} {planned_or_unplanned} - {title.strip()}"

    # Description — Value Statement format
    desc_parts = []

    # Optional user story opener
    if role and goal and benefit:
        desc_parts.append(f"*As a* {role},")
        desc_parts.append(f"*I want to* {goal},")
        desc_parts.append(f"*So that* {benefit}.")
        desc_parts.append("")

    desc_parts.append("h1. Value Statement")
    desc_parts.append("")
    desc_parts.append(f"*For:*\n{value_statement_for}")
    desc_parts.append("")
    desc_parts.append(f"*Who:*\n{value_statement_who}")
    desc_parts.append("")
    desc_parts.append(f"*The:*\n{value_statement_the}")
    desc_parts.append("")
    desc_parts.append(f"*That:*\n{value_statement_that}")
    desc_parts.append("")
    desc_parts.append(f"*Unlike:*\n{value_statement_unlike}")
    desc_parts.append("")
    desc_parts.append(f"*Our Process/Solution:*\n{value_statement_our_solution}")
    desc_parts.append("")

    # In Scope
    desc_parts.append("h2. In Scope")
    for item in in_scope.strip().split("\n"):
        item = item.strip().lstrip("*- ")
        if item:
            desc_parts.append(f" * {item}")
    desc_parts.append("")

    # Out of Scope
    desc_parts.append("h2. Out of Scope")
    for item in out_of_scope.strip().split("\n"):
        item = item.strip().lstrip("*- ")
        if item:
            desc_parts.append(f" * {item}")
    desc_parts.append("")

    # Non-Functional
    if non_functional:
        desc_parts.append("h2. Non\u2011Functional")
        for item in non_functional.strip().split("\n"):
            item = item.strip().lstrip("*- ")
            if item:
                desc_parts.append(f" * {item}")
        desc_parts.append("")

    description = "\n".join(desc_parts)

    # Date range
    if not target_start_date or not target_end_date:
        dr = _quarter_date_range(fy, quarter)
        target_start_date = target_start_date or dr["start"]
        target_end_date = target_end_date or dr["end"]

    # Enrichment — no Epic Link and no fixVersions for epics
    enrich: Dict[str, Any] = {
        "customfield_11704": target_start_date,
        "customfield_11705": target_end_date,
    }
    if acceptance_criteria:
        enrich["customfield_10500"] = acceptance_criteria

    # Components — always use the PI quarter label, never the release version
    pi_component_name = _pi_component(fy_short, quarter)
    components: List[Dict[str, str]] = [{"name": pi_component_name}]
    if pi_objective_component:
        components.append({"name": pi_objective_component})
    enrich["components"] = components

    # Labels
    if labels_json:
        import json
        try:
            enrich["labels"] = json.loads(labels_json)
        except Exception:
            enrich["labels"] = ["VALIP-PLATFORM-&-[Technical_Support]"]
    else:
        enrich["labels"] = ["VALIP-PLATFORM-&-[Technical_Support]"]

    return _create_and_enrich(
        project_key=project_key,
        summary=full_summary,
        description=description,
        issue_type="Epic",
        priority=priority,
        enrich_fields=enrich,
        assignee_username=assignee_username,
    )


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

@profiled_tool("COMPOSITE")
def create_task(
    project_key: str,
    summary: str,
    objective: str,
    steps: str,
    verification: str,
    epic_key: str,
    platform: str = "VALIP",
    priority: str = "Medium",
    background: Optional[str] = None,
    affected_systems: Optional[str] = None,
    dependencies: Optional[str] = None,
    acceptance_criteria: Optional[str] = None,
    assignee_username: Optional[str] = None,
    snow_ticket: Optional[str] = None,
    estimate: Optional[str] = None,
    target_start_date: Optional[str] = None,
    target_end_date: Optional[str] = None,
    fix_versions: Optional[str] = None,
) -> str:
    """Create a Jira Task with VALIP conventions.

    Tasks are for technical/operational work that does not map to a user story.
    The description includes objective, steps, verification, and optionally
    background, affected systems, and dependencies. Acceptance criteria use
    a checklist style rather than Given/When/Then.

    Args:
        project_key: Project key (e.g. "VALIP").
        summary: Base summary text (auto-prefixed with platform).
        objective: What needs to be done and why.
        steps: Numbered implementation steps (newline-separated).
        verification: How to verify completion.
        epic_key: Parent epic key (e.g. "VALIP-5135"). Required for tasks.
        platform: Platform name for summary prefix (default "VALIP").
        priority: Priority name (default "Medium").
        background: Context and motivation. Optional.
        affected_systems: Systems affected (newline-separated). Optional.
        dependencies: Dependencies (newline-separated). Optional.
        acceptance_criteria: Checklist-style completion criteria (newline-separated).
            Optional.
        assignee_username: Jira username to assign.
        snow_ticket: SNOW/RITM/SCTASK ticket number.
        estimate: Time estimate in Jira format (e.g. "4h", "2d").
        target_start_date: Target start in YYYY-MM-DD format.
        target_end_date: Target end in YYYY-MM-DD format.
        fix_versions: Comma-separated version names (e.g. "FY26Q3" or
            "FY26Q3,VALIP Platform 2.18.0.0"). Auto-calculated if omitted.
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not objective:
        return "Error: objective is required for tasks."
    if not steps:
        return "Error: steps is required for tasks."
    if not verification:
        return "Error: verification is required for tasks."
    if not epic_key or not epic_key.strip():
        return "Error: epic_key is required for tasks."
    epic_err = _validate_issue_key(epic_key)
    if epic_err:
        return f"Error: invalid epic_key — {epic_err}"

    full_summary = f"{platform} - {summary.strip()}"

    # Build structured description
    desc_parts = [
        "h2. Objective",
        objective.strip(),
        "",
    ]
    if background:
        desc_parts += ["h2. Background", background.strip(), ""]

    desc_parts.append("h2. Steps")
    for i, step in enumerate(steps.strip().split("\n"), 1):
        step = step.strip().lstrip("#0123456789.) ")
        if step:
            desc_parts.append(f"# {step}")
    desc_parts.append("")

    if affected_systems:
        desc_parts.append("h2. Affected Systems")
        for sys in affected_systems.strip().split("\n"):
            sys = sys.strip().lstrip("*- ")
            if sys:
                desc_parts.append(f" * {sys}")
        desc_parts.append("")

    desc_parts.append("h2. Dependencies")
    if dependencies:
        for dep in dependencies.strip().split("\n"):
            dep = dep.strip().lstrip("*- ")
            if dep:
                desc_parts.append(f" * {dep}")
    else:
        desc_parts.append(" * None")
    desc_parts.append("")

    desc_parts += ["h2. Verification", f" * {verification.strip()}", ""]

    description = "\n".join(desc_parts)

    # Build fixVersions list
    if fix_versions:
        version_names = [v.strip() for v in fix_versions.split(",") if v.strip()]
    else:
        version_names = []
    if not version_names:
        fq = _va_fiscal_quarter()
        version_names.append(_pi_component(fq["fy_short"], fq["quarter"]))

    # Enrichment
    enrich: Dict[str, Any] = {
        "customfield_10001": _normalize_issue_key(epic_key),
        "fixVersions": [{"name": v} for v in version_names],
    }
    if acceptance_criteria:
        enrich["customfield_10500"] = acceptance_criteria
    if snow_ticket:
        enrich["customfield_16316"] = snow_ticket
    if estimate:
        enrich["timetracking"] = {"originalEstimate": estimate}
    if target_start_date:
        enrich["customfield_11704"] = target_start_date
    if target_end_date:
        enrich["customfield_11705"] = target_end_date

    return _create_and_enrich(
        project_key=project_key,
        summary=full_summary,
        description=description,
        issue_type="Task",
        priority=priority,
        enrich_fields=enrich,
        assignee_username=assignee_username,
    )


# ---------------------------------------------------------------------------
# create_bug
# ---------------------------------------------------------------------------

@profiled_tool("COMPOSITE")
def create_bug(
    project_key: str,
    summary: str,
    problem_statement: str,
    steps_to_reproduce: str,
    expected_behavior: str,
    actual_behavior: str,
    epic_key: str,
    platform: str = "VALIP",
    priority: str = "High",
    environment: Optional[str] = None,
    evidence: Optional[str] = None,
    workaround: Optional[str] = None,
    acceptance_criteria: Optional[str] = None,
    assignee_username: Optional[str] = None,
    snow_ticket: Optional[str] = None,
    estimate: Optional[str] = None,
    target_start_date: Optional[str] = None,
    target_end_date: Optional[str] = None,
    fix_versions: Optional[str] = None,
) -> str:
    """Create a Jira Bug with VALIP conventions.

    Bugs auto-prefix the summary with "[BUG]" and default to High priority.
    The description includes structured sections for problem statement,
    reproduction steps, expected vs actual behavior, environment, evidence,
    and workaround.

    Summary pattern: <PLATFORM> - [BUG] <short problem description>
    Example: "VALIP - [BUG] Health check endpoint returns 503 after pod restart"

    Args:
        project_key: Project key (e.g. "VALIP").
        summary: Short problem description (auto-prefixed with platform and [BUG]).
        problem_statement: What is broken and its impact.
        steps_to_reproduce: Numbered reproduction steps (newline-separated).
        expected_behavior: What should happen.
        actual_behavior: What actually happens.
        epic_key: Parent epic key (e.g. "VALIP-5135"). Required for bugs.
        platform: Platform name for summary prefix (default "VALIP").
        priority: Priority name (default "High" for bugs).
        environment: Environment details (cluster, namespace, version). Optional.
        evidence: Screenshots, log links, error messages. Optional.
        workaround: Known workaround or "None". Optional.
        acceptance_criteria: Given/When/Then criteria for fix verification. Optional.
        assignee_username: Jira username to assign.
        snow_ticket: SNOW/RITM/SCTASK ticket number. Bugs often originate from SNOW.
        estimate: Time estimate in Jira format.
        target_start_date: Target start in YYYY-MM-DD format.
        target_end_date: Target end in YYYY-MM-DD format.
        fix_versions: Comma-separated version names (e.g. "FY26Q3" or
            "FY26Q3,VALIP Platform 2.18.0.0"). Auto-calculated if omitted.
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not summary or not summary.strip():
        return "Error: summary is required."
    if not problem_statement:
        return "Error: problem_statement is required for bugs."
    if not steps_to_reproduce:
        return "Error: steps_to_reproduce is required for bugs."
    if not expected_behavior:
        return "Error: expected_behavior is required for bugs."
    if not actual_behavior:
        return "Error: actual_behavior is required for bugs."
    if not epic_key or not epic_key.strip():
        return "Error: epic_key is required for bugs."
    epic_err = _validate_issue_key(epic_key)
    if epic_err:
        return f"Error: invalid epic_key — {epic_err}"

    # Auto-prefix summary with [BUG]
    clean_summary = summary.strip()
    if not clean_summary.upper().startswith("[BUG]"):
        clean_summary = f"[BUG] {clean_summary}"
    full_summary = f"{platform} - {clean_summary}"

    # Build structured description
    desc_parts = [
        "h2. Problem Statement",
        problem_statement.strip(),
        "",
        "h2. Steps to Reproduce",
    ]
    for i, step in enumerate(steps_to_reproduce.strip().split("\n"), 1):
        step = step.strip().lstrip("#0123456789.) ")
        if step:
            desc_parts.append(f"# {step}")
    desc_parts.append("")

    desc_parts += [
        "h2. Expected Behavior",
        expected_behavior.strip(),
        "",
        "h2. Actual Behavior",
        actual_behavior.strip(),
        "",
    ]

    if environment:
        desc_parts += ["h2. Environment", environment.strip(), ""]

    desc_parts.append("h2. Evidence")
    if evidence:
        for item in evidence.strip().split("\n"):
            item = item.strip().lstrip("*- ")
            if item:
                desc_parts.append(f" * {item}")
    else:
        desc_parts.append(" * Pending — attach screenshots or logs after creation")
    desc_parts.append("")

    desc_parts.append("h2. Workaround")
    desc_parts.append(workaround.strip() if workaround else "None")
    desc_parts.append("")

    description = "\n".join(desc_parts)

    # Build fixVersions list
    if fix_versions:
        version_names = [v.strip() for v in fix_versions.split(",") if v.strip()]
    else:
        version_names = []
    if not version_names:
        fq = _va_fiscal_quarter()
        version_names.append(_pi_component(fq["fy_short"], fq["quarter"]))

    # Enrichment
    enrich: Dict[str, Any] = {
        "customfield_10001": _normalize_issue_key(epic_key),
        "fixVersions": [{"name": v} for v in version_names],
    }
    if acceptance_criteria:
        enrich["customfield_10500"] = acceptance_criteria
    if snow_ticket:
        enrich["customfield_16316"] = snow_ticket
    if estimate:
        enrich["timetracking"] = {"originalEstimate": estimate}
    if target_start_date:
        enrich["customfield_11704"] = target_start_date
    if target_end_date:
        enrich["customfield_11705"] = target_end_date

    return _create_and_enrich(
        project_key=project_key,
        summary=full_summary,
        description=description,
        issue_type="Bug",
        priority=priority,
        enrich_fields=enrich,
        assignee_username=assignee_username,
    )


# ---------------------------------------------------------------------------
# create_initiative
# ---------------------------------------------------------------------------

@profiled_tool("COMPOSITE")
def create_initiative(
    project_key: str,
    title: str,
    work_type: str,
    planned_or_unplanned: str,
    problem_statement: str,
    value_for: str,
    value_who: str,
    value_the: str,
    value_is_a: str,
    value_that: str,
    value_unlike: str,
    value_our_solution: str,
    problem_impact: str,
    benefit_hypothesis: str,
    acceptance_criteria: str,
    priority: str = "High",
    assignee_username: Optional[str] = None,
    fix_versions: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[int] = None,
    target_start_date: Optional[str] = None,
    target_end_date: Optional[str] = None,
    labels_json: Optional[str] = None,
    pi_objective_component: Optional[str] = None,
) -> str:
    """Create a Jira Initiative with VALIP conventions.

    Initiatives sit above epics in the hierarchy and use a Lean UX problem
    statement format. They do NOT get an Epic Link (they are parents to epics).
    They default to High priority.

    Summary pattern: FY<YY> Q<N> - <WORK_TYPE>: <Planned/Unplanned> <Title>
    Example: "FY26 Q4 - OPS: Unplanned Operations & Maintenance"

    Args:
        project_key: Project key (e.g. "VALIP").
        title: Initiative title (descriptive part after prefix).
        work_type: Work type (e.g. "DEV", "SEC", "OPS").
        planned_or_unplanned: Either "Planned" or "Unplanned".
        problem_statement: Full problem statement with value proposition.
        value_for: Primary beneficiaries.
        value_who: Beneficiary need.
        value_the: Solution name.
        value_is_a: Solution category.
        value_that: Solution outcome.
        value_unlike: Current state or alternative.
        value_our_solution: Differentiating approach.
        problem_impact: Scope of impact.
        benefit_hypothesis: Expected benefit and business justification.
        acceptance_criteria: High-level Given/When/Then for initiative success.
        priority: Priority name (default "High" for initiatives).
        assignee_username: Jira username to assign.
        fix_versions: Comma-separated version names (e.g. "FY26Q3" or
            "FY26Q3,VALIP Platform 2.18.0.0"). Auto-calculated if omitted.
        fiscal_year: Full fiscal year (e.g. 2026). Auto-calculated if omitted.
        fiscal_quarter: Fiscal quarter (1-4). Auto-calculated if omitted.
        target_start_date: YYYY-MM-DD override. Auto-calculated if omitted.
        target_end_date: YYYY-MM-DD override. Auto-calculated if omitted.
        labels_json: JSON array of label strings.
            Default: ["VALIP-PLATFORM-&-[Technical_Support]"].
        pi_objective_component: Optional PI Objective component name
            (e.g. "FY26Q4 - OPS Unplanned Platform Objective").
    """
    if not project_key or not project_key.strip():
        return "Error: project_key is required."
    if not title or not title.strip():
        return "Error: title is required."
    if not work_type or not work_type.strip():
        return "Error: work_type is required."
    if planned_or_unplanned not in ("Planned", "Unplanned"):
        return "Error: planned_or_unplanned must be 'Planned' or 'Unplanned'."
    if not problem_statement:
        return "Error: problem_statement is required for initiatives."

    # Fiscal calendar
    if fiscal_year and fiscal_quarter:
        fy = fiscal_year
        fy_short = fy % 100
        quarter = fiscal_quarter
    else:
        fq = _va_fiscal_quarter()
        fy = fq["fy"]
        fy_short = fq["fy_short"]
        quarter = fq["quarter"]

    # Summary — note dash separator differs from epics
    full_summary = f"FY{fy_short} Q{quarter} - {work_type.upper()}: {planned_or_unplanned} {title.strip()}"

    # Description — Lean UX problem statement format
    desc_parts = [
        f"*Problem Statement:* {problem_statement.strip()}",
        "",
        f"*For:* {value_for}",
        "",
        f"*Who:* {value_who}",
        "",
        f"*The:* {value_the}",
        "",
        f"*Is a:* {value_is_a}",
        "",
        f"*That:* {value_that}",
        "",
        f"*Unlike:* {value_unlike}",
        "",
        f"*Our solution:* {value_our_solution}",
        "",
        f"*Problem Impact:* {problem_impact}",
        "",
        f"*Benefit Hypothesis:* {benefit_hypothesis}",
    ]
    description = "\n".join(desc_parts)

    # Date range
    if not target_start_date or not target_end_date:
        dr = _quarter_date_range(fy, quarter)
        target_start_date = target_start_date or dr["start"]
        target_end_date = target_end_date or dr["end"]

    # Build fixVersions list
    if fix_versions:
        version_names = [v.strip() for v in fix_versions.split(",") if v.strip()]
    else:
        version_names = []
    if not version_names:
        version_names.append(_pi_component(fy_short, quarter))

    # Enrichment — no Epic Link for initiatives
    enrich: Dict[str, Any] = {
        "fixVersions": [{"name": v} for v in version_names],
        "customfield_11704": target_start_date,
        "customfield_11705": target_end_date,
    }
    if acceptance_criteria:
        enrich["customfield_10500"] = acceptance_criteria

    # Components — always use the PI quarter label, never the release version
    pi_component_name = _pi_component(fy_short, quarter)
    components: List[Dict[str, str]] = [{"name": pi_component_name}]
    if pi_objective_component:
        components.append({"name": pi_objective_component})
    enrich["components"] = components

    # Labels
    if labels_json:
        import json
        try:
            enrich["labels"] = json.loads(labels_json)
        except Exception:
            enrich["labels"] = ["VALIP-PLATFORM-&-[Technical_Support]"]
    else:
        enrich["labels"] = ["VALIP-PLATFORM-&-[Technical_Support]"]

    return _create_and_enrich(
        project_key=project_key,
        summary=full_summary,
        description=description,
        issue_type="Initiative",
        priority=priority,
        enrich_fields=enrich,
        assignee_username=assignee_username,
    )
