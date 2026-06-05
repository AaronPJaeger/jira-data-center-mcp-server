# Jira Data Center v10 MCP Server Implementation Plan v3

## Scope

Version 3 expands the server from basic Jira issue operations into an agent-ready Jira Data Center MCP surface.

## Capability Groups

### Search and inspection

- `search_issues`
- `validate_jql`
- `get_issue_details`

### Metadata and schema discovery

- `list_projects`
- `get_project_metadata`
- `get_create_issue_metadata`
- `list_issue_types`
- `list_priorities`
- `list_fields`
- `list_components`
- `list_versions`

### Creation and field mutation

- `create_issue`
- `update_issue`
- `update_issue_structured`
- `update_issue_fields`

### Workflow

- `get_available_transitions`
- `transition_issue`

### Collaboration and assignment

- `add_comment`
- `assign_issue`
- `unassign_issue`
- `watch_issue`
- `unwatch_issue`
- `list_watchers`
- `search_users`

### Links and dependencies

- `list_issue_links`
- `list_issue_link_types`
- `create_issue_link`
- `delete_issue_link`

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

### Agile / Jira Software

- `list_boards`
- `get_board_configuration`
- `list_sprints`
- `get_sprint`
- `list_sprint_issues`
- `move_issues_to_sprint`
- `move_issues_to_backlog`
- `rank_issue`

### Identity, permissions, and server info

- `get_myself`
- `get_my_permissions`
- `get_server_info`

### Conservative bulk operations

- `bulk_update_issues`
- `bulk_transition_issues`
- `bulk_add_comment`

## Safety and reliability constraints

- Bulk operations require explicit issue keys.
- Bulk operations are capped by `JIRA_MCP_BULK_MAX_ISSUES`, defaulting to 50.
- Search results are capped by `JIRA_MCP_ABSOLUTE_MAX_RESULTS`, defaulting to 100.
- Custom field mutation requires explicit field IDs supplied by the caller after using `list_fields` or `get_create_issue_metadata`.
- Logs remain on stderr; stdout remains reserved for MCP JSON-RPC framing.

## Runtime environment

Required:

```dotenv
JIRA_SERVER_URL=https://your-enterprise-jira-datacenter.com
JIRA_PAT=your_secure_personal_access_token_string_here
```

Optional:

```dotenv
LOG_LEVEL=INFO
JIRA_MCP_DEFAULT_MAX_RESULTS=50
JIRA_MCP_ABSOLUTE_MAX_RESULTS=100
JIRA_MCP_BULK_MAX_ISSUES=50
```
