# Jira Data Center v10 MCP Server

Enterprise-grade Model Context Protocol (MCP) server for Jira Data Center v10.

This server exposes Jira search, issue inspection, creation, rich updates, workflow transitions, comments, identity lookup, schema discovery, issue links, attachments, worklogs, Jira Software Agile operations, audit/history, saved filters, issue properties, project roles, groups, security levels, and guarded destructive operations to MCP-compatible clients.

## Installation

### Quick Install with `uv` (Recommended)

Install the server with [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/AaronPJaeger/jira-data-center-mcp-server.git
```

To install a specific release:

```bash
uv tool install git+https://github.com/AaronPJaeger/jira-data-center-mcp-server.git@v0.1.0
```

This installs `jira-data-center-mcp-server` as a standalone executable with all dependencies pre-resolved. To upgrade later:

```bash
uv tool upgrade jira-data-center-mcp-server
```

For development, clone the repository and install locally:

```bash
git clone https://github.com/AaronPJaeger/jira-data-center-mcp-server.git
cd jira-data-center-mcp-server
uv sync                      # install dependencies into local .venv
uv tool install --force .    # rebuild the global executable used by MCP clients
```

After making code changes, rebuild and restart the MCP server:

```bash
uv tool install --force .
# Then restart the MCP server from your MCP client (e.g. VS Code MCP panel)
```

### MCP Client Configuration

After installing, add the server to your MCP client configuration. Use the full path to the executable — find it with `uv tool dir --bin` (typically `~/.local/bin` on Linux/macOS or `%USERPROFILE%\.local\bin` on Windows).

**VS Code** (`settings.json` or user-level `mcp.json`):

```json
{
  "servers": {
    "jira": {
      "type": "stdio",
      "command": "/full/path/to/jira-data-center-mcp-server",
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.com",
        "JIRA_PAT": "your_personal_access_token",
        "JIRA_MCP_PROFILE": "standard"
      }
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "jira": {
      "command": "/full/path/to/jira-data-center-mcp-server",
      "env": {
        "JIRA_SERVER_URL": "https://your-jira-instance.com",
        "JIRA_PAT": "your_personal_access_token",
        "JIRA_MCP_PROFILE": "standard"
      }
    }
  }
}
```

> **Tip:** If `~/.local/bin` is on your PATH (run `uv tool update-shell` to add it), you can use just `"jira-data-center-mcp-server"` instead of the full path.

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

#### Profiles

Profiles control which tools the server exposes to MCP clients. Use `standard` if you're unsure — it covers normal day-to-day Jira work without exposing destructive or bulk operations.

| Profile | Purpose |
| :--- | :--- |
| `readonly` | Discovery, triage, reporting, metadata, issue history, Agile read-only. Safe for dashboards and bots. |
| `standard` | **Recommended default.** Normal issue work — create, update, transition, comment, link, attach — without destructive or bulk tools. |
| `agile` | Sprint and backlog planning. Adds board/sprint write operations. |
| `admin` | Metadata, roles, groups, permissions, and security context. Read-heavy admin tasks. |
| `full` | All non-destructive, non-bulk tools. |
| `dangerous` | All tools, including delete and bulk operations. Destructive tools still require `confirm=True`. |

You can also bypass profiles and enable exact tool groups:

```dotenv
JIRA_MCP_ENABLED_GROUPS=READONLY_CORE,METADATA,WORKFLOW_READ,AGILE_READ
```

The `get_mcp_profile_status` tool reports the active profile and enabled groups at runtime.

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

### Versions and releases

- `get_version`
- `get_version_related_issues`
- `create_version`
- `update_version`
- `release_version`
- `unrelease_version`
- `archive_version`
- `unarchive_version`
- `delete_version`

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
- `delete_version(confirm=True)`
- `bulk_update_issues(confirm=True)`
- `bulk_transition_issues(confirm=True)`
- `bulk_add_comment(confirm=True)`

Bulk operations only accept explicit issue keys. They do not mutate by broad JQL query.
