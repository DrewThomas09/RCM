"""Guard against partial-refresh vintage drift across market_reports/.

The prior incident: a refresh wave moved 9 of 14 IFT modules to the CMS/RAND
GADCS *Year 1-Year 4* cohort appendix (Dec 2025) and left 5 asserting the
superseded *Year 1-2* figures (Dec 2024) as current. The result was worse
than uniformly-stale data: two pages of the same report quoted different
values for the same published mean, so a reader had no way to tell which one
the platform believed. The same thing happened independently with the CMS
CERT ambulance improper-payment rate, where 3 modules carried the 2025
supplemental release and 1 still carried 2024.

A superseded figure is not banned outright -- naming what a number replaced
is good provenance writing, and several modules deliberately do it
("SUPERSEDES the Year 1-2 cohort figures ($2,673 ...)"). What is banned is
asserting one as CURRENT. So the rule enforced here is: a superseded token
may appear only inside explicit historical framing.

If a genuinely new release supersedes today's figures, update the CURRENT
table below and move the old values into SUPERSEDED -- do not delete the
check.
"""
from __future__ import annotations

import pathlib
import re
import unittest

_MR = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "market_reports"

# Figures the platform currently asserts, each verified against the primary
# PDF (not a secondary summary) on 2026-08-03.
CURRENT = {
    # CMS/RAND GADCS Report Appendix, Year 1-Year 4 Cohort Analysis
    # (posted 2025-12-09, data reported through 2025-05-15).
    "gadcs_cost_mean_all": "2,763",       # n=9,599, median 1,355
    "gadcs_cost_mean_forprofit": "1,912",  # n=1,869
    "gadcs_cost_mean_gov": "3,167",        # n=5,121
    "gadcs_revenue_mean_all": "1,268",     # n=9,599, median 613
    # CMS CERT 2025 Medicare FFS Supplemental Improper Payment Data
    # (published 2026-01-24; claims 2023-07-01 to 2024-06-30).
    "cert_ambulance_rate": "10.4%",
    "cert_ambulance_projected": "452.6",
    "cert_insufficient_doc": "46.7%",
    "cert_medical_necessity": "24.9%",
}

# Values a newer official release has replaced. Key = human label used in the
# failure message so a future maintainer knows which release to consult.
SUPERSEDED = {
    "2,673": "GADCS Y1-2 mean cost/transport (superseded by $2,763, Y1-4)",
    "3,127": "GADCS Y1-2 governmental cost (superseded by $3,167, Y1-4)",
    "1,788": "GADCS Y1-2 for-profit/unknown cost (superseded by $1,912, Y1-4)",
    "1,147": "GADCS Y1-2 mean revenue/transport (superseded by $1,268, Y1-4)",
    "13.2%": "CERT 2024 ambulance improper rate (superseded by 10.4%, 2025)",
    "595.1": "CERT 2024 ambulance projected $ (superseded by $452.6M, 2025)",
    "63.5%": "CERT 2024 insufficient-doc share (superseded by 46.7%, 2025)",
}

# Phrases that mark a superseded figure as history rather than an assertion.
# Matched case-insensitively against the offending line plus the two lines
# above it, because these modules wrap prose and a docstring sentence often
# carries the marker on an earlier line than the number.
_HISTORY_MARKERS = (
    "supersede",
    "previously",
    "up from",
    "was ",
    "prior to",
    "no longer",
    "replaced",
    "mean of $",
)
_LOOKBACK = 2


def _is_historical(lines: list[str], idx: int) -> bool:
    window = " ".join(lines[max(0, idx - _LOOKBACK): idx + 1]).lower()
    return any(marker in window for marker in _HISTORY_MARKERS)


class SupersededFiguresAreHistoricalOnly(unittest.TestCase):
    def test_no_module_asserts_a_superseded_figure_as_current(self):
        offenders = []
        for path in sorted(_MR.rglob("*.py")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines):
                for token, why in SUPERSEDED.items():
                    if token in line and not _is_historical(lines, idx):
                        offenders.append(
                            f"{path.relative_to(_MR.parent.parent)}:{idx + 1}"
                            f" asserts {token!r} as current -- {why}\n"
                            f"    {line.strip()[:110]}"
                        )
        self.assertEqual(
            [], offenders,
            "Superseded figures asserted as current in "
            f"{len(offenders)} place(s). Either refresh them to the current "
            "release or wrap them in explicit historical framing:\n"
            + "\n".join(offenders),
        )


class CurrentFiguresAgreeAcrossModules(unittest.TestCase):
    """The refreshed values must actually be present, or the guard above
    would pass trivially on a codebase that had dropped the claims entirely."""

    def test_current_figures_are_still_cited_somewhere(self):
        corpus = "\n".join(
            p.read_text(encoding="utf-8") for p in _MR.rglob("*.py")
        )
        for name, token in CURRENT.items():
            with self.subTest(figure=name):
                self.assertIn(
                    token, corpus,
                    f"{name} ({token}) is cited nowhere in market_reports/ -- "
                    "if a newer release superseded it, move it into "
                    "SUPERSEDED rather than deleting the entry.",
                )

    def test_primary_sources_are_cited_by_url(self):
        corpus = "\n".join(
            p.read_text(encoding="utf-8") for p in _MR.rglob("*.py")
        )
        for label, fragment in (
            ("GADCS Y1-Y4 appendix",
             "gadcs-report-appendix-year-1-year-4-cohort-analysis"),
            ("CERT 2025 supplemental",
             "nov-2025-medicare-ffs-supplemental-improper-payment-data"),
        ):
            with self.subTest(source=label):
                self.assertIn(
                    fragment, corpus,
                    f"{label} is quoted but its primary-source URL is not "
                    "cited anywhere -- a figure without a fetchable source "
                    "is exactly what this program exists to eliminate.",
                )


class SupersededTableIsWellFormed(unittest.TestCase):
    def test_no_token_is_both_current_and_superseded(self):
        overlap = set(CURRENT.values()) & set(SUPERSEDED)
        self.assertEqual(
            set(), overlap,
            f"{overlap} listed as both current and superseded -- the tables "
            "have drifted apart.",
        )

    def test_tokens_look_like_figures(self):
        for token in list(CURRENT.values()) + list(SUPERSEDED):
            with self.subTest(token=token):
                self.assertRegex(token, r"^[\d,.]+%?$")


if __name__ == "__main__":
    unittest.main()
