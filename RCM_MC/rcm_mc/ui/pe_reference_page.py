"""PE Intelligence reference libraries — /diligence/pe-reference.

Surfaces the deal-independent *curated knowledge* libraries from the
pe_intelligence package, which were built but never linked to any UI. Unlike
the deal-driven tool runner (/diligence/pe-tool), these are reference content:
real, named patterns and partner-judgment analysis that don't change per deal
— so they're shown as a browsable library, not "computed from your deal".

Six libraries are wired, each backed by a curated dataclass list:
  * Historical failures — dated PE-healthcare blow-ups + the partner lesson.
  * Partner traps — seller pitch vs the rebuttal + realistic number.
  * Seller motivations — what's really driving the sale + the partner play.
  * Failure archetypes — structural failure shapes + the counter.
  * Bidder landscape — buyer profiles, expected premium, partner posture.
  * Banker narratives — the CIM/management-meeting plays + how to defuse them.

Honesty: the patterns/events are real partner knowledge; framing and any
magnitudes are partner judgment, not a live feed. Labeled a curated corpus.
"""
from __future__ import annotations

import dataclasses
import html as _html
import importlib
from typing import Any, Callable, Dict, List, Optional

from ._chartis_kit import (
    P,
    chartis_shell,
    ck_illustrative_note,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
    ck_source_purpose,
)


def _humanize(name: str) -> str:
    return " ".join(w.capitalize() for w in str(name).replace("_", " ").split())


# ── generic card primitives ────────────────────────────────────────────────
def _chip(text: str) -> str:
    return (
        f'<span style="display:inline-block;font-family:var(--ck-mono);'
        f'font-size:9.5px;letter-spacing:0.03em;color:{P["text_dim"]};'
        f'background:{P["panel"]};border:1px solid {P["border_dim"]};'
        f'border-radius:2px;padding:2px 6px;margin:0 5px 5px 0;">'
        f'{_html.escape(_humanize(text))}</span>'
    )


def _meta_badge(label: str, value: str) -> str:
    return (
        f'<span style="display:inline-block;font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.04em;margin:0 6px 5px 0;'
        f'color:{P["text_dim"]};"><span style="color:{P["text_faint"]};'
        f'text-transform:uppercase;">{_html.escape(label)}</span> '
        f'{_html.escape(_humanize(value))}</span>'
    )


def _field(label: str, value: str, *, italic: bool = False) -> str:
    quote = ('&ldquo;' + _html.escape(value) + '&rdquo;') if italic \
        else _html.escape(value)
    style = (f'font-size:12.5px;line-height:1.55;color:'
             f'{P["text_dim"] if italic else P["text"]};'
             + ('font-style:italic;' if italic else ''))
    return (
        f'<div style="margin:7px 0;"><div style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{P["text_faint"]};margin-bottom:2px;">{_html.escape(label)}</div>'
        f'<div style="{style}">{quote}</div></div>'
    )


