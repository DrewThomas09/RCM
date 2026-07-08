"""Tests for the claims-understatement analyzer + gross-up (understatement.py).

Real-path only — no mocks of our own code. Each test crafts a small synthetic
claims frame that exhibits one understatement cause, asserts detection fires
correctly, checks the gross-up arithmetic is exactly reproducible for a fixed
assumption (hand-computed), exercises the "not detectable -> diligence request"
path, confirms the scorecard renders safely (html-escaped, basis labels, no
markup leaks), and enforces the honesty rail (no unlabeled "true"/precise
figure).
"""
from __future__ import annotations

import unittest

from rcm_mc.npi_cleaner import understatement as u
from rcm_mc.npi_cleaner import understatement_report as ur


# Luhn-valid synthetic NPIs (pass the CMS 80840 check) — not real providers.
NPI_A = "1679576722"
NPI_B = "1245319599"
NPI_C = "1699999984"
NPI_R = "1234567893"  # rendering


def _finding(result: u.Result, cause_id: str) -> u.Finding:
    for f in result.findings:
        if f.cause_id == cause_id:
            return f
    raise AssertionError(f"no finding for cause {cause_id}")


class TestTaxonomy(unittest.TestCase):
    def test_taxonomy_is_complete_and_well_formed(self):
        # Every entry files under exactly one of the three levers and states a
        # method + assumption a partner can act on.
        self.assertGreaterEqual(len(u.TAXONOMY), 18)
        for c in u.TAXONOMY:
            self.assertIn(c.lever, u.LEVERS)
            for fld in (c.name, c.why_it_understates, c.how_to_detect,
                        c.how_to_correct, c.magnitude):
                self.assertTrue(fld and fld.strip())
        # All three levers are represented.
        levers = {c.lever for c in u.TAXONOMY}
        self.assertEqual(levers, set(u.LEVERS))
        # ids are unique.
        ids = [c.id for c in u.TAXONOMY]
        self.assertEqual(len(ids), len(set(ids)))


class TestGrossUpMath(unittest.TestCase):
    def test_volume_grossup_exact(self):
        # Hand-computed: 800 x (1 + 0.10 + 0.05 + 0.15) ... but band uses the
        # per-component low/base/high sums.
        comps = [
            {"uplift_low": 0.05, "uplift_base": 0.10, "uplift_high": 0.15},
            {"uplift_low": 0.00, "uplift_base": 0.05, "uplift_high": 0.10},
        ]
        g = u.grossup_volume(800, comps)
        self.assertEqual(g["observed"], 800)
        # base: 800 * (1 + 0.15) = 920
        self.assertEqual(g["base"], 920)
        # low: 800 * (1 + 0.05) = 840
        self.assertEqual(g["low"], 840)
        # high: 800 * (1 + 0.25) = 1000
        self.assertEqual(g["high"], 1000)

    def test_realized_rate_grossup_exact(self):
        g = u.grossup_realized_rate(100.0, 0.05, (0.025, 0.075))
        self.assertAlmostEqual(g["base"], 105.0, places=6)
        self.assertAlmostEqual(g["low"], 102.5, places=6)
        self.assertAlmostEqual(g["high"], 107.5, places=6)

    def test_analyze_volume_single_component_reproducible(self):
        # A frame where ONLY the self-pay add-back fires: denials are present
        # (captured, no add-back), there is a payer column but zero self-pay
        # rows (component fires), and no date column (run-out not assessable).
        headers = ["ClaimID", "BillingNPI", "PayerName", "DenialCode"]
        rows = []
        for i in range(10):
            code = "CO-45" if i == 0 else ""   # one denied line => captured
            rows.append([str(1000 + i), NPI_A, "Aetna", code])
        A = u.Assumptions()  # self_pay_share = 0.08
        res = u.analyze(headers, rows, assumptions=A)
        gv = res.grossups["volume"]
        # Exactly one add-back component, and it is the self-pay one.
        self.assertTrue(gv.computable)
        self.assertEqual([c["id"] for c in gv.components],
                         ["self_pay_never_billed"])
        # Hand-computed: observed 10 x (1 + 0.08/0.92) = 10.8695... -> 11
        self.assertEqual(gv.observed, 10.0)
        self.assertEqual(gv.base, 11.0)
        # Denials captured, not added back.
        self.assertEqual(_finding(res, "denied_lines_dropped").status,
                         u.STATUS_CLEAN)
        # Self-pay column present but none found -> detected understatement.
        self.assertEqual(_finding(res, "self_pay_never_billed").status,
                         u.STATUS_DETECTED)


