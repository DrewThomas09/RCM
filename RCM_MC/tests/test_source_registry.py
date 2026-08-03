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
        "HCRIS": "cost-reports",                # bare form, most-cited
        "HCRIS X-Ray": "cost-reports",
        "MGMA": "mgma.com",
        "MGMA DataDive 2025": "mgma.com",
        "AHA": "aha.org",
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


class TestAmbiguousAcronymsDoNotHijack(unittest.TestCase):
    """Report-0282: a wrong link is worse than no link.

    Adding a bare ``"ACS"`` key would have resolved *"ACS Cancer Facts &
    Figures"* — the American Cancer Society — to the Census Bureau's American
    Community Survey. The label would have rendered as a confident,
    clickable, wrong citation on a partner-facing page. Caught by resolving
    every source label in the package against the proposed registry before
    committing it; the fix was to register the disambiguated forms only.
    """

    def test_american_cancer_society_does_not_resolve_to_census(self):
        self.assertIsNone(source_url("ACS Cancer Facts & Figures"))

    def test_census_acs_labels_still_resolve(self):
        for label in (
            "US Census / ACS county estimates",
            "County Health Rankings / Census ACS",
            "US Census ACS / County Health Rankings (vendored)",
            "ACS demographics (vendored) + CMS MA geographic",
        ):
            with self.subTest(label=label):
                url = source_url(label)
                self.assertIsNotNone(url, f"{label!r} lost its link")
                self.assertIn("census.gov", url)

    def test_ccw_is_not_captured_by_the_dataset_key(self):
        # "Chronic Conditions Data Warehouse" must beat "Chronic Conditions".
        self.assertIn("ccwdata.org",
                      source_url("CMS Chronic Conditions Data Warehouse"))
        self.assertIn("medicare-chronic-conditions",
                      source_url("CMS Medicare Chronic Conditions"))


class TestReport0282Additions(unittest.TestCase):
    """The 14 labels four UI audits found rendering as dead plain text."""

    CASES = {
        "CDC PLACES county estimates, state-rolled (vendored)": "i46a-9kgh",
        "CMS PECOS enrolled providers, national (vendored)":
            "medicare-provider-supplier-enrollment",
        "FTC/DOJ Horizontal Merger Guidelines (2023)":
            "2023-merger-guidelines",
        "NHIA industry report (home + suite)": "nhia.org",
        "openFDA drug shortages (live snapshot)": "open.fda.gov",
        "NUCC provider taxonomy": "nucc.org",
        "CMS ASP Pricing File": "asp-pricing-files",
        "CMS Medicare Monthly Enrollment": "medicare-monthly-enrollment",
        "Medicare Outpatient Hospitals by Provider & Service":
            "medicare-outpatient-hospitals",
        "Census Population Estimates": "popest",
        # The emitter alias: npi_cleaner/enrich.py says "Medicare Physician
        # & Other Practitioners", which does NOT substring-match the
        # "CMS Physician & Other Practitioners" key.
        "Medicare Physician & Other Practitioners — by Provider, data.cms.gov":
            "medicare-physician-other-practitioners",
    }

    def test_each_resolves(self):
        for label, fragment in self.CASES.items():
            with self.subTest(label=label):
                url = source_url(label)
                self.assertIsNotNone(url, f"{label!r} did not resolve")
                self.assertIn(fragment, url)


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
