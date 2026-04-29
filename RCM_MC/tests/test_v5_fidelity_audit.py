"""Test the v5 fidelity audit scorer.

Pin the scoring rubric so re-calibration is intentional, not
accidental drift. The cycle 6-15 editorial-port renderers
(/library, /notes, /research, /escalations, /my/<owner>) should
clear the 70 threshold; bespoke / legacy / helper-only files
should land far below.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# tools/ is not a package; add to sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.normpath(os.path.join(_HERE, "..", "tools"))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import v5_fidelity_audit as audit  # noqa: E402


def _write(src: str) -> Path:
    """Drop ``src`` into a temp .py and return its Path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8",
    )
    tmp.write(src)
    tmp.close()
    return Path(tmp.name)


class FidelityScorerTests(unittest.TestCase):
    def test_helper_file_with_no_render_entry_returns_none(self):
        # No `def render_…` / `def page_…` etc. → the scorer skips
        # this file entirely. It's a helper, not a page.
        path = _write("""
from typing import Any

def _normalize(x: str) -> str:
    return x.strip()
""")
        try:
            self.assertIsNone(audit.score_file(path))
        finally:
            path.unlink()

    def test_minimal_chartis_shell_page_floors_above_legacy(self):
        # A bare page that only calls chartis_shell still gets the
        # +25 shell credit — well above a legacy bespoke renderer
        # that doesn't reach the editorial chrome at all.
        path = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell

def render_minimal() -> str:
    return chartis_shell("<p>hi</p>", title="Min")
""")
        try:
            s = audit.score_file(path)
            self.assertIsNotNone(s)
            self.assertTrue(s.has_chartis_shell)
            self.assertGreaterEqual(s.score, 25)
        finally:
            path.unlink()

    def test_bespoke_renderer_without_shell_excluded_from_audit(self):
        # Cycle 33 — a renderer-named function that doesn't call
        # any editorial-shell entry point is a helper / fragment
        # module, not a page. The audit excludes it from the
        # denominator entirely (returns None) rather than scoring
        # it low. This keeps the pass rate denominator honest:
        # "pages above threshold of pages that COULD reach
        # editorial chrome", not "any module with a render_X
        # function".
        path = _write("""
def render_bespoke() -> str:
    return (
        '<div style="background: red;">Run</div>'
        '<div style="background: blue;">Click here</div>'
    )
""")
        try:
            s = audit.score_file(path)
            self.assertIsNone(s)
        finally:
            path.unlink()

    def test_full_editorial_page_clears_threshold(self):
        # Mirror the cycle 6-15 port shape: shell + several ck_*
        # primitives + italic_word + clean. Expect score >= 70.
        path = _write("""
from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_section_intro, ck_search_hero, ck_filter_sidebar,
    ck_results_header, ck_section_header, ck_severity_panel,
    ck_affirm_empty,
)

def render_full() -> str:
    intro = ck_section_intro(
        eyebrow="EYEBROW",
        headline="The portfolio reveals the day.",
        italic_word="reveals",
    )
    hero = ck_search_hero(action="/x", name="q")
    rail = ck_filter_sidebar(groups=[], form_action="/x")
    head = ck_results_header(count=0, label="Items")
    section = ck_section_header("Title")
    panel = ck_severity_panel(tone="red", label="x", count=0, rows_html="")
    empty = ck_affirm_empty(headline="x", body="y")
    body = intro + hero + rail + head + section + panel + empty
    return chartis_shell(body, title="X")
""")
        try:
            s = audit.score_file(path)
            self.assertIsNotNone(s)
            self.assertGreaterEqual(
                s.score, 70,
                f"Editorial page must clear 70; got {s.score} "
                f"(notes: {s.notes})",
            )
        finally:
            path.unlink()

    def test_lazy_label_drops_score(self):
        # Same minimal shell, but with one lazy label — should
        # surface the penalty.
        good = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell

def render_x() -> str:
    return chartis_shell("<p>Run analysis</p>", title="X")
""")
        bad = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell

def render_x() -> str:
    return chartis_shell("<button>Run</button>", title="X")
""")
        try:
            s_good = audit.score_file(good)
            s_bad = audit.score_file(bad)
            self.assertGreater(s_good.score, s_bad.score)
            self.assertEqual(s_bad.lazy_label_count, 1)
        finally:
            good.unlink(); bad.unlink()

    def test_inline_style_drops_score(self):
        clean = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header

def render_x() -> str:
    return chartis_shell(ck_section_header("Title"), title="X")
""")
        # Inline-style penalty scales with the count of `style="`
        # substrings IN THE SOURCE — runtime loops don't count.
        # Repeat the literal to make the penalty visible.
        styled = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell

def render_x() -> str:
    body = (
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
        '<div style="background:red;padding:10px;">x</div>'
    )
    return chartis_shell(body, title="X")
""")
        try:
            s_clean = audit.score_file(clean)
            s_styled = audit.score_file(styled)
            self.assertGreater(s_clean.score, s_styled.score)
            self.assertGreater(s_styled.inline_style_count, 5)
        finally:
            clean.unlink(); styled.unlink()

    def test_editorial_div_with_ck_class_not_penalized(self):
        # ck_* class divs are editorial — the bespoke-div penalty
        # must NOT count them. Otherwise every editorial page would
        # be self-penalized for using its own primitives.
        path = _write("""
from rcm_mc.ui._chartis_kit import chartis_shell

def render_x() -> str:
    body = '<div class="ck-rail-layout"><div class="ck-rail-content">x</div></div>'
    return chartis_shell(body, title="X")
""")
        try:
            s = audit.score_file(path)
            self.assertEqual(s.bespoke_div_count, 0)
        finally:
            path.unlink()

    def test_real_my_dashboard_page_clears_threshold(self):
        # End-to-end check against the real cycle-15 port. If this
        # ever drops below 70 the threshold or rubric drifted.
        repo_root = Path(_HERE).parent
        target = repo_root / "rcm_mc" / "ui" / "my_dashboard_page.py"
        s = audit.score_file(target)
        self.assertIsNotNone(s)
        self.assertGreaterEqual(
            s.score, 70,
            f"my_dashboard_page must clear 70; got {s.score} "
            f"(notes: {s.notes})",
        )

    def test_real_escalations_page_clears_threshold(self):
        repo_root = Path(_HERE).parent
        target = repo_root / "rcm_mc" / "ui" / "escalations_page.py"
        s = audit.score_file(target)
        self.assertIsNotNone(s)
        self.assertGreaterEqual(s.score, 70)

    def test_audit_tree_normalizes_paths_to_repo_relative(self):
        repo_root = Path(_HERE).parent
        ui_dir = repo_root / "rcm_mc" / "ui"
        scores = audit.audit_tree(ui_dir, repo_root=repo_root.parent)
        self.assertGreater(len(scores), 0)
        # Every path should start with `RCM_MC/rcm_mc/ui/` (relative
        # to the parent of repo_root in this layout).
        for s in scores:
            self.assertNotIn("/Users/", s.file)
            self.assertNotIn("\\", s.file)

    def test_main_exit_zero_when_all_pass_with_low_threshold(self):
        # With threshold 0, every renderer passes → exit 0.
        # We bypass the human banner with --json so the test doesn't
        # depend on stdout structure.
        rc = audit.main(["--threshold", "0", "--json"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
