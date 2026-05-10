"""Source-level guard against US-style date format strings.

CLAUDE.md date-format spec:
  * Dates → ISO-like (``2026-04-15``, ``2026Q1`` for quarter).
    Never US-style ``4/15/2026``.
  * Times → UTC ISO (``2026-04-15T10:00:00+00:00``).

The runtime audit doesn't currently police date format (the
``number-format-clean`` rule only handles money / percent /
multiples). This guard fills the gap at the source level, blocking
US-style strftime/strptime patterns from being introduced anywhere
in the rcm_mc package.

Forbidden patterns (any case, anchored to ``strftime(`` calls):
  * ``strftime("%m/%d/%Y")`` / ``strftime("%-m/%-d/%Y")``
  * ``strftime('%m/%d/%Y')`` / ``strftime('%-m/%-d/%Y')``
  * ``strftime("%m/%d/%y")`` / lowercase year variants

Anchored to ``strftime(`` so parsing-format allowlists (e.g.
``_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", ...]`` consumed by
pandas ``to_datetime`` to accept partner-pasted dates) are not
flagged. Parsing US-style is legitimate input handling; outputting
it isn't.

The current source tree has zero violations. The guard is hard
zero-tolerance from day one — adding any new US-style strftime
output pattern fails the test.
"""
from __future__ import annotations

import pathlib
import re
import unittest


# Regex: US-style date format strings appearing inside ``strftime(``
# calls. Parsing-format allowlists (used by ``strptime`` / pandas
# ``to_datetime`` to accept partner-pasted dates) are intentionally
# multi-format and legitimate; the guard only flags OUTPUT format
# strings, which must follow CLAUDE.md.
#
# Pattern: a strftime call literal containing %m/%d/%Y or
# %m/%d/%y, optionally with the ``-`` no-pad flag (POSIX). The
# enclosing strftime( anchors the match to output context.
_US_DATE_RE = re.compile(
    r'\bstrftime\(\s*[\'"][^\'"]*%[\-]?[mM]/%[\-]?[dD]/%[Yy]'
)


def _scan_for_violations() -> list[tuple[str, int, str]]:
    """Walk rcm_mc/ for US-style date format strings inside
    ``strftime(`` calls. Returns list of (path, line_number, text)."""
    pkg_root = (
        pathlib.Path(__file__).resolve().parent.parent / "rcm_mc"
    )
    hits: list[tuple[str, int, str]] = []
    for py in pkg_root.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _US_DATE_RE.search(line):
                rel = py.relative_to(pkg_root.parent)
                hits.append((str(rel), lineno, line.strip()))
    return hits


class NoUSStyleDateFormatAtSource(unittest.TestCase):
    """Hard zero-tolerance: no US-style date format strings.

    CLAUDE.md mandates ISO-like dates. The runtime layer doesn't
    police this (no per-route rule), so the source guard is the
    single line of defense. Caught at commit time."""

    def test_no_us_style_date_format(self) -> None:
        violations = _scan_for_violations()
        if violations:
            details = "\n".join(
                f"  {path}:{lineno}  → {text[:90]}"
                for path, lineno, text in violations[:10]
            )
            extra = (
                f"\n  ...and {len(violations) - 10} more"
                if len(violations) > 10 else ""
            )
            self.fail(
                f"Found {len(violations)} US-style date format "
                f"violations at source. Use ISO-like patterns "
                f"(``%Y-%m-%d``) per CLAUDE.md.\n{details}{extra}"
            )


if __name__ == "__main__":
    unittest.main()
