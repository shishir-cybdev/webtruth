"""WebTruth Persistent Evidence MCP Server (Phase 2C).

Provides tamper-evident, SHA-256 verified, SQLite-backed persistence for
investigation evidence records, product price histories, and duplicate detection.
"""

from mcp_servers.evidence.server import server

__all__ = ["server"]
