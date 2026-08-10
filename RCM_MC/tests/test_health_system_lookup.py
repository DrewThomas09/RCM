"""Health-system master mapping — matcher, rollup, and the lookup page.

The mapping's whole value is that a hospital count is trustworthy, so
the assertions here are mostly about *precision*: a brand must not leak
across systems or states. Two regressions are pinned explicitly because
both shipped in the first cut of the matcher:

  1. ``str.startswith`` matching pulled CHINLE / CHINESE HOSPITAL /
     CHINO VALLEY and five children's hospitals into CommonSpirit off
     the ``CHI`` brand — short abbreviations need a trailing boundary.
  2. A bare ``^TRINITY`` pattern claimed UnityPoint's Quad-Cities
     hospitals (and an unrelated CAH in California) for Trinity Health.
"""
from __future__ import annotations

import csv
import html as _html
import io
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path

import pandas as pd

from rcm_mc.data.cms_facility_names import cms_name, load_cms_facilities
from rcm_mc.data.health_systems import (
    ACUTE_REGISTRY,
    CCN_OVERRIDES,
    CHAIN_ALIASES,
    POST_ACUTE_REGISTRY,
    STATUS_ACTIVE,
    STATUS_CERTIFIED,
    STATUS_DORMANT,
    STATUS_STOPPED,
    SYSTEM_REGISTRY,
    UNMAPPED_ID,
    assign_all,
    assign_post_acute,
    assign_systems,
    build_system_map,
    candidate_clusters,
    concentration_ranking,
    dead_patterns,
    get_system,
    get_system_map,
    export_mapping,
    find_hospitals,
    hhi_band,
    inactive_facilities,
    leading_states,
    state_concentration,
    match_system,
    normalize_name,
    registry_size,
    system_hospitals,
)
from rcm_mc.ui.data_public.health_system_lookup_page import (
    render_health_system_lookup,
)


def _frame(rows):
    """Minimal HCRIS-shaped frame — the columns the mapper reads."""
    return pd.DataFrame([
        {
            "ccn": ccn, "name": name, "city": "Somewhere", "state": state,
            "beds": beds, "net_patient_revenue": npr,
        }
        for ccn, name, state, beds, npr in rows
    ])


class NormalizationTests(unittest.TestCase):
    def test_saint_variants_fold_together(self) -> None:
        for raw in ("ST. MARY'S HOSPITAL", "ST MARYS HOSPITAL",
                    "SAINT MARYS HOSPITAL"):
            self.assertEqual(normalize_name(raw), "SAINT MARYS HOSPITAL")

    def test_amendment_markers_are_stripped(self) -> None:
        """Regression: HCRIS files amended reports under names carrying the
        amendment marker, which silently defeated every anchored pattern —
        HCA's Lakeview and Centerpoint were unmapped purely because of it."""
        for raw in ("AMEND #1 LAKEVIEW HOSPITAL", "AMEND 1 LAKEVIEW HOSPITAL",
                    "AMEND #2 LAKEVIEW HOSPITAL"):
            self.assertEqual(normalize_name(raw), "LAKEVIEW HOSPITAL")
        self.assertEqual(normalize_name("LOUISIANA BEHAVIORAL HEALTH AMEND #1"),
                         "LOUISIANA BEHAVIORAL HEALTH")
        # A real word starting with AMEND is untouched.
        self.assertEqual(normalize_name("AMENDED CARE HOSPITAL"),
                         "AMENDED CARE HOSPITAL")

    def test_amended_filings_reach_their_system(self) -> None:
        self.assertEqual(match_system("AMEND #1 LAKEVIEW HOSPITAL", "UT")[0].system_id,
                         "hca")
        self.assertEqual(
            match_system("AMEND #2 RESEARCH MEDICAL CENTER", "MO")[0].system_id, "hca")

    def test_ampersand_becomes_and(self) -> None:
        self.assertEqual(normalize_name("BAYLOR S&W IRVING"), "BAYLOR S AND W IRVING")


class MatcherPrecisionTests(unittest.TestCase):
    def test_abbreviation_needs_a_word_boundary(self) -> None:
        """Regression: '^CHI ' must not match CHINLE / CHINESE / CHILDRENS."""
        for name, state in (("CHINLE COMPREHENSIVE CARE FACILITY", "AZ"),
                            ("CHINESE HOSPITAL", "CA"),
                            ("CHINO VALLEY MEDICAL CENTER", "CA"),
                            ("CHILDRENS HOSPITAL LOS ANGELES", "CA"),
                            ("CHICOT MEMORIAL MEDICAL CENTER", "AR")):
            sysdef, _ = match_system(name, state)
            got = sysdef.system_id if sysdef else None
            self.assertNotEqual(got, "commonspirit", f"{name} leaked into CommonSpirit")

    def test_chi_brand_still_matches(self) -> None:
        sysdef, pattern = match_system("CHI ST. VINCENT HOT SPRINGS", "AR")
        self.assertIsNotNone(sysdef)
        self.assertEqual(sysdef.system_id, "commonspirit")
        self.assertEqual(pattern, "^CHI ")

    def test_trinity_brand_is_not_claimed_wholesale(self) -> None:
        """Regression: UnityPoint's Trinity hospitals are not Trinity Health."""
        sysdef, _ = match_system("TRINITY ROCK ISLAND", "IL")
        self.assertIsNotNone(sysdef)
        self.assertEqual(sysdef.system_id, "unitypoint")
        sysdef, _ = match_system("TRINITY HOSPITAL", "CA")
        self.assertIsNone(sysdef)
        sysdef, _ = match_system("TRINITY HEALTH ANN ARBOR", "MI")
        self.assertEqual(sysdef.system_id, "trinity")

    def test_state_scope_keeps_overloaded_brands_apart(self) -> None:
        """MERCY names at least six unrelated owners — the scope is load-bearing."""
        mo, _ = match_system("MERCY HOSPITAL JOPLIN", "MO")
        oh, _ = match_system("MERCY HEALTH WEST HOSPITAL", "OH")
        self.assertEqual(mo.system_id, "mercy_mo")
        self.assertEqual(oh.system_id, "bon_secours")
        # A Mercy outside either footprint stays unmapped rather than
        # being handed to whichever entry happens to sort first.
        far, _ = match_system("MERCY HOSPITAL", "ME")
        self.assertIsNone(far)

    def test_longest_pattern_wins(self) -> None:
        sysdef, pattern = match_system("BAPTIST MEMORIAL HOSPITAL TIPTON", "TN")
        self.assertEqual(sysdef.system_id, "baptist_memphis")
        self.assertEqual(pattern, "^BAPTIST MEMORIAL")

    def test_per_pattern_state_scope(self) -> None:
        """A state-scoped pattern keeps a national system as ONE row."""
        sysdef, _ = match_system("ALTA VIEW HOSPITAL", "UT")
        self.assertEqual(sysdef.system_id, "intermountain")
        # Same name, wrong state -> no claim.
        self.assertIsNone(match_system("ALTA VIEW HOSPITAL", "FL")[0])

    def test_unbranded_name_is_unmapped(self) -> None:
        self.assertIsNone(match_system("CRENSHAW COMMUNITY HOSPITAL", "AL")[0])

    def test_leading_article_does_not_hide_a_brand(self) -> None:
        """HCRIS carries both "THE JOHNS HOPKINS HOSPITAL" and "JOHNS
        HOPKINS BAYVIEW"; an anchored pattern can only catch one unless
        the article is dropped."""
        self.assertEqual(normalize_name("THE JOHNS HOPKINS HOSPITAL"),
                         "JOHNS HOPKINS HOSPITAL")
        self.assertEqual(
            match_system("THE JOHNS HOPKINS HOSPITAL", "MD")[0].system_id, "hopkins")
        # "THE" inside the name is left alone.
        self.assertEqual(normalize_name("HOUSTON METHODIST THE WOODLANDS"),
                         "HOUSTON METHODIST THE WOODLANDS")

    def test_three_methodists_do_not_share_an_estate(self) -> None:
        """Regression: '^METHODIST' scoped to Texas swallowed Dallas,
        Houston and San Antonio — three unrelated organizations."""
        cases = {
            "METHODIST DALLAS MEDICAL CENTER": "methodist_dallas",
            "METHODIST CHARLTON MEDICAL CENTER": "methodist_dallas",
            "METHODIST SUGAR LAND HOSPITAL": "houston_methodist",
            "METHODIST WEST HOUSTON HOSPITAL": "houston_methodist",
            "SAN JACINTO METHODIST HOSPITAL": "houston_methodist",
            "METHODIST STONE OAK HOSPITAL": "methodist_san_antonio",
            "METHODIST HOSPITAL SOUTH": "methodist_san_antonio",
        }
        for name, expected in cases.items():
            sysdef, _ = match_system(name, "TX")
            self.assertIsNotNone(sysdef, name)
            self.assertEqual(sysdef.system_id, expected, name)

    def test_long_patterns_match_as_prefixes(self) -> None:
        """Regression: the trailing word boundary that stops CHI->CHINLE
        also killed '^BRIGHAM AND WOMEN' against BRIGHAM AND WOMENS —
        Mass General Brigham's second-largest hospital sat unmapped over
        an apostrophe. Long brand strings match as prefixes."""
        self.assertEqual(
            match_system("BRIGHAM AND WOMENS HOSPITAL", "MA")[0].system_id,
            "mass_general_brigham")

    def test_short_patterns_keep_their_boundary(self) -> None:
        """The relaxation must not reopen the CHI leak."""
        self.assertNotEqual(
            (match_system("CHINLE COMPREHENSIVE CARE FACILITY", "AZ")[0] or
             get_system("hca")).system_id, "commonspirit")
        self.assertIsNone(match_system("CHINESE HOSPITAL", "CA")[0])

    def test_the_prefix_index_finds_what_a_brute_force_scan_finds(self) -> None:
        """The index skips patterns that cannot match a name's first two
        characters. That is only safe because an anchored pattern
        compiles to ``^`` plus an escaped literal — if that ever stops
        being true, the index silently starts losing matches, and this is
        what catches it."""
        from rcm_mc.data.health_systems import (
            _EXCLUDE_INDEX, _STATE_PATTERNS, _UNSCOPED_PATTERNS, _Bucket)

        def brute(norm: str, state: str):
            scoped = _STATE_PATTERNS.get(state, _Bucket({}, ()))
            every = (tuple(e for v in scoped.by_prefix.values() for e in v)
                     + scoped.floating
                     + tuple(e for v in _UNSCOPED_PATTERNS.by_prefix.values() for e in v)
                     + _UNSCOPED_PATTERNS.floating)
            best, best_pattern, best_key = None, "", (-1, -1)
            for entry in every:
                key = (entry.specificity, 1 if entry.scope else 0)
                if key <= best_key or not entry.regex.search(norm):
                    continue
                excludes = _EXCLUDE_INDEX.get(entry.sysdef.system_id)
                if excludes and any(x.search(norm) for x in excludes):
                    continue
                best, best_pattern, best_key = entry.sysdef, entry.raw, key
            return best, best_pattern

        universe = assign_all()
        sample = universe.iloc[::37]  # ~1,300 rows spanning every class
        self.assertGreater(len(sample), 1000)
        for name, state in zip(sample["name"], sample["state"], strict=True):
            norm = normalize_name(name)
            if not norm:
                continue
            st = str(state).upper().strip()
            indexed = match_system(name, state)
            expected = brute(norm, st)
            self.assertEqual(
                (indexed[0].system_id if indexed[0] else None, indexed[1]),
                (expected[0].system_id if expected[0] else None, expected[1]),
                f"{name} ({state})")

    def test_a_state_scope_keeps_two_uh_apart(self) -> None:
        """University Hospitals of Cleveland files eleven hospitals as
        "UH <place>". University Hospital in Newark files as
        "UH - UNIVERSITY HOSPITAL" and is a different organization."""
        self.assertEqual(match_system("UH CLEVELAND MEDICAL CENTER", "OH")[0]
                         .system_id, "uh_ohio")
        self.assertEqual(match_system("UNIVERSITY HOSPITALS AVON REHAB", "OH")[0]
                         .system_id, "uh_ohio")
        self.assertIsNone(match_system("UH - UNIVERSITY HOSPITAL", "NJ")[0])

    def test_a_brand_that_is_also_a_place_name_stays_scoped(self) -> None:
        """Whittier CA and Whittier MA; Sage Memorial AZ and Sage Rehab LA.
        A national pattern would merge four unrelated hospitals."""
        self.assertEqual(match_system("WHITTIER HOSPITAL BRADFORD", "MA")[0]
                         .system_id, "whittier_ma")
        self.assertIsNone(match_system("WHITTIER HOSPITAL MEDICAL CENTER", "CA")[0])
        self.assertEqual(match_system("SAGE REHAB HOSPITAL", "LA")[0]
                         .system_id, "sage_la")
        self.assertIsNone(match_system("SAGE MEMORIAL HOSPITAL", "AZ")[0])
        self.assertIsNone(match_system("SAGE WEST HEALTH CARE", "WY")[0])

    def test_dead_pattern_scan_finds_typos(self) -> None:
        """The scan is the maintenance loop for the registry: patterns
        that match nothing are usually typos. Some are deliberate — house
        brands carried early for a future refresh — so this pins the
        specific ones that must stay alive rather than demanding zero."""
        dead = set(dead_patterns())
        for must_match in (("novant", "NC:^FORSYTH MEMORIAL"),
                           ("mass_general_brigham", "^BRIGHAM AND WOMEN"),
                           ("hopkins", "^JOHNS HOPKINS"),
                           ("intermountain", "UT:^UTAH VALLEY HOSPITAL"),
                           ("oceans", "^OCEANS")):
            self.assertNotIn(must_match, dead, f"{must_match} matches nothing")

    def test_every_registry_entry_is_reachable(self) -> None:
        """No dead entries: each system matches at least one real provider.

        Scoped to everything the registry can reach, not the hospital
        rollup. DaVita holds 2,800 CCNs and not one hospital; Global
        Medical Response holds 648 NPIs and not one CCN. Measuring
        reachability against hospitals alone would call both dead."""
        from rcm_mc.data.npi_registry import assign_npi_registry

        live = set(assign_all()["system_id"]) | set(
            assign_npi_registry()["system_id"])
        dead = sorted(s.system_id for s in SYSTEM_REGISTRY if s.system_id not in live)
        self.assertEqual(dead, [], f"registry entries that match nothing: {dead}")

    def test_the_acute_registry_stays_reachable_from_hospitals_alone(self) -> None:
        """The post-acute entries must not paper over an acute one going
        dead. Every entry written for HCRIS still has to match in HCRIS."""
        live = {r.system_id for r in get_system_map().systems}
        dead = sorted(s.system_id for s in ACUTE_REGISTRY if s.system_id not in live)
        self.assertEqual(dead, [], f"acute entries that match no hospital: {dead}")


