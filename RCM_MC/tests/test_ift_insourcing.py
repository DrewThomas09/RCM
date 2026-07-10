"""Real-path tests for the IFT insource-vs-outsource + claims gross-up module.

Exercises the REAL ``ift_insourcing`` functions against the REAL ``ift_geo`` /
``ift_analytics`` / ``npi_cleaner.understatement`` spines (no mocks of our own
code) and pins the three shared-brief contract guarantees:

  (a) results are non-empty and sane;
  (b) every figure/row carries a valid honesty basis in
      {GOV, SOURCED, ACADEMIC, ILLUSTRATIVE}; system NAMES carry a PUBLIC-WEB
      note (never a data chip); ``source_label`` leads with its dominant basis;
  (c) every function degrades — never raises — when a dependency is unavailable.

Plus the SOW-specific rules from the transcripts: classification is by transport
VOLUME not asset ownership; the biller proxy is the insource UPPER BOUND and is
REUSED from ift_analytics.health_system_sam (not reinvented); the gross-up
references the understatement.py cause taxonomy for direct-bill + unbilled.
"""
from __future__ import annotations

import unittest

from rcm_mc.market_reports import ift_insourcing as ins
from rcm_mc.market_reports import ift_geo as geo

_BASES = {"GOV", "SOURCED", "ACADEMIC", "FRAMEWORK",
          "ILLUSTRATIVE"}  # FRAMEWORK: 2026-07-10 rename of the scaffold basis


def _leads_with_basis(label: str) -> bool:
    """A source_label must LEAD with an honest basis chip (the UI splits on
    ' · '), so its first token before the separator names one of the bases."""
    head = label.split(" · ", 1)[0].strip().upper()
    return any(head.startswith(b) for b in _BASES)


# ═════════════════════════════════════════════════════════════════════════════
# (1) insourcing_framework — the classification model
# ═════════════════════════════════════════════════════════════════════════════
class FrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fw = ins.insourcing_framework()

    def test_available_and_four_ordered_bands(self):
        self.assertTrue(self.fw.available)
        self.assertEqual([b.key for b in self.fw.bands], list(ins._BAND_ORDER))
        self.assertEqual(len(self.fw.bands), 4)
        self.assertTrue(_leads_with_basis(self.fw.source_label))
        self.assertTrue(self.fw.headline and self.fw.note)

    def test_classification_axis_is_volume_not_assets(self):
        # The load-bearing transcript rule: classify by transport VOLUME, not
        # asset ownership.
        axis = self.fw.classification_axis.lower()
        self.assertIn("volume", axis)
        self.assertIn("not", axis)
        self.assertTrue("asset" in axis or "ownership" in axis)
        # At least one band spells out the "owns a few trucks ≠ insourced" trap.
        joined = " ".join(b.asset_vs_volume_note.lower() for b in self.fw.bands)
        self.assertTrue("asset" in joined or "own" in joined)

    def test_bands_are_contiguous_and_ordered_over_unit_interval(self):
        bands = self.fw.bands
        self.assertAlmostEqual(bands[0].volume_share_low, 0.0, places=6)
        self.assertAlmostEqual(bands[-1].volume_share_high, 1.0, places=6)
        for b in bands:
            self.assertGreaterEqual(b.volume_share_low, 0.0, b.key)
            self.assertLess(b.volume_share_low, b.volume_share_high, b.key)
            self.assertLessEqual(b.volume_share_high, 1.0, b.key)
        for a, b in zip(bands, bands[1:]):
            self.assertAlmostEqual(a.volume_share_high, b.volume_share_low,
                                   places=6, msg=f"{a.key}->{b.key} not contiguous")

    def test_every_band_is_sane_and_labelled(self):
        for b in self.fw.bands:
            self.assertTrue(b.name and b.definition, b.key)
            self.assertTrue(b.operating_requirement, b.key)   # the rationale
            self.assertTrue(b.asset_vs_volume_note, b.key)
            self.assertTrue(b.addressable_read, b.key)
            self.assertIn(b.basis, _BASES, b.key)
            self.assertIn("PUBLIC-WEB", b.names_basis, b.key)
            self.assertTrue(_leads_with_basis(b.source_label), b.key)
            self.assertEqual(ins.band_label(b.key), b.name)

    def test_example_systems_are_reused_from_ift_geo(self):
        # Every example system name must be derivable from a REAL ift_geo
        # named_operators / anchor_systems string (reused, not invented).
        geo_names = set()
        for md in geo.MARKETS:
            for raw in tuple(md.named_operators) + tuple(md.anchor_systems):
                geo_names.add(ins._clean_name(raw))
        seen_any = False
        for b in self.fw.bands:
            for name in b.example_systems:
                seen_any = True
                self.assertIn(name, geo_names,
                              f"{b.key}: {name!r} not from ift_geo")
        self.assertTrue(seen_any, "no example systems wired from ift_geo at all")

    def test_insourced_examples_are_the_captive_systems(self):
        by_key = {b.key: b for b in self.fw.bands}
        # Mayo is the fully-insourced captive proof point.
        joined_full = " ".join(by_key[ins.BAND_FULLY_INSOURCED].example_systems)
        self.assertIn("Mayo", joined_full)
        # Twin Cities captive fleets anchor the mostly-insourced band.
        joined_mostly = " ".join(by_key[ins.BAND_MOSTLY_INSOURCED].example_systems)
        self.assertTrue("Allina" in joined_mostly or "North Memorial" in joined_mostly)


