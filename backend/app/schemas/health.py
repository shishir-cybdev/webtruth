from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for GET /api/health response."""

    status: str = Field(default="healthy", description="Current service health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the health check")
    mcp_status: str = Field(..., description="Status of the MCP intelligence server integrations")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "app_name": "WebTruth API",
                "version": "0.2.0-phase2a",
                "environment": "development",
                "timestamp": "2026-11-24T15:00:00Z",
                "mcp_status": "Phase 2B - Pending Integration",
            }
        }
    }
