"""Golden test for PACK-01 composite diligence pack.

Builds a pack from a deal bundle and asserts:
- the constituent sections are present and in order,
- flags roll up severity-ranked (risk before warn before info),
- a heavy-Medicaid CA target surfaces its regulatory red flags at the pack level,
- partner render carries no internal assumptions; internal does,
- pack reconciliation holds only when every section reconciles.
"""
import unittest

from rcm_mc.cdd.diligence_pack import build_diligence_pack

DEAL = {
    "name": "Project Cedar",
    "tam": {
        "segments": [
            {"segment": "ASC", "unit_count": 500, "price": 20.0, "penetration_rate": 0.4},
            {"segment": "HOPD", "unit_count": 1000, "price": 10.0, "penetration_rate": 0.5},
        ],
        "sales_capacity_units": 600, "win_rate": 0.5, "top_down": 18000.0,
        "source": "Golden", "vintage": "2026",
    },
    "concentration": {
        "accounts": [{"account": "A", "revenue": 50}, {"account": "B", "revenue": 30},
                     {"account": "C", "revenue": 20}],
        "source": "Golden", "vintage": "2026",
    },
    "regulatory": {"payer_mix": {"Medicaid": 0.50}, "state": "CA", "subsector": "home-health"},
    "vintage": "2026",
}


class TestDiligencePack(unittest.TestCase):
    def test_sections_present_and_ordered(self):
        pack = build_diligence_pack(DEAL)
        ids = [ex.feature_id for ex in pack.exhibits]
        self.assertEqual(ids, ["NEW-01", "NEW-10", "NEW-17"])

    def test_flag_rollup_severity_ranked(self):
        pack = build_diligence_pack(DEAL)
        flags = pack.all_flags()
        ranks = [{"risk": 0, "warn": 1, "info": 2}[f["severity"]] for f in flags]
        self.assertEqual(ranks, sorted(ranks))

    def test_regulatory_red_flags_surface_in_summary(self):
        ex = build_diligence_pack(DEAL).summary_exhibit()
        codes = ex.flag_codes()
        self.assertTrue(any("obbba_medicaid_exposure" in c for c in codes))
        self.assertTrue(any("state_pe_oversight" in c for c in codes))

    def test_concentration_red_flag_rolls_up(self):
        # Account A is 50% of revenue -> single_account_over_40pct (risk).
        flags = build_diligence_pack(DEAL).all_flags()
        self.assertTrue(any(f["code"] == "single_account_over_40pct" for f in flags))

    def test_partner_render_no_assumption_leak(self):
        pack = build_diligence_pack(DEAL)
        partner = pack.render(internal_mode=False)
        for sub in partner["exhibits"]:
            self.assertNotIn("assumptions", sub)
        internal = pack.render(internal_mode=True)
        # At least one internal section exposes assumptions (TAM/SAM has them).
        self.assertTrue(any("assumptions" in sub for sub in internal["exhibits"]))

    def test_summary_reconciles_when_sections_reconcile(self):
        ex = build_diligence_pack(DEAL).summary_exhibit()
        # NEW-01 here has top_down within tolerance, others reconcile -> all good.
        self.assertEqual(ex.meta["reconciled_all"], True)
        self.assertTrue(ex.reconciled)

    def test_empty_bundle_raises(self):
        with self.assertRaises(ValueError):
            build_diligence_pack({"name": "empty"})


if __name__ == "__main__":
    unittest.main()
