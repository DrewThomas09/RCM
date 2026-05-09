"""tests for ``rcm_mc.ui._ui_kit.recent_runs``.

PROMPTS.md Phase 2 / Prompt 14: per-module continuity rail. Tests
cover empty list, one row, five rows, and rows with/without the
optional ``summary`` field.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import recent_runs


def _run(deal: str, **extra) -> dict:
    return {"deal_name": deal, "ran_at": "2026-05-09", "href": f"/run/{deal}", **extra}


class EmptyState(unittest.TestCase):

    def test_empty_list_renders_default_copy(self) -> None:
        html = recent_runs([], module="Bridge audits")
        self.assertIn("recent-runs-empty", html)
        self.assertIn("No Bridge audits yet", html)

    def test_custom_empty_label_overrides(self) -> None:
        html = recent_runs(
            [], module="Bridge audits",
            empty_label="Nothing here — run an audit above.",
        )
        self.assertIn("Nothing here", html)
        self.assertNotIn("No Bridge audits yet", html)


class PopulatedRows(unittest.TestCase):

    def test_one_row(self) -> None:
        html = recent_runs([_run("Aurora")], module="Bridge audits")
        # One <a> row, no empty-state class.
        self.assertEqual(html.count('class="recent-runs-row"'), 1)
        self.assertNotIn("recent-runs-empty", html)
        self.assertIn("Aurora", html)
        self.assertIn('href="/run/Aurora"', html)

    def test_five_rows(self) -> None:
        runs = [_run(f"Deal{i}") for i in range(5)]
        html = recent_runs(runs, module="Monte Carlo runs")
        self.assertEqual(html.count('class="recent-runs-row"'), 5)


class SummaryOptional(unittest.TestCase):

    def test_summary_renders_when_present(self) -> None:
        html = recent_runs(
            [_run("Aurora", summary="MOIC P50 2.80x")],
            module="Bridge audits",
        )
        self.assertIn("recent-runs-summary", html)
        self.assertIn("MOIC P50 2.80x", html)

    def test_summary_omitted_when_absent(self) -> None:
        html = recent_runs(
            [_run("Aurora")],
            module="Bridge audits",
        )
        self.assertNotIn("recent-runs-summary", html)


class HtmlEscaping(unittest.TestCase):

    def test_module_label_escaped(self) -> None:
        html = recent_runs([], module="<x>")
        self.assertIn("&lt;x&gt;", html)

    def test_deal_name_escaped(self) -> None:
        html = recent_runs(
            [{"deal_name": "<b>", "ran_at": "x", "href": "/x"}],
            module="m",
        )
        self.assertIn("&lt;b&gt;", html)


if __name__ == "__main__":
    unittest.main()
