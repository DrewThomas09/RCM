"""The gate a proposed registry entry has to clear.

Every assertion here is about *refusal*. The registry went from 382
entries to 896 in one sweep, and that is only safe because nothing was
taken on trust — so the tests that matter are the ones proving the gate
says no, and says no for the right reason.

The cases are the real ones. A bare ``^SAINT`` really was proposed and
really would have taken 302 mapped facilities from Ascension,
CommonSpirit, Mayo and MedStar. Medical Services of America really came
back three times under three identifiers, which is why dedup is on the
facilities claimed and not on the name.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.registry_proposals import (
    COLLISION_FAMILIES, Proposal, check, check_batch, compile_pattern,
    dedupe_by_claim, render_system_def, summarise,
)


def _register() -> pd.DataFrame:
    """A miniature register: two mapped facilities and four free ones."""
    return pd.DataFrame([
        {"ccn": "010011", "name": "ASCENSION SAINT VINCENTS", "state": "AL",
         "system_id": "ascension", "provider_class": "hospital"},
        {"ccn": "450358", "name": "THE METHODIST HOSPITAL", "state": "TX",
         "system_id": "houston_methodist", "provider_class": "hospital"},
        {"ccn": "157034", "name": "Caretenders", "state": "IN",
         "system_id": "_unmapped", "provider_class": "hha"},
        {"ccn": "187084", "name": "CARETENDERS", "state": "KY",
         "system_id": "_unmapped", "provider_class": "hha"},
        {"ccn": "500001", "name": "SAINT MARYS HOSPITAL", "state": "WA",
         "system_id": "_unmapped", "provider_class": "hospital"},
        {"ccn": "500002", "name": "HARBORVIEW HEALTH CENTER", "state": "GA",
         "system_id": "_unmapped", "provider_class": "snf"},
    ])


def _proposal(**kwargs) -> Proposal:
    base = {"system_id": "x", "name": "X", "patterns": ("^X",), "states": ()}
    base.update(kwargs)
    return Proposal.from_dict(base)


class CompileTests(unittest.TestCase):
    """The gate must compile a pattern the way the matcher will. A gate
    that compiles differently clears patterns that then behave
    differently in production, which is the failure it exists to stop."""

    def test_a_state_prefix_is_a_scope_not_part_of_the_name(self) -> None:
        scope, regex = compile_pattern("TX:^BAPTIST MEDICAL")
        self.assertEqual(scope, ("TX",))
        self.assertTrue(regex.search("BAPTIST MEDICAL CENTER"))

    def test_several_states_scope_one_pattern(self) -> None:
        scope, _ = compile_pattern("TN,KY,GA:^TRISTAR")
        self.assertEqual(scope, ("TN", "KY", "GA"))

    def test_a_short_pattern_stops_at_a_word_boundary(self) -> None:
        """^CHI must not reach CHINLE. That is incident number one."""
        _, regex = compile_pattern("^CHI")
        self.assertTrue(regex.search("CHI SAINT LUKES"))
        self.assertIsNone(regex.search("CHINLE COMPREHENSIVE"))

    def test_a_long_pattern_matches_as_a_bare_prefix(self) -> None:
        """Ten characters and over, the matcher drops the boundary — so
        ^MONUMENT HEALTH also reaches MONUMENT HEALTHCARE. The gate has
        to reproduce that or it under-reports what a pattern claims."""
        _, regex = compile_pattern("^MONUMENT HEALTH")
        self.assertTrue(regex.search("MONUMENT HEALTHCARE MURRAY CREEK"))

    def test_an_empty_pattern_matches_nothing_rather_than_everything(self):
        _, regex = compile_pattern("^")
        self.assertIsNone(regex.search("ANY HOSPITAL AT ALL"))


class RefusalTests(unittest.TestCase):
    def test_it_refuses_taking_a_facility_another_system_holds(self) -> None:
        """The proposal is not adding coverage, it is overwriting a
        curated answer."""
        verdict = check(_proposal(system_id="s", name="S",
                                  patterns=("^ASCENSION",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertFalse(verdict.ok)
        self.assertIn("already held by ascension", " ".join(verdict.refusals))
        self.assertEqual(verdict.conflicts, (("010011", "ascension"),))

    def test_it_refuses_a_collision_family_with_no_state_scope(self) -> None:
        """A bare ^SAINT was really proposed. Unscoped it is the shape of
        all three incidents this repo has shipped."""
        verdict = check(_proposal(system_id="s", name="S",
                                  patterns=("^SAINT",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertFalse(verdict.ok)
        self.assertIn("collision family", " ".join(verdict.refusals))

    def test_the_same_family_is_allowed_once_it_is_scoped(self) -> None:
        """Scoped patterns are how the registry already carries Saint
        Joseph's of Atlanta. The rule is about reach, not the word."""
        verdict = check(_proposal(system_id="s", name="S",
                                  patterns=("WA:^SAINT MARYS",),
                                  states=("WA",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertTrue(verdict.ok, verdict.refusals)
        self.assertEqual(verdict.facilities, 1)

    def test_it_refuses_a_pattern_that_matches_nothing(self) -> None:
        """Almost always a typo, and a dead entry is upkeep with no
        coverage behind it."""
        verdict = check(_proposal(patterns=("^ZZQQXX",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertFalse(verdict.ok)
        self.assertIn("no facility", " ".join(verdict.refusals))

    def test_it_refuses_an_identifier_or_name_already_in_use(self) -> None:
        verdict = check(_proposal(system_id="ascension", name="Caretenders",
                                  patterns=("^CARETENDERS",)), _register(),
                        taken_ids={"ascension"}, taken_names={"caretenders"})
        self.assertFalse(verdict.ok)
        self.assertEqual(len(verdict.refusals), 2)

    def test_a_scope_confines_the_claim_rather_than_failing_it(self) -> None:
        """Caretenders is in IN and KY. Scoped to IN it claims one."""
        verdict = check(_proposal(system_id="c", name="C",
                                  patterns=("^CARETENDERS",),
                                  states=("IN",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertTrue(verdict.ok, verdict.refusals)
        self.assertEqual(verdict.states_reached, ("IN",))


class AcceptanceTests(unittest.TestCase):
    def test_a_clean_proposal_reports_what_it_claims(self) -> None:
        verdict = check(_proposal(system_id="caretenders", name="Caretenders",
                                  patterns=("^CARETENDERS",)), _register(),
                        taken_ids=set(), taken_names=set())
        self.assertTrue(verdict.ok, verdict.refusals)
        self.assertEqual(verdict.facilities, 2)
        self.assertEqual(verdict.states_reached, ("IN", "KY"))

    def test_a_batch_accumulates_what_it_has_already_accepted(self) -> None:
        """Otherwise the second proposal of one operator in a single
        batch passes, and two entries ship under one name."""
        first = _proposal(system_id="c1", name="Caretenders",
                          patterns=("^CARETENDERS",))
        second = _proposal(system_id="c1", name="Caretenders Again",
                           patterns=("^CARETENDERS",))
        verdicts = check_batch([first, second], _register())
        self.assertTrue(verdicts[0].ok)
        self.assertFalse(verdicts[1].ok)
        self.assertIn("already taken", " ".join(verdicts[1].refusals))


class DedupeTests(unittest.TestCase):
    """A state-by-state sweep finds a multi-state operator once per state
    it touches, under a different identifier each time."""

    def test_the_same_operator_under_two_names_collapses_to_one(self) -> None:
        register = _register()
        a = check(_proposal(system_id="caretenders_in", name="A",
                            patterns=("^CARETENDERS",), states=("IN",)),
                  register, taken_ids=set(), taken_names=set())
        b = check(_proposal(system_id="caretenders", name="B",
                            patterns=("^CARETENDERS",)),
                  register, taken_ids=set(), taken_names=set())
        merged = dedupe_by_claim([a, b])
        self.assertEqual(len(merged), 1)
        # The survivor is the one reaching more facilities.
        self.assertEqual(merged[0].proposal.system_id, "caretenders")

    def test_operators_that_share_no_facility_both_survive(self) -> None:
        register = _register()
        a = check(_proposal(system_id="c", name="C",
                            patterns=("^CARETENDERS",)), register,
                  taken_ids=set(), taken_names=set())
        b = check(_proposal(system_id="h", name="H",
                            patterns=("GA:^HARBORVIEW",), states=("GA",)),
                  register, taken_ids=set(), taken_names=set())
        self.assertEqual(len(dedupe_by_claim([a, b])), 2)

    def test_a_refused_proposal_never_survives_dedup(self) -> None:
        register = _register()
        bad = check(_proposal(patterns=("^ZZQQ",)), register,
                    taken_ids=set(), taken_names=set())
        self.assertEqual(dedupe_by_claim([bad]), [])

    def test_the_survivor_does_not_change_between_runs(self) -> None:
        """Ties break on the shorter identifier so a rerun writes the
        same registry rather than renaming an entry."""
        register = _register()
        pair = [
            check(_proposal(system_id="bbbb", name="B",
                            patterns=("^CARETENDERS",)), register,
                  taken_ids=set(), taken_names=set()),
            check(_proposal(system_id="aa", name="A",
                            patterns=("^CARETENDERS",)), register,
                  taken_ids=set(), taken_names=set()),
        ]
        self.assertEqual(dedupe_by_claim(pair)[0].proposal.system_id,
                         dedupe_by_claim(pair[::-1])[0].proposal.system_id)


class RenderTests(unittest.TestCase):
    """515 entries is more than anyone transcribes without a mistake."""

    def test_it_emits_a_parseable_system_def(self) -> None:
        text = render_system_def(
            _proposal(system_id="c", name="Caretenders",
                      patterns=("^CARETENDERS", "OH:CARETENDERS"),
                      states=("IN", "KY"), hq_state="KY"),
            kind_const="KIND_FOR_PROFIT", focus_const="FOCUS_HOME_HEALTH")
        self.assertIn('"c", "Caretenders"', text)
        self.assertIn('patterns=("^CARETENDERS", "OH:CARETENDERS")', text)
        self.assertIn('states=("IN", "KY")', text)
        self.assertIn("KIND_FOR_PROFIT, FOCUS_HOME_HEALTH", text)

    def test_a_single_pattern_keeps_its_trailing_comma(self) -> None:
        """("^X") is a string; ("^X",) is a tuple. Without the comma the
        entry iterates character by character."""
        text = render_system_def(_proposal(patterns=("^X",)),
                                 kind_const="KIND_NON_PROFIT",
                                 focus_const="FOCUS_ACUTE")
        self.assertIn('patterns=("^X",)', text)

    def test_an_unscoped_entry_omits_the_states_line(self) -> None:
        text = render_system_def(_proposal(patterns=("^X",), states=()),
                                 kind_const="KIND_NON_PROFIT",
                                 focus_const="FOCUS_ACUTE")
        self.assertNotIn("states=", text)

    def test_a_quote_in_a_name_cannot_break_the_source(self) -> None:
        text = render_system_def(
            _proposal(name='King\'s "Daughters"', patterns=("^KINGS",)),
            kind_const="KIND_NON_PROFIT", focus_const="FOCUS_ACUTE")
        self.assertIn(r'\"Daughters\"', text)


class SummaryTests(unittest.TestCase):
    def test_it_groups_refusals_by_shape_not_by_wording(self) -> None:
        """The reason strings carry identifiers and counts, so grouping
        on the raw text gives one bucket per refusal and tells a reviewer
        nothing about the batch."""
        register = _register()
        verdicts = [
            check(_proposal(system_id="a", name="A", patterns=("^SAINT",)),
                  register, taken_ids=set(), taken_names=set()),
            check(_proposal(system_id="b", name="B", patterns=("^MERCY",)),
                  register, taken_ids=set(), taken_names=set()),
        ]
        reasons = summarise(verdicts)["refusal_reasons"]
        self.assertEqual(reasons.get("collision family with no state scope"), 2)

    def test_an_empty_batch_summarises_to_zeros(self) -> None:
        self.assertEqual(summarise([])["proposed"], 0)


class RealRegisterTests(unittest.TestCase):
    """Against the register on disk, where the sweep actually ran."""

    def test_a_bare_saint_is_refused_against_the_real_register(self) -> None:
        verdict = check(_proposal(system_id="probe", name="Probe Only",
                                  patterns=("^SAINT",)))
        self.assertFalse(verdict.ok)
        self.assertGreater(len(verdict.conflicts), 200)

    def test_an_entry_already_in_the_registry_is_refused(self) -> None:
        verdict = check(_proposal(system_id="ascension", name="Probe Two",
                                  patterns=("^ASCENSION",)))
        self.assertFalse(verdict.ok)
        self.assertIn("already taken", " ".join(verdict.refusals))

    def test_the_gate_is_mechanical_and_says_so(self) -> None:
        """^BROOKDALE passes here — the Brooklyn hospital it collides
        with is itself unmapped, so nothing is being taken. It is the
        invariants in test_health_system_lookup that refuse it, and this
        test exists so nobody mistakes a pass here for a verdict."""
        verdict = check(_proposal(system_id="probe_three", name="Probe Three",
                                  patterns=("^BROOKDALE",)))
        self.assertTrue(verdict.ok, verdict.refusals)


if __name__ == "__main__":
    unittest.main()
