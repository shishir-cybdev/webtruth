# WEBTRUTH - Comparison MCP Server (Phase 2D)

The **WEBTRUTH Comparison MCP Server** is a standalone, deterministic Model Context Protocol (MCP) server designed to normalize product specifications, compare verified evidence records, detect conflicting claims across retailers, audit policies (warranty, returns, replacement, delivery), and generate evidence-backed comparison reports.

It communicates through standard input/output (`stdio`) using the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`), maintaining compatibility with Browser MCP (Phase 2B) and Evidence MCP (Phase 2C).

---

## Core Design Principles

1. **Deterministic Processing (No AI Hallucinations)**:
   - Specification matching, price differences, and conflict detection use rule-based, deterministic Python algorithms.
   - Values are never guessed, hallucinated, or fabricated.
2. **Configuration Fingerprinting**:
   - Products are categorized by a deterministic configuration hash combining `brand`, `model`, `model_number`, `cpu`, `ram`, `storage`, and `gpu`.
   - Different product configurations (e.g. 16GB RAM vs 32GB RAM, or Dell XPS 9520 vs 9530) are **never falsely equated**.
3. **Preservation of Raw Values**:
   - Every normalization step retains both `raw_value` and `normalized_value` alongside extracted units, numeric values, and confidence scores.
4. **Currency Mismatch Protection**:
   - Price differences and spreads are calculated **only** when currencies match (or an explicit conversion rate is supplied).
   - If currencies differ (e.g., USD vs INR), numeric subtraction is suppressed and flagged with `currency_mismatch_detected=True`.
5. **Full Evidence Traceability**:
   - Every claim, spec, price point, policy item, and conflict links back to its originating `evidence_id`, `source_url`, and `source_domain`.
6. **Explicit Absence Flagging**:
   - Missing fields (e.g. absent warranty or return window) are explicitly flagged as `is_missing=True`, never treated as zero or invented.

---

## Architecture & Directory Structure

```
backend/mcp_servers/comparison/
├── __init__.py               # Package exports
├── __main__.py               # Entrypoint: python -m mcp_servers.comparison
├── server.py                 # MCP server instance with 6 registered @server.tool definitions
├── schemas.py                # Strongly typed Pydantic models for inputs and outputs
├── normalization.py          # Deterministic normalizers (brand, model, CPU, RAM, storage, etc.)
├── comparison_service.py     # Core business logic: price spreads, spec diffs, policy audit, conflicts
└── README.md                 # This documentation
```

---

## Functional MCP Tools

### 1. `normalize_product`
Normalizes raw product fields while preserving original strings, units, and numeric values.
- **Inputs**:
  - `product_name` (str)
  - `brand` (optional str)
  - `model` (optional str)
  - `model_number` (optional str)
  - `specifications` (optional dict of key/values)
  - `source_evidence_id` (optional str)
  - `source_url` (optional str)
- **Outputs**: `NormalizedProduct` containing normalized fields (`brand`, `model`, `model_number`, `ram`, `storage`, `cpu`, `gpu`, `screen_size`, `additional_specs`) and a `configuration_fingerprint`.

### 2. `compare_prices`
Compares displayed prices across evidence records.
- **Inputs**: `price_records` (list of dicts containing `source_url`, `raw_displayed_price`, `currency`, `numeric_price`, `evidence_id`, etc.)
- **Outputs**: `PriceComparisonResult` with:
  - `price_points`: List of normalized price records.
  - `lowest_price`, `highest_price`, `average_price`, `price_spread` (only computed if currencies match).
  - `cheapest_source_url`, `cheapest_evidence_id`.
  - `currency_mismatch_detected`: Boolean flag indicating if mismatched currencies were encountered.
  - `missing_price_count`: Number of sources lacking a numeric price.

### 3. `compare_specifications`
Compares technical specifications between matching or differing products.
- **Inputs**: `products` (list of raw product dicts or normalized products)
- **Outputs**: `SpecComparisonResult` with:
  - `configuration_match`: True if all sources share the same configuration fingerprint.
  - `common_specs`: Specifications that match identically across all sources.
  - `differing_specs`: Specifications with variances across sources.
  - `missing_specs_per_source`: Specs present in some sources but missing in others.

### 4. `compare_policies`
Audits warranty, return, replacement, and delivery policies across sources.
- **Inputs**: `policy_records` (list of dicts with `source_url`, `warranty`, `return_policy`, `replacement_policy`, `delivery_info`, `evidence_id`)
- **Outputs**: `PolicyComparisonResult` with:
  - Audited `items` flagged with `is_missing` and `is_ambiguous` (e.g., "standard warranty applies" or "contact seller").
  - `has_missing_policies`: Boolean flag.
  - `ambiguous_policy_count`: Total ambiguous terms found.

### 5. `find_product_conflicts`
Identifies conflicting factual claims for the same field across multiple evidence sources.
- **Inputs**: `products` (list of product dicts)
- **Outputs**: `ProductConflictResult` with:
  - `has_conflicts`: True if conflicting claims exist.
  - `conflicts`: List of `ProductConflictItem` detailing the field, distinct claims, and evidence IDs asserting each claim.

### 6. `generate_comparison`
Produces a unified, comprehensive comparison synthesizing product identities, price spreads, spec differences, policy audits, conflicting claims, and unknown fields.
- **Inputs**: `evidence_records` (list of evidence records as produced by Browser MCP and stored in Evidence MCP)
- **Outputs**: `ComprehensiveComparisonResult` containing:
  - `comparison_id`, `generated_at`.
  - `products`: List of normalized products with fingerprints.
  - `all_same_configuration`: Boolean flag.
  - `configuration_clusters`: Mapping of fingerprint to product IDs.
  - `price_analysis`: Embedded `PriceComparisonResult`.
  - `spec_analysis`: Embedded `SpecComparisonResult`.
  - `policy_analysis`: Embedded `PolicyComparisonResult`.
  - `conflicts`: Embedded `ProductConflictResult`.
  - `evidence_references`: List of all contributing evidence IDs and domains.

---

## Running & Testing

### 1. Activate Environment (Windows PowerShell)

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
& "venv\Scripts\Activate.ps1"
```

