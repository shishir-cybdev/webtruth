import json
import tempfile
from pathlib import Path
import pytest

from mcp_servers.evidence.database import EvidenceDatabase
from mcp_servers.evidence.evidence_service import (
    EvidenceService,
    compute_canonical_evidence_hash,
)
from mcp_servers.evidence.schemas import (
    DuplicateEvidenceResult,
    EvidenceRecord,
    ProductEvidenceHistoryResult,
    SaveEvidenceRequest,
    SearchEvidenceResult,
    VerifyEvidenceResult,
)
from mcp_servers.evidence.server import (
    detect_duplicate_evidence,
    get_evidence,
    get_product_evidence_history,
    save_evidence,
    search_evidence,
    server,
    verify_evidence,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Provide a temporary database path for isolated persistence tests."""
    return str(tmp_path / "test_evidence.db")


@pytest.fixture
def isolated_service(temp_db_path: str) -> EvidenceService:
    """Create an EvidenceService instance connected to an isolated test database."""
    db = EvidenceDatabase(db_path=temp_db_path)
    return EvidenceService(db=db)


# =========================================================================
# 1. MCP Tool Discovery
# =========================================================================
@pytest.mark.anyio
async def test_evidence_mcp_tool_discovery():
    """Verify that Evidence MCP server exposes all 6 required tools."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected = {
        "save_evidence",
        "get_evidence",
        "search_evidence",
        "verify_evidence",
        "get_product_evidence_history",
        "detect_duplicate_evidence",
    }
    assert expected.issubset(tool_names), f"Missing tools. Found: {tool_names}"
    assert server.name == "webtruth-evidence"


# =========================================================================
# 2. Persistence Across Database Connections
# =========================================================================
def test_persistence_across_connections(temp_db_path: str):
    """Verify evidence survives connection closing and is readable from fresh connection."""
    # Write using service 1
    db1 = EvidenceDatabase(db_path=temp_db_path)
    svc1 = EvidenceService(db=db1)

    req = SaveEvidenceRequest(
        investigation_id="inv_test001",
        product_id="dell-xps-15",
        source_url="https://amazon.in/dp/B0CX214981",
        source_title="Dell XPS 15 (2024)",
        evidence_type="retailer_price",
        extracted_claims=["Intel Core i7-13700H", "16GB DDR5", "OLED 3.5K"],
        raw_displayed_price="₹1,89,999.00",
        currency="INR",
        numeric_price=189999.0,
    )
    saved = svc1.save_evidence(req)
    evidence_id = saved.evidence_id

    # Disconnect & open completely fresh connection to same file
    del svc1
    del db1

    db2 = EvidenceDatabase(db_path=temp_db_path)
    svc2 = EvidenceService(db=db2)

    retrieved = svc2.get_evidence(evidence_id)
    assert retrieved is not None
    assert retrieved.evidence_id == evidence_id
    assert retrieved.investigation_id == "inv_test001"
    assert retrieved.product_id == "dell-xps-15"
    assert retrieved.source_domain == "amazon.in"
    assert retrieved.numeric_price == 189999.0
    assert retrieved.currency == "INR"
    assert retrieved.extracted_claims == ["Intel Core i7-13700H", "16GB DDR5", "OLED 3.5K"]
    assert len(retrieved.evidence_hash) == 64


# =========================================================================
# 3. Canonical SHA-256 Hashing & Verification
# =========================================================================
def test_hash_verification_valid(isolated_service: EvidenceService):
    """Verify that an untampered record passes SHA-256 integrity verification."""
    req = SaveEvidenceRequest(
        investigation_id="inv_test002",
        product_id="apple-macbook-pro-14",
        source_url="https://apple.com/in/shop/buy-mac/macbook-pro",
        source_title="Buy MacBook Pro 14",
        evidence_type="retailer_price",
        extracted_claims=["Apple M3 Pro Chip", "18GB Unified Memory", "512GB SSD"],
        raw_displayed_price="₹1,99,900.00",
        currency="INR",
        numeric_price=199900.0,
    )
    saved = isolated_service.save_evidence(req)

    verification = isolated_service.verify_evidence(saved.evidence_id)
    assert isinstance(verification, VerifyEvidenceResult)
    assert verification.is_valid is True
    assert verification.status == "valid"
    assert verification.stored_hash == saved.evidence_hash
    assert verification.computed_hash == saved.evidence_hash
    assert "integrity verified" in verification.message.lower()


