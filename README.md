# Jira Data Center v10 MCP Server

Enterprise-grade Model Context Protocol (MCP) server for Jira Data Center v10.

This server exposes Jira search, issue inspection, creation, rich updates, workflow transitions, comments, identity lookup, schema discovery, issue links, attachments, worklogs, Jira Software Agile operations, audit/history, saved filters, issue properties, project roles, groups, security levels, and guarded destructive operations to MCP-compatible clients.

## Tool Coverage

### Search and inspection

- `search_issues`
- `get_issue_details`
- `validate_jql`
- `get_issue_changelog`
- `get_issue_activity`

### Project/schema metadata

- `list_projects`
- `get_project_metadata`
- `get_create_issue_metadata`
- `list_issue_types`
- `list_priorities`
- `list_fields`
- `get_custom_field_options`
- `list_components`
- `list_versions`

### Issue lifecycle and mutation

- `create_issue`
- `create_subtask`
- `list_subtasks`
- `update_issue`
- `update_issue_structured`
- `update_issue_fields`
- `delete_issue`

### Workflow

- `get_available_transitions`
- `transition_issue`
- `transition_issue_with_fields`
- `list_statuses`
- `list_resolutions`
- `list_workflows`

### Comments and collaboration

- `add_comment`
- `list_comments`
- `update_comment`
- `delete_comment`
- `assign_issue`
- `unassign_issue`
- `list_watchers`
- `watch_issue`
- `unwatch_issue`
- `search_users`

### Permissions and server context

- `get_myself`
- `get_my_permissions`
- `get_server_info`

### Links, remote links, and issue properties

- `list_issue_links`
- `list_issue_link_types`
- `create_issue_link`
- `delete_issue_link`
- `list_remote_links`
- `add_remote_link`
- `delete_remote_link`
- `list_issue_properties`
- `get_issue_property`
- `set_issue_property`
- `delete_issue_property`

### Attachments

- `list_attachments`
- `add_attachment`
- `download_attachment`
- `delete_attachment`

### Worklogs

- `list_worklogs`
- `add_worklog`
- `update_worklog`
- `delete_worklog`

### Jira Software Agile

- `list_boards`
- `get_board_configuration`
- `list_sprints`
- `get_sprint`
- `list_sprint_issues`
- `move_issues_to_sprint`
- `move_issues_to_backlog`
- `rank_issue`

### Filters, roles, groups, security

- `list_filters`
- `get_filter`
- `run_filter`
- `list_project_roles`
- `get_project_role_actors`
- `list_groups`
- `list_security_levels`
- `set_issue_security_level`

### Conservative bulk operations

- `bulk_update_issues`
- `bulk_transition_issues`
- `bulk_add_comment`

## Installation

```bash
git clone https://github.com/AaronPJaeger/jira-data-center-mcp-server.git
cd jira-data-center-mcp-server

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
JIRA_SERVER_URL=https://your-enterprise-jira-datacenter.com
JIRA_PAT=your_secure_personal_access_token_string_here
LOG_LEVEL=INFO
```

Do not commit `.env` or Jira PAT values.

## Smoke Test

```bash
npx @modelcontextprotocol/inspector python /absolute/path/to/jira-data-center-mcp-server/jira_server.py
```

## Claude Desktop Example

```json
{
  "mcpServers": {
    "jira-datacenter-v10-service": {
      "command": "python",
      "args": [
        "/absolute/secure/path/to/jira-data-center-mcp-server/jira_server.py"
      ],
      "env": {
        "JIRA_SERVER_URL": "https://your-enterprise-jira-datacenter.com",
        "JIRA_PAT": "your_secure_personal_access_token_string_here"
      }
    }
  }
}
```

## v4.1 Addition

- `get_custom_field_options(field_id, context_id=None)` for retrieving allowed custom field options where exposed by the Jira Data Center REST surface.


## Version 5: Profile-Based Tool Sets

The server now supports grouped tool exposure through profiles. This keeps Copilot/agents focused and lets you avoid exposing destructive or bulk tools during normal work.

Set one profile:

```dotenv
JIRA_MCP_PROFILE=standard
```

Supported profiles:

| Profile | Purpose |
| :--- | :--- |
| `readonly` | Discovery, triage, reporting, metadata, comments read, issue history, Agile read-only. |
| `standard` | Default. Normal day-to-day issue work without destructive/bulk tools. |
| `agile` | Sprint/backlog planning profile. |
| `admin` | Metadata, roles, groups, permissions, and security context. |
| `full` | All non-destructive, non-bulk tools. |
| `dangerous` | All tools, including destructive and bulk tools. Destructive tools still require `confirm=True`. |

You can also bypass profiles and enable exact groups:

```dotenv
JIRA_MCP_ENABLED_GROUPS=READONLY_CORE,METADATA,WORKFLOW_READ,AGILE_READ
```

Available groups:

```text
READONLY_CORE
METADATA
WORKFLOW_READ
WORKFLOW_WRITE
ISSUE_WRITE
COMMENT_WRITE
ASSIGNMENT_WRITE
LINK_WRITE
PROPERTY_WRITE
ATTACHMENT_WRITE
WORKLOG_WRITE
AGILE_READ
AGILE_WRITE
ADMIN_READ
ADMIN_WRITE
BULK
DESTRUCTIVE
```

The `get_mcp_profile_status` tool is exposed through the `METADATA` group and reports the active profile and enabled groups.

### VS Code/Copilot profile example

Use `vscode_mcp_profiles.example.json` as a template for multiple local MCP server entries, all pointing to the same `jira_server.py` but with different `JIRA_MCP_PROFILE` values.

## Safety and Operational Notes

Destructive or broad actions require explicit confirmation parameters:

- `delete_issue(confirm=True)`
- `delete_comment(confirm=True)`
- `delete_issue_link(confirm=True)`
- `delete_remote_link(confirm=True)`
- `delete_issue_property(confirm=True)`
- `delete_attachment(confirm=True)`
- `delete_worklog(confirm=True)`
- `bulk_update_issues(confirm=True)`
- `bulk_transition_issues(confirm=True)`
- `bulk_add_comment(confirm=True)`

Bulk operations only accept explicit issue keys. They do not mutate by broad JQL query.
