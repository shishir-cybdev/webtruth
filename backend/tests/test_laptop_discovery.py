"""Phase 2G.6 regression tests: laptop model-token extraction, ad-tracker filtering, and discovery."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from mcp_servers.browser.identity import (
    ProductMatchStatus,
    evaluate_product_identity,
    extract_model_tokens,
)
from mcp_servers.browser.server import _is_ad_or_tracker_url, discover_product_urls


# ---------------------------------------------------------------------------
# 1. Model-Token Extraction: Strip Spec Units While Preserving Model Numbers
# ---------------------------------------------------------------------------


def test_extract_model_tokens_strips_spaced_and_unspaced_spec_units():
    tokens = extract_model_tokens(
        "DELL XPS Snapdragon X Elite - (16 GB/512 GB SSD/1 TB HDD/165 Hz/16GB/15.6 inch) 9345 Laptop",
        brand="dell",
    )
    assert "16" not in tokens
    assert "512" not in tokens
    assert "1" not in tokens
    assert "165" not in tokens
    assert "15" not in tokens
    assert "6" not in tokens
    assert "xps" in tokens
    assert "9345" in tokens


def test_extract_model_tokens_preserves_genuine_model_numbers():
    assert extract_model_tokens("Dell XPS 16", brand="dell") == ["xps", "16"]
    assert extract_model_tokens("iPhone 16", brand=None) == ["iphone", "16"]
    assert extract_model_tokens("Dell Alienware 16", brand="dell") == ["alienware", "16"]
    assert extract_model_tokens("Dell XPS 15 9530", brand="dell") == ["xps", "15", "9530"]


# ---------------------------------------------------------------------------
# 2. Dell XPS 16 Identity Matching vs XPS 13 (16 GB), Alienware 16, HP
# ---------------------------------------------------------------------------


def test_dell_xps_16_does_not_match_xps_13_with_16gb_ram():
    res = evaluate_product_identity(
        query="Dell XPS 16",
        extracted_product_name="DELL XPS Snapdragon X Elite - (16 GB/512 GB SSD/Windows 11 Home) 9345 Thin and Light Laptop",
        extracted_brand="DELL",
        expected_category="laptop",
    )
    assert res.match_status == ProductMatchStatus.MODEL_MISMATCH
    assert res.match_status != ProductMatchStatus.EXACT_MATCH
    assert res.match_status != ProductMatchStatus.RELATED_VARIANT


def test_dell_xps_16_does_not_match_alienware_16():
    res = evaluate_product_identity(
        query="Dell XPS 16",
        extracted_product_name="DELL Alienware 16 Aurora Intel Core 7 240H - (16 GB/1 TB SSD) Gaming Laptop",
        extracted_brand="DELL",
        expected_category="laptop",
    )
    assert res.match_status == ProductMatchStatus.MODEL_MISMATCH


# ---------------------------------------------------------------------------
# 3. Ad-Tracker Rejection & Discovery Slot Filtering
# ---------------------------------------------------------------------------


def test_ad_tracker_urls_rejected():
    assert _is_ad_or_tracker_url(
        "https://aax-eu-zaz.amazon.in/x/c/JKHL/https://www.amazon.in/dp/B0HM3FJ35T"
    ) is True
    assert _is_ad_or_tracker_url(
        "https://www.amazon.in/sspa/click?ie=UTF8&url=%2Fdp%2FB0HM3FJ35T"
    ) is True
    assert _is_ad_or_tracker_url(
        "https://www.amazon.in/Dell-XPS-16-9640-Laptop/dp/B0DELLXPS16"
    ) is False


@pytest.mark.anyio
async def test_dell_xps_16_discovery_rejects_hp_ads_xps13_alienware_and_survives_blocked_retailers():
    amazon_search_html = """
    <html><body>
      <a href="https://aax-eu-zaz.amazon.in/x/c/JKHL/https://www.amazon.in/dp/B0HM3FJ35T">HP OmniBook 5 AI Laptop</a>
      <a href="/sspa/click?url=/dp/B0SPONSORED">Sponsored Dell Inspiron 16</a>
      <a href="/Dell-XPS-16-9640-Laptop/dp/B0XPS169640">Dell XPS 16 9640 Intel Core Ultra 7 (16 GB/1 TB SSD) Laptop</a>
    </body></html>
    """
    flipkart_search_html = """
    <html><body>
      <a href="/dell-xps-snapdragon-x-elite-16-gb-512-gb-ssd-9345-laptop/p/itmc9a828b274988">DELL XPS Snapdragon X Elite - (16 GB/512 GB SSD) 9345 Laptop</a>
      <a href="/dell-alienware-16-aurora-gaming-laptop/p/itm5d0745cd0e132">DELL Alienware 16 Aurora Gaming Laptop</a>
      <a href="/dell-xps-16-core-ultra-9-32-gb-1-tb-ssd-9640-laptop/p/itmxps16exact">DELL XPS 16 Core Ultra 9 (32 GB/1 TB SSD) 9640 Laptop</a>
    </body></html>
    """

    async def fake_fetch(url, timeout_ms=None):
        if "amazon.in" in url:
            return SimpleNamespace(
                source_url=url,
                final_url=url,
                status_code=200,
                title="Amazon.in : Dell XPS 16",
                html_content=amazon_search_html,
                error=None,
            )
        if "flipkart.com" in url:
            return SimpleNamespace(
                source_url=url,
                final_url=url,
                status_code=200,
                title="Dell XPS 16 - Flipkart",
                html_content=flipkart_search_html,
                error=None,
            )
        # Simulate HTTP 403 on both croma.com and dell.com
        return SimpleNamespace(
            source_url=url,
            final_url=url,
            status_code=403,
            title="Access Denied",
            html_content="",
            error="HTTP 403",
        )

    with patch("mcp_servers.browser.server.browser_manager.fetch_page", side_effect=AsyncMock(side_effect=fake_fetch)):
        res = await discover_product_urls(query="Dell XPS 16", category="laptop", max_results=4)

    urls = [item.url for item in res.discovered_urls]
    assert len(urls) == 2
    assert "https://www.amazon.in/Dell-XPS-16-9640-Laptop/dp/B0XPS169640" in urls
    assert "https://www.flipkart.com/dell-xps-16-core-ultra-9-32-gb-1-tb-ssd-9640-laptop/p/itmxps16exact" in urls
    # Blocked retailers recorded gracefully without blocking Amazon/Flipkart
    assert any("croma.com" in b for b in res.blocked_sources)
    assert any("dell.com" in b for b in res.blocked_sources)


# ---------------------------------------------------------------------------
# 4. Preserve iPhone 16 Flow
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_iphone_16_discovery_still_matches_exact_and_separates_variants():
    amazon_search_html = """
    <html><body>
      <a href="/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y">Apple iPhone 16 (128 GB) - Black</a>
    </body></html>
    """
    flipkart_search_html = """
    <html><body>
      <a href="/apple-iphone-16e-white-128-gb/p/itm7971f594b0906">Apple iPhone 16e (White, 128 GB)</a>
      <a href="/apple-iphone-16-plus-black-256-gb/p/itma302a45837ec4">Apple iPhone 16 Plus (Black, 256 GB)</a>
    </body></html>
    """

    async def fake_fetch(url, timeout_ms=None):
        if "amazon.in" in url:
            return SimpleNamespace(source_url=url, final_url=url, status_code=200, title="Amazon", html_content=amazon_search_html, error=None)
        if "flipkart.com" in url:
            return SimpleNamespace(source_url=url, final_url=url, status_code=200, title="Flipkart", html_content=flipkart_search_html, error=None)
        return SimpleNamespace(source_url=url, final_url=url, status_code=403, title="", html_content="", error="HTTP 403")

    with patch("mcp_servers.browser.server.browser_manager.fetch_page", side_effect=AsyncMock(side_effect=fake_fetch)):
        res = await discover_product_urls(query="iPhone 16", category="smartphone", max_results=4)

    urls = [item.url for item in res.discovered_urls]
    assert urls[0] == "https://www.amazon.in/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y"

    # Verify exact vs variant classification remains intact
    exact = evaluate_product_identity("iPhone 16", "Apple iPhone 16 (128 GB) - Black", expected_category="smartphone")
    v16e = evaluate_product_identity("iPhone 16", "Apple iPhone 16e (White, 128 GB)", extracted_brand="APPLE", expected_category="smartphone")
    v16p = evaluate_product_identity("iPhone 16", "Apple iPhone 16 Plus (Black, 256 GB)", extracted_brand="APPLE", expected_category="smartphone")
    assert exact.match_status == ProductMatchStatus.EXACT_MATCH
    assert v16e.match_status == ProductMatchStatus.RELATED_VARIANT
    assert v16p.match_status == ProductMatchStatus.RELATED_VARIANT
