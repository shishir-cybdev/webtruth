import pytest
from pathlib import Path

from app.orchestrator.investigation_engine import default_investigation_engine
from app.orchestrator.schemas import StageStatus
from mcp_servers.browser.identity import ProductMatchStatus, evaluate_product_identity


def test_oneplus_13_exact_match():
    """Test 1: OnePlus 13 exact match with storage/color descriptors is EXACT_MATCH."""
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus 13 5G (12GB RAM, 256GB Storage, Arctic Dawn)",
        extracted_brand="OnePlus",
        extracted_model="OnePlus 13",
        page_title="OnePlus 13 5G Smartphone | Amazon.in",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.EXACT_MATCH
    assert res.extracted_brand == "oneplus"


def test_oneplus_13s_variant_rejected_from_exact_match():
    """Test 2: OnePlus 13S must be classified as RELATED_VARIANT, never EXACT_MATCH."""
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus 13S 5G (12GB RAM, 256GB)",
        extracted_brand="OnePlus",
        extracted_model="OnePlus 13S",
        page_title="OnePlus 13S | Flipkart.com",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.RELATED_VARIANT
    assert "13s" in res.reason.lower()


def test_oneplus_accessories_rejected():
    """Test 3: Accessories containing 'OnePlus' (e.g. Snapdragon Segments, Back Cover) are ACCESSORY."""
    res_seg = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus Snapdragon Segments",
        extracted_brand="OnePlus",
        page_title="OnePlus Snapdragon Segments | Amazon.in",
        expected_category="smartphone",
    )
    assert res_seg.match_status == ProductMatchStatus.ACCESSORY

    res_case = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus 13 Official Sandstone Magnetic Back Cover Case",
        extracted_brand="OnePlus",
        expected_category="smartphone",
    )
    assert res_case.match_status == ProductMatchStatus.ACCESSORY


def test_lava_phone_rejected():
    """Test 4: Lava Virat V1 must be rejected as BRAND_MISMATCH when investigating OnePlus 13."""
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="Lava Virat V1 (4GB RAM, 64GB)",
        extracted_brand="Lava",
        extracted_model="Virat V1",
        page_title="Lava Virat V1 | Flipkart.com",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.BRAND_MISMATCH
    assert res.extracted_brand == "lava"


def test_wrong_category_rejected():
    """Test 5: Wrong product category (laptop when investigating smartphone) is CATEGORY_MISMATCH."""
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name="OnePlus Book Laptop 15",
        extracted_brand="OnePlus",
        page_title="OnePlus Book Laptop 15",
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.CATEGORY_MISMATCH


def test_missing_product_identity():
    """Test 6: Missing product name/title/model is marked INSUFFICIENT_IDENTITY."""
    res = evaluate_product_identity(
        query="OnePlus 13",
        extracted_product_name=None,
        extracted_brand=None,
        extracted_model=None,
        page_title=None,
        expected_category="smartphone",
    )
    assert res.match_status == ProductMatchStatus.INSUFFICIENT_IDENTITY


@pytest.mark.anyio
async def test_exact_matches_from_multiple_retailers(tmp_path):
    """Test 7: Two valid OnePlus 13 pages from distinct fixtures both pass as EXACT_MATCH."""
    p1 = tmp_path / "op13_amazon.html"
    p1.write_text(
        """<!DOCTYPE html><html><head><title>OnePlus 13 5G | Amazon.in</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"OnePlus 13 5G","brand":{"@type":"Brand","name":"OnePlus"},"model":"OnePlus 13","offers":{"@type":"Offer","price":69999,"priceCurrency":"INR"}}</script>
        </head><body><h1>OnePlus 13 5G</h1><div class="product-price">₹69,999.00</div></body></html>""",
        encoding="utf-8",
    )
    p2 = tmp_path / "op13_croma.html"
    p2.write_text(
        """<!DOCTYPE html><html><head><title>OnePlus 13 5G | Croma</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"OnePlus 13","brand":{"@type":"Brand","name":"OnePlus"},"model":"OnePlus 13","offers":{"@type":"Offer","price":68999,"priceCurrency":"INR"}}</script>
        </head><body><h1>OnePlus 13</h1><div class="product-price">₹68,999.00</div></body></html>""",
        encoding="utf-8",
    )

    rec = default_investigation_engine.initialize_investigation(
        query="OnePlus 13",
        category="smartphone",
        target_urls=[f"file:///{p1.as_posix()}", f"file:///{p2.as_posix()}"],
    )
    completed = await default_investigation_engine.run_investigation(rec.investigation_id)

    assert completed.status == "completed"
    assert len(completed.extracted_records) == 2
    assert len(completed.evidence_ids) == 2
    assert len(completed.related_variants) == 0
    assert len(completed.rejected_candidates) == 0
    assert completed.comparison_result["price_comparison"]["lowest_price"]["numeric_price"] == 68999.0


