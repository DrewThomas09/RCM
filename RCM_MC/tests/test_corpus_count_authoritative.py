"""The corpus-reporting pages show the authoritative, consistent count.

Across the platform, 147 engines roll their own _load_corpus() with
divergent range(2,N) spans, so the informational "Corpus Deals" badge
varies page-to-page. The two pages whose JOB is to report the corpus —
/corpus-dashboard and /corpus-coverage — previously used bespoke
subsets (range(2,32)=~655, range(2,39)) that materially under-counted
the real corpus (~1760). They now both source the canonical
corpus_loader.load_corpus_deals('all'), so they agree with each other
and with the authoritative count. (Scoped fix: the cosmetic per-tracker
badges are intentionally left alone — changing all 147 would shift
displayed numbers platform-wide and break count-asserting tests.)
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.corpus_loader import load_corpus_deals
from rcm_mc.ui.data_public import corpus_coverage_page, corpus_dashboard_page


class CorpusCountAuthoritativeTests(unittest.TestCase):
    def test_dashboard_and_coverage_match_canonical(self):
        canonical = len(load_corpus_deals("all"))
        self.assertEqual(len(corpus_dashboard_page._load_corpus()), canonical)
        self.assertEqual(len(corpus_coverage_page._load_corpus()), canonical)

    def test_canonical_is_substantial(self):
        # Guards against a regression that silently empties the corpus.
        self.assertGreater(len(load_corpus_deals("all")), 1000)


if __name__ == "__main__":
    unittest.main()
