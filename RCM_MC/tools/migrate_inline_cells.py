"""Migrate hand-rolled inline-styled ``<td>`` cells to ``ck_data_cell``.

The cycle 22 audit confirmed ~700 instances of a single inline-style
pattern across 124 data_public pages — each table cell hand-rolls a
~200-byte style attribute. Cycle 23 ships the migration:

    f'<td style="text-align:right;padding:5px 10px;'
    f'font-variant-numeric:tabular-nums;font-family:JetBrains '
    f'Mono,monospace;font-size:11px;color:{text_dim}">{value}</td>'

becomes

    ck_data_cell(f"{value}", align="right", mono=True, tone="dim")

The script parses the style attribute, maps known properties to
``ck_data_cell`` kwargs, and rewrites the cell. **Conservative
defaults**: a cell with an unrecognised style fragment is left
alone — no destructive rewrites. The unmigrated cells stay as
hand-rolled inline-styled `<td>` and the audit's cleanliness
penalty still applies; this is by design (cycle 21 lesson:
mechanical scripts must fail closed, not destructively).

Color-token mapping:
- ``color:{text_dim}``  → ``tone="dim"``
- ``color:{text}``      → no tone (default text color)
- ``color:{pos}``       → ``tone="pos"``
- ``color:{neg}``       → ``tone="neg"``
- ``color:{acc}``       → ``tone="acc"``
- ``color:{P[...``      → no tone (dynamic; left as inline style)
- ``color:{<other>}``   → no tone (unknown variable; skip)

Usage::

    python tools/migrate_inline_cells.py --dry-run path/to/page.py
    python tools/migrate_inline_cells.py path/to/page1.py path/to/page2.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# Captures the LITERAL inline-styled <td> shape we know about. The
# style attr is matched as a flat string; we parse properties out
# of it inside the rewrite. F-string interpolations like
# ``{text_dim}`` stay as literals in the captured group.
_RE_INLINE_TD = re.compile(
    r"""
    <td\s+style="
    (?P<style>[^"]+)
    ">
    (?P<inner>.*?)
    </td>
    """,
    re.VERBOSE | re.DOTALL,
)

# Recognised color-token names to tone modifiers. Any other token
# (e.g. {dp_c}, {ir_c}, dynamic colors) → no tone, skip rewrite.
_COLOR_TONES = {
    "text_dim": "dim",
    "P[\"text_dim\"]": "dim",
    "text": None,        # default — no tone
    "P[\"text\"]": None,
    "pos": "pos",
    "P[\"positive\"]": "pos",
    "neg": "neg",
    "P[\"negative\"]": "neg",
    "acc": "acc",
    "P[\"accent\"]": "acc",
}


def _parse_style(style: str) -> Optional[dict]:
    """Map an inline-style attr to ``ck_data_cell`` kwargs.

    Returns None when the style contains a fragment we don't
    recognise — caller should leave the original cell alone.
    """
    kwargs = {}
    # Tokenise on ``;`` and trim.
    props = [p.strip() for p in style.split(";") if p.strip()]
    for prop in props:
        if ":" not in prop:
            return None
        name, _, value = prop.partition(":")
        name, value = name.strip(), value.strip()

        if name == "text-align":
            if value not in ("left", "right", "center"):
                return None
            if value != "left":
                kwargs["align"] = value
        elif name == "padding":
            # Only accept the canonical "5px 10px" — anything else
            # means a non-standard cell that needs human review.
            if value != "5px 10px":
                return None
        elif name == "font-family":
            if "JetBrains Mono" in value or "Mono,monospace" in value:
                kwargs["mono"] = True
            else:
                return None
        elif name == "font-variant-numeric":
            if value != "tabular-nums":
                return None
            kwargs["mono"] = True  # implies mono
        elif name == "font-size":
            # Only accept 11px (the canonical body) and 10px (the
            # secondary). 10px doesn't have a class yet — bail.
            if value not in ("11px", "10px"):
                return None
            if value == "10px":
                return None
        elif name == "font-weight":
            try:
                w = int(value)
            except ValueError:
                return None
            if w not in (600, 700):
                return None
            kwargs["weight"] = w
        elif name == "color":
            # Color value must be {var}-shape; extract the var name
            m = re.match(r"\{([^}]+)\}$", value)
            if not m:
                return None
            varname = m.group(1)
            if varname not in _COLOR_TONES:
                return None
            tone = _COLOR_TONES[varname]
            if tone is not None:
                kwargs["tone"] = tone
        else:
            # Unknown property — bail
            return None
    return kwargs


def _kwargs_to_call(inner: str, kwargs: dict) -> str:
    """Render the ``ck_data_cell`` call from inner content + kwargs.

    ``inner`` is the cell content as it appeared in the source,
    typically containing f-string interpolations. We wrap it in a
    new f-string so interpolations evaluate at render time.
    """
    parts = [f'f"{inner}"']
    for key in ("align", "mono", "tone", "weight"):
        if key not in kwargs:
            continue
        v = kwargs[key]
        if isinstance(v, str):
            parts.append(f'{key}="{v}"')
        elif isinstance(v, bool):
            parts.append(f'{key}={v}')
        elif isinstance(v, int):
            parts.append(f'{key}={v}')
    return f'ck_data_cell({", ".join(parts)})'


def migrate_file(path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """Returns (cells_migrated, cells_skipped)."""
    src = path.read_text(encoding="utf-8")
    migrated = 0
    skipped = 0
    out_parts: List[str] = []
    last_end = 0
    for m in _RE_INLINE_TD.finditer(src):
        style = m.group("style")
        inner = m.group("inner")
        kwargs = _parse_style(style)
        out_parts.append(src[last_end:m.start()])
        if kwargs is None:
            # Leave the original cell alone
            out_parts.append(m.group(0))
            skipped += 1
        else:
            out_parts.append(_kwargs_to_call(inner, kwargs))
            migrated += 1
        last_end = m.end()
    out_parts.append(src[last_end:])
    new_src = "".join(out_parts)

    # Need to ensure ck_data_cell is imported
    if migrated > 0 and "ck_data_cell" not in src:
        # Inject into an existing _chartis_kit import line if present
        import_line_re = re.compile(
            r"(from rcm_mc\.ui\._chartis_kit import [^\n]+)",
        )
        m = import_line_re.search(new_src)
        if m and "ck_data_cell" not in m.group(1):
            new_line = m.group(1).rstrip()
            if new_line.endswith(")"):
                new_line = new_line[:-1] + ", ck_data_cell)"
            else:
                new_line = new_line + ", ck_data_cell"
            new_src = new_src.replace(m.group(1), new_line, 1)
        else:
            # No existing import — prepend at top
            new_src = (
                "from rcm_mc.ui._chartis_kit import ck_data_cell\n"
                + new_src
            )

    if not dry_run and migrated > 0:
        path.write_text(new_src, encoding="utf-8")
    return (migrated, skipped)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("files", nargs="+", help="Files to migrate")
    p.add_argument(
        "--dry-run", action="store_true",
        help="Report counts without writing",
    )
    args = p.parse_args(argv)

    total_migrated = 0
    total_skipped = 0
    for f in args.files:
        path = Path(f)
        if not path.exists():
            sys.stderr.write(f"skip (not found): {f}\n")
            continue
        m_count, s_count = migrate_file(path, dry_run=args.dry_run)
        total_migrated += m_count
        total_skipped += s_count
        marker = "+" if m_count else " "
        sys.stdout.write(
            f"  {marker} {f}: migrated={m_count} skipped={s_count}\n"
        )
    sys.stdout.write(
        f"\nTotal: {total_migrated} cells migrated, "
        f"{total_skipped} skipped (unrecognised style).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
