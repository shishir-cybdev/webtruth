import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.orchestrator.investigation_engine import default_investigation_engine
from app.orchestrator.investigation_state import default_state_store
from app.orchestrator.schemas import (
    InvestigationEvent,
    InvestigationRecord,
    StageStatus,
)
from app.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationListResponse,
    InvestigationResponse,
    InvestigationStatus,
    InvestigationStepInfo,
    StepStatus,
)
from app.services.investigation_service import (
    InvestigationServiceInterface,
    get_investigation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])


def map_record_to_response(rec: InvestigationRecord) -> InvestigationResponse:
    """Convert an internal InvestigationRecord into the public API response schema."""
    status_map = {
        StageStatus.PENDING: StepStatus.PENDING,
        StageStatus.RUNNING: StepStatus.RUNNING,
        StageStatus.COMPLETED: StepStatus.COMPLETED,
        StageStatus.FAILED: StepStatus.FAILED,
        StageStatus.SKIPPED: StepStatus.SKIPPED,
    }

    ordered_stages = [
        ("plan", "Query Understanding & Plan", "Orchestrator"),
        ("browser", "Browser MCP Ingestion", "Browser MCP"),
        ("evidence", "Evidence Vault Persistence", "Evidence MCP"),
        ("comparison", "Comparison & Conflict Engine", "Comparison MCP"),
        ("trust", "Trust & Integrity Verification", "Trust MCP"),
        ("result", "Report Synthesis", "Orchestrator"),
    ]

    steps: List[InvestigationStepInfo] = []
    for key, default_label, default_server in ordered_stages:
        st = rec.stages.get(key)
        if st:
            steps.append(
                InvestigationStepInfo(
                    step_id=f"step-{key}",
                    label=st.label or default_label,
                    mcp_server=st.mcp_server or default_server,
                    status=status_map.get(st.status, StepStatus.PENDING),
                    description=st.message or f"Execution stage: {key}",
                    message=st.message,
                )
            )
        else:
            steps.append(
                InvestigationStepInfo(
                    step_id=f"step-{key}",
                    label=default_label,
                    mcp_server=default_server,
                    status=StepStatus.PENDING,
                    description=f"Planned stage: {key}",
                    message="Pending execution",
                )
            )

    inv_status_map = {
        "pending": InvestigationStatus.PENDING,
        "processing": InvestigationStatus.PROCESSING,
        "completed": InvestigationStatus.COMPLETED,
        "failed": InvestigationStatus.FAILED,
    }

    return InvestigationResponse(
        id=rec.investigation_id,
        query=rec.query,
        category=rec.category,
        resolved_category=rec.category,
        budget_inr=rec.budget_inr,
        status=inv_status_map.get(rec.status, InvestigationStatus.PROCESSING),
        created_at=datetime.fromisoformat(rec.created_at_utc),
        updated_at=datetime.fromisoformat(rec.updated_at_utc),
        is_placeholder=False,
        disclaimer=(
            "REAL MCP ORCHESTRATION: Live multi-agent MCP execution active. "
            "Public product pages inspected via Browser MCP, evidence persisted in Evidence MCP, "
            "specifications normalized via Comparison MCP, and integrity verified via Trust MCP."
        ),
        pipeline_steps=steps,
        summary=rec.summary,
        evidence_ids=rec.evidence_ids,
        comparison_result=rec.comparison_result,
        trust_report=rec.trust_report,
        target_urls=rec.target_urls,
        tool_logs_count=len(rec.all_tool_logs),
        warnings=rec.warnings,
        failures=rec.failures,
        related_variants=rec.related_variants,
        rejected_candidates=rec.rejected_candidates,
    )


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Product Investigation",
    description="Initialize a product investigation. Set mode='real' for live MCP orchestration or mode='demo' for simulated pipeline.",
)
async def create_investigation(
    payload: InvestigationCreateRequest,
    mode: Optional[str] = Query(default=None, description="'real' for real MCP orchestration, 'demo' for placeholder"),
    service: InvestigationServiceInterface = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Submit a product research query to start an investigation."""
    effective_mode = payload.mode or mode
    is_real = effective_mode == "real" or bool(payload.target_urls)

    if is_real:
        logger.info("Starting real MCP investigation: query='%s', category=%s", payload.query, payload.category)
        rec = await default_investigation_engine.start_investigation(
            query=payload.query,
            category=payload.category,
            budget_inr=payload.budget_inr,
            notes=payload.notes,
            target_urls=payload.target_urls,
        )
        return map_record_to_response(rec)
    else:
        logger.info("Using placeholder investigation service: query='%s'", payload.query)
        try:
            return await service.create_investigation(payload)
        except Exception as e:
            logger.error("Failed to create placeholder investigation: %s", str(e), exc_info=True)
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
    logger.debug("Fetching investigation id=%s", investigation_id)
    # Check real state store first
    real_rec = default_state_store.get_investigation(investigation_id)
    if real_rec:
        return map_record_to_response(real_rec)

    # Fall back to placeholder service
    investigation = await service.get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found."
        )
    return investigation


@router.get(
    "/{investigation_id}/events",
    summary="Stream Investigation Progress Events (SSE)",
    description="Subscribe to real-time Server-Sent Events (SSE) streaming stage progress and tool executions.",
)
async def get_investigation_events(investigation_id: str):
    """Server-Sent Events endpoint streaming live investigation events."""
    logger.info("Client subscribed to SSE events for investigation '%s'", investigation_id)
    queue = default_investigation_engine.subscribe(investigation_id)

    async def event_generator():
        try:
            # Yield initial status if investigation exists
            rec = default_state_store.get_investigation(investigation_id)
            if rec:
                init_payload = {
                    "event_type": "initial_state",
                    "investigation_id": investigation_id,
                    "status": rec.status,
                    "current_stage": rec.current_stage,
                    "stages": {k: s.model_dump() for k, s in rec.stages.items()},
                }
                yield f"data: {json.dumps(init_payload)}\n\n"
                if rec.status in ("completed", "failed"):
                    return

            while True:
                try:
                    event: InvestigationEvent = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                    if event.event_type in ("completed", "error"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"
        finally:
            default_investigation_engine.unsubscribe(investigation_id, queue)
            logger.info("Client unsubscribed from SSE for investigation '%s'", investigation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    real_recs = default_state_store.list_investigations(limit=limit, offset=offset)
    if real_recs:
        items = [map_record_to_response(r) for r in real_recs]
        return InvestigationListResponse(total=len(items), items=items)

    return await service.list_investigations(limit=limit, offset=offset)
