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
    link_npis_to_ccns,
    match_organization,
    npi_coverage,
    npi_rows,
)
from rcm_mc.data.provider_crosswalk import (
    CROSSWALK_COLUMNS,
    NUCC_BY_FACILITY_TYPE,
    SCOPE_ALL,
    _county_by_zip,
    _resolve_npi_collisions,
    _same_taxonomy_family,
    build_crosswalk,
    cbsa_for_county,
    county_fips_for,
    crosswalk_by_cbsa,
    crosswalk_by_class,
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

    def test_the_ccn_classifier_agrees_with_cms_on_every_row(self) -> None:
        """CMS publishes its own hospital_type for 5,085 facilities. That
        is an independent check on the CCN-range classifier, and it should
        be exact — this assertion is what caught the 0880-0899 bucket
        falling through to "other" and then being asserted to be a chronic
        disease hospital."""
        xw = get_crosswalk(scope=SCOPE_ALL)
        both = xw[xw["cms_hospital_type"].ne("") & xw["facility_type"].ne("")]
        self.assertGreater(len(both), 5000)
        expected = {
            "general": "Acute Care Hospitals",
            "critical_access": "Critical Access Hospitals",
            "psychiatric": "Psychiatric",
            "children": "Childrens",
            "ltach": "Long-term",
        }
        disagreements = [
            (row["ccn"], row["name"], row["facility_type"],
             row["cms_hospital_type"])
            for row in both.to_dict("records")
            if expected.get(row["facility_type"]) != row["cms_hospital_type"]
        ]
        self.assertEqual(disagreements, [],
                         f"CCN range disagrees with CMS: {disagreements[:5]}")

    def test_the_religious_nonmedical_series_is_typed_as_itself(self) -> None:
        """CCN sequence 1990-1999 is the RNHCI series — Christian Science
        sanatoria, which file no hospital quality data and appear nowhere
        in Care Compare. They were previously typed "other" and emitted
        as chronic disease hospitals."""
        xw = get_crosswalk(scope=SCOPE_ALL)
        rnhci = xw[xw["facility_type"].eq("rnhci")]
        self.assertGreaterEqual(len(rnhci), 10)
        self.assertEqual(set(rnhci["taxonomy_code"]), {"282J00000X"})
        self.assertTrue(rnhci["cms_hospital_type"].eq("").all())
        sequences = {int(c[-4:]) for c in rnhci["ccn"]}
        self.assertTrue(all(1990 <= s <= 1999 for s in sequences), sequences)

    def test_unclassified_emits_no_taxonomy_rather_than_a_guess(self) -> None:
        """A NUCC code is a clinical assertion. Emitting one for a
        facility whose type we could not determine is a fabricated fact
        that reads exactly like a derived one."""
        self.assertEqual(facility_taxonomy("other"), ("", ""))
        self.assertEqual(facility_taxonomy("nonsense"), ("", ""))
        # Nothing falls through today, so fill is still complete.
        xw = get_crosswalk(scope=SCOPE_ALL)
        self.assertEqual(int(xw["facility_type"].eq("other").sum()), 0)
        self.assertTrue(xw["taxonomy_code"].ne("").all())

    def test_the_physician_owned_texas_hospitals_type_as_acute(self) -> None:
        from rcm_mc.data.hcris import classify_hospital_type

        for ccn in ("450880", "450890", "450893"):
            self.assertEqual(classify_hospital_type(ccn), "general", ccn)
        self.assertEqual(classify_hospital_type("051993"), "rnhci")

    def test_post_acute_classes_map_to_their_own_vocabulary(self) -> None:
        """CMS states the provider class outright in the Compare files —
        re-deriving it from a CCN range would only add a way to be
        wrong."""
        self.assertEqual(facility_taxonomy("snf")[0], "314000000X")
        self.assertEqual(facility_taxonomy("hha")[0], "251E00000X")
        self.assertEqual(facility_taxonomy("hospice")[0], "251G00000X")
        self.assertEqual(facility_taxonomy("dialysis")[0], "261QE0700X")

    def test_codes_are_well_formed_nucc(self) -> None:
        # NUCC codes are 10 characters: a 3-digit grouping, then six
        # alphanumerics of classification + specialization, then a
        # trailing X. 282N00000X carries one classification letter,
        # 282NC0060X (Critical Access) two, 314000000X (SNF) none.
        for facility_type, (code, desc) in NUCC_BY_FACILITY_TYPE.items():
            if facility_type == "other":
                # The one deliberate sentinel: unclassified emits nothing.
                self.assertEqual((code, desc), ("", ""))
                continue
            self.assertRegex(code, r"^\d{3}[0-9A-Z]{6}X$")
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


class FullScopeTests(unittest.TestCase):
    """``scope="all"`` — every Medicare-certified CCN, not just hospitals."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.xw = get_crosswalk(scope=SCOPE_ALL)

    def test_the_full_scope_is_eight_times_the_hospital_one(self) -> None:
        self.assertGreater(len(self.xw), 48000)
        self.assertGreater(len(self.xw), len(get_crosswalk()) * 7)
        self.assertEqual(len(self.xw), self.xw["ccn"].nunique())
        self.assertEqual(list(self.xw.columns), list(CROSSWALK_COLUMNS))

    def test_the_hospital_scope_is_a_strict_subset(self) -> None:
        hospitals = get_crosswalk()
        self.assertTrue(set(hospitals["ccn"]).issubset(set(self.xw["ccn"])))
        self.assertEqual(
            int(self.xw["provider_class"].eq("hospital").sum()), len(hospitals))

    def test_an_unknown_scope_is_refused_rather_than_guessed(self) -> None:
        with self.assertRaises(ValueError):
            get_crosswalk(scope="everything")

    def test_every_class_is_geocoded_to_a_county(self) -> None:
        by_class = crosswalk_by_class().set_index("provider_class")
        for provider_class in ("snf", "hha", "hospice", "dialysis"):
            row = by_class.loc[provider_class]
            self.assertGreater(row["with_county"] / row["facilities"], 0.85,
                               provider_class)

    def test_mapping_strength_varies_enormously_by_class(self) -> None:
        """One average across dialysis and nursing homes describes
        neither: CMS publishes a parent chain for dialysis and nothing
        for SNFs, whose names are local and whose operators churn."""
        by_class = crosswalk_by_class().set_index("provider_class")
        self.assertGreater(by_class.loc["dialysis", "mapped_pct"], 80.0)
        self.assertLess(by_class.loc["snf", "mapped_pct"], 25.0)

    def test_beds_stay_on_the_hospital_rows(self) -> None:
        """A dialysis station has no beds. Letting the market rollup
        count facilities and beds off the same rows would make
        beds-per-facility read as a tenth of its real value."""
        non_hospital = self.xw[self.xw["provider_class"].ne("hospital")]
        beds = pd.to_numeric(non_hospital["net_patient_revenue"], errors="coerce")
        self.assertTrue(beds.isna().all())
        markets = crosswalk_by_cbsa(scope=SCOPE_ALL).set_index("cbsa_code")
        ny = markets.loc["35620"]
        self.assertGreater(ny["facilities"], ny["hospitals"] * 3)
        self.assertGreater(ny["beds"], 30000)

    def test_a_zip_resolves_the_county_the_home_health_file_omits(self) -> None:
        """Home health is the one class CMS publishes with no county
        column. The ZIP-learned mapping is what gives those 12,392
        agencies any geography at all."""
        sources = self.xw["county_fips_source"].value_counts()
        self.assertGreater(sources.get("zip inferred", 0), 5000)
        hha = self.xw[self.xw["provider_class"].eq("hha")]
        inferred = hha[hha["county_fips_source"].eq("zip inferred")]
        self.assertGreater(len(inferred) / len(hha), 0.8)

    def test_an_ambiguous_zip_is_dropped_not_guessed(self) -> None:
        """A ZIP that straddles a county line resolves to two FIPS in the
        observed data. An inferred county that is right most of the time
        is worse than an absent one — nothing downstream can tell which
        rows to distrust."""
        learned = _county_by_zip()
        self.assertGreater(len(learned), 10000)
        self.assertTrue(all(len(v) == 5 and v.isdigit() for v in learned.values()))
        # Every learned ZIP maps to exactly one county by construction.
        self.assertEqual(len(set(learned)), len(learned))


class NpiLinkTests(unittest.TestCase):
    """CCN -> NPI, from the one NPPES source that exists offline.

    The join is name+state+ZIP5 against both the legal name and every
    d/b/a. What makes it worth shipping at 90 rows is not the count —
    it is that 187 of the 277 raw matches are WRONG in a way that looks
    right, and the rules reject all of them.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.xw = get_crosswalk(scope=SCOPE_ALL)
        cls.linked = cls.xw[cls.xw["npi"].ne("")]

    def test_the_column_is_no_longer_hardcoded_empty(self) -> None:
        self.assertGreater(len(self.linked), 50)
        self.assertTrue(self.linked["npi"].str.fullmatch(r"\d{10}").all())
        self.assertTrue(self.linked["npi_source"].ne("").all())

    def test_one_npi_per_ccn_and_one_ccn_per_npi(self) -> None:
        """The invariant that matters, however it is achieved.

        On the bundled data the taxonomy-family gate is what delivers
        this — a hospital and its own rehab unit file the same name at
        the same address, and the unit is rejected for being typed 283X
        against a 282N NPI. The collision resolver is tested separately
        and directly, because here it would pass vacuously."""
        self.assertEqual(len(self.linked), self.linked["npi"].nunique())
        self.assertEqual(len(self.linked), self.linked["ccn"].nunique())

    def test_the_taxonomy_gate_is_what_separates_a_unit_from_its_parent(self) -> None:
        """Name the mechanism, so the invariant above cannot quietly
        start depending on something else. Riverside Medical Center is
        CCN 140186 and 14T186 at one address under one name."""
        pair = self.xw[self.xw["ccn"].isin(["140186", "14T186"])].set_index("ccn")
        self.assertEqual(len(pair), 2)
        self.assertNotEqual(pair.loc["140186", "npi"], "")
        self.assertEqual(pair.loc["14T186", "npi"], "")
        self.assertEqual(pair.loc["140186", "name"], pair.loc["14T186", "name"])
        self.assertEqual(pair.loc["140186", "zip"], pair.loc["14T186", "zip"])

    def test_the_collision_resolver_breaks_a_tie_it_can_break(self) -> None:
        """Exercised directly: nothing in the bundled universe reaches
        it, because the taxonomy gate rejects the mismatched claimant
        first. What is left for it is two rows of the SAME type sharing
        a name and ZIP, which does not occur today but would be a real
        error if it did."""
        rows = [
            {"ccn": "111111", "npi": "1234567893", "npi_source": "nppes name",
             "npi_taxonomy": "282N00000X", "taxonomy_code": "282N00000X"},
            {"ccn": "222222", "npi": "1234567893", "npi_source": "nppes name",
             "npi_taxonomy": "282N00000X", "taxonomy_code": "283X00000X"},
        ]
        _resolve_npi_collisions(rows)
        self.assertEqual(rows[0]["npi"], "1234567893")
        self.assertEqual(rows[1]["npi"], "")
        self.assertEqual(rows[1]["npi_source"], "")
        self.assertEqual(rows[1]["npi_taxonomy"], "")

    def test_an_unbreakable_tie_costs_every_claimant_the_npi(self) -> None:
        """Two rows of the same type with equal claim. Guessing between
        them would put an NPI on the wrong row half the time."""
        rows = [
            {"ccn": "111111", "npi": "1234567893", "npi_source": "nppes name",
             "npi_taxonomy": "282N00000X", "taxonomy_code": "282N00000X"},
            {"ccn": "222222", "npi": "1234567893", "npi_source": "nppes name",
             "npi_taxonomy": "282N00000X", "taxonomy_code": "282N00000X"},
        ]
        _resolve_npi_collisions(rows)
        self.assertEqual([r["npi"] for r in rows], ["", ""])

    def test_a_lone_claimant_is_left_alone(self) -> None:
        rows = [{"ccn": "111111", "npi": "1234567893", "npi_source": "nppes name",
                 "npi_taxonomy": "282N00000X", "taxonomy_code": "283X00000X"}]
        _resolve_npi_collisions(rows)
        self.assertEqual(rows[0]["npi"], "1234567893")

    def test_the_npi_describes_the_same_kind_of_provider_as_the_row(self) -> None:
        """A hospital's ambulance service, its rehab unit and its
        nursing home all enumerate under the hospital's name at the
        hospital's address. Comparing the NUCC classification family
        rejects every one of those."""
        for row in self.linked.to_dict("records"):
            self.assertEqual(row["npi_taxonomy"][:4], row["taxonomy_code"][:4],
                             f"{row['ccn']} {row['name']}")

    def test_a_finer_taxonomy_is_a_refinement_not_a_conflict(self) -> None:
        """282NR1301X (Rural Acute Care) on a row typed 282N00000X is
        the same hospital described more precisely. Rejecting it would
        throw away correct links to prove a point."""
        self.assertTrue(_same_taxonomy_family("282NR1301X", "282N00000X"))
        self.assertTrue(_same_taxonomy_family("282NC0060X", "282N00000X"))
        self.assertFalse(_same_taxonomy_family("283X00000X", "282N00000X"))
        self.assertFalse(_same_taxonomy_family("3416L0300X", "282N00000X"))
        self.assertFalse(_same_taxonomy_family("", "282N00000X"))
        refined = self.linked[
            self.linked["npi_taxonomy"] != self.linked["taxonomy_code"]]
        self.assertGreater(len(refined), 0)

    def test_the_dba_tier_carries_its_weight(self) -> None:
        """NPI 1841241833 files legally as HOT SPRINGS NATIONAL PARK
        HOSPITAL HOLDINGS LLC and does business as NATIONAL PARK MEDICAL
        CENTER, which is the name on the cost report."""
        sources = self.linked["npi_source"].value_counts()
        self.assertGreater(sources.get("nppes dba+state+zip5", 0), 20)
        self.assertGreater(sources.get("nppes name+state+zip5", 0), 20)
        by_ccn = self.linked.set_index("ccn")
        self.assertEqual(by_ccn.loc["040078", "npi"], "1841241833")
        self.assertEqual(by_ccn.loc["040078", "npi_source"],
                         "nppes dba+state+zip5")

    def test_every_linked_npi_is_in_the_roster(self) -> None:
        from rcm_mc.data.npi_registry import load_npi_registry

        roster = load_npi_registry()
        for row in self.linked.to_dict("records"):
            record = roster.get(row["npi"])
            self.assertIsNotNone(record, row["npi"])
            self.assertEqual(record.state, row["state"])
            self.assertEqual(record.zip5, str(row["zip"])[:5])

    def test_the_index_drops_a_key_two_npis_claim(self) -> None:
        from rcm_mc.data.npi_registry import load_npi_registry, organization_index

        index = organization_index()
        self.assertGreater(len(index), 15000)
        # Every entry resolves to exactly one NPI by construction.
        roster = load_npi_registry()
        for (_, state, zip5), (npi, taxonomy, basis) in list(index.items())[:200]:
            self.assertIn(npi, roster)
            self.assertEqual(roster[npi].state, state)
            self.assertEqual(roster[npi].zip5, zip5)
            self.assertEqual(roster[npi].taxonomy_code, taxonomy)
            self.assertIn(basis, ("name", "dba"))


class CoverageTests(unittest.TestCase):
    def test_coverage_is_reported_worst_first(self) -> None:
        stats = crosswalk_coverage()
        self.assertTrue(stats)
        pcts = [s.pct for s in stats]
        self.assertEqual(pcts, sorted(pcts))

    def test_ccn_is_complete_and_npi_is_honest_about_being_thin(self) -> None:
        """NPI is the weakest link and the note has to say why. It is
        thin because the only NPPES source available offline is a
        20,401-NPI ambulance roster, not because the join is broken."""
        by_id = {s.identifier: s for s in crosswalk_coverage()}
        self.assertEqual(by_id["CCN"].pct, 100.0)
        self.assertGreater(by_id["NPI"].resolved, 0)
        self.assertLess(by_id["NPI"].pct, 5.0)
        self.assertIn("NPPES", by_id["NPI"].note)
        self.assertIn("name+state+ZIP5", by_id["NPI"].note)

    def test_observed_ownership_is_reported_as_its_own_identifier(self) -> None:
        by_id = {s.identifier: s for s in crosswalk_coverage()}
        self.assertIn("CMS ownership", by_id)
        self.assertGreater(by_id["CMS ownership"].pct, 80.0)

    def test_ownership_survives_the_widening_to_every_class(self) -> None:
        """CMS publishes an ownership class for all seven provider
        classes. Carrying it for hospitals only would report 10% where
        the data supports 96%."""
        by_id = {s.identifier: s
                 for s in crosswalk_coverage(scope=SCOPE_ALL)}
        self.assertGreater(by_id["CMS ownership"].pct, 90.0)
        xw = get_crosswalk(scope=SCOPE_ALL)
        # Hospice is the weakest class at ~89%; CMS simply leaves the
        # field blank on some agencies.
        for provider_class in ("snf", "hha", "hospice", "dialysis"):
            rows = xw[xw["provider_class"].eq(provider_class)]
            self.assertGreater(rows["cms_ownership"].ne("").mean(), 0.85,
                               provider_class)

    def test_certification_dates_ride_along_and_stay_sortable(self) -> None:
        xw = get_crosswalk(scope=SCOPE_ALL)
        dates = xw["certification_date"]
        present = dates[dates.ne("")]
        self.assertGreater(len(present), 40000)
        self.assertTrue(present.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all())
        # Hospitals file no certification date in HCRIS.
        hospitals = xw[xw["provider_class"].eq("hospital")]
        self.assertTrue(hospitals["certification_date"].eq("").all())


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


def _link_fixture(path: Path) -> None:
    """Three NPIs claiming one CCN, one clean pair, one many-CCN key."""
    rows = [
        # Same name, state and ZIP on three NPIs — a hospital and two of
        # its own subparts is exactly how this happens in NPPES.
        {COL_NPI: "1000000001", COL_ENTITY: "2",
         COL_LEGAL_NAME: "CONTESTED REGIONAL HOSPITAL", COL_STATE: "TX",
         COL_CITY: "ANYTOWN", COL_ZIP: "70001", COL_TAXONOMY: "282N00000X"},
        {COL_NPI: "1000000002", COL_ENTITY: "2",
         COL_LEGAL_NAME: "CONTESTED REGIONAL HOSPITAL", COL_STATE: "TX",
         COL_CITY: "ANYTOWN", COL_ZIP: "70001", COL_TAXONOMY: "282N00000X"},
        {COL_NPI: "1000000003", COL_ENTITY: "2",
         COL_LEGAL_NAME: "CONTESTED REGIONAL HOSPITAL", COL_STATE: "TX",
         COL_CITY: "ANYTOWN", COL_ZIP: "70001", COL_TAXONOMY: "282N00000X"},
        # One NPI, one CCN, nothing else in the way.
        {COL_NPI: "1000000005", COL_ENTITY: "2",
         COL_LEGAL_NAME: "CLEAN PAIR HOSPITAL", COL_STATE: "TX",
         COL_CITY: "ELSEWHERE", COL_ZIP: "70003", COL_TAXONOMY: "282N00000X"},
        # Its key matches two CCNs — the direction that was always caught.
        {COL_NPI: "1000000004", COL_ENTITY: "2",
         COL_LEGAL_NAME: "TWIN CAMPUS HOSPITAL", COL_STATE: "TX",
         COL_CITY: "TWINSVILLE", COL_ZIP: "70002", COL_TAXONOMY: "282N00000X"},
    ]
    cols = [COL_NPI, COL_ENTITY, COL_LEGAL_NAME, COL_DBA, COL_LAST, COL_FIRST,
            COL_ADDR, COL_CITY, COL_STATE, COL_ZIP, COL_TAXONOMY,
            COL_DEACTIVATION, COL_REACTIVATION]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in cols})


