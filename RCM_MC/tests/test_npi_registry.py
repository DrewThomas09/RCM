"""Organization NPIs from the bundled NPPES cache.

This is a 20,401-NPI ambulance slice, not NPPES. Every assertion here is
scoped to that slice on purpose — the point is to exercise the d/b/a
match, the PECOS grouping and the precision guards on real NPPES records
while the full 9GB dissemination file is out of reach.
"""
from __future__ import annotations

import csv
import io
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing

from rcm_mc.data.health_systems import EMS_REGISTRY, UNMAPPED_ID, get_system
from rcm_mc.data.npi_registry import (
    NPI_COLUMNS,
    _split_dbas,
    assign_npi_registry,
    load_npi_registry,
    npi_registry_coverage,
    pecos_groups,
)
from rcm_mc.data.nppes_ingest import match_organization


class RegistryShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_npi_registry()
        cls.frame = assign_npi_registry()

    def test_the_three_extracts_merge_on_npi(self) -> None:
        self.assertGreater(len(self.records), 20000)
        self.assertEqual(len(self.frame), len(self.records))
        self.assertEqual(len(self.frame), self.frame["npi"].nunique())
        self.assertEqual(list(self.frame.columns), list(NPI_COLUMNS))

    def test_every_npi_is_ten_digits(self) -> None:
        npis = self.frame["npi"]
        self.assertTrue(npis.str.fullmatch(r"\d{10}").all())

    def test_the_pecos_group_comes_from_the_pecos_file(self) -> None:
        """``PECOS_ASCT_CNTL_ID`` is CMS's own grouping of NPIs under one
        enrolled organization — the only ownership signal in this data we
        do not have to infer."""
        grouped = self.frame[self.frame["pecos_group"].ne("")]
        self.assertGreater(len(grouped), 10000)
        self.assertLess(len(grouped), len(self.frame))

    def test_multi_valued_dbas_are_split(self) -> None:
        """NPPES packs several d/b/a names into one semicolon-delimited
        field, and either may be the one carrying the brand."""
        self.assertEqual(_split_dbas("LYNCH AMBULANCE;LYNCH EMS"),
                         ("LYNCH AMBULANCE", "LYNCH EMS"))
        self.assertEqual(_split_dbas("<UNAVAIL>"), ())
        self.assertEqual(_split_dbas("", None), ())
        self.assertEqual(_split_dbas("A;B", "B;C"), ("A", "B", "C"))
        self.assertGreater(int((self.frame["dba_count"] > 1).sum()), 100)


class GeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = assign_npi_registry()

    def test_a_zip_is_the_only_geography_these_records_carry(self) -> None:
        """NPPES gives a practice ZIP and no county. The ZIP mapping
        learned from the certified universe is what turns that into a
        county and then an MSA."""
        resolved = self.frame[self.frame["county_fips"].ne("")]
        self.assertGreater(len(resolved) / len(self.frame), 0.55)
        self.assertTrue(resolved["county_fips"].str.fullmatch(r"\d{5}").all())

    def test_a_cbsa_never_appears_without_a_county(self) -> None:
        orphan = self.frame["cbsa_code"].ne("") & self.frame["county_fips"].eq("")
        self.assertEqual(int(orphan.sum()), 0)


class PrecisionTests(unittest.TestCase):
    """The guards that stop a hospital pattern from eating an EMS roster."""

    def test_a_civil_body_is_not_a_subsidiary(self) -> None:
        """Jefferson Township, Aurora IL and Grady County are place
        names that collide with health-system brands. There is no
        reading in which a fire district belongs to a health system
        because it shares a town name."""
        for name, state in (
            ("JEFFERSON TOWNSHIP VOLUNTEER AMBULANCE", "PA"),
            ("AURORA TOWNSHIP FIRE PROTECTION DISTRICT", "IL"),
            ("GRADY COUNTY BOARD OF COMMISSIONERS", "GA"),
            ("HACKENSACK VOLUNTEER AMBULANCE CORPS, INC.", "NJ"),
            ("STONY BROOK VOLUNTEER AMBULANCE CORPS INC", "NY"),
        ):
            self.assertEqual(match_organization(name, "", state), ("", ""), name)

    def test_a_match_outside_the_footprint_is_rejected(self) -> None:
        """Eight independent ambulance companies are called MedStar, in
        eight states MedStar Health has never operated."""
        for state in ("TX", "IL", "MA", "AL", "MI", "PR"):
            self.assertEqual(
                match_organization("MEDSTAR AMBULANCE INC", "", state),
                ("", ""), state)
        # The guard is a footprint check, not a blanket veto on the brand.
        self.assertEqual(
            match_organization("MEDSTAR HEALTH INC", "", "MD",
                               require_footprint=False)[0], "medstar")

    def test_the_footprint_guard_does_not_demand_a_ccn(self) -> None:
        """An ambulance operator holds NPIs and no CCNs, so it has no
        footprint to check. Absence of evidence is not a veto."""
        system_id, basis = match_organization("AIR EVAC EMS INC", "", "MS")
        self.assertEqual(system_id, "global_medical_response")
        self.assertTrue(basis.startswith("legal name:"))

    def test_the_dba_is_tried_when_the_legal_name_is_a_holding_company(self) -> None:
        system_id, basis = match_organization(
            "SOME HOLDING COMPANY LLC", "AIR METHODS CORPORATION", "CO")
        self.assertEqual(system_id, "air_methods")
        self.assertTrue(basis.startswith("dba:"))


