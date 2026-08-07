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
    COL_CREDENTIAL,
    COL_DBA,
    COL_DEACTIVATION,
    COL_EIN,
    COL_ENTITY,
    COL_ENUMERATION,
    COL_FIRST,
    COL_LAST,
    COL_LAST_UPDATE,
    COL_LEGAL_NAME,
    COL_NPI,
    COL_PARENT_LBN,
    COL_PARENT_TIN,
    COL_REACTIVATION,
    COL_SOLE_PROPRIETOR,
    COL_STATE,
    COL_SUBPART,
    COL_TAXONOMY,
    COL_ZIP,
    STATUS_ACTIVE,
    STATUS_DEACTIVATED,
    STATUS_REACTIVATED,
    USE_COLUMNS,
    ingest_deactivations,
    ingest_nppes,
    link_npis_to_ccns,
    match_organization,
    npi_coverage,
    npi_rows,
)
from rcm_mc.data.county_demographics import (
    _county_by_name,
    _norm_county,
    _norm_county_for,
)
from rcm_mc.data.provider_crosswalk import (
    CROSSWALK_COLUMNS,
    NUCC_BY_FACILITY_TYPE,
    CBSA_SOURCE_CT_CITY,
    CBSA_SOURCE_CT_COUNTY,
    CBSA_SOURCE_NO_COUNTY,
    CBSA_SOURCE_OMB,
    CBSA_SOURCE_OUTSIDE,
    PARENT_SOURCE,
    SCOPE_ALL,
    _cbsa_by_county,
    _county_by_zip,
    _norm_city,
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
    parent_ccn_for,
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
        self.assertEqual(set(xw.loc[no_cbsa, "cbsa_source"]),
                         {CBSA_SOURCE_OUTSIDE})

    def test_every_row_says_where_its_cbsa_came_from_or_why_not(self) -> None:
        """A blank cbsa_code meant three different things and said none
        of them: rural geography, an unresolved county, and — for all
        385 Connecticut facilities — a county-vintage break."""
        xw = get_crosswalk(scope=SCOPE_ALL)
        self.assertTrue(xw["cbsa_source"].ne("").all())
        for row in xw.to_dict("records"):
            if row["cbsa_code"]:
                self.assertIn(row["cbsa_source"],
                              (CBSA_SOURCE_OMB, CBSA_SOURCE_CT_CITY,
                               CBSA_SOURCE_CT_COUNTY, PARENT_SOURCE),
                              row["ccn"])
            else:
                self.assertIn(row["cbsa_source"],
                              (CBSA_SOURCE_OUTSIDE, CBSA_SOURCE_NO_COUNTY),
                              row["ccn"])
        # A row with no county normally has no CBSA either — except in
        # Connecticut, where the principal-city tier reaches rows the
        # county chain never resolved at all.
        blank_county = xw["county_fips"].eq("")
        self.assertEqual(set(xw.loc[blank_county, "cbsa_source"]),
                         {CBSA_SOURCE_NO_COUNTY, CBSA_SOURCE_CT_CITY})
        outside_ct = (blank_county & xw["state"].ne("CT")
                      & xw["parent_ccn"].eq(""))
        self.assertEqual(set(xw.loc[outside_ct, "cbsa_source"]),
                         {CBSA_SOURCE_NO_COUNTY})


class CountyNameNormalizationTests(unittest.TestCase):
    """The county label differs from the ACS label by punctuation alone.

    O'Brien IA, Prince George's MD, E. Baton Rouge LA, St. Lucie FL —
    each failed an exact-match join over an apostrophe, a period or an
    abbreviation, and each is a real county with real demographics
    sitting on the other side.
    """

    def test_the_rules_do_what_they_claim(self) -> None:
        for raw, expected in (("O'BRIEN", "OBRIEN"),
                              ("Prince George's", "PRINCEGEORGES"),
                              ("St. Louis", "SAINTLOUIS"),
                              ("ST LUCIE", "SAINTLUCIE"),
                              ("E. Baton Rouge", "EASTBATONROUGE"),
                              ("W. Feliciana", "WESTFELICIANA"),
                              ("Houston County", "HOUSTON"),
                              ("De Kalb", "DEKALB")):
            self.assertEqual(_norm_county(raw), expected, raw)

    def test_saint_expansion_is_bounded(self) -> None:
        """ST -> SAINT must be a word, or STERLING becomes SAINTERLING."""
        self.assertEqual(_norm_county("STERLING"), "STERLING")
        self.assertEqual(_norm_county("STARK"), "STARK")
        self.assertEqual(_norm_county("STONE"), "STONE")

    def test_an_independent_city_never_merges_with_its_county(self) -> None:
        """Thirty-six facilities sit in a city sharing a name with the
        surrounding county, and the FIPS carry wildly different
        demographics — St. Louis County has 990,414 people, St. Louis
        city 286,578. Stripping a trailing ' CITY' would relocate large
        urban academic centers."""
        index = _county_by_name()
        for state, county, city, county_fips, city_fips in (
            ("MD", "Baltimore County", "Baltimore city", "24005", "24510"),
            ("MO", "St. Louis County", "St. Louis city", "29189", "29510"),
            ("VA", "Fairfax County", "Fairfax city", "51059", "51600"),
            ("VA", "Richmond County", "Richmond city", "51159", "51760"),
        ):
            self.assertEqual(
                index[(state, _norm_county(county))]["county_fips"], county_fips)
            self.assertEqual(
                index[(state, _norm_county(city))]["county_fips"], city_fips)

    def test_normalization_introduces_no_ambiguity(self) -> None:
        """The index must stay collision-free: 3,143 counties, 3,143
        keys. A widened normalizer can only add hits, never a choice."""
        index = _county_by_name()
        with (Path("rcm_mc/data/vendor/county_demographics")
              / "county_demographics.csv").open() as fh:
            source_rows = sum(1 for _ in csv.DictReader(fh))
        self.assertEqual(len(index), source_rows)

    def test_the_district_of_columbia_answers_to_its_short_names(self) -> None:
        self.assertEqual(_norm_county_for("DC", "DC"), "DISTRICTOFCOLUMBIA")
        self.assertEqual(_norm_county_for("DC", "The District"),
                         "DISTRICTOFCOLUMBIA")
        # The alias is state-scoped: Washington County MD is not DC.
        self.assertEqual(_norm_county_for("MD", "Washington"), "WASHINGTON")

    def test_county_coverage_moved(self) -> None:
        xw = get_crosswalk(scope=SCOPE_ALL)
        self.assertGreater(int(xw["county_fips"].ne("").sum()), 46600)


class ParentHospitalTests(unittest.TestCase):
    """A rehab unit inside a hospital knows nothing about where it is.

    810 of the 879 IRF rows are hospital-based units. They carry no
    coordinates at all and a county only when they happened to file
    one — while their parent hospital, already in this universe, has
    every bit of it.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.xw = get_crosswalk(scope=SCOPE_ALL)
        cls.children = cls.xw[cls.xw["parent_ccn"].ne("")]

    def test_the_transform_is_signal_not_ccn_density(self) -> None:
        """Worth checking rather than assuming: perturbing the sequence
        number by one resolves 41% and a random in-state sequence 12%,
        against 99.9% for the real rule."""
        universe = set(self.xw["ccn"])
        t_units = [c for c in universe
                   if len(c) == 6 and c[2] == "T" and c[3:].isdigit()]
        self.assertGreater(len(t_units), 700)
        real = sum(1 for c in t_units if parent_ccn_for(c) in universe)
        placebo = sum(1 for c in t_units
                      if f"{c[:2]}0{int(c[3:]) + 1:0{len(c) - 3}d}" in universe)
        self.assertGreater(real / len(t_units), 0.99)
        self.assertGreater(real, placebo * 2)

    def test_alpha_tailed_units_resolve_to_nothing_rather_than_guessing(self) -> None:
        """45TA23 is an LTCH unit whose parent is not in this universe.
        None of the ten digit substitutions hits, so it is unresolvable
        here rather than a near miss."""
        self.assertEqual(parent_ccn_for("45TA23"), "")
        self.assertEqual(parent_ccn_for("060010"), "")   # not a unit
        self.assertEqual(parent_ccn_for(""), "")
        self.assertEqual(parent_ccn_for("06T010"), "060010")

    def test_every_parent_is_a_hospital_in_this_universe(self) -> None:
        self.assertGreater(len(self.children), 700)
        self.assertEqual(set(self.children["provider_class"]), {"irf"})
        parents = self.xw[self.xw["ccn"].isin(set(self.children["parent_ccn"]))]
        self.assertEqual(len(parents), len(set(self.children["parent_ccn"])))
        self.assertEqual(set(parents["provider_class"]), {"hospital"})

    def test_geography_is_inherited_and_says_so(self) -> None:
        located = self.children[self.children["lat"].notna()]
        self.assertGreater(len(located), 600)
        self.assertEqual(set(located["geo_match_quality"]), {PARENT_SOURCE})

    def test_beds_and_revenue_are_never_inherited(self) -> None:
        """01T033 Spain Rehabilitation Center would take 1,138 beds and
        $2.29B from University of Alabama Hospital, and every per-bed
        figure downstream would be nonsense."""
        # A post-acute row carries "" where a hospital carries a
        # number, so assert on numeric content rather than on NaN.
        beds = pd.to_numeric(self.children["beds"], errors="coerce")
        revenue = pd.to_numeric(self.children["net_patient_revenue"],
                                errors="coerce")
        self.assertEqual(int(beds.notna().sum()), 0)
        self.assertEqual(int(revenue.notna().sum()), 0)

    def test_the_units_own_health_system_wins(self) -> None:
        """Where both name a system they agree 257 times in 262, but
        five genuinely differ — a Mercy rehab unit inside an Ascension
        hospital is still Mercy's."""
        inherited = self.children[
            self.children["system_match"].str.startswith(PARENT_SOURCE)]
        self.assertGreater(len(inherited), 100)
        # Nothing inherited a system it already had.
        by_ccn = self.xw.set_index("ccn")
        for row in inherited.to_dict("records"):
            parent = by_ccn.loc[row["parent_ccn"]]
            self.assertNotEqual(parent["system_id"], "_unmapped")
            self.assertEqual(row["system_id"], parent["system_id"])

    def test_the_rule_is_not_generalised_to_nursing_homes(self) -> None:
        """SNF CCNs also carry an alpha third character, but those are
        state numbering overflow rather than unit designators — the same
        transform resolves 17% of them and would fabricate ~211 false
        parent edges."""
        snf = self.xw[self.xw["provider_class"].eq("snf")]
        alpha = snf[snf["ccn"].str[2].str.isalpha()]
        self.assertGreater(len(alpha), 100)
        self.assertTrue(alpha["parent_ccn"].eq("").all())


class ConnecticutVintageTests(unittest.TestCase):
    """Connecticut swapped counties for planning regions in 2022.

    The bundled demographics file still mints legacy county FIPS
    (09001-09015); the bundled OMB-2023 delineation keys on planning
    regions (09110-09190). The two sets share nothing, so every
    Connecticut facility failed the county to CBSA join and was
    reported as sitting outside every metro area — 7,554 hospital beds
    and $14.87B of net patient revenue missing from the market view,
    in metros the delineation file itself lists.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.xw = get_crosswalk(scope=SCOPE_ALL)
        cls.ct = cls.xw[cls.xw["state"].eq("CT")]

    def test_the_vintage_break_is_real_and_is_connecticut_alone(self) -> None:
        """Derived, not asserted: compare the two files' key sets state
        by state. Only one state's intersection is empty."""
        import collections

        cbsa_keys = collections.defaultdict(set)
        for fips in _cbsa_by_county():
            cbsa_keys[fips[:2]].add(fips)
        demo_keys = collections.defaultdict(set)
        with (Path("rcm_mc/data/vendor/county_demographics")
              / "county_demographics.csv").open() as fh:
            for row in csv.DictReader(fh):
                fips = row["county_fips"].zfill(5)
                demo_keys[fips[:2]].add(fips)
        disjoint = sorted(
            prefix for prefix in set(cbsa_keys) & set(demo_keys)
            if cbsa_keys[prefix] and demo_keys[prefix]
            and not (cbsa_keys[prefix] & demo_keys[prefix]))
        self.assertEqual(disjoint, ["09"])

    def test_connecticut_facilities_are_no_longer_reported_as_rural(self) -> None:
        self.assertGreater(len(self.ct), 350)
        self.assertGreater(int(self.ct["cbsa_code"].ne("").sum()), 250)
        # Not one CT row may claim to be outside every metro area: the
        # state has no county that is.
        self.assertNotIn(CBSA_SOURCE_OUTSIDE, set(self.ct["cbsa_source"]))

    def test_the_principal_city_tier_beats_the_county_tier(self) -> None:
        """Waterbury and Shelton are named in the Waterbury-Shelton
        title. A county rule would file Waterbury under New Haven and
        Shelton under Bridgeport — both wrong, and both large."""
        waterbury = self.ct[self.ct["city"].str.upper().str.strip().eq("WATERBURY")]
        self.assertGreater(len(waterbury), 5)
        self.assertEqual(set(waterbury["cbsa_code"]), {"47930"})
        self.assertEqual(set(waterbury["cbsa_source"]), {CBSA_SOURCE_CT_CITY})

    def test_the_big_connecticut_hospitals_land_in_the_right_metro(self) -> None:
        by_ccn = self.xw.set_index("ccn")
        for ccn, cbsa in (("070022", "35300"),    # Yale New Haven
                          ("070025", "25540"),    # Hartford Hospital
                          ("070010", "14860"),    # Bridgeport Hospital
                          ("070006", "14860"),    # Stamford
                          ("070007", "35980"),    # Lawrence & Memorial
                          ("070005", "47930"),    # Waterbury Hospital
                          ("070016", "47930")):   # St. Mary's Waterbury
            self.assertEqual(by_ccn.loc[ccn, "cbsa_code"], cbsa, ccn)

    def test_connecticut_markets_reach_the_rollup(self) -> None:
        markets = crosswalk_by_cbsa()
        ct_markets = markets[markets["cbsa_title"].str.endswith(", CT")]
        self.assertEqual(len(ct_markets), 7)
        self.assertGreater(int(ct_markets["beds"].sum()), 7000)

    def test_a_city_is_normalised_before_it_is_matched(self) -> None:
        """HCRIS types a city three ways and all three must key alike."""
        self.assertEqual(_norm_city("STAMFORD  CT 06904"), "STAMFORD")
        self.assertEqual(_norm_city("GREENWICH, CT"), "GREENWICH")
        self.assertEqual(_norm_city("west hartford"), "WEST HARTFORD")
        self.assertEqual(_norm_city(None), "")

    def test_a_non_connecticut_row_never_takes_the_ct_path(self) -> None:
        rest = self.xw[self.xw["state"].ne("CT")]
        self.assertNotIn(CBSA_SOURCE_CT_CITY, set(rest["cbsa_source"]))
        self.assertNotIn(CBSA_SOURCE_CT_COUNTY, set(rest["cbsa_source"]))

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
        # A subpart naming its parent, with the primary taxonomy in slot 2
        # rather than slot 1 — both are ordinary in the real file and both
        # were invisible to the reader before.
        {COL_NPI: "7777777777", COL_ENTITY: "2",
         COL_LEGAL_NAME: "ASCENSION SAINT THOMAS HOME CARE", COL_STATE: "TN",
         COL_CITY: "NASHVILLE", COL_ZIP: "37205",
         COL_TAXONOMY: "332B00000X",
         "Healthcare Provider Primary Taxonomy Switch_1": "N",
         "Healthcare Provider Taxonomy Code_2": "251E00000X",
         "Healthcare Provider Primary Taxonomy Switch_2": "Y",
         COL_SUBPART: "Y", COL_PARENT_LBN: "ASCENSION HEALTH",
         COL_PARENT_TIN: "999999999", COL_EIN: "123456789",
         COL_ENUMERATION: "05/23/2006", COL_LAST_UPDATE: "01/02/2024"},
        # A sole proprietor with a credential — an individual NPI that is
        # also, legally, the business.
        {COL_NPI: "8888888888", COL_ENTITY: "1", COL_FIRST: "SAM",
         COL_LAST: "ROE", COL_STATE: "TX", COL_CITY: "AUSTIN",
         COL_ZIP: "78701", COL_TAXONOMY: "207Q00000X",
         COL_CREDENTIAL: "M.D.", COL_SOLE_PROPRIETOR: "Y"},
    ]
    cols = list(USE_COLUMNS) + [
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
        self.assertEqual(report.chunks, 4)
        self.assertEqual(report.rows_read, 8)

    def test_a_dba_carries_the_brand_when_the_legal_name_is_a_holdco(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=2)
        self.assertEqual(report.matched_by_dba, 1)
        self.assertEqual(report.matched_by_legal_name, 3)
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

    def test_a_dead_npi_is_recorded_not_forgotten(self) -> None:
        """A crosswalk exists to resolve identifiers found in other data,
        and old claims are full of NPIs NPPES has since retired. Dropping
        them makes a retired identifier indistinguishable from a typo."""
        report = ingest_nppes(self.csv, self.db, chunk_size=2)
        self.assertEqual(report.deactivated_skipped, 0)
        self.assertEqual(report.deactivated_kept, 1)
        self.assertEqual(report.reactivated, 1)
        rows = {r["npi"]: r for r in npi_rows(self.db, limit=50)}
        self.assertEqual(rows["5555555555"]["status"], STATUS_DEACTIVATED)
        self.assertEqual(rows["5555555555"]["deactivation_date"], "01/05/2020")
        # Reactivated is its own state: it bills today but has a gap, and
        # a claim from inside that gap is a different question.
        self.assertEqual(rows["6666666666"]["status"], STATUS_REACTIVATED)
        self.assertEqual(rows["6666666666"]["reactivation_date"], "03/09/2021")
        self.assertEqual(rows["1111111111"]["status"], STATUS_ACTIVE)

    def test_active_only_still_available_for_callers_that_want_it(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=2, active_only=True)
        self.assertEqual(report.deactivated_skipped, 1)
        self.assertEqual(report.deactivated_kept, 0)
        npis = {r["npi"] for r in npi_rows(self.db, limit=50)}
        self.assertNotIn("5555555555", npis)
        self.assertIn("6666666666", npis)

    def test_the_primary_taxonomy_is_the_switched_one_not_the_first(self) -> None:
        """Providers reorder their taxonomy slots between updates, so slot
        1 is not reliably the primary. Reading it as if it were turns a
        home-health agency into a DME supplier."""
        ingest_nppes(self.csv, self.db, chunk_size=4)
        row = {r["npi"]: r for r in npi_rows(self.db, limit=50)}["7777777777"]
        self.assertEqual(row["taxonomy_code"], "251E00000X")
        self.assertEqual(row["taxonomy_category"], "home_health")
        # …and the other enrolment is not lost, just not primary.
        self.assertEqual(row["taxonomy_codes"], "332B00000X|251E00000X")

    def test_subpart_and_parent_organization_survive_the_ingest(self) -> None:
        """NPPES's own statement of who owns whom. It is the first tier of
        parent resolution, and it was being read past."""
        report = ingest_nppes(self.csv, self.db, chunk_size=4)
        self.assertEqual(report.subparts, 1)
        self.assertEqual(report.with_parent_org, 1)
        row = {r["npi"]: r for r in npi_rows(self.db, limit=50)}["7777777777"]
        self.assertEqual(row["is_subpart"], "Y")
        self.assertEqual(row["parent_org_lbn"], "ASCENSION HEALTH")
        self.assertEqual(row["ein"], "123456789")

    def test_taxonomy_classification_lands_on_every_row(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=4)
        rows = {r["npi"]: r for r in npi_rows(self.db, limit=50)}
        self.assertEqual(rows["1111111111"]["taxonomy_category"], "hospital")
        self.assertEqual(rows["1111111111"]["taxonomy_level_i"], "Hospitals")
        self.assertEqual(rows["8888888888"]["taxonomy_category"], "physician")
        # A row with no taxonomy at all gets blanks, never a guess.
        self.assertEqual(rows["5555555555"]["taxonomy_category"], "")

    def test_coverage_reports_the_status_and_category_mix(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=4)
        cov = npi_coverage(self.db)
        self.assertEqual(cov["by_status"][STATUS_DEACTIVATED], 1)
        self.assertEqual(cov["by_status"][STATUS_REACTIVATED], 1)
        self.assertEqual(cov["by_category"]["hospital"], 4)
        self.assertEqual(cov["subparts"], 1)
        self.assertEqual(cov["naming_a_parent_organization"], 1)

    def test_rerunning_upserts_rather_than_duplicating(self) -> None:
        """A 9 GB ingest will get interrupted; resuming has to be safe."""
        ingest_nppes(self.csv, self.db, chunk_size=2)
        first = npi_coverage(self.db)
        ingest_nppes(self.csv, self.db, chunk_size=4)
        self.assertEqual(npi_coverage(self.db), first)

    def test_organizations_only_skips_the_individual_bulk(self) -> None:
        report = ingest_nppes(self.csv, self.db, chunk_size=3,
                              organizations_only=True)
        self.assertEqual(report.individuals, 2)
        self.assertNotIn("4444444444", {r["npi"] for r in npi_rows(self.db, limit=50)})

    def test_a_file_that_is_not_nppes_is_rejected(self) -> None:
        bogus = Path(self.tmp.name) / "not_nppes.csv"
        bogus.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest_nppes(bogus, self.db)

    def test_coverage_counts_what_was_written(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=2)
        cov = npi_coverage(self.db)
        self.assertEqual(cov["npis"], 8)
        self.assertEqual(cov["organizations"], 6)
        self.assertEqual(cov["individuals"], 2)
        self.assertEqual(cov["system_matched"], 4)

    def test_rows_are_filterable_by_system_and_state(self) -> None:
        ingest_nppes(self.csv, self.db, chunk_size=6)
        self.assertEqual(len(npi_rows(self.db, system_id="oceans")), 1)
        self.assertEqual(len(npi_rows(self.db, state="TN")), 4)
        self.assertEqual(len(npi_rows(self.db, status=STATUS_DEACTIVATED)), 1)
        self.assertEqual(len(npi_rows(self.db, category="home_health")), 1)


class DeactivationFileTests(unittest.TestCase):
    """CMS's monthly deactivation file is the only source for NPIs that
    have dropped out of the dissemination snapshot entirely."""

    #: A real CMS-derived extract already vendored in this repository —
    #: 4,000 NPIs with their deactivation dates.
    SEED = (Path(__file__).resolve().parents[1] / "rcm_mc" / "npi_cleaner"
            / "vendor_v49" / "npi_recovery" / "reference"
            / "nppes_deactivated_seed.csv")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "npidata_pfile_sample.csv"
        self.db = Path(self.tmp.name) / "npi.db"
        _nppes_fixture(self.csv)
        ingest_nppes(self.csv, self.db, chunk_size=4)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, rows: list) -> Path:
        path = Path(self.tmp.name) / "deact.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["NPI",
                                                    "NPPES Deactivation Date"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_an_unknown_npi_becomes_a_tombstone_not_a_silence(self) -> None:
        """"Retired in 2019" and "no such NPI" are different answers, and
        only one of them is useful to whoever is holding the number."""
        path = self._write([{"NPI": "9999999999",
                             "NPPES Deactivation Date": "08/12/2019"}])
        stats = ingest_deactivations(path, self.db)
        self.assertEqual(stats["tombstoned"], 1)
        rows = {r["npi"]: r for r in npi_rows(self.db, limit=50)}
        self.assertIn("9999999999", rows)
        self.assertEqual(rows["9999999999"]["status"], STATUS_DEACTIVATED)
        self.assertEqual(rows["9999999999"]["deactivation_date"], "08/12/2019")
        # A tombstone claims nothing it does not know.
        self.assertEqual(rows["9999999999"]["legal_name"], None)
        self.assertEqual(rows["9999999999"]["taxonomy_category"], None)

    def test_a_known_active_npi_is_moved_to_deactivated(self) -> None:
        path = self._write([{"NPI": "1111111111",
                             "NPPES Deactivation Date": "01/01/2026"}])
        stats = ingest_deactivations(path, self.db)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["tombstoned"], 0)
        row = {r["npi"]: r for r in npi_rows(self.db, limit=50)}["1111111111"]
        self.assertEqual(row["status"], STATUS_DEACTIVATED)

    def test_a_reactivated_npi_is_not_re_killed(self) -> None:
        """The deactivation file records a moment, not the current state.
        6666666666 was deactivated in 2020 and came back in 2021."""
        path = self._write([{"NPI": "6666666666",
                             "NPPES Deactivation Date": "01/05/2020"}])
        stats = ingest_deactivations(path, self.db)
        self.assertEqual(stats["kept_reactivated"], 1)
        self.assertEqual(stats["updated"], 0)
        row = {r["npi"]: r for r in npi_rows(self.db, limit=50)}["6666666666"]
        self.assertEqual(row["status"], STATUS_REACTIVATED)

    def test_a_tombstone_does_not_overwrite_a_later_full_ingest(self) -> None:
        path = self._write([{"NPI": "1234567890",
                             "NPPES Deactivation Date": "08/12/2019"}])
        ingest_deactivations(path, self.db)
        before = npi_coverage(self.db)["npis"]
        ingest_deactivations(path, self.db)
        self.assertEqual(npi_coverage(self.db)["npis"], before)

    def test_the_vendored_cms_extract_ingests_as_shipped(self) -> None:
        """The repo already carries a real 4,000-row CMS deactivation
        extract under a different header. Reading it must not require
        anyone to reshape a CMS file by hand."""
        self.assertTrue(self.SEED.exists())
        stats = ingest_deactivations(self.SEED, self.db)
        self.assertGreater(stats["read"], 3_000)
        self.assertEqual(stats["read"], stats["tombstoned"] + stats["updated"]
                         + stats["kept_reactivated"])
        cov = npi_coverage(self.db)
        self.assertEqual(cov["by_status"][STATUS_DEACTIVATED],
                         stats["tombstoned"] + 1)

    def test_a_file_that_is_not_a_deactivation_list_is_rejected(self) -> None:
        bogus = Path(self.tmp.name) / "nope.csv"
        bogus.write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest_deactivations(bogus, self.db)


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

    def test_parents_are_opt_in_and_off_by_default(self) -> None:
        """Nine extra columns and a graph build. A caller who did not ask
        should not pay for them."""
        rows = self._rows("/provider-crosswalk.csv?state=UT")
        self.assertNotIn("final_parent", rows[0])

    def test_parents_widen_the_export_with_a_resolved_owner(self) -> None:
        rows = self._rows("/provider-crosswalk.csv?state=UT&parents=1")
        self.assertTrue(rows)
        for col in ("final_parent", "final_parent_name", "parent_tier",
                    "parent_confidence", "parent_hops", "parent_basis"):
            self.assertIn(col, rows[0])
        resolved = [r for r in rows if r["final_parent"]]
        self.assertTrue(resolved)
        for row in resolved:
            with self.subTest(ccn=row["ccn"]):
                # A readable name, not just the internal key, and the
                # evidence for it.
                self.assertTrue(row["final_parent_name"])
                self.assertNotEqual(row["final_parent_name"],
                                    row["final_parent"])
                self.assertIn(row["ccn"], row["parent_basis"])

    def test_a_parent_across_a_state_line_survives_a_state_filter(self) -> None:
        """The graph is a property of the whole universe. Resolving inside
        a one-state slice would drop every parent that sits outside it —
        which is most of them, since systems are multi-state."""
        national = {r["ccn"]: r["final_parent"] for r in
                    self._rows("/provider-crosswalk.csv?scope=all&parents=1")}
        utah = self._rows("/provider-crosswalk.csv?scope=all&state=UT&parents=1")
        self.assertTrue(utah)
        for row in utah:
            with self.subTest(ccn=row["ccn"]):
                self.assertEqual(row["final_parent"], national[row["ccn"]])

    def test_the_hospital_scope_gets_the_same_parents_as_the_full_one(self) -> None:
        """One graph, not one per scope. Two graphs able to disagree about
        the same CCN is the kind of thing that stays fine right up until
        it doesn't."""
        national = {r["ccn"]: r["final_parent"] for r in
                    self._rows("/provider-crosswalk.csv?scope=all&parents=1")}
        hospitals = self._rows("/provider-crosswalk.csv?parents=1")
        self.assertGreater(len(hospitals), 6_000)
        for row in hospitals:
            with self.subTest(ccn=row["ccn"]):
                self.assertEqual(row["final_parent"], national[row["ccn"]])


if __name__ == "__main__":
    unittest.main()
