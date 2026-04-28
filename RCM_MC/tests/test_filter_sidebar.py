"""Test for the ck_filter_sidebar editorial helper.

Built per docs/CHARTIS_MATCH_NOTES.md pattern 02 — eyebrow rail with
grouped checkbox/radio rows and a <details> 'More' expander when a
group exceeds the threshold. Pairs with ck_search_hero (pattern 01)
on /library, /research, /notes so the partner sees the same Insights
triplet (search + filter + results) as chartis.com.

Asserts:
  - .ck-filter-rail wrapper class (CSS hook)
  - group title + group head render escape-safe
  - radio vs checkbox input_type honored
  - checked option renders ``checked`` attribute
  - More expander appears only when options > more_threshold
  - extra_hidden round-trips sibling form state through hidden inputs
  - form_action wraps in <form>; absent form_action emits bare <aside>
  - auto-submit onchange attribute appears only when intended
  - submit_label suppresses auto-submit and renders an explicit button
  - escape-safety on user-controlled label / value strings
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_filter_sidebar


def _group(title="By topic", name="topic", input_type="checkbox", options=None):
    return {
        "title": title,
        "name": name,
        "input_type": input_type,
        "options": options or [
            {"label": "AI", "value": "ai", "checked": False},
            {"label": "Digital", "value": "digital", "checked": True},
        ],
    }


class CkFilterSidebarTests(unittest.TestCase):
    def test_minimal_render_emits_rail_wrapper(self) -> None:
        html = ck_filter_sidebar(groups=[_group()])
        self.assertIn('class="ck-filter-rail"', html)
        self.assertIn('class="ck-filter-rail-title"', html)
        self.assertIn(">Filter</h2>", html)

    def test_group_head_and_options_render(self) -> None:
        html = ck_filter_sidebar(groups=[_group()])
        self.assertIn('class="ck-filter-group"', html)
        self.assertIn('class="ck-filter-group-head"', html)
        self.assertIn(">By topic</header>", html)
        self.assertIn('name="topic"', html)
        self.assertIn('value="ai"', html)
        self.assertIn(">AI</span>", html)
        self.assertIn(">Digital</span>", html)

    def test_checked_option_emits_checked_attribute(self) -> None:
        html = ck_filter_sidebar(groups=[_group()])
        # "Digital" was checked=True
        self.assertIn('value="digital" checked', html)
        # "AI" was checked=False — no checked attribute
        self.assertNotIn('value="ai" checked', html)

    def test_input_type_radio_honored(self) -> None:
        html = ck_filter_sidebar(groups=[_group(input_type="radio")])
        self.assertIn('type="radio"', html)
        self.assertNotIn('type="checkbox"', html)

    def test_input_type_checkbox_default(self) -> None:
        # Omit input_type — should default to checkbox
        html = ck_filter_sidebar(
            groups=[{"title": "By topic", "name": "topic",
                     "options": [{"label": "x", "value": "x", "checked": False}]}]
        )
        self.assertIn('type="checkbox"', html)

    def test_unknown_input_type_falls_back_to_checkbox(self) -> None:
        html = ck_filter_sidebar(groups=[_group(input_type="bogus")])
        self.assertIn('type="checkbox"', html)
        self.assertNotIn('type="bogus"', html)

    def test_more_expander_appears_when_options_exceed_threshold(self) -> None:
        opts = [
            {"label": f"opt{i}", "value": f"v{i}", "checked": False}
            for i in range(12)
        ]
        html = ck_filter_sidebar(
            groups=[_group(options=opts)], more_threshold=8,
        )
        self.assertIn('class="ck-filter-overflow"', html)
        self.assertIn("<summary>More</summary>", html)
        # First 8 are in the head list; remaining 4 are in the overflow.
        head_idx = html.index('class="ck-filter-group-head"')
        more_idx = html.index('class="ck-filter-overflow"')
        self.assertLess(head_idx, more_idx)

    def test_more_expander_omitted_when_below_threshold(self) -> None:
        opts = [
            {"label": f"opt{i}", "value": f"v{i}", "checked": False}
            for i in range(5)
        ]
        html = ck_filter_sidebar(
            groups=[_group(options=opts)], more_threshold=8,
        )
        self.assertNotIn("ck-filter-overflow", html)
        self.assertNotIn("<summary>", html)

    def test_form_action_wraps_in_form(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library",
        )
        self.assertIn('<form method="GET" action="/library">', html)
        self.assertIn("</form>", html)

    def test_no_form_action_emits_bare_aside(self) -> None:
        html = ck_filter_sidebar(groups=[_group()])
        self.assertNotIn("<form", html)
        self.assertIn("<aside", html)

    def test_auto_submit_attached_when_form_action_provided(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library",
        )
        self.assertIn('onchange="this.form.submit()"', html)

    def test_auto_submit_disabled_by_submit_label(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library",
            submit_label="Apply",
        )
        self.assertNotIn("onchange", html)
        self.assertIn(">Apply</button>", html)
        self.assertIn('class="ck-filter-submit"', html)

    def test_auto_submit_disabled_by_explicit_flag(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library", auto_submit=False,
        )
        self.assertNotIn("onchange", html)

    def test_extra_hidden_round_trips_sibling_state(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library",
            extra_hidden={"q": "Apollo Health", "sort_by": "moic"},
        )
        self.assertIn(
            '<input type="hidden" name="q" value="Apollo Health">', html,
        )
        self.assertIn(
            '<input type="hidden" name="sort_by" value="moic">', html,
        )

    def test_extra_hidden_skips_empty_values(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], form_action="/library",
            extra_hidden={"q": "", "sort_by": "moic"},
        )
        self.assertNotIn('name="q"', html.split('<ul')[0])  # not in hidden block
        self.assertIn('name="sort_by" value="moic"', html)

    def test_extra_hidden_ignored_without_form_action(self) -> None:
        # Hidden inputs only make sense inside a form
        html = ck_filter_sidebar(
            groups=[_group()],
            extra_hidden={"q": "Apollo"},
        )
        self.assertNotIn('type="hidden"', html)

    def test_label_value_html_escape(self) -> None:
        opts = [{
            "label": "<script>x</script>",
            "value": '"onerror="alert(1)',
            "checked": False,
        }]
        html = ck_filter_sidebar(
            groups=[_group(options=opts)], form_action="/library",
        )
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", html)
        self.assertNotIn('"onerror="alert(1)', html)
        self.assertIn("&quot;onerror=&quot;alert(1)", html)

    def test_custom_title_renders(self) -> None:
        html = ck_filter_sidebar(
            groups=[_group()], title="Refine results",
        )
        self.assertIn(">Refine results</h2>", html)


if __name__ == "__main__":
    unittest.main()
