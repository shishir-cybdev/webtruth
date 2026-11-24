import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp_servers.trust.freshness import (
    FreshnessClassification,
    FreshnessPolicy,
    evaluate_freshness,
)
from mcp_servers.trust.schemas import (
    ClaimItem,
    ClaimStatus,
    ClaimVerificationItem,
    ConsistencyStatus,
    EvidenceQualityItem,
    EvidenceQualityResult,
    FieldConsistencyItem,
    QualityIssue,
    RecommendedVerificationStep,
    SourceConsistencyResult,
    SourceFreshnessItem,
    SourceFreshnessResult,
    TrustAssessmentResult,
    TrustComponentBreakdown,
    TrustReportResult,
    UnsupportedClaimsResult,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.trust.service")


def clean_spec_token(val: Any) -> str:
    """Normalize specification string for invariant comparison (ignoring case, whitespace, dashes)."""
    if val is None:
        return ""
    return re.sub(r"[\s\-_]+", "", str(val)).lower()


def extract_domain(url: Optional[str]) -> str:
    """Extract domain hostname from URL safely."""
    if not url:
        return "unknown"
    if url.startswith("file://"):
        return "local_fixture"
    try:
        parsed = urlparse(url)
        return (parsed.hostname or "unknown").lower()
    except Exception:
        return "unknown"


def compute_canonical_evidence_hash(
    investigation_id: str,
    product_id: str,
    source_url: str,
    capture_timestamp: str,
    evidence_type: str,
    extracted_claims: List[str],
    raw_displayed_price: Optional[str] = None,
    currency: Optional[str] = None,
) -> str:
    """Deterministic SHA-256 calculation matching Evidence MCP schema."""
    normalized_claims = sorted(str(c).strip() for c in extracted_claims if str(c).strip())
    canonical_dict = {
        "capture_timestamp": str(capture_timestamp).strip(),
        "currency": str(currency).strip() if currency else None,
        "evidence_type": str(evidence_type).strip().lower(),
        "extracted_claims": normalized_claims,
        "investigation_id": str(investigation_id).strip(),
        "product_id": str(product_id).strip().lower(),
        "raw_displayed_price": str(raw_displayed_price).strip() if raw_displayed_price else None,
        "source_url": str(source_url).strip(),
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class TrustService:
    """Deterministic trust, evidence quality, freshness, and consistency evaluation service."""

    # -----------------------------------------------------------------------
    # Tool 1: assess_evidence_quality
    # -----------------------------------------------------------------------
    def assess_evidence_quality(
        self,
        evidence_records: List[Dict[str, Any]],
    ) -> EvidenceQualityResult:
        """Evaluate completeness, traceability, timestamp, and cryptographic integrity of records."""
        items: List[EvidenceQualityItem] = []
        high_count = 0
        med_count = 0
        low_count = 0
        tampered_count = 0
        evaluation_notes: List[str] = []

        if not evidence_records:
            return EvidenceQualityResult(
                total_records=0,
                high_quality_count=0,
                medium_quality_count=0,
                low_quality_count=0,
                tampered_records_count=0,
                records=[],
                overall_quality_assessment="No evidence records provided for evaluation.",
                evaluation_notes=["No evidence records to assess."],
            )

        for rec in evidence_records:
            evi_id = str(rec.get("evidence_id") or "evi_unassigned")
            url = str(rec.get("source_url") or "")
            domain = rec.get("source_domain") or extract_domain(url)
            ts = rec.get("capture_timestamp")
            claims = rec.get("extracted_claims") or []
            if isinstance(claims, str):
                claims = [claims]
            price_raw = rec.get("raw_displayed_price")
            price_num = rec.get("numeric_price")
            stored_hash = rec.get("evidence_hash")

            issues: List[QualityIssue] = []

            # 1. Traceability
            has_traceable_url = bool(url and (url.startswith("http://") or url.startswith("https://") or url.startswith("file://")))
            if not has_traceable_url:
                issues.append(
                    QualityIssue(
                        issue_type="missing_source_url",
                        severity="critical",
                        description="Source URL is missing or does not have a valid protocol scheme.",
                    )
                )

            # 2. Timestamp availability
            has_timestamp = bool(ts and str(ts).strip())
            if not has_timestamp:
                issues.append(
                    QualityIssue(
                        issue_type="missing_timestamp",
                        severity="critical",
                        description="Capture timestamp is missing. Evidence age cannot be audited.",
                    )
                )

            # 3. Completeness of extracted claims and price
            has_price = bool(price_raw is not None or price_num is not None)
            has_extracted_data = bool(claims) or has_price or bool(rec.get("specifications"))
            if not has_extracted_data:
                issues.append(
                    QualityIssue(
                        issue_type="no_extracted_claims",
                        severity="warning",
                        description="Record contains no extracted claims, specifications, or pricing quotes.",
                    )
                )

            # 4. Integrity check (SHA-256)
            if stored_hash:
                try:
                    recomputed = compute_canonical_evidence_hash(
                        investigation_id=str(rec.get("investigation_id") or ""),
                        product_id=str(rec.get("product_id") or ""),
                        source_url=url,
                        capture_timestamp=str(ts or ""),
                        evidence_type=str(rec.get("evidence_type") or "retailer_price"),
                        extracted_claims=claims,
                        raw_displayed_price=str(price_raw) if price_raw else None,
                        currency=str(rec.get("currency")) if rec.get("currency") else None,
                    )
                    if recomputed == str(stored_hash).strip():
                        integrity_status = "verified"
                    else:
                        integrity_status = "tampered"
                        tampered_count += 1
                        issues.append(
                            QualityIssue(
                                issue_type="tampered_hash",
                                severity="critical",
                                description=(
                                    "Cryptographic SHA-256 hash does not match canonical contents. "
                                    "Database record has been modified or corrupted post-capture."
                                ),
                            )
                        )
                except Exception as ex:
                    integrity_status = "tampered"
                    tampered_count += 1
                    issues.append(
                        QualityIssue(
                            issue_type="hash_computation_error",
                            severity="critical",
                            description=f"Error recalculating hash: {ex}",
                        )
                    )
            else:
                integrity_status = "unverified_missing_hash"
                issues.append(
                    QualityIssue(
                        issue_type="missing_hash",
                        severity="info",
                        description="Evidence record lacks a pre-computed SHA-256 cryptographic hash.",
                    )
                )

            # Score calculation
            score = 0.0
            if has_traceable_url:
                score += 0.25
            if has_timestamp:
                score += 0.25
            if has_extracted_data:
                score += 0.25
            if integrity_status == "verified":
                score += 0.25
            elif integrity_status == "unverified_missing_hash":
                score += 0.10
            elif integrity_status == "tampered":
                # Severe penalty for tampered records
                score = min(score, 0.2)

            score = round(max(0.0, min(1.0, score)), 2)

            if score >= 0.8 and integrity_status != "tampered":
                quality_rating = "high"
                high_count += 1
            elif score >= 0.5 and integrity_status != "tampered":
                quality_rating = "medium"
                med_count += 1
            else:
                quality_rating = "low"
                low_count += 1

            items.append(
                EvidenceQualityItem(
                    evidence_id=evi_id,
                    source_url=url,
                    source_domain=domain,
                    has_timestamp=has_timestamp,
                    has_traceable_url=has_traceable_url,
                    has_extracted_data=has_extracted_data,
                    claims_count=len(claims),
                    has_price=has_price,
                    integrity_status=integrity_status,
                    quality_rating=quality_rating,
                    quality_score=score,
                    issues=issues,
                )
            )

        if tampered_count > 0:
            overall = f"WARNING: {tampered_count} evidence record(s) failed cryptographic integrity verification."
            evaluation_notes.append("Cryptographic hash mismatch indicates post-capture modification or corruption.")
        elif low_count > len(items) // 2:
            overall = "POOR: Significant completeness or traceability gaps across evidence records."
            evaluation_notes.append("High incidence of missing timestamps, missing URLs, or empty claim extractions.")
        elif high_count == len(items):
            overall = "HIGH: All records demonstrate complete traceability, timestamps, and verifiable integrity."
            evaluation_notes.append("All evidence records have verifiable provenance and uncorrupted payloads.")
        else:
            overall = "MODERATE: Most records provide usable evidence with acceptable documentation."
            evaluation_notes.append("Minor documentation gaps exist (e.g. unhashed or single-quote extractions).")

        return EvidenceQualityResult(
            total_records=len(items),
            high_quality_count=high_count,
            medium_quality_count=med_count,
            low_quality_count=low_count,
            tampered_records_count=tampered_count,
            records=items,
            overall_quality_assessment=overall,
            evaluation_notes=evaluation_notes,
        )

    # -----------------------------------------------------------------------
    # Tool 2: check_source_freshness
    # -----------------------------------------------------------------------
    def check_source_freshness(
        self,
        evidence_records: List[Dict[str, Any]],
        policy: Optional[FreshnessPolicy] = None,
        evaluated_at: Optional[datetime] = None,
    ) -> SourceFreshnessResult:
        """Evaluate evidence recency against configurable thresholds without claiming old data is false."""
        if policy is None:
            policy = FreshnessPolicy()

        items: List[SourceFreshnessItem] = []
        fresh_count = 0
        acceptable_count = 0
        aging_count = 0
        stale_count = 0
        unknown_count = 0
        ages_days: List[float] = []

        for rec in evidence_records:
            evi_id = rec.get("evidence_id")
            url = str(rec.get("source_url") or "unknown")
            domain = rec.get("source_domain") or extract_domain(url)
            ts = rec.get("capture_timestamp")

            classification, age_sec, age_hours, age_days, note = evaluate_freshness(
                capture_timestamp=ts,
                policy=policy,
                evaluated_at=evaluated_at,
            )

            is_stale = classification == FreshnessClassification.STALE

            if classification == FreshnessClassification.FRESH:
                fresh_count += 1
            elif classification == FreshnessClassification.ACCEPTABLE:
                acceptable_count += 1
            elif classification == FreshnessClassification.AGING:
                aging_count += 1
            elif classification == FreshnessClassification.STALE:
                stale_count += 1
            else:
                unknown_count += 1

            if age_days is not None:
                ages_days.append(age_days)

            items.append(
                SourceFreshnessItem(
                    evidence_id=evi_id,
                    source_url=url,
                    source_domain=domain,
                    capture_timestamp=ts,
                    age_hours=round(age_hours, 2) if age_hours is not None else None,
                    age_days=round(age_days, 2) if age_days is not None else None,
                    classification=classification,
                    explanation=note,
                    is_stale=is_stale,
                )
            )

        oldest = max(ages_days) if ages_days else None
        newest = min(ages_days) if ages_days else None

        if stale_count > 0:
            overall = FreshnessClassification.STALE
        elif aging_count > 0:
            overall = FreshnessClassification.AGING
        elif acceptable_count > 0:
            overall = FreshnessClassification.ACCEPTABLE
        elif fresh_count > 0:
            overall = FreshnessClassification.FRESH
        else:
            overall = FreshnessClassification.UNKNOWN_TIMESTAMP

        eval_notes = [
            "Freshness measures elapsed time since observation. Stale evidence indicates data age, not that claims are false.",
            "Prices and promotions change frequently; hardware specifications are generally fixed after product release.",
        ]
        if stale_count > 0:
            eval_notes.append(f"{stale_count} source(s) are older than {policy.aging_hours / 24:.0f} days; re-verification is advised.")

        return SourceFreshnessResult(
            total_evaluated=len(items),
            fresh_count=fresh_count,
            acceptable_count=acceptable_count,
            aging_count=aging_count,
            stale_count=stale_count,
            unknown_count=unknown_count,
            items=items,
            oldest_record_age_days=round(oldest, 2) if oldest is not None else None,
            newest_record_age_days=round(newest, 2) if newest is not None else None,
            overall_freshness=overall,
            freshness_policy_applied=policy,
            evaluation_notes=eval_notes,
        )

    # -----------------------------------------------------------------------
    # Tool 3: detect_unsupported_claims
    # -----------------------------------------------------------------------
    def detect_unsupported_claims(
        self,
        claims: List[Dict[str, Any]],
        evidence_records: List[Dict[str, Any]],
        conflicts: Optional[List[Dict[str, Any]]] = None,
    ) -> UnsupportedClaimsResult:
        """Audit asserted claims, distinguishing supported, unsupported, and contradicted assertions."""
        evidence_by_id: Dict[str, Dict[str, Any]] = {}
        for rec in evidence_records:
            eid = rec.get("evidence_id")
            if eid:
                evidence_by_id[eid] = rec

        # Build conflict fields map if available
        conflict_fields: Dict[str, List[Dict[str, Any]]] = {}
        if conflicts:
            for conf in conflicts:
                fname = str(conf.get("field_name") or "").strip().lower()
                conflict_fields[fname] = conf.get("claims") or []

        verified_claims: List[ClaimVerificationItem] = []
        supported_count = 0
        unsupported_count = 0
        contradicted_count = 0

        for c in claims:
            cid = str(c.get("claim_id") or "clm_unassigned")
            field = str(c.get("field") or "unknown_field").strip()
            claimed_val = c.get("claimed_value")
            claimed_str = str(claimed_val).strip() if claimed_val is not None else ""
            cited_ids = c.get("cited_evidence_ids") or []
            if isinstance(cited_ids, str):
                cited_ids = [cited_ids]

            supporting_ids: List[str] = []
            contradicting_ids: List[str] = []
            missing_ids: List[str] = []

            for eid in cited_ids:
                if eid in evidence_by_id:
                    supporting_ids.append(eid)
                else:
                    missing_ids.append(eid)

            field_lower = field.lower()
            is_contradicted = False
            contradiction_note = ""

            # Check if comparison conflicts exist for this field
            claimed_tok = clean_spec_token(claimed_str)
            if field_lower in conflict_fields:
                comp_claims = conflict_fields[field_lower]
                # If opposing claims exist with distinct values
                opposing = [cc for cc in comp_claims if clean_spec_token(cc.get("raw_value")) != claimed_tok]
                if opposing:
                    is_contradicted = True
                    for op in opposing:
                        op_eid = op.get("evidence_id")
                        if op_eid and op_eid not in contradicting_ids:
                            contradicting_ids.append(op_eid)
                    contradiction_note = f"Disputed by competing source(s) asserting alternate value '{opposing[0].get('raw_value')}'."

            # Check if other evidence records contradict this claim
            for eid, rec in evidence_by_id.items():
                if eid in supporting_ids:
                    continue
                # If evidence record has explicit contradictory spec or price
                rec_specs = rec.get("specifications") or {}
                if isinstance(rec_specs, dict):
                    for k, v in rec_specs.items():
                        if k.strip().lower() == field_lower and clean_spec_token(v) != claimed_tok:
                            is_contradicted = True
                            if eid not in contradicting_ids:
                                contradicting_ids.append(eid)
                            contradiction_note = f"Disputed by evidence {eid} asserting '{v}' for {field}."

            # Determine final status
            if is_contradicted:
                status = ClaimStatus.CONTRADICTED
                contradicted_count += 1
                expl = f"Contradicted claim: {contradiction_note}"
            elif not cited_ids:
                status = ClaimStatus.UNSUPPORTED
                unsupported_count += 1
                expl = "Unsupported claim: No evidence ID was cited for this assertion."
            elif missing_ids and not supporting_ids:
                status = ClaimStatus.UNSUPPORTED
                unsupported_count += 1
                expl = f"Unsupported claim: Cited evidence ID(s) {missing_ids} not found in evidence store."
            else:
                # Evidence was found. Verify if text/specs corroborate claim
                corroborated = False
                for sid in supporting_ids:
                    srec = evidence_by_id[sid]
                    claims_text = " ".join(srec.get("extracted_claims") or [])
                    raw_p = str(srec.get("raw_displayed_price") or "")
                    specs_text = " ".join(f"{k}:{v}" for k, v in (srec.get("specifications") or {}).items())
                    combined = f"{claims_text} {raw_p} {specs_text}".lower()
                    if claimed_str.lower() in combined or not claimed_str or claimed_tok in clean_spec_token(combined):
                        corroborated = True
                        break

                if corroborated or not claimed_str:
                    status = ClaimStatus.SUPPORTED
                    supported_count += 1
                    expl = f"Supported by verified evidence record(s): {supporting_ids}."
                else:
                    status = ClaimStatus.UNSUPPORTED
                    unsupported_count += 1
                    expl = (
                        f"Unsupported claim: Cited evidence record(s) {supporting_ids} exist, "
                        f"but do not contain verbatim or semantic support for '{claimed_str}'."
                    )

            verified_claims.append(
                ClaimVerificationItem(
                    claim_id=cid,
                    field=field,
                    claimed_value=claimed_val,
                    status=status,
                    cited_evidence_ids=cited_ids,
                    supporting_evidence_ids=supporting_ids,
                    contradicting_evidence_ids=contradicting_ids,
                    missing_evidence_ids=missing_ids,
                    explanation=expl,
                )
            )

        summary = (
            f"Evaluated {len(claims)} claim(s): {supported_count} supported, "
            f"{unsupported_count} unsupported, {contradicted_count} contradicted."
        )

        return UnsupportedClaimsResult(
            total_claims=len(claims),
            supported_count=supported_count,
            unsupported_count=unsupported_count,
            contradicted_count=contradicted_count,
            claims=verified_claims,
            has_unsupported_claims=unsupported_count > 0,
            has_contradictions=contradicted_count > 0,
            summary=summary,
        )

    # -----------------------------------------------------------------------
    # Tool 4: evaluate_source_consistency
    # -----------------------------------------------------------------------
    def evaluate_source_consistency(
        self,
        products: Optional[List[Dict[str, Any]]] = None,
        spec_comparison: Optional[Dict[str, Any]] = None,
        price_comparison: Optional[Dict[str, Any]] = None,
        conflicts: Optional[Dict[str, Any]] = None,
    ) -> SourceConsistencyResult:
        """Evaluate agreement, disagreement, and single-source status across fields."""
        field_claims: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Ingest from product list if provided
        if products:
            for p in products:
                url = p.get("source_url") or "unknown"
                eid = p.get("source_evidence_id") or p.get("evidence_id")
                domain = extract_domain(url)

                # Standard fields
                for fname in ["brand", "model", "model_number", "cpu", "ram", "storage", "gpu", "screen_size"]:
                    fval = p.get(fname)
                    val_str = None
                    if isinstance(fval, dict):
                        val_str = fval.get("normalized_value") or fval.get("raw_value")
                    elif fval:
                        val_str = str(fval)

                    if val_str:
                        field_claims.setdefault(fname, []).append({
                            "source_url": url,
                            "source_domain": domain,
                            "evidence_id": eid,
                            "raw_value": val_str,
                        })

                # Additional specs
                specs = p.get("specifications") or p.get("other_specs") or {}
                if isinstance(specs, dict):
                    for sk, sv in specs.items():
                        sval_str = sv.get("normalized_value") or sv.get("raw_value") if isinstance(sv, dict) else str(sv)
                        if sval_str:
                            field_claims.setdefault(sk, []).append({
                                "source_url": url,
                                "source_domain": domain,
                                "evidence_id": eid,
                                "raw_value": sval_str,
                            })

                # Price if present on product
                if p.get("raw_displayed_price") or p.get("numeric_price"):
                    pval = p.get("raw_displayed_price") or str(p.get("numeric_price"))
                    field_claims.setdefault("price", []).append({
                        "source_url": url,
                        "source_domain": domain,
                        "evidence_id": eid,
                        "raw_value": pval,
                    })

        # 2. Ingest from spec_comparison if provided
        if spec_comparison:
            for item in spec_comparison.get("equal_fields", []):
                fname = item.get("field_name")
                for src, val in item.get("values_by_source", {}).items():
                    field_claims.setdefault(fname, []).append({
                        "source_url": src,
                        "source_domain": extract_domain(src),
                        "evidence_id": None,
                        "raw_value": str(val),
                    })
            for item in spec_comparison.get("different_fields", []):
                fname = item.get("field_name")
                for src, val in item.get("values_by_source", {}).items():
                    field_claims.setdefault(fname, []).append({
                        "source_url": src,
                        "source_domain": extract_domain(src),
                        "evidence_id": None,
                        "raw_value": str(val),
                    })

        # 3. Ingest from price_comparison if provided
        if price_comparison:
            pts = price_comparison.get("price_points") or []
            for pt in pts:
                field_claims.setdefault("price", []).append({
                    "source_url": pt.get("source_url") or "unknown",
                    "source_domain": pt.get("source_domain") or extract_domain(pt.get("source_url")),
                    "evidence_id": pt.get("evidence_id"),
                    "raw_value": pt.get("raw_displayed_price") or str(pt.get("numeric_price")),
                })

        # 4. Ingest from conflicts if provided
        if conflicts:
            confl_items = conflicts.get("conflicts", []) if isinstance(conflicts, dict) else conflicts
            if isinstance(confl_items, list):
                for item in confl_items:
                    fname = item.get("field_name")
                    if fname:
                        for c in item.get("claims", []):
                            field_claims.setdefault(fname, []).append({
                                "source_url": c.get("source_url") or "unknown",
                                "source_domain": extract_domain(c.get("source_url")),
                                "evidence_id": c.get("evidence_id"),
                                "raw_value": str(c.get("raw_value") or ""),
                            })

        # Evaluate each field
        items: List[FieldConsistencyItem] = []
        agree_count = 0
        disagree_count = 0
        single_count = 0

        for fname, claims_list in field_claims.items():
            total_srcs = len(claims_list)
            if total_srcs == 0:
                items.append(
                    FieldConsistencyItem(
                        field_name=fname,
                        status=ConsistencyStatus.UNKNOWN,
                        agreement_count=0,
                        total_sources=0,
                        distinct_claims=[],
                        explanation=f"No source reports data for '{fname}'.",
                    )
                )
                continue

            if total_srcs == 1:
                single_count += 1
                items.append(
                    FieldConsistencyItem(
                        field_name=fname,
                        status=ConsistencyStatus.SINGLE_SOURCE,
                        agreement_count=1,
                        total_sources=1,
                        distinct_claims=claims_list,
                        explanation=f"Attribute '{fname}' is reported by only 1 source. Unconfirmed by independent secondary sources.",
                    )
                )
                continue

            # Group distinct values (case-insensitive normalized token matching)
            val_groups: Dict[str, List[Dict[str, Any]]] = {}
            for c in claims_list:
                v_clean = clean_spec_token(c.get("raw_value"))
                val_groups.setdefault(v_clean, []).append(c)

            if len(val_groups) == 1:
                agree_count += 1
                items.append(
                    FieldConsistencyItem(
                        field_name=fname,
                        status=ConsistencyStatus.AGREEMENT,
                        agreement_count=total_srcs,
                        total_sources=total_srcs,
                        distinct_claims=claims_list,
                        explanation=f"Consistent agreement: All {total_srcs} reporting sources confirm the exact same value for '{fname}'.",
                    )
                )
            else:
                disagree_count += 1
                # Format explanation with distinct values
                group_summaries = [f"'{k}' ({len(v)} sources)" for k, v in val_groups.items()]
                items.append(
                    FieldConsistencyItem(
                        field_name=fname,
                        status=ConsistencyStatus.DISAGREEMENT,
                        agreement_count=max(len(v) for v in val_groups.values()),
                        total_sources=total_srcs,
                        distinct_claims=claims_list,
                        explanation=f"Discrepancy detected across sources: competing values {', '.join(group_summaries)}.",
                    )
                )

        multi_src_fields = agree_count + disagree_count
        consistency_ratio = round(agree_count / multi_src_fields, 2) if multi_src_fields > 0 else (1.0 if single_count > 0 else 0.0)

        if multi_src_fields == 0:
            overall = "mostly_single_source" if single_count > 0 else "insufficient_evidence"
        elif disagree_count == 0:
            overall = "high_agreement"
        elif agree_count >= disagree_count:
            overall = "partial_disagreements"
        else:
            overall = "high_disagreement"

        return SourceConsistencyResult(
            total_fields_evaluated=len(items),
            agreeing_fields_count=agree_count,
            disagreeing_fields_count=disagree_count,
            single_source_fields_count=single_count,
            fields=items,
            overall_consistency=overall,
            consistency_ratio=consistency_ratio,
        )

    # -----------------------------------------------------------------------
    # Tool 5: calculate_trust_assessment
    # -----------------------------------------------------------------------
    def calculate_trust_assessment(
        self,
        evidence_records: List[Dict[str, Any]],
        quality_result: Optional[EvidenceQualityResult] = None,
        freshness_result: Optional[SourceFreshnessResult] = None,
        consistency_result: Optional[SourceConsistencyResult] = None,
        claims_result: Optional[UnsupportedClaimsResult] = None,
    ) -> TrustAssessmentResult:
        """Produce transparent, explainable indicators for coverage, provenance, freshness, integrity, and consistency."""
        # 1. Quality & Provenance
        if quality_result is None:
            quality_result = self.assess_evidence_quality(evidence_records)

        total_recs = quality_result.total_records
        tampered_count = quality_result.tampered_records_count

        # Provenance: proportion with valid traceable URLs
        traceable_recs = sum(1 for r in quality_result.records if r.has_traceable_url)
        prov_score = round(traceable_recs / total_recs, 2) if total_recs > 0 else 0.0
        prov_rating = "high" if prov_score >= 0.8 else ("moderate" if prov_score >= 0.5 else "low")

        # Integrity: proportion of verified SHA-256 hashes
        verified_recs = sum(1 for r in quality_result.records if r.integrity_status == "verified")
        if tampered_count > 0:
            integ_score = 0.0
            integ_rating = "critical_failure"
            integ_expl = f"CRITICAL: {tampered_count} record(s) failed cryptographic integrity verification. Post-capture database tampering detected."
        elif total_recs == 0:
            integ_score = 0.0
            integ_rating = "insufficient_data"
            integ_expl = "No records to verify integrity."
        else:
            integ_score = round(verified_recs / total_recs, 2)
            integ_rating = "high" if integ_score >= 0.8 else ("moderate" if integ_score > 0 else "unverified")
            integ_expl = (
                f"{verified_recs} of {total_recs} records cryptographically verified with SHA-256 hashes. "
                "Confirms record immutability since capture."
            )

        # 2. Freshness
        if freshness_result is None:
            freshness_result = self.check_source_freshness(evidence_records)

        fresh_acc = freshness_result.fresh_count + freshness_result.acceptable_count
        fresh_score = round(fresh_acc / total_recs, 2) if total_recs > 0 else 0.0
        fresh_rating = "high" if fresh_score >= 0.8 else ("moderate" if fresh_score >= 0.4 else "low")
        fresh_expl = (
            f"{fresh_acc} of {total_recs} evidence records were captured recently (<= 7 days). "
            f"Stale records: {freshness_result.stale_count}."
        )

        # 3. Consistency
        if consistency_result is None:
            consistency_result = self.evaluate_source_consistency()

        cons_score = consistency_result.consistency_ratio
        cons_rating = "high" if cons_score >= 0.8 else ("moderate" if cons_score >= 0.5 else "low")
        cons_expl = (
            f"Cross-retailer agreement ratio: {cons_score * 100:.0f}%. "
            f"{consistency_result.agreeing_fields_count} agreeing field(s), "
            f"{consistency_result.disagreeing_fields_count} conflicting field(s)."
        )

        # 4. Evidence Coverage
        # Check presence of primary attributes across records
        all_specs_found: set[str] = set()
        has_any_price = False
        for rec in evidence_records:
            if rec.get("raw_displayed_price") or rec.get("numeric_price"):
                has_any_price = True
            for k in (rec.get("specifications") or {}).keys():
                all_specs_found.add(k.lower())
            for c in (rec.get("extracted_claims") or []):
                all_specs_found.add("claims")

        core_expected = ["product_name", "price", "brand", "model", "ram", "storage", "warranty"]
        found_expected = 0
        if any(rec.get("product_id") for rec in evidence_records):
            found_expected += 1
        if has_any_price:
            found_expected += 1
        for expected in ["brand", "model", "ram", "storage", "warranty"]:
            if any(expected in s for s in all_specs_found):
                found_expected += 1

        coverage_score = round(found_expected / len(core_expected), 2)
        coverage_rating = "high" if coverage_score >= 0.75 else ("moderate" if coverage_score >= 0.4 else "low")
        coverage_expl = f"Covered {found_expected} of {len(core_expected)} essential product decision attributes."

        # Key factors
        confidence_factors: List[str] = []
        risk_factors: List[str] = []

        if integ_score == 1.0 and total_recs > 0:
            confidence_factors.append("All evidence records passed cryptographic SHA-256 integrity verification.")
        if prov_score >= 0.8:
            confidence_factors.append("Strong provenance: Sources have fully traceable URLs and distinct domains.")
        if cons_score >= 0.8 and consistency_result.total_fields_evaluated > 0:
            confidence_factors.append("High multi-source consistency: Retailers agree on technical specifications.")

        if tampered_count > 0:
            risk_factors.append(f"CRITICAL: {tampered_count} record(s) failed hash verification (tampering detected).")
        if consistency_result.disagreeing_fields_count > 0:
            risk_factors.append(f"Contradiction alert: {consistency_result.disagreeing_fields_count} specification or pricing dispute(s) across sources.")
        if freshness_result.stale_count > 0:
            risk_factors.append(f"Aging data: {freshness_result.stale_count} source(s) are over 30 days old; verify live pricing.")
        if claims_result and claims_result.unsupported_count > 0:
            risk_factors.append(f"Unsupported assertions: {claims_result.unsupported_count} claim(s) lack supporting evidence records.")

        # Overall Trust Tier
        if tampered_count > 0:
            overall_tier = "CAUTION_FLAGGED"
        elif total_recs < 2 or coverage_score < 0.35:
            overall_tier = "INSUFFICIENT_DATA"
        elif consistency_result.disagreeing_fields_count > 2 or (claims_result and claims_result.contradicted_count > 0):
            overall_tier = "CAUTION_FLAGGED"
        elif (prov_score + fresh_score + cons_score + coverage_score + integ_score) / 5.0 >= 0.70:
            overall_tier = "HIGH_TRANSPARENCY"
        else:
            overall_tier = "MODERATE_TRANSPARENCY"

        return TrustAssessmentResult(
            overall_trust_tier=overall_tier,
            evidence_coverage=TrustComponentBreakdown(
                indicator_name="Evidence Coverage",
                score=coverage_score,
                rating=coverage_rating,
                metric_details={"found_attributes": found_expected, "total_core": len(core_expected)},
                explanation=coverage_expl,
            ),
            provenance_transparency=TrustComponentBreakdown(
                indicator_name="Provenance Transparency",
                score=prov_score,
                rating=prov_rating,
                metric_details={"traceable_records": traceable_recs, "total_records": total_recs},
                explanation=f"{traceable_recs} of {total_recs} records trace directly to verifiable source URLs.",
            ),
            freshness_indicator=TrustComponentBreakdown(
                indicator_name="Evidence Freshness",
                score=fresh_score,
                rating=fresh_rating,
                metric_details={
                    "fresh_acceptable": fresh_acc,
                    "stale_count": freshness_result.stale_count,
                    "total_records": total_recs,
                },
                explanation=fresh_expl,
            ),
            integrity_indicator=TrustComponentBreakdown(
                indicator_name="Cryptographic Record Integrity",
                score=integ_score,
                rating=integ_rating,
                metric_details={"verified_count": verified_recs, "tampered_count": tampered_count, "total": total_recs},
                explanation=integ_expl,
            ),
            source_consistency=TrustComponentBreakdown(
                indicator_name="Cross-Source Consistency",
                score=cons_score,
                rating=cons_rating,
                metric_details={
                    "agreeing_fields": consistency_result.agreeing_fields_count,
                    "disagreeing_fields": consistency_result.disagreeing_fields_count,
                    "single_source": consistency_result.single_source_fields_count,
                },
                explanation=cons_expl,
            ),
            key_confidence_factors=confidence_factors,
            key_risk_factors=risk_factors,
        )

    # -----------------------------------------------------------------------
    # Tool 6: generate_trust_report
    # -----------------------------------------------------------------------
    def generate_trust_report(
        self,
        evidence_records: List[Dict[str, Any]],
        comparison_data: Optional[Dict[str, Any]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
        policy: Optional[FreshnessPolicy] = None,
    ) -> TrustReportResult:
        """Combine evidence, freshness, consistency, and comparison into a unified trust report."""
        import uuid
        report_id = f"tr_{uuid.uuid4().hex[:12]}"

        # 1. Quality
        quality_res = self.assess_evidence_quality(evidence_records)

        # 2. Freshness
        freshness_res = self.check_source_freshness(evidence_records, policy=policy)

        # 3. Consistency
        comparison_dict = comparison_data or {}
        products = comparison_dict.get("products")
        spec_comp = comparison_dict.get("spec_comparison")
        price_comp = comparison_dict.get("price_comparison")
        conflicts = comparison_dict.get("conflicts", {})

        consistency_res = self.evaluate_source_consistency(
            products=products,
            spec_comparison=spec_comp,
            price_comparison=price_comp,
            conflicts=conflicts,
        )

        # 4. Claims audit
        input_claims = claims or []
        # If no explicit claims were passed, construct testable claims from comparison
        if not input_claims and products:
            for p in products:
                eid = p.get("source_evidence_id") or p.get("evidence_id")
                if p.get("ram"):
                    input_claims.append({
                        "claim_id": f"clm_ram_{eid or 'unknown'}",
                        "field": "RAM",
                        "claimed_value": p.get("ram").get("raw_value") if isinstance(p.get("ram"), dict) else str(p.get("ram")),
                        "cited_evidence_ids": [eid] if eid else [],
                    })

        claims_res = self.detect_unsupported_claims(
            claims=input_claims,
            evidence_records=evidence_records,
            conflicts=conflicts.get("conflicts") if isinstance(conflicts, dict) else None,
        )

        # 5. Trust Assessment
        trust_assessment = self.calculate_trust_assessment(
            evidence_records=evidence_records,
            quality_result=quality_res,
            freshness_result=freshness_res,
            consistency_result=consistency_res,
            claims_result=claims_res,
        )

        # 6. Integrity status
        if quality_res.tampered_records_count > 0:
            integrity_status = "TAMPERING_DETECTED"
        elif all(r.integrity_status == "verified" for r in quality_res.records) and quality_res.total_records > 0:
            integrity_status = "ALL_RECORDS_VERIFIED"
        else:
            integrity_status = "PARTIAL_UNVERIFIED"

        # 7. Supported, Conflicting, Unsupported, and Missing fields
        supported_list = [c for c in claims_res.claims if c.status == ClaimStatus.SUPPORTED]
        conflicting_list = [c for c in claims_res.claims if c.status == ClaimStatus.CONTRADICTED]
        unsupported_list = [c for c in claims_res.claims if c.status == ClaimStatus.UNSUPPORTED]
        stale_list = [s for s in freshness_res.items if s.is_stale]

        # Missing fields identification
        missing_fields: List[str] = []
        for field_item in consistency_res.fields:
            if field_item.status == ConsistencyStatus.UNKNOWN:
                missing_fields.append(field_item.field_name)

        # Generate recommended verification steps
        rec_steps: List[RecommendedVerificationStep] = []
        step_idx = 1

        if quality_res.tampered_records_count > 0:
            rec_steps.append(
                RecommendedVerificationStep(
                    step_id=f"step_{step_idx:02d}",
                    priority="critical",
                    action="Do not rely on cached database evidence; cryptographic hash mismatch indicates altered data.",
                    rationale=f"{quality_res.tampered_records_count} record(s) failed SHA-256 verification.",
                    relevant_urls=[],
                )
            )
            step_idx += 1

        if consistency_res.disagreeing_fields_count > 0:
            for item in consistency_res.fields:
                if item.status == ConsistencyStatus.DISAGREEMENT:
                    rec_steps.append(
                        RecommendedVerificationStep(
                            step_id=f"step_{step_idx:02d}",
                            priority="critical",
                            action=f"Check official manufacturer spec sheet (PDF) for '{item.field_name}'.",
                            rationale=f"Retailers report conflicting claims: {item.explanation}",
                            relevant_urls=[c.get("source_url") for c in item.distinct_claims if c.get("source_url")],
                        )
                    )
                    step_idx += 1

        # Also check conflicting_list from claims_res for any contradicted fields
        disputed_fields_done = {item.field_name.lower() for item in consistency_res.fields if item.status == ConsistencyStatus.DISAGREEMENT}
        for c in conflicting_list:
            if c.field.lower() not in disputed_fields_done:
                disputed_fields_done.add(c.field.lower())
                rec_steps.append(
                    RecommendedVerificationStep(
                        step_id=f"step_{step_idx:02d}",
                        priority="critical",
                        action=f"Check official manufacturer spec sheet (PDF) for '{c.field}'.",
                        rationale=f"Retailers report conflicting claims: {c.explanation}",
                        relevant_urls=[],
                    )
                )
                step_idx += 1

        if freshness_res.stale_count > 0:
            rec_steps.append(
                RecommendedVerificationStep(
                    step_id=f"step_{step_idx:02d}",
                    priority="recommended",
                    action="Verify live checkout price and stock availability directly on retailer page.",
                    rationale=f"{freshness_res.stale_count} source record(s) are older than {freshness_res.freshness_policy_applied.aging_hours / 24:.0f} days.",
                    relevant_urls=[s.source_url for s in stale_list],
                )
            )
            step_idx += 1

        if unsupported_list:
            rec_steps.append(
                RecommendedVerificationStep(
                    step_id=f"step_{step_idx:02d}",
                    priority="recommended",
                    action="Request seller documentation for unsupported claims.",
                    rationale=f"{len(unsupported_list)} product claim(s) lack supporting evidence references.",
                    relevant_urls=[],
                )
            )
            step_idx += 1

        # Product identity extraction
        product_ident = comparison_dict.get("product_identity") or {}
        if not product_ident and evidence_records:
            first = evidence_records[0]
            product_ident = {
                "product_id": first.get("product_id"),
                "product_name": first.get("product_name") or first.get("product_id"),
            }

        return TrustReportResult(
            report_id=report_id,
            product_identity=product_ident,
            trust_assessment=trust_assessment,
            evidence_quality_summary=quality_res,
            freshness_summary=freshness_res,
            consistency_summary=consistency_res,
            supported_claims=supported_list,
            conflicting_claims=conflicting_list,
            unsupported_claims=unsupported_list,
            missing_fields=missing_fields,
            stale_sources=stale_list,
            integrity_status=integrity_status,
            recommended_verification_steps=rec_steps,
        )


default_trust_service = TrustService()
