import logging
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

from mcp_servers.browser.browser_manager import browser_manager
from mcp_servers.browser.config import BrowserConfig
from mcp_servers.browser.extractor import ProductExtractor
from mcp_servers.browser.schemas import (
    DiscoverProductUrlsResult,
    DiscoveredUrlItem,
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
        "Returns final URL, document title, HTTP status, validation status, and capture timestamp. "
        "Enforces the domain allowlist policy and rejects 404/CAPTCHA/generic homepages."
    ),
)
async def open_product_page(url: str) -> OpenProductPageResult:
    """Open an allowed product page and return basic navigation metadata."""
    logger.info("Tool open_product_page called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    is_allowed = page_data.status_code != 403 or "not in the permitted domain allowlist" not in (page_data.error or "")
    is_valid, val_err, block_reason = ProductExtractor.validate_page_for_product_evidence(
        source_url=url,
        final_url=page_data.final_url,
        status_code=page_data.status_code,
        page_title=page_data.title,
        html_content=page_data.html_content,
    )
    if page_data.error:
        is_valid = False
        block_reason = block_reason or "fetch_error"

    return OpenProductPageResult(
        source_url=page_data.source_url,
        final_url=page_data.final_url,
        page_title=page_data.title or None,
        page_status=page_data.status_code,
        capture_timestamp_utc=current_utc_iso(),
        is_allowed=is_allowed,
        is_valid_product_page=is_valid,
        block_reason=block_reason,
        error=page_data.error or val_err,
    )


@server.tool(
    name="extract_product_data",
    description=(
        "Extract product name, brand, model, displayed price (preserving original currency), "
        "stock availability, technical specifications table, warranty, and return policy. "
        "Validates HTTP status and page identity; rejects 404s, CAPTCHAs, and generic homepages."
    ),
)
async def extract_product_data(url: str, expected_category: Optional[str] = None) -> ExtractedProductDataResult:
    """Extract product specifications and pricing facts from a public product page."""
    logger.info("Tool extract_product_data called with url=%s", url)
    page_data = await browser_manager.fetch_page(url)

    if page_data.error:
        return ExtractedProductDataResult(
            source_url=url,
            capture_timestamp_utc=current_utc_iso(),
            is_valid_product_page=False,
            validation_error=page_data.error,
            block_reason="fetch_error",
            error=page_data.error,
        )

    extracted = ProductExtractor.extract_product_data(
        html_content=page_data.html_content,
        source_url=page_data.final_url or url,
    )
    is_valid, val_err, block_reason = ProductExtractor.validate_page_for_product_evidence(
        source_url=url,
        final_url=page_data.final_url or url,
        status_code=page_data.status_code,
        page_title=page_data.title,
        html_content=page_data.html_content,
        extracted=extracted,
        expected_category=expected_category,
    )
    extracted.is_valid_product_page = is_valid
    extracted.validation_error = val_err
    extracted.block_reason = block_reason
    if not is_valid and block_reason in ("not_found_page", "captcha_or_antibot", "generic_homepage", "http_error"):
        extracted.product_name = None
    return extracted


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


@server.tool(
    name="discover_product_urls",
    description=(
        "Legitimately discover permitted public product URLs from allowed retailer search pages. "
        "Only returns product links actually observed in the DOM. Never guesses or constructs product URLs. "
        "Respects CAPTCHAs and anti-bot blocks."
    ),
)
async def discover_product_urls(
    query: str,
    category: Optional[str] = None,
    max_results: int = 4,
) -> DiscoverProductUrlsResult:
    """Discover real public product URLs without guessing or constructing slugs."""
    logger.info("Tool discover_product_urls called with query='%s', category=%s", query, category)
    search_term = f"{query} {category}".strip() if category and category.lower() not in query.lower() else query.strip()
    encoded = quote_plus(search_term)

    search_endpoints = [
        ("amazon.in", f"https://www.amazon.in/s?k={encoded}", ("/dp/", "/gp/product/")),
        ("croma.com", f"https://www.croma.com/searchB?q={encoded}", ("/p/",)),
        ("flipkart.com", f"https://www.flipkart.com/search?q={encoded}", ("/p/",)),
    ]

    discovered: list[DiscoveredUrlItem] = []
    seen_urls: set[str] = set()
    blocked_sources: list[str] = []
    notes: list[str] = []

    for domain, search_url, product_markers in search_endpoints:
        if len(discovered) >= max_results:
            break

        page_data = await browser_manager.fetch_page(search_url)
        if page_data.error or (page_data.status_code and page_data.status_code >= 400):
            reason = page_data.error or f"HTTP {page_data.status_code}"
            blocked_sources.append(f"{domain}: {reason}")
            continue

        is_valid, val_err, block_reason = ProductExtractor.validate_page_for_product_evidence(
            source_url=search_url,
            final_url=page_data.final_url,
            status_code=page_data.status_code,
            page_title=page_data.title,
            html_content=page_data.html_content,
        )
        if block_reason == "captcha_or_antibot":
            blocked_sources.append(f"{domain}: {val_err}")
            continue

        soup = BeautifulSoup(page_data.html_content or "", "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            abs_url = urljoin(page_data.final_url or search_url, href)
            parsed = urlparse(abs_url)
            if parsed.scheme not in ("http", "https"):
                continue
            allowed, _ = BrowserConfig.is_url_permitted(abs_url)
            if not allowed:
                continue
            if any(m in parsed.path for m in product_markers):
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    link_text = a.get_text(" ", strip=True)[:120] or None
                    discovered.append(
                        DiscoveredUrlItem(url=clean_url, domain=domain, link_text=link_text)
                    )
                    if len(discovered) >= max_results:
                        break

    if not discovered:
        notes.append(
            "No product URLs could be legitimately discovered from permitted search endpoints. "
            "Supply explicit public product URLs or use local HTML test fixtures."
        )
    else:
        notes.append(f"Legitimately discovered {len(discovered)} candidate product URL(s) from search DOM.")

    return DiscoverProductUrlsResult(
        query=query,
        category=category,
        discovered_urls=discovered,
        blocked_sources=blocked_sources,
        discovery_notes=notes,
    )
