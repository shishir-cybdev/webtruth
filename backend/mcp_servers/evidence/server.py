import logging
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from mcp_servers.evidence.evidence_service import evidence_service
from mcp_servers.evidence.schemas import (
    DuplicateEvidenceResult,
    EvidenceRecord,
    ProductEvidenceHistoryResult,
    SaveEvidenceRequest,
    SearchEvidenceResult,
    VerifyEvidenceResult,
)

logger = logging.getLogger("webtruth.evidence.mcp")

# Initialize Evidence MCP Server instance
server = MCPServer(
    name="webtruth-evidence",
    instructions=(
        "WebTruth Evidence MCP Server (Phase 2C). Manages tamper-evident persistent storage, "
        "SHA-256 integrity verification, duplicate detection, and chronological price history "
        "for investigative product claims."
    ),
    version="0.2.0-phase2c",
)


@server.tool(
    name="save_evidence",
    description=(
        "Persist an immutable, tamper-evident product evidence record into SQLite. "
        "Computes a deterministic canonical SHA-256 hash. Preserves exact displayed price "
        "and currency without unauthorized conversion or fabrication."
    ),
)
async def save_evidence(
    investigation_id: str,
    product_id: str,
    source_url: str,
    source_title: Optional[str] = None,
    capture_timestamp: Optional[str] = None,
    evidence_type: str = "retailer_price",
    extracted_claims: List[str] = [],
    raw_displayed_price: Optional[str] = None,
    currency: Optional[str] = None,
    numeric_price: Optional[float] = None,
    evidence_hash: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvidenceRecord:
    """Save a validated product evidence record."""
    req = SaveEvidenceRequest(
        investigation_id=investigation_id,
        product_id=product_id,
        source_url=source_url,
        source_title=source_title,
        capture_timestamp=capture_timestamp,
        evidence_type=evidence_type,
        extracted_claims=extracted_claims,
        raw_displayed_price=raw_displayed_price,
        currency=currency,
        numeric_price=numeric_price,
        evidence_hash=evidence_hash,
        metadata=metadata,
    )
    return evidence_service.save_evidence(req)


@server.tool(
    name="get_evidence",
    description="Retrieve a stored evidence record by its unique evidence ID.",
)
async def get_evidence(evidence_id: str) -> Optional[EvidenceRecord]:
    """Retrieve an evidence record by ID."""
    return evidence_service.get_evidence(evidence_id)


@server.tool(
    name="search_evidence",
    description=(
        "Search stored evidence records by investigation ID, product ID, source domain, "
        "and evidence type with pagination."
    ),
)
async def search_evidence(
    investigation_id: Optional[str] = None,
    product_id: Optional[str] = None,
    source_domain: Optional[str] = None,
    evidence_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> SearchEvidenceResult:
    """Search evidence records with dynamic parameterized filtering."""
    return evidence_service.search_evidence(
        investigation_id=investigation_id,
        product_id=product_id,
        source_domain=source_domain,
        evidence_type=evidence_type,
        limit=limit,
        offset=offset,
    )


@server.tool(
    name="verify_evidence",
    description=(
        "Recalculate the SHA-256 hash from canonical stored evidence fields and compare "
        "against the stored hash to detect unauthorized data modification or tampering."
    ),
)
async def verify_evidence(evidence_id: str) -> VerifyEvidenceResult:
    """Verify cryptographic integrity of an evidence record."""
    return evidence_service.verify_evidence(evidence_id)


@server.tool(
    name="get_product_evidence_history",
    description=(
        "Retrieve chronologically ordered evidence records and historical price snapshots "
        "for a given product identifier."
    ),
)
async def get_product_evidence_history(product_id: str) -> ProductEvidenceHistoryResult:
    """Fetch chronological price and evidence history for a product."""
    return evidence_service.get_product_evidence_history(product_id)


@server.tool(
    name="detect_duplicate_evidence",
    description=(
        "Identify existing records with identical source URL and content claims or matching "
        "SHA-256 hash without deleting or modifying original evidence."
    ),
)
async def detect_duplicate_evidence(
    source_url: str,
    extracted_claims: List[str] = [],
    investigation_id: Optional[str] = None,
    product_id: Optional[str] = None,
    evidence_hash: Optional[str] = None,
) -> DuplicateEvidenceResult:
    """Check for duplicate evidence records."""
    return evidence_service.detect_duplicate_evidence(
        source_url=source_url,
        extracted_claims=extracted_claims,
        investigation_id=investigation_id,
        product_id=product_id,
        evidence_hash=evidence_hash,
    )
