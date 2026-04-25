"""Shared components for the web-deployment UI layer.

Consistent typography, spacing, breadcrumbs, sortable tables, loading
spinners, and responsive wrappers. Consumed by ``dashboard_page``,
``exports_index_page``, ``data_refresh_page``, and any future
web-deployment-specific page.

**Does NOT touch** the 200+ existing non-web page renderers — those
pages are shipped and working; this module is additive for new web
UX surfaces only.

Public API:
    web_styles()           -> str   # one <style> block; include once per page
    page_header(...)       -> str   # h1 + subtitle + breadcrumbs
    breadcrumbs([...])     -> str   # trail standalone
    section_card(title, body, *, pad=True) -> str
    sortable_table(headers, rows, *, id=None) -> str
    loading_spinner(id)    -> str   # hidden by default; JS toggles display
    responsive_container(body) -> str   # max-width wrapper with mobile padding

Every component produces self-contained HTML + inline CSS classes
that the one-time ``web_styles()`` block defines. No external assets,
no framework deps.
"""
from __future__ import annotations

import html as _html
from typing import Iterable, List, Optional, Tuple


# ── Single style block ────────────────────────────────────────────────

def web_styles() -> str:
    """One-time <style> block. Include at the start of any web page body."""
    return """<style>
/* ── Web UI baseline: typography, spacing, responsive ─────────── */
.wc-container { max-width: 1100px; margin: 0 auto; padding: 24px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Oxygen, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
    color: #111827; line-height: 1.5; font-size: 14px; }
.wc-container h1 { font-size: 24px; margin: 0; font-weight: 600;
    letter-spacing: -0.01em; color: #0f172a; }
.wc-container h2 { font-size: 16px; margin: 24px 0 12px; font-weight: 600;
    color: #1f2937; letter-spacing: -0.005em; }
.wc-container h3 { font-size: 13px; margin: 16px 0 8px; font-weight: 600;
    color: #374151; text-transform: uppercase; letter-spacing: 0.04em; }
.wc-container p  { margin: 4px 0; color: #4b5563; }
.wc-container code { background:#f3f4f6; padding:2px 6px; border-radius:3px;
    font-family: "SF Mono", Monaco, Consolas, monospace; font-size: 12px; }

/* Breadcrumb trail */
.wc-breadcrumbs { font-size: 12px; color: #6b7280; margin-bottom: 12px;
    letter-spacing: 0.01em; }
.wc-breadcrumbs a { color: #6b7280; text-decoration: none; }
.wc-breadcrumbs a:hover { color: #1f2937; text-decoration: underline; }
.wc-breadcrumbs .sep { margin: 0 6px; color: #d1d5db; }

/* Section card */
.wc-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
    margin: 16px 0; overflow: hidden; }
.wc-card-head { padding: 12px 16px; border-bottom: 1px solid #f3f4f6;
    background: #fafbfc; font-size: 13px; font-weight: 600; color: #1f2937;
    display: flex; align-items: center; justify-content: space-between; }
.wc-card-body { padding: 16px; }
.wc-card-body.wc-no-pad { padding: 0; }

/* Sortable table */
.wc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.wc-table thead th { padding: 10px 12px; text-align: left; font-weight: 600;
    color: #374151; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
    cursor: pointer; user-select: none; white-space: nowrap; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.03em; }
.wc-table thead th:hover { background: #f3f4f6; }
.wc-table thead th.wc-sorted-asc::after  { content: " ↑"; color: #1F4E78; }
.wc-table thead th.wc-sorted-desc::after { content: " ↓"; color: #1F4E78; }
.wc-table tbody td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6;
    vertical-align: top; color: #1f2937; }
.wc-table tbody tr:hover { background: #fafbfc; }
.wc-table tbody tr:last-child td { border-bottom: none; }

/* Filter input above sortable tables */
.wc-filter { display: block; width: 100%; max-width: 320px;
    padding: 6px 10px; margin: 0 0 8px;
    font-size: 13px; font-family: inherit;
    border: 1px solid #e5e7eb; border-radius: 4px;
    background: #fff; color: #111827;
    transition: border-color 0.1s, box-shadow 0.1s; }
.wc-filter:focus { outline: none; border-color: #1F4E78;
    box-shadow: 0 0 0 2px rgba(31, 78, 120, 0.15); }
.wc-table tbody tr.wc-filter-hide { display: none; }

/* Command palette (Cmd-K / Ctrl-K) */
.wc-cmdk-backdrop { position: fixed; inset: 0; z-index: 9999;
    background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(2px);
    display: none; align-items: flex-start; justify-content: center;
    padding-top: 12vh; }
.wc-cmdk-backdrop.wc-cmdk-open { display: flex; }
.wc-cmdk-backdrop[aria-hidden="true"] { display: none; }
.wc-cmdk-card { width: 92%; max-width: 560px; background: #fff;
    border: 1px solid #e5e7eb; border-radius: 10px;
    box-shadow: 0 20px 50px -10px rgba(0,0,0,0.35),
                0 8px 20px -8px rgba(0,0,0,0.2);
    overflow: hidden; font-family: inherit; }
.wc-cmdk-input-wrap { display: flex; align-items: center; gap: 10px;
    padding: 14px 16px; border-bottom: 1px solid #f3f4f6; }
.wc-cmdk-input { flex: 1; border: none; outline: none;
    font-size: 15px; font-family: inherit; color: #111827;
    background: transparent; padding: 0; }
.wc-cmdk-input::placeholder { color: #9ca3af; }
.wc-cmdk-hint { font-size: 10px; padding: 2px 6px;
    background: #f3f4f6; color: #6b7280; border-radius: 3px;
    font-family: monospace; border: 1px solid #e5e7eb; }
.wc-cmdk-results { max-height: 50vh; overflow-y: auto; padding: 4px 0; }
.wc-cmdk-row { display: flex; align-items: center; gap: 12px;
    padding: 8px 16px; color: #111827; text-decoration: none;
    font-size: 13px; border-left: 2px solid transparent; }
.wc-cmdk-row:hover, .wc-cmdk-row.wc-cmdk-active {
    background: #f0f6fc; border-left-color: #1F4E78; }
.wc-cmdk-id { font-family: monospace; color: #1F4E78;
    font-size: 11px; min-width: 90px; flex-shrink: 0;
    text-transform: uppercase; letter-spacing: 0.03em; }
.wc-cmdk-name { flex: 1; color: #1f2937; }
.wc-cmdk-badge { font-size: 10px; padding: 1px 6px;
    background: #fef3c7; color: #92400e; border-radius: 3px; }
.wc-cmdk-empty { padding: 20px 16px; text-align: center;
    color: #9ca3af; font-size: 13px; }
.wc-cmdk-section { padding: 6px 16px 2px;
    font-size: 10px; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #6b7280;
    border-top: 1px solid #f3f4f6; background: #fafbfc; }
.wc-cmdk-section:first-child { border-top: 0; }
.wc-cmdk-footer { display: flex; gap: 16px; padding: 8px 16px;
    border-top: 1px solid #f3f4f6; font-size: 11px; color: #6b7280;
    background: #fafbfc; }
.wc-cmdk-footer kbd { font-family: monospace; padding: 1px 5px;
    background: #fff; color: #374151; border: 1px solid #e5e7eb;
    border-radius: 3px; font-size: 10px; margin: 0 2px; }

/* Loading spinner (CSS-only; JS toggles display) */
.wc-spinner { display: none; width: 16px; height: 16px; border: 2px solid #e5e7eb;
    border-top-color: #1F4E78; border-radius: 50%;
    animation: wc-spin 0.7s linear infinite;
    vertical-align: middle; margin-right: 6px; }
.wc-spinner.wc-on { display: inline-block; }
@keyframes wc-spin { to { transform: rotate(360deg); } }

/* Buttons — match export menu styling */
.wc-btn { display: inline-block; padding: 8px 16px; border-radius: 6px;
    font-size: 13px; font-weight: 500; text-decoration: none;
    cursor: pointer; border: 1px solid #1F4E78; transition: background 0.1s; }
.wc-btn-primary { background: #1F4E78; color: #fff; }
.wc-btn-primary:hover { background: #1a3f61; }
.wc-btn-secondary { background: #fff; color: #1F4E78; }
.wc-btn-secondary:hover { background: #eff4f8; }

/* Responsive — mobile/tablet breakpoints */
@media (max-width: 768px) {
    .wc-container { padding: 16px 12px; font-size: 13px; }
    .wc-container h1 { font-size: 20px; }
    .wc-container h2 { font-size: 15px; }
    .wc-table { font-size: 12px; }
    .wc-table thead th, .wc-table tbody td { padding: 8px 6px; }
    .wc-card-body { padding: 12px; }
    /* Hide decorative columns on narrow screens */
    .wc-hide-sm { display: none !important; }
}
@media (max-width: 480px) {
    .wc-container { padding: 12px 8px; }
    .wc-hide-xs { display: none !important; }
}
</style>"""


