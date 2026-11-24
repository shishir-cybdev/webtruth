"""Exceptions for WebTruth MCP Orchestration Layer (Phase 2F)."""


class MCPOrchestrationError(Exception):
    """Base exception for all MCP orchestration errors."""
    pass


class MCPServerConnectionError(MCPOrchestrationError):
    """Raised when an MCP server subprocess cannot be launched or fails initialization."""
    pass


class MCPToolExecutionError(MCPOrchestrationError):
    """Raised when an MCP tool invocation fails or returns an error result."""
    pass


class MCPTimeoutError(MCPOrchestrationError):
    """Raised when an MCP connection or tool execution exceeds its timeout limit."""
    pass


class InvestigationNotFoundError(MCPOrchestrationError):
    """Raised when a requested investigation ID is not found in the state store."""
    pass


class StageExecutionError(MCPOrchestrationError):
    """Raised when a specific pipeline stage encounters an unrecoverable failure."""
    def __init__(self, stage: str, message: str, details: dict | None = None) -> None:
        super().__init__(f"Stage '{stage}' failed: {message}")
        self.stage = stage
        self.message = message
        self.details = details or {}