class TestVolumeDetection(unittest.TestCase):
    def test_denied_lines_present_are_captured(self):
        headers = ["ClaimID", "BillingNPI", "BilledAmt", "PaidAmt",
                   "DenialCode"]
        rows = [
            ["1", NPI_A, "420", "240", ""],
            ["2", NPI_A, "420", "0", "CO-197"],   # denied, zero paid
            ["3", NPI_B, "600", "0", "PR-1"],      # denied, zero paid
        ]
        res = u.analyze(headers, rows)
        f = _finding(res, "denied_lines_dropped")
        self.assertEqual(f.status, u.STATUS_CLEAN)
        self.assertEqual(f.evidence["denied_lines"], 2)

    def test_zero_paid_proxy_when_no_carc(self):
        # No CARC column, but billed>0 & paid==0 is the zero-pay proxy.
        headers = ["ClaimID", "BillingNPI", "BilledAmt", "PaidAmt"]
        rows = [["1", NPI_A, "420", "0"], ["2", NPI_A, "420", "240"]]
        res = u.analyze(headers, rows)
        f = _finding(res, "denied_lines_dropped")
        self.assertEqual(f.status, u.STATUS_CLEAN)
        self.assertEqual(f.evidence["mode"], "zeropay")

    def test_self_pay_labeled_captured(self):
        headers = ["ClaimID", "BillingNPI", "PayerName", "FinancialClass"]
        rows = [
            ["1", NPI_A, "Aetna", "COMMERCIAL"],
            ["2", NPI_A, "Self Pay", "SELFPAY"],
            ["3", NPI_B, "Cash Pay", "SELFPAY"],
        ]
        res = u.analyze(headers, rows)
        f = _finding(res, "self_pay_never_billed")
        self.assertEqual(f.status, u.STATUS_CLEAN)
        self.assertEqual(f.evidence["self_pay_lines"], 2)

    def test_split_prof_facility(self):
        headers = ["ClaimID", "BillingNPI", "RevenueCode", "HCPCS",
                   "PlaceOfService"]
        rows = [
            ["1", NPI_A, "", "99213", "11"],     # professional (office)
            ["2", NPI_A, "0450", "", "22"],      # facility (revenue code)
        ]
        res = u.analyze(headers, rows)
        f = _finding(res, "split_prof_facility_miscount")
        self.assertEqual(f.status, u.STATUS_DETECTED)
        self.assertEqual(f.evidence["facility_lines"], 1)
        self.assertEqual(f.evidence["professional_lines"], 1)

    def test_secondary_cob_leg_detected(self):
        headers = ["ClaimID", "BillingNPI", "PayerSequence", "PayerName"]
        rows = [
            ["1", NPI_A, "Primary", "Aetna"],
            ["1", NPI_A, "Secondary", "Medicare"],
        ]
        res = u.analyze(headers, rows)
        f = _finding(res, "cob_secondary_collapsed")
        self.assertEqual(f.status, u.STATUS_DETECTED)
        self.assertEqual(f.evidence["secondary_legs"], 1)


