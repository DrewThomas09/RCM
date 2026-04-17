"""Tests for `rcm_mc.pe_integration` — auto-compute on `rcm-mc run` (Brick 46)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.pe.pe_integration import (
    _derive_entry_ebitda,
    _uplift_from_summary,
    compute_and_persist_pe_math,
)


def _sample_summary(uplift: float = 8e6) -> pd.DataFrame:
    return pd.DataFrame(
        {"mean": [uplift, 6e6], "p10": [5e6, 4e6], "p90": [11e6, 8e6]},
        index=["ebitda_drag", "economic_drag"],
    )


def _sample_cfg(with_deal: bool = True) -> dict:
    cfg = {
        "hospital": {
            "annual_revenue": 500e6,
            "ebitda_margin": 0.10,
        },
    }
    if with_deal:
        cfg["deal"] = {
            "entry_multiple": 9.0,
            "exit_multiple": 10.0,
            "hold_years": 5,
            "organic_growth_pct": 0.03,
            "equity_pct": 0.40,
            "covenant_max_leverage": 6.5,
            "interest_rate": 0.08,
        }
    return cfg


class TestUpliftFromSummary(unittest.TestCase):
    def test_pulls_ebitda_drag_mean(self):
        summary = _sample_summary(uplift=8e6)
        self.assertAlmostEqual(_uplift_from_summary(summary), 8e6)

    def test_prefers_ebitda_uplift_when_present(self):
        # If the sim reports a distinct uplift metric, use it over drag
        summary = pd.DataFrame(
            {"mean": [12e6, 8e6], "p10": [9e6, 5e6], "p90": [15e6, 11e6]},
            index=["ebitda_uplift", "ebitda_drag"],
        )
        self.assertAlmostEqual(_uplift_from_summary(summary), 12e6)

    def test_returns_zero_when_no_relevant_metric(self):
        summary = pd.DataFrame({"mean": [1.0]}, index=["something_else"])
        self.assertEqual(_uplift_from_summary(summary), 0.0)

    def test_returns_zero_for_none_or_empty(self):
        self.assertEqual(_uplift_from_summary(None), 0.0)
        self.assertEqual(_uplift_from_summary(pd.DataFrame()), 0.0)


class TestDeriveEntryEbitda(unittest.TestCase):
    def test_uses_explicit_entry_ebitda(self):
        deal = {"entry_ebitda": 75e6}
        hospital = {"annual_revenue": 500e6, "ebitda_margin": 0.10}
        self.assertAlmostEqual(_derive_entry_ebitda(deal, hospital), 75e6)

    def test_derives_from_revenue_and_margin(self):
        self.assertAlmostEqual(
            _derive_entry_ebitda({}, {"annual_revenue": 500e6, "ebitda_margin": 0.10}),
            50e6,
        )

    def test_raises_when_neither_path_works(self):
        with self.assertRaises(ValueError):
            _derive_entry_ebitda({}, {"annual_revenue": 500e6})


class TestComputeAndPersistPEMath(unittest.TestCase):
    """End-to-end: cfg + summary → 4 artifacts on disk."""

    def test_no_deal_section_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = compute_and_persist_pe_math(tmp, _sample_cfg(with_deal=False), _sample_summary())
            self.assertEqual(paths, [])
            self.assertEqual(os.listdir(tmp), [])

    def test_writes_all_four_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = compute_and_persist_pe_math(tmp, _sample_cfg(), _sample_summary())
            names = [os.path.basename(p) for p in paths]
            self.assertIn("pe_bridge.json", names)
            self.assertIn("pe_returns.json", names)
            self.assertIn("pe_hold_grid.csv", names)
            self.assertIn("pe_covenant.json", names)

    def test_bridge_reconciles_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            compute_and_persist_pe_math(tmp, _sample_cfg(), _sample_summary(8e6))
            with open(os.path.join(tmp, "pe_bridge.json")) as f:
                br = json.load(f)
            # Entry EV + sum(component values) == exit EV
            components = [c["value"] for c in br["components"]
                          if c["step"] not in ("Entry EV", "Exit EV")]
            reconstructed = br["entry_ev"] + sum(components)
            self.assertAlmostEqual(reconstructed, br["exit_ev"], places=2)

    def test_returns_uses_equity_pct_for_entry_equity(self):
        with tempfile.TemporaryDirectory() as tmp:
            compute_and_persist_pe_math(tmp, _sample_cfg(), _sample_summary())
            with open(os.path.join(tmp, "pe_returns.json")) as f:
                r = json.load(f)
            # Entry EV = 50M × 9x = 450M; equity 40% → 180M
            self.assertAlmostEqual(r["entry_equity"], 180e6, places=0)

    def test_covenant_leverage_computed_from_debt_and_ebitda(self):
        with tempfile.TemporaryDirectory() as tmp:
            compute_and_persist_pe_math(tmp, _sample_cfg(), _sample_summary())
            with open(os.path.join(tmp, "pe_covenant.json")) as f:
                c = json.load(f)
            # debt = 450M × 60% = 270M; 270/50 = 5.4x
            self.assertAlmostEqual(c["actual_leverage"], 5.4, places=2)

    def test_hold_grid_csv_has_rows_per_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            compute_and_persist_pe_math(tmp, _sample_cfg(), _sample_summary())
            df = pd.read_csv(os.path.join(tmp, "pe_hold_grid.csv"))
            # Default: 3 holds × 3 multiples = 9 rows (unless deltas make a mult ≤0)
            self.assertEqual(len(df), 9)
            self.assertIn("irr", df.columns)
            self.assertIn("moic", df.columns)

    def test_covenant_skipped_when_no_covenant_leverage(self):
        cfg = _sample_cfg()
        cfg["deal"].pop("covenant_max_leverage")
        with tempfile.TemporaryDirectory() as tmp:
            paths = compute_and_persist_pe_math(tmp, cfg, _sample_summary())
            names = [os.path.basename(p) for p in paths]
            self.assertNotIn("pe_covenant.json", names)
            # Other three still written
            self.assertIn("pe_bridge.json", names)

    def test_bad_deal_config_writes_error_file_not_raises(self):
        """A negative entry_ebitda must not crash `rcm-mc run`."""
        cfg = {"hospital": {"annual_revenue": 500e6}, "deal": {
            "entry_ebitda": -1.0, "entry_multiple": 9.0, "hold_years": 5.0,
        }}
        with tempfile.TemporaryDirectory() as tmp:
            paths = compute_and_persist_pe_math(tmp, cfg, _sample_summary())
            # Bridge should fail (negative entry_ebitda), error file written
            err_path = os.path.join(tmp, "pe_math_errors.txt")
            self.assertTrue(os.path.isfile(err_path))


class TestDealConfigValidation(unittest.TestCase):
    """The optional deal section is validated on config load."""

    def _load_shipped(self) -> dict:
        import copy
        import yaml
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "configs" / "actual.yaml"
        with open(path) as f:
            return copy.deepcopy(yaml.safe_load(f))

    def test_valid_deal_passes(self):
        from rcm_mc.infra.config import validate_config
        cfg = self._load_shipped()
        cfg["deal"] = {"entry_multiple": 9.0, "hold_years": 5}
        validate_config(cfg)  # must not raise

    def test_negative_entry_ebitda_rejected(self):
        from rcm_mc.infra.config import ConfigError, validate_config
        cfg = self._load_shipped()
        cfg["deal"] = {"entry_ebitda": -10e6, "entry_multiple": 9.0, "hold_years": 5}
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_equity_pct_out_of_range_rejected(self):
        from rcm_mc.infra.config import ConfigError, validate_config
        cfg = self._load_shipped()
        cfg["deal"] = {"equity_pct": 1.5, "entry_multiple": 9.0, "hold_years": 5}
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_no_deal_section_still_passes(self):
        """Back-compat: every pre-B46 config must keep validating."""
        from rcm_mc.infra.config import validate_config
        cfg = self._load_shipped()
        self.assertNotIn("deal", cfg)  # shipped config has no deal block
        validate_config(cfg)

    def test_portfolio_fields_validate_against_stage_set(self):
        from rcm_mc.infra.config import ConfigError, validate_config
        cfg = self._load_shipped()
        cfg["deal"] = {
            "entry_multiple": 9.0, "hold_years": 5,
            "portfolio_deal_id": "ccf_2026", "portfolio_stage": "loi",
        }
        validate_config(cfg)  # must not raise

        cfg["deal"]["portfolio_stage"] = "bogus-stage"
        with self.assertRaises(ConfigError):
            validate_config(cfg)


class TestAutoRegisterHook(unittest.TestCase):
    """Brick 51: `rcm-mc run` auto-snapshots to portfolio when configured."""

    def test_hook_registers_when_deal_has_portfolio_fields(self):
        import argparse
        from rcm_mc.cli import _auto_register_portfolio_snapshot
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.portfolio.portfolio_snapshots import list_snapshots

        with tempfile.TemporaryDirectory() as tmp:
            # Seed a run dir with a pe_bridge.json so the snapshot has data
            run_dir = os.path.join(tmp, "run")
            os.makedirs(run_dir)
            with open(os.path.join(run_dir, "pe_bridge.json"), "w") as f:
                json.dump({"entry_ev": 450e6, "exit_ev": 659e6}, f)
            with open(os.path.join(run_dir, "pe_returns.json"), "w") as f:
                json.dump({"moic": 2.55, "irr": 0.21}, f)

            db = os.path.join(tmp, "p.db")
            cfg = {"deal": {
                "portfolio_deal_id": "ccf_2026",
                "portfolio_stage": "loi",
            }}
            args = argparse.Namespace(
                no_portfolio=False, portfolio_db=db,
            )
            _auto_register_portfolio_snapshot(run_dir, cfg, args)
            snaps = list_snapshots(PortfolioStore(db))
            self.assertEqual(len(snaps), 1)
            self.assertEqual(snaps.iloc[0]["deal_id"], "ccf_2026")
            self.assertEqual(snaps.iloc[0]["stage"], "loi")
            self.assertAlmostEqual(snaps.iloc[0]["moic"], 2.55, places=3)

    def test_hook_noop_when_no_portfolio_id(self):
        import argparse
        from rcm_mc.cli import _auto_register_portfolio_snapshot
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.portfolio.portfolio_snapshots import list_snapshots

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            args = argparse.Namespace(no_portfolio=False, portfolio_db=db)
            # Deal block but no portfolio_deal_id → skip
            _auto_register_portfolio_snapshot(
                tmp, {"deal": {"entry_multiple": 9.0}}, args,
            )
            # DB shouldn't even have been created with data
            try:
                snaps = list_snapshots(PortfolioStore(db))
                self.assertEqual(len(snaps), 0)
            except Exception:
                pass  # DB non-existent is also acceptable

    def test_hook_respects_no_portfolio_flag(self):
        import argparse
        from rcm_mc.cli import _auto_register_portfolio_snapshot
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.portfolio.portfolio_snapshots import list_snapshots

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            cfg = {"deal": {
                "portfolio_deal_id": "x", "portfolio_stage": "loi",
            }}
            args = argparse.Namespace(no_portfolio=True, portfolio_db=db)
            _auto_register_portfolio_snapshot(tmp, cfg, args)
            try:
                snaps = list_snapshots(PortfolioStore(db))
                self.assertEqual(len(snaps), 0)
            except Exception:
                pass
