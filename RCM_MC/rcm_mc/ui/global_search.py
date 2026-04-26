"""Global search — one bar that searches everything.

The directive: hospitals, metrics, analyses, notes, exports — all
in one search. Power users hit ``/`` (already wired by ``nav.py``)
to focus the search; results show a ranked dropdown with category
chips and one-click navigation.

Architecture:

  • Each searchable source registers a function returning
    ``(label, sublabel, url, category)`` tuples.
  • ``search(store, query)`` runs every source in parallel
    (well, sequentially — the full set takes <50ms on a typical
    portfolio so threads add nothing), scores each match via
    a simple substring-rank rule, and returns a flat ranked list.
  • Sources are defensive — a missing table or bad data doesn't
    break the search, just drops that source's results.

Scoring:

  • Exact label match → 100
  • Label starts with query → 80
  • Label contains query → 50
  • Sublabel contains query → 25
  • Category-specific boosts: active deals +20, recent
    analyses +10, current metrics +5.

Sources covered out of the box:

  • Deals (PortfolioStore.list_deals)
  • Analysis packets (analysis_store.list_packets)
  • Metric glossary entries
  • Static pages (dashboard, models, catalog, refresh, etc.)

Public API::

    from rcm_mc.ui.global_search import (
        SearchResult,
        search,
        render_search_bar,
        render_search_results,
    )
"""
from __future__ import annotations

import html as _html
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# Result categories — used for chip color coding + category
# weighting.
CATEGORIES = (
    "deal", "hospital", "metric",
    "analysis", "note", "page", "export",
)

CATEGORY_LABELS = {
    "deal":    "Deal",
    "hospital": "Hospital",
    "metric":  "Metric",
    "analysis": "Analysis",
    "note":    "Note",
    "page":    "Page",
    "export":  "Export",
}

CATEGORY_BOOSTS = {
    "deal":    20,   # active partner-relevant
    "metric":  5,
    "analysis": 10,
    "page":    0,
    "note":    8,
    "hospital": 5,
    "export":  0,
}


# Static registry of platform pages — partner can search 'data'
# or 'model' to navigate without remembering the URL.
PLATFORM_PAGES = [
    ("Morning view dashboard", "Hero strip + top opportunities + alerts",
     "/?v3=1", "page"),
    ("Data catalog", "Live SQL inventory of every public-data source",
     "/data/catalog", "page"),
    ("Data refresh", "Background-job loaders for CMS / Census / CDC / APCD",
     "/data/refresh", "page"),
    ("Model quality dashboard", "CV R² + MAE + CI calibration per predictor",
     "/models/quality", "page"),
    ("Feature importance", "Per-model SVG bar charts of |coefficient|",
     "/models/importance", "page"),
    ("Exports index", "Generated reports + CSVs",
     "/exports", "page"),
    ("Legacy dashboard", "Original Bloomberg-style layout",
     "/", "page"),
]


@dataclass
class SearchResult:
    """One result returned by global search."""
    label: str
    sublabel: str
    url: str
    category: str
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "sublabel": self.sublabel,
            "url": self.url,
            "category": self.category,
            "score": self.score,
        }


# ── Scoring ─────────────────────────────────────────────────

def _score(
    query: str, label: str, sublabel: str,
    category: str,
) -> int:
    """Return a 0-200 score for one (query, candidate) pair.

    Returns 0 when no match — caller filters those out.
    """
    if not query:
        return 0
    q = query.strip().lower()
    if not q:
        return 0
    label_lc = (label or "").lower()
    sub_lc = (sublabel or "").lower()
    score = 0
    if label_lc == q:
        score = 100
    elif label_lc.startswith(q):
        score = 80
    elif q in label_lc:
        score = 50
    elif q in sub_lc:
        score = 25
    if score > 0:
        score += CATEGORY_BOOSTS.get(category, 0)
    return score


# ── Source providers ────────────────────────────────────────

