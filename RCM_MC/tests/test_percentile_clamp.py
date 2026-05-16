"""Tests for the ``_percentile`` closure inside
:func:`rcm_mc.analysis.packet_builder._merge_rcm_profile`.

Why this test exists: ``_merge_rcm_profile`` computes a
``benchmark_percentile`` on every merged ``ProfileMetric`` by counting
peer values below the target and dividing by the peer-cohort size.
The math is in [0, 1] today by construction (strict less-than counter
over a list whose emptiness is already guarded), but the rendered
value can leak into the UI; if a future refactor breaks the
invariant (weighted counts, non-strict predicate, etc.), partners
would see >100% or <0% percentile cells.

Audit framing was directionally right but mis-stated the n==0
issue — that's already guarded at line 316 via ``if not vals:
return None``. The genuinely-needed defensive fix is the [0, 1]
clamp on the return value.

These tests exercise ``_merge_rcm_profile`` via its public surface
(no closure extraction, no scope expansion) and pin the
``benchmark_percentile`` range so the clamp can't silently regress.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.packet import (
    ComparableHospital,
    ObservedMetric,
)
from rcm_mc.analysis.packet_builder import _merge_rcm_profile


def _peer(idx: int, **fields) -> ComparableHospital:
    return ComparableHospital(
        id=f"peer_{idx}",
        similarity_score=1.0,
        fields=dict(fields),
    )


def _obs(value: float) -> ObservedMetric:
    return ObservedMetric(value=float(value), source="USER_INPUT")


class TestPercentileClamp(unittest.TestCase):
    def _merge_and_pct(self, target_value, peer_values):
        peers = [_peer(i, denial_rate=v) for i, v in enumerate(peer_values)]
        observed = {"denial_rate": _obs(target_value)}
        merged = _merge_rcm_profile(
            observed=observed, predicted={}, peers=peers,
        )
        return merged["denial_rate"].benchmark_percentile

    def test_target_below_all_peers_returns_zero(self):
        # No peer is below target → percentile = 0
        pct = self._merge_and_pct(target_value=1.0, peer_values=[5.0, 6.0, 7.0])
        self.assertEqual(pct, 0.0)

    def test_target_above_all_peers_returns_one(self):
        # All peers below target → percentile = 1.0 (not >1.0)
        pct = self._merge_and_pct(target_value=10.0, peer_values=[1.0, 2.0, 3.0])
        self.assertEqual(pct, 1.0)

    def test_target_equal_to_all_peers_returns_zero(self):
        # Strict less-than semantics: peers equal to target are NOT
        # counted as below. This is the existing (pre-fix) behavior;
        # the clamp doesn't change it.
        pct = self._merge_and_pct(target_value=5.0, peer_values=[5.0, 5.0, 5.0])
        self.assertEqual(pct, 0.0)

    def test_target_at_median_returns_half(self):
        # 5 peers, 2 strictly below target=3.0 → 2/5 = 0.4
        pct = self._merge_and_pct(target_value=3.0, peer_values=[1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(pct, 0.4)

    def test_no_peer_data_for_metric_returns_none(self):
        # Empty-vals guard at line 316 already handles this; verify the
        # clamp doesn't accidentally coerce None into a numeric.
        peers = [_peer(0, other_metric=5.0)]  # no denial_rate field
        observed = {"denial_rate": _obs(3.0)}
        merged = _merge_rcm_profile(
            observed=observed, predicted={}, peers=peers,
        )
        self.assertIsNone(merged["denial_rate"].benchmark_percentile)

    def test_no_peers_at_all_returns_none(self):
        observed = {"denial_rate": _obs(3.0)}
        merged = _merge_rcm_profile(
            observed=observed, predicted={}, peers=[],
        )
        self.assertIsNone(merged["denial_rate"].benchmark_percentile)

    def test_percentile_always_in_unit_interval(self):
        # Property test: across a range of target / peer-cohort
        # combinations, the percentile must always be in [0, 1] (or None).
        # If the clamp regresses, this catches values escaping the range.
        scenarios = [
            (0.0,  [1.0, 2.0, 3.0]),         # below
            (10.0, [1.0, 2.0, 3.0]),         # above
            (2.0,  [1.0, 2.0, 3.0]),         # mid
            (-5.0, [1.0, 2.0, 3.0]),         # negative target
            (1e9,  [1.0, 2.0, 3.0]),         # huge target
            (2.5,  [2.5]),                    # single peer equal
            (2.5,  [2.5, 2.5]),               # two equal peers
            (3.0,  [1.0, 2.0, 3.0, 4.0]),    # at value
        ]
        for target, peers in scenarios:
            with self.subTest(target=target, peers=peers):
                pct = self._merge_and_pct(target_value=target, peer_values=peers)
                self.assertIsNotNone(pct, f"percentile None for {target}/{peers}")
                self.assertGreaterEqual(
                    pct, 0.0,
                    f"percentile {pct} < 0 for target={target} peers={peers}",
                )
                self.assertLessEqual(
                    pct, 1.0,
                    f"percentile {pct} > 1 for target={target} peers={peers}",
                )


if __name__ == "__main__":
    unittest.main()