def _render_card(item: Any, spec: Dict[str, Any]) -> str:
    g = lambda f: getattr(item, f, None)  # noqa: E731
    title = _humanize(g(spec["title"]) or "")
    if spec.get("title_suffix") and g(spec["title_suffix"]) is not None:
        title += f' &middot; {_html.escape(str(g(spec["title_suffix"])))}'
    badge = ""
    if spec.get("badge"):
        field, fmt = spec["badge"]
        v = g(field)
        if isinstance(v, (int, float)):
            badge = (f'<span style="font-family:var(--ck-mono);font-size:11px;'
                     f'font-weight:700;color:{P["negative"] if fmt.startswith("-") else P["accent"]};'
                     f'white-space:nowrap;">{fmt.format(v * 100)}</span>')
    metas = "".join(_meta_badge(lbl, str(g(f))) for f, lbl in spec.get("metas", [])
                    if g(f) not in (None, ""))
    bodies = "".join(_field(lbl, str(g(f)), italic=ital)
                     for f, lbl, ital in spec.get("bodies", []) if g(f))
    chips = ""
    if spec.get("chips"):
        field, lbl = spec["chips"]
        vals = g(field) or []
        if vals:
            chips = (f'<div style="margin:7px 0;"><div style="font-family:'
                     f'var(--ck-mono);font-size:9px;letter-spacing:0.1em;'
                     f'text-transform:uppercase;color:{P["text_faint"]};'
                     f'margin-bottom:3px;">{_html.escape(lbl)}</div>'
                     + "".join(_chip(str(v)) for v in vals) + '</div>')
    hi = ""
    if spec.get("highlight"):
        field, lbl = spec["highlight"]
        v = g(field)
        if v:
            hi = (f'<div style="margin-top:8px;padding-top:8px;border-top:1px '
                  f'solid {P["border_dim"]};"><span style="font-family:'
                  f'var(--ck-mono);font-size:9px;letter-spacing:0.1em;'
                  f'text-transform:uppercase;color:{P["accent"]};">'
                  f'{_html.escape(lbl)}</span><div style="font-size:12.5px;'
                  f'line-height:1.55;color:{P["text"]};margin-top:3px;">'
                  f'{_html.escape(str(v))}</div></div>')
    head = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:12px;margin-bottom:6px;">'
        f'<span style="font-family:var(--sc-serif);font-size:16px;font-weight:600;'
        f'color:{P["text"]};">{title}</span>{badge}</div>'
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;margin-bottom:12px;">'
        f'{head}{metas}{bodies}{chips}{hi}</div>'
    )


# ── per-library config: loader + intro + card spec ──────────────────────────
def _from_list(module: str, fn: str) -> Callable[[], List[Any]]:
    return lambda: list(getattr(importlib.import_module(
        f"..pe_intelligence.{module}", __package__), fn)())


def _from_const(module: str, const: str) -> Callable[[], List[Any]]:
    return lambda: list(getattr(importlib.import_module(
        f"..pe_intelligence.{module}", __package__), const))


def _combined_failures() -> List[Any]:
    """Both curated failure libraries in one tab — historical_failure_library
    plus the distinct named_failure_library_v2 set — deduped by name, newest
    first. They share the same FailurePattern shape, so one card spec renders
    both; merging avoids a confusing v1/v2 tab split."""
    out: List[Any] = []
    seen = set()
    for mod, attr, is_fn in (
        ("historical_failure_library", "list_all_patterns", True),
        ("named_failure_library_v2", "FAILURE_LIBRARY_V2", False),
    ):
        obj = getattr(importlib.import_module(
            f"..pe_intelligence.{mod}", __package__), attr)
        for p in (obj() if is_fn else obj):
            if p.name not in seen:
                seen.add(p.name)
                out.append(p)
    return sorted(out, key=lambda p: getattr(p, "year", 0), reverse=True)


def _from_chains(module: str, const: str) -> Callable[[], List[Any]]:
    """A dict of thesis-id → builder() → [implications]. Returns
    [(thesis_id, [implications]), …] for the custom chain renderer."""
    def load():
        d = getattr(importlib.import_module(
            f"..pe_intelligence.{module}", __package__), const)
        return [(tid, list(build())) for tid, build in d.items()]
    return load


_RISK_COLOR = {"high": "#b5321e", "medium": "#b8732a", "low": "#0a8a5f"}


