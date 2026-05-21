"""Two-view composition seam + Part-4 editorial guardrails.

PR #4 of the two-view Command Center work. ``render_command_center`` is
now a thin dispatcher: it builds the pure data model and routes the
body through :func:`_compose_command_center`, which branches on the
per-request workspace mode (Chartis Consulting / internal vs PE
Partner). The branch exists *now* so the later partner-v2 divergence is
a localized change rather than a render-path rewrite.

Two contracts are pinned:

  * **Seam** — the dispatcher selects the internal composition for
    CONSULTING and the partner composition otherwise, and the two
    bodies are identical today (no structural divergence has shipped).
    This test flips to asserting divergence when partner-v2 lands.
  * **Part-4 editorial guardrails** — both composition branches stay in
    the editorial register: editorial section anchors present, no
    bright/orange dashboard-marketing hex, and a declarative voice
    (no exclamation hype). These guard against a future composition
    re-introducing the "weirdly modern" dashboard-marketing chrome the
    two-view rework is meant to retire.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.command_center import (
    build_command_center_model,
    render_command_center,
    _compose_command_center,
    _compose_internal,
    _compose_partner,
)
from rcm_mc.ui._workspace_mode import (
    CONSULTING,
    PARTNER,
    set_workspace_mode,
)


def _frame(n: int = 40, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "state": rng.choice(["CA", "TX", "NY", "FL"], n),
        "beds": rng.integers(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e6, 3e8, n),
        "operating_expenses": rng.uniform(1e6, 3e8, n),
    })


class CompositionSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "p.db")
        store = PortfolioStore(self.db_path)
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS deals ("
                "deal_id TEXT PRIMARY KEY, name TEXT, "
                "profile_json TEXT, created_at TEXT, archived_at TEXT)"
            )
            con.commit()
        # Reset the per-request mode contextvar between tests so order
        # can't leak a mode set by an earlier case.
        self.addCleanup(set_workspace_mode, PARTNER)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _model(self):
        return build_command_center_model(_frame(), self.db_path)

    def test_dispatcher_routes_consulting_to_internal(self) -> None:
        m = self._model()
        self.assertEqual(
            _compose_command_center(m, CONSULTING), _compose_internal(m))

    def test_dispatcher_routes_partner_to_partner(self) -> None:
        m = self._model()
        self.assertEqual(
            _compose_command_center(m, PARTNER), _compose_partner(m))

    def test_unknown_mode_falls_through_to_partner(self) -> None:
        m = self._model()
        self.assertEqual(
            _compose_command_center(m, "nonsense"), _compose_partner(m))

    def test_no_structural_divergence_yet(self) -> None:
        # Both views share one composition today. When partner-v2 lands
        # this assertion flips to assertNotEqual.
        m = self._model()
        self.assertEqual(_compose_internal(m), _compose_partner(m))

    def test_both_modes_render_full_page(self) -> None:
        set_workspace_mode(PARTNER)
        self.assertIn("PE Desk", render_command_center(_frame(), self.db_path))
        set_workspace_mode(CONSULTING)
        self.assertIn("PE Desk", render_command_center(_frame(), self.db_path))


class Part4EditorialGuardrailTests(unittest.TestCase):
    """The composition must stay editorial — no dashboard-marketing
    chrome creeping back in as the views diverge."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "p.db")
        store = PortfolioStore(self.db_path)
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS deals ("
                "deal_id TEXT PRIMARY KEY, name TEXT, "
                "profile_json TEXT, created_at TEXT, archived_at TEXT)"
            )
            con.commit()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _bodies(self):
        m = build_command_center_model(_frame(), self.db_path)
        return {"internal": _compose_internal(m), "partner": _compose_partner(m)}

    def test_editorial_section_anchors_present(self) -> None:
        for view, body in self._bodies().items():
            with self.subTest(view=view):
                self.assertIn("ck-eyebrow", body)        # editorial anchor chrome
                self.assertIn("COMMAND CENTER", body)    # page-title eyebrow

    def test_no_bright_orange_marketing_hex(self) -> None:
        for view, body in self._bodies().items():
            low = body.lower()
            with self.subTest(view=view):
                self.assertNotIn("ff9900", low)
                self.assertNotIn("ffa500", low)
                self.assertNotIn("ff6600", low)

    def test_declarative_voice_no_exclamation(self) -> None:
        for view, body in self._bodies().items():
            with self.subTest(view=view):
                self.assertNotIn("!", body)


if __name__ == "__main__":
    unittest.main()
