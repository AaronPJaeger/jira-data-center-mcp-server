# Agent Instructions

## Project Overview

Python MCP server for Jira Data Center v10 via the Model Context Protocol. Uses `FastMCP` from the `mcp` package and `python-jira` for Jira REST API access.

Exposes **75 tools** (standard profile), **14 MCP Resources**, and **9 MCP Prompts**. Static metadata is served as Resources (`jira://` URIs), common multi-step workflows have composite tools that reduce round-trips, and guided workflows are available as Prompts.

- **License**: MIT
- **Dependencies**: See [pyproject.toml](pyproject.toml) — `mcp`, `jira`, `python-dotenv`
- **No test suite** — `.pytest_cache/` in `.gitignore` suggests future intent

## Setup

### Prerequisites — install `uv`

| OS | Command |
|----|---------|
| Windows | `winget install astral-sh.uv` |
| Fedora/RHEL | `dnf install uv` |
| macOS (Homebrew) | `brew install uv` |
| Any (standalone) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### Create venv and install dependencies

```powershell
uv venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate     # Linux/macOS
uv sync
```

> **Note:** Always use `uv` instead of `pip` for all package operations — it is significantly faster. Use `uv add <pkg>` to add dependencies, `uv sync` to install, and `uv run` to execute scripts.

Runtime requires `JIRA_SERVER_URL` and `JIRA_PAT` env vars (set in `.env`). Never commit secrets.

## Architecture

The server is split into focused modules under `src/jira_data_center_mcp_server/`:

| Module | Purpose | Key exports |
|---|---|---|
| [app.py](src/jira_data_center_mcp_server/app.py) | FastMCP instance | `mcp` |
| [config.py](src/jira_data_center_mcp_server/config.py) | Profile system, tool gating | `profiled_tool`, `get_profile_status_payload`, `ACTIVE_PROFILE_LABEL` |
| [client.py](src/jira_data_center_mcp_server/client.py) | Jira connection, REST wrappers, validation/normalization | `jira_client`, `JIRA_URL`, `_get`, `_post`, `_put`, `_delete`, validators |
| [resources.py](src/jira_data_center_mcp_server/resources.py) | 14 MCP Resources + Resource Templates | `jira://` URI handlers |
| [prompts.py](src/jira_data_center_mcp_server/prompts.py) | 9 MCP Prompts | Guided workflows |
| [tools_read.py](src/jira_data_center_mcp_server/tools_read.py) | Read-only tools | Search, get_issue, changelog, metadata |
| [tools_write.py](src/jira_data_center_mcp_server/tools_write.py) | Mutation tools | Issues, comments, links, attachments, worklogs, versions, admin, bulk |
| [tools_agile.py](src/jira_data_center_mcp_server/tools_agile.py) | Agile tools | Boards, sprints, ranking |
| [tools_composite.py](src/jira_data_center_mcp_server/tools_composite.py) | Composite tools | `preflight`, `create_and_enrich_issue` (deprecated), `complete_stage`, `close_issue` |
| [tools_create.py](src/jira_data_center_mcp_server/tools_create.py) | Type-specific creation tools | `create_story`, `create_epic`, `create_task`, `create_bug`, `create_initiative` |
| [server.py](src/jira_data_center_mcp_server/server.py) | Entry point | Imports all modules, defines `main()` |

**Import graph** (no circular dependencies):
```
app.py ← config.py ← tools_*.py
       ← client.py ← tools_*.py, tools_create.py, resources.py, tools_composite.py
       ← resources.py, prompts.py
                      server.py (imports everything)
```

## Key Conventions

### Profile-based tool registration

Tools use `@profiled_tool("GROUP_NAME")` instead of `@mcp.tool()`. This gates tool exposure at decoration time based on the active profile (`JIRA_MCP_PROFILE` env var). Available profiles: `readonly`, `standard` (default), `agile`, `admin`, `full`, `dangerous`.

When adding a new tool, always use `@profiled_tool("GROUP")` with the appropriate group from `ALL_TOOL_GROUPS`.

### MCP Resources vs Tools

- **Resources** (`@mcp.resource()`): Use for static/semi-static metadata the LLM reads but doesn't act on (projects, priorities, statuses, fields, etc.). Resources are not profile-gated.
- **Tools** (`@profiled_tool()`): Use for operations that require dynamic input, have side effects, or need profile gating.

### Composite tools (COMPOSITE group)

Multi-step operations combined into single tools to reduce round-trips:
- `preflight()` — session init (replaces 4 separate calls)
- `create_and_enrich_issue()` — **DEPRECATED** generic create + enrich + assign + link
- `complete_stage()` — transition + attach + comment (replaces 3-4 calls per stage)
- `close_issue()` — auto-discover close transition + resolve + comment

### Type-specific creation tools (COMPOSITE group, in tools_create.py)

Issue-type-aware creation tools that encode VALIP conventions:
- `create_story()` — user story format, Dev Notes separation, Given/When/Then AC
- `create_epic()` — Value Statement description, PI auto-calculation, no Epic Link
- `create_task()` — objective/steps/verification structure, checklist AC
- `create_bug()` — reproduction steps, [BUG] prefix, High priority default
- `create_initiative()` — Lean UX problem statement, no Epic Link, High priority default

Prefer these over `create_issue` or `create_and_enrich_issue` for standard VALIP work.

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
npx @modelcontextprotocol/inspector python -m jira_data_center_mcp_server
```

## Adding a New Tool

1. **Prefer extending an existing tool** over adding a new one. Can the behavior be added as a parameter?
2. **Prefer Resources for metadata**. If the tool just GETs static data, make it a `@mcp.resource()` in `resources.py`.
3. **Prefer composite tools for multi-step workflows**. If a workflow always chains the same 3-4 calls, add it to `tools_composite.py`. For issue-type-specific creation, add to `tools_create.py`.
4. If a new tool is truly needed:
   a. Choose the correct module: `tools_read.py` (read-only), `tools_write.py` (mutations), `tools_agile.py` (agile), `tools_composite.py` (composites)
   b. Choose the correct group from `ALL_TOOL_GROUPS` in `config.py`
   c. Decorate with `@profiled_tool("GROUP_NAME")`
   d. Import utilities from `client.py` (`_validate_issue_key`, `_parse_json_object`, etc.)
   e. Wrap Jira calls in try/except, return `_json_dumps()` on success, `_error()` on failure
   f. If destructive, require `confirm=True` parameter
   g. Write a rich tool description with examples — the LLM uses this to decide when to call the tool
   g. Update the Tool Coverage section in [README.md](README.md)
