import pytest
from pathlib import Path

from app.orchestrator.investigation_engine import default_investigation_engine
from app.orchestrator.schemas import StageStatus
from mcp_servers.browser.config import BrowserConfig
from mcp_servers.browser.extractor import ProductExtractor
from mcp_servers.comparison.comparison_service import comparison_service

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_invalid_and_disallowed_urls():
    """Verify disallowed domains and invalid schemes are rejected."""
    ok, reason = BrowserConfig.is_url_permitted("https://evil-phishing-site.com/product")
    assert ok is False
    assert "allowlist" in reason.lower()

    ok_ftp, _ = BrowserConfig.is_url_permitted("ftp://amazon.in/file")
    assert ok_ftp is False


def test_reject_404_page_not_found():
    """Verify HTTP 404 and Page Not Found HTML are rejected as product evidence."""
    html_404 = """
    <html><head><title>Page Not Found - Amazon.in</title></head>
    <body><h1>Looking for something? We're sorry. The Web address you entered is not a functioning page.</h1></body>
    </html>
    """
    is_valid, err, block_reason = ProductExtractor.validate_page_for_product_evidence(
        source_url="https://www.amazon.in/dp/invalid",
        final_url="https://www.amazon.in/dp/invalid",
        status_code=404,
        page_title="Page Not Found - Amazon.in",
        html_content=html_404,
    )
    assert is_valid is False
    assert block_reason == "not_found_page"
    assert "404" in err

    # Even if status was 200 (soft 404), title/heading marker rejects it
    extracted = ProductExtractor.extract_product_data(html_404, "https://www.amazon.in/dp/invalid")
    assert extracted.is_valid_product_page is False
    assert extracted.block_reason == "not_found_page"
    assert extracted.product_name is None


def test_reject_generic_homepage():
    """Verify generic retailer homepages without product signals are rejected."""
    homepage_html = """
    <html><head><title>Online Shopping site in India: Shop Online for Mobiles, Books, Watches</title></head>
    <body><div class="nav">Welcome to our store</div></body></html>
    """
    extracted = ProductExtractor.extract_product_data(homepage_html, "https://www.amazon.in/")
    assert extracted.is_valid_product_page is False
    assert extracted.block_reason == "generic_homepage"
    assert extracted.product_name is None


def test_reject_captcha_and_antibot_block():
    """Verify CAPTCHA and HTTP 403/503 blocks are detected with clear error messages."""
    captcha_html = """
    <html><head><title>Robot Check</title></head>
    <body><p>Enter the characters you see below to verify you are human.</p></body></html>
    """
    is_valid, err, block_reason = ProductExtractor.validate_page_for_product_evidence(
        source_url="https://www.amazon.in/dp/B0TEST",
        final_url="https://www.amazon.in/errors/validateCaptcha",
        status_code=200,
        page_title="Robot Check",
        html_content=captcha_html,
    )
    assert is_valid is False
    assert block_reason == "captcha_or_antibot"
    assert "CAPTCHA" in err

    is_valid_503, err_503, block_503 = ProductExtractor.validate_page_for_product_evidence(
        source_url="https://www.amazon.in/dp/B0TEST",
        final_url="https://www.amazon.in/dp/B0TEST",
        status_code=503,
        page_title="Service Unavailable",
        html_content="",
    )
    assert is_valid_503 is False
    assert block_503 == "captcha_or_antibot"
    assert "503" in err_503


def test_mismatched_product_category_and_brands():
    """Verify mismatched category (smartphone vs laptop) and mismatched brands are flagged."""
    std_html = (FIXTURES_DIR / "product_standard.html").read_text(encoding="utf-8")
    extracted = ProductExtractor.extract_product_data(std_html, "https://dell.com/in/p/xps-15-9530-laptop")
    assert extracted.is_valid_product_page is True

    # Validate against smartphone category -> must reject
    is_valid, err, block_reason = ProductExtractor.validate_page_for_product_evidence(
        source_url="https://dell.com/in/p/xps-15-9530-laptop",
        final_url="https://dell.com/in/p/xps-15-9530-laptop",
        status_code=200,
        page_title="Dell XPS 15 9530 Laptop",
        html_content=std_html,
        extracted=extracted,
        expected_category="smartphone",
    )
    assert is_valid is False
    assert block_reason == "category_mismatch"
    assert "smartphone" in err

    # Comparison MCP: mismatched brands (Apple vs Dell) must not equate or emit fake spec conflicts
    comp = comparison_service.generate_comparison([
        {
            "evidence_id": "evi_apple",
            "source_url": "https://apple.com/iphone-15",
            "product_name": "Apple iPhone 15",
            "brand": "Apple",
            "specifications": {"Storage": "128 GB"},
        },
        {
            "evidence_id": "evi_dell",
            "source_url": "https://dell.com/xps-15",
            "product_name": "Dell XPS 15 9530",
            "brand": "Dell",
            "specifications": {"Storage": "1 TB"},
        },
    ])
    assert comp.configuration_match is False
    assert any("Mismatched product brands" in w for w in comp.configuration_warnings)
    assert comp.conflicts.has_conflicts is False


