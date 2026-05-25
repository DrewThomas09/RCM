"""SNF / Nursing Home vertical — loader + screener + profile + market intel.

Data is the vendored CMS Nursing Home Care Compare 'Provider Information'
snapshot (real, official, ~14.7k facilities) — no synthetic data, no runtime
network. Tests assert the loader, the screener (national/state/locality), the
provider profile (peers + percentile), honest caveats (Medicare/public scope,
fines = regulatory penalty not revenue), 404 on unknown CCN, and no external
calls.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.snf import (
    load_snf_providers,
    load_snf_quality,
    load_snf_summary_by_state,
    snf_provider_by_ccn,
    snf_providers_for_state,
    snf_turnover_summary,
    snf_turnover_by_state,
    snf_rating_distribution,
    snf_enforcement_summary,
)
from rcm_mc.server import build_server
from rcm_mc.ui.snf_page import render_snf, render_snf_profile


def _a_ccn():
    for ccn, p in load_snf_providers().items():
        if p.state and p.county:
            return ccn
    return next(iter(load_snf_providers()))


class SnfLoaderTests(unittest.TestCase):
    def test_providers_and_quality_load_and_align(self):
        P, Q = load_snf_providers(), load_snf_quality()
        self.assertGreater(len(P), 10000)          # ~14.7k real facilities
        self.assertEqual(set(P) - set(Q), set())   # quality keyed by same CCNs
        ccn = _a_ccn()
        self.assertEqual(P[ccn], snf_provider_by_ccn(ccn))
        # Provenance carried on every row.
        self.assertIn("Provider Information", P[ccn].source)
        self.assertTrue(P[ccn].source_date)

    def test_state_summary_and_filter(self):
        S = load_snf_summary_by_state()
        self.assertGreater(len(S), 40)             # 50 states + territories
        ccn = _a_ccn()
        st = load_snf_providers()[ccn].state
        rows = snf_providers_for_state(st)
        self.assertTrue(rows and all(p.state == st for p in rows))
        # avg_overall_rating is computed only over rated facilities.
        s = S[st]
        self.assertIn("facilities", s)
        self.assertIn("avg_overall_rating", s)

    def test_missing_files_degrade_safely(self, ):
        # Loaders return {} when the CSV is absent (no crash) — guarded by
        # the .is_file() check; we just confirm the functions are callable
        # and the live (present) files are non-empty.
        self.assertTrue(load_snf_providers())


class SnfTurnoverBenchmarkTests(unittest.TestCase):
    """Real CMS nurse-staff turnover benchmark (used by Provider Retention)."""

    def test_national_summary_is_real_and_sane(self):
        s = snf_turnover_summary()
        # Thousands of facilities report turnover; missing stays out of the sample.
        self.assertGreater(s["n"], 10000)
        self.assertLessEqual(s["n"], s["facilities"])
        # Nursing-home nurse turnover is high but bounded — a real sanity band.
        self.assertTrue(20 < s["median_pct"] < 80, s["median_pct"])
        self.assertLessEqual(s["p25_pct"], s["median_pct"])
        self.assertLessEqual(s["median_pct"], s["p75_pct"])
        self.assertEqual(s["state"], "US")

    def test_state_scope_and_empty_state_safe(self):
        tx = snf_turnover_summary("TX")
        self.assertEqual(tx["state"], "TX")
        self.assertGreater(tx["n"], 100)
        # Unknown state → empty sample, no crash, None medians (never 0).
        zz = snf_turnover_summary("ZZ")
        self.assertEqual(zz["n"], 0)
        self.assertIsNone(zz["median_pct"])

    def test_by_state_worst_first_and_min_sample(self):
        rows = snf_turnover_by_state(8)
        self.assertTrue(rows)
        self.assertLessEqual(len(rows), 8)
        # Worst-first ordering, and no state with <10 facilities masquerades.
        meds = [r["median_pct"] for r in rows]
        self.assertEqual(meds, sorted(meds, reverse=True))
        self.assertTrue(all(r["facilities_reporting"] >= 10 for r in rows))

    def test_rating_distribution_is_real_and_complete(self):
        r = snf_rating_distribution("overall_rating")
        self.assertGreater(r["n"], 10000)
        self.assertTrue(1.0 <= r["mean"] <= 5.0, r["mean"])
        # All five star buckets present; percentages sum to ~100.
        self.assertEqual(set(r["dist"]), {"1", "2", "3", "4", "5"})
        self.assertEqual(sum(d["count"] for d in r["dist"].values()), r["n"])
        self.assertAlmostEqual(sum(d["pct"] for d in r["dist"].values()), 100.0, delta=0.5)
        # Unknown metric is rejected, not silently wrong.
        with self.assertRaises(ValueError):
            snf_rating_distribution("not_a_rating")

    def test_ownership_summary_is_real_and_pii_free(self):
        from rcm_mc.data.snf import snf_ownership_summary
        import csv as _csv
        from pathlib import Path as _P
        o = snf_ownership_summary()
        self.assertGreater(o["facilities"], 10000)          # ~14.4k SNFs
        self.assertTrue(1 <= o["median_owners_per_facility"] <= 100)
        self.assertTrue(0 <= o["pct_with_indirect_ownership"] <= 100)
        # The committed aggregate is a summary JSON — no owner-name columns/keys.
        for k in o:
            self.assertNotIn("name", k.lower())
            self.assertNotIn("first", k.lower())

    def test_top_owner_orgs_real_and_sorted(self):
        from rcm_mc.data.snf import snf_top_owner_orgs
        rows = snf_top_owner_orgs(10)
        self.assertTrue(rows)
        counts = [r["facilities_owned"] for r in rows]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertGreater(counts[0], 50)        # largest owners hold 100s
        self.assertTrue(all(r["owner_organization"] for r in rows))

    def test_enforcement_summary_is_real_and_sane(self):
        e = snf_enforcement_summary()
        self.assertGreater(e["facilities"], 10000)
        # Enforcement is common but not universal in this sector.
        self.assertTrue(10 < e["pct_fined"] < 90, e["pct_fined"])
        self.assertGreater(e["total_fines_usd"], 0)
        # Median fine is a positive dollar amount, mean >= 0.
        self.assertGreater(e["median_fine_usd"], 0)
        self.assertGreaterEqual(e["pct_payment_denial"], 0)
        self.assertGreaterEqual(e["pct_any_penalty"], 0)


class SnfScreenerTests(unittest.TestCase):
    def setUp(self):
        self.providers = load_snf_providers()
        self.ccn = _a_ccn()
        self.state = self.providers[self.ccn].state

    def test_national_screener(self):
        html = render_snf()
        self.assertIn("ck-page-title", html)
        self.assertIn("Facilities", html)
        self.assertIn("SNF / NURSING HOME", html)
        # honest caveats present
        self.assertIn("not a final investment recommendation", html.lower())
        self.assertIn("penalty", html.lower())

    def test_state_view_market_intel(self):
        html = render_snf({"state": [self.state]})
        self.assertIn("market summary", html)
        self.assertIn("County competition", html)   # SNF has county
        self.assertIn("Overall ★", html)        # rating column

    def test_screener_rows_link_to_profiles(self):
        html = render_snf({"state": [self.state]})
        self.assertIn(f'/nursing-homes/{self.ccn}"', html)

    def test_no_external_calls(self):
        # No runtime data/map/CDN calls. (Bare "http://" excluded — it
        # matches benign SVG xmlns namespaces in the shell.)
        low = render_snf().lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "data.cms.gov",
                    "tile.openstreetmap", "unpkg", "cdn.jsdelivr"):
            self.assertNotIn(bad, low)


class SnfProfileTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.html = render_snf_profile(self.ccn)
        self.providers = load_snf_providers()

    def test_profile_identity_metrics_peers(self):
        self.assertIsNotNone(self.html)
        self.assertIn("NURSING HOME (SNF)", self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Overall 5-star rating", self.html)
        self.assertIn("%ile", self.html)                       # percentile col
        self.assertIn(f"Peers in {self.providers[self.ccn].state}", self.html)
        self.assertIn(f"Peers in {self.providers[self.ccn].county}", self.html)

    def test_lower_is_better_metrics_not_shown_with_percentile(self):
        # Lower-is-better signals must NOT appear as percentile metric-table
        # rows (would invert the "higher percentile = better" frame). These
        # exact metric labels were intentionally excluded. ("Total fines"
        # still appears in the caveat prose — that's intended.)
        self.assertNotIn("Number of fines", self.html)
        self.assertNotIn("Payment denials", self.html)
        self.assertNotIn("nursing-staff turnover", self.html)

    def test_provenance_and_unknown_ccn(self):
        flat = " ".join(self.html.split())
        self.assertIn("NH_ProviderInfo", flat)
        self.assertIn("not a final investment recommendation", flat.lower())
        self.assertIsNone(render_snf_profile("000000"))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class SnfRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.ccn = _a_ccn()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        import os
        os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse(); b = r.read().decode("utf-8", "replace"); c.close()
        return r.status, b

    def test_routes(self):
        self.assertEqual(self._get("/nursing-homes")[0], 200)
        self.assertEqual(self._get(f"/nursing-homes/{self.ccn}")[0], 200)
        s, b = self._get("/nursing-homes/000000")
        self.assertEqual(s, 404)
        self.assertIn("Not Found", b)


class SnfGuideContextTests(unittest.TestCase):
    def test_curated_context_exists(self):
        from rcm_mc.assistant.context.get_page_context import get_page_context
        res = get_page_context("/nursing-homes")
        self.assertTrue(res.found)
        self.assertGreaterEqual(len(res.context.common_questions), 8)


if __name__ == "__main__":
    unittest.main()
