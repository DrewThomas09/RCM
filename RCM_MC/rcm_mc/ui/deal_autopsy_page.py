"""Deal Autopsy page at /diligence/deal-autopsy.

Given a target's 9-dim signature, rank a curated library of historical
PE healthcare deals by similarity and surface the closest matches with
their outcome + partner lesson.

The page works in three modes:

    1. **Fixture mode** — pick a CCD fixture; signature is auto-built
       from the CCD plus optional metadata query params.

    2. **Custom signature mode** — paste in 9 values directly.

    3. **Landing** — pre-run, shows the library + an explainer.

Every hero / headline number is accompanied by a plain-English
"What this shows" callout so a partner can read it cold.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

from ..diligence import ingest_dataset
from ..diligence._pages import AVAILABLE_FIXTURES, _resolve_dataset
from ..diligence.deal_autopsy import (
    DealSignature, FEATURE_NAMES, MatchResult,
    OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE, OUTCOME_DELISTED,
    OUTCOME_STRONG_EXIT, OUTCOME_STRONG_PUBLIC,
    historical_library, match_target, signature_from_ccd,
)
from ..diligence.deal_autopsy.library import outcomes_summary
from ..diligence.deal_autopsy.matcher import FEATURE_LABELS
from ._chartis_kit import P, chartis_shell
from .power_ui import provenance, sortable_table


# Outcome → (label, color-key) for badge rendering.
_OUTCOME_PRESENTATION: Dict[str, Tuple[str, str]] = {
    OUTCOME_BANKRUPTCY:      ("Bankruptcy",      "negative"),
    OUTCOME_CHAPTER_11:      ("Chapter 11",      "negative"),
    OUTCOME_DISTRESSED_SALE: ("Distressed sale", "warning"),
    OUTCOME_DELISTED:        ("Delisted",        "warning"),
    OUTCOME_STRONG_EXIT:     ("Strong exit",     "positive"),
    OUTCOME_STRONG_PUBLIC:   ("Strong public",   "positive"),
}


_NEGATIVE_OUTCOMES = (
    OUTCOME_BANKRUPTCY,
    OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE,
    OUTCOME_DELISTED,
)


# ────────────────────────────────────────────────────────────────────
# Scoped styles (Bloomberg-tier polish)
#
# Palette hooks read off the existing Chartis variables set by the
# shell; nothing here overrides other pages. Every class is prefixed
# ``da-`` so this page can never collide with other UI assets.
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    """Scoped CSS for the Deal Autopsy page.

    Uses str.format with palette values, then wraps the result in
    <style>...</style>.  Keeps the CSS readable while still pulling
    live colors from :data:`P`.
    """
    css = """
