"""Tests for Phase M (Workflow Automation) and Phase N (Deployment + Scale).

Covers:
- infra/automation_engine.py (Prompt 63)
- analysis/refresh_scheduler.py (Prompt 64)
- domain/custom_metrics.py (Prompt 65)
- infra/backup.py (Prompt 68)
- infra/multi_fund.py (Prompt 67)
- deploy/ config files (Prompt 66)
"""
from __future__ import annotations

import gzip
import json
import os
import sqlite3
import tempfile
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rcm_mc.portfolio.store import PortfolioStore


def _make_store(tmp_dir: str) -> PortfolioStore:
    db_path = os.path.join(tmp_dir, "test.db")
    store = PortfolioStore(db_path)
    store.init_db()
    return store


# ═══════════════════════════════════════════════════════════════════════
# Automation Engine (Prompt 63)
# ═══════════════════════════════════════════════════════════════════════

class TestAutomationEngine(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(self.tmp)
        # Reset module-level cache so each test starts fresh
        from rcm_mc.infra.automation_engine import reset_tables_created_flag
        reset_tables_created_flag()

    def test_save_and_list_rule(self):
        from rcm_mc.infra.automation_engine import (
            AutomationRule, save_rule, list_rules,
        )
        rule = AutomationRule(
            rule_id="test_r1",
            name="Test rule",
            trigger="stage_change",
            conditions=[{"field": "new_stage", "op": "eq", "value": "IC"}],
            actions=[{"action_type": "send_notification"}],
            created_by="tester",
        )
        save_rule(self.store, rule)
        rules = list_rules(self.store)
        ids = [r.rule_id for r in rules]
        self.assertIn("test_r1", ids)

    def test_preset_rules_seeded(self):
        from rcm_mc.infra.automation_engine import list_rules
        rules = list_rules(self.store)
        ids = {r.rule_id for r in rules}
        self.assertIn("preset_ic_package", ids)
        self.assertIn("preset_hold_onboarding", ids)
        self.assertIn("preset_covenant_warning", ids)
        self.assertIn("preset_stale_analysis", ids)
        self.assertIn("preset_consecutive_miss", ids)
        self.assertEqual(len(ids), 5)

    def test_toggle_rule(self):
        from rcm_mc.infra.automation_engine import (
            list_rules, toggle_rule,
        )
        list_rules(self.store)  # seed presets
        ok = toggle_rule(self.store, "preset_ic_package", False)
        self.assertTrue(ok)
        rules = list_rules(self.store)
        ic = [r for r in rules if r.rule_id == "preset_ic_package"][0]
        self.assertFalse(ic.active)

    def test_toggle_nonexistent(self):
        from rcm_mc.infra.automation_engine import toggle_rule
        ok = toggle_rule(self.store, "nonexistent_xyz", True)
        self.assertFalse(ok)

    def test_evaluate_stage_change(self):
        from rcm_mc.infra.automation_engine import evaluate_rules
        results = evaluate_rules(
            self.store, "stage_change", {"new_stage": "IC"},
        )
        self.assertTrue(len(results) >= 1)
        ic_results = [r for r in results if r.rule_id == "preset_ic_package"]
        self.assertEqual(len(ic_results), 1)
        self.assertTrue(ic_results[0].success)
        self.assertEqual(ic_results[0].action_type, "rebuild_analysis")

    def test_evaluate_no_match(self):
        from rcm_mc.infra.automation_engine import evaluate_rules
        results = evaluate_rules(
            self.store, "stage_change", {"new_stage": "closed"},
        )
        # No preset matches "closed"
        self.assertEqual(len(results), 0)

    def test_evaluate_metric_threshold(self):
        from rcm_mc.infra.automation_engine import evaluate_rules
        results = evaluate_rules(
            self.store, "metric_threshold",
            {"metric_key": "covenant_headroom", "value": 0.05},
        )
        matched = [r for r in results if r.rule_id == "preset_covenant_warning"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].action_type, "send_notification")

    def test_log_table_populated(self):
        from rcm_mc.infra.automation_engine import evaluate_rules
        evaluate_rules(self.store, "stage_change", {"new_stage": "IC"})
        with self.store.connect() as con:
            count = con.execute("SELECT COUNT(*) FROM automation_log").fetchone()[0]
        self.assertGreaterEqual(count, 1)

    def test_action_result_fields(self):
        from rcm_mc.infra.automation_engine import ActionResult
        ar = ActionResult(rule_id="r1", action_type="add_tag", success=True, detail="ok")
        self.assertEqual(ar.rule_id, "r1")
        self.assertEqual(ar.action_type, "add_tag")
        self.assertTrue(ar.success)

    def test_conditions_operators(self):
        from rcm_mc.infra.automation_engine import _conditions_match
        # gt
        self.assertTrue(_conditions_match(
            [{"field": "val", "op": "gt", "value": 5}],
            {"val": 10},
        ))
        self.assertFalse(_conditions_match(
            [{"field": "val", "op": "gt", "value": 15}],
            {"val": 10},
        ))
        # contains
        self.assertTrue(_conditions_match(
            [{"field": "msg", "op": "contains", "value": "hello"}],
            {"msg": "say hello world"},
        ))
        # ne
        self.assertTrue(_conditions_match(
            [{"field": "x", "op": "ne", "value": "a"}],
            {"x": "b"},
        ))


