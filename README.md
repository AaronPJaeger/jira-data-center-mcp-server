# Jira Data Center v10 MCP Server

Task-oriented Model Context Protocol (MCP) server for Jira Data Center v10.

Exposes consolidated tools for issue management, workflow transitions, and agile operations. Static metadata is available as MCP Resources (`jira://` URIs). Common multi-step workflows have dedicated composite tools that reduce LLM round-trips. Guided workflows are available as MCP Prompts.

## Installation

### Prerequisites — install `uv`

| OS | Command |
|----|--------|
| Windows | `winget install astral-sh.uv` |
| Fedora/RHEL | `dnf install uv` |
| macOS (Homebrew) | `brew install uv` |
| Any (standalone) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### Quick Install with `uv` (Recommended)

Install the server with [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://<your-github-host>/<org>/jira-data-center-mcp-server.git
```

To install a specific release:

```bash
uv tool install git+https://<your-github-host>/<org>/jira-data-center-mcp-server.git@v0.1.0
```

This installs `jira-data-center-mcp-server` as a standalone executable with all dependencies pre-resolved. To upgrade later:

```bash
uv tool upgrade jira-data-center-mcp-server
```

For development, clone the repository and install locally:

```bash
git clone https://<your-github-host>/<org>/jira-data-center-mcp-server.git
cd jira-data-center-mcp-server
uv sync                                # install dependencies into local .venv
uv tool install --force --no-cache .   # rebuild the global executable used by MCP clients
```

After making code changes, rebuild and restart the MCP server:

```bash
uv tool install --force --no-cache .
# Then restart the MCP server from your MCP client (e.g. VS Code MCP panel)
```

> **Important:** Always use `--no-cache` when installing from a local checkout. Without it, `uv` may reuse a cached wheel from a previous build and silently skip your code changes.

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

The `preflight` composite tool reports the active profile, server info, and current user at runtime.

**Getting Your Jira PAT (Personal Access Token):**
1. Log in to your Jira Data Center instance
2. Navigate to **Profile > Personal Access Tokens** (or your admin dashboard)
3. Click **Create Token**
4. Name it "MCP Server" and copy the token value
5. **Do not commit `.env` to version control** — add it to `.gitignore` if not already present

### Manual Installation (without `uv`)

<details>
<summary>Click to expand manual setup steps</summary>

> **Note:** `uv` is strongly recommended over `pip` for significantly faster installs. See the prerequisites table above.

#### Prerequisites

- Python 3.10 or later
- Git

#### Step 1: Clone the Repository

```bash
git clone https://<your-github-host>/<org>/jira-data-center-mcp-server.git
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

### Composite tools (multi-step workflows)

- `preflight` — Session init: server info + current user + profile + link types in one call
- `create_and_enrich_issue` — Create + enrich custom fields + assign + link in one call
- `complete_stage` — Transition + attach evidence + add comment in one call
- `close_issue` — Auto-discover close transition + set resolution + comment

### Type-specific creation tools

- `create_story` — User story format with Dev Notes separation, Given/When/Then AC
- `create_epic` — Value Statement description, PI auto-calculation
- `create_task` — Objective/steps/verification structure, checklist AC
- `create_bug` — Reproduction steps, [BUG] prefix, High priority default
- `create_initiative` — Lean UX problem statement, High priority default

### Search and inspection

- `search_issues`
- `get_issue` (detail_level: summary/full/raw)
- `get_issue_editmeta`
- `validate_jql`
- `get_issue_changelog`
- `get_issue_activity`

### MCP Resources (static metadata — no tool call needed)

| Resource URI | Description |
|---|---|
| `jira://profile` | Active MCP profile and enabled groups |
| `jira://server-info` | Jira server version and configuration |
| `jira://me` | Authenticated user identity |
| `jira://projects` | All visible projects |
| `jira://priorities` | Priority values |
| `jira://fields` | All fields including custom fields |
| `jira://statuses` | Workflow statuses |
| `jira://resolutions` | Issue resolutions |
| `jira://link-types` | Issue link types (Blocks, Relates, etc.) |
| `jira://projects/{key}` | Project metadata |
| `jira://projects/{key}/issue-types` | Issue types for a project |
| `jira://projects/{key}/components` | Project components |
| `jira://projects/{key}/versions` | Project versions/releases |
| `jira://projects/{key}/create-meta` | Required fields for issue creation |

### Dynamic metadata tools

- `search_users`
- `get_my_permissions`
- `get_custom_field_options`
- `list_workflows`
- `get_version`
- `get_version_related_issues`

### Versions and releases

- `create_version`
- `update_version` (with action: release/unrelease/archive/unarchive)
- `get_or_create_version`
- `delete_version`

### Issue lifecycle and mutation

- `create_issue`
- `create_subtask`
- `list_subtasks`
- `update_issue` (unified: named params + fields_json escape hatch)
- `assign_issue`
- `unassign_issue`
- `delete_issue`

### Workflow

- `get_available_transitions`
- `transition_issue` (with optional fields, comment, resolution)

### Comments and collaboration

- `add_comment`
- `list_comments`
- `update_comment`
- `delete_comment`
- `list_watchers`
- `watch_issue`
- `unwatch_issue`

### Links, remote links, and issue properties

- `list_issue_links`
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

- `use_filter` (list, get, or run a saved filter)
- `get_project_roles` (list roles or get actors)
- `list_groups`
- `list_security_levels`
- `set_issue_security_level`

### Conservative bulk operations

- `bulk_update_issues`
- `bulk_transition_issues`
- `bulk_add_comment`

### MCP Prompts (guided workflows)

- `create-and-assign` — Guided issue creation with assignment
- `create-story` — Guided user story creation
- `create-epic` — Guided epic creation
- `create-task` — Guided task creation
- `create-bug` — Guided bug creation
- `create-initiative` — Guided initiative creation
- `close-issue` — Guided issue closure with resolution
- `triage-issue` — Guided triage (priority, assign, label, sprint)
- `release-version` — Guided version release

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
