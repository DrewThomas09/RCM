"""Golden test for the CDD foundation: exhibit contract, copy linting, registry.

Guards the Part 4 hard constraints that every feature relies on:
- em-dash and AI-filler rejection in user-facing copy,
- audience separation enforced in code (partner render strips assumptions),
- every registered feature resolves and renders, carries a footnote, and emits
  reconciliations that are machine-readable.
"""
import json
import os
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.cli import main as cli_main
from rcm_mc.cdd.exhibit import (
    AssumptionNode,
    CopyError,
    Exhibit,
    Footnote,
    Reconciliation,
    Series,
    lint_copy,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
FEATURE_LIST = os.path.join(REPO_ROOT, "feature_list.json")


class TestCopyLint(unittest.TestCase):
    def test_rejects_em_dash(self):
        with self.assertRaises(CopyError):
            lint_copy("Revenue grew sharply — driven by volume")

    def test_rejects_en_dash(self):
        with self.assertRaises(CopyError):
            lint_copy("2024–2025 trend")

    def test_rejects_ai_filler(self):
        with self.assertRaises(CopyError):
            lint_copy("In today's fast-paced landscape, margins compressed")
        with self.assertRaises(CopyError):
            lint_copy("It's worth noting that volume fell")

    def test_accepts_clean_copy(self):
        self.assertEqual(lint_copy("Volume fell 4 percent. Price held."),
                         "Volume fell 4 percent. Price held.")


class TestExhibitContract(unittest.TestCase):
    def _exhibit(self):
        return Exhibit(
            feature_id="TEST-00",
            title="Test exhibit",
            audience="both",
            series=[
                Series(name="public", points=[{"label": "a", "value": 1.0}]),
                Series(name="secret", points=[{"label": "b", "value": 2.0}], internal_only=True),
            ],
            footnote=Footnote(source="src", vintage="2026", assumptions=["a1"]),
            assumptions=[AssumptionNode(key="k", label="lbl", value=1.0, source="s")],
            reconciliations=[Reconciliation(identity="x==x", lhs=1.0, rhs=1.0, tolerance=1e-9)],
        )

    def test_partner_render_strips_internal(self):
        ex = self._exhibit()
        partner = ex.render(internal_mode=False)
        self.assertNotIn("assumptions", partner)
        names = {s["name"] for s in partner["series"]}
        self.assertEqual(names, {"public"})

    def test_internal_render_includes_internal(self):
        ex = self._exhibit()
        internal = ex.render(internal_mode=True)
        self.assertIn("assumptions", internal)
        names = {s["name"] for s in internal["series"]}
        self.assertEqual(names, {"public", "secret"})

    def test_exhibit_requires_footnote(self):
        ex = self._exhibit()
        ex.footnote = None
        with self.assertRaises(ValueError):
            ex.validate()

    def test_em_dash_in_title_rejected(self):
        ex = self._exhibit()
        ex.title = "Bad — title"
        with self.assertRaises(CopyError):
            ex.validate()

    def test_reconciliation_gap_and_ok(self):
        r = Reconciliation(identity="t", lhs=10.0, rhs=10.5, tolerance=1.0)
        self.assertAlmostEqual(r.gap, -0.5, places=9)
        self.assertTrue(r.ok)
        r2 = Reconciliation(identity="t", lhs=10.0, rhs=12.0, tolerance=1.0)
        self.assertFalse(r2.ok)


class TestRegistry(unittest.TestCase):
    def test_every_registered_feature_renders(self):
        feats = registry.all_features()
        self.assertTrue(feats, "registry must have at least one feature")
        for f in feats:
            partner = registry.run(f.feature_id, internal_mode=False)
            internal = registry.run(f.feature_id, internal_mode=True)
            self.assertEqual(partner["feature_id"], f.feature_id)
            self.assertIsNotNone(partner["footnote"], f"{f.feature_id} missing footnote")
            self.assertTrue(partner["footnote"]["source"])
            self.assertTrue(partner["footnote"]["vintage"])
            self.assertNotIn("assumptions", partner,
                             f"{f.feature_id} partner view leaked assumptions")

    def test_feature_list_new_ids_are_registered(self):
        # Every NEW-* feature marked passes:true must resolve in the registry.
        with open(FEATURE_LIST) as fh:
            data = json.load(fh)
        registered = set(registry.feature_ids())
        for feat in data["features"]:
            if feat["id"].startswith("NEW-") and feat.get("passes"):
                self.assertIn(feat["id"], registered,
                              f"{feat['id']} marked passes but not registered")

    def test_cli_list_and_run(self):
        self.assertEqual(cli_main(["list"]), 0)
        # NEW-01 is the first feature and should run in both modes.
        self.assertEqual(cli_main(["run", "NEW-01"]), 0)
        self.assertEqual(cli_main(["run", "NEW-01", "--internal"]), 0)
        self.assertEqual(cli_main(["run", "DOES-NOT-EXIST"]), 2)


if __name__ == "__main__":
    unittest.main()
