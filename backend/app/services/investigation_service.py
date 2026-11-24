import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationListResponse,
    InvestigationResponse,
    InvestigationStatus,
    InvestigationStepInfo,
    StepStatus,
)

logger = logging.getLogger(__name__)


# Pipeline stage template matching the WebTruth MCP architecture
PIPELINE_TEMPLATES = [
    {
        "step_id": "step-query-parse",
        "label": "Query Understanding",
        "mcp_server": "PriceSpider MCP",
        "description": "Parses product intent, identifies model numbers, and normalizes brand/category terms.",
        "placeholder_message": "Query validated and parsed. Ready for multi-agent dispatch.",
    },
    {
        "step_id": "step-price-crawl",
        "label": "Price Spider Ingestion",
        "mcp_server": "PriceSpider MCP",
        "description": "Searches 50+ Indian e-commerce sites for live and historical pricing signals.",
        "placeholder_message": "Phase 2B pending: PriceSpider MCP tool 'fetch_price' not yet active.",
    },
    {
        "step_id": "step-review-analysis",
        "label": "Review Sentiment & Authenticity",
        "mcp_server": "ReviewSense MCP",
        "description": "Analyzes verified customer reviews, detects sentiment polarity and astroturfing patterns.",
        "placeholder_message": "Phase 2B pending: ReviewSense MCP tool 'aggregate_reviews' not yet active.",
    },
    {
        "step_id": "step-spec-verify",
        "label": "Datasheet Cross-Referencing",
        "mcp_server": "SpecVerify MCP",
        "description": "Cross-references seller claimed specifications against official manufacturer databases.",
        "placeholder_message": "Phase 2B pending: SpecVerify MCP tool 'verify_spec' not yet active.",
    },
    {
        "step_id": "step-contradiction-detect",
        "label": "Contradiction & Anomaly Detection",
        "mcp_server": "TrustScore MCP",
        "description": "Surfaces discrepancies between seller claims, reviewer complaints, and MSRP.",
        "placeholder_message": "Phase 2B pending: TrustScore MCP tool 'flag_contradiction' not yet active.",
    },
    {
        "step_id": "step-trust-compute",
        "label": "Trust Score Synthesis",
        "mcp_server": "TrustScore MCP",
        "description": "Calculates composite trust metrics and synthesizes human-readable risk summary.",
        "placeholder_message": "Phase 2B pending: TrustScore MCP tool 'compute_trust' not yet active.",
    },
]


class InvestigationNotFoundError(Exception):
    """Raised when an investigation ID does not exist."""
    def __init__(self, investigation_id: str):
        super().__init__(f"Investigation with ID '{investigation_id}' was not found.")
        self.investigation_id = investigation_id


class InvestigationServiceInterface(ABC):
    """Abstract interface for WebTruth investigation operations.
    
    Any concrete implementation must adhere to this interface, whether it's
    the Phase 2A placeholder service or the Phase 2B multi-agent MCP coordinator.
    """

    @abstractmethod
    async def create_investigation(self, request: InvestigationCreateRequest) -> InvestigationResponse:
        """Initialize and trigger a product investigation workflow."""
        pass

    @abstractmethod
    async def get_investigation(self, investigation_id: str) -> Optional[InvestigationResponse]:
        """Retrieve investigation state and pipeline progress by ID."""
        pass

    @abstractmethod
    async def list_investigations(self, limit: int = 20, offset: int = 0) -> InvestigationListResponse:
        """List recently submitted investigations."""
        pass


class PlaceholderInvestigationService(InvestigationServiceInterface):
    """Phase 2A Placeholder Investigation Service.
    
    IMPORTANT ARCHITECTURAL NOTE:
    -----------------------------
    This implementation explicitly stores and simulates investigation workflows in-memory.
    It DOES NOT execute live web scraping, fake external citations, or fabricate real-time
    pricing data. All results are clearly flagged with `is_placeholder=True` and clear
    disclaimers until Phase 2B integrates the real MCP servers.
    """

    def __init__(self) -> None:
        self._storage: Dict[str, InvestigationResponse] = {}
        logger.info("Initialized PlaceholderInvestigationService (Phase 2A in-memory store)")

    def _build_initial_steps(self) -> List[InvestigationStepInfo]:
        """Construct initial pipeline steps for an investigation."""
        steps: List[InvestigationStepInfo] = []
        for i, tmpl in enumerate(PIPELINE_TEMPLATES):
            # First step completes to verify query receipt; remaining are pending Phase 2B
            status = StepStatus.COMPLETED if i == 0 else StepStatus.PENDING
            steps.append(
                InvestigationStepInfo(
                    step_id=tmpl["step_id"],
                    label=tmpl["label"],
                    mcp_server=tmpl["mcp_server"],
                    status=status,
                    description=tmpl["description"],
                    message=tmpl["placeholder_message"],
                )
            )
        return steps

    async def create_investigation(self, request: InvestigationCreateRequest) -> InvestigationResponse:
        """Create and register a new simulated investigation."""
        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        budget_str = f" within budget of ₹{request.budget_inr:,.0f}" if request.budget_inr else ""
        category_str = f" in category '{request.category}'" if request.category else ""

        summary = (
            f"Investigation initialized for '{request.query}'{category_str}{budget_str}. "
            "Pipeline stage 1 (Query Understanding) completed. Subsequent MCP agent stages "
            "are currently in placeholder mode awaiting Phase 2B server hookups."
        )

        response = InvestigationResponse(
            id=inv_id,
            query=request.query,
            category=request.category,
            budget_inr=request.budget_inr,
            status=InvestigationStatus.PROCESSING,
            created_at=now,
            updated_at=now,
            is_placeholder=True,
            pipeline_steps=self._build_initial_steps(),
            summary=summary,
        )

        self._storage[inv_id] = response
        logger.info("Created placeholder investigation: id=%s query='%s'", inv_id, request.query)
        return response

    async def get_investigation(self, investigation_id: str) -> Optional[InvestigationResponse]:
        """Retrieve an investigation by its ID."""
        investigation = self._storage.get(investigation_id)
        if investigation is None:
            logger.warning("Investigation not found: id=%s", investigation_id)
            return None
        return investigation

    async def list_investigations(self, limit: int = 20, offset: int = 0) -> InvestigationListResponse:
        """List stored investigations with pagination."""
        all_items = list(self._storage.values())
        # Sort newest first
        all_items.sort(key=lambda x: x.created_at, reverse=True)
        paginated = all_items[offset : offset + limit]
        return InvestigationListResponse(
            total=len(all_items),
            items=paginated,
        )


# Singleton instance for dependency injection
_investigation_service_instance = PlaceholderInvestigationService()


def get_investigation_service() -> InvestigationServiceInterface:
    """Dependency provider for investigation service."""
    return _investigation_service_instance
