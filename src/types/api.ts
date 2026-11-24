// Typed API contracts matching the FastAPI backend and MCP servers (Phases 2A–2F)

export type BackendInvestigationStatus = "pending" | "processing" | "completed" | "failed";
export type BackendStepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface InvestigationCreateRequest {
  query: string;
  category?: string | null;
  budget_inr?: number | null;
  notes?: string | null;
  mode?: "real" | "demo";
  target_urls?: string[] | null;
}

export interface PipelineStepInfo {
  step_id: string;
  label: string;
  mcp_server: string;
  status: BackendStepStatus;
  description: string;
  message?: string | null;
}

// Comparison MCP Output Structures
export interface PricePoint {
  source_url: string;
  source_domain: string;
  source_title?: string | null;
  capture_timestamp: string;
  raw_displayed_price?: string | null;
  currency?: string | null;
  numeric_price?: number | null;
  evidence_id?: string | null;
}

export interface PriceComparisonResult {
  total_sources: number;
  price_points: PricePoint[];
  lowest_price?: PricePoint | null;
  highest_price?: PricePoint | null;
  price_spread?: number | null;
  currency_mismatch_detected: boolean;
  currencies_found: string[];
  missing_price_sources: string[];
  comparison_notes: string[];
}

export interface SpecComparisonItem {
  field_name: string;
  status: "equal" | "different" | "unavailable";
  values_by_source: Record<string, string | null>;
  evidence_ids: string[];
  note?: string | null;
}

export interface SpecComparisonResult {
  equal_fields: SpecComparisonItem[];
  different_fields: SpecComparisonItem[];
  unavailable_fields: SpecComparisonItem[];
  total_fields_compared: number;
  configuration_match: boolean;
}

export interface PolicyItem {
  policy_type: string;
  source_url: string;
  source_domain: string;
  evidence_id?: string | null;
  raw_terms?: string | null;
  is_missing: boolean;
  is_ambiguous: boolean;
}

export interface PolicyComparisonResult {
  policies: PolicyItem[];
  missing_policies_count: number;
  summary: string;
}

export interface ProductConflictItem {
  field_name: string;
  conflict_description: string;
  claims: Array<{
    raw_value?: string;
    source_url?: string;
    evidence_id?: string;
  }>;
}

export interface ProductConflictResult {
  has_conflicts: boolean;
  conflicts_count: number;
  conflicts: ProductConflictItem[];
}

export interface ComprehensiveComparisonResult {
  product_identity: Record<string, unknown>;
  configuration_match: boolean;
  configuration_warnings: string[];
  price_comparison: PriceComparisonResult;
  spec_comparison: SpecComparisonResult;
  policy_comparison: PolicyComparisonResult;
  conflicts: ProductConflictResult;
  unknown_fields: string[];
  evidence_references: string[];
  generated_at_utc: string;
}

// Trust MCP Output Structures
export interface TrustComponentBreakdown {
  indicator_name: string;
  score: number;
  rating: string;
  metric_details: Record<string, unknown>;
  explanation: string;
}

export interface TrustAssessmentResult {
  overall_trust_tier: "HIGH_TRANSPARENCY" | "MODERATE_TRANSPARENCY" | "CAUTION_FLAGGED" | "INSUFFICIENT_DATA";
  evidence_coverage: TrustComponentBreakdown;
  provenance_transparency: TrustComponentBreakdown;
  freshness_indicator: TrustComponentBreakdown;
  integrity_indicator: TrustComponentBreakdown;
  source_consistency: TrustComponentBreakdown;
  key_confidence_factors: string[];
  key_risk_factors: string[];
  disclaimer: string;
}

export interface QualityIssue {
  issue_type: string;
  severity: "info" | "warning" | "critical";
  description: string;
}

export interface EvidenceQualityItem {
  evidence_id: string;
  source_url: string;
  source_domain: string;
  has_timestamp: boolean;
  has_traceable_url: boolean;
  has_extracted_data: boolean;
  claims_count: number;
  has_price: boolean;
  integrity_status: "verified" | "tampered" | "unverified_missing_hash";
  quality_rating: "high" | "medium" | "low";
  quality_score: number;
  issues: QualityIssue[];
}

