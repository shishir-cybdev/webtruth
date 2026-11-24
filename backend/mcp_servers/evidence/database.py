import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger("webtruth.evidence.db")

DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "evidence.db"


class EvidenceDatabase:
    """SQLite database manager for persistent evidence records."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self.db_path = str(db_path)
        else:
            env_path = os.getenv("EVIDENCE_DB_PATH")
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
        """Context manager providing a SQLite connection with row factories enabled."""
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
        """Create tables and performance indexes using safe idempotent DDL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_domain TEXT NOT NULL,
                    source_title TEXT,
                    capture_timestamp TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    extracted_claims_json TEXT NOT NULL,
                    raw_displayed_price TEXT,
                    currency TEXT,
                    numeric_price REAL,
                    evidence_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            # Create search and integrity indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence_records(investigation_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_product ON evidence_records(product_id, capture_timestamp);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_domain ON evidence_records(source_domain);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence_records(evidence_type);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence_records(evidence_hash);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evidence_url ON evidence_records(source_url);"
            )
            logger.info("Initialized Evidence database schema at %s", self.db_path)


# Global singleton instance for production use
default_db = EvidenceDatabase()
