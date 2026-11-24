import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from mcp.client.stdio import StdioServerParameters

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class ServerDefinition(BaseModel):
    """Configuration definition for an independent stdio MCP server."""
    name: str = Field(..., description="Internal registry key (e.g. 'browser')")
    display_name: str = Field(..., description="Human-readable server title")
    module_name: str = Field(..., description="Python module executed with -m")
    description: str = Field(..., description="Functional purpose of the server")
    timeout_seconds: float = Field(default=30.0, description="Default command timeout in seconds")
    env: Dict[str, str] = Field(default_factory=dict, description="Custom environment variables")

    def build_stdio_parameters(self) -> StdioServerParameters:
        """Create StdioServerParameters using current Python interpreter and backend working dir."""
        merged_env = os.environ.copy()
        merged_env.update(self.env)
        # Ensure backend directory is in PYTHONPATH so module imports resolve cleanly
        existing_py_path = merged_env.get("PYTHONPATH", "")
        backend_str = str(BACKEND_DIR)
        if backend_str not in existing_py_path:
            merged_env["PYTHONPATH"] = f"{backend_str}{os.pathsep}{existing_py_path}" if existing_py_path else backend_str

        return StdioServerParameters(
            command=sys.executable,
            args=["-m", self.module_name],
            env=merged_env,
            cwd=str(BACKEND_DIR),
        )


class ServerRegistry:
    """Registry managing the four official WebTruth MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, ServerDefinition] = {}
        self._register_default_servers()

    def _register_default_servers(self) -> None:
        """Register the 4 official WebTruth MCP servers."""
        self.register(
            ServerDefinition(
                name="browser",
                display_name="Browser MCP Server",
                module_name="mcp_servers.browser",
                description="Inspects public product pages, extracts structured data, and captures DOM evidence.",
                timeout_seconds=45.0,  # Browser launches may need slightly higher headroom on Windows
            )
        )
        self.register(
            ServerDefinition(
                name="evidence",
                display_name="Evidence MCP Server",
                module_name="mcp_servers.evidence",
                description="Persists immutable evidence records in SQLite with SHA-256 integrity verification.",
                timeout_seconds=30.0,
            )
        )
        self.register(
            ServerDefinition(
                name="comparison",
                display_name="Comparison MCP Server",
                module_name="mcp_servers.comparison",
                description="Deterministic specification normalization, price comparisons, and conflict detection.",
                timeout_seconds=30.0,
            )
        )
        self.register(
            ServerDefinition(
                name="trust",
                display_name="Trust MCP Server",
                module_name="mcp_servers.trust",
                description="Evaluates evidence quality, freshness, consistency, unsupported claims, and generates trust reports.",
                timeout_seconds=30.0,
            )
        )

    def register(self, definition: ServerDefinition) -> None:
        """Register a server definition."""
        self._servers[definition.name] = definition

    def get(self, name: str) -> Optional[ServerDefinition]:
        """Retrieve a registered server definition by name."""
        return self._servers.get(name)

    def list_servers(self) -> List[ServerDefinition]:
        """Return all registered server definitions."""
        return list(self._servers.values())


registry = ServerRegistry()
