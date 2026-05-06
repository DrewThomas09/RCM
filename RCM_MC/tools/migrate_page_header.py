"""Migrate the data_public page-header inline-style cluster.

Cycle 31 ships utility classes (`ck-page-wrap`, `ck-page-head`,
`ck-page-h1`, `ck-page-sub`) for the boilerplate header block
that ~124 data_public pages roll by hand:

    <div style="padding:20px;max-width:1400px;margin:0 auto">
      <div style="margin-bottom:20px">
        <h1 style="font-size:18px;font-weight:700;color:{text};
                   letter-spacing:0.02em">{title}</h1>
        <p style="font-size:12px;color:{text_dim};margin-top:4px">
          {subtitle}</p>

This script replaces each inline-styled wrapper / h1 / subtitle
with its class-based equivalent. ~500 inline-style instances
eliminated when applied across all data_public pages.

Conservative scope: literal exact-string replacements only. Pages
with header variants (different padding, fonts, etc.) are left
alone for human review.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


_REPLACEMENTS: List[Tuple[str, str]] = [
    (
        '<div style="padding:20px;max-width:1400px;margin:0 auto">',
        '<div class="ck-page-wrap">',
    ),
    (
        '<div style="margin-bottom:20px">',
        '<div class="ck-page-head">',
    ),
    (
        '<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">',
        '<h1 class="ck-page-h1">',
    ),
    (
        '<p style="font-size:12px;color:{text_dim};margin-top:4px">',
        '<p class="ck-page-sub">',
    ),
]


def migrate_file(path: Path, dry_run: bool = False) -> int:
    src = path.read_text(encoding="utf-8")
    new_src = src
    total = 0
    for old, new in _REPLACEMENTS:
        if old in new_src:
            count = new_src.count(old)
            new_src = new_src.replace(old, new)
            total += count
    if total > 0 and not dry_run:
        path.write_text(new_src, encoding="utf-8")
    return total


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="+", help="Files to migrate")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Report counts without writing",
    )
    args = p.parse_args(argv)

    total = 0
    for f in args.files:
        path = Path(f)
        if not path.exists():
            sys.stderr.write(f"skip (not found): {f}\n")
            continue
        n = migrate_file(path, dry_run=args.dry_run)
        marker = "+" if n else " "
        sys.stdout.write(f"  {marker} {f}: {n} replacements\n")
        total += n
    sys.stdout.write(
        f"\nTotal: {total} page-header elements "
        f"{'would be ' if args.dry_run else ''}migrated.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
