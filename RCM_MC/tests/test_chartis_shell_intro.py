"""Test the chartis_shell ``editorial_intro`` kwarg added in cycle 20.

The kwarg auto-prepends a ``ck_section_intro`` block to the body so
existing chartis_shell-using renderers can adopt the chartis cadence
(italic-serif headline + eyebrow + body) with a single 3-line
addition. Cycle 20 lifted 11 pages over the 70 fidelity threshold
this way.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class ChartisShellEditorialIntroTests(unittest.TestCase):
    def test_no_intro_kwarg_renders_body_verbatim(self):
        # Backward-compat: omitting editorial_intro changes nothing.
        html = chartis_shell("<p>hello</p>", title="X")
        self.assertIn("<p>hello</p>", html)
        # No section-intro emitted
        self.assertNotIn('class="ck-section-intro"', html)

    def test_intro_kwarg_prepends_section_intro(self):
        html = chartis_shell(
            "<p>body</p>", title="X",
            editorial_intro={
                "eyebrow": "TEST",
                "headline": "The platform finds its voice.",
                "italic_word": "finds",
            },
        )
        # Section intro present
        self.assertIn('class="ck-section-intro"', html)
        # Eyebrow + italic word both rendered
        self.assertIn(">TEST</div>", html)
        self.assertIn("<em>finds</em>", html)
        # Body still appears AFTER the intro
        intro_idx = html.index('class="ck-section-intro"')
        body_idx = html.index("<p>body</p>")
        self.assertLess(intro_idx, body_idx)

    def test_intro_kwarg_with_body_text(self):
        html = chartis_shell(
            "<p>x</p>", title="X",
            editorial_intro={
                "eyebrow": "EYEBROW",
                "headline": "Headline.",
                "italic_word": "Headline",
                "body": "Supporting paragraph copy.",
            },
        )
        self.assertIn(">Supporting paragraph copy.</p>", html)

    def test_intro_kwarg_does_not_affect_other_kwargs(self):
        html = chartis_shell(
            "<p>x</p>", title="X",
            subtitle="Sub",
            breadcrumbs=[("Home", "/")],
            editorial_intro={
                "eyebrow": "TEST",
                "headline": "Where the voice resides.",
                "italic_word": "resides",
            },
        )
        # Subtitle still renders
        self.assertIn(">Sub</div>", html)
        # Breadcrumbs still render
        self.assertIn('class="ck-breadcrumbs"', html)
        # Intro still renders
        self.assertIn("<em>resides</em>", html)

    def test_empty_dict_intro_treated_as_none(self):
        # An empty dict is falsy in the kwarg test → no intro emitted.
        html = chartis_shell(
            "<p>body</p>", title="X",
            editorial_intro={},
        )
        self.assertNotIn('class="ck-section-intro"', html)


class ChartisShellLegacySectionIntroAutoTitleTests(unittest.TestCase):
    """Pages that call ``ck_section_intro`` *directly* in their body
    (rather than via the ``editorial_intro=`` kwarg) used to render
    without any page H1 — the partner saw a bare italic deck headline
    floating at the top with no title above it (bear_case,
    covenant_lab, payer_stress, bridge_audit, regulatory_calendar,
    ic_memo, day_one, portfolio_monitor, regression).

    The shell now auto-injects a ck_page_title using the shell's
    ``title`` arg whenever the body signals editorial cadence
    (presence of ``ck-section-intro``) but has no ``ck-page-title``
    yet.
    """

    def test_body_with_section_intro_gets_page_title(self):
        body = (
            '<div class="ck-section-intro" data-ck-intro="x">'
            '<h2>The deck headline.</h2></div>'
            '<p>body</p>'
        )
        html = chartis_shell(body, title="Bear Case")
        # ck_page_title now present
        self.assertIn('class="ck-page-title"', html)
        # And it appears BEFORE the section intro
        title_idx = html.index('class="ck-page-title"')
        intro_idx = html.index('class="ck-section-intro"')
        self.assertLess(title_idx, intro_idx)
        # The title text rendered
        self.assertIn(">Bear Case</h1>", html)

    def test_body_without_section_intro_now_gets_backstop_title(self):
        # 2026-05-29 audit follow-up — the old contract was "plain
        # body, no editorial signal → leave alone." The audit found
        # that six chartis-direct routes (/runs, /query, /settings,
        # /engagements, /fund-learning, /admin/audit-chain) shipped
        # with NO <h1> at all under that contract, violating
        # CLAUDE.md's One-H1 invariant. The new contract uses the
        # shell's `title` arg as a backstop: when the body still has
        # no `<h1`, prepend a ck_page_title from it. Pages that
        # genuinely want no h1 (login, error pages, callers passing
        # their own header) pass `omit_h1=True` — covered in
        # test_b165 — or carry their own `<h1` in the body.
        html = chartis_shell("<p>just body</p>", title="Plain")
        self.assertIn('class="ck-page-title"', html,
                      "backstop must inject a ck_page_title from title "
                      "when body has no <h1>")
        # And opting out works:
        html_opt = chartis_shell(
            "<p>just body</p>", title="Plain", omit_h1=True)
        self.assertNotIn('class="ck-page-title"', html_opt)

    def test_body_with_existing_page_title_not_doubled(self):
        body = (
            '<header class="ck-page-title"><h1>Already Titled</h1>'
            '</header>'
            '<div class="ck-section-intro" data-ck-intro="x">'
            '<h2>Deck.</h2></div>'
        )
        html = chartis_shell(body, title="Should Not Appear")
        # Only one ck-page-title in the rendered HTML
        self.assertEqual(html.count('class="ck-page-title"'), 1)
        # The auto-injected title is NOT prepended on top
        self.assertNotIn("Should Not Appear</h1>", html)

    def test_default_pe_desk_title_does_not_inject(self):
        # Pages that don't pass a real title get no H1 either —
        # avoids surfacing "PE Desk" as a meaningless H1 string.
        body = (
            '<div class="ck-section-intro" data-ck-intro="x">'
            '<h2>Deck.</h2></div>'
        )
        html = chartis_shell(body)  # no title= → defaults to "PE Desk"
        self.assertNotIn('class="ck-page-title"', html)

    def test_editorial_intro_kwarg_path_still_wins(self):
        # When editorial_intro= is set, that path handles title
        # injection (with eyebrow). The fallback path must NOT
        # fire again and double the title.
        html = chartis_shell(
            "<p>body</p>", title="X",
            editorial_intro={
                "eyebrow": "EYE",
                "headline": "Headline.",
            },
        )
        self.assertEqual(html.count('class="ck-page-title"'), 1)


if __name__ == "__main__":
    unittest.main()
