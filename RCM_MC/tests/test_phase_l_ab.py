"""Tests for Phase L: Playbook Builder (59), Fund Attribution (60).

PLAYBOOK BUILDER:
 1. _classify_pattern → commercial_heavy_denial archetype.
 2. _classify_pattern → medicare_heavy_ar archetype.
 3. _classify_pattern → rural_access_coding (<200 beds).
 4. _classify_pattern → system_acquisition (system-affiliated).
 5. _classify_pattern → general fallback.
 6. _achievement_pct computes correctly.
 7. _is_success threshold at 80%.
 8. build_playbook returns empty when <3 matching deals.
 9. build_playbook returns entry when >=3 matching deals exist.
10. PlaybookEntry.to_dict round-trips key fields.

FUND ATTRIBUTION:
11. compute_fund_attribution with no deals → zero totals.
12. compute_fund_attribution with one deal → correct RCM + organic split.
13. compute_fund_attribution with explicit deal list filter.
14. format_fund_attribution produces terminal-friendly string.
15. FundAttribution.to_dict serializes cleanly.
16. DealAttribution fields computed correctly.
17. Multiple expansion is zero placeholder.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import zlib

from rcm_mc.analysis.playbook import (
    DealOutcome,
    PlaybookEntry,
    _achievement_pct,
    _classify_pattern,
    _is_success,
    build_playbook,
)
from rcm_mc.pe.fund_attribution import (
    DealAttribution,
    FundAttribution,
    SourceAttribution,
    compute_fund_attribution,
    format_fund_attribution,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


def _seed_deal(store, deal_id, profile=None):
    """Insert a deal with optional profile."""
    store.upsert_deal(deal_id, profile=profile or {})


def _seed_analysis_run(store, deal_id, lever_impacts, total_recurring=0.0):
    """Insert a fake analysis_runs row with v2 bridge lever_impacts."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                scenario_id TEXT,
                as_of TEXT,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                packet_json BLOB NOT NULL,
                hash_inputs TEXT,
                run_id TEXT,
                notes TEXT
            )"""
        )
        packet = {
            "deal_id": deal_id,
            "value_bridge_result": {
                "lever_impacts": lever_impacts,
                "total_recurring_ebitda_delta": total_recurring,
            },
        }
        blob = zlib.compress(json.dumps(packet).encode())
        con.execute(
            "INSERT INTO analysis_runs "
            "(deal_id, model_version, created_at, packet_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, "test", "2026-01-01T00:00:00+00:00", blob),
        )
        con.commit()


def _seed_quarterly_actuals(store, deal_id, quarter, actuals, plan=None):
    """Insert a quarterly_actuals row."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS quarterly_actuals (
                actual_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                quarter TEXT NOT NULL,
                created_at TEXT NOT NULL,
                kpis_json TEXT NOT NULL,
                plan_kpis_json TEXT,
                notes TEXT
            )"""
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_actuals_deal_qtr "
            "ON quarterly_actuals(deal_id, quarter)"
        )
        con.execute(
            "INSERT OR REPLACE INTO quarterly_actuals "
            "(deal_id, quarter, created_at, kpis_json, plan_kpis_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                deal_id, quarter, "2026-01-01T00:00:00+00:00",
                json.dumps(actuals),
                json.dumps(plan or {}),
            ),
        )
        con.commit()


def _seed_value_creation_plan(store, deal_id, initiatives):
    """Insert a value_creation_plans row."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS value_creation_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                plan_json BLOB NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT,
                version INTEGER DEFAULT 1
            )"""
        )
        plan = {"deal_id": deal_id, "initiatives": initiatives}
        blob = zlib.compress(json.dumps(plan).encode())
        con.execute(
            "INSERT INTO value_creation_plans "
            "(deal_id, plan_json, created_at) VALUES (?, ?, ?)",
            (deal_id, blob, "2026-01-01T00:00:00+00:00"),
        )
        con.commit()


# ── Playbook tests ─────────────────────────────────────────────────

class TestClassifyPattern(unittest.TestCase):

    def test_commercial_heavy_denial(self):
        profile = {"commercial_pct": 55, "denial_rate": 15}
        self.assertEqual(
            _classify_pattern("denial_rate", profile),
            "commercial_heavy_denial",
        )

    def test_medicare_heavy_ar(self):
        profile = {"medicare_pct": 60, "ar_days": 65}
        self.assertEqual(
            _classify_pattern("days_in_ar", profile),
            "medicare_heavy_ar",
        )

    def test_rural_access_coding(self):
        profile = {"beds": 120}
        self.assertEqual(
            _classify_pattern("coding_denial_rate", profile),
            "rural_access_coding",
        )

    def test_system_acquisition(self):
        profile = {"system_affiliated": True, "beds": 400}
        self.assertEqual(
            _classify_pattern("denial_rate", profile),
            "system_acquisition",
        )

    def test_general_fallback(self):
        profile = {"beds": 300}
        self.assertEqual(
            _classify_pattern("denial_rate", profile),
            "general",
        )


class TestAchievementAndSuccess(unittest.TestCase):

    def test_achievement_pct_full(self):
        # Moved from 10 to 5 (target 5), achieved 5 → 100%
        self.assertAlmostEqual(_achievement_pct(10, 5, 5), 1.0)

    def test_achievement_pct_partial(self):
        # Moved from 10 to 5 (target 5), achieved 8 → 40%
        self.assertAlmostEqual(_achievement_pct(10, 5, 8), 0.4)

    def test_achievement_pct_no_span(self):
        self.assertAlmostEqual(_achievement_pct(5, 5, 5), 0.0)

    def test_is_success_at_threshold(self):
        # 80% achievement → success
        # initial=10, target=0, achieved=2 → (2-10)/(0-10)=0.8
        self.assertTrue(_is_success(10, 0, 2))

    def test_is_success_below_threshold(self):
        # initial=10, target=0, achieved=3 → (3-10)/(0-10)=0.7
        self.assertFalse(_is_success(10, 0, 3))


class TestBuildPlaybook(unittest.TestCase):

    def test_empty_when_insufficient_matches(self):
        store, path = _tmp_store()
        try:
            _seed_deal(store, "deal_A", {"beds": 300})
            lever = {"metric_key": "denial_rate", "current_value": 12, "target_value": 6}
            _seed_analysis_run(store, "deal_A", [lever])

            # Only 2 historical deals with matching pattern — below threshold
            for i in range(2):
                did = f"hist_{i}"
                _seed_deal(store, did, {"beds": 300})
                _seed_analysis_run(store, did, [lever])
                _seed_quarterly_actuals(store, did, "2025Q4", {"denial_rate": 7})

            result = build_playbook(store, "deal_A")
            self.assertEqual(result, [])
        finally:
            os.unlink(path)

    def test_entry_when_enough_matches(self):
        store, path = _tmp_store()
        try:
            _seed_deal(store, "deal_X", {"beds": 300})
            lever = {"metric_key": "denial_rate", "current_value": 12, "target_value": 6}
            _seed_analysis_run(store, "deal_X", [lever])

            # 3 historical deals with matching "general" pattern
            for i in range(3):
                did = f"match_{i}"
                _seed_deal(store, did, {"beds": 300})
                _seed_analysis_run(store, did, [lever])
                _seed_quarterly_actuals(store, did, "2025Q4", {"denial_rate": 7})

            result = build_playbook(store, "deal_X")
            self.assertEqual(len(result), 1)
            entry = result[0]
            self.assertEqual(entry.lever, "denial_rate")
            self.assertEqual(entry.pattern, "general")
            self.assertEqual(len(entry.matching_deals), 3)
            self.assertGreater(len(entry.recommendation), 0)
        finally:
            os.unlink(path)

    def test_playbook_entry_to_dict(self):
        outcome = DealOutcome(
            deal_id="d1", initial_value=10, target_value=5,
            achieved_value=5, months_elapsed=12, success=True,
            initiatives_used=["Improve coding"],
        )
        entry = PlaybookEntry(
            lever="denial_rate", pattern="general",
            matching_deals=[outcome], success_rate=1.0,
            avg_achievement_pct=1.0,
            common_initiatives=["Improve coding"],
            recommendation="Proceed.",
        )
        d = entry.to_dict()
        self.assertEqual(d["lever"], "denial_rate")
        self.assertEqual(len(d["matching_deals"]), 1)
        self.assertEqual(d["matching_deals"][0]["deal_id"], "d1")


# ── Fund Attribution tests ─────────────────────────────────────────

class TestFundAttribution(unittest.TestCase):

    def test_empty_fund(self):
        store, path = _tmp_store()
        try:
            store.init_db()
            attr = compute_fund_attribution(store)
            self.assertAlmostEqual(attr.total_value_created, 0.0)
            self.assertEqual(len(attr.by_deal), 0)
        finally:
            os.unlink(path)

    def test_single_deal_attribution(self):
        store, path = _tmp_store()
        try:
            _seed_deal(store, "alpha")
            _seed_analysis_run(store, "alpha", [], total_recurring=5_000_000)
            _seed_quarterly_actuals(
                store, "alpha", "2025Q1",
                {"ebitda": 52_000_000},
                plan={"ebitda": 50_000_000},
            )
            _seed_quarterly_actuals(
                store, "alpha", "2025Q4",
                {"ebitda": 60_000_000},
            )

            attr = compute_fund_attribution(store)
            # Entry 50M, latest 60M → total EBITDA change 10M
            # RCM = 5M, organic = 10M - 5M = 5M, total = 10M
            self.assertAlmostEqual(attr.total_value_created, 10_000_000)
            rcm = attr.by_source["rcm_improvement"]
            org = attr.by_source["organic_growth"]
            self.assertAlmostEqual(rcm.dollar_amount, 5_000_000)
            self.assertAlmostEqual(org.dollar_amount, 5_000_000)
            # Percentages
            self.assertAlmostEqual(rcm.pct_of_total, 50.0)
            self.assertAlmostEqual(org.pct_of_total, 50.0)
        finally:
            os.unlink(path)

    def test_explicit_deal_filter(self):
        store, path = _tmp_store()
        try:
            _seed_deal(store, "d1")
            _seed_deal(store, "d2")
            _seed_analysis_run(store, "d1", [], total_recurring=1_000_000)
            _seed_analysis_run(store, "d2", [], total_recurring=2_000_000)
            _seed_quarterly_actuals(store, "d1", "2025Q1", {"ebitda": 10_000_000}, plan={"ebitda": 10_000_000})
            _seed_quarterly_actuals(store, "d2", "2025Q1", {"ebitda": 20_000_000}, plan={"ebitda": 20_000_000})

            # Only include d1
            attr = compute_fund_attribution(store, deals=["d1"])
            self.assertEqual(len(attr.by_deal), 1)
            self.assertIn("d1", attr.by_deal)
            self.assertNotIn("d2", attr.by_deal)
        finally:
            os.unlink(path)

    def test_format_produces_string(self):
        attr = FundAttribution(
            total_value_created=10_000_000,
            by_source={
                "rcm_improvement": SourceAttribution(6_000_000, 60.0),
                "organic_growth": SourceAttribution(4_000_000, 40.0),
                "multiple_expansion": SourceAttribution(0, 0.0),
            },
            by_deal={
                "d1": DealAttribution(
                    deal_id="d1", rcm_value=6_000_000,
                    organic_growth=4_000_000, total_value_created=10_000_000,
                    entry_ebitda=50_000_000, latest_ebitda=60_000_000,
                ),
            },
        )
        text = format_fund_attribution(attr)
        self.assertIn("FUND VALUE-CREATION ATTRIBUTION", text)
        self.assertIn("$10,000,000.00", text)
        self.assertIn("Rcm Improvement", text)
        self.assertIn("d1", text)

    def test_to_dict(self):
        attr = FundAttribution(
            total_value_created=100,
            by_source={
                "rcm_improvement": SourceAttribution(60, 60.0),
                "organic_growth": SourceAttribution(40, 40.0),
                "multiple_expansion": SourceAttribution(0, 0.0),
            },
        )
        d = attr.to_dict()
        self.assertEqual(d["total_value_created"], 100)
        self.assertIn("rcm_improvement", d["by_source"])

    def test_deal_attribution_fields(self):
        da = DealAttribution(
            deal_id="x", rcm_value=3, organic_growth=2,
            multiple_expansion=0, total_value_created=5,
            entry_ebitda=10, latest_ebitda=15,
        )
        d = da.to_dict()
        self.assertEqual(d["deal_id"], "x")
        self.assertEqual(d["total_value_created"], 5)

    def test_multiple_expansion_is_zero(self):
        store, path = _tmp_store()
        try:
            _seed_deal(store, "m1")
            _seed_analysis_run(store, "m1", [], total_recurring=1_000_000)
            _seed_quarterly_actuals(store, "m1", "2025Q1", {"ebitda": 10_000_000}, plan={"ebitda": 10_000_000})

            attr = compute_fund_attribution(store)
            me = attr.by_source["multiple_expansion"]
            self.assertAlmostEqual(me.dollar_amount, 0.0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
