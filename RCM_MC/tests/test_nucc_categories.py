"""The NUCC classifier is checked against reference data, not against itself.

The module derives a Level-I grouping and a PE category from the shape of
a NUCC code, because the published 870-code set is not reachable from
this build and writing it out from memory would be inventing reference
data. A derivation is only worth anything if something independent
agrees with it, so these tests do not assert the tables against
themselves — they assert them against the three vetted NUCC sources that
were already in this repository before the classifier existed:

  * ``rcm_mc.data_public.nucc_taxonomy`` — 12 codes carrying the official
    NUCC grouping string and a PE vertical tag,
  * ``rcm_mc.npi_cleaner.refdata.TAXONOMY_SPECIALTIES`` — ~70 curated
    code → specialty labels,
  * ``npi_recovery/reference/infusion_taxonomies.csv`` — 25 codes with
    site-class tags.

and against every distinct taxonomy code that appears in the repository's
real provider data. If a future edit to the prefix tables contradicts any
of those, one of these fails.
"""
from __future__ import annotations

import csv
import re
import unittest
from pathlib import Path
from typing import Dict, Set

from rcm_mc.data.nucc_categories import (
    NUCC_CODE_RE, all_categories, classify_taxonomy, is_organisation_taxonomy,
    load_nucc_table, taxonomy_category, taxonomy_label, taxonomy_level_i,
)
from rcm_mc.data_public import nucc_taxonomy as curated
from rcm_mc.npi_cleaner.refdata import TAXONOMY_SPECIALTIES

_REPO = Path(__file__).resolve().parents[1]
_INFUSION_CSV = (_REPO / "rcm_mc" / "npi_cleaner" / "vendor_v49"
                 / "npi_recovery" / "reference" / "infusion_taxonomies.csv")

#: ``data_public`` tags verticals in its own vocabulary; two of them are
#: spelled differently here. Everything else must match name-for-name.
_VERTICAL_TO_CATEGORY = {
    "asc": "ambulatory_surgery",
    "physician_primary_care": "physician",
}


def _infusion_reference_codes() -> Set[str]:
    with _INFUSION_CSV.open(newline="", encoding="utf-8") as fh:
        return {row["taxonomy_code"].strip().upper()
                for row in csv.DictReader(fh)}


class CodeShapeTests(unittest.TestCase):
    def test_regex_accepts_codes_that_do_not_end_in_x(self):
        # 261QI0500N is a real code sitting beside 261QI0500X. A pattern
        # that assumed a trailing "X" would drop it silently.
        self.assertTrue(NUCC_CODE_RE.match("261QI0500N"))
        self.assertTrue(NUCC_CODE_RE.match("251F00000X"))

    def test_malformed_codes_classify_to_nothing_rather_than_a_guess(self):
        for junk in ("", None, "   ", "28", "282N0000", "282N00000XX",
                     "X82N00000X", "679576722E"):
            with self.subTest(junk=junk):
                t = classify_taxonomy(junk)
                self.assertEqual(t.level_i, "")
                self.assertEqual(t.category, "")
                self.assertFalse(t.is_organisation)
                self.assertFalse(t.is_known)

    def test_the_unused_35_block_is_rejected_not_invented(self):
        # NUCC has 29 Level-I groupings and none of them is "35".
        t = classify_taxonomy("350000000X")
        self.assertEqual(t.level_i, "")
        self.assertFalse(t.is_organisation)

    def test_lookup_is_case_and_whitespace_insensitive(self):
        self.assertEqual(taxonomy_category("  282n00000x  "), "hospital")


