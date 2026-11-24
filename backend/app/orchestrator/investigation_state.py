import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional

from app.orchestrator.errors import InvestigationNotFoundError
from app.orchestrator.schemas import (
    InvestigationRecord,
    InvestigationStage,
    StageRecord,
    StageStatus,
    ToolCallLog,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.orchestrator.state")

DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "investigations.db"


class InvestigationStateStore:
    """Persistent SQLite store for complete investigation lifecycle state and audit records."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self.db_path = str(db_path)
        else:
            env_path = os.getenv("INVESTIGATIONS_DB_PATH")
            if env_path:
                self.db_path = env_path
            else:
                DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
                self.db_path = str(DEFAULT_DB_PATH)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._initialize_schema()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a SQLite connection with row factories enabled and automatic commit/rollback."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        """Create tables and indexes for investigations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    category TEXT,
                    budget_inr REAL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT,
                    data_json TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inv_status ON investigations(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inv_created ON investigations(created_at_utc)
            """)
        logger.debug("Investigation state database initialized at '%s'", self.db_path)

    def save_investigation(self, record: InvestigationRecord) -> None:
        """Insert or replace an investigation record."""
        record.updated_at_utc = current_utc_iso()
        data_json = record.model_dump_json()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO investigations (
                    investigation_id, query, category, budget_inr, status,
                    current_stage, created_at_utc, updated_at_utc, completed_at_utc, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(investigation_id) DO UPDATE SET
                    query = excluded.query,
                    category = excluded.category,
                    budget_inr = excluded.budget_inr,
                    status = excluded.status,
                    current_stage = excluded.current_stage,
                    updated_at_utc = excluded.updated_at_utc,
                    completed_at_utc = excluded.completed_at_utc,
                    data_json = excluded.data_json
                """,
                (
                    record.investigation_id,
                    record.query,
                    record.category,
                    record.budget_inr,
                    record.status,
                    record.current_stage.value if hasattr(record.current_stage, "value") else str(record.current_stage),
                    record.created_at_utc,
                    record.updated_at_utc,
                    record.completed_at_utc,
                    data_json,
                ),
            )
        logger.debug("Saved investigation %s (status=%s)", record.investigation_id, record.status)

    def get_investigation(self, investigation_id: str) -> Optional[InvestigationRecord]:
        """Retrieve an investigation by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_json FROM investigations WHERE investigation_id = ?",
                (investigation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return InvestigationRecord.model_validate_json(row["data_json"])

    def list_investigations(self, limit: int = 50, offset: int = 0) -> List[InvestigationRecord]:
        """Return list of recent investigations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data_json FROM investigations
                ORDER BY created_at_utc DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            return [InvestigationRecord.model_validate_json(r["data_json"]) for r in rows]

    def update_stage_progress(
        self,
        investigation_id: str,
        stage: InvestigationStage,
        status: StageStatus,
        message: Optional[str] = None,
        tool_log: Optional[ToolCallLog] = None,
    ) -> InvestigationRecord:
        """Update a stage's status, progress message, and append tool logs."""
        rec = self.get_investigation(investigation_id)
        if not rec:
            raise InvestigationNotFoundError(f"Investigation '{investigation_id}' not found.")

        stage_key = stage.value if hasattr(stage, "value") else str(stage)
        stage_record = rec.stages.get(stage_key)
        now = current_utc_iso()

        if not stage_record:
            stage_record = StageRecord(
                stage=stage,
                label=f"STAGE — {stage_key.upper()}",
                status=status,
                started_at_utc=now if status == StageStatus.RUNNING else None,
            )
            rec.stages[stage_key] = stage_record

        stage_record.status = status
        if message:
            stage_record.message = message

        if status == StageStatus.RUNNING and not stage_record.started_at_utc:
            stage_record.started_at_utc = now
        elif status in (StageStatus.COMPLETED, StageStatus.FAILED):
            stage_record.completed_at_utc = now

        if tool_log:
            stage_record.tool_logs.append(tool_log)
            rec.all_tool_logs.append(tool_log)

        rec.current_stage = stage
        if status == StageStatus.RUNNING and rec.status == "pending":
            rec.status = "processing"

        self.save_investigation(rec)
        return rec

    def fail_investigation(self, investigation_id: str, error_message: str) -> InvestigationRecord:
        """Mark investigation and current stage as failed."""
        rec = self.get_investigation(investigation_id)
        if not rec:
            raise InvestigationNotFoundError(f"Investigation '{investigation_id}' not found.")

        rec.status = "failed"
        rec.failures.append(error_message)
        rec.updated_at_utc = current_utc_iso()

        stage_key = rec.current_stage.value if hasattr(rec.current_stage, "value") else str(rec.current_stage)
        if stage_key in rec.stages:
            rec.stages[stage_key].status = StageStatus.FAILED
            rec.stages[stage_key].message = f"Failed: {error_message}"
            rec.stages[stage_key].completed_at_utc = current_utc_iso()

        self.save_investigation(rec)
        return rec

    def complete_investigation(self, investigation_id: str, summary: Optional[str] = None) -> InvestigationRecord:
        """Mark investigation as successfully completed."""
        rec = self.get_investigation(investigation_id)
        if not rec:
            raise InvestigationNotFoundError(f"Investigation '{investigation_id}' not found.")

        rec.status = "completed"
        rec.current_stage = InvestigationStage.RESULT
        rec.completed_at_utc = current_utc_iso()
        rec.updated_at_utc = rec.completed_at_utc
        if summary:
            rec.summary = summary

        # Complete final result stage
        result_key = InvestigationStage.RESULT.value
        rec.stages[result_key] = StageRecord(
            stage=InvestigationStage.RESULT,
            label="STAGE 6 — RESULT",
            status=StageStatus.COMPLETED,
            started_at_utc=rec.stages.get(result_key, StageRecord(stage=InvestigationStage.RESULT, label="")).started_at_utc or rec.completed_at_utc,
            completed_at_utc=rec.completed_at_utc,
            message="Investigation synthesized and persisted successfully.",
        )

        self.save_investigation(rec)
        return rec


default_state_store = InvestigationStateStore()
