"""Source-level guard: money / multiple / percent format violations.

CLAUDE.md format spec:
  * Money:     ``$X.XXM`` / ``$X.XXB`` (2 decimal places)
  * Multiples: ``X.XXx`` (2 decimal places)
  * Percent:   ``X.X%``  (1 decimal place)

The runtime ``number-format-clean`` per-route compliance rule (P94)
catches violations in rendered HTML, but only on routes the
per-route sweep actually exercises. This guard extends the same
contract to the *source code*, statically — covering CSV exports,
CLI rendering, IC-packet generation, etc.

Adding a NEW ``${val/1e6:.1f}M`` or ``${moic:.1f}x`` f-string
anywhere in the rcm_mc package fails this test. To pass:

  * use ``:.2f}M`` / ``:.2f}B`` / ``:.2f}x`` / ``:.1f}%`` directly,
    OR
  * use the kit's ``format_value(val, kind="money")`` (or
    ``kind="multiple"`` / ``kind="percent"``) which emits the
    spec-compliant form with missing-aware fallback.

The percent guard is context-aware: ``:.0f}%`` literals appear
legitimately inside CSS layout properties (``width:50%;``,
``transform:translateX(50%)``, etc.), so the scanner skips lines
matching a CSS-layout regex. The remaining text-context
``:.0f}%`` patterns are partner-facing prose / metric values that
must follow the 1dp spec.

The forbidden money/multiple patterns are literal substrings —
the test does NOT regex-parse f-string syntax; it greps the
source bytes.
"""
from __future__ import annotations

import pathlib
import re
import unittest


# CSS-layout properties that legitimately accept percentage values
# (``width:50%;`` etc.). Lines matching this regex are skipped by
# the percent-format scanner.
_CSS_LAYOUT_RE = re.compile(
    r'(?:width|height|top|bottom|left|right|margin|padding|'
    r'transform|opacity|max-width|max-height|min-width|min-height|'
    r'inset|gap|grid-template|background-position|background-size):'
)


# Text-context ``:.0f}%`` pattern — Python f-string formatting for
# integer percent. Match only if the next char is NOT a digit, dot,
# dash, semicolon, or quote (those rule out continuation forms).
_PERCENT_FMT_RE = re.compile(r':\.0f\}%[^.\d\-;"]')


# Format-string substrings that violate the CLAUDE.md money/multiple
# 2dp spec. Includes comma-grouped variants. Multiples (``X.XXx``)
# share the same source-level rules — runtime audit catches them
# at render but only on routes the per-route sweep exercises.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    # Money — 2 decimal places (CLAUDE.md)
    ":.1f}M",
    ":.1f}B",
    ":,.1f}M",
    ":,.1f}B",
    ":.0f}M",   # also catches integer money (no decimal at all)
    ":,.0f}M",  # comma-grouped integer money
    # Multiples — 2 decimal places (e.g. 2.50x)
    ":.1f}x",
    ":.0f}x",
    ":,.1f}x",
    ":,.0f}x",
    # Note: :.0f}B (integer billions) would also be a violation but
    # is rare enough that we don't pin it as a guard rule yet —
    # add when we see the first one.
)


def _scan_for_violations() -> list[tuple[str, str, int, str]]:
    """Walk rcm_mc/ for forbidden format-string substrings.
    Returns list of (path, pattern, line_number, line_text)."""
    pkg_root = (
        pathlib.Path(__file__).resolve().parent.parent / "rcm_mc"
    )
    hits: list[tuple[str, str, int, str]] = []
    for py in pkg_root.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            # Money/multiple — literal-substring scan
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    rel = py.relative_to(pkg_root.parent)
                    hits.append((str(rel), pattern, lineno, line.strip()))
                    break
            else:
                # Percent — context-aware regex; skip CSS-layout lines
                if _CSS_LAYOUT_RE.search(line):
                    continue
                if _PERCENT_FMT_RE.search(line):
                    rel = py.relative_to(pkg_root.parent)
                    hits.append(
                        (str(rel), ":.0f}%", lineno, line.strip()),
                    )
    return hits


class NoNumberFormatViolationsAtSource(unittest.TestCase):
    """Walks rcm_mc/ for money / multiple / percent format-string
    violations at source. Caught before render — covers code paths
    the per-route compliance sweep doesn't exercise (CSV export,
    CLI rendering, IC-packet generation)."""

    def test_no_one_or_zero_decimal_format_strings(self) -> None:
        violations = _scan_for_violations()
        if violations:
            details = "\n".join(
                f"  {path}:{lineno}  {pattern!r}  → {text[:90]}"
                for path, pattern, lineno, text in violations[:20]
            )
            extra = (
                f"\n  ...and {len(violations) - 20} more"
                if len(violations) > 20 else ""
            )
            self.fail(
                f"Found {len(violations)} number-format violations "
                f"at source. Use ``:.2f}}M`` / ``:.2f}}B`` / "
                f"``:.2f}}x`` / ``:.1f}}%`` or ``format_value(v, "
                f"kind='money'|'multiple'|'percent')`` from the "
                f"kit.\n{details}{extra}"
            )


if __name__ == "__main__":
    unittest.main()