def _render_chain(thesis_id: str, impls: List[Any]) -> str:
    """One thesis → the chain of implicit claims a partner must check."""
    rows = []
    for im in impls:
        risk = str(getattr(im, "risk", "") or "")
        rc = _RISK_COLOR.get(risk.lower(), P["text_faint"])
        pf = getattr(im, "packet_field", "") or ""
        pf_chip = (f'<span style="font-family:var(--ck-mono);font-size:9px;'
                   f'color:{P["text_faint"]};background:{P["panel"]};'
                   f'border:1px solid {P["border_dim"]};border-radius:2px;'
                   f'padding:1px 5px;">{_html.escape(pf)}</span>' if pf else "")
        rows.append(
            f'<div style="padding:8px 0;border-bottom:1px solid {P["border_dim"]};">'
            f'<div style="display:flex;gap:8px;align-items:baseline;">'
            f'<span style="font-family:var(--ck-mono);font-size:8.5px;'
            f'font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
            f'color:{rc};white-space:nowrap;">{_html.escape(risk) or "—"} risk</span>'
            f'<span style="font-size:12.5px;line-height:1.5;color:{P["text"]};'
            f'font-weight:600;">{_html.escape(getattr(im,"claim","") or "")}</span>'
            f'</div>'
            f'<div style="margin-top:3px;display:flex;gap:8px;align-items:baseline;'
            f'flex-wrap:wrap;"><span style="font-size:12px;line-height:1.5;'
            f'color:{P["text_dim"]};">&rarr; {_html.escape(getattr(im,"partner_check","") or "")}'
            f'</span>{pf_chip}</div></div>'
        )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="font-family:var(--sc-serif);font-size:16px;font-weight:600;'
        f'color:{P["text"]};margin-bottom:4px;">{_html.escape(_humanize(thesis_id))}'
        f'</div><div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:{P["text_faint"]};'
        f'margin-bottom:6px;">{len(impls)} implicit claims to check</div>'
        f'{"".join(rows)}</div>'
    )


_LIBRARIES: Dict[str, Dict[str, Any]] = {
    "failures": {
        "title": "Historical Failures",
        "intro": "Dated PE-healthcare deals that broke — thesis at entry, what "
                 "happened, and the lesson. Pattern-match a live deal before "
                 "you repeat one.",
        "load": _combined_failures,
        "spec": {
            "title": "name", "title_suffix": "year",
            "badge": ("ebitda_destruction_pct", "-{:.1f}% EBITDA"),
            "bodies": [("deal_summary", "The deal", False),
                       ("thesis_at_entry", "Thesis at entry", False),
                       ("what_went_wrong", "What went wrong", False)],
            "chips": ("early_warning_signals", "Early-warning signals"),
            "highlight": ("partner_lesson", "Partner lesson"),
        },
    },
    "traps": {
        "title": "Partner Traps",
        "intro": "Seller pitches a partner has heard before, each paired with "
                 "the rebuttal and the realistic number to underwrite to.",
        "load": _from_list("partner_traps_library", "list_all_traps"),
        "spec": {
            "title": "name",
            "bodies": [("seller_pitch", "Seller pitch", True)],
            "highlight": ("partner_rebuttal", "Partner rebuttal"),
        },
    },
    "motivations": {
        "title": "Seller Motivations",
        "intro": "What's really driving the sale — urgency, leverage, and the "
                 "partner play that uses it.",
        "load": _from_const("seller_motivation_decoder", "MOTIVATION_LIBRARY"),
        "spec": {
            "title": "name",
            "metas": [("seller_urgency", "urgency"),
                      ("buyer_leverage", "our leverage"),
                      ("price_sensitivity", "price sens.")],
            "bodies": [("description", "Signal", False),
                       ("common_seller_position", "Typical seller position", False)],
            "highlight": ("negotiation_counter", "Partner play"),
        },
    },
    "archetypes": {
        "title": "Failure Archetypes",
        "intro": "Structural shapes a deal fails in — the mechanism and the "
                 "counter, independent of any single named deal.",
        "load": _from_const("failure_archetype_library", "ARCHETYPES"),
        "spec": {
            "title": "name",
            "bodies": [("shape_description", "Shape", False),
                       ("structural_reason", "Why it breaks", False)],
            "chips": ("signals", "Signals to watch"),
            "highlight": ("partner_counter", "Partner counter"),
        },
    },
    "bidders": {
        "title": "Bidder Landscape",
        "intro": "Buyer profiles in a process — typical behavior, the premium "
                 "they'll pay, and the posture to take against each.",
        "load": _from_const("bidder_landscape_reader", "PROFILE_LIBRARY"),
        "spec": {
            "title": "name",
            "badge": ("expected_price_premium_pct", "+{:.1f}% premium"),
            "metas": [("concession_posture", "concedes on"),
                      ("partner_posture", "our posture")],
            "bodies": [("typical_behavior", "Typical behavior", False)],
            "highlight": ("partner_counter", "Partner counter"),
        },
    },
    "narratives": {
        "title": "Banker Narratives",
        "intro": "The CIM and management-meeting plays a banker runs — name the "
                 "play, know why it works, and defuse it.",
        "load": _from_const("banker_narrative_decoder", "NARRATIVE_LIBRARY"),
        "spec": {
            "title": "name",
            "bodies": [("what_banker_says", "What the banker says", True),
                       ("why_it_works", "Why it works", False)],
            "chips": ("tells", "Tells"),
            "highlight": ("partner_counter", "Partner counter"),
        },
    },
    "signing": {
        "title": "Signing-to-Close Risks",
        "intro": "What can break a deal between signing and close — frequency, "
                 "severity, the early warnings, and the pre-close counter.",
        "load": _from_const("signing_to_close_risk_register", "RISK_LIBRARY"),
        "spec": {
            "title": "name",
            "badge": ("typical_cost_to_buyer_pct", "{:.1f}% cost"),
            "metas": [("frequency", "frequency"), ("severity", "severity")],
            "bodies": [("description", "Risk", False)],
            "chips": ("early_warning_signals", "Early-warning signals"),
            "highlight": ("partner_counter_pre_close", "Counter · pre-close"),
        },
    },
    "thesis": {
        "title": "Thesis Chains",
        "intro": "Every healthcare thesis carries implicit claims. Each chain "
                 "lays out what must be true, the partner check, and the risk "
                 "if it isn't — so the diligence plan writes itself.",
        "load": _from_chains("thesis_implications_chain", "THESIS_CHAINS"),
        "kind": "chains",
    },
}
_DEFAULT_LIB = "failures"