def test_tampered_evidence_detection(isolated_service: EvidenceService):
    """Verify that modifying a row in the database causes verify_evidence to fail."""
    req = SaveEvidenceRequest(
        investigation_id="inv_test003",
        product_id="sony-wh1000xm5",
        source_url="https://croma.com/sony-wh-1000xm5",
        source_title="Sony WH-1000XM5 Headphones",
        evidence_type="retailer_price",
        extracted_claims=["Active Noise Cancellation", "30hr Battery"],
        raw_displayed_price="₹29,990.00",
        currency="INR",
        numeric_price=29990.0,
    )
    saved = isolated_service.save_evidence(req)

    # Simulate unauthorized direct SQL tampering
    with isolated_service.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE evidence_records SET raw_displayed_price = ? WHERE evidence_id = ?;",
            ("₹19,990.00", saved.evidence_id),  # Fraudulent price change
        )

    # Verification must flag the discrepancy
    tampered_verification = isolated_service.verify_evidence(saved.evidence_id)
    assert tampered_verification.is_valid is False
    assert tampered_verification.status == "modified"
    assert tampered_verification.stored_hash != tampered_verification.computed_hash
    assert "INTEGRITY VIOLATION" in tampered_verification.message


# =========================================================================
# 4. Missing Price Handling (No Hallucination)
# =========================================================================
def test_missing_price_handling(isolated_service: EvidenceService):
    """Verify missing prices and currencies are stored as None, never fabricated."""
    req = SaveEvidenceRequest(
        investigation_id="inv_test004",
        product_id="lenovo-thinkpad-p16",
        source_url="https://lenovo.com/in/workstations/p16",
        source_title="ThinkPad P16 Mobile Workstation",
        evidence_type="specs_table",
        extracted_claims=["Intel Core i9-13980HX", "ECC Memory Supported"],
        raw_displayed_price=None,
        currency=None,
        numeric_price=None,
    )
    saved = isolated_service.save_evidence(req)

    assert saved.raw_displayed_price is None
    assert saved.currency is None
    assert saved.numeric_price is None

    # Retrieve again
    retrieved = isolated_service.get_evidence(saved.evidence_id)
    assert retrieved is not None
    assert retrieved.raw_displayed_price is None
    assert retrieved.currency is None


# =========================================================================
# 5. Duplicate Evidence Detection
# =========================================================================
def test_duplicate_detection(isolated_service: EvidenceService):
    """Verify duplicate detection matches existing identical records without modifying them."""
    req = SaveEvidenceRequest(
        investigation_id="inv_test005",
        product_id="asus-rog-g14",
        source_url="https://asus.com/in/rog-g14",
        source_title="ROG Zephyrus G14",
        evidence_type="retailer_price",
        extracted_claims=["AMD Ryzen 9 7940HS", "RTX 4060 8GB"],
        raw_displayed_price="₹1,39,990.00",
        currency="INR",
        numeric_price=139990.0,
    )
    saved = isolated_service.save_evidence(req)

    # Check duplicate with same URL and claims
    dup_res = isolated_service.detect_duplicate_evidence(
        source_url="https://asus.com/in/rog-g14",
        extracted_claims=["AMD Ryzen 9 7940HS", "RTX 4060 8GB"],
    )
    assert isinstance(dup_res, DuplicateEvidenceResult)
    assert dup_res.is_duplicate is True
    assert dup_res.duplicate_count >= 1
    assert dup_res.matched_records[0].evidence_id == saved.evidence_id

    # Check with different claims -> not duplicate
    non_dup = isolated_service.detect_duplicate_evidence(
        source_url="https://asus.com/in/rog-g14",
        extracted_claims=["AMD Ryzen 7 7735HS", "RTX 4050"],
    )
    assert non_dup.is_duplicate is False
    assert non_dup.duplicate_count == 0


