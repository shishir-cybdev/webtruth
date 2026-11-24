from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class InvestigationStatus(str, Enum):
    """Investigation execution lifecycle status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Status of an individual pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class InvestigationCreateRequest(BaseModel):
    """Schema for POST /api/investigations request body."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Product name, model number, or search query to investigate",
        examples=["Dell XPS 15 9530", "Sony WH-1000XM5", "MacBook Pro 14 M3"]
    )
    category: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional product category (e.g. laptop, smartphone, audio)",
        examples=["laptop"]
    )
    budget_inr: Optional[float] = Field(
        default=None,
        gt=0,
        le=5000000,
        description="Optional maximum budget in Indian Rupees (INR)",
        examples=[150000.0]
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional user criteria or key features to prioritize"
    )
    mode: Optional[str] = Field(
        default=None,
        description="'real' for multi-agent MCP orchestration, 'demo' for placeholder",
    )
    target_urls: Optional[List[str]] = Field(
        default=None,
        description="Explicit target URLs for investigation",
    )

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty or whitespace only")
        return cleaned

    @field_validator("category")
    @classmethod
    def clean_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip().lower()
        return cleaned if cleaned else None


class InvestigationStepInfo(BaseModel):
    """Schema for individual MCP pipeline step status."""

    step_id: str = Field(..., description="Unique step identifier")
    label: str = Field(..., description="Human-readable step name")
    mcp_server: str = Field(..., description="Associated planned MCP server")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Execution status")
    description: str = Field(..., description="Purpose of this pipeline step")
    message: Optional[str] = Field(default=None, description="Current step log or status output")


class InvestigationResponse(BaseModel):
    """Schema for investigation details response."""

    id: str = Field(..., description="Unique investigation identifier (inv_...)")
    query: str = Field(..., description="Investigated product search query")
    category: Optional[str] = Field(default=None, description="Product category")
    budget_inr: Optional[float] = Field(default=None, description="User budget in INR")
    status: InvestigationStatus = Field(..., description="Current status of the investigation")
    created_at: datetime = Field(..., description="Creation timestamp in UTC")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC")
    
    # Transparency & Phase 2A demo demarcation
    is_placeholder: bool = Field(
        default=True,
        description="Always True in Phase 2A. No live web scrapers or MCP tools are executed."
    )
    disclaimer: str = Field(
        default=(
            "PHASE 2A DEMO MODE: This investigation was processed by the Phase 2A placeholder "
            "service. No live e-commerce prices, external reviews, or seller data were scraped. "
            "Real multi-source MCP intelligence agent integrations begin in Phase 2B."
        ),
        description="Honest statement of prototype limitations"
    )

    pipeline_steps: List[InvestigationStepInfo] = Field(
        default_factory=list,
        description="Simulated MCP server pipeline stages and status"
    )
    summary: Optional[str] = Field(
        default=None,
        description="High-level placeholder summary of findings"
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Persisted Evidence record IDs",
    )
    comparison_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Synthesized comparison output across retailers",
    )
    trust_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured trust and integrity assessment report",
    )
    target_urls: List[str] = Field(
        default_factory=list,
        description="URLs analyzed during the investigation",
    )
    tool_logs_count: int = Field(
        default=0,
        description="Count of MCP tool executions across all servers",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings or rejected source reasons recorded during investigation",
    )
    failures: List[str] = Field(
        default_factory=list,
        description="Failures recorded during investigation",
    )
    related_variants: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Related product variants separated from exact-match comparison (e.g. OnePlus 13S)",
    )
    rejected_candidates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rejected non-matching candidates (accessories, brand/model mismatches, 404s, CAPTCHAs)",
    )


class InvestigationListResponse(BaseModel):
    """Schema for listing recent investigations."""

    total: int = Field(..., description="Total number of stored investigations")
    items: List[InvestigationResponse] = Field(..., description="List of investigations")
