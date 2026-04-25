"""Tests for the comparable-deal benchmarking module.

End-to-end coverage:
  1. Per-feature scoring (sector / size / year / payer / buyer)
  2. Composite score_match math
  3. find_comparables ranking + self-exclusion
  4. summarize_outcomes percentile + win-rate logic
  5. benchmark_deal one-shot dict shape
  6. /diligence/comparable-outcomes HTTP route
  7. /api/diligence/comparable-outcomes JSON contract
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPerFeatureScoring(unittest.TestCase):
    def test_sector_exact_match(self):
        from rcm_mc.diligence.comparable_outcomes import _sector_match
        self.assertEqual(_sector_match("hospital", "hospital"), 1.0)

    def test_sector_related_partial_credit(self):
        from rcm_mc.diligence.comparable_outcomes import _sector_match
        # Hospital ↔ post_acute share margin dynamics
        self.assertEqual(_sector_match("hospital", "post_acute"), 0.5)

    def test_sector_unrelated_zero(self):
        from rcm_mc.diligence.comparable_outcomes import _sector_match
        self.assertEqual(_sector_match("hospital", "managed_care"), 0.0)

    def test_size_distance_same_size_full_score(self):
        from rcm_mc.diligence.comparable_outcomes import _size_distance
        self.assertEqual(_size_distance(500.0, 500.0), 1.0)

    def test_size_distance_5x_apart_zero(self):
        from rcm_mc.diligence.comparable_outcomes import _size_distance
        self.assertEqual(_size_distance(100.0, 500.0), 0.0)

    def test_size_distance_handles_none(self):
        from rcm_mc.diligence.comparable_outcomes import _size_distance
        self.assertEqual(_size_distance(None, 500.0), 0.5)

    def test_year_recency_same_year(self):
        from rcm_mc.diligence.comparable_outcomes import _year_recency
        self.assertEqual(_year_recency(2024, 2024), 1.0)

    def test_year_recency_decays_to_zero_at_10y(self):
        from rcm_mc.diligence.comparable_outcomes import _year_recency
        self.assertEqual(_year_recency(2024, 2014), 0.0)

    def test_payer_mix_close_match(self):
        from rcm_mc.diligence.comparable_outcomes import _payer_mix_match
        a = {"medicare": 0.5, "medicaid": 0.2}
        b = {"medicare": 0.52, "medicaid": 0.18}
        # Government share: 0.7 vs 0.7 → full score
        self.assertEqual(_payer_mix_match(a, b), 1.0)


class TestCompositeMatch(unittest.TestCase):
    def test_perfect_match_is_100(self):
        from rcm_mc.diligence.comparable_outcomes import score_match
        target = {"sector": "hospital", "ev_mm": 500, "year": 2024,
                  "payer_mix": {"medicare": 0.5, "medicaid": 0.2},
                  "buyer": "NMC"}
        self.assertEqual(score_match(target, target), 100.0)

    def test_unrelated_sector_dominates_low_score(self):
        from rcm_mc.diligence.comparable_outcomes import score_match
        target = {"sector": "hospital", "ev_mm": 500, "year": 2024}
        bad = {"sector": "managed_care", "ev_mm": 500, "year": 2024}
        self.assertLess(score_match(target, bad), 70)


class TestFindComparables(unittest.TestCase):
    def test_self_excluded_from_match_set(self):
        """A deal must not appear in its own comparable set."""
        from rcm_mc.diligence.comparable_outcomes import find_comparables

        class _FakeCorpus:
            def list(self, **_kw):
                return [
                    {"source_id": "TARGET", "sector": "hospital",
                     "ev_mm": 500, "year": 2024, "realized_moic": 2.0},
                    {"source_id": "OTHER", "sector": "hospital",
                     "ev_mm": 500, "year": 2024, "realized_moic": 3.0},
                ]

        target = {"source_id": "TARGET", "sector": "hospital",
                  "ev_mm": 500, "year": 2024}
        comps = find_comparables(_FakeCorpus(), target, top_n=5)
        ids = {c.deal["source_id"] for c in comps}
        self.assertNotIn("TARGET", ids)

    def test_match_reasons_populated(self):
        from rcm_mc.diligence.comparable_outcomes import find_comparables

        class _FakeCorpus:
            def list(self, **_kw):
                return [
                    {"source_id": "MATCH", "sector": "hospital",
                     "ev_mm": 480, "year": 2024,
                     "realized_moic": 2.5, "buyer": "NMC"},
                ]

        target = {"sector": "hospital", "ev_mm": 500, "year": 2024,
                  "buyer": "NMC"}
        comps = find_comparables(_FakeCorpus(), target, top_n=1)
        self.assertEqual(len(comps), 1)
        self.assertGreater(len(comps[0].match_reasons), 0)


class TestOutcomeSummary(unittest.TestCase):
    def test_percentiles_correct(self):
        from rcm_mc.diligence.comparable_outcomes import (
            summarize_outcomes, Comparable,
        )
        comps = [
            Comparable(deal={"realized_moic": 1.0, "realized_irr": 0.05}, score=80),
            Comparable(deal={"realized_moic": 2.0, "realized_irr": 0.15}, score=80),
            Comparable(deal={"realized_moic": 3.0, "realized_irr": 0.25}, score=80),
            Comparable(deal={"realized_moic": 4.0, "realized_irr": 0.35}, score=80),
        ]
        out = summarize_outcomes(comps)
        self.assertEqual(out["moic"]["median"], 2.5)
        self.assertEqual(out["n_comparables"], 4)

    def test_win_rate_at_2_5x_threshold(self):
        from rcm_mc.diligence.comparable_outcomes import (
            summarize_outcomes, Comparable,
        )
        # 4 deals, 2 over 2.5x → 50% win rate
        comps = [
            Comparable(deal={"realized_moic": 1.5}, score=80),
            Comparable(deal={"realized_moic": 2.0}, score=80),
            Comparable(deal={"realized_moic": 3.0}, score=80),
            Comparable(deal={"realized_moic": 4.0}, score=80),
        ]
        out = summarize_outcomes(comps)
        self.assertEqual(out["win_rate_2_5x"], 0.5)


class TestBenchmarkDealShape(unittest.TestCase):
    def test_one_shot_dict_shape(self):
        from rcm_mc.diligence.comparable_outcomes import benchmark_deal

        class _FakeCorpus:
            def list(self, **_kw):
                return [
                    {"source_id": f"D{i}", "sector": "hospital",
                     "ev_mm": 500 + i*10, "year": 2023,
                     "realized_moic": 2.0 + 0.5*i,
                     "realized_irr": 0.15 + 0.02*i,
                     "hold_years": 5,
                     "deal_name": f"Hospital {i}",
                     "buyer": "NMC"}
                    for i in range(8)
                ]

        target = {"sector": "hospital", "ev_mm": 500, "year": 2024}
        result = benchmark_deal(_FakeCorpus(), target, top_n=5)

        # Required top-level keys
        self.assertIn("target", result)
        self.assertIn("comparables", result)
        self.assertIn("outcome_distribution", result)

        # Each comparable carries the needed fields
        c0 = result["comparables"][0]
        for field in ("deal_id", "deal_name", "year", "buyer", "ev_mm",
                      "realized_moic", "realized_irr", "hold_years",
                      "match_score", "match_reasons"):
            self.assertIn(field, c0)


class TestComparableHttpRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def test_html_route_initial_load_shows_form(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}"
            "/diligence/comparable-outcomes",
            timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode()
        self.assertIn("Comparable-deal outcomes", html)
        self.assertIn("Find comparables", html)
        # Sector dropdown options present
        self.assertIn('value="hospital"', html)
        self.assertIn('value="managed_care"', html)

    def test_html_route_with_inputs_renders_table(self):
        params = urllib.parse.urlencode({
            "sector": "hospital", "ev_mm": "500", "year": "2024",
        })
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}"
            f"/diligence/comparable-outcomes?{params}",
            timeout=10,
        ) as resp:
            html = resp.read().decode()
        # Stat strip + table headers
        self.assertIn("Median MOIC", html)
        self.assertIn("Win rate", html)

    def test_json_api(self):
        params = urllib.parse.urlencode({
            "sector": "hospital", "ev_mm": "500", "year": "2024",
            "top_n": "5",
        })
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}"
            f"/api/diligence/comparable-outcomes?{params}",
            timeout=10,
        ) as resp:
            body = json.loads(resp.read())
        self.assertIn("target", body)
        self.assertIn("comparables", body)
        self.assertIn("outcome_distribution", body)
        # Top-N respected
        self.assertLessEqual(len(body["comparables"]), 5)


if __name__ == "__main__":
    unittest.main()
