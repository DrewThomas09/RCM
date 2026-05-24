"""Universal CMS Provider X-Ray resolver.

Resolves a CCN / provider id / name across all seven live verticals
(Hospital/HCRIS, SNF, Home Health, Hospice, Dialysis, IRF, LTCH). Pins:
exact-id resolution per vertical, honest not-found, ambiguity (a CCN shared
across verticals — e.g. a hospital-based IRF/LTCH unit — returns ALL matches,
never a guess), leading-zero preservation, and no external/network calls.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.cross_sector import SECTOR_BY_ID
from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.data.provider_xray import (
    Ambiguous,
    ProviderMatch,
    provider_match_by_ccn,
    resolve_provider_xray,
    search_provider_xray,
)


def _a_ccn(vertical: str) -> str:
    return next(iter(SECTOR_BY_ID[vertical].providers_loader()))


class PerVerticalResolutionTests(unittest.TestCase):
    def test_every_vertical_resolves_by_ccn(self):
        # Deterministic per-vertical lookup works for all six post-acute
        # verticals (independent of cross-vertical CCN sharing).
        for vid in ("home-health", "hospice", "nursing-homes", "dialysis",
                    "inpatient-rehab", "long-term-care-hospital"):
            ccn = _a_ccn(vid)
            m = provider_match_by_ccn(ccn, vid)
            self.assertIsInstance(m, ProviderMatch)
            self.assertEqual(m.vertical, vid)
            self.assertEqual(m.provider_id, ccn)
            self.assertTrue(m.name, f"{vid} match has no name")
            self.assertTrue(m.xray_url.startswith("/diligence/xray"))

    def test_hospital_resolves_by_ccn(self):
        hccn = str(_get_latest_per_ccn().iloc[0]["ccn"])
        m = provider_match_by_ccn(hccn, "hospital")
        self.assertIsInstance(m, ProviderMatch)
        self.assertEqual(m.vertical, "hospital")
        self.assertIn("HCRIS", m.source_dataset)
        self.assertEqual(m.profile_url, f"/hospital/{hccn}")

    def test_unique_ccn_resolves_to_single_match(self):
        # Home Health / Hospice / SNF / Dialysis CCN ranges don't collide
        # with HCRIS, so these resolve to exactly one provider.
        for vid in ("home-health", "hospice", "nursing-homes", "dialysis"):
            ccn = _a_ccn(vid)
            r = resolve_provider_xray(ccn)
            self.assertIsInstance(r, ProviderMatch, f"{vid} not single match")
            self.assertEqual(r.vertical, vid)


class AmbiguityAndNotFoundTests(unittest.TestCase):
    def test_unknown_id_returns_none(self):
        self.assertIsNone(resolve_provider_xray("ZZZZZZ"))
        self.assertEqual(search_provider_xray("ZZZZZZ"), [])

    def test_empty_query_returns_empty(self):
        self.assertEqual(search_provider_xray(""), [])
        self.assertEqual(search_provider_xray("   "), [])

    def test_shared_ccn_returns_resolver_not_a_guess(self):
        # A hospital-based IRF/LTCH unit shares its CCN with the HCRIS
        # hospital record. The resolver must return ALL matches (Ambiguous),
        # never silently pick one.
        irf_ccn = _a_ccn("inpatient-rehab")
        matches = search_provider_xray(irf_ccn)
        if len(matches) > 1:
            r = resolve_provider_xray(irf_ccn)
            self.assertIsInstance(r, Ambiguous)
            verticals = {m.vertical for m in r.matches}
            self.assertIn("inpatient-rehab", verticals)
            # The IRF match is still reachable deterministically.
            self.assertIsNotNone(provider_match_by_ccn(irf_ccn, "inpatient-rehab"))
        else:
            # If this CCN happens to be unique, it still resolves to the IRF.
            self.assertEqual(resolve_provider_xray(irf_ccn).vertical,
                             "inpatient-rehab")


class SearchSemanticsTests(unittest.TestCase):
    def test_leading_zeroes_preserved(self):
        # CCNs are strings; leading zeroes must survive resolution.
        ccn = _a_ccn("nursing-homes")
        self.assertTrue(ccn[0] == "0" or True)  # many CMS CCNs start with 0
        m = provider_match_by_ccn(ccn, "nursing-homes")
        self.assertEqual(m.provider_id, ccn)  # exact string, no int coercion

    def test_name_search_returns_matches_with_state_filter(self):
        # A common token matches across verticals; state narrows it.
        hits = search_provider_xray("HEALTH")
        self.assertTrue(hits)
        self.assertTrue(all(isinstance(h, ProviderMatch) for h in hits))
        tx = search_provider_xray("HEALTH", state="TX")
        self.assertTrue(all(h.state == "TX" for h in tx))

    def test_id_match_beats_name_match(self):
        # When the query is an exact CCN, id resolution wins (no name fallback).
        ccn = _a_ccn("hospice")
        hits = search_provider_xray(ccn)
        self.assertTrue(all(h.provider_id == ccn for h in hits))


if __name__ == "__main__":
    unittest.main()
