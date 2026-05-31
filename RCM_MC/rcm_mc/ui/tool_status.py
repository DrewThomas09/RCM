"""Single source of truth for a tool's data-lineage status — the colored
status dot shown next to a tool in the index/dashboard surfaces.

Status is a *provenance claim*, so it is derived from real code signals
and an audited override map — never guessed from the tool's name.

Three states (matching the existing module-index palette):
  - ``live``         green  — computed live from the realized-deal corpus
                              or live portfolio data
  - ``cms``          teal   — computed from CMS public datasets
  - ``illustrative`` amber  — hardcoded representative figures, not live data

Resolution order (``resolve_tool_status``):
  1. Audited ``_OVERRIDE`` map (route -> (key, reason)).
  2. The route's data_public page calls ``ck_illustrative_note(...)`` — a
     definitive illustrative signal — => ``illustrative``.
  3. Safe default => ``illustrative``. Rationale: a wrong "live" tag is the
     credibility-damaging direction (it overclaims real data); underclaiming
     as illustrative is merely conservative. Known-live tools are therefore
     listed explicitly in ``_OVERRIDE``; anything unaudited stays
     conservative. ``audit_defaulted_routes`` surfaces every route that hits
     this default so it can be reviewed/promoted.
"""
from __future__ import annotations

import functools
import html as _html
import pathlib
from typing import Dict, FrozenSet, List, Tuple

# (color token, short label, accessible tooltip)
SOURCE_META: Dict[str, Tuple[str, str, str]] = {
    "live": ("var(--sc-positive,#0a8a5f)", "Live",
             "Computed live from the realized-deal corpus or live portfolio data"),
    "cms": ("var(--sc-teal,#155752)", "CMS",
            "Computed from CMS public datasets"),
    "illustrative": ("var(--sc-warning,#b8732a)", "Illustrative",
                     "Illustrative template — representative figures, not live data"),
}

# Audited classifications. Each entry is route -> (status, reason). Seeded
# from the former module_index _MODULE_SOURCE plus evidence-checked
# leftovers and the live operational/diligence surfaces. Keep the reason
# accurate — it is the audit trail for a provenance claim.
_OVERRIDE: Dict[str, Tuple[str, str]] = {
    # ── Live: realized-deal corpus / computed analytics ──
    "/base-rates": ("live", "computed from realized-deal corpus"),
    "/market-rates": ("live", "computed from realized-deal corpus"),
    "/redflag-scanner": ("live", "rule-based scan over corpus deals"),
    "/backtester": ("live", "backtest over realized corpus"),
    "/antitrust-screener": ("live", "computed over corpus deals"),
    "/rollup-economics": ("live", "computed from corpus"),
    "/sponsor-league": ("live", "computed from corpus deals"),
    "/sponsor-heatmap": ("live", "computed from corpus deals"),
    "/exit-timing": ("live", "loads realized-deal corpus (_load_corpus)"),
    # ── Live: operational / portfolio-DB-backed surfaces ──
    "/app": ("live", "Command Center over the live portfolio store"),
    "/day-one": ("live", "live portfolio brief"),
    "/alerts": ("live", "live alerts lifecycle"),
    "/escalations": ("live", "live escalations"),
    "/watchlist": ("live", "live watchlist"),
    "/pipeline": ("live", "live deal pipeline"),
    "/portfolio": ("live", "live portfolio store"),
    "/activity": ("live", "live audit/activity log"),
    # ── CMS public data ──
    "/cms-data-browser": ("cms", "CMS public datasets"),
    "/cms-sources": ("cms", "CMS public datasets"),
    "/msa-concentration": ("cms", "CMS public datasets"),
    # ── Illustrative: hardcoded representative templates ──
    "/deal-origination": ("illustrative", "hardcoded representative data"),
    "/payer-concentration": ("illustrative", "hardcoded representative data"),
    "/fraud-detection": ("illustrative", "hardcoded representative data"),
    "/drug-shortage": ("illustrative", "hardcoded representative data"),
    "/cyber-risk": ("illustrative", "hardcoded representative data"),
    "/ai-operating-model": ("illustrative", "hardcoded representative data"),
    "/health-equity": ("illustrative", "hardcoded representative data"),
    "/physician-labor": ("illustrative", "hardcoded representative data"),
    "/phys-comp-plan": ("illustrative", "hardcoded representative data"),
    "/locum-tracker": ("illustrative", "hardcoded representative data"),
    "/ma-contracts": ("illustrative", "hardcoded representative data"),
    "/drug-pricing-340b": ("illustrative", "hardcoded representative data"),
    "/aco-economics": ("illustrative", "hardcoded representative data"),
    "/denovo-expansion": ("illustrative", "hardcoded representative data"),
    "/pmi-playbook": ("illustrative", "hardcoded representative data"),
    "/direct-employer": ("illustrative", "hardcoded representative data"),
    "/cin-analyzer": ("illustrative", "hardcoded representative data"),
    "/zbb-tracker": ("illustrative", "hardcoded representative data"),
    "/capital-pacing": ("illustrative", "hardcoded representative data"),
    "/covenant-headroom": ("illustrative", "hardcoded representative data"),
    "/direct-lending": ("illustrative", "hardcoded representative data"),
    "/reit-analyzer": ("illustrative", "hardcoded representative data"),
    "/telehealth-econ": ("illustrative", "hardcoded representative data"),
    "/hcit-platform": ("illustrative", "hardcoded representative data"),
    "/biosimilars": ("illustrative", "hardcoded representative data"),
    "/trial-site-econ": ("illustrative", "hardcoded representative data"),
    "/platform-maturity": ("illustrative", "hardcoded tables, no live loader"),
    "/ic-memo-gen": ("illustrative", "hardcoded template tables, no live loader"),
}

