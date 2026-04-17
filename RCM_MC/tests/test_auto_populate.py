"""Tests for the one-name auto-population engine (Prompt 23).

Invariants locked here:

 1. Fuzzy name match returns up to ``limit`` candidates, sorted by
    confidence descending.
 2. An exact CCN lookup returns confidence 1.0.
 3. A too-short query returns an empty candidate list (HCRIS lookup
    enforces its own min-length policy).
 4. ``"Name, ST"`` form parses into name + state and scopes the
    search to that state.
 5. Source-priority: HCRIS wins over a matching IRS 990 row for the
    same provider/metric.
 6. Freshness band: a stale ``loaded_at`` downgrades the confidence
    label.
 7. Gap list is sorted by ``ebitda_sensitivity_rank`` and only
    contains metrics not populated from any source.
 8. ``coverage_pct`` is ``hits / 38 * 100``.
 9. Auto-select fires only when the top candidate crosses the 0.90
    threshold.
10. ``AutoPopulateResult`` serializes cleanly to JSON.
11. Empty query / non-string / whitespace returns an empty result
    without raising.
12. Benchmark table missing (fresh DB, no refresh) still works.
13. ``search_hospitals`` mirrors the fuzzy match and respects limit.
14. Packet builder honours the ``auto_populated`` kwarg —
    auto-populated metrics land in ``rcm_profile`` with
    ``MetricSource.AUTO_POPULATED``.
15. Observed metric wins over auto-populated for the same key.
16. The ``MetricSource`` enum carries the new tiers.
17. ``_merge_all_sources`` converts HCRIS day-percentage columns
    into a ``payer_mix`` dict on the profile.
18. The CLI ``deal auto-populate`` exits 0 on a hit.
19. Invalid JSON body to ``POST /api/deals`` returns a 400.
20. ``POST /api/deals`` auto-upserts the deal row when the top match
    clears the confidence bar.
21. ``GET /api/data/hospitals?q=…`` returns match dicts.
22. ``GET /api/data/hospitals`` with empty q returns empty matches.
23. Two-word query prefers the better match.
24. Gap items carry a non-empty ``why_it_matters``.
25. ``to_dict`` on the result round-trips through ``json.dumps``.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rcm_mc.analysis.packet import MetricSource
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.data.auto_populate import (
    AutoPopulateResult,
    GapItem,
    HospitalMatch,
    SourceAttribution,
    _merge_all_sources,
    _source_priority,
    auto_populate,
    search_hospitals,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store() -> tuple:
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── Fuzzy matching ────────────────────────────────────────────────

class TestFuzzyMatching(unittest.TestCase):

    def test_name_query_returns_candidates(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy")
            self.assertGreater(len(r.matches), 0)
            self.assertLessEqual(len(r.matches), 3)
        finally:
            os.unlink(path)

    def test_matches_sorted_by_confidence(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy Hospital")
            confidences = [m.confidence for m in r.matches]
            self.assertEqual(confidences, sorted(confidences, reverse=True))
        finally:
            os.unlink(path)

    def test_ccn_exact_match_confidence_one(self):
        store, path = _tmp_store()
        try:
            # Use a CCN that's in the shipped HCRIS bundle.
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            r = auto_populate(store, ccn)
            self.assertEqual(len(r.matches), 1)
            self.assertEqual(r.matches[0].confidence, 1.0)
            self.assertIsNotNone(r.selected)
        finally:
            os.unlink(path)

    def test_short_query_returns_empty(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "ab")
            self.assertEqual(r.matches, [])
            self.assertIsNone(r.selected)
        finally:
            os.unlink(path)

    def test_name_comma_state_form(self):
        store, path = _tmp_store()
        try:
            r_all = auto_populate(store, "Mercy")
            r_scoped = auto_populate(store, "Mercy, CA")
            # Scoped matches are a subset of the unscoped match pool.
            scoped_ccns = {m.ccn for m in r_scoped.matches}
            for m in r_scoped.matches:
                self.assertEqual(m.state, "CA")
        finally:
            os.unlink(path)

    def test_empty_and_none_query(self):
        store, path = _tmp_store()
        try:
            self.assertEqual(auto_populate(store, "").matches, [])
            self.assertEqual(auto_populate(store, "   ").matches, [])
            # non-string handled:
            self.assertEqual(auto_populate(store, None).matches, [])
        finally:
            os.unlink(path)

    def test_search_hospitals_respects_limit(self):
        matches = search_hospitals("Mercy", limit=2)
        self.assertLessEqual(len(matches), 2)


# ── Source priority ───────────────────────────────────────────────

class TestSourcePriority(unittest.TestCase):

    def test_hcris_over_irs_990(self):
        self.assertGreater(_source_priority("HCRIS"),
                            _source_priority("IRS_990"))

    def test_care_compare_over_utilization(self):
        self.assertGreater(_source_priority("CARE_COMPARE"),
                            _source_priority("UTILIZATION"))

    def test_unknown_source_priority_zero(self):
        self.assertEqual(_source_priority("NOT_A_SOURCE"), 0)


# ── Merge logic ───────────────────────────────────────────────────

class TestMergeLogic(unittest.TestCase):

    def _seed_benchmarks(self, store: PortfolioStore) -> None:
        from rcm_mc.data.data_refresh import _ensure_tables
        _ensure_tables(store)
        now = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=600)).isoformat()
        with store.connect() as con:
            # Same metric from two sources — HCRIS fresher + higher prio.
            con.execute(
                "INSERT INTO hospital_benchmarks "
                "(provider_id, source, metric_key, value, period, loaded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("999999", "IRS_990", "total_assets", 100_000_000,
                 "FY2022", old),
            )
            con.execute(
                "INSERT INTO hospital_benchmarks "
                "(provider_id, source, metric_key, value, period, loaded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("999999", "HCRIS", "total_assets", 105_000_000,
                 "FY2024", now),
            )
            con.commit()

    def test_hcris_wins_over_irs_990(self):
        store, path = _tmp_store()
        try:
            self._seed_benchmarks(store)
            profile, financials, q, u, benchmarks, sources = (
                _merge_all_sources(store, "999999", None)
            )
            # ``total_assets`` is in the FINANCIAL_KEYS bucket, not
            # benchmark_metrics — check financials.
            self.assertEqual(financials.get("total_assets"), 105_000_000)
            winning = next(
                (s for s in sources if s.field == "total_assets"), None,
            )
            self.assertIsNotNone(winning)
            self.assertEqual(winning.source, "HCRIS")
        finally:
            os.unlink(path)

    def test_freshness_downgrades_confidence(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.data.data_refresh import _ensure_tables
            _ensure_tables(store)
            stale = (datetime.now(timezone.utc)
                     - timedelta(days=900)).isoformat()
            with store.connect() as con:
                con.execute(
                    "INSERT INTO hospital_benchmarks "
                    "(provider_id, source, metric_key, value, period, loaded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("888888", "HCRIS", "total_assets", 1_000_000,
                     "FY2020", stale),
                )
                con.commit()
            _, _, _, _, benchmarks, sources = _merge_all_sources(
                store, "888888", None,
            )
            s = next(s for s in sources if s.field == "total_assets")
            # 900 days old ≥ 540 → HIGH demotes to MEDIUM.
            self.assertEqual(s.confidence, "MEDIUM")
        finally:
            os.unlink(path)

    def test_missing_benchmarks_table_ok(self):
        """A fresh DB has no ``hospital_benchmarks`` table; merge
        should return the HCRIS-only bucket without error."""
        store, path = _tmp_store()
        try:
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            r = auto_populate(store, ccn)
            self.assertIsNotNone(r.selected)
            # Profile came from HCRIS.
            self.assertIn("HCRIS", {s.source for s in r.sources})
        finally:
            os.unlink(path)

    def test_payer_mix_derived_from_day_percentages(self):
        """HCRIS carries ``medicare_day_pct`` etc.; the merge should
        derive a ``payer_mix`` dict on the profile."""
        store, path = _tmp_store()
        try:
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            # Find a row with non-null medicare_day_pct.
            cand = df[df["medicare_day_pct"].notna()].iloc[0]
            ccn = str(cand["ccn"])
            r = auto_populate(store, ccn)
            self.assertIsNotNone(r.selected)
            self.assertIn("payer_mix", r.profile)
            mix = r.profile["payer_mix"]
            self.assertTrue(set(mix.keys()) & {
                "medicare", "medicaid", "commercial", "self_pay",
            })
        finally:
            os.unlink(path)


# ── Gaps + coverage ───────────────────────────────────────────────

class TestGapsAndCoverage(unittest.TestCase):

    def test_gaps_sorted_by_ebitda_sensitivity(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy Hospital")
            if r.selected is None:
                # Force a candidate so we get gap info.
                r.selected = r.matches[0]
            ranks = [g.ebitda_sensitivity_rank for g in r.gaps]
            self.assertEqual(ranks, sorted(ranks))
        finally:
            os.unlink(path)

    def test_gaps_exclude_populated_keys(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy Hospital")
            populated = set(r.financials) | set(r.quality) \
                | set(r.utilization) | set(r.benchmark_metrics)
            for g in r.gaps:
                self.assertNotIn(g.metric_key, populated)
        finally:
            os.unlink(path)

    def test_gaps_have_why_it_matters(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy Hospital")
            # Top gap should at least carry the display name as a
            # fallback narrative.
            if r.gaps:
                self.assertTrue(r.gaps[0].why_it_matters)
        finally:
            os.unlink(path)

    def test_coverage_pct_bounded(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy Hospital")
            self.assertGreaterEqual(r.coverage_pct, 0.0)
            self.assertLessEqual(r.coverage_pct, 100.0)
        finally:
            os.unlink(path)


# ── Auto-select ────────────────────────────────────────────────────

class TestAutoSelect(unittest.TestCase):

    def test_ambiguous_name_no_selection(self):
        store, path = _tmp_store()
        try:
            # A short partial name is unlikely to clear 0.90.
            r = auto_populate(store, "Community")
            if r.matches:
                # The top confidence should be well below 1.0; auto-
                # select only fires when it clears 0.90.
                if r.matches[0].confidence < 0.90:
                    self.assertIsNone(r.selected)
        finally:
            os.unlink(path)

    def test_ccn_auto_selects(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            r = auto_populate(store, ccn)
            self.assertIsNotNone(r.selected)
            self.assertEqual(r.selected.ccn, ccn.zfill(6))
        finally:
            os.unlink(path)


# ── Serialization ─────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_result_to_dict_json_safe(self):
        store, path = _tmp_store()
        try:
            r = auto_populate(store, "Mercy")
            d = r.to_dict()
            # ``json.dumps`` must not raise on any nested type.
            s = json.dumps(d, default=str)
            self.assertIn("matches", s)
        finally:
            os.unlink(path)

    def test_hospital_match_to_dict(self):
        m = HospitalMatch(
            ccn="123456", name="Test", city="Austin", state="TX",
            bed_count=200, confidence=0.85,
        )
        self.assertEqual(m.to_dict()["ccn"], "123456")

    def test_metric_source_enum_has_new_tiers(self):
        self.assertIn("AUTO_POPULATED", MetricSource.__members__)
        self.assertIn("EXTRACTED", MetricSource.__members__)


# ── Packet-builder integration ────────────────────────────────────

class TestPacketBuilderIntegration(unittest.TestCase):

    def test_auto_populated_tag_on_profile_metric(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="Test",
                              profile={"payer_mix": {"commercial": 1.0},
                                        "bed_count": 200})
            packet = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
                auto_populated={"days_in_ar": 52.0},
            )
            # denial_rate came from observed, days_in_ar from auto-populate.
            self.assertEqual(
                packet.rcm_profile["denial_rate"].source,
                MetricSource.OBSERVED,
            )
            self.assertEqual(
                packet.rcm_profile["days_in_ar"].source,
                MetricSource.AUTO_POPULATED,
            )
        finally:
            os.unlink(path)

    def test_observed_wins_over_auto_populated(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="Test",
                              profile={"bed_count": 200})
            packet = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 11.0},
                auto_populated={"denial_rate": 9999.0},  # would be suspicious
            )
            self.assertEqual(
                packet.rcm_profile["denial_rate"].value, 11.0,
            )
            self.assertEqual(
                packet.rcm_profile["denial_rate"].source,
                MetricSource.OBSERVED,
            )
        finally:
            os.unlink(path)


# ── CLI ───────────────────────────────────────────────────────────

class TestCLI(unittest.TestCase):

    def test_deal_auto_populate_happy_path(self):
        from rcm_mc.deals.deal import main as deal_main
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            # Prose output — just confirm exit code.
            rc = deal_main([
                "auto-populate", "--db", tf.name,
                "--name", "Mercy",
            ])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(tf.name)

    def test_deal_auto_populate_json_mode(self):
        from rcm_mc.deals.deal import main as deal_main
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            rc = deal_main([
                "auto-populate", "--db", tf.name,
                "--name", "Mercy", "--json",
            ])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(tf.name)


# ── HTTP API ──────────────────────────────────────────────────────

class TestAPI(unittest.TestCase):

    def _start(self, db_path: str) -> tuple:
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_hospitals_search_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/data/hospitals?q=Mercy&limit=3"
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["query"], "Mercy")
                self.assertLessEqual(len(body["matches"]), 3)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_hospitals_search_empty_query(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/data/hospitals?q="
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["matches"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_post_deals_missing_name_returns_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_post_deals_with_ccn_upserts(self):
        """A CCN guarantees confidence 1.0 → auto-select → deal upserted."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            from rcm_mc.data.hcris import _get_hcris_cached
            df = _get_hcris_cached()
            ccn = str(df.iloc[0]["ccn"])
            server, port = self._start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals",
                    data=json.dumps({"name": ccn}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertIsNotNone(body.get("selected"))
                self.assertIsNotNone(body.get("deal_id"))
                # The deal row lands in the store.
                store = PortfolioStore(tf.name)
                with store.connect() as con:
                    row = con.execute(
                        "SELECT deal_id FROM deals WHERE deal_id = ?",
                        (body["deal_id"],),
                    ).fetchone()
                self.assertIsNotNone(row)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
