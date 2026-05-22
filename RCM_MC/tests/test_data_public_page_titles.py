"""Every partner-visible data_public page must surface a page title.

This locks in the end-state of the "B11 broader sweep" — the migration
of every ``rcm_mc/ui/data_public/*_page.py`` away from the Bloomberg-era
bespoke ``<h1 class="ck-page-h1">`` header onto the editorial
``ck_page_title`` primitive.

A page can satisfy the title contract three ways:

1. Calls ``ck_page_title(...)`` directly in its body (the explicit form
   most swept pages now use).
2. Passes ``editorial_intro=`` to ``chartis_shell`` — the shell
   auto-injects a ``ck_page_title`` from the page ``title`` + the
   intro's eyebrow (see ``chartis_shell`` "Missing-title bugfix").
3. Emits a ``ck_section_intro`` block directly in its body — the shell's
   second-pass auto-injection prepends a ``ck_page_title`` from the
   shell ``title`` arg.

A page that does none of these renders with NO partner-visible title —
the exact regression the sweep eliminated. The unit-level behavior of
the auto-injection itself is covered by
``test_chartis_shell_intro.py``; this test guards the *page-level*
invariant so a newly added data_public page can't silently ship
title-less.
"""
from __future__ import annotations

import io
import pathlib
import re
import tokenize
import unittest


def _strip_comments(src: str) -> str:
    """Return ``src`` with Python comments removed but string literals
    (including CSS colors and emitted markup) intact, so a class name
    mentioned only in an explanatory comment isn't mistaken for emitted
    HTML."""
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                continue
            out.append(tok.string)
    except tokenize.TokenError:
        return src
    return "".join(out)

_DATA_PUBLIC = (
    pathlib.Path(__file__).resolve().parent.parent
    / "rcm_mc" / "ui" / "data_public"
)

# Any one of these source signals guarantees a rendered ck-page-title.
_EXPLICIT_TITLE = re.compile(r"\bck_page_title\s*\(")
_EDITORIAL_INTRO = re.compile(r"\beditorial_intro\s*=")
_SECTION_INTRO = re.compile(r"\bck_section_intro\s*\(")
_BESPOKE_H1 = re.compile(r"<h1\b")


class DataPublicPageTitleContractTests(unittest.TestCase):
    def test_every_page_carries_a_title_signal(self):
        pages = sorted(
            p for p in _DATA_PUBLIC.glob("*_page.py")
            if p.name != "__init__.py"
        )
        self.assertGreater(len(pages), 100, "data_public page glob looks empty")

        titleless = []
        for p in pages:
            src = p.read_text()
            if (
                _EXPLICIT_TITLE.search(src)
                or _EDITORIAL_INTRO.search(src)
                or _SECTION_INTRO.search(src)
                or _BESPOKE_H1.search(src)
            ):
                continue
            titleless.append(p.name)

        self.assertEqual(
            titleless, [],
            "These data_public pages render without any page-title signal "
            "(no ck_page_title, no editorial_intro, no ck_section_intro, no "
            f"<h1>): {titleless}. Add ck_page_title(...) or pass "
            "editorial_intro= to chartis_shell.",
        )

    def test_no_bespoke_ck_page_h1_class_remains(self):
        # The sweep's whole point: the legacy ``ck-page-h1`` class is
        # retired in favor of ``ck_page_title``. Guard against a
        # regression that reintroduces the bespoke header markup.
        offenders = []
        for p in sorted(_DATA_PUBLIC.glob("*_page.py")):
            if p.name == "__init__.py":
                continue
            if 'class="ck-page-h1"' in _strip_comments(p.read_text()):
                offenders.append(p.name)
        self.assertEqual(
            offenders, [],
            f"Bespoke .ck-page-h1 header reintroduced in: {offenders}. "
            "Use ck_page_title(title, eyebrow=, meta=) instead.",
        )


if __name__ == "__main__":
    unittest.main()