### 2. Run the Comparison MCP Server via stdio

```powershell
& "venv\Scripts\python.exe" -m mcp_servers.comparison
```
The server will start listening for JSON-RPC messages on standard input/output (`stdio`).

### 3. Run Pytest Test Suite

```powershell
# Run Comparison MCP tests specifically
& "venv\Scripts\python.exe" -m pytest tests/test_comparison_mcp.py -v

# Run the complete WEBTRUTH backend test suite (FastAPI, Browser MCP, Evidence MCP, Comparison MCP)
& "venv\Scripts\python.exe" -m pytest tests -v
```

---

## Test Scenarios Covered

The `tests/test_comparison_mcp.py` test suite comprehensively covers:
1. `test_comparison_mcp_tool_discovery`: Verifies all 6 tools are discovered on the MCP server instance.
2. `test_mcp_tools_e2e_invocation`: End-to-end execution of all 6 tools through server tool endpoints.
3. `test_normalization_preserves_raw_values`: Confirms raw text is never lost when normalized.
4. `test_same_product_across_multiple_retailers`: Identical configuration detection and price spread across retailers.
5. `test_similar_names_different_model_numbers`: Verifies Dell XPS 9520 and 9530 receive distinct fingerprints and are flagged as different configurations.
6. `test_different_ram_storage_configurations`: Verifies 16GB vs 32GB RAM variations are identified as distinct configurations.
7. `test_price_comparison_with_spread`: Mathematical accuracy of min, max, avg, and spread.
8. `test_missing_prices_handling`: Safe handling when prices are absent without hallucination.
9. `test_currency_mismatch_suppresses_spread`: Suppression of numeric spread when comparing USD vs INR.
10. `test_conflicting_specifications_detection`: Identification of conflicting display refresh rates (60Hz vs 120Hz) with source traceability.
11. `test_missing_warranty_and_policy`: Explicit flagging of missing warranty and ambiguous policy terms.
12. `test_evidence_traceability_and_duplicates`: Comprehensive synthesis linking every claim to its originating `evidence_id`.