.da-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.da-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.da-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.da-h2{{font-size:14px;color:{tx};font-weight:600;margin:0;
letter-spacing:-.1px;}}
.da-lead{{font-size:13px;color:{td};line-height:1.65;max-width:880px;}}
.da-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:20px 0 10px 0;}}
.da-num{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.da-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.da-callout.alert{{border-left-color:{ne};color:{ne};font-weight:600;font-size:13px;}}
.da-callout.warn{{border-left-color:{wn};color:{wn};font-weight:600;font-size:13px;}}
.da-callout.good{{border-left-color:{po};color:{po};font-weight:600;font-size:13px;}}
.da-card{{background:{pn};border:1px solid {bd};border-radius:4px;
margin-bottom:16px;overflow:hidden;
transition:transform 140ms ease,border-color 140ms ease,box-shadow 140ms ease;}}
.da-card:hover{{transform:translateY(-1px);border-color:{tf};
box-shadow:0 8px 24px rgba(0,0,0,0.35);}}
.da-card__band{{height:3px;}}
.da-card__body{{padding:18px 22px;}}
.da-card__head{{display:flex;justify-content:space-between;
align-items:flex-start;gap:20px;flex-wrap:wrap;}}
.da-card__meta{{min-width:300px;}}
.da-card__meta-top{{font-size:10px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;}}
.da-card__title{{font-size:18px;color:{tx};font-weight:600;letter-spacing:-.15px;}}
.da-card__sim{{text-align:right;min-width:160px;}}
.da-card__sim-val{{font-size:38px;line-height:1;
font-family:"JetBrains Mono",monospace;font-weight:700;
font-variant-numeric:tabular-nums;}}
.da-pill{{display:inline-block;padding:2px 9px;font-size:9px;
letter-spacing:1.3px;text-transform:uppercase;font-weight:700;
border-radius:3px;border:1px solid currentColor;}}
.da-chip{{display:inline-block;padding:4px 10px;margin:3px 5px 3px 0;
border:1px solid currentColor;font-size:10.5px;border-radius:3px;
transition:background 120ms ease;background:{pn};}}
.da-chip:hover{{background:{pa};}}
.da-chip__num{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;margin-left:4px;color:{td};}}
.da-grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;}}
.da-warnings li{{margin:4px 0;color:{td};line-height:1.55;}}
.da-warnings li::marker{{color:{tf};}}
.da-lesson{{margin-top:14px;font-size:12.5px;color:{tx};line-height:1.6;}}
.da-lesson__tag{{color:{ac};text-transform:uppercase;font-size:10px;
letter-spacing:1.3px;font-weight:700;margin-right:4px;}}
.da-quote{{margin-top:12px;padding:12px 16px;background:{pa};
border-left:2px solid {ac};font-style:italic;font-size:12.5px;
line-height:1.6;color:{td};border-radius:0 3px 3px 0;}}
.da-quote small{{display:block;margin-top:6px;font-style:normal;
font-size:10px;color:{tf};}}
.da-spectrum{{height:6px;background:{bdim};border-radius:3px;
position:relative;overflow:hidden;margin-top:10px;}}
.da-spectrum__fill{{height:100%;background:linear-gradient(90deg,
{po} 0%,{wn} 55%,{ne} 100%);}}
.da-spectrum__marker{{position:absolute;top:-5px;width:2px;
height:16px;background:{tx};border-radius:1px;}}
.da-sig-row{{display:flex;justify-content:space-between;gap:12px;
padding:5px 0;border-bottom:1px solid {bdim};font-size:11.5px;
color:{td};align-items:baseline;}}
.da-sig-row:last-child{{border-bottom:0;}}
.da-sig-row__val{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;color:{tx};min-width:60px;
text-align:right;font-weight:600;}}
.da-sig-row__src{{color:{tf};font-size:9.5px;min-width:200px;
text-align:right;font-family:"JetBrains Mono",monospace;}}
@media (max-width:720px){{.da-grid2{{grid-template-columns:1fr;}}
.da-card__head{{flex-direction:column;}}
.da-card__sim{{text-align:left;}}}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], bdim=P["border_dim"],
        ac=P["accent"], po=P["positive"],
        ne=P["negative"], wn=P["warning"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _first(qs: Dict[str, List[str]], key: str, default: str = "") -> str:
    return (qs.get(key) or [default])[0].strip()


def _float_arg(qs: Dict[str, List[str]], key: str) -> Optional[float]:
    raw = _first(qs, key)
    if raw == "":
        return None
    try:
        v = float(raw)
    except ValueError:
        return None
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _signature_from_qs(
    qs: Dict[str, List[str]],
) -> Optional[DealSignature]:
    """Build a signature entirely from query params (custom mode).

    Returns None if the user has not supplied any signature fields
    (meaning they want landing / fixture mode instead).
    """
    supplied = False
    fields: Dict[str, float] = {}
    for name in FEATURE_NAMES:
        val = _float_arg(qs, name)
        if val is not None:
            supplied = True
            fields[name] = val
        else:
            fields[name] = 0.0
    if not supplied:
        return None
    return DealSignature(
        **fields,
        provenance={n: "query param" for n in fields},
    )


def _metadata_from_qs(
    qs: Dict[str, List[str]],
) -> Dict[str, float]:
    """Extract the metadata-only dimensions from the query string
    when a user picks a fixture but supplies override values."""
    md: Dict[str, float] = {}
    for key in (
        "lease_intensity", "ebitdar_stress", "dar_stress",
        "regulatory_exposure", "physician_concentration",
    ):
        v = _float_arg(qs, key)
        if v is not None:
            md[key] = v
    return md


def _signature_chart(
    target: DealSignature, deal_sig: Tuple[float, ...],
    width: int = 560, height: int = 210,
) -> str:
    """Grouped bar chart: target vs. historical for each feature."""
    pad_l, pad_r, pad_t, pad_b = 130, 20, 20, 28
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    n = len(FEATURE_NAMES)
    row_h = inner_h / n
    tgt = target.as_tuple()

    bars: List[str] = []
    labels: List[str] = []
    for i, name in enumerate(FEATURE_NAMES):
        y = pad_t + row_h * i + 4
        lbl = FEATURE_LABELS.get(name, name)
        labels.append(
            f'<text x="{pad_l - 8:.0f}" y="{y + row_h/2 + 1:.0f}" '
            f'fill="{P["text_dim"]}" font-size="9" text-anchor="end" '
            f'font-family="Helvetica Neue, Arial, sans-serif">'
            f'{html.escape(lbl)}</text>'
        )
        # Background track.
        bars.append(
            f'<rect x="{pad_l}" y="{y:.0f}" width="{inner_w}" '
            f'height="{row_h - 8:.0f}" fill="{P["border_dim"]}" />'
        )
        # Historical (faint).
        hw = inner_w * deal_sig[i]
        bars.append(
            f'<rect x="{pad_l}" y="{y + 1:.0f}" width="{hw:.1f}" '
            f'height="{(row_h - 10)/2:.1f}" '
            f'fill="{P["text_faint"]}" opacity="0.6" />'
        )
        # Target (accent).
        tw = inner_w * tgt[i]
        bars.append(
            f'<rect x="{pad_l}" y="{y + (row_h-10)/2 + 2:.0f}" '
            f'width="{tw:.1f}" height="{(row_h - 10)/2:.1f}" '
            f'fill="{P["accent"]}" />'
        )
    legend = (
        f'<g transform="translate({pad_l},{height - 10:.0f})">'
        f'<rect width="10" height="6" fill="{P["accent"]}" />'
        f'<text x="16" y="6" fill="{P["text_dim"]}" font-size="9" '
        f'font-family="Helvetica Neue, Arial, sans-serif">target</text>'
        f'<rect x="72" width="10" height="6" '
        f'fill="{P["text_faint"]}" opacity="0.6" />'
        f'<text x="88" y="6" fill="{P["text_dim"]}" font-size="9" '
        f'font-family="Helvetica Neue, Arial, sans-serif">historical</text>'
        f'</g>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'{"".join(bars)}{"".join(labels)}{legend}</svg>'
    )


def _outcome_badge(outcome: str) -> str:
    label, tone = _OUTCOME_PRESENTATION.get(
        outcome, (outcome, "text_dim"),
    )
    color = P.get(tone, P["text_dim"])
    return (
        f'<span class="da-pill" style="color:{color};">'
        f'{html.escape(label)}</span>'
    )


def _feature_chips(
    deltas: List, *, kind: str = "aligning",
) -> str:
    if not deltas:
        return ""
    color = (
        P["positive"] if kind == "aligning" else P["warning"]
    )
    chips = []
    for d in deltas:
        share_pct = d.share_of_distance * 100
        chips.append(
            f'<span class="da-chip" style="color:{color};">'
            f'{html.escape(d.label)}'
            f'<span class="da-chip__num">'
            f'{d.target_value:.2f} / {d.historical_value:.2f}'
            f' · {share_pct:.0f}%</span></span>'
        )
    return "".join(chips)


def _similarity_spectrum(value: float) -> str:
    """Left-to-right gradient ribbon with a marker at the value."""
    pct = max(0.0, min(1.0, value)) * 100
    return (
        f'<div class="da-spectrum">'
        f'<div class="da-spectrum__fill"></div>'
        f'<div class="da-spectrum__marker" '
        f'style="left:calc({pct:.2f}% - 1px);"></div>'
        f'</div>'
    )


def _match_card(result: MatchResult, target: DealSignature) -> str:
    deal = result.deal
    sim_pct = result.similarity * 100
    # Similarity narrative band.
    if result.similarity >= 0.85:
        sim_color = (
            P["negative"] if deal.autopsy.is_negative else P["positive"]
        )
        sim_label = "Strong signature match"
    elif result.similarity >= 0.72:
        sim_color = (
            P["warning"] if deal.autopsy.is_negative else P["positive"]
        )
        sim_label = "Meaningful match"
    elif result.similarity >= 0.60:
        sim_color = P["text_dim"]
        sim_label = "Partial match"
    else:
        sim_color = P["text_faint"]
        sim_label = "Weak match"

    warnings = "".join(
        f'<li>{html.escape(w)}</li>'
        for w in deal.autopsy.early_warning_signs
    )
    quote_html = (
        f'<div class="da-quote">'
        f'"{html.escape(deal.autopsy.partner_quote)}"'
        f'<small>— post-mortem reflection on '
        f'{html.escape(deal.name)}</small></div>'
    ) if deal.autopsy.partner_quote else ""

    lesson_html = (
        f'<div class="da-lesson">'
        f'<span class="da-lesson__tag">Partner lesson:</span>'
        f'{html.escape(deal.autopsy.partner_lesson)}</div>'
    ) if deal.autopsy.partner_lesson else ""

    primary_killer_html = ""
    if deal.autopsy.primary_killer:
        primary_killer_html = (
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'margin-top:6px;">Primary driver of failure · '
            f'<code style="color:{P["text_dim"]};background:'
            f'{P["panel_alt"]};padding:1px 6px;border-radius:2px;">'
            f'{html.escape(deal.autopsy.primary_killer)}</code></div>'
        )

    sources_html = ""
    if deal.sources:
        sources_html = (
            f'<details style="margin-top:12px;font-size:10px;'
            f'color:{P["text_faint"]};">'
            f'<summary style="cursor:pointer;color:{P["text_dim"]};'
            f'letter-spacing:1.3px;text-transform:uppercase;'
            f'font-weight:600;font-size:9px;">Sources</summary>'
            f'<ul style="margin:6px 0 0 20px;line-height:1.7;">'
            + "".join(f'<li>{html.escape(s)}</li>' for s in deal.sources)
            + "</ul></details>"
        )

    # Banner color by outcome class.
    outcome_band_color = (
        P["negative"] if deal.autopsy.is_negative else P["positive"]
    )

    return (
        f'<div class="da-card">'
        f'<div class="da-card__band" style="background:{outcome_band_color};"></div>'
        f'<div class="da-card__body">'
        f'<div class="da-card__head">'
        f'<div class="da-card__meta">'
        f'<div class="da-card__meta-top">'
        f'{html.escape(deal.sector.replace("_", " "))} · '
        f'{html.escape(deal.sponsor)} · entry {deal.entry_year}</div>'
        f'<div class="da-card__title">{html.escape(deal.name)}</div>'
        f'<div style="margin-top:8px;display:flex;gap:8px;'
        f'align-items:center;">'
        f'{_outcome_badge(deal.autopsy.outcome)}'
        f'<span style="color:{P["text_faint"]};font-size:11px;'
        f'font-family:\'JetBrains Mono\',monospace;">'
        f'{deal.autopsy.outcome_year}</span></div>'
        f'{primary_killer_html}'
        f'</div>'
        f'<div class="da-card__sim">'
        f'<div class="da-card__meta-top">Similarity</div>'
        f'<div class="da-card__sim-val" style="color:{sim_color};">'
        f'{sim_pct:.0f}<span style="font-size:18px;opacity:.7;">%</span>'
        f'</div>'
        f'<div style="font-size:10.5px;color:{sim_color};'
        f'margin-top:2px;font-weight:600;">{html.escape(sim_label)}</div>'
        f'<div style="font-size:9.5px;color:{P["text_faint"]};'
        f'margin-top:2px;font-family:\'JetBrains Mono\',monospace;">'
        f'd = {result.distance:.2f}</div>'
        f'{_similarity_spectrum(result.similarity)}'
        f'</div>'
        f'</div>'
        f'<div class="da-grid2">'
        f'<div>'
        f'<div class="da-card__meta-top">Features that match</div>'
        f'{_feature_chips(result.aligning, kind="aligning")}'
        f'</div>'
        f'<div>'
        f'<div class="da-card__meta-top">Features that diverge</div>'
        f'{_feature_chips(result.diverging, kind="diverging")}'
        f'</div>'
        f'</div>'
        f'<div style="margin-top:18px;">'
        f'{_signature_chart(target, deal.signature)}'
        f'</div>'
        f'<div style="margin-top:16px;font-size:11.5px;color:{P["text_dim"]};'
        f'line-height:1.6;">'
        f'<strong style="color:{P["text"]};">Early warning signs · '
        f'what a diligence tool could have caught:</strong>'
        f'<ul class="da-warnings" style="margin:6px 0 0 20px;">{warnings}</ul>'
        f'</div>'
        f'{lesson_html}'
        f'{quote_html}'
        f'{sources_html}'
        f'</div>'
        f'</div>'
    )


def _target_signature_panel(
    sig: DealSignature, *, heading: str,
    dataset_label: Optional[str] = None,
) -> str:
    rows = []
    for name in FEATURE_NAMES:
        val = getattr(sig, name)
        src = sig.provenance.get(name, "default 0.0")
        tooltip = provenance(
            f'{val:.3f}',
            source=src,
            formula=(
                f'Signature dimension: {FEATURE_LABELS.get(name, name)}. '
                'Range [0.0, 1.0] — higher = more risk. '
                'See module docstring for provenance.'
            ),
            detail=(
                'CCD-derived dimensions come from ingested claims. '
                'Metadata-only dimensions (lease, EBITDAR, DAR, '
                'regulatory, physician concentration) require '
                'explicit deal metadata.'
            ),
        )
        rows.append(
            f'<div class="da-sig-row">'
            f'<span>{html.escape(FEATURE_LABELS.get(name, name))}</span>'
            f'<span class="da-sig-row__val">{tooltip}</span>'
            f'<span class="da-sig-row__src">{html.escape(src)}</span>'
            f'</div>'
        )
    fixture_tag = (
        f'<span style="font-size:10px;color:{P["text_faint"]};'
        f'margin-left:12px;">· {html.escape(dataset_label)}</span>'
    ) if dataset_label else ""
    return (
        f'<div class="da-card" style="margin-bottom:20px;">'
        f'<div class="da-card__body" style="padding-top:14px;padding-bottom:14px;">'
        f'<div class="da-eyebrow" style="margin-bottom:6px;">'
        f'Target signature{fixture_tag}</div>'
        f'<div class="da-h2" style="margin-bottom:12px;">'
        f'{html.escape(heading)}</div>'
        f'{"".join(rows)}'
        f'</div>'
        f'</div>'
    )


def _summary_hero(
    target: DealSignature, matches: List[MatchResult],
    dataset_label: Optional[str],
) -> str:
    n_library = len(historical_library())
    negatives = [m for m in matches if m.deal.autopsy.is_negative]
    positives = [m for m in matches if not m.deal.autopsy.is_negative]
    top = matches[0] if matches else None

    if top is None:
        banner = "No historical matches available."
        banner_class = ""
    elif top.deal.autopsy.is_negative and top.similarity >= 0.80:
        banner = (
            f'⚠ You are underwriting a deal with an '
            f'{top.similarity*100:.0f}% signature match to '
            f'{top.deal.name} ({top.deal.autopsy.outcome_year} — '
            f'{_OUTCOME_PRESENTATION[top.deal.autopsy.outcome][0]}).'
        )
        banner_class = "alert"
    elif top.deal.autopsy.is_negative and top.similarity >= 0.72:
        banner = (
            f'Signature is {top.similarity*100:.0f}% aligned with '
            f'{top.deal.name} — a meaningful resemblance to a deal '
            f'that ended in '
            f'{_OUTCOME_PRESENTATION[top.deal.autopsy.outcome][0].lower()}.'
        )
        banner_class = "warn"
    elif not top.deal.autopsy.is_negative and top.similarity >= 0.72:
        banner = (
            f'Closest signature match is {top.deal.name} '
            f'({top.similarity*100:.0f}%) — a successful exit '
            f'pattern. Survivor-type signature.'
        )
        banner_class = "good"
    else:
        banner = (
            f'No strong match in the library '
            f'(top: {top.deal.name} at {top.similarity*100:.0f}%). '
            f'This target does not cleanly rhyme with either the '
            f'failure or survivor cohort.'
        )
        banner_class = ""

    summary = (
        f"The target's 9-feature risk signature was compared against "
        f"{n_library} historical PE healthcare deals. "
        f"{len(negatives)} of the top {len(matches)} matches ended in "
        f"bankruptcy, distressed sale, or delisting; {len(positives)} "
        f"exited strong. The top match is "
        f"{html.escape(top.deal.name) if top else '—'}."
    )
    fixture_tag = (
        f' · <span style="color:{P["text_faint"]};">'
        f'{html.escape(dataset_label)}</span>'
    ) if dataset_label else ""

    return (
        f'<div style="padding:24px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:24px;">'
        f'<div class="da-eyebrow">Deal Autopsy{fixture_tag}</div>'
        f'<div class="da-h1">Historical Failure-Pattern Match</div>'
        f'<div class="da-callout {banner_class}">{html.escape(banner)}</div>'
        f'<div class="da-callout">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'{summary}</div>'
        f'</div>'
    )


def _library_summary_card() -> str:
    counts = outcomes_summary()
    rows = []
    for outcome, (label, tone) in _OUTCOME_PRESENTATION.items():
        n = counts.get(outcome, 0)
        color = P.get(tone, P["text_dim"])
        rows.append(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:4px 0;font-size:11px;color:{P["text_dim"]};">'
            f'<span style="color:{color};">{html.escape(label)}</span>'
            f'<span style="color:{P["text"]};font-family:\'JetBrains Mono\',monospace;">'
            f'{n}</span>'
            f'</div>'
        )
    total = sum(counts.values())
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:14px 20px;'
        f'margin-bottom:20px;max-width:360px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:8px;">Library composition</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:8px;">{total} historical deals</div>'
        f'{"".join(rows)}'
        f'</div>'
    )