# ═════════════════════════════════════════════════════════════════════════════
# (2) biller_proxy — the insource UPPER BOUND
# ═════════════════════════════════════════════════════════════════════════════
class BillerProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bp = ins.biller_proxy()

    def test_available_and_labelled(self):
        self.assertTrue(self.bp.available)
        self.assertTrue(_leads_with_basis(self.bp.source_label))
        self.assertTrue(self.bp.headline and self.bp.proxy_rule)
        self.assertTrue(self.bp.limitations)

    def test_ceiling_is_a_real_band_and_reused_from_health_system_sam(self):
        from rcm_mc.market_reports import ift_analytics as an
        hs = an.health_system_sam()
        self.assertTrue(hs.available)
        # REUSED verbatim — not a different number.
        self.assertEqual(
            (self.bp.ceiling_low, self.bp.ceiling_central, self.bp.ceiling_high),
            tuple(float(x) for x in hs.insource_ceiling))
        # a real (0,1) monotone band
        self.assertLess(0.0, self.bp.ceiling_low)
        self.assertLess(self.bp.ceiling_low, self.bp.ceiling_central)
        self.assertLess(self.bp.ceiling_central, self.bp.ceiling_high)
        self.assertLess(self.bp.ceiling_high, 1.0)

    def test_addressable_is_one_minus_ceiling(self):
        # addressable_share = 1 − insource ceiling (the outsourceable market).
        self.assertAlmostEqual(self.bp.addressable_central,
                               1.0 - self.bp.ceiling_central, places=3)
        self.assertAlmostEqual(self.bp.addressable_low,
                               1.0 - self.bp.ceiling_high, places=3)
        self.assertAlmostEqual(self.bp.addressable_high,
                               1.0 - self.bp.ceiling_low, places=3)

    def test_it_is_explained_as_an_upper_bound(self):
        blob = (self.bp.upper_bound_rationale + " "
                + " ".join(self.bp.limitations)).lower()
        self.assertIn("upper bound", blob)
        # the ceiling framing + the billed-not-run limitation are both present
        self.assertIn("ceiling", blob)
        self.assertTrue("subcontract" in blob or "joint" in blob or "billed" in blob)


