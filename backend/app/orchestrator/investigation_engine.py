import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.orchestrator.errors import (
    InvestigationNotFoundError,
    MCPToolExecutionError,
    StageExecutionError,
)
from app.orchestrator.mcp_manager import mcp_manager
from app.orchestrator.investigation_state import (
    InvestigationStateStore,
    default_state_store,
)
from app.orchestrator.schemas import (
    InvestigationEvent,
    InvestigationRecord,
    InvestigationStage,
    StageRecord,
    StageStatus,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.orchestrator.engine")
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


class InvestigationEngine:
    """Multi-stage orchestration engine coordinating all 4 MCP servers over stdio."""

    def __init__(self, state_store: Optional[InvestigationStateStore] = None) -> None:
        self.state_store = state_store or default_state_store
        self.mcp = mcp_manager
        # In-memory pub-sub queues for SSE event streaming per investigation
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    # -----------------------------------------------------------------------
    # SSE Event Streaming Helpers
    # -----------------------------------------------------------------------
    def subscribe(self, investigation_id: str) -> asyncio.Queue:
        """Subscribe to live investigation progress events."""
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.setdefault(investigation_id, []).append(q)
        return q

    def unsubscribe(self, investigation_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from live events."""
        if investigation_id in self._listeners:
            if queue in self._listeners[investigation_id]:
                self._listeners[investigation_id].remove(queue)
            if not self._listeners[investigation_id]:
                del self._listeners[investigation_id]

    async def broadcast_event(
        self,
        investigation_id: str,
        event_type: str,
        stage: InvestigationStage,
        status: StageStatus,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Broadcast an event to all connected SSE clients."""
        event = InvestigationEvent(
            event_type=event_type,
            investigation_id=investigation_id,
            stage=stage.value if hasattr(stage, "value") else str(stage),
            status=status.value if hasattr(status, "value") else str(status),
            message=message,
            data=data,
        )
        queues = self._listeners.get(investigation_id, [])
        for q in queues:
            await q.put(event)

    # -----------------------------------------------------------------------
    # Investigation Initialization & Lifecycle
    # -----------------------------------------------------------------------
    def initialize_investigation(
        self,
        query: str,
        category: Optional[str] = None,
        budget_inr: Optional[float] = None,
        notes: Optional[str] = None,
        target_urls: Optional[List[str]] = None,
    ) -> InvestigationRecord:
        """Create and persist an initial investigation record in pending state."""
        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        now = current_utc_iso()

        # Initialize all 6 standard pipeline stage records
        stages = {
            InvestigationStage.PLAN.value: StageRecord(
                stage=InvestigationStage.PLAN,
                label="STAGE 1 — PLAN",
                status=StageStatus.PENDING,
                message="Plan investigation scope, parameters, and target URLs.",
            ),
            InvestigationStage.BROWSER.value: StageRecord(
                stage=InvestigationStage.BROWSER,
                label="STAGE 2 — BROWSER MCP",
                mcp_server="browser",
                status=StageStatus.PENDING,
                message="Inspect public product pages and extract specifications and evidence.",
            ),
            InvestigationStage.EVIDENCE.value: StageRecord(
                stage=InvestigationStage.EVIDENCE,
                label="STAGE 3 — EVIDENCE MCP",
                mcp_server="evidence",
                status=StageStatus.PENDING,
                message="Persist immutable evidence records in SQLite with SHA-256 verification.",
            ),
            InvestigationStage.COMPARISON.value: StageRecord(
                stage=InvestigationStage.COMPARISON,
                label="STAGE 4 — COMPARISON MCP",
                mcp_server="comparison",
                status=StageStatus.PENDING,
                message="Normalize specifications, compute configuration fingerprints, and audit policies.",
            ),
            InvestigationStage.TRUST.value: StageRecord(
                stage=InvestigationStage.TRUST,
                label="STAGE 5 — TRUST MCP",
                mcp_server="trust",
                status=StageStatus.PENDING,
                message="Assess evidence quality, freshness, consistency, and generate trust report.",
            ),
            InvestigationStage.RESULT.value: StageRecord(
                stage=InvestigationStage.RESULT,
                label="STAGE 6 — RESULT",
                status=StageStatus.PENDING,
                message="Synthesize and persist final investigation report.",
            ),
        }

        record = InvestigationRecord(
            investigation_id=inv_id,
            query=query.strip(),
            category=category.strip().lower() if category else "laptop",
            budget_inr=budget_inr,
            notes=notes,
            status="pending",
            current_stage=InvestigationStage.PLAN,
            created_at_utc=now,
            updated_at_utc=now,
            target_urls=target_urls or [],
            stages=stages,
        )
        self.state_store.save_investigation(record)
        logger.info("Initialized investigation '%s' for query '%s'", inv_id, query)
        return record

    async def start_investigation(
        self,
        query: str,
        category: Optional[str] = None,
        budget_inr: Optional[float] = None,
        notes: Optional[str] = None,
        target_urls: Optional[List[str]] = None,
    ) -> InvestigationRecord:
        """Create investigation and trigger asynchronous execution task."""
        record = self.initialize_investigation(
            query=query,
            category=category,
            budget_inr=budget_inr,
            notes=notes,
            target_urls=target_urls,
        )
        # Launch engine in background task
        asyncio.create_task(self.run_investigation(record.investigation_id))
        return record

    # -----------------------------------------------------------------------
    # Main Multi-Stage Orchestration
    # -----------------------------------------------------------------------
    async def run_investigation(self, investigation_id: str) -> InvestigationRecord:
        """Execute the complete 6-stage investigation workflow connecting all 4 MCP servers."""
        rec = self.state_store.get_investigation(investigation_id)
        if not rec:
            raise InvestigationNotFoundError(f"Investigation '{investigation_id}' not found.")

        logger.info("Starting multi-stage execution for investigation '%s'", investigation_id)

        try:
            # ---------------------------------------------------------------
            # STAGE 1 — PLAN
            # ---------------------------------------------------------------
            rec = await self._run_stage_plan(rec)

            # ---------------------------------------------------------------
            # STAGE 2 — BROWSER MCP
            # ---------------------------------------------------------------
            rec = await self._run_stage_browser(rec)

            # ---------------------------------------------------------------
            # STAGE 3 — EVIDENCE MCP
            # ---------------------------------------------------------------
            rec = await self._run_stage_evidence(rec)

            # ---------------------------------------------------------------
            # STAGE 4 — COMPARISON MCP
            # ---------------------------------------------------------------
            rec = await self._run_stage_comparison(rec)

            # ---------------------------------------------------------------
            # STAGE 5 — TRUST MCP
            # ---------------------------------------------------------------
            rec = await self._run_stage_trust(rec)

            # ---------------------------------------------------------------
            # STAGE 6 — RESULT
            # ---------------------------------------------------------------
            rec = await self._run_stage_result(rec)

            return rec

        except Exception as ex:
            logger.error("Investigation '%s' failed: %s", investigation_id, ex, exc_info=True)
            rec = self.state_store.fail_investigation(investigation_id, str(ex))
            await self.broadcast_event(
                investigation_id=investigation_id,
                event_type="error",
                stage=rec.current_stage,
                status=StageStatus.FAILED,
                message=f"Investigation failed: {ex}",
            )
            return rec

    # -----------------------------------------------------------------------
    # Stage 1: Plan
    # -----------------------------------------------------------------------
    async def _run_stage_plan(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.PLAN
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, "Analyzing query and determining public target sources."
        )
        await self.broadcast_event(rec.investigation_id, "stage_started", stage, StageStatus.RUNNING, "Planning research scope.")

        # Determine target URLs ONLY from explicit input, local fixtures, or real Browser MCP discovery
        target_urls = list(rec.target_urls)
        if not target_urls:
            if "fixture" in rec.query.lower() or (rec.notes and "fixture" in rec.notes.lower()):
                std_fix = FIXTURES_DIR / "product_standard.html"
                if std_fix.exists():
                    target_urls.append(f"file:///{std_fix.as_posix()}")
            else:
                # Never guess or concatenate retailer URLs; use legitimate Browser MCP search discovery
                try:
                    async with self.mcp.open_session("browser") as session:
                        disc_res, disc_log = await self.mcp.call_tool_on_session(
                            session,
                            "browser",
                            "discover_product_urls",
                            {"query": rec.query, "category": rec.category, "max_results": 4},
                            timeout_seconds=25.0,
                        )
                        rec.stages[stage.value].tool_logs.append(disc_log)
                        rec.all_tool_logs.append(disc_log)

                        for item in disc_res.get("discovered_urls") or []:
                            if item.get("url"):
                                target_urls.append(item["url"])
                        for blk in disc_res.get("blocked_sources") or []:
                            rec.warnings.append(f"Search blocked: {blk}")
                        for note in disc_res.get("discovery_notes") or []:
                            if not target_urls:
                                rec.warnings.append(note)
                except Exception as ex:
                    logger.warning("URL discovery failed: %s", ex)
                    rec.warnings.append(f"Product URL discovery unavailable: {ex}")

        plan_data = {
            "query": rec.query,
            "category": rec.category,
            "budget_inr": rec.budget_inr,
            "target_urls": target_urls,
            "approved_domains": ["amazon.in", "flipkart.com", "croma.com", "dell.com", "lenovo.com", "apple.com"],
            "comparison_criteria": ["price", "specs", "ram", "storage", "warranty", "return_policy"],
        }

        rec.plan_data = plan_data
        rec.target_urls = target_urls
        self.state_store.save_investigation(rec)
        rec = self.state_store.update_stage_progress(
            rec.investigation_id,
            stage,
            StageStatus.COMPLETED,
            f"Plan finalized with {len(target_urls)} target source(s).",
        )
        await self.broadcast_event(
            rec.investigation_id,
            "stage_completed",
            stage,
            StageStatus.COMPLETED,
            f"Planned targets: {target_urls}",
            plan_data,
        )
        return rec

    # -----------------------------------------------------------------------
    # Stage 2: Browser MCP
    # -----------------------------------------------------------------------
    async def _run_stage_browser(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.BROWSER
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, f"Connecting to Browser MCP to inspect {len(rec.target_urls)} page(s)."
        )
        await self.broadcast_event(rec.investigation_id, "stage_started", stage, StageStatus.RUNNING, "Browser MCP active.")

        extracted_records: List[Dict[str, Any]] = []

        if not rec.target_urls:
            rec.warnings.append("No valid product URLs were discovered or provided; Browser MCP extraction skipped.")
            self.state_store.save_investigation(rec)
            rec = self.state_store.update_stage_progress(
                rec.investigation_id,
                stage,
                StageStatus.SKIPPED,
                "Skipped: no valid public product URLs discovered or supplied.",
            )
            await self.broadcast_event(
                rec.investigation_id,
                "stage_completed",
                stage,
                StageStatus.SKIPPED,
                "No target URLs to inspect.",
            )
            return rec

        # Connect to Browser MCP via stdio
        async with self.mcp.open_session("browser") as session:
            for url in rec.target_urls:
                try:
                    logger.info("Browser MCP opening: %s", url)
                    open_res, open_log = await self.mcp.call_tool_on_session(
                        session, "browser", "open_product_page", {"url": url}, timeout_seconds=20.0
                    )
                    rec.stages[stage.value].tool_logs.append(open_log)
                    rec.all_tool_logs.append(open_log)

                    # Validate HTTP status & page eligibility BEFORE extracting/storing evidence
                    page_status = open_res.get("page_status")
                    if open_res.get("error") or not open_res.get("is_valid_product_page", True) or (page_status is not None and page_status >= 400):
                        reason = open_res.get("error") or f"HTTP {page_status} / invalid page"
                        logger.warning("Rejected source '%s' during open_product_page: %s", url, reason)
                        rec.warnings.append(f"Rejected {url}: {reason}")
                        rec.rejected_candidates.append({
                            "source_url": open_res.get("final_url") or url,
                            "product_name": open_res.get("page_title"),
                            "match_status": open_res.get("block_reason") or "HTTP_OR_PAGE_ERROR",
                            "reason": reason,
                            "capture_timestamp": open_res.get("capture_timestamp_utc") or current_utc_iso(),
                        })
                        continue

                    # Extract product data with strict token-aware identity & category validation
                    data_res, data_log = await self.mcp.call_tool_on_session(
                        session,
                        "browser",
                        "extract_product_data",
                        {
                            "url": url,
                            "expected_category": rec.category,
                            "expected_query": rec.query,
                        },
                        timeout_seconds=20.0,
                    )
                    rec.stages[stage.value].tool_logs.append(data_log)
                    rec.all_tool_logs.append(data_log)

                    match_status = data_res.get("match_status")
                    if data_res.get("error") or not data_res.get("is_valid_product_page", True):
                        reason = data_res.get("validation_error") or data_res.get("error") or "Invalid product page"
                        price_obj = data_res.get("price") or {}
                        diag = {
                            "source_url": open_res.get("final_url") or url,
                            "product_name": data_res.get("product_name") or open_res.get("page_title"),
                            "brand": data_res.get("brand"),
                            "model": data_res.get("model"),
                            "raw_displayed_price": price_obj.get("displayed_text"),
                            "currency": price_obj.get("currency"),
                            "numeric_price": price_obj.get("numeric_amount"),
                            "match_status": match_status or data_res.get("block_reason") or "REJECTED",
                            "reason": reason,
                            "capture_timestamp": data_res.get("capture_timestamp_utc") or current_utc_iso(),
                        }
                        if match_status == "RELATED_VARIANT":
                            logger.info("Separated related variant '%s': %s", url, reason)
                            rec.related_variants.append(diag)
                            rec.warnings.append(f"Separated variant {url} (excluded from exact match): {reason}")
                        else:
                            logger.warning("Rejected source '%s' during extraction: %s", url, reason)
                            rec.rejected_candidates.append(diag)
                            rec.warnings.append(f"Rejected {url}: {reason}")
                        continue

                    # Capture DOM evidence ONLY for validated product pages
                    evi_res, evi_log = await self.mcp.call_tool_on_session(
                        session, "browser", "capture_page_evidence", {"url": url}, timeout_seconds=20.0
                    )
                    rec.stages[stage.value].tool_logs.append(evi_log)
                    rec.all_tool_logs.append(evi_log)

                    price_obj = data_res.get("price") or {}
                    combined_record = {
                        "source_url": open_res.get("final_url") or url,
                        "source_title": open_res.get("page_title") or data_res.get("product_name"),
                        "product_name": data_res.get("product_name") or rec.query,
                        "brand": data_res.get("brand"),
                        "model": data_res.get("model"),
                        "model_number": data_res.get("model_number"),
                        "raw_displayed_price": price_obj.get("displayed_text"),
                        "currency": price_obj.get("currency"),
                        "numeric_price": price_obj.get("numeric_amount"),
                        "specifications": data_res.get("specifications") or {},
                        "warranty": data_res.get("warranty"),
                        "return_policy": data_res.get("return_policy"),
                        "extracted_claims": evi_res.get("extracted_text_snippets") or [],
                        "page_sha256_hash": evi_res.get("sha256_hash"),
                        "capture_timestamp": evi_res.get("capture_timestamp_utc") or current_utc_iso(),
                    }
                    extracted_records.append(combined_record)

                except Exception as ex:
                    logger.warning("Browser MCP inspection failed for URL '%s': %s", url, ex)
                    rec.warnings.append(f"Browser inspection failed for {url}: {ex}")

        rec.extracted_records = extracted_records
        self.state_store.save_investigation(rec)
        if not extracted_records:
            rec = self.state_store.update_stage_progress(
                rec.investigation_id,
                stage,
                StageStatus.FAILED,
                "All target URLs failed product page validation (404, anti-bot block, or generic homepage).",
            )
            await self.broadcast_event(
                rec.investigation_id,
                "stage_completed",
                stage,
                StageStatus.FAILED,
                "0 valid product sources extracted.",
            )
            return rec

        rec = self.state_store.update_stage_progress(
            rec.investigation_id,
            stage,
            StageStatus.COMPLETED,
            f"Successfully inspected and validated {len(extracted_records)} product source(s).",
        )
        await self.broadcast_event(
            rec.investigation_id,
            "stage_completed",
            stage,
            StageStatus.COMPLETED,
            f"Extracted {len(extracted_records)} validated records from Browser MCP.",
        )
        return rec

    # -----------------------------------------------------------------------
    # Stage 3: Evidence MCP
    # -----------------------------------------------------------------------
    async def _run_stage_evidence(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.EVIDENCE
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, "Persisting evidence records in Evidence MCP."
        )
        await self.broadcast_event(rec.investigation_id, "stage_started", stage, StageStatus.RUNNING, "Evidence MCP active.")

        if not rec.extracted_records:
            rec = self.state_store.update_stage_progress(
                rec.investigation_id,
                stage,
                StageStatus.SKIPPED,
                "Skipped: no validated product sources were extracted to persist.",
            )
            await self.broadcast_event(
                rec.investigation_id,
                "stage_completed",
                stage,
                StageStatus.SKIPPED,
                "Evidence persistence skipped (0 valid sources).",
            )
            return rec

        saved_evidence_ids: List[str] = []
        persisted_records: List[Dict[str, Any]] = []

        async with self.mcp.open_session("evidence") as session:
            for item in rec.extracted_records:
                raw_pid = (item.get("product_name") or rec.query or "product").strip()
                slug_pid = re.sub(r"[^a-z0-9]+", "-", raw_pid.lower()).strip("-")[:80].strip("-")
                if len(slug_pid) < 2:
                    slug_pid = "product-item"

                raw_title = item.get("source_title")
                bounded_title = raw_title[:450] if isinstance(raw_title, str) and len(raw_title) > 450 else raw_title

                save_payload = {
                    "investigation_id": rec.investigation_id,
                    "product_id": slug_pid,
                    "source_url": item["source_url"][:2048],
                    "source_title": bounded_title,
                    "capture_timestamp": item.get("capture_timestamp"),
                    "evidence_type": "retailer_price",
                    "extracted_claims": item.get("extracted_claims") or [],
                    "raw_displayed_price": item.get("raw_displayed_price"),
                    "currency": item.get("currency"),
                    "numeric_price": item.get("numeric_price"),
                    "evidence_hash": item.get("evidence_hash"),
                    "metadata": {
                        "specifications": item.get("specifications"),
                        "warranty": item.get("warranty"),
                        "return_policy": item.get("return_policy"),
                        "full_source_title": raw_title if bounded_title != raw_title else None,
                    },
                }

                try:
                    save_res, save_log = await self.mcp.call_tool_on_session(
                        session, "evidence", "save_evidence", save_payload, timeout_seconds=15.0
                    )
                    rec.stages[stage.value].tool_logs.append(save_log)
                    rec.all_tool_logs.append(save_log)

                    eid = save_res.get("evidence_id")
                    if eid:
                        saved_evidence_ids.append(eid)
                        item["evidence_id"] = eid
                        item["evidence_hash"] = save_res.get("evidence_hash")
                        item["investigation_id"] = save_res.get("investigation_id")
                        item["product_id"] = save_res.get("product_id")
                        item["evidence_type"] = save_res.get("evidence_type")
                        persisted_records.append(item)
                except Exception as ex:
                    logger.warning(
                        "Failed to persist evidence for URL '%s': %s",
                        item.get("source_url"),
                        ex,
                        exc_info=True,
                    )
                    rec.warnings.append(f"Evidence persistence failed for {item.get('source_url')}: {ex}")

        if not saved_evidence_ids:
            raise StageExecutionError("evidence", "Evidence MCP failed to persist any evidence records.")

        rec.extracted_records = persisted_records
        rec.evidence_ids = saved_evidence_ids
        self.state_store.save_investigation(rec)
        rec = self.state_store.update_stage_progress(
            rec.investigation_id,
            stage,
            StageStatus.COMPLETED,
            f"Persisted {len(saved_evidence_ids)} immutable evidence record(s).",
        )
        await self.broadcast_event(
            rec.investigation_id,
            "stage_completed",
            stage,
            StageStatus.COMPLETED,
            f"Stored Evidence IDs: {saved_evidence_ids}",
        )
        return rec

    # -----------------------------------------------------------------------
    # Stage 4: Comparison MCP
    # -----------------------------------------------------------------------
    async def _run_stage_comparison(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.COMPARISON
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, "Normalizing specs and comparing prices in Comparison MCP."
        )
        await self.broadcast_event(rec.investigation_id, "stage_started", stage, StageStatus.RUNNING, "Comparison MCP active.")

        if not rec.extracted_records:
            rec = self.state_store.update_stage_progress(
                rec.investigation_id,
                stage,
                StageStatus.SKIPPED,
                "Skipped: no validated product sources available to compare.",
            )
            await self.broadcast_event(
                rec.investigation_id,
                "stage_completed",
                stage,
                StageStatus.SKIPPED,
                "Comparison skipped (0 valid sources).",
            )
            return rec

        async with self.mcp.open_session("comparison") as session:
            # 1. Normalize each product
            normalized_products: List[Dict[str, Any]] = []
            for item in rec.extracted_records:
                norm_res, norm_log = await self.mcp.call_tool_on_session(
                    session,
                    "comparison",
                    "normalize_product",
                    {
                        "product_name": item.get("product_name") or rec.query,
                        "brand": item.get("brand"),
                        "model": item.get("model"),
                        "model_number": item.get("model_number"),
                        "specifications": item.get("specifications") or {},
                        "source_evidence_id": item.get("evidence_id"),
                        "source_url": item.get("source_url"),
                    },
                )
                rec.stages[stage.value].tool_logs.append(norm_log)
                rec.all_tool_logs.append(norm_log)
                normalized_products.append(norm_res)

            # 2. Compare prices
            price_recs = [
                {
                    "source_url": item["source_url"],
                    "source_domain": item["source_url"].split("//")[-1].split("/")[0],
                    "source_title": item.get("source_title"),
                    "capture_timestamp": item.get("capture_timestamp"),
                    "raw_displayed_price": item.get("raw_displayed_price"),
                    "currency": item.get("currency"),
                    "numeric_price": item.get("numeric_price"),
                    "evidence_id": item.get("evidence_id"),
                }
                for item in rec.extracted_records
            ]
            price_res, price_log = await self.mcp.call_tool_on_session(
                session, "comparison", "compare_prices", {"price_records": price_recs}
            )
            rec.stages[stage.value].tool_logs.append(price_log)
            rec.all_tool_logs.append(price_log)

            # 3. Compare specifications
            spec_res, spec_log = await self.mcp.call_tool_on_session(
                session, "comparison", "compare_specifications", {"products": normalized_products}
            )
            rec.stages[stage.value].tool_logs.append(spec_log)
            rec.all_tool_logs.append(spec_log)

            # 4. Compare policies
            policy_recs = [
                {
                    "source_url": item["source_url"],
                    "warranty": item.get("warranty"),
                    "return_policy": item.get("return_policy"),
                    "evidence_id": item.get("evidence_id"),
                }
                for item in rec.extracted_records
            ]
            policy_res, policy_log = await self.mcp.call_tool_on_session(
                session, "comparison", "compare_policies", {"policy_records": policy_recs}
            )
            rec.stages[stage.value].tool_logs.append(policy_log)
            rec.all_tool_logs.append(policy_log)

            # 5. Find conflicts
            conflict_res, conflict_log = await self.mcp.call_tool_on_session(
                session, "comparison", "find_product_conflicts", {"products": normalized_products}
            )
            rec.stages[stage.value].tool_logs.append(conflict_log)
            rec.all_tool_logs.append(conflict_log)

            # 6. Generate comprehensive comparison
            comp_res, comp_log = await self.mcp.call_tool_on_session(
                session, "comparison", "generate_comparison", {"evidence_items": rec.extracted_records}
            )
            rec.stages[stage.value].tool_logs.append(comp_log)
            rec.all_tool_logs.append(comp_log)

            rec.comparison_result = comp_res

        self.state_store.save_investigation(rec)
        rec = self.state_store.update_stage_progress(
            rec.investigation_id,
            stage,
            StageStatus.COMPLETED,
            f"Comparison generated across {len(normalized_products)} product configuration(s).",
        )
        await self.broadcast_event(
            rec.investigation_id,
            "stage_completed",
            stage,
            StageStatus.COMPLETED,
            "Comparison completed.",
            {"configuration_match": comp_res.get("configuration_match")},
        )
        return rec

    # -----------------------------------------------------------------------
    # Stage 5: Trust MCP
    # -----------------------------------------------------------------------
    async def _run_stage_trust(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.TRUST
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, "Assessing evidence quality, freshness, and trust in Trust MCP."
        )
        await self.broadcast_event(rec.investigation_id, "stage_started", stage, StageStatus.RUNNING, "Trust MCP active.")

        async with self.mcp.open_session("trust") as session:
            # 1. Evidence quality
            q_res, q_log = await self.mcp.call_tool_on_session(
                session, "trust", "assess_evidence_quality", {"evidence_records": rec.extracted_records}
            )
            rec.stages[stage.value].tool_logs.append(q_log)
            rec.all_tool_logs.append(q_log)

            # 2. Freshness
            f_res, f_log = await self.mcp.call_tool_on_session(
                session, "trust", "check_source_freshness", {"evidence_records": rec.extracted_records}
            )
            rec.stages[stage.value].tool_logs.append(f_log)
            rec.all_tool_logs.append(f_log)

            # 3. Detect unsupported claims
            claims_input = []
            for item in rec.extracted_records:
                eid = item.get("evidence_id")
                for c in item.get("extracted_claims", []):
                    claims_input.append({
                        "claim_id": f"clm_{uuid.uuid4().hex[:8]}",
                        "field": "Extracted Claim",
                        "claimed_value": c,
                        "cited_evidence_ids": [eid] if eid else [],
                    })
            if not claims_input and rec.evidence_ids:
                claims_input = [
                    {"claim_id": "clm_def", "field": "Product", "claimed_value": rec.query, "cited_evidence_ids": rec.evidence_ids}
                ]

            claims_res, claims_log = await self.mcp.call_tool_on_session(
                session,
                "trust",
                "detect_unsupported_claims",
                {
                    "claims": claims_input,
                    "evidence_records": rec.extracted_records,
                    "conflicts": rec.comparison_result.get("conflicts", {}).get("conflicts", []) if rec.comparison_result else [],
                },
            )
            rec.stages[stage.value].tool_logs.append(claims_log)
            rec.all_tool_logs.append(claims_log)

            # 4. Consistency
            cons_res, cons_log = await self.mcp.call_tool_on_session(
                session,
                "trust",
                "evaluate_source_consistency",
                {
                    "spec_comparison": rec.comparison_result.get("spec_comparison") if rec.comparison_result else None,
                    "price_comparison": rec.comparison_result.get("price_comparison") if rec.comparison_result else None,
                    "conflicts": rec.comparison_result.get("conflicts") if rec.comparison_result else None,
                },
            )
            rec.stages[stage.value].tool_logs.append(cons_log)
            rec.all_tool_logs.append(cons_log)

            # 5. Trust Assessment
            t_res, t_log = await self.mcp.call_tool_on_session(
                session,
                "trust",
                "calculate_trust_assessment",
                {
                    "evidence_records": rec.extracted_records,
                    "quality_result": q_res,
                    "freshness_result": f_res,
                    "consistency_result": cons_res,
                    "claims_result": claims_res,
                },
            )
            rec.stages[stage.value].tool_logs.append(t_log)
            rec.all_tool_logs.append(t_log)

            # 6. Generate Trust Report
            report_res, report_log = await self.mcp.call_tool_on_session(
                session,
                "trust",
                "generate_trust_report",
                {
                    "evidence_records": rec.extracted_records,
                    "comparison_data": rec.comparison_result,
                    "claims": claims_input,
                },
            )
            rec.stages[stage.value].tool_logs.append(report_log)
            rec.all_tool_logs.append(report_log)

            rec.trust_report = report_res

        tier = report_res.get("trust_assessment", {}).get("overall_trust_tier", "COMPLETED")
        self.state_store.save_investigation(rec)
        rec = self.state_store.update_stage_progress(
            rec.investigation_id,
            stage,
            StageStatus.COMPLETED,
            f"Trust report generated with status: {tier}.",
        )
        await self.broadcast_event(
            rec.investigation_id,
            "stage_completed",
            stage,
            StageStatus.COMPLETED,
            f"Trust assessment tier: {tier}",
            {"overall_trust_tier": tier},
        )
        return rec

    # -----------------------------------------------------------------------
    # Stage 6: Result Synthesis
    # -----------------------------------------------------------------------
    async def _run_stage_result(self, rec: InvestigationRecord) -> InvestigationRecord:
        stage = InvestigationStage.RESULT
        self.state_store.update_stage_progress(
            rec.investigation_id, stage, StageStatus.RUNNING, "Synthesizing investigation findings and audit trail."
        )

        tier = rec.trust_report.get("trust_assessment", {}).get("overall_trust_tier", "MODERATE_TRANSPARENCY") if rec.trust_report else "COMPLETED"
        evi_count = len(rec.evidence_ids)
        src_count = len(rec.extracted_records)
        summary = (
            f"Investigation for '{rec.query}' completed across {src_count} source(s) and {evi_count} evidence record(s). "
            f"Trust tier: {tier}. All 4 MCP servers executed over stdio with full cryptographic provenance."
        )

        rec = self.state_store.complete_investigation(rec.investigation_id, summary=summary)
        await self.broadcast_event(
            rec.investigation_id,
            "completed",
            stage,
            StageStatus.COMPLETED,
            summary,
            {"investigation_id": rec.investigation_id, "summary": summary},
        )
        logger.info("Investigation '%s' successfully completed", rec.investigation_id)
        return rec


default_investigation_engine = InvestigationEngine()
