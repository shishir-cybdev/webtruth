# WebTruth Evidence MCP Server (Phase 2C)

A dedicated, persistent Model Context Protocol (MCP) server built with the official **Python MCP SDK**, **SQLite**, and **SHA-256 cryptographic hashing**. It provides tamper-evident storage, integrity verification, chronological price tracking, and duplicate detection for investigative product claims.

---

## Architecture & Data Integrity Principles

- **Official MCP Protocol:** Implements the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`), communicating over standard I/O (`stdio`).
- **Persistent SQLite Storage:** Persists evidence records in an indexed SQLite database (`backend/data/evidence.db`). Records survive server restarts.
- **Immutable Evidence Records:** Evidence records are write-once, read-many. New observations or updates create distinct chronological records; existing rows are never silently overwritten.
- **Deterministic SHA-256 Hashing:** Recomputes canonical JSON hashes with sorted keys and normalized strings to verify that stored data has not been modified or corrupted.
- **No Hallucination / Price Preservation:** Verbatim displayed prices (e.g. `₹1,89,999.00`, `$1,299`) and currencies are preserved. Missing fields are stored as `null`/`None` and never invented.
- **Untrusted Web Content Safety:** Extracted claims and text snippets are treated strictly as untrusted data fields and never evaluated or executed.
- **Parameterized SQL:** All queries use parameterized statements (`?`) to prevent SQL injection.
- **Indexed Search Performance:** Six dedicated B-tree indexes cover `investigation_id`, `product_id`, `source_domain`, `evidence_type`, `evidence_hash`, and `source_url`.

---

## Tools Implemented

The server exposes 6 standardized MCP tools:

| Tool Name | Arguments | Output Schema | Description |
| :--- | :--- | :--- | :--- |
| `save_evidence` | `investigation_id, product_id, source_url, source_title, capture_timestamp, evidence_type, extracted_claims, raw_displayed_price, currency, numeric_price, evidence_hash, metadata` | `EvidenceRecord` | Validates, canonicalizes, computes SHA-256 hash, and inserts immutable evidence record into SQLite. |
| `get_evidence` | `evidence_id: str` | `Optional[EvidenceRecord]` | Retrieves a complete evidence record by its primary key ID (`evi_...`). |
| `search_evidence` | `investigation_id, product_id, source_domain, evidence_type, limit, offset` | `SearchEvidenceResult` | Dynamically searches stored records using indexed parameterized queries with pagination. |
| `verify_evidence` | `evidence_id: str` | `VerifyEvidenceResult` | Recomputes the SHA-256 hash from stored row data and compares it against the stored hash to detect tampering. |
| `get_product_evidence_history` | `product_id: str` | `ProductEvidenceHistoryResult` | Returns all records for a product sorted chronologically by capture timestamp, including historical price points. |
| `detect_duplicate_evidence` | `source_url, extracted_claims, investigation_id, product_id, evidence_hash` | `DuplicateEvidenceResult` | Identifies duplicate records with identical hash or identical URL and claims without deleting existing evidence. |

---

## Setup & Running with Windows PowerShell

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Virtual environment in `backend/venv`

### 2. Activate Virtual Environment

From the project root:
```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
.\venv\Scripts\Activate.ps1
```

### 3. Run the Evidence MCP Server in stdio Mode

```powershell
python -m mcp_servers.evidence
```

Or execute directly with the virtualenv binary:
```powershell
& "c:\Users\Admin\Desktop\webtruth\backend\venv\Scripts\python.exe" -m mcp_servers.evidence
```

---

## Configuration via Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `EVIDENCE_DB_PATH` | `backend/data/evidence.db` | Custom file path for the SQLite database. Can be set to `:memory:` for ephemeral testing. |

---

## MCP Host Configuration Example

To connect this Evidence MCP server to an MCP client (such as Claude Desktop or an agent harness), add this entry to your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "webtruth-evidence": {
      "command": "c:\\Users\\Admin\\Desktop\\webtruth\\backend\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_servers.evidence"],
      "cwd": "c:\\Users\\Admin\\Desktop\\webtruth\\backend",
      "env": {
        "EVIDENCE_DB_PATH": "c:\\Users\\Admin\\Desktop\\webtruth\\backend\\data\\evidence.db"
      }
    }
  }
}
```

---

## Running the Automated Test Suite

Run the isolated Evidence MCP test suite:
```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
.\venv\Scripts\pytest.exe tests/test_evidence_mcp.py -v
```

All 8 tests verify:
- MCP server tool discovery and registration (all 6 tools)
- Persistence across separate database connections and restarts
- Deterministic canonical SHA-256 hashing
- Tampered evidence detection (detects fraudulent direct SQL edits)
- Missing price preservation (`price: null`)
- Duplicate evidence detection
- Chronological price history ordering
- Direct tool execution through the MCP server interface

To run the entire WebTruth backend test suite (FastAPI + Browser MCP + Evidence MCP):
```powershell
.\venv\Scripts\pytest.exe tests -v
```
*(All 26 tests pass)*