# ── Components ────────────────────────────────────────────────────────

def breadcrumbs(items: Iterable[Tuple[str, Optional[str]]]) -> str:
    """Trail of (label, href) pairs. Last item has href=None (current page)."""
    parts: List[str] = []
    items = list(items)
    for i, (label, href) in enumerate(items):
        label_esc = _html.escape(label)
        if href and i < len(items) - 1:
            parts.append(f'<a href="{_html.escape(href)}">{label_esc}</a>')
        else:
            parts.append(f'<span>{label_esc}</span>')
    return f'<nav class="wc-breadcrumbs">{("<span class=\"sep\">/</span>").join(parts)}</nav>'


def page_header(title: str, *, subtitle: Optional[str] = None,
                crumbs: Optional[Iterable[Tuple[str, Optional[str]]]] = None) -> str:
    bc = breadcrumbs(crumbs) if crumbs else ""
    sub = (f'<p style="color:#6b7280;font-size:13px;margin:6px 0 0;">'
           f'{_html.escape(subtitle)}</p>') if subtitle else ""
    return (
        f'<header style="margin:4px 0 20px;">'
        f'{bc}<h1>{_html.escape(title)}</h1>{sub}</header>'
    )


def section_card(title: str, body_html: str, *, pad: bool = True,
                 actions_html: str = "") -> str:
    """Panel: header strip + body. `actions_html` floats on the header right."""
    pad_class = "" if pad else " wc-no-pad"
    return (
        f'<section class="wc-card"><div class="wc-card-head">'
        f'<span>{_html.escape(title)}</span>'
        f'<span>{actions_html}</span>'
        f'</div>'
        f'<div class="wc-card-body{pad_class}">{body_html}</div></section>'
    )


