"""Wave-28: phantom-table query audit.

Wave-27 found /portfolio/monitor silently losing all health scores to
a bare except around a bad column name. A sweep of every raw SELECT
in the UI found four more queries against tables that DON'T EXIST:

  - ``deal_health_scores`` (real table: deal_health_history) — the
    home page's health distribution always showed its empty state.
  - ``alerts`` (real tables: alert_history + alert_acks) — the home
    page alert panel + KPI count, the command center alert list, and
    the portfolio monitor's alert load were all permanently empty.

These tests run the EXACT queries from the page sources against the
real schemas (created by the same _ensure_table code production
uses), so any future schema drift fails loudly instead of silently.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore


def _extract_queries(path: str) -> list:
    """Pull every concatenated double-quoted SELECT from a source file."""
    src = Path(path).read_text()
    out = []
    for m in re.finditer(r'execute\(\s*((?:"[^"]*"\s*\n?\s*)+)', src):
        q = "".join(re.findall(r'"([^"]*)"', m.group(1)))
        if q.strip().upper().startswith("SELECT"):
            out.append(q)
    return out


class DeadTableQueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(str(Path(self.tmp.name) / "t.db"))
        # Create the REAL schemas via the production ensure functions.
        from rcm_mc.alerts.alert_acks import _ensure_table as ensure_acks
        from rcm_mc.alerts.alert_history import (
            _ensure_table as ensure_history,
        )
        from rcm_mc.deals.health_score import _ensure_history_table
        ensure_history(self.store)
        ensure_acks(self.store)
        _ensure_history_table(self.store)
        self.store.upsert_deal("d1")
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO alert_history VALUES "
                "('covenant','d1','k1','2026-06-01','2026-06-10',"
                "'red','Covenant trip','detail',3)")
            con.execute(
                "INSERT INTO deal_health_history VALUES "
                "('d1','2026-06-10',72,'amber')")
            con.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def _run_selects(self, path: str, must_mention: str) -> int:
        """Execute every SELECT in ``path`` that mentions a keyword."""
        ran = 0
        queries = [q for q in _extract_queries(path) if must_mention in q]
        self.assertTrue(queries, f"no {must_mention} SELECTs in {path}")
        with self.store.connect() as con:
            for q in queries:
                con.execute(q.replace("?", "'x'")).fetchall()  # must not raise
                ran += 1
        return ran

    def test_home_page_alert_and_health_queries_run(self):
        self._run_selects("rcm_mc/ui/chartis/home_page.py", "alert_history")
        self._run_selects(
            "rcm_mc/ui/chartis/home_page.py", "deal_health_history")

    def test_command_center_alert_query_runs(self):
        self._run_selects("rcm_mc/ui/command_center.py", "alert_history")

    def test_portfolio_monitor_alert_query_runs(self):
        self._run_selects(
            "rcm_mc/ui/portfolio_monitor_page.py", "alert_history")

    def test_no_ui_query_references_phantom_tables(self):
        import glob
        offenders = []
        for f in glob.glob("rcm_mc/ui/**/*.py", recursive=True):
            for q in _extract_queries(f):
                if re.search(r"\bFROM alerts\b", q) or \
                        "deal_health_scores" in q:
                    offenders.append((f, q[:80]))
        self.assertEqual(offenders, [])

    def test_home_page_deadlines_query_runs(self):
        """Wave-29: deal_deadlines has ``label``, not ``title`` — the
        home page deadlines panel was always empty."""
        from rcm_mc.deals.deal_deadlines import _ensure_table as ensure_dl
        ensure_dl(self.store)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deal_deadlines "
                "(deal_id, label, due_date, created_at) "
                "VALUES ('d1','QoE call','2026-06-12','2026-06-01')")
            con.commit()
        queries = [q for q in _extract_queries(
            "rcm_mc/ui/chartis/home_page.py") if "deal_deadlines" in q]
        self.assertTrue(queries)
        with self.store.connect() as con:
            rows = con.execute(queries[0], ("2026-06-18",)).fetchall()
        self.assertEqual(str(rows[0]["title"]), "QoE call")

    def test_settings_ai_cost_queries_run(self):
        """Wave-29: llm_calls has ``cost_usd``, not cost_usd_estimate."""
        from rcm_mc.ai.llm_client import _ensure_tables as ensure_llm
        ensure_llm(self.store)
        queries = [q for q in _extract_queries(
            "rcm_mc/ui/settings_ai_page.py") if "llm_calls" in q]
        self.assertEqual(len(queries), 2)
        with self.store.connect() as con:
            for q in queries:
                con.execute(q).fetchall()  # must not raise

    def test_monitor_snapshot_query_runs(self):
        """Wave-29: deal_snapshots has no ``snapshot_json`` column."""
        from rcm_mc.portfolio.portfolio_snapshots import (
            _ensure_snapshot_table as ensure_snap,
        )
        ensure_snap(self.store)
        queries = [q for q in _extract_queries(
            "rcm_mc/ui/portfolio_monitor_page.py")
            if "deal_snapshots" in q]
        self.assertTrue(queries)
        with self.store.connect() as con:
            for q in queries:
                con.execute(q).fetchall()  # must not raise

    def test_unacked_join_excludes_acked_rows(self):
        q = [x for x in _extract_queries("rcm_mc/ui/command_center.py")
             if "alert_history" in x][0]
        with self.store.connect() as con:
            self.assertEqual(len(con.execute(q).fetchall()), 1)
            con.execute(
                "INSERT INTO alert_acks "
                "(kind, deal_id, trigger_key, acked_at) "
                "VALUES ('covenant','d1','k1','2026-06-11')")
            self.assertEqual(len(con.execute(q).fetchall()), 0)


if __name__ == "__main__":
    unittest.main()
