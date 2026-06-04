"""Outcome statistics on the real corpus: Wilson CIs, denominator honesty,
small-sample flags, and real-corpus integration.

The real tier's realized_moic is too thin (~6%) for a MOIC regression, but
`outcome` is ~83% populated, so the credible real-data statistics are
distress/loss base rates — computed here with proper proportion confidence
intervals and explicit insufficient-sample flags.
"""
import unittest

from rcm_mc.data_public.corpus_outcome_stats import (
    OutcomeStats,
    compute_outcome_stats,
    corpus_outcome_summary,
    outcome_stats_by_sector,
    outcome_stats_by_vintage,
    real_corpus_outcome_report,
    wilson_interval,
)


def _deal(outcome=None, sector="other_services", year=2020):
    return {"outcome": outcome, "sector": sector, "year": year}


class TestWilsonInterval(unittest.TestCase):
    def test_zero_n_is_maximal_ignorance(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))

    def test_known_reference_value(self):
        # k=2, n=10 (p=0.2): Wilson 95% CI ~= [0.0567, 0.5098] (hand-computed).
        lo, hi = wilson_interval(2, 10)
        self.assertAlmostEqual(lo, 0.0567, places=3)
        self.assertAlmostEqual(hi, 0.5098, places=3)

    def test_brackets_point_estimate_and_stays_in_unit(self):
        for k, n in [(0, 5), (1, 5), (5, 5), (3, 200), (17, 333)]:
            lo, hi = wilson_interval(k, n)
            p = k / n
            self.assertLessEqual(lo, p + 1e-9)
            self.assertGreaterEqual(hi, p - 1e-9)
            self.assertGreaterEqual(lo, 0.0)
            self.assertLessEqual(hi, 1.0)

    def test_zero_successes_lower_bound_is_zero(self):
        lo, hi = wilson_interval(0, 29)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_interval_tightens_with_n(self):
        _, hi_small = wilson_interval(1, 10)
        _, hi_big = wilson_interval(10, 100)  # same p=0.1, 10x the data
        self.assertLess(hi_big, hi_small)


class TestComputeOutcomeStats(unittest.TestCase):
    def setUp(self):
        self.deals = [
            _deal("bankrupt"), _deal("distressed"),
            _deal("exited"), _deal("exited"),
            _deal("active"), _deal("active"),
            _deal(None),  # unknown -> excluded from denominator
        ]

    def test_counts(self):
        s = compute_outcome_stats(self.deals)
        self.assertEqual(s.n_total, 7)
        self.assertEqual(s.n_known, 6)        # None excluded
        self.assertEqual(s.n_bankrupt, 1)
        self.assertEqual(s.n_distressed, 1)
        self.assertEqual(s.n_exited, 2)
        self.assertEqual(s.n_active, 2)
        self.assertEqual(s.n_adverse, 2)

    def test_distress_rate_and_realized_loss(self):
        s = compute_outcome_stats(self.deals)
        self.assertAlmostEqual(s.distress_rate, 2 / 6)
        # realized = bankrupt + exited = 1 + 2 = 3; realized loss = 1/3
        self.assertEqual(s.n_realized, 3)
        self.assertAlmostEqual(s.realized_loss_rate, 1 / 3)

    def test_ci_brackets_rate(self):
        s = compute_outcome_stats(self.deals)
        self.assertLessEqual(s.distress_ci_lo, s.distress_rate)
        self.assertGreaterEqual(s.distress_ci_hi, s.distress_rate)

    def test_coverage(self):
        s = compute_outcome_stats(self.deals)
        self.assertAlmostEqual(s.coverage, 6 / 7)

    def test_insufficient_flag(self):
        self.assertFalse(compute_outcome_stats(self.deals, min_known=5).insufficient)
        self.assertTrue(compute_outcome_stats(self.deals, min_known=10).insufficient)

    def test_empty(self):
        s = compute_outcome_stats([])
        self.assertEqual(s.n_known, 0)
        self.assertIsNone(s.distress_rate)
        self.assertIsNone(s.realized_loss_rate)
        self.assertTrue(s.insufficient)

    def test_denominator_honesty_unknowns_do_not_dilute(self):
        """A None-outcome deal must NOT be silently counted as non-distressed:
        adding unknowns leaves the distress rate unchanged."""
        base = [_deal("bankrupt"), _deal("exited")]
        padded = base + [_deal(None), _deal(None), _deal(None)]
        self.assertEqual(
            compute_outcome_stats(base).distress_rate,
            compute_outcome_stats(padded).distress_rate,
        )