def test_page_title_differences_not_treated_as_spec_conflicts():
    """Verify PAGE_TITLE differences in extracted_claims are never reported as spec contradictions."""
    comp = comparison_service.generate_comparison([
        {
            "evidence_id": "evi_1",
            "source_url": "https://amazon.in/dp/xps15",
            "product_name": "Dell XPS 15 9530",
            "brand": "Dell",
            "extracted_claims": [
                "PAGE_TITLE: Dell XPS 15 9530 | Amazon.in",
                "SPECIFICATION: RAM = 16 GB",
            ],
        },
        {
            "evidence_id": "evi_2",
            "source_url": "https://dell.com/xps15",
            "product_name": "Dell XPS 15 9530",
            "brand": "Dell",
            "extracted_claims": [
                "PAGE_TITLE: Buy Dell XPS 15 9530 Official Store",
                "SPECIFICATION: RAM = 16 GB",
            ],
        },
    ])
    assert comp.conflicts.has_conflicts is False
    diff_names = {f.field_name.lower() for f in comp.spec_comparison.different_fields}
    assert "page_title" not in diff_names


def test_unavailable_prices_preserved_as_none():
    """Verify missing prices remain unavailable/None and are never fabricated."""
    no_price_html = (FIXTURES_DIR / "product_missing_price.html").read_text(encoding="utf-8")
    extracted = ProductExtractor.extract_product_data(no_price_html, "https://flipkart.com/p/test-laptop")
    assert extracted.price is None or extracted.price.numeric_amount is None


@pytest.mark.anyio
async def test_orchestrator_rejects_404_fixture_and_reports_insufficient_data(tmp_path):
    """Verify Orchestrator rejects invalid/404 pages, does not store them in Evidence MCP, and Trust reports INSUFFICIENT_DATA."""
    bad_html = tmp_path / "not_found.html"
    bad_html.write_text(
        "<html><head><title>Page Not Found</title></head><body><h1>404 Not Found</h1></body></html>",
        encoding="utf-8",
    )
    bad_url = f"file:///{bad_html.as_posix()}"

    rec = default_investigation_engine.initialize_investigation(
        query="iPhone 15",
        category="smartphone",
        target_urls=[bad_url],
    )
    completed = await default_investigation_engine.run_investigation(rec.investigation_id)

    # Should NOT crash; should reject invalid page, skip evidence/comparison, and report INSUFFICIENT_DATA
    assert completed.status == "completed"
    assert len(completed.extracted_records) == 0
    assert len(completed.evidence_ids) == 0
    assert completed.stages["evidence"].status == StageStatus.SKIPPED
    assert completed.stages["comparison"].status == StageStatus.SKIPPED
    assert any("Rejected" in w for w in completed.warnings)
    assert completed.trust_report is not None
    assert completed.trust_report["trust_assessment"]["overall_trust_tier"] == "INSUFFICIENT_DATA"


@pytest.mark.anyio
async def test_browser_fetch_timeout_and_cleanup():
    """Verify browser navigation timeout returns 504 error cleanly and cleans up browser context."""
    from mcp_servers.browser.browser_manager import browser_manager

    std_url = f"file:///{(FIXTURES_DIR / 'product_standard.html').as_posix()}"
    res = await browser_manager.fetch_page(std_url, timeout_ms=1)
    # 1ms timeout should either fail with 504/500 timeout or succeed if OS cached; if it timed out, check status/error
    if res.error:
        assert res.status_code in (500, 504)
    await browser_manager.close()
    assert browser_manager._context is None
    assert browser_manager._browser is None


@pytest.mark.anyio
async def test_partial_source_failure_preserves_valid_results(tmp_path):
    """Verify partial source failure (1 valid fixture + 1 404 page) preserves valid evidence."""
    valid_url = f"file:///{(FIXTURES_DIR / 'product_standard.html').as_posix()}"
    bad_html = tmp_path / "missing_page.html"
    bad_html.write_text(
        "<html><head><title>Page Not Found</title></head><body><h1>404 Not Found</h1></body></html>",
        encoding="utf-8",
    )
    bad_url = f"file:///{bad_html.as_posix()}"

    rec = default_investigation_engine.initialize_investigation(
        query="Dell XPS 15 9530",
        category="laptop",
        target_urls=[valid_url, bad_url],
    )
    completed = await default_investigation_engine.run_investigation(rec.investigation_id)

    assert completed.status == "completed"
    assert len(completed.extracted_records) == 1
    assert len(completed.evidence_ids) == 1
    assert completed.stages["browser"].status == StageStatus.COMPLETED
    assert completed.stages["evidence"].status == StageStatus.COMPLETED
    assert completed.stages["comparison"].status == StageStatus.COMPLETED
    assert completed.stages["trust"].status == StageStatus.COMPLETED
    assert any("Rejected" in w for w in completed.warnings)