# ═══════════════════════════════════════════════════════════════════════
# Refresh Scheduler (Prompt 64)
# ═══════════════════════════════════════════════════════════════════════

class TestRefreshScheduler(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(self.tmp)

    def _seed_packet(self, deal_id: str, created_at: str):
        """Insert a minimal analysis_runs row."""
        with self.store.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deal_id TEXT NOT NULL,
                    scenario_id TEXT,
                    as_of TEXT,
                    model_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    packet_json BLOB NOT NULL,
                    hash_inputs TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    notes TEXT
                )"""
            )
            blob = zlib.compress(json.dumps({"deal_id": deal_id}).encode())
            con.execute(
                """INSERT INTO analysis_runs
                   (deal_id, scenario_id, as_of, model_version, created_at,
                    packet_json, hash_inputs, run_id, notes)
                   VALUES (?, NULL, NULL, 'v1', ?, ?, 'h1', 'r1', NULL)""",
                (deal_id, created_at, blob),
            )
            con.commit()

    def _seed_source(self, source_name: str, last_refresh_at: str):
        with self.store.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS data_source_status (
                    source_name TEXT PRIMARY KEY,
                    last_refresh_at TEXT,
                    record_count INTEGER DEFAULT 0,
                    next_refresh_at TEXT,
                    status TEXT,
                    error_detail TEXT,
                    interval_days INTEGER DEFAULT 30
                )"""
            )
            con.execute(
                """INSERT OR REPLACE INTO data_source_status
                   (source_name, last_refresh_at, status)
                   VALUES (?, ?, 'OK')""",
                (source_name, last_refresh_at),
            )
            con.commit()

    def test_detect_stale_basic(self):
        from rcm_mc.analysis.refresh_scheduler import detect_stale_analyses
        # Packet built Jan 1, source refreshed Jan 15
        self._seed_packet("deal_A", "2026-01-01T00:00:00+00:00")
        self._seed_source("hcris", "2026-01-15T00:00:00+00:00")
        stale = detect_stale_analyses(self.store)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].deal_id, "deal_A")
        self.assertIn("hcris", stale[0].stale_sources)

    def test_detect_not_stale(self):
        from rcm_mc.analysis.refresh_scheduler import detect_stale_analyses
        # Packet built AFTER source refresh
        self._seed_packet("deal_B", "2026-02-01T00:00:00+00:00")
        self._seed_source("hcris", "2026-01-01T00:00:00+00:00")
        stale = detect_stale_analyses(self.store)
        self.assertEqual(len(stale), 0)

    def test_detect_multiple_stale_sources(self):
        from rcm_mc.analysis.refresh_scheduler import detect_stale_analyses
        self._seed_packet("deal_C", "2026-01-01T00:00:00+00:00")
        self._seed_source("hcris", "2026-01-15T00:00:00+00:00")
        self._seed_source("care_compare", "2026-01-20T00:00:00+00:00")
        stale = detect_stale_analyses(self.store)
        self.assertEqual(len(stale), 1)
        self.assertEqual(len(stale[0].stale_sources), 2)

    def test_detect_empty_tables(self):
        from rcm_mc.analysis.refresh_scheduler import detect_stale_analyses
        stale = detect_stale_analyses(self.store)
        self.assertEqual(stale, [])

    def test_staleness_sorted_oldest_first(self):
        from rcm_mc.analysis.refresh_scheduler import detect_stale_analyses
        self._seed_packet("deal_old", "2025-01-01T00:00:00+00:00")
        self._seed_packet("deal_new", "2026-03-01T00:00:00+00:00")
        self._seed_source("hcris", "2026-04-01T00:00:00+00:00")
        stale = detect_stale_analyses(self.store)
        self.assertEqual(len(stale), 2)
        self.assertEqual(stale[0].deal_id, "deal_old")


# ═══════════════════════════════════════════════════════════════════════
# Custom Metrics (Prompt 65)
# ═══════════════════════════════════════════════════════════════════════

