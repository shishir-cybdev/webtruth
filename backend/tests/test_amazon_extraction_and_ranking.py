"""Regression tests for Amazon title/price extraction and exact-model discovery ranking."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from mcp_servers.browser.extractor import ProductExtractor
from mcp_servers.browser.identity import ProductMatchStatus, evaluate_product_identity
from mcp_servers.browser.server import discover_product_urls, score_discovered_candidate


AMAZON_IPHONE_16_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Apple iPhone 16 (128 GB) - Black : Amazon.in: Electronics</title>
</head>
<body>
  <div id="cart-modal" class="attach-warranty-modal">
    <h1 class="a-size-medium">Add to your order</h1>
    <div class="a-price protection-plan-price">
      <span class="price">₹11,999.00</span>
    </div>
    <span>AppleCare+ Protection Plan</span>
  </div>

  <div id="ppd">
    <h1 id="title" class="a-size-large a-spacing-none">
      <span id="productTitle" class="a-size-large product-title-word-break">
        Apple iPhone 16 (128 GB) - Black
      </span>
    </h1>

    <div id="corePriceDisplay_desktop_feature_div">
      <span class="a-price aok-align-center reinventPricePriceToPayMargin priceToPay">
        <span class="a-offscreen">₹79,900.00</span>
      </span>
      <span class="a-price a-text-price" data-a-strike="true">
        <span class="a-offscreen">₹89,900.00</span>
      </span>
    </div>

    <div id="emi-box" class="emi-installment">
      <span class="price">₹3,874/mo No Cost EMI</span>
    </div>
  </div>
</body>
</html>
"""


AMAZON_MISSING_PRICE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Apple iPhone 16 (128 GB) - Black : Amazon.in: Electronics</title>
</head>
<body>
  <div id="cart-modal">
    <h1>Add to your order</h1>
    <span class="price protection-plan">₹11,999.00</span>
  </div>
  <h1 id="title"><span id="productTitle">Apple iPhone 16 (128 GB) - Black</span></h1>
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-price a-text-price" data-a-strike="true">
      <span class="a-offscreen">₹89,900.00</span>
    </span>
    <span class="price">₹3,874 per month No Cost EMI</span>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 1-4: Amazon Title & Price Extraction Tests
# ---------------------------------------------------------------------------


def test_amazon_modal_h1_does_not_override_product_title():
    res = ProductExtractor.extract_product_data(
        AMAZON_IPHONE_16_HTML,
        "https://www.amazon.in/iPhone-16-128-GB-Control/dp/B0DGJHBX5Y",
    )
    assert res.product_name == "Apple iPhone 16 (128 GB) - Black"
    assert res.product_name != "Add to your order"
    assert res.is_valid_product_page is True


def test_amazon_upsell_and_strike_and_emi_prices_not_selected():
    res = ProductExtractor.extract_product_data(
        AMAZON_IPHONE_16_HTML,
        "https://www.amazon.in/iPhone-16-128-GB-Control/dp/B0DGJHBX5Y",
    )
    assert res.price is not None
    assert res.price.numeric_amount != 11999.0  # upsell/protection plan
    assert res.price.numeric_amount != 89900.0  # crossed-out MRP
    assert res.price.numeric_amount != 3874.0   # EMI installment


def test_amazon_correct_main_product_price_extracted():
    res = ProductExtractor.extract_product_data(
        AMAZON_IPHONE_16_HTML,
        "https://www.amazon.in/iPhone-16-128-GB-Control/dp/B0DGJHBX5Y",
    )
    assert res.price is not None
    assert res.price.numeric_amount == 79900.0
    assert res.price.currency == "INR"
    assert res.price.displayed_text == "₹79,900.00"


def test_missing_main_price_returns_null_with_warning():
    res = ProductExtractor.extract_product_data(
        AMAZON_MISSING_PRICE_HTML,
        "https://www.amazon.in/iPhone-16-128-GB-Control/dp/B0DGJHBX5Y",
    )
    assert res.product_name == "Apple iPhone 16 (128 GB) - Black"
    assert res.price is None
    assert len(res.extraction_warnings) >= 1


# ---------------------------------------------------------------------------
# 5-9: Token-Aware Product Identity Matching for iPhone 16 Family
# ---------------------------------------------------------------------------


def test_iphone_16_exact_model_matching():
    res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16 (128 GB) - Black",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.EXACT_MATCH


def test_iphone_16e_classified_as_related_variant():
    res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16e (White, 128 GB)",
        extracted_brand="APPLE",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.RELATED_VARIANT


def test_iphone_16_plus_classified_as_related_variant():
    res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16 Plus (Black, 256 GB)",
        extracted_brand="APPLE",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.RELATED_VARIANT