def _deals_source(
    store: Any, query: str,
) -> List[SearchResult]:
    """Search deals via PortfolioStore.list_deals."""
    out: List[SearchResult] = []
    try:
        deals = store.list_deals(include_archived=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "deals source failed: %s", exc)
        return out
    try:
        rows = (deals.to_dict("records")
                if hasattr(deals, "to_dict") else deals)
    except Exception:  # noqa: BLE001
        return out
    for r in rows:
        deal_id = (r.get("deal_id") or r.get("id")
                   or "").strip()
        if not deal_id:
            continue
        deal_name = (r.get("name")
                     or r.get("deal_name")
                     or deal_id)
        sub_parts = []
        if r.get("state"):
            sub_parts.append(str(r["state"]))
        if r.get("fund"):
            sub_parts.append(str(r["fund"]))
        if r.get("archived"):
            sub_parts.append("archived")
        score = _score(query, deal_name,
                       " ".join(sub_parts), "deal")
        if score == 0:
            score = _score(
                query, deal_id, "", "deal")
        if score > 0:
            out.append(SearchResult(
                label=str(deal_name),
                sublabel=" · ".join(sub_parts),
                url=f"/deal/{deal_id}/profile",
                category="deal",
                score=score))
    return out


def _packets_source(
    store: Any, query: str,
) -> List[SearchResult]:
    """Search analysis packets."""
    out: List[SearchResult] = []
    try:
        from ..analysis.analysis_store import list_packets
        rows = list_packets(store) or []
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "packets source failed: %s", exc)
        return out
    seen = set()
    for r in rows:
        deal_id = r.get("deal_id") or ""
        if not deal_id or deal_id in seen:
            continue
        seen.add(deal_id)
        ts = r.get("created_at") or r.get("timestamp") or ""
        score = _score(
            query, deal_id, "analysis packet", "analysis")
        if score > 0:
            out.append(SearchResult(
                label=f"Analysis: {deal_id}",
                sublabel=f"packet · {ts[:10]}",
                url=f"/deal/{deal_id}/profile",
                category="analysis",
                score=score))
    return out


def _metrics_source(
    store: Any, query: str,
) -> List[SearchResult]:
    """Search the metric glossary."""
    out: List[SearchResult] = []
    try:
        from .metric_glossary import (
            list_metrics, get_metric_definition,
        )
    except Exception:  # noqa: BLE001
        return out
    for key in list_metrics():
        d = get_metric_definition(key)
        if d is None:
            continue
        score = _score(
            query, d.label, d.definition, "metric")
        if score == 0:
            score = _score(query, key, "", "metric")
        if score > 0:
            out.append(SearchResult(
                label=d.label,
                sublabel=d.definition[:80] + (
                    "…" if len(d.definition) > 80 else ""),
                url=f"/data/catalog#{key}",
                category="metric",
                score=score))
    return out


def _pages_source(
    store: Any, query: str,
) -> List[SearchResult]:
    """Search the static page registry."""
    out: List[SearchResult] = []
    for label, sub, url, category in PLATFORM_PAGES:
        score = _score(query, label, sub, category)
        if score > 0:
            out.append(SearchResult(
                label=label, sublabel=sub,
                url=url, category=category,
                score=score))
    return out


# Default source set. Callers can swap or extend.
DEFAULT_SOURCES: List[
    Callable[[Any, str], List[SearchResult]]] = [
    _deals_source,
    _packets_source,
    _metrics_source,
    _pages_source,
]


def search(
    store: Any,
    query: str,
    *,
    limit: int = 25,
    sources: Optional[
        List[Callable[[Any, str],
                      List[SearchResult]]]] = None,
) -> List[SearchResult]:
    """Run global search across all sources.

    Returns: ranked list capped at ``limit``. Empty query
    returns []. Each source is wrapped in try/except — a
    missing table doesn't break the others.
    """
    if not query or not query.strip():
        return []
    out: List[SearchResult] = []
    for src in (sources or DEFAULT_SOURCES):
        try:
            out.extend(src(store, query))
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "source %s failed: %s",
                src.__name__, exc)
            continue
    out.sort(key=lambda r: -r.score)
    return out[:limit]


# ── UI rendering ────────────────────────────────────────────

