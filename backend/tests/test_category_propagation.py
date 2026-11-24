"""Regression tests for category propagation — never default to 'laptop'."""

import pytest

from app.orchestrator.category import (
    ProductCategory,
    classify_query_category,
    normalize_category,
)
from app.orchestrator.investigation_engine import InvestigationEngine
from app.orchestrator.investigation_state import InvestigationStateStore


# ---------------------------------------------------------------------------
# Unit tests: normalize_category
# ---------------------------------------------------------------------------


class TestNormalizeCategory:
    def test_none_returns_none(self):
        assert normalize_category(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_category("") is None

    def test_whitespace_returns_none(self):
        assert normalize_category("   ") is None

    def test_auto_returns_none(self):
        assert normalize_category("auto") is None

    def test_unspecified_returns_none(self):
        assert normalize_category("unspecified") is None

    def test_laptop_passthrough(self):
        assert normalize_category("laptop") == "laptop"

    def test_smartphone_passthrough(self):
        assert normalize_category("smartphone") == "smartphone"

    def test_case_insensitive(self):
        assert normalize_category("SMARTPHONE") == "smartphone"

    def test_alias_phone(self):
        assert normalize_category("phone") == "smartphone"

    def test_alias_mobile(self):
        assert normalize_category("mobile") == "smartphone"

    def test_alias_notebook(self):
        assert normalize_category("notebook") == "laptop"

    def test_alias_earbuds(self):
        assert normalize_category("earbuds") == "headphones"

    def test_unknown_category_passthrough(self):
        assert normalize_category("smartwatch") == "smartwatch"


# ---------------------------------------------------------------------------
# Unit tests: classify_query_category
# ---------------------------------------------------------------------------


class TestClassifyQueryCategory:
    def test_iphone_16_smartphone(self):
        assert classify_query_category("iPhone 16") == "smartphone"

    def test_iphone_16_pro_max_smartphone(self):
        assert classify_query_category("iPhone 16 Pro Max") == "smartphone"

    def test_oneplus_13_smartphone(self):
        assert classify_query_category("OnePlus 13") == "smartphone"

    def test_galaxy_s25_smartphone(self):
        assert classify_query_category("Samsung Galaxy S25") == "smartphone"

    def test_pixel_9_smartphone(self):
        assert classify_query_category("Pixel 9 Pro") == "smartphone"

    def test_redmi_note_smartphone(self):
        assert classify_query_category("Redmi Note 14 Pro") == "smartphone"

    def test_poco_smartphone(self):
        assert classify_query_category("POCO X7") == "smartphone"

    def test_realme_smartphone(self):
        assert classify_query_category("Realme GT 7 Pro") == "smartphone"

    def test_iqoo_smartphone(self):
        assert classify_query_category("iQOO Neo 10") == "smartphone"

    def test_dell_xps_15_laptop(self):
        assert classify_query_category("Dell XPS 15") == "laptop"

    def test_macbook_air_m3_laptop(self):
        assert classify_query_category("MacBook Air M3") == "laptop"

    def test_thinkpad_laptop(self):
        assert classify_query_category("ThinkPad X1 Carbon") == "laptop"

    def test_chromebook_laptop(self):
        assert classify_query_category("HP Chromebook 14") == "laptop"

    def test_sony_wh1000xm5_headphones(self):
        assert classify_query_category("Sony WH-1000XM5") == "headphones"

    def test_airpods_headphones(self):
        assert classify_query_category("AirPods Pro 2") == "headphones"

    def test_ipad_tablet(self):
        assert classify_query_category("iPad Pro 13") == "tablet"

    def test_galaxy_tab_tablet(self):
        assert classify_query_category("Samsung Galaxy Tab S10") == "tablet"

    def test_dslr_camera(self):
        assert classify_query_category("Canon EOS R5 mirrorless") == "camera"

    def test_monitor(self):
        assert classify_query_category("LG 27GP850-B monitor") == "monitor"

    def test_ambiguous_returns_none(self):
        assert classify_query_category("best deals today") is None

    def test_empty_returns_none(self):
        assert classify_query_category("") is None

    def test_none_returns_none(self):
        assert classify_query_category(None) is None


# ---------------------------------------------------------------------------
# Integration tests: InvestigationEngine.initialize_investigation
# ---------------------------------------------------------------------------


class TestCategoryPropagationEngine:
    """Ensure the investigation engine never silently defaults to 'laptop'."""

    def _make_engine(self) -> InvestigationEngine:
        return InvestigationEngine(state_store=InvestigationStateStore())

    def test_explicit_smartphone_stays_smartphone(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="iPhone 16", category="smartphone")
        assert rec.category == "smartphone"

    def test_explicit_laptop_stays_laptop(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="Dell XPS 15", category="laptop")
        assert rec.category == "laptop"

    def test_explicit_headphones_for_phone_query_stays_headphones(self):
        """Explicit user category takes precedence even if it conflicts with query."""
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="iPhone 16", category="headphones")
        assert rec.category == "headphones"

    def test_oneplus_13_with_smartphone_stays_smartphone(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="OnePlus 13", category="smartphone")
        assert rec.category == "smartphone"

    def test_missing_category_inferred_iphone(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="iPhone 16")
        assert rec.category == "smartphone"

    def test_missing_category_inferred_macbook(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="MacBook Air M3")
        assert rec.category == "laptop"

    def test_missing_category_inferred_headphones(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="Sony WH-1000XM5")
        assert rec.category == "headphones"

    def test_missing_category_ambiguous_returns_none(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="best deals today")
        assert rec.category is None

    def test_empty_category_string_does_not_default_to_laptop(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="iPhone 16", category="")
        # Empty string is normalized to None → query inference → smartphone
        assert rec.category == "smartphone"

    def test_auto_category_does_not_default_to_laptop(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="Dell XPS 15", category="auto")
        # "auto" is normalized to None → query inference → laptop
        assert rec.category == "laptop"

    def test_category_never_defaults_to_laptop_for_unknown_query(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="xyz unknown product")
        # Must NOT be "laptop" — should be None for ambiguous
        assert rec.category != "laptop"
        assert rec.category is None

    def test_alias_phone_resolves_to_smartphone(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="OnePlus 13", category="phone")
        assert rec.category == "smartphone"

    def test_alias_mobile_resolves_to_smartphone(self):
        engine = self._make_engine()
        rec = engine.initialize_investigation(query="OnePlus 13", category="mobile")
        assert rec.category == "smartphone"
