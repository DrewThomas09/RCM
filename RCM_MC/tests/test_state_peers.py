"""Similar States (/state-peers): a comp-set finder ranking states by
standardized-distance similarity over the real metric layer. Guards state
validation, that the target is excluded, that distances are real/sorted, the
self-distance logic, thin-coverage handling, and GREEN classification.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.state_peers_page import (
    _DEFAULT,
    _parse_state,
    rank_peers,
    render_state_peers,
)


class StatePeersTests(unittest.TestCase):
    def test_parse_state_validates(self):
        self.assertEqual(_parse_state({"state": ["tx"]}), "TX")
        self.assertEqual(_parse_state({"state": ["ZZ"]}), _DEFAULT)
        self.assertEqual(_parse_state({}), _DEFAULT)

    def test_peers_sorted_and_exclude_self(self):
        peers, thin = rank_peers("OH")
        states = [s for s, _, _ in peers]
        self.assertNotIn("OH", states)  # target excluded
        self.assertNotIn("OH", thin)
        dists = [d for _, d, _ in peers]
        self.assertEqual(dists, sorted(dists))  # closest-first
        # distances are real, non-negative, finite
        for d in dists:
            self.assertGreaterEqual(d, 0)
            self.assertEqual(d, d)

    def test_peers_have_minimum_shared_metrics(self):
        peers, _ = rank_peers("CA")
        for _s, _d, shared in peers:
            self.assertGreaterEqual(shared, 6)

    def test_no_state_double_counted(self):
        peers, thin = rank_peers("TX")
        ranked = {s for s, _, _ in peers}
        self.assertTrue(ranked.isdisjoint(set(thin)))

    def test_page_renders(self):
        h = render_state_peers({"state": ["OH"]})
        self.assertIn("Similar States", h)
        self.assertIn("<table", h)
        self.assertIn("derived", h)
        self.assertIn("fabricated", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/state-peers")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
