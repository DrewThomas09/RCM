"""b169 — pipeline funnel bar widths.

PROMPTS.md Phase 1 / Prompt 8: with seven stages, the home-page
Pipeline Funnel scaled each bar against the *total* deal count.
That meant the busiest stage never exceeded ~30% bar width — every
bar read as a near-empty rectangle, the funnel shape was invisible.

Fix: scale each bar against the busiest stage (peak) so the leading
stage fills 100%. Keep a 2% minimum so empty stages still show the
baseline track.

The right-hand percentage label still shows share-of-total, which is
the right metric for "what fraction of pipeline sits here."
"""
from __future__ import annotations

import inspect
import unittest


class FunnelScalesAgainstPeak(unittest.TestCase):

    def test_peak_denominator_present(self) -> None:
        from rcm_mc.ui.chartis import home_page

        src = inspect.getsource(home_page._pipeline_funnel)
        # The fix must scale bar width against the busiest stage.
        self.assertIn("peak", src,
                      "funnel must compute a peak/max-count denominator")
        self.assertIn("(n / peak)", src,
                      "bar width must be n / peak (not n / total)")

    def test_uneven_distribution_produces_full_width_leading_bar(
        self,
    ) -> None:
        # Build a synthetic store-like object where one stage holds
        # most of the volume, others are sparse. Verify the leading
        # bar's inline width is 100% (or near it after the int()).
        from rcm_mc.ui.chartis.home_page import _STAGES, _pipeline_funnel

        class FakeStore:
            def list_deals(self):
                # 10 deals in the busiest stage, 1 in the next two,
                # nothing elsewhere — simulates a realistic top-heavy
                # funnel where the screening stage dominates.
                rows = [{"stage": _STAGES[0]}] * 10
                rows += [{"stage": _STAGES[1]}, {"stage": _STAGES[2]}]
                return rows

        html = _pipeline_funnel(FakeStore())
        # Leading bar must be 100% wide (or 99% — int() floor) — the
        # peak stage should fill the track.
        self.assertTrue(
            "width:100%" in html or "width:99%" in html,
            f"leading-stage bar should fill the track; got HTML: {html[:400]}",
        )

    def test_zero_count_stage_keeps_baseline_track(self) -> None:
        # An empty stage must still produce a visible 2% track so the
        # row is anchored visually rather than collapsing to zero.
        from rcm_mc.ui.chartis.home_page import _STAGES, _pipeline_funnel

        class FakeStore:
            def list_deals(self):
                return [{"stage": _STAGES[0]}] * 5  # only stage 0 occupied

            # _pipeline_funnel calls `.to_dict("records")` if available.

        html = _pipeline_funnel(FakeStore())
        self.assertIn("width:2%", html,
                      "empty stages should render a 2% baseline track")


if __name__ == "__main__":
    unittest.main()
