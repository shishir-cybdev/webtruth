from mcp_servers.comparison.server import server


def main():
    """Run WebTruth Comparison MCP Server in standard I/O (stdio) mode."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
