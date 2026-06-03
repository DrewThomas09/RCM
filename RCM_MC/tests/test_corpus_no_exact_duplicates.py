"""Guard against accidental duplicate deals in the seed corpus.

The corpus is "real deals · modeled financials" — each real transaction
should appear once. Across 30+ seed batches the same deal had been
entered 2-4x with modeled-figure variance (e.g. Envision/KKR 2018 at
$9.9B appeared three times), which inflated the headline deal count and
double-counted those deals in every corpus analytic (deal-quality, IRR
dispersion, sector momentum, benchmarks). 26 such exact double-entries
were removed; this test stops them returning.

"Exact duplicate" here is deliberately tight — same normalized target +
same normalized buyer + same (non-null) year + entry EV within 12% — so
genuinely distinct rounds/events (a 2012 take-private vs a 2022 strategic
exit) are NOT flagged.
"""
from __future__ import annotations

import collections
import re
import unittest

from rcm_mc.ui.chartis._helpers import load_corpus_deals


def _norm_target(name: str) -> str:
    name = (name or "").lower()
    name = re.split(r"[–—\-/(]", name)[0]
    name = re.sub(
        r"\b(health|healthcare|group|inc|llc|corp|partners|systems?|"
        r"holdings?|services?|the)\b",
        "",
        name,
    )
    return re.sub(r"[^a-z0-9]", "", name)


def _norm_buyer(buyer: str) -> str:
    buyer = (buyer or "").lower()
    buyer = re.split(r"[(/+]", buyer)[0]
    return re.sub(r"[^a-z0-9]", "", buyer)[:12]


def _ev(deal: dict) -> float:
    try:
        return float(deal.get("ev_mm") or 0)
    except (TypeError, ValueError):
        return 0.0


class CorpusNoExactDuplicatesTest(unittest.TestCase):
    def test_no_exact_duplicate_deals(self) -> None:
        deals = load_corpus_deals()
        self.assertGreater(len(deals), 500, "corpus unexpectedly empty/small")

        groups: dict = collections.defaultdict(list)
        for d in deals:
            key = (
                _norm_target(d.get("deal_name") or d.get("company_name") or ""),
                _norm_buyer(d.get("buyer")),
                d.get("year"),
            )
            if key[0] and key[2] is not None:
                groups[key].append(d)

        dupes = []
        for (target, buyer, year), ds in groups.items():
            for i in range(len(ds)):
                for j in range(i + 1, len(ds)):
                    a, b = _ev(ds[i]), _ev(ds[j])
                    if a > 0 and b > 0 and 0.88 <= a / b <= 1.136:
                        dupes.append(
                            f"{target} ({year}, {buyer}): "
                            f"{ds[i].get('source_id')} ~ {ds[j].get('source_id')}"
                        )

        self.assertEqual(
            dupes,
            [],
            "exact-duplicate deals re-introduced into the corpus:\n  "
            + "\n  ".join(dupes),
        )


if __name__ == "__main__":
    unittest.main()
