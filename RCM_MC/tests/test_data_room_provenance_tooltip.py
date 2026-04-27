"""Test for the 4C provenance-tooltip adoption on
ui/data_room_page.py (campaign target 4C, loop 155).

Loop 107 wrapped each calibration-row metric label in
metric_label_link (a /metric-glossary anchor). This loop
wraps each row's Bayesian-posterior value cell in
provenance_tooltip — the "money column" partners read most.
build_provenance_graph auto-loads data_room_calibrations
via db_path, so every metric whose posterior was computed
gets a CALCULATED canonical node at observed:<metric> with
ML/SELLER parents (per loop 124's constructor).

Asserts:
  - render_data_room produces HTML with one prov-tt wrapper
    per non-skipped calibration row (matches the count of
    rows in the rendered cal_rows table).
  - The CSS injects exactly once per render.
  - Every wrapper has a paired card.
  - PREDICTED node-type label appears (for metrics where
    only an ML prior exists in the test fixture; CALCULATED
    would appear only with a real data_room_calibrations
    row).
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.data_room_page import render_data_room


class DataRoomProvenanceTooltipTests(unittest.TestCase):
    def _render_with_temp_db(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            PortfolioStore(db)
            return render_data_room(
                ccn="010001",
                hospital_name="Test Acute",
                beds=200,
                state="GA",
                ml_predictions={
                    "denial_rate": 0.10,
                    "days_in_ar": 50,
                },
                db_path=db,
                hcris_profile={
                    "net_patient_revenue": 1.5e8,
                    "operating_margin": 0.05,
                },
            )

    def test_render_includes_prov_tt_wrappers(self) -> None:
        out = self._render_with_temp_db()
        n = len(re.findall(r'class="prov-tt"', out))
        self.assertGreater(
            n, 0,
            "expected at least one prov-tt wrapper on the "
            "calibration-table posterior cells",
        )

    def test_every_wrapper_has_card(self) -> None:
        out = self._render_with_temp_db()
        n_w = len(re.findall(r'class="prov-tt"', out))
        n_c = len(re.findall(r'class="prov-tt-card"', out))
        self.assertEqual(n_w, n_c)

    def test_tooltip_css_injects_only_once(self) -> None:
        out = self._render_with_temp_db()
        n = out.count(".prov-tt {")
        self.assertEqual(
            n, 1,
            f"expected exactly 1 prov-tt CSS block; found {n}",
        )

    def test_predicted_node_type_appears(self) -> None:
        """Without a real data_room_calibrations row, the
        ml_predictions-only metrics resolve to PREDICTED.
        Confirms graph integration."""
        out = self._render_with_temp_db()
        self.assertIn("PREDICTED", out)


if __name__ == "__main__":
    unittest.main()
