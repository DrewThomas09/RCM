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


# Tokens that are NOT a target identity — deal-structure words and common
# corporate suffixes. The buyer's own words are stripped per-deal too, so a
# pair only matches on a shared *target* token, not a shared sponsor name.
_GENERIC_TOKENS = {
    "health", "healthcare", "group", "inc", "llc", "corp", "corporation",
    "partners", "systems", "system", "holdings", "holding", "services",
    "service", "the", "merger", "acquisition", "buyout", "take", "private",
    "lbo", "platform", "recap", "secondary", "deal", "physician", "staffing",
    "capital", "management", "company", "associates", "round", "preipo", "ipo",
}


def _target_tokens(name: str, buyer: str) -> set:
    buyer_tokens = set(re.findall(r"[a-z]{4,}", (buyer or "").lower()))
    return {
        t
        for t in re.findall(r"[a-z]{4,}", (name or "").lower())
        if t not in _GENERIC_TOKENS and t not in buyer_tokens
    }


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

    def test_no_cross_side_duplicate_deals(self) -> None:
        """Catch the same deal entered from BOTH sides of the transaction.

        The target-name check above misses these because "Teladoc–Livongo"
        and "Livongo / Teladoc Merger" normalize to different targets. They
        share, instead, the same buyer + year + entry EV AND a non-sponsor
        target token. Distinct deals by one sponsor in a year (e.g. Waud
        Capital's Acadia vs Healogics, both 2011/$300M) don't share a target
        token, so they are not flagged.
        """
        deals = load_corpus_deals()
        groups: dict = collections.defaultdict(list)
        for d in deals:
            if _ev(d) > 0 and d.get("year") is not None:
                groups[(_norm_buyer(d.get("buyer")), d.get("year"))].append(d)

        dupes = []
        for (_buyer, year), ds in groups.items():
            for i in range(len(ds)):
                for j in range(i + 1, len(ds)):
                    a, b = _ev(ds[i]), _ev(ds[j])
                    shared = _target_tokens(
                        ds[i].get("deal_name"), ds[i].get("buyer")
                    ) & _target_tokens(ds[j].get("deal_name"), ds[j].get("buyer"))
                    if a > 0 and b > 0 and 0.94 <= a / b <= 1.064 and shared:
                        dupes.append(
                            f"{year} {sorted(shared)}: "
                            f"{ds[i].get('source_id')} ~ {ds[j].get('source_id')}"
                        )

        self.assertEqual(
            dupes,
            [],
            "cross-side-named duplicate deals re-introduced:\n  "
            + "\n  ".join(dupes),
        )


if __name__ == "__main__":
    unittest.main()
