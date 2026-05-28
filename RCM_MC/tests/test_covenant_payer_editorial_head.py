"""Editorial-head + Copy-share-link contract for /diligence/covenant-
stress and /diligence/payer-stress (sweep batch 16).

Both pages have four render paths sharing a masthead. Sweep batch 16
introduces two local helpers (_cv_head, _ps_head) that compose the
strict Tier-1 5-block head once per file, plus a Copy-share-link
button that deep-links the current URL to the partner's clipboard
via navigator.clipboard.

Pins:
  · Each page exposes a working helper (_cv_head, _ps_head).
  · The helper emits a single h1 + eyebrow + dash + meta + italic-
    first-phrase lede + status-dot legend.
  · The Copy-share-link button uses the `data-rcm-share-link`
    attribute (the inline JS binds to this selector).
  · The inline JS guards against duplicate install via
    `window.__rcmCopyShareLinkInstalled`.
  · The landing-path on each page renders one h1 + the head shape.
"""
from __future__ import annotations

import re
import unittest


class CovenantHeadCascadeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.covenant_lab_page import _landing
        cls.html = _landing()

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="cv-head"', self.html)

    def test_eyebrow_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>',
        )

    def test_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>When the covenant cliff hits — by quarter.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_clipboard_install_script_present(self) -> None:
        # The inline JS is shipped with the CSS block; verify it
        # guards against duplicate install.
        self.assertIn("__rcmCopyShareLinkInstalled", self.html)
        self.assertIn("data-rcm-share-link", self.html)


class PayerStressHeadCascadeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.payer_stress_page import _landing
        cls.html = _landing()

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="ps-head"', self.html)

    def test_eyebrow_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>',
        )

    def test_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>Empirical rate-movement priors against your "
            "payer portfolio.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )


class CopyShareLinkButtonContractTests(unittest.TestCase):
    """The _cv_head / _ps_head helpers accept actions_html and emit
    a Copy-share-link button when callers pass one."""

    def test_cv_head_emits_share_button(self) -> None:
        from rcm_mc.ui.covenant_lab_page import _cv_head
        html = _cv_head(
            eyebrow="E",
            title="T",
            meta="M",
            lede_italic_phrase="L.",
            lede_body="b",
            actions_html=(
                '<button type="button" data-rcm-share-link>'
                'Copy share link</button>'
            ),
        )
        # Button present with the auto-bind attribute.
        self.assertIn("data-rcm-share-link", html)
        self.assertIn(">Copy share link</button>", html)
        # Actions wrapper present.
        self.assertIn('class="head-actions"', html)

    def test_ps_head_emits_share_button(self) -> None:
        from rcm_mc.ui.payer_stress_page import _ps_head
        html = _ps_head(
            eyebrow="E",
            title="T",
            meta="M",
            lede_italic_phrase="L.",
            lede_body="b",
            actions_html=(
                '<button type="button" data-rcm-share-link>'
                'Copy share link</button>'
            ),
        )
        self.assertIn("data-rcm-share-link", html)
        self.assertIn(">Copy share link</button>", html)
        self.assertIn('class="head-actions"', html)

    def test_helpers_emit_5_block_anatomy(self) -> None:
        from rcm_mc.ui.covenant_lab_page import _cv_head
        from rcm_mc.ui.payer_stress_page import _ps_head
        for helper, head_cls in [
            (_cv_head, "cv-head"), (_ps_head, "ps-head"),
        ]:
            with self.subTest(helper=helper.__name__):
                html = helper(
                    eyebrow="EYE",
                    title="TITLE",
                    meta="META",
                    lede_italic_phrase="Italic.",
                    lede_body="Body.",
                )
                self.assertIn(f'class="{head_cls}"', html)
                self.assertIn('class="eyebrow"', html)
                self.assertIn('class="dash"', html)
                self.assertIn("<h1>TITLE</h1>", html)
                self.assertIn('class="meta"', html)
                self.assertIn(">META<", html)
                self.assertIn("<em>Italic.</em> Body.", html)
                self.assertIn('class="legend"', html)
                # Single h1.
                self.assertEqual(
                    len(re.findall(r"<h1[ >]", html)), 1,
                )


if __name__ == "__main__":
    unittest.main()
