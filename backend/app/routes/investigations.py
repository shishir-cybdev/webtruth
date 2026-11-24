import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationListResponse,
    InvestigationResponse,
)
from app.services.investigation_service import (
    InvestigationNotFoundError,
    InvestigationServiceInterface,
    get_investigation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Product Investigation",
    description=(
        "Initialize an investigation for a product query, category, and optional budget in INR. "
        "In Phase 2A, this registers a placeholder workflow showing how multi-agent MCP execution "
        "will run in Phase 2B."
    ),
)
async def create_investigation(
    payload: InvestigationCreateRequest,
    service: InvestigationServiceInterface = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Submit a product research query to start an investigation."""
    logger.info("Received investigation creation request: query='%s', category=%s", payload.query, payload.category)
    try:
        response = await service.create_investigation(payload)
        return response
    except Exception as e:
        logger.error("Failed to create investigation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the investigation."
        )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Get Investigation Status",
    description="Retrieve the current status, pipeline stages, and findings for an investigation by ID.",
)
async def get_investigation(
    investigation_id: str,
    service: InvestigationServiceInterface = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Fetch status and steps for an investigation."""
    logger.info("Fetching investigation id=%s", investigation_id)
    investigation = await service.get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found."
        )
    return investigation


@router.get(
    "",
    response_model=InvestigationListResponse,
    summary="List Recent Investigations",
    description="Retrieve a paginated list of recently created investigations.",
)
async def list_investigations(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    service: InvestigationServiceInterface = Depends(get_investigation_service),
) -> InvestigationListResponse:
    """List investigations with pagination."""
    return await service.list_investigations(limit=limit, offset=offset)
