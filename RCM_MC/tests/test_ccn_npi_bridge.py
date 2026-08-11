"""The harvested CCN↔NPI bridge: validation, conflicts, and the join."""

from __future__ import annotations

import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from rcm_mc.data import ccn_npi_bridge as bridge
from rcm_mc.data.ccn_npi_bridge import (
    BRIDGE_COLUMNS,
    BRIDGE_SOURCE,
    BridgeRow,
    bridge_conflicts,
    bridge_summary,
    cross_state_npis,
    load_bridge,
    normalise_ptan,
    ptan_contradictions,
    shared_npis,
)

# Check digits computed with npi_identifier.npi_check_digit, so the
# fixtures pass the same Luhn test the loader applies.
NPI_A = "1234567893"
NPI_B = "1456789019"
NPI_C = "1567890128"
NPI_D = "1678901236"
BAD_CHECK_DIGIT = "1234567890"


def _row(ccn: str, npi: str, **over: str) -> dict:
    row = {
        "ccn": ccn,
        "npi": npi,
        "npi_name": "TEST HOSPITAL",
        "npi_dba": "",
        "npi_taxonomy_code": "282N00000X",
        "npi_taxonomy_desc": "General Acute Care Hospital",
        "npi_street": "1 MAIN ST",
        "npi_city": "SPRINGFIELD",
        "npi_state": "AL",
        "npi_zip": "35801",
        "ptan": "",
        "match_basis": "address+taxonomy",
        "confidence": "high",
    }
    row.update(over)
    return row


