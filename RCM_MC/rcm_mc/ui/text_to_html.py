"""Turn a terminal-formatted text block into a styled HTML page (UI-3).

Many ``rcm-mc`` commands emit text with ANSI colors and box-drawing
characters (severity glyphs, ✓/⚠/✗, unicode rules). That's great for
terminal, but when an analyst clicks the file in the output-folder index
they land on a raw monospace blob.

This module provides a single public function:

    text_to_html(text, title) -> str
    wrap_text_file(in_path, out_path=None, title=None) -> str

``wrap_text_file`` reads the terminal output, strips ANSI escapes,
re-colors severity glyphs (✓/⚠/✗/red/green/amber cues), auto-links any
``wrote: path/to/file`` lines, and wraps the result in a self-contained
HTML page that matches the rest of the rcm-mc visual language.

Design choices:
  - **Preserve monospace alignment** — box characters + column padding
    built by the terminal formatters must still read correctly.
  - **Semantic re-coloring** — ✓ green, ⚠ amber, ✗ red, SAFE/TRIPPED
    highlighted. Color comes from the HTML wrapper, not from preserved
    ANSI (which would require escape parsing + still look "off" in
    browsers).
  - **Zero JS, zero external CSS** — output is a single file.
"""
from __future__ import annotations

import html
import os
import re
from typing import Optional


# ── ANSI strip ─────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escapes so the raw glyphs survive without color noise."""
    return _ANSI_RE.sub("", text)


# ── Semantic re-coloring ───────────────────────────────────────────────────

# Terminal glyphs mapped to CSS classes; applied as single-char wraps so
# the surrounding monospace layout isn't disturbed.
_GLYPH_CLASS = {
    "✓": "ok",
    "⚠": "warn",
    "✗": "err",
    "↑": "up",
    "↓": "down",
    "→": "flat",
    "●": "info",
}

# Banner words that should pop — lowercase kept flexible, we match at any position
_STATUS_WORDS = [
    ("TRIPPED", "err"),
    ("SAFE",    "ok"),
    ("TIGHT",   "warn"),
    ("off_track",  "err"),
    ("concerning", "err"),
    ("favorable",  "ok"),
    ("on_track",   "ok"),
    ("lagging",    "warn"),
    ("no_plan",    "muted"),
]


def _colorize_line(line: str) -> str:
    """HTML-escape + wrap severity glyphs/words in spans. Preserves spacing."""
    out = html.escape(line)
    for glyph, cls in _GLYPH_CLASS.items():
        out = out.replace(glyph, f'<span class="{cls}">{glyph}</span>')
    for word, cls in _STATUS_WORDS:
        # Word-boundary match so "SAFE" matches "SAFE" but not e.g. "safer"
        out = re.sub(rf"\b{re.escape(word)}\b",
                     f'<span class="{cls}">{word}</span>', out)
    return out


def _linkify_wrote(line: str) -> str:
    """If a line says ``Wrote: <path>`` (or ``wrote:``), make the path clickable."""
    m = re.match(r"^(\s*)(Wrote:|wrote:)\s+(.+)$", line)
    if not m:
        return _colorize_line(line)
    indent, verb, path = m.group(1), m.group(2), m.group(3).strip()
    # Relative link — user is viewing HTML inside the same folder
    rel = os.path.basename(path)
    return (
        f'{indent}<span class="muted">{verb}</span> '
        f'<a href="{html.escape(rel)}">{html.escape(rel)}</a>'
    )


# ── Public API ─────────────────────────────────────────────────────────────

def text_to_html(
    text: str,
    title: str,
    *,
    subtitle: Optional[str] = None,
    back_href: Optional[str] = None,
) -> str:
    """Wrap terminal-formatted ``text`` in a styled HTML document.

    The output is a complete standalone HTML file (no external deps).
    If ``back_href`` is given, a breadcrumb link is added at the top —
    useful for "← back to index" navigation from within a sub-page.
    """
    from ._ui_kit import shell

    stripped = _strip_ansi(text)
    rendered = "\n".join(_linkify_wrote(line) for line in stripped.splitlines())

    return shell(
        body=f'<pre>{rendered}</pre>',
        title=title,
        back_href=back_href,
        subtitle=subtitle,
    )


def wrap_text_file(
    in_path: str,
    out_path: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Read a text file, wrap it in HTML, write next to it. Returns HTML path.

    If ``out_path`` is None, writes ``in_path`` with ``.html`` swapped in
    for the extension (same directory). Title defaults to the filename
    stem, humanized (``37_remark_ccf`` → ``Remark Ccf``).
    """
    if not os.path.isfile(in_path):
        raise FileNotFoundError(f"Text file not found: {in_path}")

    with open(in_path, encoding="utf-8") as f:
        text = f.read()

    if out_path is None:
        stem, _ = os.path.splitext(in_path)
        out_path = stem + ".html"

    if title is None:
        stem = os.path.splitext(os.path.basename(in_path))[0]
        # Strip leading numeric prefix (demo script uses "37_remark_ccf")
        stem = re.sub(r"^\d+_", "", stem)
        title = stem.replace("_", " ").replace("-", " ").title()

    doc = text_to_html(text, title, back_href="index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def wrap_text_files_in_folder(
    folder: str,
    extensions: tuple = (".txt", ".md"),
) -> list:
    """Write an ``.html`` sibling for every matching text/markdown file in ``folder``.

    Returns paths written. Only the immediate folder — sub-folders get their
    own pass if the caller chooses. Skips files that already have an
    ``.html`` companion of the same stem to avoid overwriting custom HTML.
    """
    if not os.path.isdir(folder):
        return []
    written = []
    for name in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in extensions:
            continue
        # Don't clobber a hand-written HTML companion with the same stem
        if os.path.isfile(os.path.join(folder, stem + ".html")):
            continue
        try:
            out = wrap_text_file(os.path.join(folder, name))
            written.append(out)
        except OSError:
            continue
    return written
