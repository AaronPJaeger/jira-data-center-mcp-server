# Jira Data Center v10 MCP Server Implementation Plan v5

## Goal

Version 5 implements profile-based grouped tool registration for the Jira Data Center MCP server.

## Why

A large Jira MCP tool surface is powerful, but it can make agents noisier and riskier. Profiles let the same codebase expose only the tool groups needed for a given task or client session.

## Environment Controls

```dotenv
JIRA_MCP_PROFILE=standard
```

Supported profiles:

- `readonly`
- `standard`
- `agile`
- `admin`
- `full`
- `dangerous`

Explicit group override:

```dotenv
JIRA_MCP_ENABLED_GROUPS=READONLY_CORE,METADATA,WORKFLOW_READ
```

If `JIRA_MCP_ENABLED_GROUPS` is set, it takes precedence over `JIRA_MCP_PROFILE`.

## Tool Groups

- `READONLY_CORE`
- `METADATA`
- `WORKFLOW_READ`
- `WORKFLOW_WRITE`
- `ISSUE_WRITE`
- `COMMENT_WRITE`
- `ASSIGNMENT_WRITE`
- `LINK_WRITE`
- `PROPERTY_WRITE`
- `ATTACHMENT_WRITE`
- `WORKLOG_WRITE`
- `AGILE_READ`
- `AGILE_WRITE`
- `ADMIN_READ`
- `ADMIN_WRITE`
- `BULK`
- `DESTRUCTIVE`

## Profiles

### readonly

For reporting, triage, and planning. No mutations.

### standard

Default day-to-day Jira operations. Excludes destructive and bulk operations.

### agile

Sprint/backlog planning and workflow coordination.

### admin

Metadata, roles, groups, permissions, and security-level context.

### full

All non-destructive, non-bulk tools.

### dangerous

All tools. Destructive tools still require `confirm=True`.

## Implementation

Tools are decorated with:

```python
@profiled_tool("GROUP_NAME")
```

The decorator conditionally registers the function with FastMCP only when its group is enabled. Disabled functions remain available for import/testing but are not advertised to MCP clients.

## New Diagnostic Tool

- `get_mcp_profile_status`
