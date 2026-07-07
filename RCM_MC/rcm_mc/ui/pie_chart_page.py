"""Pie Chart — type a label, a value, and a colour per slice, get a
clean, client-ready pie or donut. No table paste, no dynamic data: just
fill in the rows and render a presentable static chart for the deck.

Each slice is three fields — ``l{i}`` label, ``v{i}`` value, ``c{i}``
colour — so a configured chart is a shareable URL. Blank rows are
ignored. Rendering is ``cdd_chart_kit.presentable_pie``.

2026-07 facelift (v5 chartis editorial): ck_editorial_head masthead
with live-state meta, page-scoped .pc-* CSS (kit vars only — no inline
hexes), donut-with-centre-TOTAL as the default presentation
(product-owner ask; the donut control is a two-option select so the
"off" state always round-trips through the URL), a page-side
"Computed shares" table at house numeric discipline (1dp percents),
and a skipped-rows warning so a typo'd value never vanishes silently.
The SVG itself still comes from the shared ``presentable_pie`` —
its white background is intentional (slide paste) and untouched.
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_copy_share_link_button, ck_editorial_head,
    ck_eyebrow, ck_fmt_number, ck_fmt_percent, ck_page_actions,
    ck_provenance_tooltip, ck_source_purpose,
)
from .cdd_chart_kit import (
    presentable_pie, PALETTES, SIZE_PRESETS, chart_export_toolbar,
)

_ROWS = 10
_CHARTIS = PALETTES["Chartis"]
# Swatch colours echo user input into a style attribute — restrict to a
# literal hex token so nothing but a colour can land there. (The chart
# SVG keeps the raw value: shared-kit behaviour, unchanged.)
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")

# A clear, client-ready default so the page opens populated.
_DEFAULTS: List[Dict[str, Any]] = [
    {"label": "Segment A", "value": "40", "color": _CHARTIS[0]},
    {"label": "Segment B", "value": "25", "color": _CHARTIS[1]},
    {"label": "Segment C", "value": "20", "color": _CHARTIS[2]},
    {"label": "Segment D", "value": "15", "color": _CHARTIS[3]},
]


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _qsbool(qs, key, default):
    v = _qs1(qs, key, "")
    if v == "":
        return default
    return v not in ("0", "false", "off", "no")


def _collect_slices(qs: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pull slice rows from the qs; fall back to the defaults the first
    time the page is opened (no slice params present)."""
    any_row = any(_qs1(qs, f"l{i}") or _qs1(qs, f"v{i}")
                  for i in range(_ROWS))
    rows: List[Dict[str, Any]] = []
    for i in range(_ROWS):
        if not any_row and i < len(_DEFAULTS):
            d = _DEFAULTS[i]
            rows.append({"label": d["label"], "value": d["value"],
                         "color": d["color"]})
            continue
        label = _qs1(qs, f"l{i}")
        val = _qs1(qs, f"v{i}")
        color = _qs1(qs, f"c{i}") or _CHARTIS[i % len(_CHARTIS)]
        rows.append({"label": label, "value": val, "color": color})
    return rows


