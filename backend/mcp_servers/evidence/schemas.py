from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


def current_utc_iso() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class EvidenceType(str, Enum):
    """Categorization of evidence records."""
    RETAILER_PRICE = "retailer_price"
    SPECS_TABLE = "specs_table"
    REVIEW_SUMMARY = "review_summary"
    DATASHEET = "datasheet"
    PAGE_SNAPSHOT = "page_snapshot"
    METADATA = "metadata"
    CONTRADICTION_ALERT = "contradiction_alert"


class SaveEvidenceRequest(BaseModel):
    """Payload to store an evidence record."""

    investigation_id: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Associated investigation ID (e.g. 'inv_a8f9c2d1e0b4')",
        examples=["inv_a8f9c2d1e0b4"],
    )
    product_id: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target product model or canonical identifier",
        examples=["dell-xps-15-9530"],
    )
    source_url: str = Field(
        ...,
        min_length=4,
        max_length=2048,
        description="Source URL where evidence was gathered",
        examples=["https://amazon.in/dp/B0CX214981"],
    )
    source_title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Document title of the source page",
    )
    capture_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC timestamp of original capture. Defaults to now.",
    )
    evidence_type: str = Field(
        default=EvidenceType.RETAILER_PRICE.value,
        description="Classification of this evidence (e.g. 'retailer_price', 'specs_table')",
    )
    extracted_claims: List[str] = Field(
        default_factory=list,
        description="Verbatim text claims, specifications, or pricing quotes extracted from page",
    )
    raw_displayed_price: Optional[str] = Field(
        default=None,
        description="Preserved exact price text displayed on the page (e.g. '₹1,89,999.00'). Never invent.",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Preserved currency code or symbol (e.g. 'INR', 'USD'). Never convert without rate.",
    )
    numeric_price: Optional[float] = Field(
        default=None,
        description="Parsed numeric price value if available",
    )
    evidence_hash: Optional[str] = Field(
        default=None,
        description="Optional pre-computed SHA-256 hash. If omitted, computed automatically from canonical payload.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional auxiliary attributes, e.g. extractor version or seller rating",
    )

    @field_validator("investigation_id", "product_id", "source_url")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only")
        return cleaned


class EvidenceRecord(BaseModel):
    """Immutable persistent record of product evidence."""

    evidence_id: str = Field(..., description="Unique immutable evidence identifier ('evi_...')")
    investigation_id: str = Field(..., description="Associated investigation ID")
    product_id: str = Field(..., description="Associated product identifier")
    source_url: str = Field(..., description="Source URL")
    source_domain: str = Field(..., description="Extracted source domain (e.g. 'amazon.in')")
    source_title: Optional[str] = Field(default=None, description="Source page title")
    capture_timestamp: str = Field(..., description="UTC ISO timestamp when data was captured")
    evidence_type: str = Field(..., description="Type of evidence")
    extracted_claims: List[str] = Field(default_factory=list, description="Verbatim text claims")
    raw_displayed_price: Optional[str] = Field(default=None, description="Exact displayed price string")
    currency: Optional[str] = Field(default=None, description="Currency string")
    numeric_price: Optional[float] = Field(default=None, description="Numeric price float")
    evidence_hash: str = Field(..., description="Cryptographic SHA-256 hash of canonical payload")
    created_at: str = Field(..., description="UTC ISO timestamp when record was saved")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary metadata")


class VerifyEvidenceResult(BaseModel):
    """Result of SHA-256 integrity verification."""

    evidence_id: str = Field(..., description="ID of verified evidence record")
    is_valid: bool = Field(..., description="True if computed hash matches stored hash exactly")
    stored_hash: str = Field(..., description="Hash stored in the database")
    computed_hash: str = Field(..., description="Hash recomputed from canonical stored fields")
    status: str = Field(..., description="'valid', 'modified', or 'not_found'")
    message: str = Field(..., description="Human-readable explanation of verification outcome")


class SearchEvidenceResult(BaseModel):
    """Result of search_evidence query."""

    total: int = Field(..., description="Total matching records found")
    items: List[EvidenceRecord] = Field(default_factory=list, description="Matching evidence records")


class PriceHistorySnapshot(BaseModel):
    """Snapshot of a product price point over time."""

    capture_timestamp: str = Field(..., description="Capture timestamp")
    source_url: str = Field(..., description="Source URL")
    source_domain: str = Field(..., description="Source retailer/domain")
    raw_displayed_price: Optional[str] = Field(default=None, description="Raw displayed price")
    currency: Optional[str] = Field(default=None, description="Currency")
    numeric_price: Optional[float] = Field(default=None, description="Clean numeric amount")
    evidence_id: str = Field(..., description="Backlink to underlying evidence record")


class ProductEvidenceHistoryResult(BaseModel):
    """Chronological history of all evidence and prices for a product."""

    product_id: str = Field(..., description="Product identifier")
    total_records: int = Field(..., description="Total evidence records on file")
    price_history: List[PriceHistorySnapshot] = Field(
        default_factory=list,
        description="Chronological price points with timestamps and sources",
    )
    evidence_records: List[EvidenceRecord] = Field(
        default_factory=list,
        description="All evidence items ordered chronologically",
    )


class DuplicateEvidenceResult(BaseModel):
    """Outcome of duplicate detection analysis."""

    is_duplicate: bool = Field(..., description="True if matching evidence records already exist")
    duplicate_count: int = Field(..., description="Number of duplicate records found")
    matched_records: List[EvidenceRecord] = Field(
        default_factory=list,
        description="Existing records with identical hash or identical URL and claims",
    )
    reason: Optional[str] = Field(default=None, description="Explanation of match criteria")