def _load(library: str) -> List[Any]:
    cfg = _LIBRARIES.get(library) or _LIBRARIES[_DEFAULT_LIB]
    return cfg["load"]()


def render_pe_reference_page(library: str = "") -> str:
    """Render a curated reference library (deal-independent)."""
    library = library if library in _LIBRARIES else _DEFAULT_LIB
    cfg = _LIBRARIES[library]
    title, intro = cfg["title"], cfg["intro"]
    items = _load(library)

    if cfg.get("kind") == "chains":
        cards = "".join(_render_chain(tid, impls) for tid, impls in items)
    else:
        cards = "".join(_render_card(it, cfg["spec"]) for it in items)

    tabs = []
    for key, c in _LIBRARIES.items():
        on = key == library
        n = len(c["load"]())
        tabs.append(
            f'<a href="/diligence/pe-reference?library={key}" '
            f'style="font-family:var(--ck-mono);font-size:11px;padding:5px 11px;'
            f'margin:0 6px 6px 0;display:inline-block;border-radius:3px;'
            f'text-decoration:none;border:1px solid '
            f'{P["accent"] if on else P["border"]};'
            f'background:{P["accent"] if on else P["panel"]};'
            f'color:{"#fff" if on else P["text_dim"]};">'
            f'{_html.escape(c["title"])} ({n})</a>'
        )

    kpis = (
        ck_kpi_block("Entries", str(len(items)), title)
        + ck_kpi_block("Libraries", str(len(_LIBRARIES)),
                       "curated, deal-independent")
        + ck_kpi_block("Use", "Pattern-match", "against a live deal before you "
                       "commit")
    )

    sp = ck_source_purpose(
        purpose=intro,
        universe="corpus",
        confidence="derived",
        source="rcm_mc.pe_intelligence curated libraries — real partner "
               "knowledge + judgment analysis (not a live data feed)",
        next_action="Run a tool on a deal",
        next_href="/diligence/pe-tool",
    )

    body = (
        ck_page_title(title, eyebrow="DILIGENCE · REFERENCE",
                      meta=f"{len(items)} entries · curated knowledge base")
        + ck_illustrative_note("a curated knowledge base — real patterns with "
                               "partner-judgment analysis, not live data")
        + sp
        + f'<div style="margin:10px 0 14px;">{"".join(tabs)}</div>'
        + f'<div class="ck-kpi-grid">{kpis}</div>'
        + ck_section_header(title.upper(), intro, count=len(items))
        + cards
    )
    return chartis_shell(body, title=title, active_nav="/diligence")
