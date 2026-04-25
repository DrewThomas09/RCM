"""Tests for the payer contract strength estimator."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed(store, rates):
    """Seed pricing_payer_rates + minimum NPPES for tests."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    npis = sorted({r["npi"] for r in rates})
    with store.connect() as con:
        # Seed NPPES for state lookup
        for npi in npis:
            con.execute(
                "INSERT OR REPLACE INTO pricing_nppes "
                "(npi, entity_type, state, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (npi, 2, "GA", now))
        for r in rates:
            con.execute(
                "INSERT OR REPLACE INTO "
                "pricing_payer_rates "
                "(payer_name, plan_name, npi, code, "
                " code_type, negotiation_arrangement, "
                " negotiated_rate, service_line, "
                " loaded_at) "
                "VALUES "
                "(?, '', ?, ?, 'CPT', 'ffs', ?, ?, ?)",
                (r["payer_name"], r["npi"], r["code"],
                 r["rate"], r.get("service_line"), now))
        con.commit()


class TestPercentile(unittest.TestCase):
    def test_basic(self):
        from rcm_mc.ml.contract_strength import _percentile
        self.assertEqual(_percentile([10, 20, 30, 40, 50],
                                     0.50), 30)
        self.assertEqual(_percentile([100], 0.50), 100)
        self.assertEqual(_percentile([], 0.50), 0.0)

    def test_interpolation(self):
        from rcm_mc.ml.contract_strength import _percentile
        # p25 of [1,2,3,4,5]: index = 4*0.25=1, val=2
        self.assertEqual(_percentile([1, 2, 3, 4, 5], 0.25),
                         2)


class TestStrengthBand(unittest.TestCase):
    def test_all_bands(self):
        from rcm_mc.ml.contract_strength import (
            _band_for_strength,
        )
        self.assertEqual(_band_for_strength(0.80), "very_weak")
        self.assertEqual(_band_for_strength(0.90), "weak")
        self.assertEqual(_band_for_strength(1.00), "market")
        self.assertEqual(_band_for_strength(1.10), "strong")
        self.assertEqual(_band_for_strength(1.30),
                         "very_strong")


class TestMarketReferenceRates(unittest.TestCase):
    def test_builds_percentiles_per_pair(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_market_reference_rates,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            rates = []
            # 5 NPIs, all on Aetna for code 27447
            for i in range(5):
                rates.append({
                    "payer_name": "Aetna",
                    "npi": f"100{i:07d}",
                    "code": "27447",
                    "rate": 20_000 + i * 1_000,
                })
            _seed(store, rates)
            ref = compute_market_reference_rates(
                store, state="GA")
            self.assertIn(("Aetna", "27447"),
                          ref.rates_by_pair)
            r = ref.rates_by_pair[("Aetna", "27447")]
            self.assertEqual(r["n"], 5)
            self.assertAlmostEqual(r["p50"], 22_000.0)
        finally:
            tmp.cleanup()

    def test_min_providers_filter(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_market_reference_rates,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            # Only 2 NPIs for code 99213 — below default 3
            rates = [
                {"payer_name": "Aetna",
                 "npi": "1000000001",
                 "code": "99213", "rate": 100},
                {"payer_name": "Aetna",
                 "npi": "1000000002",
                 "code": "99213", "rate": 110},
            ]
            _seed(store, rates)
            ref = compute_market_reference_rates(
                store, state="GA")
            # Filtered out by min_providers=3
            self.assertNotIn(
                ("Aetna", "99213"), ref.rates_by_pair)
            # Lower the bar
            ref2 = compute_market_reference_rates(
                store, state="GA", min_providers=2)
            self.assertIn(
                ("Aetna", "99213"), ref2.rates_by_pair)
        finally:
            tmp.cleanup()


class TestContractStrength(unittest.TestCase):
    def _build_market(self, store, target_npi,
                      target_premium: float = 1.0):
        """6 peer NPIs on the same payers + codes; target_npi
        prices at target_premium × peer median."""
        rates = []
        codes = [
            ("Aetna", "27447", 20_000),
            ("Aetna", "70551", 1_200),
            ("UHC", "27447", 22_000),
            ("UHC", "70551", 1_300),
            ("Cigna", "27447", 21_000),
            ("Cigna", "70551", 1_250),
        ]
        # 6 peers per code with rates around the median
        for payer, code, base in codes:
            for i in range(6):
                rates.append({
                    "payer_name": payer,
                    "npi": f"200{i:07d}",
                    "code": code,
                    "rate": base * (0.85 + i * 0.05),
                })
        # Target NPI on every (payer, code)
        for payer, code, base in codes:
            rates.append({
                "payer_name": payer,
                "npi": target_npi,
                "code": code,
                "rate": base * target_premium,
            })
        _seed(store, rates)

    def test_strong_negotiator(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            self._build_market(store, "TARGETNPI",
                               target_premium=1.10)
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA")
            self.assertIsNotNone(score)
            # 10% premium → overall strength near 1.10
            self.assertGreater(score.overall_strength, 1.05)
            self.assertEqual(
                score.overall_band, "strong")
            self.assertEqual(score.n_codes_compared, 6)
            self.assertEqual(score.n_payers_compared, 3)
            # Most contracts above market → flagged in notes
            self.assertGreater(score.pct_above_market, 0.50)
            self.assertTrue(any("exit-cycle" in n
                                for n in score.notes))
        finally:
            tmp.cleanup()

    def test_weak_negotiator(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            self._build_market(store, "TARGETNPI",
                               target_premium=0.80)
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA")
            self.assertLess(score.overall_strength, 0.90)
            self.assertEqual(score.overall_band, "very_weak")
            self.assertGreater(score.pct_below_market, 0.50)
            self.assertTrue(any("uplift opportunity" in n
                                for n in score.notes))
        finally:
            tmp.cleanup()

    def test_at_market_negotiator(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            self._build_market(store, "TARGETNPI",
                               target_premium=1.00)
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA")
            self.assertGreater(score.overall_strength, 0.95)
            self.assertLess(score.overall_strength, 1.05)
            self.assertEqual(score.overall_band, "market")
        finally:
            tmp.cleanup()

    def test_per_payer_breakdown(self):
        """Asymmetric pricing: target gets premium on Aetna,
        discount on UHC."""
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            rates = []
            # 4 peers per (payer, code)
            for payer, code, base in [
                ("Aetna", "27447", 20_000),
                ("UHC", "27447", 22_000),
            ]:
                for i in range(5):
                    rates.append({
                        "payer_name": payer,
                        "npi": f"300{i:07d}",
                        "code": code,
                        "rate": base * (0.90 + i * 0.05),
                    })
            # 5 codes for the target — all premium on Aetna,
            # all discount on UHC
            for code, base in [
                ("27447", 20_000), ("70551", 1_200),
                ("99213", 100), ("99214", 150),
                ("70553", 1_500),
            ]:
                # Add peer rates for the new codes too
                for i in range(5):
                    rates.append({
                        "payer_name": "Aetna",
                        "npi": f"300{i:07d}",
                        "code": code,
                        "rate": base * (0.90 + i * 0.05),
                    })
                    rates.append({
                        "payer_name": "UHC",
                        "npi": f"300{i:07d}",
                        "code": code,
                        "rate": base * 1.10
                        * (0.90 + i * 0.05),
                    })
                rates.append({
                    "payer_name": "Aetna",
                    "npi": "TARGETNPI",
                    "code": code, "rate": base * 1.30,
                })
                rates.append({
                    "payer_name": "UHC",
                    "npi": "TARGETNPI",
                    "code": code,
                    "rate": base * 1.10 * 0.80,
                })
            _seed(store, rates)
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA",
                min_codes=5)
            self.assertIn("Aetna", score.by_payer)
            self.assertIn("UHC", score.by_payer)
            # Aetna should be strong, UHC weak
            self.assertGreater(score.by_payer["Aetna"], 1.10)
            self.assertLess(score.by_payer["UHC"], 0.90)
        finally:
            tmp.cleanup()

    def test_top_variances_surfaced(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            self._build_market(store, "TARGETNPI",
                               target_premium=1.00)
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA", top_k=3)
            self.assertLessEqual(
                len(score.top_above_market), 3)
            self.assertLessEqual(
                len(score.top_below_market), 3)
            # Sorted by ratio descending / ascending
            ratios_above = [c.rate_ratio
                            for c in score.top_above_market]
            self.assertEqual(
                ratios_above,
                sorted(ratios_above, reverse=True))
        finally:
            tmp.cleanup()

    def test_volume_weighting(self):
        """A small-rate-ratio code with huge volume should
        dominate; no-volume case should weight equally."""
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            rates = []
            # 6 peer NPIs on 2 codes
            for code, base in [("27447", 20000),
                               ("99213", 100)]:
                for i in range(6):
                    rates.append({
                        "payer_name": "Aetna",
                        "npi": f"400{i:07d}",
                        "code": code,
                        "rate": base * (0.85 + i * 0.05),
                    })
            # Target: above market on small code, below
            # market on big code
            rates.append({
                "payer_name": "Aetna",
                "npi": "TARGETNPI",
                "code": "27447", "rate": 18_000,  # below
            })
            rates.append({
                "payer_name": "Aetna",
                "npi": "TARGETNPI",
                "code": "99213", "rate": 130,    # above
            })
            _seed(store, rates)
            # Equal-weight: roughly cancels out
            score_eq = compute_contract_strength(
                store, "TARGETNPI", state="GA",
                min_codes=2)
            # Volume-weighted: big code dominates → below market
            score_vol = compute_contract_strength(
                store, "TARGETNPI", state="GA",
                min_codes=2,
                code_volumes={"27447": 1000,
                              "99213": 10})
            self.assertLess(
                score_vol.overall_strength,
                score_eq.overall_strength)
        finally:
            tmp.cleanup()

    def test_too_few_codes_returns_none(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            compute_contract_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            self._build_market(store, "TARGETNPI",
                               target_premium=1.0)
            # Default min_codes is 5; we only have 6 codes,
            # but require 100
            score = compute_contract_strength(
                store, "TARGETNPI", state="GA",
                min_codes=100)
            self.assertIsNone(score)
        finally:
            tmp.cleanup()


class TestRanking(unittest.TestCase):
    def test_ranks_descending_by_strength(self):
        from rcm_mc.pricing.store import PricingStore
        from rcm_mc.ml.contract_strength import (
            rank_hospitals_by_strength,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            rates = []
            # 5 peers
            for code, base in [("27447", 20000),
                               ("70551", 1200),
                               ("99213", 100)]:
                for i in range(5):
                    rates.append({
                        "payer_name": "Aetna",
                        "npi": f"500{i:07d}",
                        "code": code,
                        "rate": base * (0.90 + i * 0.05),
                    })
            # 3 hospitals at different premiums
            for npi, premium in [
                ("STRONGNPI", 1.25),
                ("WEAKNPI", 0.80),
                ("MARKETNPI", 1.00),
            ]:
                for code, base in [("27447", 20000),
                                   ("70551", 1200),
                                   ("99213", 100)]:
                    rates.append({
                        "payer_name": "Aetna",
                        "npi": npi, "code": code,
                        "rate": base * premium,
                    })
            _seed(store, rates)
            scores = rank_hospitals_by_strength(
                store,
                ["STRONGNPI", "WEAKNPI", "MARKETNPI"],
                state="GA", min_codes=3)
            self.assertEqual(len(scores), 3)
            self.assertEqual(scores[0].npi, "STRONGNPI")
            self.assertEqual(scores[-1].npi, "WEAKNPI")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
