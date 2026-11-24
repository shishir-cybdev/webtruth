# WEBTRUTH - Trust MCP Server (Phase 2E)

The **WEBTRUTH Trust MCP Server** is a standalone, deterministic Model Context Protocol (MCP) server responsible for evaluating evidence quality, auditing source freshness, detecting unsupported or contradicted claims, evaluating cross-retailer consistency, calculating transparent trust indicators, and generating actionable verification reports for consumers.

It operates over standard input/output (`stdio`) using the official Python MCP SDK (`mcp.server.mcpserver.MCPServer`), maintaining full schema compatibility with Browser MCP (Phase 2B), Evidence MCP (Phase 2C), and Comparison MCP (Phase 2D).

---

## Core Principles & Scientific Guarantees

1. **SHA-256 Record Integrity ≠ Factual Truth**:
   - A valid SHA-256 hash mathematically proves that the database record was not altered or corrupted post-capture.
   - It does **not** prove that what the retailer wrote on their webpage is factually accurate or honest.
2. **Freshness ≠ Truth**:
   - Stale evidence indicates data age (e.g. promotional discounts or stock availability may have changed).
   - Old information is **never** claimed to be false; specifications often remain valid indefinitely after product launch.
3. **Transparent Indicators (No Black-Box AI Scores)**:
   - Does not fabricate arbitrary numerical trust scores or claim mathematical proof of truth.
   - Outputs objective, explainable indicators: Evidence Coverage, Provenance Transparency, Freshness Ratio, Cryptographic Integrity, and Source Consistency.
4. **Never Silently Resolve Disagreements**:
   - When retailers disagree (e.g., 60Hz vs 120Hz refresh rate), the conflict is surfaced with source citations and attributed evidence IDs.
5. **Distinguish Unsupported vs Contradicted**:
   - **Unsupported**: The claim lacks an evidence citation or cites nonexistent records.
   - **Contradicted**: Competing evidence explicitly disputes the claim with alternate values.
6. **Untrusted Input Safety**:
   - Webpage content and retailer claims are treated strictly as untrusted text strings. Never executed as code or instructions.
7. **No Paid APIs or External AI Dependencies**:
   - 100% deterministic Python algorithms running locally.

---

## Architecture & Directory Structure

```
backend/mcp_servers/trust/
├── __init__.py               # Package exports
├── __main__.py               # CLI entrypoint: python -m mcp_servers.trust
├── server.py                 # MCPServer instance with 6 registered @server.tool definitions
├── schemas.py                # Strongly typed Pydantic models for inputs and outputs
├── freshness.py              # Timezone-aware ISO 8601 parsing and freshness policy tiers
├── trust_service.py          # Deterministic quality, claims audit, consistency, and reporting engine
└── README.md                 # This documentation
```

---

## The Six Functional MCP Tools

### 1. `assess_evidence_quality`
Evaluates completeness, source traceability, timestamp availability, extraction quality, and cryptographic integrity across evidence records.
- **Inputs**: `evidence_records: List[Dict[str, Any]]`
- **Outputs**: `EvidenceQualityResult` containing:
  - `total_records`, `high_quality_count`, `medium_quality_count`, `low_quality_count`, `tampered_records_count`.
  - Itemized `records` with `quality_score`, `integrity_status` (`verified`, `tampered`, `unverified_missing_hash`), and specific `issues`.

### 2. `check_source_freshness`
Audits the elapsed age since evidence capture using configurable freshness policies.
- **Inputs**:
  - `evidence_records: List[Dict[str, Any]]`
  - `policy: Optional[Dict[str, Any]]` (configurable thresholds: default `<=24h` fresh, `<=7d` acceptable, `<=30d` aging, `>30d` stale)
- **Outputs**: `SourceFreshnessResult` containing:
  - `fresh_count`, `acceptable_count`, `aging_count`, `stale_count`, `unknown_count`.
  - `oldest_record_age_days`, `newest_record_age_days`.
  - Explanatory caveat explicitly noting that stale records indicate elapsed observation time, not falsity.

### 3. `detect_unsupported_claims`
Audits asserted product claims against available evidence records.
- **Inputs**:
  - `claims: List[Dict[str, Any]]` (with `claim_id`, `field`, `claimed_value`, `cited_evidence_ids`)
  - `evidence_records: List[Dict[str, Any]]`
  - `conflicts: Optional[List[Dict[str, Any]]]` (from comparison)
- **Outputs**: `UnsupportedClaimsResult` containing:
  - `supported_count`, `unsupported_count`, `contradicted_count`.
  - Itemized verification outcomes distinguishing unbacked assertions from actively disputed claims.

