"""Editorial-head cascade for render_grouped_catalog (sweep batch 4).

The shared renderer powers MANY section landings — `/diligence` plus
every `/best/<section>` route via `render_section_landing`. Pre-sweep,
each page stacked three editorial blocks at the top (`ck_page_title`
→ `ck_page_explainer` → `ck_section_intro`), producing two `<h2>`
decks above the page `<h1>` — visual stacking confusion.

This sweep replaces that triple with the strict Tier-1 5-block head
in the SHARED helper, so one edit cascades to every consuming page.

Pins:
  · ONE <h1> per page (the #1036 a11y invariant) — was previously
    coupled to TWO h2 decks above it.
  · Eyebrow + 24×1px green-dash glyph.
  · Mono meta-line in --green-deep / --muted with surface count +
    pillar count + per-tier coverage.
  · Italic-first-phrase serif lede.
  · Explainer body as a second roman serif paragraph.
  · Mono source-note line below.
  · 4-bucket status-dot legend.
"""
from __future__ import annotations

import re
import unittest


def _three_pillar_fixture():
    return [
        {
            "title": "Profile",
            "eyebrow": "PROFILE",
            "body": "Pillar body line.",
            "links": [
                {"href": "/source", "label": "Source",
                 "blurb": "Source surface."},
                {"href": "/portfolio", "label": "Portfolio",
                 "blurb": "Portfolio surface."},
            ],
        },
        {
            "title": "Thesis",
            "eyebrow": "THESIS",
            "body": "Pillar body line.",
            "links": [
                {"href": "/diligence/playbook", "label": "Playbook",
                 "blurb": "Playbook surface."},
            ],
        },
    ]


class CatalogHeadStrictAnatomyTests(unittest.TestCase):
    """The shared helper produces the spec's 5-block head."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.section_catalog_page import render_grouped_catalog
        cls.html = render_grouped_catalog(
            section="diligence",
            title="Diligence",
            eyebrow="RCM PLAYBOOK",
            pillars=_three_pillar_fixture(),
            explainer_head="Where diligence happens.",
            explainer_body=(
                "Catalog of every diligence surface, grouped into pillars."
            ),
            explainer_source="Curated catalog of /diligence/* routes.",
            intro_headline="Where the diligence work actually lives.",
            intro_italic="lives",
            intro_body=(
                "Twenty-four surfaces in four pillars. Each tile names "
                "the surface and the one-line job."
            ),
        )

    def test_one_h1_per_page(self) -> None:
        # #1036 a11y invariant. Was 1 h1 + 2 h2 decks before sweep;
        # now the head emits exactly one h1 and the section_intro is
        # gone.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block_present(self) -> None:
        self.assertIn('class="sc-head"', self.html)

    def test_eyebrow_has_green_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*RCM PLAYBOOK',
        )

    def test_h1_is_section_title(self) -> None:
        self.assertIn("<h1>Diligence</h1>", self.html)

    def test_meta_line_quotes_real_counts(self) -> None:
        # 3 surfaces, 2 pillars. Renders uppercased.
        self.assertRegex(
            self.html,
            r'class="meta">\s*3 SURFACES\s*·\s*2 PILLARS',
        )

    def test_lede_italic_first_phrase(self) -> None:
        # intro_italic="lives" → "<em>lives</em>" in the headline.
        self.assertIn("<em>lives</em>", self.html)

    def test_explainer_body_renders_under_lede(self) -> None:
        # The explainer_body lands as a second roman lede paragraph
        # (not as a separate ck_page_explainer block).
        self.assertIn(
            "Catalog of every diligence surface, grouped into pillars.",
            self.html,
        )

    def test_source_note_renders(self) -> None:
        self.assertIn(
            "Curated catalog of /diligence/* routes.",
            self.html,
        )
        self.assertIn('class="source-note"', self.html)

    def test_status_dot_legend_present(self) -> None:
        # The 4-bucket legend (live / computed / needs / illustrative)
        # is rendered inside the head, not below it.
        self.assertIn("sc-legend", self.html)
        for label in ("Live data", "Computed", "Needs data", "Illustrative"):
            self.assertIn(label, self.html)


class CatalogCascadeTests(unittest.TestCase):
    """The shared head is wired to /diligence + /best/<section>."""

    def test_diligence_index_uses_strict_head(self) -> None:
        from rcm_mc.ui.diligence_index_page import render_diligence_index
        html = render_diligence_index()
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertIn('class="sc-head"', html)
        self.assertIn('class="eyebrow"><span class="dash">', html)

    def test_best_source_uses_strict_head(self) -> None:
        from rcm_mc.ui.section_landings import render_section_landing
        html = render_section_landing("source") or ""
        self.assertNotEqual(html, "")
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertIn('class="sc-head"', html)

    def test_best_research_uses_strict_head(self) -> None:
        from rcm_mc.ui.section_landings import render_section_landing
        html = render_section_landing("research") or ""
        self.assertNotEqual(html, "")
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertIn('class="sc-head"', html)

    def test_best_pipeline_uses_strict_head(self) -> None:
        from rcm_mc.ui.section_landings import render_section_landing
        html = render_section_landing("pipeline") or ""
        self.assertNotEqual(html, "")
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertIn('class="sc-head"', html)

    def test_best_library_uses_strict_head(self) -> None:
        from rcm_mc.ui.section_landings import render_section_landing
        html = render_section_landing("library") or ""
        self.assertNotEqual(html, "")
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertIn('class="sc-head"', html)


if __name__ == "__main__":
    unittest.main()
