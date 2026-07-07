"""Pivot / analysis workbench for a cleaned claims file — ``/npi-cleaner/analyze/<job>``.

A self-contained, Tableau-style pivot builder: assign any column to Rows,
Columns, Values (with Count / Sum / Avg / Min / Max) or Filters, and get a live
pivot table plus a chart (grouped bar / stacked bar / line / heatmap / scatter /
box / histogram / correlation) built with an inline-SVG renderer — no chart
library, CSP-safe. The cleaned rows are fetched from ``/npi-cleaner/data/<job>``
(capped server-side) and everything computes in the browser, so pivoting and
re-charting are instant.

Visual system is the v5 chartis editorial kit: parchment page, paper cards,
deep-green accents, JetBrains Mono numerics, and the house dataviz tokens
(``--sc-data-1..5`` + severity colors) for every chart series. Charts carry a
legend for >=2 series, direct value labels when the mark count is small,
hover/focus tooltips and a recessive grid. The pivot table itself is the
always-present table view: sticky header row + sticky row-label column,
zebra striping, quantized green heat-wash on value cells, and an emphasized
grand-total row/column.
"""
from __future__ import annotations

from ._chartis_kit import (
    chartis_shell,
    ck_editorial_head,
    ck_empty_state,
    ck_fmt_number,
    ck_page_actions,
    ck_provenance_tooltip,
    ck_section_header,
    ck_signal_badge,
)

# The /npi-cleaner/data/<job> feed is capped server-side (server.py) — every
# pivot total is computed on at most this many rows. Disclosed in the head's
# source note, the warning badge and the under-table note so a partner never
# mistakes a truncated total for a whole-file total.
_DATA_CAP = 20000


