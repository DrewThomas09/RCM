"""Canonical sector backfill for the verified-real corpus.

The real seed groups (``_SEED_DEALS`` + ``extended_seed``) were authored
without a ``sector`` field, while the synthetic ``extended_seed_{N}`` batches
each carry one. That left the *credible* deals unclassified, so any
sector-sliced analytic (corpus-dashboard verified mode, sector-intel) silently
dropped them. ``deals_corpus.REAL_DEAL_SECTORS`` + the copy-safe backfill in
``corpus_loader.load_corpus_deals`` restore that. These tests guard:
  - every real deal is now sector-tagged,
  - the tags use the corpus's existing canonical vocabulary (so they aggregate
    rather than spawn duplicate near-name buckets),
  - the backfill never mutates the shared module-level seed lists,
  - a couple of business-fact classifications that are easy to get wrong.
"""
import unittest

from rcm_mc.data_public.corpus_loader import load_corpus_deals
from rcm_mc.data_public.deals_corpus import REAL_DEAL_SECTORS, _SEED_DEALS


class TestRealDealSectors(unittest.TestCase):
    def test_every_real_deal_is_sector_tagged(self):
        real = load_corpus_deals("real")
        untagged = [d.get("source_id") for d in real if not d.get("sector")]
        self.assertEqual(untagged, [], f"real deals still missing a sector: {untagged}")

    def test_tags_use_canonical_vocabulary(self):
        """Real-deal sectors must reuse a value that already exists in the
        synthetic corpus, otherwise they would never aggregate with it."""
        synthetic = load_corpus_deals("synthetic")
        existing = {d.get("sector") for d in synthetic if d.get("sector")}
        for sid, sec in REAL_DEAL_SECTORS.items():
            self.assertIn(
                sec, existing,
                f"{sid} tagged with non-canonical sector {sec!r} "
                "(would not aggregate with the synthetic rows)",
            )

    def test_backfill_does_not_mutate_shared_seed_list(self):
        """The loader enriches per-row copies; the module-level _SEED_DEALS
        must stay free of the injected sector (the legacy loaders share it)."""
        load_corpus_deals("real")  # trigger the backfill
        injected = [d.get("source_id") for d in _SEED_DEALS if d.get("sector")]
        self.assertEqual(
            injected, [],
            f"_SEED_DEALS was mutated in place with sectors: {injected}",
        )

    def test_known_classifications(self):
        """A few business-fact classifications that the deal *name* alone gets
        wrong — guard them so a future rename doesn't silently mis-bucket."""
        # DaVita-HealthCare Partners is the capitated medical group, NOT dialysis.
        self.assertEqual(REAL_DEAL_SECTORS["ext_003"], "managed_care")
        # Air Methods is air-medical transport.
        self.assertEqual(REAL_DEAL_SECTORS["seed_041"], "ems")
        # Cano Health is value-based senior primary care (the VBC wipeout).
        self.assertEqual(REAL_DEAL_SECTORS["seed_046"], "value_based_care")
        # R1 RCM / athenahealth / Cotiviti are the platform's home sector.
        for sid in ("seed_036", "seed_037", "seed_038"):
            self.assertEqual(REAL_DEAL_SECTORS[sid], "health_it")

    def test_all_mode_sector_coverage_improved(self):
        """Backfilling the real deals raises full-corpus sector coverage."""
        allc = load_corpus_deals("all")
        tagged = sum(1 for d in allc if d.get("sector"))
        # 68 real deals newly classified — coverage must clear the prior ~1414.
        self.assertGreaterEqual(tagged, 1414 + 60)


if __name__ == "__main__":
    unittest.main()
