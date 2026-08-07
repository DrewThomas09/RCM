"""The master NPI file — what it claims, what it refuses to claim.

Two failure modes matter more than the rest.

The first is a file that looks complete because it invented the missing
part. NPPES has no employer field for a person, so an individual NPI has
no parent, and the tests below require that to stay true no matter what
the graph contains — a physician sharing a building with a hospital is
not owned by it.

The second is a file that silently drops rows. Roots, tombstones and
uncategorised providers all belong in a crosswalk: "this is the top of
its tree", "retired in 2019" and "NPPES does not say what this is" are
answers, and omitting them makes the file look tidier than the data.
"""
from __future__ import annotations

import csv
import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from rcm_mc.data.master_provider_file import (
    INDIVIDUAL_NO_PARENT, MASTER_COLUMNS, ROOT_BASIS, build_master_file,
    export_master_file, master_file_coverage,
)
from rcm_mc.data.nppes_ingest import (
    ENTITY_INDIVIDUAL, ENTITY_ORGANIZATION, STATUS_ACTIVE, STATUS_DEACTIVATED,
    ensure_table,
)
from rcm_mc.data.parent_resolution import NS_SYSTEM, ParentGraph, node_key


def _crosswalk() -> pd.DataFrame:
    """Three certified facilities: a system hospital, its rehab unit, and
    a chain dialysis clinic."""
    return pd.DataFrame([
        {"ccn": "010011", "name": "ASCENSION SAINT VINCENTS",
         "street": "810 ST VINCENTS DR", "city": "BIRMINGHAM", "state": "AL",
         "zip": "35205", "provider_class": "hospital",
         "facility_type": "general", "facility_status": "operating",
         "system_id": "ascension", "system_name": "Ascension",
         "system_match": "^ASCENSION", "chain_name": "",
         "taxonomy_code": "282N00000X", "county": "JEFFERSON",
         "county_fips": "01073", "cbsa_code": "13820",
         "cbsa_title": "Birmingham-Hoover, AL", "cbsa_type": "metro",
         "certification_date": "1966-01-01", "parent_ccn": "",
         "parent_ccn_source": "", "npi": "1111111111",
         "npi_source": "name+state+zip"},
        {"ccn": "01T011", "name": "ASCENSION SAINT VINCENTS REHAB",
         "street": "810 ST VINCENTS DR", "city": "BIRMINGHAM", "state": "AL",
         "zip": "35205", "provider_class": "hospital",
         "facility_type": "rehab", "facility_status": "operating",
         "system_id": "ascension", "system_name": "Ascension",
         "system_match": "", "chain_name": "", "taxonomy_code": "283X00000X",
         "county": "JEFFERSON", "county_fips": "01073", "cbsa_code": "13820",
         "cbsa_title": "Birmingham-Hoover, AL", "cbsa_type": "metro",
         "certification_date": "1985-01-01", "parent_ccn": "010011",
         "parent_ccn_source": "parent facility", "npi": "", "npi_source": ""},
        {"ccn": "012501", "name": "DAVITA BIRMINGHAM", "street": "1 MAIN ST",
         "city": "BIRMINGHAM", "state": "AL", "zip": "35205",
         "provider_class": "dialysis", "facility_type": "dialysis",
         "facility_status": "operating", "system_id": "", "system_name": "",
         "system_match": "", "chain_name": "DAVITA",
         "taxonomy_code": "261QE0700X", "county": "JEFFERSON",
         "county_fips": "01073", "cbsa_code": "13820",
         "cbsa_title": "Birmingham-Hoover, AL", "cbsa_type": "metro",
         "certification_date": "2001-01-01", "parent_ccn": "",
         "parent_ccn_source": "", "npi": "2222222222",
         "npi_source": "name+state+zip"},
    ])


