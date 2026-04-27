"""Test for the 4C provenance-tooltip adoption on
ui/competitive_intel_page.py (campaign target 4C, loop 143).

Loop 112 wrapped each metric LABEL in metric_label_link (a
/metric-glossary anchor). This loop wraps each metric VALUE
in provenance_tooltip — the same per-row label that's
already a glossary link now also has a hover-card showing
where the number came from. Combined coverage on this page:
label = anchor link to definition, value = tooltip card with
provenance.

Asserts:
  - render_competitive_intel produces HTML with multiple
    `class="prov-tt"` wrappers (one per non-skipped row in
    _METRIC_DEFS).
  - The tooltip CSS injects only ONCE inside the per-row
    loop (the inject_css=False optimization works).
  - Every prov-tt wrapper has a corresponding card body
    (`prov-tt-card`).
  - The test fixture confirms a SOURCE node-type label
    appears (HCRIS-derived metrics → SOURCE).
"""
from __future__ import annotations

import re
import unittest

import pandas as pd

from rcm_mc.ui.competitive_intel_page import render_competitive_intel


def _build_hcris_fixture() -> pd.DataFrame:
    """A 12-row peer set so size-matched / state filters
    produce a non-empty cohort for the percentile table."""
    base = {
        "ccn": "010001", "name": "Test Acute", "state": "GA",
        "beds": 200,
        "net_patient_revenue": 1.5e8,
        "operating_expenses": 1.4e8,
        "operating_margin": 0.067,
        "net_income": 1.0e7,
        "medicare_day_pct": 0.45,
        "medicaid_day_pct": 0.20,
        "occupancy_rate": 0.65,
        "total_patient_days": 47000,
        "commercial_pct": 0.35,
        "payer_diversity": 0.7,
        "expense_per_bed": 7e5,
        "revenue_per_bed": 7.5e5,
        "net_to_gross_ratio": 0.34,
    }
    peer = dict(base)
    peer.update({
        "ccn": "010002", "name": "Peer A",
        "beds": 220, "operating_margin": 0.094,
        "expense_per_bed": 6.6e5, "revenue_per_bed": 7.3e5,
    })
    return pd.DataFrame([base] + [peer] * 11)


class CompetitiveIntelProvenanceTooltipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = _build_hcris_fixture()

    def test_render_includes_multiple_prov_tt_wrappers(self) -> None:
        """At least 8 metric rows in _METRIC_DEFS produce a
        non-zero value and thus a tooltip-wrapped value cell."""
        out = render_competitive_intel("010001", self.df)
        n = len(re.findall(r'class="prov-tt"', out))
        self.assertGreaterEqual(
            n, 8,
            f"expected ≥8 prov-tt wrappers (one per non-zero "
            f"metric row); found {n}",
        )

    def test_tooltip_css_injects_only_once_per_render(self) -> None:
        """The inject_css=False optimization should keep the
        prov-tt <style> block from being duplicated 12 times.
        Other modules (e.g. metric_glossary tooltip if used
        elsewhere) may emit their own <style> blocks; here we
        check the prov-tt-specific class name appears in
        exactly one <style> block."""
        out = render_competitive_intel("010001", self.df)
        # Count <style> blocks that contain the prov-tt class
        style_blocks = re.findall(
            r"<style>(.+?)</style>", out, flags=re.DOTALL,
        )
        prov_styles = [s for s in style_blocks if ".prov-tt" in s]
        self.assertEqual(
            len(prov_styles), 1,
            f"expected exactly 1 <style> block to contain the "
            f".prov-tt CSS; found {len(prov_styles)}",
        )

    def test_every_wrapper_has_card(self) -> None:
        """Each prov-tt wrapper should have a paired
        prov-tt-card span."""
        out = render_competitive_intel("010001", self.df)
        n_wrappers = len(re.findall(r'class="prov-tt"', out))
        n_cards = len(re.findall(r'class="prov-tt-card"', out))
        self.assertEqual(n_wrappers, n_cards)

    def test_source_node_type_appears(self) -> None:
        """HCRIS-derived metric values should emit a SOURCE
        node-type tag in their card."""
        out = render_competitive_intel("010001", self.df)
        self.assertIn("SOURCE", out)


if __name__ == "__main__":
    unittest.main()
