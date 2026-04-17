"""Auto-generated navigable index for an output folder (UI-4).

Every ``rcm-mc`` command drops files — sometimes dozens — into a folder.
Without a landing page, the analyst opens ``MANIFEST.txt`` and hunts.
``build_output_index(outdir)`` writes ``index.html`` at the top of the
folder: one clickable page grouping every artifact by kind, with
descriptions so an analyst knows which file answers which question.

Four groups, top-to-bottom (the read order a partner actually follows):

    1. **Deliverables** — the partner-facing HTML / Excel outputs the
       analyst would hand off (``partner_brief.html``,
       ``diligence_workbook.xlsx``, ``report.html``, ``exit_memo*.html``,
       ``portfolio_dashboard.html``).
    2. **Data tables** — machine-readable outputs (CSV, JSON) for anyone
       who wants to pipe the results elsewhere.
    3. **Sub-folders** — nested output directories (e.g., ``_detail/``,
       ``lookup_data/``) get their own tile with a child-index if one exists.
    4. **Everything else** — long-tail files (SQLite, YAML, TXT).

No external deps. Self-contained HTML (inline CSS). Deliberately skips
``.DS_Store``, ``__pycache__``, hidden files, and itself.
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ── Classification tables ──────────────────────────────────────────────────

# Known-file descriptions so the index shows "what's in this file?" for
# the artifacts a PE analyst actually reads. Fallback to extension-based
# category + human-readable filename for unknown files.
_FILE_DESCRIPTIONS: Dict[str, str] = {
    # Diligence run
    "report.html":                 "Full audit-grade simulation report (methodology + sensitivity + charts)",
    "partner_brief.html":          "One-page IC-ready executive brief",
    "diligence_workbook.xlsx":     "Partner workbook with 14+ tabs (bridge, peers, stress, lineage, PE math)",
    "data_requests.md":            "Priority data asks for management (auto-generated from assumed fields)",
    "report.md":                   "Markdown version of the audit report",
    "report.pptx":                 "PowerPoint export of the headline slides",
    "summary.csv":                 "Headline metrics (mean / median / P10 / P90)",
    "simulations.csv":             "Per-simulation Monte Carlo output (raw rows)",
    "provenance.json":             "Source-grade evidence tracking (observed / prior / assumed)",
    "runs.sqlite":                 "Run history database",
    # PE math
    "pe_bridge.json":              "Value creation bridge: entry EV → organic / RCM uplift / multiple expansion → exit EV",
    "pe_returns.json":             "Base-case MOIC + IRR given equity structure",
    "pe_covenant.json":            "Leverage + covenant headroom snapshot",
    "pe_hold_grid.csv":            "Hold-years × exit-multiple sensitivity (IRR / MOIC grid)",
    # Peer + trend
    "peer_comparison.csv":         "15 matched HCRIS peers with full KPIs",
    "peer_target_percentiles.csv": "Target's rank against peers on each KPI",
    "trend.csv":                   "Multi-year HCRIS table for the target",
    "trend_signals.csv":           "Year-over-year diligence signals (with severity)",
    # Portfolio
    "portfolio.db":                "SQLite store of deals, snapshots, actuals, initiatives",
    "portfolio_dashboard.html":    "Cross-portfolio dashboard (rollup, funnel, variance)",
    # Demo-script outputs
    "MANIFEST.txt":                "Plain-text file listing",
    "_demo_actual.yaml":           "Demo config used for the diligence run",
    "_shortlist.csv":              "Demo CCN shortlist",
}

# Files that belong in "Deliverables" regardless of extension: partner-facing
# HTML / Excel. Extension-based fallbacks handle everything else.
_DELIVERABLE_NAMES = {
    "report.html", "partner_brief.html", "portfolio_dashboard.html",
    "diligence_workbook.xlsx", "report.pptx", "data_requests.md",
}

# File "kinds" by extension — used when there's no explicit description.
_KIND_BY_EXT: Dict[str, str] = {
    ".html": "HTML",
    ".xlsx": "Excel",
    ".pptx": "PowerPoint",
    ".pdf":  "PDF",
    ".csv":  "CSV",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml":  "YAML",
    ".md":   "Markdown",
    ".txt":  "Text",
    ".sqlite": "SQLite",
    ".db":   "SQLite",
    ".png":  "Image",
    ".jpg":  "Image",
    ".jpeg": "Image",
    ".svg":  "Image",
}

# Stuff we never show in the index.
_HIDDEN_PREFIXES = ("_", ".")
_HIDDEN_NAMES = {"__pycache__", "index.html"}


# ── Per-page CSS (index-specific extras on top of the shared _ui_kit) ──
#
# The shared kit covers typography, card, badge, table styles. The index
# needs its own grid layout, per-kind pill colors, and card-as-link hover.
_EXTRA_CSS = """
.grid { display: grid; gap: 0.75rem;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
a.card { text-decoration: none; color: inherit; display: block;
         padding: 1rem 1.1rem; transition: box-shadow 0.15s, border-color 0.15s, transform 0.1s; }
a.card:hover { border-color: var(--accent); box-shadow: var(--shadow-md);
               transform: translateY(-1px); }
a.card .kind { display: inline-block; font-size: 0.7rem; font-weight: 600;
               padding: 2px 8px; border-radius: 4px;
               background: var(--accent-soft); color: var(--accent);
               letter-spacing: 0.04em; text-transform: uppercase; }
a.card .kind.html  { background: var(--red-soft); color: var(--red-text); }
a.card .kind.excel { background: var(--green-soft); color: var(--green-text); }
a.card .kind.csv   { background: var(--amber-soft); color: var(--amber-text); }
a.card .kind.json  { background: var(--blue-soft); color: var(--blue-text); }
a.card .kind.yaml  { background: #F3E8FF; color: #6B21A8; }
a.card .kind.markdown { background: #F0FDF4; color: #166534; }
a.card .kind.powerpoint { background: #FED7AA; color: #9A3412; }
a.card .kind.sqlite { background: #E2E8F0; color: #334155; }
a.card .kind.folder { background: var(--blue); color: #FFFFFF; }
a.card h3 { font-size: 0.95rem; margin: 0.5rem 0 0.25rem 0;
            font-family: "SF Mono", Menlo, Consolas, monospace;
            word-break: break-all; }
a.card .desc { font-size: 0.82rem; color: var(--muted); margin: 0; line-height: 1.4; }
a.card .meta { font-size: 0.72rem; color: var(--muted); margin-top: 0.5rem;
               font-variant-numeric: tabular-nums; }
.empty { color: var(--muted); font-style: italic; padding: 1rem 0; }
.section-hint { color: var(--muted); font-size: 0.85rem; margin: 0 0 0.75rem 0; }
"""


# ── Helpers ────────────────────────────────────────────────────────────────

def _hidden(name: str) -> bool:
    if name in _HIDDEN_NAMES:
        return True
    return any(name.startswith(p) for p in _HIDDEN_PREFIXES)


def _kind(path: str) -> str:
    """Human-readable file kind for the pill label."""
    ext = os.path.splitext(path)[1].lower()
    return _KIND_BY_EXT.get(ext, "File")


def _fmt_size(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{n/1_000:.0f} KB"
    return f"{n} B"


def _describe(name: str) -> str:
    """Return the description for a known file; synthesize one otherwise."""
    if name in _FILE_DESCRIPTIONS:
        return _FILE_DESCRIPTIONS[name]
    # Heuristic fallbacks for files the shipped tables don't know about
    lower = name.lower()
    if lower.endswith(".html"):
        return "Browser-viewable HTML document"
    if lower.endswith(".csv"):
        return "Data table (CSV)"
    if lower.endswith(".json"):
        return "Structured data (JSON)"
    if lower.endswith(".md"):
        return "Markdown document"
    if lower.endswith((".yaml", ".yml")):
        return "Configuration (YAML)"
    if lower.endswith((".sqlite", ".db")):
        return "SQLite database"
    if lower.endswith((".xlsx",)):
        return "Excel workbook"
    if lower.endswith((".pptx",)):
        return "PowerPoint presentation"
    return "Output file"


# ── Scanning ───────────────────────────────────────────────────────────────

def _scan(outdir: str) -> Tuple[List[str], List[str], List[str]]:
    """Return ``(files, subfolders, hidden_count)`` for the top of ``outdir``.

    Only walks one level — sub-folders get their own card that links into
    a child index (or the folder itself).

    De-duplicates text/markdown sources when a matching ``.html`` companion
    exists (UI-3 writes those). The source files stay on disk for
    scripting consumers; the index points the human at the HTML view.
    """
    raw_files: List[str] = []
    subs: List[str] = []
    for entry in sorted(os.listdir(outdir)):
        full = os.path.join(outdir, entry)
        if _hidden(entry):
            continue
        if os.path.isdir(full):
            subs.append(entry)
        elif os.path.isfile(full):
            raw_files.append(entry)

    html_stems = {
        os.path.splitext(n)[0] for n in raw_files if n.lower().endswith(".html")
    }
    files: List[str] = []
    for name in raw_files:
        stem, ext = os.path.splitext(name)
        # Sources that have an HTML companion are hidden — the HTML view
        # surfaces instead. Applies to text / markdown / CSV / JSON.
        if ext.lower() in (".txt", ".md", ".csv", ".json") and stem in html_stems:
            continue
        files.append(name)
    return files, subs, 0


def _classify(files: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Split files into (deliverables, data, other)."""
    deliverables: List[str] = []
    data: List[str] = []
    other: List[str] = []
    for name in files:
        ext = os.path.splitext(name)[1].lower()
        if name in _DELIVERABLE_NAMES:
            deliverables.append(name)
        elif ext in (".html", ".pdf"):
            deliverables.append(name)
        elif ext in (".csv", ".json"):
            data.append(name)
        else:
            other.append(name)
    return deliverables, data, other


# ── Rendering ──────────────────────────────────────────────────────────────

def _render_card(outdir: str, name: str, is_folder: bool = False) -> str:
    """One tile: pill label, filename, description, size+mtime footnote."""
    full = os.path.join(outdir, name)
    href = html.escape(name + ("/" if is_folder else ""))

    if is_folder:
        kind_label = "Folder"
        kind_class = "folder"
        desc = f"Sub-folder ({sum(1 for _ in os.listdir(full) if not _hidden(_))} entries)"
        meta = ""
    else:
        kind_label = _kind(name)
        kind_class = kind_label.lower()
        desc = _describe(name)
        try:
            st = os.stat(full)
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            meta = f"{_fmt_size(st.st_size)} · {mtime.strftime('%Y-%m-%d %H:%M UTC')}"
        except OSError:
            meta = ""

    return (
        f'<a class="card" href="{href}">'
        f'<span class="kind {html.escape(kind_class)}">{html.escape(kind_label)}</span>'
        f'<h3>{html.escape(name)}</h3>'
        f'<p class="desc">{html.escape(desc)}</p>'
        + (f'<div class="meta">{html.escape(meta)}</div>' if meta else '')
        + '</a>'
    )


def _render_section(title: str, hint: str, cards: List[str]) -> str:
    if not cards:
        return f'<h2>{html.escape(title)}</h2><p class="empty">None</p>'
    return (
        f'<h2>{html.escape(title)}</h2>'
        f'<p class="section-hint">{html.escape(hint)}</p>'
        f'<div class="grid">{"".join(cards)}</div>'
    )


# ── Public API ─────────────────────────────────────────────────────────────

def build_output_index(
    outdir: str,
    title: Optional[str] = None,
) -> str:
    """Write ``index.html`` at the top of ``outdir``. Returns the path.

    Safe to call multiple times — overwrites the previous index. If ``outdir``
    doesn't exist or is empty, still writes an index (with "None" placeholders)
    so analysts don't get 404s when opening a partially-completed run.
    """
    os.makedirs(outdir, exist_ok=True)
    files, subs, _ = _scan(outdir)
    deliverables, data, other = _classify(files)

    deliverable_cards = [_render_card(outdir, n) for n in deliverables]
    data_cards = [_render_card(outdir, n) for n in data]
    folder_cards = [_render_card(outdir, n, is_folder=True) for n in subs]
    other_cards = [_render_card(outdir, n) for n in other]

    from ..ui._ui_kit import shell
    folder_name = os.path.basename(os.path.abspath(outdir)) or outdir
    t = title or f"Output — {folder_name}"
    subtitle = (
        f"{len(files)} file{'s' if len(files) != 1 else ''} · "
        f"{len(subs)} sub-folder{'s' if len(subs) != 1 else ''}"
    )

    body_parts = [
        _render_section(
            "Deliverables",
            "Partner-facing HTML / Excel — start here.",
            deliverable_cards,
        ),
        _render_section(
            "Data tables",
            "Machine-readable outputs (CSV, JSON) for scripting or further analysis.",
            data_cards,
        ),
    ]
    if folder_cards:
        body_parts.append(_render_section(
            "Sub-folders",
            "Nested output directories. Click to open; a child index is "
            "auto-generated inside each folder.",
            folder_cards,
        ))
    if other_cards:
        body_parts.append(_render_section(
            "Everything else",
            "Config files, databases, manifests.",
            other_cards,
        ))
    body = "\n".join(body_parts)

    html_doc = shell(
        body=body, title=t, subtitle=subtitle, extra_css=_EXTRA_CSS,
    )

    out_path = os.path.join(outdir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out_path


def build_indices_recursive(outdir: str, title: Optional[str] = None) -> List[str]:
    """Build index.html at ``outdir`` and in every non-hidden sub-folder.

    Returns the list of paths written. Sub-folders get their own index
    so clicking into one from the top navigates somewhere useful.
    """
    written: List[str] = [build_output_index(outdir, title=title)]
    for entry in os.listdir(outdir):
        full = os.path.join(outdir, entry)
        if _hidden(entry) or not os.path.isdir(full):
            continue
        written.append(build_output_index(full))
    return written
