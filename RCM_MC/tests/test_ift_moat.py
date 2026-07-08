"""Real-path tests for the IFT moat / stickiness scorecard (``ift_moat``).

These exercise the REAL functions (no mocks of our own code) against the real
ift_geo footprint data, and pin the honesty invariants the diligence tool rests
on:

  * the seven stickiness factors are complete and each carries a valid basis;
  * every per-metro factor score is a labelled ordinal with a valid basis — the
    density factor SOURCED (computed from the ift_geo node count), the six
    qualitative factors ILLUSTRATIVE (never SOURCED/GOV);
  * the composite is a labelled ILLUSTRATIVE 1.00-3.00 ordinal mean, never a
    fabricated 0-100 score;
  * the cross-market proof points pull their evidence VERBATIM from ift_geo (so
    nothing is re-invented), name a real market and the factor(s) they prove;
  * every function degrades — never raises — when a dependency is unavailable.
"""
from __future__ import annotations

import unittest

from rcm_mc.market_reports import ift_moat as mo
from rcm_mc.market_reports import ift_geo as geo


class TestMoatFactors(unittest.TestCase):
    def test_seven_factors_with_stable_ids(self):
        factors = mo.moat_factors()
        self.assertEqual(len(factors), 7)
        self.assertEqual(tuple(f.id for f in factors), mo.FACTOR_ORDER)
        # the seven ids match the framework the thesis names
        self.assertEqual(
            {f.id for f in factors},
            {mo.F_FIRST_CALL, mo.F_SHARE_OF_WALLET, mo.F_COLOCATED,
             mo.F_WORKFLOW, mo.F_DENSITY, mo.F_SWITCHING, mo.F_PROOF})

    def test_every_factor_well_formed_and_labelled(self):
        for f in mo.moat_factors():
            self.assertTrue(f.name, f.id)
            self.assertTrue(f.definition, f.id)
            self.assertTrue(f.why_it_matters, f.id)
            self.assertTrue(f.how_evidenced, f.id)
            self.assertIn(f.basis, mo.VALID_BASES, f"{f.id}: bad basis {f.basis}")

    def test_share_of_wallet_carries_85_target_illustrative(self):
        by_id = {f.id: f for f in mo.moat_factors()}
        sow = by_id[mo.F_SHARE_OF_WALLET]
        self.assertEqual(sow.target, "85%+")
        # the 85% target is the operator thesis, never a measured GOV/SOURCED figure
        self.assertEqual(sow.basis, mo.BASIS_ILLUSTRATIVE)

    def test_density_factor_names_sourced_input(self):
        by_id = {f.id: f for f in mo.moat_factors()}
        dens = by_id[mo.F_DENSITY]
        self.assertEqual(dens.basis, mo.BASIS_SOURCED)
        self.assertIn("metro_structure", dens.how_evidenced)

    def test_factors_source_label_leads_illustrative(self):
        # A mixed framework must lead with its dominant honest basis.
        self.assertTrue(mo.moat_factors_source_label().startswith(mo.BASIS_ILLUSTRATIVE))


