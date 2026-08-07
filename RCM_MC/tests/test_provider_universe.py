"""The six non-hospital provider classes.

The hospital universe is 6,123 CCNs. The Medicare-certified universe is
roughly eight times that, and the difference is where most of a health
system's post-acute estate lives.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.health_systems import assign_systems
from rcm_mc.data.provider_universe import (
    CLASS_LABELS,
    CLASS_SPECS,
    UNIVERSE_COLUMNS,
    chain_roster,
    class_counts,
    load_post_acute_universe,
)


class UniverseShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.universe = load_post_acute_universe()

    def test_every_class_loaded(self) -> None:
        present = set(self.universe["provider_class"])
        self.assertEqual(present, {s.provider_class for s in CLASS_SPECS})

    def test_one_row_per_ccn(self) -> None:
        self.assertEqual(len(self.universe), self.universe["ccn"].nunique())

    def test_the_shape_is_the_promised_one(self) -> None:
        self.assertEqual(list(self.universe.columns), list(UNIVERSE_COLUMNS))

    def test_the_scale_is_what_makes_it_worth_loading(self) -> None:
        counts = class_counts(self.universe).set_index("provider_class")
        self.assertGreater(int(counts.loc["snf", "facilities"]), 14000)
        self.assertGreater(int(counts.loc["hha", "facilities"]), 12000)
        self.assertGreater(int(counts.loc["dialysis", "facilities"]), 7000)
        self.assertGreater(int(counts.loc["hospice", "facilities"]), 6000)
        self.assertGreater(len(self.universe), 40000)

    def test_state_and_zip_are_normalised(self) -> None:
        states = self.universe["state"]
        self.assertTrue(states.eq(states.str.upper()).all())
        zips = self.universe["zip"]
        self.assertTrue(zips[zips.ne("")].str.len().eq(5).all())

    def test_certification_dates_are_sortable(self) -> None:
        """CMS writes 1969-09-01 in one file and 10/01/1983 in another.
        Carrying both verbatim would make the column unsortable, which is
        the only thing a certification date is for."""
        dates = self.universe["certification_date"]
        present = dates[dates.ne("")]
        self.assertGreater(len(present), 40000)
        self.assertTrue(present.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all())
        self.assertEqual(present.min()[:2], "19")

    def test_an_unparseable_date_becomes_empty_not_a_sentinel(self) -> None:
        """One home-health agency files its certification date as a bare
        "-", which would sort before every real date in the file."""
        from rcm_mc.data.provider_universe import _norm_date

        self.assertEqual(_norm_date("-"), "")
        self.assertEqual(_norm_date("unknown"), "")
        self.assertEqual(_norm_date("10/01/1983"), "1983-10-01")
        self.assertEqual(_norm_date("1969-09-01"), "1969-09-01")
        self.assertEqual(_norm_date(""), "")

    def test_every_class_carries_a_display_label(self) -> None:
        for spec in CLASS_SPECS:
            self.assertEqual(CLASS_LABELS[spec.provider_class], spec.label)
        pairs = self.universe[["provider_class", "provider_class_label"]]
        self.assertEqual(len(pairs.drop_duplicates()), len(CLASS_SPECS))


class ExclusionTests(unittest.TestCase):
    def test_hospital_ccns_can_be_held_out(self) -> None:
        """IRFs and LTCHs that file their own cost report are in HCRIS
        too — 342 of 1,221 and 309 of 317. The HCRIS row is strictly
        richer, so the Compare row is the one that goes."""
        hospital_ccns = frozenset(assign_systems()["ccn"].astype(str))
        full = load_post_acute_universe()
        held_out = load_post_acute_universe(hospital_ccns)
        self.assertGreater(len(full) - len(held_out), 600)
        self.assertEqual(set(held_out["ccn"]) & hospital_ccns, set())

    def test_holding_out_nothing_changes_nothing(self) -> None:
        self.assertEqual(len(load_post_acute_universe(frozenset())),
                         len(load_post_acute_universe()))


class ChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.universe = load_post_acute_universe()

    def test_the_published_chain_is_carried(self) -> None:
        roster = chain_roster(self.universe)
        top = roster.set_index("chain_name")["facilities"]
        self.assertGreater(int(top.get("DaVita", 0)), 2500)
        self.assertGreater(int(top.get("Fresenius Medical Care", 0)), 2500)
        self.assertGreater(int(top.get("US Renal Care, Inc.", 0)), 300)

    def test_independent_is_an_answer_not_a_chain(self) -> None:
        """"Independent" is CMS answering the ownership question, not
        naming a parent. Treating it as a chain would invent the
        country's largest dialysis operator."""
        names = set(chain_roster(self.universe)["chain_name"])
        for non_chain in ("Independent", "Other", "State Owned"):
            self.assertNotIn(non_chain, names)

    def test_only_the_file_that_publishes_a_chain_has_one(self) -> None:
        named = self.universe[self.universe["chain_name"].ne("")]
        self.assertEqual(set(named["provider_class"]), {"dialysis"})
        self.assertGreater(len(named), 6000)


class DegradationTests(unittest.TestCase):
    def test_a_missing_file_does_not_take_the_loader_down(self) -> None:
        import rcm_mc.data.provider_universe as pu

        original = pu._DATA
        try:
            pu._DATA = pu.Path("/definitely/not/here")
            pu._clear_cache()
            out = load_post_acute_universe()
            self.assertTrue(out.empty)
            self.assertEqual(list(out.columns), list(UNIVERSE_COLUMNS))
            self.assertTrue(class_counts(out).empty)
            self.assertTrue(chain_roster(out).empty)
        finally:
            pu._DATA = original
            pu._clear_cache()

    def test_empty_frame_rollups_return_their_shape(self) -> None:
        empty = pd.DataFrame(columns=list(UNIVERSE_COLUMNS))
        self.assertEqual(list(class_counts(empty).columns),
                         ["provider_class", "provider_class_label",
                          "facilities", "with_chain"])
        self.assertEqual(list(chain_roster(empty).columns),
                         ["chain_name", "facilities", "states", "classes"])


if __name__ == "__main__":
    unittest.main()
