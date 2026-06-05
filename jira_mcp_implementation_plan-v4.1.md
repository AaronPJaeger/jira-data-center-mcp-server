# Jira Data Center v10 MCP Server Implementation Plan v4.1

## Purpose

Version 4 adds the final agent-completeness layer on top of the v3 Jira MCP server.

## Added in v4

- Changelog and compact issue activity tools
- Comment CRUD
- Remote web links
- Issue properties
- Subtask creation and listing
- Transition-with-fields support for workflows requiring resolution/comment/custom fields
- Status, resolution, and workflow/status metadata
- Saved filter listing, reading, and execution
- Project roles and role actors
- Group search/listing
- Issue security scheme/level read and issue security update
- Guarded issue deletion

## Tool Count

The v4 `jira_server.py` exposes 69 MCP tools.

## Guardrails

Destructive and broad operations require explicit `confirm=True`.

## Runtime

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
npx @modelcontextprotocol/inspector python /absolute/path/to/jira_server.py
```


## v4.1 Addition

- Added `get_custom_field_options(field_id, context_id=None)` for custom select-list/option field discovery.
