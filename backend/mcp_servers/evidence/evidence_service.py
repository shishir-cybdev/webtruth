import hashlib
import json
import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp_servers.evidence.database import EvidenceDatabase, default_db
from mcp_servers.evidence.schemas import (
    DuplicateEvidenceResult,
    EvidenceRecord,
    PriceHistorySnapshot,
    ProductEvidenceHistoryResult,
    SaveEvidenceRequest,
    SearchEvidenceResult,
    VerifyEvidenceResult,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.evidence.service")


def extract_domain(url: str) -> str:
    """Extract domain host from URL without port, handling file:// gracefully."""
    if not url:
        return "unknown"
    if url.startswith("file://"):
        return "local_fixture"
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return host if host else "unknown"
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
    """Compute deterministic SHA-256 hash over canonical JSON payload.
    
    Guarantees that identical evidence contents yield identical hashes regardless of
    in-memory dictionary ordering.
    """
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
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class EvidenceService:
    """Service handling tamper-evident evidence persistence and verification."""

    def __init__(self, db: Optional[EvidenceDatabase] = None) -> None:
        self.db = db or default_db

    def _row_to_record(self, row: sqlite3.Row) -> EvidenceRecord:
        """Map SQLite row to EvidenceRecord Pydantic model."""
        claims = json.loads(row["extracted_claims_json"])
        meta = json.loads(row["metadata_json"])
        return EvidenceRecord(
            evidence_id=row["evidence_id"],
            investigation_id=row["investigation_id"],
            product_id=row["product_id"],
            source_url=row["source_url"],
            source_domain=row["source_domain"],
            source_title=row["source_title"],
            capture_timestamp=row["capture_timestamp"],
            evidence_type=row["evidence_type"],
            extracted_claims=claims,
            raw_displayed_price=row["raw_displayed_price"],
            currency=row["currency"],
            numeric_price=row["numeric_price"],
            evidence_hash=row["evidence_hash"],
            created_at=row["created_at"],
            metadata=meta,
        )

    def save_evidence(self, request: SaveEvidenceRequest) -> EvidenceRecord:
        """Validate, compute canonical hash, and persist an immutable evidence record."""
        capture_time = request.capture_timestamp or current_utc_iso()
        domain = extract_domain(request.source_url)
        computed_hash = compute_canonical_evidence_hash(
            investigation_id=request.investigation_id,
            product_id=request.product_id,
            source_url=request.source_url,
            capture_timestamp=capture_time,
            evidence_type=request.evidence_type,
            extracted_claims=request.extracted_claims,
            raw_displayed_price=request.raw_displayed_price,
            currency=request.currency,
        )

        evidence_id = f"evi_{uuid.uuid4().hex[:12]}"
        now = current_utc_iso()
        claims_json = json.dumps(request.extracted_claims, ensure_ascii=False)
        meta_json = json.dumps(request.metadata or {}, ensure_ascii=False)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evidence_records (
                    evidence_id, investigation_id, product_id, source_url, source_domain,
                    source_title, capture_timestamp, evidence_type, extracted_claims_json,
                    raw_displayed_price, currency, numeric_price, evidence_hash,
                    metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    evidence_id,
                    request.investigation_id,
                    request.product_id,
                    request.source_url,
                    domain,
                    request.source_title,
                    capture_time,
                    request.evidence_type,
                    claims_json,
                    request.raw_displayed_price,
                    request.currency,
                    request.numeric_price,
                    computed_hash,
                    meta_json,
                    now,
                ),
            )

        logger.info(
            "Saved evidence: id=%s product=%s hash=%s domain=%s",
            evidence_id,
            request.product_id,
            computed_hash[:12],
            domain,
        )
        return self.get_evidence(evidence_id)  # type: ignore

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Retrieve a stored evidence record by its primary key ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evidence_records WHERE evidence_id = ?;",
                (evidence_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def search_evidence(
        self,
        investigation_id: Optional[str] = None,
        product_id: Optional[str] = None,
        source_domain: Optional[str] = None,
        evidence_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SearchEvidenceResult:
        """Search evidence records with dynamic parameterized filtering."""
        where_clauses: List[str] = []
        params: List[Any] = []

        if investigation_id:
            where_clauses.append("investigation_id = ?")
            params.append(investigation_id.strip())
        if product_id:
            where_clauses.append("product_id = ?")
            params.append(product_id.strip().lower())
        if source_domain:
            where_clauses.append("source_domain = ?")
            params.append(source_domain.strip().lower())
        if evidence_type:
            where_clauses.append("evidence_type = ?")
            params.append(evidence_type.strip().lower())

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Count total
            count_query = f"SELECT COUNT(*) as total FROM evidence_records {where_sql};"
            cursor.execute(count_query, params)
            total = cursor.fetchone()["total"]

            # Fetch page
            data_query = f"""
                SELECT * FROM evidence_records {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(data_query, params + [max(1, limit), max(0, offset)])
            rows = cursor.fetchall()
            records = [self._row_to_record(r) for r in rows]

        return SearchEvidenceResult(total=total, items=records)

    def verify_evidence(self, evidence_id: str) -> VerifyEvidenceResult:
        """Recompute SHA-256 from stored row fields and compare against stored hash."""
        record = self.get_evidence(evidence_id)
        if not record:
            return VerifyEvidenceResult(
                evidence_id=evidence_id,
                is_valid=False,
                stored_hash="",
                computed_hash="",
                status="not_found",
                message=f"Evidence record '{evidence_id}' does not exist in the database.",
            )

        recomputed_hash = compute_canonical_evidence_hash(
            investigation_id=record.investigation_id,
            product_id=record.product_id,
            source_url=record.source_url,
            capture_timestamp=record.capture_timestamp,
            evidence_type=record.evidence_type,
            extracted_claims=record.extracted_claims,
            raw_displayed_price=record.raw_displayed_price,
            currency=record.currency,
        )

        is_valid = recomputed_hash == record.evidence_hash
        status = "valid" if is_valid else "modified"
        message = (
            "Evidence integrity verified: canonical content matches SHA-256 hash."
            if is_valid
            else "INTEGRITY VIOLATION: Stored content does not match the original SHA-256 hash. Data was tampered."
        )

        return VerifyEvidenceResult(
            evidence_id=evidence_id,
            is_valid=is_valid,
            stored_hash=record.evidence_hash,
            computed_hash=recomputed_hash,
            status=status,
            message=message,
        )

    def get_product_evidence_history(self, product_id: str) -> ProductEvidenceHistoryResult:
        """Retrieve chronological history of evidence and price snapshots for a product."""
        clean_pid = product_id.strip().lower()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM evidence_records
                WHERE product_id = ?
                ORDER BY capture_timestamp ASC;
                """,
                (clean_pid,),
            )
            rows = cursor.fetchall()
            records = [self._row_to_record(r) for r in rows]

        price_history: List[PriceHistorySnapshot] = []
        for r in records:
            if r.raw_displayed_price or r.numeric_price is not None:
                price_history.append(
                    PriceHistorySnapshot(
                        capture_timestamp=r.capture_timestamp,
                        source_url=r.source_url,
                        source_domain=r.source_domain,
                        raw_displayed_price=r.raw_displayed_price,
                        currency=r.currency,
                        numeric_price=r.numeric_price,
                        evidence_id=r.evidence_id,
                    )
                )

        return ProductEvidenceHistoryResult(
            product_id=clean_pid,
            total_records=len(records),
            price_history=price_history,
            evidence_records=records,
        )

    def detect_duplicate_evidence(
        self,
        source_url: str,
        extracted_claims: List[str],
        investigation_id: Optional[str] = None,
        product_id: Optional[str] = None,
        evidence_hash: Optional[str] = None,
    ) -> DuplicateEvidenceResult:
        """Find identical records without deleting or altering existing evidence."""
        matched_records: List[EvidenceRecord] = []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Exact hash match if hash provided
            if evidence_hash:
                cursor.execute(
                    "SELECT * FROM evidence_records WHERE evidence_hash = ? ORDER BY created_at ASC;",
                    (evidence_hash.strip(),),
                )
                rows = cursor.fetchall()
                if rows:
                    matched_records.extend(self._row_to_record(r) for r in rows)

            # 2. Match identical URL and extracted claims
            if not matched_records:
                cursor.execute(
                    "SELECT * FROM evidence_records WHERE source_url = ? ORDER BY created_at ASC;",
                    (source_url.strip(),),
                )
                rows = cursor.fetchall()
                target_claims_set = set(str(c).strip() for c in extracted_claims if str(c).strip())
                for r in rows:
                    rec = self._row_to_record(r)
                    rec_claims_set = set(str(c).strip() for c in rec.extracted_claims if str(c).strip())
                    if rec_claims_set == target_claims_set and target_claims_set:
                        matched_records.append(rec)

        is_dup = len(matched_records) > 0
        reason = (
            f"Found {len(matched_records)} matching record(s) with identical content/hash"
            if is_dup
            else None
        )

        return DuplicateEvidenceResult(
            is_duplicate=is_dup,
            duplicate_count=len(matched_records),
            matched_records=matched_records,
            reason=reason,
        )


# Global singleton instance
evidence_service = EvidenceService()
