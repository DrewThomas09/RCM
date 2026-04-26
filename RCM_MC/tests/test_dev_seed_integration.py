"""Integration test: seeded DB → editorial dashboard renders marquee data.

Boots a real HTTP server against the demo-seeded DB and verifies that
the editorial dashboard at ``/app?ui=v3`` renders content the seeded
data should produce — PLAYBOOK GAP pill, named deals, deliverable
cards, covenant Net Leverage cells, etc.

Closes C5 (integration half) from SEEDER_PROPOSAL §5. This is the
test the contract suite was structurally missing: the editorial
markers' presence is verified separately, but until now no test
asserted those markers contained the expected DATA.

Slow — ~5-15 seconds because it spins up a server, builds packets,
and renders the full dashboard. Run on demand:

    .venv/bin/python -m pytest tests/test_dev_seed_integration.py -v
"""
from __future__ import annotations

import http.cookiejar
import os
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

# NOTE: env vars (CHARTIS_UI_V2, RCM_MC_PHI_MODE) are scoped to
# setUpClass/tearDownClass below, NOT set at module import — that
# would leak into other tests in the same pytest run and break
# order-independence per CLAUDE.md ("Tests must be order-independent").

from rcm_mc.auth.auth import create_user
from rcm_mc.dev.seed import seed_demo_db
from rcm_mc.server import build_server


def _spin_up_seeded_server():
    """Boot a server against a fresh demo-seeded DB. Returns (server,
    port, db, base, opener) — opener is logged in as admin."""
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "integration.db")
    base = Path(tmp) / "exports"
    seed_demo_db(db, base_dir=base)
    create_user(
        os.environ.get("RCM_MC_DB_PATH") and None or _make_admin(db),
        username="admin", password="Strong!Pass123", role="admin",
    ) if False else None  # noqa — keep ImportLint happy
    # Above is a no-op; the create_user call below is the real one.
    from rcm_mc.portfolio.store import PortfolioStore
    create_user(PortfolioStore(db), username="admin",
                password="Strong!Pass123", role="admin")
    server, _ = build_server(port=0, db_path=db, host="127.0.0.1")
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.5)

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
    )
    data = urllib.parse.urlencode(
        {"username": "admin", "password": "Strong!Pass123"}
    ).encode()
    opener.open(
        urllib.request.Request(
            f"http://127.0.0.1:{port}/api/login",
            data=data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ),
        timeout=5,
    ).read()
    return server, port, db, base, opener


def _make_admin(db_path: str):  # noqa
    """Helper retained for clarity; create_user lives in auth.auth."""
    from rcm_mc.portfolio.store import PortfolioStore
    return PortfolioStore(db_path)


class TestSeededDashboardRendersMarqueeData(unittest.TestCase):
    """Editorial dashboard at /app?ui=v3 contains the expected seeded
    content when the DB has been demo-seeded."""

    @classmethod
    def setUpClass(cls) -> None:
        # Snapshot any pre-existing env values so tearDownClass can
        # restore them — preserves order-independence with other tests.
        cls._saved_env = {
            k: os.environ.get(k)
            for k in ("CHARTIS_UI_V2", "RCM_MC_PHI_MODE")
        }
        os.environ["CHARTIS_UI_V2"] = "1"
        os.environ["RCM_MC_PHI_MODE"] = "disallowed"
        cls.server, cls.port, cls.db, cls.base, cls.opener = (
            _spin_up_seeded_server()
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        # Restore env to pre-test state
        for k, v in cls._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _fetch(self, path: str) -> str:
        resp = self.opener.open(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        )
        return resp.read().decode("utf-8", errors="replace")

    def test_dashboard_renders_named_deal_in_deals_table(self) -> None:
        """Cypress Crossing Health (ccf_2026) is the flagship demo
        deal — must appear by name on the deals table."""
        body = self._fetch("/app?ui=v3")
        self.assertTrue(
            "Cypress Crossing" in body or "ccf_2026" in body,
            "flagship deal missing from dashboard",
        )

    def test_focused_deal_renders_covenant_heatmap_with_real_data(self) -> None:
        """Focusing ccf_2026 should render the covenant heatmap with
        Net Leverage values (the wired row, per Phase 3 Q4.5)."""
        body = self._fetch("/app?ui=v3&deal=ccf_2026")
        self.assertIn("app-cov-heat", body, "covenant heatmap missing")
        # Net Leverage is the 1 wired row — its label must render
        self.assertIn("Net Leverage", body, "Net Leverage row missing")

    def test_initiative_tracker_fires_playbook_gap_pill(self) -> None:
        """Cross-portfolio (no deal focused) initiative tracker must
        fire the PLAYBOOK GAP pill for prior_auth_improvement —
        seeded across 3 deals at -50% / -40% / -30%."""
        body = self._fetch("/app?ui=v3")
        self.assertIn(
            "PLAYBOOK GAP", body,
            "PLAYBOOK GAP pill not firing — seeder didn't produce "
            "the expected cross-portfolio signal",
        )

    def test_deliverables_block_lists_seeded_export_cards(self) -> None:
        """Deliverables block should list the 8 seeded generated_exports
        rows when no deal is focused, OR a subset when a deal is
        focused — either way, NOT the empty-state."""
        body = self._fetch("/app?ui=v3&deal=ccf_2026")
        self.assertIn("app-deliv", body, "deliverables block missing")
        # ccf_2026 was seeded with 3 export rows; at least one filename
        # token should appear
        self.assertTrue(
            "full_html_report" in body
            or "ic_packet" in body
            or "deal_export" in body
            or "/exports/" in body,
            "no seeded export filenames or links visible",
        )

    def test_phi_banner_renders_in_disallowed_mode(self) -> None:
        body = self._fetch("/app?ui=v3")
        self.assertIn(
            'data-phi-mode="disallowed"', body,
            "PHI banner missing — RCM_MC_PHI_MODE not respected",
        )

    def test_dashboard_status_200_against_seeded_db(self) -> None:
        """Sanity: the route returns 200, not 500/redirect/etc., when
        backed by a seeded DB. The contract suite already covers
        this against an empty DB; this asserts the seeded path too."""
        resp = self.opener.open(
            f"http://127.0.0.1:{self.port}/app?ui=v3", timeout=5,
        )
        self.assertEqual(resp.status, 200)


if __name__ == "__main__":
    unittest.main()
