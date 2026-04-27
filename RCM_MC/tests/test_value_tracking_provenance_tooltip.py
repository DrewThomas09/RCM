"""Test for the 4C provenance-tooltip adoption on
ui/value_tracking_page.py (campaign target 4C, loop 167).

Loop 109 wrapped each lever NAME in metric_label_link
(/metric-glossary anchor) using a name→glossary-key reverse
table. This loop wraps the per-lever ACTUAL value cell in
provenance_tooltip — partners hovering see CALCULATED
node-type cards detailing the realization-vs-frozen-plan
ratio.

The graph is built manually inside the lever-render branch
(only when summary is non-None) — one CALCULATED node per
lever at observed:<glossary_key>, source="VALUE_TRACKER".

The plan-active branch requires a frozen plan plus quarterly
lever rows in the value-tracker tables. A full fixture for
that path lives in pe.value_tracker. This test sticks to
source-grep regression guards plus the no-plan branch
render so the test is self-contained and fast.

Asserts:
  - The module imports provenance_tooltip + ProvenanceGraph
    + ProvenanceNode + NodeType.
  - The module references CALCULATED (the partner-language
    node-type label rendered for realized values).
  - The actual-value cell at line ~141 no longer renders
    as bare _fm(lev["actual"]) — it now goes through
    provenance_tooltip.
  - The no-plan branch still renders cleanly (existing
    contract from loop 51 test).
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.value_tracking_page import render_value_tracker


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "value_tracking_page.py"
)


class ValueTrackingProvenanceTooltipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _MODULE_PATH.read_text(encoding="utf-8")

    def test_module_imports_provenance_tooltip(self) -> None:
        self.assertIn(
            "from ._provenance_tooltip import provenance_tooltip",
            self.text,
        )

    def test_module_imports_graph_types(self) -> None:
        self.assertIn(
            "from ..provenance.graph import",
            self.text,
        )
        self.assertIn("ProvenanceGraph", self.text)
        self.assertIn("ProvenanceNode", self.text)
        self.assertIn("NodeType", self.text)

    def test_calculated_node_type_referenced(self) -> None:
        """The lever realization is a CALCULATED node (sum
        of quarterly actuals against the frozen plan)."""
        self.assertIn("NodeType.CALCULATED", self.text)

    def test_actual_value_no_longer_renders_bare(self) -> None:
        """Loop 167 wraps the actual-value cell. The bare
        substring `_fm(lev["actual"])` should appear inside
        the provenance_tooltip call (not as a top-level
        f-string interpolation that just emits the formatted
        money value)."""
        # Specifically check the prior bare-cell pattern is gone:
        bare = '"font-weight:600;">{_fm(lev["actual"])}</td>'
        self.assertNotIn(
            bare, self.text,
            "actual-value cell still rendering as bare "
            f'{bare!r} — Phase 4C wrap regressed',
        )
        # And the helper IS called somewhere in the module
        self.assertIn("provenance_tooltip(", self.text)

    def test_provenance_tooltip_called_with_lever_metric_key(
        self,
    ) -> None:
        """The wrap should resolve the lever name to its
        glossary key via _LEVER_NAME_TO_GLOSSARY_KEY."""
        # The wrap call references _LEVER_NAME_TO_GLOSSARY_KEY
        # in addition to the loop-109 metric_label_link call
        # so the helper count is ≥2x.
        ref_count = len(
            re.findall(r"_LEVER_NAME_TO_GLOSSARY_KEY", self.text)
        )
        self.assertGreaterEqual(
            ref_count, 3,
            f"_LEVER_NAME_TO_GLOSSARY_KEY should appear ≥3x "
            f"(builder + label link + value tooltip); "
            f"found {ref_count}",
        )

    def test_no_plan_branch_still_renders_cleanly(self) -> None:
        """Existing contract from loop 51 test: a fresh
        PortfolioStore-init DB has no frozen plan; the page
        renders the no-plan branch without raising even with
        the new 4C wiring above the lever-rendering loop."""
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            PortfolioStore(db)
            out = render_value_tracker("010001", db)
            self.assertIn("No Value Creation Plan", out)


if __name__ == "__main__":
    unittest.main()
