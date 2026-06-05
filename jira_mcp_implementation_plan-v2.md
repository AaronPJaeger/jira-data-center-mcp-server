# Jira Data Center v10 MCP Server Implementation Plan v2

## 1. Exact Dependency Manifest

```text
mcp>=0.1.0
jira>=3.8.0
python-dotenv>=1.0.1
```

## 2. Server Architecture and Initialization

The server initializes a FastMCP application, loads environment variables from `.env`, authenticates to Jira Data Center using a Personal Access Token, and preserves stdout exclusively for MCP stdio JSON-RPC framing while sending logs to stderr.

Required environment variables:

- `JIRA_SERVER_URL`
- `JIRA_PAT`

Optional environment variable:

- `LOG_LEVEL`

## 3. Core Tooling

### 3.1 Search and Discovery

`search_issues(jql_query: str, max_results: int = 50) -> str`

Queries Jira with JQL and returns a Markdown table containing issue key, summary, status, assignee, and priority.

### 3.2 Deep Read Operations

`get_issue_details(issue_key: str) -> str`

Retrieves a structured JSON payload with issue metadata, description, timestamps, user mappings, and comments.

### 3.3 Mutation Operations

`create_issue(project_key: str, summary: str, description: str, issue_type: str = "Story", priority: Optional[str] = None) -> str`

Creates a new issue in Jira Data Center.

`update_issue_fields(issue_key: str, summary: Optional[str] = None, description: Optional[str] = None, assignee_username: Optional[str] = None) -> str`

Updates selected issue fields only when supplied.

### 3.4 Workflow Transition Engine

`transition_issue(issue_key: str, transition_name_or_id: str) -> str`

Inspects available Jira transitions for the issue's current state, resolves a requested transition by case-insensitive name or numeric ID, and executes the transition. If the transition is unavailable, it returns the valid transition options.

### 3.5 Collaboration Engine

`add_comment(issue_key: str, body: str) -> str`

Adds a comment to the target issue.

### 3.6 Identity Search

`search_users(query: str) -> str`

Searches Jira users and returns display names, usernames or keys, and active state.

## 4. Deployment Steps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, then launch the inspector:

```bash
npx @modelcontextprotocol/inspector python /absolute/path/to/jira_server.py
```

## 5. Client Configuration

Use `claude_desktop_config.example.json` as the client configuration template.

## 6. Version 2 Additions

- Added `transition_issue` for Kanban/Scrum workflow state movement.
- Added workflow graph fallback output listing valid transition names and IDs.
- Preserved stdout for MCP protocol framing.
- Added defensive input validation for issue keys, JQL, empty mutation payloads, and max-results bounds.
- Added `.env.example`, `.gitignore`, config template, and operational README.
