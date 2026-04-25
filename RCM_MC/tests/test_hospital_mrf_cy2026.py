"""Tests for the CY2026 Hospital MRF schema additions:
percentile allowed amounts + Type-2 billing NPI."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


def _cy2026_fixture():
    import rcm_mc.pricing as _pkg
    return (Path(_pkg.__file__).parent
            / "fixtures" / "sample_hospital_mrf_cy2026.json")


def _v2_fixture():
    import rcm_mc.pricing as _pkg
    return (Path(_pkg.__file__).parent
            / "fixtures" / "sample_hospital_mrf.json")


class TestParserCY2026(unittest.TestCase):
    def test_percentile_flat_keys(self):
        """First record uses flat percentile_*_charge keys."""
        from rcm_mc.pricing.hospital_mrf import (
            parse_hospital_mrf,
        )
        records = list(parse_hospital_mrf(_cy2026_fixture()))
        knee = [r for r in records if r.code == "27447"]
        self.assertGreater(len(knee), 0)
        first = knee[0]
        self.assertEqual(first.percentile_25, 24500)
        self.assertEqual(first.percentile_50, 28000)
        self.assertEqual(first.percentile_75, 38000)

    def test_percentile_nested_block(self):
        """Second record uses the nested
        ``percentile_allowed_amounts`` block."""
        from rcm_mc.pricing.hospital_mrf import (
            parse_hospital_mrf,
        )
        records = list(parse_hospital_mrf(_cy2026_fixture()))
        mri = [r for r in records if r.code == "70551"]
        self.assertGreater(len(mri), 0)
        first = mri[0]
        self.assertEqual(first.percentile_25, 1100)
        self.assertEqual(first.percentile_50, 1180)
        self.assertEqual(first.percentile_75, 1820)

    def test_billing_npi_type_2(self):
        from rcm_mc.pricing.hospital_mrf import (
            parse_hospital_mrf,
        )
        records = list(parse_hospital_mrf(_cy2026_fixture()))
        for r in records:
            self.assertEqual(
                r.billing_npi_type_2, "1003456789")

    def test_v2_legacy_no_percentiles(self):
        """The v2.0 fixture (no percentile fields) should still
        load — percentile fields just come back None."""
        from rcm_mc.pricing.hospital_mrf import (
            parse_hospital_mrf,
        )
        records = list(parse_hospital_mrf(_v2_fixture()))
        for r in records:
            self.assertIsNone(r.percentile_25)
            self.assertIsNone(r.percentile_50)
            self.assertIsNone(r.percentile_75)
        # billing_npi_type_2 falls back to billing_npi
        self.assertTrue(records[0].billing_npi_type_2)


class TestStorePersistsCY2026(unittest.TestCase):
    def test_round_trip_cy2026_fields(self):
        from rcm_mc.pricing import (
            PricingStore, parse_hospital_mrf, load_hospital_mrf,
            list_charges_by_code,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            records = list(parse_hospital_mrf(_cy2026_fixture()))
            n = load_hospital_mrf(store, records)
            self.assertGreater(n, 0)

            knee_rows = list_charges_by_code(store, "27447")
            self.assertGreater(len(knee_rows), 0)
            row = knee_rows[0]
            self.assertEqual(row["percentile_25"], 24500)
            self.assertEqual(row["percentile_50"], 28000)
            self.assertEqual(row["percentile_75"], 38000)
            self.assertEqual(
                row["billing_npi_type_2"], "1003456789")
        finally:
            tmp.cleanup()

    def test_legacy_v2_load_fields_null(self):
        """Legacy v2.0 fixtures persist with NULL percentile
        columns — partner can detect coverage gaps."""
        from rcm_mc.pricing import (
            PricingStore, parse_hospital_mrf, load_hospital_mrf,
            list_charges_by_code,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            records = list(parse_hospital_mrf(_v2_fixture()))
            load_hospital_mrf(store, records)
            knee_rows = list_charges_by_code(store, "27447")
            self.assertGreater(len(knee_rows), 0)
            for row in knee_rows:
                self.assertIsNone(row["percentile_25"])
                self.assertIsNone(row["percentile_50"])
                self.assertIsNone(row["percentile_75"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