class AssignmentTests(unittest.TestCase):
    def test_columns_and_behavioral_flag(self) -> None:
        df = _frame([
            ("012345", "OCEANS BEHAVIORAL HOSPITAL OF ABILENE", "TX", 24, 1e7),
            ("012346", "ENCOMPASS HEALTH REHAB OF DALLAS", "TX", 40, 2e7),
            ("012347", "SMALLTOWN COUNTY HOSPITAL", "TX", 12, 5e6),
        ])
        out = assign_systems(df)
        for col in ("system_id", "system_name", "system_kind", "system_focus",
                    "system_match", "facility_type", "facility_type_label",
                    "is_behavioral"):
            self.assertIn(col, out.columns)
        self.assertEqual(list(out["system_id"]), ["oceans", "encompass", UNMAPPED_ID])
        self.assertEqual(list(out["is_behavioral"]), [True, False, False])
        # No fiscal_year column to age against -> everything reads operating.
        self.assertTrue(out["is_operating"].all())

    def test_behavioral_detected_by_name_outside_the_psych_ccn_range(self) -> None:
        df = _frame([("010001", "SUN BEHAVIORAL HEALTH KENTUCKY", "KY", 80, 1e7)])
        out = assign_systems(df)
        self.assertTrue(bool(out["is_behavioral"].iloc[0]))

    def test_empty_frame_is_tolerated(self) -> None:
        out = assign_systems(pd.DataFrame(
            columns=["ccn", "name", "state", "beds", "net_patient_revenue"]))
        self.assertTrue(out.empty)
        self.assertIn("system_id", out.columns)

    def test_returned_frame_is_a_copy(self) -> None:
        """The cached universe must not be mutable through a caller's frame."""
        first = assign_systems()
        first.loc[first.index[0], "system_name"] = "MUTATED"
        second = assign_systems()
        self.assertNotEqual(second["system_name"].iloc[0], "MUTATED")


class CcnOverrideTests(unittest.TestCase):
    """The escape hatch for facilities a name can never resolve."""

    def test_overrides_point_at_real_systems_and_real_facilities(self) -> None:
        """Checked against the whole register, not the hospital slice.

        Overrides used to be honoured only in the acute universe, so a
        hand assignment on a home health agency silently did nothing.
        Now that both universes consult the table, an entry is valid if
        the CCN exists anywhere in the register.
        """
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        universe = set(get_crosswalk(scope=SCOPE_ALL)["ccn"].astype(str))
        for ccn, system_id in CCN_OVERRIDES.items():
            self.assertIsNotNone(get_system(system_id), f"{ccn} -> {system_id}")
            self.assertIn(ccn, universe, f"{ccn} is not in the universe")

    def test_override_wins_over_the_name_match(self) -> None:
        """Houston Methodist's flagship files as "THE METHODIST HOSPITAL"
        and San Antonio's as "METHODIST HOSPITAL" — the same string once
        normalized, in the same state."""
        assigned = assign_systems().set_index("ccn")
        self.assertEqual(assigned.loc["450358", "system_id"], "houston_methodist")
        self.assertEqual(assigned.loc["450388", "system_id"], "methodist_san_antonio")
        self.assertEqual(normalize_name("THE METHODIST HOSPITAL"),
                         normalize_name("METHODIST HOSPITAL"))

    def test_override_is_visible_as_its_own_match_basis(self) -> None:
        """An asserted assignment must not read like a derived one."""
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        assigned = get_crosswalk(scope=SCOPE_ALL).set_index(
            get_crosswalk(scope=SCOPE_ALL)["ccn"].astype(str))
        for ccn in CCN_OVERRIDES:
            self.assertEqual(assigned.loc[ccn, "system_match"],
                             f"ccn override {ccn}")

    def test_an_override_reaches_a_post_acute_facility(self) -> None:
        """Baptist Home Health Care in Pensacola belongs to Baptist
        Health Care, not to Baptist Health South Florida three hundred
        miles away. Before the post-acute path consulted the table, the
        override for it did nothing at all."""
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        register = get_crosswalk(scope=SCOPE_ALL)
        row = register[register["ccn"].astype(str) == "107006"].iloc[0]
        self.assertEqual(row["provider_class"], "hha")
        self.assertEqual(row["system_id"], "baptist_pensacola")
        self.assertEqual(row["system_match"], "ccn override 107006")

    def test_truncated_names_are_reachable_only_by_override(self) -> None:
        """HCRIS cuts at ~36 chars: 'Hospital of the University of
        Pennsylvania' files as 'HOSPITAL OF THE UNIV OF PENNA'."""
        self.assertIsNone(match_system("HOSPITAL OF THE UNIV OF PENNA", "PA")[0])
        assigned = assign_systems().set_index("ccn")
        self.assertEqual(assigned.loc["390111", "system_id"], "penn_medicine")


