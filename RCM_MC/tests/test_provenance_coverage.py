"""Provenance-coverage scan contract (BACKLOG #32 / P10).

Pins, per the backlog verification plan:
  · The scan is reproducible — same tree in, same report out (checked
    on an isolated fixture tree so concurrent edits to the live UI
    tree can't flake the assertion).
  · The number matches a HAND COUNT on two stable pages
    (exports_index_page.py, source_page.py) — see the counts spelled
    out in TestHandCountedPages.
  · Boundary behavior on a synthetic module with known call sites —
    exact totals, including the cases that earn coverage (help=,
    ck_provenance_tooltip, ck_source_link, Source:/basis: markers,
    one-hop variable resolution) and the ones that must NOT
    (bare calls, help=None, CSS flex-basis:).
  · /methodology publishes the numbers computed by THE SAME scan
    function — never a hardcoded copy that can drift.

Deliberately NOT pinned: the global percentage / call-site totals of
the live tree. Pages gain and lose KPI blocks constantly; the metric
is supposed to move. Only internal consistency is asserted globally.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from rcm_mc.ui._provenance_coverage import (
    CoverageReport,
    PageCoverage,
    cached_coverage_report,
    scan_provenance_coverage,
)


_FIXTURE_PAGE = '''\
"""Synthetic page renderer for the provenance-coverage boundary test."""
from ._chartis_kit import (
    ck_kpi_block, ck_provenance_tooltip, ck_source_link,
)


def ck_kpi_block_lookalike():
    # A *definition* whose name merely contains the substring must
    # never register; only ast.Call nodes count.
    pass


def render_fixture(kit):
    # 1 — bare: no affordance anywhere.               → NOT covered
    a = ck_kpi_block("Deals", "12", "active")
    # 2 — help= gloss.                                → covered
    b = ck_kpi_block(
        "Margin", "8.7%",
        help={"definition": "Operating margin on the patient basis."},
    )
    # 3 — value wrapped inline in ck_provenance_tooltip. → covered
    c = ck_kpi_block("NPR", ck_provenance_tooltip("NPR", "$884.69M"))
    # 4 — inline Source: marker in the sub slot.      → covered
    d = ck_kpi_block("Beds", "292", "Source: CMS HCRIS FY2022")
    # 5 — multi-line call, ck_source_link in sub.     → covered
    e = ck_kpi_block(
        "Medicare Share",
        "39.4%",
        sub=ck_source_link("CMS HCRIS"),
    )
    # 6 — one-hop local variable carrying the tooltip. → covered
    wrapped = ck_provenance_tooltip("MOIC", "2.50x", explainer="hold math")
    f = ck_kpi_block("MOIC", wrapped, "at exit")
    # 7 — f-string basis: marker.                     → covered
    fy = 2023
    g = ck_kpi_block("DAR", "41", f"basis: FY{fy} cost reports")
    # 8 — CSS flex-basis: must NOT read as a basis note. → NOT covered
    h = ck_kpi_block("Rate", "4.1%", '<span style="flex-basis:100%">u</span>')
    # 9 — explicit help=None is the deliberate opt-out. → NOT covered
    i = ck_kpi_block("Count", "7", help=None)
    # 10 — attribute-style call, bare.                → NOT covered
    j = kit.ck_kpi_block("Score", "81")
    return a + b + c + d + e + f + g + h + i + j
'''

# Hand tally of the fixture above — keep in sync with the comments.
_FIXTURE_TOTAL = 10
_FIXTURE_COVERED = 6
_FIXTURE_PCT = 60.0


class TestSyntheticBoundaries(unittest.TestCase):
    """Exact counts on a tree we fully control."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.mkdtemp(prefix="prov_cov_fixture_")
        root = Path(cls._tmp)
        (root / "fixture_page.py").write_text(_FIXTURE_PAGE, encoding="utf-8")
        # A file with zero call sites must not appear in the report.
        (root / "no_kpis_page.py").write_text(
            "VALUE = 1\n", encoding="utf-8")
        # An unparseable file (concurrent editor mid-save) must be
        # reported as skipped, never crash the scan / the page.
        (root / "broken_page.py").write_text(
            "def render(:\n    ck_kpi_block(", encoding="utf-8")
        # __pycache__ content is never a page.
        pyc = root / "__pycache__"
        pyc.mkdir()
        (pyc / "cached_copy.py").write_text(
            'x = ck_kpi_block("A", "1")\n', encoding="utf-8")
        cls.report = scan_provenance_coverage(root)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_exact_counts_on_known_tree(self) -> None:
        self.assertEqual(
            [p.page for p in self.report.pages], ["fixture_page.py"])
        page = self.report.pages[0]
        self.assertEqual(page.total_sites, _FIXTURE_TOTAL)
        self.assertEqual(page.with_provenance, _FIXTURE_COVERED)
        self.assertEqual(page.pct, _FIXTURE_PCT)

    def test_overall_mirrors_single_page(self) -> None:
        self.assertEqual(self.report.total_sites, _FIXTURE_TOTAL)
        self.assertEqual(self.report.with_provenance, _FIXTURE_COVERED)
        self.assertEqual(self.report.pct, _FIXTURE_PCT)

    def test_unparseable_file_skipped_not_fatal(self) -> None:
        self.assertEqual(self.report.skipped, ("broken_page.py",))

    def test_reproducible_same_tree_same_report(self) -> None:
        # The backlog contract: the published number is a pure
        # function of the tree. Frozen dataclasses give us deep
        # equality for free.
        again = scan_provenance_coverage(self._tmp)
        self.assertEqual(self.report, again)

    def test_pct_is_one_decimal_place(self) -> None:
        # House percentage convention (CLAUDE.md): 1dp, never 0 or 2.
        # 2/3 must come out as 66.7, not 66.66666 / 67.
        tmp = tempfile.mkdtemp(prefix="prov_cov_pct_")
        try:
            Path(tmp, "two_thirds_page.py").write_text(
                'a = ck_kpi_block("A", "1", "Source: HCRIS")\n'
                'b = ck_kpi_block("B", "2", "basis: FY2023")\n'
                'c = ck_kpi_block("C", "3")\n',
                encoding="utf-8",
            )
            report = scan_provenance_coverage(tmp)
            self.assertEqual(report.pages[0].pct, 66.7)
            self.assertEqual(report.pct, 66.7)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestHandCountedPages(unittest.TestCase):
    """The scan's numbers match a manual count on two stable pages.

    Hand count, 2026-07-07:

    exports_index_page.py — TWO ck_kpi_block calls ("Portfolio
    Exports", "Corpus Browsers"), BOTH carrying help={"definition":…}
    → 2 sites, 2 covered, 100.0%.

    source_page.py — THREE ck_kpi_block calls: "Matches Found" and
    "Theses Available" pass values built one line up via
    ck_provenance_tooltip (the one-hop rule a human hand-counter
    applies by reading the assignment), "HCRIS Universe" ("~6,000",
    "hospitals tracked") carries nothing → 3 sites, 2 covered, 66.7%.

    If one of these pages legitimately gains/loses a KPI block or an
    affordance, redo the hand count above and update the pins — that
    is the point of the test.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.by_page = {p.page: p for p in scan_provenance_coverage().pages}

    def test_exports_index_hand_count(self) -> None:
        page = self.by_page["exports_index_page.py"]
        self.assertEqual(
            (page.total_sites, page.with_provenance, page.pct),
            (2, 2, 100.0),
        )

    def test_source_page_hand_count(self) -> None:
        page = self.by_page["source_page.py"]
        self.assertEqual(
            (page.total_sites, page.with_provenance, page.pct),
            (3, 2, 66.7),
        )


class TestLiveTreeConsistency(unittest.TestCase):
    """Internal consistency of the live scan — no exact global pins
    (concurrent work moves the real numbers; it is supposed to)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report: CoverageReport = scan_provenance_coverage()

    def test_totals_are_sums_of_pages(self) -> None:
        self.assertEqual(
            self.report.total_sites,
            sum(p.total_sites for p in self.report.pages))
        self.assertEqual(
            self.report.with_provenance,
            sum(p.with_provenance for p in self.report.pages))

    def test_overall_pct_derives_from_totals(self) -> None:
        expected = round(
            100.0 * self.report.with_provenance / self.report.total_sites, 1)
        self.assertEqual(self.report.pct, expected)

    def test_every_page_internally_consistent(self) -> None:
        for p in self.report.pages:
            with self.subTest(page=p.page):
                self.assertGreaterEqual(p.total_sites, 1)
                self.assertLessEqual(p.with_provenance, p.total_sites)
                self.assertEqual(
                    p.pct,
                    round(100.0 * p.with_provenance / p.total_sites, 1))

    def test_pages_sorted_for_stable_comparison(self) -> None:
        names = [p.page for p in self.report.pages]
        self.assertEqual(names, sorted(names))

    def test_ui_tree_has_a_kpi_surface_at_all(self) -> None:
        # Sanity floor so an accidentally-empty scan (wrong root,
        # over-aggressive pre-filter) cannot pass as "consistent".
        self.assertGreater(len(self.report.pages), 50)
        self.assertGreater(self.report.total_sites, 500)


