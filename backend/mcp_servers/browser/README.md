# WebTruth Browser MCP Server (Phase 2B)

An independent Model Context Protocol (MCP) server built with the official **Python MCP SDK** and **Playwright**. Its purpose is to investigate publicly accessible product pages and extract verifiable, evidence-backed product data.

---

## Key Features & Design Principles

- **Official MCP Protocol:** Implements the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`), communicating over standard I/O (`stdio`).
- **Domain Allowlist:** Strictly restricts page navigation to an explicit, configurable allowlist of domains (e.g., `amazon.in`, `flipkart.com`, `croma.com`, `dell.com`, `apple.com`, `localhost`, and `file://` local fixtures).
- **Public Pages Only:** Automatically blocks authenticated, sensitive, or checkout paths (e.g. `/login`, `/cart`, `/checkout`, `/account`).
- **Zero Hallucination / No Price Fabrication:** Missing prices, specifications, or stock statuses are represented as `null`/`None`. They are never guessed or manufactured.
- **Original Currency Preserved:** Displayed prices and original currencies are extracted as verbatim facts. No currency conversion to INR is performed unless exchange rates and timestamps are explicitly provided.
- **Cryptographic Evidence Audit Trail:** Every captured page generates a canonical SHA-256 fingerprint alongside verbatim text snippets, source URL, and UTC timestamps.
- **Robust Multi-Strategy Extraction:** Combines authoritative Schema.org JSON-LD (`schema.org/Product`), OpenGraph metadata (`og:*`), and resilient HTML specification table parsing.

---

## Tools Implemented

The server provides 5 standardized MCP tools:

| Tool Name | Arguments | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `open_product_page` | `url: str` | Opens an allowed product page in headless Chromium. Enforces domain allowlist. | `OpenProductPageResult` (status, final URL, title, timestamp) |
| `extract_product_data` | `url: str` | Extracts product name, brand, model, displayed price, currency, availability, specs, and warranty. | `ExtractedProductDataResult` |
| `extract_structured_product_data` | `url: str` | Parses Product JSON-LD script blocks, OpenGraph tags, and meta tags. | `StructuredProductDataResult` |
| `capture_page_evidence` | `url: str` | Captures key page text snippets and computes a canonical SHA-256 hash. | `PageEvidenceRecordResult` |
| `inspect_page_metadata` | `url: str` | Returns canonical URL, all `<meta>` properties, and detected schema.org types. | `PageMetadataResult` |

---

## Setup & Running with Windows PowerShell

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Playwright Chromium browser installed

### 2. Activate Virtual Environment & Install Dependencies

From the project root:
```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements (if not already installed)
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Running the MCP Server (stdio Mode)

To run the MCP server as a standalone stdio process (e.g., for connection to Claude Desktop, Gemini CLI, or an MCP client):

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
python -m mcp_servers.browser
```

Or execute directly with the virtualenv binary:
```powershell
& "c:\Users\Admin\Desktop\webtruth\backend\venv\Scripts\python.exe" -m mcp_servers.browser
```

---

## Configuration via Environment Variables

The server can be configured via environment variables or a `.env` file in the backend root:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `BROWSER_ALLOWED_DOMAINS` | `amazon.in,flipkart.com,croma.com,dell.com,apple.com,asus.com,hp.com,sony.co.in` | Comma-separated list of permitted domains. `localhost` and `file://` are always permitted. |
| `BROWSER_HEADLESS` | `true` | Run Chromium in headless mode (`true`/`false`). |
| `BROWSER_PAGE_TIMEOUT_MS` | `25000` | Navigation timeout in milliseconds (25 seconds). |
| `BROWSER_DOM_WAIT_TIMEOUT_MS` | `5000` | DOM selector wait timeout in milliseconds. |

---

## MCP Client Configuration Example

To connect this browser MCP server to an MCP host (such as Claude Desktop or another agent harness), add the following entry to your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "webtruth-browser": {
      "command": "c:\\Users\\Admin\\Desktop\\webtruth\\backend\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_servers.browser"],
      "cwd": "c:\\Users\\Admin\\Desktop\\webtruth\\backend",
      "env": {
        "BROWSER_HEADLESS": "true"
      }
    }
  }
}
```

---

## Running the Automated Test Suite

The test suite includes end-to-end tests with real Playwright headless navigation against local HTML fixtures (standard product with JSON-LD, missing price page, and malformed HTML):

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
.\venv\Scripts\pytest.exe tests/test_browser_mcp.py -v
```

All 13 Browser MCP tests verify:
- MCP server tool discovery and registration
- Permitted vs. disallowed domain filtering
- Blocked sensitive path rejection (`/login`, `/checkout`)
- Extraction of specifications, brand, model, and prices without hallucination
- Missing price handling (`price: null`)
- SHA-256 evidence hashing and verification
- Malformed HTML resiliency