def _npi_frame() -> pd.DataFrame:
    return pd.DataFrame([
        # An organization tied to a CCN inside a system.
        {"npi": "1111111111", "entity_type": ENTITY_ORGANIZATION,
         "legal_name": "ASCENSION SAINT VINCENTS", "ccn": "010011",
         "taxonomy_code": "282N00000X", "state": "AL", "city": "BIRMINGHAM",
         "zip": "35205", "status": STATUS_ACTIVE},
        # An organization tied to a chain clinic.
        {"npi": "2222222222", "entity_type": ENTITY_ORGANIZATION,
         "legal_name": "DAVITA BIRMINGHAM", "ccn": "012501",
         "taxonomy_code": "261QE0700X", "state": "AL", "city": "BIRMINGHAM",
         "zip": "35205", "status": STATUS_ACTIVE},
        # A physician practising at the hospital's address. NPPES says
        # nothing about who employs them, and neither may this file.
        {"npi": "3333333333", "entity_type": ENTITY_INDIVIDUAL,
         "legal_name": "JANE DOE", "credential": "M.D.", "ccn": "",
         "taxonomy_code": "207R00000X", "state": "AL", "city": "BIRMINGHAM",
         "zip": "35205", "status": STATUS_ACTIVE},
        # An organization NPPES itself calls a subpart of a named parent.
        {"npi": "4444444444", "entity_type": ENTITY_ORGANIZATION,
         "legal_name": "ASCENSION HOME CARE OF ALABAMA", "ccn": "",
         "parent_org_lbn": "ASCENSION HEALTH", "is_subpart": "Y",
         "taxonomy_code": "251E00000X", "state": "AL", "city": "BIRMINGHAM",
         "zip": "35205", "status": STATUS_ACTIVE},
        # A retired NPI. It still has to resolve, or the file cannot
        # answer a question about a 2019 claim.
        {"npi": "5555555555", "entity_type": ENTITY_ORGANIZATION,
         "legal_name": "CLOSED AMBULANCE CO", "ccn": "",
         "taxonomy_code": "341600000X", "state": "AL", "city": "MOBILE",
         "zip": "36601", "status": STATUS_DEACTIVATED,
         "deactivation_date": "08/12/2019"},
    ])


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = build_master_file(crosswalk=_crosswalk(),
                                       npi_frame=_npi_frame())

    def test_the_file_has_the_declared_columns_in_order(self):
        self.assertEqual(list(self.frame.columns), list(MASTER_COLUMNS))

    def test_one_row_per_npi(self):
        self.assertEqual(len(self.frame), 5)
        self.assertEqual(self.frame["npi"].nunique(), 5)

    def test_an_empty_build_is_an_empty_typed_frame(self):
        empty = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=pd.DataFrame(columns=["npi"]))
        self.assertTrue(empty.empty)
        self.assertEqual(list(empty.columns), list(MASTER_COLUMNS))


class IndividualTests(unittest.TestCase):
    """The refusal this file is built around."""

    def setUp(self) -> None:
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        self.rows = {r["npi"]: r for r in frame.to_dict("records")}

    def test_a_physician_at_a_hospital_address_is_not_owned_by_it(self):
        row = self.rows["3333333333"]
        self.assertEqual(row["entity_label"], "individual")
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["parent_basis"], INDIVIDUAL_NO_PARENT)

    def test_the_reason_is_stated_rather_than_left_blank(self):
        """A blank parent with no explanation reads as a data gap. It is
        not one — it is the absence of a source."""
        row = self.rows["3333333333"]
        self.assertIn("no employer", row["parent_basis"])
        self.assertIn("affiliation", row["parent_basis"])

    def test_an_individual_still_gets_identity_taxonomy_and_geography(self):
        row = self.rows["3333333333"]
        self.assertEqual(row["credential"], "M.D.")
        self.assertEqual(row["taxonomy_category"], "physician")
        self.assertEqual(row["state"], "AL")
        self.assertEqual(row["is_organisation"], 0)


class ParentResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        self.rows = {r["npi"]: r for r in frame.to_dict("records")}

    def test_a_hospital_npi_reaches_its_system_through_its_ccn(self):
        row = self.rows["1111111111"]
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "ascension"))
        self.assertEqual(row["ccn"], "010011")
        self.assertGreaterEqual(row["parent_hops"], 2)
        self.assertIn("ccn:010011", row["parent_basis"])

    def test_a_chain_clinic_npi_reaches_the_system_behind_the_chain(self):
        row = self.rows["2222222222"]
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "davita"))
        self.assertIn("chain:DAVITA", row["parent_basis"])

    def test_nppes_own_subpart_filing_outranks_everything_else(self):
        row = self.rows["4444444444"]
        self.assertEqual(row["is_subpart"], "Y")
        self.assertEqual(row["parent_org_lbn"], "ASCENSION HEALTH")
        # …and the filed parent name is itself lifted to the registry
        # system, so the answer is final rather than one hop short.
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "ascension"))
        self.assertIn("nppes_subpart", row["parent_basis"])

    def test_an_unparented_organization_says_so_instead_of_going_blank(self):
        row = self.rows["5555555555"]
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["parent_basis"], ROOT_BASIS)

    def test_every_parent_carries_a_tier_and_a_confidence(self):
        parented = [r for r in self.rows.values() if r["final_parent"]]
        self.assertGreaterEqual(len(parented), 3)
        for row in parented:
            with self.subTest(npi=row["npi"]):
                self.assertTrue(row["parent_tier"])
                self.assertGreater(float(row["parent_confidence"]), 0.0)
                self.assertLessEqual(float(row["parent_confidence"]), 1.0)


class RetiredNpiTests(unittest.TestCase):
    def test_a_deactivated_npi_is_still_in_the_file(self):
        """A crosswalk that forgets retired identifiers fails on exactly
        the data people bring to it — old claims and old rosters."""
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        row = frame[frame["npi"] == "5555555555"].iloc[0]
        self.assertEqual(row["status"], STATUS_DEACTIVATED)
        self.assertEqual(row["deactivation_date"], "08/12/2019")
        self.assertEqual(row["taxonomy_category"], "ambulance")


class InheritedGeographyTests(unittest.TestCase):
    def test_an_npi_inherits_county_and_cbsa_from_its_certified_facility(self):
        """NPPES gives a practice address but no county and no CBSA. The
        crosswalk already resolved those, including the Connecticut
        planning-region break a naive ZIP join gets wrong."""
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        row = frame[frame["npi"] == "1111111111"].iloc[0]
        self.assertEqual(row["county_fips"], "01073")
        self.assertEqual(row["cbsa_code"], "13820")
        self.assertEqual(row["provider_class"], "hospital")
        self.assertEqual(row["facility_type"], "general")

    def test_an_npi_with_no_ccn_does_not_borrow_a_facility_s_geography(self):
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        row = frame[frame["npi"] == "4444444444"].iloc[0]
        self.assertEqual(row["ccn"], "")
        self.assertEqual(row["county_fips"], "")
        self.assertEqual(row["provider_class"], "")


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_csv_round_trips_the_built_frame(self):
        stats = export_master_file(self.dir / "master.csv",
                                   crosswalk=_crosswalk(),
                                   npi_frame=_npi_frame())
        rows = list(csv.DictReader((self.dir / "master.csv").open()))
        self.assertEqual(len(rows), stats["rows"])
        self.assertEqual(list(rows[0]), list(MASTER_COLUMNS))

    def test_the_export_counts_what_it_wrote(self):
        stats = export_master_file(self.dir / "master.csv",
                                   crosswalk=_crosswalk(),
                                   npi_frame=_npi_frame())
        self.assertEqual(stats["rows"], 5)
        self.assertEqual(stats["organizations"], 4)
        self.assertEqual(stats["individuals"], 1)
        self.assertEqual(stats["with_ccn"], 2)
        self.assertEqual(stats["by_status"][STATUS_DEACTIVATED], 1)
        self.assertEqual(stats["by_category"]["hospital"], 1)

    def test_compression_is_a_flag_not_a_different_writer(self):
        export_master_file(self.dir / "master.csv.gz", compress=True,
                           crosswalk=_crosswalk(), npi_frame=_npi_frame())
        with gzip.open(self.dir / "master.csv.gz", "rt") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 5)
        self.assertEqual(list(rows[0]), list(MASTER_COLUMNS))

    def test_progress_is_reported_so_a_long_run_is_not_a_black_box(self):
        seen = []
        export_master_file(self.dir / "master.csv", crosswalk=_crosswalk(),
                           npi_frame=_npi_frame(),
                           progress=lambda s: seen.append(s["rows"]))
        self.assertTrue(seen)
        self.assertEqual(seen[-1], 5)


