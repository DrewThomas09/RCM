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

import unittest

import pandas as pd

from rcm_mc.data.health_systems import (
    SYSTEM_REGISTRY,
    UNMAPPED_ID,
    assign_systems,
    build_system_map,
    candidate_clusters,
    get_system,
    get_system_map,
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


class RollupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = get_system_map()

    def test_totals_reconcile(self) -> None:
        mapped = sum(s.hospitals for s in self.m.systems)
        self.assertEqual(mapped, self.m.mapped_hospitals)
        self.assertEqual(mapped + self.m.unmapped.hospitals, self.m.total_hospitals)

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
        top = self.m.systems[0]
        roster = system_hospitals(top.system_id)
        self.assertEqual(len(roster), top.hospitals)
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
        self.assertEqual(m.mapped_hospitals, 2)
        self.assertEqual(m.system_count, 1)
        self.assertEqual(m.systems[0].system_id, "ascension")
        self.assertEqual(m.systems[0].state_count, 2)
        self.assertEqual(m.unmapped.hospitals, 1)


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

    def test_registry_note_surfaces_on_the_roster(self) -> None:
        sysdef = get_system("trinity")
        self.assertTrue(sysdef.note)
        html = render_health_system_lookup({"system": "trinity"})
        self.assertIn("UnityPoint", html)


if __name__ == "__main__":
    unittest.main()