def sortable_table(
    headers: List[str],
    rows: List[List[str]],
    *,
    id: Optional[str] = None,
    hide_columns_sm: Optional[List[int]] = None,
    filterable: bool = False,
    filter_placeholder: str = "Filter…",
) -> str:
    """Client-side sortable (and optionally filterable) table.

    Args:
        headers: Column labels.
        rows:    Each inner list is one row of pre-formatted cells (can
                 contain HTML — caller is responsible for escaping).
        id:      Optional anchor id (also used to scope the filter input).
        hide_columns_sm: Zero-indexed columns to hide on mobile.
        filterable: When True, prepends a text input that filters rows
                 by case-insensitive substring match across every cell.
                 Requires sortable_table_js() in the page body.
        filter_placeholder: Placeholder text for the filter input.
    """
    hide_set = set(hide_columns_sm or [])
    th_cells = []
    for i, h in enumerate(headers):
        cls = "wc-hide-sm" if i in hide_set else ""
        th_cells.append(f'<th class="{cls}" data-col="{i}">{_html.escape(h)}</th>')
    td_rows = []
    for row in rows:
        tds = []
        for i, cell in enumerate(row):
            cls = "wc-hide-sm" if i in hide_set else ""
            tds.append(f'<td class="{cls}">{cell}</td>')
        td_rows.append(f'<tr>{"".join(tds)}</tr>')
    table_id_attr = f' id="{_html.escape(id)}"' if id else ""
    table_html = (
        f'<table class="wc-table wc-sortable"{table_id_attr}>'
        f'<thead><tr>{"".join(th_cells)}</tr></thead>'
        f'<tbody>{"".join(td_rows)}</tbody></table>'
    )
    if not filterable:
        return table_html
    # Filter input — paired to the table by `data-filter-for` so the
    # JS can find it without needing global state. Uses the table id
    # as the binding key when present; falls back to a generated id.
    filter_target = id or f"wc-tbl-{abs(hash(tuple(headers))) % (10**8)}"
    if not id:
        table_html = table_html.replace(
            '<table class="wc-table wc-sortable"',
            f'<table class="wc-table wc-sortable" id="{filter_target}"',
            1,
        )
    return (
        f'<input type="search" class="wc-filter" '
        f'data-filter-for="{_html.escape(filter_target)}" '
        f'placeholder="{_html.escape(filter_placeholder)}" '
        f'aria-label="{_html.escape(filter_placeholder)}">'
        + table_html
    )