# =========================================================================
# 6. Search & Chronological Price History
# =========================================================================
def test_search_and_chronological_history(isolated_service: EvidenceService):
    """Verify dynamic filtering and chronological price history tracking."""
    pid = "samsung-galaxy-s24-ultra"

    # Insert 3 records with distinct timestamps
    timestamps = [
        "2026-11-10T10:00:00Z",
        "2026-11-15T10:00:00Z",
        "2026-11-20T10:00:00Z",
    ]
    prices = [129999.0, 124999.0, 119999.0]

    for ts, p in zip(timestamps, prices):
        isolated_service.save_evidence(
            SaveEvidenceRequest(
                investigation_id="inv_s24",
                product_id=pid,
                source_url=f"https://amazon.in/dp/s24-{p}",
                capture_timestamp=ts,
                evidence_type="retailer_price",
                extracted_claims=[f"Snapdragon 8 Gen 3 at ₹{p:,.0f}"],
                raw_displayed_price=f"₹{p:,.0f}",
                currency="INR",
                numeric_price=p,
            )
        )

    # Test chronological history
    history = isolated_service.get_product_evidence_history(pid)
    assert isinstance(history, ProductEvidenceHistoryResult)
    assert history.total_records == 3
    assert len(history.price_history) == 3

    # Must be sorted in ascending order of capture timestamp
    assert history.price_history[0].capture_timestamp == "2026-11-10T10:00:00Z"
    assert history.price_history[0].numeric_price == 129999.0
    assert history.price_history[2].capture_timestamp == "2026-11-20T10:00:00Z"
    assert history.price_history[2].numeric_price == 119999.0

    # Test search by domain
    search_res = isolated_service.search_evidence(source_domain="amazon.in", limit=10)
    assert isinstance(search_res, SearchEvidenceResult)
    assert search_res.total >= 3
    assert all(r.source_domain == "amazon.in" for r in search_res.items)


# =========================================================================
# 7. End-to-End Tool Invocation Through MCP Server
# =========================================================================
@pytest.mark.anyio
async def test_mcp_server_tool_calls_e2e():
    """Verify tool execution directly through the MCP server functions."""
    # 1. save_evidence tool
    record = await save_evidence(
        investigation_id="inv_e2e_001",
        product_id="lg-gram-16",
        source_url="https://croma.com/lg-gram-16",
        source_title="LG Gram 16 Lightweight Laptop",
        evidence_type="retailer_price",
        extracted_claims=["Intel Core Ultra 7", "1.19kg Weight"],
        raw_displayed_price="₹1,15,000.00",
        currency="INR",
        numeric_price=115000.0,
    )
    assert isinstance(record, EvidenceRecord)
    evi_id = record.evidence_id

    # 2. get_evidence tool
    retrieved = await get_evidence(evi_id)
    assert retrieved is not None
    assert retrieved.product_id == "lg-gram-16"

    # 3. verify_evidence tool
    verification = await verify_evidence(evi_id)
    assert verification.is_valid is True

    # 4. search_evidence tool
    search_out = await search_evidence(investigation_id="inv_e2e_001")
    assert search_out.total >= 1

    # 5. get_product_evidence_history tool
    history = await get_product_evidence_history("lg-gram-16")
    assert history.total_records >= 1
    assert len(history.price_history) >= 1

    # 6. detect_duplicate_evidence tool
    dup = await detect_duplicate_evidence(
        source_url="https://croma.com/lg-gram-16",
        extracted_claims=["Intel Core Ultra 7", "1.19kg Weight"],
    )
    assert dup.is_duplicate is True
