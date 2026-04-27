"""Test for the 4C provenance-tooltip adoption on
ui/ebitda_bridge_page.py (campaign target 4C, loop 149).

Loop 106 wrapped each lever NAME in metric_label_link (a
/metric-glossary anchor). This loop wraps each lever's
CURRENT VALUE (denial rate %, A/R days, etc.) in
provenance_tooltip — so partners hovering the value see
the node type (SOURCE if HCRIS-derived, OBSERVED if from
the data room, PREDICTED if a model-default lever value)
and the explanation.

The bridge's lever metric_keys are the bridge's short
forms (denial_rate, days_in_ar, ..., cmi). The cmi → case_
mix_index alias from loop 106 (_LEVER_METRIC_TO_GLOSSARY)
is reused here so both the 4A label and the 4C value
tooltip resolve to the same canonical glossary key.

Asserts:
  - render_ebitda_bridge produces HTML with one prov-tt
    wrapper per lever (6 levers).
  - Every wrapper has a paired prov-tt-card.
  - The CSS injects exactly once per render (the inject_css
    flag works inside the per-lever loop).
  - PREDICTED node-type label appears (lever defaults are
    classified as PREDICTED when not from the data room).
"""
from __future__ import annotations

import re
import unittest

import pandas as pd

from rcm_mc.ui.ebitda_bridge_page import render_ebitda_bridge


def _build_hcris_fixture() -> pd.DataFrame:
    """Single-hospital fixture with enough HCRIS columns to
    drive the bridge through to its detail-table render."""
    return pd.DataFrame([{
        "ccn": "010001",
        "name": "Test Acute General",
        "state": "GA",
        "beds": 200,
        "net_patient_revenue": 1.5e8,
        "operating_expenses": 1.4e8,
        "medicare_day_pct": 0.45,
        "medicaid_day_pct": 0.20,
    }])


class EbitdaBridgeProvenanceTooltipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = _build_hcris_fixture()

    def test_render_includes_six_prov_tt_wrappers(self) -> None:
        """Bridge has 6 levers; each lever-current cell gets
        a tooltip → 6 prov-tt wrappers in the rendered HTML."""
        out = render_ebitda_bridge("010001", self.df)
        n = len(re.findall(r'class="prov-tt"', out))
        self.assertEqual(
            n, 6,
            f"expected 6 prov-tt wrappers (one per lever); "
            f"found {n}",
        )

    def test_every_wrapper_has_card(self) -> None:
        out = render_ebitda_bridge("010001", self.df)
        n_w = len(re.findall(r'class="prov-tt"', out))
        n_c = len(re.findall(r'class="prov-tt-card"', out))
        self.assertEqual(n_w, n_c)

    def test_tooltip_css_injects_only_once_per_render(self) -> None:
        """The per-lever loop should inject the prov-tt
        <style> block exactly once (first iteration); the
        remaining 5 iterations pass inject_css=False."""
        out = render_ebitda_bridge("010001", self.df)
        # Count occurrences of the .prov-tt class definition
        n_css = out.count(".prov-tt {")
        self.assertEqual(
            n_css, 1,
            f"expected exactly 1 prov-tt CSS block; "
            f"found {n_css} (per-lever inject_css guard regressed)",
        )

    def test_predicted_node_type_appears(self) -> None:
        """Without a db_path the bridge has no seller data, so
        every lever-current value is classified as MODEL_DEFAULT
        → PREDICTED node type. Confirms the manually-added
        per-lever nodes flow into explain_for_ui's output."""
        out = render_ebitda_bridge("010001", self.df)
        self.assertIn("PREDICTED", out)


if __name__ == "__main__":
    unittest.main()
