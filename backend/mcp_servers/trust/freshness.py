from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FreshnessClassification(str, Enum):
    """Classification of evidence age based on configurable policies."""
    FRESH = "fresh"              # Within primary fresh window (default: <= 24 hours)
    ACCEPTABLE = "acceptable"    # Moderately recent (default: <= 7 days)
    AGING = "aging"              # Older evidence, prices/stock may fluctuate (default: <= 30 days)
    STALE = "stale"              # Historic evidence (default: > 30 days)
    UNKNOWN_TIMESTAMP = "unknown_timestamp"  # Missing or invalid timestamp


class FreshnessPolicy(BaseModel):
    """Configurable thresholds (in hours) for classifying evidence freshness."""
    fresh_hours: float = Field(default=24.0, description="Max hours for 'fresh' status")
    acceptable_hours: float = Field(default=168.0, description="Max hours for 'acceptable' status (7 days)")
    aging_hours: float = Field(default=720.0, description="Max hours for 'aging' status (30 days)")


def parse_iso_utc(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string into a timezone-aware UTC datetime."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    cleaned = ts_str.strip()
    if not cleaned:
        return None
    try:
        # Normalize trailing Z to UTC offset for compatibility
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def evaluate_freshness(
    capture_timestamp: Optional[str],
    policy: Optional[FreshnessPolicy] = None,
    evaluated_at: Optional[datetime] = None,
) -> tuple[FreshnessClassification, Optional[float], Optional[float], Optional[float], str]:
    """Evaluate evidence age and assign a freshness tier.
    
    Returns:
        (classification, age_seconds, age_hours, age_days, explanation_note)
    
    Rule: Stale evidence indicates data age (e.g. price or stock may have shifted),
    not that the factual claims or specifications are necessarily false.
    """
    if policy is None:
        policy = FreshnessPolicy()
    
    now = evaluated_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
        
    dt = parse_iso_utc(capture_timestamp)
    if dt is None:
        return (
            FreshnessClassification.UNKNOWN_TIMESTAMP,
            None,
            None,
            None,
            "Capture timestamp was missing or unparseable. Age cannot be verified deterministically.",
        )
    
    age_seconds = max(0.0, (now - dt).total_seconds())
    age_hours = age_seconds / 3600.0
    age_days = age_seconds / 86400.0
    
    if age_hours <= policy.fresh_hours:
        classification = FreshnessClassification.FRESH
        note = f"Captured {age_hours:.1f} hours ago. Data is very fresh and highly reliable for current retail status."
    elif age_hours <= policy.acceptable_hours:
        classification = FreshnessClassification.ACCEPTABLE
        note = f"Captured {age_days:.1f} days ago. Specifications are generally stable; live pricing should be verified."
    elif age_hours <= policy.aging_hours:
        classification = FreshnessClassification.AGING
        note = f"Captured {age_days:.1f} days ago. Evidence is aging; promotional pricing or availability may have expired."
    else:
        classification = FreshnessClassification.STALE
        note = (
            f"Captured {age_days:.1f} days ago. Stale evidence indicates old observation time, "
            "not that specs are false. Direct source re-verification strongly recommended before purchase."
        )
        
    return classification, age_seconds, age_hours, age_days, note
