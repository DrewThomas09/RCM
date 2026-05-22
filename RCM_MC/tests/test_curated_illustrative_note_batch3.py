"""Curated-labeling sweep, batch 3 — the remaining illustrative trackers.

Applies the honest ck_illustrative_note() marker to data_public tracker
pages confirmed curated per docs/PEDESK_UNDERSTANDING/08 (hardcoded
demo data, NOT [corpus]/[CMS]/[calc]). Each page is rendered and the
marker asserted; a negative guard confirms genuinely-live pages are
never labeled.
"""
from __future__ import annotations

import importlib
import unittest

_BATCH3A = [
    "medicaid_unwinding", "telehealth_econ", "tax_credits", "nsa_tracker",
    "payer_concentration", "payer_contracts", "ma_contracts",
    "ma_star_tracker", "tracker_340b", "drug_shortage", "gpo_supply_tracker",
    "cyber_risk", "health_equity", "esg_impact", "litigation_tracker",
    "rw_insurance", "fraud_detection", "key_person", "physician_labor",
    "phys_comp_plan", "mgmt_comp",
]


def _render_any(module_name: str) -> str:
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{module_name}_page")
    for fn in dir(mod):
        if fn.startswith("render_"):
            try:
                out = getattr(mod, fn)({})
            except Exception:
                continue
            if isinstance(out, str) and "ck-page" in out or (
                isinstance(out, str) and "<" in out
            ):
                return out
    raise AssertionError(f"no renderable function found for {module_name}")


class CuratedBatch3Tests(unittest.TestCase):
    def test_each_curated_page_carries_marker(self):
        for name in _BATCH3A:
            html = _render_any(name)
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)

    def test_live_pages_never_labeled(self):
        # Genuinely live / calc pages must never carry the marker.
        from rcm_mc.ui.data_public.base_rates_page import render_base_rates
        from rcm_mc.ui.data_public.scenario_mc_page import render_scenario_mc
        self.assertNotIn("ck-illus-note", render_base_rates())
        self.assertNotIn("ck-illus-note", render_scenario_mc({}))


if __name__ == "__main__":
    unittest.main()
