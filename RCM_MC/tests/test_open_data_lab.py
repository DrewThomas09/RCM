"""Internal open-data integrations lab (/tools/open-data).

Pins: the registry is well-formed, the backend pages render, and the lab is
NOT promoted into the front nav (it must stay an internal, WIP, Tools-tab-only
surface).
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import open_data_registry as reg
from rcm_mc.ui.open_data_lab_page import (
    render_open_data_lab, render_open_data_source,
)


class RegistryTests(unittest.TestCase):
    def test_registry_well_formed(self):
        srcs = reg.all_sources()
        self.assertGreater(len(srcs), 20)
        ids = set()
        cat_ids = {c[0] for c in reg.CATEGORIES}
        for s in srcs:
            for key in ("id", "name", "category", "access", "url", "blurb",
                        "relevance", "status", "integration"):
                self.assertTrue(s.get(key), f"{s.get('id')} missing {key}")
            self.assertNotIn(s["id"], ids, f"duplicate id {s['id']}")
            ids.add(s["id"])
            self.assertIn(s["category"], cat_ids)
            self.assertIn(s["access"],
                          {"open", "api", "credentialed", "self-host", "model"})
            self.assertIn(s["status"], {"registered", "wired"})
            self.assertTrue(s["url"].startswith("http"))

    def test_lookup_and_grouping(self):
        self.assertEqual(reg.get("synthea")["name"], "Synthea (synthetic patients)")
        self.assertEqual(reg.get("nope"), {})
        grouped = reg.by_category()
        self.assertTrue(grouped)
        # every source appears in exactly one group
        total = sum(len(items) for _, _, items in grouped)
        self.assertEqual(total, len(reg.all_sources()))


class PageTests(unittest.TestCase):
    def test_lab_renders(self):
        html = render_open_data_lab()
        self.assertIn("Open-data integrations", html)
        self.assertIn("Internal", html)              # WIP / internal framing
        self.assertIn("Synthea", html)               # a sample source
        self.assertIn("Open datasets", html)         # a category label
        self.assertIn("/tools/open-data/synthea", html)  # detail link

    def test_detail_renders(self):
        html = render_open_data_source("open_targets")
        self.assertIn("Open Targets", html)
        self.assertIn("Why it matters", html)
        self.assertIn("platform.opentargets.org", html)

    def test_unknown_source_is_graceful(self):
        html = render_open_data_source("does-not-exist")
        self.assertIn("not found", html.lower())


class NotFrontFacingTests(unittest.TestCase):
    def test_lab_not_in_top_nav(self):
        # The lab must NOT be promoted into the corpus top nav — it is an
        # internal, backend Tools-tab surface only.
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV
        hrefs = " ".join(str(n.get("href", "")) for n in _CORPUS_NAV)
        self.assertNotIn("open-data", hrefs)


if __name__ == "__main__":
    unittest.main()