class DatabaseSourceTests(unittest.TestCase):
    """The path the national file will actually take: a database written
    by ``ingest_nppes``, streamed rather than materialised."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "npi.db"
        con = sqlite3.connect(str(self.db))
        ensure_table(con)
        con.executemany(
            "INSERT INTO npi_crosswalk (npi, entity_type, legal_name, ccn, "
            "taxonomy_code, taxonomy_category, state, city, zip, status, "
            "is_organisation) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [("1111111111", ENTITY_ORGANIZATION, "ASCENSION SAINT VINCENTS",
              "010011", "282N00000X", "hospital", "AL", "BIRMINGHAM",
              "35205", STATUS_ACTIVE, 1),
             ("3333333333", ENTITY_INDIVIDUAL, "JANE DOE", "", "207R00000X",
              "physician", "AL", "BIRMINGHAM", "35205", STATUS_ACTIVE, 0),
             ("5555555555", ENTITY_ORGANIZATION, "CLOSED AMBULANCE CO", "",
              "341600000X", "ambulance", "AL", "MOBILE", "36601",
              STATUS_DEACTIVATED, 1)])
        con.commit()
        con.close()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_database_is_read_in_chunks_and_nothing_is_lost(self):
        out = Path(self.tmp.name) / "master.csv"
        stats = export_master_file(out, db_path=self.db,
                                   crosswalk=_crosswalk(), chunk_size=1)
        rows = list(csv.DictReader(out.open()))
        self.assertEqual(len(rows), 3)
        self.assertEqual(stats["rows"], 3)
        self.assertEqual({r["npi"] for r in rows},
                         {"1111111111", "3333333333", "5555555555"})

    def test_chunking_does_not_change_the_answer(self):
        one = Path(self.tmp.name) / "one.csv"
        many = Path(self.tmp.name) / "many.csv"
        export_master_file(one, db_path=self.db, crosswalk=_crosswalk(),
                           chunk_size=500)
        export_master_file(many, db_path=self.db, crosswalk=_crosswalk(),
                           chunk_size=1)
        self.assertEqual(one.read_text(), many.read_text())

    def test_the_graph_is_built_from_organizations_only(self):
        """Individuals carry no ownership edge, so excluding them keeps
        the graph to a fraction of the register at no cost."""
        out = Path(self.tmp.name) / "master.csv"
        export_master_file(out, db_path=self.db, crosswalk=_crosswalk())
        rows = {r["npi"]: r for r in csv.DictReader(out.open())}
        self.assertEqual(rows["1111111111"]["final_parent"],
                         node_key(NS_SYSTEM, "ascension"))
        self.assertEqual(rows["3333333333"]["final_parent"], "")

    def test_a_database_without_the_table_is_rejected(self):
        empty = Path(self.tmp.name) / "empty.db"
        sqlite3.connect(str(empty)).close()
        with self.assertRaises(ValueError):
            export_master_file(Path(self.tmp.name) / "x.csv", db_path=empty,
                               crosswalk=_crosswalk())


class CoverageTests(unittest.TestCase):
    def test_coverage_reports_the_mix_rather_than_a_single_percentage(self):
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        cov = master_file_coverage(frame)
        self.assertEqual(cov["npis"], 5)
        self.assertEqual(cov["organizations"], 4)
        self.assertEqual(cov["individuals"], 1)
        self.assertEqual(cov["organizations_with_a_parent"], 3)
        self.assertEqual(cov["linked_to_ccn"], 2)
        self.assertIn("hospital", cov["by_category"])
        self.assertIn(STATUS_DEACTIVATED, cov["by_status"])

    def test_coverage_of_an_empty_file_is_zero_not_an_exception(self):
        self.assertEqual(master_file_coverage(pd.DataFrame())["npis"], 0)

    def test_the_percentage_is_over_organizations_not_over_every_npi(self):
        """Individuals cannot have a parent, so counting them in the
        denominator would make the file look worse every time it got
        more complete."""
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        cov = master_file_coverage(frame)
        self.assertAlmostEqual(cov["organization_parent_pct"], 75.0)


class BundledBuildTests(unittest.TestCase):
    """With no arguments the builder runs on what is actually on disk."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = build_master_file()
        cls.cov = master_file_coverage(cls.frame)

    def test_it_builds_the_ambulance_slice_and_says_that_is_what_it_is(self):
        self.assertGreater(self.cov["npis"], 20_000)
        sources = set(self.frame["source"])
        self.assertTrue(any("ambulance" in s for s in sources), sources)

    def test_more_than_half_the_organizations_reach_a_parent(self):
        self.assertGreater(self.cov["organization_parent_pct"], 50.0)

    def test_nearly_every_row_carries_a_provider_category(self):
        self.assertGreater(self.cov["with_a_category"], self.cov["npis"] * 0.99)

    def test_the_status_vocabulary_is_the_one_the_schema_declares(self):
        """The roster spells status A/D and the ingest spells it
        active/deactivated. A column carrying both cannot be grouped on."""
        self.assertTrue(set(self.cov["by_status"]) <=
                        {STATUS_ACTIVE, STATUS_DEACTIVATED, "reactivated"},
                        self.cov["by_status"])

    def test_the_coverage_report_is_json_serialisable(self):
        # It ends up in CLI output and in a page; a numpy int64 in there
        # is a TypeError at the last possible moment.
        json.loads(json.dumps(self.cov, default=int))


