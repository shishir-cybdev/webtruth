"""Regression tests for camera spec stripping and Amazon image/title anchor merging."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from mcp_servers.browser.identity import (
    ProductMatchStatus,
    evaluate_product_identity,
    extract_model_tokens,
)
from mcp_servers.browser.server import discover_product_urls


# ---------------------------------------------------------------------------
# 1-5: Camera Megapixel Spec Handling & Known Variant Suffix Matching
# ---------------------------------------------------------------------------


def test_13mp_rear_camera_cannot_match_model_13():
    tokens = extract_model_tokens("OnePlus N6X 13MP Rear Camera 5000 mAh", brand="oneplus")
    assert "13" not in tokens
    assert "13mp" not in tokens


def test_50mp_and_200mp_camera_cannot_match_model_numbers():
    tokens_50 = extract_model_tokens("Redmi 50MP Camera 5000 mAh", brand="redmi")
    tokens_200 = extract_model_tokens("Samsung Galaxy 200 Megapixel Camera", brand="samsung")
    assert "50" not in tokens_50
    assert "50mp" not in tokens_50
    assert "200" not in tokens_200


def test_oneplus_n6x_with_13mp_camera_is_model_mismatch_not_related_variant():
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus N6X (Burgundy Red, 128 GB) 13MP Rear Camera 7000 mAh",
        extracted_brand="OnePlus",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.MODEL_MISMATCH
    assert res.match_status != ProductMatchStatus.RELATED_VARIANT


def test_oneplus_13s_still_classified_as_related_variant():
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus 13s 5G (Black Velvet, 512 GB)",
        extracted_brand="OnePlus",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.RELATED_VARIANT


def test_genuine_oneplus_13_remains_exact_match():
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus 13 (Arctic Dawn, 12GB RAM, 256GB Storage)",
        extracted_brand="OnePlus",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.EXACT_MATCH


# ---------------------------------------------------------------------------
# 6-9: Amazon Image/Title Anchor Merging, Deduplication & iPhone 16 Preservation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_amazon_image_and_title_anchors_merged_and_deduplicated():
    amazon_html = """
    <html><body>
      <a href="/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13"><img src="img.jpg" /></a>
      <a href="/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13">OnePlus 13 | Snapdragon 8 Elite | 12GB+256GB</a>
      <a href="/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13">(49)</a>
      <a href="/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13">₹69,999</a>
      <a href="/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13"></a>
    </body></html>
    """
    flipkart_html = """
    <html><body>
      <a href="/oneplus-n6x-burgundy-red-128-gb/p/itm4be54d70a3bed">OnePlus N6X (Burgundy Red, 128 GB) 13MP Rear Camera</a>
      <a href="/oneplus-13s-5g-black-velvet-256-gb/p/itmb6d10cf953b5d">OnePlus 13s 5G (Black Velvet, 256 GB)</a>
    </body></html>
    """

    async def fake_fetch(url, timeout_ms=None):
        if "amazon.in" in url:
            return SimpleNamespace(source_url=url, final_url=url, status_code=200, title="Amazon", html_content=amazon_html, error=None)
        if "flipkart.com" in url:
            return SimpleNamespace(source_url=url, final_url=url, status_code=200, title="Flipkart", html_content=flipkart_html, error=None)
        return SimpleNamespace(source_url=url, final_url=url, status_code=403, title="", html_content="", error="HTTP 403")

    with patch("mcp_servers.browser.server.browser_manager.fetch_page", side_effect=AsyncMock(side_effect=fake_fetch)):
        res = await discover_product_urls(query="OnePlus 13", category="smartphone", max_results=4)

    urls = [item.url for item in res.discovered_urls]
    # Exact OnePlus 13 on Amazon is retained with title text (not shadowed by empty image anchor) and deduplicated
    assert urls.count("https://www.amazon.in/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13") == 1
    assert urls[0] == "https://www.amazon.in/OnePlus-Snapdragon-Smarter-Lifetime-Warranty/dp/B0ONEPLUS13"
    assert "OnePlus 13" in (res.discovered_urls[0].link_text or "")
    # OnePlus N6X with 13MP camera is rejected and does not enter discovered_urls
    assert "https://www.flipkart.com/oneplus-n6x-burgundy-red-128-gb/p/itm4be54d70a3bed" not in urls
    # OnePlus 13s variant is still preserved after exact match
    assert "https://www.flipkart.com/oneplus-13s-5g-black-velvet-256-gb/p/itmb6d10cf953b5d" in urls


@pytest.mark.anyio
async def test_iphone_16_matching_continues_to_work():
    amazon_html = """
    <html><body>
      <a href="/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y"></a>
      <a href="/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y">Apple iPhone 16 (128 GB) - Black</a>
    </body></html>
    """

    async def fake_fetch(url, timeout_ms=None):
        if "amazon.in" in url:
            return SimpleNamespace(source_url=url, final_url=url, status_code=200, title="Amazon", html_content=amazon_html, error=None)
        return SimpleNamespace(source_url=url, final_url=url, status_code=403, title="", html_content="", error="HTTP 403")

    with patch("mcp_servers.browser.server.browser_manager.fetch_page", side_effect=AsyncMock(side_effect=fake_fetch)):
        res = await discover_product_urls(query="iPhone 16", category="smartphone", max_results=4)

    assert len(res.discovered_urls) == 1
    assert res.discovered_urls[0].url == "https://www.amazon.in/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y"
    assert res.discovered_urls[0].link_text == "Apple iPhone 16 (128 GB) - Black"
