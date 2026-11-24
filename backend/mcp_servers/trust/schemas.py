from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mcp_servers.trust.freshness import (
    FreshnessClassification,
    FreshnessPolicy,
)


def current_utc_iso() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 1. Evidence Quality Schemas
# ---------------------------------------------------------------------------

class QualityIssue(BaseModel):
    """Specific flaw or defect identified in an evidence record."""
    issue_type: str = Field(..., description="Category of defect (e.g. 'missing_timestamp', 'tampered_hash')")
    severity: str = Field(..., description="'info', 'warning', or 'critical'")
    description: str = Field(..., description="Human-readable explanation of the defect")


class EvidenceQualityItem(BaseModel):
    """Quality evaluation of an individual evidence record."""
    evidence_id: str = Field(..., description="ID of the evaluated record")
    source_url: str = Field(..., description="Source URL where evidence was gathered")
    source_domain: str = Field(..., description="Extracted domain of the source")
    has_timestamp: bool = Field(..., description="Whether a valid capture timestamp exists")
    has_traceable_url: bool = Field(..., description="Whether source URL is a valid, traceable web address")
    has_extracted_data: bool = Field(..., description="Whether the record contains text claims or specifications")
    claims_count: int = Field(default=0, description="Number of verbatim claims or snippets recorded")
    has_price: bool = Field(default=False, description="Whether pricing data was captured")
    integrity_status: str = Field(
        ...,
        description="'verified' (SHA-256 matches), 'tampered' (mismatch), or 'unverified_missing_hash'",
    )
    quality_rating: str = Field(..., description="'high', 'medium', or 'low'")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Normalized score from 0.0 to 1.0")
    issues: List[QualityIssue] = Field(default_factory=list, description="Defects or warnings for this record")


class EvidenceQualityResult(BaseModel):
    """Aggregate quality assessment across all evaluated evidence records."""
    total_records: int = Field(..., description="Total evidence records evaluated")
    high_quality_count: int = Field(default=0, description="Records with high completeness and integrity")
    medium_quality_count: int = Field(default=0, description="Records with minor gaps but usable claims")
    low_quality_count: int = Field(default=0, description="Records with critical gaps or missing data")
    tampered_records_count: int = Field(default=0, description="Records failing cryptographic hash verification")
    records: List[EvidenceQualityItem] = Field(default_factory=list, description="Individual evaluations")
    overall_quality_assessment: str = Field(..., description="Summary statement of overall evidence quality")
    evaluation_notes: List[str] = Field(default_factory=list, description="Transparency notes and cautions")


# ---------------------------------------------------------------------------
# 2. Source Freshness Schemas
# ---------------------------------------------------------------------------

class SourceFreshnessItem(BaseModel):
    """Freshness evaluation of an individual evidence record."""
    evidence_id: Optional[str] = Field(default=None, description="Referenced evidence ID")
    source_url: str = Field(..., description="Source URL")
    source_domain: str = Field(..., description="Domain of the source")
    capture_timestamp: Optional[str] = Field(default=None, description="Reported capture timestamp")
    age_hours: Optional[float] = Field(default=None, description="Age in hours from evaluation moment")
    age_days: Optional[float] = Field(default=None, description="Age in days from evaluation moment")
    classification: FreshnessClassification = Field(..., description="Freshness tier ('fresh', 'stale', etc.)")
    explanation: str = Field(..., description="Explanation note with practical buying context")
    is_stale: bool = Field(default=False, description="True if age exceeds the aging threshold")


class SourceFreshnessResult(BaseModel):
    """Aggregate freshness assessment across all evidence sources."""
    total_evaluated: int = Field(..., description="Total records evaluated for freshness")
    fresh_count: int = Field(default=0, description="Records within fresh threshold (<=24h)")
    acceptable_count: int = Field(default=0, description="Records within acceptable threshold (<=7d)")
    aging_count: int = Field(default=0, description="Records within aging threshold (<=30d)")
    stale_count: int = Field(default=0, description="Records older than aging threshold (>30d)")
    unknown_count: int = Field(default=0, description="Records with missing or unparseable timestamps")
    items: List[SourceFreshnessItem] = Field(default_factory=list, description="Individual freshness evaluations")
    oldest_record_age_days: Optional[float] = Field(default=None, description="Age of oldest record in days")
    newest_record_age_days: Optional[float] = Field(default=None, description="Age of newest record in days")
    overall_freshness: FreshnessClassification = Field(..., description="Overall dataset freshness tier")
    freshness_policy_applied: FreshnessPolicy = Field(default_factory=FreshnessPolicy)
    evaluation_notes: List[str] = Field(default_factory=list, description="Contextual notes on evidence age")


