"""Tests for ``ck_action_button`` — the editorial primary-action
button primitive.

Why this primitive exists: four pages (compare, counterfactual,
denial_prediction, deal_autopsy) had previously emitted bespoke
inline-styled buttons whose background resolved to ``P["accent"]``
(``#155752``) — a *third* color distinct from the marketing CTA
near-black-navy and the workbench cad-btn-primary teal (``#1F7A75``).
Each used a different pattern (inline ``style=``, page-scoped
``.cf-form button``, etc.), so a uniform fix required a primitive.

The primitive consumes the existing ``.cad-btn .cad-btn-primary``
class pair from ``/static/v3/chartis.css`` (the workbench convention)
rather than introducing new CSS — keeping the visual change to
"these four pages now match the rest of the workbench."

Cross-surface unification (marketing ``.cta-btn`` near-navy vs.
workbench ``.cad-btn-primary`` teal) is a separate Tier B ticket.
This file does not test that question.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_action_button


class TestActionButtonRendering(unittest.TestCase):
    def test_default_primary_emits_cad_btn_primary_pair(self):
        # The whole point of this PR — the primitive emits the
        # workbench teal classes, not inline ``background:#155752``.
        html = ck_action_button("Compare")
        self.assertIn('class="cad-btn cad-btn-primary"', html)
        self.assertIn('type="submit"', html)
        self.assertIn(">Compare</button>", html)
        # And does NOT carry the old bespoke patterns:
        self.assertNotIn("background:", html)
        self.assertNotIn("#155752", html)
        self.assertNotIn('style=', html)

    def test_type_button_renders_button(self):
        html = ck_action_button("Cancel", type="button")
        self.assertIn('type="button"', html)
        self.assertNotIn('type="submit"', html)

    def test_unknown_type_falls_back_to_submit(self):
        # Typo-safety: an unrecognised type silently degrades to
        # "submit" so a form doesn't lose its submit affordance
        # because of a one-letter mistake.
        html = ck_action_button("Go", type="not-a-real-type")
        self.assertIn('type="submit"', html)

    def test_form_target_emits_form_attribute_when_provided(self):
        # HTML5 form-association: lets a button outside its <form>
        # reference the form by id. Only emitted when caller asks
        # for it — keeps the common-case markup clean.
        html = ck_action_button("Submit", form_target="deal-search-form")
        self.assertIn('form="deal-search-form"', html)

    def test_form_target_omitted_when_none(self):
        html = ck_action_button("Submit")
        self.assertNotIn('form=', html)

    def test_form_target_is_escaped(self):
        # Defensive — form_target is unlikely to be user-supplied but
        # escape anyway so a future caller can't poison the attribute.
        # Security guarantee under test: the unescaped quote that
        # would break out of the form= attribute is encoded as
        # &quot;. Substrings like "onclick=" remaining INSIDE the
        # quoted attribute value are harmless — browsers don't
        # reparse attribute values as markup.
        html = ck_action_button("X", form_target='evil" onclick="bad()')
        self.assertIn('&quot;', html)
        # The literal unescaped quote (which would break out) must
        # not appear in the form= attribute value
        self.assertNotIn('form="evil"', html)

    def test_text_is_escaped(self):
        html = ck_action_button("<script>x</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_variant_falls_back_to_primary(self):
        # Future-proofing: when "secondary" / "destructive" land,
        # they're a dict addition in _chartis_kit. Until then, a
        # caller passing one of those values gets the primary style
        # rather than an unstyled button — visual mistake is loud.
        html = ck_action_button("Save", variant="secondary")
        self.assertIn('class="cad-btn cad-btn-primary"', html)


class TestFourPagesNowUseThePrimitive(unittest.TestCase):
    """Integration check: render each of the four previously-broken
    pages and assert the new primitive's markup appears (and the old
    bespoke patterns are gone).

    These pages each have a different historical pattern; this test
    locks the migration so a future regression that re-introduces an
    inline-styled button or a page-scoped ``.cf-form button`` block
    is caught at PR time, not at screenshot-review time.
    """

    def test_compare_page_uses_primitive(self):
        from rcm_mc.ui.compare_page import render_compare_page
        html = render_compare_page(left="", right="")
        # The Compare button now goes through the primitive
        self.assertIn(
            'class="cad-btn cad-btn-primary"', html,
            "compare page no longer emits the primitive's class pair",
        )
        # And the previous inline-style pattern is gone
        self.assertNotIn(
            'background:#155752', html,
            "compare page still contains the old P['accent'] inline style",
        )

    def test_counterfactual_page_uses_primitive(self):
        from rcm_mc.ui.counterfactual_page import render_counterfactual_page
        # The bare ``<button type="submit">Run advisor</button>`` lives
        # on the landing page (no dataset query) per the page's
        # _landing_page() helper.
        html = render_counterfactual_page(dataset="")
        self.assertIn('class="cad-btn cad-btn-primary"', html)
        # The deleted ``.cf-form button { background: #155752; ... }``
        # rule produced inline text containing the hex value. Verify
        # it's gone from the scoped CSS block (the hex shouldn't
        # appear anywhere on the rendered page — the only place it
        # used to come from was the deleted rule).
        self.assertNotIn('#155752', html)

    def test_denial_prediction_page_uses_primitive(self):
        from rcm_mc.ui.denial_prediction_page import (
            render_denial_prediction_page,
        )
        # Landing page (no dataset) renders the form with the button.
        html = render_denial_prediction_page(dataset="")
        self.assertIn('class="cad-btn cad-btn-primary"', html)
        self.assertNotIn('background:#155752', html)

    def test_deal_autopsy_page_uses_primitive(self):
        from rcm_mc.ui.deal_autopsy_page import render_deal_autopsy_page
        # No qs provided → landing page with the form + Run autopsy match button
        html = render_deal_autopsy_page(qs={})
        self.assertIn('class="cad-btn cad-btn-primary"', html)
        # The .da-form-submit scoped class is replaced by the
        # primitive; only the wrapper div carries the spacing class
        # now.
        self.assertNotIn('class="da-form-submit"', html)
        self.assertNotIn('background:#155752', html)


if __name__ == "__main__":
    unittest.main()
