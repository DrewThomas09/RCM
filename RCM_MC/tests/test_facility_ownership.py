"""Clustering facilities by operator when their names group with nothing."""

from __future__ import annotations

import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from rcm_mc.data import facility_ownership as own
from rcm_mc.data.facility_ownership import (
    MAX_OFFICIALS_PER_ADDRESS,
    OWNERSHIP_COLUMNS,
    OwnershipRow,
    is_remote_mailing,
    load_ownership,
    ownership_clusters,
    ownership_summary,
    service_addresses,
)

# Check digits from npi_identifier.npi_check_digit.
NPIS = ["1234567893", "1456789019", "1567890128", "1678901236",
        "1789012345", "1890123452", "2345678900"]


def _row(ccn, npi, **over):
    row = {c: "" for c in OWNERSHIP_COLUMNS}
    row.update({
        "ccn": ccn, "npi": npi,
        "legal_name": "SOME OPERATOR LLC",
        "mail_street": "1 SOUTHERN WAY", "mail_city": "MOBILE",
        "mail_state": "AL", "mail_zip": "36619",
        "taxonomy_code": "314000000X",
        "match_basis": "address+taxonomy", "confidence": "high",
    })
    row.update(over)
    return row


class Fixture(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "own.csv.gz"
        own._clear_cache()

    def tearDown(self):
        self._dir.cleanup()
        own._clear_cache()

    def write(self, rows):
        own._clear_cache()
        with gzip.open(self.path, "wt", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(OWNERSHIP_COLUMNS))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return self.path


class LoadTests(Fixture):
    def test_a_missing_file_loads_as_empty(self):
        self.assertEqual(load_ownership(Path(self._dir.name) / "no.csv.gz"), {})

    def test_a_row_loads_and_derives_its_keys(self):
        self.write([_row("015014", NPIS[0], legal_name="BALL HEALTHCARE EASTVIEW INC",
                         official_name="SARA WALLACE")])
        r = load_ownership(self.path)["015014"]
        self.assertIsInstance(r, OwnershipRow)
        self.assertEqual(r.mail_key, "1 SOUTHERN WAY|MOBILE|AL")
        self.assertEqual(r.official_key, "SARA WALLACE")

    def test_a_bad_check_digit_is_dropped(self):
        self.write([_row("015014", "1234567890"), _row("015015", NPIS[0])])
        self.assertEqual(set(load_ownership(self.path)), {"015015"})


class RemoteMailingTests(Fixture):
    """The guard the whole method depends on."""

    def test_mailing_to_a_different_city_is_evidence(self):
        self.write([_row("015014", NPIS[0])])
        row = load_ownership(self.path)["015014"]
        self.assertTrue(is_remote_mailing(row, "BIRMINGHAM", "7755 4TH AVE S"))

    def test_mailing_to_your_own_building_is_not_evidence(self):
        """Independent facilities file their own street. Joining on that
        would union every facility that happens to share an address."""
        self.write([_row("015014", NPIS[0], mail_city="BIRMINGHAM",
                         mail_street="7755 4TH AVE S")])
        row = load_ownership(self.path)["015014"]
        self.assertFalse(is_remote_mailing(row, "BIRMINGHAM", "7755 4TH AVE S"))

    def test_a_different_street_in_the_same_city_is_evidence(self):
        self.write([_row("015014", NPIS[0], mail_city="BIRMINGHAM",
                         mail_street="500 CORPORATE PKWY")])
        row = load_ownership(self.path)["015014"]
        self.assertTrue(is_remote_mailing(row, "BIRMINGHAM", "7755 4TH AVE S"))

    def test_a_blank_mailing_address_is_never_evidence(self):
        """Otherwise every unfiled row fuses into one giant cluster."""
        self.write([_row("015014", NPIS[0], mail_street="", mail_city="",
                         mail_state="")])
        row = load_ownership(self.path)["015014"]
        self.assertFalse(is_remote_mailing(row, "BIRMINGHAM", "1 MAIN ST"))


class ClusterTests(Fixture):
    def test_unrelated_names_at_one_back_office_become_one_cluster(self):
        """The Farmington UT case: six Ohio buildings, six legal names
        that share nothing, one Utah office 1,600 miles away."""
        rows = [
            _row("365001", NPIS[0], legal_name="BARBERTON SNF HEALTHCARE LLC"),
            _row("365002", NPIS[1], legal_name="DAYTON SNF HEALTHCARE LLC"),
            _row("365003", NPIS[2], legal_name="MARION POST ACUTE, LLC"),
        ]
        for r in rows:
            r.update(mail_street="262 N UNIVERSITY AVE", mail_city="FARMINGTON",
                     mail_state="UT")
        self.write(rows)
        fac = {"365001": ("BARBERTON", "1 A ST"), "365002": ("DAYTON", "2 B ST"),
               "365003": ("MARION", "3 C ST")}
        clusters = ownership_clusters(self.path, fac)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].size, 3)
        self.assertEqual(clusters[0].joined_by, "mail")
        self.assertTrue(clusters[0].names_differ)

    def test_one_officer_across_several_addresses_still_clusters(self):
        """Soon Burnam signs eight Texas NPIs under six different
        hospital-district names at different addresses. The person is
        the join, not the building."""
        rows = [
            _row("675001", NPIS[0], legal_name="FANNIN COUNTY HOSPITAL AUTHORITY",
                 mail_street="1 A ST", mail_city="BONHAM", mail_state="TX",
                 official_name="SOON BURNAM"),
            _row("675002", NPIS[1], legal_name="HAMILTON COUNTY HOSPITAL DISTRICT",
                 mail_street="2 B ST", mail_city="HAMILTON", mail_state="TX",
                 official_name="SOON BURNAM"),
        ]
        self.write(rows)
        clusters = ownership_clusters(self.path, {})
        self.assertEqual([c.joined_by for c in clusters], ["official"])

    def test_a_declared_parent_clusters_without_inference(self):
        rows = [_row("365010", NPIS[0], legal_name="LONDON HEALTH LLC",
                     parent_org="SABER HEALTHCARE HOLDINGS, LLC"),
                _row("365011", NPIS[1], legal_name="UNIVERSITY MANOR INC",
                     parent_org="SABER HEALTHCARE HOLDINGS LLC")]
        self.write(rows)
        kinds = {c.joined_by for c in ownership_clusters(self.path, {})}
        self.assertIn("parent", kinds)

    def test_one_legal_entity_across_unrelated_towns_clusters(self):
        """The Texas QIPP case. These facilities mail to themselves, so
        the address key never fires — but four buildings in four towns
        file under one hospital district, which is one legal person."""
        rows = [_row("675101", NPIS[0], legal_name="FANNIN COUNTY HOSPITAL AUTHORITY",
                     mail_street="1 A ST", mail_city="WACO", mail_state="TX"),
                _row("675102", NPIS[1], legal_name="FANNIN COUNTY HOSPITAL AUTHORITY",
                     mail_street="2 B ST", mail_city="PARIS", mail_state="TX"),
                _row("675103", NPIS[2], legal_name="FANNIN COUNTY HOSPITAL AUTHORITY",
                     mail_street="3 C ST", mail_city="DENISON", mail_state="TX")]
        self.write(rows)
        fac = {"675101": ("WACO", "1 A ST"), "675102": ("PARIS", "2 B ST"),
               "675103": ("DENISON", "3 C ST")}
        clusters = ownership_clusters(self.path, fac)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].size, 3)
        self.assertEqual(clusters[0].joined_by, "legal")
        # Same entity, so the legal names agree; the CMS names do not,
        # which is why nothing name-based finds this.
        self.assertFalse(clusters[0].names_differ)

    def test_a_lone_facility_is_not_a_cluster(self):
        self.write([_row("015014", NPIS[0], legal_name="", official_name="ONLY ONE")])
        self.assertEqual(ownership_clusters(self.path, {}), [])

    def test_without_facility_addresses_mail_joins_are_withheld(self):
        """Under-claiming beats over-claiming: with nothing to compare
        against, a mailing address cannot be shown to be remote."""
        rows = [_row("365001", NPIS[0], legal_name="A LLC"),
                _row("365002", NPIS[1], legal_name="B LLC")]
        self.write(rows)
        self.assertEqual(ownership_clusters(self.path, {}), [])