class NpiToCcnLinkTests(unittest.TestCase):
    """Ambiguity runs both ways, and only one way used to be visible."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "npidata.csv"
        self.db = Path(self.tmp.name) / "npi.db"
        _link_fixture(self.csv)
        ingest_nppes(self.csv, self.db, chunk_size=10)
        self.crosswalk = pd.DataFrame([
            {"ccn": "333333", "name": "CONTESTED REGIONAL HOSPITAL",
             "state": "TX", "zip": "70001"},
            {"ccn": "444444", "name": "TWIN CAMPUS HOSPITAL",
             "state": "TX", "zip": "70002"},
            {"ccn": "444445", "name": "TWIN CAMPUS HOSPITAL",
             "state": "TX", "zip": "70002"},
            {"ccn": "555555", "name": "CLEAN PAIR HOSPITAL",
             "state": "TX", "zip": "70003"},
        ])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _linked(self):
        import sqlite3

        con = sqlite3.connect(str(self.db))
        try:
            return dict(con.execute(
                "SELECT npi, ccn FROM npi_crosswalk WHERE ccn IS NOT NULL"))
        finally:
            con.close()

    def test_a_ccn_several_npis_claim_is_left_unlinked(self) -> None:
        """This is the direction that was invisible. Each of the three
        NPIs saw a single-element candidate list, so all three linked and
        `ambiguous` stayed at zero while CCN 333333 quietly acquired
        three NPIs."""
        stats = link_npis_to_ccns(self.db, crosswalk=self.crosswalk)
        self.assertEqual(stats["ccn_contested"], 1)
        linked = self._linked()
        self.assertNotIn("1000000001", linked)
        self.assertNotIn("1000000002", linked)
        self.assertNotIn("1000000003", linked)
        self.assertNotIn("333333", set(linked.values()))

    def test_an_npi_matching_two_ccns_is_still_caught(self) -> None:
        stats = link_npis_to_ccns(self.db, crosswalk=self.crosswalk)
        self.assertEqual(stats["ambiguous"], 1)
        self.assertNotIn("1000000004", self._linked())

    def test_the_unambiguous_pair_still_links(self) -> None:
        """The guards must not swallow the case they exist to protect."""
        stats = link_npis_to_ccns(self.db, crosswalk=self.crosswalk)
        self.assertEqual(stats["linked"], 1)
        self.assertEqual(self._linked(), {"1000000005": "555555"})
        self.assertEqual(stats["considered"], 5)

    def test_linking_is_idempotent(self) -> None:
        first = link_npis_to_ccns(self.db, crosswalk=self.crosswalk)
        second = link_npis_to_ccns(self.db, crosswalk=self.crosswalk)
        self.assertEqual(first, second)


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

    def test_scope_all_widens_to_every_certified_ccn(self) -> None:
        rows = self._rows("/provider-crosswalk.csv?scope=all")
        self.assertEqual(len(rows), len(get_crosswalk(scope=SCOPE_ALL)))
        self.assertGreater(len(rows), 48000)
        self.assertIn("dialysis", {r["provider_class"] for r in rows})

    def test_scope_defaults_to_hospitals_rather_than_everything(self) -> None:
        """The default frame is the one with beds and revenue on it. A
        caller who did not ask for 48,510 rows should not get them."""
        rows = self._rows("/provider-crosswalk.csv?scope=nonsense")
        self.assertEqual(len(rows), len(get_crosswalk()))
        self.assertEqual({r["provider_class"] for r in rows}, {"hospital"})

    def test_class_filter_narrows_to_one_provider_class(self) -> None:
        rows = self._rows("/provider-crosswalk.csv?scope=all&class=snf")
        self.assertGreater(len(rows), 14000)
        self.assertEqual({r["provider_class"] for r in rows}, {"snf"})
        self.assertEqual({r["taxonomy_code"] for r in rows}, {"314000000X"})


if __name__ == "__main__":
    unittest.main()
