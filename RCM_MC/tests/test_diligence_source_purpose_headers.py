"""Data-honesty regression guard: core Diligence analyzer pages must keep a
source/purpose header (ck_source_purpose) or an explicit honesty label.

The Workbench Excellence Loop added source/purpose headers to these analyzer
pages so a deal team never mistakes a model/illustrative view for live
evidence. This test locks that in — removing the header (a silent honesty
regression) fails CI. Static source check (fast, no rendering).

See docs/reports/DATA_HONESTY_REGRESSION_GUARDS.md.
"""
from __future__ import annotations

import pathlib
import unittest

_UI = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "ui"

# Diligence analyzer pages that MUST declare their data basis via a
# ck_source_purpose header (or, for inherently-illustrative tools, an explicit
# illustrative/DATA-REQUIRED label). Each maps to its renderer module.
_REQUIRE_SOURCE_PURPOSE = {
    "payer_stress_page.py": _UI / "payer_stress_page.py",
    "hcris_xray_page.py": _UI / "hcris_xray_page.py",
    "provider_xray_page.py": _UI / "provider_xray_page.py",
    "bear_case_page.py": _UI / "bear_case_page.py",
    "target_screener_page.py": _UI / "target_screener_page.py",
    "data_public/cost_structure_page.py": _UI / "data_public" / "cost_structure_page.py",
    "data_public/debt_service_page.py": _UI / "data_public" / "debt_service_page.py",
}

_HONEST_MARKERS = (
    "ck_source_purpose",
    "ck_illustrative_note",
    "DATA REQUIRED",
    "USER DATA REQUIRED",
    "data_required_panel",
)


class DiligenceSourcePurposeGuard(unittest.TestCase):
    def test_analyzer_pages_declare_data_basis(self):
        for label, path in _REQUIRE_SOURCE_PURPOSE.items():
            self.assertTrue(path.is_file(), f"missing renderer: {label}")
            txt = path.read_text(encoding="utf-8", errors="replace")
            self.assertTrue(
                any(m in txt for m in _HONEST_MARKERS),
                f"{label} renders diligence analysis but no source/purpose "
                f"header or honesty label — a data-honesty regression. "
                f"Add ck_source_purpose(...) or an explicit illustrative / "
                f"DATA REQUIRED label.",
            )

    def test_core_pages_use_source_purpose_band(self):
        # The four live/model analyzer pages specifically use the standard band.
        for label in ("payer_stress_page.py", "hcris_xray_page.py",
                      "provider_xray_page.py", "target_screener_page.py"):
            txt = _REQUIRE_SOURCE_PURPOSE[label].read_text(
                encoding="utf-8", errors="replace")
            self.assertIn("ck_source_purpose", txt,
                          f"{label} should carry the ck_source_purpose band")


if __name__ == "__main__":
    unittest.main()
