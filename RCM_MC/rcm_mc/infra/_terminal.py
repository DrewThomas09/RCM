"""Terminal styling helpers — stdlib only.

Small, tasteful ANSI-based formatting for the CLI output. No external deps
(no ``rich``, no ``colorama``). Colors are **automatically disabled** when:

- stdout is not a TTY (piped to a file, captured by pytest, etc.)
- the ``NO_COLOR`` environment variable is set (respect the
  https://no-color.org convention)
- the ``TERM`` environment variable is ``dumb``

``FORCE_COLOR=1`` overrides the auto-detection (useful for CI with colored
log viewers).

Design principle: every helper returns a *string* that can be composed or
redirected to any file. The ``*_print`` variants call the ``print`` builtin
for convenience in cli.py.
"""
from __future__ import annotations

import os
import shutil
import sys
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Tuple


# ── Color tables ────────────────────────────────────────────────────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_ITALIC = "\033[3m"

# Foreground colors (256-color palette subset for good terminal-theme support)
_FG = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    # Bright variants — better contrast on dark terminals
    "bright_red":    "\033[91m",
    "bright_green":  "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue":   "\033[94m",
    "bright_cyan":   "\033[96m",
    "gray":          "\033[90m",
}


# ── TTY / preference detection ──────────────────────────────────────────────

def supports_color(stream=None) -> bool:
    """True if we should emit ANSI codes. Respects NO_COLOR / FORCE_COLOR /
    TERM=dumb / non-TTY stdout.
    """
    stream = stream if stream is not None else sys.stdout
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    # Has to be a real terminal (test runs capture, pipes suppress, etc.)
    return hasattr(stream, "isatty") and stream.isatty()


def paint(
    text: str,
    color: Optional[str] = None,
    bold: bool = False,
    dim: bool = False,
    italic: bool = False,
    stream=None,
) -> str:
    """Wrap ``text`` in ANSI codes when ``supports_color(stream)``.

    Degrades to the plain string when colors aren't supported, so callers
    can pass the result straight to ``print()`` or ``sys.stderr.write()``.
    """
    if not supports_color(stream):
        return text
    codes: List[str] = []
    if bold:
        codes.append(_BOLD)
    if dim:
        codes.append(_DIM)
    if italic:
        codes.append(_ITALIC)
    if color and color in _FG:
        codes.append(_FG[color])
    if not codes:
        return text
    return f"{''.join(codes)}{text}{_RESET}"


# ── Semantic print helpers ──────────────────────────────────────────────────

_OK_MARK = "✓"
_WARN_MARK = "⚠"
_ERR_MARK = "✗"
_ARROW_MARK = "▶"


def banner(title: str, *, stream=None) -> str:
    """A styled section banner, used between pipeline stages.

    Falls back to ``=== title ===`` when colors are off.
    """
    if not supports_color(stream):
        return f"\n=== {title} ==="
    arrow = paint(_ARROW_MARK, color="cyan", bold=True, stream=stream)
    name = paint(title, bold=True, stream=stream)
    return f"\n{arrow} {name}"


def success(text: str, *, stream=None) -> str:
    mark = paint(_OK_MARK, color="green", bold=True, stream=stream)
    return f"  {mark} {text}"


def warn(text: str, *, stream=None) -> str:
    mark = paint(_WARN_MARK, color="yellow", bold=True, stream=stream)
    return f"  {mark} {text}"


def error(text: str, *, stream=None) -> str:
    mark = paint(_ERR_MARK, color="red", bold=True, stream=stream)
    return f"  {mark} {text}"


def info(text: str, *, stream=None) -> str:
    return f"  {text}"


def wrote(path: str, *, label: str = "wrote", stream=None) -> str:
    """``  ✓ wrote /long/path/to/file.csv`` with path dimmed when color-on."""
    dirname, basename = os.path.split(path)
    if dirname and supports_color(stream):
        dir_part = paint(dirname + os.sep, color="gray", stream=stream)
        path_rendered = f"{dir_part}{basename}"
    else:
        path_rendered = path
    mark = paint(_OK_MARK, color="green", bold=True, stream=stream)
    verb = paint(label, dim=True, stream=stream)
    return f"  {mark} {verb} {path_rendered}"


# ── Completion box ──────────────────────────────────────────────────────────

def _terminal_width(fallback: int = 70) -> int:
    try:
        return max(50, min(shutil.get_terminal_size((fallback, 20)).columns, 100))
    except (AttributeError, ValueError, OSError):
        return fallback


def completion_box(
    title: str,
    items: Iterable[Tuple[str, str]],
    *,
    width: Optional[int] = None,
    stream=None,
) -> str:
    """Final "RUN COMPLETE" banner with label/value pairs.

    ``items`` is an iterable of ``(label, value)`` tuples. Labels left-align
    and share a column width; values wrap if necessary. Looks like::

        ──────────────────────────────────────────────────────────────────
          ✓ RUN COMPLETE — outputs are on disk
        ──────────────────────────────────────────────────────────────────
          Folder:    /path/to/outdir
          Report:    file:///path/to/outdir/report.html
          Workbook:  /path/to/outdir/diligence_workbook.xlsx
          Tables:    /path/to/outdir/summary.csv
                     /path/to/outdir/simulations.csv
        ──────────────────────────────────────────────────────────────────
    """
    w = width or _terminal_width()
    lines: List[str] = []

    rule_char = "─"
    rule = rule_char * w
    rule_p = paint(rule, color="cyan", stream=stream)
    mark = paint(_OK_MARK, color="green", bold=True, stream=stream)
    title_p = paint(title, bold=True, stream=stream)

    lines.append("")
    lines.append(rule_p)
    lines.append(f"  {mark} {title_p}")
    lines.append(rule_p)

    # Normalize: accept a list of (label, value_or_list)
    pairs: List[Tuple[str, List[str]]] = []
    for label, value in items:
        if isinstance(value, (list, tuple)):
            vals = [str(v) for v in value]
        else:
            vals = [str(value)]
        pairs.append((str(label), vals))

    if pairs:
        max_label = max(len(p[0]) for p in pairs)
        for label, vals in pairs:
            padded_label = label.ljust(max_label)
            label_p = paint(padded_label, bold=True, stream=stream)
            first = True
            for v in vals:
                if first:
                    lines.append(f"  {label_p}  {v}")
                    first = False
                else:
                    lines.append(f"  {' ' * max_label}  {v}")

    lines.append(rule_p)
    lines.append("")
    return "\n".join(lines)


# ── Convenience: context manager for a named pipeline step ──────────────────

@contextmanager
def step(title: str, *, stream=None) -> Iterator[None]:
    """Print a banner on enter; no explicit outro (the next banner marks the next step)."""
    print(banner(title, stream=stream), file=stream or sys.stdout)
    yield
