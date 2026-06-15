---
name: jira-mcp-setup
description: Interactive guided setup for the Jira Data Center v10 MCP server. Walks users through prerequisites, installation, and configuration.
triggers:
  - setup jira mcp server
  - install jira datacenter mcp
  - configure jira server
  - jira mcp setup
  - help me set up jira mcp
applyTo:
  - .
---

# Jira Data Center MCP Server Setup Skill

## Workflow

This skill guides users through the complete setup process step-by-step, using the built-in VSCode terminal and Copilot Chat for verification and error handling.

### Phase 1: Prerequisites Check

1. **Verify system requirements**
  - Detect OS (Windows/macOS/Linux)
  - Check if Python 3.14+ is installed: `python --version`
  - Check if Git is installed: `git --version`
  - Check if Node.js is installed (optional): `node --version`

2. **If missing, install prerequisites**
  - For Windows users: Copy-paste package manager commands for `winget`
  - For macOS/Linux users: Copy-paste `brew` commands
  - Verify each installation after completion

### Phase 2: Clone Repository

1. **Prompt for workspace location**
  - Ask where user wants to clone (default: home directory)
  - Provide copy-paste git clone command
  - Confirm successful clone

### Phase 3: Virtual Environment Setup

1. **Create Python virtual environment**
  - Windows: `.\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `source .venv/bin/activate`
  - Verify activation by checking terminal prompt

### Phase 4: Install Dependencies

1. **Run pip install**
  - Execute: `pip install -r requirements.txt`
  - Monitor output for any errors
  - Verify all three packages installed: `mcp`, `jira`, `python-dotenv`

### Phase 5: Environment Configuration

1. **Create .env file**
  - Windows: `Copy-Item ".env.example" ".env"`
  - macOS/Linux: `cp .env.example .env`
  - Guide user to edit `.env` with Jira credentials

2. **Collect Jira credentials**
  - Ask for Jira server URL
  - **IMPORTANT:** Never use `vscode_askQuestions` for PAT token
  - Instruct user to obtain PAT from Jira instance
  - Tell user to paste token directly into terminal/editor (hidden input)

3. **Verify .env structure**
  - Check that `.env` contains:
    - `JIRA_SERVER_URL`
    - `JIRA_PAT`
    - `LOG_LEVEL=INFO`
    - `JIRA_MCP_PROFILE=standard`

### Phase 6: Verification

1. **Test MCP server**
  - Run: `python jira_server.py`
  - Monitor output for: `[INFO] Jira Data Center MCP Server initialized`
  - Check for profile and enabled groups confirmation
  - Stop with `Ctrl+C`

2. **Optional: MCP Inspector smoke test**
  - If Node.js is installed, offer to run inspector
  - Command: `npx @modelcontextprotocol/inspector python jira_server.py`
  - Explain browser-based tool testing interface

## Error Handling

### Common Issues

| Issue | Detection | Solution |
|-------|-----------|----------|
| Python not in PATH | `command not found: python` | Reinstall Python and ensure "Add to PATH" is checked, or use full path |
| Git not installed | `git clone` fails | Run winget/brew install Git.Git, verify `git --version` |
| Jira connection fails (401) | `JIRAError: (401) Unauthorized` | Verify PAT token is valid and hasn't expired |
| Jira connection fails (404) | `JIRAError: (404) Not Found` | Double-check `JIRA_SERVER_URL` in `.env` |
| .env not loading | Server ignores credentials | Restart server, verify `.env` is in project root |

## Tips for Users

1. **Copy-paste commands** — All commands are designed to be copy-pasted into the terminal
2. **Virtual environment** — Always activate before running server or installing packages
3. **Credentials** — Never commit `.env` or PAT tokens to version control
4. **Multiple profiles** — Use different config entries in `claude_desktop_config.json` for different tool sets (readonly, agile, admin)
5. **Smoke testing** — Use MCP Inspector to verify tools before integrating with Claude Desktop

## Success Criteria

User has successfully completed setup when:
- [ ] All prerequisites installed and verified
- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] `.env` file configured with valid Jira credentials
- [ ] `python jira_server.py` starts without errors and shows initialization message

## Next Steps After Setup

Once setup is complete, the MCP server is ready for integration with any MCP-compatible client:
- Use with VS Code Copilot Chat
- Integrate with Claude Desktop or other MCP clients
- Embed in custom applications via the MCP protocol

Example usage queries:
- "Search for issues assigned to me"
- "Get details on VALIP-5370"
- "Create a new story for..."
- "Move this issue to Done"
- "Show my recent activity"

For more information, see the main [README.md](../../README.md).
