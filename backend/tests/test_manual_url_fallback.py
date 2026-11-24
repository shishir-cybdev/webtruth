from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.orchestrator.investigation_engine import InvestigationEngine
from app.orchestrator.investigation_state import InvestigationStateStore
from app.orchestrator.schemas import StageStatus, ToolCallLog
from app.schemas.investigation import InvestigationCreateRequest
from mcp_servers.browser.config import BrowserConfig

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_target_urls_normalization_in_request_schema():
    """Whitespace-only entries are dropped and duplicate URLs are deduplicated."""
    req = InvestigationCreateRequest(
        query="Samsung S24 Ultra",
        target_urls=[
            "  https://www.samsung.com/in/smartphones/galaxy-s24-ultra/  ",
            "",
            "   ",
            "https://www.samsung.com/in/smartphones/galaxy-s24-ultra/",
        ],
    )
    assert req.target_urls == ["https://www.samsung.com/in/smartphones/galaxy-s24-ultra/"]

    empty_req = InvestigationCreateRequest(
        query="Samsung S24 Ultra",
        target_urls=["  ", ""],
    )
    assert empty_req.target_urls is None


def test_discovery_timeout_config_and_allowlist():
    """Discovery timeout defaults to 12000ms and security path blocking remains intact."""
    assert BrowserConfig.DISCOVERY_TIMEOUT_MS >= 12000

    ok, _ = BrowserConfig.is_url_permitted("https://www.samsung.com/in/smartphones/galaxy-s24-ultra/")
    assert ok is True

    ok_oneplus, _ = BrowserConfig.is_url_permitted("https://www.oneplus.in/oneplus-13")
    assert ok_oneplus is True

    blocked, _ = BrowserConfig.is_url_permitted("https://www.samsung.com/in/checkout")
    assert blocked is False


@pytest.mark.anyio
async def test_manual_urls_bypass_discovery_and_complete_pipeline(tmp_path, monkeypatch):
    """When target_urls are supplied, discovery is skipped and full MCP pipeline runs."""
    fixture_path = FIXTURES_DIR / "product_standard.html"
    assert fixture_path.exists()
    fixture_url = f"file:///{fixture_path.as_posix()}"

    store = InvestigationStateStore(db_path=str(tmp_path / "manual_url_inv.db"))
    engine = InvestigationEngine(state_store=store)

    called_tools: list[str] = []
    orig_call = engine.mcp.call_tool_on_session

    async def spy_call_tool_on_session(session, server_name, tool_name, arguments=None, timeout_seconds=30.0):
        called_tools.append(f"{server_name}.{tool_name}")
        return await orig_call(session, server_name, tool_name, arguments=arguments, timeout_seconds=timeout_seconds)

    monkeypatch.setattr(engine.mcp, "call_tool_on_session", spy_call_tool_on_session)

    rec = engine.initialize_investigation(
        query="Dell XPS 15 9530",
        category="laptop",
        target_urls=[fixture_url],
    )
    await engine.run_investigation(rec.investigation_id)
    final_rec = store.get_investigation(rec.investigation_id)

    assert final_rec is not None
    assert final_rec.status == "completed"
    assert "browser.discover_product_urls" not in called_tools
    assert "browser.open_product_page" in called_tools
    assert "browser.extract_product_data" in called_tools
    assert "browser.capture_page_evidence" in called_tools

    assert final_rec.stages["plan"].status == StageStatus.COMPLETED
    assert final_rec.stages["browser"].status == StageStatus.COMPLETED
    assert final_rec.stages["evidence"].status == StageStatus.COMPLETED
    assert final_rec.stages["comparison"].status == StageStatus.COMPLETED
    assert final_rec.stages["trust"].status == StageStatus.COMPLETED
    assert len(final_rec.evidence_ids) == 1
    assert final_rec.comparison_result is not None
    assert final_rec.trust_report is not None


@pytest.mark.anyio
async def test_zero_discovery_returns_clear_warnings_without_fabrication(tmp_path, monkeypatch):
    """When automatic discovery returns 0 URLs, clear retailer warnings are returned and nothing is fabricated."""
    store = InvestigationStateStore(db_path=str(tmp_path / "zero_disc_inv.db"))
    engine = InvestigationEngine(state_store=store)

    orig_open = engine.mcp.open_session
    orig_call = engine.mcp.call_tool_on_session

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        if server_name == "browser":
            yield object()
            return
        async with orig_open(server_name, timeout_seconds=timeout_seconds) as session:
            yield session

    async def fake_call_tool_on_session(session, server_name, tool_name, arguments=None, timeout_seconds=30.0):
        if server_name == "browser" and tool_name == "discover_product_urls":
            log = ToolCallLog(
                call_id="call_test_zero",
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments or {},
                status="success",
                execution_time_ms=10.0,
            )
            return {
                "query": arguments.get("query"),
                "category": arguments.get("category"),
                "discovered_urls": [],
                "blocked_sources": [
                    "amazon.in: HTTP 503",
                    "croma.com: HTTP 403",
                    "flipkart.com: Browser navigation timed out after 12000ms",
                ],
                "discovery_notes": [
                    "No product URLs could be legitimately discovered from permitted search endpoints. Supply explicit public product URLs or use local HTML test fixtures."
                ],
            }, log
        return await orig_call(session, server_name, tool_name, arguments=arguments, timeout_seconds=timeout_seconds)

    monkeypatch.setattr(engine.mcp, "open_session", fake_open_session)
    monkeypatch.setattr(engine.mcp, "call_tool_on_session", fake_call_tool_on_session)

    rec = engine.initialize_investigation(query="Samsung S24 Ultra", category="smartphone")
    await engine.run_investigation(rec.investigation_id)
    final_rec = store.get_investigation(rec.investigation_id)

    assert final_rec is not None
    assert final_rec.status == "completed"
    assert final_rec.target_urls == []
    assert final_rec.evidence_ids == []
    assert final_rec.comparison_result is None
    assert final_rec.stages["browser"].status == StageStatus.SKIPPED
    assert final_rec.stages["evidence"].status == StageStatus.SKIPPED
    assert final_rec.stages["comparison"].status == StageStatus.SKIPPED
    assert "Search blocked: amazon.in: HTTP 503" in final_rec.warnings
    assert "Search blocked: croma.com: HTTP 403" in final_rec.warnings
    assert any("flipkart.com" in w for w in final_rec.warnings)
