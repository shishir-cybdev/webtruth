from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def current_utc_iso() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class NormalizedSpecField(BaseModel):
    """Normalized specification field preserving raw text alongside canonicalized values."""

    field_name: str = Field(..., description="Canonical specification attribute name")
    raw_value: Optional[str] = Field(default=None, description="Original unparsed string from source")
    normalized_value: Optional[str] = Field(default=None, description="Standardized canonical display string")
    numeric_value: Optional[float] = Field(default=None, description="Extracted numeric measurement if applicable")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. GB, TB, GHz, inches)")


class NormalizedProduct(BaseModel):
    """Complete product profile with raw and normalized specifications."""

    product_name: str = Field(..., description="Product display title")
    brand: NormalizedSpecField = Field(..., description="Brand/Manufacturer field")
    model: NormalizedSpecField = Field(..., description="Product model line")
    model_number: Optional[NormalizedSpecField] = Field(default=None, description="Specific model/SKU code")
    ram: Optional[NormalizedSpecField] = Field(default=None, description="RAM memory specification")
    storage: Optional[NormalizedSpecField] = Field(default=None, description="Storage drive specification")
    cpu: Optional[NormalizedSpecField] = Field(default=None, description="Processor specification")
    gpu: Optional[NormalizedSpecField] = Field(default=None, description="Graphics card specification")
    screen_size: Optional[NormalizedSpecField] = Field(default=None, description="Display size specification")
    other_specs: Dict[str, NormalizedSpecField] = Field(
        default_factory=dict,
        description="Additional technical specifications",
    )
    config_fingerprint: str = Field(
        ...,
        description="Deterministic configuration key ensuring different configurations are not equated",
    )
    source_evidence_id: Optional[str] = Field(default=None, description="Associated evidence ID if available")
    source_url: Optional[str] = Field(default=None, description="Origin URL of this product profile")


class PricePoint(BaseModel):
    """Itemized price observation from a specific retailer or evidence record."""

    source_url: str = Field(..., description="Origin product page URL")
    source_domain: str = Field(..., description="Retailer or host domain (e.g. amazon.in)")
    source_title: Optional[str] = Field(default=None, description="Title of the source page")
    capture_timestamp: str = Field(..., description="UTC ISO timestamp of price observation")
    raw_displayed_price: Optional[str] = Field(
        default=None,
        description="Exact displayed price string verbatim from source (e.g. '₹1,89,999.00'). Never invented.",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Original currency symbol or ISO code. Never converted without rate.",
    )
    numeric_price: Optional[float] = Field(
        default=None,
        description="Extracted clean numeric amount, or null if missing/unparseable",
    )
    evidence_id: Optional[str] = Field(default=None, description="Traceable Evidence ID")


class PriceComparisonResult(BaseModel):
    """Outcome of price comparison across multiple sources."""

    total_sources: int = Field(..., description="Total price points analyzed")
    price_points: List[PricePoint] = Field(default_factory=list, description="All gathered price points")
    lowest_price: Optional[PricePoint] = Field(default=None, description="Lowest verified price point")
    highest_price: Optional[PricePoint] = Field(default=None, description="Highest verified price point")
    price_spread: Optional[float] = Field(
        default=None,
        description="Numeric difference between highest and lowest. Computed ONLY when currencies match.",
    )
    currency_mismatch_detected: bool = Field(
        default=False,
        description="True if sources present differing currencies without exchange rates",
    )
    currencies_found: List[str] = Field(default_factory=list, description="Unique currencies observed")
    missing_price_sources: List[str] = Field(
        default_factory=list,
        description="Sources where prices were missing or unavailable",
    )
    comparison_notes: List[str] = Field(default_factory=list, description="Audit and transparency notes")


class SpecComparisonItem(BaseModel):
    """Comparison of a single specification field across sources."""

    field_name: str = Field(..., description="Specification attribute name")
    status: str = Field(..., description="'equal', 'different', or 'unavailable'")
    values_by_source: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Values mapped by source URL or domain",
    )
    evidence_ids: List[str] = Field(default_factory=list, description="Referenced evidence record IDs")
    note: Optional[str] = Field(default=None, description="Detailed explanation if differing or unavailable")


class SpecComparisonResult(BaseModel):
    """Result of specification comparison across matching products."""

    equal_fields: List[SpecComparisonItem] = Field(
        default_factory=list,
        description="Fields where all sources agree",
    )
    different_fields: List[SpecComparisonItem] = Field(
        default_factory=list,
        description="Fields with differing claimed values across sources",
    )
    unavailable_fields: List[SpecComparisonItem] = Field(
        default_factory=list,
        description="Fields missing from one or more sources",
    )
    total_fields_compared: int = Field(..., description="Total specification fields scrutinized")
    configuration_match: bool = Field(
        default=True,
        description="False if key hardware (RAM, Storage, CPU, GPU) differs significantly",
    )


class PolicyItem(BaseModel):
    """Audit of warranty, return, replacement, or delivery policies."""

    policy_type: str = Field(..., description="'warranty', 'returns', 'replacement', 'delivery'")
    source_url: str = Field(..., description="Origin URL")
    source_domain: str = Field(..., description="Host domain")
    evidence_id: Optional[str] = Field(default=None, description="Evidence ID")
    raw_terms: Optional[str] = Field(default=None, description="Verbatim extracted policy statement")
    is_missing: bool = Field(default=False, description="True if source discloses no terms")
    is_ambiguous: bool = Field(default=False, description="True if terms are vague or conditional")


class PolicyComparisonResult(BaseModel):
    """Result of policy comparison across sources."""

    policies: List[PolicyItem] = Field(default_factory=list, description="Extracted policy terms")
    missing_policies_count: int = Field(..., description="Count of sources with missing policies")
    summary: str = Field(..., description="Summary of policy consistency and missing terms")


class ProductConflictItem(BaseModel):
    """A conflicting factual claim between two or more sources."""

    field_name: str = Field(..., description="Conflicted attribute (e.g. RAM, Display Type, Warranty)")
    conflict_description: str = Field(..., description="Clear explanation of the factual dispute")
    claims: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of competing claims with raw values, source URLs, and evidence IDs",
    )


class ProductConflictResult(BaseModel):
    """Result of contradiction and conflict detection."""

    has_conflicts: bool = Field(..., description="True if any conflicting claims were detected")
    conflicts_count: int = Field(..., description="Number of conflicting fields found")
    conflicts: List[ProductConflictItem] = Field(
        default_factory=list,
        description="List of identified factual contradictions",
    )


class ComprehensiveComparisonResult(BaseModel):
    """Complete product investigation comparison synthesis."""

    product_identity: Dict[str, Any] = Field(..., description="Canonical product identification and model")
    configuration_match: bool = Field(
        ...,
        description="Whether all sources are describing the exact same hardware configuration",
    )
    configuration_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings if different configurations/models were compared",
    )
    price_comparison: PriceComparisonResult = Field(..., description="Price analysis and spread")
    spec_comparison: SpecComparisonResult = Field(..., description="Specification matrix")
    policy_comparison: PolicyComparisonResult = Field(..., description="Warranty and returns comparison")
    conflicts: ProductConflictResult = Field(..., description="Detected contradictions")
    unknown_fields: List[str] = Field(
        default_factory=list,
        description="Important product specifications that could not be verified anywhere",
    )
    evidence_references: List[str] = Field(
        default_factory=list,
        description="List of all Evidence IDs underpinning this comparison",
    )
    generated_at_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of generation")
