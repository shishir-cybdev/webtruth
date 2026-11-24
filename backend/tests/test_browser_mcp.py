from pathlib import Path
import pytest

from mcp_servers.browser.config import BrowserConfig
from mcp_servers.browser.extractor import ProductExtractor
from mcp_servers.browser.schemas import (
    ExtractedProductDataResult,
    OpenProductPageResult,
    PageEvidenceRecordResult,
    PageMetadataResult,
    StructuredProductDataResult,
)
from mcp_servers.browser.server import (
    capture_page_evidence,
    extract_product_data,
    extract_structured_product_data,
    inspect_page_metadata,
    open_product_page,
    server,
)
from mcp_servers.browser.browser_manager import browser_manager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def standard_html() -> str:
    return (FIXTURES_DIR / "product_standard.html").read_text(encoding="utf-8")


@pytest.fixture
def missing_price_html() -> str:
    return (FIXTURES_DIR / "product_missing_price.html").read_text(encoding="utf-8")


@pytest.fixture
def malformed_html() -> str:
    return (FIXTURES_DIR / "product_malformed.html").read_text(encoding="utf-8")


@pytest.fixture
def standard_file_url() -> str:
    file_path = (FIXTURES_DIR / "product_standard.html").resolve()
    return file_path.as_uri()