# Inline JS — debounced fetch to /api/search, render dropdown.
_SEARCH_JS = """
<script>
(function() {
  var input = document.getElementById("global-search-input");
  if (!input) return;
  var dropdown = document.getElementById(
    "global-search-dropdown");
  var timer = null;
  function hide() {
    if (dropdown) dropdown.style.display = "none";
  }
  function show() {
    if (dropdown) dropdown.style.display = "block";
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({"&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#39;"})[c];
    });
  }
  function fetchAndRender() {
    var q = input.value.trim();
    if (!q) { hide(); return; }
    fetch("/api/global-search?q=" + encodeURIComponent(q))
      .then(function(r) { return r.json(); })
      .then(function(payload) {
        var rows = (payload && payload.results) || [];
        if (!rows.length) {
          dropdown.innerHTML =
            '<div style="padding:14px 16px;' +
            'color:var(--faint);font-size:13px;">' +
            'No matches for ' +
            escapeHtml('"' + q + '"') + '.</div>';
          show();
          return;
        }
        var html = rows.map(function(r) {
          return (
            '<a href="' + encodeURI(r.url) + '" ' +
            'style="display:block;padding:10px 14px;' +
            'border-bottom:1px solid var(--border);' +
            'color:var(--ink);text-decoration:none;' +
            'font-size:13px;">' +
            '<span style="display:inline-block;' +
            'padding:1px 8px;border-radius:4px;' +
            'background:var(--border);color:var(--faint);' +
            'font-size:10px;text-transform:uppercase;' +
            'letter-spacing:0.05em;margin-right:8px;">' +
            escapeHtml(r.category) + '</span>' +
            escapeHtml(r.label) +
            (r.sublabel ?
              '<div style="font-size:11px;' +
              'color:var(--faint);margin-top:2px;' +
              'margin-left:0;">' +
              escapeHtml(r.sublabel) + '</div>' : '') +
            '</a>');
        }).join("");
        dropdown.innerHTML = html;
        show();
      })
      .catch(function() { hide(); });
  }
  input.addEventListener("input", function() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(fetchAndRender, 180);
  });
  input.addEventListener("focus", function() {
    if (input.value.trim()) fetchAndRender();
  });
  document.addEventListener("click", function(e) {
    if (!dropdown) return;
    if (e.target === input ||
        dropdown.contains(e.target)) return;
    hide();
  });
  input.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      input.value = "";
      hide();
      input.blur();
    }
  });
})();
</script>
"""


def render_search_bar(*, inject_css: bool = True) -> str:
    """Render the global search input + JS-driven dropdown.

    Drop into the page header. Press ``/`` (wired by nav.py) to
    focus. Esc clears + closes.
    """
    css = (
        '<style>'
        '.global-search-wrap{position:relative;'
        'min-width:240px;flex:1 1 auto;max-width:480px;}'
        '#global-search-input{width:100%;background:var(--paper-pure);'
        'border:1px solid var(--border);border-radius:6px;'
        'padding:6px 12px;color:var(--ink);font-size:13px;'
        'box-sizing:border-box;font-family:system-ui;}'
        '#global-search-input::placeholder{color:var(--muted);}'
        '#global-search-input:focus{outline:none;'
        'border-color:var(--teal);}'
        '#global-search-dropdown{display:none;'
        'position:absolute;top:calc(100% + 4px);'
        'left:0;right:0;background:var(--bg);'
        'border:1px solid var(--border);border-radius:6px;'
        'box-shadow:0 8px 24px rgba(0,0,0,0.5);'
        'max-height:480px;overflow-y:auto;z-index:1500;}'
        '#global-search-dropdown a:hover{'
        'background:var(--paper-pure);}'
        '</style>') if inject_css else ""
    return (
        css
        + '<div class="global-search-wrap">'
        '<input id="global-search-input" type="search" '
        'placeholder="Search deals, metrics, pages…  /" '
        'autocomplete="off" aria-label="Global search">'
        '<div id="global-search-dropdown" '
        'role="listbox"></div></div>'
        + _SEARCH_JS)


