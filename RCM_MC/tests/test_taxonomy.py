"""Tests for the healthcare-subsector taxonomy.

Covers the registry's structural invariants (size, MECE groupings, unique ids,
valid crosswalks), the lookup helpers, and the CLI's render + JSON paths. The
crosswalk tests are the load-bearing ones: a typo'd ``vertical`` or
``nucc_verticals`` tag would silently break the provider-supply join, so we
assert every reference resolves against the real source-of-truth modules.
"""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from rcm_mc.taxonomy import (
    Grouping,
    KPI,
    Subsector,
    all_subsectors,
    by_grouping,
    by_id,
    by_nucc_vertical,
    by_vertical,
    central_subsectors,
    grouping_counts,
    groupings,
    search,
)
from rcm_mc.taxonomy import registry
from rcm_mc.taxonomy.cli import main as taxonomy_cli


# ── Registry structure ────────────────────────────────────────────────────

class TestRegistryStructure(unittest.TestCase):
    def test_has_roughly_55_subsectors(self):
        # Spec: "~55 subsectors across six groupings". We carry 59 today
        # (behavioral health + post-acute sub-segments split out). Guard the
        # band so an accidental truncation or a runaway paste is caught.
        n = len(all_subsectors())
        self.assertGreaterEqual(n, 55)
        self.assertLessEqual(n, 65)

    def test_six_groupings(self):
        self.assertEqual(len(groupings()), 6)
        self.assertEqual(len(list(Grouping)), 6)

    def test_ids_are_unique(self):
        ids = [s.id for s in all_subsectors()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_ids_are_slug_shaped(self):
        # by_id lower-cases its argument, so an id with uppercase/space would be
        # unreachable. Enforce the slug convention the lookup assumes.
        for s in all_subsectors():
            self.assertEqual(s.id, s.id.lower().strip(), s.id)
            self.assertNotIn(" ", s.id, s.id)

    def test_grouping_counts_sum_to_total(self):
        counts = grouping_counts()
        self.assertEqual(sum(counts.values()), len(all_subsectors()))
        # Every grouping is represented (MECE — none empty).
        for g in Grouping:
            self.assertGreater(counts[g], 0, g)

    def test_every_subsector_has_core_fields(self):
        for s in all_subsectors():
            self.assertTrue(s.name, s.id)
            self.assertTrue(s.business_model, s.id)
            self.assertIsInstance(s.grouping, Grouping)
            self.assertGreater(len(s.kpis), 0, f"{s.id} has no KPIs")
            self.assertGreater(len(s.exhibits), 0, f"{s.id} has no exhibits")
            for k in s.kpis:
                self.assertIsInstance(k, KPI)
                self.assertTrue(k.name, s.id)

    def test_duplicate_id_validation_fires(self):
        # The import-time guard is the safety net for the single-source-of-truth
        # invariant; prove it actually raises rather than silently shadowing.
        dup = Subsector(id="x", name="X", grouping=Grouping.CONSUMER_OTHER,
                        business_model="bm", kpis=(KPI("k"),), exhibits=("e",))
        original = registry._SUBSECTORS
        try:
            registry._SUBSECTORS = original + (dup, dup)
            with self.assertRaises(ValueError):
                registry._validate()
        finally:
            registry._SUBSECTORS = original


# ── Crosswalk integrity ───────────────────────────────────────────────────

class TestCrosswalks(unittest.TestCase):
    def test_vertical_refs_resolve(self):
        from rcm_mc.verticals.registry import Vertical
        valid = {v.value for v in Vertical}
        for s in all_subsectors():
            if s.vertical:
                self.assertIn(s.vertical, valid, f"{s.id} -> {s.vertical}")

    def test_nucc_vertical_refs_resolve(self):
        from rcm_mc.data_public.nucc_taxonomy import VERTICALS
        valid = set(VERTICALS)
        for s in all_subsectors():
            for n in s.nucc_verticals:
                self.assertIn(n, valid, f"{s.id} -> {n}")

    def test_central_subsectors_carry_deep_dive(self):
        central = central_subsectors()
        self.assertTrue(central)
        for s in central:
            self.assertTrue(s.central)
            self.assertTrue(s.deep_dive, f"{s.id} central but no deep_dive")


# ── Lookups ───────────────────────────────────────────────────────────────

class TestLookups(unittest.TestCase):
    def test_by_id_known_and_unknown(self):
        self.assertEqual(by_id("dermatology").name, "Dermatology")
        # Case/whitespace tolerant, mirroring nucc_taxonomy.by_code.
        self.assertEqual(by_id("  ASC  ").id, "asc")
        self.assertIsNone(by_id("not_a_real_subsector"))

    def test_by_grouping_enum_and_string(self):
        by_enum = by_grouping(Grouping.FACILITY_BASED)
        by_label = by_grouping("Facility-Based Care")
        by_name = by_grouping("FACILITY_BASED")
        self.assertEqual([s.id for s in by_enum], [s.id for s in by_label])
        self.assertEqual([s.id for s in by_enum], [s.id for s in by_name])
        self.assertIn("asc", [s.id for s in by_enum])

    def test_by_grouping_bad_value_raises(self):
        with self.assertRaises(ValueError):
            by_grouping("Not A Grouping")

    def test_search_matches_thesis_and_risks(self):
        ids = [s.id for s in search("site-of-service")]
        self.assertIn("orthopedics", ids)
        # Matches risk text, not just names.
        self.assertTrue(any("pbm" == s.id for s in search("any-willing-pharmacy")))

    def test_search_empty_returns_nothing(self):
        self.assertEqual(search(""), [])
        self.assertEqual(search("   "), [])

    def test_by_vertical(self):
        self.assertTrue(by_vertical("MSO"))
        self.assertIn("hospitals", [s.id for s in by_vertical("hospital")])

    def test_by_nucc_vertical(self):
        self.assertEqual([s.id for s in by_nucc_vertical("home_health")],
                         ["home_health"])
        # Behavioral tag fans out to all four BH sub-segments.
        self.assertEqual(len(by_nucc_vertical("behavioral")), 4)


# ── CLI ───────────────────────────────────────────────────────────────────

class TestCLI(unittest.TestCase):
    def _run(self, *argv) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = taxonomy_cli(list(argv))
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_groupings(self):
        out = self._run("groupings")
        self.assertIn("TOTAL", out)
        self.assertIn("Facility-Based Care", out)

    def test_list_and_grouping_filter(self):
        out = self._run("list", "--grouping", "FACILITY_BASED")
        self.assertIn("asc", out)
        self.assertNotIn("dermatology", out)

    def test_show_text_and_json(self):
        out = self._run("show", "home_health")
        self.assertIn("PDGM", out)
        payload = json.loads(self._run("show", "asc", "--json"))
        self.assertEqual(payload["id"], "asc")
        self.assertEqual(payload["grouping"], "Facility-Based Care")
        self.assertTrue(payload["kpis"])

    def test_search_cli(self):
        out = self._run("search", "dialysis")
        self.assertIn("dialysis", out)

    def test_central_cli(self):
        out = self._run("central")
        self.assertIn("home_health", out)

    def test_show_unknown_exits_nonzero(self):
        with self.assertRaises(SystemExit):
            taxonomy_cli(["show", "no_such_id"])

    def test_list_json_is_valid(self):
        payload = json.loads(self._run("list", "--json"))
        self.assertEqual(len(payload), len(all_subsectors()))


if __name__ == "__main__":
    unittest.main()
