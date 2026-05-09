"""Source-level guard: no ``:.1f}M`` / ``:.1f}B`` money format strings.

CLAUDE.md money-format spec: ``$X.XXM`` (2 decimal places). The
``number-format-clean`` per-route compliance rule (P94) catches
violations in rendered HTML, but only at runtime — and only on
routes that the per-route sweep actually exercises. This guard
extends the same contract to the *source code*, statically.

Adding a NEW ``${val/1e6:.1f}M`` (or ``:.1f}B``) f-string anywhere
in the rcm_mc package fails this test. To pass:

  * use ``:.2f}M`` / ``:.2f}B`` directly, OR
  * use the kit's ``format_value(val, kind="money")`` which emits
    the spec-compliant form with missing-aware fallback.

The forbidden patterns are the literal substrings — the test does
NOT regex-parse f-string syntax; it greps the source bytes. False
positives possible only inside string literals not intended as
format strings (none in the current codebase).
"""
from __future__ import annotations

import pathlib
import unittest


# Format-string substrings that violate the money 2dp spec. Includes
# the comma-grouped variant ``,.1f}`` which is also 1dp.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    ":.1f}M",
    ":.1f}B",
    ":,.1f}M",
    ":,.1f}B",
    ":.0f}M",   # also catches integer money (no decimal at all)
    ":,.0f}M",  # comma-grouped integer money
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


class NoMoneyFormatViolationsAtSource(unittest.TestCase):
    """Walks rcm_mc/ for ``:.1f}M``-style money-format violations.

    Caught at source rather than render — covers code paths the
    per-route compliance sweep doesn't exercise (e.g., CSV export,
    CLI rendering, IC-packet generation)."""

    def test_no_one_or_zero_decimal_money_format_strings(self) -> None:
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
                f"Found {len(violations)} money-format violations "
                f"at source. Use ``:.2f}}M`` / ``:.2f}}B`` or "
                f"``format_value(v, kind='money')`` from the kit.\n"
                f"{details}{extra}"
            )


if __name__ == "__main__":
    unittest.main()