class CmsNameTierTests(unittest.TestCase):
    """The second name: Care Compare's, when the cost report's is too short.

    HCRIS truncates at ~36 characters and abbreviates on top of that.
    No registry pattern written from a real brand can reach
    "BHMC-CONWAY" or "PROV. KODIAK ISLAND MEDICAL CENT". Care Compare
    publishes the untruncated name for the same CCN, so the matcher
    gets a second attempt before a facility is called unmapped.
    """

    def test_the_snapshot_loaded(self) -> None:
        facilities = load_cms_facilities()
        self.assertGreater(len(facilities), 5000)
        # Every key is a CCN and every row keeps a name to match on.
        self.assertTrue(all(k and k == k.strip() for k in facilities))
        self.assertGreater(sum(1 for f in facilities.values() if f.name),
                           len(facilities) - 10)

    def test_a_truncated_cost_report_name_resolves_on_the_cms_name(self) -> None:
        """Providence Kodiak Island: the cost report ran out of characters
        mid-word, so the brand is only legible in the CMS name."""
        self.assertIsNone(match_system("PROV. KODIAK ISLAND MEDICAL CENT", "AK")[0])
        self.assertIn("PROVIDENCE", cms_name("021306").upper())
        assigned = assign_systems().set_index("ccn")
        self.assertEqual(assigned.loc["021306", "system_id"], "providence")

    def test_the_second_name_is_visible_as_its_own_match_basis(self) -> None:
        """A row matched on a different string than the one displayed has
        to say so, or the roster looks like it matched on nothing."""
        assigned = assign_systems()
        via_cms = assigned[assigned["system_match"].astype(str)
                           .str.startswith("cms name: ")]
        self.assertGreater(len(via_cms), 300)
        for basis in via_cms["system_match"].unique():
            self.assertTrue(basis[len("cms name: "):].strip(), basis)

    def test_the_tier_only_fires_where_the_cost_report_name_failed(self) -> None:
        """Second chance, not second opinion — a facility the cost-report
        name already resolved must never be re-decided by CMS's string."""
        assigned = assign_systems()
        via_cms = assigned[assigned["system_match"].astype(str)
                           .str.startswith("cms name: ")]
        for name, state in zip(via_cms["name"], via_cms["state"], strict=True):
            self.assertIsNone(match_system(str(name), str(state))[0],
                              f"{name} ({state}) already matched on its own name")

    def test_an_override_still_outranks_the_cms_name(self) -> None:
        """Overrides exist because a name — either name — is unusable."""
        assigned = assign_systems().set_index("ccn")
        for ccn in CCN_OVERRIDES:
            if ccn not in assigned.index:
                continue          # post-acute; covered in CcnOverrideTests
            self.assertEqual(assigned.loc[ccn, "system_match"],
                             f"ccn override {ccn}")

    def test_the_tier_pays_for_itself_in_coverage(self) -> None:
        assigned = assign_systems()
        operating = assigned[assigned["is_operating"]]
        mapped = int((operating["system_id"] != UNMAPPED_ID).sum())
        # 1,987 operating facilities mapped on the cost-report name alone.
        self.assertGreater(mapped, 2300)

    def test_a_missing_snapshot_does_not_take_the_mapping_down(self) -> None:
        """An optional reference file must degrade, never raise."""
        import rcm_mc.data.cms_facility_names as cfn

        original = cfn._CACHE
        try:
            cfn._CACHE = Path(tempfile.gettempdir()) / "definitely-not-here.json.gz"
            cfn._clear_cache()
            self.assertEqual(cfn.load_cms_facilities(), {})
            self.assertEqual(cfn.cms_name("021306"), "")
            self.assertIsNone(cfn.cms_facility("021306"))
        finally:
            cfn._CACHE = original
            cfn._clear_cache()

    def test_ownership_flags_partition_the_classes(self) -> None:
        facilities = load_cms_facilities()
        flagged = [f for f in facilities.values() if f.ownership]
        self.assertGreater(len(flagged), 5000)
        for facility in flagged:
            classes = (facility.is_government, facility.is_for_profit,
                       facility.is_nonprofit)
            self.assertLessEqual(sum(classes), 1, facility.ownership)


class PostAcuteUniverseTests(unittest.TestCase):
    """The 42,387 CCNs that are not hospitals.

    A hospital-only mapping undercounts a health system twice: it misses
    the dialysis stations, nursing homes, agencies and hospices a system
    holds, and it misses the operators whose entire estate is those CCNs.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.post_acute = assign_post_acute()
        cls.everything = assign_all()

    def test_the_post_acute_universe_dwarfs_the_hospital_one(self) -> None:
        self.assertGreater(len(self.post_acute), 40000)
        self.assertGreater(len(self.everything), 48000)
        self.assertEqual(len(self.everything),
                         self.everything["ccn"].nunique())

    def test_hospital_ccns_are_not_double_counted(self) -> None:
        """An IRF or LTCH that files its own cost report is in both files.
        The HCRIS row wins — it carries beds, revenue and a filing
        history the Compare files have no equivalent for."""
        hospital_ccns = set(assign_systems()["ccn"].astype(str))
        overlap = hospital_ccns & set(self.post_acute["ccn"].astype(str))
        self.assertEqual(overlap, set())
        classes = set(self.everything["provider_class"])
        self.assertEqual(classes,
                         {"hospital", "snf", "hha", "hospice", "dialysis",
                          "irf", "ltch"})

    def test_the_published_chain_outranks_the_name_match(self) -> None:
        """CMS names the parent for 6,699 dialysis facilities. That is the
        operator's own answer; our reading of their signage is not."""
        via_chain = self.post_acute[
            self.post_acute["system_match"].astype(str).str.startswith("chain: ")]
        self.assertGreater(len(via_chain), 6000)
        self.assertTrue((via_chain["provider_class"] == "dialysis").all())
        self.assertTrue((via_chain["system_id"] != UNMAPPED_ID).all())

    def test_the_chain_column_reaches_facilities_no_name_could(self) -> None:
        """Northwest Kidney Centers files eleven facilities under place
        names. Only the chain column connects them."""
        nwk = self.post_acute[self.post_acute["system_id"] == "northwest_kidney"]
        self.assertGreater(len(nwk), 10)
        self.assertTrue(nwk["system_match"].str.startswith("chain: ").all())

    def test_the_big_post_acute_operators_land(self) -> None:
        counts = (self.everything[self.everything["system_id"] != UNMAPPED_ID]
                  .groupby("system_id").size())
        for system_id, floor in (("davita", 2500), ("fresenius", 2500),
                                 ("centerwell", 200), ("amedisys", 200),
                                 ("life_care_centers", 100)):
            self.assertGreater(int(counts.get(system_id, 0)), floor, system_id)

    def test_every_chain_alias_points_at_a_real_system(self) -> None:
        for chain, system_id in CHAIN_ALIASES.items():
            self.assertIsNotNone(get_system(system_id), f"{chain} -> {system_id}")
            self.assertEqual(chain, normalize_name(chain),
                             "alias keys are matched post-normalization")

    def test_an_acquired_brand_rolls_up_to_its_acquirer(self) -> None:
        """A rollup that lists an acquirer's brands as separate operators
        is not a rollup. Amedisys still runs Beacon Hospice and AseraCare
        under their own signage; Compassus files half its agencies as
        "Hospice Compassus"."""
        for name, state, system_id in (
            ("BEACON HOSPICE", "MA", "amedisys"),
            ("ASERACARE HOSPICE", "AL", "amedisys"),
            ("HOSPICE COMPASSUS OF NASHVILLE", "TN", "compassus"),
            ("NHC HOMECARE KNOXVILLE", "TN", "national_healthcare"),
        ):
            matched = match_system(name, state)[0]
            self.assertIsNotNone(matched, name)
            self.assertEqual(matched.system_id, system_id, name)

    def test_descriptions_and_place_names_are_left_unmapped(self) -> None:
        """The largest remaining clusters are the ones that must NOT
        become registry entries. "HOSPICE OF" spans 206 facilities in 40
        states and names no company."""
        for name, state in (("HOSPICE OF THE VALLEY", "AZ"),
                            ("COMMUNITY HOME HEALTH CARE", "NY"),
                            ("MOUNTAIN VIEW HEALTH AND REHABILITATION", "TN"),
                            ("VALLEY VIEW NURSING CENTER", "PA"),
                            ("ADVANCED HOME HEALTH SERVICES", "TX")):
            self.assertIsNone(match_system(name, state)[0], name)

    def test_three_brands_are_withheld_because_they_hit_a_hospital(self) -> None:
        """Genesis, Brookdale and Arbor read as national post-acute
        operators, and each collides with an unrelated acute hospital. A
        wrong parent is worse than no parent — nobody audits a mapping
        that looks complete."""
        for name, state in (("GENESIS HEALTHCARE SYSTEM", "OH"),
                            ("BROOKDALE HOSPITAL MEDICAL CENTER", "NY"),
                            ("ARBOR HEALTH MORTON HOSPITAL", "WA")):
            self.assertIsNone(match_system(name, state)[0], name)

    def test_post_acute_status_does_not_claim_a_check_that_never_ran(self) -> None:
        """The Compare files carry no termination date, so filing recency
        cannot be computed. Reusing "Active" would assert otherwise."""
        self.assertEqual(set(self.post_acute["facility_status"]), {STATUS_CERTIFIED})
        self.assertTrue(self.post_acute["is_operating"].all())
        self.assertNotIn(STATUS_ACTIVE, set(self.post_acute["facility_status"]))

    def test_post_acute_entries_do_not_leak_into_the_hospital_estate(self) -> None:
        """Adding fifty post-acute operators must not move one hospital."""
        hospitals = assign_systems()
        post_acute_ids = {s.system_id for s in POST_ACUTE_REGISTRY}
        # Encompass / Kindred / Select are acute entries that also reach
        # post-acute CCNs; nothing written FOR post-acute may claim a bed.
        claimed = hospitals[hospitals["system_id"].isin(post_acute_ids)]
        self.assertEqual(len(claimed), 0,
                         f"post-acute entries claimed hospitals: "
                         f"{list(claimed['name'])[:5]}")

    def test_empty_frame_is_tolerated(self) -> None:
        out = assign_post_acute(pd.DataFrame(
            columns=["ccn", "name", "state", "provider_class", "chain_name"]))
        self.assertTrue(out.empty)
        self.assertIn("system_id", out.columns)


