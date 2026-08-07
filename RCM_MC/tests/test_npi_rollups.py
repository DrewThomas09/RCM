"""Long-form NPI tables and the rollups over them.

The failure this guards against is a silent fan-out. A rollup grouped on
a per-NPI attribute must have one row per NPI; if a join has quietly
duplicated rows, `rows` drifts above `npis` and every share is wrong
while every number still looks plausible. So every rollup reports both,
and the tests assert the relationship each one should have.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.npi_rollups import (
    ROLLUP_COLUMNS, TAXONOMY_LONG_COLUMNS, npi_taxonomies_long,
    rollup_by_category, rollup_by_entity, rollup_by_parent,
    rollup_by_parent_tier, rollup_by_state, rollup_by_status, rollup_summary,
)


def _frame() -> pd.DataFrame:
    """Two singly-enrolled NPIs and one enrolled three ways."""
    return pd.DataFrame([
        {"npi": "1111111111", "taxonomy_code": "282N00000X",
         "taxonomy_codes": "282N00000X", "entity_label": "organization",
         "state": "AL", "status": "active", "final_parent": "sys:ascension",
         "parent_tier": "ccn_system", "cbsa_title": "Birmingham-Hoover, AL"},
        {"npi": "2222222222", "taxonomy_code": "341600000X",
         "taxonomy_codes": "341600000X", "entity_label": "organization",
         "state": "TX", "status": "deactivated", "final_parent": "",
         "parent_tier": "", "cbsa_title": ""},
        # Enrolled as DME, home health and infusion at once.
        {"npi": "3333333333", "taxonomy_code": "251E00000X",
         "taxonomy_codes": "332B00000X|251E00000X|3336I0012X",
         "entity_label": "organization", "state": "AL", "status": "active",
         "final_parent": "sys:ascension", "parent_tier": "nppes_subpart",
         "cbsa_title": "Birmingham-Hoover, AL"},
    ])


class LongFormTests(unittest.TestCase):
    def test_the_declared_columns_are_present(self) -> None:
        self.assertEqual(list(npi_taxonomies_long(_frame()).columns),
                         list(TAXONOMY_LONG_COLUMNS))

    def test_one_row_per_enrolment_not_per_provider(self) -> None:
        """A pipe-joined cell cannot be grouped on. That is the whole
        reason this table exists."""
        long_form = npi_taxonomies_long(_frame())
        self.assertEqual(len(long_form), 5)
        self.assertEqual(long_form["npi"].nunique(), 3)

    def test_the_primary_flag_marks_exactly_one_row_per_provider(self) -> None:
        long_form = npi_taxonomies_long(_frame())
        per_npi = long_form.groupby("npi")["is_primary"].sum()
        self.assertEqual(set(per_npi), {1})
        # …and it is the switched code, not the first slot: this
        # provider files DME first and home health as primary.
        row = long_form[(long_form["npi"] == "3333333333")
                        & (long_form["is_primary"] == 1)].iloc[0]
        self.assertEqual(row["taxonomy_code"], "251E00000X")

    def test_each_enrolment_carries_its_own_category(self) -> None:
        long_form = npi_taxonomies_long(_frame())
        got = set(long_form[long_form["npi"] == "3333333333"]["taxonomy_category"])
        self.assertEqual(got, {"dme", "home_health", "infusion"})

    def test_an_empty_frame_is_an_empty_typed_table(self) -> None:
        empty = npi_taxonomies_long(pd.DataFrame(columns=["npi"]))
        self.assertTrue(empty.empty)
        self.assertEqual(list(empty.columns), list(TAXONOMY_LONG_COLUMNS))


class CountingRuleTests(unittest.TestCase):
    """The gap between rows and distinct NPIs is the thing to be honest
    about, not the thing to hide."""

    def test_a_per_npi_rollup_has_no_fan_out(self) -> None:
        for rollup in (rollup_by_state, rollup_by_status, rollup_by_entity,
                       rollup_by_parent, rollup_by_parent_tier):
            with self.subTest(rollup=rollup.__name__):
                out = rollup(_frame())
                self.assertTrue((out["rows"] == out["npis"]).all(),
                                f"{rollup.__name__} fanned out")

    def test_the_taxonomy_rollup_counts_every_enrolment(self) -> None:
        """An infusion pharmacy that is also a DME supplier is both, and
        counting it once under one of them answers neither question."""
        out = rollup_by_category(_frame())
        by_key = dict(zip(out["key"], out["npis"], strict=True))
        self.assertEqual(by_key["dme"], 1)
        self.assertEqual(by_key["home_health"], 1)
        self.assertEqual(by_key["infusion"], 1)
        self.assertEqual(int(out["npis"].sum()), 5)

    def test_primary_only_counts_each_provider_once(self) -> None:
        out = rollup_by_category(_frame(), long_form=False)
        self.assertEqual(int(out["npis"].sum()), 3)
        self.assertNotIn("dme", set(out["key"]))

    def test_rollups_declare_their_columns(self) -> None:
        self.assertEqual(list(rollup_by_state(_frame()).columns),
                         list(ROLLUP_COLUMNS))

    def test_shares_sum_to_one(self) -> None:
        self.assertAlmostEqual(float(rollup_by_state(_frame())["share"].sum()),
                               1.0, places=9)

    def test_rows_with_no_parent_are_labelled_not_dropped(self) -> None:
        """They are the majority in most slices. A ranking that hides
        them makes the resolved operators look like the whole market."""
        out = rollup_by_parent(_frame())
        self.assertIn("(no parent)", set(out["key"]))
        self.assertEqual(int(out[out["key"] == "(no parent)"]["npis"].iloc[0]), 1)

    def test_an_empty_frame_rolls_up_to_an_empty_typed_table(self) -> None:
        out = rollup_by_state(pd.DataFrame(columns=["npi", "state"]))
        self.assertTrue(out.empty)
        self.assertEqual(list(out.columns), list(ROLLUP_COLUMNS))


class SummaryTests(unittest.TestCase):
    def test_the_summary_states_the_multi_enrolment_gap(self) -> None:
        summary = rollup_summary(_frame())
        self.assertEqual(summary["npis"], 3)
        self.assertEqual(summary["taxonomy_rows"], 5)
        self.assertEqual(summary["multi_taxonomy_npis"], 1)

    def test_an_empty_summary_is_zero_not_an_exception(self) -> None:
        self.assertEqual(rollup_summary(pd.DataFrame())["npis"], 0)


class RealFileTests(unittest.TestCase):
    """Against the bundled master file, not a fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = rollup_summary()

    def test_it_rolls_up_the_whole_bundled_file(self) -> None:
        self.assertGreater(self.summary["npis"], 20_000)

    def test_the_bundled_slice_carries_one_taxonomy_each(self) -> None:
        """Not a claim about NPPES. The ambulance extract has a single
        taxonomy column, so slots 2-15 are empty here and the
        multi-enrolment gap only opens once the dissemination file is
        ingested. Pinned so that change is visible rather than surprising."""
        self.assertEqual(self.summary["multi_taxonomy_npis"], 0)
        self.assertEqual(self.summary["taxonomy_rows"], self.summary["npis"])

    def test_the_parent_tier_mix_is_reported(self) -> None:
        tiers = {r["key"] for r in self.summary["by_parent_tier"]}
        self.assertIn("pecos_group", tiers)
        self.assertIn("(no parent)", tiers)

    def test_every_rollup_share_sums_to_one(self) -> None:
        for name in ("by_entity", "by_status", "by_parent_tier"):
            with self.subTest(name=name):
                total = sum(r["share"] for r in self.summary[name])
                self.assertAlmostEqual(total, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
