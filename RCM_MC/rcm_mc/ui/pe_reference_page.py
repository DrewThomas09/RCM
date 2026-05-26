"""PE Intelligence reference libraries — /diligence/pe-reference.

Surfaces the deal-independent *curated knowledge* libraries from the
pe_intelligence package, which were built but never linked to any UI. Unlike
the deal-driven tool runner (/diligence/pe-tool), these are reference content:
real, named historical events and partner-judgment analysis that don't change
per deal — so they're shown as a browsable library, not "computed from your
deal".

Two libraries are wired (both back rich dataclasses):
  * Historical Failure Library — dated PE-healthcare blow-ups (Envision/KKR
    No Surprises Act 2023, etc.), each with thesis-at-entry, what-went-wrong,
    EBITDA destruction, early-warning signals, and the partner lesson.
  * Partner Traps — common seller pitches paired with the partner's rebuttal
    and a realistic number to underwrite to.

Honesty: the events are real and public; the analysis (lessons, magnitudes) is
partner judgment. Labeled as a curated corpus, not a live feed. String-ID-only
libraries (seller motivations, failure archetypes, …) need a per-id expander
and are surfaced as the registry grows.
"""
from __future__ import annotations

import html as _html
import importlib
from typing import Any, Dict, List, Tuple

from ._chartis_kit import (
    P,
    chartis_shell,
    ck_illustrative_note,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
    ck_source_purpose,
)

# library key → (module, list_fn, title, one-line intro)
_LIBRARIES: Dict[str, Tuple[str, str, str, str]] = {
    "failures": (
        "historical_failure_library", "list_all_patterns",
        "Historical Failure Library",
        "Dated PE-healthcare deals that broke — what the thesis was, what "
        "actually happened, and the lesson. Fingerprint-match a live deal "
        "against these before you repeat one.",
    ),
    "traps": (
        "partner_traps_library", "list_all_traps",
        "Partner Traps",
        "Seller pitches a partner has heard before, each paired with the "
        "rebuttal and the realistic number to underwrite to.",
    ),
}
_DEFAULT_LIB = "failures"


def _humanize(name: str) -> str:
    return " ".join(w.capitalize() for w in name.replace("_", " ").split())


def _chip(text: str) -> str:
    return (
        f'<span style="display:inline-block;font-family:var(--ck-mono);'
        f'font-size:9.5px;letter-spacing:0.03em;color:{P["text_dim"]};'
        f'background:{P["panel"]};border:1px solid {P["border_dim"]};'
        f'border-radius:2px;padding:2px 6px;margin:0 5px 5px 0;">'
        f'{_html.escape(_humanize(text))}</span>'
    )


def _field(label: str, value: str) -> str:
    return (
        f'<div style="margin:7px 0;"><div style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{P["text_faint"]};margin-bottom:2px;">{_html.escape(label)}</div>'
        f'<div style="font-size:12.5px;line-height:1.55;color:{P["text"]};">'
        f'{_html.escape(value)}</div></div>'
    )


def _failure_card(p: Any) -> str:
    year = getattr(p, "year", "")
    dest = getattr(p, "ebitda_destruction_pct", None)
    stat = ""
    if isinstance(dest, (int, float)):
        stat = (
            f'<span style="font-family:var(--ck-mono);font-size:11px;'
            f'font-weight:700;color:{P["negative"]};white-space:nowrap;">'
            f'-{dest * 100:.0f}% EBITDA</span>'
        )
    signals = getattr(p, "early_warning_signals", []) or []
    sig_html = ("".join(_chip(s) for s in signals)) if signals else ""
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:12px;margin-bottom:8px;">'
        f'<span style="font-family:var(--sc-serif);font-size:16px;font-weight:600;'
        f'color:{P["text"]};">{_html.escape(_humanize(getattr(p,"name","")))}</span>'
        f'{stat}</div>'
        + _field(f"The deal · {year}", getattr(p, "deal_summary", ""))
        + _field("Thesis at entry", getattr(p, "thesis_at_entry", ""))
        + _field("What went wrong", getattr(p, "what_went_wrong", ""))
        + (f'<div style="margin:7px 0;"><div style="font-family:var(--ck-mono);'
           f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
           f'color:{P["text_faint"]};margin-bottom:3px;">Early-warning signals'
           f'</div>{sig_html}</div>' if sig_html else "")
        + f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid '
        f'{P["border_dim"]};"><span style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{P["accent"]};">Partner lesson</span>'
        f'<div style="font-size:12.5px;line-height:1.55;color:{P["text"]};'
        f'font-style:italic;margin-top:3px;">'
        f'{_html.escape(getattr(p,"partner_lesson",""))}</div></div>'
        f'</div>'
    )


