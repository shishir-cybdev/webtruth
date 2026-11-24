import pytest

from mcp_servers.comparison.comparison_service import comparison_service
from mcp_servers.comparison.normalization import (
    extract_model_number,
    generate_configuration_fingerprint,
    normalize_brand,
    normalize_cpu,
    normalize_ram,
    normalize_storage,
)
from mcp_servers.comparison.schemas import (
    ComprehensiveComparisonResult,
    NormalizedProduct,
    PolicyComparisonResult,
    PriceComparisonResult,
    ProductConflictResult,
    SpecComparisonResult,
)
from mcp_servers.comparison.server import (
    compare_policies,
    compare_prices,
    compare_specifications,
    find_product_conflicts,
    generate_comparison,
    normalize_product,
    server,
)


# =========================================================================
# 1. MCP Tool Discovery
# =========================================================================
@pytest.mark.anyio
async def test_comparison_mcp_tool_discovery():
    """Verify that Comparison MCP server exposes all 6 required tools."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected = {
        "normalize_product",
        "compare_prices",
        "compare_specifications",
        "compare_policies",
        "find_product_conflicts",
        "generate_comparison",
    }
    assert expected.issubset(tool_names), f"Missing tools. Found: {tool_names}"
    assert server.name == "webtruth-comparison"


# =========================================================================
# 2. Normalization Engine (Preserves Raw & Normalizes Canonical)
# =========================================================================
def test_normalization_preserves_raw_values():
    """Verify that normalizers preserve exact raw text alongside normalized output."""
    raw_b, norm_b = normalize_brand("dell")
    assert raw_b == "dell"
    assert norm_b == "Dell"

    ram_info = normalize_ram("16 GB: 2 x 8 GB, DDR5, 4800 MT/s")
    assert ram_info["raw_value"] == "16 GB: 2 x 8 GB, DDR5, 4800 MT/s"
    assert ram_info["numeric_value"] == 16.0
    assert ram_info["unit"] == "GB"
    assert ram_info["memory_type"] == "DDR5"
    assert ram_info["normalized_value"] == "16 GB DDR5"

    stor_info = normalize_storage("1TB NVMe M.2 Solid State Drive")
    assert stor_info["numeric_value"] == 1024.0
    assert "1 TB" in stor_info["normalized_value"]
    assert "NVMe SSD" in stor_info["normalized_value"]

    cpu_info = normalize_cpu("13th Gen Intel Core i7-13700H Processor")
    assert cpu_info["vendor"] == "Intel"
    assert cpu_info["tier"] == "Core I7"
    assert cpu_info["chip_code"] == "13700H"


# =========================================================================
# 3. Same Product Across Multiple Retailers
# =========================================================================
def test_same_product_across_multiple_retailers():
    """Verify comparison for exact same model (Dell XPS 15 9530) across 3 retailers."""
    evidence_items = [
        {
            "evidence_id": "evi_amz_01",
            "source_url": "https://amazon.in/dp/dell-xps-15",
            "source_domain": "amazon.in",
            "product_name": "Dell XPS 15 9530 Laptop",
            "brand": "Dell",
            "model": "XPS 15 9530",
            "raw_displayed_price": "₹1,89,999.00",
            "currency": "INR",
            "numeric_price": 189999.0,
            "specifications": {
                "CPU": "Intel Core i7-13700H",
                "RAM": "16 GB DDR5",
                "Storage": "512 GB SSD",
                "GPU": "NVIDIA RTX 4060 8GB",
                "Display": '15.6" OLED 3.5K',
            },
            "warranty": "1 Year Onsite Support",
        },
        {
            "evidence_id": "evi_flk_02",
            "source_url": "https://flipkart.com/dell-xps-15-9530",
            "source_domain": "flipkart.com",
            "product_name": "Dell XPS 15 9530",
            "brand": "Dell",
            "model": "XPS 15 9530",
            "raw_displayed_price": "₹1,84,999.00",
            "currency": "INR",
            "numeric_price": 184999.0,
            "specifications": {
                "CPU": "Intel Core i7-13700H",
                "RAM": "16 GB DDR5",
                "Storage": "512 GB SSD",
                "GPU": "NVIDIA RTX 4060 8GB",
                "Display": '15.6" OLED 3.5K',
            },
            "warranty": "1 Year Onsite Support",
        },
    ]

    res = comparison_service.generate_comparison(evidence_items)
    assert isinstance(res, ComprehensiveComparisonResult)
    assert res.configuration_match is True
    assert len(res.configuration_warnings) == 0
    assert res.price_comparison.lowest_price.source_domain == "flipkart.com"
    assert res.price_comparison.lowest_price.numeric_price == 184999.0
    assert res.price_comparison.highest_price.numeric_price == 189999.0
    assert res.price_comparison.price_spread == 5000.0
    assert res.conflicts.has_conflicts is False


# =========================================================================
# 4. Similar Names but Different Model Numbers
# =========================================================================
def test_similar_names_different_model_numbers():
    """Verify that different model generations (XPS 15 9530 vs 9520) are NOT equated."""
    p1 = comparison_service.normalize_product(
        product_name="Dell XPS 15 9530",
        brand="Dell",
        model="XPS 15 9530",
        specifications={"CPU": "Intel Core i7-13700H", "RAM": "16 GB"},
        source_evidence_id="evi_9530",
    )
    p2 = comparison_service.normalize_product(
        product_name="Dell XPS 15 9520",
        brand="Dell",
        model="XPS 15 9520",
        specifications={"CPU": "Intel Core i7-12700H", "RAM": "16 GB"},
        source_evidence_id="evi_9520",
    )

    assert p1.model_number.normalized_value == "9530"
    assert p2.model_number.normalized_value == "9520"
    assert p1.config_fingerprint != p2.config_fingerprint

    comp = comparison_service.generate_comparison([
        {"evidence_id": "evi_9530", "product_name": p1.product_name, "model": "XPS 15 9530", "specifications": {"CPU": "13700H"}},
        {"evidence_id": "evi_9520", "product_name": p2.product_name, "model": "XPS 15 9520", "specifications": {"CPU": "12700H"}},
    ])
    assert comp.configuration_match is False
    assert any("Multiple model numbers detected" in w for w in comp.configuration_warnings)


# =========================================================================
# 5. Different RAM/Storage Configurations
# =========================================================================
def test_different_ram_storage_configurations():
    """Verify that 16GB/512GB vs 32GB/1TB are distinguished as different configurations."""
    p1 = comparison_service.normalize_product(
        product_name="ThinkPad X1 Carbon Gen 11",
        brand="Lenovo",
        specifications={"RAM": "16 GB LPDDR5", "Storage": "512 GB SSD"},
    )
    p2 = comparison_service.normalize_product(
        product_name="ThinkPad X1 Carbon Gen 11",
        brand="Lenovo",
        specifications={"RAM": "32 GB LPDDR5", "Storage": "1 TB SSD"},
    )

    assert p1.config_fingerprint != p2.config_fingerprint

    spec_res = comparison_service.compare_specifications([p1, p2])
    assert spec_res.configuration_match is False
    diff_fields = {d.field_name for d in spec_res.different_fields}
    assert "ram" in diff_fields
    assert "storage" in diff_fields


# =========================================================================
# 6. Price Comparison (Spread Calculation & Formatting)
# =========================================================================
def test_price_comparison_with_spread():
    """Verify accurate price spread computation when currencies match."""
    prices = [
        {"source_url": "https://store-a.com", "raw_displayed_price": "₹1,50,000", "currency": "INR", "numeric_price": 150000.0},
        {"source_url": "https://store-b.com", "raw_displayed_price": "₹1,42,000", "currency": "INR", "numeric_price": 142000.0},
        {"source_url": "https://store-c.com", "raw_displayed_price": "₹1,55,000", "currency": "INR", "numeric_price": 155000.0},
    ]
    res = comparison_service.compare_prices(prices)
    assert res.lowest_price.numeric_price == 142000.0
    assert res.highest_price.numeric_price == 155000.0
    assert res.price_spread == 13000.0
    assert res.currency_mismatch_detected is False


# =========================================================================
# 7. Missing Prices Handling (Never Invent Missing Data)
# =========================================================================
def test_missing_prices_handling():
    """Verify that sources with missing prices are flagged and no price is invented."""
    prices = [
        {"source_url": "https://retailer-a.com", "raw_displayed_price": "₹1,80,000", "currency": "INR", "numeric_price": 180000.0},
        {"source_url": "https://retailer-b.com", "raw_displayed_price": None, "currency": None, "numeric_price": None},
    ]
    res = comparison_service.compare_prices(prices)
    assert res.total_sources == 2
    assert "https://retailer-b.com" in res.missing_price_sources
    assert res.lowest_price.source_url == "https://retailer-a.com"
    # Spread should be 0 or None since only one price exists
    assert res.price_spread is None or res.price_spread == 0.0


# =========================================================================
# 8. Currency Mismatch Handling (No Unauthenticated Conversion)
# =========================================================================
def test_currency_mismatch_suppresses_spread():
    """Verify that differing currencies without conversion rates do not compute invalid spreads."""
    prices = [
        {"source_url": "https://amazon.in", "raw_displayed_price": "₹1,89,999", "currency": "INR", "numeric_price": 189999.0},
        {"source_url": "https://amazon.com", "raw_displayed_price": "$1,499.00", "currency": "USD", "numeric_price": 1499.0},
    ]
    res = comparison_service.compare_prices(prices)
    assert res.currency_mismatch_detected is True
    assert set(res.currencies_found) == {"INR", "USD"}
    assert res.price_spread is None, "Price spread must be suppressed when currencies mismatch without conversion rate"
    assert any("Currencies mismatch" in n for n in res.comparison_notes)


# =========================================================================
# 9. Conflicting Specifications Detection
# =========================================================================
def test_conflicting_specifications_detection():
    """Verify that conflicting specifications across sources are isolated with evidence IDs."""
    p1 = comparison_service.normalize_product(
        product_name="ASUS ROG Zephyrus G14",
        brand="ASUS",
        specifications={"RAM": "16 GB DDR5", "Display": '14" 165Hz IPS'},
        source_evidence_id="evi_src_1",
        source_url="https://asus.com/g14",
    )
    p2 = comparison_service.normalize_product(
        product_name="ASUS ROG Zephyrus G14",
        brand="ASUS",
        specifications={"RAM": "32 GB DDR5", "Display": '14" 120Hz OLED'},
        source_evidence_id="evi_src_2",
        source_url="https://retailer.com/g14",
    )

    conflicts = comparison_service.find_product_conflicts([p1, p2])
    assert isinstance(conflicts, ProductConflictResult)
    assert conflicts.has_conflicts is True
    assert conflicts.conflicts_count >= 2

    ram_conflict = next(c for c in conflicts.conflicts if c.field_name == "ram")
    assert len(ram_conflict.claims) == 2
    claims_evis = {c["evidence_id"] for c in ram_conflict.claims}
    assert claims_evis == {"evi_src_1", "evi_src_2"}


# =========================================================================
# 10. Missing Warranty & Policy Information
# =========================================================================
def test_missing_warranty_and_policy():
    """Verify that absent warranty is flagged as missing rather than hallucinated."""
    policies = [
        {"source_url": "https://official.com", "evidence_id": "evi_off", "warranty": "2 Years International Warranty"},
        {"source_url": "https://shady-reseller.com", "evidence_id": "evi_shady", "warranty": None, "return_policy": "No Returns"},
    ]
    res = comparison_service.compare_policies(policies)
    assert isinstance(res, PolicyComparisonResult)
    assert res.missing_policies_count >= 1

    missing_item = next(p for p in res.policies if p.source_url == "https://shady-reseller.com" and p.policy_type == "warranty")
    assert missing_item.is_missing is True
    assert missing_item.raw_terms is None


# =========================================================================
# 11. Evidence Traceability & Duplicate Evidence
# =========================================================================
def test_evidence_traceability_and_duplicates():
    """Verify that all comparison outputs trace to evidence IDs and duplicate evidence is handled."""
    item1 = {
        "evidence_id": "evi_001",
        "source_url": "https://croma.com/xps15",
        "product_name": "Dell XPS 15",
        "brand": "Dell",
        "raw_displayed_price": "₹1,89,999.00",
        "currency": "INR",
        "numeric_price": 189999.0,
        "specifications": {"RAM": "16 GB", "Storage": "512 GB"},
    }
    # Duplicate item with same evidence ID
    item_dup = dict(item1)

    item2 = {
        "evidence_id": "evi_002",
        "source_url": "https://reliancedigital.in/xps15",
        "product_name": "Dell XPS 15",
        "brand": "Dell",
        "raw_displayed_price": "₹1,88,000.00",
        "currency": "INR",
        "numeric_price": 188000.0,
        "specifications": {"RAM": "16 GB", "Storage": "512 GB"},
    }

    comp = comparison_service.generate_comparison([item1, item_dup, item2])
    assert "evi_001" in comp.evidence_references
    assert "evi_002" in comp.evidence_references
    # References must be deduplicated
    assert len(comp.evidence_references) == 2


# =========================================================================
# 12. MCP Tool Execution E2E
# =========================================================================
@pytest.mark.anyio
async def test_mcp_tools_e2e_invocation():
    """Verify tool execution directly through the registered MCP server tool functions."""
    # 1. normalize_product tool
    norm = await normalize_product(
        product_name="MacBook Pro 14 M3",
        brand="Apple",
        model="MacBook Pro 14",
        specifications={"CPU": "M3 Pro", "RAM": "18 GB Unified", "Storage": "512 GB SSD"},
        source_evidence_id="evi_mac_01",
        source_url="https://apple.com/macbook-pro",
    )
    assert isinstance(norm, NormalizedProduct)
    assert norm.brand.normalized_value == "Apple"
    assert norm.ram.numeric_value == 18.0

    # 2. compare_prices tool
    p_comp = await compare_prices([
        {"source_url": "https://store1.com", "raw_displayed_price": "₹1,99,900", "currency": "INR", "numeric_price": 199900.0},
        {"source_url": "https://store2.com", "raw_displayed_price": "₹1,95,000", "currency": "INR", "numeric_price": 195000.0},
    ])
    assert isinstance(p_comp, PriceComparisonResult)
    assert p_comp.price_spread == 4900.0

    # 3. compare_specifications tool
    s_comp = await compare_specifications([
        {"product_name": "XPS 15", "brand": "Dell", "specifications": {"RAM": "16 GB"}},
        {"product_name": "XPS 15", "brand": "Dell", "specifications": {"RAM": "16 GB"}},
    ])
    assert isinstance(s_comp, SpecComparisonResult)
    assert s_comp.configuration_match is True

    # 4. compare_policies tool
    pol_comp = await compare_policies([
        {"source_url": "https://s1.com", "warranty": "1 Year Standard"},
    ])
    assert isinstance(pol_comp, PolicyComparisonResult)

    # 5. find_product_conflicts tool
    conflicts = await find_product_conflicts([
        {"product_name": "Laptop", "specifications": {"RAM": "16 GB"}},
        {"product_name": "Laptop", "specifications": {"RAM": "32 GB"}},
    ])
    assert isinstance(conflicts, ProductConflictResult)
    assert conflicts.has_conflicts is True

    # 6. generate_comparison tool
    gen_comp = await generate_comparison([
        {"evidence_id": "evi_1", "product_name": "Laptop", "brand": "Dell", "numeric_price": 100000.0, "currency": "INR"},
        {"evidence_id": "evi_2", "product_name": "Laptop", "brand": "Dell", "numeric_price": 95000.0, "currency": "INR"},
    ])
    assert isinstance(gen_comp, ComprehensiveComparisonResult)
    assert gen_comp.price_comparison.lowest_price.numeric_price == 95000.0