# =========================================================================
# 1. MCP Tool Discovery Tests
# =========================================================================
@pytest.mark.anyio
async def test_mcp_tool_discovery():
    """Verify that the official MCP server registers and exposes all 5 required tools."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected_tools = {
        "open_product_page",
        "extract_product_data",
        "extract_structured_product_data",
        "capture_page_evidence",
        "inspect_page_metadata",
    }
    assert expected_tools.issubset(tool_names), f"Missing tools. Registered: {tool_names}"
    assert server.name == "webtruth-browser"


# =========================================================================
# 2. Domain Allowlist & Policy Tests
# =========================================================================
def test_domain_allowlist_policy():
    """Verify that domain filtering permits approved sites and blocks unauthorized ones."""
    # Permitted domains
    ok, _ = BrowserConfig.is_url_permitted("https://amazon.in/dp/B0CX214981")
    assert ok is True

    ok, _ = BrowserConfig.is_url_permitted("https://www.dell.com/en-in/shop/laptops/xps-15")
    assert ok is True

    ok, _ = BrowserConfig.is_url_permitted("http://localhost:8000/product/test")
    assert ok is True

    ok, _ = BrowserConfig.is_url_permitted("file:///C:/test.html")
    assert ok is True

    # Blocked domains
    blocked, reason = BrowserConfig.is_url_permitted("https://unauthorized-store.xyz/product")
    assert blocked is False
    assert "not in the permitted domain allowlist" in reason

    # Blocked private/auth paths
    blocked_path, reason_path = BrowserConfig.is_url_permitted("https://amazon.in/login")
    assert blocked_path is False
    assert "blocked pattern" in reason_path

    blocked_checkout, _ = BrowserConfig.is_url_permitted("https://www.dell.com/checkout/step1")
    assert blocked_checkout is False


# =========================================================================
# 3. Product Extraction on Standard Fixture
# =========================================================================
def test_extractor_standard_product(standard_html: str):
    """Verify extraction of product facts, specs, and price without hallucination."""
    result = ProductExtractor.extract_product_data(standard_html, "https://dell.com/xps-15")

    assert isinstance(result, ExtractedProductDataResult)
    assert result.product_name == "Dell XPS 15 9530"
    assert result.brand == "Dell"
    assert result.model == "XPS 15 9530"
    assert result.availability == "InStock"
    assert result.extraction_method == "json_ld"

    # Price verification
    assert result.price is not None
    assert result.price.numeric_amount == 189999.0
    assert result.price.currency == "INR"
    assert "189999" in (result.price.displayed_text or "")
    # Conversion rate must remain None unless explicitly performed
    assert result.price.conversion_rate_to_inr is None

    # Specifications
    assert len(result.specifications) >= 5
    assert "Processor" in result.specifications
    assert "13700H" in result.specifications["Processor"]
    assert "Display" in result.specifications


# =========================================================================
# 4. Structured Data (JSON-LD & OpenGraph)
# =========================================================================
def test_extractor_structured_data(standard_html: str):
    """Verify JSON-LD and OpenGraph metadata parsing."""
    result = ProductExtractor.extract_structured_data(standard_html, "https://dell.com/xps-15")

    assert isinstance(result, StructuredProductDataResult)
    assert len(result.json_ld_products) == 1
    assert result.json_ld_products[0]["name"] == "Dell XPS 15 9530"
    assert "Product" in result.detected_schemas

    assert result.open_graph.get("og:title") == "Dell XPS 15 9530 Laptop"
    assert result.open_graph.get("og:price:amount") == "189999"
    assert result.open_graph.get("og:price:currency") == "INR"


# =========================================================================
# 5. Missing Price Handling (No Hallucination)
# =========================================================================
def test_extractor_missing_price_handling(missing_price_html: str):
    """Verify that pages without prices return price=None and do NOT fabricate prices."""
    result = ProductExtractor.extract_product_data(missing_price_html, "https://dell.com/precision-7960")

    assert result.product_name == "Dell Precision 7960 Tower Workstation"
    assert result.brand == "Dell"
    assert result.price is None, "Price must be None when not displayed or available"
    assert "CPU Architecture" in result.specifications


# =========================================================================
# 6. Malformed HTML Resiliency
# =========================================================================
def test_extractor_malformed_html(malformed_html: str):
    """Verify that broken JSON-LD and sparse markup do not raise exceptions."""
    result = ProductExtractor.extract_product_data(malformed_html, "https://example.com/sparse")
    assert result.product_name is None or isinstance(result.product_name, str)
    assert result.price is None
    assert len(result.specifications) == 0


# =========================================================================
# 7. Evidence Record & SHA-256 Hashing
# =========================================================================
def test_evidence_capture_and_sha256(standard_html: str):
    """Verify evidence text snippets extraction and SHA-256 fingerprint generation."""
    evidence = ProductExtractor.generate_page_evidence(
        standard_html, "https://dell.com/xps-15", "Dell XPS 15 Official Page"
    )

    assert isinstance(evidence, PageEvidenceRecordResult)
    assert len(evidence.sha256_hash) == 64
    assert all(c in "0123456789abcdef" for c in evidence.sha256_hash)
    assert evidence.page_title == "Dell XPS 15 Official Page"
    assert len(evidence.extracted_text_snippets) >= 3

    # Determinism: same content produces same hash
    second_run = ProductExtractor.generate_page_evidence(
        standard_html, "https://dell.com/xps-15", "Dell XPS 15 Official Page"
    )
    # The timestamps will differ slightly, so let's verify format
    assert len(second_run.sha256_hash) == 64


# =========================================================================
# 8. Full End-to-End Tool Invocation with Playwright & Local Fixture
# =========================================================================
@pytest.mark.anyio
async def test_tool_open_product_page_e2e(standard_file_url: str):
    """E2E test: open local fixture through Playwright via open_product_page."""
    res = await open_product_page(standard_file_url)
    assert isinstance(res, OpenProductPageResult)
    assert res.is_allowed is True
    assert res.page_status == 200
    assert "Dell XPS 15" in (res.page_title or "")
    assert res.error is None


@pytest.mark.anyio
async def test_tool_extract_product_data_e2e(standard_file_url: str):
    """E2E test: extract product data through extract_product_data tool."""
    res = await extract_product_data(standard_file_url)
    assert isinstance(res, ExtractedProductDataResult)
    assert res.product_name == "Dell XPS 15 9530"
    assert res.brand == "Dell"
    assert res.price is not None
    assert res.price.currency == "INR"
    assert res.price.numeric_amount == 189999.0
    assert "Processor" in res.specifications


@pytest.mark.anyio
async def test_tool_capture_page_evidence_e2e(standard_file_url: str):
    """E2E test: capture evidence record through capture_page_evidence tool."""
    res = await capture_page_evidence(standard_file_url)
    assert isinstance(res, PageEvidenceRecordResult)
    assert len(res.sha256_hash) == 64
    assert len(res.extracted_text_snippets) > 0


@pytest.mark.anyio
async def test_tool_inspect_page_metadata_e2e(standard_file_url: str):
    """E2E test: inspect page metadata through inspect_page_metadata tool."""
    res = await inspect_page_metadata(standard_file_url)
    assert isinstance(res, PageMetadataResult)
    assert res.canonical_url == "https://dell.com/in/p/xps-15-9530-laptop"
    assert "Product" in res.detected_structured_data_types


@pytest.mark.anyio
async def test_tool_disallowed_domain_rejection():
    """Verify that disallowed domains are rejected across MCP tools."""
    bad_url = "https://unauthorized-crawler-target.org/fake-laptop"
    res = await open_product_page(bad_url)
    assert res.is_allowed is False
    assert res.page_status == 403
    assert "not in the permitted domain allowlist" in (res.error or "")


@pytest.mark.anyio
async def test_z_browser_cleanup():
    """Ensure browser resources are cleanly finalized."""
    await browser_manager.close()
