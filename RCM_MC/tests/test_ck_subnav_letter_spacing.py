"""Lock-in test for the ck-subnav-link letter-spacing value.

Why this test exists: the sub-nav at the top of every workbench
page renders through a single global CSS rule (``.ck-subnav-link``
in ``_chartis_kit.py``'s inline CSS). At the original value
``letter-spacing: 0.04em`` — the tightest tracking in the system —
Title-Case 12px semibold text read as crammed against itself,
distinct from the looser tracking on every sibling nav surface
(``.ck-nav`` topnav at 0.06em, ``.topnav`` editorial at 0.14em,
``.ck-eyebrow`` etc.).

The fix bumped the value to 0.08em — surgical, single-character
change, mid-range of the system's tracking scale. This test pins
the new value so a future "tighten everything for density" pass
doesn't silently regress the sub-nav back into the crammed state
that prompted the partner-visible complaint.

The companion Tier B "design unification sweep" ticket is the
right place to revisit the entire nav visual register (topnav /
sub-nav / breadcrumbs / eyebrows) as a coordinated pass; until
that lands, this test guards the per-rule value.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class TestSubnavLetterSpacing(unittest.TestCase):
    def test_ck_subnav_link_renders_letter_spacing_0_08em(self):
        # Any chartis_shell render carries the inline CSS that
        # defines .ck-subnav-link. We don't need a sub-nav-having
        # active_nav to assert the rule's value — the rule is in
        # the always-injected fallback CSS block.
        html = chartis_shell(body="<main/>", title="Test")
        # Pull the .ck-subnav-link rule out of the rendered CSS and
        # assert the letter-spacing inside it. Matching the property
        # *inside* the rule (rather than anywhere in the document)
        # prevents accidentally passing because some other selector
        # happens to use 0.08em.
        match = re.search(
            r'\.ck-subnav-link\s*\{[^}]*letter-spacing\s*:\s*([0-9.]+em)',
            html,
        )
        self.assertIsNotNone(
            match,
            ".ck-subnav-link rule missing or has no letter-spacing declaration",
        )
        self.assertEqual(
            match.group(1), "0.08em",
            f"sub-nav letter-spacing regressed to {match.group(1)} — see "
            "tests/test_ck_subnav_letter_spacing.py docstring for context",
        )

    def test_old_0_04em_value_no_longer_present_in_ck_subnav_link_rule(self):
        # Defensive: make sure the pre-fix value is fully gone from
        # the ck-subnav-link rule specifically. Other rules in the
        # kit may legitimately use 0.04em — we only check inside
        # this rule.
        html = chartis_shell(body="<main/>", title="Test")
        match = re.search(r'\.ck-subnav-link\s*\{[^}]*\}', html)
        self.assertIsNotNone(match, ".ck-subnav-link rule missing entirely")
        self.assertNotIn(
            'letter-spacing:0.04em', match.group(0),
            "old crammed-tracking value 0.04em still present in "
            ".ck-subnav-link rule",
        )


if __name__ == "__main__":
    unittest.main()
