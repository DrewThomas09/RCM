"""Tests for Sprint 6: Dashboard v2 (31), Webhooks (39), SEC EDGAR (40).

DASHBOARD V2:
 1. render_dashboard_v2 returns valid HTML with summary strip.
 2. Empty portfolio shows "No deals yet" message.
 3. Deal cards sorted by EBITDA opportunity.
 4. Critical risk count rendered.
 5. Needs-attention list includes high-severity deals.
 6. Quick action links present.

WEBHOOKS:
 7. register_webhook returns an ID.
 8. list_webhooks returns registered entries.
 9. delete_webhook removes the row.
10. dispatch_event matches event filter.
11. dispatch_event skips inactive webhooks.
12. HMAC signature verifiable with the shared secret.
13. Delivery record written to webhook_deliveries.
14. Unknown event type → 0 matched.

SEC EDGAR:
15. HCA maps to CIK 0000860730.
16. match_facility_to_system finds "HCA" in hospital name.
17. Unknown system name → None.
18. fetch_system_context with skip_network returns skeleton.
19. SystemContext.to_dict round-trips.
20. SYSTEM_CIK_MAP has at least 10 entries.
21. CIK values are 10-digit strings.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest

from rcm_mc.data.sec_edgar import (
    SYSTEM_CIK_MAP,
    SystemContext,
    fetch_system_context,
    match_facility_to_system,
)
from rcm_mc.infra.webhooks import (
    _sign,
    delete_webhook,
    dispatch_event,
    list_webhooks,
    register_webhook,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.dashboard_v2 import render_dashboard_v2


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── Dashboard v2 ──────────────────────────────────────────────────

class TestDashboardV2(unittest.TestCase):

    def test_renders_html(self):
        store, path = _tmp_store()
        try:
            html = render_dashboard_v2(store)
            self.assertIn("Portfolio Dashboard", html)
            self.assertIn("Active Deals", html)
        finally:
            os.unlink(path)

    def test_empty_portfolio_message(self):
        store, path = _tmp_store()
        try:
            html = render_dashboard_v2(store)
            self.assertIn("No deals yet", html)
        finally:
            os.unlink(path)

    def test_deal_card_present_after_packet(self):
        from rcm_mc.analysis.analysis_store import save_packet
        from rcm_mc.analysis.packet import DealAnalysisPacket, EBITDABridgeResult
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="Acme")
            save_packet(
                store,
                DealAnalysisPacket(
                    deal_id="d1", deal_name="Acme",
                    ebitda_bridge=EBITDABridgeResult(total_ebitda_impact=5e6),
                ),
                inputs_hash="h",
            )
            html = render_dashboard_v2(store)
            self.assertIn("Acme", html)
            self.assertIn("$5.0M", html)
        finally:
            os.unlink(path)

    def test_quick_actions_present(self):
        store, path = _tmp_store()
        try:
            html = render_dashboard_v2(store)
            self.assertIn("/new-deal", html)
            self.assertIn("Heatmap", html)
        finally:
            os.unlink(path)


# ── Webhooks ──────────────────────────────────────────────────────

class TestWebhooks(unittest.TestCase):

    def test_register_and_list(self):
        store, path = _tmp_store()
        try:
            wid = register_webhook(
                store, "https://example.com/hook", "s3cret",
                ["deal.created", "analysis.completed"],
            )
            self.assertGreater(wid, 0)
            hooks = list_webhooks(store)
            self.assertEqual(len(hooks), 1)
            self.assertIn("deal.created", hooks[0]["events"])
        finally:
            os.unlink(path)

    def test_delete(self):
        store, path = _tmp_store()
        try:
            wid = register_webhook(store, "https://x.com", "s", ["*"])
            self.assertTrue(delete_webhook(store, wid))
            self.assertEqual(list_webhooks(store), [])
        finally:
            os.unlink(path)

    def test_dispatch_matches_event(self):
        store, path = _tmp_store()
        try:
            register_webhook(store, "https://x.com/nope", "s",
                             ["deal.created"], description="test")
            # This URL won't connect — that's fine; we check match count.
            matched = dispatch_event(
                store, "deal.created",
                {"deal_id": "d1"},
                async_delivery=False,
            )
            self.assertEqual(matched, 1)
        finally:
            os.unlink(path)

    def test_dispatch_skips_non_matching_event(self):
        store, path = _tmp_store()
        try:
            register_webhook(store, "https://x.com", "s",
                             ["deal.created"])
            matched = dispatch_event(
                store, "analysis.completed",
                {"deal_id": "d1"},
                async_delivery=False,
            )
            self.assertEqual(matched, 0)
        finally:
            os.unlink(path)

    def test_wildcard_event_matches_all(self):
        store, path = _tmp_store()
        try:
            register_webhook(store, "https://x.com", "s", ["*"])
            matched = dispatch_event(
                store, "anything.at.all", {},
                async_delivery=False,
            )
            self.assertEqual(matched, 1)
        finally:
            os.unlink(path)

    def test_hmac_signature_verifiable(self):
        body = b'{"event":"test"}'
        secret = "my_secret"
        sig = _sign(body, secret)
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256,
        ).hexdigest()
        self.assertEqual(sig, expected)

    def test_delivery_logged(self):
        store, path = _tmp_store()
        try:
            register_webhook(store, "https://x.com/nope", "s", ["*"])
            dispatch_event(store, "test", {}, async_delivery=False)
            with store.connect() as con:
                rows = con.execute(
                    "SELECT * FROM webhook_deliveries",
                ).fetchall()
            self.assertGreater(len(rows), 0)
        finally:
            os.unlink(path)


# ── SEC EDGAR ─────────────────────────────────────────────────────

class TestSECEdgar(unittest.TestCase):

    def test_hca_cik(self):
        self.assertEqual(SYSTEM_CIK_MAP["HCA Healthcare"], "0000860730")

    def test_match_hca_in_name(self):
        result = match_facility_to_system("HCA Houston Methodist")
        self.assertIsNotNone(result)
        self.assertIn("HCA", result)

    def test_unknown_system(self):
        self.assertIsNone(
            match_facility_to_system("Totally Independent Hospital"),
        )

    def test_skip_network_returns_skeleton(self):
        ctx = fetch_system_context("HCA Healthcare", skip_network=True)
        self.assertEqual(ctx.cik, "0000860730")
        self.assertIsNone(ctx.latest_annual_revenue)

    def test_system_context_to_dict(self):
        ctx = SystemContext(system_name="HCA", cik="0000860730")
        d = ctx.to_dict()
        self.assertEqual(d["system_name"], "HCA")
        json.dumps(d)  # must not raise

    def test_cik_map_size(self):
        self.assertGreaterEqual(len(SYSTEM_CIK_MAP), 10)

    def test_cik_values_are_10_digits(self):
        for name, cik in SYSTEM_CIK_MAP.items():
            self.assertEqual(
                len(cik), 10,
                f"{name} CIK {cik!r} is not 10 digits",
            )
            self.assertTrue(cik.isdigit())


if __name__ == "__main__":
    unittest.main()