class FacilityStatusTests(unittest.TestCase):
    """Closed hospitals must not be counted as operating ones."""

    def _aged(self):
        """A frame whose latest year is 2022, with one row per status."""
        rows = [
            ("010001", "ACTIVE GENERAL HOSPITAL", "AL", 2022, 100, 20000, 5e7),
            ("010002", "DORMANT REGIONAL HOSPITAL", "AL", 2021, 80, 15000, 4e7),
            ("010003", "CLOSED COUNTY HOSPITAL", "AL", 2020, 60, 12000, 3e7),
            ("010004", "DARK SHELL HOSPITAL", "AL", 2022, 0, 0, 0),
        ]
        return pd.DataFrame([
            {"ccn": c, "name": n, "city": "Town", "state": st,
             "fiscal_year": fy, "beds": b, "total_patient_days": d,
             "net_patient_revenue": r}
            for c, n, st, fy, b, d, r in rows
        ])

    def test_status_comes_from_filing_recency(self) -> None:
        out = assign_systems(self._aged())
        self.assertEqual(list(out["facility_status"]), [
            STATUS_ACTIVE, STATUS_DORMANT, STATUS_STOPPED, STATUS_ACTIVE])
        self.assertEqual(list(out["is_operating"]), [True, False, False, True])

    def test_zero_activity_is_a_flag_not_a_closure(self) -> None:
        """Regression: an earlier cut treated a zero-activity filing as
        closed, which dropped Mary Bridge Children's, Shriners and Texas
        Scottish Rite — all open hospitals that simply do not report beds,
        days or revenue the way a general acute hospital does."""
        out = assign_systems(self._aged())
        self.assertEqual(list(out["reports_no_activity"]),
                         [False, False, False, True])
        # The dark shell still filed currently, so it still counts.
        self.assertTrue(bool(out.iloc[3]["is_operating"]))

        real = assign_systems()
        for open_hospital in ("MARY BRIDGE CHILDRENS HOSPITAL",
                              "TEXAS SCOTTISH RITE HOSPITAL FOR CHI"):
            row = real[real["name"] == open_hospital]
            self.assertFalse(row.empty, open_hospital)
            self.assertTrue(bool(row.iloc[0]["is_operating"]), open_hospital)
            self.assertTrue(bool(row.iloc[0]["reports_no_activity"]), open_hospital)

    def test_only_operating_facilities_feed_the_counts(self) -> None:
        m = build_system_map(self._aged())
        self.assertEqual(m.total_hospitals, 2)
        self.assertEqual(m.inactive_hospitals, 2)
        self.assertEqual(m.universe_facilities, 4)
        self.assertEqual(m.zero_activity_hospitals, 1)
        # Beds follow the same rule — a closed hospital's last-reported
        # beds are the least real number in the frame.
        self.assertEqual(m.total_beds, 100)

    def test_status_is_relative_to_the_corpus_not_the_wall_clock(self) -> None:
        """An older extract must not read as a universe of closed hospitals."""
        old = self._aged()
        old["fiscal_year"] = old["fiscal_year"] - 6
        self.assertEqual(list(assign_systems(old)["facility_status"]),
                         list(assign_systems(self._aged())["facility_status"]))

    def test_system_counts_exclude_closed_facilities(self) -> None:
        df = _frame([
            ("012345", "OCEANS BEHAVIORAL HOSPITAL OF ABILENE", "TX", 24, 1e7),
            ("012346", "OCEANS BEHAVIORAL HOSPITAL OF KATY", "TX", 20, 8e6),
        ])
        df["fiscal_year"] = [2022, 2019]
        df["total_patient_days"] = [5000, 4000]
        rollup = build_system_map(df).systems[0]
        self.assertEqual(rollup.system_id, "oceans")
        self.assertEqual(rollup.hospitals, 1)
        self.assertEqual(rollup.inactive_hospitals, 1)
        self.assertEqual(rollup.total_facilities, 2)
        self.assertEqual(rollup.beds, 24)
        self.assertEqual(rollup.behavioral_hospitals, 1)

    def test_real_universe_has_a_plausible_closed_tail(self) -> None:
        m = get_system_map()
        self.assertGreater(m.inactive_hospitals, 50)
        # Closures are a tail, not the bulk of the universe.
        self.assertLess(m.inactive_hospitals, m.total_hospitals * 0.1)
        self.assertEqual(m.status_total(STATUS_ACTIVE), m.total_hospitals)
        self.assertEqual(
            m.status_total(STATUS_DORMANT) + m.status_total(STATUS_STOPPED),
            m.inactive_hospitals)

    def test_last_active_year_separates_dark_from_never_reported(self) -> None:
        real = assign_systems()
        dark = real[real["reports_no_activity"]]
        self.assertFalse(dark.empty)
        # Both kinds exist: some ran and went quiet, some never reported.
        self.assertGreater(int(dark["last_active_fiscal_year"].notna().sum()), 0)
        self.assertGreater(int(dark["last_active_fiscal_year"].isna().sum()), 0)

    def test_inactive_list_holds_only_non_filers(self) -> None:
        rows = inactive_facilities()
        self.assertEqual(set(rows["facility_status"]),
                         {STATUS_DORMANT, STATUS_STOPPED})

    def test_inactive_facilities_are_listed_and_ordered_by_signal(self) -> None:
        rows = inactive_facilities()
        self.assertEqual(len(rows), get_system_map().inactive_hospitals)
        self.assertFalse(rows["is_operating"].any())
        # Stopped-filing first: the strongest closure signal leads.
        self.assertEqual(rows.iloc[0]["facility_status"], STATUS_STOPPED)
        stopped = inactive_facilities(status=STATUS_STOPPED)
        self.assertEqual(set(stopped["facility_status"]), {STATUS_STOPPED})
        self.assertEqual(len(stopped),
                         get_system_map().status_total(STATUS_STOPPED))

    def test_known_closures_are_flagged(self) -> None:
        """Spot-check against hospitals that really did close."""
        rows = inactive_facilities()
        names = " | ".join(rows["name"].astype(str))
        for closed in ("MADERA COMMUNITY HOSPITAL", "OLYMPIA MEDICAL CENTER",
                       "GALESBURG COTTAGE HOSPITAL", "PICKENS COUNTY MEDICAL"):
            self.assertIn(closed, names)


class RollupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = get_system_map()

    def test_totals_reconcile(self) -> None:
        """Operating counts reconcile, and so does the whole extract."""
        mapped = sum(s.hospitals for s in self.m.systems)
        self.assertEqual(mapped, self.m.mapped_hospitals)
        self.assertEqual(mapped + self.m.unmapped.hospitals, self.m.total_hospitals)
        inactive = sum(s.inactive_hospitals for s in self.m.systems)
        self.assertEqual(inactive + self.m.unmapped.inactive_hospitals,
                         self.m.inactive_hospitals)
        self.assertEqual(self.m.total_hospitals + self.m.inactive_hospitals,
                         self.m.universe_facilities)
        self.assertEqual(sum(self.m.status_totals.values()),
                         self.m.universe_facilities)

    def test_per_system_type_counts_sum_to_its_hospital_count(self) -> None:
        for s in self.m.systems:
            self.assertEqual(sum(s.type_counts.values()), s.hospitals, s.system_name)

    def test_behavioral_never_exceeds_hospital_count(self) -> None:
        for s in self.m.systems:
            self.assertLessEqual(s.behavioral_hospitals, s.hospitals, s.system_name)
            self.assertLessEqual(s.behavioral_share, 1.0)

    def test_sorted_by_hospital_count(self) -> None:
        counts = [s.hospitals for s in self.m.systems]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_registry_carries_a_meaningful_universe(self) -> None:
        self.assertGreater(registry_size(), 100)
        self.assertGreater(self.m.system_count, 100)
        self.assertGreater(self.m.mapped_hospitals, 1000)
        self.assertGreater(self.m.total_behavioral, 500)

    def test_pure_play_behavioral_system_reads_as_behavioral(self) -> None:
        oceans = next(s for s in self.m.systems if s.system_id == "oceans")
        self.assertEqual(oceans.behavioral_hospitals, oceans.hospitals)
        self.assertEqual(oceans.focus, "Behavioral")

    def test_roster_matches_the_rollup_count(self) -> None:
        """The roster lists every CCN; only Active ones feed the estate."""
        top = self.m.systems[0]
        roster = system_hospitals(top.system_id)
        self.assertEqual(len(roster), top.total_facilities)
        self.assertEqual(int(roster["is_operating"].sum()), top.hospitals)
        # Roster is largest-first so the drill-down opens on what matters.
        beds = list(pd.to_numeric(roster["beds"], errors="coerce").fillna(0))
        self.assertEqual(beds, sorted(beds, reverse=True))

    def test_candidate_clusters_are_unmapped_only(self) -> None:
        assigned = assign_systems()
        unmapped_names = set(assigned[assigned["system_id"] == UNMAPPED_ID]["name"])
        for cluster in candidate_clusters(limit=10):
            self.assertGreaterEqual(cluster.hospitals, 2)
            for example in cluster.examples:
                self.assertIn(example, unmapped_names)

    def test_build_over_a_supplied_frame_bypasses_the_cache(self) -> None:
        df = _frame([
            ("012345", "ASCENSION SAINT VINCENT", "IN", 100, 5e8),
            ("012346", "ASCENSION VIA CHRISTI", "KS", 80, 3e8),
            ("012347", "UNRELATED COUNTY HOSPITAL", "IA", 10, 4e6),
        ])
        m = build_system_map(df)
        self.assertEqual(m.total_hospitals, 3)
        self.assertEqual(m.inactive_hospitals, 0)
        self.assertEqual(m.mapped_hospitals, 2)
        self.assertEqual(m.system_count, 1)
        self.assertEqual(m.systems[0].system_id, "ascension")
        self.assertEqual(m.systems[0].state_count, 2)
        self.assertEqual(m.unmapped.hospitals, 1)