### 4. `evaluate_source_consistency`
Evaluates multi-source agreement across technical specifications and pricing fields.
- **Inputs**:
  - `products: Optional[List[Dict[str, Any]]]`
  - `spec_comparison: Optional[Dict[str, Any]]`
  - `price_comparison: Optional[Dict[str, Any]]`
  - `conflicts: Optional[Dict[str, Any]]`
- **Outputs**: `SourceConsistencyResult` containing:
  - `agreeing_fields_count`, `disagreeing_fields_count`, `single_source_fields_count`.
  - Per-field items categorized as `AGREEMENT`, `DISAGREEMENT`, `SINGLE_SOURCE`, or `UNKNOWN`.
  - `consistency_ratio` and overall consistency tier.

### 5. `calculate_trust_assessment`
Produces transparent, explainable indicators across 5 objective dimensions:
- **Inputs**: `evidence_records`, optional pre-computed quality, freshness, consistency, and claims results.
- **Outputs**: `TrustAssessmentResult` containing:
  - `overall_trust_tier` (`HIGH_TRANSPARENCY`, `MODERATE_TRANSPARENCY`, `CAUTION_FLAGGED`, `INSUFFICIENT_DATA`).
  - Breakdown components: Evidence Coverage, Provenance Transparency, Evidence Freshness, Cryptographic Record Integrity, and Cross-Source Consistency.
  - `key_confidence_factors`, `key_risk_factors`.
  - Mandatory consumer and scientific transparency disclaimer.

### 6. `generate_trust_report`
Produces a unified investigation synthesis report combining evidence quality, freshness, consistency, claims audits, and actionable consumer verification steps.
- **Inputs**: `evidence_records`, `comparison_data`, `claims`, `policy`.
- **Outputs**: `TrustReportResult` containing:
  - `report_id`, `product_identity`.
  - Core `trust_assessment`.
  - Filtered lists: `supported_claims`, `conflicting_claims`, `unsupported_claims`, `missing_fields`, `stale_sources`.
  - `integrity_status` (`ALL_RECORDS_VERIFIED`, `TAMPERING_DETECTED`, `PARTIAL_UNVERIFIED`).
  - `recommended_verification_steps`: Prioritized actionable advice (e.g. checking manufacturer PDF for disputed specs, verifying live checkout price).

---

## Running & Testing

### 1. Run the Trust MCP Server via stdio (Windows PowerShell)

```powershell
Set-Location "c:\Users\Admin\Desktop\webtruth\backend"
& "venv\Scripts\python.exe" -m mcp_servers.trust
```
The server will start listening for JSON-RPC 2.0 messages on standard input/output (`stdio`).

### 2. Run Pytest Test Suite

```powershell
# Run Trust MCP tests (14 tests)
& "venv\Scripts\python.exe" -m pytest tests/test_trust_mcp.py -v

# Run the complete WEBTRUTH test suite (52 tests across FastAPI, Browser, Evidence, Comparison, Trust)
& "venv\Scripts\python.exe" -m pytest tests -v
```

---

## Test Coverage Summary

The `tests/test_trust_mcp.py` suite covers all 12 required scenarios:
1. `test_trust_mcp_tool_discovery`: Verifies registration of all 6 MCP tools.
2. `test_trust_mcp_tool_e2e_invocation`: Asynchronous execution of all 6 tools through server endpoints.
3. `test_complete_evidence`: Verifies high quality rating (>=0.8) and zero issues for fully documented records.
4. `test_missing_evidence`: Flags absence of extracted claims/specs as a quality warning.
5. `test_missing_timestamps`: Flags missing timestamp and classifies freshness as `UNKNOWN_TIMESTAMP`.
6. `test_stale_evidence`: Classifies records >30 days as `STALE` with proper non-falsity caveats.
7. `test_conflicting_prices`: Detects price disagreement across retailers without silent merging.
8. `test_conflicting_specifications`: Detects conflicting hardware specs (e.g. RAM) and preserves competing values.
9. `test_unsupported_claims`: Differentiates supported, unsupported, and actively contradicted claims.
10. `test_valid_and_modified_evidence_hashes`: Validates SHA-256 match and detects post-capture tampering.
11. `test_multiple_sources_agreeing`: Confirms high consistency when retailers report identical specs.
12. `test_multiple_sources_disagreeing`: Surfaces discrepancies with competing retailer citations.
13. `test_insufficient_evidence`: Identifies single-source specs as unconfirmed by independent secondary sources.
14. `test_generate_trust_report_comprehensive`: End-to-end report generation with prioritized verification steps.