# ---------------------------------------------------------------------------
# 3. Unsupported Claims Schemas
# ---------------------------------------------------------------------------

class ClaimStatus(str, Enum):
    """Verification status of a specific claim."""
    SUPPORTED = "supported"        # Backed by valid cited evidence record
    UNSUPPORTED = "unsupported"    # No evidence cited, or cited evidence record not found / lacks claim
    CONTRADICTED = "contradicted"  # Competing evidence explicitly disputes this claim


class ClaimItem(BaseModel):
    """Input claim to be checked against evidence."""
    claim_id: str = Field(..., description="Unique claim identifier (e.g. 'clm_01')")
    field: str = Field(..., description="Target attribute (e.g. 'RAM', 'Price', 'Warranty')")
    claimed_value: Optional[str] = Field(default=None, description="Asserted value or statement")
    cited_evidence_ids: List[str] = Field(
        default_factory=list,
        description="Evidence IDs claimed to support this assertion",
    )
    source_url: Optional[str] = Field(default=None, description="Optional source claiming this value")


class ClaimVerificationItem(BaseModel):
    """Detailed verification outcome of an individual claim."""
    claim_id: str = Field(..., description="Claim identifier")
    field: str = Field(..., description="Target attribute")
    claimed_value: Optional[str] = Field(default=None, description="Asserted value")
    status: ClaimStatus = Field(..., description="'supported', 'unsupported', or 'contradicted'")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs cited by claim")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Verified supporting evidence IDs")
    contradicting_evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs disputing claim")
    missing_evidence_ids: List[str] = Field(default_factory=list, description="Cited evidence IDs not found in DB")
    explanation: str = Field(..., description="Clear explanation of the claim verification outcome")


class UnsupportedClaimsResult(BaseModel):
    """Result of audit across all asserted claims."""
    total_claims: int = Field(..., description="Total claims scrutinized")
    supported_count: int = Field(default=0, description="Number of fully evidenced claims")
    unsupported_count: int = Field(default=0, description="Claims lacking evidence or citing nonexistent records")
    contradicted_count: int = Field(default=0, description="Claims actively disputed by opposing evidence")
    claims: List[ClaimVerificationItem] = Field(default_factory=list, description="Itemized verification outcomes")
    has_unsupported_claims: bool = Field(default=False, description="True if any unbacked claims exist")
    has_contradictions: bool = Field(default=False, description="True if any claims are actively contradicted")
    summary: str = Field(..., description="Concise summary of claim audit")


# ---------------------------------------------------------------------------
# 4. Source Consistency Schemas
# ---------------------------------------------------------------------------

class ConsistencyStatus(str, Enum):
    """Consistency outcome across multiple sources for a field."""
    AGREEMENT = "agreement"                    # >= 2 sources agree on the normalized value
    DISAGREEMENT = "disagreement"              # >= 2 sources report conflicting values
    SINGLE_SOURCE = "single_source"            # Exactly 1 source provides this field (unverified)
    UNKNOWN = "unknown"                        # 0 sources report this field


class FieldConsistencyItem(BaseModel):
    """Consistency analysis for a specific product attribute."""
    field_name: str = Field(..., description="Attribute name (e.g. 'RAM', 'Price', 'Warranty')")
    status: ConsistencyStatus = Field(..., description="Consistency status")
    agreement_count: int = Field(default=0, description="Number of sources sharing the dominant value")
    total_sources: int = Field(default=0, description="Total sources with data on this field")
    distinct_claims: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All competing or matching claims with raw values, source URLs, and evidence IDs",
    )
    explanation: str = Field(..., description="Transparent explanation of agreement or disagreement")


class SourceConsistencyResult(BaseModel):
    """Overall cross-source consistency audit."""
    total_fields_evaluated: int = Field(..., description="Total specification and pricing fields evaluated")
    agreeing_fields_count: int = Field(default=0, description="Fields where all reporting sources agree")
    disagreeing_fields_count: int = Field(default=0, description="Fields with conflicting claims")
    single_source_fields_count: int = Field(default=0, description="Fields supported by only one source")
    fields: List[FieldConsistencyItem] = Field(default_factory=list, description="Per-field consistency analysis")
    overall_consistency: str = Field(
        ...,
        description="'high_agreement', 'partial_disagreements', 'mostly_single_source', or 'insufficient_evidence'",
    )
    consistency_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proportion of multi-source fields that agree (1.0 if all agree, 0.0 if all conflict)",
    )


