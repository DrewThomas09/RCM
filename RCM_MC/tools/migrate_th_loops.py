"""Migrate hand-rolled ``<th>`` header-cell loops to ck_data_cell.

Cycle 30 ships the migration script paired with the cycle-30
update to ``ck_data_cell`` (``is_header=True`` now adds the
``ck-data-table-head`` class for editorial header styling).

The dominant pattern across data_public pages (~720 instances):

    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;'
        f'border-bottom:1px solid {border};font-size:10px;'
        f'color:{text_dim};letter-spacing:0.05em">{c}</th>'
        for c, a in cols
    )

Becomes:

    ths = "".join(
        ck_data_cell(c, align=a, is_header=True)
        for c, a in cols
    )

Conservative scope: matches only the canonical
"text-align:{a};padding:6px 10px;border-bottom:1px solid {…};
font-size:10px;color:{…};letter-spacing:0.05em" shape inside an
f-string-with-loop expression. Anything else stays untouched.

Usage::

    python tools/migrate_th_loops.py --dry-run path/to/page.py
    python tools/migrate_th_loops.py rcm_mc/ui/data_public/*.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


# Match the typical pattern: an f-string that opens a <th>, contains
# the canonical style attribute, and closes with the loop variable.
# We intentionally match a SPECIFIC shape; pages with variant header
# patterns (white-space:nowrap, font-weight, custom width) are left
# alone for human review.
_RE_TH_PATTERN = re.compile(
    r"""f'<th\s+style="
        text-align:\{(?P<align_var>\w+)\};
        padding:6px\s+10px;
        border-bottom:1px\s+solid\s+\{(?P<border_var>\w+)\};
        font-size:10px;
        color:\{(?P<color_var>\w+)\};
        letter-spacing:0\.05em
        (?:;white-space:nowrap)?
    ">(?P<inner>.*?)</th>'""",
    re.VERBOSE,
)


def migrate_file(path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """Returns (replacements, hits-not-rewritten)."""
    src = path.read_text(encoding="utf-8")
    matches = list(_RE_TH_PATTERN.finditer(src))
    if not matches:
        return (0, 0)

    new_src = src
    # Replace from the END so byte indices don't shift.
    rewrites = 0
    for m in reversed(matches):
        align = m.group("align_var")
        inner = m.group("inner")
        # The inner is inside an f-string context (we matched f'...').
        # ck_data_cell does not html-escape; pass inner verbatim as
        # an f-string interpolation. If inner contains literal
        # ``"`` we use triple-double-quotes to wrap; if ``"""`` is
        # present (extreme edge case) we skip the rewrite.
        if '"""' in inner:
            continue
        # Build the replacement call. The original was a SINGLE
        # f-string element of an iterable — replace it with a
        # function call that returns the same string.
        replacement = (
            f'ck_data_cell(f"""{inner}""", align={align}, is_header=True)'
        )
        new_src = new_src[:m.start()] + replacement + new_src[m.end():]
        rewrites += 1

    if rewrites > 0 and not dry_run:
        # Ensure ck_data_cell is imported. The page already has it
        # from cycle 25 in most cases — check first.
        if "ck_data_cell" not in src:
            ml_re = re.compile(
                r"(from rcm_mc\.ui\._chartis_kit import \()"
                r"(?P<body>[^)]+)(\))",
                re.DOTALL,
            )
            m_ml = ml_re.search(new_src)
            if m_ml:
                body = m_ml.group("body").rstrip()
                new_body = (
                    body + (" ck_data_cell," if body.endswith(",") else ", ck_data_cell,") + "\n"
                )
                new_src = (
                    new_src[:m_ml.start("body")]
                    + new_body
                    + new_src[m_ml.end("body"):]
                )
            else:
                sl_re = re.compile(
                    r"(from rcm_mc\.ui\._chartis_kit import [^\n(]+)",
                )
                m_sl = sl_re.search(new_src)
                if m_sl:
                    new_src = new_src.replace(
                        m_sl.group(1),
                        m_sl.group(1).rstrip() + ", ck_data_cell",
                        1,
                    )
        path.write_text(new_src, encoding="utf-8")
    return (rewrites, len(matches) - rewrites)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="+", help="Files to migrate")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Report counts without writing",
    )
    args = p.parse_args(argv)

    total_rewrites = 0
    total_skipped = 0
    for f in args.files:
        path = Path(f)
        if not path.exists():
            sys.stderr.write(f"skip (not found): {f}\n")
            continue
        rewrites, skipped = migrate_file(path, dry_run=args.dry_run)
        total_rewrites += rewrites
        total_skipped += skipped
        marker = "+" if rewrites else " "
        sys.stdout.write(
            f"  {marker} {f}: rewrote={rewrites} skipped={skipped}\n"
        )
    sys.stdout.write(
        f"\nTotal: {total_rewrites} <th> patterns "
        f"{'would be ' if args.dry_run else ''}migrated, "
        f"{total_skipped} skipped (triple-quote edge case).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
