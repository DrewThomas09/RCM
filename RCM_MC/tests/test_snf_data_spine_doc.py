"""Guards for the SNF / Nursing Home data-spine audit doc (PR #600).

The audit doc itself must keep its honesty discipline (Medicare/Medicaid-
certified + public-CMS scope, no commercial-revenue claim, no runtime
network) and stay the planning record for the spine. The scope-clean "no
data/loader shipped yet" guards were intentionally retired once the SNF
vertical was actually built and merged (PR #610): snf.py + the vendored
CSVs now exist by design, so asserting their absence is obsolete.
"""
from __future__ import annotations

import pathlib
import unittest

_REPO = pathlib.Path(__file__).resolve().parents[1]          # RCM_MC/
_DOC = _REPO / "docs" / "PEDESK_SNF_DATA_SPINE.md"
_ROADMAP = _REPO / "docs" / "PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md"
_DATA = _REPO / "rcm_mc" / "data"


class SnfSpineDocTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(_DOC.is_file(), "SNF data-spine doc missing")
        self.text = _DOC.read_text(encoding="utf-8")
        self.low = self.text.lower()

    def test_scope_is_medicare_medicaid_certified(self):
        self.assertIn("medicare/medicaid-certified", self.low)

    def test_no_commercial_revenue_claim(self):
        self.assertIn("not commercial revenue", self.low)
        # The penalty "fines" total must be flagged as regulatory, not income.
        self.assertIn("penalty", self.low)
        self.assertIn("not", self.low)
        self.assertTrue("not revenue" in self.low or "not facility revenue" in self.low
                        or "not commercial revenue" in self.low)

    def test_states_no_runtime_network(self):
        self.assertIn("no runtime network", self.low)

    def test_names_first_ingest_target_and_plan(self):
        # Provider Information is the named first target; the two normalized
        # files + the loader API are specified.
        self.assertIn("Provider Information", self.text)
        self.assertIn("snf_providers.csv", self.text)
        self.assertIn("snf_quality.csv", self.text)
        for fn in ("load_snf_providers", "load_snf_quality",
                   "load_snf_summary_by_state", "snf_providers_for_state",
                   "snf_provider_by_ccn"):
            self.assertIn(fn, self.text)

    def test_names_primary_keys_and_grain(self):
        self.assertIn("CCN", self.text)                      # spine PK
        self.assertIn("one row per", self.low)               # grain stated

    def test_lists_the_ui_phase_plan(self):
        for pr in ("#601", "#602", "#603"):
            self.assertIn(pr, self.text)

    def test_roadmap_links_the_spine_doc(self):
        self.assertIn("PEDESK_SNF_DATA_SPINE.md",
                      _ROADMAP.read_text(encoding="utf-8"))


class SpineWasSubsequentlyBuiltTests(unittest.TestCase):
    """The spine the doc planned has since shipped (PR #610) — confirm the
    plan and the built artifacts now agree, so the doc stays a true record."""

    def test_snf_loader_and_data_now_exist(self):
        self.assertTrue((_DATA / "snf.py").exists(),
                        "snf.py loader should exist now that #610 shipped")
        self.assertTrue((_DATA / "snf_providers.csv").exists())
        self.assertTrue((_DATA / "snf_quality.csv").exists())

    def test_built_loader_matches_the_documented_api(self):
        from rcm_mc.data import snf
        for fn in ("load_snf_providers", "load_snf_quality",
                   "load_snf_summary_by_state", "snf_providers_for_state",
                   "snf_provider_by_ccn"):
            self.assertTrue(hasattr(snf, fn), f"snf.{fn} missing")


if __name__ == "__main__":
    unittest.main()
