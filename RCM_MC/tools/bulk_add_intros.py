"""Bulk-add ``editorial_intro`` kwarg to ``chartis_shell`` calls.

Cycle 20 shipped the ``editorial_intro`` kwarg on ``chartis_shell``
that auto-prepends ``ck_section_intro`` to the body — letting a
legacy renderer adopt the chartis cadence with one 3-line addition
instead of restructuring. Cycle 21 applies that addition
mechanically to a list of target page files.

The intro generated for each file is template-shaped using the
filename as a fallback eyebrow. The headline and italic_word are
derived from the title kwarg in the chartis_shell call when
detectable; otherwise they default to a generic editorial cadence.
The insertion point is the LAST chartis_shell call in the file
(usually the main happy-path return).

This is intentionally a one-shot script — run it once per cycle to
lift a tier of pages, review the diff, refine the headlines manually
where the templates read flat. Don't rely on the templates as
permanent copy.

Usage::

    python tools/bulk_add_intros.py path/to/page1.py path/to/page2.py
    python tools/bulk_add_intros.py --threshold 70  # auto-pick from audit

When ``--threshold`` is given, the script invokes the v5 fidelity
audit, picks every page scoring below the threshold but above the
lower bound, and applies the intro to each.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# Regex that locates a ``chartis_shell(...)`` call. Matches the
# whole call including all kwargs up to the closing paren of the
# call. Doesn't try to be a full Python parser — just enough to
# find insertion points.
_RE_CHARTIS_SHELL_CALL = re.compile(
    r"(?P<indent>\n[ \t]+)?return\s+chartis_shell\s*\(",
)


def _balance_paren_end(src: str, start: int) -> Optional[int]:
    """Find the index of the close-paren matching the open at ``start``.

    Naive but adequate: counts parens, ignoring those inside string
    literals (we just look for ``"`` and ``'`` and toggle a "we are
    inside a string" flag). Ignores escapes; chartis_shell call args
    don't typically contain backslash-quote pairs in their string
    values.
    """
    depth = 1
    i = start
    in_string: Optional[str] = None  # current quote char or None
    while i < len(src):
        ch = src[i]
        if in_string is not None:
            if ch == in_string and src[i - 1] != "\\":
                in_string = None
        else:
            if ch in ('"', "'"):
                # Detect triple-quoted strings (rare in chartis_shell
                # arg position) by checking the next two chars.
                if src[i:i + 3] in ('"""', "'''"):
                    end = src.find(src[i:i + 3], i + 3)
                    if end == -1:
                        return None
                    i = end + 3
                    continue
                in_string = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


def _generate_intro(file_path: Path, title_in_call: Optional[str]) -> dict:
    """Generate a template ``editorial_intro`` dict for a file.

    Eyebrow comes from the title (uppercased) when available, else
    from the filename (de-suffixed). Headline and italic_word use
    safe defaults. The result is a dict ready to inject as the
    ``editorial_intro`` kwarg.
    """
    if title_in_call:
        eyebrow = title_in_call.upper().split("·")[0].strip()
    else:
        # bankruptcy_survivor_page → BANKRUPTCY SURVIVOR
        stem = file_path.stem
        if stem.endswith("_page"):
            stem = stem[: -len("_page")]
        eyebrow = stem.replace("_", " ").upper()
    # Generic editorial cadence — headline calls out the page noun
    # with a verb-italic that makes the noun the subject of action.
    noun = (
        title_in_call.split("·")[0].strip()
        if title_in_call else file_path.stem.replace("_", " ")
    )
    headline = f"What the {noun.lower()} reveals on this deal."
    italic = "reveals"
    return {
        "eyebrow": eyebrow,
        "headline": headline,
        "italic_word": italic,
    }


_RE_TITLE_KWARG = re.compile(
    r"""title\s*=\s*(?:f?["']([^"']+)["']|f?["']([^"']*)\{[^}]+\}([^"']*)["'])""",
)


def _extract_title(call_src: str) -> Optional[str]:
    """Pull the ``title="..."`` kwarg literal out of a chartis_shell call."""
    m = _RE_TITLE_KWARG.search(call_src)
    if not m:
        return None
    if m.group(1):
        return m.group(1)
    # f-string with {var} interpolation — return the surrounding
    # literal parts joined.
    return (m.group(2) or "") + (m.group(3) or "")


def add_intro_to_file(path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Insert an ``editorial_intro`` kwarg into the LAST chartis_shell
    call in ``path``. Returns (changed, message).
    """
    src = path.read_text(encoding="utf-8")
    if "editorial_intro" in src:
        return (False, "already has editorial_intro")
    matches = list(_RE_CHARTIS_SHELL_CALL.finditer(src))
    if not matches:
        return (False, "no return chartis_shell(... ) found")
    # Take the last one — usually the happy-path return at the
    # bottom of the render function.
    m = matches[-1]
    open_paren = m.end() - 1  # index of the "(" we matched
    close_paren = _balance_paren_end(src, open_paren + 1)
    if close_paren is None:
        return (False, "unbalanced parens — paste error?")

    call_src = src[m.start():close_paren + 1]
    title = _extract_title(call_src)
    intro = _generate_intro(path, title)

    # Pretty-print the kwarg with the same indentation as the call.
    indent_match = re.search(r"\n([ \t]+)return\s+chartis_shell\s*\(",
                             src[m.start():m.start() + 200])
    indent = indent_match.group(1) if indent_match else "    "
    inner_indent = indent + "    "
    intro_kwarg = (
        f",\n{inner_indent}editorial_intro={{"
        f'\n{inner_indent}    "eyebrow": "{intro["eyebrow"]}",'
        f'\n{inner_indent}    "headline": "{intro["headline"]}",'
        f'\n{inner_indent}    "italic_word": "{intro["italic_word"]}",'
        f"\n{inner_indent}}}"
    )

    # Insert before the closing ")". The byte BEFORE the close paren
    # may be whitespace + newline + a trailing comma — Python allows
    # trailing commas in call kwarg lists. If the last non-whitespace
    # char before ")" is already a comma, our prepended ", \n..."
    # would produce ",,\n..." which is a syntax error. Scan back and
    # truncate any trailing comma before inserting.
    insert_at = close_paren
    j = close_paren - 1
    while j > open_paren and src[j] in " \t\n":
        j -= 1
    has_trailing_comma = j > open_paren and src[j] == ","
    if has_trailing_comma:
        # Replace the trailing comma + everything up to the close
        # paren with our kwarg's leading comma + body. This preserves
        # the original indentation style.
        insert_at = j + 1  # right after the existing trailing comma
        # The kwarg starts with ",\n..." — strip the leading comma
        # because the existing one is already there.
        intro_kwarg = intro_kwarg[1:]
    new_src = (
        src[:insert_at]
        + intro_kwarg
        + src[insert_at:]
    )

    if dry_run:
        return (True, "would-add intro")
    path.write_text(new_src, encoding="utf-8")
    return (True, "added intro")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Bulk-add editorial_intro kwarg to chartis_shell calls.",
    )
    p.add_argument("files", nargs="*", help="Page files to update")
    p.add_argument(
        "--from-audit-tier", type=int, default=None,
        help="Auto-pick files from V5 fidelity audit scoring "
             "below this threshold (e.g. 70 picks the 50-69 tier).",
    )
    p.add_argument(
        "--max-files", type=int, default=30,
        help="Cap the number of files when --from-audit-tier is used",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without writing",
    )
    args = p.parse_args(argv)

    files: List[Path] = [Path(f) for f in args.files]

    if args.from_audit_tier:
        sys.path.insert(0, str(Path(__file__).parent))
        import v5_fidelity_audit as audit
        ui_dir = (
            Path(__file__).parent.parent / "rcm_mc" / "ui"
        )
        scores = audit.audit_tree(
            ui_dir, repo_root=Path(__file__).parent.parent,
        )
        below = [
            s for s in scores
            if s.score < args.from_audit_tier and s.has_chartis_shell
        ]
        below.sort(key=lambda s: -s.score)
        repo_root = Path(__file__).parent.parent
        for s in below[: args.max_files]:
            files.append(repo_root / s.file)

    if not files:
        sys.stderr.write(
            "No files specified. Pass paths directly or use "
            "--from-audit-tier.\n"
        )
        return 2

    changed = 0
    for f in files:
        if not f.exists():
            sys.stderr.write(f"skip (not found): {f}\n")
            continue
        ok, msg = add_intro_to_file(f, dry_run=args.dry_run)
        marker = "+" if ok else " "
        sys.stdout.write(f"  {marker} {f}: {msg}\n")
        if ok:
            changed += 1
    sys.stdout.write(
        f"\n{changed} file{'s' if changed != 1 else ''} "
        f"{'would be ' if args.dry_run else ''}updated.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