class CuratedCrosswalkAgreementTests(unittest.TestCase):
    """``data_public/nucc_taxonomy`` carries the official grouping string.
    The derived grouping has to reproduce it exactly."""

    def test_every_curated_grouping_is_reproduced_from_the_code_alone(self):
        for tax in curated.all_taxonomies():
            with self.subTest(code=tax.code):
                self.assertEqual(taxonomy_level_i(tax.code), tax.grouping)

    def test_every_curated_vertical_is_reproduced_as_a_category(self):
        for tax in curated.all_taxonomies():
            expected = _VERTICAL_TO_CATEGORY.get(tax.vertical, tax.vertical)
            with self.subTest(code=tax.code, vertical=tax.vertical):
                self.assertEqual(taxonomy_category(tax.code), expected)

    def test_the_three_infusion_codes_agree_despite_three_groupings(self):
        # Infusion is the case that proves the refinement layer earns its
        # keep: the same category arrives via Ambulatory Health Care
        # Facilities, Suppliers and Agencies.
        codes = ["261QI0500N", "3336I0012X", "251F00000X"]
        self.assertEqual([taxonomy_category(c) for c in codes],
                         ["infusion"] * 3)
        self.assertEqual(len({taxonomy_level_i(c) for c in codes}), 3)


class ReferenceFileCoverageTests(unittest.TestCase):
    """Every code in the repository's vetted reference files must resolve."""

    def _all_reference_codes(self) -> Set[str]:
        codes = set(TAXONOMY_SPECIALTIES) | _infusion_reference_codes()
        codes |= {t.code for t in curated.all_taxonomies()}
        return codes

    def test_every_reference_code_is_well_formed(self):
        for code in sorted(self._all_reference_codes()):
            with self.subTest(code=code):
                self.assertTrue(NUCC_CODE_RE.match(code))

    def test_every_reference_code_resolves_to_a_grouping(self):
        unresolved = sorted(c for c in self._all_reference_codes()
                            if not taxonomy_level_i(c))
        self.assertEqual(unresolved, [])

    def test_almost_every_reference_code_resolves_to_a_category(self):
        # "Other Service Providers" (17xx) declines to say what the
        # provider is, so we decline too — 174200000X (meal delivery) is
        # the only reference code that legitimately has no category.
        uncategorised = sorted(c for c in self._all_reference_codes()
                               if not taxonomy_category(c))
        self.assertEqual(uncategorised, ["174200000X"])


class RepositoryDataCoverageTests(unittest.TestCase):
    """The real test of a derivation: sweep the codes actually present in
    this repository's provider data and require every one to resolve."""

    _SWEEP = re.compile(rb"\b[0-9]{3}[0-9A-Z]{6}[A-Z]\b")
    #: A ten-character alphanumeric run is not always a taxonomy code.
    #: This one is an identifier in an unrelated fixture and is excluded
    #: by name so the sweep cannot be quietly widened to hide a failure.
    _NOT_A_TAXONOMY = {"679576722E"}

    def _codes_in_repo(self) -> Set[str]:
        found: Set[str] = set()
        for path in (_REPO / "rcm_mc").rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".csv", ".json"}:
                continue
            try:
                blob = path.read_bytes()
            except OSError:
                continue
            found.update(m.decode() for m in self._SWEEP.findall(blob))
        return found - self._NOT_A_TAXONOMY

    def test_every_taxonomy_code_in_the_repository_resolves(self):
        codes = self._codes_in_repo()
        self.assertGreater(len(codes), 100, "sweep found suspiciously few codes")
        unresolved = sorted(c for c in codes if not taxonomy_level_i(c))
        self.assertEqual(unresolved, [])

    def test_organisation_flag_splits_the_repository_codes_sensibly(self):
        codes = self._codes_in_repo()
        orgs = {c for c in codes if is_organisation_taxonomy(c)}
        people = codes - orgs
        # Both sides are populated — a flag that says "everything" or
        # "nothing" would pass a weaker assertion.
        self.assertGreater(len(orgs), 10)
        self.assertGreater(len(people), 10)
        # And the split is the one the code prefix implies.
        self.assertTrue(all(c[:2] in {"19", "25", "26", "27", "28", "29",
                                      "30", "31", "32", "33", "34", "38"}
                            for c in orgs))