class ServiceAddressTests(Fixture):
    def test_a_registered_agent_address_is_refused(self):
        """A law firm receives mail for hundreds of unrelated companies.
        Joining on it would fuse a whole state into one fiction."""
        rows = []
        for i in range(MAX_OFFICIALS_PER_ADDRESS + 2):
            rows.append(_row(f"36500{i}", NPIS[i % len(NPIS)][:9] + str(i % 10),
                             legal_name=f"UNRELATED COMPANY {i} LLC",
                             official_name=f"LAWYER NUMBER {i}",
                             mail_street="1 REGISTERED AGENT PLZ",
                             mail_city="DOVER", mail_state="DE"))
        # Fix check digits by reusing valid NPIs; duplicates are dropped
        # by CCN anyway, so give each row a distinct valid NPI.
        for i, r in enumerate(rows):
            r["npi"] = NPIS[i % len(NPIS)]
        self.write(rows)
        flagged = service_addresses(self.path)
        self.assertIn("1 REGISTERED AGENT PLZ|DOVER|DE", flagged)

    def test_a_real_back_office_is_not_refused(self):
        # Nineteen legal names and one Sandy Muir is a chain, not an
        # agent. Counting names here refused exactly the right answer.
        rows = [_row(f"36501{i}", NPIS[i], legal_name=f"OPERATOR {i} LLC",
                     official_name="SANDY MUIR",
                     mail_street="262 N UNIVERSITY AVE", mail_city="FARMINGTON",
                     mail_state="UT") for i in range(7)]
        self.write(rows)
        self.assertEqual(service_addresses(self.path), {})


class SummaryTests(Fixture):
    def test_the_summary_reports_what_names_could_not_have_found(self):
        rows = [_row("365001", NPIS[0], legal_name="BARBERTON SNF HEALTHCARE LLC"),
                _row("365002", NPIS[1], legal_name="DAYTON SNF HEALTHCARE LLC")]
        for r in rows:
            r.update(mail_street="262 N UNIVERSITY AVE", mail_city="FARMINGTON",
                     mail_state="UT")
        self.write(rows)
        fac = {"365001": ("BARBERTON", "1 A ST"), "365002": ("DAYTON", "2 B ST")}
        s = ownership_summary(self.path, fac)
        self.assertEqual(s["facilities_harvested"], 2)
        self.assertEqual(s["clusters"], 1)
        self.assertEqual(s["clusters_whose_legal_names_differ"], 1)
        self.assertEqual(s["facilities_no_name_could_group"], 2)


class ShippedTests(unittest.TestCase):
    """Whatever ships has to satisfy the module's own invariants."""

    def setUp(self):
        own._clear_cache()

    def test_every_shipped_ccn_is_state_coded(self):
        for ccn in load_ownership():
            self.assertTrue(ccn[:2].isdigit(), ccn)

    def test_no_shipped_cluster_rests_on_a_service_address(self):
        flagged = set(service_addresses())
        for cluster in ownership_clusters():
            if cluster.joined_by == "mail":
                self.assertNotIn(cluster.key, flagged, cluster.key)


if __name__ == "__main__":
    unittest.main()
