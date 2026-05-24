"""Investable-evidence scoring v1 — transparent, peer-relative, no black box.

Asserts the honesty discipline: every component's raw value/weight/percentile
is exposed; the index is the mean of available component percentiles; z-scores
are guarded (n>=5, sd>0); risk flags are surfaced separately and never folded
into the index; caveats disclaim recommendation/revenue/market-share/causality.
"""
from __future__ import annotations

import unittest

from rcm_mc.data import snf
from rcm_mc.data.cross_sector import SECTOR_BY_ID
from rcm_mc.data.investable_evidence import evidence_profile


def _a_state_ccn(mod_loader, state="TX"):
    for c, p in mod_loader().items():
        if (getattr(p, "state", "") or "").upper() == state:
            return c
    return next(iter(mod_loader()))


class ProfileShapeTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_state_ccn(snf.load_snf_providers)
        self.ep = evidence_profile("nursing-homes", self.ccn)

    def test_core_fields_present(self):
        ep = self.ep
        self.assertIsNotNone(ep)
        self.assertTrue(ep.components)
        self.assertEqual(ep.ccn, self.ccn)
        self.assertGreater(ep.sample_size, 0)
        self.assertIn("evidence_index = mean", ep.formula)

    def test_index_is_mean_of_available_percentiles(self):
        ep = self.ep
        pcts = [c.peer_percentile for c in ep.components
                if c.peer_percentile is not None]
        if pcts:
            self.assertAlmostEqual(ep.evidence_index,
                                   round(sum(pcts) / len(pcts), 1), places=1)
            self.assertTrue(0 <= ep.evidence_index <= 100)
        else:
            self.assertIsNone(ep.evidence_index)

    def test_every_component_exposes_its_inputs(self):
        for c in self.ep.components:
            self.assertTrue(c.label)
            self.assertGreater(c.weight, 0)
            if c.peer_percentile is not None:
                self.assertTrue(0 <= c.peer_percentile <= 100)

    def test_weights_sum_to_about_one(self):
        total = sum(c.weight for c in self.ep.components)
        self.assertAlmostEqual(total, 1.0, places=1)


class GuardrailTests(unittest.TestCase):
    def test_zscore_guarded_on_tiny_peer_set(self):
        # LTCH has states with <5 facilities — z-score and percentile must
        # be suppressed there.
        found = False
        for st in ("VT", "WY", "AK", "MT", "ND", "SD", "DE", "RI", "NH"):
            from rcm_mc.data import ltch
            ccns = [c for c, p in ltch.load_ltch_providers().items()
                    if p.state == st]
            if 0 < len(ccns) < 5:
                ep = evidence_profile("long-term-care-hospital", ccns[0])
                self.assertIsNotNone(ep)
                for c in ep.components:
                    self.assertIsNone(c.z_score, f"{st}: z-score not suppressed")
                found = True
        self.assertTrue(found, "expected a tiny-sample LTCH state")

    def test_risk_flags_only_where_data_exists(self):
        snf_ccn = _a_state_ccn(snf.load_snf_providers)
        self.assertTrue(evidence_profile("nursing-homes", snf_ccn).risk_flags)
        # Sectors without enforcement data carry no risk flags.
        for sid in ("home-health", "hospice", "dialysis", "inpatient-rehab",
                    "long-term-care-hospital"):
            spec = SECTOR_BY_ID[sid]
            ccn = next(iter(spec.providers_loader()))
            self.assertEqual(evidence_profile(sid, ccn).risk_flags, [])

    def test_caveats_disclaim_recommendation_and_separation(self):
        cav = " ".join(self.caveats())
        self.assertIn("not an investment recommendation", cav.lower())
        self.assertIn("market share", cav.lower())
        self.assertIn("never folded into the evidence index", cav.lower())

    def caveats(self):
        ccn = _a_state_ccn(snf.load_snf_providers)
        return evidence_profile("nursing-homes", ccn).caveats

    def test_unknown_sector_and_ccn(self):
        self.assertIsNone(evidence_profile("dental", "x"))
        self.assertIsNone(evidence_profile("nursing-homes", "000000"))


class AllSectorsResolveTests(unittest.TestCase):
    def test_every_live_sector_builds_a_profile(self):
        for sid, spec in SECTOR_BY_ID.items():
            ccn = next(iter(spec.providers_loader()))
            ep = evidence_profile(sid, ccn)
            self.assertIsNotNone(ep, f"{sid} profile is None")
            self.assertTrue(ep.components, f"{sid} has no components")
            self.assertTrue(ep.caveats, f"{sid} has no caveats")


if __name__ == "__main__":
    unittest.main()
