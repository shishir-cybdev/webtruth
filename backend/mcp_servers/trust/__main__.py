from mcp_servers.trust.server import server


def main():
    """Run WebTruth Trust MCP Server in standard I/O (stdio) mode."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