# ---------------------------------------------------------------------------
# 5. Trust Assessment Schemas
# ---------------------------------------------------------------------------

class TrustComponentBreakdown(BaseModel):
    """Individual transparent trust component indicator."""
    indicator_name: str = Field(..., description="Name of the transparency metric")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized indicator value from 0.0 to 1.0")
    rating: str = Field(..., description="'high', 'moderate', 'low', or 'insufficient_data'")
    metric_details: Dict[str, Any] = Field(default_factory=dict, description="Raw metrics supporting indicator")
    explanation: str = Field(..., description="Human-readable description of how this value was derived")


class TrustAssessmentResult(BaseModel):
    """Transparent, explainable trust assessment combining multiple objective indicators."""
    overall_trust_tier: str = Field(
        ...,
        description="'HIGH_TRANSPARENCY', 'MODERATE_TRANSPARENCY', 'CAUTION_FLAGGED', or 'INSUFFICIENT_DATA'",
    )
    evidence_coverage: TrustComponentBreakdown = Field(..., description="Completeness of key product attributes")
    provenance_transparency: TrustComponentBreakdown = Field(..., description="Source URL and evidence traceability")
    freshness_indicator: TrustComponentBreakdown = Field(..., description="Temporal recency of evidence records")
    integrity_indicator: TrustComponentBreakdown = Field(..., description="Cryptographic SHA-256 verification rate")
    source_consistency: TrustComponentBreakdown = Field(..., description="Cross-retailer agreement ratio")
    key_confidence_factors: List[str] = Field(default_factory=list, description="Positive structural indicators")
    key_risk_factors: List[str] = Field(default_factory=list, description="Identified warning flags or uncertainties")
    disclaimer: str = Field(
        default=(
            "Trust indicators represent structural transparency, source traceability, cryptographic "
            "record integrity, and cross-source consistency. A high indicator confirms verifiable "
            "documentation; it does NOT mathematically prove retailer honesty or guarantee absence of "
            "retailer errors. SHA-256 verifies that the record was not altered post-capture."
        ),
        description="Mandatory scientific and consumer disclaimer",
    )


# ---------------------------------------------------------------------------
# 6. Trust Report Schemas
# ---------------------------------------------------------------------------

class RecommendedVerificationStep(BaseModel):
    """Actionable verification instruction for the user before purchasing."""
    step_id: str = Field(..., description="Step identifier (e.g. 'step_01')")
    priority: str = Field(..., description="'critical', 'recommended', or 'optional'")
    action: str = Field(..., description="Clear imperative instruction for the user")
    rationale: str = Field(..., description="Why this verification is necessary based on evidence findings")
    relevant_urls: List[str] = Field(default_factory=list, description="URLs to inspect")


class TrustReportResult(BaseModel):
    """Unified comprehensive trust and investigation report."""
    report_id: str = Field(..., description="Unique report identifier ('tr_...')")
    generated_at_utc: str = Field(default_factory=current_utc_iso, description="UTC generation timestamp")
    product_identity: Dict[str, Any] = Field(default_factory=dict, description="Product identification")
    trust_assessment: TrustAssessmentResult = Field(..., description="Core transparent trust assessment")
    evidence_quality_summary: EvidenceQualityResult = Field(..., description="Evidence completeness and integrity")
    freshness_summary: SourceFreshnessResult = Field(..., description="Freshness breakdown")
    consistency_summary: SourceConsistencyResult = Field(..., description="Cross-source agreement audit")
    supported_claims: List[ClaimVerificationItem] = Field(default_factory=list, description="Evidenced claims")
    conflicting_claims: List[ClaimVerificationItem] = Field(default_factory=list, description="Disputed claims")
    unsupported_claims: List[ClaimVerificationItem] = Field(default_factory=list, description="Unbacked assertions")
    missing_fields: List[str] = Field(default_factory=list, description="Critical specs missing from all sources")
    stale_sources: List[SourceFreshnessItem] = Field(default_factory=list, description="Sources exceeding freshness limits")
    integrity_status: str = Field(
        ...,
        description="'ALL_RECORDS_VERIFIED', 'TAMPERING_DETECTED', or 'PARTIAL_UNVERIFIED'",
    )
    recommended_verification_steps: List[RecommendedVerificationStep] = Field(
        default_factory=list,
        description="Actionable guidance for the consumer",
    )
