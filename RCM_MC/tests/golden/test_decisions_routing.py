"""Golden test for BOLSTER-06 DECISIONS.md routing pattern.

Asserts every non-default choice has a decision entry, the parser reads the
session log, the append helper writes the canonical format, and the missing
check catches an uncovered choice.
"""
import os
import tempfile
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.decisions import (
    NON_DEFAULT_CHOICES,
    append_decision,
    covered_features,
    missing_decisions,
)


class TestDecisionsRouting(unittest.TestCase):
    def test_no_missing_decisions_in_session_log(self):
        missing = missing_decisions()
        self.assertEqual(missing, [],
                         msg=f"non-default choices lacking a decision entry: {missing}")

    def test_session_log_covers_known_features(self):
        covered = covered_features()
        for fid in ("NEW-01", "NEW-02", "BOLSTER-01", "BOLSTER-03"):
            self.assertIn(fid, covered)

    def test_append_and_parse_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "DECISIONS.md")
            with open(path, "w") as fh:
                fh.write("# DECISIONS\n")
            self.assertEqual(covered_features(path), {})
            append_decision("NEW-99", "Test choice", context="c", options="A/B",
                            decision="B", rationale="r", validation="v", path=path)
            self.assertIn("NEW-99", covered_features(path))

    def test_missing_check_flags_uncovered(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "DECISIONS.md")
            with open(path, "w") as fh:
                fh.write("# DECISIONS\n")  # nothing covered
            missing = missing_decisions(path, choices={"NEW-01": "x", "NEW-02": "y"})
            self.assertEqual(set(missing), {"NEW-01", "NEW-02"})

    def test_demo_reconciles_when_log_current(self):
        ex = registry.get("BOLSTER-06").demo()
        self.assertTrue(ex.reconciled)
        self.assertEqual(ex.meta["missing"], [])

    def test_every_non_default_choice_is_a_real_feature(self):
        # Each declared choice must map to a registered feature.
        registered = set(registry.feature_ids())
        for fid in NON_DEFAULT_CHOICES:
            self.assertIn(fid, registered, msg=f"{fid} declared but not registered")


if __name__ == "__main__":
    unittest.main()
