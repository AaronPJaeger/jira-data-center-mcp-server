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

### Quick Install with `uv` (Recommended)

The fastest way to install and run the server is with [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install jira-data-center-mcp-server
```

Or run directly without installing:

```bash
uvx jira-data-center-mcp-server
```

For development, clone the repository and install in editable mode:

```bash
git clone https://github.com/AaronPJaeger/jira-data-center-mcp-server.git
cd jira-data-center-mcp-server
uv pip install -e .
```

You can also run the package as a module:

```bash
python -m jira_data_center_mcp_server
```

### MCP Client Configuration

Add the server to your MCP client configuration (e.g. Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "jira": {
      "command": "uvx",
      "args": ["jira-data-center-mcp-server"],
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.com",
        "JIRA_PAT": "your_personal_access_token",
        "JIRA_MCP_PROFILE": "standard"
      }
    }
  }
}
```

### Configuration

The server is configured via environment variables. Create a `.env` file in your working directory or pass them directly:

```dotenv
JIRA_SERVER_URL=https://your-enterprise-jira-datacenter.com
JIRA_PAT=your_personal_access_token_here
LOG_LEVEL=INFO
JIRA_MCP_PROFILE=standard
```

| Variable | Purpose | Default |
|----------|---------|---------|
| `JIRA_SERVER_URL` | Jira Data Center base URL | (required) |
| `JIRA_PAT` | Personal Access Token | (required) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `JIRA_MCP_PROFILE` | Active tool profile | `standard` |
| `JIRA_MCP_ENABLED_GROUPS` | Override profile with explicit groups (comma-separated) | (none) |

**Getting Your Jira PAT (Personal Access Token):**
1. Log in to your Jira Data Center instance
2. Navigate to **Profile > Personal Access Tokens** (or your admin dashboard)
3. Click **Create Token**
4. Name it "MCP Server" and copy the token value
5. **Do not commit `.env` to version control** — add it to `.gitignore` if not already present

### Manual Installation (without `uv`)

<details>
<summary>Click to expand manual setup steps</summary>

#### Prerequisites

- Python 3.10 or later
- Git

#### Step 1: Clone the Repository

```bash
git clone https://github.com/AaronPJaeger/jira-data-center-mcp-server.git
cd jira-data-center-mcp-server
```

#### Step 2: Create a Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Run the Server

```bash
python -m jira_data_center_mcp_server
```

</details>

## v4.1 Addition

- `get_custom_field_options(field_id, context_id=None)` for retrieving allowed custom field options where exposed by the Jira Data Center REST surface.


## Version 5: Profile-Based Tool Sets

The server now supports grouped tool exposure through profiles. This lets you avoid exposing destructive or bulk tools during normal work.

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

## Troubleshooting

### Virtual Environment Issues

**Problem:** `command not found: python` or `.venv not activated`

**Solution:**
- Verify Python is installed: `python --version`
- Reactivate the virtual environment:
  - Windows: `.\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `source .venv/bin/activate`

### Jira Connection Errors

**Problem:** `JIRAError: (401) Unauthorized`

**Solution:**
- Verify `JIRA_SERVER_URL` is correct (no trailing slashes)
- Verify `JIRA_PAT` token is valid and has not expired
- Confirm the token has permissions for your Jira instance

**Problem:** `JIRAError: (404) Not Found`

**Solution:**
- Double-check the Jira server URL
- Verify you have network access to the Jira instance

### .env File Not Loading

**Problem:** Server starts but ignores `.env` values

**Solution:**
- Confirm `.env` exists in the project root directory
- Check file encoding is UTF-8 (not UTF-16 or other)
- Restart the server after editing `.env`

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