class CliTests(unittest.TestCase):
    """``rcm-mc data master-file`` is how this gets run outside a notebook."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, argv):
        import contextlib
        import io

        from rcm_mc.cli import data_main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = data_main(argv, prog="rcm-mc data")
        return code, buffer.getvalue()

    def test_without_out_it_reports_coverage_and_writes_nothing(self):
        code, out = self._run(["master-file"])
        self.assertEqual(code, 0)
        self.assertIn("Master NPI crosswalk", out)
        self.assertIn("nothing was written", out)

    def test_json_output_is_machine_readable(self):
        code, out = self._run(["master-file", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertGreater(payload["npis"], 20_000)

    def test_out_writes_a_csv_and_reports_its_path(self):
        target = Path(self.tmp.name) / "master.csv"
        code, out = self._run(["master-file", "--out", str(target)])
        self.assertEqual(code, 0)
        self.assertIn(str(target), out)
        with target.open() as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, list(MASTER_COLUMNS))

    def test_the_disagreement_queue_is_written_and_counted(self):
        """CMS publishes change-of-ownership only as state-by-year counts,
        so the closest thing to an acquisition list this data supports is
        the set of facilities whose sources name different owners."""
        target = Path(self.tmp.name) / "disagreements.csv"
        code, out = self._run(["master-file", "--disagreements-out",
                               str(target)])
        self.assertEqual(code, 0)
        self.assertIn("disagreements", out)
        rows = list(csv.DictReader(target.open()))
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(node=row["node"]):
                # Both answers and the evidence for each, or it is not a
                # queue anyone can work.
                self.assertTrue(row["resolved_parent"])
                self.assertTrue(row["rival_parent"])
                self.assertNotEqual(row["resolved_parent"], row["rival_parent"])
                self.assertIn(":", row["evidence"])

    def test_gzip_is_a_flag(self):
        target = Path(self.tmp.name) / "master.csv.gz"
        code, _ = self._run(["master-file", "--out", str(target), "--gzip"])
        self.assertEqual(code, 0)
        with gzip.open(target, "rt") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, list(MASTER_COLUMNS))


if __name__ == "__main__":
    unittest.main()
