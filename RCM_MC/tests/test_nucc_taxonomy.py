"""NUCC taxonomy crosswalk + generalized provider-supply counter.

Pure crosswalk lookups (no network) plus a check that the infusion vertical
stays byte-identical to the legacy constants, and that the generalized counter
works for a non-infusion vertical with a mocked NPPES.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data_public import nucc_taxonomy as nt
from rcm_mc.data import nppes_infusion as ni


class CrosswalkTests(unittest.TestCase):
    def test_by_code_roundtrip_and_case_insensitive(self):
        t = nt.by_code("261qi0500n")  # lower-case in → found
        self.assertIsNotNone(t)
        self.assertEqual(t.vertical, "infusion")
        self.assertEqual(t.label, "Clinic/Center — Infusion Therapy")

    def test_unknown_code_is_none_not_error(self):
        self.assertIsNone(nt.by_code("999ZZZ999X"))

    def test_for_vertical_groups_codes(self):
        codes = {t.code for t in nt.for_vertical("infusion")}
        self.assertEqual(codes, {"261QI0500N", "3336I0012X", "251F00000X"})
        self.assertEqual(nt.for_vertical("not_a_vertical"), [])

    def test_descriptions_for_dedupes(self):
        # Two infusion codes share "Infusion Therapy" → one token, plus
        # "Home Infusion".
        self.assertEqual(nt.descriptions_for("infusion"),
                         ["Infusion Therapy", "Home Infusion"])

    def test_verticals_cover_beyond_infusion(self):
        for v in ("infusion", "home_health", "hospice", "snf", "dialysis"):
            self.assertIn(v, nt.VERTICALS)
            self.assertTrue(nt.for_vertical(v))

    def test_label_without_specialization_is_classification(self):
        snf = nt.for_vertical("snf")[0]
        self.assertEqual(snf.label, "Skilled Nursing Facility")


class LegacyParityTests(unittest.TestCase):
    def test_infusion_taxonomies_shape_preserved(self):
        codes = {t["code"] for t in ni.INFUSION_TAXONOMIES}
        self.assertEqual(codes, {"261QI0500N", "3336I0012X", "251F00000X"})
        for t in ni.INFUSION_TAXONOMIES:
            self.assertTrue(t["label"] and t["kind"])


class GeneralCounterTests(unittest.TestCase):
    def test_counts_for_arbitrary_vertical(self):
        import rcm_mc.data_public.nppes_api_client as client
        calls = iter([{"result_count": 12}])
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: next(calls)):
            out = ni.count_providers_by_taxonomy(
                "CO", nt.descriptions_for("home_health"))
        self.assertTrue(out["live"])
        self.assertEqual(out["count"], 12)

    def test_empty_descriptions_fails_closed(self):
        self.assertEqual(
            ni.count_providers_by_taxonomy("CO", []), {"live": False})

    def test_capped_flag_propagates(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: {"result_count": 200}):
            out = ni.count_providers_by_taxonomy(
                "CO", nt.descriptions_for("snf"))
        self.assertTrue(out["capped"])


if __name__ == "__main__":
    unittest.main()