class BridgeFixtureCase(unittest.TestCase):
    """Writes a .csv.gz fixture and points the loader at it."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "bridge.csv.gz"
        bridge._clear_cache()

    def tearDown(self) -> None:
        self._dir.cleanup()
        bridge._clear_cache()

    def write(self, rows) -> Path:
        bridge._clear_cache()
        with gzip.open(self.path, "wt", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(BRIDGE_COLUMNS))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return self.path


class LoadTests(BridgeFixtureCase):
    def test_a_missing_file_loads_as_empty_rather_than_raising(self):
        # The harvest is incremental and the enrichment is optional; a
        # missing file must not take the whole crosswalk down.
        missing = Path(self._dir.name) / "not-here.csv.gz"
        self.assertEqual(load_bridge(missing), {})
        self.assertEqual(bridge_conflicts(missing), ())

    def test_a_row_loads_with_every_field_carried_through(self):
        self.write([_row("010039", NPI_A)])
        rows = load_bridge(self.path)
        self.assertEqual(set(rows), {"010039"})
        row = rows["010039"]
        self.assertIsInstance(row, BridgeRow)
        self.assertEqual(row.npi, NPI_A)
        self.assertEqual(row.taxonomy_code, "282N00000X")
        self.assertEqual(row.state, "AL")
        self.assertTrue(row.is_high_confidence)

    def test_a_bad_check_digit_is_dropped(self):
        # The one error class catchable with no network at all: a
        # transcription slip in a harvested file is otherwise silent.
        self.write([_row("010039", BAD_CHECK_DIGIT), _row("010040", NPI_A)])
        self.assertEqual(set(load_bridge(self.path)), {"010040"})

    def test_a_row_with_no_ccn_is_dropped(self):
        self.write([_row("", NPI_A), _row("010040", NPI_B)])
        self.assertEqual(set(load_bridge(self.path)), {"010040"})

    def test_confidence_defaults_to_medium_when_blank(self):
        self.write([_row("010039", NPI_A, confidence="")])
        self.assertEqual(load_bridge(self.path)["010039"].confidence, "medium")

    def test_the_ccn_is_upper_cased_so_lookups_are_stable(self):
        self.write([_row("01aaa9", NPI_A)])
        self.assertIn("01AAA9", load_bridge(self.path))


class PtanTests(BridgeFixtureCase):
    def test_a_ptan_normalises_to_the_ccn_it_encodes(self):
        # MACs write the institutional number several ways; all three
        # spellings are CCN 020001.
        for spelling in ("02-0001", "020001", "02 0001"):
            self.assertEqual(normalise_ptan(spelling), "020001", spelling)

    def test_a_ptan_that_is_not_a_ccn_normalises_to_nothing(self):
        # Practitioner and legacy PTANs are not six characters; saying
        # "" beats guessing at a CCN they do not encode.
        for other in ("", "1234", "ABCDEF", "1234567890", None):
            self.assertEqual(normalise_ptan(other), "")

    def test_a_ptan_naming_another_ccn_drops_the_row(self):
        # The provider filed the number themselves — this is never a
        # judgement call.
        self.write([_row("010039", NPI_A, ptan="45-0100"),
                    _row("010040", NPI_B)])
        self.assertEqual(set(load_bridge(self.path)), {"010040"})
        bad = ptan_contradictions(self.path)
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0].ccn, bad[0].npi, bad[0].ptan_ccn),
                         ("010039", NPI_A, "450100"))

    def test_a_matching_ptan_marks_the_row_confirmed(self):
        self.write([_row("010039", NPI_A, ptan="01-0039", match_basis="ptan")])
        row = load_bridge(self.path)["010039"]
        self.assertTrue(row.is_ptan_confirmed)
        self.assertEqual(bridge_summary(self.path)["ptan_confirmed"], 1)

    def test_a_ptan_confirmed_row_outranks_an_address_match(self):
        # An address match that got there first must not shut out the
        # provider's own filing.
        self.write([_row("010039", NPI_A),
                    _row("010039", NPI_B, ptan="01-0039", match_basis="ptan")])
        kept = load_bridge(self.path)["010039"]
        self.assertEqual(kept.npi, NPI_B)
        self.assertTrue(kept.is_ptan_confirmed)
        self.assertEqual(bridge_conflicts(self.path)[0].rejected, (NPI_A,))

    def test_an_address_match_does_not_displace_a_ptan_confirmed_row(self):
        self.write([_row("010039", NPI_B, ptan="01-0039", match_basis="ptan"),
                    _row("010039", NPI_A)])
        self.assertEqual(load_bridge(self.path)["010039"].npi, NPI_B)
        self.assertEqual(bridge_conflicts(self.path)[0].rejected, (NPI_A,))


class ConflictTests(BridgeFixtureCase):
    def test_a_ccn_claimed_by_two_npis_keeps_the_first_and_reports_it(self):
        # Whichever row sorted last silently winning would hide the
        # fact that the harvest contradicted itself.
        self.write([_row("010039", NPI_A), _row("010039", NPI_B)])
        self.assertEqual(load_bridge(self.path)["010039"].npi, NPI_A)
        conflicts = bridge_conflicts(self.path)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].ccn, "010039")
        self.assertEqual(conflicts[0].kept, NPI_A)
        self.assertEqual(conflicts[0].rejected, (NPI_B,))

    def test_the_same_row_twice_is_not_a_conflict(self):
        self.write([_row("010039", NPI_A), _row("010039", NPI_A)])
        self.assertEqual(bridge_conflicts(self.path), ())

    def test_one_npi_over_several_ccns_is_reported_not_refused(self):
        # A hospital with a distinct-part rehab unit holds several CCNs
        # under one enumeration. That is the parent_ccn relationship,
        # not an error.
        self.write([_row("010039", NPI_A), _row("013027", NPI_A)])
        self.assertEqual(len(load_bridge(self.path)), 2)
        self.assertEqual(shared_npis(self.path), {NPI_A: ("010039", "013027")})
        self.assertEqual(cross_state_npis(self.path), {})

    def test_one_npi_across_two_states_is_surfaced_as_suspect(self):
        # The CCN's first two digits are its state code, so this needs
        # no join. Two states means a corporate NPI got attached to a
        # local facility.
        self.write([_row("010039", NPI_A), _row("450039", NPI_A)])
        self.assertEqual(cross_state_npis(self.path),
                         {NPI_A: ("010039", "450039")})


class SummaryTests(BridgeFixtureCase):
    def test_the_summary_counts_coverage_and_its_caveats_together(self):
        self.write([
            _row("010039", NPI_A),
            _row("013027", NPI_A),                       # shared, same state
            _row("450100", NPI_B, confidence="medium"),  # other state
            _row("450101", NPI_C),
            _row("450101", NPI_D),                       # conflict
        ])
        summary = bridge_summary(self.path)
        self.assertEqual(summary["ccns_resolved"], 4)
        self.assertEqual(summary["distinct_npis"], 3)
        self.assertEqual(summary["high_confidence"], 3)
        self.assertEqual(summary["medium_confidence"], 1)
        self.assertEqual(summary["states"], 2)
        self.assertEqual(summary["conflicting_ccns"], 1)
        self.assertEqual(summary["ptan_contradictions"], 0)
        self.assertEqual(summary["npis_covering_several_ccns"], 1)
        self.assertEqual(summary["npis_spanning_states"], 0)

    def test_an_empty_bridge_summarises_to_zeroes(self):
        self.write([])
        summary = bridge_summary(self.path)
        self.assertEqual(summary["ccns_resolved"], 0)
        self.assertEqual(summary["conflicting_ccns"], 0)


class ShippedBridgeTests(unittest.TestCase):
    """Whatever is shipped must satisfy the module's own invariants."""

    def setUp(self) -> None:
        bridge._clear_cache()

    def test_every_shipped_row_carries_a_state_coded_ccn(self):
        for ccn in load_bridge():
            self.assertTrue(ccn[:2].isdigit(), ccn)

    def test_the_shipped_bridge_does_not_contradict_itself(self):
        self.assertEqual(bridge_conflicts(), ())

    def test_no_shipped_npi_is_stretched_across_states(self):
        self.assertEqual(cross_state_npis(), {})

    def test_no_shipped_ptan_contradicts_its_own_row(self):
        self.assertEqual(ptan_contradictions(), ())


class CrosswalkJoinTests(unittest.TestCase):
    """The bridge has to actually reach the crosswalk, and be labelled."""

    def test_the_crosswalk_prefers_the_bridge_over_name_matching(self):
        from rcm_mc.data.provider_crosswalk import _npi_for

        rows = load_bridge()
        if not rows:
            self.skipTest("no bridge shipped yet")
        ccn, row = next(iter(rows.items()))
        npi, source, taxonomy = _npi_for(
            {"ccn": ccn, "name": "NOTHING LIKE THE REAL NAME", "state": "ZZ"},
            "00000", {}, row.taxonomy_code)
        self.assertEqual(npi, row.npi)
        self.assertIn(BRIDGE_SOURCE, source)
        self.assertEqual(taxonomy, row.taxonomy_code)

    def test_a_bridge_row_of_the_wrong_provider_kind_is_still_rejected(self):
        # Keying on the CCN removes the ambiguity about which facility,
        # not the one about which of that facility's enumerations.
        from rcm_mc.data.provider_crosswalk import _npi_for

        rows = load_bridge()
        if not rows:
            self.skipTest("no bridge shipped yet")
        ccn, row = next(iter(rows.items()))
        npi, source, _ = _npi_for(
            {"ccn": ccn, "name": "", "state": ""}, "", {}, "3140N0000X")
        self.assertEqual(npi, "")
        self.assertEqual(source, "")


if __name__ == "__main__":
    unittest.main()