# ═════════════════════════════════════════════════════════════════════════════
# (3) claims_grossup — the undercount adjustment
# ═════════════════════════════════════════════════════════════════════════════
class ClaimsGrossupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cg = ins.claims_grossup()

    def test_available_and_labelled(self):
        self.assertTrue(self.cg.available)
        self.assertTrue(_leads_with_basis(self.cg.source_label))
        self.assertIn("understatement", self.cg.source_label.lower())
        self.assertTrue(self.cg.headline and self.cg.taxonomy_source)

    def test_two_components_direct_bill_and_unbilled(self):
        keys = {c.key for c in self.cg.components}
        self.assertEqual(keys, {"direct_bill", "unbilled"})
        for c in self.cg.components:
            self.assertIn(c.basis, _BASES, c.key)
            self.assertTrue(c.mechanism and c.named_basis, c.key)
            self.assertTrue(c.named_basis.startswith("FRAMEWORK"), c.key)
            # a real, ordered fraction band inside (0,1)
            self.assertLess(0.0, c.frac_low, c.key)
            self.assertLessEqual(c.frac_low, c.frac_central, c.key)
            self.assertLessEqual(c.frac_central, c.frac_high, c.key)
            self.assertLess(c.frac_high, 1.0, c.key)

    def test_components_reference_the_understatement_taxonomy(self):
        # (c) consistency, not reinvention: every referenced cause id must be a
        # REAL cause in the imported understatement taxonomy, and the surfaced
        # cause names must match the taxonomy's own names.
        from rcm_mc.npi_cleaner import understatement as us
        self.assertTrue(self.cg.taxonomy_available)
        for c in self.cg.components:
            self.assertTrue(c.understatement_cause_ids, c.key)
            for cid, name in zip(c.understatement_cause_ids, c.understatement_causes):
                self.assertIn(cid, us.TAXONOMY_BY_ID,
                              f"{c.key}: {cid} not a real understatement cause")
                self.assertEqual(name, us.TAXONOMY_BY_ID[cid].name, cid)
        # the transport-drop cause must anchor the direct-bill leg
        direct = next(c for c in self.cg.components if c.key == "direct_bill")
        self.assertIn("ancillary_transport_dropped", direct.understatement_cause_ids)

    def test_multiplier_is_grossup_of_missing_share(self):
        cg = self.cg
        # additive missing share = sum of component fractions (central)
        exp_central = sum(c.frac_central for c in cg.components)
        self.assertAlmostEqual(cg.total_missing_central, exp_central, places=6)
        # multiplier = 1 / (1 − missing), monotone and strictly > 1
        for miss, mult in ((cg.total_missing_low, cg.multiplier_low),
                           (cg.total_missing_central, cg.multiplier_central),
                           (cg.total_missing_high, cg.multiplier_high)):
            self.assertAlmostEqual(mult, 1.0 / (1.0 - miss), places=3)
            self.assertGreater(mult, 1.0)
        self.assertLess(cg.multiplier_low, cg.multiplier_central)
        self.assertLess(cg.multiplier_central, cg.multiplier_high)

    def test_reference_application_grosses_claims_up_to_true(self):
        # claims_observed < true, and grossing it up recovers the true market.
        cg = self.cg
        self.assertIsNotNone(cg.true_market_bn)
        self.assertIsNotNone(cg.claims_observed_bn)
        self.assertLess(cg.claims_observed_bn, cg.true_market_bn)
        self.assertGreater(cg.missing_bn, 0.0)
        self.assertAlmostEqual(cg.claims_observed_bn + cg.missing_bn,
                               cg.true_market_bn, places=2)
        # the true-market reference IS the GOV-anchored ground-IFT TAM central
        from rcm_mc.market_reports import ift_analytics as an
        tam = an.ground_tam()
        self.assertAlmostEqual(cg.true_market_bn, tam.allpayer_tam_bn_central,
                               places=2)


