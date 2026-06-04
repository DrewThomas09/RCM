"""Demo mode: the KKR healthcare portfolio seed.

Loading the demo must populate the portfolio with real KKR deals and credible,
internally-consistent metrics so the command center / portfolio surface fully
lights up. These tests lock in: every deal seeds, PE snapshots carry the
modeled MOIC/IRR/EBITDA, health scores produce a green/amber/red spread
(incl. the honest Envision downside), the command center renders the deals,
and the downloadable rows are well-formed.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class TestKKRDemoSeed(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.demo.kkr_demo import seed_kkr_demo, KKR_DEMO_DEALS
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        self.run_dir = os.path.join(self.tmp.name, "runs")
        self.n = seed_kkr_demo(self.store, run_dir=self.run_dir)
        self.specs = KKR_DEMO_DEALS

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_deals_seeded(self):
        self.assertEqual(self.n, len(self.specs))
        deals = self.store.list_deals(include_archived=True)
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else deals
        ids = {r.get("deal_id") or r.get("id") for r in rows}
        for s in self.specs:
            self.assertIn(s["id"], ids, f"{s['id']} not seeded")
        # Real KKR names present (command-center / search will surface these).
        names = {(r.get("name") or "") for r in rows}
        for nm in ("Envision Healthcare", "Cotiviti", "BrightSpring Health Services",
                   "Heartland Dental", "PetVet Care Centers"):
            self.assertIn(nm, names)

    def test_snapshots_carry_pe_metrics(self):
        # Each deal's hold snapshot must carry the modeled MOIC/IRR/EBITDA.
        with self.store.connect() as con:
            rows = {r["deal_id"]: r for r in con.execute(
                "SELECT deal_id, moic, irr, entry_ebitda, entry_ev, "
                "covenant_headroom_turns FROM deal_snapshots").fetchall()}
        self.assertEqual(set(rows) >= {s["id"] for s in self.specs}, True)
        # Envision is the honest downside: MOIC ~0, covenant tripped (<0 headroom).
        env = rows["envision"]
        self.assertAlmostEqual(env["moic"], 0.0, places=2)
        self.assertLess(env["covenant_headroom_turns"], 0)
        # Cotiviti is a healthy winner.
        cot = rows["cotiviti"]
        self.assertGreater(cot["moic"], 2.0)
        self.assertGreater(cot["entry_ebitda"], 0)
        # EV anchored to the real disclosed figure (~$9.9B) for Envision.
        self.assertGreater(env["entry_ev"], 9_000e6)

    def test_health_spread(self):
        from rcm_mc.deals.health_score import compute_health
        bands = {}
        for s in self.specs:
            h = compute_health(self.store, s["id"])
            bands[s["id"]] = h.get("band")
        # A showcase needs a real spread, not all-green. Envision must not be green.
        self.assertNotEqual(bands.get("envision"), "green")
        distinct = {b for b in bands.values() if b}
        self.assertGreaterEqual(len(distinct), 2, f"no health spread: {bands}")

    def test_command_center_portfolio_query_populated(self):
        # The command center reads non-archived deals + profile_json from the
        # store (see ui/command_center.py). Assert that exact query returns the
        # seeded KKR deals with profile metadata — i.e. the populated portfolio
        # panel will render. (Full page render is exercised via the /demo route
        # smoke, which feeds the server's real CMS frame.)
        import json
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT deal_id, name, profile_json FROM deals "
                "WHERE archived_at IS NULL ORDER BY created_at DESC").fetchall()
        self.assertGreaterEqual(len(rows), len(self.specs))
        names = {r["name"] for r in rows}
        self.assertIn("Cotiviti", names)
        self.assertIn("Envision Healthcare", names)
        # profile carries the KKR/sector/sponsor metadata the panel uses.
        prof = {r["deal_id"]: json.loads(r["profile_json"] or "{}") for r in rows}
        self.assertEqual(prof["cotiviti"].get("sponsor"), "KKR")
        self.assertEqual(prof["cotiviti"].get("demo"), "kkr")
        self.assertTrue(prof["envision"].get("observed_metrics"))

    def test_idempotent(self):
        # Re-seeding must not duplicate deals (upsert semantics).
        from rcm_mc.demo.kkr_demo import seed_kkr_demo
        seed_kkr_demo(self.store, run_dir=self.run_dir)
        deals = self.store.list_deals(include_archived=True)
        rows = deals.to_dict("records") if hasattr(deals, "to_dict") else deals
        ids = [r.get("deal_id") or r.get("id") for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len([i for i in ids if i == "envision"]), 1)

    def test_quarterly_history_trajectory(self):
        # Each deal carries a multi-quarter EBITDA actuals-vs-plan series (not a
        # single point), so the trajectory / variance / health-trend surfaces
        # have something to draw. The arc direction matches the tier: greens
        # improve, reds deteriorate into distress.
        from rcm_mc.pe.hold_tracking import variance_report
        from rcm_mc.demo.kkr_demo import _HIST_QUARTERS

        def ebitda_var(did):
            vdf = variance_report(self.store, did)
            eb = vdf[vdf["kpi"] == "ebitda"].sort_values("quarter")
            return [float(v) for v in eb["variance_pct"] if v == v]

        cot = ebitda_var("cotiviti")   # green
        env = ebitda_var("envision")   # red
        self.assertGreaterEqual(len(cot), len(_HIST_QUARTERS) - 1)
        self.assertGreaterEqual(len(env), len(_HIST_QUARTERS) - 1)
        # Green compounds a beat (last >= first, and ends positive);
        # red slides (last << first, and ends a deep miss).
        self.assertGreater(cot[-1], cot[0])
        self.assertGreaterEqual(cot[-1], 0.0)
        self.assertLess(env[-1], env[0])
        self.assertLessEqual(env[-1], -0.15)
        # NPSR is tracked too (a second trajectory line).
        vdf = variance_report(self.store, "cotiviti")
        self.assertIn("net_patient_revenue", set(vdf["kpi"]))


class TestDemoRows(unittest.TestCase):
    def test_download_rows_wellformed(self):
        from rcm_mc.demo.kkr_demo import demo_deal_rows, KKR_DEMO_DEALS
        rows = demo_deal_rows()
        self.assertEqual(len(rows), len(KKR_DEMO_DEALS))
        for r in rows:
            for f in ("deal_id", "name", "sponsor", "sector", "vintage",
                      "entry_ev_mm", "moic", "irr", "source_url"):
                self.assertIn(f, r)
            self.assertEqual(r["sponsor"], "KKR")
            self.assertTrue(r["source_url"].startswith("http"))

    def test_real_evs_flagged(self):
        # The disclosed EVs (Envision/Cotiviti/BrightSpring/Therapy Brands) are
        # flagged real; modeled ones are flagged modeled (credibility honesty).
        from rcm_mc.demo.kkr_demo import demo_deal_rows
        by = {r["deal_id"]: r for r in demo_deal_rows()}
        self.assertTrue(by["envision"]["ev_disclosed"])
        self.assertTrue(by["cotiviti"]["ev_disclosed"])
        self.assertFalse(by["petvet"]["ev_disclosed"])


if __name__ == "__main__":
    unittest.main()
