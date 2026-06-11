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
    TEMPLATES, TamSamModel, compute, fertility_ivf_template,
)
from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_page_title, ck_panel,
    ck_source_purpose,
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
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.1f}M"
    return f"${v:,.0f}"


def _fmt_step_value(st: Dict[str, Any]) -> str:
    if st["op"] == "rate":
        return f"{st['value']*100:,.2f}%"
    if st["op"] == "price":
        return f"${st['value']:,.0f}"
    # Plain decimal — :,.4g goes scientific on populations (3.66e+06).
    v = st["value"]
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}"


def _fmt_running(st: Dict[str, Any]) -> str:
    # Once a price step lands, the running value is dollars.
    return (_fmt_money(st["running"]) if st["op"] == "price"
            else f"{st['running']:,.0f}")


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
    for i, g in enumerate(model.growth_drivers):
        ov = fnum(f"growth{i}")
        if ov is not None and -50.0 <= ov <= 100.0:
            g.annual_pct = ov
    return model


def render_tam_sam_page(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    model = model_from_qs(qs)
    out = compute(model)
    tmpl_key = (qs.get("template") or ["fertility_ivf"])[0]

    title = ck_page_title(
        "TAM / SAM Builder",
        eyebrow="DILIGENCE · MARKET SIZING",
        meta=(f"{html.escape(out['name'])} · TAM {_fmt_money(out['tam'])} · "
              f"{out['composite_cagr_pct']:+.1f}%/yr composite"),
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

    tmpl_bar = (
        '<div class="ts2-tmpl">'
        + "".join(
            f'<a href="/diligence/tam-sam?template={k}" '
            f'class="{"on" if k == tmpl_key else ""}">{html.escape(lbl)}</a>'
            for k, lbl in (("fertility_ivf", "Fertility · IVF"),
                           ("dialysis", "Dialysis · in-center"),
                           ("blank", "Blank scaffold")))
        + '</div>'
    )

    funnel = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);'
        'gap:8px;margin:0 0 16px;">'
        + ck_kpi_block("TAM", _fmt_money(out["tam"]), "full driver chain")
        + ck_kpi_block(
            "SAM", _fmt_money(out["sam"]),
            f"{out['sam_share']*100:.0f}% addressable")
        + ck_kpi_block(
            "SOM", _fmt_money(out["som"]),
            f"{out['som_share']*100:.0f}% of SAM obtainable")
        + ck_kpi_block(
            "Composite growth", f"{out['composite_cagr_pct']:+.1f}%/yr",
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
            f'<td>{html.escape(st["name"])}'
            f'<div class="ts2-src">{html.escape(st["source"] or "")}</div></td>'
            f'<td class="r"><input name="step{i}" value="{form_val}" '
            f'aria-label="{html.escape(st["name"], quote=True)}"/>'
            f' <span class="ts2-src">{html.escape(st["unit"])}'
            f'{" (%)" if st["op"] == "rate" else ""}</span></td>'
            f'<td class="r">{_fmt_step_value(st)}</td>'
            f'<td class="r ts2-run">{_fmt_running(st)}</td>'
            '</tr>'
        )
    sam_row = (
        '<tr><td>Addressable share (SAM)'
        f'<div class="ts2-src">{html.escape(model.sam_note or "")}</div></td>'
        f'<td class="r"><input name="sam_share" '
        f'value="{model.sam_share*100:g}"/> <span class="ts2-src">% of TAM'
        '</span></td>'
        f'<td class="r">{model.sam_share*100:,.1f}%</td>'
        f'<td class="r ts2-run">{_fmt_money(out["sam"])}</td></tr>'
        '<tr><td>Obtainable share (SOM)'
        f'<div class="ts2-src">{html.escape(model.som_note or "")}</div></td>'
        f'<td class="r"><input name="som_share" '
        f'value="{model.som_share*100:g}"/> <span class="ts2-src">% of SAM'
        '</span></td>'
        f'<td class="r">{model.som_share*100:,.1f}%</td>'
        f'<td class="r ts2-run">{_fmt_money(out["som"])}</td></tr>'
    )
    growth_inputs = "".join(
        '<div class="ts2-drv">'
        f'<span>{html.escape(g["name"])}'
        f'<div class="ts2-src">{html.escape(g["note"] or "")}</div></span>'
        f'<span class="pct"><input name="growth{i}" '
        f'value="{g["annual_pct"]:g}" style="width:70px;"/> %/yr</span>'
        '</div>'
        for i, g in enumerate(out["growth_drivers"])
    )
    chain_panel = ck_panel(
        f'<form method="GET" action="/diligence/tam-sam">'
        f'<input type="hidden" name="template" '
        f'value="{html.escape(tmpl_key, quote=True)}"/>'
        '<table class="ts2-chain"><thead><tr>'
        '<th>Driver</th><th style="text-align:right;">Your input</th>'
        '<th style="text-align:right;">Applied</th>'
        '<th style="text-align:right;">Running value</th>'
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

    seg_rows = ""
    for s in out["segments"]:
        sr = (f"{s['success_rate']*100:,.0f}%"
              if s["success_rate"] is not None else "—")
        seg_rows += (
            '<tr>'
            f'<td>{html.escape(s["name"])}'
            f'<div class="ts2-src">{html.escape(s["note"] or "")}</div></td>'
            f'<td class="r">{s["share_of_volume"]*100:,.0f}%</td>'
            f'<td class="r">{_fmt_money(s["tam_value"])}</td>'
            f'<td class="r">{sr}</td>'
            '</tr>'
        )
    seg_panel = ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        '<th>Segment</th><th style="text-align:right;">Volume share</th>'
        '<th style="text-align:right;">TAM slice</th>'
        '<th style="text-align:right;">Success rate</th>'
        f'</tr></thead><tbody>{seg_rows}</tbody></table>',
        title="Segments · the whitespace map",
    ) if out["segments"] else ""

    proj_rows = "".join(
        '<tr>'
        f'<td>Year {p["year"]}</td>'
        f'<td class="r">{_fmt_money(p["tam"])}</td>'
        f'<td class="r">{_fmt_money(p["sam"])}</td>'
        f'<td class="r">{_fmt_money(p["som"])}</td>'
        '</tr>'
        for p in out["projection"]
    )
    proj_panel = ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        '<th>Horizon</th><th style="text-align:right;">TAM</th>'
        '<th style="text-align:right;">SAM</th>'
        '<th style="text-align:right;">SOM</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table>'
        f'<p class="ts2-src" style="margin:10px 0 0;">Composite '
        f'{out["composite_cagr_pct"]:+.1f}%/yr from the named drivers '
        'above — the decomposition survives into the export so the IC '
        'sees which lever carries the growth.</p>',
        title=f"{out['horizon_years']}-year projection",
    )

    export_qs = urllib.parse.urlencode(
        {k: v[0] for k, v in qs.items() if v}, doseq=False)
    export_panel = ck_panel(
        '<div class="ts2-form-bar" style="margin:0;" id="ts2-export">'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.xlsx?{export_qs}" download>'
        '⬇ Formatted Excel (.xlsx)</a>'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.csv?{export_qs}" download>'
        '⬇ CSV</a>'
        '<span class="ts2-src">Excel ships 3 formatted sheets — Funnel '
        '&amp; chain, Segments, Projection — headers, $ and % formats, '
        'column widths set.</span></div>',
        title="Export · drop into the deal model",
    )

    basis = (
        f'<p class="ts2-src" style="margin:4px 0 14px;">'
        f'{html.escape(out["basis_note"])}</p>'
        if out["basis_note"] else ""
    )

    body = (
        _CSS + title + src + tmpl_bar + basis + funnel
        + chain_panel + seg_panel + proj_panel + export_panel
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
    model = model_from_qs(qs)
    out = compute(model)
    buf = io.StringIO()
    w = csv.writer(buf)
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
        w.writerow(["Segment", "Volume share", "TAM slice", "Success rate",
                    "Note"])
        for s in out["segments"]:
            w.writerow([s["name"], s["share_of_volume"],
                        round(s["tam_value"], 2),
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
    return buf.getvalue()


def tam_sam_xlsx(qs: Dict[str, List[str]]) -> bytes:
    from ..exports.xlsx_writer import Sheet, write_xlsx
    model = model_from_qs(qs)
    out = compute(model)
    H = "header"
    funnel_rows: List[List[Any]] = [
        [(f"TAM/SAM build · {out['name']}", H), ("", H), ("", H), ("", H),
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
         ("Success rate", H), ("Note", H)],
    ] + [
        [s["name"], (s["share_of_volume"], "pct"),
         (s["tam_value"], "money"),
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
    return write_xlsx([
        Sheet("Funnel & chain", funnel_rows,
              col_widths=[34, 8, 14, 16, 44, 16]),
        Sheet("Segments", seg_rows, col_widths=[14, 14, 16, 14, 40]),
        Sheet("Projection", proj_rows, col_widths=[34, 12, 40, 16]),
    ])