_DEFAULT_STATUS = "illustrative"
_DEFAULT_REASON = "unaudited — defaulted to illustrative (never overclaims live)"

_DATA_PUBLIC_DIR = pathlib.Path(__file__).resolve().parent / "data_public"


@functools.lru_cache(maxsize=1)
def _illustrative_routes_from_pages() -> FrozenSet[str]:
    """Routes whose data_public page module calls ``ck_illustrative_note`` —
    a definitive, self-declared illustrative signal. Scanned once, cached."""
    out = set()
    route_re = __import__("re").compile(r"""["']/(?:[a-z0-9][a-z0-9/_-]*)["']""")
    for path in _DATA_PUBLIC_DIR.glob("*_page.py"):
        text = path.read_text(encoding="utf-8")
        if "ck_illustrative_note" not in text:
            continue
        for m in route_re.finditer(text):
            tok = m.group(0).strip("\"'")
            if tok.count("/") == 1:  # top-level route only, not asset paths
                out.add(tok)
    return frozenset(out)


def resolve_tool_status(route: str) -> Tuple[str, str]:
    """Return ``(status_key, reason)`` for a tool route. Never raises."""
    r = (route or "").split("?")[0].rstrip("/") or "/"
    if r in _OVERRIDE:
        return _OVERRIDE[r]
    if r in _illustrative_routes_from_pages():
        return ("illustrative", "page declares ck_illustrative_note")
    return (_DEFAULT_STATUS, _DEFAULT_REASON)


def status_dot(route: str, *, show_label: bool = False) -> str:
    """A small colored status dot for a tool, with an accessible label.

    Color alone is never the only signal — the dot carries a ``title`` and
    ``aria-label`` ("Live data" / "CMS public data" / "Illustrative
    template"), and an optional visible text label."""
    key, _reason = resolve_tool_status(route)
    color, label, title = SOURCE_META[key]
    dot = (
        f'<span class="tool-status-dot" role="img" '
        f'style="--tsd-c:{color};" '
        f'title="{_html.escape(title, quote=True)}" '
        f'aria-label="{_html.escape(label)} — {_html.escape(title, quote=True)}">'
        f'</span>'
    )
    if show_label:
        dot += (
            f'<span class="tool-status-label" '
            f'style="--tsd-c:{color};">{_html.escape(label)}</span>'
        )
    return dot


def status_dot_css() -> str:
    """Scoped CSS for the status dot + label. Include once per page."""
    return (
        "<style>"
        ".tool-status-dot{display:inline-block;width:8px;height:8px;"
        "border-radius:50%;background:var(--tsd-c);vertical-align:middle;"
        "margin-right:6px;flex:none;}"
        ".tool-status-label{font-family:var(--sc-mono,monospace);font-size:10px;"
        "font-weight:700;letter-spacing:0.08em;text-transform:uppercase;"
        "color:var(--tsd-c);}"
        "</style>"
    )


def audit_defaulted_routes(routes: List[str]) -> List[str]:
    """Routes (from ``routes``) that fall through to the safe default — i.e.
    not in the override and lacking the ck_illustrative_note signal. Used by
    tests/operators to find tools that still need an audited classification."""
    illus = _illustrative_routes_from_pages()
    out = []
    for route in routes:
        r = (route or "").split("?")[0].rstrip("/") or "/"
        if r not in _OVERRIDE and r not in illus:
            out.append(r)
    return out
