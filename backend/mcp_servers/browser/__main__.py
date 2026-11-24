import asyncio
import sys
from mcp_servers.browser.server import server
from mcp_servers.browser.browser_manager import browser_manager


def main():
    """Run WebTruth Browser MCP Server in standard I/O mode."""
    try:
        server.run(transport="stdio")
    finally:
        # Ensure browser is cleaned up when server shuts down
        try:
            asyncio.run(browser_manager.close())
        except Exception:
            pass


if __name__ == "__main__":
    main()
