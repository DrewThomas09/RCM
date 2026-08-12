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


class AffiliatedIndividualTests(unittest.TestCase):
    """The one route by which a person gets a parent — and its fence."""

    def _affiliations(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"individual_npi": "3333333333",
             "organization_npi": "1111111111",
             "method": "shared_address+name", "confidence": 0.85,
             "evidence": "co-located @ 810 ST VINCENTS DR|35205"},
        ])

    def _rows(self, affiliations=None):
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame(),
                                  affiliations=affiliations)
        return {r["npi"]: r for r in frame.to_dict("records")}

    def test_a_physician_reaches_a_system_when_a_bridge_names_the_link(self):
        row = self._rows(self._affiliations())["3333333333"]
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "ascension"))
        self.assertIn("affiliation", row["parent_basis"])
        self.assertEqual(row["entity_label"], "individual")

    def test_without_a_bridge_the_same_physician_has_no_parent(self):
        """Nothing about the person changed. The difference is whether a
        source exists, and the file says which."""
        row = self._rows()["3333333333"]
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["parent_basis"], INDIVIDUAL_NO_PARENT)

    def test_co_location_alone_still_buys_nothing(self):
        weak = pd.DataFrame([{
            "individual_npi": "3333333333", "organization_npi": "1111111111",
            "method": "shared_practice_address", "confidence": 0.45,
            "evidence": "co-located; 3 org(s) at address"}])
        row = self._rows(weak)["3333333333"]
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["parent_basis"], INDIVIDUAL_NO_PARENT)

    def test_coverage_counts_affiliated_individuals_separately(self):
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame(),
                                  affiliations=self._affiliations())
        cov = master_file_coverage(frame)
        # The organization percentage must not move: individuals are not
        # in that denominator and adding one to the numerator would make
        # the file look better for the wrong reason.
        self.assertAlmostEqual(cov["organization_parent_pct"], 75.0)
        self.assertEqual(cov["individuals_with_a_parent"], 1)


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


