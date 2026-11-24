import asyncio
import os
import pytest
from pathlib import Path
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.orchestrator.errors import (
    MCPServerConnectionError,
    MCPTimeoutError,
)
from app.orchestrator.investigation_engine import default_investigation_engine
from app.orchestrator.investigation_state import InvestigationStateStore
from app.orchestrator.mcp_manager import mcp_manager
from app.orchestrator.schemas import (
    InvestigationStage,
    StageStatus,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# =========================================================================
# 1. MCP Initialization and Tool Discovery
# =========================================================================
@pytest.mark.anyio
async def test_mcp_initialization_and_tool_discovery():
    """Verify stdio initialization and dynamic tool discovery for all four MCP servers."""
    servers = ["browser", "evidence", "comparison", "trust"]
    expected_tools = {
        "browser": ["open_product_page", "extract_product_data", "extract_structured_product_data", "capture_page_evidence", "inspect_page_metadata"],
        "evidence": ["save_evidence", "get_evidence", "search_evidence", "verify_evidence", "get_product_evidence_history", "detect_duplicate_evidence"],
        "comparison": ["normalize_product", "compare_prices", "compare_specifications", "compare_policies", "find_product_conflicts", "generate_comparison"],
        "trust": ["assess_evidence_quality", "check_source_freshness", "detect_unsupported_claims", "evaluate_source_consistency", "calculate_trust_assessment", "generate_trust_report"],
    }

    for s_name in servers:
        tools = await mcp_manager.list_tools(s_name)
        assert len(tools) == len(expected_tools[s_name]), f"Server {s_name} exposed {len(tools)} tools, expected {len(expected_tools[s_name])}"
        for exp in expected_tools[s_name]:
            assert exp in tools, f"Tool '{exp}' missing from server '{s_name}'"


# =========================================================================
# 2. Tool Invocation over stdio
# =========================================================================
@pytest.mark.anyio
async def test_actual_tool_invocation_over_stdio():
    """Verify tool execution over real stdio subprocess producing structured JSON and telemetry logs."""
    data, log_item = await mcp_manager.call_tool(
        server_name="trust",
        tool_name="check_source_freshness",
        arguments={
            "evidence_records": [
                {
                    "source_url": "https://apple.com/macbook",
                    "capture_timestamp": "2026-11-24T12:00:00Z",
                }
            ]
        },
    )
    assert log_item.status == "success"
    assert log_item.execution_time_ms > 0
    assert log_item.server_name == "trust"
    assert log_item.tool_name == "check_source_freshness"
    assert isinstance(data, dict)
    assert data["total_evaluated"] == 1
    assert data["fresh_count"] == 1


# =========================================================================
# 3. Error Handling: Unavailable Server & Timeouts
# =========================================================================
@pytest.mark.anyio
async def test_unavailable_server_handling():
    """Verify that attempting to connect to an unregistered server raises MCPServerConnectionError."""
    with pytest.raises(MCPServerConnectionError):
        await mcp_manager.call_tool("nonexistent_server", "dummy_tool")


@pytest.mark.anyio
async def test_timeout_handling():
    """Verify that an impossibly short timeout raises MCPTimeoutError."""
    with pytest.raises(MCPTimeoutError):
        await mcp_manager.call_tool("trust", "check_source_freshness", timeout_seconds=0.0001)


# =========================================================================
# 4. State Store Persistence and Recovery
# =========================================================================
def test_state_store_persistence_and_recovery(tmp_path):
    """Verify SQLite state persistence, stage updates, and post-restart recovery."""
    db_file = tmp_path / "test_inv.db"
    store = InvestigationStateStore(db_path=str(db_file))

    # Initialize investigation
    rec = default_investigation_engine.initialize_investigation(
        query="Dell XPS 15 9530",
        category="laptop",
        budget_inr=190000.0,
    )
    store.save_investigation(rec)

    # Update stage progress
    store.update_stage_progress(
        rec.investigation_id,
        InvestigationStage.PLAN,
        StageStatus.COMPLETED,
        "Stage 1 completed.",
    )

    # Simulate process restart by creating a new store instance pointing to same DB
    recovered_store = InvestigationStateStore(db_path=str(db_file))
    recovered_rec = recovered_store.get_investigation(rec.investigation_id)

    assert recovered_rec is not None
    assert recovered_rec.investigation_id == rec.investigation_id
    assert recovered_rec.query == "Dell XPS 15 9530"
    assert recovered_rec.stages["plan"].status == StageStatus.COMPLETED
    assert recovered_rec.stages["plan"].message == "Stage 1 completed."


# =========================================================================
# 5. Real End-to-End Multi-Stage Investigation with HTML Fixtures
# =========================================================================
@pytest.mark.anyio
async def test_end_to_end_real_investigation_with_local_fixture():
    """Execute complete 6-stage investigation over real MCP subprocesses using local HTML fixtures."""
    fixture_path = FIXTURES_DIR / "product_standard.html"
    assert fixture_path.exists(), "Test fixture product_standard.html must exist"
    fixture_url = f"file:///{fixture_path.as_posix()}"

    # Initialize investigation with fixture target URL
    rec = default_investigation_engine.initialize_investigation(
        query="Dell XPS 15 9530",
        category="laptop",
        budget_inr=200000.0,
        target_urls=[fixture_url],
    )

    # Execute all 6 stages over real stdio MCP subprocesses
    completed_rec = await default_investigation_engine.run_investigation(rec.investigation_id)

    # Assertions across the 6 stages
    assert completed_rec.status == "completed"
    assert completed_rec.current_stage == InvestigationStage.RESULT

    # STAGE 1: PLAN
    assert completed_rec.stages["plan"].status == StageStatus.COMPLETED
    assert fixture_url in completed_rec.target_urls

    # STAGE 2: BROWSER MCP
    assert completed_rec.stages["browser"].status == StageStatus.COMPLETED
    assert len(completed_rec.extracted_records) == 1
    extracted = completed_rec.extracted_records[0]
    assert "Dell XPS 15" in extracted["product_name"]
    assert extracted["numeric_price"] == 189999.0
    assert extracted["currency"] == "INR"
    assert extracted["evidence_hash"] is not None

    # STAGE 3: EVIDENCE MCP
    assert completed_rec.stages["evidence"].status == StageStatus.COMPLETED
    assert len(completed_rec.evidence_ids) == 1
    assert completed_rec.evidence_ids[0].startswith("evi_")

    # STAGE 4: COMPARISON MCP
    assert completed_rec.stages["comparison"].status == StageStatus.COMPLETED
    assert completed_rec.comparison_result is not None
    assert "product_identity" in completed_rec.comparison_result
    assert "price_comparison" in completed_rec.comparison_result

    # STAGE 5: TRUST MCP
    assert completed_rec.stages["trust"].status == StageStatus.COMPLETED
    assert completed_rec.trust_report is not None
    assert "trust_assessment" in completed_rec.trust_report
    assert "overall_trust_tier" in completed_rec.trust_report["trust_assessment"]

    # STAGE 6: RESULT
    assert completed_rec.stages["result"].status == StageStatus.COMPLETED
    assert completed_rec.summary is not None
    assert "Dell XPS 15 9530" in completed_rec.summary


# =========================================================================
# 6. API Integration Tests (Health MCP, Real Investigation, SSE)
# =========================================================================
@pytest.mark.anyio
async def test_api_mcp_health_endpoint():
    """Verify GET /api/health/mcp audits all four MCP servers over real stdio."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health/mcp")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["total_tools_count"] == 23
        assert "browser" in data["servers"]
        assert "evidence" in data["servers"]
        assert "comparison" in data["servers"]
        assert "trust" in data["servers"]
        assert data["servers"]["browser"]["status"] == "connected"
        assert data["servers"]["evidence"]["status"] == "connected"


@pytest.mark.anyio
async def test_api_real_investigation_endpoint():
    """Verify POST /api/investigations?mode=real triggers real orchestration."""
    fixture_path = FIXTURES_DIR / "product_standard.html"
    fixture_url = f"file:///{fixture_path.as_posix()}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "Dell XPS 15 9530",
            "category": "laptop",
            "budget_inr": 200000.0,
            "target_urls": [fixture_url],
            "mode": "real",
        }
        create_res = await client.post("/api/investigations", json=payload)
        assert create_res.status_code == 201
        created = create_res.json()
        assert created["id"].startswith("inv_")
        assert created["is_placeholder"] is False
        assert "REAL MCP ORCHESTRATION" in created["disclaimer"]

        # Retrieve investigation status
        inv_id = created["id"]
        get_res = await client.get(f"/api/investigations/{inv_id}")
        assert get_res.status_code == 200
        retrieved = get_res.json()
        assert retrieved["id"] == inv_id
        assert retrieved["is_placeholder"] is False


@pytest.mark.anyio
async def test_api_sse_events_endpoint():
    """Verify GET /api/investigations/{id}/events returns text/event-stream headers."""
    fixture_path = FIXTURES_DIR / "product_standard.html"
    fixture_url = f"file:///{fixture_path.as_posix()}"

    rec = default_investigation_engine.initialize_investigation(
        query="Dell XPS 15",
        target_urls=[fixture_url],
    )
    default_investigation_engine.state_store.complete_investigation(rec.investigation_id, "Done")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request stream endpoint
        async with client.stream("GET", f"/api/investigations/{rec.investigation_id}/events") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            # Read first line
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    assert "initial_state" in line
                    break
