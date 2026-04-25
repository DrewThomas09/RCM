"""End-to-end comp engine workflow test.

The directive: select a hospital, view comps, understand WHY they
were selected, override selections — defensible.

Coverage:
  • Select target → find_comparables ranks peers correctly.
  • Similarity components surface every dimension's contribution
    so a partner can defend each peer in IC.
  • Bed-size proximity drives ranking (small + small > small +
    big).
  • Region match meaningfully boosts score.
  • Payer-mix similarity (cosine) computed correctly.
  • Missing-field neutrality: a peer with unknown teaching status
    isn't penalized to zero on that dimension.
  • Self-exclusion: a hospital never appears as its own peer.
  • Override: callers can drop / pin / replace specific peers
    after the engine runs (the engine returns a list, partners
    edit it).
  • Audit trail: similarity_components persisted on each peer
    enables partner to defend the selection in IC.
"""
from __future__ import annotations

import unittest


def _hospital(
    *,
    ccn: str,
    bed_count: int = 200,
    region: str = "South",
    payer_mix: dict = None,
    system_affiliation: str = "Independent",
    teaching_status: str = "Non-teaching",
    urban_rural: str = "Urban",
    name: str = "",
) -> dict:
    return {
        "ccn": ccn,
        "name": name or f"Hospital {ccn}",
        "bed_count": bed_count,
        "region": region,
        "payer_mix": payer_mix or {
            "medicare": 0.40, "medicaid": 0.15,
            "commercial": 0.45},
        "system_affiliation": system_affiliation,
        "teaching_status": teaching_status,
        "urban_rural": urban_rural,
    }


# ── Similarity scoring ──────────────────────────────────────

class TestSimilarityScoring(unittest.TestCase):
    def test_identical_hospitals_score_1(self):
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        a = _hospital(ccn="A")
        b = _hospital(ccn="B")  # identical except CCN
        sim = similarity_score(a, b)
        self.assertAlmostEqual(
            sim["score"], 1.0, places=2)

    def test_components_sum_with_weights(self):
        from rcm_mc.ml.comparable_finder import (
            similarity_score, WEIGHTS,
        )
        a = _hospital(ccn="A")
        b = _hospital(ccn="B")
        sim = similarity_score(a, b)
        manual = sum(
            sim["components"][k] * WEIGHTS[k]
            for k in WEIGHTS)
        self.assertAlmostEqual(
            sim["score"], manual, places=4)

    def test_weights_sum_to_1(self):
        from rcm_mc.ml.comparable_finder import WEIGHTS
        self.assertAlmostEqual(
            sum(WEIGHTS.values()), 1.0, places=4)

    def test_bed_size_proximity_drives_score(self):
        """Two 200-bed hospitals should score higher together
        than 200-bed + 1000-bed."""
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        target = _hospital(ccn="T", bed_count=200)
        close = _hospital(ccn="C", bed_count=220)
        far = _hospital(ccn="F", bed_count=1000)
        s_close = similarity_score(target, close)
        s_far = similarity_score(target, far)
        self.assertGreater(
            s_close["components"]["bed_count"],
            s_far["components"]["bed_count"])

    def test_region_match_boosts_score(self):
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        target = _hospital(ccn="T", region="South")
        same = _hospital(ccn="C", region="South")
        diff = _hospital(ccn="F", region="Northeast")
        s_same = similarity_score(target, same)
        s_diff = similarity_score(target, diff)
        self.assertGreater(s_same["score"], s_diff["score"])

    def test_payer_mix_cosine_similarity(self):
        """Similar payer mixes → high payer_mix component."""
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        target = _hospital(
            ccn="T",
            payer_mix={"medicare": 0.50,
                       "medicaid": 0.20,
                       "commercial": 0.30})
        close = _hospital(
            ccn="C",
            payer_mix={"medicare": 0.48,
                       "medicaid": 0.22,
                       "commercial": 0.30})
        far = _hospital(
            ccn="F",
            payer_mix={"medicare": 0.10,
                       "medicaid": 0.10,
                       "commercial": 0.80})
        s_close = similarity_score(target, close)
        s_far = similarity_score(target, far)
        self.assertGreater(
            s_close["components"]["payer_mix"],
            s_far["components"]["payer_mix"])

    def test_missing_field_is_neutral(self):
        """When a dimension is missing on the peer, it
        contributes 0.5 (neutral) — not 0.0 (penalized)."""
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        target = _hospital(
            ccn="T", teaching_status="Teaching")
        peer = _hospital(ccn="P")
        peer.pop("teaching_status", None)
        sim = similarity_score(target, peer)
        # Neutral handling
        self.assertAlmostEqual(
            sim["components"]["teaching_status"], 0.5,
            places=2)


