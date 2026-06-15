"""FastMCP application instance — imported by all other modules."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Jira-Data-Center-v10",
    instructions=(
        "Task-oriented MCP server for Jira Data Center v10. Exposes consolidated tools for "
        "issue management, workflow transitions, and agile operations. Static metadata is "
        "available as MCP Resources (jira:// URIs). Common multi-step workflows have dedicated "
        "composite tools that reduce round-trips."
    ),
)
