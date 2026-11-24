from datetime import datetime, timezone
import logging
from fastapi import APIRouter
from app.config import settings
from app.orchestrator.mcp_manager import mcp_manager
from app.orchestrator.schemas import MCPHealthResponse
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the current operating status, API version, and MCP integration readiness of WebTruth backend."
)
async def get_health() -> HealthResponse:
    """Check health and version metadata."""
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        mcp_status=settings.MCP_INTEGRATION_STATUS,
    )


@router.get(
    "/mcp",
    response_model=MCPHealthResponse,
    summary="Inspect MCP Server Ecosystem Health",
    description="Inspects real stdio connections, process availability, and discovered tool counts across all four MCP servers.",
)
async def get_mcp_health() -> MCPHealthResponse:
    """Audit health and discovered tools for browser, evidence, comparison, and trust MCP servers."""
    logger.info("Performing live health inspection across all four MCP servers")
    return await mcp_manager.check_all_health()
