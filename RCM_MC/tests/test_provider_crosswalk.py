"""Provider identifier crosswalk — CCN to system, county, CBSA, taxonomy, NPI.

The crosswalk's value is that a join can be trusted, so the assertions
here are about *provenance and honesty*: every derived identifier names
its source, an absent CBSA is distinguished from a failed lookup, and an
individual NPI never acquires a health system it cannot have.
"""
from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from rcm_mc.data.nppes_ingest import (
    COL_ADDR,
    COL_CITY,
    COL_DBA,
    COL_DEACTIVATION,
    COL_ENTITY,
    COL_FIRST,
    COL_LAST,
    COL_LEGAL_NAME,
    COL_NPI,
    COL_REACTIVATION,
    COL_STATE,
    COL_TAXONOMY,
    COL_ZIP,
    ingest_nppes,
    match_organization,
    npi_coverage,
    npi_rows,
)
from rcm_mc.data.provider_crosswalk import (
    CROSSWALK_COLUMNS,
    NUCC_BY_FACILITY_TYPE,
    build_crosswalk,
    cbsa_for_county,
    county_fips_for,
    crosswalk_by_cbsa,
    crosswalk_coverage,
    facility_taxonomy,
    get_crosswalk,
)


class CrosswalkShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.xw = get_crosswalk()

    def test_one_row_per_ccn(self) -> None:
        self.assertEqual(len(self.xw), self.xw["ccn"].nunique())
        self.assertTrue((self.xw["ccn"].astype(str).str.len() > 0).all())

    def test_every_promised_column_is_present(self) -> None:
        self.assertEqual(list(self.xw.columns), list(CROSSWALK_COLUMNS))

    def test_every_derived_identifier_names_its_source(self) -> None:
        """A row whose provenance is invisible is a row nobody can check."""
        for value, source in (("county_fips", "county_fips_source"),
                              ("npi", "npi_source")):
            self.assertIn(source, self.xw.columns)
            has_value = self.xw[value].astype(str).str.strip().ne("")
            has_source = self.xw[source].astype(str).str.strip().ne("")
            self.assertTrue((~has_value | has_source).all(),
                            f"{value} present without {source}")


class CountyAndCbsaTests(unittest.TestCase):
    def test_two_independent_sources_resolve_the_county(self) -> None:
        """The cost-report fallback is not a rounding error: it carries
        1,500+ facilities the geocode file never had."""
        xw = get_crosswalk()
        sources = xw[xw["county_fips"].ne("")]["county_fips_source"].value_counts()
        self.assertGreater(sources.get("geocode", 0), 3000)
        self.assertGreater(sources.get("cost report", 0), 1000)

    def test_county_coverage_beats_the_geocode_file_alone(self) -> None:
        xw = get_crosswalk()
        resolved = int(xw["county_fips"].ne("").sum())
        self.assertGreater(resolved / len(xw), 0.90)

    def test_fips_is_always_five_digits(self) -> None:
        fips = get_crosswalk()["county_fips"]
        present = fips[fips.ne("")]
        self.assertTrue(present.str.fullmatch(r"\d{5}").all())

    def test_absent_cbsa_is_geography_not_a_failed_lookup(self) -> None:
        """A rural county sits outside every metro and micro area by
        definition. Calling that 'missing' invents a data-quality problem
        where there is only geography."""
        xw = get_crosswalk()
        has_fips = xw["county_fips"].ne("")
        no_cbsa = has_fips & xw["cbsa_code"].eq("")
        self.assertGreater(int(no_cbsa.sum()), 500)
        # Those rows resolved a county — the chain worked, the answer is "none".
        self.assertTrue(xw.loc[no_cbsa, "county_fips"].ne("").all())

    def test_cbsa_lookup_is_exact(self) -> None:
        # Salt Lake County, UT.
        rec = cbsa_for_county("49035")
        self.assertIsNotNone(rec)
        self.assertIn("Salt Lake", rec["cbsa_title"])
        self.assertEqual(rec["cbsa_type"], "Metropolitan")
        self.assertIsNone(cbsa_for_county(""))
        self.assertIsNone(cbsa_for_county("99999"))

    def test_county_resolution_returns_its_basis(self) -> None:
        fips, source = county_fips_for("010001", "AL", "HOUSTON")
        self.assertTrue(fips.startswith("01"))
        self.assertIn(source, ("geocode", "cost report"))
        self.assertEqual(county_fips_for("zzz", "ZZ", "NOWHERE"), ("", ""))