_EXTRA_CSS = r"""
/* ============================================================
   NPI Pivot / Analysis workbench — v5 chartis editorial skin.
   Kit tokens only (canonical fallbacks): --paper-card / --bg /
   --sc-bone surfaces, --sc-rule / --rule-soft hairlines,
   --green-deep accent, --ink / --ink-2 text, --sc-mono numerics.
   ============================================================ */
.an-wrap{max-width:1220px;margin:0 auto;
  --an-r:var(--sc-r-2,4px);
  --an-shadow:var(--sc-shadow-1,0 1px 2px rgba(6,22,38,.06))}
.an-wrap *{box-sizing:border-box}

/* ---- meta / status row ---- */
.an-meta-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  margin:0 0 18px}
.an-meta{font-size:11px;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);letter-spacing:.08em;
  text-transform:uppercase;background:var(--sc-bone,#ece5d6);
  border:1px solid var(--sc-rule,#d6cfc0);padding:5px 10px;
  border-radius:var(--an-r);font-variant-numeric:tabular-nums}
#an-warn[hidden],.an-note[hidden]{display:none}
.an-note{font-size:11px;color:var(--green-deep,#154e36);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);letter-spacing:.03em}

/* ---- stat tiles (ck_kpi_block anatomy, JS-rendered) ---- */
.an-tiles-caprow{margin:0 0 8px}
.an-tiles-cap{font-size:10px;font-weight:600;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(152px,1fr));
  gap:12px;margin-bottom:20px}
.an-tile{display:block;border:1px solid var(--sc-rule,#d6cfc0);
  border-top:2px solid var(--green-deep,#154e36);border-radius:var(--an-r);
  background:var(--paper-card,#fefcf3);padding:12px 14px;
  box-shadow:var(--an-shadow);min-width:0}
.an-tile .k{display:block;font-size:10px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--ink-2,#2b3e54);font-weight:600;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.an-tile .v{display:block;font-size:21px;margin-top:5px;
  color:var(--ink,#16263a);line-height:1.1;letter-spacing:-.01em;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums}
.an-tile .s{display:block;font-size:10px;color:var(--ink-2,#2b3e54);
  opacity:.72;margin-top:5px;letter-spacing:.02em;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ---- quick views ---- */
.an-views{display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  margin-bottom:20px}
.an-views-lbl{font-size:10px;color:var(--ink-2,#2b3e54);font-weight:600;
  text-transform:uppercase;letter-spacing:.14em;
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}

/* ---- layout ---- */
.an-grid{display:grid;grid-template-columns:262px 1fr;gap:20px;
  align-items:start}
.an-grid>*{min-width:0}
@media(max-width:820px){
  .an-grid{grid-template-columns:1fr}
  .an-fields{position:static;max-height:none}
}

/* ---- field list rail ---- */
.an-fields{border:1px solid var(--sc-rule,#d6cfc0);border-radius:var(--an-r);
  background:var(--paper-card,#fefcf3);padding:14px;max-height:74vh;
  overflow:auto;box-shadow:var(--an-shadow);position:sticky;top:12px}
.an-fields h4{margin:0 0 4px;font-size:10px;text-transform:uppercase;
  letter-spacing:.14em;color:var(--ink-2,#2b3e54);font-weight:600;
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-fields-hint{margin:0 0 10px;padding-bottom:9px;font-size:10px;
  color:var(--ink-2,#2b3e54);opacity:.75;letter-spacing:.03em;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  border-bottom:1px solid var(--rule-soft,#ddd1ac)}
.an-field{display:flex;align-items:center;justify-content:space-between;
  gap:6px;padding:5px 8px;border-radius:var(--an-r);font-size:12.5px;
  transition:background .12s}
.an-field:hover{background:color-mix(in srgb,var(--green-deep,#154e36) 6%,transparent)}
.an-field .fn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--ink,#16263a)}
.an-field .num{color:var(--green-deep,#154e36);font-size:9.5px;margin-left:5px;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);font-weight:700}
.an-field .btns{display:flex;gap:3px;flex:none;opacity:.55;transition:opacity .12s}
.an-field:hover .btns,.an-field:focus-within .btns{opacity:1}
.an-field button{appearance:none;border:1px solid var(--sc-rule,#d6cfc0);
  background:var(--sc-bone,#ece5d6);border-radius:var(--an-r);width:23px;
  height:23px;font-size:10.5px;font-weight:700;cursor:pointer;
  color:var(--ink-2,#2b3e54);padding:0;transition:all .12s;
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-field button:hover{border-color:var(--green-deep,#154e36);
  color:#fff;background:var(--green-deep,#154e36)}

/* ---- drop zones ---- */
.an-zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(172px,1fr));
  gap:12px;margin-bottom:16px}
.an-zone{border:1px dashed var(--sc-rule-2,#bfb6a2);border-radius:var(--an-r);
  padding:11px 12px;background:var(--paper-card,#fefcf3);min-height:66px;
  transition:border-color .12s,background .12s}
.an-zone:hover{border-color:color-mix(in srgb,var(--green-deep,#154e36) 45%,var(--sc-rule-2,#bfb6a2));
  background:color-mix(in srgb,var(--green-deep,#154e36) 2.5%,var(--paper-card,#fefcf3))}
.an-zone h5{margin:0 0 8px;font-size:10px;text-transform:uppercase;
  letter-spacing:.1em;color:var(--ink-2,#2b3e54);font-weight:600;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  display:flex;align-items:center;gap:6px}
.an-zone h5::before{content:"";width:7px;height:7px;
  border-radius:var(--sc-r-1,2px);background:var(--green-deep,#154e36);
  opacity:.7;flex:none}
.an-hint{font-size:11.5px;color:var(--ink-2,#2b3e54);opacity:.65;
  font-style:italic;font-family:var(--sc-serif,'Source Serif 4',Georgia,serif)}

/* ---- chips (assigned fields) ---- */
.an-chip{display:inline-flex;align-items:center;gap:4px;
  background:color-mix(in srgb,var(--green-deep,#154e36) 10%,transparent);
  color:var(--green-deep,#154e36);
  border:1px solid color-mix(in srgb,var(--green-deep,#154e36) 24%,transparent);
  border-radius:10px;padding:2px 4px 2px 10px;font-size:12px;
  margin:2px 5px 2px 0;font-weight:600;transition:background .12s,border-color .12s;
  max-width:100%;vertical-align:middle}
.an-chip:hover{background:color-mix(in srgb,var(--green-deep,#154e36) 15%,transparent);
  border-color:color-mix(in srgb,var(--green-deep,#154e36) 40%,transparent)}
.an-chip .x{appearance:none;border:0;background:transparent;cursor:pointer;
  color:inherit;font-weight:700;font-size:13px;line-height:1;width:18px;
  height:18px;display:inline-flex;align-items:center;justify-content:center;
  border-radius:50%;opacity:.7;padding:0;transition:all .12s}
.an-chip .x:hover{opacity:1;
  background:color-mix(in srgb,var(--green-deep,#154e36) 20%,transparent)}

/* ---- control panel: labelled fieldset groups on hairline dividers ---- */
.an-panel{border:1px solid var(--sc-rule,#d6cfc0);border-radius:var(--an-r);
  background:var(--paper-card,#fefcf3);box-shadow:var(--an-shadow);
  padding:2px 16px;margin-bottom:16px}
.an-group{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  border:0;margin:0;min-width:0;
  padding:10px 0;border-bottom:1px solid var(--rule-soft,#ddd1ac)}
.an-group:last-child{border-bottom:0}
.an-group-lbl{float:left;padding:0;flex:none;width:104px;font-size:10px;
  font-weight:600;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-ctl{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;
  text-transform:uppercase;letter-spacing:.04em;font-weight:600;
  color:var(--ink-2,#2b3e54);
  font-family:var(--sc-sans,'Inter Tight',sans-serif)}
.an-agg{margin-top:8px}
.an-agg select,.an-ctl select,.an-group select,
.an-group input[type=text],.an-group input:not([type]){
  padding:5px 8px;border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:var(--an-r);font-size:12px;
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a);
  font-weight:500;text-transform:none;letter-spacing:0;cursor:pointer;
  transition:border-color .12s;
  font-family:var(--sc-sans,'Inter Tight',sans-serif)}
.an-group input[type=text],.an-group input:not([type]){cursor:text;width:130px}
.an-agg select:hover,.an-ctl select:hover,.an-group select:hover{
  border-color:var(--green-deep,#154e36)}
.an-agg select:focus,.an-ctl select:focus,.an-group select:focus,
.an-group input:focus{outline:none;border-color:var(--green-deep,#154e36);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--green-deep,#154e36) 15%,transparent)}
.an-ctl input[type=checkbox]{accent-color:var(--green-deep,#154e36);
  width:15px;height:15px;cursor:pointer}

/* ---- buttons ----
   Same anatomy as the cleaner/history buttons (.npi-dl / .nh-btn):
   2px radius, uppercase 12px/600 tracking — so the trio's controls
   read as one tool. Cards/panels keep the 4px --an-r. */
.an-btn{appearance:none;border:1px solid var(--sc-rule-2,#bfb6a2);
  background:var(--paper-card,#fefcf3);border-radius:var(--sc-r-1,2px);
  padding:6px 12px;font-size:12px;font-weight:600;cursor:pointer;
  letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink,#16263a);transition:all .12s;line-height:1.4;
  font-family:var(--sc-sans,'Inter Tight',sans-serif)}
.an-btn:hover{border-color:var(--green-deep,#154e36);
  background:color-mix(in srgb,var(--green-deep,#154e36) 6%,var(--paper-card,#fefcf3))}
.an-btn:active{transform:translateY(1px)}
.an-btn.prim{background:var(--green-deep,#154e36);color:#fff;
  border-color:var(--green-deep,#154e36)}
.an-btn.prim:hover{filter:brightness(1.12);background:var(--green-deep,#154e36)}
.an-btn.vw:hover{color:var(--green-deep,#154e36)}

/* shared keyboard focus ring */
.an-btn:focus-visible,.an-chip .x:focus-visible,
.an-field button:focus-visible,.an-flt-clear:focus-visible,
.an-ptbl th.sortable:focus-visible{
  outline:2px solid var(--green-deep,#154e36);outline-offset:2px}

/* ---- scatter controls ---- */
.an-scatter-ctl{display:none;gap:12px;align-items:center;flex-wrap:wrap}
.an-scatter-ctl.on{display:flex}

/* ---- chart card (a <figure>) ---- */
.an-chart{border:1px solid var(--sc-rule,#d6cfc0);border-radius:var(--an-r);
  padding:16px;margin:8px 0 0;background:var(--paper-card,#fefcf3);
  box-shadow:var(--an-shadow);min-height:80px}
.an-chart-title{margin:0 0 6px;font-size:13px;font-weight:600;
  color:var(--ink,#16263a);
  font-family:var(--sc-sans,'Inter Tight',sans-serif)}
.an-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;
  font-size:12px;align-items:center}
.an-legend .lg{display:inline-flex;align-items:center;gap:6px;
  color:var(--ink-2,#2b3e54)}
.an-legend .sw{width:11px;height:11px;border-radius:var(--sc-r-1,2px);flex:none}
.an-legend .lg-note{color:var(--ink-2,#2b3e54);opacity:.8}
/* legend swatches — same order as the JS PAL array (house data tokens) */
.an-sw-0{background:var(--sc-data-1,#2fb3ad)}
.an-sw-1{background:var(--sc-data-2,#3a6fb0)}
.an-sw-2{background:var(--sc-data-3,#b8732a)}
.an-sw-3{background:var(--sc-data-4,#5c3e8c)}
.an-sw-4{background:var(--sc-data-5,#0a8a5f)}
.an-sw-5{background:var(--sc-negative,#b5321e)}
.an-sw-6{background:var(--sc-teal-ink,#155752)}
.an-sw-7{background:var(--sc-navy,#0b2341)}
.an-scroll{overflow:auto}

/* ---- client-side empty state (ck_empty_state anatomy) ---- */
.an-es{padding:34px 22px;text-align:center}
.an-es .ic{width:44px;height:44px;border-radius:50%;
  background:var(--sc-bone,#ece5d6);display:inline-flex;align-items:center;
  justify-content:center;font-size:19px;color:var(--green-deep,#154e36);
  margin-bottom:10px}
.an-es .t{display:block;font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);
  font-size:17px;font-weight:600;color:var(--ink,#16263a);margin:0 0 6px}
.an-es .b{display:block;font-size:12.5px;color:var(--ink-2,#2b3e54);
  line-height:1.55;max-width:54ch;margin:0 auto}
.an-es .b em{color:var(--green-deep,#154e36);font-style:italic}
.an-es .b a{color:var(--green-deep,#154e36);font-weight:600}

/* ---- loading skeletons ---- */
@keyframes an-shimmer{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
.an-skel-tile,.an-skel-line,.an-skel-block{display:block;position:relative;
  overflow:hidden;border-radius:var(--an-r);
  background:color-mix(in srgb,var(--ink,#16263a) 6%,var(--paper-card,#fefcf3))}
.an-skel-tile::after,.an-skel-line::after,.an-skel-block::after{content:"";
  position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.5),transparent);
  animation:an-shimmer 1.2s infinite}
.an-skel-tile{min-height:74px}
.an-skel-line{height:13px;margin:9px 0}
.an-skel-block{height:180px;margin:8px 0}

/* ============================================================
   Pivot grid — the headline surface.
   Sticky header row + sticky row-label column, JetBrains Mono
   tabular-nums numerics, zebra, quantized heat-wash classes,
   emphasized grand-total row/column. Rule order matters:
   zebra < heat-wash < row hover < totals < heatmap-view heat.
   ============================================================ */
.an-ptbl-wrap{overflow:auto;border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:var(--an-r);max-height:62vh;background:var(--paper-card,#fefcf3);
  box-shadow:var(--an-shadow);margin-top:16px;-webkit-overflow-scrolling:touch}
table.an-ptbl{border-collapse:collapse;width:100%;
  font-variant-numeric:tabular-nums}
.an-ptbl th,.an-ptbl td{padding:7px 13px;text-align:right;white-space:nowrap;
  border-bottom:1px solid var(--rule-soft,#ddd1ac)}
.an-ptbl td{font-size:12px;color:var(--ink,#16263a);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
/* sticky header row */
.an-ptbl thead th{position:sticky;top:0;z-index:2;
  background:var(--paper-card,#fefcf3);color:var(--ink-2,#2b3e54);
  font-weight:600;font-size:10px;text-transform:uppercase;
  letter-spacing:.06em;padding-top:9px;padding-bottom:9px;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  border-bottom:1.5px solid var(--sc-rule-2,#bfb6a2)}
/* sticky row-label column — labels stay in the UI sans */
.an-ptbl th.k,.an-ptbl td.k{position:sticky;left:0;text-align:left;
  font-weight:600;color:var(--ink,#16263a);font-size:12.5px;
  font-family:var(--sc-sans,'Inter Tight',sans-serif);
  background:var(--paper-card,#fefcf3);
  border-right:1.5px solid var(--sc-rule,#d6cfc0);max-width:300px;
  overflow:hidden;text-overflow:ellipsis}
.an-ptbl thead th.k{z-index:3;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10px}
.an-ptbl tbody td.k{z-index:1}
/* zebra striping */
.an-ptbl tbody tr:nth-child(even) td{
  background:color-mix(in srgb,var(--sc-bone,#ece5d6) 55%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr:nth-child(even) td.k{
  background:color-mix(in srgb,var(--sc-bone,#ece5d6) 80%,var(--paper-card,#fefcf3))}
/* quantized heat-wash on value cells (replaces per-cell inline styles;
   sits above zebra, below row hover so hover reads through) */
.an-ptbl tbody tr td.an-hw-1{background:color-mix(in srgb,var(--green-deep,#154e36) 4%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-hw-2{background:color-mix(in srgb,var(--green-deep,#154e36) 7%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-hw-3{background:color-mix(in srgb,var(--green-deep,#154e36) 10%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-hw-4{background:color-mix(in srgb,var(--green-deep,#154e36) 13%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-hw-5{background:color-mix(in srgb,var(--green-deep,#154e36) 16%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-hw-6{background:color-mix(in srgb,var(--green-deep,#154e36) 20%,var(--paper-card,#fefcf3))}
/* row hover — declared after the wash so hovering reads through heat */
.an-ptbl tbody tr:hover td{
  background:color-mix(in srgb,var(--green-deep,#154e36) 8%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr:hover td.k{
  background:color-mix(in srgb,var(--green-deep,#154e36) 12%,var(--paper-card,#fefcf3))}
/* sortable headers — keyboard-focusable, aria-sort carried in markup */
.an-ptbl th.k{cursor:default}
.an-ptbl th.sortable{cursor:pointer;user-select:none;transition:color .12s}
.an-ptbl th.sortable:hover{color:var(--green-deep,#154e36)}
.an-ptbl th .arr{font-size:9px;margin-left:3px;color:var(--green-deep,#154e36)}
/* grand-total column */
.an-ptbl tbody tr td.tot{font-weight:700;color:var(--ink,#16263a);
  background:color-mix(in srgb,var(--green-deep,#154e36) 6%,var(--paper-card,#fefcf3));
  border-left:1px solid var(--rule-soft,#ddd1ac)}
.an-ptbl thead th.tot{color:var(--green-deep,#154e36);
  background:color-mix(in srgb,var(--green-deep,#154e36) 9%,var(--paper-card,#fefcf3))}
/* grand-total row — sticks to the bottom of the scroll box */
.an-ptbl tbody tr.tot td{position:sticky;bottom:0;z-index:2;font-weight:700;
  color:var(--ink,#16263a);border-bottom:none;
  border-top:1.5px solid var(--sc-rule-2,#bfb6a2);
  background:color-mix(in srgb,var(--green-deep,#154e36) 10%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr.tot td.k{z-index:3;
  background:color-mix(in srgb,var(--green-deep,#154e36) 13%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr.tot td.tot{
  background:color-mix(in srgb,var(--green-deep,#154e36) 15%,var(--paper-card,#fefcf3))}
/* heatmap-view cells — full green sequential ramp; declared after the
   hover rule so the heat stays legible while a row is hovered */
.an-ptbl td.hm{text-align:center;min-width:56px}
.an-ptbl tbody tr td.an-heat-0{background:var(--paper-card,#fefcf3)}
.an-ptbl tbody tr td.an-heat-1{background:color-mix(in srgb,var(--green-deep,#154e36) 10%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-heat-2{background:color-mix(in srgb,var(--green-deep,#154e36) 22%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-heat-3{background:color-mix(in srgb,var(--green-deep,#154e36) 38%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-heat-4{background:color-mix(in srgb,var(--green-deep,#154e36) 55%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-heat-5{background:color-mix(in srgb,var(--green-deep,#154e36) 72%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-heat-6{background:color-mix(in srgb,var(--green-deep,#154e36) 88%,var(--paper-card,#fefcf3))}
/* correlation-view cells — diverging ramp desaturated toward the house
   blue (--sc-data-2) and red (--sc-negative) endpoints */
.an-ptbl td.cm{text-align:center;min-width:52px}
.an-ptbl tbody tr td.an-cor-x{background:transparent}
.an-ptbl tbody tr td.an-cor-0{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 88%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-cor-1{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 55%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-cor-2{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 24%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-cor-3{background:var(--paper-card,#fefcf3)}
.an-ptbl tbody tr td.an-cor-4{background:color-mix(in srgb,var(--sc-negative,#b5321e) 24%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-cor-5{background:color-mix(in srgb,var(--sc-negative,#b5321e) 55%,var(--paper-card,#fefcf3))}
.an-ptbl tbody tr td.an-cor-6{background:color-mix(in srgb,var(--sc-negative,#b5321e) 88%,var(--paper-card,#fefcf3))}
/* the −1…+1 legend ramp reuses the same classes on bare swatch spans,
   which the td-scoped rules above cannot reach */
.an-legend .sw.an-cor-0{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 88%,var(--paper-card,#fefcf3))}
.an-legend .sw.an-cor-1{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 55%,var(--paper-card,#fefcf3))}
.an-legend .sw.an-cor-2{background:color-mix(in srgb,var(--sc-data-2,#3a6fb0) 24%,var(--paper-card,#fefcf3))}
.an-legend .sw.an-cor-3{background:var(--paper-card,#fefcf3);border:1px solid var(--sc-rule,#d6cfc0)}
.an-legend .sw.an-cor-4{background:color-mix(in srgb,var(--sc-negative,#b5321e) 24%,var(--paper-card,#fefcf3))}
.an-legend .sw.an-cor-5{background:color-mix(in srgb,var(--sc-negative,#b5321e) 55%,var(--paper-card,#fefcf3))}
.an-legend .sw.an-cor-6{background:color-mix(in srgb,var(--sc-negative,#b5321e) 88%,var(--paper-card,#fefcf3))}
/* strong heat / strong |r| cells flip to white text for contrast */
.an-ptbl tbody tr td.an-heat-4,.an-ptbl tbody tr td.an-heat-5,
.an-ptbl tbody tr td.an-heat-6,.an-ptbl tbody tr td.str{color:#fff}
/* under-table provenance note */
.an-tbl-note{margin-top:8px;font-size:10.5px;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  letter-spacing:.04em;font-variant-numeric:tabular-nums}

/* ---- filter value pickers ---- */
.an-flt{margin-top:8px}
.an-flt-lbl{display:block;font-size:10px;font-weight:600;
  letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);margin-bottom:4px}
.an-flt select{width:100%;font-size:12px;padding:4px;
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:var(--an-r);
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-flt select:focus{outline:none;border-color:var(--green-deep,#154e36);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--green-deep,#154e36) 15%,transparent)}
.an-flt-sub{display:flex;align-items:center;justify-content:space-between;
  gap:8px;margin-top:3px;font-size:10px;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums}
.an-flt-clear{appearance:none;border:0;background:transparent;padding:0;
  cursor:pointer;font-size:10px;font-weight:600;letter-spacing:.06em;
  text-transform:uppercase;color:var(--green-deep,#154e36);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-flt-clear:hover{text-decoration:underline}

/* ---- column profiler ---- */
.an-prof{border:1px solid var(--sc-rule,#d6cfc0);border-radius:var(--an-r);
  margin:4px 0 16px;overflow:auto;max-height:340px;box-shadow:var(--an-shadow);
  background:var(--paper-card,#fefcf3)}
.an-prof table{border-collapse:collapse;width:100%;font-size:12px}
.an-prof th,.an-prof td{padding:6px 11px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);
  text-align:left;white-space:nowrap;color:var(--ink,#16263a)}
.an-prof th{background:var(--paper-card,#fefcf3);position:sticky;top:0;
  z-index:1;font-weight:600;font-size:10px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--ink-2,#2b3e54);
  font-family:var(--sc-mono,'JetBrains Mono',monospace)}
.an-prof td.num{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums}
.an-prof tbody tr:nth-child(even) td{
  background:color-mix(in srgb,var(--sc-bone,#ece5d6) 45%,var(--paper-card,#fefcf3))}
.an-pbar{vertical-align:middle;margin-right:4px}
.an-cf-badge{color:var(--green-deep,#154e36);font-size:10px;margin-left:4px;
  font-weight:700;font-family:var(--sc-mono,'JetBrains Mono',monospace)}

/* ---- tooltip (ink-deep stays dark in both themes) ---- */
.an-tip{position:fixed;pointer-events:none;background:var(--ink-deep,#0e1a29);
  color:#fff;font-size:11.5px;padding:6px 9px;
  border-radius:var(--an-r);opacity:0;transition:opacity .1s;z-index:50;
  white-space:nowrap;font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums;box-shadow:var(--sc-shadow-2,0 6px 24px rgba(6,22,38,.08))}

/* ---- print: let the pivot expand, drop the interactive chrome ---- */
@media print{
  .an-ptbl-wrap{max-height:none;overflow:visible}
  .an-fields{position:static;max-height:none}
  .an-panel,.an-views,.an-note{display:none}
  .an-wrap svg{print-color-adjust:exact;-webkit-print-color-adjust:exact}
}
"""


