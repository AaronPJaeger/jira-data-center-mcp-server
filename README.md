# Jira Data Center v10 MCP Server

Enterprise-grade Model Context Protocol (MCP) server for Jira Data Center v10. This server exposes Jira search, issue inspection, issue creation, field updates, workflow transitions, comments, and user lookup to MCP-compatible clients such as Claude Desktop.

## Capabilities

| Tool | Purpose |
| :--- | :--- |
| `search_issues` | Query Jira with JQL and return a Markdown results table. |
| `get_issue_details` | Retrieve structured issue metadata, description, assignee, timestamps, and comments. |
| `create_issue` | Create Story, Bug, Task, Epic, or other configured Jira issue types. |
| `update_issue_fields` | Update issue summary, description, or assignee username. |
| `transition_issue` | Move an issue through a valid workflow transition by name or transition ID. |
| `add_comment` | Add a comment to an issue. |
| `search_users` | Search Jira users for assignment or identity mapping. |

## Requirements

- Python 3.10+
- Jira Data Center v10
- Jira Personal Access Token (PAT)
- MCP-compatible client

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

## Environment Configuration

Copy the sample environment file:

```bash
cp .env.example .env
```

Then edit `.env`:

```dotenv
JIRA_SERVER_URL=https://your-enterprise-jira-datacenter.com
JIRA_PAT=your_secure_personal_access_token_string_here
LOG_LEVEL=INFO
```

Do not commit `.env` or any Jira PAT.

## Local Smoke Test

Validate the MCP runtime with the official inspector:

```bash
npx @modelcontextprotocol/inspector python /absolute/path/to/jira-data-center-mcp-server/jira_server.py
```

You can also run the server directly:

```bash
python jira_server.py
```

The process communicates over stdio. Logs are written to stderr so stdout remains reserved for MCP JSON-RPC framing.

## Claude Desktop Configuration

Use the included `claude_desktop_config.example.json` as a template:

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

## Example Tool Prompts

- "Search Jira for `project = DEVOPS AND status = \"To Do\" ORDER BY updated DESC`."
- "Get details for `OPS-431` before updating it."
- "Create a High priority Bug in project API for the OAuth callback failure."
- "Move `PROJ-123` to In Progress."
- "Add a comment to `OPS-431` with the deployment status."
- "Search Jira users for `asmith`."

## Security Notes

- Use a service account or PAT scoped to the minimum Jira permissions needed.
- Keep `.env` out of source control.
- Keep MCP logs on stderr only; stdout must remain clean for JSON-RPC framing.
- Prefer read-only Jira permissions unless mutation tools are required.

## Project Structure

```text
.
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── claude_desktop_config.example.json
├── jira_mcp_implementation_plan-v2.md
├── jira_server.py
└── requirements.txt
```

## Operational Notes

`transition_issue` resolves valid transitions dynamically from the current workflow state. If the requested transition is not currently reachable, it returns the valid transition names and IDs so the agent can retry without stalling.
