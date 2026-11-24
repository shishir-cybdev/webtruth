from mcp_servers.evidence.server import server


def main():
    """Run WebTruth Evidence MCP Server in standard I/O (stdio) mode."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