@pytest.mark.anyio
async def test_mixed_exact_and_related_variants_and_rejected_candidates(tmp_path):
    """Test 8: Only OnePlus 13 enters Evidence/Comparison; 13S goes to related_variants; Lava & accessory go to rejected_candidates."""
    p_exact = tmp_path / "op13_exact.html"
    p_exact.write_text(
        """<!DOCTYPE html><html><head><title>OnePlus 13 5G Smartphone</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"OnePlus 13 5G","brand":{"@type":"Brand","name":"OnePlus"},"model":"OnePlus 13","offers":{"@type":"Offer","price":69999,"priceCurrency":"INR"}}</script>
        </head><body><h1>OnePlus 13 5G</h1><div class="product-price">₹69,999.00</div></body></html>""",
        encoding="utf-8",
    )
    p_13s = tmp_path / "op13s.html"
    p_13s.write_text(
        """<!DOCTYPE html><html><head><title>OnePlus 13S 5G Smartphone</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"OnePlus 13S 5G","brand":{"@type":"Brand","name":"OnePlus"},"model":"OnePlus 13S","offers":{"@type":"Offer","price":54079,"priceCurrency":"INR"}}</script>
        </head><body><h1>OnePlus 13S 5G</h1><div class="product-price">₹54,079.00</div></body></html>""",
        encoding="utf-8",
    )
    p_lava = tmp_path / "lava.html"
    p_lava.write_text(
        """<!DOCTYPE html><html><head><title>Lava Virat V1 Smartphone</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"Lava Virat V1","brand":{"@type":"Brand","name":"Lava"},"model":"Virat V1","offers":{"@type":"Offer","price":13999,"priceCurrency":"INR"}}</script>
        </head><body><h1>Lava Virat V1</h1><div class="product-price">₹13,999.00</div></body></html>""",
        encoding="utf-8",
    )
    p_acc = tmp_path / "segments.html"
    p_acc.write_text(
        """<!DOCTYPE html><html><head><title>OnePlus Snapdragon Segments</title>
        <script type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","name":"OnePlus Snapdragon Segments","brand":{"@type":"Brand","name":"OnePlus"},"offers":{"@type":"Offer","price":1599,"priceCurrency":"INR"}}</script>
        </head><body><h1>OnePlus Snapdragon Segments</h1><div class="product-price">₹1,599.00</div></body></html>""",
        encoding="utf-8",
    )

    rec = default_investigation_engine.initialize_investigation(
        query="OnePlus 13",
        category="smartphone",
        target_urls=[
            f"file:///{p_exact.as_posix()}",
            f"file:///{p_13s.as_posix()}",
            f"file:///{p_lava.as_posix()}",
            f"file:///{p_acc.as_posix()}",
        ],
    )
    completed = await default_investigation_engine.run_investigation(rec.investigation_id)

    assert completed.status == "completed"
    # ONLY the exact OnePlus 13 record entered Evidence & Comparison
    assert len(completed.extracted_records) == 1
    assert len(completed.evidence_ids) == 1
    assert completed.extracted_records[0]["numeric_price"] == 69999.0
    assert completed.comparison_result["price_comparison"]["lowest_price"]["numeric_price"] == 69999.0

    # OnePlus 13S separated into related_variants
    assert len(completed.related_variants) == 1
    assert completed.related_variants[0]["match_status"] == "RELATED_VARIANT"
    assert completed.related_variants[0]["numeric_price"] == 54079.0

    # Lava and OnePlus Segments rejected cleanly
    assert len(completed.rejected_candidates) == 2
    rejected_statuses = {c["match_status"] for c in completed.rejected_candidates}
    assert rejected_statuses == {"BRAND_MISMATCH", "ACCESSORY"}
