import logging
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from mcp_servers.trust.freshness import FreshnessPolicy
from mcp_servers.trust.schemas import (
    EvidenceQualityResult,
    SourceConsistencyResult,
    SourceFreshnessResult,
    TrustAssessmentResult,
    TrustReportResult,
    UnsupportedClaimsResult,
)
from mcp_servers.trust.trust_service import default_trust_service

logger = logging.getLogger("webtruth.trust.mcp")

# Initialize Trust MCP Server instance
server = MCPServer(
    name="webtruth-trust",
    instructions=(
        "WebTruth Trust MCP Server (Phase 2E). Evaluates evidence quality, checks source freshness, "
        "detects unsupported claims, evaluates multi-source consistency, calculates transparent "
        "trust indicators without arbitrary scores, and generates actionable verification guidance."
    ),
    version="0.2.0-phase2e",
)


@server.tool(
    name="assess_evidence_quality",
    description=(
        "Evaluate completeness, source traceability, timestamp availability, extraction quality, "
        "and SHA-256 cryptographic integrity of evidence records."
    ),
)
async def assess_evidence_quality(
    evidence_records: List[Dict[str, Any]],
) -> EvidenceQualityResult:
    """Evaluate completeness and integrity of evidence records."""
    return default_trust_service.assess_evidence_quality(evidence_records=evidence_records)


@server.tool(
    name="check_source_freshness",
    description=(
        "Evaluate the age of evidence using capture timestamps and configurable freshness policies. "
        "Returns age in hours/days and freshness classification (fresh, acceptable, aging, stale). "
        "Does not claim old information is false."
    ),
)
async def check_source_freshness(
    evidence_records: List[Dict[str, Any]],
    policy: Optional[Dict[str, Any]] = None,
) -> SourceFreshnessResult:
    """Evaluate evidence recency against freshness policies."""
    freshness_policy = FreshnessPolicy(**policy) if policy else None
    return default_trust_service.check_source_freshness(
        evidence_records=evidence_records,
        policy=freshness_policy,
    )


@server.tool(
    name="detect_unsupported_claims",
    description=(
        "Identify product claims without supporting evidence IDs, missing source records, or unsupported "
        "assertions. Distinguishes unsupported (no evidence cited / evidence not found) from contradicted "
        "(opposing evidence actively disputes the claim)."
    ),
)
async def detect_unsupported_claims(
    claims: List[Dict[str, Any]],
    evidence_records: List[Dict[str, Any]],
    conflicts: Optional[List[Dict[str, Any]]] = None,
) -> UnsupportedClaimsResult:
    """Audit asserted claims against available evidence records."""
    return default_trust_service.detect_unsupported_claims(
        claims=claims,
        evidence_records=evidence_records,
        conflicts=conflicts,
    )


@server.tool(
    name="evaluate_source_consistency",
    description=(
        "Evaluate multiple claims about the same product field across retailers and identify agreement, "
        "disagreement, and single-source (insufficient evidence) status. Disagreements are never silently resolved."
    ),
)
async def evaluate_source_consistency(
    products: Optional[List[Dict[str, Any]]] = None,
    spec_comparison: Optional[Dict[str, Any]] = None,
    price_comparison: Optional[Dict[str, Any]] = None,
    conflicts: Optional[Dict[str, Any]] = None,
) -> SourceConsistencyResult:
    """Audit cross-retailer specification and price agreement."""
    return default_trust_service.evaluate_source_consistency(
        products=products,
        spec_comparison=spec_comparison,
        price_comparison=price_comparison,
        conflicts=conflicts,
    )


@server.tool(
    name="calculate_trust_assessment",
    description=(
        "Produce transparent, explainable indicators for evidence coverage, provenance transparency, "
        "freshness, cryptographic integrity, and source consistency. Does not use arbitrary AI-generated "
        "scores or claim mathematical proof of truth."
    ),
)
async def calculate_trust_assessment(
    evidence_records: List[Dict[str, Any]],
    quality_result: Optional[Dict[str, Any]] = None,
    freshness_result: Optional[Dict[str, Any]] = None,
    consistency_result: Optional[Dict[str, Any]] = None,
    claims_result: Optional[Dict[str, Any]] = None,
) -> TrustAssessmentResult:
    """Calculate transparent indicators across evidence dimensions."""
    qr = EvidenceQualityResult(**quality_result) if quality_result else None
    fr = SourceFreshnessResult(**freshness_result) if freshness_result else None
    cr = SourceConsistencyResult(**consistency_result) if consistency_result else None
    clr = UnsupportedClaimsResult(**claims_result) if claims_result else None

    return default_trust_service.calculate_trust_assessment(
        evidence_records=evidence_records,
        quality_result=qr,
        freshness_result=fr,
        consistency_result=cr,
        claims_result=clr,
    )


@server.tool(
    name="generate_trust_report",
    description=(
        "Combine evidence records and comparison findings into a comprehensive structured report with "
        "supported claims, conflicting claims, unsupported claims, missing fields, stale sources, "
        "integrity status, and recommended user verification steps."
    ),
)
async def generate_trust_report(
    evidence_records: List[Dict[str, Any]],
    comparison_data: Optional[Dict[str, Any]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> TrustReportResult:
    """Generate complete evidence-backed trust and investigation report."""
    freshness_policy = FreshnessPolicy(**policy) if policy else None
    return default_trust_service.generate_trust_report(
        evidence_records=evidence_records,
        comparison_data=comparison_data,
        claims=claims,
        policy=freshness_policy,
    )
