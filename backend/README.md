# WebTruth Backend — Phase 2A

FastAPI-powered backend service for the **WebTruth** product investigation platform.

> [!NOTE]
> **Phase 2A Status: Backend Core & Placeholder Service**
> This phase establishes the modular FastAPI application, typed Pydantic contracts, CORS configuration for the Next.js frontend, and the `InvestigationServiceInterface`. All investigation results returned by the service in Phase 2A are explicitly flagged as `is_placeholder: true` with honest disclaimers. Real MCP intelligence agents (PriceSpider, ReviewSense, SpecVerify, TrustScore, PriceAlert) will be integrated in Phase 2B.

---

## Architecture Overview

```
backend/
├── app/
│   ├── __init__.py           # Application package metadata
│   ├── main.py               # FastAPI entry point, middleware, exception handlers
│   ├── config.py             # Pydantic Settings and environment configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py         # GET /api/health
│   │   └── investigations.py # POST /api/investigations, GET /api/investigations/{id}
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── health.py         # HealthResponse schema
│   │   └── investigation.py  # InvestigationCreateRequest, InvestigationResponse, etc.
│   └── services/
│       ├── __init__.py
│       └── investigation_service.py # InvestigationServiceInterface & PlaceholderImplementation
├── tests/
│   └── test_api.py           # Pytest test suite for health, investigations, CORS, validation
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This documentation
```

---

## Prerequisites

- **Python 3.10+** (Python 3.12+ recommended; tested on Python 3.14)
- **Windows PowerShell**

---

## Setup & Running with Windows PowerShell

### 1. Navigate to the backend directory

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
```

### 2. Create and activate a Virtual Environment

```powershell
# Create virtual environment (if not already created)
py -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

> *Tip: If you encounter an execution policy error when activating, run:*
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start the Uvicorn Server

```powershell
# Option A: Using the activated virtual environment
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option B: Direct one-line command from project root
& "c:\Users\Admin\Desktop\webtruth\backend\venv\Scripts\uvicorn.exe" app.main:app --app-dir "c:\Users\Admin\Desktop\webtruth\backend" --host 0.0.0.0 --port 8000 --reload
```

The API will now be available at:
- **Interactive OpenAPI Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## Running the Automated Test Suite

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
.\venv\Scripts\pytest.exe tests -v
```

All 5 test cases will run against the ASGI application verifying:
- Health check response schema and metadata
- Product investigation creation and field normalization
- Input validation rejection rules (e.g., empty query, negative budget)
- Investigation retrieval by ID and 404 handling
- CORS origin headers for `http://localhost:3000`

---

## API Endpoints

### 1. Health Check
- **Route:** `GET /api/health`
- **Description:** Returns service status, version, UTC timestamp, and MCP integration readiness.
- **Sample Response:**
```json
{
  "status": "healthy",
  "app_name": "WebTruth API",
  "version": "0.2.0-phase2a",
  "environment": "development",
  "timestamp": "2026-11-24T15:10:00Z",
  "mcp_status": "Phase 2B - Pending Integration"
}
```

### 2. Create Investigation
- **Route:** `POST /api/investigations`
- **Status:** `201 Created`
- **Request Body:**
```json
{
  "query": "Dell XPS 15 9530",
  "category": "laptop",
  "budget_inr": 189999.0,
  "notes": "Looking for OLED 3.5K display variant"
}
```
- **Sample Response:**
```json
{
  "id": "inv_a8f9c2d1e0b4",
  "query": "Dell XPS 15 9530",
  "category": "laptop",
  "budget_inr": 189999.0,
  "status": "processing",
  "created_at": "2026-11-24T15:10:05Z",
  "updated_at": "2026-11-24T15:10:05Z",
  "is_placeholder": true,
  "disclaimer": "PHASE 2A DEMO MODE: This investigation was processed by the Phase 2A placeholder service. No live e-commerce prices, external reviews, or seller data were scraped. Real multi-source MCP intelligence agent integrations begin in Phase 2B.",
  "pipeline_steps": [
    {
      "step_id": "step-query-parse",
      "label": "Query Understanding",
      "mcp_server": "PriceSpider MCP",
      "status": "completed",
      "description": "Parses product intent, identifies model numbers, and normalizes brand/category terms.",
      "message": "Query validated and parsed. Ready for multi-agent dispatch."
    },
    {
      "step_id": "step-price-crawl",
      "label": "Price Spider Ingestion",
      "mcp_server": "PriceSpider MCP",
      "status": "pending",
      "description": "Searches 50+ Indian e-commerce sites for live and historical pricing signals.",
      "message": "Phase 2B pending: PriceSpider MCP tool 'fetch_price' not yet active."
    }
  ],
  "summary": "Investigation initialized for 'Dell XPS 15 9530' in category 'laptop' within budget of ₹189,999. Pipeline stage 1 (Query Understanding) completed. Subsequent MCP agent stages are currently in placeholder mode awaiting Phase 2B server hookups."
}
```

### 3. Retrieve Investigation
- **Route:** `GET /api/investigations/{investigation_id}`
- **Description:** Returns the current state and steps of an investigation by ID (returns 404 if not found).

### 4. List Investigations
- **Route:** `GET /api/investigations?limit=20&offset=0`
- **Description:** Returns a list of recently created investigations with pagination.

---

## Limitations in Phase 2A

1. **In-Memory Storage:** Investigations are stored in memory within the `PlaceholderInvestigationService`. They will reset upon server restart. (Database persistence planned for future phase).
2. **Simulated Pipeline Execution:** Stages 2 through 6 reflect placeholder states until Phase 2B connects the live MCP servers.
3. **No External Scraping:** No live web scrapers, paid APIs, or external price lookups are performed.
