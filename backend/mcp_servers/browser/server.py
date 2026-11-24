import logging
from mcp.server.mcpserver import MCPServer

from mcp_servers.browser.browser_manager import browser_manager
from mcp_servers.browser.extractor import ProductExtractor
from mcp_servers.browser.schemas import (
    ExtractedProductDataResult,
    OpenProductPageResult,
    PageEvidenceRecordResult,
    PageMetadataResult,
    StructuredProductDataResult,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.browser_mcp")

# Initialize MCP Server instance
server = MCPServer(
    name="webtruth-browser",
    instructions=(
        "WebTruth Browser MCP Server (Phase 2B). Investigates publicly accessible product pages, "
        "enforces a domain allowlist, extracts evidence-backed product specs, structured data, "
        "and generates cryptographic SHA-256 evidence records."
    ),
    version="0.2.0-phase2b",
)


@server.tool(
    name="open_product_page",
    description=(
        "Open an allowed public product page in headless Chromium. "
        "Returns final URL, document title, HTTP status, and capture timestamp. "
        "Enforces the domain allowlist policy."
    ),
)
async def open_product_page(url: str) -> OpenProductPageResult:
    """Open an allowed product page and return basic navigation metadata."""
    logger.info("Tool open_product_page called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    is_allowed = page_data.status_code != 403 or "not in the permitted domain allowlist" not in (page_data.error or "")

    return OpenProductPageResult(
        source_url=page_data.source_url,
        final_url=page_data.final_url,
        page_title=page_data.title or None,
        page_status=page_data.status_code,
        capture_timestamp_utc=current_utc_iso(),
        is_allowed=is_allowed,
        error=page_data.error,
    )


@server.tool(
    name="extract_product_data",
    description=(
        "Extract product name, brand, model, displayed price (preserving original currency), "
        "stock availability, technical specifications table, warranty, and return policy. "
        "Does not fabricate missing prices or convert currency to INR."
    ),
)
async def extract_product_data(url: str) -> ExtractedProductDataResult:
    """Extract product specifications and pricing facts from a public product page."""
    logger.info("Tool extract_product_data called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    if page_data.error:
        return ExtractedProductDataResult(
            source_url=url,
            capture_timestamp_utc=current_utc_iso(),
            error=page_data.error,
        )

    return ProductExtractor.extract_product_data(
        html_content=page_data.html_content,
        source_url=page_data.final_url or url,
    )


@server.tool(
    name="extract_structured_product_data",
    description=(
        "Parse Product JSON-LD (schema.org/Product) script blocks, OpenGraph (og:*) tags, "
        "and page meta tags from the requested public product page."
    ),
)
async def extract_structured_product_data(url: str) -> StructuredProductDataResult:
    """Extract JSON-LD and OpenGraph metadata from the product page."""
    logger.info("Tool extract_structured_product_data called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    if page_data.error:
        return StructuredProductDataResult(
            source_url=url,
            capture_timestamp_utc=current_utc_iso(),
            error=page_data.error,
        )

    return ProductExtractor.extract_structured_data(
        html_content=page_data.html_content,
        source_url=page_data.final_url or url,
    )


@server.tool(
    name="capture_page_evidence",
    description=(
        "Capture source URL, page title, extracted text snippets, content length, "
        "and a cryptographic SHA-256 hash of the evidence record for verifiable audit trails."
    ),
)
async def capture_page_evidence(url: str) -> PageEvidenceRecordResult:
    """Capture verifiable text snippets and generate a SHA-256 evidence record."""
    logger.info("Tool capture_page_evidence called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    if page_data.error:
        return PageEvidenceRecordResult(
            source_url=url,
            capture_timestamp_utc=current_utc_iso(),
            sha256_hash="",
            error=page_data.error,
        )

    return ProductExtractor.generate_page_evidence(
        html_content=page_data.html_content,
        source_url=page_data.final_url or url,
        page_title=page_data.title,
    )


@server.tool(
    name="inspect_page_metadata",
    description=(
        "Inspect page metadata including canonical URL, document title, all meta tags, "
        "and detected structured data schema types (e.g. Product, Offer, BreadcrumbList)."
    ),
)
async def inspect_page_metadata(url: str) -> PageMetadataResult:
    """Inspect page meta tags, canonical URL, and detected schema.org types."""
    logger.info("Tool inspect_page_metadata called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    if page_data.error:
        return PageMetadataResult(
            source_url=url,
            final_url=page_data.final_url,
            capture_timestamp_utc=current_utc_iso(),
            error=page_data.error,
        )

    return ProductExtractor.inspect_metadata(
        html_content=page_data.html_content,
        source_url=url,
        final_url=page_data.final_url,
        page_title=page_data.title,
    )
