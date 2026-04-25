"""Tests for the weekly incremental NPPES + Type-1 ↔ Type-2
affiliation linking."""
from __future__ import annotations

import os
import tempfile
import unittest


def _record(npi, entity_type=2, last_updated="2026-01-01",
            org_name="Org", last_name=""):
    from rcm_mc.pricing.nppes import NppesRecord
    return NppesRecord(
        npi=npi, entity_type=entity_type,
        organization_name=org_name,
        last_name=last_name,
        first_name="",
        taxonomy_code="282N00000X",
        taxonomy_label="Y",
        address_line="123 Main St",
        city="DALLAS", state="TX",
        zip5="75201", cbsa="19100",
        nppes_last_updated=last_updated,
    )


class TestIncrementalLoad(unittest.TestCase):
    def setUp(self):
        from rcm_mc.pricing import PricingStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PricingStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_initial_insert(self):
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
        )
        report = incremental_nppes_load(
            self.store,
            records=[
                _record("1003456789", 2, "2026-01-15",
                        "Hospital A"),
                _record("1003456790", 1, "2026-01-15",
                        last_name="Smith"),
            ],
        )
        self.assertEqual(report.rows_inserted, 2)
        self.assertEqual(report.rows_updated, 0)

    def test_skip_when_no_newer_update(self):
        """Re-running with identical timestamp → skipped."""
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
        )
        incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-01-15")])
        # Same timestamp → no update
        report = incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-01-15")])
        self.assertEqual(report.rows_skipped, 1)
        self.assertEqual(report.rows_updated, 0)

    def test_update_when_newer_timestamp(self):
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
        )
        incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-01-15",
                             "Old Name")])
        # Newer timestamp + new name → update
        report = incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-04-01",
                             "New Name")])
        self.assertEqual(report.rows_updated, 1)
        # Verify the org name was updated
        with self.store.connect() as con:
            row = con.execute(
                "SELECT organization_name FROM pricing_nppes "
                "WHERE npi = '1003456789'").fetchone()
        self.assertEqual(
            row["organization_name"], "New Name")

    def test_no_update_when_older_timestamp(self):
        """If a delta file ships an OLDER timestamp than what we
        have, we shouldn't downgrade."""
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
        )
        incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-04-01",
                             "Current")])
        # Older timestamp ships → skip
        report = incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2025-01-01",
                             "Stale")])
        self.assertEqual(report.rows_skipped, 1)
        self.assertEqual(report.rows_updated, 0)

    def test_deactivations_marked(self):
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
        )
        incremental_nppes_load(
            self.store,
            records=[_record("1003456789", 2, "2026-01-15")])
        report = incremental_nppes_load(
            self.store, records=[],
            deactivations=[
                ("1003456789", "2026-04-15"),
            ],
        )
        self.assertEqual(report.rows_deactivated, 1)
        # Deactivation_date populated on the row
        with self.store.connect() as con:
            row = con.execute(
                "SELECT deactivation_date FROM pricing_nppes "
                "WHERE npi = '1003456789'").fetchone()
        self.assertEqual(
            row["deactivation_date"], "2026-04-15")


class TestAffiliations(unittest.TestCase):
    def setUp(self):
        from rcm_mc.pricing import PricingStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PricingStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_affiliation_individual_to_org(self):
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
            list_individuals_at_organization,
            list_organizations_for_individual,
        )
        # Two individuals + one organization
        incremental_nppes_load(
            self.store,
            records=[
                _record("1003456789", 2, "2026-01-15",
                        "Big Hospital"),
                _record("1234567890", 1, "2026-01-15",
                        last_name="Smith"),
                _record("0987654321", 1, "2026-01-15",
                        last_name="Jones"),
            ],
            affiliations=[
                ("1234567890", "1003456789", "billing"),
                ("0987654321", "1003456789", "billing"),
            ],
        )
        # Org → 2 individuals
        org_individuals = list_individuals_at_organization(
            self.store, "1003456789")
        self.assertEqual(len(org_individuals), 2)
        # Smith → 1 organization
        smith_orgs = list_organizations_for_individual(
            self.store, "1234567890")
        self.assertEqual(len(smith_orgs), 1)
        self.assertEqual(
            smith_orgs[0]["organization_npi"], "1003456789")

    def test_affiliation_idempotent(self):
        """Re-recording the same affiliation upserts cleanly."""
        from rcm_mc.pricing.nppes_incremental import (
            incremental_nppes_load,
            list_affiliations_for_npi,
        )
        incremental_nppes_load(
            self.store, records=[],
            affiliations=[
                ("1234567890", "1003456789", "billing"),
                ("1234567890", "1003456789", "billing"),
            ],
        )
        rows = list_affiliations_for_npi(
            self.store, "1234567890")
        # Composite PK collapses duplicates
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