class TestMethodologyPagePublishes(unittest.TestCase):
    """/methodology renders the numbers computed by the shared scan
    function — the render and the assertion read the same cached
    report, so concurrent edits to other pages cannot flake this."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.library_page import render_library
        cls.report = cached_coverage_report()
        cls.html = render_library()

    def _row_cells(self, page_name: str) -> list:
        row_match = re.search(
            rf"<tr><td[^>]*>{re.escape(page_name)}</td>(.*?)</tr>",
            self.html,
        )
        self.assertIsNotNone(row_match, f"no table row for {page_name}")
        return re.findall(r">([\d.]+%?)</td>", row_match.group(1))

    def test_section_present_with_computed_overall(self) -> None:
        self.assertIn('id="provenance-coverage"', self.html)
        self.assertIn(f"{self.report.pct:.1f}%", self.html)
        # Both counts render (grouped per ck_fmt_number).
        self.assertIn(f"{self.report.total_sites:,}", self.html)
        self.assertIn(f"{self.report.with_provenance:,}", self.html)

    def test_explains_what_counts_as_provenance(self) -> None:
        self.assertIn("counts as covered", self.html)
        self.assertIn("ck_provenance_tooltip", self.html)
        self.assertIn("ck_source_link", self.html)

    def test_per_page_rows_match_report(self) -> None:
        for page_name in ("exports_index_page.py", "source_page.py"):
            page = {p.page: p for p in self.report.pages}[page_name]
            cells = self._row_cells(page_name)
            self.assertEqual(
                cells,
                [str(page.total_sites), str(page.with_provenance),
                 f"{page.pct:.1f}%"],
            )

    def test_appendix_hidden_under_keyword_filter(self) -> None:
        from rcm_mc.ui.library_page import render_library
        self.assertNotIn(
            'id="provenance-coverage"', render_library(q="DCF"))

    def test_methodology_dogfoods_its_own_metric(self) -> None:
        # The three KPI blocks this feature added to library_page.py
        # all carry help= glosses — the coverage page must not itself
        # be an uncovered surface.
        page = {p.page: p for p in self.report.pages}.get("library_page.py")
        self.assertIsNotNone(page)
        self.assertEqual(page.with_provenance, page.total_sites)


if __name__ == "__main__":
    unittest.main()