class TestCustomMetrics(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(self.tmp)

    def test_register_and_list(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric, list_custom_metrics,
        )
        m = CustomMetric(
            metric_key="my_custom_score",
            display_name="My Custom Score",
            unit="index",
            directionality="higher_is_better",
        )
        register_custom_metric(self.store, m)
        metrics = list_custom_metrics(self.store)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].metric_key, "my_custom_score")
        self.assertEqual(metrics[0].display_name, "My Custom Score")

    def test_reject_invalid_key_uppercase(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric,
        )
        m = CustomMetric(metric_key="BadKey", display_name="Bad")
        with self.assertRaises(ValueError):
            register_custom_metric(self.store, m)

    def test_reject_invalid_key_dash(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric,
        )
        m = CustomMetric(metric_key="bad-key", display_name="Bad")
        with self.assertRaises(ValueError):
            register_custom_metric(self.store, m)

    def test_reject_builtin_conflict(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric,
        )
        # "denial_rate" is in the built-in registry
        m = CustomMetric(metric_key="denial_rate", display_name="Dup")
        with self.assertRaises(ValueError) as ctx:
            register_custom_metric(self.store, m)
        self.assertIn("RCM_METRIC_REGISTRY", str(ctx.exception))

    def test_reject_duplicate(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric,
        )
        m = CustomMetric(metric_key="unique_one", display_name="U1")
        register_custom_metric(self.store, m)
        with self.assertRaises(ValueError):
            register_custom_metric(self.store, m)

    def test_delete(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric, delete_custom_metric,
            list_custom_metrics,
        )
        m = CustomMetric(metric_key="deletable", display_name="Del")
        register_custom_metric(self.store, m)
        ok = delete_custom_metric(self.store, "deletable")
        self.assertTrue(ok)
        self.assertEqual(len(list_custom_metrics(self.store)), 0)

    def test_delete_nonexistent(self):
        from rcm_mc.domain.custom_metrics import delete_custom_metric
        ok = delete_custom_metric(self.store, "nope")
        self.assertFalse(ok)

    def test_reject_bad_directionality(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric,
        )
        m = CustomMetric(
            metric_key="some_metric",
            display_name="S",
            directionality="sideways",
        )
        with self.assertRaises(ValueError):
            register_custom_metric(self.store, m)

    def test_valid_range_round_trip(self):
        from rcm_mc.domain.custom_metrics import (
            CustomMetric, register_custom_metric, list_custom_metrics,
        )
        m = CustomMetric(
            metric_key="ranged",
            display_name="Ranged",
            valid_range=(-10.5, 200.0),
        )
        register_custom_metric(self.store, m)
        loaded = list_custom_metrics(self.store)[0]
        self.assertAlmostEqual(loaded.valid_range[0], -10.5)
        self.assertAlmostEqual(loaded.valid_range[1], 200.0)


# ═══════════════════════════════════════════════════════════════════════
# Backup (Prompt 68)
# ═══════════════════════════════════════════════════════════════════════

