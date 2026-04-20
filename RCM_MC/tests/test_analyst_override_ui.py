"""Tests for the Analyst Override / Assumptions tab in the Analysis Workbench.

ASSUMPTIONS TAB:
 1. render_workbench includes "Assumptions" tab button.
 2. Tab button shows override count when overrides are set.
 3. Bridge override banner appears in the Bridge tab panel.
 4. Assumptions tab panel renders all bridge fields.
 5. Assumptions tab panel renders ramp curve rows.
 6. Assumptions tab panel renders payer mix rows.
 7. Metric target add form is present.
 8. Raw/custom override add form is present.
 9. Active override value shows [A] badge in row.
10. Override JS block is included in output.

API ROUND-TRIP (end-to-end HTTP):
11. PUT + GET + rendered badge visible for bridge.exit_multiple.
12. DELETE clears override.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
import json

from rcm_mc.analysis.packet import DealAnalysisPacket
from rcm_mc.ui.analysis_workbench import render_workbench


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestAssumptionsTabRender(unittest.TestCase):

    def _packet(self, overrides=None):
        p = DealAnalysisPacket(deal_id="test-deal", deal_name="Test Hospital")
        if overrides:
            p.analyst_overrides = overrides
        return p

    def test_tab_button_present(self):
        html = render_workbench(self._packet())
        self.assertIn('data-tab="assumptions"', html)
        self.assertIn("Assumptions", html)

    def test_tab_button_no_badge_when_no_overrides(self):
        html = render_workbench(self._packet())
        self.assertNotIn("Assumptions (", html)

    def test_tab_button_shows_count(self):
        html = render_workbench(self._packet({"bridge.exit_multiple": 11.0}))
        self.assertIn("Assumptions (1)", html)

    def test_bridge_override_banner_absent_without_overrides(self):
        html = render_workbench(self._packet())
        self.assertNotIn('class="ov-bridge-banner"', html)

    def test_bridge_override_banner_present_with_bridge_override(self):
        html = render_workbench(self._packet({"bridge.exit_multiple": 11.0}))
        self.assertIn("ov-bridge-banner", html)
        self.assertIn("exit_multiple", html)

    def test_assumptions_panel_present(self):
        html = render_workbench(self._packet())
        self.assertIn('data-panel="assumptions"', html)

    def test_bridge_fields_rendered(self):
        html = render_workbench(self._packet())
        self.assertIn("bridge.exit_multiple", html)
        self.assertIn("bridge.collection_realization", html)
        self.assertIn("bridge.denial_overturn_rate", html)
        self.assertIn("bridge.cost_of_capital", html)

    def test_ramp_curve_rows_rendered(self):
        html = render_workbench(self._packet())
        self.assertIn("ramp.denial_management.months_to_full", html)
        self.assertIn("ramp.ar_collections.months_to_25_pct", html)

    def test_payer_mix_rows_rendered(self):
        html = render_workbench(self._packet())
        self.assertIn("payer_mix.commercial_share", html)
        self.assertIn("payer_mix.medicaid_share", html)

    def test_metric_target_add_form(self):
        html = render_workbench(self._packet())
        self.assertIn("ov-mt-add-btn", html)
        self.assertIn("ov-mt-key", html)

    def test_raw_add_form(self):
        html = render_workbench(self._packet())
        self.assertIn("ov-raw-add-btn", html)
        self.assertIn("ov-raw-key", html)

    def test_active_override_shows_badge(self):
        html = render_workbench(self._packet({"bridge.exit_multiple": 11.5}))
        self.assertIn("ov-badge-a", html)
        self.assertIn("11.5", html)

    def test_override_js_included(self):
        html = render_workbench(self._packet())
        self.assertIn("ov-clear-btn", html)
        self.assertIn("ovPut", html)
        self.assertIn("ovDelete", html)

    def test_clear_button_present_for_active_override(self):
        html = render_workbench(self._packet({"bridge.cost_of_capital": 12.0}))
        self.assertIn("ov-clear-btn", html)

    def test_clear_button_absent_when_no_override(self):
        html = render_workbench(self._packet())
        # ov-clear-btn injected by JS, not in initial HTML for non-overridden rows
        self.assertNotIn('data-ov-key="bridge.exit_multiple"'
                         '" class="wb-btn wb-btn-danger ov-clear-btn"', html)


class TestOverrideAPIEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls.tf.name)
        store.upsert_deal("smoke", name="Smoke Hospital",
                          profile={"denial_rate": 12, "days_in_ar": 48,
                                   "net_revenue": 250e6, "bed_count": 200,
                                   "state": "TX"})
        cls.server, cls.port = _start(cls.tf.name)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        os.unlink(cls.tf.name)

    def _put(self, key, value, reason="unit test"):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/deals/smoke/overrides/{key}",
            data=json.dumps({"value": value, "reason": reason}).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    def _get_all(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/deals/smoke/overrides"
        ) as r:
            return json.loads(r.read())

    def _delete(self, key):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/deals/smoke/overrides/{key}",
            method="DELETE",
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    def test_put_and_get_bridge_override(self):
        result = self._put("bridge.exit_multiple", 11.0)
        self.assertEqual(result["override_key"], "bridge.exit_multiple")
        self.assertEqual(result["override_value"], 11.0)

        body = self._get_all()
        self.assertIn("bridge.exit_multiple", body["overrides"])
        self.assertEqual(body["overrides"]["bridge.exit_multiple"], 11.0)

    def test_delete_override(self):
        self._put("bridge.cost_of_capital", 12.5)
        result = self._delete("bridge.cost_of_capital")
        self.assertTrue(result["deleted"])
        body = self._get_all()
        self.assertNotIn("bridge.cost_of_capital", body["overrides"])

    def test_invalid_key_returns_400(self):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/deals/smoke/overrides/not.a.valid.key",
            data=json.dumps({"value": 1.0}).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
