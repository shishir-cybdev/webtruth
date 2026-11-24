from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def current_utc_iso() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class PriceFact(BaseModel):
    """Preserves original displayed price and currency without unauthorized conversion."""

    displayed_text: Optional[str] = Field(
        default=None,
        description="Exact raw price text as displayed on the page (e.g. '₹1,89,999.00', '$1,299')",
    )
    numeric_amount: Optional[float] = Field(
        default=None,
        description="Parsed clean numeric amount, or null if unparseable/missing",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Original currency symbol or ISO code (e.g. 'INR', 'USD', '₹')",
    )
    is_inferred: bool = Field(
        default=False,
        description="Whether this price was inferred from surrounding text rather than direct tag",
    )
    conversion_rate_to_inr: Optional[float] = Field(
        default=None,
        description="Exchange rate used only if explicit conversion occurred, otherwise null",
    )
    conversion_timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp when conversion rate was sourced, otherwise null",
    )


class OpenProductPageResult(BaseModel):
    """Result of open_product_page MCP tool."""

    source_url: str = Field(..., description="Requested product page URL")
    final_url: Optional[str] = Field(default=None, description="Final resolved URL after redirects")
    page_title: Optional[str] = Field(default=None, description="Document title")
    page_status: Optional[int] = Field(default=None, description="HTTP status code (e.g. 200, 404)")
    capture_timestamp_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of capture")
    is_allowed: bool = Field(..., description="Whether the domain was permitted by the allowlist policy")
    error: Optional[str] = Field(default=None, description="Error message if navigation failed")


class ExtractedProductDataResult(BaseModel):
    """Result of extract_product_data MCP tool."""

    source_url: str = Field(..., description="Source URL of the product page")
    capture_timestamp_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of capture")
    product_name: Optional[str] = Field(default=None, description="Extracted product title or name")
    brand: Optional[str] = Field(default=None, description="Extracted manufacturer or brand name")
    model: Optional[str] = Field(default=None, description="Extracted model identifier")
    price: Optional[PriceFact] = Field(default=None, description="Extracted price facts, or null if missing")
    availability: Optional[str] = Field(
        default=None,
        description="Stock availability status (e.g. 'InStock', 'OutOfStock', 'PreOrder')",
    )
    specifications: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs of technical specifications extracted from tables or lists",
    )
    warranty: Optional[str] = Field(default=None, description="Extracted warranty terms if present")
    return_policy: Optional[str] = Field(default=None, description="Extracted return window/policy if present")
    extraction_method: str = Field(
        default="hybrid",
        description="Method used for extraction: 'json_ld', 'opengraph', 'dom', or 'hybrid'",
    )
    error: Optional[str] = Field(default=None, description="Error explanation if extraction failed")


class StructuredProductDataResult(BaseModel):
    """Result of extract_structured_product_data MCP tool."""

    source_url: str = Field(..., description="Source URL")
    capture_timestamp_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of capture")
    json_ld_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of raw JSON-LD schema.org/Product objects parsed from script tags",
    )
    open_graph: Dict[str, str] = Field(
        default_factory=dict,
        description="OpenGraph tags (og:title, og:price:amount, og:image, etc.)",
    )
    meta_data: Dict[str, str] = Field(
        default_factory=dict,
        description="Meta tags (description, keywords, twitter:*, etc.)",
    )
    detected_schemas: List[str] = Field(
        default_factory=list,
        description="List of schema.org types detected (e.g. ['Product', 'Offer'])",
    )
    error: Optional[str] = Field(default=None, description="Error if structured data could not be parsed")


class PageEvidenceRecordResult(BaseModel):
    """Result of capture_page_evidence MCP tool."""

    source_url: str = Field(..., description="Source URL")
    capture_timestamp_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of capture")
    page_title: Optional[str] = Field(default=None, description="Page title at time of capture")
    canonical_url: Optional[str] = Field(default=None, description="Declared canonical URL")
    extracted_text_snippets: List[str] = Field(
        default_factory=list,
        description="Key text snippets extracted from the page for auditing",
    )
    sha256_hash: str = Field(
        ...,
        description="Cryptographic SHA-256 hash computed over canonicalized evidence representation",
    )
    content_length_bytes: int = Field(
        default=0,
        description="Size in bytes of raw evidence source text",
    )
    error: Optional[str] = Field(default=None, description="Error if evidence capture failed")


class PageMetadataResult(BaseModel):
    """Result of inspect_page_metadata MCP tool."""

    source_url: str = Field(..., description="Requested URL")
    final_url: Optional[str] = Field(default=None, description="Final resolved URL")
    canonical_url: Optional[str] = Field(default=None, description="Declared canonical link")
    title: Optional[str] = Field(default=None, description="Document title")
    page_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="All extracted meta tags (name/property -> content)",
    )
    detected_structured_data_types: List[str] = Field(
        default_factory=list,
        description="List of detected JSON-LD types (e.g. ['Product', 'Offer', 'BreadcrumbList'])",
    )
    capture_timestamp_utc: str = Field(default_factory=current_utc_iso, description="UTC timestamp of inspection")
    error: Optional[str] = Field(default=None, description="Error if inspection failed")