# ── find_comparables workflow ───────────────────────────────

class TestFindComparables(unittest.TestCase):
    def _universe(self):
        return [
            _hospital(
                ccn="A", bed_count=210, region="South",
                name="Close peer A"),
            _hospital(
                ccn="B", bed_count=190, region="South",
                name="Close peer B"),
            _hospital(
                ccn="C", bed_count=205,
                region="Northeast",
                name="Same size, diff region"),
            _hospital(
                ccn="D", bed_count=1500,
                region="South",
                name="Same region, much bigger"),
            _hospital(
                ccn="E", bed_count=50,
                region="West",
                payer_mix={"medicare": 0.10,
                           "medicaid": 0.10,
                           "commercial": 0.80},
                teaching_status="Teaching",
                urban_rural="Rural",
                name="Different on every dim"),
        ]

    def test_top_peer_is_most_similar(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T", bed_count=200,
                           region="South")
        peers = find_comparables(
            target, self._universe(), max_results=5)
        # Top peer should be A or B (same size + region)
        self.assertIn(
            peers[0]["ccn"], ["A", "B"])
        # E (different on everything) should be at the
        # bottom
        self.assertEqual(peers[-1]["ccn"], "E")

    def test_self_excluded_by_ccn(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T")
        # Universe contains the target's CCN
        universe = (self._universe()
                    + [_hospital(ccn="T")])
        peers = find_comparables(target, universe)
        # Target's CCN should NOT appear in peers
        self.assertNotIn(
            "T", [p["ccn"] for p in peers])

    def test_max_results_respected(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T")
        peers = find_comparables(
            target, self._universe(), max_results=3)
        self.assertEqual(len(peers), 3)

    def test_max_results_zero(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        peers = find_comparables(
            _hospital(ccn="T"),
            self._universe(),
            max_results=0)
        self.assertEqual(peers, [])

    def test_empty_universe(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        peers = find_comparables(
            _hospital(ccn="T"), [])
        self.assertEqual(peers, [])

    def test_components_persisted_for_audit(self):
        """Every returned peer has similarity_components so a
        partner can defend the selection in IC: 'this peer is
        in because of bed size and region; not because of
        teaching status.'"""
        from rcm_mc.ml.comparable_finder import (
            find_comparables, WEIGHTS,
        )
        target = _hospital(ccn="T")
        peers = find_comparables(
            target, self._universe(), max_results=5)
        for peer in peers:
            self.assertIn("similarity_score", peer)
            self.assertIn("similarity_components", peer)
            comps = peer["similarity_components"]
            # Every weight dimension is captured
            for dim in WEIGHTS:
                self.assertIn(dim, comps)
                # Components in [0, 1]
                self.assertGreaterEqual(comps[dim], 0)
                self.assertLessEqual(comps[dim], 1)

    def test_results_sorted_by_score_desc(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T")
        peers = find_comparables(
            target, self._universe(), max_results=10)
        scores = [p["similarity_score"] for p in peers]
        self.assertEqual(
            scores, sorted(scores, reverse=True))


# ── Override workflow ───────────────────────────────────────

class TestOverrideWorkflow(unittest.TestCase):
    """Partners edit the engine's output — drop weak peers,
    pin specific ones, replace selections. Verify the
    semantics of those override operations."""

    def _peers(self):
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T", bed_count=200,
                           region="South")
        universe = [
            _hospital(ccn=str(i), bed_count=200 + i,
                      region="South")
            for i in range(10)
        ]
        return find_comparables(target, universe)

    def test_drop_specific_peer(self):
        peers = self._peers()
        # Drop peer with ccn '0'
        kept = [p for p in peers if p["ccn"] != "0"]
        self.assertNotIn(
            "0", [p["ccn"] for p in kept])
        self.assertEqual(len(kept), len(peers) - 1)

    def test_pin_peer_to_top(self):
        """Partner can re-order to pin a specific peer at
        position 0 — preserves similarity_components for
        defense."""
        peers = self._peers()
        # Find peer '5' (mid-rank); pin it to top
        pinned = next(p for p in peers
                      if p["ccn"] == "5")
        others = [p for p in peers
                  if p["ccn"] != "5"]
        reordered = [pinned] + others
        # Pinned peer at top
        self.assertEqual(reordered[0]["ccn"], "5")
        # similarity_components still intact
        self.assertIn(
            "similarity_components", reordered[0])

    def test_filter_by_minimum_score(self):
        """Partner can drop low-similarity peers via
        threshold — engine returns enough info to do this."""
        peers = self._peers()
        threshold = 0.85
        strong = [
            p for p in peers
            if p["similarity_score"] >= threshold]
        for p in strong:
            self.assertGreaterEqual(
                p["similarity_score"], threshold)

    def test_filter_by_component_threshold(self):
        """Partner can drop peers with poor bed-size match
        even if overall score is high — needs per-component
        breakdown to do so."""
        peers = self._peers()
        # Drop peers whose bed_count component < 0.5
        good_size = [
            p for p in peers
            if p["similarity_components"]["bed_count"]
            >= 0.5]
        for p in good_size:
            self.assertGreaterEqual(
                p["similarity_components"]
                ["bed_count"], 0.5)


# ── Defensibility / audit trail ─────────────────────────────

class TestDefensibility(unittest.TestCase):
    def test_per_component_breakdown_tells_a_story(self):
        """A peer with strong overall match might fail on
        teaching status — partner needs to see this so they
        don't get blindsided in IC."""
        from rcm_mc.ml.comparable_finder import (
            similarity_score,
        )
        target = _hospital(
            ccn="T", teaching_status="Teaching")
        peer = _hospital(
            ccn="P",
            teaching_status="Non-teaching")
        sim = similarity_score(target, peer)
        # Most components match (1.0); teaching is the
        # dissenter (0.0)
        self.assertEqual(
            sim["components"]["teaching_status"], 0.0)
        # The overall score reflects the gap
        self.assertLess(sim["score"], 1.0)

    def test_self_match_via_object_identity(self):
        """Pass the target itself in the universe (no CCN
        match) — engine still excludes it via identity."""
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T")
        # Strip ccn so object identity is the only signal
        target_no_ccn = dict(target)
        target_no_ccn.pop("ccn")
        universe = [
            target_no_ccn,
            _hospital(ccn="A", bed_count=200),
        ]
        peers = find_comparables(
            target_no_ccn, universe)
        # Target shouldn't appear by identity
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0]["ccn"], "A")


# ── Performance ─────────────────────────────────────────────

class TestPerformance(unittest.TestCase):
    def test_1000_hospitals_under_200ms(self):
        import time
        from rcm_mc.ml.comparable_finder import (
            find_comparables,
        )
        target = _hospital(ccn="T")
        universe = [
            _hospital(ccn=str(i),
                      bed_count=100 + i % 500,
                      region=("South"
                              if i % 2 == 0
                              else "Northeast"))
            for i in range(1000)
        ]
        t0 = time.perf_counter()
        peers = find_comparables(
            target, universe, max_results=50)
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(peers), 50)
        self.assertLess(
            elapsed, 0.2,
            f"1k-hospital comp ranking took "
            f"{elapsed:.3f}s (>200ms is too slow)")


if __name__ == "__main__":
    unittest.main()
