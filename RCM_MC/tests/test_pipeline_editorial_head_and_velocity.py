"""Editorial head + stage-velocity contract for /pipeline (sweep batch 2).

Pins the Tier-1 5-block anatomy on /pipeline AND the new
functionality lift — median days in stage + stalled count + velocity
verdict — so a later edit can't silently roll them back. Pin-down
only on the head + funnel block; the table/searches/activity sections
remain free to evolve.

Pins:
  · ONE <h1> on the page (the #1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph at the masthead.
  · Mono meta-line quotes REAL counts (hospital count, active count,
    diligence count, saved-search count) — never hard-coded.
  · Italic-first-phrase serif lede.
  · 4-bucket status-dot legend.
  · Funnel adds a head-row labeling the new columns + per-row
    Med-d (median days in stage) + Stalled (no-activity > 30 days)
    cells. Every value computed from real pipeline data.
  · Velocity verdict quotes a real number (count of stalled
    hospitals + worst stage when > 0).
  · The spec-forbidden "card with left-border accent" trope is gone
    from the active funnel row (active depth is by background tone
    only).
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.data.pipeline import (
    _ensure_tables,
    add_to_pipeline,
    save_search,
    update_stage,
)
from rcm_mc.portfolio.store import PortfolioStore


def _seed_pipeline(stages=("screening", "loi", "diligence")) -> str:
    """Create a temp SQLite + populate one hospital at each given
    stage. Returns the db path; caller must os.unlink when done.

    Explicitly con.commit() at the end — the pipeline data
    functions rely on the caller to flush the implicit transaction,
    and the PortfolioStore.connect() context manager only closes
    (it doesn't commit). Without the commit, render_pipeline's
    fresh connection sees zero rows.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = PortfolioStore(path)
    with store.connect() as con:
        _ensure_tables(con)
        for i, stage in enumerate(stages, start=1):
            add_to_pipeline(
                con,
                ccn=f"{i:06d}",
                hospital_name=f"Hospital {i}",
                state="AL",
                beds=200 + i * 100,
                stage=stage,
            )
        save_search(
            con,
            name="test search",
            filters={"state": "AL"},
            created_by="analyst",
        )
        con.commit()
    return path


class PipelineEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.db = _seed_pipeline()
        from rcm_mc.ui.pipeline_page import render_pipeline
        cls.html = render_pipeline(cls.db)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls.db)
        except OSError:
            pass

    def test_one_h1_per_page(self) -> None:
        # #1036 a11y invariant.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block_present(self) -> None:
        self.assertIn('class="pp-head"', self.html)

    def test_eyebrow_has_green_dash(self) -> None:
        # Spec Tier-2 §2.1 — eyebrow text follows the 24×1px dash.
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*DEAL PIPELINE',
        )

    def test_h1_present(self) -> None:
        self.assertIn("<h1>Deal Pipeline</h1>", self.html)

    def test_meta_line_quotes_real_counts(self) -> None:
        # Seeded 3 hospitals (all active — none in closed/passed), 1
        # in diligence, 1 saved search.
        self.assertRegex(
            self.html,
            r'class="meta">\s*3 HOSPITALS\s*·\s*3 ACTIVE\s*·\s*'
            r'1 IN DILIGENCE\s*·\s*1 SAVED SEARCH<',
        )

    def test_lede_italic_first_phrase(self) -> None:
        # Spec §2.3 — italic first phrase, serif body.
        self.assertIn(
            "<em>How prospects flow from screening to close.</em>",
            self.html,
        )

    def test_status_dot_legend_present(self) -> None:
        # 4-bucket legend per spec Tier-2 §2.4.
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
                f"missing legend dot: {cls_name}",
            )

    def test_no_left_border_accent_on_active_funnel_row(self) -> None:
        # Tier-4 don'ts — the active funnel row used to carry
        # `border-left-color:var(--sc-teal,#155752)`; depth must
        # now come from background-tone only.
        self.assertNotIn(
            "border-left-color:var(--sc-teal,#155752)",
            self.html,
        )


class PipelineFunnelVelocityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.db = _seed_pipeline()
        from rcm_mc.ui.pipeline_page import render_pipeline
        cls.html = render_pipeline(cls.db)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls.db)
        except OSError:
            pass

    def test_funnel_head_row_present(self) -> None:
        # The head row labels each column so the partner doesn't have
        # to hover anything.
        self.assertIn('class="ck-funnel-head"', self.html)
        for label in ("Stage", "Count", "Conv %", "Med d", "Stalled"):
            self.assertIn(f">{label}<", self.html)

    def test_funnel_row_carries_new_columns(self) -> None:
        # Per-row Med-d + Stalled cells render with the expected
        # class names so they're styleable + queryable.
        self.assertIn('class="ck-funnel-median"', self.html)
        # Stalled cell can be either the bare "ck-funnel-stalled" or
        # the "ck-funnel-stalled ck-funnel-stalled-on" coral variant.
        self.assertIn("ck-funnel-stalled", self.html)

    def test_velocity_verdict_present(self) -> None:
        # Verdict line that auto-derives from real counts.
        self.assertIn("<strong>Velocity:</strong>", self.html)

    def test_velocity_verdict_quotes_real_state(self) -> None:
        # Freshly-added hospitals have no stalled rows (>30 days).
        # The verdict must read "Healthy flow — no hospitals stalled
        # ...", quoting that real state — never editorial filler.
        self.assertRegex(
            self.html,
            r"Velocity:.*Healthy flow.*no hospitals stalled",
        )


class PipelineEmptyStateTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls.db = path
        store = PortfolioStore(path)
        with store.connect() as con:
            _ensure_tables(con)
        from rcm_mc.ui.pipeline_page import render_pipeline
        cls.html = render_pipeline(cls.db)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls.db)
        except OSError:
            pass

    def test_empty_state_keeps_editorial_head(self) -> None:
        # Empty pipeline still renders the 5-block head — same shape
        # as the populated path so the layout doesn't flicker.
        self.assertIn('class="pp-head"', self.html)
        self.assertIn("<h1>Deal Pipeline</h1>", self.html)
        self.assertIn(
            "<em>How prospects flow from screening to close.</em>",
            self.html,
        )

    def test_empty_state_velocity_verdict_honest(self) -> None:
        # No hospitals → verdict must say so plainly, never fabricate
        # "0 stalled (no activity in 30 days)" filler.
        self.assertRegex(
            self.html,
            r"Velocity:.*No hospitals in the pipeline yet",
        )


if __name__ == "__main__":
    unittest.main()