def loading_spinner(id: str) -> str:
    return (
        f'<span id="{_html.escape(id)}" class="wc-spinner" '
        f'role="status" aria-live="polite"></span>'
    )


def responsive_container(body_html: str) -> str:
    return f'<div class="wc-container">{body_html}</div>'


def command_palette() -> str:
    """Hidden modal overlay — opens on Cmd-K / Ctrl-K.

    Searches deals + HCRIS hospitals via ``/api/deals/search?q=<query>``,
    renders results as an arrow-key-navigable list, and redirects to
    ``/deal/<deal_id>`` on Enter. Esc closes. Standard SaaS pattern
    (Linear, Notion, GitHub Vercel) so partners don't need to be
    taught it.

    Include once per page alongside ``command_palette_js()``.
    """
    return r"""<div id="wc-cmdk" class="wc-cmdk-backdrop" role="dialog"
  aria-label="Jump to deal or hospital" aria-hidden="true">
  <div class="wc-cmdk-card" role="document">
    <div class="wc-cmdk-input-wrap">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
           stroke="#6b7280" stroke-width="2" aria-hidden="true"
           style="flex-shrink:0;">
        <circle cx="11" cy="11" r="7"></circle>
        <path d="m21 21-4.3-4.3"></path>
      </svg>
      <input type="search" id="wc-cmdk-input" class="wc-cmdk-input"
             placeholder="Jump to a deal or hospital — type a name or ID"
             autocomplete="off" spellcheck="false">
      <kbd class="wc-cmdk-hint">Esc</kbd>
    </div>
    <div id="wc-cmdk-results" class="wc-cmdk-results"></div>
    <div class="wc-cmdk-footer">
      <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
      <span><kbd>⏎</kbd> open</span>
      <span><kbd>esc</kbd> close</span>
    </div>
  </div>
</div>"""


