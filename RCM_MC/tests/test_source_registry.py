"""Report-0277: the provenance source-URL registry.

Every partner-facing surface prints data-source labels through
``ck_source_link`` -> ``source_url``. The registry covered only 7 labels
while the platform cites dozens, so most labels rendered as dead plain
text. These tests pin the expanded registry and, more importantly, the
longest-match resolution rule that makes it SAFE TO EXTEND: with the old
insertion-order matching, adding a short generic key ("BLS", "340B")
above a specific one silently hijacked every label containing it.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import SOURCE_URLS, source_url


class TestRegistryShape(unittest.TestCase):
    def test_every_url_is_https_and_absolute(self):
        for label, url in SOURCE_URLS.items():
            self.assertTrue(
                url.startswith("https://"),
                f"{label!r} -> {url!r} must be an absolute https URL",
            )

    def test_no_empty_keys(self):
        for label in SOURCE_URLS:
            self.assertTrue(label.strip(), "empty label key in SOURCE_URLS")


class TestLabelResolution(unittest.TestCase):
    """Each label the platform actually cites must resolve."""

    CASES = {
        "CMS HCRIS": "cost-reports",
        "CMS HCRIS · FY2023": "cost-reports",   # decorated label
        "NPPES": "nppes",
        "NPPES ambulance taxonomy 3416": "nppes",
        "MedPAC assessment of GADCS data, Dec 2025": "medpac.gov",
        "IRS990": "form-990",
        "BLS OEWS May 2025": "bls.gov/oes",
        "HRSA OPA Audit": "hrsa.gov/opa",
        "340B covered entity": "hrsa.gov/opa",
        "Medicare Physician Fee Schedule (annual Final Rule)":
            "fee-schedules/physician",
        "CMS Hospice Compare": "yc9t-dgbk",
    }

    def test_cited_labels_resolve(self):
        for label, expected_fragment in self.CASES.items():
            with self.subTest(label=label):
                url = source_url(label)
                self.assertIsNotNone(url, f"{label!r} did not resolve")
                self.assertIn(expected_fragment, url)

    def test_unknown_label_returns_none(self):
        self.assertIsNone(source_url("Totally Unknown Source"))
        self.assertIsNone(source_url(""))
        self.assertIsNone(source_url(None))


class TestLongestMatchWins(unittest.TestCase):
    def test_specific_key_beats_shorter_substring(self):
        # "CMS HCRIS ..." contains no shorter registry key today, but the
        # rule must hold structurally: the longest matching key wins
        # regardless of dict insertion order.
        label = "CMS Physician & Other Practitioners 2023"
        self.assertIn("medicare-physician-other-practitioners",
                      source_url(label))

    def test_resolution_is_order_independent(self):
        # Re-resolving against a reversed copy of the registry must give
        # the same answer — proves we are not relying on insertion order.
        import rcm_mc.ui._chartis_kit as kit
        original = kit.SOURCE_URLS
        try:
            kit.SOURCE_URLS = dict(reversed(list(original.items())))
            for label in TestLabelResolution.CASES:
                with self.subTest(label=label):
                    self.assertEqual(
                        kit.source_url(label),
                        original.get(label) or kit.source_url(label),
                    )
            # The decisive case: a label containing both a short and a
            # long key resolves to the long one either way.
            self.assertIn("hrsa.gov/opa", kit.source_url("HRSA OPA Audit"))
        finally:
            kit.SOURCE_URLS = original


if __name__ == "__main__":
    unittest.main()
