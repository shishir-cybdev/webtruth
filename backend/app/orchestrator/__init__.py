"""WebTruth MCP Orchestration Layer (Phase 2F).

Connects and orchestrates Browser, Evidence, Comparison, and Trust MCP servers
over real stdio subprocesses using the official Python MCP client SDK.
"""

from app.orchestrator.errors import (
    InvestigationNotFoundError,
    MCPServerConnectionError,
    MCPTimeoutError,
    MCPToolExecutionError,
    StageExecutionError,
)
from app.orchestrator.investigation_engine import (
    InvestigationEngine,
    default_investigation_engine,
)
from app.orchestrator.investigation_state import (
    InvestigationStateStore,
    default_state_store,
)
from app.orchestrator.mcp_manager import MCPManager, mcp_manager
from app.orchestrator.schemas import (
    InvestigationEvent,
    InvestigationRecord,
    InvestigationStage,
    MCPHealthResponse,
    ServerHealthInfo,
    ServerStatus,
    StageRecord,
    StageStatus,
    ToolCallLog,
)
from app.orchestrator.server_registry import ServerDefinition, ServerRegistry, registry

__all__ = [
    "MCPManager",
    "mcp_manager",
    "ServerRegistry",
    "registry",
    "ServerDefinition",
    "InvestigationEngine",
    "default_investigation_engine",
    "InvestigationStateStore",
    "default_state_store",
    "InvestigationRecord",
    "InvestigationEvent",
    "InvestigationStage",
    "StageRecord",
    "StageStatus",
    "ToolCallLog",
    "MCPHealthResponse",
    "ServerHealthInfo",
    "ServerStatus",
    "MCPServerConnectionError",
    "MCPToolExecutionError",
    "MCPTimeoutError",
    "InvestigationNotFoundError",
    "StageExecutionError",
]