class TestMarketMoatScores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc = mo.market_moat_scores()

    def test_scorecard_covers_every_market(self):
        self.assertTrue(self.sc.available)
        self.assertEqual(self.sc.n_markets, len(geo.MARKETS))
        self.assertEqual(len(self.sc.rows), len(geo.MARKETS))

    def test_every_row_has_seven_scored_factors(self):
        for r in self.sc.rows:
            self.assertTrue(r.available, r.name)
            self.assertEqual(len(r.factors), 7, r.name)
            self.assertEqual(tuple(f.factor_id for f in r.factors), mo.FACTOR_ORDER)

    def test_every_factor_score_is_valid_ordinal_with_valid_basis(self):
        # Contract (b): every figure/row carries a valid basis; scores are labelled
        # ordinals, and points reconcile with the ordinal.
        for r in self.sc.rows:
            for f in r.factors:
                self.assertIn(f.score, mo.VALID_SCORES, f"{r.name}/{f.factor_id}")
                self.assertIn(f.basis, mo.VALID_BASES, f"{r.name}/{f.factor_id}")
                self.assertEqual(f.points, mo._ORDINAL_POINTS[f.score])
                self.assertTrue(f.evidence, f"{r.name}/{f.factor_id} has no evidence")

    def test_density_factor_is_sourced_and_the_rest_illustrative(self):
        # The load-bearing honesty split: density SOURCED (real node count), the
        # six qualitative factors ILLUSTRATIVE — never SOURCED/GOV.
        for r in self.sc.rows:
            by_id = {f.factor_id: f for f in r.factors}
            self.assertEqual(by_id[mo.F_DENSITY].basis, mo.BASIS_SOURCED, r.name)
            for fid in mo.FACTOR_ORDER:
                if fid == mo.F_DENSITY:
                    continue
                self.assertEqual(by_id[fid].basis, mo.BASIS_ILLUSTRATIVE,
                                 f"{r.name}/{fid} should be ILLUSTRATIVE")

    def test_density_score_matches_sourced_structure(self):
        # The density ordinal is derived from the real ift_geo node count/tier —
        # not a parallel copy. Spot-check a dense metro and a rural one.
        by_name = {r.name: r for r in self.sc.rows}
        kc = by_name["Kansas City (bi-state)"]
        dens_kc = {f.factor_id: f for f in kc.factors}[mo.F_DENSITY]
        struct_kc = geo.metro_structure("Kansas City (bi-state)")
        self.assertEqual(kc.n_nodes, struct_kc.n_nodes)
        self.assertEqual(kc.density_tier, struct_kc.density_tier)
        self.assertEqual(dens_kc.score, mo.STRONG)          # very-dense
        np = by_name["North Platte"]
        dens_np = {f.factor_id: f for f in np.factors}[mo.F_DENSITY]
        self.assertEqual(dens_np.score, mo.WEAK)            # rural thin/long-leg

    def test_composite_is_illustrative_ordinal_mean(self):
        for r in self.sc.rows:
            # 1.00-3.00 ordinal mean, never a fabricated 0-100 score
            self.assertGreaterEqual(r.composite_index, 1.0, r.name)
            self.assertLessEqual(r.composite_index, 3.0, r.name)
            expect = round(sum(f.points for f in r.factors) / 7, 2)
            self.assertEqual(r.composite_index, expect, r.name)
            self.assertTrue(r.composite_basis.startswith(mo.BASIS_ILLUSTRATIVE))
            self.assertIn(r.overall_verdict, mo.VALID_SCORES, r.name)

    def test_verdict_counts_reconcile(self):
        counts = self.sc.verdict_counts
        self.assertEqual(sum(counts.values()), self.sc.n_markets)
        got = {mo.STRONG: 0, mo.MODERATE: 0, mo.WEAK: 0}
        for r in self.sc.rows:
            got[r.overall_verdict] += 1
        self.assertEqual(got, counts)

    def test_contestability_and_public_reads_travel_with_each_row(self):
        # Who holds the moat must be stated (so a strong INSOURCED score is not
        # mistaken for a winnable prize), and the ift_geo public/analyst reads ride.
        for r in self.sc.rows:
            self.assertTrue(r.contestability, r.name)
            self.assertTrue(r.overall_read, r.name)
            self.assertEqual(r.moat_note, geo.metro_def(r.name).moat_note)
            self.assertEqual(r.insource_read, geo.metro_def(r.name).insource_read)

    def test_scores_source_label_leads_illustrative_and_names_sourced(self):
        self.assertTrue(self.sc.source_label.startswith(mo.BASIS_ILLUSTRATIVE))
        self.assertIn(mo.BASIS_SOURCED, self.sc.source_label)

    def test_specific_market_reads_track_iftgeo_text(self):
        # Within-archetype variation is honestly reflected, driven by the ift_geo
        # free-text signals (not flattened to the archetype).
        def scores(name):
            return {f.factor_id: f.score for f in mo.market_moat_score(name).factors}
        # Wichita flip → weak switching, but the flip itself is a proof point.
        wich = scores("Wichita")
        self.assertEqual(wich[mo.F_SWITCHING], mo.WEAK)
        self.assertEqual(wich[mo.F_PROOF], mo.STRONG)
        # Mount Carmel–Superior embedded coordinators → workflow-integration moat.
        self.assertEqual(scores("Columbus (OH)")[mo.F_WORKFLOW], mo.STRONG)
        # Mayo captive fleet → infinite switching cost.
        self.assertEqual(scores("Rochester (MN)")[mo.F_SWITCHING], mo.STRONG)
        # UofL co-branding + embedded coordinators → workflow moat.
        self.assertEqual(scores("Louisville")[mo.F_WORKFLOW], mo.STRONG)
        # Ryan Brothers 60-yr relationships → strong first-call + switching.
        mad = scores("Madison")
        self.assertEqual(mad[mo.F_FIRST_CALL], mo.STRONG)
        self.assertEqual(mad[mo.F_SWITCHING], mo.STRONG)
        # "LOW structural moat" (Columbus NE) → downgraded qualitative factors.
        cne = scores("Columbus (NE)")
        self.assertEqual(cne[mo.F_FIRST_CALL], mo.WEAK)
        self.assertEqual(cne[mo.F_SWITCHING], mo.WEAK)


class TestProofPoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ps = mo.proof_points()

    def test_non_empty_and_public_web_labelled(self):
        self.assertTrue(self.ps.available)
        self.assertGreaterEqual(len(self.ps.points), 8)
        # named honestly, no data chip and no asserted exclusivities/rates
        self.assertIn("named honestly", self.ps.source_label)
        self.assertIn("public", self.ps.source_label.lower())

    def test_every_proof_point_names_real_market_and_factors(self):
        market_names = {md.name for md in geo.MARKETS}
        factor_ids = set(mo.FACTOR_ORDER)
        for p in self.ps.points:
            self.assertIn(p.market, market_names, p.market)
            self.assertTrue(p.factors, p.market)
            for fid in p.factors:
                self.assertIn(fid, factor_ids, f"{p.market}: bad factor {fid}")
            self.assertEqual(len(p.factor_names), len(p.factors))
            self.assertTrue(p.claim, p.market)
            self.assertTrue(p.source_note, p.market)

    def test_evidence_is_pulled_verbatim_from_iftgeo(self):
        # The evidence must be the ift_geo field text verbatim — proof it is pulled
        # from the curated public/analyst read, not re-typed (and cannot drift).
        for p in self.ps.points:
            md = geo.metro_def(p.market)
            self.assertIsNotNone(md, p.market)
            field = p.evidence_source.split(".")[-1]
            self.assertEqual(p.evidence, getattr(md, field),
                             f"{p.market}: evidence is not verbatim from ift_geo")
            self.assertTrue(p.evidence, p.market)

    def test_headline_proof_points_present(self):
        by_market = {p.market: p for p in self.ps.points}
        # the four the brief calls out, plus the captive/co-branding pair
        for market in ("Wichita", "Columbus (OH)", "Lincoln", "Madison",
                       "Rochester (MN)", "Louisville"):
            self.assertIn(market, by_market, f"missing proof point: {market}")
        # Wichita flip proves share-of-wallet fragility + is a cross-market proof
        wich = by_market["Wichita"]
        self.assertIn(mo.F_SWITCHING, wich.factors)
        self.assertIn("77%", wich.evidence)          # ~77% county IFT flipped to AMR
        # Mount Carmel proves the workflow-integration moat
        self.assertIn(mo.F_WORKFLOW, by_market["Columbus (OH)"].factors)
        self.assertIn("embedded", by_market["Columbus (OH)"].evidence.lower())

    def test_proof_markets_score_strong_on_factor_seven(self):
        # A market that furnishes a proof point scores strong on cross-market proof.
        for p in self.ps.points:
            row = mo.market_moat_score(p.market)
            proof = {f.factor_id: f for f in row.factors}[mo.F_PROOF]
            self.assertEqual(proof.score, mo.STRONG, p.market)


class TestDegradesNeverRaises(unittest.TestCase):
    def test_unknown_metro_degrades(self):
        r = mo.market_moat_score("Nowhere-ville")
        self.assertFalse(r.available)
        self.assertEqual(r.factors, ())
        self.assertTrue(r.source_label)
        self.assertTrue(r.note)

    def test_all_public_functions_return_without_raising(self):
        # Smoke: the whole public surface runs offline and returns typed records.
        self.assertTrue(mo.moat_factors())
        self.assertTrue(mo.market_moat_scores().available)
        self.assertTrue(mo.proof_points().available)
        self.assertIsNotNone(mo.market_moat_score("Omaha"))


if __name__ == "__main__":
    unittest.main()