def _to_float(s: str) -> Optional[float]:
    try:
        return float(str(s).replace("%", "").replace("$", "")
                     .replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _num(v: float) -> str:
    """House number formatting for user-unit values: integers plain,
    fractional values at 2dp — never 1 or 3."""
    return ck_fmt_number(v) if v == int(v) else \
        ck_fmt_number(v, precision=2)


# Page-scoped CSS — every colour is a kit var with its canonical
# fallback; 2px radii per the kit idiom. Injected via chartis_shell's
# extra_css so it lands in <head> after the kit sheet.
_PC_CSS = """
.pc-wrap{max-width:1040px;margin:0 auto;}
.pc-wrap .ck-eyebrow{margin-bottom:10px;}
.pc-grid{display:grid;grid-template-columns:1fr 1.05fr;gap:30px;
  align-items:start;}
@media (max-width:860px){.pc-grid{grid-template-columns:1fr;}}
.pc-cols-head{display:grid;grid-template-columns:24px 1fr 92px 52px;
  gap:8px;font:500 10px/1 var(--sc-mono,monospace);letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted,#7a8595);margin:0 0 5px;}
.pc-cols-head .r{text-align:right;}
.pc-row{display:grid;grid-template-columns:24px 1fr 92px 52px;gap:8px;
  align-items:center;margin-bottom:6px;}
.pc-row-n{font:500 11px/1 var(--sc-mono,monospace);
  font-variant-numeric:tabular-nums;color:var(--muted,#7a8595);
  text-align:right;}
.pc-input{height:30px;border:1px solid var(--rule,#c9bf9c);
  border-radius:2px;padding:0 8px;width:100%;box-sizing:border-box;
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a);
  font:400 13.5px/1 var(--sc-serif,Georgia),serif;}
.pc-num{text-align:right;font-family:var(--sc-mono,monospace);
  font-variant-numeric:tabular-nums;font-size:12.5px;}
.pc-color{width:52px;height:30px;border:1px solid var(--rule,#c9bf9c);
  border-radius:2px;padding:2px;background:var(--paper-card,#fefcf3);
  cursor:pointer;box-sizing:border-box;}
.pc-help{font:400 11.5px/1.55 var(--sc-sans,Inter),sans-serif;
  color:var(--muted,#7a8595);margin:8px 0 0;max-width:54ch;}
.pc-help em{font-family:var(--sc-serif,Georgia),serif;font-style:italic;
  color:var(--green-deep,#154e36);}
.pc-opts{display:flex;flex-direction:column;gap:20px;}
.pc-group{border:0;padding:0;margin:0;min-width:0;display:flex;
  flex-direction:column;gap:9px;}
.pc-group legend{font:500 10px/1 var(--sc-mono,monospace);
  letter-spacing:.16em;text-transform:uppercase;
  color:var(--green-deep,#154e36);padding:0;margin:0 0 2px;}
.pc-field{display:block;font:500 11px/1.5 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);}
.pc-field .pc-input,.pc-field .pc-select{margin-top:3px;height:32px;}
.pc-duo{display:flex;gap:10px;}
.pc-duo .pc-field{flex:1;min-width:0;}
.pc-duo .pc-field.pc-narrow{flex:0 0 110px;}
.pc-select{width:100%;height:32px;border:1px solid var(--rule,#c9bf9c);
  border-radius:2px;box-sizing:border-box;padding:0 6px;
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a);
  font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;}
.pc-actions{display:flex;align-items:center;gap:16px;margin-top:6px;}
.pc-primary{font:600 11px/1 var(--sc-sans,Inter),sans-serif;
  letter-spacing:.1em;text-transform:uppercase;
  background:var(--ink-deep,#0e1a29);color:var(--paper-card,#fefcf3);
  border:1px solid var(--ink-deep,#0e1a29);border-radius:2px;
  padding:11px 20px;cursor:pointer;
  transition:background .12s,border-color .12s;}
.pc-primary:hover{background:var(--green-deep,#154e36);
  border-color:var(--green-deep,#154e36);}
.pc-reset{font:500 11px/1 var(--sc-sans,Inter),sans-serif;
  letter-spacing:.06em;text-transform:uppercase;
  color:var(--green-deep,#154e36);text-decoration:none;
  border-bottom:1px solid var(--rule,#c9bf9c);padding-bottom:2px;}
.pc-reset:hover{border-bottom-color:var(--green-deep,#154e36);}
.pc-warn{font:500 11px/1.5 var(--sc-mono,monospace);letter-spacing:.04em;
  color:var(--gold,#a08227);background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);
  border-left:3px solid var(--gold,#a08227);border-radius:2px;
  padding:9px 12px;margin:24px 0 0;}
.pc-card{background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:18px 20px 16px;margin-top:26px;}
.pc-card-head{display:flex;justify-content:space-between;
  align-items:baseline;gap:14px;flex-wrap:wrap;margin:0 0 12px;}
.pc-card-note{font:500 10px/1.4 var(--sc-mono,monospace);
  letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted,#7a8595);}
.pc-stage{text-align:center;}
.pc-caption{font:500 10px/1.6 var(--sc-mono,monospace);
  letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted,#7a8595);text-align:center;margin:12px 0 0;}
.pc-shares table{width:100%;border-collapse:collapse;}
.pc-shares th{font:500 10px/1 var(--sc-mono,monospace);
  letter-spacing:.12em;text-transform:uppercase;text-align:left;
  color:var(--muted,#7a8595);padding:6px 8px;
  border-bottom:1px solid var(--rule,#c9bf9c);}
.pc-shares th.r,.pc-shares td.r{text-align:right;}
.pc-shares td{font:400 13px/1.4 var(--sc-sans,Inter),sans-serif;
  color:var(--ink,#16263a);padding:7px 8px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.pc-shares td.r{font-family:var(--sc-mono,monospace);
  font-variant-numeric:tabular-nums;font-size:12.5px;}
.pc-shares td.pc-td-n{font-family:var(--sc-mono,monospace);
  font-variant-numeric:tabular-nums;color:var(--muted,#7a8595);
  font-size:11px;text-align:right;width:24px;}
.pc-shares tbody tr:hover td{background:var(--paper-hi,#fbf6e8);}
.pc-shares tr.pc-total td{font-weight:700;border-bottom:0;
  border-top:1px solid var(--rule,#c9bf9c);
  color:var(--ink-deep,#0e1a29);}
.pc-swatch{display:inline-block;width:10px;height:10px;border-radius:2px;
  margin-right:8px;vertical-align:middle;
  border:1px solid var(--rule,#c9bf9c);}
.pc-form input:focus-visible,.pc-form select:focus-visible,
.pc-form button:focus-visible,.pc-wrap a:focus-visible{
  outline:2px solid var(--green-deep,#154e36);outline-offset:1px;}
@media print{.pc-form,.pc-warn{display:none;}}
"""


def render_pie_chart_page(qs: "Dict[str, Any] | None" = None) -> str:
    rows = _collect_slices(qs)
    title = _qs1(qs, "title", "")
    subtitle = _qs1(qs, "subtitle", "")
    suffix = _qs1(qs, "suffix", "")
    # Donut with the serif centre TOTAL is the default presentation
    # (product-owner ask). The control below is a two-option select —
    # unlike the old checkbox it ALWAYS submits, so donut=0 survives
    # the URL round-trip and partners can still get a solid pie.
    donut = _qsbool(qs, "donut", True)
    label_mode = _qs1(qs, "mode", "percent")
    if label_mode not in ("percent", "value", "both", "none"):
        label_mode = "percent"
    size = _qs1(qs, "size", "M")
    width_px = dict(SIZE_PRESETS).get(size, 720)
    center = _qs1(qs, "center", "")

    slices = [{"label": r["label"], "value": _to_float(r["value"]),
               "color": r["color"]} for r in rows]
    footnote = _qs1(qs, "footnote", "")
    pie_opts: Dict[str, Any] = {
        "title": title or "Pie Chart", "subtitle": subtitle,
        "donut": donut, "label_mode": label_mode, "value_suffix": suffix,
        "width_px": width_px, "footnote": footnote,
    }
    if center:
        # Partner override for the donut centre (e.g. "$4.2M"); when
        # absent the renderer draws the auto sum + TOTAL caption.
        pie_opts["hole_total"] = center
    svg = presentable_pie(slices, pie_opts)

    # Mirror the shared renderer's filter so the page-side numbers
    # always agree with the drawn chart: positive numeric values only.
    clean = [s for s in slices
             if s["value"] is not None and s["value"] > 0]
    total = sum(s["value"] for s in clean)
    skipped = sum(
        1 for r, s in zip(rows, slices)
        if (str(r["label"]).strip() or str(r["value"]).strip())
        and not (s["value"] is not None and s["value"] > 0))

    # ── Masthead — real state in the meta, sentence case in the lede.
    n = len(clean)
    shape_word = "DONUT" if donut else "PIE"
    mode_word = {"percent": "PERCENT", "value": "VALUE",
                 "both": "VALUE·%", "none": "NO"}[label_mode]
    size_label = size if size in dict(SIZE_PRESETS) else "M"
    if clean:
        meta = (f"{n} SLICE{'S' if n != 1 else ''} · TOTAL {_num(total)}"
                f"{suffix} · {shape_word} · {mode_word} LABELS · "
                f"SIZE {size_label}")
    else:
        meta = f"NO SLICES YET · {shape_word} · SIZE {size_label}"
    head = ck_editorial_head(
        "RESEARCH · CHART STUDIO",
        "Pie Chart",
        meta=meta,
        lede_italic_phrase="A deck-ready donut in seconds —",
        lede_body=(
            "type a label, a value, and a colour per slice. The "
            "configured chart is a shareable URL, and it exports as "
            "SVG or 3× PNG for slide paste."),
        actions_html=ck_copy_share_link_button(),
        show_legend=False,
    )

    # ── Slice input rows.
    row_html = ""
    for i, r in enumerate(rows):
        row_html += (
            f'<div class="pc-row">'
            f'<span class="pc-row-n">{i + 1}</span>'
            f'<input type="text" class="pc-input" name="l{i}" '
            f'value="{html.escape(r["label"])}" placeholder="Label" '
            f'aria-label="Label for slice {i + 1}">'
            f'<input type="text" class="pc-input pc-num" name="v{i}" '
            f'value="{html.escape(r["value"])}" placeholder="Value" '
            f'inputmode="decimal" aria-label="Value for slice {i + 1}">'
            f'<input type="color" class="pc-color" name="c{i}" '
            f'aria-label="Colour for slice {i + 1}" '
            f'value="{html.escape(r["color"])}">'
            f'</div>')

    mode_opts = "".join(
        f'<option value="{m}"{" selected" if m == label_mode else ""}>'
        f'{lab}</option>' for m, lab in
        # "No labels", not "None": a literal >None< in page HTML is
        # indistinguishable from a None-leak to the route walker's leak
        # gate (and reads ambiguous to a partner anyway).
        (("percent", "Percent"), ("value", "Value"),
         ("both", "Value · %"), ("none", "No labels")))
    donut_opts = (
        f'<option value="1"{" selected" if donut else ""}>'
        f'Donut (ring)</option>'
        f'<option value="0"{"" if donut else " selected"}>'
        f'Pie (solid)</option>')
    size_opts = "".join(
        f'<option value="{k}"{" selected" if k == size else ""}>{k}'
        f'</option>' for k, _w in SIZE_PRESETS)

    slices_col = (
        '<section>'
        + ck_eyebrow("SLICES — LABEL · VALUE · COLOUR")
        + '<div class="pc-cols-head"><span></span><span>Label</span>'
          '<span class="r">Value</span><span>Colour</span></div>'
        + row_html
        + '<p class="pc-help">Leave a row blank to drop the slice. '
          'Values can be any units (percent or absolute) — the chart '
          'computes <em>shares</em>. Tip: if your values are already '
          'percentages, leave Unit blank and choose Percent labels to '
          'avoid double percent signs.</p>'
        + '</section>')

    opts_col = (
        '<div class="pc-opts">'
        # Chart text.
        '<fieldset class="pc-group"><legend>Text</legend>'
        '<label class="pc-field">Title'
        f'<input type="text" class="pc-input" name="title" '
        f'value="{html.escape(title)}"></label>'
        '<label class="pc-field">Subtitle'
        f'<input type="text" class="pc-input" name="subtitle" '
        f'value="{html.escape(subtitle)}"></label>'
        '<label class="pc-field">Source / footnote'
        f'<input type="text" class="pc-input" name="footnote" '
        f'value="{html.escape(footnote)}" placeholder="Source: …">'
        '</label></fieldset>'
        # Labels & units.
        '<fieldset class="pc-group"><legend>Labels &amp; units</legend>'
        '<div class="pc-duo">'
        '<label class="pc-field">Slice labels'
        f'<select name="mode" class="pc-select">{mode_opts}</select>'
        '</label>'
        '<label class="pc-field pc-narrow">Unit'
        f'<input type="text" class="pc-input pc-num" name="suffix" '
        f'value="{html.escape(suffix)}" placeholder="% or $"></label>'
        '</div></fieldset>'
        # Shape & size.
        '<fieldset class="pc-group"><legend>Shape &amp; size</legend>'
        '<div class="pc-duo">'
        '<label class="pc-field">Shape'
        f'<select name="donut" class="pc-select">{donut_opts}</select>'
        '</label>'
        '<label class="pc-field pc-narrow">Size'
        f'<select name="size" class="pc-select">{size_opts}</select>'
        '</label></div>'
        '<label class="pc-field">Centre text (donut)'
        f'<input type="text" class="pc-input" name="center" '
        f'value="{html.escape(center)}" '
        f'placeholder="Auto: sum + TOTAL caption"></label>'
        '</fieldset>'
        # Actions.
        '<div class="pc-actions">'
        '<button type="submit" class="pc-primary">Render chart</button>'
        '<a class="pc-reset" href="/pie-chart">Reset to example</a>'
        '</div></div>')

    form = (
        '<form method="get" action="/pie-chart" class="pc-form">'
        f'<div class="pc-grid">{slices_col}{opts_col}</div></form>')

    # ── Partial-failure feedback: a typo'd or negative value silently
    # vanishes from the chart (kit drops it) — say so, quietly.
    warn_html = ""
    if skipped:
        warn_html = (
            f'<p class="pc-warn" role="status">{skipped} row'
            f'{"s" if skipped != 1 else ""} skipped — values must be '
            f'positive numbers to draw.</p>')

    # ── Preview card. The SVG keeps its own white background (the
    # slide plate) — the parchment card frames it deliberately.
    caption = (f"LIVE PREVIEW · {shape_word} · "
               f"{n} SLICE{'S' if n != 1 else ''} · EXPORTS REPRODUCE "
               f"THIS FRAME ON A WHITE SLIDE PLATE")
    preview = (
        '<section class="pc-card">'
        '<div class="pc-card-head">'
        + ck_eyebrow("Preview")
        + '<span class="pc-card-note">EXPORTS: SVG · PNG 3× — WHITE '
          'SLIDE BACKGROUND</span></div>'
        + f'<div class="pc-stage"><div id="pieOut">{svg}</div>'
        + chart_export_toolbar("pieOut", "pie-chart")
        + '</div>'
        + f'<p class="pc-caption">{caption}</p>'
        + '</section>')

    # ── Computed shares — the page-side numeric readout at house
    # discipline (1dp percents, mono tabular-nums, emphasized TOTAL).
    shares_html = ""
    if clean:
        esc_suffix = html.escape(suffix)
        body_rows = ""
        for i, s in enumerate(clean):
            frac = s["value"] / total if total else 0.0
            color = str(s["color"] or "")
            if not _HEX_RE.match(color):
                color = _CHARTIS[i % len(_CHARTIS)]
            label = s["label"] or f"Slice {i + 1}"
            body_rows += (
                f'<tr><td class="pc-td-n">{i + 1}</td>'
                f'<td><span class="pc-swatch" '
                f'style="background:{color};"></span>'
                f'{html.escape(label)}</td>'
                f'<td class="r">{_num(s["value"])}{esc_suffix}</td>'
                f'<td class="r">{ck_fmt_percent(frac)}</td></tr>')
        total_value = ck_provenance_tooltip(
            "Computed total", f"{_num(total)}{esc_suffix}",
            explainer=(
                "Sum of every positive slice value. Each share is "
                "value ÷ total; rows with blank, non-numeric, zero, "
                "or negative values are excluded from the chart and "
                "from this table."))
        shares_html = (
            '<section class="pc-card pc-shares">'
            '<div class="pc-card-head">'
            + ck_eyebrow("Computed shares")
            + '<span class="pc-card-note">SHARES AT 1DP · ROWS MATCH '
              'THE DRAWN CHART</span></div>'
            '<table><thead><tr><th class="r">#</th><th>Slice</th>'
            '<th class="r">Value</th><th class="r">Share</th></tr>'
            '</thead><tbody>'
            + body_rows
            + f'<tr class="pc-total"><td class="pc-td-n"></td>'
              f'<td>TOTAL</td><td class="r">{total_value}</td>'
              f'<td class="r">{ck_fmt_percent(1.0)}</td></tr>'
            + '</tbody></table></section>')

    body = (
        head
        + ck_source_purpose(
            purpose="Make a clean, deck-ready pie or donut in seconds — "
                    "set each slice's value and colour directly.",
            universe="user-supplied",
            source="Your slice inputs. Defaults are example placeholders.",
        )
        + '<div class="pc-wrap">'
        + form
        + warn_html
        + preview
        + shares_html
        + '</div>'
        + ck_page_actions()
    )
    return chartis_shell(
        body, "Pie Chart", active_nav="/research",
        subtitle="Client-ready pie/donut", extra_css=_PC_CSS)