def _library_table() -> str:
    headers = [
        "Deal", "Sponsor", "Sector", "Entry", "Outcome", "Year", "Primary driver",
    ]
    rows: List[List[str]] = []
    keys: List[List[Any]] = []
    for d in historical_library():
        label, tone = _OUTCOME_PRESENTATION.get(
            d.autopsy.outcome, (d.autopsy.outcome, "text_dim"),
        )
        color = P.get(tone, P["text_dim"])
        outcome_html = (
            f'<span style="color:{color};font-weight:600;">'
            f'{html.escape(label)}</span>'
        )
        rows.append([
            d.name, d.sponsor, d.sector.replace("_", " "),
            str(d.entry_year), outcome_html,
            str(d.autopsy.outcome_year),
            d.autopsy.primary_killer or "—",
        ])
        keys.append([
            d.name, d.sponsor, d.sector, d.entry_year,
            d.autopsy.outcome, d.autopsy.outcome_year,
            d.autopsy.primary_killer,
        ])
    return sortable_table(
        headers, rows, name="autopsy_library", sort_keys=keys,
    )


# ────────────────────────────────────────────────────────────────────
# Landing
# ────────────────────────────────────────────────────────────────────

def _matches_table(matches: List[MatchResult]) -> str:
    """Sortable/CSV-exportable flat view of the match ranking —
    inherits power_ui's export + filter + copy behaviour."""
    if not matches:
        return ""
    headers = [
        "Rank", "Deal", "Sponsor", "Sector", "Outcome", "Year",
        "Similarity", "Distance",
    ]
    rows: List[List[str]] = []
    keys: List[List[Any]] = []
    for i, m in enumerate(matches, start=1):
        deal = m.deal
        label, tone = _OUTCOME_PRESENTATION.get(
            deal.autopsy.outcome, (deal.autopsy.outcome, "text_dim"),
        )
        color = P.get(tone, P["text_dim"])
        outcome_html = (
            f'<span style="color:{color};font-weight:600;">'
            f'{html.escape(label)}</span>'
        )
        rows.append([
            str(i), deal.name, deal.sponsor,
            deal.sector.replace("_", " "),
            outcome_html, str(deal.autopsy.outcome_year),
            f"{m.similarity*100:.1f}%",
            f"{m.distance:.3f}",
        ])
        keys.append([
            i, deal.name, deal.sponsor, deal.sector,
            deal.autopsy.outcome, deal.autopsy.outcome_year,
            m.similarity, m.distance,
        ])
    return sortable_table(
        headers, rows, name="autopsy_matches", sort_keys=keys,
    )


