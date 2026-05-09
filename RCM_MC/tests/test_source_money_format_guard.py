"""Source-level guard: no money/multiple format-string violations.

CLAUDE.md format spec:
  * Money:     ``$X.XXM`` / ``$X.XXB`` (2 decimal places)
  * Multiples: ``X.XXx`` (2 decimal places)
  * Percent:   ``X.X%``  (1 decimal place — handled by the runtime
    ``number-format-clean`` rule with prose-context lookbehinds; a
    source guard would over-flag inline CSS percentages.)

The runtime ``number-format-clean`` per-route compliance rule (P94)
catches violations in rendered HTML, but only on routes the
per-route sweep actually exercises. This guard extends the same
contract to the *source code*, statically — covering CSV exports,
CLI rendering, IC-packet generation, etc.

Adding a NEW ``${val/1e6:.1f}M`` or ``${moic:.1f}x`` f-string
anywhere in the rcm_mc package fails this test. To pass:

  * use ``:.2f}M`` / ``:.2f}B`` / ``:.2f}x`` directly, OR
  * use the kit's ``format_value(val, kind="money")`` (or
    ``kind="multiple"``) which emits the spec-compliant form with
    missing-aware fallback.

The forbidden patterns are the literal substrings — the test does
NOT regex-parse f-string syntax; it greps the source bytes. False
positives possible only inside string literals not intended as
format strings (none in the current codebase).
"""
from __future__ import annotations

import pathlib
import unittest


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
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    rel = py.relative_to(pkg_root.parent)
                    hits.append((str(rel), pattern, lineno, line.strip()))
                    break
    return hits


class NoMoneyOrMultipleFormatViolationsAtSource(unittest.TestCase):
    """Walks rcm_mc/ for money or multiple format-string violations.

    Caught at source rather than render — covers code paths the
    per-route compliance sweep doesn't exercise (e.g., CSV export,
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
                f"Found {len(violations)} money/multiple-format "
                f"violations at source. Use ``:.2f}}M`` / "
                f"``:.2f}}B`` / ``:.2f}}x`` or ``format_value(v, "
                f"kind='money')`` (or kind='multiple') from the "
                f"kit.\n{details}{extra}"
            )


if __name__ == "__main__":
    unittest.main()
