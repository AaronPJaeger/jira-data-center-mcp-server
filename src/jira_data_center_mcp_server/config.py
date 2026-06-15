"""Profile-based tool registration system."""

import logging
import os
from typing import Any, Dict

from .app import mcp

logger = logging.getLogger("jira_mcp_server")

# ---------------------------------------------------------------------------
# Profile-based tool registration
# ---------------------------------------------------------------------------

ALL_TOOL_GROUPS = {
    "READONLY_CORE",
    "METADATA",
    "WORKFLOW_READ",
    "WORKFLOW_WRITE",
    "ISSUE_WRITE",
    "COMMENT_WRITE",
    "LINK_WRITE",
    "PROPERTY_WRITE",
    "ATTACHMENT_WRITE",
    "WORKLOG_WRITE",
    "AGILE_READ",
    "AGILE_WRITE",
    "VERSION_WRITE",
    "ADMIN_READ",
    "ADMIN_WRITE",
    "BULK",
    "DESTRUCTIVE",
    "COMPOSITE",
}

PROFILE_GROUPS = {
    "readonly": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "AGILE_READ",
        "ADMIN_READ",
        "COMPOSITE",
    },
    "standard": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "ISSUE_WRITE",
        "COMMENT_WRITE",
        "LINK_WRITE",
        "PROPERTY_WRITE",
        "ATTACHMENT_WRITE",
        "WORKLOG_WRITE",
        "VERSION_WRITE",
        "AGILE_READ",
        "ADMIN_READ",
        "COMPOSITE",
    },
    "agile": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "COMMENT_WRITE",
        "AGILE_READ",
        "AGILE_WRITE",
        "ADMIN_READ",
        "COMPOSITE",
    },
    "admin": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "VERSION_WRITE",
        "AGILE_READ",
        "ADMIN_READ",
        "ADMIN_WRITE",
        "COMPOSITE",
    },
    "full": {
        "READONLY_CORE",
        "METADATA",
        "WORKFLOW_READ",
        "WORKFLOW_WRITE",
        "ISSUE_WRITE",
        "COMMENT_WRITE",
        "LINK_WRITE",
        "PROPERTY_WRITE",
        "ATTACHMENT_WRITE",
        "WORKLOG_WRITE",
        "VERSION_WRITE",
        "AGILE_READ",
        "AGILE_WRITE",
        "ADMIN_READ",
        "ADMIN_WRITE",
        "COMPOSITE",
    },
    "dangerous": set(ALL_TOOL_GROUPS),
}

DEFAULT_PROFILE = os.environ.get("JIRA_MCP_PROFILE", "standard").strip().lower()
EXPLICIT_GROUPS = {
    group.strip().upper()
    for group in os.environ.get("JIRA_MCP_ENABLED_GROUPS", "").split(",")
    if group.strip()
}

if EXPLICIT_GROUPS:
    ENABLED_TOOL_GROUPS = EXPLICIT_GROUPS
    ACTIVE_PROFILE_LABEL = "custom"
else:
    ENABLED_TOOL_GROUPS = PROFILE_GROUPS.get(DEFAULT_PROFILE, PROFILE_GROUPS["standard"])
    ACTIVE_PROFILE_LABEL = DEFAULT_PROFILE if DEFAULT_PROFILE in PROFILE_GROUPS else "standard"

logger.info(
    "Jira MCP profile active: %s | groups=%s",
    ACTIVE_PROFILE_LABEL,
    ",".join(sorted(ENABLED_TOOL_GROUPS)),
)


def group_enabled(group: str) -> bool:
    return group.upper() in ENABLED_TOOL_GROUPS


def profiled_tool(group: str):
    """Register an MCP tool only when its group is enabled by the active profile."""
    normalized_group = group.upper()

    def decorator(fn):
        if group_enabled(normalized_group):
            logger.debug("Registering MCP tool %s in group %s", fn.__name__, normalized_group)
            return mcp.tool()(fn)
        logger.debug("Skipping MCP tool %s in disabled group %s", fn.__name__, normalized_group)
        return fn

    return decorator


def get_profile_status_payload() -> Dict[str, Any]:
    return {
        "active_profile": ACTIVE_PROFILE_LABEL,
        "enabled_groups": sorted(ENABLED_TOOL_GROUPS),
        "available_profiles": {name: sorted(groups) for name, groups in PROFILE_GROUPS.items()},
        "all_groups": sorted(ALL_TOOL_GROUPS),
    }
