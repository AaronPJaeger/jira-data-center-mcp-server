"""Jira Data Center v10 MCP Server — entry point.

Importing this module triggers tool/resource/prompt registration via side effects
in each submodule. The ``main()`` function starts the MCP stdio transport.
"""

import logging
import os

# Configure logging before any other imports (stdout reserved for MCP JSON-RPC).
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from .app import mcp  # noqa: F401 — FastMCP instance
from .config import ACTIVE_PROFILE_LABEL  # noqa: F401

# Side-effect imports: each module registers its tools/resources/prompts on import.
from . import resources  # noqa: F401
from . import prompts  # noqa: F401
from . import tools_read  # noqa: F401
from . import tools_write  # noqa: F401
from . import tools_agile  # noqa: F401
from . import tools_composite  # noqa: F401
from . import tools_create  # noqa: F401

logger = logging.getLogger("jira_mcp_server")


def main():
    """Entry point for the console script and ``python -m`` invocation."""
    logger.info("Initializing Jira MCP server stdio runtime with profile %s.", ACTIVE_PROFILE_LABEL)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
