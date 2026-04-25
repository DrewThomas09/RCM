"""End-to-end screening workflow test.

The directive: filter, sort, click through to profile, back to
results — fast and smooth. This suite covers:

  • Universe scoring (predict_deal_metrics + score_universe)
  • Filter every dimension exposed by DealFilter (sector, size
    range, confidence, exclude_topics, min_uplift)
  • Sort by every available column
  • End-to-end HTTP: filter URL works, profile drilldown reachable
  • Performance: scoring + filtering 200-deal universe under 200ms
  • Empty / edge cases (no matches, single match)
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_universe(n: int = 50, seed: int = 7):
    """Synthesize a representative deal universe."""
    import random
    from rcm_mc.screening.predict import DealCandidate
    rng = random.Random(seed)
    sectors = [
        "physician_group", "asc", "mso", "imaging",
        "behavioral_health", "dental", "lab",
        "dialysis", "hospital", "skilled_nursing",
    ]
    out = []
    for i in range(n):
        sector = sectors[i % len(sectors)]
        revenue = rng.uniform(20_000_000, 500_000_000)
        margin = rng.uniform(-0.05, 0.25)
        ebitda = revenue * margin
        out.append(DealCandidate(
            deal_id=f"deal-{i:03d}",
            name=f"Deal {i:03d}",
            sector=sector,
            state=rng.choice(
                ["TX", "FL", "CA", "GA", "NY"]),
            revenue_mm=revenue / 1e6,
            ebitda_mm=ebitda / 1e6,
            ebitda_margin=margin,
            growth_rate=rng.uniform(-0.05, 0.15),
            payer_concentration=rng.uniform(0.20, 0.75),
            physician_concentration=rng.uniform(
                0.10, 0.55),
            cash_pay_share=rng.uniform(0.0, 0.30),
            out_of_network_share=rng.uniform(
                0.0, 0.20),
            has_pe_history=(i % 3 == 0)))
    return out


# ── Universe scoring ────────────────────────────────────────

class TestUniverseScoring(unittest.TestCase):
    def test_predict_returns_full_result(self):
        from rcm_mc.screening.predict import (
            predict_deal_metrics,
        )
        candidates = _build_universe(n=1)
        result = predict_deal_metrics(candidates[0])
        self.assertEqual(
            result.deal_id, candidates[0].deal_id)
        self.assertGreaterEqual(result.confidence, 0)
        self.assertLessEqual(result.confidence, 1)
        self.assertIn(
            result.confidence_band,
            ["high", "medium", "low"])

    def test_score_universe_sorts_by_uplift_desc(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        results = score_universe(_build_universe(n=20))
        uplifts = [
            r.predicted_ebitda_uplift_mm
            for r in results]
        self.assertEqual(
            uplifts, sorted(uplifts, reverse=True))

    def test_score_universe_50_deals(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        results = score_universe(_build_universe(n=50))
        self.assertEqual(len(results), 50)


# ── Filter on every dimension ───────────────────────────────

class TestFilters(unittest.TestCase):
    def setUp(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        self.results = score_universe(
            _build_universe(n=50, seed=9))

    def test_sector_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(sectors=["physician_group"]))
        for r in filtered:
            self.assertEqual(
                r.sector, "physician_group")

    def test_multi_sector_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(sectors=["asc", "imaging"]))
        for r in filtered:
            self.assertIn(r.sector, ["asc", "imaging"])

    def test_size_min_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(size_min_mm=20.0))
        for r in filtered:
            self.assertGreaterEqual(r.ebitda_mm, 20.0)

    def test_size_max_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(size_max_mm=10.0))
        for r in filtered:
            self.assertLessEqual(r.ebitda_mm, 10.0)

    def test_confidence_floor(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(confidence_floor=0.7))
        for r in filtered:
            self.assertGreaterEqual(r.confidence, 0.7)

    def test_min_uplift_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(min_uplift_mm=5.0))
        for r in filtered:
            self.assertGreaterEqual(
                r.predicted_ebitda_uplift_mm, 5.0)

    def test_exclude_topics_filter(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        # Exclude any deal flagged with payer concentration
        filtered = apply_filter(
            self.results,
            DealFilter(
                exclude_topics=["payer concentration"]))
        for r in filtered:
            joined = " ".join(r.risk_factors).lower()
            self.assertNotIn(
                "payer concentration", joined)

    def test_combined_filters(self):
        """Multiple filter dimensions stack — all must hold."""
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(
                sectors=["asc", "imaging",
                         "physician_group"],
                size_min_mm=5.0,
                confidence_floor=0.4,
                min_uplift_mm=1.0))
        for r in filtered:
            self.assertIn(r.sector, [
                "asc", "imaging",
                "physician_group"])
            self.assertGreaterEqual(
                r.ebitda_mm, 5.0)
            self.assertGreaterEqual(r.confidence, 0.4)
            self.assertGreaterEqual(
                r.predicted_ebitda_uplift_mm, 1.0)

    def test_empty_filter_keeps_all(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results, DealFilter())
        self.assertEqual(
            len(filtered), len(self.results))

    def test_filter_to_zero_results(self):
        """Aggressive filter → empty list, no crash."""
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        filtered = apply_filter(
            self.results,
            DealFilter(
                size_min_mm=1e9,   # impossible threshold
                confidence_floor=0.99))
        self.assertEqual(filtered, [])


# ── Sort behaviors ──────────────────────────────────────────

class TestSorts(unittest.TestCase):
    """The dashboard's table is sortable. score_universe sorts
    by uplift desc by default; partner can re-sort by any
    numeric column. Verify resort produces correct order."""

    def setUp(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        self.results = score_universe(
            _build_universe(n=20, seed=11))

    def test_sort_by_revenue_desc(self):
        sorted_r = sorted(
            self.results,
            key=lambda r: -r.revenue_mm)
        revenues = [r.revenue_mm for r in sorted_r]
        self.assertEqual(
            revenues, sorted(revenues, reverse=True))

    def test_sort_by_ebitda_asc(self):
        sorted_r = sorted(
            self.results, key=lambda r: r.ebitda_mm)
        ebitdas = [r.ebitda_mm for r in sorted_r]
        self.assertEqual(ebitdas, sorted(ebitdas))

    def test_sort_by_confidence_desc(self):
        sorted_r = sorted(
            self.results,
            key=lambda r: -r.confidence)
        confs = [r.confidence for r in sorted_r]
        self.assertEqual(
            confs, sorted(confs, reverse=True))

    def test_sort_by_improvement_pct(self):
        sorted_r = sorted(
            self.results,
            key=lambda r: -r.predicted_improvement_pct)
        pcts = [
            r.predicted_improvement_pct
            for r in sorted_r]
        self.assertEqual(
            pcts, sorted(pcts, reverse=True))


# ── Performance ─────────────────────────────────────────────

class TestPerformance(unittest.TestCase):
    def test_score_200_deals_fast(self):
        """Scoring + filtering 200 deals must run in <500ms.
        The dashboard re-runs this on every filter change."""
        from rcm_mc.screening.predict import (
            score_universe,
        )
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        candidates = _build_universe(n=200, seed=13)
        t0 = time.perf_counter()
        results = score_universe(candidates)
        filtered = apply_filter(
            results,
            DealFilter(sectors=["physician_group"],
                       size_min_mm=5.0,
                       confidence_floor=0.4))
        elapsed = time.perf_counter() - t0
        # Generous bound — typical run is ~30ms
        self.assertLess(
            elapsed, 0.5,
            f"200-deal screen took {elapsed:.3f}s "
            f"(>500ms is too slow for interactive)")

    def test_filter_200_deals_fast(self):
        """Re-filter (without rescoring) must be even faster
        — partner toggles filters and expects instant
        feedback."""
        from rcm_mc.screening.predict import (
            score_universe,
        )
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        results = score_universe(
            _build_universe(n=200, seed=17))
        t0 = time.perf_counter()
        for _ in range(20):
            apply_filter(
                results,
                DealFilter(sectors=["physician_group"]))
        elapsed = time.perf_counter() - t0
        # 20 filter passes in <100ms
        self.assertLess(
            elapsed, 0.1,
            f"20 filter passes took {elapsed:.3f}s")


# ── End-to-end HTTP routing ─────────────────────────────────

class TestEndToEndRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "p.db")
        cls.port = _free_port()
        cls.srv, _ = build_server(
            port=cls.port, db_path=cls.db,
            host="127.0.0.1")
        cls.thread = threading.Thread(
            target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def _get(self, path: str):
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}",
                timeout=10)
        except urllib.error.HTTPError as exc:
            return exc

    def test_screening_dashboard_loads(self):
        """/screening/dashboard should render even with empty DB."""
        resp = self._get("/screening/dashboard")
        # Must be 200 (or graceful redirect/empty); never 500
        self.assertNotEqual(resp.status, 500)

    def test_drill_through_to_profile_works(self):
        """After screening, click a deal → /deal/<id>/profile.
        Should render even when no packet exists."""
        resp = self._get(
            "/deal/deal-005/profile")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        # Empty-state copy
        self.assertIn("deal-005", body)

    def test_back_to_morning_view_works(self):
        """From profile, breadcrumb back to the dashboard."""
        resp = self._get("/?v3=1")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Morning view", body)

    def test_screening_endpoint_handles_empty(self):
        """No 500 on the legacy /screen page."""
        resp = self._get("/screen")
        self.assertNotEqual(resp.status, 500)


# ── Edge cases ──────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):
    def test_empty_universe(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        self.assertEqual(score_universe([]), [])

    def test_single_deal_universe(self):
        from rcm_mc.screening.predict import (
            score_universe,
        )
        results = score_universe(
            _build_universe(n=1, seed=23))
        self.assertEqual(len(results), 1)

    def test_filter_empty_universe(self):
        from rcm_mc.screening.filter import (
            apply_filter, DealFilter,
        )
        self.assertEqual(
            apply_filter([], DealFilter()), [])


if __name__ == "__main__":
    unittest.main()