class TestPriceDetection(unittest.TestCase):
    def test_realized_rate_computable_from_paid(self):
        headers = ["ClaimID", "BillingNPI", "BilledAmt", "AllowedAmt",
                   "PaidAmt", "Units"]
        rows = [
            ["1", NPI_A, "400", "300", "200", "1"],
            ["2", NPI_A, "400", "300", "300", "1"],
        ]
        res = u.analyze(headers, rows, assumptions=u.Assumptions())
        g = res.grossups["realized_rate"]
        self.assertTrue(g.computable)
        self.assertEqual(g.label, "MODELED")
        # observed rate = (200+300)/2 units = 250; base = 250 * 1.05 = 262.5
        self.assertAlmostEqual(g.observed, 250.0, places=6)
        self.assertAlmostEqual(g.base, 262.5, places=6)

    def test_billed_only_realized_rate_not_computable(self):
        headers = ["ClaimID", "BillingNPI", "BilledAmt"]
        rows = [["1", NPI_A, "400"], ["2", NPI_A, "600"]]
        res = u.analyze(headers, rows)
        g = res.grossups["realized_rate"]
        self.assertFalse(g.computable)
        self.assertIsNotNone(g.diligence)
        # The billed-not-allowed-paid cause is flagged as an understatement.
        self.assertEqual(_finding(res, "billed_not_allowed_paid").status,
                         u.STATUS_DETECTED)


class TestScaleDetection(unittest.TestCase):
    def test_npi_tin_fragmentation_with_owner_observed_rollup(self):
        headers = ["ClaimID", "BillingNPI", "BillingTIN", "OwnerName",
                   "BilledAmt"]
        rows = [
            ["1", NPI_A, "88-1", "Summit Health", "400"],
            ["2", NPI_B, "88-2", "Summit Health", "500"],
            ["3", NPI_C, "88-3", "Summit Health", "600"],
        ]
        res = u.analyze(headers, rows)
        f = _finding(res, "npi_tin_fragmentation")
        self.assertEqual(f.status, u.STATUS_DETECTED)
        self.assertEqual(f.evidence["distinct_npis"], 3)
        self.assertEqual(f.evidence["distinct_owners"], 1)
        g = res.grossups["scale"]
        # Owner roll-up is OBSERVED (real arithmetic), not MODELED.
        self.assertEqual(g.label, "OBSERVED")
        self.assertTrue(g.computable)
        self.assertEqual(g.observed, 3.0)  # 3 distinct NPIs
        self.assertEqual(g.base, 1.0)       # roll to 1 owner
        # Owner charge roll-up is a real sum.
        self.assertEqual(g.components[0]["owner"], "Summit Health")
        self.assertAlmostEqual(g.components[0]["charges"], 1500.0, places=2)

    def test_billing_vs_rendering_attribution(self):
        headers = ["ClaimID", "BillingNPI", "RenderingNPI"]
        rows = [["1", NPI_A, NPI_R]]
        res = u.analyze(headers, rows)
        self.assertEqual(
            _finding(res, "billing_vs_rendering_attribution").status,
            u.STATUS_DETECTED)


class TestNotDetectablePath(unittest.TestCase):
    def test_minimal_frame_emits_diligence_requests(self):
        # Only a claim id and a billing NPI: most causes are not detectable and
        # must degrade to diligence requests, never raise.
        headers = ["ClaimID", "BillingProviderNPI"]
        rows = [["1", NPI_A], ["2", NPI_B]]
        res = u.analyze(headers, rows)
        self.assertTrue(res.diligence_requests)
        # Realized rate is unobservable without paid -> not computable + ask.
        rr = res.grossups["realized_rate"]
        self.assertFalse(rr.computable)
        self.assertIsNotNone(rr.diligence)
        # Scale can't roll to an owner without an owner column -> not computable.
        sc = res.grossups["scale"]
        self.assertFalse(sc.computable)
        self.assertIsNotNone(sc.diligence)
        # Several causes are explicitly not_detectable.
        na = [f for f in res.findings if f.status == u.STATUS_NOT_DETECTABLE]
        self.assertGreaterEqual(len(na), 5)
        for f in na:
            self.assertTrue(f.diligence)

    def test_empty_headers_degrade_not_raise(self):
        res = u.analyze([], [])
        self.assertEqual(res.n_rows, 0)
        self.assertTrue(res.warnings)