def render_search_results_json(
    results: List[SearchResult],
) -> str:
    """Serialize results for the /api/search endpoint."""
    return json.dumps({
        "results": [r.to_dict() for r in results]})


def render_global_search_page(
    query: str, results: List[SearchResult],
) -> str:
    """Editorial server-rendered search results page.

    Per UI_REWORK_PLAN.md Phase 1 architecture decision (URL round-
    trips, no client-side state): search submits via a normal form
    GET to ``/global-search?q=…`` and the server returns a fully-
    rendered HTML page. No JS dropdown.

    Wraps the body in ``chartis_shell()`` so the editorial topbar +
    breadcrumbs + PHI banner render around the results list.
    """
    import html as _html
    from ._chartis_kit import chartis_shell

    q_safe = _html.escape(query or "")
    if not query or not query.strip():
        body = (
            '<div class="search-results">'
            '<h1 class="search-h1">Search</h1>'
            '<p class="search-empty">Enter a query in the topbar — '
            'searches deals, packets, metrics, and pages.</p>'
            '</div>'
        )
    elif not results:
        body = (
            '<div class="search-results">'
            f'<h1 class="search-h1">No matches for &ldquo;{q_safe}&rdquo;</h1>'
            '<p class="search-empty">No results across deals, packets, '
            'metrics, or pages. Try a shorter query or different keywords.</p>'
            '</div>'
        )
    else:
        rows: List[str] = []
        for r in results:
            cat = _html.escape(r.category)
            label = _html.escape(r.label)
            sub = _html.escape(r.sublabel) if r.sublabel else ""
            url = _html.escape(r.url, quote=True)
            sub_html = (
                f'<div class="sub">{sub}</div>' if sub else ""
            )
            rows.append(
                f'<a class="hit" href="{url}">'
                f'<span class="cat">{cat}</span>'
                f'<span class="label">{label}</span>'
                f'{sub_html}'
                f'</a>'
            )
        body = (
            '<div class="search-results">'
            f'<h1 class="search-h1">Results for &ldquo;{q_safe}&rdquo;</h1>'
            f'<p class="search-meta">{len(results)} match'
            f'{"es" if len(results) != 1 else ""} across deals, '
            'packets, metrics, and pages.</p>'
            '<div class="hits">' + "".join(rows) + '</div>'
            '</div>'
        )

    extra_css = """
    .search-results { max-width: 960px; margin: 1.5rem auto;
                       padding: 0 2rem; }
    .search-h1 { font-family: 'Source Serif 4', Georgia, serif;
                  font-weight: 400; font-size: 1.75rem;
                  color: var(--ink); margin-bottom: .5rem; }
    .search-meta { color: var(--muted); font-size: .85rem;
                    margin-bottom: 1.5rem; }
    .search-empty { color: var(--muted); font-size: .95rem;
                     padding: 2rem 0; }
    .hits { display: flex; flex-direction: column; gap: .5rem; }
    .hit { display: grid; grid-template-columns: 8rem 1fr;
           grid-template-rows: auto auto; gap: .15rem .9rem;
           padding: .75rem 1rem; border: 1px solid var(--border);
           background: var(--paper-pure); text-decoration: none;
           color: var(--ink); transition: border-color 140ms ease; }
    .hit:hover { border-color: var(--teal-deep); }
    .hit .cat { grid-row: 1 / 3; align-self: start;
                font-family: 'JetBrains Mono', monospace;
                font-size: .65rem; letter-spacing: .14em;
                text-transform: uppercase; color: var(--muted);
                padding: .15rem .5rem; border: 1px solid var(--border);
                background: var(--paper); height: fit-content; }
    .hit .label { font-size: .95rem; font-weight: 500; color: var(--ink); }
    .hit .sub { font-size: .8rem; color: var(--muted); }
    """

    return chartis_shell(
        body,
        title=f"Search · {query}" if query else "Search",
        active_nav="",
        extra_css=extra_css,
        breadcrumbs=[
            ("Home", "/app"),
            ("Search", None),
        ],
    )
