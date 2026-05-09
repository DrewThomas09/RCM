"""b163 — regression for the literal `<span class="mn">…</span>` leak.

PROMPTS.md Phase 1 / Prompt 1: `/library/market-rates` and
`/research/backtest` historically rendered escaped span markup as
visible text because chartis-kit value formatters returned HTML
strings that were then html.escape()'d a second time downstream.

The fix (commits 84a6e21, a77d47c, e11ce2e) sanitised values inside
`ck_kpi_block` and removed the redundant escape on the data path.
This test pins that behaviour: neither page may emit `&lt;span` —
the unambiguous escaped-open-tag signal — under either UI-flag
value.
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest


def _render(module_path: str, fn_name: str, flag_value: str) -> str:
    """Render a page after forcing CHARTIS_UI_V2 and reloading the kit."""
    if flag_value is None:
        os.environ.pop("CHARTIS_UI_V2", None)
    else:
        os.environ["CHARTIS_UI_V2"] = flag_value
    # Drop cached kit + page modules so the flag re-reads on import.
    for name in list(sys.modules):
        if (
            name.startswith("rcm_mc.ui._chartis_kit")
            or name == module_path
            or name.startswith("rcm_mc.ui.data_public.")
        ):
            sys.modules.pop(name, None)
    mod = importlib.import_module(module_path)
    return getattr(mod, fn_name)()


class LiteralSpanLeakRegression(unittest.TestCase):
    """Both pages must render formatter output as live HTML, never as
    visible escaped text."""

    SENTINEL = "&lt;span"  # any escaped span open-tag is a leak

    def _assert_no_escaped_span(self, html: str, where: str) -> None:
        self.assertNotIn(
            self.SENTINEL,
            html,
            f"{where}: literal escaped span markup leaked into the page body",
        )

    def test_market_rates_no_escaped_span_legacy(self) -> None:
        html = _render(
            "rcm_mc.ui.data_public.market_rates_page",
            "render_market_rates",
            flag_value="0",
        )
        self._assert_no_escaped_span(html, "/library/market-rates [legacy]")

    def test_market_rates_no_escaped_span_v2(self) -> None:
        html = _render(
            "rcm_mc.ui.data_public.market_rates_page",
            "render_market_rates",
            flag_value="1",
        )
        self._assert_no_escaped_span(html, "/library/market-rates [v2]")

    def test_backtest_no_escaped_span_legacy(self) -> None:
        html = _render(
            "rcm_mc.ui.data_public.backtest_page",
            "render_backtest",
            flag_value="0",
        )
        self._assert_no_escaped_span(html, "/research/backtest [legacy]")

    def test_backtest_no_escaped_span_v2(self) -> None:
        html = _render(
            "rcm_mc.ui.data_public.backtest_page",
            "render_backtest",
            flag_value="1",
        )
        self._assert_no_escaped_span(html, "/research/backtest [v2]")


class BankruptcySurvivorHeaderLayout(unittest.TestCase):
    """PROMPTS.md Phase 1 / Prompt 2: the eyebrow and the H1 must stack
    vertically inside a single `.page-header` wrapper so the H1 cannot
    float into a sibling grid column on any future shell change."""

    def test_eyebrow_and_h1_share_page_header(self) -> None:
        from rcm_mc.ui.bankruptcy_survivor_page import render_scan_landing

        html = render_scan_landing()
        # Find the page-header block.
        marker = "<div class='page-header'>"
        start = html.find(marker)
        self.assertNotEqual(start, -1, "page-header wrapper missing")
        end = html.find("</div>", start) + len("</div>")
        # Cheaply locate the matching closing div: page-header has two
        # nested divs, so step past the eyebrow's closer to find the
        # outer one.
        scan = html[start + len(marker):]
        depth = 1
        i = 0
        while depth and i < len(scan):
            if scan.startswith("<div", i):
                depth += 1
                i += 4
            elif scan.startswith("</div>", i):
                depth -= 1
                if depth == 0:
                    break
                i += 6
            else:
                i += 1
        end = start + len(marker) + i + len("</div>")
        block = html[start:end]
        self.assertIn("<div class='eyebrow'>", block)
        self.assertIn("<h1>", block)
        eyebrow_at = block.find("<div class='eyebrow'>")
        h1_at = block.find("<h1>")
        self.assertLess(eyebrow_at, h1_at, "H1 must follow the eyebrow")

    def test_page_header_uses_flex_column(self) -> None:
        from rcm_mc.ui.bankruptcy_survivor_page import render_scan_landing

        html = render_scan_landing()
        # The CSS rule must declare flex-direction: column so the two
        # children stack regardless of viewport width.
        self.assertIn("flex-direction:column", html.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