class TestBackup(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(self.tmp)
        # Seed some data
        self.store.upsert_deal("deal_1", name="First Deal")
        self.store.upsert_deal("deal_2", name="Second Deal")

    def test_create_backup(self):
        from rcm_mc.infra.backup import create_backup
        dest = os.path.join(self.tmp, "backups")
        path = create_backup(self.store, dest)
        self.assertTrue(path.exists())
        self.assertTrue(str(path).endswith(".db.gz"))
        self.assertIn("rcm_mc_backup_", path.name)

    def test_backup_is_valid_gzip(self):
        from rcm_mc.infra.backup import create_backup
        dest = os.path.join(self.tmp, "backups")
        path = create_backup(self.store, dest)
        # Should decompress without error
        with gzip.open(path, "rb") as f:
            data = f.read()
        self.assertGreater(len(data), 0)

    def test_restore_backup(self):
        from rcm_mc.infra.backup import create_backup, restore_backup
        dest = os.path.join(self.tmp, "backups")
        backup_path = create_backup(self.store, dest)
        target = os.path.join(self.tmp, "restored.db")
        ok = restore_backup(str(backup_path), target)
        self.assertTrue(ok)
        # Verify data survived
        con = sqlite3.connect(target)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM deals").fetchall()
        con.close()
        deal_ids = {r["deal_id"] for r in rows}
        self.assertIn("deal_1", deal_ids)
        self.assertIn("deal_2", deal_ids)

    def test_verify_backup(self):
        from rcm_mc.infra.backup import create_backup, verify_backup
        dest = os.path.join(self.tmp, "backups")
        backup_path = create_backup(self.store, dest)
        info = verify_backup(str(backup_path))
        self.assertTrue(info["valid"])
        self.assertEqual(info["integrity"], "ok")
        self.assertIn("deals", info["tables"])
        self.assertEqual(info["tables"]["deals"], 2)

    def test_verify_nonexistent(self):
        from rcm_mc.infra.backup import verify_backup
        info = verify_backup("/tmp/no_such_file.db.gz")
        self.assertFalse(info["valid"])
        self.assertIn("not found", info["error"])

    def test_restore_nonexistent(self):
        from rcm_mc.infra.backup import restore_backup
        ok = restore_backup("/tmp/no_such_file.db.gz", "/tmp/target.db")
        self.assertFalse(ok)


# ═══════════════════════════════════════════════════════════════════════
# Multi-Fund (Prompt 67)
# ═══════════════════════════════════════════════════════════════════════

class TestMultiFund(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(self.tmp)

    def test_create_and_list_fund(self):
        from rcm_mc.infra.multi_fund import Fund, create_fund, list_funds
        f = Fund(fund_id="f1", fund_name="Fund I", vintage_year=2020, fund_size=500.0)
        create_fund(self.store, f)
        funds = list_funds(self.store)
        self.assertEqual(len(funds), 1)
        self.assertEqual(funds[0].fund_id, "f1")
        self.assertEqual(funds[0].fund_name, "Fund I")
        self.assertEqual(funds[0].vintage_year, 2020)
        self.assertAlmostEqual(funds[0].fund_size, 500.0)

    def test_duplicate_fund_raises(self):
        from rcm_mc.infra.multi_fund import Fund, create_fund
        f = Fund(fund_id="f1", fund_name="Fund I", vintage_year=2020)
        create_fund(self.store, f)
        with self.assertRaises(ValueError):
            create_fund(self.store, f)

    def test_assign_deal_to_fund(self):
        from rcm_mc.infra.multi_fund import (
            Fund, create_fund, assign_deal_to_fund, deals_for_fund,
        )
        create_fund(self.store, Fund("f1", "Fund I", 2020))
        assign_deal_to_fund(self.store, "deal_A", "f1")
        assign_deal_to_fund(self.store, "deal_B", "f1")
        deals = deals_for_fund(self.store, "f1")
        self.assertEqual(set(deals), {"deal_A", "deal_B"})

    def test_assign_idempotent(self):
        from rcm_mc.infra.multi_fund import (
            Fund, create_fund, assign_deal_to_fund, deals_for_fund,
        )
        create_fund(self.store, Fund("f1", "Fund I", 2020))
        assign_deal_to_fund(self.store, "deal_A", "f1")
        assign_deal_to_fund(self.store, "deal_A", "f1")  # no error
        deals = deals_for_fund(self.store, "f1")
        self.assertEqual(len(deals), 1)

    def test_assign_to_nonexistent_fund(self):
        from rcm_mc.infra.multi_fund import assign_deal_to_fund
        with self.assertRaises(ValueError):
            assign_deal_to_fund(self.store, "deal_X", "no_fund")

    def test_funds_for_deal(self):
        from rcm_mc.infra.multi_fund import (
            Fund, create_fund, assign_deal_to_fund, funds_for_deal,
        )
        create_fund(self.store, Fund("f1", "Fund I", 2020))
        create_fund(self.store, Fund("f2", "Fund II", 2023))
        assign_deal_to_fund(self.store, "deal_A", "f1")
        assign_deal_to_fund(self.store, "deal_A", "f2")
        funds = funds_for_deal(self.store, "deal_A")
        ids = {f.fund_id for f in funds}
        self.assertEqual(ids, {"f1", "f2"})

    def test_list_funds_order(self):
        from rcm_mc.infra.multi_fund import Fund, create_fund, list_funds
        create_fund(self.store, Fund("f1", "Fund I", 2018))
        create_fund(self.store, Fund("f2", "Fund II", 2023))
        create_fund(self.store, Fund("f3", "Fund III", 2020))
        funds = list_funds(self.store)
        years = [f.vintage_year for f in funds]
        self.assertEqual(years, [2023, 2020, 2018])


# ═══════════════════════════════════════════════════════════════════════
# Deploy config files (Prompt 66)
# ═══════════════════════════════════════════════════════════════════════

class TestDeployFiles(unittest.TestCase):

    def test_dockerfile_exists(self):
        path = Path(__file__).resolve().parent.parent / "deploy" / "Dockerfile"
        self.assertTrue(path.exists(), f"Dockerfile not found at {path}")

    def test_dockerfile_has_expose(self):
        path = Path(__file__).resolve().parent.parent / "deploy" / "Dockerfile"
        content = path.read_text()
        self.assertIn("EXPOSE", content)
        self.assertIn("8080", content)

    def test_docker_compose_exists(self):
        path = Path(__file__).resolve().parent.parent / "deploy" / "docker-compose.yml"
        self.assertTrue(path.exists(), f"docker-compose.yml not found at {path}")

    def test_docker_compose_has_service(self):
        path = Path(__file__).resolve().parent.parent / "deploy" / "docker-compose.yml"
        content = path.read_text()
        self.assertIn("rcm-mc", content)
        self.assertIn("8080", content)


if __name__ == "__main__":
    unittest.main()