class TaxonomyTests(unittest.TestCase):
    def test_ccn_range_maps_to_the_standard_vocabulary(self) -> None:
        """The CCN range says what a facility is; NUCC codes are what the
        rest of the industry actually joins on."""
        self.assertEqual(facility_taxonomy("general")[0], "282N00000X")
        self.assertEqual(facility_taxonomy("critical_access")[0], "282NC0060X")
        self.assertEqual(facility_taxonomy("psychiatric")[0], "283Q00000X")
        self.assertEqual(facility_taxonomy("children")[0], "282NC2000X")
        self.assertEqual(facility_taxonomy("nonsense"), ("", ""))

    def test_every_facility_carries_a_taxonomy(self) -> None:
        xw = get_crosswalk()
        self.assertTrue(xw["taxonomy_code"].ne("").all())

    def test_codes_are_well_formed_nucc(self) -> None:
        # NUCC codes are 10 characters: a 3-digit grouping, a 1-2 letter
        # classification, digits, and a trailing X — 282N00000X carries one
        # letter, 282NC0060X (Critical Access) carries two.
        for code, desc in NUCC_BY_FACILITY_TYPE.values():
            self.assertRegex(code, r"^\d{3}[A-Z]{1,2}\d{4,5}X$")
            self.assertEqual(len(code), 10, code)
            self.assertTrue(desc)


class CareCompareTests(unittest.TestCase):
    """Care Compare's view of the same CCN, carried alongside HCRIS's."""

    def setUp(self) -> None:
        self.xw = get_crosswalk()

    def test_the_untruncated_name_is_carried_next_to_the_filed_one(self) -> None:
        """Both names are on the row on purpose: the filed one is what the
        matcher saw, the CMS one is what the facility is actually called."""
        both = self.xw[self.xw["cms_name"].ne("")]
        self.assertGreater(len(both), 5000)
        differ = both[both["cms_name"].str.upper() != both["name"].str.upper()]
        self.assertGreater(len(differ), 2000)

    def test_observed_ownership_is_the_only_signal_an_unmapped_row_has(self) -> None:
        """`system_kind` is a judgement about a system. A facility with no
        system has none — CMS's own class is what is left."""
        unmapped = self.xw[self.xw["system_id"].eq("_unmapped")]
        self.assertGreater(int(unmapped["cms_ownership"].ne("").sum()),
                           len(unmapped) * 0.6)
        self.assertIn("Proprietary", set(self.xw["cms_ownership"]))
        self.assertTrue(any(v.startswith("Government")
                            for v in set(self.xw["cms_ownership"])))

    def test_care_compare_county_is_a_third_source_not_a_replacement(self) -> None:
        """It only runs where the geocode file and the cost report both
        came up empty, so it must be the smallest of the three."""
        sources = self.xw[self.xw["county_fips"].ne("")]["county_fips_source"]
        counts = sources.value_counts()
        self.assertGreater(counts.get("care compare", 0), 0)
        self.assertLess(counts.get("care compare", 0), counts.get("cost report", 0))

    def test_ownership_and_type_are_blank_rather_than_guessed(self) -> None:
        """A facility Care Compare never listed gets an empty string, not
        an inferred class."""
        absent = self.xw[self.xw["cms_name"].eq("")]
        self.assertGreater(len(absent), 0)
        self.assertTrue(absent["cms_ownership"].eq("").all())
        self.assertTrue(absent["cms_hospital_type"].eq("").all())
        self.assertTrue(absent["emergency_services"].eq("").all())


class CoverageTests(unittest.TestCase):
    def test_coverage_is_reported_worst_first(self) -> None:
        stats = crosswalk_coverage()
        self.assertTrue(stats)
        pcts = [s.pct for s in stats]
        self.assertEqual(pcts, sorted(pcts))

    def test_ccn_is_complete_and_npi_is_honest_about_being_empty(self) -> None:
        by_id = {s.identifier: s for s in crosswalk_coverage()}
        self.assertEqual(by_id["CCN"].pct, 100.0)
        self.assertEqual(by_id["NPI"].resolved, 0)
        self.assertIn("NPPES", by_id["NPI"].note)

    def test_observed_ownership_is_reported_as_its_own_identifier(self) -> None:
        by_id = {s.identifier: s for s in crosswalk_coverage()}
        self.assertIn("CMS ownership", by_id)
        self.assertGreater(by_id["CMS ownership"].pct, 80.0)


class MarketRollupTests(unittest.TestCase):
    def test_cbsa_rollup_is_the_market_unit(self) -> None:
        markets = crosswalk_by_cbsa()
        self.assertGreater(len(markets), 500)
        top = markets.iloc[0]
        self.assertIn("New York", top["cbsa_title"])
        self.assertGreater(top["facilities"], 100)
        self.assertGreater(top["beds"], 10000)

    def test_rollup_counts_only_operating_facilities(self) -> None:
        xw = get_crosswalk()
        live_with_cbsa = xw[xw["is_operating"] & xw["cbsa_code"].ne("")]
        self.assertEqual(int(crosswalk_by_cbsa()["facilities"].sum()),
                         len(live_with_cbsa))

    def test_a_multi_state_metro_reports_multiple_states(self) -> None:
        markets = crosswalk_by_cbsa().set_index("cbsa_code")
        self.assertGreater(int(markets.loc["35620", "states"]), 1)  # NY-NJ


