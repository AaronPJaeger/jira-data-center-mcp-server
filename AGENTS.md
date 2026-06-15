# Agent Instructions

## Project Overview

Single-file Python MCP server (`jira_server.py`, ~2020 lines) exposing 88 tools for Jira Data Center v10 via the Model Context Protocol. Uses `FastMCP` from the `mcp` package and `python-jira` for Jira REST API access.

- **License**: MIT
- **Dependencies**: See [requirements.txt](requirements.txt) — `mcp`, `jira`, `python-dotenv`
- **No test suite** — `.pytest_cache/` in `.gitignore` suggests future intent

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Runtime requires `JIRA_SERVER_URL` and `JIRA_PAT` env vars (set in `.env`). Never commit secrets.

## Architecture

Everything lives in [jira_server.py](jira_server.py). Key sections in order:

1. **Imports, logging, FastMCP init** — logging routes to stderr (stdout reserved for MCP JSON-RPC)
2. **Profile system** (~lines 35–165) — tool groups, profile definitions, `@profiled_tool` decorator
3. **Jira connection & utilities** (~lines 170–370) — validation, normalization, REST wrappers, JSON helpers
4. **Tool functions** (~lines 375–2020) — grouped by domain (search, metadata, versions/releases, mutation, workflow, comments, links, attachments, worklogs, agile, admin, bulk)
5. **Entry point** — `mcp.run()` at bottom

## Key Conventions

### Profile-based tool registration

Tools use `@profiled_tool("GROUP_NAME")` instead of `@mcp.tool()`. This gates tool exposure at decoration time based on the active profile (`JIRA_MCP_PROFILE` env var). Available profiles: `readonly`, `standard` (default), `agile`, `admin`, `full`, `dangerous`.

When adding a new tool, always use `@profiled_tool("GROUP")` with the appropriate group from `ALL_TOOL_GROUPS`.

### Destructive operation confirmation

All destructive tools (delete_*, bulk_*) require a `confirm: bool = False` parameter. The tool must refuse to act unless `confirm=True`. This is a safety gate, not optional.

### Validation pattern

Use `_validate_issue_key()` / `_validate_issue_keys()` before any Jira API call that takes issue keys. Normalize with `_normalize_issue_key()`.

### Error handling

Wrap Jira API calls in try/except, catching `JIRAError` and returning `_error(str(e))`. Never let exceptions propagate to MCP clients unhandled.

### Direct REST fallback

When python-jira doesn't expose an endpoint, use the thin wrappers `_get()`, `_post()`, `_put()`, `_delete()` which hit `jira_client._session` directly.

### JSON output

All tool return values go through `_json_dumps()` for consistent formatting.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `JIRA_SERVER_URL` | Jira Data Center base URL | (required) |
| `JIRA_PAT` | Personal Access Token | (required) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `JIRA_MCP_PROFILE` | Active tool profile | `standard` |
| `JIRA_MCP_ENABLED_GROUPS` | Override profile with explicit groups (comma-separated) | (none) |

## Smoke Test

```bash
npx @modelcontextprotocol/inspector python jira_server.py
```

## Adding a New Tool

1. Choose the correct group from `ALL_TOOL_GROUPS`
2. Decorate with `@profiled_tool("GROUP_NAME")`
3. Add input validation (`_validate_issue_key`, `_parse_json_object`, etc.)
4. Wrap Jira calls in try/except, return `_json_dumps()` on success, `_error()` on failure
5. If destructive, require `confirm=True` parameter
6. Update the Tool Coverage section in [README.md](README.md)
