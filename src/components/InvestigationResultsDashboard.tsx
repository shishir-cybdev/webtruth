"use client";

import { motion } from "motion/react";
import {
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Hash,
  FileSearch,
  DollarSign,
  Scale,
  Info,
  ListChecks,
} from "lucide-react";
import type { InvestigationResponse } from "@/types/api";

function TrustTierBadge({ tier }: { tier: string }) {
  if (tier === "HIGH_TRANSPARENCY") {
    return (
      <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-green-500/15 text-green-400 border border-green-500/30">
        HIGH TRANSPARENCY
      </span>
    );
  }
  if (tier === "MODERATE_TRANSPARENCY") {
    return (
      <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
        MODERATE TRANSPARENCY
      </span>
    );
  }
  if (tier === "CAUTION_FLAGGED") {
    return (
      <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
        CAUTION FLAGGED
      </span>
    );
  }
  return (
    <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
      INSUFFICIENT DATA
    </span>
  );
}

export function InvestigationResultsDashboard({
  investigation,
}: {
  investigation: InvestigationResponse;
}) {
  const comp = investigation.comparison_result;
  const trust = investigation.trust_report;
  const assessment = trust?.trust_assessment;

  const productName =
    (comp?.product_identity?.product_name as string) ||
    (trust?.product_identity?.product_name as string) ||
    investigation.query;

  const prices = comp?.price_comparison?.price_points || [];
  const equalSpecs = comp?.spec_comparison?.equal_fields || [];
  const diffSpecs = comp?.spec_comparison?.different_fields || [];
  const unavailSpecs = comp?.spec_comparison?.unavailable_fields || [];
  const policies = comp?.policy_comparison?.policies || [];
  const conflicts = comp?.conflicts?.conflicts || [];
  const qualityRecords = trust?.evidence_quality_summary?.records || [];
  const freshnessItems = trust?.freshness_summary?.items || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="space-y-6 mt-8"
    >
      {/* Top Executive Summary Card */}
      <div className="glass rounded-2xl border border-cyan-500/25 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4 pb-4 border-b border-slate-800/80">
          <div className="flex items-start gap-3">
            <div className="w-11 h-11 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center shrink-0">
              <FileSearch className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-xl font-bold text-slate-100">{productName}</h2>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {investigation.id}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Category: <span className="text-slate-200">{investigation.category || "unspecified"}</span>
                {investigation.budget_inr ? (
                  <>
                    {" "}• Budget Cap: <span className="text-cyan-400 font-mono">₹{investigation.budget_inr.toLocaleString("en-IN")}</span>
                  </>
                ) : null}
                {" "}• Tool Calls Executed: <span className="text-violet-400 font-mono">{investigation.tool_logs_count}</span>
              </p>
            </div>
          </div>
          {assessment && <TrustTierBadge tier={assessment.overall_trust_tier} />}
        </div>

        {investigation.summary && (
          <p className="text-sm text-slate-300 leading-relaxed mb-4">{investigation.summary}</p>
        )}

        {/* Configuration Match Banner */}
        {comp && (
          <div
            className={`rounded-xl px-4 py-3 text-xs border flex items-start gap-2.5 ${
              comp.configuration_match
                ? "bg-green-500/10 border-green-500/25 text-green-300"
                : "bg-amber-500/10 border-amber-500/30 text-amber-300"
            }`}
          >
            {comp.configuration_match ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            )}
            <div>
              <span className="font-semibold">
                {comp.configuration_match
                  ? "Configuration Fingerprints Match:"
                  : "Configuration Mismatch Detected:"}
              </span>{" "}
              {comp.configuration_match
                ? "Observed sources describe the same hardware configuration."
                : comp.configuration_warnings?.join(" ") ||
                  "Sources may describe different RAM/Storage/Model variants. Do not equate prices."}
            </div>
          </div>
        )}

        {/* Warnings & Rejected Sources */}
        {((investigation.warnings && investigation.warnings.length > 0) ||
          (investigation.failures && investigation.failures.length > 0)) && (
          <div className="mt-4 rounded-xl bg-amber-500/10 border border-amber-500/25 p-4 space-y-1.5 text-xs">
            <div className="font-semibold text-amber-300 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              Source Validation &amp; Access Warnings
            </div>
            <ul className="space-y-1 text-amber-200/80 pl-5 list-disc">
              {(investigation.warnings || []).map((w, idx) => (
                <li key={`w-${idx}`}>{w}</li>
              ))}
              {(investigation.failures || []).map((f, idx) => (
                <li key={`f-${idx}`} className="text-red-300">{f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Observed Prices & Sources */}
      <div className="glass rounded-2xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-cyan-400" />
            <h3 className="text-base font-semibold text-slate-100">
              Observed Prices &amp; Captured Sources
            </h3>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            OBSERVED DATA ({prices.length} SOURCE{prices.length === 1 ? "" : "S"})
          </span>
        </div>

        {prices.length === 0 ? (
          <div className="text-sm text-slate-500 py-4 text-center border border-dashed border-slate-800 rounded-xl">
            No price observations were returned by Browser / Comparison MCP.
          </div>
        ) : (
          <div className="space-y-3">
            {prices.map((pt, idx) => {
              const qRec = qualityRecords.find((r) => r.evidence_id === pt.evidence_id);
              const fRec = freshnessItems.find((r) => r.evidence_id === pt.evidence_id || r.source_url === pt.source_url);
              return (
                <div
                  key={`${pt.source_url}-${idx}`}
                  className="rounded-xl bg-slate-900/60 border border-slate-800 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-200">{pt.source_domain}</span>
                      {pt.evidence_id && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20">
                          <Hash className="w-2.5 h-2.5" />
                          {pt.evidence_id}
                        </span>
                      )}
                      {qRec && (
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            qRec.integrity_status === "verified"
                              ? "bg-green-500/10 text-green-400 border-green-500/25"
                              : qRec.integrity_status === "tampered"
                              ? "bg-red-500/15 text-red-400 border-red-500/30"
                              : "bg-slate-800 text-slate-400 border-slate-700"
                          }`}
                        >
                          HASH: {qRec.integrity_status.toUpperCase()}
                        </span>
                      )}
                    </div>

                    <a
                      href={pt.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 break-all"
                    >
                      {pt.source_url}
                      <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>

                    <div className="flex items-center gap-3 text-[11px] text-slate-500 flex-wrap">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Captured: {pt.capture_timestamp || "Unknown"}
                      </span>
                      {fRec && (
                        <span className="font-mono text-slate-400">
                          Freshness: {fRec.classification.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="text-left sm:text-right shrink-0">
                    <div className="text-lg font-bold font-mono text-cyan-400">
                      {pt.raw_displayed_price || "Unavailable"}
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      Currency: {pt.currency || "Unknown"}
                      {pt.numeric_price !== null && pt.numeric_price !== undefined
                        ? ` • Numeric: ${pt.numeric_price.toLocaleString("en-IN")}`
                        : ""}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {comp?.price_comparison?.currency_mismatch_detected && (
          <div className="mt-3 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/25 rounded-lg p-3">
            Currency mismatch detected ({comp.price_comparison.currencies_found.join(", ")}). Numeric spread calculation was suppressed to prevent unauthorized currency conversion.
          </div>
        )}
      </div>

      {/* Trust Assessment Dimensions */}
      {assessment && (
        <div className="glass rounded-2xl border border-violet-500/25 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-violet-400" />
              <h3 className="text-base font-semibold text-slate-100">
                Explainable Trust Assessment
              </h3>
            </div>
            {trust?.integrity_status && (
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {trust.integrity_status}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-5">
            {[
              assessment.evidence_coverage,
              assessment.provenance_transparency,
              assessment.freshness_indicator,
              assessment.integrity_indicator,
              assessment.source_consistency,
            ].map((dim) => (
              <div
                key={dim.indicator_name}
                className="rounded-xl bg-slate-900/70 border border-slate-800 p-3.5 flex flex-col justify-between"
              >
                <div>
                  <div className="text-xs text-slate-400 mb-1">{dim.indicator_name}</div>
                  <div className="flex items-baseline justify-between mb-2">
                    <span className="text-lg font-bold font-mono text-slate-100">
                      {Math.round(dim.score * 100)}%
                    </span>
                    <span className="text-[10px] font-mono uppercase text-cyan-400">
                      {dim.rating}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-400 to-violet-400 rounded-full"
                      style={{ width: `${Math.round(dim.score * 100)}%` }}
                    />
                  </div>
                </div>
                <p className="text-[11px] text-slate-500 leading-snug">{dim.explanation}</p>
              </div>
            ))}
          </div>

          {/* Mandatory Transparency Disclaimer */}
          <div className="rounded-xl bg-slate-950/70 border border-slate-800 p-3.5 text-xs text-slate-400 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <span>{assessment.disclaimer}</span>
          </div>
        </div>
      )}

      {/* Specifications & Policies Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Specification Matrix */}
        <div className="glass rounded-2xl border border-slate-800 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Scale className="w-4 h-4 text-cyan-400" />
            <h3 className="text-base font-semibold text-slate-100">Specification Verification</h3>
          </div>

          {equalSpecs.length === 0 && diffSpecs.length === 0 && unavailSpecs.length === 0 ? (
            <p className="text-sm text-slate-500">No specification matrix data returned.</p>
          ) : (
            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {diffSpecs.map((sp) => (
                <div key={sp.field_name} className="rounded-lg bg-red-500/10 border border-red-500/25 p-3 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-red-300">{sp.field_name}</span>
                    <span className="font-mono text-[10px] text-red-400">CONTRADICTED / DIFFERS</span>
                  </div>
                  <div className="text-slate-400 space-y-0.5">
                    {Object.entries(sp.values_by_source).map(([src, val]) => (
                      <div key={src} className="truncate">
                        <span className="text-slate-500">{src}:</span> {val ?? "Unavailable"}
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {equalSpecs.map((sp) => (
                <div key={sp.field_name} className="rounded-lg bg-slate-900/60 border border-slate-800 p-3 text-xs flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-300">{sp.field_name}</span>
                  <span className="text-green-400 font-mono truncate max-w-[60%]">
                    {Object.values(sp.values_by_source)[0] ?? "Observed"}
                  </span>
                </div>
              ))}

              {unavailSpecs.map((sp) => (
                <div key={sp.field_name} className="rounded-lg bg-slate-900/40 border border-slate-800/60 p-3 text-xs flex items-center justify-between gap-2">
                  <span className="text-slate-400">{sp.field_name}</span>
                  <span className="text-amber-400/90 font-mono text-[10px]">UNAVAILABLE</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Policies & Conflicts */}
        <div className="glass rounded-2xl border border-slate-800 p-6 space-y-5">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <FileSearch className="w-4 h-4 text-violet-400" />
              <h3 className="text-base font-semibold text-slate-100">Warranty &amp; Return Policies</h3>
            </div>
            {policies.length === 0 ? (
              <p className="text-xs text-slate-500">No policy disclosures extracted.</p>
            ) : (
              <div className="space-y-2">
                {policies.map((pol, i) => (
                  <div key={`${pol.policy_type}-${i}`} className="rounded-lg bg-slate-900/60 border border-slate-800 p-3 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="uppercase font-mono text-[11px] text-slate-300">
                        {pol.policy_type} ({pol.source_domain})
                      </span>
                      {pol.is_missing ? (
                        <span className="text-[10px] font-mono text-amber-400">UNAVAILABLE</span>
                      ) : pol.is_ambiguous ? (
                        <span className="text-[10px] font-mono text-amber-300">AMBIGUOUS</span>
                      ) : (
                        <span className="text-[10px] font-mono text-cyan-400">OBSERVED</span>
                      )}
                    </div>
                    <p className="text-slate-400">
                      {pol.raw_terms || "No policy terms disclosed on source page."}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Source Conflicts */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-slate-100">
                Source Conflicts ({conflicts.length})
              </h3>
            </div>
            {conflicts.length === 0 ? (
              <p className="text-xs text-slate-500">No cross-source contradictions flagged.</p>
            ) : (
              <div className="space-y-2">
                {conflicts.map((c, idx) => (
                  <div key={idx} className="rounded-lg bg-red-500/10 border border-red-500/25 p-3 text-xs">
                    <div className="font-semibold text-red-300 mb-1">{c.field_name}</div>
                    <p className="text-slate-300">{c.conflict_description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Claims Audit & Missing Fields */}
      {trust && (
        <div className="glass rounded-2xl border border-slate-800 p-6 space-y-5">
          <div className="flex items-center gap-2">
            <ListChecks className="w-4 h-4 text-green-400" />
            <h3 className="text-base font-semibold text-slate-100">
              Claims Audit &amp; Verification Guidance
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-green-400 mb-2">
                <CheckCircle2 className="w-4 h-4" />
                Evidenced Claims ({trust.supported_claims.length})
              </div>
              {trust.supported_claims.length === 0 ? (
                <p className="text-xs text-slate-500">None recorded.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {trust.supported_claims.slice(0, 5).map((cl) => (
                    <li key={cl.claim_id} className="truncate" title={cl.claimed_value || ""}>
                      • {cl.claimed_value || cl.field}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 mb-2">
                <HelpCircle className="w-4 h-4" />
                Unsupported Claims ({trust.unsupported_claims.length})
              </div>
              {trust.unsupported_claims.length === 0 ? (
                <p className="text-xs text-slate-500">No unsupported claims detected.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {trust.unsupported_claims.slice(0, 5).map((cl) => (
                    <li key={cl.claim_id} className="truncate">
                      • {cl.field}: {cl.claimed_value}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-red-400 mb-2">
                <XCircle className="w-4 h-4" />
                Contradicted Claims ({trust.conflicting_claims.length})
              </div>
              {trust.conflicting_claims.length === 0 ? (
                <p className="text-xs text-slate-500">No contradicted claims detected.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {trust.conflicting_claims.slice(0, 5).map((cl) => (
                    <li key={cl.claim_id} className="truncate">
                      • {cl.field}: {cl.claimed_value}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Recommended User Verification Steps */}
          {trust.recommended_verification_steps.length > 0 && (
            <div className="pt-2">
              <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
                Recommended Consumer Verification Steps
              </h4>
              <div className="space-y-2">
                {trust.recommended_verification_steps.map((step) => (
                  <div
                    key={step.step_id}
                    className="rounded-xl bg-cyan-500/5 border border-cyan-500/20 p-3.5 text-xs flex items-start gap-3"
                  >
                    <span
                      className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase shrink-0 ${
                        step.priority === "critical"
                          ? "bg-red-500/20 text-red-300"
                          : "bg-cyan-500/20 text-cyan-300"
                      }`}
                    >
                      {step.priority}
                    </span>
                    <div>
                      <div className="font-semibold text-slate-200">{step.action}</div>
                      <div className="text-slate-400 mt-0.5">{step.rationale}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Related Variants (Explicitly separated from exact-match comparison) */}
      {investigation.related_variants && investigation.related_variants.length > 0 && (
        <div className="glass rounded-2xl border border-violet-500/20 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-base font-semibold text-slate-100">
              Related Model Variants ({investigation.related_variants.length})
            </h3>
            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/30">
              EXCLUDED FROM EXACT MATCH
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            These products are related variants (e.g., S/R/Pro editions) and were excluded from the exact-match price comparison.
          </p>
          <div className="space-y-2">
            {investigation.related_variants.map((rv, idx) => (
              <div key={idx} className="rounded-xl bg-slate-900/60 border border-slate-800 p-3.5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-semibold text-slate-200 truncate">{rv.product_name || rv.source_url}</div>
                  <div className="text-slate-400 mt-0.5">{rv.reason}</div>
                  <a href={rv.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 mt-1 break-all">
                    {rv.source_url} <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                </div>
                <div className="text-left sm:text-right shrink-0 font-mono text-violet-300">
                  {rv.raw_displayed_price || "Unavailable"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rejected Candidates Diagnostics */}
      {investigation.rejected_candidates && investigation.rejected_candidates.length > 0 && (
        <div className="glass rounded-2xl border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-200">
              Rejected Non-Matching Candidates ({investigation.rejected_candidates.length})
            </h3>
            <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/25">
              NOT STORED AS EVIDENCE
            </span>
          </div>
          <div className="space-y-2">
            {investigation.rejected_candidates.map((rc, idx) => (
              <div key={idx} className="rounded-lg bg-slate-950/60 border border-slate-800/80 p-3 text-xs">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-semibold text-slate-300 truncate">{rc.product_name || rc.source_url}</span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/25 shrink-0">
                    {rc.match_status}
                  </span>
                </div>
                <p className="text-slate-400">{rc.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