class TestBreakdowns(unittest.TestCase):
    def test_by_sector_sorted_and_flagged(self):
        deals = (
            [_deal("bankrupt", "dialysis")]                       # 1 known, high rate, low n
            + [_deal("exited", "dental") for _ in range(6)]       # 6 known, 0 rate
            + [_deal("distressed", "dental")]                     # dental: 7 known
        )
        rows = outcome_stats_by_sector(deals, min_known=5)
        labels = [r.label for r in rows]
        self.assertIn("dialysis", labels)
        self.assertIn("dental", labels)
        # dialysis (rate 1.0) sorts before dental (rate ~0.14)
        self.assertLess(labels.index("dialysis"), labels.index("dental"))
        # dialysis has only 1 known outcome -> insufficient
        dia = next(r for r in rows if r.label == "dialysis")
        den = next(r for r in rows if r.label == "dental")
        self.assertTrue(dia.insufficient)
        self.assertFalse(den.insufficient)

    def test_by_vintage_buckets_and_order(self):
        deals = [_deal("exited", year=2005), _deal("bankrupt", year=2006),
                 _deal("active", year=2021), _deal("exited", year=2022)]
        rows = outcome_stats_by_vintage(deals, bucket=3, min_known=1)
        labels = [r.label for r in rows]
        self.assertEqual(labels, sorted(labels))      # chronological
        self.assertTrue(all("-" in l for l in labels))  # range labels
        self.assertEqual(rows[0].n_total, 2)            # 2004-2006 bucket


class TestRealCorpusIntegration(unittest.TestCase):
    def test_summary_real_universe(self):
        from rcm_mc.data_public.corpus_loader import load_corpus_deals
        summ = corpus_outcome_summary("real")
        n_real = len(load_corpus_deals("real"))
        self.assertEqual(summ["universe"], "real")
        self.assertEqual(summ["overall"]["n_total"], n_real)
        # Real corpus carries real outcomes (>=1 known, >=1 bankruptcy).
        self.assertGreater(summ["overall"]["n_known"], 50)
        self.assertGreaterEqual(summ["overall"]["n_bankrupt"], 1)
        rate = summ["overall"]["distress_rate"]
        self.assertIsNotNone(rate)
        self.assertGreaterEqual(rate, 0.0)
        self.assertLessEqual(rate, 1.0)
        lo, hi = summ["overall"]["ci"]
        self.assertLessEqual(lo, rate)
        self.assertGreaterEqual(hi, rate)
        self.assertTrue(summ["by_sector"])
        self.assertTrue(summ["by_vintage"])

    def test_report_renders(self):
        rpt = real_corpus_outcome_report()
        self.assertIn("Real-Corpus Outcome Statistics", rpt)
        self.assertIn("Distress incidence", rpt)
        self.assertIn("95% CI", rpt)
        self.assertIn("By sector", rpt)
        self.assertIn("By vintage", rpt)
        # The honesty caveat must be present.
        self.assertIn("not realized IRR/MOIC losses", rpt)

    def test_real_corpus_has_thin_moic_but_rich_outcomes(self):
        """Documents the premise: outcomes are far better populated than MOIC,
        which is why outcome-based stats are the credible real-data read."""
        from rcm_mc.data_public.corpus_loader import load_corpus_deals
        real = load_corpus_deals("real")
        with_moic = sum(1 for d in real if d.get("realized_moic") is not None)
        with_outcome = sum(1 for d in real if d.get("outcome"))
        self.assertGreater(with_outcome, with_moic * 3)


if __name__ == "__main__":
    unittest.main()