def _body(job_id: str, available: bool, src_name: str) -> str:
    import html as _h
    cap_str = ck_fmt_number(_DATA_CAP)
    if not available:
        head = ck_editorial_head(
            # Eyebrow matches /npi-cleaner/history ("TOOLS · NPI CLAIMS
            # CLEANER") so the cleaner → pivot → history trio reads as
            # one tool family.
            eyebrow="TOOLS · NPI CLAIMS CLEANER",
            title="Pivot Workbench",
            meta="SESSION EXPIRED OR JOB NOT FOUND",
            lede_italic_phrase="This analysis session is gone",
            lede_body=(
                " — pivot sessions live in the in-memory job store, and the "
                "store resets whenever the server restarts."),
            # Masthead actions carry only page-specific quick links; the
            # standard action pills land at the page bottom, matching the
            # site-wide ck_page_actions placement.
            actions_html='<a href="/npi-cleaner">← Back to NPI Cleaner</a>',
            show_legend=False,
        )
        empty = ck_empty_state(
            "This analysis session has expired.",
            ("The cleaning job was not found — the in-memory job store "
             "resets when the server restarts. Re-run the cleaner and open "
             "the analysis again from the scorecard."),
            eyebrow="NPI CLEANER",
            icon="⟳",
            cta_label="Re-run the cleaner",
            cta_href="/npi-cleaner",
            tone="warning",
        )
        return (f"{head}\n{empty}\n"
                + ck_page_actions(glossary=False, methodology=False))

    safe_job = _h.escape(job_id)
    safe_name = _h.escape(src_name or "cleaned data")
    head = ck_editorial_head(
        # Eyebrow matches /npi-cleaner/history so the trio reads as one
        # tool family under the NPI Claims Cleaner umbrella.
        eyebrow="TOOLS · NPI CLAIMS CLEANER",
        title="Pivot Workbench",
        meta=f"IN-BROWSER PIVOT ENGINE · FIRST {cap_str} ROWS · CSV + PNG EXPORT",
        lede_italic_phrase="Slice the cleaned file",
        lede_body=(
            f" ({safe_name}) by rows, columns, values and filters. Every "
            "pivot, chart and CSV computes <em>in your browser</em> — "
            "nothing you build here is posted back to the server."),
        source_note=(
            f"In-browser aggregation over the cleaned output; the data feed "
            f"is capped at the first {cap_str} rows."),
        # Only the page-specific quick link lives in the masthead; the
        # standard ck_page_actions row lands at the page bottom like
        # every other editorial page (exports, source, diligence family).
        actions_html='<a href="/npi-cleaner">← Back to NPI Cleaner</a>',
        show_legend=False,
    )
    meta_prov = ck_provenance_tooltip(
        "In-browser pivot engine",
        f'<span class="an-meta" id="an-meta">Loading {safe_name}…</span>',
        explainer=(
            "Rows are fetched once from /npi-cleaner/data/<job> and "
            "aggregated in your browser. Pivots, charts and CSV downloads "
            f"never leave this machine. Feeds above {cap_str} rows are "
            "truncated — a warning badge appears when totals are partial."),
    )
    warn_badge = ck_signal_badge(
        f"COMPUTED ON FIRST {cap_str} ROWS", tone="warning")
    tiles_prov = ck_provenance_tooltip(
        "Headline measures",
        '<span class="an-tiles-cap">Headline measures</span>',
        explainer=(
            "Tiles are matched heuristically by column name (NPI, "
            "allowed/paid/charge amount, state, procedure code). Each tile "
            "names the source column it was computed from."),
        inject_css=False,
    )
    workspace_head = ck_section_header(
        "Pivot workspace", eyebrow="ROWS × COLUMNS × VALUES × FILTERS")
    return f"""
{head}
<div class="an-wrap" data-job="{safe_job}" data-src="{safe_name}">
  <p class="an-meta-row">
    {meta_prov}
    <span id="an-warn" hidden>{warn_badge}</span>
  </p>

  <p class="an-tiles-caprow">{tiles_prov}</p>
  <div class="an-tiles" id="an-tiles"><span class="an-skel-tile"></span><span
    class="an-skel-tile"></span><span class="an-skel-tile"></span><span
    class="an-skel-tile"></span></div>

  <div class="an-views" id="an-views">
    <span class="an-views-lbl">Quick views</span>
    <button class="an-btn vw" data-view="rows_by_billing">Claims by billing NPI</button>
    <button class="an-btn vw" data-view="amt_by_state">Allowed $ by state</button>
    <button class="an-btn vw" data-view="amt_by_hcpcs">Allowed $ by procedure</button>
    <button class="an-btn vw" data-view="count_by_payer">Claims by payer</button>
  </div>

  {workspace_head}
  <div class="an-grid">
    <aside class="an-fields" aria-label="Available fields">
      <h4>Fields</h4>
      <p class="an-fields-hint">R rows · C columns · V values · F filter</p>
      <div id="an-fieldlist"><span class="an-skel-line"></span><span
        class="an-skel-line"></span><span class="an-skel-line"></span><span
        class="an-skel-line"></span><span class="an-skel-line"></span></div>
    </aside>

    <div>
      <div class="an-zones">
        <div class="an-zone"><h5>Rows</h5><div id="zone-rows"></div></div>
        <div class="an-zone"><h5>Columns</h5><div id="zone-cols"></div></div>
        <div class="an-zone"><h5>Values</h5><div id="zone-vals"></div>
          <p class="an-agg">
            <select id="an-agg" aria-label="Aggregation">
              <option value="count">Count</option>
              <option value="sum">Sum</option>
              <option value="avg">Average</option>
              <option value="min">Min</option>
              <option value="max">Max</option>
            </select>
          </p>
        </div>
        <div class="an-zone"><h5>Filters</h5><div id="zone-filters"></div>
          <div id="an-filter-values"></div></div>
      </div>

      <section class="an-panel" aria-label="Pivot controls">
        <fieldset class="an-group">
          <legend class="an-group-lbl">Chart</legend>
          <label class="an-ctl">Type
            <select id="an-charttype">
              <option value="bar">Grouped bar</option>
              <option value="stacked">Stacked bar</option>
              <option value="line">Line</option>
              <option value="heatmap">Heatmap</option>
              <option value="scatter">Scatter</option>
              <option value="box">Box plot</option>
              <option value="histogram">Histogram</option>
              <option value="correlation">Correlation matrix</option>
            </select></label>
          <label class="an-ctl">Chart top
            <select id="an-topn">
              <option value="12">12 rows</option>
              <option value="20">20 rows</option>
              <option value="30">30 rows</option>
              <option value="0">All</option>
            </select></label>
          <label class="an-ctl"><input type="checkbox" id="an-pct"> % of total</label>
          <span class="an-scatter-ctl" id="an-scatter-ctl">
            <label class="an-ctl">X <select id="an-sx"></select></label>
            <label class="an-ctl">Y <select id="an-sy"></select></label>
            <label class="an-ctl">Color <select id="an-scolor"></select></label>
          </span>
        </fieldset>
        <fieldset class="an-group">
          <legend class="an-group-lbl">Actions</legend>
          <button class="an-btn" id="an-reset">Reset</button>
          <button class="an-btn" id="an-png">Export chart PNG</button>
          <button class="an-btn prim" id="an-dl">Download pivot CSV</button>
          <span class="an-note" id="an-note" role="status" hidden></span>
        </fieldset>
        <fieldset class="an-group">
          <legend class="an-group-lbl">Saved views</legend>
          <select id="an-views-sel" aria-label="Saved views"><option value="">—</option></select>
          <input id="an-view-name" type="text" placeholder="View name"
            aria-label="Name for the saved view">
          <button class="an-btn" id="an-save-view">Save current view</button>
          <button class="an-btn" id="an-del-view">Delete view</button>
        </fieldset>
        <fieldset class="an-group">
          <legend class="an-group-lbl">Derived field</legend>
          <select id="an-cf-a" aria-label="First operand"></select>
          <select id="an-cf-op" aria-label="Operator">
            <option value="div">÷</option><option value="sub">−</option>
            <option value="mul">×</option><option value="add">+</option></select>
          <select id="an-cf-b" aria-label="Second operand"></select>
          <input id="an-cf-name" type="text" placeholder="name (optional)"
            aria-label="New field name">
          <button class="an-btn" id="an-cf-add">Add field</button>
          <button class="an-btn" id="an-profile-toggle">Profile columns</button>
        </fieldset>
      </section>
      <div id="an-profile"></div>

      <figure class="an-chart" id="an-chart-box"><span class="an-skel-block"></span></figure>

      <div class="an-ptbl-wrap"><div id="an-ptbl"><span class="an-skel-block"></span></div></div>
      <p class="an-tbl-note" id="an-tbl-note"></p>
    </div>
  </div>
  <span class="an-tip" id="an-tip" aria-hidden="true"></span>
</div>
{ck_page_actions(glossary=False, methodology=False)}"""


