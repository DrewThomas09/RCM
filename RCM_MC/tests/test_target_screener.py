"""PR E — unified Target Screener under Source.

One entry that explains and routes to the three overlapping screeners (Thesis
Sourcing, Hospital Screener, Predictive Screener), all over the same CMS/HCRIS
universe. The three old routes are PRESERVED unchanged (backward compatible).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TargetScreenerRenderTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.h = render_target_screener({})

    def test_unified_header_and_cms_label(self):
        self.assertIn("Target Screener", self.h)
        self.assertIn("CMS PUBLIC DATA", self.h)        # market data, not deals

    def test_three_modes_route_to_existing_screeners(self):
        for href in ("/source", "/screen", "/predictive-screener"):
            self.assertIn(f'href="{href}"', self.h)

    def test_explains_same_universe(self):
        low = self.h.lower()
        self.assertIn("same", low)
        self.assertIn("universe", low)
        self.assertIn("promote", low)                   # path into Pipeline

    def test_active_mode_highlights(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.assertIn("is-active", render_target_screener({"mode": ["hospital"]}))


class WorkbenchShellTests(unittest.TestCase):
    """PR 2 — the six-screen workbench shell (view= states), recreated
    PEdesk-native from the workbench-full.html handoff."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_six_screens_render(self):
        for view in ("main", "inspector", "columns", "compare", "missed", "saved"):
            h = self._render(view=view)
            self.assertIn("<!doctype html>", h.lower(), view)
            self.assertIn("Target Screener", h, view)

    def test_view_param_selects_active_tab(self):
        h = self._render(view="compare")
        # The active tab carries aria-current=page on the Compare link.
        self.assertIn('aria-current="page"', h)
        self.assertIn("view=compare", h)  # tab links carry view=

    def test_bogus_view_falls_back_to_main(self):
        h = self._render(view="nope")
        self.assertIn("<!doctype html>", h.lower())

    def test_all_six_tabs_present(self):
        h = self._render()
        # Tabs italicize an emphasis word (e.g. "Just <em>missed</em>"), so
        # assert the rendered tokens + the workbench numerals 01..06.
        for token in ("Main", "Inspector", "Columns", "Compare",
                      "missed", "Saved"):
            self.assertIn(token, h, token)
        for num in ("01", "02", "03", "04", "05", "06"):
            self.assertIn(f'tsw-num">{num}', h, num)

    def test_vertical_selector_includes_live_verticals(self):
        h = self._render()
        for label in ("Hospitals", "Home Health", "Hospice", "SNF",
                      "Dialysis", "IRF", "LTCH"):
            self.assertIn(label, h, label)

    def test_vertical_param_activates(self):
        h = self._render(vertical="hospice")
        self.assertIn("tsw-vert is-active", h)
        self.assertIn("Hospice", h)

    def test_no_iframe_prototype_shipped(self):
        for view in ("main", "compare", "saved"):
            self.assertNotIn("<iframe", self._render(view=view).lower())

    def test_no_prototype_external_font(self):
        # The shell loads PEdesk house fonts; the page must not add the
        # prototype's Public Sans / a bespoke CDN font.
        self.assertNotIn("Public Sans", self._render())

    def test_empty_states_are_labeled_not_faked(self):
        # All six screens are built; the remaining scaffolds are honest EMPTY
        # states (inspector with no CCN, compare with empty basket) — never
        # fabricated data.
        self.assertIn("Scaffold", self._render(view="inspector"))   # no ccn
        self.assertIn("Scaffold", self._render(view="compare"))     # empty basket

    # ── 2026-05-28 layout-fix regression pins ────────────────────────
    # The user reported (a) two CMS PUBLIC DATA pills stacked under the
    # title, (b) overlapping/jumbled text inside the workbench tabs, and
    # (c) the mode-card "selection" panel appearing below the map and
    # ranked-providers table. Each of these is now load-bearing
    # behavior — pin them so the bugs can't quietly come back.

    def test_only_one_cms_pill_renders(self):
        # The page must render exactly one CMS PUBLIC DATA pill (the one
        # inside the ck_source_purpose strip). A second standalone pill
        # underneath the title was the "two CMS public data things"
        # the user reported.
        import re
        h = self._render()
        chips = re.findall(r'<span class="ck-universe ck-universe-cms"', h)
        self.assertEqual(len(chips), 1,
                         f"expected exactly one CMS pill, got {len(chips)}")

    def test_workbench_tabs_have_tsw_meta_css(self):
        # .tsw-meta is the flex-column wrapper that stacks each tab's
        # title and subtitle. Without it the two spans render inline
        # and overlap (which the user saw as the "jumbled textbar").
        h = self._render()
        self.assertIn(".tsw-meta{display:flex", h)
        # And the HTML still uses the wrapper.
        self.assertIn('class="tsw-meta"', h)

    def test_modes_panel_precedes_map_and_table(self):
        # Pinned by 2026-05-28 better-fitted redesign: the entry-point
        # mode cards now live in the merged universe panel (sub-block
        # 3) rather than as their own panel. They still must render
        # ABOVE the map and the ranked-providers table — pin by the
        # FIRST mode label so the test survives future panel renames.
        h = self._render()
        modes_idx = h.find("Thesis Sourcing")
        map_idx = h.find("Provider density")
        table_idx = h.find("Ranked providers")
        self.assertGreater(modes_idx, 0, "Thesis Sourcing entry-point missing")
        self.assertGreater(map_idx, 0, "map panel missing")
        self.assertGreater(table_idx, 0, "table panel missing")
        self.assertLess(modes_idx, map_idx,
                        "entry-point modes must render before the map panel")
        self.assertLess(map_idx, table_idx,
                        "map panel must render before the ranked-providers table")

    # ── 2026-05-28 better-fitted redesign pins ──────────────────────
    # Stop the layout from quietly drifting back to 5+ stacked navy
    # panels. The merged "Choose a universe & entry point" panel is
    # the load-bearing top-of-page surface; if it splinters back into
    # separate vertical-bar / Active-universe / modes panels, the
    # "jumbled" feedback the user described will return.

    def test_main_view_has_four_ck_panels(self):
        # Main view should render exactly 4 panels: merged universe
        # panel, map, table, next-steps. The pre-redesign page had
        # 5+ and the partner reported it as visually noisy.
        import re
        h = self._render()
        titles = re.findall(r'class="ck-panel-title">([^<]+)<', h)
        self.assertEqual(
            len(titles), 4,
            f"expected 4 panels in main view, got {len(titles)}: {titles}")

    def test_merged_universe_panel_has_three_sub_blocks(self):
        # The merged panel groups three named sub-blocks (universe
        # selector / active screen summary / pre-set entry points)
        # behind a single navy header strip. Each sub-block has a
        # ts-univ-block wrapper so the hairline separators stay
        # consistent — pin that count.
        import re
        h = self._render()
        sub_blocks = re.findall(r'<div class="ts-univ-block">', h)
        self.assertEqual(len(sub_blocks), 3,
                         f"expected 3 ts-univ-block sub-blocks, got {len(sub_blocks)}")
        # And the three sub-block eyebrow labels are present.
        for lbl in ("Universe", "Active screen",
                    "Or start with a pre-set entry point"):
            self.assertIn(f'class="ts-univ-lbl">{lbl}<', h, lbl)

    def test_trailing_footer_panel_dropped(self):
        # The redundant "One universe, one workbench" closer panel
        # at the very bottom is gone — its content was duplicated by
        # the source-purpose strip + the next-steps panel.
        h = self._render()
        self.assertNotIn("One universe, one workbench", h)

    def test_entry_point_mode_cards_dropped_open_x_line(self):
        # Mode cards now show just the label + the "how" subtitle.
        # The ALL-CAPS "OPEN X →" footer line was the bulk of each
        # card's vertical footprint and is now removed; the hover
        # affordance still conveys clickability.
        h = self._render()
        # The CSS class for the dropped line should no longer be
        # referenced in the rendered HTML.
        self.assertNotIn('class="ts-mode-go"', h)

    # ── 2026-05-28 Wave 1 — active filter chips ───────────────────
    # Pre-existing pain: state/min-quality/min-size/ownership filters
    # were surfaced in 4 different places (state in the map summary;
    # the other three only in the table's filter-form clear-link,
    # which only appeared if a filter was already set). A partner
    # couldn't glance at the top of the page and answer "what's
    # filtered?". The Active-screen sub-block now renders a chip
    # per active filter, each a one-click "remove" link, plus a
    # "Clear all filters" link when 2+ are active.

    def test_filter_chips_hidden_when_no_filters(self):
        # The chip strip element is suppressed on a clean page load
        # so it doesn't add visual noise to the default state.
        h = self._render()
        self.assertNotIn('<div class="ts-fchips"', h)

    def test_state_filter_renders_chip(self):
        h = self._render(state="TX")
        self.assertIn('<div class="ts-fchips"', h)
        self.assertIn('ts-fchip-lbl">State<', h)
        self.assertIn('ts-fchip-val">TX<', h)
        # One chip → no clear-all link yet.
        self.assertNotIn("Clear all filters", h)

    def test_multiple_filters_render_chips_and_clear_all(self):
        import re
        h = self._render(state="CA", min_quality="3", ownership="for-profit")
        chips = re.findall(r'<a class="ts-fchip" href="', h)
        self.assertEqual(len(chips), 3,
                         f"expected 3 chips, got {len(chips)}")
        self.assertIn("Clear all filters", h)
        # Each chip carries a real removable URL — clear-all goes back
        # to the unfiltered universe view.
        self.assertIn(
            '/target-screener?view=main&vertical=snf"',
            h.replace("hospitals", "snf"),  # canonical clear-all shape
        )

    # ── 2026-05-28 Wave 2 — universe chip provider counts ────────
    # Each vertical chip now carries a real CMS provider-count badge
    # so the partner can compare scale across universes at a glance
    # without clicking into each. Geo verticals (provider_supply,
    # market) have no provider universe → no count rendered.

    def test_universe_chip_has_provider_count_badge(self):
        # Live verticals carry a numeric count in a <span class="n">.
        h = self._render()
        # The active vertical (hospitals) and at least one inactive
        # vertical should both carry counts in the chip strip.
        self.assertIn('<span class="n">', h)
        import re
        # Find every count badge in the chip strip.
        badges = re.findall(r'<span class="n">([\d,]+)</span>', h)
        # 7 live verticals (hospitals, HHA, hospice, SNF, dialysis,
        # IRF, LTCH) each carry a count; provider_supply and market
        # are geo screens with no provider universe.
        self.assertGreaterEqual(
            len(badges), 7,
            f"expected at least 7 chip-count badges, got {len(badges)}")
        # Each badge is a positive number (no fabricated zeros).
        for b in badges:
            self.assertGreater(int(b.replace(",", "")), 0, b)

    def test_geo_verticals_have_no_count_badge_on_their_chip(self):
        # The provider_supply and market chips render WITHOUT a
        # numeric count — those verticals screen geographies, not
        # providers. Inject nothing rather than fabricating a value.
        import re
        h = self._render()
        # The chip HTML pattern includes the universe label and an
        # optional .n span. Extract the chip block for each geo
        # vertical and assert no .n span inside.
        for slug, label in (("provider_supply", "Provider Supply"),
                            ("market", "Market")):
            chip_blocks = re.findall(
                rf'<a class="tsw-vert[^"]*" href="[^"]*vertical={slug}[^"]*"[^>]*>'
                r'(.*?)</a>',
                h, re.DOTALL)
            self.assertEqual(len(chip_blocks), 1,
                             f"{slug} chip not found uniquely")
            self.assertNotIn(
                'class="n"', chip_blocks[0],
                f"{label} chip should not carry a provider-count badge")

    def test_chip_remove_link_drops_only_that_param(self):
        import re
        h = self._render(state="TX", min_quality="4")
        # Find each chip and its href.
        chips = re.findall(
            r'<a class="ts-fchip" href="([^"]+)"[^>]*>'
            r'.*?ts-fchip-lbl">([^<]+)<.*?ts-fchip-val">([^<]+)<',
            h, re.DOTALL)
        self.assertEqual(len(chips), 2)
        by_label = {lbl: href for href, lbl, _val in chips}
        # The State chip's removal href drops state= but keeps min_quality=4.
        self.assertNotIn("state=TX", by_label["State"])
        self.assertIn("min_quality=4", by_label["State"])
        # The Min quality chip's removal href drops min_quality but keeps state=TX.
        self.assertNotIn("min_quality=4", by_label["Min quality"])
        self.assertIn("state=TX", by_label["Min quality"])