def _landing() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    form = (
        f'<form method="GET" action="/diligence/deal-autopsy" '
        f'style="max-width:560px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;'
        f'padding:20px;margin-bottom:20px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:10px;">Fixture mode — auto-build from CCD</div>'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">CCD fixture</label>'
        f'<select name="dataset" style="width:100%;padding:6px 8px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;'
        f'margin-bottom:12px;">'
        f'<option value="">— pick a fixture (optional) —</option>'
        f'{options}</select>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
        + "".join(
            f'<div><label style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
            f'display:block;margin-bottom:2px;">{html.escape(FEATURE_LABELS[name])}</label>'
            f'<input name="{name}" placeholder="0.0 – 1.0" '
            f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
            f'color:{P["text"]};border:1px solid {P["border"]};'
            f'font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            f'</div>'
            for name in FEATURE_NAMES
        )
        + f'</div>'
        f'<div style="margin-top:14px;font-size:10px;color:{P["text_faint"]};'
        f'line-height:1.5;">'
        f'Leave signature fields blank to default to zero. Fields you '
        f'supply override CCD-derived values.</div>'
        f'<button type="submit" style="margin-top:14px;padding:8px 20px;'
        f'background:{P["accent"]};color:{P["panel"]};border:0;'
        f'font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;">Run autopsy match</button>'
        f'</form>'
    )
    explainer = (
        f'<div style="max-width:720px;margin-bottom:24px;'
        f'font-size:13px;color:{P["text_dim"]};line-height:1.65;">'
        f'The Deal Autopsy engine compares your target\'s 9-feature risk '
        f'signature against a curated library of historical PE healthcare '
        f'deals — bankruptcies, distressed sales, delistings, and strong '
        f'exits — and surfaces the closest matches along with the '
        f'partner lesson from each outcome. '
        f'Treat it as a "you\'re about to do X again" check layered on top '
        f'of the rest of the diligence stack.'
        f'</div>'
    )
    body = (
        _scoped_styles()
        + f'<div class="da-wrap">'
        + f'<div style="padding:24px 0 12px 0;">'
        f'<div class="da-eyebrow">RCM Diligence</div>'
        f'<div class="da-h1">Deal Autopsy — Historical Failure Match</div>'
        f'</div>'
        + explainer
        + _library_summary_card()
        + form
        + f'<div class="da-section-label">Full library</div>'
        + _library_table()
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Deal Autopsy",
        subtitle="Historical failure-pattern match",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_deal_autopsy_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    dataset = _first(qs, "dataset")
    custom_sig = _signature_from_qs(qs)
    dataset_label: Optional[str] = None

    if dataset:
        ds_path = _resolve_dataset(dataset)
        if ds_path is None:
            return _landing()
        try:
            ccd = ingest_dataset(ds_path)
        except Exception as exc:  # noqa: BLE001
            return chartis_shell(
                f'<div style="padding:24px;color:{P["negative"]};">'
                f'Failed to ingest {html.escape(dataset)}: '
                f'{html.escape(str(exc))}</div>',
                "Deal Autopsy",
            )
        metadata = _metadata_from_qs(qs)
        if custom_sig is not None:
            # Merge: custom_sig overrides what CCD produced.
            metadata = {**metadata}
            for name in FEATURE_NAMES:
                if qs.get(name):
                    metadata[name] = getattr(custom_sig, name)
        target = signature_from_ccd(ccd, metadata=metadata)
        for lbl, fx_name in AVAILABLE_FIXTURES:
            if lbl == dataset:
                dataset_label = fx_name
                break
        dataset_label = dataset_label or dataset
        heading = dataset_label
    elif custom_sig is not None:
        target = custom_sig
        heading = "Custom signature"
    else:
        return _landing()

    top_k_raw = _first(qs, "top_k", "5")
    try:
        top_k = max(1, min(12, int(top_k_raw)))
    except ValueError:
        top_k = 5

    matches = match_target(
        target, historical_library(), top_k=top_k,
    )

    if not matches:
        body = (
            _scoped_styles()
            + '<div class="da-wrap">'
            + _summary_hero(target, matches, dataset_label)
            + _target_signature_panel(
                target, heading=heading, dataset_label=dataset_label,
            )
            + f'<div style="padding:24px;color:{P["text_faint"]};">'
              f'No matches found in the library.</div>'
            + '</div>'
        )
        return chartis_shell(body, "Deal Autopsy")

    cards = "".join(
        _match_card(m, target) for m in matches
    )
    body = (
        _scoped_styles()
        + '<div class="da-wrap">'
        + _summary_hero(target, matches, dataset_label)
        + _target_signature_panel(
            target, heading=heading, dataset_label=dataset_label,
        )
        + f'<div class="da-section-label">'
          f'Top {len(matches)} matches · ranked by similarity</div>'
        + cards
        + f'<div class="da-section-label">'
          f'Matches · sortable + exportable</div>'
        + _matches_table(matches)
        + '</div>'
    )
    return chartis_shell(
        body, f"Deal Autopsy — {heading}",
        subtitle="Historical failure-pattern match",
    )
