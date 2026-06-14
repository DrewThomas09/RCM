"""Golden test for BOLSTER-05 chart-pack rendering standards.

Sweeps every registered feature and asserts:
- zero standards violations (footnote with source/vintage/assumptions, IBCS
  green/red/blue waterfall convention, no em-dashes in labels or titles),
- snapshots are stable across two renders (deterministic structure),
- the validator actually catches an injected violation.
"""
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.chartpack import audit_standards, snapshot_exhibit, validate_standards
from rcm_mc.cdd.exhibit import Footnote, Series


class TestChartpackStandards(unittest.TestCase):
    def test_no_violations_across_registry(self):
        report = audit_standards()
        self.assertTrue(report)
        for fid, violations in report.items():
            self.assertEqual(violations, [], msg=f"{fid} standards violations: {violations}")

    def test_every_feature_has_footnote_metadata(self):
        for f in registry.all_features():
            fn = f.demo().render(internal_mode=True)["footnote"]
            self.assertTrue(fn["source"], f"{f.feature_id} missing source")
            self.assertTrue(fn["vintage"], f"{f.feature_id} missing vintage")
            self.assertTrue(fn["assumptions"], f"{f.feature_id} missing assumptions")

    def test_snapshots_stable_on_two_renders(self):
        # Two datasets: the demo and a re-run; deterministic so snapshots match.
        for f in registry.all_features():
            a = snapshot_exhibit(f.demo())
            b = snapshot_exhibit(f.demo())
            self.assertEqual(a, b, msg=f"{f.feature_id} snapshot not stable")

    def test_validator_catches_emdash(self):
        ex = registry.get("NEW-01").demo()
        # Inject an em-dash into a series name post-build and re-validate.
        ex.series.append(Series(name="bad", points=[{"label": "a", "value": 1}]))
        # Bypass copy lint by mutating the rendered structure is not possible;
        # instead validate a hand-built exhibit-like via a label with a dash.
        ex.series[-1].points[0]["label"] = "2024" + "—" + "2025"
        violations = validate_standards(ex)
        self.assertTrue(any("em-dash" in v for v in violations))

    def test_validator_catches_waterfall_color_violation(self):
        ex = registry.get("NEW-02").demo()
        wf = next(s for s in ex.series if s.kind == "waterfall")
        # Flip a start point to a wrong color.
        for pt in wf.points:
            if pt["kind"] == "start":
                pt["color"] = "green"
                break
        self.assertTrue(any("not blue" in v for v in validate_standards(ex)))

    def test_clean_exhibit_has_no_violations(self):
        self.assertEqual(validate_standards(registry.get("NEW-16").demo()), [])


if __name__ == "__main__":
    unittest.main()