class ReverseLookupTests(unittest.TestCase):
    """Hospital name / CCN in, system out — the other direction."""

    def test_exact_ccn_lookup(self) -> None:
        hits = find_hospitals("450087")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits.iloc[0]["system_id"], "hca")

    def test_ccn_lookup_tolerates_a_missing_leading_zero(self) -> None:
        padded = find_hospitals("010001")
        unpadded = find_hospitals("10001")
        self.assertEqual(len(padded), 1)
        self.assertEqual(list(padded["ccn"]), list(unpadded["ccn"]))

    def test_name_lookup_ranks_prefix_matches_first(self) -> None:
        hits = find_hospitals("oceans behavioral", limit=5)
        self.assertGreater(len(hits), 1)
        self.assertTrue(all(h == "Oceans Healthcare" for h in hits["system_name"]))

    def test_name_lookup_folds_punctuation(self) -> None:
        """'ST. MARY'S' and 'ST MARYS' are the same hospital name in HCRIS."""
        self.assertFalse(find_hospitals("st. mary's hospital").empty)

    def test_unmatched_and_empty_queries_return_nothing(self) -> None:
        self.assertTrue(find_hospitals("zzzz-no-such-hospital").empty)
        self.assertTrue(find_hospitals("").empty)
        self.assertTrue(find_hospitals("   ").empty)


class ExportTests(unittest.TestCase):
    def test_export_is_one_row_per_hospital(self) -> None:
        """The export ships closed facilities too — the status column is
        what makes it reconcile against the page rather than diverge."""
        frame = export_mapping()
        self.assertEqual(len(frame), get_system_map().universe_facilities)
        for col in ("ccn", "name", "state", "system_name", "facility_type_label",
                    "is_behavioral", "beds", "net_patient_revenue"):
            self.assertIn(col, frame.columns)

    def test_filters_are_facility_grained(self) -> None:
        """'Behavioral in TX' means behavioral facilities in TX, not every
        facility of every system that happens to run one."""
        frame = export_mapping(state="TX", ftype="behavioral")
        self.assertFalse(frame.empty)
        self.assertEqual(set(frame["state"]), {"TX"})
        self.assertEqual(set(frame["is_behavioral"]), {"Y"})

    def test_system_filter_matches_the_rollup(self) -> None:
        oceans = next(s for s in get_system_map().systems if s.system_id == "oceans")
        self.assertEqual(len(export_mapping(system_id="oceans")), oceans.hospitals)

    def test_unmapped_rows_carry_an_empty_system_id(self) -> None:
        frame = export_mapping()
        unmapped = frame[frame["system_name"] == "Independent / Unmapped"]
        self.assertFalse(unmapped.empty)
        self.assertEqual(set(unmapped["system_id"]), {""})


class ConcentrationTests(unittest.TestCase):
    """Bed-share concentration — the "who controls this market" read."""

    def _state(self):
        """One state: a 2-hospital system, a big independent, a small one."""
        rows = [
            ("450001", "ENCOMPASS HEALTH REHAB A", "ZZ", 2022, 100),
            ("450002", "ENCOMPASS HEALTH REHAB B", "ZZ", 2022, 100),
            ("450003", "BIG INDEPENDENT HOSPITAL", "ZZ", 2022, 700),
            ("450004", "SMALL INDEPENDENT HOSPITAL", "ZZ", 2022, 100),
        ]
        return pd.DataFrame([
            {"ccn": c, "name": n, "city": "Town", "state": st,
             "fiscal_year": fy, "beds": b, "total_patient_days": 1000,
             "net_patient_revenue": 1e7}
            for c, n, st, fy, b in rows
        ])

    def test_share_is_measured_on_beds_not_facility_count(self) -> None:
        c = state_concentration("ZZ", self._state())
        self.assertEqual(c.beds, 1000)
        leader = c.leader
        # The single 700-bed independent leads, not the 2-facility system.
        self.assertTrue(leader.is_independent)
        self.assertAlmostEqual(leader.bed_share, 0.70)
        system = next(s for s in c.shares if s.system_id == "encompass")
        self.assertEqual(system.hospitals, 2)
        self.assertAlmostEqual(system.bed_share, 0.20)

    def test_hhi_treats_each_unmapped_facility_as_its_own_firm(self) -> None:
        """Lumping independents would invent a cartel; dropping them would
        hand the lead to whichever small system happens to be mapped."""
        c = state_concentration("ZZ", self._state())
        # 20^2 (system) + 70^2 + 10^2 (two independents) = 400 + 4900 + 100
        self.assertAlmostEqual(c.hhi, 5400.0)
        self.assertEqual(len(c.shares), 3)
        self.assertEqual(c.independent_facilities, 2)
        self.assertAlmostEqual(c.independent_share, 0.80)

    def test_shares_sum_to_one(self) -> None:
        for st in ("TX", "UT", "CA"):
            c = state_concentration(st)
            self.assertAlmostEqual(sum(s.bed_share for s in c.shares), 1.0, places=6)

    def test_cr_measures_are_ordered_and_bounded(self) -> None:
        c = state_concentration("TX")
        self.assertLessEqual(c.cr1, c.cr3)
        self.assertLessEqual(c.cr3, 1.0)
        self.assertGreater(c.hhi, 0.0)

    def test_closed_hospitals_hold_no_share(self) -> None:
        df = self._state()
        df.loc[df["ccn"] == "450003", "fiscal_year"] = 2019   # stopped filing
        c = state_concentration("ZZ", df)
        self.assertEqual(c.beds, 300)
        self.assertEqual(c.hospitals, 3)
        self.assertEqual(c.leader.system_id, "encompass")

    def test_band_thresholds_follow_the_merger_guidelines(self) -> None:
        self.assertEqual(hhi_band(1499), "Unconcentrated")
        self.assertEqual(hhi_band(1500), "Moderately concentrated")
        self.assertEqual(hhi_band(2499), "Moderately concentrated")
        self.assertEqual(hhi_band(2500), "Highly concentrated")

    def test_unknown_or_empty_state_returns_none(self) -> None:
        self.assertIsNone(state_concentration(""))
        self.assertIsNone(state_concentration("ZZ"))

    def test_ranking_excludes_trivially_small_markets(self) -> None:
        """A three-hospital territory is arithmetically concentrated
        without that meaning anything to a buyer."""
        ranked = concentration_ranking(min_hospitals=10, limit=10)
        self.assertTrue(ranked)
        self.assertTrue(all(c.hospitals >= 10 for c in ranked))
        hhis = [c.hhi for c in ranked]
        self.assertEqual(hhis, sorted(hhis, reverse=True))

    def test_leading_states_is_share_based_not_count_based(self) -> None:
        """Running the most hospitals in a state and being its largest
        operator are different claims."""
        for state in leading_states("intermountain"):
            self.assertEqual(state_concentration(state).leader.system_id,
                             "intermountain")
        self.assertIn("UT", leading_states("intermountain"))
        # A system with no state lead reports none rather than guessing.
        self.assertEqual(leading_states("not-a-system"), ())

    def test_every_state_lead_is_a_mapped_system(self) -> None:
        """A single unmapped hospital can top a state; it must not be
        credited to any system."""
        from rcm_mc.data.health_systems import _leader_map

        for system_id, states in _leader_map().items():
            self.assertTrue(system_id)
            self.assertIsNotNone(get_system(system_id))
            self.assertTrue(states)

    def test_utah_reads_as_intermountain_led(self) -> None:
        """Sanity anchor against a market whose shape is public knowledge."""
        c = state_concentration("UT")
        self.assertEqual(c.leader.system_id, "intermountain")
        self.assertGreater(c.hhi, 1500)