# ═════════════════════════════════════════════════════════════════════════════
# (4) market_insourcing — per-metro read
# ═════════════════════════════════════════════════════════════════════════════
class MarketInsourcingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mi = ins.market_insourcing()

    def test_available_one_row_per_market_and_counts_sum(self):
        self.assertTrue(self.mi.available)
        self.assertEqual(len(self.mi.rows), len(geo.MARKETS))
        self.assertTrue(_leads_with_basis(self.mi.source_label))
        self.assertEqual(sum(self.mi.band_counts.values()), len(geo.MARKETS))
        for k in self.mi.band_counts:
            self.assertIn(k, ins._BAND_ORDER)

    def test_every_row_is_sane_and_labelled(self):
        for r in self.mi.rows:
            self.assertTrue(r.name and r.region_label and r.insource_class, r.name)
            self.assertIn(r.framework_band, ins._BAND_ORDER, r.name)
            self.assertEqual(r.framework_band_label,
                             ins.band_label(r.framework_band), r.name)
            self.assertTrue(r.volume_read, r.name)
            self.assertTrue(r.insource_read and r.moat_note, r.name)  # PUBLIC-WEB
            self.assertIn(r.basis, _BASES, r.name)
            self.assertIn("PUBLIC-WEB", r.names_basis, r.name)
            self.assertTrue(_leads_with_basis(r.source_label), r.name)
            # insourced-VOLUME-share band is a real ordered fraction in [0,1]
            self.assertLessEqual(0.0, r.insourced_volume_share_low, r.name)
            self.assertLessEqual(r.insourced_volume_share_low,
                                 r.insourced_volume_share_high, r.name)
            self.assertLessEqual(r.insourced_volume_share_high, 1.0, r.name)

    def test_contestable_residual_reuses_the_sizing_model(self):
        # The contestable residual IS ift_analytics.sam_formula's s(m).
        from rcm_mc.market_reports import ift_analytics as an
        sam = an.sam_formula()
        if not sam.available:
            self.skipTest("sam_formula unavailable offline")
        s_by = {row.name: row.serviceable_share for row in sam.rows}
        for r in self.mi.rows:
            self.assertAlmostEqual(r.contestable_residual_share, s_by[r.name],
                                   places=6, msg=r.name)

    def test_volume_not_asset_classification_for_known_metros(self):
        byn = {r.name: r for r in self.mi.rows}
        # Captive-fleet systems read (mostly-)insourced by volume.
        for nm in ("Rochester (MN)", "Twin Cities"):
            self.assertEqual(byn[nm].framework_band, ins.BAND_MOSTLY_INSOURCED, nm)
            self.assertGreaterEqual(byn[nm].insourced_volume_share_low, 0.50, nm)
        # Cleveland OWNS high-acuity CCT but by VOLUME is mostly OUTSOURCED — the
        # asset-vs-volume distinction the transcripts insist on.
        self.assertEqual(byn["Cleveland"].framework_band,
                         ins.BAND_MOSTLY_OUTSOURCED)
        self.assertLessEqual(byn["Cleveland"].insourced_volume_share_high, 0.50)
        # Private-dominant / contract-gated markets read fully outsourced.
        for nm in ("Milwaukee", "Madison", "Louisville"):
            self.assertEqual(byn[nm].framework_band, ins.BAND_FULLY_OUTSOURCED, nm)
            self.assertLessEqual(byn[nm].insourced_volume_share_high, 0.10, nm)
        # The footprint is outsourced-heavy: most metros are NOT insourced.
        outsourced = (self.mi.band_counts.get(ins.BAND_FULLY_OUTSOURCED, 0)
                      + self.mi.band_counts.get(ins.BAND_MOSTLY_OUTSOURCED, 0))
        self.assertGreater(outsourced, len(geo.MARKETS) // 2)

    def test_volume_read_prose_names_the_volume_basis(self):
        # Each read must argue on VOLUME (that is the whole point).
        for r in self.mi.rows:
            self.assertIn("volume", r.volume_read.lower(), r.name)


# ═════════════════════════════════════════════════════════════════════════════
# (c) Degrade-never-raise — dependencies unavailable
# ═════════════════════════════════════════════════════════════════════════════
class DegradeTests(unittest.TestCase):
    def setUp(self):
        self._clear()

    def tearDown(self):
        # Restore any patched module attributes, then clear caches so later
        # tests see the real data.
        ins._markets = _ORIG_MARKETS
        ins._health_system_sam = _ORIG_HS
        ins._ground_tam = _ORIG_TAM
        ins._understatement = _ORIG_US
        self._clear()

    def _clear(self):
        ins._markets.cache_clear()
        ins._all_geo_names.cache_clear()
        ins._serviceable_share_by_metro.cache_clear()
        ins.insourcing_framework.cache_clear()
        ins.biller_proxy.cache_clear()
        ins.claims_grossup.cache_clear()
        ins.market_insourcing.cache_clear()

    def test_framework_degrades_to_empty_examples_without_ift_geo(self):
        # The authored model still renders; only the example lists degrade.
        ins._markets = lambda: tuple()  # type: ignore[assignment]
        ins._all_geo_names.cache_clear()
        fw = ins.insourcing_framework.__wrapped__()
        self.assertTrue(fw.available)                 # authored content survives
        self.assertEqual(len(fw.bands), 4)
        for b in fw.bands:
            self.assertEqual(b.example_systems, ())   # names degraded, not faked
            self.assertTrue(_leads_with_basis(b.source_label))

    def test_market_insourcing_degrades_without_markets(self):
        ins._markets = lambda: tuple()  # type: ignore[assignment]
        mi = ins.market_insourcing.__wrapped__()
        self.assertFalse(mi.available)
        self.assertEqual(mi.rows, [])
        self.assertTrue(_leads_with_basis(mi.source_label))

    def test_biller_proxy_degrades_without_health_system_sam(self):
        ins._health_system_sam = lambda: None  # type: ignore[assignment]
        bp = ins.biller_proxy.__wrapped__()
        self.assertFalse(bp.available)
        self.assertTrue(_leads_with_basis(bp.source_label))
        self.assertTrue(bp.note)

    def test_claims_grossup_survives_without_taxonomy_or_tam(self):
        # The core fractions/multiplier are ours, so the gross-up stays available
        # even if the cleaner import and the TAM reference both fail.
        ins._understatement = lambda: None   # type: ignore[assignment]
        ins._ground_tam = lambda: None        # type: ignore[assignment]
        cg = ins.claims_grossup.__wrapped__()
        self.assertTrue(cg.available)                 # never raises, still usable
        self.assertFalse(cg.taxonomy_available)       # honest about the gap
        self.assertIsNone(cg.true_market_bn)          # no reference market
        self.assertEqual(len(cg.components), 2)
        self.assertGreater(cg.multiplier_central, 1.0)
        # cause names honestly fall back to the ids when the taxonomy is absent
        for c in cg.components:
            self.assertEqual(c.understatement_causes, c.understatement_cause_ids)


# Capture the real accessors once so DegradeTests can restore them.
_ORIG_MARKETS = ins._markets
_ORIG_HS = ins._health_system_sam
_ORIG_TAM = ins._ground_tam
_ORIG_US = ins._understatement


if __name__ == "__main__":
    unittest.main()
