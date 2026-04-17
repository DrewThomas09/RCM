"""Tests for portfolio early-warning digest (Brick 54)."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_digest import (
    build_digest,
    digest_to_frame,
    format_digest,
)
from rcm_mc.portfolio.portfolio_snapshots import _ensure_snapshot_table


def _seed_snapshots(store: PortfolioStore, rows: list) -> None:
    """Direct INSERT so we can set explicit timestamps for deterministic tests.

    Each row: (deal_id, stage, created_at, covenant_status, moic, irr).
    """
    _ensure_snapshot_table(store)
    with store.connect() as con:
        for row in rows:
            did, stage, t, cov, moic, irr = row
            # Upsert the deal row (deals table FK)
            con.execute(
                "INSERT OR IGNORE INTO deals(deal_id, name, created_at, profile_json) "
                "VALUES (?,?,?,?)",
                (did, did, t, "{}"),
            )
            con.execute(
                "INSERT INTO deal_snapshots(deal_id, stage, created_at, "
                "covenant_status, moic, irr) VALUES (?,?,?,?,?,?)",
                (did, stage, t, cov, moic, irr),
            )
        con.commit()


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class TestBuildDigest(unittest.TestCase):
    """The diff logic identifies only material crossings in the window."""

    def test_empty_store_has_no_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            events = build_digest(store, since=_iso_days_ago(30))
            self.assertEqual(events, [])

    def test_new_deal_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            # Deal first appeared 2 days ago; cutoff 7 days → new
            _seed_snapshots(store, [
                ("rural", "sourced", _iso_days_ago(2), None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].change_type, "new_deal")
            self.assertEqual(events[0].deal_id, "rural")

    def test_stage_advance_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("ccf", "sourced", _iso_days_ago(14), None, None, None),
                ("ccf", "ioi",     _iso_days_ago(1),  None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].change_type, "stage_advance")
            self.assertEqual(events[0].from_state, "sourced")
            self.assertEqual(events[0].to_state, "ioi")

    def test_stage_regress_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("xfail", "loi", _iso_days_ago(14), None, None, None),
                ("xfail", "sourced", _iso_days_ago(1), None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            types = [e.change_type for e in events]
            self.assertIn("stage_regress", types)

    def test_covenant_degrade_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("bigco", "hold", _iso_days_ago(14), "SAFE", 2.5, 0.20),
                ("bigco", "hold", _iso_days_ago(1),  "TRIPPED", 2.5, 0.20),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            types = [e.change_type for e in events]
            self.assertIn("covenant_degrade", types)
            degrade = [e for e in events if e.change_type == "covenant_degrade"][0]
            self.assertEqual(degrade.from_state, "SAFE")
            self.assertEqual(degrade.to_state, "TRIPPED")

    def test_covenant_recover_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("fixit", "hold", _iso_days_ago(14), "TIGHT", 2.0, 0.15),
                ("fixit", "hold", _iso_days_ago(1),  "SAFE",  2.0, 0.15),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            types = [e.change_type for e in events]
            self.assertIn("covenant_recover", types)

    def test_no_material_change_produces_no_events(self):
        """Same stage, same covenant → quiet portfolio → no digest noise."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("stable", "hold", _iso_days_ago(14), "SAFE", 2.5, 0.20),
                ("stable", "hold", _iso_days_ago(1),  "SAFE", 2.5, 0.20),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            self.assertEqual(events, [])

    def test_events_sorted_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("a", "sourced", _iso_days_ago(14), None, None, None),
                ("a", "ioi",     _iso_days_ago(3),  None, None, None),
                ("b", "sourced", _iso_days_ago(1),  None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            # b's new_deal (most recent) should come first
            self.assertEqual(events[0].deal_id, "b")


class TestDigestToFrame(unittest.TestCase):
    def test_empty_returns_empty_df(self):
        df = digest_to_frame([])
        self.assertTrue(df.empty)
        # Columns still present — JSON output stays consistent
        for col in ("deal_id", "change_type", "timestamp"):
            self.assertIn(col, df.columns)


class TestFormatDigest(unittest.TestCase):
    def test_empty_renders_placeholder(self):
        text = format_digest([], since=_iso_days_ago(7))
        self.assertIn("No material changes", text)

    def test_grouped_by_severity_alerts_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                # Covenant degrade → Alert
                ("bad", "hold", _iso_days_ago(14), "SAFE", 2.0, 0.15),
                ("bad", "hold", _iso_days_ago(1),  "TRIPPED", 2.0, 0.15),
                # Stage advance → Positive
                ("good", "sourced", _iso_days_ago(14), None, None, None),
                ("good", "loi",     _iso_days_ago(1),  None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            text = format_digest(events, since=_iso_days_ago(7))
            alerts_pos = text.find("Alerts")
            positive_pos = text.find("Positive changes")
            self.assertGreater(alerts_pos, 0)
            self.assertGreater(positive_pos, alerts_pos)  # alerts first

    def test_summary_line_shows_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_snapshots(store, [
                ("a", "sourced", _iso_days_ago(14), None, None, None),
                ("a", "ioi",     _iso_days_ago(1),  None, None, None),
            ])
            events = build_digest(store, since=_iso_days_ago(7))
            text = format_digest(events, since=_iso_days_ago(7))
            self.assertIn("Summary:", text)
            self.assertIn("positive changes", text.lower())


class TestDigestCLI(unittest.TestCase):
    def test_digest_subcommand_runs(self):
        import io
        import sys
        from rcm_mc.portfolio_cmd import main as pm

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_snapshots(store, [
                ("a", "sourced", _iso_days_ago(1), None, None, None),
            ])
            out, err = io.StringIO(), io.StringIO()
            so, se = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = out, err
            try:
                rc = pm(["--db", db, "digest", "--since", _iso_days_ago(7)[:10]])
            finally:
                sys.stdout, sys.stderr = so, se
            self.assertEqual(rc, 0)
            self.assertIn("Portfolio digest", out.getvalue())
            self.assertIn("a", out.getvalue())

    def test_digest_bad_since_returns_2(self):
        import io
        import sys
        from rcm_mc.portfolio_cmd import main as pm

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            err = io.StringIO()
            se = sys.stderr
            sys.stderr = err
            try:
                rc = pm(["--db", db, "digest", "--since", "not-a-date"])
            finally:
                sys.stderr = se
            self.assertEqual(rc, 2)
            self.assertIn("Invalid --since", err.getvalue())