class OrganisationFlagTests(unittest.TestCase):
    def test_facilities_are_organisations_and_clinicians_are_not(self):
        for code in ("282N00000X", "314000000X", "251E00000X", "341600000X",
                     "3336I0012X", "291U00000X", "261Q00000X"):
            with self.subTest(code=code):
                self.assertTrue(is_organisation_taxonomy(code))
                self.assertFalse(classify_taxonomy(code).is_individual)
        for code in ("207Q00000X", "163W00000X", "363L00000X", "122300000X",
                     "213E00000X"):
            with self.subTest(code=code):
                self.assertFalse(is_organisation_taxonomy(code))
                self.assertTrue(classify_taxonomy(code).is_individual)


class RefinementTests(unittest.TestCase):
    """A refinement must be narrower than its grouping, never a
    contradiction of it, and must not leak to unrelated siblings."""

    def test_refinements_do_not_leak_to_sibling_specialisations(self):
        # 261Q is Clinic/Center generally; only the specialisations we can
        # vouch for get a narrower category.
        self.assertEqual(taxonomy_category("261Q00000X"), "clinic")
        self.assertEqual(taxonomy_category("261QC1500X"), "clinic")
        self.assertEqual(taxonomy_category("261QE0700X"), "dialysis")
        self.assertEqual(taxonomy_category("261QU0200X"), "urgent_care")

    def test_longest_prefix_wins(self):
        # 3336 is a pharmacy; 3336I and 3336H are infusion pharmacies.
        self.assertEqual(taxonomy_category("333600000X"), "pharmacy")
        self.assertEqual(taxonomy_category("3336C0003X"), "pharmacy")
        self.assertEqual(taxonomy_category("3336I0012X"), "infusion")
        self.assertEqual(taxonomy_category("3336H0001X"), "infusion")
        # …and the grouping stays Suppliers for all of them.
        for code in ("333600000X", "3336I0012X", "332B00000X"):
            self.assertEqual(taxonomy_level_i(code), "Suppliers")

    def test_supplier_default_survives_where_no_refinement_applies(self):
        self.assertEqual(taxonomy_category("3336S0011X"), "pharmacy")
        self.assertEqual(taxonomy_category("332BX2000X"), "dme")

    def test_declared_categories_cover_everything_the_module_emits(self):
        declared = set(all_categories())
        emitted = {taxonomy_category(c) for c in TAXONOMY_SPECIALTIES}
        emitted |= {taxonomy_category(t.code) for t in curated.all_taxonomies()}
        emitted.discard("")
        self.assertTrue(emitted <= declared, emitted - declared)


class LabelTests(unittest.TestCase):
    def test_label_falls_back_to_the_grouping_when_nothing_is_vendored(self):
        # No NUCC CSV is bundled in this build, so the label degrades to
        # the derived grouping rather than to an invented string.
        self.assertEqual(load_nucc_table(), {})
        self.assertEqual(taxonomy_label("282N00000X"), "Hospitals")

    def test_label_of_a_junk_code_is_the_code(self):
        self.assertEqual(taxonomy_label("NOT-A-CODE"), "NOT-A-CODE")


class CategoryVocabularyTests(unittest.TestCase):
    def test_category_names_are_stable_snake_case_tokens(self):
        for name in all_categories():
            with self.subTest(name=name):
                self.assertRegex(name, r"^[a-z][a-z_]*[a-z]$")

    def test_the_categories_a_deal_team_screens_on_are_all_present(self):
        must_have = {"hospital", "snf", "home_health", "hospice", "dialysis",
                     "ambulance", "infusion", "pharmacy", "dme", "physician",
                     "behavioral", "lab", "clinic", "urgent_care",
                     "ambulatory_surgery"}
        self.assertTrue(must_have <= set(all_categories()),
                        must_have - set(all_categories()))


if __name__ == "__main__":
    unittest.main()
