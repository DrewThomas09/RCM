"""Tests for PE JSON → HTML renderers (UI-6)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.ui.json_to_html import (
    render_pe_bridge,
    render_pe_covenant,
    render_pe_hold_grid,
    render_pe_returns,
    wrap_pe_artifacts_in_folder,
)


_BRIDGE_PAYLOAD = {
    "entry_ebitda": 50e6, "exit_ebitda": 66e6,
    "entry_multiple": 9.0, "exit_multiple": 10.0,
    "hold_years": 5, "rcm_uplift": 8e6,
    "entry_ev": 450e6, "exit_ev": 660e6,
    "total_value_created": 210e6,
    "components": [
        {"step": "Entry EV",            "value": 450e6, "share_of_creation": None, "note": "9x × 50M"},
        {"step": "Organic EBITDA",      "value": 72e6,  "share_of_creation": 0.34, "note": "3%/yr × 5y"},
        {"step": "RCM uplift",          "value": 72e6,  "share_of_creation": 0.34, "note": "× 9x entry"},
        {"step": "Multiple expansion",  "value": 66e6,  "share_of_creation": 0.32, "note": "Δ+1x"},
        {"step": "Exit EV",             "value": 660e6, "share_of_creation": None, "note": "10x × 66M"},
    ],
}

_RETURNS_PAYLOAD = {
    "entry_equity": 180e6, "exit_proceeds": 459e6,
    "hold_years": 5, "moic": 2.55, "irr": 0.206,
    "total_distributions": 459e6,
}

_COVENANT_PAYLOAD = {
    "ebitda": 50e6, "debt": 270e6,
    "covenant_max_leverage": 6.5, "actual_leverage": 5.4,
    "covenant_headroom_turns": 1.1, "ebitda_cushion_pct": 0.17,
    "covenant_trips_at_ebitda": 41.5e6, "interest_coverage": 2.3,
}


class TestRenderPEBridge(unittest.TestCase):
    def test_includes_kpi_cards(self):
        html = render_pe_bridge(_BRIDGE_PAYLOAD)
        self.assertIn("Entry EV", html)
        self.assertIn("Exit EV", html)
        self.assertIn("Value Created", html)
        self.assertIn("Hold Period", html)

    def test_renders_all_components(self):
        html = render_pe_bridge(_BRIDGE_PAYLOAD)
        for step in ("Entry EV", "Organic EBITDA", "RCM uplift",
                     "Multiple expansion", "Exit EV"):
            self.assertIn(step, html)

    def test_money_formatted(self):
        html = render_pe_bridge(_BRIDGE_PAYLOAD)
        # $450M entry EV rendered
        self.assertIn("$450M", html)
        # $210M value created
        self.assertIn("$210M", html)

    def test_back_link_present(self):
        html = render_pe_bridge(_BRIDGE_PAYLOAD)
        self.assertIn("Back to index", html)

    def test_bridge_table_has_caption_and_column_scope(self):
        html = render_pe_bridge(_BRIDGE_PAYLOAD)
        self.assertIn('<caption class="sr-only">Value creation bridge components', html)
        self.assertIn('<th scope="col">Step</th>', html)


class TestRenderPEReturns(unittest.TestCase):
    def test_moic_and_irr_rendered(self):
        html = render_pe_returns(_RETURNS_PAYLOAD)
        self.assertIn("2.55x", html)
        self.assertIn("20.6%", html)

    def test_color_threshold_green_for_high_moic(self):
        """MOIC ≥2.5x → green."""
        html = render_pe_returns({**_RETURNS_PAYLOAD, "moic": 3.0, "irr": 0.30})
        # Both color hex codes for green appear
        self.assertIn("var(--green)", html)

    def test_color_threshold_red_for_low_moic(self):
        html = render_pe_returns({**_RETURNS_PAYLOAD, "moic": 1.5, "irr": 0.05})
        self.assertIn("var(--red)", html)

    def test_handles_missing_moic_gracefully(self):
        html = render_pe_returns({"hold_years": 5})
        self.assertIn("—", html)  # dash placeholder


class TestRenderPECovenant(unittest.TestCase):
    def test_safe_status_badge(self):
        html = render_pe_covenant(_COVENANT_PAYLOAD)
        self.assertIn("SAFE", html)
        self.assertIn("badge-green", html)

    def test_tripped_status_badge(self):
        payload = {**_COVENANT_PAYLOAD, "covenant_headroom_turns": -0.5,
                   "actual_leverage": 7.0}
        html = render_pe_covenant(payload)
        self.assertIn("TRIPPED", html)
        self.assertIn("badge-red", html)

    def test_tight_status_badge(self):
        payload = {**_COVENANT_PAYLOAD, "covenant_headroom_turns": 0.3}
        html = render_pe_covenant(payload)
        self.assertIn("TIGHT", html)
        self.assertIn("badge-amber", html)

    def test_detail_table_has_all_fields(self):
        html = render_pe_covenant(_COVENANT_PAYLOAD)
        for label in ("EBITDA", "Total debt", "Trips at EBITDA",
                      "Interest coverage"):
            self.assertIn(label, html)

    def test_detail_table_uses_row_headers(self):
        html = render_pe_covenant(_COVENANT_PAYLOAD)
        self.assertIn('<caption class="sr-only">Covenant detail values', html)
        self.assertIn('<th scope="row">EBITDA</th>', html)


class TestRenderPEHoldGrid(unittest.TestCase):
    def test_pivot_layout(self):
        rows = [
            {"hold_years": 3, "exit_multiple": 9.0, "moic": 1.65, "irr": 0.18},
            {"hold_years": 3, "exit_multiple": 10.0, "moic": 1.98, "irr": 0.26},
            {"hold_years": 5, "exit_multiple": 9.0, "moic": 2.08, "irr": 0.16},
            {"hold_years": 5, "exit_multiple": 10.0, "moic": 2.44, "irr": 0.20},
        ]
        html = render_pe_hold_grid(rows)
        # Column headers for each multiple
        self.assertIn("9.0x", html)
        self.assertIn("10.0x", html)
        # Row headers for each hold
        self.assertIn("3y", html)
        self.assertIn("5y", html)
        # IRR + MOIC values cell content
        self.assertIn("+18%", html)
        self.assertIn("1.65x", html)

    def test_underwater_flag_shown(self):
        rows = [{"hold_years": 5, "exit_multiple": 8.0, "moic": 0.0, "irr": -1.0,
                 "underwater": True}]
        html = render_pe_hold_grid(rows)
        self.assertIn("⚠", html)

    def test_empty_rows_renders_placeholder(self):
        html = render_pe_hold_grid([])
        self.assertIn("No data", html)

    def test_hold_grid_uses_table_scope_and_caption(self):
        rows = [{"hold_years": 5, "exit_multiple": 8.0, "moic": 1.2, "irr": 0.08}]
        html = render_pe_hold_grid(rows)
        self.assertIn('<caption class="sr-only">Sensitivity grid by hold period', html)
        self.assertIn('<th scope="col">Hold</th>', html)
        self.assertIn('<th scope="row"><strong>5y</strong></th>', html)


class TestWrapPEArtifactsInFolder(unittest.TestCase):
    def test_writes_html_for_each_known_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "pe_bridge.json"), "w") as f:
                json.dump(_BRIDGE_PAYLOAD, f)
            with open(os.path.join(tmp, "pe_returns.json"), "w") as f:
                json.dump(_RETURNS_PAYLOAD, f)
            with open(os.path.join(tmp, "pe_covenant.json"), "w") as f:
                json.dump(_COVENANT_PAYLOAD, f)
            written = wrap_pe_artifacts_in_folder(tmp)
            names = sorted(os.path.basename(p) for p in written)
            self.assertEqual(names, [
                "pe_bridge.html", "pe_covenant.html", "pe_returns.html",
            ])

    def test_unknown_json_not_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "arbitrary.json"), "w") as f:
                json.dump({"data": "whatever"}, f)
            self.assertEqual(wrap_pe_artifacts_in_folder(tmp), [])

    def test_corrupt_json_silently_skipped(self):
        """A broken file shouldn't abort the batch."""
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "pe_bridge.json"), "w") as f:
                f.write("{not json")
            with open(os.path.join(tmp, "pe_returns.json"), "w") as f:
                json.dump(_RETURNS_PAYLOAD, f)
            written = wrap_pe_artifacts_in_folder(tmp)
            names = sorted(os.path.basename(p) for p in written)
            self.assertEqual(names, ["pe_returns.html"])

    def test_existing_html_not_clobbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "pe_bridge.json"), "w") as f:
                json.dump(_BRIDGE_PAYLOAD, f)
            with open(os.path.join(tmp, "pe_bridge.html"), "w") as f:
                f.write("<!-- hand-written -->")
            wrap_pe_artifacts_in_folder(tmp)
            with open(os.path.join(tmp, "pe_bridge.html")) as f:
                self.assertIn("hand-written", f.read())

    def test_nonexistent_folder_returns_empty(self):
        self.assertEqual(wrap_pe_artifacts_in_folder("/nonexistent"), [])
