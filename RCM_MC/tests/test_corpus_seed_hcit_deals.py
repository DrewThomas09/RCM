"""Verified-real corpus additions: healthcare-IT / RCM / services + a
documented downside (seed_036–seed_043).

These broaden the verified-real tier in this platform's core domain (RCM,
health-IT, physician/home services) and recent vintages, where the prior
seed set skewed toward hospitals. Identity facts are publicly disclosed
M&A; realized_moic is set only for the unambiguous Air Methods Chapter-11
loss. This guards their presence, provenance ("real"), and schema validity.
"""

import unittest

from rcm_mc.data_public.corpus_loader import load_corpus_deals
from rcm_mc.data_public.deals_corpus import _SEED_DEALS

_NEW_IDS = [f"seed_{n:03d}" for n in range(36, 44)]


class TestCorpusHcitAdditions(unittest.TestCase):
    def test_new_deals_present_in_seed(self):
        ids = {d["source_id"] for d in _SEED_DEALS}
        for sid in _NEW_IDS:
            self.assertIn(sid, ids, f"{sid} missing from _SEED_DEALS")

    def test_new_deals_load_as_real(self):
        by_id = {d.get("source_id"): d for d in load_corpus_deals("all")}
        for sid in _NEW_IDS:
            self.assertIn(sid, by_id)
            self.assertEqual(by_id[sid]["provenance"], "real")

    def test_new_deals_schema_valid(self):
        new = [d for d in _SEED_DEALS if d["source_id"] in _NEW_IDS]
        self.assertEqual(len(new), len(_NEW_IDS))
        for d in new:
            self.assertTrue(d["deal_name"] and d["buyer"] and d["seller"])
            self.assertIsInstance(d["year"], int)
            self.assertGreater(d["ev_mm"], 0)
            # payer_mix is a real distribution summing to 1.
            self.assertAlmostEqual(sum(d["payer_mix"].values()), 1.0, places=3)

    def test_air_methods_documented_loss(self):
        am = next(d for d in _SEED_DEALS if d["source_id"] == "seed_041")
        self.assertIn("Air Methods", am["deal_name"])
        # Chapter 11 → near-total equity loss (a real downside data point).
        self.assertIsNotNone(am["realized_moic"])
        self.assertLess(am["realized_moic"], 0.2)

    def test_rcm_domain_deal_present(self):
        """R1 RCM — a pure-play revenue-cycle-management take-private — is
        directly the domain this platform models."""
        r1 = next(d for d in _SEED_DEALS if d["source_id"] == "seed_036")
        self.assertIn("R1 RCM", r1["deal_name"])


if __name__ == "__main__":
    unittest.main()
