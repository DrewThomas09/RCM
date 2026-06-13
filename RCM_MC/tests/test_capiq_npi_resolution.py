"""CapIQ → NPPES Type-2 NPI resolution (the non-hospital counterpart).

``resolve_record`` reaches only CMS CCNs in HCRIS (Medicare hospitals);
most diligence targets are non-hospital and land UNMATCHED there. These
tests exercise the NPPES resolver with an injected ``fetch`` so they run
offline and deterministically — no network, no live registry. The bar is
the same as the CCN path: a clean match RESOLVES, a generic name stays
AMBIGUOUS (never auto-picked), and no candidates means UNMATCHED.
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import List, Optional

from rcm_mc.data import capiq
from rcm_mc.data.capiq import ResolutionStatus


@dataclass
class _FakeProvider:
    """Minimal stand-in for NppesProvider — only the attrs the resolver reads."""
    npi: str
    organization_name: str
    state: Optional[str] = None
    taxonomy_label: str = ""


def _fetch_returning(providers):
    """Build a fetch seam that records its calls and returns a fixed list."""
    calls = []

    def _fetch(name, state, limit):
        calls.append((name, state, limit))
        return list(providers)

    _fetch.calls = calls  # type: ignore[attr-defined]
    return _fetch


def _rec(name, state=None):
    return capiq.CapIQRecord(capiq_id=name, company_name=name, state=state)


class TestNpiResolution(unittest.TestCase):
    def test_clean_single_match_resolves(self):
        fetch = _fetch_returning([
            _FakeProvider("1922011111", "Acme Infusion Centers LLC", "TX",
                          "Clinic/Center"),
        ])
        res = capiq.resolve_record_to_npi(_rec("Acme Infusion Centers LLC", "TX"),
                                          fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.npi, "1922011111")
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_generic_name_is_ambiguous_not_guessed(self):
        # Two near-identical strong matches → must not auto-pick.
        fetch = _fetch_returning([
            _FakeProvider("1000000001", "Memorial Health", "TX"),
            _FakeProvider("1000000002", "Memorial Health", "OH"),
        ])
        res = capiq.resolve_record_to_npi(_rec("Memorial Health"), fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(res.npi)
        self.assertGreater(len(res.candidates), 1)
        scores = [c.score for c in res.candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))  # sorted desc

    def test_no_candidates_is_unmatched(self):
        res = capiq.resolve_record_to_npi(_rec("Nobody Here LLC", "TX"),
                                          fetch=_fetch_returning([]))
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)
        self.assertIsNone(res.npi)

    def test_retries_unscoped_when_state_scope_empty(self):
        # First (state-scoped) call empty, second (unscoped) finds the match.
        seq = [[], [_FakeProvider("1922011111", "Acme Infusion Centers LLC")]]

        def _fetch(name, state, limit):
            return seq.pop(0)

        res = capiq.resolve_record_to_npi(_rec("Acme Infusion Centers LLC", "TX"),
                                          fetch=_fetch)
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.npi, "1922011111")

    def test_candidate_without_npi_is_dropped(self):
        fetch = _fetch_returning([
            _FakeProvider("", "Acme Infusion Centers LLC", "TX"),
        ])
        res = capiq.resolve_record_to_npi(_rec("Acme Infusion Centers LLC"),
                                          fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)

    def test_resolve_export_to_npi_maps_each_record(self):
        fetch = _fetch_returning([
            _FakeProvider("1922011111", "Acme Infusion Centers LLC", "TX"),
        ])
        out = capiq.resolve_export_to_npi(
            [_rec("Acme Infusion Centers LLC", "TX")], fetch=fetch)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].status, ResolutionStatus.RESOLVED)

    def test_default_fetch_fails_closed_when_registry_raises(self):
        # An unreachable/erroring NPPES must yield no candidates (→ UNMATCHED
        # upstream), never raise — exercised without a socket by patching the
        # client to raise. Guards the no-egress render path.
        import rcm_mc.data_public.nppes_api_client as client

        orig = client.search_by_organization
        client.search_by_organization = (  # type: ignore[assignment]
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no egress")))
        try:
            self.assertEqual(capiq._default_npi_fetch("Acme", "TX", 10), [])
        finally:
            client.search_by_organization = orig  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