class PageTests(unittest.TestCase):
    def test_page_renders_with_the_master_table(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("Health System Lookup", html)
        self.assertIn("Master Mapping", html)
        self.assertIn("ck-data-table", html)          # click-to-sort applies
        self.assertIn("Behavioral Health Platforms", html)
        self.assertIn("Ascension", html)
        self.assertIn("Encompass Health", html)

    def test_coverage_is_disclosed_not_hidden(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("Independent / Unmapped", html)
        self.assertIn("name-matched", html)

    def test_filters_are_rendered_and_applied(self) -> None:
        html = render_health_system_lookup({})
        for field in ("q", "state", "kind", "focus", "type", "min_hospitals", "sort"):
            self.assertIn(f'name="{field}"', html)
        filtered = render_health_system_lookup({"state": "TX", "type": "behavioral"})
        self.assertIn("State: TX", filtered)
        self.assertIn("Operates: Behavioral health", filtered)

    def test_search_filter_narrows_the_table(self) -> None:
        html = render_health_system_lookup({"q": "oceans"})
        self.assertIn("system=oceans", html)
        # Encompass is the largest system overall (so it still names the
        # KPI tile) but must be gone from the filtered table itself.
        self.assertNotIn("system=encompass", html)

    def test_unmatched_filter_shows_an_empty_state_not_a_crash(self) -> None:
        html = render_health_system_lookup({"q": "zzzz-no-such-system"})
        self.assertIn("No systems match these filters", html)

    def test_roster_drilldown(self) -> None:
        html = render_health_system_lookup({"system": "oceans"})
        self.assertIn("SYSTEM ROSTER", html)
        self.assertIn("Oceans Healthcare", html)
        self.assertIn("Matched On", html)     # the per-facility audit trail
        self.assertIn("/hospital/", html)     # facilities link to their profile

    def test_unknown_system_id_is_ignored(self) -> None:
        html = render_health_system_lookup({"system": "not-a-system"})
        self.assertNotIn("SYSTEM ROSTER", html)
        self.assertIn("Master Mapping", html)

    def test_bad_params_do_not_crash(self) -> None:
        html = render_health_system_lookup(
            {"min_hospitals": "abc", "sort": "'; DROP TABLE", "state": "<script>"})
        self.assertIn("Health System Lookup", html)
        self.assertNotIn("<script>alert", html)

    def test_hospital_lookup_panel(self) -> None:
        html = render_health_system_lookup({"hospital": "crenshaw"})
        self.assertIn("Which System Owns This Facility", html)
        self.assertIn("CRENSHAW COMMUNITY HOSPITAL", html)
        # An unmapped facility says so rather than being hidden.
        self.assertIn("Independent / Unmapped", html)

    def test_hospital_lookup_by_ccn_links_the_system(self) -> None:
        html = render_health_system_lookup({"hospital": "450087"})
        self.assertIn("MEDICAL CITY NORTH HILLS", html)
        self.assertIn("system=hca", html)

    def test_hospital_lookup_miss_shows_an_empty_state(self) -> None:
        html = render_health_system_lookup({"hospital": "zzzz-nope"})
        self.assertIn("No facility matches", html)

    def test_csv_link_carries_the_active_filters(self) -> None:
        html = render_health_system_lookup({"state": "TX", "type": "behavioral"})
        self.assertIn("health-system-lookup.csv", html)
        self.assertIn("state=TX", html)

    def test_inactive_section_lists_closed_facilities(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("Not Operating", html)
        self.assertIn("Stopped filing", html)
        self.assertIn("MADERA COMMUNITY HOSPITAL", html)
        # And it explains the criteria rather than asserting "closed".
        self.assertIn("no closed flag", html)
        # The zero-activity group is disclosed as counted, not held out.
        self.assertIn("Mary Bridge", html)

    def test_inactive_status_filter(self) -> None:
        html = render_health_system_lookup({"status": STATUS_STOPPED})
        self.assertIn("hsl-chip-on", html)
        # Pickens County (last cost report FY2020) is stopped-filing;
        # Madera closed in 2023 and its last full report is FY2021, so it
        # reads Dormant and must NOT appear under this filter.
        self.assertIn("PICKENS COUNTY MEDICAL", html)
        self.assertNotIn("MADERA COMMUNITY HOSPITAL", html)

    def test_kpis_report_the_operating_basis(self) -> None:
        m = get_system_map()
        html = render_health_system_lookup({})
        self.assertIn("Operating hospitals", html)
        self.assertIn("Not operating", html)
        self.assertIn(f"{m.total_hospitals:,}", html)
        self.assertIn(f"of {m.universe_facilities:,} CCNs in HCRIS", html)

    def test_concentration_ranking_shows_nationally(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("Most Concentrated States", html)
        self.assertIn("HHI", html)

    def test_state_filter_swaps_in_that_state_s_concentration(self) -> None:
        html = render_health_system_lookup({"state": "UT"})
        self.assertIn("Market Concentration", html)
        self.assertIn("UT bed-share concentration", html)
        self.assertIn("Intermountain Health", html)
        # The floor caveat travels with the number.
        self.assertIn("floor", html)

    def test_states_led_column_and_roster_line(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("States Led", html)
        roster = render_health_system_lookup({"system": "providence"})
        self.assertIn("largest operator in", roster)

    def test_concentration_map_shades_states_and_drills_down(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("usm-cell", html)                      # the cartogram
        self.assertIn("/health-system-lookup?state=", html)  # click-through
        self.assertIn("Intermountain Health leads at", html)  # tooltip note

    def test_concentration_map_marks_the_filtered_state(self) -> None:
        html = render_health_system_lookup({"state": "UT"})
        self.assertIn("usm-selected", html)

    def test_map_shades_only_markets_deep_enough_to_mean_something(self) -> None:
        """Every shaded tile clears the 5-hospital floor. A three-hospital
        territory shading as 'highly concentrated' would read as a signal
        where there is none."""
        from rcm_mc.data.health_systems import _all_state_concentration
        from rcm_mc.ui.us_map import STATE_NAMES, _TILE

        html = render_health_system_lookup({})
        by_state = {c.state: c for c in _all_state_concentration()}
        for abbr in _TILE:
            label = STATE_NAMES.get(abbr, abbr)
            c = by_state.get(abbr)
            if c is not None and c.hospitals >= 5:
                self.assertNotIn(f"{label}: no data", html)
            else:
                self.assertIn(f"{label}: no data", html)
        # The markets currently below the floor are territories the
        # cartogram has no tile for, so they are not drawn at all.
        for thin in [c.state for c in _all_state_concentration()
                     if c.hospitals < 5]:
            self.assertNotIn(thin, _TILE)

    def test_roster_carries_a_footprint_map_with_leads_accented(self) -> None:
        html = render_health_system_lookup({"system": "providence"})
        self.assertIn("usm-cell", html)
        self.assertIn("usm-accent", html)
        self.assertIn("operating hospitals", html)

    def test_registry_note_surfaces_on_the_roster(self) -> None:
        sysdef = get_system("trinity")
        self.assertTrue(sysdef.note)
        html = render_health_system_lookup({"system": "trinity"})
        self.assertIn("UnityPoint", html)

    def test_the_page_shows_the_whole_certified_universe(self) -> None:
        """The hospital count is not the CCN count, and a page that only
        shows the first invites a partner to size a system by its
        hospitals when most of its CCNs are somewhere else."""
        from rcm_mc.data.provider_crosswalk import crosswalk_by_class

        html = render_health_system_lookup({})
        self.assertIn("Full Provider Universe", html)
        classes = crosswalk_by_class()
        for label in classes["provider_class_label"]:
            self.assertIn(label, html)
        total = int(classes["facilities"].sum())
        self.assertIn(f"{total:,} CCNs", html)
        self.assertIn("/provider-crosswalk.csv?scope=all", html)

    def test_the_npi_panel_says_what_slice_it_is(self) -> None:
        """20,401 ambulance NPIs is not NPPES, and a coverage bar that
        does not say so invites reading 6.6% as national."""
        html = render_health_system_lookup({})
        self.assertIn("Organization NPIs", html)
        self.assertIn("Global Medical Response", html)
        self.assertIn("not all of NPPES", html)
        self.assertIn("PECOS", html)


class SystemNpiRosterTests(unittest.TestCase):
    """An operator's estate is its CCNs and its NPIs, and those are
    different lists."""

    def test_an_operator_with_no_ccn_still_has_a_roster(self) -> None:
        """Air Methods holds 289 NPIs and no certified facility. A bare
        "no facilities mapped" was hiding its entire estate — which is
        the case this page exists for."""
        html = render_health_system_lookup({"system": "air_methods"})
        self.assertIn("NPI ROSTER", html)
        self.assertIn("bills under NPIs only", html)
        self.assertIn("289 NPIs", html)

    def test_a_system_with_both_shows_both(self) -> None:
        html = render_health_system_lookup({"system": "ascension"})
        self.assertIn("SYSTEM ROSTER", html)
        self.assertIn("NPI ROSTER", html)

    def test_the_tier_travels_with_each_npi(self) -> None:
        """A PECOS enrolment group is CMS's own grouping; a name match is
        our reading of the signage. The roster cannot present them as the
        same claim, so every row names the hop it is least sure about."""
        from rcm_mc.data.master_provider_file import cached_master_file

        html = render_health_system_lookup({"system": "global_medical_response"})
        frame = cached_master_file()
        hits = frame[frame["final_parent"] == "sys:global_medical_response"]
        tiers = {str(t).replace("_", " ") for t in hits["parent_tier"]}
        self.assertTrue(tiers)
        for tier in tiers:
            with self.subTest(tier=tier):
                self.assertIn(tier, html)
        self.assertIn("CMS's own", html.replace("&#x27;", "'"))

    def test_the_count_is_labelled_a_floor(self) -> None:
        """The bundled extracts are an ambulance and EMS slice. Reading
        648 NPIs as an operator's full estate would be wrong."""
        html = render_health_system_lookup({"system": "air_methods"})
        self.assertIn("floor rather than", html)

    def test_an_absence_is_explained_rather_than_left_blank(self) -> None:
        """DaVita has no ambulance NPIs. That is a gap in the slice, not
        a statement about DaVita."""
        html = render_health_system_lookup({"system": "davita"})
        self.assertIn("gap in the", html)

    def test_the_roster_links_to_the_full_download(self) -> None:
        html = render_health_system_lookup({"system": "air_methods"})
        self.assertIn("/master-npi-file.csv?parent=sys%3Aair_methods", html)


class NpiLookupPanelTests(unittest.TestCase):
    """The crosswalk answered from the direction people hold it: a
    ten-digit number and nothing else."""

    def test_an_exact_npi_returns_that_row(self) -> None:
        html = render_health_system_lookup({"npi": "1316943566"})
        self.assertIn("NPI Lookup", html)
        self.assertIn("ACADIAN AMBULANCE SERVICE", html)

    def test_a_name_fragment_works_too(self) -> None:
        """A partner reading a CIM has the name, not the number."""
        html = render_health_system_lookup({"npi": "AIR METHODS"})
        self.assertIn("1285773473", html)
        self.assertIn("sys:air_methods", html)

    def test_the_answer_shows_the_chain_not_just_the_conclusion(self) -> None:
        """"Belongs to Air Methods" is a claim. The hops that produced it
        are what makes it checkable."""
        html = render_health_system_lookup({"npi": "AIR METHODS"})
        self.assertIn("name_system", html)
        self.assertIn("The <strong>Why</strong> column", html)

    def test_the_form_renders_before_anything_is_typed(self) -> None:
        html = render_health_system_lookup({})
        self.assertIn("NPI Lookup", html)
        self.assertIn('name="npi"', html)

    def test_a_miss_explains_the_slice_rather_than_going_blank(self) -> None:
        html = render_health_system_lookup({"npi": "ZZZZ-NOT-A-THING"})
        self.assertIn("No NPI matches", html)
        self.assertIn("not the full register", html)

    def test_the_individual_caveat_travels_with_the_panel(self) -> None:
        html = render_health_system_lookup({"npi": "ACADIAN"})
        self.assertIn("no employer field", html)

    def test_a_cluster_parent_is_shown_by_name_not_only_by_number(self) -> None:
        """``pecos:2264404516`` is the honest answer to "which cluster"
        and a useless one to "who owns this", which is what the partner
        typed the NPI to find out."""
        html = render_health_system_lookup({"npi": "ACADIAN"})
        self.assertIn("ACADIAN AMBULANCE SERVICE", html)
        self.assertIn("of members", html)

    def test_the_identifier_stays_under_the_name(self) -> None:
        """A label is a plurality of member filings; the identifier is
        what was actually resolved. Replacing one with the other would
        make an inference look like a lookup."""
        html = render_health_system_lookup({"npi": "ACADIAN"})
        self.assertIn("pecos:", html)
        self.assertIn('class="hsl-sub"', html)

    def test_the_legend_says_what_the_share_means(self) -> None:
        html = render_health_system_lookup({"npi": "ACADIAN"})
        self.assertIn("how many members filed that name", html)


class ParentCellTests(unittest.TestCase):
    """The cell that renders a resolved parent."""

    @staticmethod
    def _cell(*args):
        from rcm_mc.ui.data_public.health_system_lookup_page import (
            _parent_cell)
        return _parent_cell(*args)

    def test_no_parent_renders_as_a_dash_not_an_empty_cell(self) -> None:
        self.assertEqual(self._cell("", "", ""), "—")

    def test_an_unlabelled_parent_still_shows_its_identifier(self) -> None:
        """The abstaining clusters are the ones where members file too
        many names to pick one. They must not render blank — the parent
        was resolved, only the name was withheld."""
        self.assertEqual(self._cell("official:BRIAN TIERNEY", "", ""),
                         "official:BRIAN TIERNEY")

    def test_a_labelled_parent_leads_with_the_name(self) -> None:
        out = self._cell("pecos:555", "METRO AMBULANCE SERVICES INC", 1.0)
        self.assertTrue(out.startswith("METRO AMBULANCE SERVICES INC"))
        self.assertIn("pecos:555", out)
        self.assertIn("100% of members", out)

    def test_an_unreadable_support_drops_the_share_not_the_name(self) -> None:
        out = self._cell("pecos:555", "METRO AMBULANCE INC", "")
        self.assertIn("METRO AMBULANCE INC", out)
        self.assertNotIn("of members", out)

    def test_a_hostile_label_cannot_close_the_cell(self) -> None:
        out = self._cell("pecos:555", '<script>alert(1)</script>', 1.0)
        self.assertNotIn("<script>", out)


class OwnershipPanelTests(unittest.TestCase):
    """The ownership graph on the page — how the answers were reached,
    and the ones the sources cannot agree on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = render_health_system_lookup({})

    def test_the_panel_renders_with_its_tier_mix(self) -> None:
        """A coverage number cannot be read without knowing which tiers
        produced it: a facility reaching a system on the registry's
        say-so is a different claim from one reaching it through the
        operator's own chain filing."""
        self.assertIn("Ownership Graph", self.html)
        for tier in ("ccn system", "ccn chain", "ccn parent"):
            self.assertIn(tier, self.html)

    def test_the_disagreement_table_shows_both_answers(self) -> None:
        from rcm_mc.data.parent_resolution import (
            crosswalk_graph, ownership_disagreements,
        )

        queue = ownership_disagreements(crosswalk_graph())
        self.assertFalse(queue.empty)
        self.assertIn("Resolved parent", self.html)
        self.assertIn("Rival parent", self.html)
        # Every disagreement on the page names the facility and both
        # candidates — a queue with one side missing is not workable.
        for rec in queue.head(12).to_dict("records"):
            with self.subTest(ccn=rec["identifier"]):
                self.assertIn(rec["identifier"], self.html)
                self.assertIn(_html.escape(rec["rival_parent"]), self.html)

    def test_the_panel_says_what_it_is_and_is_not(self) -> None:
        """CMS publishes change-of-ownership only as state-by-year
        counts. Calling this an acquisition list without that caveat
        would be claiming a fact."""
        self.assertIn("acquisition list", self.html)
        self.assertIn("state-by-year", self.html)
        self.assertIn("registry edit", self.html)

    def test_the_panel_links_to_the_exports_that_carry_the_answer(self) -> None:
        self.assertIn("/provider-crosswalk.csv?scope=all&amp;parents=1",
                      self.html)
        self.assertIn("master-file", self.html)

    def test_cycles_are_reported_rather_than_left_implicit(self) -> None:
        """A graph with no cycles is a finding, not an absence — the page
        states the count so a future non-zero one is visible."""
        self.assertIn("Cycles are flagged", self.html)


class CsvRouteTests(unittest.TestCase):
    """The export is served over real HTTP, defanged, on a live server."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as sock:
            sock.bind(("127.0.0.1", 0))
            cls._port = sock.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "hsl.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _get(self, route: str):
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{self._port}{route}", timeout=60)
        return resp, resp.read().decode("utf-8")

    def test_page_serves_200(self) -> None:
        resp, body = self._get("/health-system-lookup")
        self.assertEqual(resp.status, 200)
        self.assertIn("Health System Lookup", body)

    def test_csv_serves_as_an_attachment(self) -> None:
        resp, body = self._get("/health-system-lookup.csv?state=TX&type=behavioral")
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))
        rows = list(csv.DictReader(io.StringIO(body)))
        self.assertTrue(rows)
        self.assertEqual({r["state"] for r in rows}, {"TX"})
        self.assertEqual({r["is_behavioral"] for r in rows}, {"Y"})
        self.assertIn("system_name", rows[0])

    def test_csv_covers_the_whole_universe_unfiltered(self) -> None:
        _, body = self._get("/health-system-lookup.csv")
        rows = list(csv.DictReader(io.StringIO(body)))
        self.assertEqual(len(rows), get_system_map().universe_facilities)
        self.assertIn("facility_status", rows[0])

    def test_csv_status_filter(self) -> None:
        _, body = self._get("/health-system-lookup.csv?status=operating")
        rows = list(csv.DictReader(io.StringIO(body)))
        self.assertEqual(len(rows), get_system_map().total_hospitals)
        self.assertEqual({r["facility_status"] for r in rows}, {"Active"})


if __name__ == "__main__":
    unittest.main()


class RegistryPrecisionTests(unittest.TestCase):
    """Precision of what is already mapped, not recall of what is not.

    Every previous test here asks whether the matcher finds enough. None
    asked whether what it found is right. An audit of the 14,425 mapped
    facilities turned up 53 that were wrong — fourteen Southeast nursing
    homes called Harborview assigned to UW Medicine in Seattle, twelve
    Utah nursing homes called Monument Healthcare assigned to Monument
    Health in South Dakota, eight nursing homes called The Cedars
    assigned to Cedars-Sinai — and the whole suite passed while they
    were there.

    So these are structural invariants over the real register rather
    than assertions about the systems that happened to be wrong. A
    pinned list of nine catches those nine; an invariant catches the
    tenth.
    """

    ACUTE = frozenset({"hospital", "irf", "ltch"})

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.health_systems import UNMAPPED_ID
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        crosswalk = get_crosswalk(scope=SCOPE_ALL)
        system = crosswalk["system_id"].astype(str)
        cls.mapped = crosswalk[system.ne("") & system.ne(UNMAPPED_ID)]

    def test_a_single_market_system_does_not_reach_across_the_country(self):
        """The failure shape, stated once.

        A system whose hospitals sit in exactly one state has a
        single-market brand, and post-acute facilities carrying that
        brand in other states are almost always a different company
        using the same word. Nine systems were doing this; the rule is
        what stops the tenth.
        """
        from rcm_mc.data.health_systems import SYSTEM_REGISTRY

        unscoped = {s.system_id for s in SYSTEM_REGISTRY if not s.states}
        offenders = {}
        for system_id, group in self.mapped.groupby(
                self.mapped["system_id"].astype(str)):
            if system_id not in unscoped:
                continue
            acute = {str(state) for state, klass
                     in zip(group["state"], group["provider_class"])
                     if str(klass) in self.ACUTE}
            if len(acute) != 1:
                continue
            home = next(iter(acute))
            away = group[group["state"].astype(str) != home]
            if len(away) > 1:
                offenders[system_id] = sorted(set(away["state"].astype(str)))
        self.assertEqual(
            offenders, {},
            "Single-market systems reaching outside their acute state — "
            "give each a states=() footprint or an exclude: "
            f"{offenders}")

    def test_no_two_systems_claim_the_same_facility_name_in_one_town(self):
        """One name, one town, one owner.

        Keyed on city and not merely state, because the first cut of
        this test keyed on state and flagged Houston Methodist against
        Methodist Hospital San Antonio — two genuinely different Texas
        systems, both assigned by hand CCN override, both correct. Two
        facilities sharing a name across a state is normal; sharing one
        within a town means a pattern has reached into another system's
        estate.
        """
        from rcm_mc.data.health_systems import normalize_name

        claims = {}
        for name, state, city, system_id in zip(
                self.mapped["name"], self.mapped["state"],
                self.mapped["city"], self.mapped["system_id"]):
            key = (normalize_name(name), str(state), str(city).upper().strip())
            claims.setdefault(key, set()).add(str(system_id))
        split = {k: sorted(v) for k, v in claims.items() if len(v) > 1}
        self.assertEqual(split, {}, f"Same name, same town, two systems: {split}")

    def test_the_registry_states_its_own_rule_and_follows_it(self):
        """SystemDef's docstring says a footprint is required for every
        brand naming more than one unrelated organization. These nine
        were the standing violations."""
        from rcm_mc.data.health_systems import get_system

        for system_id, expected in (("uw_medicine", ("WA",)),
                                    ("cedars", ("CA",)),
                                    ("wellbridge", ("TX",)),
                                    ("madonna", ("NE",)),
                                    ("emory", ("GA",)),
                                    ("four_winds", ("NY",)),
                                    ("bayhealth", ("DE",))):
            with self.subTest(system=system_id):
                self.assertEqual(get_system(system_id).states, expected)

    def test_two_systems_sharing_a_name_in_one_state_are_kept_apart(self):
        """Missouri has two unrelated Saint Luke's and Florida has three
        unrelated Baptists. A state scope cannot separate them, so the
        overrides do — and the check is that each estate is in its own
        metro rather than that the counts happen to be right."""
        stl = self.mapped[self.mapped["system_id"].astype(str) == "st_lukes_stl"]
        self.assertEqual(set(stl["city"].astype(str).str.upper()),
                         {"CHESTERFIELD", "ST. LOUIS"})
        kc = self.mapped[self.mapped["system_id"].astype(str) == "st_lukes_kc"]
        self.assertNotIn("CHESTERFIELD", set(kc["city"].astype(str).str.upper()))

        jax = self.mapped[self.mapped["system_id"].astype(str) == "baptist_jax"]
        self.assertTrue(all(c.upper().startswith(("JACKSONVILLE", "FERNANDINA"))
                            for c in jax["city"].astype(str)))
        pens = self.mapped[self.mapped["system_id"].astype(str)
                           == "baptist_pensacola"]
        self.assertEqual(set(pens["city"].astype(str).str.upper()), {"PENSACOLA"})
        miami = self.mapped[self.mapped["system_id"].astype(str) == "baptist_fl"]
        self.assertEqual(set(miami["city"].astype(str).str.upper()), {"MIAMI"})

    def test_a_unit_and_its_parent_hospital_agree(self):
        """A T in the third position of a CCN is CMS stating that this
        unit is part of that hospital. Two different owners on the two
        ends is the register contradicting itself, and in every case it
        was ownership staleness: one of the two names had not caught up
        with an acquisition.

        Five existed. Each was read individually rather than fixed by a
        blanket "unit inherits parent" rule, because the stale name is
        sometimes on the unit — MERCY HOSPITAL PITTSBURG under a parent
        already reading ASCENSION VIA CHRISTI — and sometimes on the
        parent, where MERCY REGIONAL HEALTH CENTER sits above a unit
        already reading VIA CHRISTI MANHATTAN. A blanket rule would have
        fixed four and broken the fifth.
        """
        from rcm_mc.data.health_systems import UNMAPPED_ID

        indexed = self.mapped.set_index(self.mapped["ccn"].astype(str))
        by_ccn = indexed["system_id"].astype(str)
        split = {}
        for ccn, parent in zip(self.mapped["ccn"].astype(str),
                               self.mapped["parent_ccn"].astype(str)):
            if not parent or parent not in by_ccn.index:
                continue
            unit_system, parent_system = by_ccn.loc[ccn], by_ccn.loc[parent]
            if UNMAPPED_ID in (unit_system, parent_system):
                continue
            if unit_system != parent_system:
                split[ccn] = (unit_system, parent, parent_system)
        self.assertEqual(split, {},
                         f"Unit and parent hospital owned by different "
                         f"systems: {split}")

    def test_a_real_out_of_state_facility_is_kept(self):
        """Marshfield genuinely runs Dickinson in Iron Mountain,
        Michigan. The scope had to admit MI while dropping a nursing
        home in Marshfield, Missouri — a town, not this system."""
        from rcm_mc.data.health_systems import get_system

        self.assertEqual(get_system("marshfield").states, ("WI", "MI"))
        names = set(self.mapped[self.mapped["system_id"].astype(str)
                                == "marshfield"]["state"].astype(str))
        self.assertEqual(names, {"WI", "MI"})


class NameDisagreementTests(unittest.TestCase):
    """CMS publishes two names per facility on two clocks. When a
    hospital changes hands one of them moves first, so a disagreement is
    the register reporting a transaction — the only way this data ever
    does, since CMS publishes change-of-ownership as state-by-year counts
    and nothing else."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.health_systems import name_disagreements

        cls.queue = name_disagreements()

    def test_neither_name_is_automatically_the_fresher_one(self):
        """The reason this reports instead of resolving.

        Twelve of the seventeen had the newer name on Care Compare — the
        Centura hospitals that went to AdventHealth, Ascension's two
        Michigan hospitals that went to Henry Ford. Three had it on the
        cost report instead: CCF MERCY, UVA HEALTH PRINCE WILLIAM and
        VIA CHRISTI PITTSBURG were already updated there while Care
        Compare still carried the seller. "Always prefer the CMS name"
        would have fixed twelve and broken three.
        """
        from rcm_mc.data.health_systems import CCN_OVERRIDES

        # The three where the cost report is fresher must NOT be
        # overridden towards Care Compare.
        for ccn, keeps in (("360070", "cleveland_clinic"),
                           ("490045", "uva"),
                           ("170006", "ascension")):
            with self.subTest(ccn=ccn):
                self.assertNotIn(ccn, CCN_OVERRIDES)
                row = self.mapped_row(ccn)
                self.assertEqual(row["system_id"], keeps)

    @staticmethod
    def mapped_row(ccn: str):
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        register = get_crosswalk(scope=SCOPE_ALL)
        return register[register["ccn"].astype(str) == ccn].iloc[0]

    def test_the_settled_transactions_moved(self):
        """The twelve that were adjudicated are no longer in the queue,
        and their facilities sit with the buyer."""
        for ccn, buyer in (("230165", "henry_ford"),
                           ("230195", "henry_ford"),
                           ("060064", "adventhealth"),
                           ("060125", "adventhealth"),
                           ("050152", "uc_health"),
                           ("440034", "covenant_tn"),
                           ("150146", "parkview")):
            with self.subTest(ccn=ccn):
                self.assertEqual(self.mapped_row(ccn)["system_id"], buyer)
        settled = {d.ccn for d in self.queue}
        self.assertEqual(settled & {"230165", "060064", "050152"}, set())

    def test_a_chain_filing_is_never_in_the_queue(self):
        """It never consulted a name, so it cannot disagree with one."""
        for entry in self.queue:
            with self.subTest(ccn=entry.ccn):
                self.assertFalse(
                    self.mapped_row(entry.ccn)["system_match"].startswith(
                        ("chain:", "ccn override")))

    def test_what_is_left_is_genuinely_undecidable(self):
        """Baylor St Luke's is a real CommonSpirit/Baylor joint venture
        and either name is defensible. A queue that emptied itself would
        mean it had started guessing."""
        self.assertLessEqual(len(self.queue), 8)
        self.assertIn("450193", {d.ccn for d in self.queue})


class SplitSystemIdentityTests(unittest.TestCase):
    """One id held two companies and called itself a third thing."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        cls.register = get_crosswalk(scope=SCOPE_ALL)

    def test_hoag_is_its_own_system(self):
        """Hoag separated from Providence in 2022. It was sitting inside
        an entry whose id was "cedars_marina" and whose display name was
        "Providence Southern California" — an id from one era, a name
        from another, and two companies inside."""
        from rcm_mc.data.health_systems import get_system

        self.assertIsNone(get_system("cedars_marina"))
        self.assertIsNotNone(get_system("hoag"))
        hoag = self.register[self.register["system_id"].astype(str) == "hoag"]
        self.assertEqual(len(hoag), 5)
        self.assertTrue(all("HOAG" in n.upper() or "FUDGE" in n.upper()
                            for n in hoag["name"].astype(str)))

    def test_mission_hospital_went_to_providence(self):
        for ccn in ("050567", "05T567"):
            with self.subTest(ccn=ccn):
                row = self.register[
                    self.register["ccn"].astype(str) == ccn].iloc[0]
                self.assertEqual(row["system_id"], "providence")

    def test_no_two_ids_hold_the_same_company(self):
        """The old entry also carried ^SAINT JOSEPH HOSPITAL ORANGE,
        which `providence` already reaches, so one company sat under two
        ids and every system-level rollup counted it twice."""
        from rcm_mc.data.health_systems import SYSTEM_REGISTRY

        names = [s.name.strip().lower() for s in SYSTEM_REGISTRY]
        duplicates = {n for n in names if names.count(n) > 1}
        self.assertEqual(duplicates, set())


class ChangedHandsPanelTests(unittest.TestCase):
    """The queue on /health-system-lookup."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = render_health_system_lookup({})

    def test_the_panel_is_on_the_page(self) -> None:
        self.assertIn("Changed Hands", self.html)
        self.assertIn("450193", self.html)

    def test_it_says_why_it_does_not_just_pick_one(self) -> None:
        """A reader who cannot see that preferring either source would
        be wrong a fifth of the time has no reason to accept a queue
        instead of an answer."""
        self.assertIn("Neither name is reliably the fresher one", self.html)

    def test_it_names_the_transactions_already_settled(self) -> None:
        self.assertIn("Centura", self.html)
        self.assertIn("Henry Ford", self.html)

    def test_it_explains_why_this_is_the_only_chow_signal(self) -> None:
        self.assertIn("state-by-year counts", self.html)


class ChainVersusNameTests(unittest.TestCase):
    """CMS's chain column and the facility's own name disagree 55 times.

    The chain column is a third party's statement and it goes stale; the
    name is the facility's own. So the name wins, and chain_name stays
    on the row for the cases where both are true.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk

        cls.register = get_crosswalk(scope=SCOPE_ALL)
        cls.flipped = cls.register[
            cls.register["system_match"].astype(str).str.startswith(
                "name over chain")]

    def _row(self, ccn: str):
        return self.register[
            self.register["ccn"].astype(str) == ccn].iloc[0]

    def test_a_retired_chain_brand_does_not_hold_its_buyer_s_clinics(self):
        """US Renal Care bought DSI in 2016. Eight clinics named
        "USRC …" were still filed under the retired brand, and the
        registry had an entry existing only to hold them."""
        from rcm_mc.data.health_systems import get_system

        self.assertIsNone(get_system("dsi_renal"))
        for ccn in ("032583", "032608", "372598"):
            with self.subTest(ccn=ccn):
                row = self._row(ccn)
                self.assertTrue(row["name"].upper().startswith("USRC"))
                self.assertEqual(row["system_id"], "us_renal_care")

    def test_one_operator_is_not_split_down_the_middle(self):
        """33 clinics named "SHC …" sat under US Renal Care while 44
        identically-named ones sat under Satellite, decided by the chain
        column alone. SHC is Satellite's own abbreviation, and it files
        its own chain string in Tennessee and Texas."""
        shc = self.register[
            self.register["name"].astype(str).str.upper().str.startswith("SHC ")]
        self.assertGreater(len(shc), 70)
        self.assertEqual(set(shc["system_id"].astype(str)),
                         {"satellite_healthcare"})

    def test_a_joint_venture_keeps_both_answers(self):
        """Billings Clinic Dialysis is Billings Clinic's, operated by
        DCI. Both are true and the row carries both — the system is the
        brand on the door, the operator stays in chain_name."""
        row = self._row("272510")
        self.assertEqual(row["system_id"], "billings")
        self.assertEqual(row["chain_name"], "Dialysis Clinic, Inc.")

    def test_the_override_is_visible_as_its_own_basis(self):
        """A reader must be able to see that the chain column was
        consulted and overruled, not that it was never read."""
        self.assertGreater(len(self.flipped), 40)
        for basis in set(self.flipped["system_match"].astype(str)):
            self.assertTrue(basis.startswith("name over chain: "))

    def test_an_agreeing_chain_filing_is_left_alone(self):
        """Only disagreements change. The other 6,600 chain-filed
        facilities keep their basis."""
        chain_filed = self.register[
            self.register["system_match"].astype(str).str.startswith("chain:")]
        self.assertGreater(len(chain_filed), 6_000)
