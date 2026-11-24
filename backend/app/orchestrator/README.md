# WEBTRUTH - MCP Orchestration Layer (Phase 2F)

The **WEBTRUTH MCP Orchestration Layer** connects and coordinates all four independently implemented Model Context Protocol (MCP) servers:
1. **`mcp_servers.browser`** (Browser MCP Server)
2. **`mcp_servers.evidence`** (Evidence MCP Server)
3. **`mcp_servers.comparison`** (Comparison MCP Server)
4. **`mcp_servers.trust`** (Trust MCP Server)

---

## Architectural Guarantee: Real MCP Client Protocol over stdio

This orchestration layer does **not** import or call internal service functions directly. Instead, it utilizes the official Python MCP SDK client transport (`mcp.client.stdio.stdio_client`) and session protocol (`mcp.client.session.ClientSession`).

Each MCP server is launched as an independent operating system subprocess communicating via standard input/output (`stdio`) JSON-RPC messages. The orchestrator initializes protocol sessions, dynamically discovers exposed tools, invokes them with schema validation, captures structured telemetry logs, and terminates subprocesses cleanly.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Web Layer                               │
│      POST /api/investigations       GET /api/investigations/{id}       │
│      GET /api/health/mcp            GET /api/investigations/{id}/events│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Investigation Engine (Phase 2F)                      │
│            Multi-stage coordinator & SSE event broadcaster             │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       MCP Manager & Registry         │  │   SQLite Investigation Store │
│ Stdio subprocess lifecycle & logs    │  │   investigations.db (State)  │
└───────┬──────────┬──────────┬────────┘  └──────────────────────────────┘
        │ stdio    │ stdio    │ stdio    │ stdio
        ▼          ▼          ▼          ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Browser MCP  │ │ Evidence MCP │ │Comparison MCP│ │  Trust MCP   │
│ (Playwright) │ │  (SQLite)    │ │(Normalizer)  │ │(Integrity)   │
│   5 Tools    │ │   6 Tools    │ │   6 Tools    │ │   6 Tools    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## The 6-Stage Investigation Workflow

When a product investigation request is initiated:

### STAGE 1 — PLAN
- Validates query, product category, and optional budget in INR.
- Identifies approved public domains from the browser allowlist.
- Determines safe target URLs for multi-source inspection.

### STAGE 2 — BROWSER MCP
- Launches `mcp_servers.browser` via stdio.
- Invokes `open_product_page(url)`, `extract_product_data(url)`, and `capture_page_evidence(url)`.
- Extracts product name, brand, model, displayed prices, currency, specifications, and DOM snippet hashes.
- Never bypasses CAPTCHAs, paywalls, or authentication barriers.

### STAGE 3 — EVIDENCE MCP
- Launches `mcp_servers.evidence` via stdio.
- Invokes `save_evidence(evidence_data)` for every extracted record.
- Persists immutable records into SQLite (`backend/data/evidence.db`).
- Returns traceable `evidence_id`s with canonical SHA-256 hashes.

### STAGE 4 — COMPARISON MCP
- Launches `mcp_servers.comparison` via stdio.
- Invokes `normalize_product` to extract canonical spec tokens and compute configuration fingerprints.
- Invokes `compare_prices` (with strict currency mismatch protection).
- Invokes `compare_specifications`, `compare_policies`, and `find_product_conflicts`.
- Synthesizes a structured `ComprehensiveComparisonResult`.

### STAGE 5 — TRUST MCP
- Launches `mcp_servers.trust` via stdio.
- Invokes `assess_evidence_quality`, `check_source_freshness`, `detect_unsupported_claims`, `evaluate_source_consistency`, and `calculate_trust_assessment`.
- Generates an explainable `TrustReportResult` with actionable consumer verification guidance.

### STAGE 6 — RESULT
- Synthesizes findings, evidence IDs, comparison outputs, trust assessments, and audit logs.
- Persists the completed investigation record into SQLite (`backend/data/investigations.db`).
- Broadcasts final completion event to connected SSE subscribers.

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/investigations` | Start a product investigation (`mode='real'` for live MCP or default demo). |
| `GET` | `/api/investigations/{id}` | Retrieve current status, pipeline stages, and findings. |
| `GET` | `/api/investigations/{id}/events` | Real-time Server-Sent Events (SSE) streaming stage progress and tool calls. |
| `GET` | `/api/health/mcp` | Live audit of all 4 stdio MCP servers, process status, and tool counts. |
| `GET` | `/api/health` | Backend service health and version metadata. |

---

## Windows PowerShell Commands

### 1. Inspect MCP Ecosystem Health
```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
& "venv\Scripts\python.exe" -c "
import asyncio
from app.orchestrator.mcp_manager import mcp_manager

async def test():
    health = await mcp_manager.check_all_health()
    print('Overall Status:', health.status)
    print('Total Tools:', health.total_tools_count)
    for name, s in health.servers.items():
        print(f'  {name}: {s.status.value} ({s.tool_count} tools, {s.latency_ms}ms)')

asyncio.run(test())
"
```

### 2. Start the FastAPI Backend
```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
& "venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Run Pytest Test Suites
```powershell
# Run Orchestrator and Integration tests
& "venv\Scripts\python.exe" -m pytest tests/test_orchestrator.py -v

# Run the complete WEBTRUTH test suite
& "venv\Scripts\python.exe" -m pytest tests -v
```
