"""CapIQ → IRS EIN resolution (nonprofit targets).

irs990.fetch_990 needs an EIN that an analyst currently looks up by hand.
These tests exercise the name→EIN resolver with an injected ``fetch`` so they
run offline — no ProPublica call. Same bar as the CCN/NPI resolvers: clean
match RESOLVES, generic name stays AMBIGUOUS (never auto-picked), no
candidates → UNMATCHED, and the live fetch fails closed.
"""
from __future__ import annotations

import unittest

from rcm_mc.data import capiq
from rcm_mc.data.capiq import ResolutionStatus


def _fetch_returning(orgs):
    def _fetch(name, state, limit):
        return list(orgs)
    return _fetch


def _rec(name, state=None):
    return capiq.CapIQRecord(capiq_id=name, company_name=name, state=state)


class TestEinResolution(unittest.TestCase):
    def test_clean_single_match_resolves(self):
        fetch = _fetch_returning([
            {"ein": "131837418", "name": "Beacon Health System Inc", "state": "IN"},
        ])
        res = capiq.resolve_record_to_ein(_rec("Beacon Health System Inc", "IN"),
                                          fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.ein, "131837418")
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_generic_name_is_ambiguous_not_guessed(self):
        fetch = _fetch_returning([
            {"ein": "111111111", "name": "Memorial Health", "state": "TX"},
            {"ein": "222222222", "name": "Memorial Health", "state": "OH"},
        ])
        res = capiq.resolve_record_to_ein(_rec("Memorial Health"), fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(res.ein)
        self.assertGreater(len(res.candidates), 1)
        scores = [c.score for c in res.candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_no_candidates_is_unmatched(self):
        res = capiq.resolve_record_to_ein(_rec("For-Profit Surgical LLC", "TX"),
                                          fetch=_fetch_returning([]))
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)
        self.assertIsNone(res.ein)

    def test_org_without_ein_is_dropped(self):
        fetch = _fetch_returning([{"ein": "", "name": "Beacon Health System Inc"}])
        res = capiq.resolve_record_to_ein(_rec("Beacon Health System Inc"),
                                          fetch=fetch)
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)

    def test_retries_unscoped_when_state_scope_empty(self):
        seq = [[], [{"ein": "131837418", "name": "Beacon Health System Inc"}]]

        def _fetch(name, state, limit):
            return seq.pop(0)

        res = capiq.resolve_record_to_ein(_rec("Beacon Health System Inc", "IN"),
                                          fetch=_fetch)
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.ein, "131837418")

    def test_resolve_export_to_ein_maps_each_record(self):
        fetch = _fetch_returning([
            {"ein": "131837418", "name": "Beacon Health System Inc", "state": "IN"},
        ])
        out = capiq.resolve_export_to_ein(
            [_rec("Beacon Health System Inc", "IN")], fetch=fetch)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].status, ResolutionStatus.RESOLVED)

    def test_default_fetch_fails_closed_when_search_raises(self):
        import rcm_mc.data_public.public_api_clients as client

        orig = client.propublica_search
        client.propublica_search = (  # type: ignore[assignment]
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no egress")))
        try:
            self.assertEqual(capiq._default_ein_fetch("Beacon", "IN", 10), [])
        finally:
            client.propublica_search = orig  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