class EmsOperatorTests(unittest.TestCase):
    """Operators that hold NPIs and no CCNs at all."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = assign_npi_registry()

    def test_the_national_consolidators_land(self) -> None:
        """Global Medical Response runs AMR on the ground and Air Evac,
        Med-Trans, Guardian Flight, REACH and EagleMed in the air. None
        of those names says so."""
        counts = self.frame.groupby("system_id").size()
        self.assertGreater(int(counts.get("global_medical_response", 0)), 500)
        self.assertGreater(int(counts.get("air_methods", 0)), 200)
        self.assertGreater(int(counts.get("phi_health", 0)), 10)

    def test_ems_operators_hold_no_ccns(self) -> None:
        """If one of these ever appeared in a facility file, the entry
        would need re-examining — the whole point is that they are
        invisible to CCN-keyed data."""
        from rcm_mc.data.health_systems import assign_all

        ems_ids = {s.system_id for s in EMS_REGISTRY}
        universe = assign_all()
        self.assertEqual(int(universe["system_id"].isin(ems_ids).sum()), 0)
        for sysdef in EMS_REGISTRY:
            self.assertIsNotNone(get_system(sysdef.system_id))
            self.assertEqual(sysdef.focus, "Emergency Medical")

    def test_pecos_groups_expose_multi_state_operators(self) -> None:
        groups = pecos_groups(min_size=2)
        self.assertGreater(len(groups), 20)
        top = groups.iloc[0]
        self.assertGreater(int(top["npis"]), 20)
        self.assertGreater(int(top["states"]), 15)
        self.assertTrue((groups["npis"] >= 2).all())

    def test_coverage_is_reported_against_this_slice_not_nppes(self) -> None:
        stats = dict((name, (res, total)) for name, res, total in
                     npi_registry_coverage())
        self.assertEqual(stats["NPI"][0], stats["NPI"][1])
        self.assertEqual(stats["Taxonomy"][0], stats["Taxonomy"][1])
        mapped, total = stats["Health system"]
        self.assertGreater(mapped, 1000)
        self.assertLess(mapped, total)
        self.assertGreater(stats["PECOS group"][0], 10000)


class DegradationTests(unittest.TestCase):
    def test_a_missing_cache_yields_an_empty_registry(self) -> None:
        import rcm_mc.data.npi_registry as nr

        original = nr._CACHE
        try:
            nr._CACHE = nr.Path("/definitely/not/here")
            nr._clear_cache()
            self.assertEqual(nr.load_npi_registry(), {})
            frame = nr.assign_npi_registry()
            self.assertTrue(frame.empty)
            self.assertEqual(list(frame.columns), list(NPI_COLUMNS))
            self.assertEqual(nr.npi_registry_coverage(), [])
            self.assertTrue(nr.pecos_groups().empty)
        finally:
            nr._CACHE = original
            nr._clear_cache()

    def test_unmapped_records_say_so_rather_than_guessing(self) -> None:
        frame = assign_npi_registry()
        unmapped = frame[frame["system_id"] == UNMAPPED_ID]
        self.assertGreater(len(unmapped), 15000)
        self.assertTrue(unmapped["system_match"].eq("").all())


class CsvRouteTests(unittest.TestCase):
    """Served over real HTTP, defanged, on a live server."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as sock:
            sock.bind(("127.0.0.1", 0))
            cls._port = sock.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "npi.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _rows(self, route: str):
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{self._port}{route}", timeout=120)
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))

    def test_the_whole_slice_serves(self) -> None:
        rows = self._rows("/npi-registry.csv")
        self.assertEqual(len(rows), len(assign_npi_registry()))
        for col in ("npi", "dba", "pecos_group", "taxonomy_code",
                    "county_fips", "cbsa_title", "system_name"):
            self.assertIn(col, rows[0])

    def test_filters_narrow_the_export(self) -> None:
        texas = self._rows("/npi-registry.csv?state=TX")
        self.assertTrue(texas)
        self.assertEqual({r["state"] for r in texas}, {"TX"})
        gmr = self._rows("/npi-registry.csv?system=global_medical_response")
        self.assertGreater(len(gmr), 500)
        self.assertEqual({r["system_id"] for r in gmr},
                         {"global_medical_response"})

    def test_a_pecos_group_pulls_its_whole_enrolment(self) -> None:
        """The grouping is the point: one query returns every NPI CMS
        enrolled under the same organization."""
        biggest = pecos_groups(min_size=2).iloc[0]["pecos_group"]
        rows = self._rows(f"/npi-registry.csv?pecos_group={biggest}")
        self.assertGreater(len(rows), 20)
        self.assertEqual({r["pecos_group"] for r in rows}, {biggest})
        self.assertGreater(len({r["state"] for r in rows}), 15)


if __name__ == "__main__":
    unittest.main()