export interface EvidenceQualityResult {
  total_records: number;
  high_quality_count: number;
  medium_quality_count: number;
  low_quality_count: number;
  tampered_records_count: number;
  records: EvidenceQualityItem[];
  overall_quality_assessment: string;
  evaluation_notes: string[];
}

export interface SourceFreshnessItem {
  evidence_id?: string | null;
  source_url: string;
  source_domain: string;
  capture_timestamp?: string | null;
  age_hours?: number | null;
  age_days?: number | null;
  classification: "fresh" | "acceptable" | "aging" | "stale" | "unknown_timestamp";
  explanation: string;
  is_stale: boolean;
}

export interface SourceFreshnessResult {
  total_evaluated: number;
  fresh_count: number;
  acceptable_count: number;
  aging_count: number;
  stale_count: number;
  unknown_count: number;
  items: SourceFreshnessItem[];
  oldest_record_age_days?: number | null;
  newest_record_age_days?: number | null;
  overall_freshness: string;
  evaluation_notes: string[];
}

export interface ClaimVerificationItem {
  claim_id: string;
  field: string;
  claimed_value?: string | null;
  status: "supported" | "unsupported" | "contradicted";
  cited_evidence_ids: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  missing_evidence_ids: string[];
  explanation: string;
}

export interface RecommendedVerificationStep {
  step_id: string;
  priority: "critical" | "recommended" | "optional";
  action: string;
  rationale: string;
  relevant_urls: string[];
}

export interface TrustReportResult {
  report_id: string;
  generated_at_utc: string;
  product_identity: Record<string, unknown>;
  trust_assessment: TrustAssessmentResult;
  evidence_quality_summary: EvidenceQualityResult;
  freshness_summary: SourceFreshnessResult;
  supported_claims: ClaimVerificationItem[];
  conflicting_claims: ClaimVerificationItem[];
  unsupported_claims: ClaimVerificationItem[];
  missing_fields: string[];
  stale_sources: SourceFreshnessItem[];
  integrity_status: "ALL_RECORDS_VERIFIED" | "TAMPERING_DETECTED" | "PARTIAL_UNVERIFIED";
  recommended_verification_steps: RecommendedVerificationStep[];
}

export interface InvestigationResponse {
  id: string;
  query: string;
  category?: string | null;
  budget_inr?: number | null;
  status: BackendInvestigationStatus;
  created_at: string;
  updated_at: string;
  is_placeholder: boolean;
  disclaimer: string;
  pipeline_steps: PipelineStepInfo[];
  summary?: string | null;
  evidence_ids: string[];
  comparison_result?: ComprehensiveComparisonResult | null;
  trust_report?: TrustReportResult | null;
  target_urls: string[];
  tool_logs_count: number;
  warnings?: string[];
  failures?: string[];
}

export interface InvestigationListResponse {
  total: number;
  items: InvestigationResponse[];
}

export interface ServerHealthInfo {
  server_name: string;
  module_name: string;
  status: "connected" | "disconnected" | "error";
  discovered_tools: string[];
  tool_count: number;
  latency_ms?: number | null;
  error?: string | null;
  checked_at_utc: string;
}

export interface MCPHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  total_tools_count: number;
  servers: Record<string, ServerHealthInfo>;
  checked_at_utc: string;
}

export interface BackendHealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  mcp_status: string;
}

export interface InvestigationSSEEvent {
  event_type: "initial_state" | "stage_started" | "stage_completed" | "log" | "completed" | "error";
  investigation_id: string;
  stage?: string;
  status: string;
  current_stage?: string;
  message?: string;
  timestamp_utc?: string;
  data?: Record<string, unknown> | null;
  stages?: Record<string, {
    stage: string;
    label: string;
    mcp_server?: string;
    status: BackendStepStatus;
    message?: string;
  }>;
}