class MasterGraphTests(unittest.TestCase):
    """The disagreement queue has to see both sides of the crosswalk."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.master_provider_file import master_graph
        from rcm_mc.data.parent_resolution import crosswalk_graph

        cls.wide = master_graph().stats()
        cls.narrow = crosswalk_graph().stats()

    def test_the_wide_graph_carries_the_npi_tiers_too(self):
        """A PECOS group disagreeing with a name match is the same kind
        of finding as a chain disagreeing with a system, and it is
        invisible if the NPI sources are left out of the graph."""
        wide_tiers = set(self.wide["claims_by_tier"])
        narrow_tiers = set(self.narrow["claims_by_tier"])
        self.assertIn("pecos_group", wide_tiers)
        self.assertNotIn("pecos_group", narrow_tiers)
        self.assertTrue(narrow_tiers <= wide_tiers)

    def test_widening_adds_identifiers_rather_than_replacing_them(self):
        self.assertGreater(self.wide["nodes"], self.narrow["nodes"])
        self.assertGreaterEqual(self.wide["claims"], self.narrow["claims"])

    def test_the_wide_graph_is_still_acyclic(self):
        self.assertEqual(self.wide["cycles"], 0)
        self.assertEqual(self.wide["truncated"], 0)

    def test_no_pecos_group_is_split_across_two_systems(self):
        """A group whose members name different systems is left as its
        own root by the unanimity rule, which would hide a real conflict.
        There are none in this data — pinned so a future one surfaces
        rather than being silently absorbed."""
        from rcm_mc.data.master_provider_file import master_graph
        from rcm_mc.data.parent_resolution import NS_PECOS, TIER_NAME_SYSTEM

        graph = master_graph()
        split = []
        for node in graph.nodes:
            if not node.startswith(f"{NS_PECOS}:"):
                continue
            systems = {c.parent for child in graph.children_of(node)
                       for c in graph.claims_for(child)
                       if c.tier == TIER_NAME_SYSTEM}
            if len(systems) > 1:
                split.append((node, sorted(systems)))
        self.assertEqual(split, [])


class RouteTests(unittest.TestCase):
    """Served over real HTTP, on a live server, like every other export."""

    @classmethod
    def setUpClass(cls) -> None:
        import os
        import socket
        import threading
        import time
        from contextlib import closing

        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as sock:
            sock.bind(("127.0.0.1", 0))
            cls._port = sock.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "m.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._thread.join(timeout=5)
        cls._tmp.cleanup()

    def _rows(self, route: str):
        import io
        import urllib.request

        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{self._port}{route}", timeout=180)
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))

    def test_the_route_serves_the_whole_file(self) -> None:
        rows = self._rows("/master-npi-file.csv")
        self.assertGreater(len(rows), 20_000)
        self.assertEqual(list(rows[0]), list(MASTER_COLUMNS))

    def test_filters_narrow_without_changing_the_shape(self) -> None:
        rows = self._rows("/master-npi-file.csv?state=TX")
        self.assertTrue(rows)
        self.assertEqual({r["state"] for r in rows}, {"TX"})
        self.assertEqual(list(rows[0]), list(MASTER_COLUMNS))

    def test_category_filter_uses_the_taxonomy_vocabulary(self) -> None:
        rows = self._rows("/master-npi-file.csv?category=ambulance")
        self.assertGreater(len(rows), 10_000)
        self.assertEqual({r["taxonomy_category"] for r in rows}, {"ambulance"})

    def test_parented_is_opt_in_because_omission_flatters(self) -> None:
        """A crosswalk that silently drops the unresolved looks far more
        complete than it is."""
        everything = self._rows("/master-npi-file.csv?state=TX")
        parented = self._rows("/master-npi-file.csv?state=TX&parented=1")
        self.assertLess(len(parented), len(everything))
        self.assertTrue(all(r["final_parent"] for r in parented))
        self.assertTrue(any(not r["final_parent"] for r in everything))

    def test_the_parent_name_filter_takes_the_name_not_the_key(self) -> None:
        """Nobody holding a CIM knows ``pecos:2264404516``. They know
        "Acadian", which until now matched nothing on this route."""
        rows = self._rows("/master-npi-file.csv?parent_name=ACADIAN")
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("ACADIAN", row["final_parent_label"].upper())

    def test_the_parent_name_filter_is_a_substring_not_an_equality(self) -> None:
        """Filed names carry suffixes — "ACADIAN AMBULANCE SERVICE INC" —
        that nobody types."""
        rows = self._rows("/master-npi-file.csv?parent_name=acadian%20ambulance")
        self.assertTrue(rows)
        self.assertNotIn("acadian ambulance",
                         {r["final_parent_label"] for r in rows})

    def test_a_regex_in_the_parent_name_matches_nothing_rather_than_raising(
            self) -> None:
        """The value goes into a pandas string match. Treated as a
        pattern, ``(`` is an unbalanced-parenthesis error and a 500."""
        self.assertEqual(self._rows("/master-npi-file.csv?parent_name=(("), [])

    def test_a_filtered_request_does_not_corrupt_the_next_one(self) -> None:
        """The frame is cached across requests; a handler filtering it in
        place would shrink it for everyone after."""
        first = len(self._rows("/master-npi-file.csv"))
        self._rows("/master-npi-file.csv?state=TX")
        self.assertEqual(len(self._rows("/master-npi-file.csv")), first)


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


def _pecos_frame() -> pd.DataFrame:
    """One PECOS enrolment holding five ambulance NPIs under one brand,
    plus a second holding five that agree on nothing."""
    rows = []
    for n in range(1, 6):
        rows.append({"npi": f"10000000{n:02d}", "entity_type": ENTITY_ORGANIZATION,
                     "legal_name": "METRO AMBULANCE SERVICES INC", "ccn": "",
                     "pecos_group": "555", "taxonomy_code": "341600000X",
                     "state": "AL", "city": "MOBILE", "zip": "36601",
                     "status": STATUS_ACTIVE})
    for n in range(1, 6):
        rows.append({"npi": f"20000000{n:02d}", "entity_type": ENTITY_ORGANIZATION,
                     "legal_name": f"COUNTY {n} EMERGENCY SERVICE INC",
                     "ccn": "", "pecos_group": "666",
                     "taxonomy_code": "341600000X", "state": "TX",
                     "city": "AUSTIN", "zip": "78701", "status": STATUS_ACTIVE})
    return pd.DataFrame(rows)


class ParentLabelTests(unittest.TestCase):
    """A final parent nobody can read is a final parent nobody can use.
    Nine in ten resolved rows in the bundled build land on a cluster
    identifier — ``pecos:2264404516`` — which answers "which cluster" and
    not "who owns this"."""

    def setUp(self) -> None:
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        self.rows = {r["npi"]: r for r in frame.to_dict("records")}
        pecos = build_master_file(crosswalk=pd.DataFrame(),
                                  npi_frame=_pecos_frame())
        self.pecos = {r["npi"]: r for r in pecos.to_dict("records")}

    def test_the_columns_sit_beside_the_identifier_they_explain(self):
        self.assertEqual(
            MASTER_COLUMNS[MASTER_COLUMNS.index("final_parent_id") + 1],
            "final_parent_label")

    def test_a_registry_system_keeps_its_registered_name(self):
        """Not a plurality of its members — the registry name is a fact
        and would only be degraded by an inference over it."""
        row = self.rows["1111111111"]
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "ascension"))
        self.assertEqual(row["final_parent_label"], "Ascension")
        self.assertEqual(row["final_parent_label_support"], 1.0)

    def test_a_pecos_cluster_is_named_by_the_members_inside_it(self):
        row = self.pecos["1000000001"]
        self.assertEqual(row["final_parent_type"], "pecos")
        self.assertEqual(row["final_parent_label"],
                         "METRO AMBULANCE SERVICES INC")
        self.assertEqual(row["final_parent_label_support"], 1.0)

    def test_a_cluster_that_agrees_on_nothing_stays_unnamed(self):
        """Five NPIs filing five different names share an enrolment, not a
        brand. Labelling that cluster after any one of them would invent
        an owner, so the row keeps the identifier and no name."""
        row = self.pecos["2000000001"]
        self.assertEqual(row["final_parent_type"], "pecos")
        self.assertEqual(row["final_parent_label"], "")
        self.assertEqual(row["final_parent_label_support"], "")

    def test_a_row_with_no_parent_has_no_label_either(self):
        row = self.rows["5555555555"]
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["final_parent_label"], "")
        self.assertEqual(row["final_parent_label_support"], "")

    def test_the_label_survives_the_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "master.csv"
            export_master_file(path, crosswalk=_crosswalk(),
                               npi_frame=_npi_frame())
            with path.open(newline="", encoding="utf-8") as handle:
                rows = {r["npi"]: r for r in csv.DictReader(handle)}
        self.assertEqual(rows["1111111111"]["final_parent_label"], "Ascension")


class RealParentLabelTests(unittest.TestCase):
    """Against the bundled build, where the gap was measured."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = build_master_file()
        cls.resolved = cls.frame[cls.frame["final_parent"] != ""]

    def test_nearly_every_resolved_row_can_name_its_parent(self):
        named = (self.resolved["final_parent_label"].astype(str) != "").sum()
        self.assertGreater(named / len(self.resolved), 0.99)

    def test_a_named_parent_always_carries_its_support(self):
        named = self.resolved[
            self.resolved["final_parent_label"].astype(str) != ""]
        support = pd.to_numeric(named["final_parent_label_support"],
                                errors="coerce")
        self.assertFalse(support.isna().any())
        self.assertTrue((support > 0).all())
        self.assertTrue((support <= 1.0).all())

    def test_an_unnamed_row_is_unnamed_because_the_data_disagrees(self):
        """The abstentions are not gaps in coverage — they are clusters
        whose members file too many different names to pick one. Pinned
        so a regression that starts naming them is visible."""
        blank = self.resolved[
            self.resolved["final_parent_label"].astype(str) == ""]
        self.assertLess(len(blank), len(self.resolved) * 0.01)
        self.assertEqual(set(blank["final_parent_type"]) - {"official"}, set())


class RollupHonestyTests(unittest.TestCase):
    """"Resolved" and "rolled up" are different claims, and the file was
    only reporting the first."""

    def test_a_singleton_parent_is_not_a_rollup(self):
        """A PECOS enrolment with one member resolves that NPI correctly
        and aggregates nothing. Counting it as coverage is how 11,477
        came to stand for a roll-up that is really 1,562."""
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_pecos_frame())
        cov = master_file_coverage(frame)
        self.assertEqual(cov["npis_sharing_a_parent"]
                         + cov["npis_alone_under_a_parent"],
                         cov["organizations_with_a_parent"])
        self.assertGreater(cov["parents_holding_more_than_one_npi"], 0)

    def test_the_two_numbers_are_reported_side_by_side(self):
        frame = build_master_file(crosswalk=_crosswalk(),
                                  npi_frame=_npi_frame())
        cov = master_file_coverage(frame)
        for key in ("organizations_with_a_parent", "npis_sharing_a_parent",
                    "npis_alone_under_a_parent",
                    "parents_holding_more_than_one_npi"):
            self.assertIn(key, cov)

    def test_an_empty_frame_reports_zeros_not_an_exception(self):
        cov = master_file_coverage(pd.DataFrame(columns=list(MASTER_COLUMNS)))
        self.assertEqual(cov, {"npis": 0})


