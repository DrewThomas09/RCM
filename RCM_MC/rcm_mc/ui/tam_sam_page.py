"""TAM / SAM / SOM Builder — /diligence/tam-sam.

Driver-tree market sizing the way CDD teams actually build it (see
diligence/tam_sam.py): an editable driver chain, segment bands, a TAM →
SAM → SOM funnel, a growth-driver-decomposed projection, and one-click
formatted exports (CSV + real .xlsx) so the output drops straight into
the deal team's model.

Every chain value is editable via the form (qs overrides the template
defaults); the audit trail renders the running value at every step — the
chain IS the methodology, shown, not hidden.
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Any, Dict, List, Optional

from ..diligence.tam_sam import (
    ARCHETYPES, TEMPLATES, TamSamModel, compute, fertility_ivf_template,
    monte_carlo,
)
from ._chartis_kit import (
    chartis_shell, ck_empty_state, ck_kpi_block, ck_next_section,
    ck_page_title, ck_panel, ck_source_link, ck_source_purpose,
)

_CSS = """
<style>
.ts2-chain{width:100%;border-collapse:collapse;font-size:13px;}
.ts2-chain th{font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-text-dim,#465366);text-align:left;
 padding:6px 10px;border-bottom:2px solid var(--sc-rule,#c9c1ac);}
.ts2-chain td{padding:7px 10px;border-bottom:1px solid var(--sc-rule,#e4ddcd);}
.ts2-chain .r{text-align:right;font-variant-numeric:tabular-nums;
 font-family:var(--sc-mono);}
.ts2-chain input{width:120px;padding:4px 7px;border:1px solid
 var(--sc-rule,#c9c1ac);border-radius:2px;font-size:12.5px;text-align:right;
 font-variant-numeric:tabular-nums;}
.ts2-src{font-size:10.5px;color:var(--sc-text-faint,#8b94a0);}
.ts2-run{font-weight:600;color:var(--sc-navy,#0b2341);}
.ts2-form-bar{display:flex;gap:10px;align-items:center;margin:12px 0 0;
 flex-wrap:wrap;}
.ts2-btn{padding:8px 16px;background:var(--sc-navy,#0b2341);color:#fff;
 border:0;border-radius:2px;font-size:12px;font-weight:600;cursor:pointer;}
.ts2-export{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;background:#fff;
 color:var(--sc-navy,#0b2341);font-size:12px;font-weight:600;
 text-decoration:none;}
.ts2-drv{display:flex;justify-content:space-between;gap:14px;padding:7px 2px;
 border-bottom:1px solid var(--sc-rule,#e4ddcd);font-size:12.5px;}
.ts2-drv .pct{font-family:var(--sc-mono);font-variant-numeric:tabular-nums;
 font-weight:600;}
.ts2-tmpl{display:flex;gap:8px;margin:0 0 14px;flex-wrap:wrap;}
.ts2-tmpl a{padding:6px 13px;border:1px solid var(--sc-rule,#c9c1ac);
 border-radius:2px;font-size:12px;text-decoration:none;
 color:var(--sc-text,#1a2332);}
.ts2-tmpl a.on{border-color:var(--sc-teal,#155752);
 color:var(--sc-teal-ink,#0f3d39);font-weight:600;}
</style>
"""


def _fmt_money(v: float) -> str:
    # House rule: money always carries 2 decimals ($450.25M, $1,204.50) at
    # every magnitude — the $M branch used to print 1dp, which read as a
    # different precision convention from the $B branch two lines above it.
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.2f}M"
    return f"${v:,.2f}"


def _fmt_pct(v: float, *, sign: bool = False) -> str:
    """House percent format — 1 decimal, never 0 or 2.

    Every rate on this page routes through here so the applied-rate column,
    the segment shares, the payer mix, and the funnel sub-labels read at one
    precision instead of the three they drifted into."""
    return f"{v:+,.1f}%" if sign else f"{v:,.1f}%"


def _fmt_multiple(v: Optional[float]) -> str:
    """House multiple format — 2 decimals + ``x`` (``2.50x``)."""
    return f"{v:,.2f}x" if v else "—"


def _fmt_step_value(st: Dict[str, Any]) -> str:
    if st["op"] == "rate":
        return _fmt_pct(st["value"] * 100)
    if st["op"] == "price":
        # A unit price is never abbreviated to $M — the partner needs the
        # literal rate to check it against a fee schedule.
        return f"${st['value']:,.2f}"
    # Plain decimal — :,.4g goes scientific on populations (3.66e+06).
    v = st["value"]
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}"


def _fmt_running(st: Dict[str, Any]) -> str:
    # Once a price step lands, the running value is dollars.
    return (_fmt_money(st["running"]) if st["op"] == "price"
            else f"{st['running']:,.0f}")


def _build_href(template: str, scenario: str = "base", sort: str = "tam",
                *, explicit_scenario: bool = False) -> str:
    """Canonical link back into this builder with the partner's context kept.

    ``template`` arrives straight off the query string, so it is
    percent-encoded (not merely HTML-escaped) — it lands inside a URL, and a
    key carrying ``&`` or ``#`` would otherwise silently truncate the link.
    Non-default scenario/sort ride along so switching vertical (or
    re-sorting) doesn't quietly reset the partner to Base/TAM; the defaults
    are dropped so the everyday URL stays short. ``explicit_scenario`` keeps
    ``scenario=base`` on the wire for the scenario chip row, where the Base
    chip needs a self-describing link."""
    href = (
        "/diligence/tam-sam?template="
        f"{urllib.parse.quote(str(template), safe='')}"
    )
    if scenario in ("conservative", "aggressive") or (
            explicit_scenario and scenario == "base"):
        href += f"&scenario={scenario}"
    if sort in ("growth", "archetype"):
        href += f"&sort={sort}"
    return html.escape(href, quote=True)


def _source_list_links(text: str, sep: str = ", ") -> str:
    """Link each citation in a comma-joined source list independently.

    The archetype's ``primary_sources`` is a list ("NPPES, POS file, Care
    Compare, HCRIS facility counts, …"). Routing the WHOLE string through
    ck_source_link would make every citation in it point at whichever single
    dataset matched longest — a wrong link looks verified. Splitting first
    means each name resolves to its own dataset or stays plain text."""
    if not text:
        return ""
    return sep.join(ck_source_link(part.strip())
                    for part in str(text).split(",") if part.strip())


def _cited_prose(text: str) -> str:
    """Link the citation clause of a ``"<claim> — <commentary>"`` string.

    Triangulation bases and deep-dive source notes read like "Medicare
    hospice spend ~$25B (MedPAC) - scope check vs the users-days-rate
    build". Linking the entire sentence would turn a paragraph into one
    hyperlink; linking only the clause before the first em-dash or semicolon
    keeps the methodology commentary as prose."""
    s = str(text or "")
    if not s:
        return ""
    cuts = [i for i in (s.find("—"), s.find(";")) if i > 0]
    if not cuts:
        return ck_source_link(s)
    i = min(cuts)
    lead = " " if s[i] == "—" else ""
    return (f'{ck_source_link(s[:i].strip())}{lead}{html.escape(s[i])} '
            f'{html.escape(s[i + 1:].strip())}')


def model_from_qs(qs: Dict[str, List[str]]) -> TamSamModel:
    """Resolve template + apply qs overrides (every chain value, sam/som
    shares, growth drivers — all clamped to sane ranges)."""
    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    tmpl_key = first("template", "fertility_ivf")
    factory = TEMPLATES.get(tmpl_key, fertility_ivf_template)
    model = factory()

    def fnum(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            x = float(v.replace(",", "").replace("$", "").replace("%", ""))
        except ValueError:
            return None
        if x != x or x in (float("inf"), float("-inf")):
            return None
        return x

    for i, st in enumerate(model.chain):
        ov = fnum(f"step{i}")
        if ov is not None and ov >= 0:
            # Rates arrive as percent points from the form (2.3 → 0.023).
            st.value = ov / 100.0 if st.op == "rate" else ov
    sam = fnum("sam_share")
    if sam is not None:
        model.sam_share = max(0.0, min(100.0, sam)) / 100.0
    som = fnum("som_share")
    if som is not None:
        model.som_share = max(0.0, min(100.0, som)) / 100.0
    # Scenario presets — Conservative halves tailwinds and amplifies
    # headwinds ×1.5; Aggressive mirrors. Applied BEFORE the explicit
    # per-driver overrides so a typed value always wins.
    scenario = first("scenario", "base").lower()
    if scenario in ("conservative", "aggressive"):
        for g in model.growth_drivers:
            if scenario == "conservative":
                g.annual_pct = (g.annual_pct * 0.5 if g.annual_pct > 0
                                else g.annual_pct * 1.5)
            else:
                g.annual_pct = (g.annual_pct * 1.5 if g.annual_pct > 0
                                else g.annual_pct * 0.5)
    for i, g in enumerate(model.growth_drivers):
        ov = fnum(f"growth{i}")
        if ov is not None and -50.0 <= ov <= 100.0:
            g.annual_pct = ov
    return model


def _state_bar_svg(states: List[Dict[str, Any]], width: int = 560) -> str:
    """Horizontal bars: facilities by state; the independent slice (the
    acquirable pool) overlaid in teal so whitespace is visible at a
    glance. Inline SVG, house pattern."""
    if not states:
        return ""
    mx = max(s["facilities"] for s in states) or 1
    row_h, pad_l, pad_r = 22, 46, 110
    bar_w = width - pad_l - pad_r
    # The aria-label carries what the picture says, not just what it is —
    # a screen-reader user gets the scale of the bars and the overlay's
    # meaning rather than the bare words "facilities by state". Describe
    # the LARGEST bar, not states[0]: the caller's ordering is not always
    # by facility count (hospitals ranks by filed NPR).
    top = max(states, key=lambda s: s["facilities"])
    summary = (
        f'Facilities by state — {len(states)} states shown, bars scaled to '
        f'{top["state"]} at {top["facilities"]:,} facilities; the teal '
        'overlay on each bar is the independent (acquirable) slice'
    )
    parts = [f'<svg width="{width}" height="{len(states)*row_h + 6}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             f'aria-label="{html.escape(summary, quote=True)}">'
             f'<title>{html.escape(summary)}</title>']
    for i, s in enumerate(states):
        y = i * row_h + 4
        w = s["facilities"] / mx * bar_w
        w_ind = s["independent"] / mx * bar_w
        parts.append(
            f'<text x="{pad_l-6}" y="{y+11}" text-anchor="end" '
            'font-family="monospace" font-size="10.5" '
            f'fill="#465366">{html.escape(s["state"])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{w:.1f}" height="13" '
            'fill="#0b2341" opacity="0.85"/>'
            f'<rect x="{pad_l}" y="{y}" width="{w_ind:.1f}" height="13" '
            'fill="#1F7A75"/>'
            f'<text x="{pad_l+w+6:.1f}" y="{y+11}" font-family="monospace" '
            f'font-size="10" fill="#465366">{s["facilities"]:,} '
            f'({s["independent"]} indep)</text>'
        )
    parts.append('</svg>')
    return "".join(parts)


def _projection_svg(projection: List[Dict[str, Any]],
                    width: int = 640, height: int = 220) -> str:
    """TAM/SAM/SOM lines over the horizon — the IC's one-look growth
    picture. Inline SVG, house palette, end-value labels."""
    if len(projection) < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 56, 110, 14, 26
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    mx = max(p["tam"] for p in projection) or 1
    n = len(projection) - 1
    series = [("TAM", "tam", "#0b2341"), ("SAM", "sam", "#1F7A75"),
              ("SOM", "som", "#a08227")]
    last = projection[-1]
    parts = [f'<svg width="{width}" height="{height}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="TAM SAM SOM projection">'
             # Hover tooltip for the sighted partner — the end-state the
             # three lines are heading toward, without reading the table.
             f'<title>TAM / SAM / SOM projection over '
             f'{len(projection) - 1} years — by Y{last["year"]}: TAM '
             f'{_fmt_money(last["tam"])}, SAM {_fmt_money(last["sam"])}, '
             f'SOM {_fmt_money(last["som"])}</title>']
    for i, p in enumerate(projection):
        x = pad_l + i / n * pw
        parts.append(
            f'<text x="{x:.0f}" y="{height-8}" text-anchor="middle" '
            'font-family="monospace" font-size="9.5" fill="#7a8699">'
            f'Y{p["year"]}</text>')
    for label, key, color in series:
        pts = " ".join(
            f"{pad_l + i / n * pw:.1f},"
            f"{pad_t + (1 - p[key] / mx) * ph:.1f}"
            for i, p in enumerate(projection))
        y_end = pad_t + (1 - projection[-1][key] / mx) * ph
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            'stroke-width="2"/>'
            f'<text x="{pad_l + pw + 6}" y="{y_end + 4:.1f}" '
            'font-family="monospace" font-size="10" '
            f'fill="{color}">{label} {_fmt_money(projection[-1][key])}'
            '</text>')
        y0 = pad_t + (1 - projection[0][key] / mx) * ph
        parts.append(f'<circle cx="{pad_l}" cy="{y0:.1f}" r="2.5" '
                     f'fill="{color}"/>')
    parts.append("</svg>")
    return "".join(parts)


def _sources_panel(out: Dict[str, Any],
                   dive: Optional[Dict[str, Any]]) -> str:
    """Numbered source footnotes — every default in the build traces to a
    named public source. The defensibility layer: an IC member (or a
    trainee) can check any number against where it came from."""
    items: List[str] = []
    seen = set()
    for st in out["steps"]:
        if st["source"] and st["source"] not in seen:
            seen.add(st["source"])
            items.append(f'{html.escape(st["name"])} — '
                         f'{ck_source_link(st["source"])}')
    for g in out["growth_drivers"]:
        if g["note"] and g["note"] not in seen:
            seen.add(g["note"])
            items.append(f'{html.escape(g["name"])} (growth driver) — '
                         f'{_cited_prose(g["note"])}')
    if dive:
        for k in ("facility_source", "quality_source"):
            v = dive.get(k)
            if v and v not in seen:
                seen.add(v)
                items.append(_cited_prose(v))
    if out.get("basis_note"):
        items.append(_cited_prose(out["basis_note"]))
    if not items:
        # The blank scaffold carries no sourced defaults — say so rather
        # than rendering an empty numbered list under a "sources" heading,
        # which reads as "we lost the citations".
        return ck_panel(
            ck_empty_state(
                "No sourced defaults in this build.",
                "The blank scaffold ships with unsourced placeholder "
                "drivers. Pick a vertical template to inherit its public-"
                "data citations, or type your engagement figures into the "
                "driver chain and record the source in the deal file.",
                eyebrow="Sources",
                cta_label="Start from a sized vertical",
                cta_href="/diligence/tam-sam?template=fertility_ivf",
            ),
            title="Sources & footnotes · every default traces to a named "
                  "public source",
        )
    lis = "".join(
        f'<li style="margin:0 0 6px;"><span style="font-family:'
        f'var(--sc-mono);color:#7a8699;">[{i+1}]</span> {t}</li>'
        for i, t in enumerate(items))
    return ck_panel(
        f'<ol style="list-style:none;margin:0;padding:0;font-size:12px;'
        f'line-height:1.5;color:#465366;">{lis}</ol>'
        '<p class="ts2-src" style="margin:9px 0 0;">Underlined citations '
        'open the public dataset they came from — check any number at '
        'its origin.</p>',
        title="Sources & footnotes · every default traces to a named "
              "public source",
    )


def _segment_bar_svg(segments: List[Dict[str, Any]],
                     width: int = 640) -> str:
    """One stacked bar: how the TAM splits across segments — the
    composition picture above the segment table. House categorical
    hues; ★ marker on the fastest grower; labels inline where the
    slice is wide enough, legend beneath otherwise."""
    if not segments:
        return ""
    palette = ["#0b2341", "#1F7A75", "#b8732a", "#a98545", "#5b6b85",
               "#8a5a44", "#46604a"]
    h, bar_h = 64, 26
    # Slice labels are clipped to 22 chars to fit the bar; the untruncated
    # composition lives in the SVG <title> so a hover (and the tooltip a
    # partner reaches for on an unfamiliar segment name) resolves it.
    full = " \u00b7 ".join(
        f'{s["name"]} {_fmt_pct(max(0.0, float(s.get("share_of_volume") or 0)) * 100)}'
        for s in segments)
    parts = [f'<svg width="{width}" height="{h}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Segment composition">'
             f'<title>Segment composition \u2014 {html.escape(full)}</title>']
    x = 0.0
    legend: List[str] = []
    for i, s in enumerate(segments):
        share = max(0.0, float(s.get("share_of_volume") or 0))
        w = share * width
        color = palette[i % len(palette)]
        star = " \u2605" if s.get("is_fastest") else ""
        name = str(s["name"])
        clipped = name[:22]
        # Slice labels stay at 0dp: they sit INSIDE the bar and a 110px
        # slice cannot carry "Commercial payer 23.4%". The segment table
        # directly below prints the house 1-decimal share.
        label = f'{clipped}{star} {share*100:.0f}%'
        title = (f'{name}{star} \u2014 '
                 f'{_fmt_pct(share * 100)} of volume')
        parts.append(
            f'<rect x="{x:.1f}" y="6" width="{max(w,1):.1f}" '
            f'height="{bar_h}" fill="{color}">'
            f'<title>{html.escape(title)}</title></rect>')
        if w >= 110:
            parts.append(
                f'<text x="{x + w/2:.1f}" y="{6 + bar_h/2 + 4}" '
                'text-anchor="middle" font-family="sans-serif" '
                f'font-size="10" fill="#ffffff">{html.escape(label)}'
                f'<title>{html.escape(title)}</title></text>')
        else:
            legend.append(
                f'<span title="{html.escape(title, quote=True)}" '
                f'style="display:inline-flex;align-items:center;'
                f'gap:4px;margin-right:12px;font-size:10.5px;'
                f'color:#465366;"><span style="width:9px;height:9px;'
                f'background:{color};display:inline-block;"></span>'
                f'{html.escape(label)}</span>')
        x += w
    parts.append('</svg>')
    legend_html = (f'<div style="margin:2px 0 6px;">{"".join(legend)}'
                   '</div>' if legend else "")
    return "".join(parts) + legend_html


def _derive_agenda_items(out: Dict[str, Any]) -> List[str]:
    """Plain-text agenda items — single source for the page panel and
    the exports, so the workbook never carries a thinner question list
    than the screen."""
    items: List[str] = []
    tri = out.get("triangulation")
    if tri and tri["band"] in ("amber", "red"):
        items.append(
            f'Reconcile the sizing: bottom-up '
            f'({_fmt_money(tri["bottom_up_tam"])}) vs top-down '
            f'({_fmt_money(tri["top_down_tam"])}) diverge '
            f'{_fmt_pct(tri["gap_pct"])} ({tri["band"].upper()}) — check '
            f'segmentation, payer mix, and the top-down basis '
            f'({tri.get("top_down_source", "")})')
    for g in out["growth_drivers"]:
        if g["annual_pct"] < 0:
            note = f' — {g["note"]}' if g.get("note") else ""
            items.append(
                f'Quantify the exposure: {g["name"]} '
                f'(priced {g["annual_pct"]:+.1f}%/yr){note}')
    fastest = next((s for s in out["segments"] if s.get("is_fastest")),
                   None)
    if fastest:
        note = f' — {fastest["note"]}' if fastest.get("note") else ""
        items.append(
            f'Validate the growth thesis: can the target capture '
            f'{fastest["name"]} '
            f'({_fmt_pct(fastest["growth_pct"], sign=True)}/yr)?'
            f'{note}')
    for s in out["segments"]:
        if (s.get("growth_pct") or 0) < 0:
            items.append(
                f'Size the decline: what share of the target revenue '
                f'sits in {s["name"]} '
                f'({_fmt_pct(s["growth_pct"], sign=True)}/yr)?')
    if out.get("sam_note"):
        items.append(f'Confirm addressability: {out["sam_note"]}')
    if out.get("som_note"):
        items.append(f'Pressure-test share: {out["som_note"]}')
    return items


def _diligence_agenda_panel(out: Dict[str, Any]) -> str:
    """The training layer: a working diligence agenda DERIVED from the
    build itself — every priced headwind becomes a quantification
    question, the fastest segment becomes a validation question, the
    SAM/SOM notes become the addressability and share questions.
    Nothing hand-written per industry; nothing the build doesn't
    already assert."""
    items: List[str] = []
    tri = out.get("triangulation")
    if tri and tri["band"] in ("amber", "red"):
        items.append(
            f'<strong>Reconcile the sizing:</strong> bottom-up '
            f'({_fmt_money(tri["bottom_up_tam"])}) vs top-down '
            f'({_fmt_money(tri["top_down_tam"])}) diverge '
            f'{_fmt_pct(tri["gap_pct"])} ({tri["band"].upper()}) — check '
            f'segmentation, payer mix, and the top-down basis '
            f'({_cited_prose(tri.get("top_down_source", ""))})')
    for g in out["growth_drivers"]:
        if g["annual_pct"] < 0:
            note = f' — {g["note"]}' if g.get("note") else ""
            items.append(
                f'<strong>Quantify the exposure:</strong> '
                f'{html.escape(g["name"])} (priced '
                f'{g["annual_pct"]:+.1f}%/yr){html.escape(note)}')
    fastest = next((s for s in out["segments"] if s.get("is_fastest")),
                   None)
    if fastest:
        note = (f' — {fastest["note"]}' if fastest.get("note") else "")
        items.append(
            f'<strong>Validate the growth thesis:</strong> can the '
            f'target capture {html.escape(fastest["name"])} '
            f'({_fmt_pct(fastest["growth_pct"], sign=True)}/yr)?'
            f'{html.escape(note)}')
    declining = [s for s in out["segments"]
                 if (s.get("growth_pct") or 0) < 0]
    for s in declining:
        items.append(
            f'<strong>Size the decline:</strong> what share of the '
            f'target\u2019s revenue sits in '
            f'{html.escape(s["name"])} '
            f'({_fmt_pct(s["growth_pct"], sign=True)}/yr)?')
    if out.get("sam_note"):
        items.append(
            f'<strong>Confirm addressability:</strong> '
            f'{html.escape(out["sam_note"])}')
    if out.get("som_note"):
        items.append(
            f'<strong>Pressure-test share:</strong> '
            f'{html.escape(out["som_note"])}')
    if not items:
        # Reachable today via ?template=blank (and any build with no priced
        # headwind, no fastest segment and no SAM/SOM notes): the panel used
        # to render an empty <ol> under its heading, which reads as a bug.
        return ck_panel(
            ck_empty_state(
                "This build implies no questions yet.",
                "The agenda is derived from the build itself — price a "
                "headwind as a negative growth driver, set per-segment "
                "growth, or write the SAM/SOM addressability notes, and "
                "the questions appear here and in the exports.",
                eyebrow="Diligence agenda",
                cta_label="Edit the driver chain",
                cta_href="#ts-chain",
            ),
            title="Diligence agenda · the questions this build implies",
        )
    lis = "".join(
        f'<li style="margin:0 0 8px;line-height:1.5;">'
        f'<span style="font-family:var(--sc-mono);color:#7a8699;'
        f'margin-right:6px;">Q{i+1}</span>{t}</li>'
        for i, t in enumerate(items))
    return ck_panel(
        f'<ol style="list-style:none;margin:0;padding:0;font-size:12.5px;'
        f'color:#1a2332;">{lis}</ol>'
        '<p class="ts2-src" style="margin:8px 0 0;">Auto-derived from '
        'this build\u2019s own drivers and notes \u2014 every priced '
        'headwind becomes a quantification question. Edit the drivers '
        'above and the agenda follows.</p>',
        title="Diligence agenda \u00b7 the questions this build implies",
    )


def _industry_panels(tmpl_key: str) -> str:
    """Real-data deep-dive panels under the sizing build (additive — the
    registry decides which industries have a data layer yet)."""
    from ..diligence.industry_deep_dive import deep_dive_for
    dive = deep_dive_for(tmpl_key)
    if not dive:
        return ""
    if dive.get("deals_only"):
        # No vendored facility file for this vertical — geography is
        # omitted rather than fabricated; the deal history is real.
        sd = dive["sector_deals"]
        if not sd.get("n"):
            return ""
        med = sd.get("median_moic")
        mult = sd.get("median_entry_multiple")
        yrs = (f", {sd['year_min']}–{sd['year_max']}"
               if sd.get("year_min") else "")
        med_s = _fmt_multiple(med)
        mult_s = _fmt_multiple(mult)
        return ck_panel(
            f'<p class="ck-section-body" style="margin:0 0 8px;">'
            f'<strong>{sd["n"]} corpus deals</strong> '
            f'({sd.get("n_realized", 0)} realized{yrs}) · '
            f'median realized MOIC <strong>{med_s}</strong> · '
            f'median entry EV/EBITDA <strong>{mult_s}</strong> · '
            f'<a class="ck-link" href="{html.escape(dive["deals_href"])}">'
            'open the deals →</a></p>'
            f'<p class="ts2-src" style="margin:0;">'
            f'{html.escape(dive.get("geo_note", ""))}</p>',
            title="What this sector traded for",
        )
    pool_label = dive.get("pool_label", "Independent")
    cap_label = dive.get("capacity_label")
    q_label = dive.get("quality_label", "Quality (med)")
    # The payer dimension — present when the dive computes it (hospitals:
    # filed Medicare day share, state median from HCRIS).
    has_payer = any(s.get("medicare_mix_med") is not None
                    for s in dive["top_states"])
    # 1 · State footprint — top 10 states with the whitespace overlay.
    rows = ""
    for s in dive["top_states"]:
        q = dive["quality_by_state"].get(s["state"]) or {}
        qv = q.get("value")
        qs_s = (f"{qv:,.1f}" if qv is not None and qv < 100
                else f"{qv:,.0f}" if qv is not None else "—")
        cap_td = (f'<td class="r">{s["stations"]:,}</td>'
                  if cap_label else "")
        mm = s.get("medicare_mix_med")
        payer_td = (
            f'<td class="r">{_fmt_pct(mm * 100)}</td>' if has_payer and
            mm is not None else ('<td class="r">—</td>' if has_payer
                                 else "")
        )
        rows += (
            '<tr>'
            f'<th scope="row" style="font-weight:400;">'
            f'{html.escape(s["state"])}</th>'
            f'<td class="r">{s["facilities"]:,}</td>'
            f'{cap_td}'
            f'<td class="r">{s["independent"]:,}</td>'
            f'<td class="r">{_fmt_pct(s["independent_share"] * 100)}</td>'
            f'{payer_td}'
            f'<td class="r">{qs_s}</td></tr>'
        )
    if not rows:
        # A vertical whose vendored facility file loads but yields no state
        # rows would otherwise print a headed table with nothing under it.
        rows = (
            f'<tr><td colspan="{4 + bool(cap_label) + bool(has_payer)}" '
            'class="ts2-src" style="padding:14px 10px;">No state rows in '
            'the vendored snapshot for this vertical.</td></tr>'
        )
    footprint = ck_panel(
        '<div style="display:grid;grid-template-columns:minmax(0,1fr) '
        'minmax(0,1fr);gap:24px;align-items:start;">'
        f'<div>{_state_bar_svg(dive["top_states"])}'
        '<p class="ts2-src" style="margin:8px 0 0;">Navy = all '
        f'facilities · teal = {html.escape(dive.get("pool_note", "the pool"))}. '
        f'{_cited_prose(dive["facility_source"])}.</p></div>'
        '<table class="ts2-chain"><thead><tr>'
        '<th scope="col">State</th>'
        '<th scope="col" style="text-align:right;">Facilities</th>'
        + (f'<th scope="col" style="text-align:right;">'
           f'{html.escape(cap_label)}</th>' if cap_label else "")
        + f'<th scope="col" style="text-align:right;">'
        f'{html.escape(pool_label)}</th>'
        f'<th scope="col" style="text-align:right;">'
        f'{html.escape(pool_label)} share</th>'
        + ('<th scope="col" style="text-align:right;">Medicare mix (med)'
           '</th>' if has_payer else "")
        + f'<th scope="col" style="text-align:right;">'
        f'{html.escape(q_label)}</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        '</div>'
        f'<p class="ts2-src" style="margin:10px 0 0;">'
        f'{_cited_prose(dive["quality_source"])}. '
        f'<a class="ck-link" href="{html.escape(dive["screener_href"])}">'
        'Open the screener for this vertical →</a></p>',
        title=f"State footprint · top 10 of {dive['n_facilities']:,} "
              "facilities (live CMS data)",
    )
    # 2 · Consolidation + whitespace.
    chain_rows = "".join(
        '<tr>'
        f'<th scope="row" style="font-weight:400;">'
        f'{html.escape(c["org"])}</th>'
        f'<td class="r">{c["facilities"]:,}</td>'
        f'<td class="r">{_fmt_pct(c["share"] * 100)}</td></tr>'
        for c in dive["chains"]
    ) or (
        '<tr><td colspan="3" class="ts2-src" style="padding:14px 10px;">'
        'No named operators in the vendored snapshot for this vertical — '
        'the pool below is the whole market.</td></tr>'
    )
    if dive.get("whitespace_mode") == "density":
        ws = ", ".join(
            f'{s["state"]} ({s["per_10k_seniors"]:.1f}/10K)'
            for s in dive["whitespace_states"][:5])
    else:
        ws = ", ".join(
            f'{s["state"]} ({s["independent"]})'
            for s in dive["whitespace_states"][:5])
    duo = dive.get("duopoly_share")
    duo_bit = (
        f'Top-2 chains hold <strong>{_fmt_pct(duo * 100)}</strong> of '
        'facilities; ' if duo else ""
    )
    # Chain-concentration HHI (DOJ/FTC scale) — the standard read on how
    # consolidated the operator layer is. <1500 unconcentrated · 1500–
    # 2500 moderate · >2500 highly concentrated.
    from ..diligence.industry_deep_dive import _chain_hhi
    # HHI only means something over named OPERATORS (chains_label
    # "Chain"); ownership-type / size-tier buckets aren't operators.
    hhi = (_chain_hhi(dive["chains"], dive.get("pool_label", "Independent"))
           if dive.get("chains_label") == "Chain" else None)
    hhi_bit = ""
    if hhi is not None:
        band = ("highly concentrated" if hhi > 2500
                else "moderately concentrated" if hhi >= 1500
                else "unconcentrated")
        tone = ("#b5321e" if hhi > 2500 else "#b8732a" if hhi >= 1500
                else "#0a8a5f")
        hhi_bit = (
            f' Chain-concentration <strong style="color:{tone};">HHI '
            f'{hhi:,.0f}</strong> ({band}, DOJ/FTC scale — named '
            'operators only).'
        )
    consolidation = ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        f'<th scope="col">{html.escape(dive.get("chains_label", "Chain"))}'
        '</th>'
        '<th scope="col" style="text-align:right;">Facilities</th>'
        '<th scope="col" style="text-align:right;">Share</th>'
        f'</tr></thead><tbody>{chain_rows}</tbody></table>'
        f'<p class="ck-section-body" style="margin:12px 0 0;">'
        f'{duo_bit}<strong>{dive["n_independent"]:,} '
        f'{html.escape(pool_label.lower())}</strong> — '
        f'{html.escape(dive.get("pool_note", ""))}.{hhi_bit} Whitespace '
        f'({html.escape(dive.get("whitespace_note", ""))}): '
        f'<strong>{html.escape(ws)}</strong>.</p>',
        title="Consolidation map · who owns the market",
    )
    # 3 · What the sector traded for.
    sd = dive["sector_deals"]
    deals_band = ""
    if sd.get("n"):
        med = sd.get("median_moic")
        mult = sd.get("median_entry_multiple")
        yrs = (f", {sd['year_min']}–{sd['year_max']}"
               if sd.get("year_min") else "")
        med_s = _fmt_multiple(med)
        mult_s = _fmt_multiple(mult)
        deals_band = ck_panel(
            f'<p class="ck-section-body" style="margin:0;">'
            f'<strong>{sd["n"]} corpus deals</strong> '
            f'({sd.get("n_realized", 0)} realized{yrs}) · '
            f'median realized MOIC <strong>{med_s}</strong> · '
            f'median entry EV/EBITDA <strong>{mult_s}</strong> · '
            f'<a class="ck-link" href="{html.escape(dive["deals_href"])}">'
            'open the deals →</a></p>',
            title="What this sector traded for",
        )
    return footprint + consolidation + deals_band


def _tornado_panel(model: TamSamModel, tam: float) -> str:
    """±20% driver sensitivity — which assumption moves the answer.
    Horizontal low–high bars around the base TAM, sorted by impact."""
    from ..diligence.tam_sam import sensitivity
    rows = sensitivity(model)
    if not rows or tam <= 0:
        # The jump nav ships a "Sensitivity" chip unconditionally, so an
        # empty return left that anchor pointing at nothing. Say why the
        # tornado is absent instead of scrolling the partner into a gap.
        return ck_panel(
            ck_empty_state(
                "No drivers to swing yet.",
                "The tornado needs a positive TAM and at least one chain "
                "driver. Enter the population, utilization and price steps "
                "in the driver chain and the ±20% sensitivity appears here.",
                eyebrow="Sensitivity",
                cta_label="Edit the driver chain",
                cta_href="#ts-chain",
            ),
            title="Driver sensitivity · ±20% tornado",
        )
    width, row_h, pad_l, pad_r = 640, 26, 230, 96
    pw = width - pad_l - pad_r
    lo_all = min(r["tam_low"] for r in rows)
    hi_all = max(r["tam_high"] for r in rows)
    span = (hi_all - lo_all) or 1
    parts = [f'<svg width="{width}" height="{len(rows)*row_h + 22}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Driver sensitivity tornado">'
             f'<title>±20% driver sensitivity around a base TAM of '
             f'{_fmt_money(tam)} — {html.escape(str(rows[0]["name"]))} '
             f'swings it most, from {_fmt_money(rows[0]["tam_low"])} to '
             f'{_fmt_money(rows[0]["tam_high"])}</title>']
    x_base = pad_l + (tam - lo_all) / span * pw
    parts.append(
        f'<line x1="{x_base:.1f}" y1="4" x2="{x_base:.1f}" '
        f'y2="{len(rows)*row_h + 8}" stroke="#7a8699" '
        'stroke-dasharray="3,3" stroke-width="1"/>')
    for i, r in enumerate(rows):
        y = i * row_h + 12
        x_lo = pad_l + (r["tam_low"] - lo_all) / span * pw
        x_hi = pad_l + (r["tam_high"] - lo_all) / span * pw
        # Driver names clip at 32 chars in the gutter — the <title> carries
        # the full name plus the swing, so a clipped label is never a
        # dead end.
        r_title = (f'{r["name"]} — ±20% swings TAM '
                   f'{_fmt_money(r["tam_low"])} to '
                   f'{_fmt_money(r["tam_high"])} (base {_fmt_money(tam)})')
        parts.append(
            f'<text x="{pad_l-8}" y="{y+5}" text-anchor="end" '
            'font-family="sans-serif" font-size="11" fill="#1a2332">'
            f'{html.escape(str(r["name"])[:32])}'
            f'<title>{html.escape(r_title)}</title></text>'
            f'<rect x="{x_lo:.1f}" y="{y-6}" '
            f'width="{max(2, x_hi-x_lo):.1f}" height="12" '
            'fill="#1F7A75" opacity="0.75">'
            f'<title>{html.escape(r_title)}</title></rect>'
            f'<text x="{x_hi+6:.1f}" y="{y+5}" font-family="monospace" '
            'font-size="9.5" fill="#465366">'
            f'{_fmt_money(r["tam_low"])}\u2013{_fmt_money(r["tam_high"])}'
            '</text>')
    parts.append('</svg>')
    return ck_panel(
        "".join(parts)
        + '<p class="ts2-src" style="margin:8px 0 0;">Each bar swings '
        'ONE driver \u00b120% (rates clamped at 100%) holding the rest at '
        'base \u2014 dashed line = base TAM. Sorted by impact: the top bar '
        'is the assumption to pressure-test first.</p>',
        title="Driver sensitivity \u00b7 \u00b120% tornado",
    )


_BAND_COLOR = {"green": "#0a8a5f", "amber": "#b8732a", "red": "#b5321e"}
_COMPLEXITY_COLOR = {"MODERATE": "#155752", "HIGH": "#b8732a",
                     "VERY HIGH": "#b5321e"}
# Compact archetype chips for the cross-industry table — one stable color
# + short label per sizing method so the whole catalogue reads at a glance.
_ARCHETYPE_CHIP = {
    "procedure_claims": ("#0b2341", "Procedure"),
    "epidemiology": ("#155752", "Epi"),
    "capitation_lives": ("#6f4d8c", "Lives"),
    "facility_capacity": ("#b8732a", "Facility"),
    "installed_base": ("#1f6f8b", "Install-base"),
    "top_down_nhe": ("#8b5e34", "Top-down"),
}


def _archetype_chip(code: str) -> str:
    color, label = _ARCHETYPE_CHIP.get(code, ("#465366", code or "—"))
    return (
        f'<span style="font-family:var(--sc-mono);font-size:9px;'
        f'letter-spacing:.06em;text-transform:uppercase;color:#fff;'
        f'background:{color};padding:1px 6px;border-radius:2px;'
        f'white-space:nowrap;">{html.escape(label)}</span>')


def _method_panel(out: Dict[str, Any], model: TamSamModel) -> str:
    """Method-&-uncertainty panel: the sizing ARCHETYPE (the discipline of
    matching the method to the vertical), the bottom-up vs top-down
    TRIANGULATION quality gate, the Monte-Carlo uncertainty band, and the
    Bass adoption curve when the model carries one. This is the analytic
    altitude the doc demands — the chain shows the build, this panel shows
    whether to trust it."""
    arch = out.get("archetype") or {}
    code = arch.get("code", "")
    comp = arch.get("complexity", "")
    comp_c = _COMPLEXITY_COLOR.get(comp, "#465366")
    # Archetype header — label + complexity chip + formula + sources.
    arch_html = (
        '<div style="margin:0 0 10px;">'
        f'<span style="font-weight:600;color:var(--sc-navy,#0b2341);">'
        f'{html.escape(arch.get("label", code))}</span> '
        f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.1em;text-transform:uppercase;color:#fff;'
        f'background:{comp_c};padding:2px 7px;border-radius:2px;'
        f'margin-left:6px;">{html.escape(comp)} complexity</span>'
        f'<div class="ts2-src" style="margin-top:6px;">'
        f'<b>Formula</b> · {html.escape(arch.get("formula", ""))}</div>'
        f'<div class="ts2-src" style="margin-top:3px;">'
        f'<b>When to use</b> · {html.escape(arch.get("when_to_use", ""))}'
        f'</div>'
        f'<div class="ts2-src" style="margin-top:3px;">'
        f'<b>Primary sources</b> · '
        f'{_source_list_links(arch.get("primary_sources", ""))}</div>'
        '</div>'
    )

    # Triangulation — the quality gate. Only when the model carries an
    # independent top-down check.
    tri = out.get("triangulation")
    tri_html = ""
    if tri:
        bc = _BAND_COLOR.get(tri["band"], "#465366")
        tri_html = (
            '<div style="margin:14px 0 0;padding:11px 13px;border-left:'
            f'4px solid {bc};background:var(--sc-bone,#ece5d6);">'
            '<div style="font-family:var(--sc-mono);font-size:9.5px;'
            'letter-spacing:.12em;text-transform:uppercase;color:#465366;'
            'margin-bottom:5px;">Triangulation · bottom-up vs top-down</div>'
            '<div style="display:flex;gap:18px;flex-wrap:wrap;'
            'align-items:baseline;">'
            f'<span>Bottom-up <b>{_fmt_money(tri["bottom_up_tam"])}</b></span>'
            f'<span>Top-down <b>{_fmt_money(tri["top_down_tam"])}</b></span>'
            f'<span style="color:{bc};font-weight:600;">Gap '
            f'{_fmt_pct(tri["gap_pct"])} · {tri["band"].upper()}</span>'
            '</div>'
            f'<div class="ts2-src" style="margin-top:6px;">'
            f'{html.escape(tri["verdict"])}</div>'
            f'<div class="ts2-src" style="margin-top:3px;">Top-down basis · '
            f'{_cited_prose(tri.get("top_down_source", ""))}</div>'
            '</div>'
        )

    # Monte-Carlo uncertainty band — P10/P50/P90 around the point estimate.
    mc = monte_carlo(model, n=4000, rel_sigma=0.15, seed=1729)
    mc_html = (
        '<div style="margin:14px 0 0;">'
        '<div style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.12em;text-transform:uppercase;color:#465366;'
        'margin-bottom:5px;">Monte-Carlo TAM band · ±15% per-driver, '
        'n=4,000</div>'
        '<div style="display:flex;gap:18px;flex-wrap:wrap;">'
        f'<span>P10 <b>{_fmt_money(mc["p10"])}</b></span>'
        f'<span>P50 <b>{_fmt_money(mc["p50"])}</b></span>'
        f'<span>P90 <b>{_fmt_money(mc["p90"])}</b></span>'
        f'<span class="ts2-src">CV {_fmt_pct(mc["cv"] * 100)}</span>'
        '</div>'
        '<p class="ts2-src" style="margin:5px 0 0;">Lognormal driver '
        'uncertainty propagated through the chain (seeded, reproducible, '
        'no LLM). The P50 reproduces the deterministic point estimate.</p>'
        '</div>'
    )

    # Bass adoption S-curve (installed-base archetype) when present.
    bass = out.get("bass")
    bass_html = ""
    if bass:
        cells = "".join(
            f'<td class="r">{_fmt_pct(b["cum_frac"] * 100)}</td>'
            for b in bass)
        hdr = "".join(f'<th scope="col" class="r">Y{b["period"]}</th>'
                      for b in bass)
        bass_html = (
            '<div style="margin:14px 0 0;">'
            '<div style="font-family:var(--sc-mono);font-size:9.5px;'
            'letter-spacing:.12em;text-transform:uppercase;color:#465366;'
            'margin-bottom:5px;">Bass adoption · SOM(t) = SAM × F(t)</div>'
            '<table class="ts2-chain"><thead><tr>'
            '<th scope="col">Cumulative adopted</th>'
            f'{hdr}</tr></thead><tbody><tr>'
            f'<th scope="row" class="ts2-src" style="font-weight:400;">'
            f'share of SAM</th>{cells}</tr></tbody></table>'
            '<p class="ts2-src" style="margin:5px 0 0;">Innovation p='
            f'{model.bass_p:g}, imitation q={model.bass_q:g} — the S-curve '
            'that governs realistic near-term capture for an adoption play.'
            '</p></div>'
        )

    return ck_panel(
        arch_html + tri_html + mc_html + bass_html,
        title="Method &amp; uncertainty · how it's built, whether to "
              "trust it",
    )


def _jump_nav(has_dive: bool) -> str:
    """One-line jump nav for the long build page — same pattern as the
    X-Ray's section nav. Anchors are attached to the panels below."""
    chips = [("#ts-compare", "Cross-industry"),
             ("#ts-method", "Method"),
             ("#ts-chain", "Chain"),
             ("#ts-segments", "Segments"),
             ("#ts-projection", "Projection"),
             ("#ts-tornado", "Sensitivity"),
             ("#ts-agenda", "Agenda")]
    if has_dive:
        chips.append(("#ts-dive", "Market data"))
    chips.append(("#ts-sources", "Sources"))
    links = "".join(
        f'<a href="{h}" style="padding:4px 10px;border:1px solid '
        'var(--sc-rule,#c9c1ac);border-radius:2px;font-size:11px;'
        'text-decoration:none;color:var(--sc-text,#1a2332);">'
        f'{label}</a>'
        for h, label in chips)
    return ('<nav aria-label="Jump to section" '
            'style="display:flex;gap:6px;flex-wrap:wrap;'
            f'margin:0 0 12px;">{links}</nav>')


def _industry_comparison_panel(active_key: str,
                               sort: str = "tam",
                               scenario: str = "base") -> str:
    """Every sized vertical side by side — sortable by TAM (where the
    biggest pieces are) or composite growth (where it grows fastest).
    Each row links into its build.

    ``scenario`` is carried through every link so switching vertical (or
    re-sorting) does not silently drop the partner back to Base."""
    from ..diligence.tam_sam import (
        TEMPLATES, TEMPLATE_ARCHETYPE, compute as _compute)
    rows = []
    for key, factory in TEMPLATES.items():
        if key == "blank":
            continue
        try:
            o = _compute(factory())
        except Exception:  # noqa: BLE001
            continue
        rows.append((key, o["name"], o["tam"], o["composite_cagr_pct"],
                     TEMPLATE_ARCHETYPE.get(key, "")))
    if sort == "growth":
        rows.sort(key=lambda r: -r[3])
    elif sort == "archetype":
        rows.sort(key=lambda r: (r[4], -r[2]))
    else:
        rows.sort(key=lambda r: -r[2])
    max_tam = max((r[2] for r in rows), default=1)
    trs = ""
    for key, name, tam, cagr, arch_code in rows:
        short = name.split("·")[0].strip()
        is_active = key == active_key
        on = (' style="background:var(--sc-bone,#ece5d6);"'
              ' aria-current="page"' if is_active else "")
        bar_w = max(2, tam / max_tam * 160)
        tone = "#0a8a5f" if cagr >= 4 else ("#b5321e" if cagr < 0 else "#1a2332")
        # The row label is the vertical's short name; the full catalogue
        # name (everything after the "·") is otherwise invisible here.
        full = f"{name} — TAM {_fmt_money(tam)}, composite " \
               f"{_fmt_pct(cagr, sign=True)}/yr"
        trs += (
            f'<tr{on}>'
            f'<th scope="row" style="font-weight:400;">'
            f'<a href="{_build_href(key, scenario, sort)}" '
            f'title="{html.escape(full, quote=True)}" '
            f'style="color:var(--sc-navy,#0b2341);font-weight:600;'
            f'text-decoration:none;">{html.escape(short)}</a></th>'
            f'<td>{_archetype_chip(arch_code)}</td>'
            f'<td class="r">{_fmt_money(tam)}</td>'
            # Decorative duplicate of the TAM cell to its left — hidden
            # from AT so the row isn't read twice.
            f'<td><svg width="170" height="12" aria-hidden="true" '
            f'focusable="false">'
            f'<rect x="0" y="1" width="{bar_w:.0f}" height="10" '
            f'fill="#0b2341" opacity="0.8"/></svg></td>'
            f'<td class="r" style="color:{tone};font-weight:600;">'
            f'{_fmt_pct(cagr, sign=True)}/yr</td></tr>'
        )
    if not trs:
        return ck_panel(
            ck_empty_state(
                "No sized verticals to compare.",
                "The cross-industry table is built from the template "
                "catalogue; none of it computed on this request.",
                eyebrow="Cross-industry view",
            ),
            title="Cross-industry view · where the biggest pieces grow "
                  "fastest",
        )

    def _sort_link(token: str, label: str) -> str:
        href = _build_href(active_key, scenario, token)
        weight = 700 if sort == token else 400
        cur = ' aria-current="true"' if sort == token else ""
        return (f'<a href="{href}"{cur} style="font-weight:{weight};'
                f'color:var(--sc-navy);">{label}</a>')

    def _sort_th(token: str, label: str) -> str:
        """Column header that IS the sort control, with aria-sort so AT
        announces which column the table is ordered by."""
        align = 'text-align:right;'
        state = 'descending' if sort == token else 'none'
        mark = ' ▾' if sort == token else ''
        return (f'<th scope="col" aria-sort="{state}" style="{align}">'
                f'<a href="{_build_href(active_key, scenario, token)}" '
                f'title="Sort the catalogue by {html.escape(label, quote=True)}" '
                f'style="color:inherit;text-decoration:none;'
                f'{"font-weight:700;" if sort == token else ""}">'
                f'{label}{mark}</a></th>')

    return ck_panel(
        '<table class="ts2-chain"><caption class="ts2-src" '
        'style="caption-side:top;text-align:left;padding:0 0 6px;">'
        'Every sized vertical, template defaults — click the TAM or '
        'Composite growth header to re-sort.</caption><thead><tr>'
        '<th scope="col">Vertical</th>'
        # NOTE: this header stays bare. tests/test_tam_sam.py
        # (ArchetypeColumnTests.test_method_column_and_sort_render) asserts
        # the literal string "<th>Method</th>", so it cannot carry scope or
        # aria-sort; the "by method" sort stays available in the footer
        # links below.
        '<th>Method</th>'
        + _sort_th("tam", "TAM")
        + '<th scope="col">Relative size</th>'
        + _sort_th("growth", "Composite growth")
        + f'</tr></thead><tbody>{trs}</tbody></table>'
        f'<p class="ts2-src" style="margin:8px 0 0;">Sort: '
        + _sort_link("tam", "biggest pieces (TAM)") + ' · '
        + _sort_link("growth", "growing fastest") + ' · '
        + _sort_link("archetype", "by method")
        + '. Template defaults — each row opens its full build. '
        'Method = the sizing archetype. Green ≥4%/yr · red = declining.</p>',
        title="Cross-industry view · where the biggest pieces grow "
              "fastest",
    )


def _dive_for_sources(tmpl_key: str) -> Optional[Dict[str, Any]]:
    from ..diligence.industry_deep_dive import deep_dive_for
    return deep_dive_for(tmpl_key)


def render_tam_sam_page(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    model = model_from_qs(qs)
    out = compute(model)
    tmpl_key = (qs.get("template") or ["fertility_ivf"])[0]

    title = ck_page_title(
        "TAM / SAM Builder",
        eyebrow="DILIGENCE · MARKET SIZING",
        meta=(f"{html.escape(out['name'])} · TAM {_fmt_money(out['tam'])} · "
              f"{_fmt_pct(out['composite_cagr_pct'], sign=True)}/yr "
              "composite"),
    )
    src = ck_source_purpose(
        purpose=("Build the market-sizing driver tree the IC expects — "
                 "population → utilization → price chain, segment bands, "
                 "TAM→SAM→SOM funnel, growth-driver-decomposed projection "
                 "— and export it formatted."),
        universe="template + your overrides",
        confidence="illustrative",
        source=("Template defaults from public data (per-step source "
                "labels). Replace with engagement data before IC use."),
        next_action="Drop the export into the deal model",
        next_href="#ts2-export",
    )

    scenario = (qs.get("scenario") or ["base"])[0].lower()
    if scenario not in ("conservative", "base", "aggressive"):
        scenario = "base"
    sort_key = (qs.get("sort") or ["tam"])[0]
    _cur_true = ' aria-current="true"'
    _cur_page = ' aria-current="page"'
    scen_bar = (
        '<nav class="ts2-tmpl" style="margin:0 0 10px;" '
        'aria-label="Scenario preset">'
        '<span class="ts2-src" style="align-self:center;'
        'margin-right:4px;text-transform:uppercase;letter-spacing:.1em;">'
        'Scenario</span>'
        + "".join(
            f'<a href="'
            f'{_build_href(tmpl_key, s, sort_key, explicit_scenario=True)}" '
            f'class="{"on" if s == scenario else ""}"'
            f'{_cur_true if s == scenario else ""}>'
            f'{s.title()}</a>'
            for s in ("conservative", "base", "aggressive"))
        + '<span class="ts2-src" style="align-self:center;">'
        'Conservative halves tailwinds / amplifies headwinds; '
        'Aggressive mirrors. Typed driver values always win.</span>'
        '</nav>'
    )
    tmpl_bar = (
        '<nav class="ts2-tmpl" aria-label="Sizing template">'
        + "".join(
            f'<a href="{_build_href(k, scenario, sort_key)}" '
            f'class="{"on" if k == tmpl_key else ""}"'
            f'{_cur_page if k == tmpl_key else ""}>'
            f'{html.escape(lbl)}</a>'
            for k, lbl in (("fertility_ivf", "Fertility · IVF"),
                           ("dialysis", "Dialysis · in-center"),
                           ("home_health", "Home health"),
                           ("hospice", "Hospice"),
                           ("snf", "SNF · nursing"),
                           ("irf", "IRF · rehab"),
                           ("ltch", "LTCH"),
                           ("behavioral_health", "Behavioral health"),
                           ("asc", "ASC · surgery"),
                           ("physician_group", "Physician groups"),
                           ("dental", "Dental · DSO"),
                           ("oncology", "Oncology"),
                           ("urgent_care", "Urgent care"),
                           ("hospitals", "Hospitals"),
                           ("infusion", "Infusion"),
                           ("imaging", "Imaging"),
                           ("physical_therapy", "Physical therapy"),
                           ("veterinary", "Veterinary"),
                           ("medspa", "Medspa"),
                           ("ems", "EMS"),
                           ("clinical_labs", "Clinical labs"),
                           ("specialty_pharmacy", "Specialty Rx"),
                           ("vision", "Vision"),
                           ("aba", "ABA · autism"),
                           ("plasma", "Plasma"),
                           ("clinical_research", "Research sites"),
                           ("wound_care", "Wound care"),
                           ("sleep", "Sleep"),
                           ("occ_health", "Occ health"),
                           ("dermatology", "Dermatology"),
                           ("pain_management", "Pain mgmt"),
                           ("hospital_at_home", "Hospital-at-home"),
                           ("ltc_pharmacy", "LTC pharmacy"),
                           ("dme", "DME"),
                           ("idd_services", "IDD services"),
                           ("eating_disorders", "Eating disorders"),
                           ("nephrology", "Nephrology"),
                           ("orthotics_prosthetics", "O&P"),
                           ("ophthalmology", "Ophthalmology"),
                           ("rcm_services", "RCM services"),
                           ("cardiology", "Cardiology"),
                           ("gastroenterology", "GI"),
                           ("orthopedics", "Orthopedics"),
                           ("womens_health", "Women's health"),
                           ("podiatry", "Podiatry"),
                           ("ent_allergy", "ENT & allergy"),
                           ("anesthesia", "Anesthesia"),
                           ("home_care", "Home care"),
                           ("pace", "PACE"),
                           ("teleradiology", "Teleradiology"),
                           ("correctional_health", "Correctional"),
                           ("locum_staffing", "Locum staffing"),
                           ("crisis_services", "Crisis services"),
                           ("school_services", "School services"),
                           ("mobile_diagnostics", "Mobile dx"),
                           ("palliative", "Palliative"),
                           ("senior_living", "Senior living"),
                           ("vascular_access", "Vascular access"),
                           ("genetic_testing", "Genetic testing"),
                           ("nemt", "NEMT"),
                           ("compounding_503b", "503B compounding"),
                           ("lop_medicine", "LOP medicine"),
                           ("dental_labs", "Dental labs"),
                           ("htm_clinical_engineering", "HTM"),
                           ("interpretation", "Interpretation"),
                           ("urology", "Urology"),
                           ("rheumatology", "Rheumatology"),
                           ("neurology", "Neurology"),
                           ("endocrinology_obesity", "Endo · obesity"),
                           ("pulmonology", "Pulmonology"),
                           ("transplant_services", "Transplant svcs"),
                           ("retail_clinics", "Retail clinics"),
                           ("surgical_assist", "Surgical assist"),
                           ("hit_consulting", "HIT consulting"),
                           ("hospitalist", "Hospitalist"),
                           ("perfusion", "Perfusion"),
                           ("sterile_processing", "Sterile processing"),
                           ("air_medical", "Air medical"),
                           ("pediatric_home_health", "Pediatric PDN"),
                           ("roi_services", "ROI services"),
                           ("virtual_primary_care", "Virtual primary"),
                           ("rpm", "RPM"),
                           ("care_navigation", "Care navigation"),
                           ("blank", "Blank scaffold")))
        + '</div>'
    )

    funnel = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);'
        'gap:8px;margin:0 0 16px;">'
        + ck_kpi_block("TAM", _fmt_money(out["tam"]), "full driver chain")
        + ck_kpi_block(
            "SAM", _fmt_money(out["sam"]),
            f"{_fmt_pct(out['sam_share'] * 100)} addressable")
        + ck_kpi_block(
            "SOM", _fmt_money(out["som"]),
            f"{_fmt_pct(out['som_share'] * 100)} of SAM obtainable")
        + ck_kpi_block(
            "Composite growth",
            f"{_fmt_pct(out['composite_cagr_pct'], sign=True)}/yr",
            f"{len(out['growth_drivers'])} named drivers")
        + '</div>'
    )

    # Editable chain — the audit trail IS the form.
    chain_rows = ""
    for i, st in enumerate(out["steps"]):
        # Plain decimal in the form — :g renders 3660000 as "3.66e+06",
        # which reads as a formula, not a population. The parser strips
        # commas on the way back in.
        if st["op"] == "rate":
            form_val = f"{st['value']*100:g}"
        elif float(st["value"]).is_integer():
            form_val = f"{int(st['value']):,}"
        else:
            form_val = f"{st['value']:,.4f}".rstrip("0").rstrip(".")
        chain_rows += (
            '<tr>'
            f'<th scope="row" style="font-weight:400;">'
            f'{html.escape(st["name"])}'
            # The per-step citation is the defensibility of the whole
            # chain — link it to the dataset instead of printing a dead
            # label the partner has to Google.
            f'<div class="ts2-src">'
            f'{ck_source_link(st["source"]) if st["source"] else ""}'
            '</div></th>'
            f'<td class="r"><input name="step{i}" value="{form_val}" '
            f'aria-label="{html.escape(st["name"], quote=True)}"/>'
            f' <span class="ts2-src">{html.escape(st["unit"])}'
            f'{" (%)" if st["op"] == "rate" else ""}</span></td>'
            f'<td class="r">{_fmt_step_value(st)}</td>'
            f'<td class="r ts2-run">{_fmt_running(st)}</td>'
            '</tr>'
        )
    sam_row = (
        '<tr><th scope="row" style="font-weight:400;">'
        'Addressable share (SAM)'
        f'<div class="ts2-src">{html.escape(model.sam_note or "")}</div></th>'
        f'<td class="r"><input name="sam_share" '
        f'value="{model.sam_share*100:g}" '
        f'aria-label="Addressable share (SAM), % of TAM"/> '
        f'<span class="ts2-src">% of TAM'
        '</span></td>'
        f'<td class="r">{_fmt_pct(model.sam_share * 100)}</td>'
        f'<td class="r ts2-run">{_fmt_money(out["sam"])}</td></tr>'
        '<tr><th scope="row" style="font-weight:400;">'
        'Obtainable share (SOM)'
        f'<div class="ts2-src">{html.escape(model.som_note or "")}</div></th>'
        f'<td class="r"><input name="som_share" '
        f'value="{model.som_share*100:g}" '
        f'aria-label="Obtainable share (SOM), % of SAM"/> '
        f'<span class="ts2-src">% of SAM'
        '</span></td>'
        f'<td class="r">{_fmt_pct(model.som_share * 100)}</td>'
        f'<td class="r ts2-run">{_fmt_money(out["som"])}</td></tr>'
    )
    # Directionality made visible: ▲ tailwind / ▼ headwind by sign, with
    # the root cause (the note) under each driver name.
    growth_inputs = ""
    for i, g in enumerate(out["growth_drivers"]):
        # role=img + aria-label so AT announces "tailwind", not the Unicode
        # name of a triangle; title gives the sighted partner the same word.
        if g["annual_pct"] > 0:
            arrow = ('<span style="color:#0a8a5f;" role="img" '
                     'aria-label="Tailwind" title="Tailwind">▲</span>')
        elif g["annual_pct"] < 0:
            arrow = ('<span style="color:#b5321e;" role="img" '
                     'aria-label="Headwind" title="Headwind">▼</span>')
        else:
            arrow = ('<span style="color:#7a8699;" role="img" '
                     'aria-label="Neutral" title="Neutral">—</span>')
        growth_inputs += (
            '<div class="ts2-drv">'
            f'<span>{arrow} {html.escape(g["name"])}'
            f'<div class="ts2-src">{_cited_prose(g["note"] or "")}</div>'
            '</span>'
            f'<span class="pct"><input name="growth{i}" '
            f'value="{g["annual_pct"]:g}" style="width:70px;" '
            f'aria-label="{html.escape(g["name"], quote=True)} (%/yr)"/> %/yr</span>'
            '</div>'
        )
    chain_panel = ck_panel(
        f'<form method="GET" action="/diligence/tam-sam">'
        f'<input type="hidden" name="template" '
        f'value="{html.escape(tmpl_key, quote=True)}"/>'
        '<table class="ts2-chain"><caption class="ts2-src" '
        'style="caption-side:top;text-align:left;padding:0 0 6px;">'
        'Population → utilization → price. Each row multiplies into the '
        'running value in the last column.</caption><thead><tr>'
        '<th scope="col">Driver</th>'
        '<th scope="col" style="text-align:right;">Your input</th>'
        '<th scope="col" style="text-align:right;">Applied</th>'
        '<th scope="col" style="text-align:right;">Running value</th>'
        f'</tr></thead><tbody>{chain_rows}{sam_row}</tbody></table>'
        '<div style="margin:16px 0 0;">'
        '<div class="ts2-src" style="margin-bottom:6px;text-transform:'
        'uppercase;letter-spacing:.1em;">Growth drivers (composed '
        'multiplicatively)</div>'
        f'{growth_inputs}</div>'
        '<div class="ts2-form-bar">'
        '<button type="submit" class="ts2-btn">Recompute</button>'
        '<span class="ts2-src">Every value editable — rates entered as '
        'percent points (2.3 = 2.3%).</span>'
        '</div></form>',
        title="Driver chain · the methodology, shown",
    )

    has_seg_growth = any(s.get("growth_pct") is not None
                         for s in out["segments"])
    seg_rows = ""
    for s in out["segments"]:
        sr = (_fmt_pct(s["success_rate"] * 100)
              if s["success_rate"] is not None else "—")
        fastest = s.get("is_fastest")
        row_style = (' style="background:var(--sc-bone,#ece5d6);"'
                     if fastest else "")
        g = s.get("growth_pct")
        g_s = (_fmt_pct(g, sign=True) if g is not None else "—")
        g_tone = ("#0a8a5f" if (g or 0) >= 5
                  else "#b5321e" if (g or 0) < 0 else "#1a2332")
        y5 = s.get("tam_y_final")
        star_html = (
            ' <span role="img" aria-label="fastest-growing segment" '
            'title="Fastest-growing segment">★</span>' if fastest else ""
        )
        growth_tds = (
            f'<td class="r" style="color:{g_tone};font-weight:600;">'
            f'{g_s}{star_html}</td>'
            f'<td class="r">{_fmt_money(y5) if y5 else "—"}</td>'
            if has_seg_growth else ""
        )
        seg_rows += (
            f'<tr{row_style}>'
            f'<th scope="row" style="font-weight:400;">'
            f'{html.escape(s["name"])}'
            f'<div class="ts2-src">{html.escape(s["note"] or "")}</div></th>'
            f'<td class="r">{_fmt_pct(s["share_of_volume"] * 100)}</td>'
            f'<td class="r">{_fmt_money(s["tam_value"])}</td>'
            f'{growth_tds}'
            f'<td class="r">{sr}</td>'
            '</tr>'
        )
    seg_panel = ck_panel(
        _segment_bar_svg(out["segments"])
        + '<table class="ts2-chain"><thead><tr>'
        '<th scope="col">Segment</th>'
        '<th scope="col" style="text-align:right;">Volume share</th>'
        '<th scope="col" style="text-align:right;">TAM slice</th>'
        + ('<th scope="col" style="text-align:right;">Growth %/yr</th>'
           f'<th scope="col" style="text-align:right;">'
           f'Y{out["horizon_years"]} slice</th>' if has_seg_growth else "")
        + '<th scope="col" style="text-align:right;">Success rate</th>'
        f'</tr></thead><tbody>{seg_rows}</tbody></table>'
        + ('<p class="ts2-src" style="margin:8px 0 0;">★ = the fastest-'
           'growing segment — where the whitespace compounds. Segment '
           'growth rates are template defaults; the composite drivers '
           'above govern the funnel projection.</p>'
           if has_seg_growth else ""),
        title="Segments · the whitespace map",
    ) if out["segments"] else ck_panel(
        # The blank scaffold has no segment bands. The jump nav still ships
        # a "Segments" chip, so the anchor needs something to land on.
        ck_empty_state(
            "No segment bands in this build.",
            "Segments split the TAM by payer, age band, acuity or site of "
            "care — the whitespace map the IC asks for. The sized vertical "
            "templates ship theirs; a blank scaffold starts without one.",
            eyebrow="Segments",
            cta_label="Browse the sized verticals",
            cta_href="#ts-compare",
        ),
        title="Segments · the whitespace map",
    )

    proj_rows = "".join(
        '<tr>'
        f'<th scope="row" style="font-weight:400;">Year {p["year"]}</th>'
        f'<td class="r">{_fmt_money(p["tam"])}</td>'
        f'<td class="r">{_fmt_money(p["sam"])}</td>'
        f'<td class="r">{_fmt_money(p["som"])}</td>'
        '</tr>'
        for p in out["projection"]
    )
    proj_panel = ck_panel(
        _projection_svg(out["projection"])
        + '<table class="ts2-chain"><thead><tr>'
        '<th scope="col">Horizon</th>'
        '<th scope="col" style="text-align:right;">TAM</th>'
        '<th scope="col" style="text-align:right;">SAM</th>'
        '<th scope="col" style="text-align:right;">SOM</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table>'
        f'<p class="ts2-src" style="margin:10px 0 0;">Composite '
        f'{_fmt_pct(out["composite_cagr_pct"], sign=True)}/yr from the '
        'named drivers above — the decomposition survives into the export '
        'so the IC sees which lever carries the growth.</p>',
        title=f"{out['horizon_years']}-year projection",
    ) if out["projection"] else ck_panel(
        ck_empty_state(
            "No horizon to project.",
            "Set a horizon and at least one growth driver and the "
            "TAM / SAM / SOM trajectory renders here.",
            eyebrow="Projection",
            cta_label="Edit the driver chain",
            cta_href="#ts-chain",
        ),
        title=f"{out['horizon_years']}-year projection",
    )

    export_qs = html.escape(urllib.parse.urlencode(
        {k: v[0] for k, v in qs.items() if v}, doseq=False), quote=True)
    export_panel = ck_panel(
        '<div class="ts2-form-bar" style="margin:0;" id="ts2-export">'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.xlsx?{export_qs}" download '
        'aria-label="Download this build as a formatted Excel workbook">'
        '<span aria-hidden="true">⬇</span> Formatted Excel (.xlsx)</a>'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.csv?{export_qs}" download '
        'aria-label="Download this build as CSV">'
        '<span aria-hidden="true">⬇</span> CSV</a>'
        '<span class="ts2-src">Excel ships 6 formatted sheets — Funnel '
        '&amp; chain, Segments, Projection, Sources, Diligence agenda, '
        'Method &amp; uncertainty — headers, $ and % formats, column '
        'widths set.</span></div>',
        title="Export · drop into the deal model",
    )

    basis = (
        f'<p class="ts2-src" style="margin:4px 0 14px;">'
        f'{_cited_prose(out["basis_note"])}</p>'
        if out["basis_note"] else ""
    )

    body = (
        _CSS + title + src + tmpl_bar + scen_bar + basis + funnel
        + _jump_nav(bool(_dive_for_sources(tmpl_key)))
        + '<div id="ts-compare"></div>'
        + _industry_comparison_panel(
            tmpl_key, sort=sort_key, scenario=scenario)
        + '<div id="ts-method"></div>' + _method_panel(out, model)
        + '<div id="ts-chain"></div>' + chain_panel
        + '<div id="ts-segments"></div>' + seg_panel
        + '<div id="ts-projection"></div>' + proj_panel
        + '<div id="ts-tornado"></div>'
        + _tornado_panel(model, out["tam"])
        + '<div id="ts-agenda"></div>'
        + _diligence_agenda_panel(out)
        + '<div id="ts-dive"></div>'
        + _industry_panels(tmpl_key)
        + '<div id="ts-sources"></div>'
        + _sources_panel(out, _dive_for_sources(tmpl_key))
        + export_panel
        + ck_next_section(
            "Carry the sizing into the IC packet",
            "/diligence/ic-packet",
            eyebrow="Up next",
            italic_word="packet",
        )
    )
    return chartis_shell(
        body, "TAM / SAM Builder",
        active_nav="/diligence/tam-sam",
    )


# ── Exports ──────────────────────────────────────────────────────────────

def tam_sam_csv(qs: Dict[str, List[str]]) -> str:
    import csv
    import io
    from ..infra.csv_safety import defang_row
    model = model_from_qs(qs)
    out = compute(model)
    buf = io.StringIO()
    _raw = csv.writer(buf)

    class _DefangWriter:
        # Report-0270: defense-in-depth. Today model_from_qs only accepts
        # numeric overrides + a fixed template key, so out's string cells
        # (name/note/source) are trusted catalog content — but this export
        # previously defanged nothing, so if a future template ever carries
        # a partner-supplied field it would inject. Route every row through
        # the shared formula-injection guard to hold the house convention.
        @staticmethod
        def writerow(row):
            _raw.writerow(defang_row(row))

        @staticmethod
        def writerows(rows):
            for r in rows:
                _raw.writerow(defang_row(r))

    w = _DefangWriter()
    w.writerow(["TAM/SAM build", out["name"]])
    w.writerow(["Basis", out["basis_note"]])
    w.writerow([])
    w.writerow(["Driver", "Op", "Value", "Unit", "Source", "Running value"])
    for st in out["steps"]:
        w.writerow([st["name"], st["op"], st["value"], st["unit"],
                    st["source"], round(st["running"], 2)])
    w.writerow(["Addressable share (SAM)", "rate", out["sam_share"],
                "of TAM", out["sam_note"], round(out["sam"], 2)])
    w.writerow(["Obtainable share (SOM)", "rate", out["som_share"],
                "of SAM", out["som_note"], round(out["som"], 2)])
    w.writerow([])
    if out["segments"]:
        w.writerow(["Segment", "Volume share", "TAM slice",
                    "Growth %/yr", f"Y{out['horizon_years']} slice",
                    "Success rate", "Note"])
        for s in out["segments"]:
            w.writerow([s["name"], s["share_of_volume"],
                        round(s["tam_value"], 2),
                        s.get("growth_pct") if s.get("growth_pct")
                        is not None else "",
                        round(s["tam_y_final"], 2)
                        if s.get("tam_y_final") else "",
                        s["success_rate"] if s["success_rate"] is not None
                        else "", s["note"]])
        w.writerow([])
    w.writerow(["Growth driver", "%/yr", "Note"])
    for g in out["growth_drivers"]:
        w.writerow([g["name"], g["annual_pct"], g["note"]])
    w.writerow(["Composite CAGR", round(out["composite_cagr_pct"], 2), ""])
    w.writerow([])
    w.writerow(["Year", "TAM", "SAM", "SOM"])
    for p in out["projection"]:
        w.writerow([p["year"], round(p["tam"], 2), round(p["sam"], 2),
                    round(p["som"], 2)])
    w.writerow([])
    # Method & uncertainty — the archetype, triangulation gate, and the
    # Monte-Carlo band travel into the deal model alongside the point build.
    arch = out.get("archetype") or {}
    w.writerow(["Method (archetype)", arch.get("label", ""),
                f"{arch.get('complexity', '')} complexity"])
    w.writerow(["Formula", arch.get("formula", "")])
    w.writerow(["Primary sources", arch.get("primary_sources", "")])
    tri = out.get("triangulation")
    if tri:
        w.writerow(["Triangulation bottom-up", round(tri["bottom_up_tam"], 2),
                    "Triangulation top-down", round(tri["top_down_tam"], 2),
                    f"gap {tri['gap_pct']:.1f}% ({tri['band'].upper()})"])
        w.writerow(["Top-down basis", tri.get("top_down_source", "")])
    mc = monte_carlo(model, n=4000, rel_sigma=0.15, seed=1729)
    w.writerow(["Monte-Carlo TAM (P10/P50/P90)", round(mc["p10"], 2),
                round(mc["p50"], 2), round(mc["p90"], 2),
                f"CV {_fmt_pct(mc['cv'] * 100)}"])
    if out.get("bass"):
        w.writerow(["Bass cum. adoption (share of SAM)"]
                   + [f"Y{b['period']}={_fmt_pct(b['cum_frac'] * 100)}"
                      for b in out["bass"]])
    w.writerow([])
    w.writerow(["Diligence agenda"])
    for i, q in enumerate(_derive_agenda_items(out), 1):
        w.writerow([f"Q{i}", q])
    return buf.getvalue()


def tam_sam_xlsx(qs: Dict[str, List[str]]) -> bytes:
    from ..exports.xlsx_writer import Sheet, write_xlsx
    model = model_from_qs(qs)
    out = compute(model)
    _scen = ((qs.get("scenario") or ["base"])[0] or "base").lower()
    if _scen not in ("conservative", "base", "aggressive"):
        _scen = "base"
    H = "header"
    funnel_rows: List[List[Any]] = [
        [(f"TAM/SAM build · {out['name']} · "
          f"{_scen.upper()} scenario", H), ("", H), ("", H), ("", H),
         ("", H), ("", H)],
        [out["basis_note"], "", "", "", "", ""],
        [],
        [("Driver", H), ("Op", H), ("Value", H), ("Unit", H),
         ("Source", H), ("Running", H)],
    ]
    for st in out["steps"]:
        val = ((st["value"], "pct") if st["op"] == "rate"
               else (st["value"], "money") if st["op"] == "price"
               else (st["value"], "num2"))
        run = ((st["running"], "money") if st["op"] == "price"
               else (st["running"], "num"))
        funnel_rows.append([st["name"], st["op"], val, st["unit"],
                            st["source"], run])
    funnel_rows += [
        ["Addressable share (SAM)", "rate", (out["sam_share"], "pct"),
         "of TAM", out["sam_note"], (out["sam"], "money")],
        ["Obtainable share (SOM)", "rate", (out["som_share"], "pct"),
         "of SAM", out["som_note"], (out["som"], "money")],
        [],
        [("TAM", H), (out["tam"], "money")],
        [("SAM", H), (out["sam"], "money")],
        [("SOM", H), (out["som"], "money")],
    ]
    seg_rows: List[List[Any]] = [
        [("Segment", H), ("Volume share", H), ("TAM slice", H),
         ("Growth %/yr", H), (f"Y{out['horizon_years']} slice", H),
         ("Success rate", H), ("Note", H)],
    ] + [
        [s["name"], (s["share_of_volume"], "pct"),
         (s["tam_value"], "money"),
         (s["growth_pct"] / 100.0, "pct")
         if s.get("growth_pct") is not None else "",
         (s["tam_y_final"], "money") if s.get("tam_y_final") else "",
         (s["success_rate"], "pct") if s["success_rate"] is not None else "",
         s["note"]]
        for s in out["segments"]
    ]
    proj_rows: List[List[Any]] = [
        [("Growth driver", H), ("%/yr", H), ("Note", H)],
    ] + [
        [g["name"], (g["annual_pct"] / 100.0, "pct"), g["note"]]
        for g in out["growth_drivers"]
    ] + [
        ["Composite CAGR", (out["composite_cagr_pct"] / 100.0, "pct"), ""],
        [],
        [("Year", H), ("TAM", H), ("SAM", H), ("SOM", H)],
    ] + [
        [p["year"], (p["tam"], "money"), (p["sam"], "money"),
         (p["som"], "money")]
        for p in out["projection"]
    ]
    src_rows: List[List[Any]] = [
        [("#", H), ("Item", H), ("Source", H)],
    ]
    n_src = 0
    seen_src = set()
    for st in out["steps"]:
        if st["source"] and st["source"] not in seen_src:
            seen_src.add(st["source"])
            n_src += 1
            src_rows.append([n_src, st["name"], st["source"]])
    for g in out["growth_drivers"]:
        if g["note"] and g["note"] not in seen_src:
            seen_src.add(g["note"])
            n_src += 1
            src_rows.append([n_src, f"{g['name']} (growth driver)",
                             g["note"]])
    if out.get("basis_note"):
        n_src += 1
        src_rows.append([n_src, "Basis", out["basis_note"]])
    agenda_rows: List[List[Any]] = [
        [("#", H), ("Diligence question", H)],
    ] + [
        [f"Q{i}", q]
        for i, q in enumerate(_derive_agenda_items(out), 1)
    ]
    # Method & uncertainty sheet — archetype, triangulation gate, MC band.
    arch = out.get("archetype") or {}
    method_rows: List[List[Any]] = [
        [("Method & uncertainty", H), ("", H)],
        ["Archetype", arch.get("label", "")],
        ["Complexity", arch.get("complexity", "")],
        ["Formula", arch.get("formula", "")],
        ["When to use", arch.get("when_to_use", "")],
        ["Primary sources", arch.get("primary_sources", "")],
        [],
    ]
    tri = out.get("triangulation")
    if tri:
        method_rows += [
            [("Triangulation (bottom-up vs top-down)", H), ("", H)],
            ["Bottom-up TAM", (tri["bottom_up_tam"], "money")],
            ["Top-down TAM", (tri["top_down_tam"], "money")],
            ["Gap", (tri["gap_pct"] / 100.0, "pct")],
            ["Band", tri["band"].upper()],
            ["Verdict", tri["verdict"]],
            ["Top-down basis", tri.get("top_down_source", "")],
            [],
        ]
    mc = monte_carlo(model, n=4000, rel_sigma=0.15, seed=1729)
    method_rows += [
        [("Monte-Carlo TAM band (±15%/driver, n=4,000)", H), ("", H)],
        ["P10", (mc["p10"], "money")],
        ["P50 (≈ point estimate)", (mc["p50"], "money")],
        ["P90", (mc["p90"], "money")],
        ["Coefficient of variation", (mc["cv"], "pct")],
    ]
    if out.get("bass"):
        method_rows += [[], [("Bass adoption · cumulative share of SAM",
                              H), ("", H)]]
        for b in out["bass"]:
            method_rows.append([f"Year {b['period']}",
                                (b["cum_frac"], "pct")])
    # Method sheet is appended LAST so the established sheet ordering
    # (Funnel=1, Segments=2, Projection=3, Sources=4, Agenda=5) — which
    # downstream code and tests index by position — is preserved.
    return write_xlsx([
        Sheet("Funnel & chain", funnel_rows,
              col_widths=[34, 8, 14, 16, 44, 16]),
        Sheet("Segments", seg_rows,
              col_widths=[26, 13, 15, 12, 15, 13, 40]),
        Sheet("Projection", proj_rows, col_widths=[34, 12, 40, 16]),
        Sheet("Sources", src_rows, col_widths=[5, 38, 70]),
        Sheet("Diligence agenda", agenda_rows, col_widths=[6, 100]),
        Sheet("Method & uncertainty", method_rows, col_widths=[34, 52]),
    ])
