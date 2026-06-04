"""The verified_deals reference list is bridged into the corpus as real.

verified_deals.VERIFIED_DEALS held 79 individually source-cited PE healthcare
deals, but the corpus loader never read them, so they didn't count toward the
provenance-tagged real universe. verified_corpus.py adapts them to corpus
schema and corpus_provenance tags the group "real". These tests guard the
bridge: it adds net-new real deals, doesn't fabricate returns, dedups true
duplicates, and keeps every row sourced + sector-tagged.
"""
import unittest

from rcm_mc.data_public.corpus_loader import load_corpus_deals
from rcm_mc.data_public.verified_corpus import VERIFIED_CORPUS_DEALS
from rcm_mc.data_public.verified_deals import VERIFIED_DEALS


class TestVerifiedCorpusBridge(unittest.TestCase):
    def test_bridge_adds_netnew_real_deals(self):
        """Bridging materially grows the real tier (was 68 pre-bridge)."""
        real = load_corpus_deals("real")
        bridged = [d for d in real if d.get("source_group") == "verified_corpus"]
        self.assertEqual(len(bridged), len(VERIFIED_CORPUS_DEALS))
        self.assertGreater(len(bridged), 50)
        self.assertGreater(len(real), 120)

    def test_dedup_dropped_true_duplicates(self):
        """Some verified rows duplicate a seed-corpus deal (same company+year,
        e.g. LifePoint/2018, Cano/2021); those must be dropped, so the bridge
        is strictly smaller than the raw verified list."""
        self.assertLess(len(VERIFIED_CORPUS_DEALS), len(VERIFIED_DEALS))

    def test_every_bridged_deal_is_sourced(self):
        """Credibility: every bridged deal carries its source in notes (the
        original source_url/source_note) and a source_url field."""
        for d in VERIFIED_CORPUS_DEALS:
            self.assertTrue(d.get("source_url"), f"{d['source_id']} missing source_url")
            self.assertIn("Source:", d.get("notes", ""))

    def test_no_fabricated_returns(self):
        """realized_moic appears ONLY for documented bankruptcies (~0.0x);
        realized_irr is never fabricated."""
        for d in VERIFIED_CORPUS_DEALS:
            if d.get("realized_moic") is not None:
                self.assertEqual(d["realized_moic"], 0.0)
                self.assertEqual(d.get("outcome"), "bankrupt")
            self.assertIsNone(d.get("realized_irr"))

    def test_sectors_canonical(self):
        """Bridged sectors use the corpus's canonical vocab (so they aggregate
        with existing rows) — never the verified-only labels like 'hospitals'."""
        bridged = [d for d in load_corpus_deals("real")
                   if d.get("source_group") == "verified_corpus"]
        for d in bridged:
            self.assertTrue(d.get("sector"))
            self.assertNotEqual(d["sector"], "hospitals")
            self.assertNotEqual(d["sector"], "rcm_healthtech")

    def test_all_real_have_provenance(self):
        real = load_corpus_deals("real")
        self.assertTrue(all(d.get("provenance") == "real" for d in real))


if __name__ == "__main__":
    unittest.main()
