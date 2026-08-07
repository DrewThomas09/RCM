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
    CCN_OVERRIDES,
    STATUS_ACTIVE,
    STATUS_DORMANT,
    STATUS_STOPPED,
    SYSTEM_REGISTRY,
    UNMAPPED_ID,
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
        """No dead entries: each system matches at least one real facility."""
        live = {r.system_id for r in get_system_map().systems}
        dead = sorted(s.system_id for s in SYSTEM_REGISTRY if s.system_id not in live)
        self.assertEqual(dead, [], f"registry entries that match nothing: {dead}")


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
        assigned = assign_systems()
        universe = set(assigned["ccn"].astype(str))
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
        assigned = assign_systems().set_index("ccn")
        for ccn in CCN_OVERRIDES:
            self.assertEqual(assigned.loc[ccn, "system_match"], f"ccn override {ccn}")

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
            self.assertEqual(assigned.loc[ccn, "system_match"], f"ccn override {ccn}")

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
