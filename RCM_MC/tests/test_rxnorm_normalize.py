"""DQ tests for RxNorm NDC + concept normalization.

The headline check is the NDC normalization round-trip: every representation of
the same NDC must reduce to one canonical 11-digit key, because that canonical
form is the only thing that makes the cross-source join work.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.rxnorm import normalize as nz
from rcm_mc.data_public.rxnorm.normalize import (NdcNormalizationError,
                                                 format_ndc_11, normalize_ndc)


class NdcNormalizationTests(unittest.TestCase):
    def test_4_4_2_pads_labeler(self):
        # 0071-0155-23 (4-4-2) → labeler padded to 5 → 00071-0155-23
        self.assertEqual(normalize_ndc("0071-0155-23"), "00071015523")

    def test_5_3_2_pads_product(self):
        self.assertEqual(normalize_ndc("55150-313-01"), "55150031301")

    def test_5_4_1_pads_package(self):
        self.assertEqual(normalize_ndc("12345-6789-1"), "12345678901")

    def test_already_5_4_2_is_stable(self):
        self.assertEqual(normalize_ndc("12345-6789-01"), "12345678901")

    def test_unhyphenated_11_passthrough(self):
        self.assertEqual(normalize_ndc("00409189620"), "00409189620")

    def test_unhyphenated_10_assumes_4_4_2_by_default(self):
        # 0409189620 (10 digit, ambiguous) → prepend one zero (4-4-2 default)
        self.assertEqual(normalize_ndc("0409189620"), "00409189620")

    def test_round_trip_all_formats_to_one_key(self):
        # Every representation of openFDA's 0409-1896-20 morphine NDC must
        # collapse to the same canonical key.
        forms = ["0409-1896-20", "00409-1896-20", "00409189620", "0409189620"]
        keys = {normalize_ndc(f) for f in forms}
        self.assertEqual(keys, {"00409189620"})

    def test_format_then_normalize_is_identity(self):
        for ndc_11 in ("00071015523", "55150031301", "12345678901"):
            self.assertEqual(normalize_ndc(format_ndc_11(ndc_11)), ndc_11)

    def test_rejects_garbage(self):
        for bad in ("", "abc", "123-456", "1234567890123"):
            with self.assertRaises(NdcNormalizationError):
                normalize_ndc(bad)

    def test_rejects_oversized_segment(self):
        with self.assertRaises(NdcNormalizationError):
            normalize_ndc("123456-7890-12")


class StatusAndParseTests(unittest.TestCase):
    def test_status_mapping(self):
        self.assertEqual(nz.normalize_status("Active"), "active")
        self.assertEqual(nz.normalize_status("Retired"), "retired")
        self.assertEqual(nz.normalize_status("Remapped"), "remapped")
        self.assertEqual(nz.normalize_status("Obsolete"), "retired")
        self.assertEqual(nz.normalize_status(""), "active")

    def test_class_type_mapping(self):
        self.assertEqual(nz.normalize_class_type("ATC1-4"), "ATC")
        self.assertEqual(nz.normalize_class_type("MOA"), "mechanism_of_action")
        self.assertEqual(nz.normalize_class_type("VA"), "therapeutic")

    def test_relationship_for_tty(self):
        self.assertEqual(nz.relationship_for_tty("IN"), "ingredient_of")
        self.assertEqual(nz.relationship_for_tty("BN"), "brand_of")
        self.assertEqual(nz.relationship_for_tty("SCD"), "clinical_drug")

    def test_parse_historystatus_remap(self):
        payload = {"rxcuiStatusHistory": {
            "metaData": {"status": "Remapped"},
            "derivedConcepts": {"remappedConcept": [{"remappedRxCui": "83367"}]},
        }}
        status, remap = nz.parse_historystatus(payload)
        self.assertEqual(status, "remapped")
        self.assertEqual(remap, "83367")

    def test_parse_allconcepts(self):
        payload = {"minConceptGroup": {"minConcept": [
            {"rxcui": "1191", "name": "aspirin", "tty": "IN"}]}}
        rows = nz.parse_allconcepts(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].rxcui, "1191")
        self.assertEqual(rows[0].tty, "IN")


if __name__ == "__main__":
    unittest.main()
