import pytest
from datetime import datetime, timedelta, timezone

from mcp_servers.trust.freshness import (
    FreshnessClassification,
    FreshnessPolicy,
    evaluate_freshness,
)
from mcp_servers.trust.schemas import (
    ClaimStatus,
    ConsistencyStatus,
    EvidenceQualityResult,
    SourceConsistencyResult,
    SourceFreshnessResult,
    TrustAssessmentResult,
    TrustReportResult,
    UnsupportedClaimsResult,
)
from mcp_servers.trust.server import (
    assess_evidence_quality,
    calculate_trust_assessment,
    check_source_freshness,
    detect_unsupported_claims,
    evaluate_source_consistency,
    generate_trust_report,
    server,
)
from mcp_servers.trust.trust_service import (
    compute_canonical_evidence_hash,
    default_trust_service,
)


@pytest.mark.anyio
async def test_trust_mcp_tool_discovery():
    """Verify that all 6 Trust tools are registered on the MCPServer instance."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected = {
        "assess_evidence_quality",
        "check_source_freshness",
        "detect_unsupported_claims",
        "evaluate_source_consistency",
        "calculate_trust_assessment",
        "generate_trust_report",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


@pytest.mark.anyio
async def test_trust_mcp_tool_e2e_invocation():
    """Verify end-to-end asynchronous invocation of all 6 tools directly through the server endpoints."""
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_recs = [
        {
            "evidence_id": "evi_test_01",
            "investigation_id": "inv_01",
            "product_id": "dell-xps-15",
            "source_url": "https://dell.com/xps15",
            "capture_timestamp": now_iso,
            "evidence_type": "retailer_price",
            "extracted_claims": ["Intel Core i7", "16GB RAM"],
            "raw_displayed_price": "₹1,89,900",
            "currency": "INR",
        }
    ]
    # 1. assess_evidence_quality
    q = await assess_evidence_quality(evidence_records=raw_recs)
    assert isinstance(q, EvidenceQualityResult)
    assert q.total_records == 1

    # 2. check_source_freshness
    f = await check_source_freshness(evidence_records=raw_recs)
    assert isinstance(f, SourceFreshnessResult)
    assert f.fresh_count == 1

    # 3. detect_unsupported_claims
    u = await detect_unsupported_claims(
        claims=[{"claim_id": "c1", "field": "RAM", "claimed_value": "16GB", "cited_evidence_ids": ["evi_test_01"]}],
        evidence_records=raw_recs,
    )
    assert isinstance(u, UnsupportedClaimsResult)
    assert u.supported_count == 1

    # 4. evaluate_source_consistency
    c = await evaluate_source_consistency(products=[
        {"source_url": "https://dell.com", "ram": "16GB", "evidence_id": "evi_test_01"}
    ])
    assert isinstance(c, SourceConsistencyResult)

    # 5. calculate_trust_assessment
    t = await calculate_trust_assessment(evidence_records=raw_recs)
    assert isinstance(t, TrustAssessmentResult)

    # 6. generate_trust_report
    r = await generate_trust_report(evidence_records=raw_recs)
    assert isinstance(r, TrustReportResult)
    assert r.report_id.startswith("tr_")


def test_complete_evidence():
    """Test 1: Complete evidence with valid URL, timestamp, claims, and hash has high quality."""
    now_iso = "2026-11-24T12:00:00Z"
    h = compute_canonical_evidence_hash(
        investigation_id="inv_full",
        product_id="dell-xps-15",
        source_url="https://dell.com/product",
        capture_timestamp=now_iso,
        evidence_type="retailer_price",
        extracted_claims=["16GB RAM", "512GB SSD"],
        raw_displayed_price="₹1,89,900",
        currency="INR",
    )
    recs = [
        {
            "evidence_id": "evi_full",
            "investigation_id": "inv_full",
            "product_id": "dell-xps-15",
            "source_url": "https://dell.com/product",
            "capture_timestamp": now_iso,
            "evidence_type": "retailer_price",
            "extracted_claims": ["16GB RAM", "512GB SSD"],
            "raw_displayed_price": "₹1,89,900",
            "currency": "INR",
            "evidence_hash": h,
        }
    ]
    res = default_trust_service.assess_evidence_quality(recs)
    assert res.total_records == 1
    assert res.high_quality_count == 1
    assert res.records[0].integrity_status == "verified"
    assert res.records[0].quality_rating == "high"
    assert res.records[0].quality_score >= 0.8
    assert res.tampered_records_count == 0


def test_missing_evidence():
    """Test 2: Records lacking extracted claims and specifications are penalized and flagged."""
    recs = [
        {
            "evidence_id": "evi_empty",
            "source_url": "https://empty-store.com",
            "capture_timestamp": "2026-11-24T10:00:00Z",
            "extracted_claims": [],
            "raw_displayed_price": None,
        }
    ]
    res = default_trust_service.assess_evidence_quality(recs)
    assert res.total_records == 1
    assert res.records[0].has_extracted_data is False
    assert any(iss.issue_type == "no_extracted_claims" for iss in res.records[0].issues)
    assert res.records[0].quality_score < 0.8


def test_missing_timestamps():
    """Test 3: Missing capture timestamp flags critical quality issue and unknown freshness."""
    recs = [
        {
            "evidence_id": "evi_no_ts",
            "source_url": "https://store.com/item",
            "capture_timestamp": None,
            "extracted_claims": ["16GB RAM"],
        }
    ]
    # Quality check
    q_res = default_trust_service.assess_evidence_quality(recs)
    assert q_res.records[0].has_timestamp is False
    assert any(iss.issue_type == "missing_timestamp" for iss in q_res.records[0].issues)

    # Freshness check
    f_res = default_trust_service.check_source_freshness(recs)
    assert f_res.unknown_count == 1
    assert f_res.items[0].classification == FreshnessClassification.UNKNOWN_TIMESTAMP


def test_stale_evidence():
    """Test 4: Evidence older than 30 days is classified as STALE without claiming data is false."""
    base_time = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
    stale_ts = (base_time - timedelta(days=45)).isoformat()

    recs = [
        {
            "evidence_id": "evi_stale",
            "source_url": "https://store.com/old-deal",
            "capture_timestamp": stale_ts,
            "extracted_claims": ["Special Promo Price ₹1,20,000"],
        }
    ]
    res = default_trust_service.check_source_freshness(recs, evaluated_at=base_time)
    assert res.total_evaluated == 1
    assert res.stale_count == 1
    assert res.items[0].classification == FreshnessClassification.STALE
    assert res.items[0].is_stale is True
    # Verify policy caveat
    assert "not that specs are false" in res.items[0].explanation or "not that claims are false" in " ".join(res.evaluation_notes).lower()


def test_conflicting_prices():
    """Test 5: Conflicting prices across sources are identified as DISAGREEMENT and never silently merged."""
    price_comp = {
        "price_points": [
            {"source_url": "https://amazon.in", "raw_displayed_price": "₹1,89,900", "evidence_id": "evi_amz"},
            {"source_url": "https://flipkart.com", "raw_displayed_price": "₹1,75,000", "evidence_id": "evi_flk"},
        ]
    }
    res = default_trust_service.evaluate_source_consistency(price_comparison=price_comp)
    assert res.disagreeing_fields_count >= 1
    price_item = next(f for f in res.fields if f.field_name == "price")
    assert price_item.status == ConsistencyStatus.DISAGREEMENT
    assert len(price_item.distinct_claims) == 2


def test_conflicting_specifications():
    """Test 6: Conflicting technical specifications are detected and both competing values preserved."""
    products = [
        {"source_url": "https://retailer-a.com", "evidence_id": "evi_a", "ram": "16 GB DDR5"},
        {"source_url": "https://retailer-b.com", "evidence_id": "evi_b", "ram": "32 GB DDR5"},
    ]
    res = default_trust_service.evaluate_source_consistency(products=products)
    ram_item = next(f for f in res.fields if f.field_name == "ram")
    assert ram_item.status == ConsistencyStatus.DISAGREEMENT
    assert "Discrepancy detected" in ram_item.explanation
    assert ram_item.total_sources == 2


def test_unsupported_claims():
    """Test 7: Unsupported claims (lacking evidence) are distinguished from contradicted claims."""
    evidence = [
        {
            "evidence_id": "evi_verified",
            "extracted_claims": ["16GB RAM", "OLED 3.5K Display"],
            "raw_displayed_price": "₹1,89,900",
        }
    ]
    claims = [
        # Supported: valid evidence ID citing OLED
        {"claim_id": "c_sup", "field": "Display", "claimed_value": "OLED", "cited_evidence_ids": ["evi_verified"]},
        # Unsupported: cites nonexistent evidence ID
        {"claim_id": "c_unsup", "field": "Storage", "claimed_value": "2TB SSD", "cited_evidence_ids": ["evi_ghost"]},
        # Unsupported: cites nothing
        {"claim_id": "c_no_cite", "field": "Battery", "claimed_value": "99Whr", "cited_evidence_ids": []},
        # Contradicted: asserts 64GB RAM when evidence specifies 16GB RAM
        {"claim_id": "c_contra", "field": "RAM", "claimed_value": "64GB", "cited_evidence_ids": []},
    ]
    conflicts = [
        {
            "field_name": "RAM",
            "claims": [
                {"raw_value": "16GB", "evidence_id": "evi_verified"},
                {"raw_value": "64GB", "evidence_id": "evi_marketing_flyer"},
            ],
        }
    ]
    res = default_trust_service.detect_unsupported_claims(
        claims=claims,
        evidence_records=evidence,
        conflicts=conflicts,
    )
    assert res.supported_count == 1
    assert res.unsupported_count == 2
    assert res.contradicted_count == 1

    c_sup = next(c for c in res.claims if c.claim_id == "c_sup")
    assert c_sup.status == ClaimStatus.SUPPORTED

    c_unsup = next(c for c in res.claims if c.claim_id == "c_unsup")
    assert c_unsup.status == ClaimStatus.UNSUPPORTED
    assert "evi_ghost" in c_unsup.missing_evidence_ids

    c_contra = next(c for c in res.claims if c.claim_id == "c_contra")
    assert c_contra.status == ClaimStatus.CONTRADICTED


def test_valid_and_modified_evidence_hashes():
    """Test 8: Cryptographic SHA-256 integrity verification detects unmodified vs tampered records."""
    valid_hash = compute_canonical_evidence_hash(
        investigation_id="inv_h",
        product_id="prod_01",
        source_url="https://dell.com",
        capture_timestamp="2026-11-24T12:00:00Z",
        evidence_type="retailer_price",
        extracted_claims=["Valid text"],
        raw_displayed_price="₹1,00,000",
    )
    records = [
        # Record 1: Valid unmodified hash
        {
            "evidence_id": "evi_valid",
            "investigation_id": "inv_h",
            "product_id": "prod_01",
            "source_url": "https://dell.com",
            "capture_timestamp": "2026-11-24T12:00:00Z",
            "evidence_type": "retailer_price",
            "extracted_claims": ["Valid text"],
            "raw_displayed_price": "₹1,00,000",
            "evidence_hash": valid_hash,
        },
        # Record 2: Tampered hash
        {
            "evidence_id": "evi_tampered",
            "investigation_id": "inv_h",
            "product_id": "prod_01",
            "source_url": "https://dell.com",
            "capture_timestamp": "2026-11-24T12:00:00Z",
            "evidence_type": "retailer_price",
            "extracted_claims": ["Tampered altered content"],
            "raw_displayed_price": "₹1,00,000",
            "evidence_hash": valid_hash,  # Hash belongs to old content
        },
    ]
    res = default_trust_service.assess_evidence_quality(records)
    assert res.total_records == 2
    assert res.tampered_records_count == 1

    valid_rec = next(r for r in res.records if r.evidence_id == "evi_valid")
    assert valid_rec.integrity_status == "verified"

    tampered_rec = next(r for r in res.records if r.evidence_id == "evi_tampered")
    assert tampered_rec.integrity_status == "tampered"
    assert any(iss.issue_type == "tampered_hash" for iss in tampered_rec.issues)


def test_multiple_sources_agreeing():
    """Test 9: Multiple independent sources agreeing on specifications yield high consistency."""
    products = [
        {"source_url": "https://amazon.in/dp/xps", "brand": "Dell", "model": "XPS 15", "ram": "16 GB"},
        {"source_url": "https://flipkart.com/dell-xps", "brand": "Dell", "model": "XPS 15", "ram": "16 GB"},
        {"source_url": "https://croma.com/p/dell-xps", "brand": "Dell", "model": "XPS 15", "ram": "16 GB"},
    ]
    res = default_trust_service.evaluate_source_consistency(products=products)
    assert res.disagreeing_fields_count == 0
    assert res.agreeing_fields_count >= 3
    assert res.overall_consistency == "high_agreement"
    assert res.consistency_ratio == 1.0


def test_multiple_sources_disagreeing():
    """Test 10: Multiple sources disagreeing on warranty terms are flagged with exact competing values."""
    products = [
        {"source_url": "https://s1.com", "evidence_id": "e1", "specifications": {"Warranty": "1 Year Onsite"}},
        {"source_url": "https://s2.com", "evidence_id": "e2", "specifications": {"Warranty": "2 Years Carry-In"}},
    ]
    res = default_trust_service.evaluate_source_consistency(products=products)
    w_item = next(f for f in res.fields if f.field_name.lower() == "warranty")
    assert w_item.status == ConsistencyStatus.DISAGREEMENT
    assert res.disagreeing_fields_count >= 1


def test_insufficient_evidence():
    """Test 11: Single-source specifications are flagged as unverified by independent sources."""
    products = [
        {"source_url": "https://rare-store.com", "evidence_id": "e_single", "specifications": {"NPU": "Intel AI Boost 1.4 GHz"}}
    ]
    res = default_trust_service.evaluate_source_consistency(products=products)
    npu_item = next(f for f in res.fields if f.field_name == "NPU")
    assert npu_item.status == ConsistencyStatus.SINGLE_SOURCE
    assert res.single_source_fields_count >= 1
    assert "reported by only 1 source" in npu_item.explanation


def test_generate_trust_report_comprehensive():
    """Test 12: Unified trust report synthesizes evidence, freshness, consistency, and actionable steps."""
    now_iso = datetime.now(timezone.utc).isoformat()
    old_iso = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

    h = compute_canonical_evidence_hash(
        investigation_id="inv_rep",
        product_id="dell-xps-15",
        source_url="https://amazon.in/dp/dell",
        capture_timestamp=now_iso,
        evidence_type="retailer_price",
        extracted_claims=["16GB RAM", "1TB SSD"],
        raw_displayed_price="₹1,89,900",
        currency="INR",
    )
    evidence = [
        {
            "evidence_id": "evi_amz",
            "investigation_id": "inv_rep",
            "product_id": "dell-xps-15",
            "source_url": "https://amazon.in/dp/dell",
            "capture_timestamp": now_iso,
            "evidence_type": "retailer_price",
            "extracted_claims": ["16GB RAM", "1TB SSD"],
            "raw_displayed_price": "₹1,89,900",
            "currency": "INR",
            "evidence_hash": h,
            "specifications": {"RAM": "16 GB", "Storage": "1 TB SSD"},
        },
        {
            "evidence_id": "evi_flk",
            "investigation_id": "inv_rep",
            "product_id": "dell-xps-15",
            "source_url": "https://flipkart.com/dell",
            "capture_timestamp": old_iso,  # Stale source
            "evidence_type": "retailer_price",
            "extracted_claims": ["16GB RAM", "Display: 60Hz"],
            "raw_displayed_price": "₹1,79,900",
            "currency": "INR",
            "specifications": {"RAM": "16 GB", "Display": "60Hz"},
        },
    ]
    comparison_data = {
        "product_identity": {"product_name": "Dell XPS 15 9530", "brand": "Dell"},
        "products": [
            {"source_url": "https://amazon.in/dp/dell", "ram": "16 GB", "evidence_id": "evi_amz"},
            {"source_url": "https://flipkart.com/dell", "ram": "16 GB", "evidence_id": "evi_flk"},
        ],
        "conflicts": {
            "conflicts": [
                {
                    "field_name": "Display",
                    "claims": [
                        {"raw_value": "120Hz OLED", "evidence_id": "evi_amz"},
                        {"raw_value": "60Hz IPS", "evidence_id": "evi_flk"},
                    ],
                }
            ]
        },
    }
    claims = [
        {"claim_id": "clm_1", "field": "RAM", "claimed_value": "16GB", "cited_evidence_ids": ["evi_amz"]},
        {"claim_id": "clm_2", "field": "Display", "claimed_value": "120Hz OLED", "cited_evidence_ids": ["evi_amz"]},
        {"claim_id": "clm_3", "field": "Battery", "claimed_value": "100Whr", "cited_evidence_ids": []},
    ]

    report = default_trust_service.generate_trust_report(
        evidence_records=evidence,
        comparison_data=comparison_data,
        claims=claims,
    )
    assert isinstance(report, TrustReportResult)
    assert len(report.supported_claims) == 1
    assert len(report.conflicting_claims) == 1
    assert len(report.unsupported_claims) == 1
    assert len(report.stale_sources) == 1
    assert len(report.recommended_verification_steps) >= 2
    # Check that recommended steps contain practical actions
    actions_text = " ".join(s.action for s in report.recommended_verification_steps)
    assert "Display" in actions_text or "manufacturer" in actions_text.lower()