_EXTRA_JS = r"""
(function(){
  var $=function(id){return document.getElementById(id);};
  // House dataviz palette — kit data tokens (CVD-separated), emitted as
  // var() so the theme layer can retint; the fallbacks keep exported PNGs
  // (where no page CSS applies) on the same canonical colors.
  var PAL=["var(--sc-data-1,#2fb3ad)","var(--sc-data-2,#3a6fb0)",
    "var(--sc-data-3,#b8732a)","var(--sc-data-4,#5c3e8c)",
    "var(--sc-data-5,#0a8a5f)","var(--sc-negative,#b5321e)",
    "var(--sc-teal-ink,#155752)","var(--sc-navy,#0b2341)"];
  var AXIS_TXT='font-size="10" font-family="var(--sc-mono,monospace)" fill="var(--ink-2,#2b3e54)" opacity="0.85"';
  var GRID='stroke="var(--sc-rule,#d6cfc0)" stroke-width="1" opacity="0.6"';
  var BASE='stroke="var(--sc-rule-2,#bfb6a2)" stroke-width="1"';
  var wrap=document.querySelector(".an-wrap"); if(!wrap) return;
  var job=wrap.getAttribute("data-job"); if(!job) return;
  var srcName=wrap.getAttribute("data-src")||"";

  var DATA={columns:[],rows:[]}, NUM={}, COMPUTED={}, state={rows:[],cols:[],val:null,filters:{},
    agg:"count",chart:"bar",topn:12,pct:false,sortCol:null,sortDir:-1,
    sx:null,sy:null,scolor:null};

  // Attribute-context-safe escape (quotes included — values land inside
  // data-tip="…" / aria-label="…" attributes as well as text nodes).
  function esc(s){ s=(s==null?"":String(s));
    return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
  function isNum(v){ if(v===""||v==null) return false; return !isNaN(parseFloat(v))&&isFinite(v.replace?v.replace(/[,$]/g,""):v); }
  function num(v){ var n=parseFloat(String(v).replace(/[,$]/g,"")); return isNaN(n)?0:n; }
  // House numeric discipline: 2dp on every magnitude bucket, thousands-
  // separated integers for counts, 2dp for fractional values.
  function fmtNum(n){ if(n==null||isNaN(n)) return ""; var a=Math.abs(n);
    if(a>=1e9)return (n/1e9).toFixed(2)+"B"; if(a>=1e6)return (n/1e6).toFixed(2)+"M";
    if(a>=1e3)return (n/1e3).toFixed(2)+"K";
    if(Number.isInteger(n))return n.toLocaleString();
    return n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}); }
  function srcBase(){ var b=srcName.replace(/\.[A-Za-z0-9]+$/,"")
    .replace(/[^A-Za-z0-9._-]+/g,"_").replace(/^_+|_+$/g,"");
    return b?b.slice(0,48):"pivot"; }
  // ck_empty_state anatomy, client-side (bone circle icon + serif title +
  // body). Call sites pass static copy only — never user data.
  function emptyState(icon,title,body){
    return '<div class="an-es"><span class="ic" aria-hidden="true">'+icon+
      '</span><span class="t">'+title+'</span><span class="b">'+body+'</span></div>'; }
  // Transient inline status line — replaces native alert()/prompt() chrome.
  function note(msg){ var n=$("an-note"); n.textContent=msg; n.hidden=false;
    clearTimeout(note._t); note._t=setTimeout(function(){ n.hidden=true; },5000); }

  fetch("/npi-cleaner/data/"+job).then(function(r){return r.json();}).then(function(j){
    if(j.error){ $("an-meta").textContent=j.error;
      $("an-tiles").innerHTML=""; $("an-fieldlist").innerHTML="";
      $("an-ptbl").innerHTML=emptyState("!","Could not load data",
        'The cleaned file for this job could not be fetched — the server may '+
        'have restarted. <a href="/npi-cleaner">Re-run the cleaner</a> and '+
        'open the analysis again.');
      $("an-chart-box").innerHTML=""; return; }
    DATA=j; detectNumeric();
    $("an-meta").textContent=(j.total_rows||j.rows.length).toLocaleString()+
      " rows × "+j.columns.length+" columns";
    if(j.truncated){ var w=$("an-warn"); w.hidden=false;
      var b=w.querySelector(".ck-badge");
      (b||w).textContent="COMPUTED ON FIRST "+j.rows.length.toLocaleString()+
        " OF "+(j.total_rows||0).toLocaleString()+" ROWS"; }
    // sensible defaults: first text col as Rows, count as value
    var firstText=j.columns.find(function(c,i){return !NUM[c];});
    if(firstText){ state.rows=[firstText]; }
    populateScatterSelects();
    renderStats(); renderFields(); renderZones(); recompute();
  }).catch(function(){ $("an-meta").textContent="Could not load data.";
    $("an-tiles").innerHTML=""; $("an-fieldlist").innerHTML="";
    $("an-ptbl").innerHTML=emptyState("!","Could not load data",
      'The data feed did not respond — the server may have restarted. '+
      '<a href="/npi-cleaner">Re-run the cleaner</a> and open the analysis again.');
    $("an-chart-box").innerHTML=""; });

  function colIdxByHint(hints){
    for(var h=0;h<hints.length;h++){
      for(var i=0;i<DATA.columns.length;i++){
        if(DATA.columns[i].toLowerCase().replace(/[^a-z0-9]/g,"").indexOf(hints[h])>=0)
          return i;
      }
    }
    return -1;
  }
  function distinctCount(ci){ if(ci<0)return null; var s={};
    for(var i=0;i<DATA.rows.length;i++){var v=DATA.rows[i][ci];if(v!=="")s[v]=1;} return Object.keys(s).length; }
  function sumCol(ci){ if(ci<0)return null; var t=0;
    for(var i=0;i<DATA.rows.length;i++){t+=num(DATA.rows[i][ci]);} return t; }

  function renderStats(){
    // [label, value, source-column sub-line] — the sub names exactly which
    // column each heuristic tile was computed from (provenance).
    var tiles=[["Rows",(DATA.total_rows||DATA.rows.length).toLocaleString(),
      DATA.truncated?("first "+DATA.rows.length.toLocaleString()+" loaded"):"all rows loaded"]];
    var bi=colIdxByHint(["billingnpi","billnpi","npi"]);
    if(bi>=0){ var dc=distinctCount(bi);
      if(dc!=null)tiles.push(["Distinct NPIs",dc.toLocaleString(),DATA.columns[bi]]); }
    var ai=colIdxByHint(["allowedamt","allowed","paidamt","chargeamt","billedamt"]);
    if(ai>=0){ var sm=sumCol(ai);
      if(sm!=null)tiles.push(["Total $ ("+DATA.columns[ai]+")","$"+fmtNum(sm),
        "sum of "+DATA.columns[ai]]); }
    var si=colIdxByHint(["providerstate","state"]);
    if(si>=0){ var sc=distinctCount(si);
      if(sc!=null)tiles.push(["States",sc.toLocaleString(),DATA.columns[si]]); }
    var hi=colIdxByHint(["hcpcs","cpt","proccode","procedurecode"]);
    if(hi>=0){ var hc=distinctCount(hi);
      if(hc!=null)tiles.push(["Procedures",hc.toLocaleString(),DATA.columns[hi]]); }
    $("an-tiles").innerHTML=tiles.map(function(t){
      return '<div class="an-tile"><span class="k">'+esc(t[0])+'</span>'+
        '<span class="v">'+esc(t[1])+'</span>'+
        (t[2]?'<span class="s">'+esc(t[2])+'</span>':'')+'</div>';
    }).join("");
  }

  function applyView(v){
    function pick(hints){ var i=colIdxByHint(hints); return i>=0?DATA.columns[i]:null; }
    state.rows=[]; state.cols=[]; state.val=null; state.filters={}; state.agg="count"; state.pct=false;
    if(v==="rows_by_billing"){ var n=pick(["billingnpi","npi","billingname","provider"]); if(n)state.rows=[n]; }
    else if(v==="amt_by_state"){ var s=pick(["providerstate","state"]); var a=pick(["allowedamt","allowed"]);
      if(s)state.rows=[s]; if(a){state.val=a;state.agg="sum";} }
    else if(v==="amt_by_hcpcs"){ var h=pick(["hcpcs","cpt","proccode"]); var a2=pick(["allowedamt","allowed"]);
      if(h)state.rows=[h]; if(a2){state.val=a2;state.agg="sum";} }
    else if(v==="count_by_payer"){ var p=pick(["payer","plan","insur"]); if(p)state.rows=[p]; }
    $("an-pct").checked=false; renderZones(); recompute();
  }

  function optList(list){ return list.map(function(c){return '<option value="'+esc(c)+'">'+esc(c)+'</option>';}).join(""); }
  function populateScatterSelects(){
    var nums=DATA.columns.filter(function(c){return NUM[c];});
    var cats=DATA.columns.filter(function(c){return !NUM[c];});
    $("an-sx").innerHTML=optList(nums); $("an-sy").innerHTML=optList(nums);
    $("an-scolor").innerHTML='<option value="">(none)</option>'+optList(cats);
    if(nums.length){ state.sx=nums[0]; state.sy=nums[Math.min(1,nums.length-1)];
      $("an-sx").value=state.sx; $("an-sy").value=state.sy; }
    $("an-cf-a").innerHTML=optList(nums); $("an-cf-b").innerHTML=optList(nums);
    loadViewsList();
  }

  // ---- Computed fields ----
  function addComputedField(){
    var a=$("an-cf-a").value, b=$("an-cf-b").value, op=$("an-cf-op").value;
    if(!a||!b) return;
    var sym={div:"÷",sub:"−",mul:"×",add:"+"}[op];
    var name=($("an-cf-name").value||"").trim()||((a+" "+sym+" "+b).slice(0,40));
    if(DATA.columns.indexOf(name)>=0) name=name+"_"+Date.now().toString().slice(-4);
    var ai=DATA.columns.indexOf(a), bi=DATA.columns.indexOf(b);
    DATA.columns.push(name);
    for(var i=0;i<DATA.rows.length;i++){ var x=num(DATA.rows[i][ai]), y=num(DATA.rows[i][bi]), v=0;
      if(op==="div")v=y?x/y:""; else if(op==="sub")v=x-y; else if(op==="mul")v=x*y; else v=x+y;
      DATA.rows[i].push(v===""?"":Math.round(v*10000)/10000); }
    NUM[name]=true; COMPUTED[name]=true;
    populateScatterSelects(); renderFields(); recompute();
    $("an-cf-name").value="";
  }

  // ---- Saved views (localStorage) ----
  var VKEY="npiPivotViews";
  function loadViews(){ try{ return JSON.parse(localStorage.getItem(VKEY)||"{}"); }catch(e){ return {}; } }
  function saveViews(v){ try{ localStorage.setItem(VKEY, JSON.stringify(v)); }catch(e){} }
  function loadViewsList(){ var v=loadViews();
    $("an-views-sel").innerHTML='<option value="">—</option>'+
      Object.keys(v).sort().map(function(n){return '<option value="'+esc(n)+'">'+esc(n)+'</option>';}).join(""); }
  function snapshotState(){ return {rows:state.rows,cols:state.cols,val:state.val,
    agg:state.agg,chart:state.chart,pct:state.pct,filters:state.filters,
    sx:state.sx,sy:state.sy,scolor:state.scolor}; }
  function restoreState(s){
    // Only restore fields that still exist in this dataset.
    function keep(arr){ return (arr||[]).filter(function(c){return DATA.columns.indexOf(c)>=0;}); }
    state.rows=keep(s.rows); state.cols=keep(s.cols);
    state.val=(s.val&&DATA.columns.indexOf(s.val)>=0)?s.val:null;
    state.agg=s.agg||"count"; state.chart=s.chart||"bar"; state.pct=!!s.pct;
    state.filters={}; Object.keys(s.filters||{}).forEach(function(f){ if(DATA.columns.indexOf(f)>=0)state.filters[f]=s.filters[f]; });
    state.sx=s.sx; state.sy=s.sy; state.scolor=s.scolor;
    $("an-agg").value=state.agg; $("an-charttype").value=state.chart; $("an-pct").checked=state.pct;
    renderZones(); recompute();
  }

  // ---- Column profiling ----
  function toggleProfile(){
    var box=$("an-profile");
    if(box.innerHTML){ box.innerHTML=""; return; }
    var h='<div class="an-prof"><table><thead><tr><th>Column</th><th>Type</th>'+
      '<th>Distinct</th><th>% filled</th><th>Min / Max / Mean · Top values</th></tr></thead><tbody>';
    DATA.columns.forEach(function(c,ci){
      var filled=0,distinct={},nums=[],counts={};
      for(var i=0;i<DATA.rows.length;i++){ var v=DATA.rows[i][ci];
        if(v!==""&&v!=null){ filled++; distinct[v]=1; counts[v]=(counts[v]||0)+1; if(NUM[c])nums.push(num(v)); } }
      var pct=DATA.rows.length?(filled/DATA.rows.length*100):0;
      var detail="";
      if(NUM[c]&&nums.length){ var mn=Math.min.apply(null,nums),mx=Math.max.apply(null,nums),
        mean=nums.reduce(function(a,b){return a+b;},0)/nums.length;
        detail=fmtNum(mn)+" / "+fmtNum(mx)+" / "+fmtNum(mean); }
      else { detail=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a];}).slice(0,3)
        .map(function(k){return esc(k||"(blank)")+" ("+counts[k]+")";}).join(", "); }
      var bw=Math.max(2,Math.round(pct*0.5));
      h+='<tr><td><b>'+esc(c)+'</b>'+(COMPUTED[c]?'<span class="an-cf-badge">ƒ</span>':'')+'</td>'+
        '<td>'+(NUM[c]?"numeric":"text")+'</td><td class="num">'+Object.keys(distinct).length.toLocaleString()+'</td>'+
        '<td class="num"><svg class="an-pbar" width="'+bw+'" height="6" aria-hidden="true">'+
        '<rect width="'+bw+'" height="6" rx="2" fill="var(--green-deep,#154e36)" opacity="0.8"/></svg> '+
        pct.toFixed(1)+'%</td>'+
        '<td class="num">'+detail+'</td></tr>';
    });
    h+='</tbody></table></div>'; box.innerHTML=h;
  }

  // ---- PNG export ----
  function exportPNG(){
    var svg=$("an-chart-box").querySelector("svg");
    if(!svg){ note("PNG export works for bar/line/scatter charts (the heatmap is a table)."); return; }
    var xml=new XMLSerializer().serializeToString(svg);
    var vb=svg.getAttribute("viewBox").split(" "), W=parseFloat(vb[2]), H=parseFloat(vb[3]);
    var scale=2, canvas=document.createElement("canvas"); canvas.width=W*scale; canvas.height=H*scale;
    var img=new Image();
    img.onload=function(){ var ctx=canvas.getContext("2d");
      ctx.fillStyle=getComputedStyle(document.body).backgroundColor||"#fff";
      ctx.fillRect(0,0,canvas.width,canvas.height); ctx.scale(scale,scale); ctx.drawImage(img,0,0);
      var a=document.createElement("a"); a.href=canvas.toDataURL("image/png");
      a.download=srcBase()+"_chart.png"; a.click(); };
    img.src="data:image/svg+xml;base64,"+btoa(unescape(encodeURIComponent(xml)));
  }

  function detectNumeric(){
    DATA.columns.forEach(function(c,ci){
      var n=0,tot=0;
      for(var i=0;i<Math.min(DATA.rows.length,200);i++){
        var v=DATA.rows[i][ci]; if(v==="")continue; tot++; if(isNum(v))n++;
      }
      NUM[c]= tot>0 && n/tot>0.8;
    });
  }

  function renderFields(){
    $("an-fieldlist").innerHTML=DATA.columns.map(function(c){
      return '<div class="an-field"><span class="fn">'+esc(c)+
        (NUM[c]?'<span class="num">#</span>':'')+'</span>'+
        '<span class="btns">'+
        '<button type="button" data-f="'+esc(c)+'" data-z="rows" title="Rows" aria-label="Add '+esc(c)+' to Rows">R</button>'+
        '<button type="button" data-f="'+esc(c)+'" data-z="cols" title="Columns" aria-label="Add '+esc(c)+' to Columns">C</button>'+
        '<button type="button" data-f="'+esc(c)+'" data-z="vals" title="Values" aria-label="Use '+esc(c)+' as Values">V</button>'+
        '<button type="button" data-f="'+esc(c)+'" data-z="filters" title="Filter" aria-label="Filter by '+esc(c)+'">F</button>'+
        '</span></div>';
    }).join("");
    $("an-fieldlist").querySelectorAll("button").forEach(function(b){
      b.addEventListener("click",function(){ assign(b.getAttribute("data-f"), b.getAttribute("data-z")); });
    });
  }

  function assign(field, zone){
    ["rows","cols","filters"].forEach(function(z){
      if(state[z].indexOf)state[z]=state[z].filter(function(x){return x!==field;});
    });
    if(state.val===field)state.val=null;
    delete state.filters[field];
    if(zone==="rows"){ if(state.rows.indexOf(field)<0)state.rows.push(field); }
    else if(zone==="cols"){ state.cols=[field]; }
    else if(zone==="vals"){ state.val=field; if(NUM[field]&&state.agg==="count")state.agg="sum"; }
    else if(zone==="filters"){ state.filters[field]=null; } // null=all
    renderZones(); recompute();
  }
  function unassign(field){
    state.rows=state.rows.filter(function(x){return x!==field;});
    state.cols=state.cols.filter(function(x){return x!==field;});
    if(state.val===field)state.val=null;
    delete state.filters[field];
    renderZones(); recompute();
  }

  function chip(f){ return '<span class="an-chip">'+esc(f)+
    '<button type="button" class="x" data-x="'+esc(f)+'" aria-label="Remove '+esc(f)+'">×</button></span>'; }
  function renderZones(){
    $("zone-rows").innerHTML=state.rows.map(chip).join("")||'<span class="an-hint">Assign a field with R</span>';
    $("zone-cols").innerHTML=state.cols.map(chip).join("")||'<span class="an-hint">Optional — assign with C</span>';
    $("zone-vals").innerHTML=state.val?chip(state.val):'<span class="an-hint">count of rows</span>';
    var fk=Object.keys(state.filters);
    $("zone-filters").innerHTML=fk.map(chip).join("")||'<span class="an-hint">Optional — assign with F</span>';
    $("an-agg").value=state.agg;
    document.querySelectorAll(".an-chip .x").forEach(function(x){
      x.addEventListener("click",function(){ unassign(x.getAttribute("data-x")); });
    });
    renderFilterValues();
  }

  function distinct(field){
    var ci=DATA.columns.indexOf(field), s={};
    for(var i=0;i<DATA.rows.length;i++){ s[DATA.rows[i][ci]]=1; }
    return Object.keys(s).sort();
  }
  // Selection-count sub-line ("3 of 47 selected · Clear") under each picker.
  function fltSub(f,shown){
    var nSel=state.filters[f]?state.filters[f].length:0;
    return '<span>'+(nSel?nSel+" of "+shown+" selected":"all "+shown+" shown")+'</span>'+
      (nSel?'<button type="button" class="an-flt-clear" data-clear="'+esc(f)+'">Clear</button>':'');
  }
  function renderFilterValues(){
    var fk=Object.keys(state.filters); var html="";
    fk.forEach(function(f,fi){
      var all=distinct(f), vals=all.slice(0,200);
      var capped=all.length>vals.length;
      html+='<div class="an-flt"><label class="an-flt-lbl" for="an-flt-'+fi+'">'+esc(f)+
        (capped?' · first 200 of '+all.length.toLocaleString():'')+'</label>'+
        '<select multiple size="4" id="an-flt-'+fi+'" data-filter="'+esc(f)+'">'+
        vals.map(function(v){var sel=(state.filters[f]&&state.filters[f].indexOf(v)>=0)?" selected":"";
          return '<option value="'+esc(v)+'"'+sel+'>'+esc(v||"(blank)")+'</option>';}).join("")+'</select>'+
        '<span class="an-flt-sub">'+fltSub(f,vals.length)+'</span></div>';
    });
    $("an-filter-values").innerHTML=html;
    $("an-filter-values").querySelectorAll("select").forEach(function(sel){
      sel.addEventListener("change",function(){
        var f=sel.getAttribute("data-filter");
        var chosen=Array.prototype.map.call(sel.selectedOptions,function(o){return o.value;});
        state.filters[f]=chosen.length?chosen:null; recompute();
        // Update the count line in place — a full re-render would drop
        // focus and scroll position mid-multi-select.
        var sub=sel.parentNode.querySelector(".an-flt-sub");
        if(sub)sub.innerHTML=fltSub(f,sel.options.length);
      });
    });
  }

  function passesFilters(row){
    for(var f in state.filters){ if(!state.filters[f])continue;
      var ci=DATA.columns.indexOf(f); if(state.filters[f].indexOf(row[ci])<0)return false; }
    return true;
  }

  var PIVOT=null;
  function recompute(){
    var rowIdx=state.rows.map(function(f){return DATA.columns.indexOf(f);});
    var colIdx=state.cols.length?DATA.columns.indexOf(state.cols[0]):-1;
    var valIdx=state.val?DATA.columns.indexOf(state.val):-1;
    var agg=state.agg;
    var cells={}, rowKeys={}, colKeys={};
    function aggInit(){return {n:0,sum:0,min:Infinity,max:-Infinity};}
    function aggAdd(a,v){ a.n++; if(valIdx>=0){var x=num(v); a.sum+=x; if(x<a.min)a.min=x; if(x>a.max)a.max=x;} }
    function aggVal(a){ if(!a)return null; if(agg==="count")return a.n;
      if(agg==="sum")return a.sum; if(agg==="avg")return a.n?a.sum/a.n:0;
      if(agg==="min")return a.min===Infinity?null:a.min; if(agg==="max")return a.max===-Infinity?null:a.max; return a.n; }
    for(var i=0;i<DATA.rows.length;i++){
      var row=DATA.rows[i]; if(!passesFilters(row))continue;
      var rk=rowIdx.length?rowIdx.map(function(ci){return row[ci];}).join(" ▸ "):"(all)";
      var ck=colIdx>=0?String(row[colIdx]):"__val";
      rowKeys[rk]=1; colKeys[ck]=1;
      var key=rk+"||"+ck; if(!cells[key])cells[key]=aggInit();
      aggAdd(cells[key], valIdx>=0?row[valIdx]:1);
    }
    var rKeys=Object.keys(rowKeys), cKeys=Object.keys(colKeys);
    // sort rows by their total desc
    function rowTotal(rk){var t=aggInit(); cKeys.forEach(function(ck){var a=cells[rk+"||"+ck];
      if(a){t.n+=a.n;t.sum+=a.sum;t.min=Math.min(t.min,a.min);t.max=Math.max(t.max,a.max);}}); return aggVal(t);}
    cKeys.sort();
    // Sort rows: by a clicked column, else by row total (desc).
    function cellVal(rk,ck){ return aggVal(cells[rk+"||"+ck])||0; }
    if(state.sortCol && state.sortCol!=="__total__" && cKeys.indexOf(state.sortCol)>=0){
      rKeys.sort(function(a,b){return (cellVal(a,state.sortCol)-cellVal(b,state.sortCol))*state.sortDir;});
    } else if(state.sortCol==="__row__"){
      rKeys.sort(function(a,b){return a<b?state.sortDir:(a>b?-state.sortDir:0);});
    } else {
      rKeys.sort(function(a,b){return ((rowTotal(b)||0)-(rowTotal(a)||0))* (state.sortDir<0?1:-1);});
    }
    var grand=0; rKeys.forEach(function(rk){grand+=(rowTotal(rk)||0);});
    PIVOT={rKeys:rKeys,cKeys:cKeys,cells:cells,aggVal:aggVal,rowTotal:rowTotal,
           singleCol:(colIdx<0),grand:grand,cellVal:cellVal};
    renderTable(); renderChart();
  }

  // Display transform: raw value, or % of grand total when the toggle is on.
  function disp(v){ if(v==null)return "";
    if(state.pct){ var g=(PIVOT&&PIVOT.grand)||0; return g?((v/g*100).toFixed(1)+"%"):"0%"; }
    return fmtNum(v); }

  // Honesty footer under the pivot: pivot row count, chart top-N scope,
  // and the server-side row cap when the feed was truncated.
  function updateTblNote(){
    var parts=[];
    if(PIVOT&&PIVOT.rKeys.length){
      parts.push(PIVOT.rKeys.length.toLocaleString()+" pivot row"+(PIVOT.rKeys.length===1?"":"s"));
      if(state.topn>0&&PIVOT.rKeys.length>state.topn)
        parts.push("chart shows top "+state.topn);
    }
    if(DATA.truncated)
      parts.push("computed on first "+DATA.rows.length.toLocaleString()+
        " of "+(DATA.total_rows||0).toLocaleString()+" source rows");
    $("an-tbl-note").textContent=parts.join(" · ");
  }

  function renderTable(){
    if(!PIVOT||!PIVOT.rKeys.length){
      $("an-ptbl").innerHTML=emptyState("▦","No rows match this pivot",
        'Add a field to Rows to build a pivot — try a <em>Quick view</em> '+
        'above, or clear a filter.');
      updateTblNote(); return; }
    var p=PIVOT, cols=p.cKeys, showTot=!p.singleCol;
    // Subtle value-heat: quantize body cells (positives only) into six
    // green-wash classes so magnitude is legible at a glance without a
    // separate heatmap view — and row hover still reads through.
    var heatMax=0;
    p.rKeys.forEach(function(rk){ cols.forEach(function(c){ var v=p.cellVal(rk,c); if(v>heatMax)heatMax=v; }); });
    function heat(v){ if(v==null||heatMax<=0)return ''; var t=v/heatMax;
      if(t<=0)return ''; var k=Math.min(6,Math.max(1,Math.ceil(t*6)));
      return ' class="an-hw-'+k+'"'; }
    function arr(key){ return state.sortCol===key?('<span class="arr">'+(state.sortDir<0?"▼":"▲")+'</span>'):''; }
    function ariaSort(key){
      var active=state.sortCol===key ||
        (key==="__default__"&&(state.sortCol==null||state.sortCol==="__default__"));
      if(!active)return "none";
      return state.sortDir<0?"descending":"ascending"; }
    var h='<table class="an-ptbl"><thead><tr>'+
      '<th class="k sortable" tabindex="0" data-sort="__row__" aria-sort="'+ariaSort("__row__")+'">'+
      esc(state.rows.join(" ▸ ")||"All")+arr("__row__")+'</th>';
    cols.forEach(function(c){ var lbl=p.singleCol?aggLabel():c;
      h+='<th class="sortable" tabindex="0" data-sort="'+esc(c)+'" aria-sort="'+ariaSort(c)+'">'+esc(lbl)+arr(c)+'</th>'; });
    if(showTot)h+='<th class="tot sortable" tabindex="0" data-sort="__default__" aria-sort="'+ariaSort("__default__")+'">Total'+
      (state.sortCol==null||state.sortCol==="__default__"?'<span class="arr">▼</span>':'')+'</th>';
    h+='</tr></thead><tbody>';
    var colTot={}; cols.forEach(function(c){colTot[c]=0;}); var grand=0;
    p.rKeys.forEach(function(rk){
      h+='<tr><td class="k">'+esc(rk)+'</td>';
      cols.forEach(function(c){ var v=p.aggVal(p.cells[rk+"||"+c]);
        colTot[c]+=(v||0); h+='<td'+heat(v)+'>'+disp(v)+'</td>'; });
      if(showTot){ var rt=p.rowTotal(rk); grand+=(rt||0); h+='<td class="tot">'+disp(rt)+'</td>'; }
      h+='</tr>';
    });
    h+='<tr class="tot"><td class="k">Total</td>';
    cols.forEach(function(c){ h+='<td>'+disp(colTot[c])+'</td>'; });
    if(showTot)h+='<td class="tot">'+disp(grand)+'</td>';
    h+='</tr></tbody></table>';
    $("an-ptbl").innerHTML=h;
    function doSort(th){ var key=th.getAttribute("data-sort");
      if(state.sortCol===key){ state.sortDir=-state.sortDir; } else { state.sortCol=key; state.sortDir=-1; }
      recompute(); }
    $("an-ptbl").querySelectorAll("th.sortable").forEach(function(th){
      th.addEventListener("click",function(){ doSort(th); });
      th.addEventListener("keydown",function(e){
        if(e.key==="Enter"||e.key===" "){ e.preventDefault(); doSort(th); } });
    });
    updateTblNote();
  }
  function aggLabel(){ return ({count:"Count",sum:"Sum",avg:"Average",min:"Min",max:"Max"})[state.agg]+
    (state.val?" of "+state.val:""); }

  // Palette accessor: the PAL entries are var() references, so the theme
  // layer (light or dark) resolves them; PNG export falls back to the
  // canonical token hex baked into each entry.
  function palette(){ return PAL; }

  function svgOpen(W,H,label){
    return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" preserveAspectRatio="xMidYMid meet" '+
      'role="img" aria-label="'+esc(label)+'" font-family="var(--sc-sans,sans-serif)">'; }
  function legendRow(inner){ return '<div class="an-legend">'+inner+'</div>'; }
  function scrollWrap(inner){ return '<div class="an-scroll">'+inner+'</div>'; }
  function axisText(x,y,anchor,txt,extra){
    return '<text x="'+x+'" y="'+y+'" text-anchor="'+anchor+'" '+AXIS_TXT+(extra||"")+'>'+txt+'</text>'; }
  function valLabel(x,y,txt,anchor){
    return '<text x="'+x+'" y="'+y+'" text-anchor="'+(anchor||"middle")+
      '" font-size="10" font-family="var(--sc-mono,monospace)" fill="var(--ink-2,#2b3e54)">'+txt+'</text>'; }

  function bindTips(box){
    var tip=$("an-tip");
    function show(el,x,y){ tip.textContent=el.getAttribute("data-tip");
      tip.style.left=x+"px"; tip.style.top=y+"px"; tip.style.opacity="1"; }
    function hide(){ tip.style.opacity="0"; }
    box.querySelectorAll("[data-tip]").forEach(function(el){
      el.addEventListener("mousemove",function(e){ show(el,e.clientX+12,e.clientY+12); });
      el.addEventListener("mouseleave",hide);
      // keyboard / AT parity — focusable tip targets announce on focus
      el.addEventListener("focus",function(){ var r=el.getBoundingClientRect();
        show(el,r.left,r.bottom+8); });
      el.addEventListener("blur",hide);
    });
  }

  function renderScatter(){
    var box=$("an-chart-box");
    var xi=DATA.columns.indexOf(state.sx||$("an-sx").value);
    var yi=DATA.columns.indexOf(state.sy||$("an-sy").value);
    var col=$("an-scolor").value, coli=col?DATA.columns.indexOf(col):-1;
    if(xi<0||yi<0){ box.innerHTML=emptyState("∷","No scatter yet",
      "Pick two numeric fields for X and Y in the Chart controls."); return; }
    var pts=[]; var cats={}, catList=[];
    for(var i=0;i<DATA.rows.length;i++){ var row=DATA.rows[i]; if(!passesFilters(row))continue;
      var x=num(row[xi]), y=num(row[yi]); var c=coli>=0?String(row[coli]):"";
      if(coli>=0 && !(c in cats)){ cats[c]=catList.length; catList.push(c); }
      pts.push([x,y,c]); }
    if(!pts.length){ box.innerHTML=emptyState("∷","No points to plot",
      "Every row is filtered out — clear a filter to bring points back."); return; }
    var xs=pts.map(function(p){return p[0];}), ys=pts.map(function(p){return p[1];});
    var xmin=Math.min.apply(null,xs), xmax=Math.max.apply(null,xs);
    var ymin=Math.min.apply(null,ys), ymax=Math.max.apply(null,ys);
    if(xmax===xmin)xmax=xmin+1; if(ymax===ymin)ymax=ymin+1;
    var pal=palette();
    var W=Math.max(560,box.clientWidth-4),H=360,L=56,R=16,T=16,B=40, iw=W-L-R, ih=H-T-B;
    function sx(v){return L+(v-xmin)/(xmax-xmin)*iw;} function sy(v){return T+ih-(v-ymin)/(ymax-ymin)*ih;}
    var title=esc(state.sy)+" vs "+esc(state.sx);
    var svg=svgOpen(W,H,state.sy+" versus "+state.sx+" scatter plot");
    for(var t=0;t<=4;t++){ var gy=T+ih-(t/4)*ih, gv=ymin+(ymax-ymin)*t/4;
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" '+GRID+'/>';
      svg+=axisText(L-6,gy+3,"end",fmtNum(gv)); }
    pts.slice(0,4000).forEach(function(pp){ var c=coli>=0?pal[cats[pp[2]]%pal.length]:pal[0];
      svg+='<circle cx="'+sx(pp[0]).toFixed(1)+'" cy="'+sy(pp[1]).toFixed(1)+'" r="3.2" fill="'+c+
        '" fill-opacity="0.6" data-tip="'+esc(state.sx+"="+fmtNum(pp[0])+", "+state.sy+"="+fmtNum(pp[1])+(pp[2]?" · "+pp[2]:""))+'"/>'; });
    svg+=axisText(L+iw/2,H-6,"middle",esc(state.sx));
    svg+='</svg>';
    var legend='';
    if(coli>=0 && catList.length>=2 && catList.length<=8){ legend=legendRow(catList.map(function(c,i){
      return '<span class="lg"><span class="sw an-sw-'+(i%pal.length)+'"></span>'+esc(c)+'</span>';}).join("")); }
    box.innerHTML='<h3 class="an-chart-title">'+title+
      ' ('+pts.length.toLocaleString()+' points)</h3>'+svg+legend;
    bindTips(box);
  }

  // Pearson r over complete observations (both values present & numeric).
  function pearson(xs, ys){
    var n=xs.length; if(n<3) return null;
    var sx=0, sy=0, i;
    for(i=0;i<n;i++){ sx+=xs[i]; sy+=ys[i]; }
    var mx=sx/n, my=sy/n, cov=0, dx=0, dy=0;
    for(i=0;i<n;i++){ var a=xs[i]-mx, b=ys[i]-my; cov+=a*b; dx+=a*a; dy+=b*b; }
    if(dx<=0||dy<=0) return null;   // a constant column has no correlation
    return cov/Math.sqrt(dx*dy);
  }

  function renderCorrelation(){
    var box=$("an-chart-box");
    var cols=DATA.columns.filter(function(c){return NUM[c];});
    var capped=cols.length>12; if(capped) cols=cols.slice(0,12);
    if(cols.length<2){ box.innerHTML=emptyState("◱","Not enough numeric fields",
      "A correlation matrix needs at least two numeric fields — add "+
      "measures or a derived field."); return; }
    var idx=cols.map(function(c){return DATA.columns.indexOf(c);});
    var rows=[];
    for(var i=0;i<DATA.rows.length;i++){ if(passesFilters(DATA.rows[i])) rows.push(DATA.rows[i]); }
    // Pairwise, using only rows where BOTH fields are present & numeric, so a
    // blank in one column never silently biases the coefficient toward zero.
    var R=[], N=[];
    for(var a=0;a<cols.length;a++){ R.push([]); N.push([]);
      for(var b=0;b<cols.length;b++){
        if(b<a){ R[a].push(R[b][a]); N[a].push(N[b][a]); continue; }  // symmetric
        var xs=[], ys=[];
        for(var r=0;r<rows.length;r++){ var va=rows[r][idx[a]], vb=rows[r][idx[b]];
          if(va===""||va==null||vb===""||vb==null||!isNum(va)||!isNum(vb)) continue;
          xs.push(num(va)); ys.push(num(vb)); }
        R[a].push(a===b?1:pearson(xs,ys)); N[a].push(xs.length);
      }
    }
    // Diverging ramp quantized into page-CSS classes: house blue
    // (--sc-data-2) = negative, house red (--sc-negative) = positive.
    function corClass(r){ if(r==null)return "an-cor-x";
      var t=(r+1)/2, k=Math.max(0,Math.min(6,Math.round(t*6))); return "an-cor-"+k; }
    var h='<h3 class="an-chart-title">Pearson correlation'+
      (capped?' (first 12 numeric fields)':'')+'</h3>';
    var tbl='<table class="an-ptbl"><thead><tr><th class="k"></th>';
    cols.forEach(function(c){ tbl+='<th>'+esc(c)+'</th>'; });
    tbl+='</tr></thead><tbody>';
    cols.forEach(function(c,a){ tbl+='<tr><td class="k">'+esc(c)+'</td>';
      cols.forEach(function(_,b){ var rr=R[a][b], nn=N[a][b];
        var strong=rr!=null&&Math.abs(rr)>0.55;
        tbl+='<td class="cm '+corClass(rr)+(strong?' str':'')+'" data-tip="'+
          esc(c+" × "+cols[b]+": r="+(rr==null?"n/a":rr.toFixed(2))+" (n="+nn.toLocaleString()+")")+'">'+
          (rr==null?"·":rr.toFixed(2))+'</td>'; });
      tbl+='</tr>'; });
    tbl+='</tbody></table>';
    h+=scrollWrap(tbl);
    var lg='−1';
    for(var k=0;k<7;k++){ lg+='<span class="sw an-cor-'+k+'"></span>'; }
    lg+='+1 &nbsp;<span class="lg-note">blue negative · red positive</span>';
    h+=legendRow(lg);
    box.innerHTML=h; bindTips(box);
  }

  // Linear-interpolation quantile (type-7, matches numpy's default) on a
  // pre-sorted ascending array.
  function quantile(s, q){
    var n=s.length; if(!n) return null; if(n===1) return s[0];
    var pos=(n-1)*q, base=Math.floor(pos), rest=pos-base;
    var lo=s[base], hi=(base+1<n)?s[base+1]:s[base];
    return lo+rest*(hi-lo);
  }

  function renderBoxplot(){
    var box=$("an-chart-box");
    var cat=state.rows[0];
    if(!cat){ box.innerHTML=emptyState("◫","No grouping yet",
      "Add a category field to Rows to group the box plot."); return; }
    // Measure = the Values field when numeric, else the first numeric column.
    var measure=(state.val&&NUM[state.val])?state.val:
      DATA.columns.filter(function(c){return NUM[c];})[0];
    if(!measure){ box.innerHTML=emptyState("◫","No numeric measure",
      "A box plot needs a numeric measure — assign one to Values with V."); return; }
    var ci=DATA.columns.indexOf(cat), mi=DATA.columns.indexOf(measure);
    var groups={}, order=[];
    for(var i=0;i<DATA.rows.length;i++){ var row=DATA.rows[i]; if(!passesFilters(row))continue;
      var mv=row[mi]; if(mv===""||mv==null||!isNum(mv))continue;
      var k=String(row[ci]===undefined||row[ci]===""?"(blank)":row[ci]);
      if(!(k in groups)){ groups[k]=[]; order.push(k); }
      groups[k].push(num(mv)); }
    if(!order.length){ box.innerHTML=emptyState("◫","No numeric values to plot",
      "Every row is blank or filtered out for this measure."); return; }
    order.sort(function(a,b){return groups[b].length-groups[a].length;});
    var capped=order.length>12; if(capped) order=order.slice(0,12);
    // Five-number summary + Tukey (1.5·IQR) fences per group.
    var stats=order.map(function(k){ var v=groups[k].slice().sort(function(a,b){return a-b;});
      var q1=quantile(v,0.25), med=quantile(v,0.5), q3=quantile(v,0.75), iqr=q3-q1;
      var loF=q1-1.5*iqr, hiF=q3+1.5*iqr;
      var inF=v.filter(function(x){return x>=loF&&x<=hiF;});
      return {k:k, n:v.length, min:v[0], max:v[v.length-1], q1:q1, med:med, q3:q3,
        wlo:inF.length?inF[0]:v[0], whi:inF.length?inF[inF.length-1]:v[v.length-1],
        out:v.filter(function(x){return x<loF||x>hiF;})}; });
    var ymin=Infinity, ymax=-Infinity;
    stats.forEach(function(s){ ymin=Math.min(ymin, s.wlo); ymax=Math.max(ymax, s.whi);
      s.out.forEach(function(o){ ymin=Math.min(ymin,o); ymax=Math.max(ymax,o); }); });
    if(ymin===ymax){ ymax=ymin+1; }
    var pal=palette();
    var W=Math.max(560, box.clientWidth-4), H=360, L=56, R=16, T=16, B=84, iw=W-L-R, ih=H-T-B;
    function sy(v){ return T+ih-(v-ymin)/(ymax-ymin)*ih; }
    var bw=iw/stats.length;
    var svg=svgOpen(W,H,measure+" distribution by "+cat+" box plot");
    for(var t=0;t<=4;t++){ var gv=ymin+(ymax-ymin)*t/4, gy=sy(gv);
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" '+GRID+'/>';
      svg+=axisText(L-6,gy+3,"end",fmtNum(gv)); }
    stats.forEach(function(s,gi){ var cx=L+(gi+0.5)*bw, half=Math.min(24, bw*0.28), c=pal[gi%pal.length];
      var tip=s.k+" · n="+s.n.toLocaleString()+" · min "+fmtNum(s.min)+" · Q1 "+fmtNum(s.q1)+
        " · med "+fmtNum(s.med)+" · Q3 "+fmtNum(s.q3)+" · max "+fmtNum(s.max);
      svg+='<line x1="'+cx+'" y1="'+sy(s.whi)+'" x2="'+cx+'" y2="'+sy(s.wlo)+'" stroke="'+c+'" stroke-width="1.5"/>';
      svg+='<line x1="'+(cx-half*0.6)+'" y1="'+sy(s.whi)+'" x2="'+(cx+half*0.6)+'" y2="'+sy(s.whi)+'" stroke="'+c+'" stroke-width="1.5"/>';
      svg+='<line x1="'+(cx-half*0.6)+'" y1="'+sy(s.wlo)+'" x2="'+(cx+half*0.6)+'" y2="'+sy(s.wlo)+'" stroke="'+c+'" stroke-width="1.5"/>';
      var yb=sy(s.q3), hh=Math.max(1, sy(s.q1)-sy(s.q3));
      svg+='<rect x="'+(cx-half)+'" y="'+yb+'" width="'+(2*half)+'" height="'+hh+'" fill="'+c+
        '" fill-opacity="0.28" stroke="'+c+'" stroke-width="1.5" data-tip="'+esc(tip)+'"/>';
      svg+='<line x1="'+(cx-half)+'" y1="'+sy(s.med)+'" x2="'+(cx+half)+'" y2="'+sy(s.med)+'" stroke="'+c+'" stroke-width="2.5"/>';
      s.out.slice(0,60).forEach(function(o){ svg+='<circle cx="'+cx+'" cy="'+sy(o).toFixed(1)+
        '" r="2.6" fill="none" stroke="'+c+'" stroke-width="1.2" data-tip="'+esc(s.k+" outlier: "+fmtNum(o))+'"/>'; });
      var lab=s.k.length>14?s.k.slice(0,13)+"…":s.k;
      svg+=axisText(cx,T+ih+14,"end",esc(lab),
        ' transform="rotate(-35 '+cx+' '+(T+ih+14)+')"');
    });
    svg+='<line x1="'+L+'" y1="'+(T+ih)+'" x2="'+(W-R)+'" y2="'+(T+ih)+'" '+BASE+'/>';
    svg+='</svg>';
    box.innerHTML='<h3 class="an-chart-title">'+esc(measure)+
      ' distribution by '+esc(cat)+(capped?' (top 12 groups by count)':'')+'</h3>'+svg;
    bindTips(box);
  }

  function renderHistogram(){
    var box=$("an-chart-box");
    // Measure = the Values field when numeric, else the first numeric column.
    var measure=(state.val&&NUM[state.val])?state.val:
      DATA.columns.filter(function(c){return NUM[c];})[0];
    if(!measure){ box.innerHTML=emptyState("▥","No numeric measure",
      "A histogram needs a numeric measure — assign one to Values with V."); return; }
    var mi=DATA.columns.indexOf(measure), vals=[];
    for(var i=0;i<DATA.rows.length;i++){ var row=DATA.rows[i]; if(!passesFilters(row))continue;
      var mv=row[mi]; if(mv===""||mv==null||!isNum(mv))continue; vals.push(num(mv)); }
    if(vals.length<2){ box.innerHTML=emptyState("▥","Not enough numeric values",
      "Fewer than two rows carry a numeric value here — clear a filter or "+
      "pick another measure."); return; }
    vals.sort(function(a,b){return a-b;});
    var n=vals.length, mn=vals[0], mx=vals[n-1];
    if(mx===mn){ box.innerHTML=emptyState("▥","Nothing to distribute",
      "All "+n.toLocaleString()+" values equal "+fmtNum(mn)+"."); return; }
    // Freedman–Diaconis bin width (robust to skew); Sturges fallback when IQR=0.
    var q1=quantile(vals,0.25), q3=quantile(vals,0.75), iqr=q3-q1, bins;
    if(iqr>0){ bins=Math.round((mx-mn)/(2*iqr/Math.pow(n,1/3))); }
    else { bins=Math.ceil(Math.log2(n))+1; }
    bins=Math.max(5, Math.min(60, bins||10));
    var width=(mx-mn)/bins, counts=new Array(bins).fill(0);
    for(i=0;i<n;i++){ var k=Math.floor((vals[i]-mn)/width); if(k>=bins)k=bins-1; if(k<0)k=0; counts[k]++; }
    var maxC=Math.max.apply(null,counts)||1, pal=palette();
    var W=Math.max(560,box.clientWidth-4),H=340,L=54,R=16,T=16,B=54,iw=W-L-R,ih=H-T-B;
    function sy(v){return T+ih-(v/maxC)*ih;}
    var bwid=iw/bins;
    var svg=svgOpen(W,H,"Distribution of "+measure+" histogram");
    for(var t=0;t<=4;t++){ var gv=maxC*t/4, gy=sy(gv);
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" '+GRID+'/>';
      svg+=axisText(L-6,gy+3,"end",fmtNum(gv)); }
    counts.forEach(function(c,bi){ var x0=L+bi*bwid, lo=mn+bi*width, hi=mn+(bi+1)*width, by=sy(c);
      svg+='<rect x="'+(x0+0.5)+'" y="'+by+'" width="'+Math.max(1,bwid-1)+'" height="'+Math.max(0,(T+ih)-by)+
        '" fill="'+pal[0]+'" fill-opacity="0.85" data-tip="'+
        esc("["+fmtNum(lo)+", "+fmtNum(hi)+"): "+c.toLocaleString()+(c===1?" row":" rows"))+'"/>'; });
    [0,0.5,1].forEach(function(f){ var xv=mn+(mx-mn)*f, xp=L+iw*f;
      svg+=axisText(xp,T+ih+16,(f===0?"start":f===1?"end":"middle"),fmtNum(xv)); });
    svg+='<line x1="'+L+'" y1="'+(T+ih)+'" x2="'+(W-R)+'" y2="'+(T+ih)+'" '+BASE+'/>';
    svg+='</svg>';
    box.innerHTML='<h3 class="an-chart-title">Distribution of '+
      esc(measure)+' ('+n.toLocaleString()+' rows · '+bins+' bins)</h3>'+svg;
    bindTips(box);
  }

  function renderHeatmap(){
    var box=$("an-chart-box"), p=PIVOT;
    var rKeys=p.rKeys.slice(0, state.topn>0?state.topn:p.rKeys.length);
    var cols=p.singleCol?[aggLabel()]:p.cKeys;
    var maxV=0,minV=Infinity;
    rKeys.forEach(function(rk){ (p.singleCol?["__val"]:p.cKeys).forEach(function(ck){
      var v=p.aggVal(p.cells[rk+"||"+ck]); if(v!=null){maxV=Math.max(maxV,v);minV=Math.min(minV,v);} }); });
    if(minV===Infinity)minV=0; maxV=maxV||1;
    // Sequential green ramp quantized into page-CSS classes mixed from
    // --green-deep (strong cells flip to white text via CSS).
    function heatClass(v){ if(v==null)return "an-heat-0";
      var t=(v-minV)/((maxV-minV)||1);
      return "an-heat-"+Math.max(0,Math.min(6,Math.round(t*6))); }
    var h='<h3 class="an-chart-title">'+esc(aggLabel())+' heatmap</h3>';
    var tbl='<table class="an-ptbl"><thead><tr><th class="k"></th>';
    cols.forEach(function(c){ tbl+='<th>'+esc(p.singleCol?"":c)+'</th>'; });
    tbl+='</tr></thead><tbody>';
    rKeys.forEach(function(rk){ tbl+='<tr><td class="k">'+esc(rk)+'</td>';
      (p.singleCol?["__val"]:p.cKeys).forEach(function(ck){ var v=p.aggVal(p.cells[rk+"||"+ck]);
        tbl+='<td class="hm '+heatClass(v)+'" data-tip="'+
          esc(rk+" · "+(p.singleCol?aggLabel():ck)+": "+fmtNum(v))+'">'+disp(v)+'</td>'; });
      tbl+='</tr>'; });
    tbl+='</tbody></table>';
    box.innerHTML=h+scrollWrap(tbl); bindTips(box);
  }

  function renderChart(){
    var box=$("an-chart-box");
    $("an-scatter-ctl").classList.toggle("on", state.chart==="scatter");
    if(state.chart==="scatter"){ return renderScatter(); }
    if(state.chart==="correlation"){ return renderCorrelation(); }
    if(state.chart==="box"){ return renderBoxplot(); }
    if(state.chart==="histogram"){ return renderHistogram(); }
    if(!PIVOT||!PIVOT.rKeys.length){ box.innerHTML=emptyState("▤","Nothing to chart yet",
      'Assign a field to Rows (press R next to a field) or pick a '+
      '<em>Quick view</em> above.'); return; }
    if(state.chart==="heatmap"){ return renderHeatmap(); }
    var p=PIVOT, topn=state.topn>0?state.topn:p.rKeys.length;
    var rKeys=p.rKeys.slice(0,topn);
    var series=p.singleCol?[aggLabel()]:p.cKeys;
    var valOf=function(rk,si){ var ck=p.singleCol?"__val":p.cKeys[si]; return p.aggVal(p.cells[rk+"||"+ck])||0; };
    var pal=palette();
    // T=26 leaves headroom for direct value labels above the tallest mark.
    var W=Math.max(560, box.clientWidth-4), H=340, L=54, R=16, T=26, B=84;
    var iw=W-L-R, ih=H-T-B;
    // Direct value labels when the mark count is small; tooltips carry the
    // dense case (docstring contract: labels on sparse charts).
    var marks=rKeys.length*series.length, labelOK=marks<=16;
    // scale
    var maxV=0;
    rKeys.forEach(function(rk,ri){ if(state.chart==="stacked"){ var s=0; series.forEach(function(_,si){s+=valOf(rk,si);}); maxV=Math.max(maxV,s);}
      else series.forEach(function(_,si){maxV=Math.max(maxV,valOf(rk,si));}); });
    maxV=maxV||1; var ticks=4;
    function sy(v){ return T+ih-(v/maxV)*ih; }
    var chartName=aggLabel()+
      (state.cols.length?" by "+(state.rows.join(", ")||"all")+" × "+state.cols[0]
        :" by "+(state.rows.join(", ")||"all"));
    var svg=svgOpen(W,H,chartName);
    // gridlines
    for(var t=0;t<=ticks;t++){ var gv=maxV*t/ticks, gy=sy(gv);
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" '+GRID+'/>';
      svg+=axisText(L-6,gy+3,"end",fmtNum(gv)); }
    var bw=iw/rKeys.length;
    rKeys.forEach(function(rk,ri){
      var x0=L+ri*bw;
      if(state.chart==="line"){ /* handled below */ }
      else if(state.chart==="stacked"){
        var acc=0;
        series.forEach(function(sname,si){ var v=valOf(rk,si); if(v<=0)return;
          var y1=sy(acc), y2=sy(acc+v); acc+=v;
          var bx=x0+bw*0.15, bwid=bw*0.7;
          svg+='<rect x="'+bx+'" y="'+y2+'" width="'+bwid+'" height="'+Math.max(0,y1-y2)+
            '" fill="'+pal[si%pal.length]+'" rx="2" data-tip="'+esc(rk+" · "+sname+": "+fmtNum(v))+'"/>';
        });
        if(rKeys.length<=16&&acc>0)
          svg+=valLabel(x0+bw/2,sy(acc)-5,fmtNum(acc));
      } else { // grouped
        var gw=bw*0.8/series.length;
        series.forEach(function(sname,si){ var v=valOf(rk,si);
          var bx=x0+bw*0.1+si*gw, by=sy(v);
          svg+='<rect x="'+bx+'" y="'+by+'" width="'+Math.max(1,gw-2)+'" height="'+Math.max(0,(T+ih)-by)+
            '" fill="'+pal[si%pal.length]+'" rx="2" data-tip="'+esc(rk+" · "+sname+": "+fmtNum(v))+'"/>';
          if(labelOK&&v>0)
            svg+=valLabel(bx+Math.max(1,gw-2)/2,by-4,fmtNum(v));
        });
      }
      // x label
      var lab=rk.length>14?rk.slice(0,13)+"…":rk;
      svg+=axisText(x0+bw/2,T+ih+14,"end",esc(lab),
        ' transform="rotate(-35 '+(x0+bw/2)+' '+(T+ih+14)+')"');
    });
    if(state.chart==="line"){
      series.forEach(function(sname,si){ var pts=[];
        rKeys.forEach(function(rk,ri){ var v=valOf(rk,si); pts.push([L+ri*bw+bw/2, sy(v)]); });
        var d=pts.map(function(pp,i){return (i?"L":"M")+pp[0]+" "+pp[1];}).join(" ");
        svg+='<path d="'+d+'" fill="none" stroke="'+pal[si%pal.length]+'" stroke-width="2"/>';
        pts.forEach(function(pp,ri){ svg+='<circle cx="'+pp[0]+'" cy="'+pp[1]+'" r="3.5" fill="'+
          pal[si%pal.length]+'" stroke="var(--paper-card,#fefcf3)" stroke-width="1.5" data-tip="'+
          esc(rKeys[ri]+" · "+sname+": "+fmtNum(valOf(rKeys[ri],si)))+'"/>';
          if(labelOK)
            svg+=valLabel(pp[0],pp[1]-8,fmtNum(valOf(rKeys[ri],si))); });
      });
    }
    // axis baseline
    svg+='<line x1="'+L+'" y1="'+(T+ih)+'" x2="'+(W-R)+'" y2="'+(T+ih)+'" '+BASE+'/>';
    svg+='</svg>';
    var legend='';
    if(series.length>=2){ legend=legendRow(series.map(function(s,si){
      return '<span class="lg"><span class="sw an-sw-'+(si%pal.length)+'"></span>'+esc(s)+'</span>'; }).join("")); }
    box.innerHTML='<h3 class="an-chart-title">'+esc(chartName)+'</h3>'+svg+legend;
    bindTips(box);
  }

  function pivotCSV(){
    if(!PIVOT)return "";
    var p=PIVOT, cols=p.cKeys, lines=[];
    var head=[state.rows.join(" > ")||"All"].concat(p.singleCol?[aggLabel()]:cols);
    if(!p.singleCol)head.push("Total");
    lines.push(head.map(csvCell).join(","));
    p.rKeys.forEach(function(rk){
      var line=[rk]; cols.forEach(function(c){var v=p.aggVal(p.cells[rk+"||"+c]); line.push(v==null?"":v);});
      if(!p.singleCol)line.push(p.rowTotal(rk));
      lines.push(line.map(csvCell).join(","));
    });
    return lines.join("\n");
  }
  function csvCell(v){ v=(v==null?"":String(v)); if(/[",\n]/.test(v))v='"'+v.replace(/"/g,'""')+'"'; return v; }

  $("an-agg").addEventListener("change",function(){ state.agg=$("an-agg").value; recompute(); });
  $("an-charttype").addEventListener("change",function(){ state.chart=$("an-charttype").value; renderChart(); });
  $("an-topn").addEventListener("change",function(){ state.topn=parseInt($("an-topn").value,10); renderChart(); updateTblNote(); });
  $("an-pct").addEventListener("change",function(){ state.pct=$("an-pct").checked; renderTable(); renderChart(); });
  ["an-sx","an-sy","an-scolor"].forEach(function(id){ $(id).addEventListener("change",function(){
    state.sx=$("an-sx").value; state.sy=$("an-sy").value; state.scolor=$("an-scolor").value; renderChart(); }); });
  document.querySelectorAll(".an-btn.vw").forEach(function(b){
    b.addEventListener("click",function(){ applyView(b.getAttribute("data-view")); }); });
  $("an-cf-add").addEventListener("click", addComputedField);
  $("an-profile-toggle").addEventListener("click", toggleProfile);
  $("an-png").addEventListener("click", exportPNG);
  $("an-save-view").addEventListener("click", function(){
    var inp=$("an-view-name"), name=(inp.value||"").trim();
    if(!name){ note("Name the view first, then Save."); inp.focus(); return; }
    var v=loadViews(); v[name]=snapshotState(); saveViews(v); loadViewsList();
    $("an-views-sel").value=name; inp.value="";
    note('Saved view "'+name+'".'); });
  $("an-view-name").addEventListener("keydown", function(e){
    if(e.key==="Enter"){ e.preventDefault(); $("an-save-view").click(); } });
  // Per-filter "Clear" affordance — delegated so in-place sub-line updates
  // never need re-binding.
  $("an-filter-values").addEventListener("click", function(e){
    var b=e.target.closest?e.target.closest(".an-flt-clear"):null; if(!b)return;
    state.filters[b.getAttribute("data-clear")]=null;
    recompute(); renderFilterValues(); });
  $("an-views-sel").addEventListener("change", function(){
    var v=loadViews(), n=$("an-views-sel").value; if(n&&v[n])restoreState(v[n]); });
  $("an-del-view").addEventListener("click", function(){
    var n=$("an-views-sel").value; if(!n)return; var v=loadViews(); delete v[n];
    saveViews(v); loadViewsList(); });
  $("an-reset").addEventListener("click",function(){ state.rows=[];state.cols=[];state.val=null;
    state.filters={};state.agg="count"; renderZones(); recompute(); });
  $("an-dl").addEventListener("click",function(){ var csv=pivotCSV();
    var a=document.createElement("a"); a.href="data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
    a.download=srcBase()+"_pivot.csv"; a.click(); });
  window.addEventListener("resize",function(){ if(PIVOT)renderChart(); });
})();
"""


def render_npi_analysis(job_id: str, *, available: bool = True,
                        src_name: str = "") -> str:
    return chartis_shell(
        _body(job_id, available, src_name),
        title="Claims Analysis — Pivot",
        active_nav="TOOLS",
        breadcrumbs=[("Tools", None), ("NPI Cleaner", "/npi-cleaner"),
                     ("Analysis", None)],
        extra_css=_EXTRA_CSS,
        extra_js=_EXTRA_JS,
    )