def test_iphone_16_pro_and_pro_max_classified_separately():
    pro_res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16 Pro (256 GB)",
        extracted_brand="APPLE",
        expected_category="smartphone",
    )
    promax_res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16 Pro Max (256 GB)",
        extracted_brand="APPLE",
        expected_category="smartphone",
    )
    assert pro_res.match_status == ProductMatchStatus.RELATED_VARIANT
    assert promax_res.match_status == ProductMatchStatus.RELATED_VARIANT


def test_accessory_links_rejected():
    res = evaluate_product_identity(
        query="iPhone 16",
        extracted_product_name="Apple iPhone 16 Silicone Case with MagSafe",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.ACCESSORY


# ---------------------------------------------------------------------------
# 10: Discovery Ranking Prioritizes Exact Matches Before Variants & Accessories
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_discovery_ranks_exact_listings_before_variants_and_accessories():
    flipkart_search_html = """
    <html><body>
      <a href="/apple-iphone-16e-white-128-gb/p/itm7971f594b0906">Apple iPhone 16e (White, 128 GB)</a>
      <a href="/apple-iphone-16-plus-black-256-gb/p/itma302a45837ec4">Apple iPhone 16 Plus (Black, 256 GB)</a>
      <a href="/apple-iphone-16-pro-max-256-gb/p/itm9999999999999">Apple iPhone 16 Pro Max (256 GB)</a>
      <a href="/apple-iphone-16-silicone-case/p/itmcase123456789">Apple iPhone 16 Silicone Case</a>
      <a href="/apple-iphone-16-black-128-gb/p/itmexact11111111">Apple iPhone 16 (Black, 128 GB)</a>
      <a href="/apple-iphone-16-teal-256-gb/p/itmexact22222222">Apple iPhone 16 (Teal, 256 GB)</a>
    </body></html>
    """
    amazon_search_html = """
    <html><body>
      <a href="/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y">Apple iPhone 16 (128 GB) - Black</a>
    </body></html>
    """

    async def fake_fetch(url, timeout_ms=None):
        if "amazon.in" in url:
            return SimpleNamespace(
                source_url=url,
                final_url=url,
                status_code=200,
                title="Amazon.in : iphone 16",
                html_content=amazon_search_html,
                error=None,
            )
        if "flipkart.com" in url:
            return SimpleNamespace(
                source_url=url,
                final_url=url,
                status_code=200,
                title="Iphone 16 - Flipkart",
                html_content=flipkart_search_html,
                error=None,
            )
        return SimpleNamespace(
            source_url=url,
            final_url=url,
            status_code=403,
            title="",
            html_content="",
            error="HTTP 403",
        )

    with patch("mcp_servers.browser.server.browser_manager.fetch_page", side_effect=AsyncMock(side_effect=fake_fetch)):
        res = await discover_product_urls(query="iPhone 16", category="smartphone", max_results=4)

    urls = [item.url for item in res.discovered_urls]
    assert len(urls) == 4
    # All 3 exact iPhone 16 listings (1 Amazon + 2 Flipkart) MUST rank in the top 3
    assert "https://www.amazon.in/Apple-iPhone-16-128-GB/dp/B0DGJHBX5Y" in urls[:3]
    assert "https://www.flipkart.com/apple-iphone-16-black-128-gb/p/itmexact11111111" in urls[:3]
    assert "https://www.flipkart.com/apple-iphone-16-teal-256-gb/p/itmexact22222222" in urls[:3]
    # Accessory must never outrank variants or exact matches
    assert "https://www.flipkart.com/apple-iphone-16-silicone-case/p/itmcase123456789" not in urls


def test_score_discovered_candidate_ordering():
    exact_score, exact_status = score_discovered_candidate(
        "iPhone 16",
        "smartphone",
        "https://www.flipkart.com/apple-iphone-16-black-128-gb/p/itmexact111",
        "Apple iPhone 16 (Black, 128 GB)",
    )
    variant_score, variant_status = score_discovered_candidate(
        "iPhone 16",
        "smartphone",
        "https://www.flipkart.com/apple-iphone-16-plus-black-256-gb/p/itma302a",
        "Apple iPhone 16 Plus (Black, 256 GB)",
    )
    acc_score, acc_status = score_discovered_candidate(
        "iPhone 16",
        "smartphone",
        "https://www.flipkart.com/apple-iphone-16-case/p/itmcase1",
        "Apple iPhone 16 Back Cover Case",
    )
    assert exact_status == "EXACT_MATCH"
    assert variant_status == "RELATED_VARIANT"
    assert acc_status == "ACCESSORY"
    assert exact_score > variant_score > acc_score
