"""WebTruth Trust MCP Server (Phase 2E).

Provides evidence quality assessment, source freshness evaluation, unsupported claim detection,
multi-source consistency auditing, and explainable trust assessment without arbitrary scores.
"""

from mcp_servers.trust.server import server

__all__ = ["server"]