class RealRollupTests(unittest.TestCase):
    """Against the bundled build."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cov = master_file_coverage(build_master_file())

    def test_most_resolved_npis_are_alone_under_their_parent(self):
        """The finding this reporting exists for, and it survives.

        Most resolved NPIs still sit under a node minted for them alone
        — a PECOS enrolment with one member, an EIN nobody else shares.
        Correct resolutions that aggregate nothing, and the reason a
        raw "resolved" count overstates how much this file rolls up.

        The margin has narrowed on purpose. It was 9,915 alone against
        1,562 sharing, better than six to one, when the only NPIs here
        came from an ambulance roster. ccn_npi_bridge added thousands
        of hospital NPIs that arrive already tied to a CCN and a health
        system, and hospitals genuinely do share parents, so the ratio
        is now about three to one. A *falling* ratio is the file
        aggregating more, not less — which is why this asserts a
        majority rather than the old multiple. If it ever inverts, that
        is worth knowing too, and the assertion will say so.
        """
        alone = self.cov["npis_alone_under_a_parent"]
        sharing = self.cov["npis_sharing_a_parent"]
        self.assertGreater(alone, sharing)
        self.assertGreater(sharing, 3_000,
                           "the bridge should be aggregating hospitals")

    def test_the_rollup_number_is_the_smaller_one(self):
        self.assertLess(self.cov["npis_sharing_a_parent"],
                        self.cov["organizations_with_a_parent"])
        self.assertGreater(self.cov["npis_sharing_a_parent"], 1_000)

    def test_the_parts_reconcile_to_the_whole(self):
        self.assertEqual(
            self.cov["npis_sharing_a_parent"]
            + self.cov["npis_alone_under_a_parent"],
            self.cov["organizations_with_a_parent"])
