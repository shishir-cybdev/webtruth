from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def current_utc_iso() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class ServerStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ServerHealthInfo(BaseModel):
    """Health and status of an individual stdio MCP server."""
    server_name: str = Field(..., description="Unique registered server name (e.g. 'browser', 'evidence')")
    module_name: str = Field(..., description="Underlying Python module path (e.g. 'mcp_servers.browser')")
    status: ServerStatus = Field(..., description="'connected', 'disconnected', or 'error'")
    discovered_tools: List[str] = Field(default_factory=list, description="List of tools exposed by server")
    tool_count: int = Field(default=0, description="Total tools discovered")
    latency_ms: Optional[float] = Field(default=None, description="Time taken to connect and list tools in ms")
    error: Optional[str] = Field(default=None, description="Error message if server failed")
    checked_at_utc: str = Field(default_factory=current_utc_iso)


class MCPHealthResponse(BaseModel):
    """Overall MCP ecosystem health across all four registered servers."""
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    total_tools_count: int = Field(..., description="Total tools discovered across all servers")
    servers: Dict[str, ServerHealthInfo] = Field(default_factory=dict, description="Status keyed by server name")
    checked_at_utc: str = Field(default_factory=current_utc_iso)


class ToolCallLog(BaseModel):
    """Structured audit log for an individual MCP tool execution."""
    call_id: str = Field(..., description="Unique call identifier")
    server_name: str = Field(..., description="Target MCP server")
    tool_name: str = Field(..., description="Invoked tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to tool")
    status: str = Field(..., description="'success' or 'failed'")
    execution_time_ms: float = Field(..., description="Duration in milliseconds")
    timestamp_utc: str = Field(default_factory=current_utc_iso)
    error: Optional[str] = Field(default=None, description="Error message if call failed")


class InvestigationStage(str, Enum):
    PLAN = "plan"
    BROWSER = "browser"
    EVIDENCE = "evidence"
    COMPARISON = "comparison"
    TRUST = "trust"
    RESULT = "result"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageRecord(BaseModel):
    """Status and logs for an individual pipeline stage."""
    stage: InvestigationStage = Field(..., description="Stage enum")
    label: str = Field(..., description="Display label (e.g. 'STAGE 2 — BROWSER MCP')")
    mcp_server: Optional[str] = Field(default=None, description="Associated MCP server")
    status: StageStatus = Field(default=StageStatus.PENDING)
    started_at_utc: Optional[str] = Field(default=None)
    completed_at_utc: Optional[str] = Field(default=None)
    message: Optional[str] = Field(default=None, description="Current progress or outcome statement")
    tool_logs: List[ToolCallLog] = Field(default_factory=list, description="Tool execution logs for this stage")


class InvestigationRecord(BaseModel):
    """Complete persistent state record for an investigation."""
    investigation_id: str = Field(..., description="Unique investigation identifier ('inv_...')")
    query: str = Field(..., description="Product search query")
    category: Optional[str] = Field(default=None)
    budget_inr: Optional[float] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    status: str = Field(default="pending", description="'pending', 'processing', 'completed', 'failed'")
    current_stage: InvestigationStage = Field(default=InvestigationStage.PLAN)
    created_at_utc: str = Field(default_factory=current_utc_iso)
    updated_at_utc: str = Field(default_factory=current_utc_iso)
    completed_at_utc: Optional[str] = Field(default=None)

    # Detailed stage tracking
    stages: Dict[str, StageRecord] = Field(default_factory=dict)
    
    # Accumulated intermediate outputs across stages
    plan_data: Optional[Dict[str, Any]] = Field(default=None)
    target_urls: List[str] = Field(default_factory=list)
    extracted_records: List[Dict[str, Any]] = Field(default_factory=list)
    related_variants: List[Dict[str, Any]] = Field(default_factory=list)
    rejected_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    comparison_result: Optional[Dict[str, Any]] = Field(default=None)
    trust_report: Optional[Dict[str, Any]] = Field(default=None)
    
    # Audit & diagnostics
    all_tool_logs: List[ToolCallLog] = Field(default_factory=list)
    unknown_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    summary: Optional[str] = Field(default=None)


class InvestigationEvent(BaseModel):
    """Server-Sent Event (SSE) message payload for real-time frontend streaming."""
    event_type: str = Field(..., description="'stage_started', 'stage_completed', 'log', 'completed', 'error'")
    investigation_id: str = Field(...)
    stage: str = Field(...)
    status: str = Field(...)
    message: str = Field(...)
    timestamp_utc: str = Field(default_factory=current_utc_iso)
    data: Optional[Dict[str, Any]] = Field(default=None)
