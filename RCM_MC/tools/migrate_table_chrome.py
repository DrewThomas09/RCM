"""Migrate table-chrome inline styles to class-based markup.

Cycle 27 shipped ``ck_data_table`` + utility CSS classes for the
table-chrome cluster (containers, scroll wrappers, alternating-
row backgrounds). Cycle 28 ships the migration script.

Conservative scope: replaces only EXACT-MATCH inline-style
attribute strings on table containers and tr backgrounds. Doesn't
touch header `<th>` cells (those need richer per-page rewriting
that cycle 29+ can address). Doesn't touch row content (already
migrated to ``ck_data_cell`` in cycle 25).

The exact patterns this script replaces:

1. ``<div style="overflow-x:auto;margin-top:12px">``
     → ``<div class="ck-data-table-scroll">``
2. ``<table style="width:100%;border-collapse:collapse;font-size:11px">``
     → ``<table class="ck-data-table">``
3. ``<tr style="background:{rb}">``
     → ``<tr>``  (alt-row backgrounds via nth-child(even) CSS)
4. ``<tr style="background:{bg}">`` (header row in some files)
     → ``<tr>``

Anything else stays verbatim — the script is lossy-by-design,
favoring safety over coverage. Cells the cycle-25 helper missed
+ header `<th>` cells will need to be migrated in a follow-up.

Usage::

    python tools/migrate_table_chrome.py --dry-run path/to/page.py
    python tools/migrate_table_chrome.py rcm_mc/ui/data_public/*.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


# Exact-match replacements. Each maps a literal source pattern to
# its class-based equivalent. The literal must appear verbatim in
# the source — no regex, no whitespace tolerance — to keep the
# script lossy-by-design.
_LITERAL_REPLACEMENTS: List[Tuple[str, str]] = [
    (
        '<div style="overflow-x:auto;margin-top:12px">',
        '<div class="ck-data-table-scroll">',
    ),
    (
        '<table style="width:100%;border-collapse:collapse;font-size:11px">',
        '<table class="ck-data-table">',
    ),
    (
        '<tr style="background:{rb}">',
        '<tr>',
    ),
    (
        '<tr style="background:{bg}">',
        '<tr>',
    ),
]


def migrate_file(path: Path, dry_run: bool = False) -> int:
    """Apply the literal replacements. Returns count of replacements."""
    src = path.read_text(encoding="utf-8")
    new_src = src
    total = 0
    for old, new in _LITERAL_REPLACEMENTS:
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
        f"\nTotal: {total} chrome elements "
        f"{'would be ' if args.dry_run else ''}migrated.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