def _trap_card(t: Any) -> str:
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:3px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="font-family:var(--sc-serif);font-size:15px;font-weight:600;'
        f'color:{P["text"]};margin-bottom:8px;">'
        f'{_html.escape(_humanize(getattr(t,"name","")))}</div>'
        f'<div style="margin:7px 0;"><div style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{P["text_faint"]};margin-bottom:2px;">Seller pitch</div>'
        f'<div style="font-size:12.5px;line-height:1.55;color:{P["text_dim"]};'
        f'font-style:italic;">&ldquo;{_html.escape(getattr(t,"seller_pitch",""))}'
        f'&rdquo;</div></div>'
        f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid '
        f'{P["border_dim"]};"><span style="font-family:var(--ck-mono);'
        f'font-size:9px;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{P["accent"]};">Partner rebuttal</span>'
        f'<div style="font-size:12.5px;line-height:1.55;color:{P["text"]};'
        f'margin-top:3px;">{_html.escape(getattr(t,"partner_rebuttal",""))}</div>'
        f'</div></div>'
    )


def _load(library: str) -> List[Any]:
    mod_name, list_fn, _, _ = _LIBRARIES[library]
    mod = importlib.import_module(f"..pe_intelligence.{mod_name}", __package__)
    return list(getattr(mod, list_fn)())


def render_pe_reference_page(library: str = "") -> str:
    """Render a curated reference library (deal-independent)."""
    library = library if library in _LIBRARIES else _DEFAULT_LIB
    _, _, title, intro = _LIBRARIES[library]
    items = _load(library)

    cards = "".join(
        (_failure_card(it) if library == "failures" else _trap_card(it))
        for it in items
    )

    # Library switcher chips.
    tabs = []
    for key, (_, _, t, _) in _LIBRARIES.items():
        on = key == library
        n = len(_load(key))
        tabs.append(
            f'<a href="/diligence/pe-reference?library={key}" '
            f'style="font-family:var(--ck-mono);font-size:11px;padding:5px 11px;'
            f'margin:0 6px 6px 0;display:inline-block;border-radius:3px;'
            f'text-decoration:none;border:1px solid '
            f'{P["accent"] if on else P["border"]};'
            f'background:{P["accent"] if on else P["panel"]};'
            f'color:{"#fff" if on else P["text_dim"]};">{_html.escape(t)} ({n})</a>'
        )

    kpis = (
        ck_kpi_block("Entries", str(len(items)), title)
        + ck_kpi_block("Libraries", str(len(_LIBRARIES)), "curated, deal-independent")
        + ck_kpi_block("Use", "Pattern-match", "against a live deal before you "
                       "repeat one")
    )

    sp = ck_source_purpose(
        purpose=intro,
        universe="corpus",
        confidence="derived",
        source="rcm_mc.pe_intelligence curated libraries — real named public "
               "events + partner-judgment analysis (not a live data feed)",
        next_action="Run a tool on a deal",
        next_href="/diligence/pe-tool",
    )

    body = (
        ck_page_title(title, eyebrow="DILIGENCE · REFERENCE",
                      meta=f"{len(items)} entries · curated knowledge base")
        + ck_illustrative_note("a curated knowledge base — real named events "
                               "with partner-judgment analysis, not live data")
        + sp
        + f'<div style="margin:10px 0 14px;">{"".join(tabs)}</div>'
        + f'<div class="ck-kpi-grid">{kpis}</div>'
        + ck_section_header(title.upper(), intro, count=len(items))
        + cards
    )
    return chartis_shell(body, title=title, active_nav="/diligence")