class WorkbenchMapTests(unittest.TestCase):
    """PR 3 — real US map (reuses render_us_geo_map), state click→filter,
    layer selector, legend, real provider-count shading."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_real_geo_map_not_squares(self):
        h = self._render(view="main", vertical="home_health")
        self.assertIn("usgeo-state", h)          # real SVG choropleth
        self.assertIn("<path", h)                # vector paths, not tiles
        self.assertNotIn("usm-tile", h)          # not the square cartogram

    def test_state_click_listener_present(self):
        self.assertIn("us-map-select", self._render(view="main"))

    def test_state_param_selects_and_shows_filter(self):
        h = self._render(view="main", vertical="hospice", state="TX")
        self.assertIn("usgeo-selected", h)       # TX highlighted
        self.assertIn("Filtered to", h)
        self.assertIn("clear state filter", h)

    def test_layer_selector_present(self):
        h = self._render(view="main")
        self.assertIn("Map layer", h)
        self.assertIn("Provider count", h)

    def test_real_provider_counts_present(self):
        # The map summary states a real provider total for the vertical.
        from rcm_mc.ui.target_screener_page import _provider_counts_by_state
        counts = _provider_counts_by_state("home_health")
        self.assertGreater(sum(counts.values()), 100)   # real CMS HHA universe
        self.assertGreater(len(counts), 30)

    def test_provider_counts_safe_on_unknown_vertical(self):
        from rcm_mc.ui.target_screener_page import _provider_counts_by_state
        self.assertEqual(_provider_counts_by_state("nope"), {})

    def test_map_has_legend(self):
        h = self._render(view="main", vertical="dialysis")
        self.assertIn("usgeo-legend", h)
        self.assertIn("No data", h)


class WorkbenchTableTests(unittest.TestCase):
    """PR 4 — ranked provider table from the real CMS loaders, state-scoped,
    with X-Ray / Inspect links and honest missingness."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_table_renders_real_rows_per_vertical(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        for v in ("hospitals", "home_health", "hospice", "snf", "dialysis", "irf", "ltch"):
            rows = _vertical_rows(v)
            self.assertGreater(len(rows), 10, v)
            self.assertTrue(all(r["ccn"] for r in rows), v)

    def test_rows_link_to_universal_xray(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn("/diligence/xray?ccn=", h)
        self.assertIn("&vertical=snf", h)

    def test_state_filter_narrows_rows(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        allrows = _vertical_rows("ltch")
        tx = _vertical_rows("ltch", "TX")
        self.assertLess(len(tx), len(allrows))
        self.assertTrue(all(r["state"] == "TX" for r in tx))

    def test_missing_values_render_dash_not_fake(self):
        # A real provider with no reported quality shows '—', never a number.
        h = self._render(view="main", vertical="hospice")
        self.assertIn("—", h)
        self.assertIn("not reported", h)  # honest caveat copy

    def test_source_chip_present(self):
        h = self._render(view="main", vertical="dialysis")
        self.assertIn("CMS Dialysis Compare", h)

    def test_rows_safe_on_unknown_vertical(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        self.assertEqual(_vertical_rows("nope"), [])

    def test_table_capped(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows, _TABLE_LIMIT
        self.assertLessEqual(len(_vertical_rows("home_health")), _TABLE_LIMIT)


class WorkbenchCompareTests(unittest.TestCase):
    """PR 5 — compare basket: same-vertical full, cross-vertical shared-only."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def _ccns(self, vertical, n=2):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        return [r["ccn"] for r in _vertical_rows(vertical)[:n]]

    def test_find_provider_resolves_real_ccn(self):
        from rcm_mc.ui.target_screener_page import _find_provider, _vertical_rows
        ccn = _vertical_rows("dialysis")[0]["ccn"]
        r = _find_provider(ccn)
        self.assertIsNotNone(r)
        self.assertEqual(r["vertical"], "dialysis")

    def test_find_provider_none_for_bogus(self):
        from rcm_mc.ui.target_screener_page import _find_provider
        self.assertIsNone(_find_provider("ZZZZZZ"))

    def test_empty_basket_state(self):
        self.assertIn("Compare basket (empty)", self._render(view="compare"))

    def test_same_vertical_compare_full(self):
        ccns = self._ccns("home_health", 3)
        h = self._render(view="compare", compare=",".join(ccns))
        self.assertIn("Comparing 3", h)
        self.assertIn("CMS X-Ray", h)
        self.assertNotIn("not directly comparable", h)  # single vertical

    def test_cross_vertical_shows_not_comparable(self):
        hh = self._ccns("home_health", 1)[0]
        dz = self._ccns("dialysis", 1)[0]
        h = self._render(view="compare", compare=f"{hh},{dz}")
        self.assertIn("verticals", h)
        self.assertIn("not directly comparable", h)

    def test_missing_ccn_reported_not_faked(self):
        h = self._render(view="compare", compare="ZZZZZZ")
        self.assertTrue("resolved to a live provider" in h or "Not found" in h)

    def test_table_has_add_to_compare(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn("+Cmp", h)
        self.assertIn("view=compare&compare=", h)


class WorkbenchJustMissedTests(unittest.TestCase):
    """PR 6 — just-missed scan: single-criterion near-misses + missing-data."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_uncapped_rows_for_scan(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows, _TABLE_LIMIT
        full = _vertical_rows("snf", limit=None)
        self.assertGreater(len(full), _TABLE_LIMIT)  # scan sees the whole universe

    def test_prompt_without_thresholds(self):
        h = self._render(view="missed", vertical="snf")
        self.assertIn("Set a", h)
        self.assertIn("Scan", h)              # the GET filter form

    def test_scan_with_thresholds_shows_just_missed(self):
        h = self._render(view="missed", vertical="snf", min_quality="4", min_size="100")
        self.assertIn("just missed", h.lower())
        self.assertIn("Just missed because", h)  # the near-miss table header

    def test_missing_data_not_failed(self):
        h = self._render(view="missed", vertical="hospice", min_quality="50")
        # Providers with no reported metric are surfaced as missing, not failed.
        self.assertTrue("not reported" in h.lower() or "missing data" in h.lower())

    def test_relax_link_present_when_near_misses(self):
        h = self._render(view="missed", vertical="dialysis", min_quality="4")
        self.assertTrue("Relax" in h or "No single-criterion" in h)

    def test_filter_form_is_get_and_shareable(self):
        h = self._render(view="missed", vertical="irf", min_quality="50")
        self.assertIn('method="get"', h)
        self.assertIn('name="min_quality"', h)


class WorkbenchColumnsTests(unittest.TestCase):
    """PR 7 — column picker / metric dictionary: grouped, sourced, live
    availability counts."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_columns_grouped_with_source_and_availability(self):
        h = self._render(view="columns", vertical="snf")
        for cat in ("Identity", "Geography", "Ownership", "Quality", "Source"):
            self.assertIn(cat, h, cat)
        self.assertIn("Availability", h)

    def test_availability_is_real_fraction(self):
        # Availability cells read "<count>/<total> (NN%)" from the universe.
        import re
        h = self._render(view="columns", vertical="dialysis")
        self.assertRegex(h, r"\d[\d,]*/\d[\d,]*\s*\(\d+%\)")

    def test_additional_quality_columns_listed(self):
        from rcm_mc.ui.target_screener_page import _quality_keys
        self.assertGreater(len(_quality_keys("snf")), 3)
        self.assertIn("Additional", self._render(view="columns", vertical="snf"))

    def test_columns_safe_unknown_vertical(self):
        h = self._render(view="columns", vertical="nope")
        self.assertIn("<!doctype html>", h.lower())  # falls back to hospitals


class WorkbenchInspectorTests(unittest.TestCase):
    """PR 8 — inspector drawer: real identity, peer/market context, links, Guide."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def _ccn(self, vertical):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        return _vertical_rows(vertical)[0]["ccn"]

    def test_no_ccn_prompts(self):
        self.assertIn("no target selected", self._render(view="inspector").lower())

    def test_bad_ccn_reported(self):
        self.assertIn("did not resolve", self._render(view="inspector", ccn="ZZZZZZ"))

    def test_selected_target_shows_identity_and_peer_context(self):
        h = self._render(view="inspector", ccn=self._ccn("snf"))
        self.assertIn("Selected target", h)
        self.assertIn("Peer rank", h)
        self.assertIn("median", h.lower())

    def test_inspector_links_to_xray_and_pipeline(self):
        h = self._render(view="inspector", ccn=self._ccn("dialysis"))
        self.assertIn("/diligence/xray?ccn=", h)
        self.assertIn("Promote to Pipeline", h)
        self.assertIn("market context", h.lower())

    def test_inspector_has_guide_questions(self):
        h = self._render(view="inspector", ccn=self._ccn("hospice"))
        self.assertIn("Ask the Guide", h)

    def test_median_helper(self):
        from rcm_mc.ui.target_screener_page import _median
        self.assertEqual(_median([1, 2, 3]), 2)
        self.assertEqual(_median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(_median([None, "x"]))


class WorkbenchSavedTests(unittest.TestCase):
    """PR 9 — saved screens: shareable URL state + honest persistence caveat."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_current_screen_is_shareable_url(self):
        h = self._render(view="saved", vertical="snf", state="TX")
        self.assertIn("/target-screener?", h)
        self.assertIn("vertical=snf", h)
        self.assertIn("state=TX", h)
        self.assertIn("shareable", h.lower())

    def test_prebuilt_screens_present(self):
        h = self._render(view="saved")
        self.assertIn("Prebuilt screens", h)
        self.assertIn("Open screen", h)

    def test_anonymous_persistence_caveat_is_honest(self):
        # No session → honest "sign in to save", screens still shareable URLs.
        h = self._render(view="saved")
        self.assertIn("sign in to save", h.lower())
        self.assertIn("shareable", h.lower())

    def test_no_fake_alerts(self):
        h = self._render(view="saved")
        # Honest: we never claim alerts that aren't implemented.
        self.assertNotIn("alert enabled", h.lower())

    def test_owner_save_form_and_listing(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        # Empty list for a signed-in user → save form + empty message.
        h = render_target_screener({"view": ["saved"], "vertical": ["snf"]},
                                   saved=[], owner="alice")
        self.assertIn("Your saved screens (0)", h)
        self.assertIn("/api/target-screener/save", h)
        self.assertIn("Save current screen as", h)
        # With saved rows → list + per-row delete.
        h2 = render_target_screener(
            {"view": ["saved"]},
            saved=[{"id": 3, "title": "TX SNFs",
                    "query_params": "view=main&vertical=snf&state=TX",
                    "created_at": "2026-05-26T00:00:00+00:00"}],
            owner="alice")
        self.assertIn("TX SNFs", h2)
        self.assertIn("/api/target-screener/delete", h2)
        self.assertIn("owner-scoped", h2)


class WorkbenchGeoVerticalTests(unittest.TestCase):
    """PR 10 — provider_supply + market screened as STATE-level geography
    views (map + ranked state table), clearly not individual providers."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_provider_supply_geo_view_real(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, label, fmt, src = _geo_state_values("provider_supply", "supply")
        self.assertGreater(len(vals), 40)               # ~all states
        self.assertGreater(vals.get("TX", 0), 1000)     # real PECOS supply
        h = self._render(view="main", vertical="provider_supply")
        self.assertIn("usgeo-state", h)                 # real map
        self.assertIn("not individual providers", h.lower())
        self.assertIn("States ranked", h)

    def test_market_geo_view_metric_selector(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, *_ = _geo_state_values("market", "population")
        self.assertGreater(len(vals), 40)
        h = self._render(view="main", vertical="market", metric="age_65_plus")
        self.assertIn("Market metric", h)
        self.assertIn("Age 65+", h)
        self.assertIn("usgeo-state", h)

    def test_market_state_links_to_state_profile(self):
        # State rows/clicks deep-link to the real per-state page (/state-profile
        # consumes ?state=), not the generic /geo-intel hub which ignores it.
        h = self._render(view="main", vertical="market")
        self.assertIn("/state-profile?state=", h)
        self.assertNotIn("/geo-intel?state=", h)

    def test_geo_value_safe_on_failure(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, *_ = _geo_state_values("nope", "x")
        self.assertEqual(vals, {})


class WorkbenchMapLayerTests(unittest.TestCase):
    """PR 12 — functional demographic map layers (real ACS shading) overlaid
    on the provider screen; provider table stays."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_default_layer_is_provider_count(self):
        self.assertIn("provider count", self._render(view="main", vertical="snf").lower())

    def test_age65_layer_shades_real_acs(self):
        h = self._render(view="main", vertical="snf", layer="age65")
        self.assertIn("Age 65+", h)
        self.assertIn("market layer", h.lower())
        self.assertIn("usgeo-state", h)            # real map still
        self.assertIn("Ranked providers", h)        # provider table preserved

    def test_income_and_uninsured_layers(self):
        self.assertIn("Median HH income",
                      self._render(view="main", vertical="dialysis", layer="income"))
        self.assertIn("Uninsured",
                      self._render(view="main", vertical="hospice", layer="uninsured"))

    def test_unsourced_layers_link_out_not_faked(self):
        from rcm_mc.ui.target_screener_page import _LAYER_BY_KEY
        self.assertFalse(_LAYER_BY_KEY["market_score"].get("live"))
        self.assertTrue(_LAYER_BY_KEY["age65"].get("live"))


class WorkbenchPromoteTests(unittest.TestCase):
    """Promote-to-Pipeline carries the target into a prefilled deal form,
    completing Source → Pipeline (was a dead generic /pipeline link)."""

    def test_inspector_promote_carries_target(self):
        from rcm_mc.ui.target_screener_page import render_target_screener, _vertical_rows
        ccn = _vertical_rows("snf")[0]["ccn"]
        h = render_target_screener({"view": ["inspector"], "ccn": [ccn]})
        self.assertIn(f"/import?deal_id=snf_{ccn.lower()}", h)
        self.assertIn("name=", h)
        self.assertIn("Promote to Pipeline (prefilled", h)

    def test_import_form_prefills_from_params(self):
        from rcm_mc.ui.quick_import import render_quick_import
        h = render_quick_import(prefill={"deal_id": "snf_015010",
                                         "name": "Coosa Valley", "state": "AL"})
        self.assertIn('value="snf_015010"', h)
        self.assertIn('value="Coosa Valley"', h)
        self.assertIn('value="AL"', h)

    def test_import_form_empty_without_prefill(self):
        import re
        from rcm_mc.ui.quick_import import render_quick_import
        m = re.search(r'name="deal_id"[^>]*>', render_quick_import())
        self.assertNotIn("value=", m.group(0))


class WorkbenchColumnVisibilityTests(unittest.TestCase):
    """PR 18 — column-visibility toggles (?hide=) wired Columns ↔ Main."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_default_shows_all_columns(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn(">Ownership<", h)
        self.assertIn(">Source<", h)

    def test_hide_removes_columns_from_main(self):
        h = self._render(view="main", vertical="snf", hide="ownership,source")
        self.assertNotIn(">Ownership</th>", h)
        self.assertNotIn(">Source</th>", h)
        self.assertIn(">Provider", h)   # identity always shown

    def test_sort_links_preserve_hide(self):
        h = self._render(view="main", vertical="snf", hide="ownership")
        self.assertIn("hide=ownership", h)

    def test_columns_screen_has_visibility_toggles(self):
        h = self._render(view="columns", vertical="snf")
        self.assertIn("On Main table", h)
        self.assertIn("Shown · hide", h)

    def test_columns_screen_reflects_hidden_state(self):
        h = self._render(view="columns", vertical="snf", hide="quality")
        self.assertIn("Hidden · show", h)


class WorkbenchFilterTests(unittest.TestCase):
    """PR 17 — Main filter panel (?min_quality / min_size / ownership)."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_filter_form_present(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn("Apply filters", h)
        self.assertIn('name="min_quality"', h)
        self.assertIn("Ownership contains", h)

    def test_min_quality_narrows_matches(self):
        import re
        h = self._render(view="main", vertical="snf", min_quality="5")
        m = re.search(r"([\d,]+) match of ([\d,]+)", h)
        self.assertIsNotNone(m)
        self.assertLess(int(m.group(1).replace(",", "")),
                        int(m.group(2).replace(",", "")))

    def test_ownership_filter_applies(self):
        self.assertIn("match of",
                      self._render(view="main", vertical="dialysis", ownership="profit"))

    def test_impossible_filter_is_honest_no_match(self):
        h = self._render(view="main", vertical="snf", min_quality="99")
        self.assertIn("match these filters", h)
        self.assertIn("Just-missed", h)   # points to near-misses, never fakes rows

    def test_clear_link_when_filtered(self):
        self.assertIn(">clear<", self._render(view="main", vertical="snf", min_quality="4"))


class WorkbenchSortTests(unittest.TestCase):
    """PR 16 — sortable provider table columns (?sort=&direction=)."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def _names(self, html):
        import re
        return re.findall(r'font-weight:600;">(.*?)<span style="font-family:var\(--sc-mono\)', html)

    def test_headers_are_sortable_links(self):
        h = self._render(view="main", vertical="snf")
        for col in ("sort=name", "sort=quality", "sort=size", "sort=location"):
            self.assertIn(col, h)

    def test_name_asc_orders_alphabetically(self):
        h = self._render(view="main", vertical="snf", sort="name", direction="asc")
        nm = [n.lower() for n in self._names(h)]
        self.assertEqual(nm, sorted(nm))
        self.assertTrue(nm)

    def test_name_desc_reverses(self):
        h = self._render(view="main", vertical="snf", sort="name", direction="desc")
        nm = [n.lower() for n in self._names(h)]
        self.assertEqual(nm, sorted(nm, reverse=True))

    def test_sort_arrow_shown(self):
        h = self._render(view="main", vertical="snf", sort="quality", direction="desc")
        self.assertTrue(("▾" in h) or ("▴" in h))

    def test_default_unsorted_is_quality_ranked(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        rows = _vertical_rows("snf", "TX")
        qs = [r["q"] for r in rows if r["q"] is not None]
        self.assertEqual(qs, sorted(qs, reverse=True))


class WorkbenchCsvExportTests(unittest.TestCase):
    """PR 14 — CSV export of the current screen (real loader rows)."""

    def test_vertical_dataframe_real(self):
        from rcm_mc.ui.target_screener_page import vertical_dataframe
        df = vertical_dataframe("snf", "TX")
        self.assertGreater(len(df), 5)
        for col in ("ccn", "name", "state", "ownership", "source"):
            self.assertIn(col, df.columns)
        self.assertTrue((df["state"] == "TX").all())

    def test_dataframe_empty_unknown_vertical(self):
        from rcm_mc.ui.target_screener_page import vertical_dataframe
        self.assertTrue(vertical_dataframe("nope").empty)

    def test_download_link_on_main(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener({"view": ["main"], "vertical": ["dialysis"],
                                    "state": ["CA"]})
        self.assertIn("/target-screener.csv?vertical=dialysis", h)
        self.assertIn("Download CSV", h)


class NavAndRouteTests(unittest.TestCase):
    def test_source_nav_lands_on_catalog_target_screener_first(self):
        # Source nav now lands on the grouped catalog (the /diligence pattern),
        # with Target Screener still the first tool in it + leading the sub-nav.
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV, _SUB_NAV, _resolve_sub_section
        src = next(n for n in _CORPUS_NAV if n["key"] == "source")
        self.assertEqual(src["href"], "/best/source")
        self.assertEqual(_SUB_NAV["source"][0]["label"], "Target Screener")
        self.assertEqual(_resolve_sub_section("/target-screener"), "source")
        from rcm_mc.ui.section_landings import render_section_landing
        self.assertIn("/target-screener", render_section_landing("source"))


class BackwardCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _status(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_target_screener_route_200(self):
        self.assertEqual(self._status("/target-screener"), 200)

    def test_all_six_views_route_200(self):
        # Every screen renders end-to-end through the real server (the saved
        # view exercises the list_screens persistence path too).
        for view in ("main", "inspector", "columns", "compare", "missed", "saved"):
            self.assertEqual(self._status(f"/target-screener?view={view}"), 200, msg=view)

    def test_csv_export_route_200(self):
        self.assertEqual(self._status("/target-screener.csv?vertical=ltch&state=TX"), 200)

    def test_old_screener_routes_still_work(self):
        # No redirects/deletes — the three screeners are unchanged.
        for path in ("/source", "/screen", "/predictive-screener"):
            self.assertEqual(self._status(path), 200, msg=path)

    def test_no_data_columns_hidden_not_shown_at_zero(self):
        # Hospitals report no ownership / operating-margin in HCRIS — those
        # columns must be dropped entirely (never shown at 0%), and the page
        # tells the reader they were hidden.
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener({"view": ["columns"], "vertical": ["hospitals"]})
        self.assertNotIn("Ownership / consolidation", h)   # 0% → dropped
        self.assertIn("Hidden for this universe", h)
        self.assertNotIn("(0%)", h)                         # no empty columns

    def test_data_columns_still_shown_where_available(self):
        # A universe that DOES carry ownership keeps the column — the hide is
        # data-driven, not blanket.
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener({"view": ["columns"], "vertical": ["snf"]})
        self.assertIn("Ownership / consolidation", h)

    def test_universe_kpi_strip_shows_real_counts(self):
        # The main view leads with a computed at-a-glance read of the universe
        # (real provider count + jurisdictions), so it's informative pre-filter.
        from rcm_mc.ui.target_screener_page import render_target_screener, _vertical_rows
        h = render_target_screener({"view": ["main"], "vertical": ["hospitals"]})
        self.assertIn("ck-kpi-grid", h)
        self.assertIn("Providers", h)
        self.assertIn("territories", h)   # "States &amp; territories" (escaped)
        # the real provider count is shown verbatim
        n = len(_vertical_rows("hospitals", limit=None))
        self.assertIn(f"{n:,}", h)

    def test_market_view_also_leads_with_kpis(self):
        # The state/market universes (no provider rows) get a state-level KPI
        # read too, so every one of the 9 universes opens informative.
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener({"view": ["main"], "vertical": ["market"]})
        self.assertIn("ck-kpi-grid", h)
        self.assertIn("territories", h)   # States & territories with data
        self.assertIn("Highest", h)


if __name__ == "__main__":
    unittest.main()
