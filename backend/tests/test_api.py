import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.anyio
async def test_health_endpoint():
    """Verify GET /api/health returns 200 and expected metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "WebTruth API"
        assert "0.2.0-phase2a" in data["version"]
        assert "timestamp" in data
        assert "Phase 2B" in data["mcp_status"]


@pytest.mark.anyio
async def test_create_investigation_valid():
    """Verify POST /api/investigations creates an investigation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "Dell XPS 15 9530",
            "category": "laptop",
            "budget_inr": 185000.0,
            "notes": "Looking for 32GB RAM variant"
        }
        response = await client.post("/api/investigations", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"].startswith("inv_")
        assert data["query"] == "Dell XPS 15 9530"
        assert data["category"] == "laptop"
        assert data["budget_inr"] == 185000.0
        assert data["is_placeholder"] is True
        assert "PHASE 2A DEMO MODE" in data["disclaimer"]
        assert len(data["pipeline_steps"]) == 6
        assert data["pipeline_steps"][0]["status"] == "completed"
        assert data["pipeline_steps"][1]["status"] == "pending"


@pytest.mark.anyio
async def test_create_investigation_validation_error():
    """Verify POST /api/investigations validates input."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Empty query
        response = await client.post("/api/investigations", json={"query": "   "})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation Error"

        # Negative budget
        response = await client.post("/api/investigations", json={"query": "iPhone 16", "budget_inr": -500})
        assert response.status_code == 422


@pytest.mark.anyio
async def test_get_investigation_by_id():
    """Verify GET /api/investigations/{id} returns created item or 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create first
        res = await client.post("/api/investigations", json={"query": "MacBook Pro 14 M3"})
        created = res.json()
        inv_id = created["id"]

        # Retrieve
        get_res = await client.get(f"/api/investigations/{inv_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == inv_id
        assert get_res.json()["query"] == "MacBook Pro 14 M3"

        # Non-existent ID
        missing = await client.get("/api/investigations/inv_nonexistent999")
        assert missing.status_code == 404


@pytest.mark.anyio
async def test_cors_headers():
    """Verify CORS headers for localhost:3000."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Origin": "http://localhost:3000"}
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

        vercel_res = await client.options(
            "/api/investigations",
            headers={
                "Origin": "https://webtruth.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert vercel_res.headers.get("access-control-allow-origin") == "https://webtruth.vercel.app"
        assert vercel_res.headers.get("access-control-allow-credentials") == "true"
