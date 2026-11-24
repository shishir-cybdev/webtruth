"""Phase 2H tests: sequential MCP health checks, single-flight locking, TTL caching, and session cleanup."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.orchestrator.mcp_manager import MCPManager
from app.orchestrator.schemas import ServerStatus


@pytest.mark.anyio
async def test_health_checks_run_sequentially_in_order(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "0")
    mgr = MCPManager()
    active_count = 0
    max_active = 0
    call_order = []

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        nonlocal active_count, max_active
        active_count += 1
        max_active = max(max_active, active_count)
        call_order.append(server_name)
        await asyncio.sleep(0.02)
        try:
            async def list_tools():
                return SimpleNamespace(tools=[SimpleNamespace(name=f"{server_name}_t1")])
            yield SimpleNamespace(list_tools=list_tools)
        finally:
            active_count -= 1

    with patch.object(mgr, "open_session", side_effect=fake_open_session):
        res = await mgr.check_all_health()

    assert max_active == 1
    assert call_order == ["browser", "evidence", "comparison", "trust"]
    assert res.status == "healthy"
    assert res.total_tools_count == 4


@pytest.mark.anyio
async def test_failed_server_does_not_prevent_later_checks(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "0")
    mgr = MCPManager()
    checked = []

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        checked.append(server_name)
        if server_name == "evidence":
            raise TimeoutError("simulated 30s timeout")
        async def list_tools():
            return SimpleNamespace(tools=[SimpleNamespace(name="t1"), SimpleNamespace(name="t2")])
        yield SimpleNamespace(list_tools=list_tools)

    with patch.object(mgr, "open_session", side_effect=fake_open_session):
        res = await mgr.check_all_health()

    assert checked == ["browser", "evidence", "comparison", "trust"]
    assert res.status == "degraded"
    assert res.servers["evidence"].status == ServerStatus.ERROR
    assert res.servers["browser"].status == ServerStatus.CONNECTED
    assert res.servers["comparison"].status == ServerStatus.CONNECTED
    assert res.servers["trust"].status == ServerStatus.CONNECTED
    assert res.total_tools_count == 6


@pytest.mark.anyio
async def test_concurrent_health_requests_share_single_check(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "60")
    mgr = MCPManager()
    invocations = 0

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        nonlocal invocations
        invocations += 1
        await asyncio.sleep(0.03)
        async def list_tools():
            return SimpleNamespace(tools=[SimpleNamespace(name="t1")])
        yield SimpleNamespace(list_tools=list_tools)

    with patch.object(mgr, "open_session", side_effect=fake_open_session):
        r1, r2, r3 = await asyncio.gather(
            mgr.check_all_health(),
            mgr.check_all_health(),
            mgr.check_all_health(),
        )

    # Only one 4-server batch executed across all 3 concurrent callers
    assert invocations == 4
    assert r1.total_tools_count == r2.total_tools_count == r3.total_tools_count == 4


@pytest.mark.anyio
async def test_cached_health_reused_within_ttl(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "60")
    mgr = MCPManager()
    invocations = 0

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        nonlocal invocations
        invocations += 1
        async def list_tools():
            return SimpleNamespace(tools=[SimpleNamespace(name="t1")])
        yield SimpleNamespace(list_tools=list_tools)

    with patch.object(mgr, "open_session", side_effect=fake_open_session):
        r1 = await mgr.check_all_health()
        r2 = await mgr.check_all_health()

    assert invocations == 4
    assert r1 is r2


@pytest.mark.anyio
async def test_ttl_zero_bypasses_cache(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "0")
    mgr = MCPManager()
    invocations = 0

    @asynccontextmanager
    async def fake_open_session(server_name: str, timeout_seconds=None):
        nonlocal invocations
        invocations += 1
        async def list_tools():
            return SimpleNamespace(tools=[SimpleNamespace(name="t1")])
        yield SimpleNamespace(list_tools=list_tools)

    with patch.object(mgr, "open_session", side_effect=fake_open_session):
        await mgr.check_all_health()
        await mgr.check_all_health()

    assert invocations == 8


@pytest.mark.anyio
async def test_exceptions_close_subprocess_sessions(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "0")
    mgr = MCPManager()
    closed_sessions = []

    @asynccontextmanager
    async def fake_stdio_client(params):
        name = params.args[-1]
        try:
            yield (object(), object())
        finally:
            closed_sessions.append(name)

    class FailingSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def initialize(self):
            raise RuntimeError("boom during init")

    with (
        patch("app.orchestrator.mcp_manager.stdio_client", side_effect=fake_stdio_client),
        patch("app.orchestrator.mcp_manager.ClientSession", FailingSession),
    ):
        res = await mgr.check_all_health()

    assert len(closed_sessions) == 4
    assert res.status == "unhealthy"


@pytest.mark.anyio
async def test_all_four_servers_retain_real_tool_counts_and_statuses(monkeypatch):
    monkeypatch.setenv("MCP_HEALTH_CACHE_TTL_SECONDS", "0")
    mgr = MCPManager()
    res = await mgr.check_all_health()

    assert res.status == "healthy"
    assert res.servers["browser"].status == ServerStatus.CONNECTED
    assert res.servers["browser"].tool_count == 6
    assert res.servers["evidence"].status == ServerStatus.CONNECTED
    assert res.servers["evidence"].tool_count >= 5
    assert res.servers["comparison"].status == ServerStatus.CONNECTED
    assert res.servers["comparison"].tool_count >= 5
    assert res.servers["trust"].status == ServerStatus.CONNECTED
    assert res.servers["trust"].tool_count >= 5
    assert res.total_tools_count >= 21