def command_palette_js(
    *, static_commands: Optional[List[Tuple[str, str, str]]] = None,
) -> str:
    """JS for the Cmd-K command palette. Include once per page.

    Depends on:
      - ``#wc-cmdk`` modal markup (from ``command_palette()``)
      - ``/api/deals/search?q=<term>&limit=10`` endpoint

    Args:
        static_commands: Optional list of ``(category, label, href)``
            tuples baked into the palette as navigation / action
            commands. Rendered alongside the live deal-search results,
            filtered client-side by substring match on category+label.
            Example: ``[("Go", "Alerts", "/alerts"),
                        ("Run", "Thesis Pipeline", "/diligence/thesis-pipeline")]``
            When None, the palette behaves exactly like the deal-only
            version (backward-compat).
    """
    import json as _json
    commands_js_lit = _json.dumps(
        [{"category": c, "label": l, "href": h}
         for c, l, h in (static_commands or [])]
    )
    return r"""<script>
(function() {
    const modal = document.getElementById('wc-cmdk');
    if (!modal) return;
    const input = document.getElementById('wc-cmdk-input');
    const list = document.getElementById('wc-cmdk-results');
    // Baked-in commands (navigation + curated analyses). Filtered
    // client-side by substring match; no server round-trip.
    const STATIC_COMMANDS = """ + commands_js_lit + r""";
    // Unified flat result array used by keyboard nav. Each entry has
    // {type: 'deal'|'command', href, ... (type-specific fields)}.
    let results = [];
    let activeIdx = -1;
    let timer = null;

    function open() {
        modal.setAttribute('aria-hidden', 'false');
        modal.classList.add('wc-cmdk-open');
        setTimeout(function() { input.focus(); input.select(); }, 10);
    }
    function close() {
        modal.setAttribute('aria-hidden', 'true');
        modal.classList.remove('wc-cmdk-open');
        input.value = '';
        results = []; activeIdx = -1;
        render();
    }
    function escape(s) {
        return String(s || '').replace(/[&<>"']/g, function(c) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
        });
    }
    function matchCommands(q) {
        if (!q) return [];
        const needle = q.toLowerCase();
        return STATIC_COMMANDS
            .filter(function(c) {
                return (c.label.toLowerCase().indexOf(needle) !== -1
                     || c.category.toLowerCase().indexOf(needle) !== -1);
            })
            .map(function(c) {
                return {type: 'command', category: c.category,
                        label: c.label, href: c.href};
            });
    }
    function renderRow(r, i) {
        const active = (i === activeIdx) ? ' wc-cmdk-active' : '';
        if (r.type === 'command') {
            return '<a href="' + escape(r.href) + '" '
                 + 'class="wc-cmdk-row' + active + '">'
                 + '<span class="wc-cmdk-id">' + escape(r.category) + '</span>'
                 + '<span class="wc-cmdk-name">' + escape(r.label) + '</span>'
                 + '</a>';
        }
        // deal
        const archived = r.archived
            ? ' <span class="wc-cmdk-badge">archived</span>' : '';
        return '<a href="/deal/' + encodeURIComponent(r.deal_id) + '" '
             + 'class="wc-cmdk-row' + active + '">'
             + '<span class="wc-cmdk-id">' + escape(r.deal_id) + '</span>'
             + '<span class="wc-cmdk-name">' + escape(r.name || '') + '</span>'
             + archived
             + '</a>';
    }
    function render() {
        if (!results.length) {
            list.innerHTML = input.value.trim()
                ? '<div class="wc-cmdk-empty">No matches.</div>'
                : '<div class="wc-cmdk-empty">Start typing to search deals, pages, and actions.</div>';
            return;
        }
        // Group by category: commands first (partner often wants to
        // navigate), then deals. Insert a section label before the
        // first entry of each group.
        let lastGroup = null;
        const out = [];
        results.forEach(function(r, i) {
            const group = r.type === 'command' ? r.category : 'Deals & hospitals';
            if (group !== lastGroup) {
                out.push('<div class="wc-cmdk-section">' + escape(group) + '</div>');
                lastGroup = group;
            }
            out.push(renderRow(r, i));
        });
        list.innerHTML = out.join('');
    }
    function navigate(r) {
        if (r.type === 'command') {
            window.location = r.href;
        } else {
            window.location = '/deal/' + encodeURIComponent(r.deal_id);
        }
    }
    function fetchResults(q) {
        if (!q) {
            results = [];
            activeIdx = -1;
            render();
            return;
        }
        // Static commands are immediate; show them right away while
        // the deal search is in flight.
        const commands = matchCommands(q);
        results = commands.slice();
        activeIdx = results.length ? 0 : -1;
        render();

        fetch('/api/deals/search?q=' + encodeURIComponent(q) + '&limit=10',
              {credentials: 'same-origin'})
            .then(function(r) { return r.json(); })
            .then(function(j) {
                const deals = ((j && j.results) || []).map(function(d) {
                    return {type: 'deal', deal_id: d.deal_id,
                            name: d.name, archived: d.archived};
                });
                results = commands.concat(deals);
                if (activeIdx < 0 && results.length) activeIdx = 0;
                if (activeIdx >= results.length) {
                    activeIdx = results.length - 1;
                }
                render();
            })
            .catch(function() {
                // Silently drop deal results on search failure —
                // static commands are still usable.
            });
    }

    input.addEventListener('input', function() {
        clearTimeout(timer);
        timer = setTimeout(function() {
            fetchResults(input.value.trim());
        }, 120);
    });

    modal.addEventListener('click', function(e) {
        if (e.target === modal) close();
    });

    input.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowDown' && results.length) {
            e.preventDefault();
            activeIdx = Math.min(results.length - 1, activeIdx + 1);
            render();
        } else if (e.key === 'ArrowUp' && results.length) {
            e.preventDefault();
            activeIdx = Math.max(0, activeIdx - 1);
            render();
        } else if (e.key === 'Enter' && activeIdx >= 0 && activeIdx < results.length) {
            e.preventDefault();
            navigate(results[activeIdx]);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            close();
        }
    });

    // Global keyboard shortcut: Cmd-K / Ctrl-K
    document.addEventListener('keydown', function(e) {
        if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            if (modal.getAttribute('aria-hidden') === 'false') close();
            else open();
        }
    });
})();
</script>"""


