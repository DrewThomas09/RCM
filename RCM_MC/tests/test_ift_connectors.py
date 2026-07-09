"""Real-path tests for the IFT data-connector estate map (ift_connectors).

Pins that every hook is REGISTERED (the wiring is genuine), DEGRADES offline to
an honest fallback citation (never a fabricated SOURCED number over zero rows),
and rolls up into a coherent estate summary. These are the honesty invariants
the workbook + pages both rest on.
"""
from __future__ import annotations

import unittest

from rcm_mc.market_reports import ift_connectors as ic
from rcm_mc.data_public import connector_estate as ce


class ConnectorEstateTests(unittest.TestCase):
    def setUp(self):
        self.probes = ic.connector_estate_map()

    def test_map_is_substantial(self):
        # a real step up from the original 3-hook sheet: many hooks, many sources
        self.assertGreaterEqual(len(self.probes), 12)
        self.assertGreaterEqual(len({p.connector for p in self.probes}), 8)

    def test_every_dataset_id_is_registered(self):
        # the wiring must be genuine — every dataset_id resolves to a real estate
        # owner, so the hook flips to SOURCED the moment the estate is ingested.
        for p in self.probes:
            self.assertIsNotNone(
                ce.dataset_owner(p.dataset_id),
                f"{p.key}: dataset_id not registered: {p.dataset_id}")
            # the declared connector matches the estate's owner
            self.assertEqual(ce.dataset_owner(p.dataset_id), p.connector, p.key)

    def test_degrades_never_raises_and_cites_honestly(self):
        # offline: no probe is SOURCED over zero rows; each carries a fallback.
        for p in self.probes:
            self.assertIn(p.basis, ("SOURCED", "CONNECTOR"), p.key)
            if not p.available:
                self.assertEqual(p.basis, "CONNECTOR", p.key)
                self.assertEqual(p.n_rows, 0, p.key)
                self.assertTrue(p.fallback_citation, p.key)
                # the shown source is the fallback when gated
                self.assertEqual(p.source_label, p.fallback_citation, p.key)
            # no SOURCED chip ever appears over an empty read
            if p.basis == "SOURCED":
                self.assertTrue(p.available and p.n_rows > 0, p.key)

    def test_every_probe_explains_its_ift_signal(self):
        for p in self.probes:
            self.assertTrue(p.title, p.key)
            self.assertGreater(len(p.ift_signal), 20, p.key)
            self.assertTrue(p.category, p.key)

    def test_summary_rolls_up_by_category(self):
        s = ic.estate_summary(self.probes)
        self.assertEqual(s.total, len(self.probes))
        self.assertEqual(s.available + s.gated, s.total)
        self.assertGreaterEqual(s.n_connectors, 8)
        # categories cover the supply / demand / facilities spine
        cats = dict(s.by_category)
        for c in ("Supply", "Demand", "Facilities"):
            self.assertIn(c, cats, f"missing category: {c}")

    def test_ambulance_taxonomies_are_real_nucc_codes(self):
        # the supplier hook filters on the real NUCC ambulance taxonomy family
        for code in ic._AMBULANCE_TAXONOMIES:
            self.assertTrue(code.startswith("3416"), code)

    def test_multi_value_filters_use_the_in_operator(self):
        # a list under a PLAIN key compiles to `WHERE col = '[repr]'` and matches
        # zero rows even after ingest — multi-value filters MUST use `field__in`.
        for spec in ic._SPECS:
            for key, value in (spec.filters or {}).items():
                if isinstance(value, (list, tuple)):
                    self.assertTrue(
                        key.endswith("__in"),
                        f"{spec.key}: multi-value filter {key!r} must use __in")

    def test_probe_columns_exist_on_the_target_table(self):
        # every group_by / metric / filter column must exist on the dataset's
        # table, or the estate aggregate QueryErrors and the probe can NEVER flip
        # to SOURCED (it stays silently network-gated). Guards the dialysis
        # group_by='state' regression (real col is bene_state_abrvtn).
        h = ce._load()
        if h is None:
            self.skipTest("connector estate not loadable")
        adapters = h[1].adapters()
        checked = 0
        for spec in ic._SPECS:
            owner = ce.dataset_owner(spec.dataset_id)
            adapter = adapters.get(owner)
            if adapter is None:
                continue
            r = adapter.by_dataset_id().get(spec.dataset_id)
            tbl = getattr(r, "target_table", None)
            table = adapter.tables_mod.TABLES.get(tbl)
            cols = set(getattr(table, "columns", []) or [])
            if not cols:
                continue
            checked += 1
            gb = (spec.group_by if isinstance(spec.group_by, (list, tuple))
                  else [spec.group_by])
            for c in gb:
                self.assertIn(c, cols, f"{spec.key}: group_by {c!r} not on {tbl}")
            for m in (spec.metrics or ()):
                field = m.split(":", 1)[1]
                self.assertIn(field, cols,
                              f"{spec.key}: metric {field!r} not on {tbl}")
            for key in (spec.filters or {}):
                field = key.rsplit("__", 1)[0] if "__" in key else key
                self.assertIn(field, cols,
                              f"{spec.key}: filter {field!r} not on {tbl}")
        self.assertGreater(checked, 8, "expected to validate most probes")


if __name__ == "__main__":
    unittest.main()