class TestReportRendering(unittest.TestCase):
    def _sample_result(self) -> u.Result:
        return u.analyze_bytes(u.sample_claims_csv().encode(), "demo.csv")

    def test_html_renders_nonempty_with_basis_and_labels(self):
        res = self._sample_result()
        html = ur.build_report(res, "demo.csv", "2026-07-08T00:00:00+00:00")
        self.assertTrue(html)
        self.assertIn("Claims-understatement scorecard", html)
        # Basis labels present on figures.
        self.assertIn("basis", html.lower())
        # Every gross-up badge is a labeled tag, never a bare number.
        self.assertIn("MODELED", html)
        self.assertIn("OBSERVED", html)
        # Per-lever sections present.
        self.assertIn("Volume", html)
        self.assertIn("Price", html)
        self.assertIn("Scale", html)

    def test_html_escapes_dynamic_strings_no_markup_leak(self):
        # A dangerous column name must be detected AND escaped in the output.
        headers = ["ClaimID", "Owner<Name>&\"x", "BillingNPI", "PaidAmt"]
        rows = [["1", "Summit", NPI_A, "200"]]
        res = u.analyze(headers, rows)
        html = ur.build_report(res, "x<y>.csv", "2026-07-08")
        # Raw markup must not appear; the escaped form must.
        self.assertNotIn("Owner<Name>", html)
        self.assertIn("Owner&lt;Name&gt;", html)
        self.assertNotIn("<script", html.lower())
        # The file name is escaped too.
        self.assertNotIn("x<y>.csv", html)
        self.assertIn("x&lt;y&gt;.csv", html)

    def test_text_render_nonempty(self):
        res = self._sample_result()
        txt = ur.render_text(res, "demo.csv")
        self.assertIn("CLAIMS-UNDERSTATEMENT SCORECARD", txt)
        self.assertIn("VOLUME", txt)
        self.assertIn("DILIGENCE REQUESTS", txt)


class TestHonesty(unittest.TestCase):
    def test_every_grossup_is_labeled(self):
        # No corrected figure is ever presented without a MODELED/OBSERVED
        # label and, when computable+MODELED, a stated assumption.
        res = u.analyze_bytes(u.sample_claims_csv().encode(), "demo.csv")
        for g in res.grossups.values():
            self.assertIn(g.label, ("MODELED", "OBSERVED"))
            if g.computable:
                self.assertTrue(g.method and g.method != "n/a")
                if g.label == "MODELED":
                    self.assertTrue(g.assumption and g.assumption != "n/a")
                # A computable estimate always carries a base figure.
                self.assertIsNotNone(g.base)
            else:
                # A non-computable gross-up must emit a diligence ask instead
                # of a fabricated number.
                self.assertIsNotNone(g.diligence)
                self.assertIsNone(g.base)

    def test_modeled_figures_carry_assumption_in_render(self):
        # The rendered scorecard shows the assumption next to every modeled
        # estimate — the number is never naked.
        res = u.analyze_bytes(u.sample_claims_csv().encode(), "demo.csv")
        html = ur.build_report(res, "demo.csv", "2026-07-08")
        self.assertIn("Assumption:", html)
        self.assertIn("Method:", html)

    def test_analyze_frame_matches_rows_path(self):
        # The pandas adapter exercises the same real path as the rows API.
        import pandas as pd
        df = pd.DataFrame(
            {"ClaimID": ["1", "2"], "BillingNPI": [NPI_A, NPI_B],
             "OwnerName": ["Summit", "Summit"], "BilledAmt": ["400", "500"],
             "PaidAmt": ["300", "400"]})
        res = u.analyze_frame(df)
        self.assertEqual(res.n_rows, 2)
        self.assertEqual(res.grossups["scale"].label, "OBSERVED")


if __name__ == "__main__":
    unittest.main()