# ── Sortable-table JS ─────────────────────────────────────────────────

def sortable_table_js() -> str:
    """Inline JS that wires up every .wc-sortable table on the page.

    Also wires `<input class="wc-filter" data-filter-for="<table-id>">`
    elements: each keystroke applies a case-insensitive substring filter
    across every cell of the linked table and toggles the
    `.wc-filter-hide` class on non-matching rows.
    """
    return r"""<script>
(function() {
    function sortTable(table, colIdx, asc) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort(function(a, b) {
            const av = (a.children[colIdx] || {}).textContent || '';
            const bv = (b.children[colIdx] || {}).textContent || '';
            const an = parseFloat(av.replace(/[,%$]/g, ''));
            const bn = parseFloat(bv.replace(/[,%$]/g, ''));
            if (!isNaN(an) && !isNaN(bn)) {
                return asc ? an - bn : bn - an;
            }
            return asc ? av.localeCompare(bv) : bv.localeCompare(av);
        });
        rows.forEach(r => tbody.appendChild(r));
    }
    document.querySelectorAll('table.wc-sortable').forEach(function(table) {
        table.querySelectorAll('thead th').forEach(function(th, colIdx) {
            th.addEventListener('click', function() {
                const wasAsc = th.classList.contains('wc-sorted-asc');
                // Clear sort markers on siblings
                th.parentNode.querySelectorAll('th').forEach(function(other) {
                    other.classList.remove('wc-sorted-asc', 'wc-sorted-desc');
                });
                const nextAsc = !wasAsc;
                th.classList.add(nextAsc ? 'wc-sorted-asc' : 'wc-sorted-desc');
                sortTable(table, colIdx, nextAsc);
            });
        });
    });

    // Filter inputs — debounced on input. Empty query reveals every row.
    function applyFilter(table, query) {
        const q = (query || '').trim().toLowerCase();
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        tbody.querySelectorAll('tr').forEach(function(tr) {
            if (!q) { tr.classList.remove('wc-filter-hide'); return; }
            const text = (tr.textContent || '').toLowerCase();
            tr.classList.toggle('wc-filter-hide', text.indexOf(q) === -1);
        });
    }
    document.querySelectorAll('input.wc-filter').forEach(function(input) {
        const targetId = input.getAttribute('data-filter-for');
        if (!targetId) return;
        const table = document.getElementById(targetId);
        if (!table) return;
        let timer = null;
        input.addEventListener('input', function() {
            clearTimeout(timer);
            timer = setTimeout(function() {
                applyFilter(table, input.value);
            }, 80);
        });
        // Esc clears + blurs the filter
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                input.value = '';
                applyFilter(table, '');
                input.blur();
            }
        });
    });

    // "/" keyboard shortcut focuses the first filter on the page —
    // the SaaS standard (GitHub, Linear, Notion). No-op when the user
    // is already typing in an input/textarea/contenteditable.
    document.addEventListener('keydown', function(e) {
        if (e.key !== '/') return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        const t = e.target;
        if (!t) return;
        const tag = (t.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || t.isContentEditable) return;
        const first = document.querySelector('input.wc-filter');
        if (first) {
            e.preventDefault();
            first.focus();
            first.select();
        }
    });
})();
</script>"""


def spinner_js() -> str:
    """Helpers to toggle a spinner by id. Used by pages with async fetches."""
    return r"""<script>
window.wcSpinner = {
    show: function(id) { const el = document.getElementById(id); if (el) el.classList.add('wc-on'); },
    hide: function(id) { const el = document.getElementById(id); if (el) el.classList.remove('wc-on'); }
};
</script>"""
