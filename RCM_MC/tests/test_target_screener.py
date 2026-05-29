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

    def test_merged_universe_panel_has_four_sub_blocks(self):
        # The merged panel groups four named sub-blocks (universe
        # selector / active screen summary + filters / pre-set entry
        # points / map shading layer) behind a single navy header
        # strip. Each sub-block has a ts-univ-block wrapper so the
        # hairline separators stay consistent — pin that count.
        #
        # Wave-4 added the Map-layer sub-block (previously inlined at
        # the top of _render_map, which buried the control inside the
        # visualization). Now sits at the end of the universe panel
        # so it flows visually into the map panel below.
        import re
        h = self._render()
        sub_blocks = re.findall(r'<div class="ts-univ-block">', h)
        self.assertEqual(len(sub_blocks), 4,
                         f"expected 4 ts-univ-block sub-blocks, got {len(sub_blocks)}")
        for lbl in ("Universe", "Active screen",
                    "Or start with a pre-set entry point",
                    "Map layer"):
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
        # Wave-14: reset link now surfaces whenever ANY non-default
        # param is active (was: only when 2+). One chip is enough.
        h = self._render(state="TX")
        self.assertIn('<div class="ts-fchips"', h)
        self.assertIn('ts-fchip-lbl">State<', h)
        self.assertIn('ts-fchip-val">TX<', h)
        self.assertIn("Reset to defaults", h)
        # Old wording is gone.
        self.assertNotIn("Clear all filters", h)

    def test_multiple_filters_render_chips_and_reset_link(self):
        # Wave-14 renamed 'Clear all filters' to 'Reset to defaults'
        # and surfaces the link whenever ANY non-default param is
        # active (was: only when 2+). Tighter scope here: 3 filters
        # → 3 chips + reset link.
        import re
        h = self._render(state="CA", min_quality="3", ownership="for-profit")
        chips = re.findall(r'<a class="ts-fchip" href="', h)
        self.assertEqual(len(chips), 3,
                         f"expected 3 chips, got {len(chips)}")
        self.assertIn("Reset to defaults", h)
        # Each chip carries a real removable URL — reset goes back
        # to the unfiltered universe view.
        self.assertIn(
            '/target-screener?view=main&vertical=snf"',
            h.replace("hospitals", "snf"),  # canonical reset shape
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

    # ── 2026-05-28 Wave 3 — tab-bar compaction ────────────────────
    # Dropped the group meta-labels ('Workbench states' / 'Linked
    # screens') and the per-tab subtitle line ('SCREEN · MAP · TABLE'
    # etc) so the workbench tab strip is single-line and ~76% the
    # width of its pre-compaction self. Subtitles moved to title=
    # attributes so the discoverability is preserved on hover.

    def test_tab_bar_subtitle_line_dropped(self):
        # tsw-s was the per-tab subtitle <span>; no longer rendered.
        h = self._render()
        self.assertNotIn('class="tsw-s"', h)

    def test_tab_bar_group_labels_dropped(self):
        # tsw-glabel was the inline 'Workbench states' / 'Linked
        # screens' meta-label — also no longer rendered.
        h = self._render()
        self.assertNotIn('class="tsw-glabel"', h)
        self.assertNotIn("Workbench<br>states", h)
        self.assertNotIn("Linked<br>screens", h)

    def test_tab_bar_groups_visually_separated(self):
        # Even with no labels, the two tab groups (workbench states
        # 01-03 vs linked screens 04-06) stay visually divided by
        # the .tsw-group + .tsw-group { border-left … } CSS rule.
        import re
        h = self._render()
        groups = re.findall(r'<div class="tsw-group">', h)
        self.assertEqual(len(groups), 2,
                         f"expected 2 group divs, got {len(groups)}")

    # ── 2026-05-28 Wave 4 — map-layer relocation ─────────────────
    # The layer-selector chips used to render inline at the top of
    # _render_map (so they sat INSIDE the map panel). Wave-4 lifted
    # them out into a 4th sub-block of the merged universe panel,
    # placed at the END of that panel so the partner's eye flows
    # universe → state filter → entry points → map-layer chips →
    # map svg directly below.

    def test_layer_chips_now_render_above_map_panel(self):
        # The "Map layer" eyebrow label is the load-bearing pin from
        # the pre-existing test_layer_selector_present test — verify
        # it now sits in the universe panel (before the map panel),
        # not inside it.
        h = self._render()
        layer_idx = h.find('class="ts-univ-lbl">Map layer<')
        map_panel_idx = h.find("Provider density · click a state to filter")
        self.assertGreater(layer_idx, 0, "Map layer sub-block missing")
        self.assertGreater(map_panel_idx, 0, "map panel missing")
        self.assertLess(layer_idx, map_panel_idx,
                        "Map layer must render BEFORE the map panel")

    def test_tab_bar_subtitles_preserved_in_title_attribute(self):
        # Discoverability — hovering a tab reveals what the dropped
        # subtitle said. Title attributes are server-rendered so a
        # browser without CSS still has the hint.
        h = self._render()
        self.assertIn('title="SCREEN · MAP · TABLE"', h)
        self.assertIn('title="DRAWER · PEER · MARKET"', h)
        self.assertIn('title="MISS-DISTANCE SCAN"', h)

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

    # ── 2026-05-28 Wave 5 — top-N row-cap toggle ───────────────────
    # The ranked-providers table caps at 150 rows historically; the
    # partner had no way to focus on just the strongest 10/25/50/100
    # without scrolling. Wave-5 adds a chip strip above the table:
    #   Show top  [10] [25] [50] [100] [150]  of matches
    # Each chip is a real GET link that flips ?limit= while keeping
    # state / sort / direction / filters / hide / compare / layer.

    def test_topn_toggle_renders_all_five_chips(self):
        import re
        h = self._render()
        chips = re.findall(r'class="ts-topn-chip[^"]*"[^>]*>(\d+)<', h)
        self.assertEqual(chips, ["10", "25", "50", "100", "150"])

    def test_topn_default_active_is_150(self):
        import re
        h = self._render()
        active = re.findall(r'class="ts-topn-chip is-active"[^>]*>(\d+)<', h)
        self.assertEqual(active, ["150"])

    def test_topn_limit_param_actually_caps_table(self):
        # When ?limit=25 is set, the rendered table really shows 25
        # rows max — not just the chip highlighting. Pinned via the
        # 'Capped at N' line at the top of the panel.
        h = self._render(limit="25")
        self.assertIn("Capped at 25.", h)
        # And the active chip is now 25.
        import re
        active = re.findall(r'class="ts-topn-chip is-active"[^>]*>(\d+)<', h)
        self.assertEqual(active, ["25"])

    def test_topn_hostile_limit_falls_back_to_150(self):
        # A bookmark or hand-crafted URL with a value outside the
        # allowed set silently falls back to the historical 150
        # default — never lets a partner accidentally render
        # 99,999 rows.
        h = self._render(limit="9999")
        self.assertIn("Capped at 150.", h)

    def test_topn_chip_urls_preserve_other_params(self):
        import re
        h = self._render(limit="10", state="TX", min_quality="3")
        hrefs = re.findall(
            r'<a class="ts-topn-chip[^"]*" href="([^"]+)"', h)
        self.assertEqual(len(hrefs), 5)
        for href in hrefs:
            self.assertIn("state=TX", href)
            self.assertIn("min_quality=3", href)

    # ── 2026-05-28 Wave 6 — table client-side name/CCN/location filter
    # The top-N toolbar now hosts a search input next to the chips.
    # Typing anything filters the table rows in real time client-side
    # by matching against a lowercased data-ts-search blob on each
    # <tr> (name + CCN + city + state). Zero server round-trips.

    def test_table_rows_carry_search_blob_attribute(self):
        import re
        h = self._render()
        rows = re.findall(r'<tr data-ts-search="([^"]+)"', h)
        # Default cap is 150 rows in the hospitals universe (real
        # CMS HCRIS provides more than that; we cap for display).
        self.assertGreaterEqual(len(rows), 100,
                                f"expected >=100 searchable rows, got {len(rows)}")
        # Each blob should be lowercased so the JS substring match
        # is case-insensitive without runtime work.
        for blob in rows[:5]:
            self.assertEqual(blob, blob.lower(),
                             f"blob not lowercased: {blob!r}")
            # And carry at least the CCN (8-char digit string).
            self.assertRegex(blob, r"\d{6,}",
                             f"blob missing a CCN: {blob!r}")

    # ── 2026-05-28 Wave 7 — sticky workbench tab bar ─────────────
    # Pre-existing pain: scrolling into the long ranked-providers
    # table buried the workbench nav. Tab bar now sticks at top:58px
    # (right below the chartis_shell topbar at 0/58 height).

    # ── 2026-05-28 Wave 8 — collapsible refine-filters ───────────
    # The Min quality / Min size / Ownership form took ~50px of
    # permanent vertical space at the top of every ranked-providers
    # table render — for a control most partners use once a session.
    # Wave-8 wraps it in <details> so it collapses by default, and
    # auto-opens when any of its filters ARE active so the partner
    # never loses state on a server round-trip.

    def test_refine_filters_collapsed_by_default(self):
        h = self._render()
        self.assertIn('<details class="ts-refine"', h)
        # The detail is NOT open when no refine-filter is set.
        self.assertNotIn('<details class="ts-refine" open>', h)

    # ── 2026-05-28 Wave 9 — '/' keyboard hotkey ──────────────────
    # '/' anywhere on the page focuses the table search input
    # (standard GitHub / Slack / Linear pattern). ESC inside the
    # search input clears the value, re-runs the filter, blurs.

    # ── 2026-05-28 Wave 10 — state-scoped KPI tiles ──────────────
    # Pre-existing pain: the KPI strip in the Active-screen sub-block
    # always described the WHOLE universe ('6,123 providers / 50
    # states') even when the partner had filtered to one state — so
    # the headline numbers were lying about what the table below
    # was actually showing. Wave-10 rescopes _universe_kpis when
    # state= is set: counts and sub-labels reflect the state, and
    # the 'States & territories' tile is dropped (rendering '1'
    # adds no information).

    def test_unfiltered_kpis_describe_whole_universe(self):
        h = self._render()
        self.assertIn("in this universe", h)
        # The 'States & territories' tile is present without a state
        # filter.
        self.assertTrue(
            "States &amp; territories" in h or "States & territories" in h,
            "States & territories KPI tile should render unfiltered")

    # ── 2026-05-28 Wave 11 — compare-basket banner ───────────────
    # Pre-existing pain: clicking '+Cmp' on a row appended the CCN
    # to the ?compare= bucket, but the partner couldn't see what
    # was in the bucket without leaving the screen. Now: a small
    # banner above the table shows the count + a one-click 'View
    # comparison' link + a 'Clear basket' link. Hidden when empty.

    # ── 2026-05-28 Wave 12 — sort indicator + reset-sort link ────
    # The active sort + direction now surfaces in the 'Showing X of Y'
    # status line ('sorted by Provider name (ascending)') and the
    # active column header gets a ↓/↑ glyph + teal-deep weight. A
    # 'reset sort' link returns to the default quality-desc ranking
    # in one click while preserving every other current param.

    # ── 2026-05-28 Wave 13 — zero-match placeholder ──────────────
    # When the client-side search filter hides every row, the table
    # used to render as an empty box with no feedback. Now a hidden
    # <tr data-ts-empty> placeholder lives inside <tbody> and the
    # JS apply() handler reveals it with a 'No providers match X'
    # message + ESC hint when shown == 0.

    # ── 2026-05-28 Wave 14 — chips widened to layer + limit; reset
    # link always-on when any param is active ──────────────────────
    # The chip strip used to only catalog state / refines / sort.
    # Wave-14 adds chips for the map layer (when non-default
    # 'provider_count') and the row cap (when non-default 150)
    # so the partner sees every off-baseline selection in one
    # place. The reset link is renamed 'Reset to defaults' and
    # surfaces any time the strip is non-empty.

    def test_non_default_layer_renders_chip(self):
        # Wave-15: chip value reads as human-friendly label
        # ('Age 65+') not the URL slug ('age65').
        h = self._render(layer="age65")
        self.assertIn('ts-fchip-lbl">Map layer<', h)
        self.assertIn('ts-fchip-val">Age 65+<', h)

    # ── 2026-05-28 Wave 15 — human-readable chip values ──────────
    # Raw URL slugs (age65 / name / 25 / for-profit) read like
    # debug API params. Map them to friendly labels for the chip.

    def test_sort_chip_humanises_with_direction_arrow(self):
        h_asc = self._render(sort="name", direction="asc")
        self.assertIn('ts-fchip-val">Provider name ↑<', h_asc)
        h_desc = self._render(sort="size", vertical="snf",
                              direction="desc")
        self.assertIn('ts-fchip-val">Size ↓<', h_desc)

    # ── 2026-05-28 Wave 16 — Copy-share-link button ──────────────
    # Partners share screen state via URL (filters / sort / layer /
    # limit are all server-rendered into the query). Pre-wave-16
    # there was no easy way to grab the current URL — the partner
    # had to copy from the browser bar. Wave-16 adds the existing
    # ck_copy_share_link_button on the Active-screen sub-block
    # eyebrow row.

    # ── 2026-05-28 Wave 17 — map state-filter banner ─────────────
    # The map panel used to render 'Filtered to <strong>TX</strong> ·
    # clear state filter.</span></p>' — buried link text + a stray
    # </span> typo. Wave-17 promotes it to a real banner with state
    # full name, in-state provider count, and a chip-styled clear
    # link.

    def test_map_filter_banner_renders_when_state_selected(self):
        h = self._render(state="TX")
        self.assertIn('<div class="ts-map-filter-banner">', h)
        # Full state name resolved from us_map.STATE_NAMES.
        self.assertIn("TX · Texas", h)

    def test_map_filter_banner_hidden_without_state(self):
        h = self._render()
        self.assertNotIn('<div class="ts-map-filter-banner">', h)

    def test_map_filter_banner_state_full_name_for_california(self):
        h = self._render(state="CA")
        self.assertIn("CA · California", h)

    def test_map_filter_banner_includes_in_state_provider_count(self):
        import re
        h = self._render(state="TX")
        m = re.search(
            r'<div class="ts-map-filter-banner">(.*?)</div>',
            h, re.DOTALL)
        self.assertIsNotNone(m)
        banner = m.group(1)
        # The banner's strong number is the per-state count
        # (Texas hospitals — not the universe total).
        in_state = re.search(r"<strong>([\d,]+)</strong>", banner)
        self.assertIsNotNone(in_state, "in-state count missing")
        n = int(in_state.group(1).replace(",", ""))
        self.assertGreater(n, 0)
        self.assertLess(n, 5000,
                        "expected TX-only count not universe total")

    def test_no_stray_span_typo_in_map_filter_banner(self):
        # Pre-wave-17 the legacy banner had '.</span></p>' closing
        # a <span> that was never opened. Pin that the typo is gone
        # even when the banner is active.
        h = self._render(state="TX")
        self.assertNotIn(".</span></p>", h)

    def test_share_link_button_present_in_universe_panel(self):
        h = self._render()
        self.assertIn(
            '<button type="button" class="ck-share-btn" '
            'data-rcm-share-link>Copy share link</button>',
            h)
        # Idempotent install guard from ck_copy_share_link_button
        # ensures the script doesn't double-bind across pages or
        # when the universe panel re-renders.
        self.assertIn("__rcmCopyShareLinkInstalled", h)

    def test_share_link_button_lives_in_active_screen_head_row(self):
        # The button shares its row with the 'Active screen' eyebrow
        # label via the .ts-univ-block-head wrapper.
        h = self._render()
        self.assertIn('<div class="ts-univ-block-head">', h)

    def test_limit_chip_uses_top_n_language(self):
        # 'top 25' reads better than just '25' on a chip labelled
        # 'Row cap'.
        h = self._render(limit="25")
        self.assertIn('ts-fchip-val">top 25<', h)

    def test_default_layer_does_NOT_render_chip(self):
        # provider_count is the default, so no chip even if it's
        # explicitly set in the URL.
        h = self._render(layer="provider_count")
        # State and refines aren't set either → strip hidden entirely.
        self.assertNotIn('<div class="ts-fchips"', h)

    def test_non_default_limit_renders_chip(self):
        # Wave-15: chip value reads as 'top 25' rather than the
        # bare '25' so the partner doesn't have to interpret what
        # 'Row cap: 25' means out of context.
        h = self._render(limit="25")
        self.assertIn('ts-fchip-lbl">Row cap<', h)
        self.assertIn('ts-fchip-val">top 25<', h)

    def test_default_limit_does_NOT_render_chip(self):
        h = self._render(limit="150")
        self.assertNotIn('<div class="ts-fchips"', h)

    def test_no_match_placeholder_row_renders_hidden(self):
        h = self._render()
        # Server renders the row but hidden so it never flashes
        # during the unfiltered state.
        self.assertIn(
            '<tr data-ts-empty style="display:none;">', h)

    def test_no_match_placeholder_message_has_kbd_hint(self):
        h = self._render()
        # The Esc hint advertises the shortcut wave-9 wired.
        self.assertIn("Press <kbd>Esc</kbd> to clear", h)

    def test_no_match_js_toggles_placeholder(self):
        # The apply() function in _TS_SEARCH_JS reads the empty
        # marker and toggles display based on shown.
        h = self._render()
        self.assertIn("tr[data-ts-empty]", h)
        # And stamps the query into the rendered message.
        self.assertIn("data-ts-empty-msg", h)

    def test_default_sort_says_ranked_by_no_reset_link(self):
        h = self._render()
        self.assertIn("ranked by", h)
        self.assertNotIn("reset sort", h)

    def test_sort_by_name_asc_shows_summary_and_arrow(self):
        import re
        h = self._render(sort="name", direction="asc")
        self.assertIn(
            "sorted by <strong>Provider name</strong> (ascending)", h)
        self.assertIn("reset sort", h)
        # Exactly one ↑ arrow span on the active column.
        spans = re.findall(
            r'<span class="ts-sort-arrow">([^<]+)</span>', h)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].strip(), "↑")

    def test_sort_does_not_lie_when_column_hidden(self):
        # HCRIS hospitals have all-None operating_margin so the q
        # column is dropped. Sorting by quality silently falls back
        # to the default 'ranked by' language rather than claiming
        # the table is 'sorted by Op margin' when there's no Op
        # margin column to point at.
        h = self._render(sort="quality")
        self.assertIn("ranked by", h)
        self.assertNotIn("sorted by <strong>Op margin", h)

    def test_reset_sort_link_drops_sort_keeps_other_params(self):
        import re
        h = self._render(sort="name", state="TX")
        m = re.search(
            r'class="ck-link ts-sort-reset" href="([^"]+)"', h)
        self.assertIsNotNone(m, "reset-sort link missing")
        reset_href = m.group(1)
        self.assertNotIn("sort=", reset_href)
        self.assertIn("state=TX", reset_href)

    def test_compare_basket_banner_hidden_when_empty(self):
        h = self._render()
        self.assertNotIn('<div class="ts-cmp-bucket"', h)

    def test_compare_basket_banner_one_provider_singular(self):
        h = self._render(compare="010001")
        self.assertIn('<div class="ts-cmp-bucket"', h)
        self.assertIn("1 provider queued", h)
        self.assertIn("View comparison", h)

    def test_compare_basket_banner_multiple_providers_plural(self):
        h = self._render(compare="010001,020001,030001")
        self.assertIn("3 providers queued", h)

    def test_compare_basket_view_link_carries_ccns_and_view(self):
        import re
        h = self._render(compare="010001,020001")
        m = re.search(
            r'class="ts-cmp-bucket-go" href="([^"]+)"', h)
        self.assertIsNotNone(m, "View comparison link missing")
        href = m.group(1)
        self.assertIn("view=compare", href)
        # Either URL-encoded or raw comma is fine.
        self.assertTrue(
            "compare=010001%2C020001" in href
            or "compare=010001,020001" in href,
            f"CCN bucket lost from view link: {href}",
        )

    def test_compare_basket_clear_link_drops_bucket(self):
        import re
        h = self._render(compare="010001,020001")
        m = re.search(
            r'class="ts-cmp-bucket-clear" href="([^"]+)"', h)
        self.assertIsNotNone(m, "Clear basket link missing")
        clear_href = m.group(1)
        # Clear basket drops compare= and stays on main view.
        self.assertNotIn("compare=", clear_href)
        self.assertIn("view=main", clear_href)

    def test_state_filtered_kpis_describe_state_scope(self):
        h = self._render(state="TX")
        # Sub-label says 'in TX' not 'in this universe'.
        self.assertIn("in TX", h)
        # The States & territories tile is dropped — '1' is no signal.
        # (The whole-universe sub-label is also gone.)
        self.assertNotIn("in this universe", h)
        # Sub-labels on the median/coverage tiles mark them as
        # state-scoped so the partner can't confuse them with
        # universe-wide medians.
        self.assertIn("TX-only", h)

    def test_slash_hotkey_handler_in_installed_js(self):
        h = self._render()
        # The keydown listener for '/' is present in the inlined JS.
        self.assertIn("e.key !== '/'", h)
        # And it focuses the same input the row filter uses.
        self.assertIn(
            "document.querySelector('[data-ts-search-input]')", h)

    def test_escape_hotkey_handler_in_installed_js(self):
        h = self._render()
        # ESC inside the search input clears and blurs.
        self.assertIn("e.key !== 'Escape'", h)

    def test_search_placeholder_advertises_hotkey(self):
        # Surface the hotkey in the placeholder + aria-label so
        # discoverability doesn't depend on the partner reading docs.
        h = self._render()
        self.assertIn("(press /)", h)
        self.assertIn(
            "Keyboard shortcut: press slash to focus, escape to clear",
            h)

    def test_refine_filters_open_when_active(self):
        # min_quality active → details open
        h_q = self._render(min_quality="3")
        self.assertIn('<details class="ts-refine" open>', h_q)
        # min_size active → details open
        h_s = self._render(min_size="50")
        self.assertIn('<details class="ts-refine" open>', h_s)
        # ownership active → details open
        h_o = self._render(ownership="for-profit")
        self.assertIn('<details class="ts-refine" open>', h_o)

    def test_workbench_tab_bar_is_sticky(self):
        h = self._render()
        # Pin the exact sticky offset so future stacking changes
        # (top:58px must match the shell's topbar height) don't
        # silently drift.
        self.assertIn("position:sticky;top:58px;z-index:30", h)

    def test_table_toolbar_has_search_input(self):
        h = self._render()
        self.assertIn("data-ts-search-input", h)
        self.assertIn("data-ts-search-count", h)
        # Idempotent install guard so re-rendering doesn't double-bind.
        self.assertIn("__rcmTsSearchInstalled", h)

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
        # Wave-17 polished the banner: 'Filtered to' → 'FILTERED TO',
        # 'clear state filter' → 'Clear state filter' inside a real
        # banner element instead of inline link text. Pin both the
        # selection and the banner element.
        h = self._render(view="main", vertical="hospice", state="TX")
        self.assertIn("usgeo-selected", h)       # TX highlighted
        self.assertIn('<div class="ts-map-filter-banner">', h)
        self.assertIn("FILTERED TO", h)
        self.assertIn("Clear state filter", h)

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
