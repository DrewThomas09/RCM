import unittest

from ..connector import MAX_RESULTS, NppesConnector
from ..endpoints import get_endpoint
from ..transport import NppesTransport
from .fakes import INDIVIDUAL, ORGANIZATION, FakeNppes, make_records


def _conn(page_limit=200):
    t = NppesTransport(min_interval_s=0.0)
    return NppesConnector(t, page_limit=page_limit, sleep=lambda s: None)


class SeedPagingTests(unittest.TestCase):
    def test_seed_pages_by_skip_and_stops_on_short_page(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 7))
        spec = get_endpoint("provider_individual")
        conn = _conn(page_limit=2)
        res = conn.fetch(spec, {"enumeration_type": "NPI-1"}, opener=fake)
        self.assertEqual(len(res.rows), 7)
        self.assertIsNone(res.next_cursor)      # short final page → exhausted
        self.assertFalse(res.truncated)
        self.assertTrue(res.done)

    def test_seed_stops_at_1200_cap_when_more_available(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 1300))
        spec = get_endpoint("provider_individual")
        conn = _conn(page_limit=200)   # 6 pages × 200 = 1200 ceiling
        res = conn.fetch(spec, {"enumeration_type": "NPI-1"}, opener=fake)
        self.assertEqual(len(res.rows), MAX_RESULTS)  # capped at 1200
        self.assertTrue(res.truncated)
        self.assertIsNone(res.next_cursor)

    def test_resumable_step_returns_cursor_then_finishes(self):
        # page_limit 2, 5 records → step 1 drains up to MAX_PAGES_PER_STEP pages.
        fake = FakeNppes(make_records(ORGANIZATION, 5))
        spec = get_endpoint("provider_organization")
        conn = _conn(page_limit=2)
        rows = conn.fetch_seed(spec, {"enumeration_type": "NPI-2"}, opener=fake)
        self.assertEqual(len(rows), 5)

    def test_default_seed_used_when_no_params(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 3))
        spec = get_endpoint("provider_individual")
        conn = _conn(page_limit=200)
        res = conn.fetch(spec, opener=fake)  # falls back to spec.seeds[0]
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(res.seed, dict(spec.seeds[0]))

    def test_discover_lists_specs(self):
        conn = _conn()
        keys = {s.key for s in conn.discover()}
        self.assertEqual(keys, {"provider_individual", "provider_organization"})


if __name__ == "__main__":
    unittest.main()
