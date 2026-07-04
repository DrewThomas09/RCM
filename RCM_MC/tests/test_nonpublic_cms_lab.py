"""Internal non-public CMS + API lab (/tools/nonpublic-cms).

Pins: the registry is well-formed, the backend pages render, honest-status
invariants hold (reachable entries are the verified live APIs; reference-only
entries never claim to be wired), and the lab stays OUT of the front nav.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import nonpublic_cms_registry as reg
from rcm_mc.ui.nonpublic_cms_lab_page import (
    render_nonpublic_cms_lab, render_nonpublic_cms_source,
)

_ACCESS = {"public", "api-key", "oauth", "bulk-fhir", "credentialed",
           "entitlement", "oss"}
_STATUS = {"reachable", "registered", "reference"}


class RegistryTests(unittest.TestCase):
    def test_registry_well_formed(self):
        srcs = reg.all_sources()
        self.assertGreaterEqual(len(srcs), 25)
        ids = set()
        cat_ids = {c[0] for c in reg.CATEGORIES}
        for s in srcs:
            for key in ("id", "name", "category", "access", "url", "blurb",
                        "relevance", "status", "integration"):
                self.assertTrue(s.get(key), f"{s.get('id')} missing {key}")
            self.assertNotIn(s["id"], ids, f"duplicate id {s['id']}")
            ids.add(s["id"])
            self.assertIn(s["category"], cat_ids)
            self.assertIn(s["access"], _ACCESS)
            self.assertIn(s["status"], _STATUS)
            self.assertTrue(s["url"].startswith("http"))

    def test_every_category_has_entries(self):
        grouped = {cid for cid, _, _ in reg.by_category()}
        for cid, _label in reg.CATEGORIES:
            self.assertIn(cid, grouped, f"category {cid} rendered empty")

    def test_reachable_are_the_verified_live_apis(self):
        # Only the three APIs we actually called this build may claim 'reachable'.
        reachable = {s["id"] for s in reg.all_sources()
                     if s["status"] == "reachable"}
        self.assertEqual(reachable,
                         {"nppes_api", "cms_coverage_api", "icd10_service"})

    def test_reference_entries_are_never_wired(self):
        # A reference-only source is study/reimplement — it must not masquerade
        # as a live client or a graduated loader.
        for s in reg.all_sources():
            if s["status"] == "reference":
                self.assertNotIn(s["integration"], {"wired"})

    def test_credentialed_microdata_is_not_a_render_path(self):
        # DUA/entitlement rungs are outside the no-network posture: none may be
        # marked reachable (that would imply we pull PHI in a render path).
        for s in reg.all_sources():
            if s["access"] in {"credentialed", "entitlement"}:
                self.assertNotEqual(s["status"], "reachable", s["id"])

    def test_lookup_and_grouping(self):
        self.assertEqual(reg.get("hccpy")["license"], "Apache-2.0")
        self.assertEqual(reg.get("nope"), {})
        grouped = reg.by_category()
        self.assertTrue(grouped)
        total = sum(len(items) for _, _, items in grouped)
        self.assertEqual(total, len(reg.all_sources()))

    def test_status_counts_sum(self):
        counts = reg.status_counts()
        self.assertEqual(sum(counts.values()), len(reg.all_sources()))


class PageTests(unittest.TestCase):
    def test_lab_renders(self):
        html = render_nonpublic_cms_lab()
        self.assertIn("Non-public CMS", html)
        self.assertIn("Internal", html)                       # WIP framing
        self.assertIn("hccpy", html)                          # an OSS source
        self.assertIn("Reachable now", html)                  # live-API status
        self.assertIn("Credentialed CMS microdata", html)     # a category label
        self.assertIn("/tools/nonpublic-cms/bcda", html)      # detail link

    def test_detail_renders(self):
        html = render_nonpublic_cms_source("resdac")
        self.assertIn("ResDAC", html)
        self.assertIn("Why it matters", html)
        self.assertIn("resdac.org", html)

    def test_detail_surfaces_verify_flag(self):
        # Entries carrying a `verify` note must surface it, so nobody treats an
        # unconfirmed fee/status as authoritative.
        html = render_nonpublic_cms_source("dpc")
        self.assertIn("Verify", html)

    def test_unknown_source_is_graceful(self):
        html = render_nonpublic_cms_source("does-not-exist")
        self.assertIn("Source not found", html)


class NavIsolationTests(unittest.TestCase):
    def test_lab_not_promoted_into_front_nav(self):
        # The lab is internal: it must not appear in the editorial top-nav rails.
        from rcm_mc.ui import _chartis_kit as kit
        blob = repr(getattr(kit, "_SUB_NAV", {})) + repr(
            getattr(kit, "_CORPUS_NAV", {}))
        self.assertNotIn("/tools/nonpublic-cms", blob)


if __name__ == "__main__":
    unittest.main()