class EmptyFrameTests(unittest.TestCase):
    def test_empty_universe_still_returns_the_shape(self) -> None:
        out = build_crosswalk(pd.DataFrame(
            columns=["ccn", "name", "state", "beds", "net_patient_revenue"]))
        self.assertTrue(out.empty)
        self.assertEqual(list(out.columns), list(CROSSWALK_COLUMNS))


def _nppes_fixture(path: Path) -> None:
    """A miniature dissemination file covering every branch that matters."""
    rows = [
        {COL_NPI: "1111111111", COL_ENTITY: "2",
         COL_LEGAL_NAME: "ASCENSION SAINT THOMAS WEST", COL_STATE: "TN",
         COL_CITY: "NASHVILLE", COL_ZIP: "372051609", COL_TAXONOMY: "282N00000X"},
        # The brand lives ONLY in the d/b/a — a holding-company legal name.
        {COL_NPI: "2222222222", COL_ENTITY: "2",
         COL_LEGAL_NAME: "HOLDCO OPERATIONS LLC",
         COL_DBA: "OCEANS BEHAVIORAL HOSPITAL OF ABILENE", COL_STATE: "TX",
         COL_CITY: "ABILENE", COL_ZIP: "79606", COL_TAXONOMY: "283Q00000X"},
        {COL_NPI: "3333333333", COL_ENTITY: "2",
         COL_LEGAL_NAME: "SMALLTOWN COUNTY HOSPITAL", COL_STATE: "TX",
         COL_CITY: "NOWHERE", COL_ZIP: "79999", COL_TAXONOMY: "282N00000X"},
        {COL_NPI: "4444444444", COL_ENTITY: "1", COL_FIRST: "JANE",
         COL_LAST: "DOE", COL_STATE: "TN", COL_CITY: "NASHVILLE",
         COL_ZIP: "37205", COL_TAXONOMY: "207R00000X"},
        {COL_NPI: "5555555555", COL_ENTITY: "2", COL_LEGAL_NAME: "CLOSED CLINIC",
         COL_STATE: "TN", COL_DEACTIVATION: "01/05/2020"},
        {COL_NPI: "6666666666", COL_ENTITY: "2",
         COL_LEGAL_NAME: "ENCOMPASS HEALTH REHAB", COL_STATE: "AL",
         COL_CITY: "BIRMINGHAM", COL_ZIP: "35243",
         COL_DEACTIVATION: "01/05/2020", COL_REACTIVATION: "03/09/2021",
         COL_TAXONOMY: "283X00000X"},
    ]
    cols = [COL_NPI, COL_ENTITY, COL_LEGAL_NAME, COL_DBA, COL_LAST, COL_FIRST,
            COL_ADDR, COL_CITY, COL_STATE, COL_ZIP, COL_TAXONOMY,
            COL_DEACTIVATION, COL_REACTIVATION,
            # CMS adds columns between releases; the reader must tolerate it.
            "Some Column CMS Added Later"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in cols})


class NppesIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "npidata_pfile_sample.csv"
        self.db = Path(self.tmp.name) / "npi.db"
        _nppes_fixture(self.csv)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_streams_in_chunks_without_reading_the_whole_file(self) -> None:
        """The real file is ~9 GB; peak memory must be one chunk."""
        report = ingest_nppes(self.csv, self.db, chunk_size=2)
        self.assertEqual(report.chunks, 3)
        self.assertEqual(report.rows_read, 6)

    def test_a_dba_carries_the_brand_when_the_legal_name_is_a_holdco(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=2)
        self.assertEqual(report.matched_by_dba, 1)
        self.assertEqual(report.matched_by_legal_name, 2)
        rows = {r["npi"]: r for r in npi_rows(self.db, limit=50)}
        self.assertEqual(rows["2222222222"]["system_id"], "oceans")
        self.assertTrue(rows["2222222222"]["match_basis"].startswith("dba"))

    def test_an_individual_npi_never_acquires_a_system(self) -> None:
        """NPPES carries no affiliation field for individuals. Inventing
        one would make the whole crosswalk untrustworthy."""
        ingest_nppes(self.csv, self.db, chunk_size=2)
        rows = {r["npi"]: r for r in npi_rows(self.db, limit=50)}
        self.assertEqual(rows["4444444444"]["entity_type"], "1")
        self.assertEqual(rows["4444444444"]["system_id"], "")

    def test_reactivated_npis_survive_and_dead_ones_do_not(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=2)
        self.assertEqual(report.deactivated_skipped, 1)
        npis = {r["npi"] for r in npi_rows(self.db, limit=50)}
        self.assertNotIn("5555555555", npis)   # deactivated, never came back
        self.assertIn("6666666666", npis)      # deactivated then reactivated

    def test_rerunning_upserts_rather_than_duplicating(self) -> None:
        """A 9 GB ingest will get interrupted; resuming has to be safe."""
        ingest_nppes(self.csv, self.db, chunk_size=2)
        first = npi_coverage(self.db)
        ingest_nppes(self.csv, self.db, chunk_size=4)
        self.assertEqual(npi_coverage(self.db), first)

    def test_organizations_only_skips_the_individual_bulk(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=3,
                              organizations_only=True)
        self.assertEqual(report.individuals, 1)
        self.assertNotIn("4444444444", {r["npi"] for r in npi_rows(self.db, limit=50)})

    def test_a_file_that_is_not_nppes_is_rejected(self) -> None:
        bogus = Path(self.tmp.name) / "not_nppes.csv"
        bogus.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest_nppes(bogus, self.db)

    def test_coverage_counts_what_was_written(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=2)
        cov = npi_coverage(self.db)
        self.assertEqual(cov["npis"], 5)
        self.assertEqual(cov["organizations"], 4)
        self.assertEqual(cov["individuals"], 1)
        self.assertEqual(cov["system_matched"], 3)

    def test_rows_are_filterable_by_system_and_state(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=6)
        self.assertEqual(len(npi_rows(self.db, system_id="oceans")), 1)
        self.assertEqual(len(npi_rows(self.db, state="TN")), 2)


class OrganizationMatchTests(unittest.TestCase):
    def test_legal_name_is_tried_before_the_dba(self) -> None:
        system_id, basis = match_organization(
            "ASCENSION SAINT THOMAS WEST", "SOMETHING ELSE", "TN")
        self.assertEqual(system_id, "ascension")
        self.assertTrue(basis.startswith("legal name"))

    def test_the_dba_is_the_fallback_not_the_afterthought(self) -> None:
        system_id, basis = match_organization(
            "HOLDCO OPERATIONS LLC", "ENCOMPASS HEALTH REHAB OF DALLAS", "TX")
        self.assertEqual(system_id, "encompass")
        self.assertTrue(basis.startswith("dba"))

    def test_no_brand_means_no_claim(self) -> None:
        self.assertEqual(
            match_organization("SMALLTOWN COUNTY HOSPITAL", "", "TX"), ("", ""))
        self.assertEqual(match_organization("", "", ""), ("", ""))

    def test_state_scoping_survives_into_npi_matching(self) -> None:
        """The registry's state scopes are load-bearing here too — a Maine
        Mercy is not the Missouri one."""
        self.assertEqual(match_organization("MERCY HOSPITAL", "", "MO")[0],
                         "mercy_mo")
        self.assertEqual(match_organization("MERCY HOSPITAL", "", "ME"), ("", ""))


class CrosswalkRouteTests(unittest.TestCase):
    """The crosswalk is served over real HTTP, filterable, defanged."""

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
                              db_path=os.path.join(cls._tmp.name, "xw.db"))
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
        import urllib.request

        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{self._port}{route}", timeout=120)
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))

    def test_full_crosswalk_serves_every_facility(self) -> None:
        rows = self._rows("/provider-crosswalk.csv")
        self.assertEqual(len(rows), len(get_crosswalk()))
        for col in ("ccn", "system_name", "county_fips", "county_fips_source",
                    "cbsa_title", "taxonomy_code", "npi"):
            self.assertIn(col, rows[0])

    def test_state_and_cbsa_filters_narrow_the_export(self) -> None:
        utah = self._rows("/provider-crosswalk.csv?state=UT")
        self.assertTrue(utah)
        self.assertEqual({r["state"] for r in utah}, {"UT"})
        nyc = self._rows("/provider-crosswalk.csv?cbsa=35620")
        self.assertTrue(nyc)
        self.assertEqual({r["cbsa_code"] for r in nyc}, {"35620"})
        self.assertGreater(len({r["state"] for r in nyc}), 1)  # NY-NJ metro

    def test_system_filter_matches_the_registry(self) -> None:
        rows = self._rows("/provider-crosswalk.csv?system=oceans")
        self.assertTrue(rows)
        self.assertEqual({r["system_id"] for r in rows}, {"oceans"})


if __name__ == "__main__":
    unittest.main()
