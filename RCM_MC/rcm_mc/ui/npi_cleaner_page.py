"""NPI Claims Cleaner — the ``/npi-cleaner`` tool page.

A drag-and-drop utility that runs a claims file through the offline NPI
cleaner (``rcm_mc.npi_cleaner.engine``): validate every NPI against the Luhn
check, de-duplicate exact rows, trim whitespace, flag missing / malformed /
checksum-failing billing NPIs, and hand back a cleaned CSV plus a scorecard.

Rendered inside ``chartis_shell`` (TOOLS nav) so it lives natively in the PE
Desk app, and typeset in the v5 chartis editorial language: kit tokens with
canonical fallbacks (``--green-deep`` #154e36, ``--paper-card`` #fefcf3,
``--rule`` #c9bf9c), JetBrains Mono tabular numerics, one toned chip system,
``ck_*`` primitives for the static chrome and kit-classed markup
(``.ck-empty-state`` / ``.ck-prov-tt`` / ``.ck-help``) from the client-side
renderers. The upload → live-progress → download loop is pure client-side JS
talking to three sibling endpoints wired in ``server.py``:

    POST /npi-cleaner/upload            (raw body, X-Filename header)
    GET  /npi-cleaner/status/<job_id>   (JSON progress + scorecard)
    GET  /npi-cleaner/download/<job_id> (the cleaned CSV)

Exempt from the DealAnalysisPacket invariant for the same reason as
``/import`` and ``/methodology``: this is a stateless data-hygiene utility, not
analytical output about a specific deal. No DB, no network — the engine is
stdlib-only.
"""
from __future__ import annotations

import html as _html

from ._chartis_kit import (
    chartis_shell,
    ck_arrow_link,
    ck_editorial_head,
    ck_eyebrow,
    ck_fmt_number,
    ck_page_actions,
    ck_provenance_tooltip,
    ck_section_header,
    ck_signal_badge,
)
from ..npi_cleaner.rules import catalog as _rule_catalog


# Accepted upload formats — drives both the dropzone badge row and the
# masthead meta count, so the two can never drift apart.
_FORMATS = ("CSV", "TSV", ".xlsx", "837 / 835", ".edi", ".zip")


_EXTRA_CSS = r"""
/* Local shorthands for the kit type stacks (canonical tokens only). */
.npi-wrap{--mono:var(--sc-mono,'JetBrains Mono',monospace);
  --sans:var(--sc-sans,'Inter Tight',sans-serif);
  --serif:var(--sc-serif,'Source Serif 4',serif);
  max-width:1080px;margin:0 auto}
/* The pre-result journey stays narrow and focused; results run wide. */
#npi-stage-upload,#npi-stage-mapping,#npi-stage-progress,#npi-stage-error{
  max-width:880px;margin:0 auto}
.npi-setup{max-width:880px;margin:36px auto 0}
.npi-wrap .ck-section-header{margin:26px 0 10px}
.npi-muted{font-size:12.5px;color:var(--sc-text-dim,#465366);margin:10px 0;
  line-height:1.55}
.npi-fine{font-size:11px;color:var(--sc-text-dim,#465366)}
.npi-mt{margin-top:16px}
.npi-mt-sm{margin-top:10px}
.npi-hidden{display:none !important}
/* ============ Upload stage — the first impression ============ */
.npi-drop{
  position:relative;
  border:1.5px dashed var(--rule,#c9bf9c);border-radius:6px;
  background:
    radial-gradient(130% 150% at 50% 0%,
      color-mix(in srgb,var(--green-deep,#154e36) 4%,transparent), transparent 58%),
    var(--paper-card,#fefcf3);
  padding:42px 28px;text-align:center;cursor:pointer;
  transition:border-color .16s ease, background .16s ease,
    box-shadow .16s ease, transform .16s ease;
}
.npi-drop:hover,.npi-drop.drag{
  border-color:var(--green-deep,#154e36);
  background:
    radial-gradient(130% 150% at 50% 0%,
      color-mix(in srgb,var(--green-deep,#154e36) 9%,transparent), transparent 60%),
    var(--paper-card,#fefcf3);
  box-shadow:0 8px 26px -14px color-mix(in srgb,var(--green-deep,#154e36) 60%,transparent);
}
.npi-drop.drag{border-style:solid;transform:translateY(-1px)}
.npi-drop .cloud{
  width:58px;height:58px;margin:0 auto 15px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:29px;line-height:1;color:var(--green-deep,#154e36);
  background:color-mix(in srgb,var(--green-deep,#154e36) 11%,transparent);
  transition:transform .16s ease, background .16s ease;
}
.npi-drop:hover .cloud,.npi-drop.drag .cloud{
  transform:translateY(-2px);
  background:color-mix(in srgb,var(--green-deep,#154e36) 17%,transparent);
}
.npi-drop .big{font-family:var(--serif);font-size:19px;font-weight:600;
  letter-spacing:-.01em;color:var(--ink,#16263a)}
.npi-drop .small{font-size:12.5px;color:var(--sc-text-dim,#465366);margin-top:8px;
  line-height:1.6;max-width:400px;margin-left:auto;margin-right:auto}
.npi-drop .pick{color:var(--green-deep,#154e36);text-decoration:underline;
  text-underline-offset:2px;font-weight:600}
/* accepted-format badges + sample link, sat calmly below the drop zone */
.npi-formats{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;
  align-items:center;margin-top:14px;font-size:11.5px;color:var(--sc-text-dim,#465366)}
.npi-formats .ck-badge{font-family:var(--mono);font-size:10px;letter-spacing:.05em}
.npi-samplerow{text-align:center;margin-top:12px;font-size:12.5px;
  color:var(--sc-text-dim,#465366)}
.npi-samplerow a{color:var(--green-deep,#154e36);font-weight:600;
  text-decoration:underline;text-underline-offset:2px}
/* Options — grouped, legible, calm */
.npi-optbox{margin-top:18px;border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:6px 6px 8px}
.npi-optbox > .hd{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;
  padding:11px 12px 5px}
.npi-optbox > .hd .t{font-family:var(--mono);font-size:10px;font-weight:600;
  text-transform:uppercase;letter-spacing:.14em;color:var(--green-deep,#154e36)}
.npi-optbox > .hd .s{font-size:12px;color:var(--sc-text-dim,#465366)}
.npi-opts{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));
  gap:5px;margin:0;font-size:13px;color:var(--ink,#16263a)}
.npi-opts .npi-opt{display:flex;align-items:flex-start;gap:10px;
  padding:11px 12px;border-radius:var(--sc-r-2,4px);border:1px solid transparent;
  transition:background .14s ease, border-color .14s ease}
.npi-opts .npi-opt:hover{background:color-mix(in srgb,var(--green-deep,#154e36) 5%,transparent)}
.npi-opts .npi-opt input[type=checkbox]{margin-top:1px;flex:none;
  width:16px;height:16px;cursor:pointer;accent-color:var(--green-deep,#154e36)}
.npi-opts .npi-opt:has(input:checked){
  border-color:color-mix(in srgb,var(--green-deep,#154e36) 34%,transparent);
  background:color-mix(in srgb,var(--green-deep,#154e36) 6%,transparent)}
.npi-opt-t{display:block;font-weight:600;font-size:13px;color:var(--ink,#16263a);
  line-height:1.35}
.npi-opt-t label{cursor:pointer}
.npi-opt-d{display:block;font-size:11.5px;color:var(--sc-text-dim,#465366);
  margin-top:3px;line-height:1.5}
.npi-optprofile{display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  padding:12px;margin-top:3px;border-top:1px solid var(--rule-soft,#ddd1ac)}
.npi-optprofile > .lab{font-weight:600;font-size:13px;color:var(--ink,#16263a)}
/* ============ Inputs ============ */
.npi-input,.npi-select{font-family:var(--sans);font-size:12.5px;padding:5px 8px;
  border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-1,2px);
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a)}
.npi-select.xs{font-size:11px;padding:2px 4px}
.npi-input.grow{flex:1;min-width:220px}
.npi-prof-num{width:70px}
/* ============ Buttons — the sc-btn institutional skeleton ============ */
.npi-dl{display:inline-flex;align-items:center;gap:8px;
  padding:10px 18px;font-family:var(--sans);font-size:12px;font-weight:600;
  letter-spacing:.06em;text-transform:uppercase;cursor:pointer;
  border:1px solid var(--green-deep,#154e36);border-radius:var(--sc-r-1,2px);
  background:var(--green-deep,#154e36);color:#fff;text-decoration:none;
  transition:background .12s ease,color .12s ease,border-color .12s ease}
.npi-dl:hover{background:var(--green-2,#2d8964);border-color:var(--green-2,#2d8964);
  color:#fff}
.npi-dl-alt{background:transparent;color:var(--green-deep,#154e36)}
.npi-dl-alt:hover{background:var(--green-deep,#154e36);color:#fff;
  border-color:var(--green-deep,#154e36)}
.npi-dl.sm{padding:6px 12px;font-size:11px}
.npi-again{font-family:var(--sans);font-size:12.5px;font-weight:600;
  color:var(--green-deep,#154e36);cursor:pointer;background:none;border:0;
  padding:0;text-decoration:underline;text-underline-offset:3px}
.npi-again:hover{color:var(--green-2,#2d8964)}
/* ============ Chips — one toned system for the whole page ============
   Status/severity chips follow the kit's .ck-badge anatomy (outline in
   currentColor, 2px radius, uppercase) so cleaner chips read the same
   as the grade badges on /npi-cleaner/history and the status chips on
   the diligence family. Count badges (.npi-badge) stay quietly tinted —
   they are tallies, not statuses. */
.npi-chip,.npi-badge{display:inline-flex;align-items:center;gap:5px;
  font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.07em;
  text-transform:uppercase;padding:2px 8px;border-radius:var(--sc-r-1,2px);
  white-space:nowrap;color:var(--sc-text-dim,#465366)}
.npi-chip{border:1px solid currentColor}
.npi-badge{margin-left:6px;vertical-align:middle;
  color:var(--green-deep,#154e36);
  background:color-mix(in srgb,var(--green-deep,#154e36) 10%,transparent)}
.npi-chip.tone-positive{color:var(--sc-positive,#0a8a5f)}
.npi-chip.tone-warning{color:color-mix(in srgb,var(--sc-warning,#b8732a) 80%,var(--ink,#16263a))}
.npi-chip.tone-negative{color:var(--sc-negative,#b5321e)}
.npi-chip.tone-critical{color:var(--sc-critical,#8a1e0e)}
.npi-chip.tone-accent{color:var(--green-deep,#154e36)}
.npi-chip.dot::before{content:"";width:6px;height:6px;border-radius:50%;
  background:currentColor}
.npi-chip.dot.on{color:var(--green-deep,#154e36)}
.npi-chip.dot.off{color:var(--sc-text-dim,#465366)}
.npi-pill{display:inline-block;font-size:10px;font-family:var(--mono);
  padding:1px 6px;border-radius:var(--sc-r-1,2px);
  background:color-mix(in srgb,var(--ink,#16263a) 7%,transparent);
  color:var(--sc-text-dim,#465366);margin-right:6px}
.npi-pill.blk{margin:0 6px 6px 0}
/* ============ Processing stage — make progress feel alive ============ */
.npi-prog{margin-top:22px;border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:20px 22px}
.npi-prog-head{display:flex;align-items:center;gap:11px;margin-bottom:14px}
.npi-spin{width:20px;height:20px;flex:none;border-radius:50%;
  border:2.5px solid color-mix(in srgb,var(--green-deep,#154e36) 22%,transparent);
  border-top-color:var(--green-deep,#154e36);animation:npi-spin .8s linear infinite}
@keyframes npi-spin{to{transform:rotate(360deg)}}
.npi-prog-title{font-family:var(--serif);font-size:16px;font-weight:600;
  letter-spacing:-.01em;color:var(--ink,#16263a)}
.npi-bar{position:relative;height:10px;border-radius:var(--sc-r-1,2px);
  background:color-mix(in srgb,var(--ink,#16263a) 8%,transparent);overflow:hidden}
.npi-bar > i{position:relative;display:block;height:100%;width:0;
  background:linear-gradient(90deg,var(--green-2,#2d8964),var(--green-deep,#154e36));
  transition:width .3s ease;overflow:hidden}
.npi-bar > i::after{content:"";position:absolute;inset:0;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);
  transform:translateX(-100%);animation:npi-sheen 1.5s ease-in-out infinite}
@keyframes npi-sheen{to{transform:translateX(100%)}}
.npi-msg{font-size:12.5px;color:var(--sc-text-dim,#465366);margin-top:10px;
  font-family:var(--mono)}
.npi-prog-note{font-size:12px;color:var(--sc-text-dim,#465366);margin-top:13px;
  padding-top:12px;border-top:1px solid var(--rule-soft,#ddd1ac);line-height:1.55}
/* ============ Error stage — clear + recoverable, not alarming ============ */
.npi-errbox{display:flex;gap:14px;align-items:flex-start;margin-top:22px;
  border:1px solid color-mix(in srgb,var(--sc-warning,#b8732a) 30%,var(--rule,#c9bf9c));
  border-left:3px solid var(--sc-warning,#b8732a);border-radius:var(--sc-r-2,4px);
  background:color-mix(in srgb,var(--sc-warning,#b8732a) 5%,var(--paper-card,#fefcf3));
  padding:18px 20px}
.npi-erb-icon{width:34px;height:34px;flex:none;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:18px;
  font-weight:700;color:var(--sc-warning,#b8732a);
  background:color-mix(in srgb,var(--sc-warning,#b8732a) 14%,transparent)}
.npi-erb-body{flex:1;min-width:0}
.npi-erb-title{font-family:var(--serif);font-size:16px;font-weight:600;
  color:var(--ink,#16263a);letter-spacing:-.01em}
.npi-erb-detail{font-size:13px;color:var(--sc-text-dim,#465366);margin-top:5px;
  line-height:1.55;word-break:break-word}
.npi-erb-actions{display:flex;gap:14px;align-items:center;flex-wrap:wrap;
  margin-top:14px}
@media (prefers-reduced-motion:reduce){
  .npi-bar > i::after{animation:none;display:none}
  .npi-spin{animation:none}
}
/* ============ Results: scorecard tiles (kit stat-tile anatomy) ============ */
.npi-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));
  gap:10px;margin:20px 0}
.npi-cards.tight{margin:10px 0 4px}
.npi-card{position:relative;border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:13px 15px;transition:border-color .15s ease,box-shadow .15s ease}
.npi-card:hover{
  border-color:color-mix(in srgb,var(--green-deep,#154e36) 40%,var(--rule,#c9bf9c));
  box-shadow:0 1px 4px color-mix(in srgb,var(--green-deep,#154e36) 10%,transparent)}
.npi-card .k{font-family:var(--sans);font-size:10px;font-weight:600;
  text-transform:uppercase;letter-spacing:.08em;color:var(--sc-text-dim,#465366)}
.npi-card .v{font-family:var(--mono);font-size:22px;font-weight:600;
  letter-spacing:-.01em;margin-top:5px;font-variant-numeric:tabular-nums;
  color:var(--ink,#16263a)}
.npi-card .v.good{color:var(--green-deep,#154e36)}
.npi-card .v.warn{color:var(--sc-warning,#b8732a)}
.npi-card .v.bad{color:var(--sc-negative,#b5321e)}
.npi-card .tag{margin-top:7px}
/* ============ Results: tables (kit typography) ============ */
.npi-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.npi-scroll--tall{max-height:430px;overflow-y:auto}
.npi-scroll--tall .npi-tbl thead th{position:sticky;top:0;z-index:1;
  background:var(--bg,#efeadd)}
.npi-tbl{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
.npi-tbl th,.npi-tbl td{padding:8px 10px;text-align:left}
.npi-tbl th{font-family:var(--sans);font-size:10.5px;font-weight:600;
  text-transform:uppercase;letter-spacing:.07em;color:var(--sc-text-dim,#465366);
  border-bottom:1px solid var(--rule,#c9bf9c);white-space:nowrap}
.npi-tbl th .ck-prov-tt-card{text-transform:none;letter-spacing:normal;
  font-weight:400;white-space:normal}
.npi-tbl td{border-bottom:1px solid var(--rule-soft,#ddd1ac);vertical-align:top}
.npi-tbl th.num,.npi-tbl td.num{text-align:right;font-variant-numeric:tabular-nums}
.npi-tbl td.num{font-family:var(--mono);font-size:12.5px}
.npi-tbl td.num.good{color:var(--green-deep,#154e36)}
.npi-tbl td.num.warn{color:var(--sc-warning,#b8732a)}
.npi-tbl td.num.bad{color:var(--sc-negative,#b5321e)}
.npi-tbl tr td.billing{font-weight:600}
.npi-tbl td.npi-cell-sm{font-size:12px}
.npi-accepted{opacity:.55}
.npi-tbl tbody tr:not(.npi-drillrows):nth-child(even){
  background:color-mix(in srgb,var(--ink,#16263a) 2.5%,transparent)}
.npi-tbl tbody tr:not(.npi-drillrows):hover{
  background:color-mix(in srgb,var(--green-deep,#154e36) 6%,transparent)}
/* ============ Section headers emitted by the JS renderers ============ */
.npi-sec{display:block;margin:26px 0 2px}
.npi-sec .eb{display:block;font-family:var(--mono);font-size:10px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;color:var(--green-deep,#154e36);
  margin-bottom:3px}
.npi-sec h3{margin:0;font-family:var(--serif);font-size:17.5px;font-weight:600;
  color:var(--ink,#16263a);letter-spacing:-.01em;line-height:1.25}
.npi-sec .ct{font-family:var(--mono);font-size:12px;font-weight:500;
  color:var(--sc-text-faint,#7a8699);margin-left:8px}
/* ============ Notices ============ */
.npi-recovered{border:1px solid color-mix(in srgb,var(--sc-positive,#0a8a5f) 35%,transparent);
  background:color-mix(in srgb,var(--sc-positive,#0a8a5f) 7%,transparent);
  color:var(--green-deep,#154e36);border-radius:var(--sc-r-2,4px);
  padding:10px 14px;font-size:13px;margin-top:16px}
.npi-warn{border:1px solid color-mix(in srgb,var(--sc-warning,#b8732a) 38%,transparent);
  background:color-mix(in srgb,var(--sc-warning,#b8732a) 7%,transparent);
  color:color-mix(in srgb,var(--sc-warning,#b8732a) 72%,var(--ink,#16263a));
  border-radius:var(--sc-r-2,4px);padding:10px 14px;font-size:12.5px;margin-top:12px}
.npi-warn ul{margin:6px 0 0 18px;padding:0}
.npi-err{border:1px solid color-mix(in srgb,var(--sc-negative,#b5321e) 35%,transparent);
  background:color-mix(in srgb,var(--sc-negative,#b5321e) 6%,transparent);
  color:color-mix(in srgb,var(--sc-negative,#b5321e) 80%,var(--ink,#16263a));
  border-radius:var(--sc-r-2,4px);padding:12px 14px;font-size:13px;margin-top:16px}
.npi-sig{font-size:11.5px}
.npi-sig.bad{color:var(--sc-negative,#b5321e);font-weight:600}
.npi-sig.warn{color:var(--sc-warning,#b8732a)}
.npi-sig.ok{color:var(--green-deep,#154e36);font-weight:600}
/* ============ Issue flag rows ============ */
.npi-flag{display:flex;justify-content:space-between;gap:12px;align-items:baseline;
  padding:9px 12px;border:1px solid var(--rule-soft,#ddd1ac);
  border-radius:var(--sc-r-2,4px);margin-bottom:7px;
  background:var(--paper-card,#fefcf3)}
.npi-flag .lab{font-weight:600;font-size:13px}
.npi-flag .lab small{display:block;font-weight:400;
  color:var(--sc-text-dim,#465366);font-size:11.5px;margin-top:3px}
.npi-flag .cnt{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-weight:700;font-size:14px;white-space:nowrap}
.npi-flag .cnt.hit{color:var(--sc-negative,#b5321e)}
.npi-flag .cnt.clear{color:var(--green-deep,#154e36)}
.npi-wl{font-size:11.5px}
.npi-flag a,.npi-wl{color:var(--green-deep,#154e36);text-decoration:underline;
  text-underline-offset:2px}
.npi-subhd{font-weight:600;font-size:12.5px;margin-top:10px}
/* Section-lede note under a ck_section_header — same spec as the
   diligence checklist's .dc-section-note so section decks read alike. */
.npi-secnote{font-size:12.5px;color:var(--sc-text-dim,#465366);
  line-height:1.6;margin:2px 0 14px;max-width:72ch}
/* ============ Issues tab chrome ============ */
.npi-adv{margin-top:6px}
.npi-eng{font-size:11px;color:var(--sc-text-dim,#465366);font-family:var(--mono);
  letter-spacing:.03em;margin:2px 0 8px}
.npi-mono-note{font-size:12px;color:var(--sc-text-dim,#465366);margin:8px 0 10px;
  font-family:var(--mono)}
.npi-cand{border:1px solid var(--rule-soft,#ddd1ac);border-radius:var(--sc-r-2,4px);
  padding:9px 12px;margin-bottom:7px;background:var(--paper-card,#fefcf3);
  font-size:13px}
.npi-cand .q{font-weight:600}
.npi-cand .arrow{color:var(--sc-text-dim,#465366);margin:0 6px}
.npi-cand code{font-family:var(--mono);
  background:color-mix(in srgb,var(--green-deep,#154e36) 10%,transparent);
  padding:1px 6px;border-radius:var(--sc-r-1,2px);
  color:var(--green-deep,#154e36);font-weight:600}
.npi-cand .rowref{font-size:11px;color:var(--sc-text-dim,#465366)}
/* ============ Results tabs ============ */
.npi-tabs{display:flex;gap:2px;border-bottom:1px solid var(--rule,#c9bf9c);
  margin-bottom:20px;flex-wrap:wrap}
.npi-tab{appearance:none;background:none;border:0;
  border-bottom:2px solid transparent;padding:9px 14px;
  font-family:var(--sans);font-size:13px;font-weight:600;letter-spacing:.02em;
  color:var(--sc-text-dim,#465366);cursor:pointer;margin-bottom:-1px}
.npi-tab:hover{color:var(--ink,#16263a)}
.npi-tab.is-active{color:var(--green-deep,#154e36);
  border-bottom-color:var(--green-deep,#154e36)}
.npi-tab-badge{display:inline-block;min-width:18px;font-size:10.5px;
  text-align:center;font-family:var(--mono);font-variant-numeric:tabular-nums;
  padding:0 5px;border-radius:var(--sc-r-2,4px);
  background:color-mix(in srgb,var(--ink,#16263a) 7%,transparent);
  color:var(--sc-text-dim,#465366);margin-left:4px}
.npi-tab-badge:empty{display:none}
.npi-panel{display:none}
.npi-panel.is-active{display:block}
/* ============ Pivot-analysis bridge — the flagship next step ============ */
.npi-bridge{display:flex;align-items:center;justify-content:space-between;
  gap:18px;flex-wrap:wrap;border:1px solid var(--rule,#c9bf9c);
  border-left:3px solid var(--green-deep,#154e36);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:16px 20px;margin:0 0 24px}
.npi-bridge .eb{display:block;font-family:var(--mono);font-size:10px;
  font-weight:600;letter-spacing:.14em;text-transform:uppercase;
  color:var(--green-deep,#154e36);margin-bottom:4px}
.npi-bridge .t{font-family:var(--serif);font-size:19px;font-weight:600;
  color:var(--ink,#16263a);letter-spacing:-.01em;line-height:1.3}
.npi-bridge .d{font-size:12.5px;color:var(--sc-text-dim,#465366);margin:3px 0 0}
.npi-bridge-copy{flex:1;min-width:260px}
.npi-bridge .ck-eyebrow{font-size:10px;margin-bottom:4px;
  color:var(--green-deep,#154e36)}
.npi-setup > .ck-eyebrow{margin-bottom:2px}
.npi-bridge-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
/* ============ Connector cards / catalog / plan ============ */
.npi-conn{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  padding:14px 16px;margin-bottom:12px;background:var(--paper-card,#fefcf3)}
.npi-conn .top{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.npi-conn .nm{font-weight:600;font-size:14px}
.npi-conn .src{font-size:11px;color:var(--sc-text-dim,#465366);font-family:var(--mono)}
.npi-conn .cnt{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-weight:700;font-size:14px;color:var(--green-deep,#154e36);white-space:nowrap}
.npi-conn .cnt.bad{color:var(--sc-negative,#b5321e)}
.npi-conn .nt{font-size:12px;color:var(--sc-text-dim,#465366);margin-top:6px}
.npi-conn .nt.bad{color:var(--sc-negative,#b5321e)}
.npi-conn .nt.ok{color:var(--green-deep,#154e36)}
.npi-cat{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
  gap:8px;margin-top:10px}
.npi-cat .c{border:1px solid var(--rule-soft,#ddd1ac);
  border-radius:var(--sc-r-2,4px);padding:8px 11px;
  background:var(--paper-card,#fefcf3)}
.npi-cat .c.on{border-color:color-mix(in srgb,var(--green-deep,#154e36) 45%,transparent);
  background:color-mix(in srgb,var(--green-deep,#154e36) 5%,transparent)}
.npi-cat .c .n{font-size:12.5px;font-weight:600}
.npi-cat .c .o{font-size:11px;color:var(--sc-text-dim,#465366)}
.npi-cat .c .free{color:var(--green-deep,#154e36)}
.npi-plan{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  overflow:hidden;background:var(--paper-card,#fefcf3);margin-bottom:16px}
.npi-plan-head{display:flex;justify-content:space-between;align-items:baseline;
  gap:10px;flex-wrap:wrap;padding:13px 16px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac)}
.npi-plan-head .t{font-family:var(--serif);font-weight:600;font-size:15.5px}
.npi-plan-head .n{font-family:var(--mono);font-size:12px;
  color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums}
.npi-plan-head .n b{color:var(--green-deep,#154e36);font-weight:700}
.npi-plan-row{display:grid;grid-template-columns:minmax(130px,1.1fr) auto minmax(0,2fr);
  gap:12px;align-items:center;padding:10px 16px;
  border-top:1px solid var(--rule-soft,#ddd1ac)}
.npi-plan-row.idle{opacity:.62}
.npi-plan-row .nm{font-size:13px;font-weight:600}
.npi-plan-row .rs{font-size:12px;color:var(--sc-text-dim,#465366);line-height:1.45}
.npi-plan-row .npi-chip{justify-self:start}
@media (max-width:560px){
  .npi-plan-row{grid-template-columns:1fr;gap:5px}
}
/* ============ Column-mapping stage ============ */
.npi-map{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  gap:10px 16px;margin-top:6px}
.npi-map .row{display:flex;flex-direction:column;gap:3px}
.npi-map label{font-size:12px;font-weight:600;color:var(--ink,#16263a)}
.npi-map select{padding:7px 9px;border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);font-size:13px;
  background:var(--paper-card,#fefcf3);color:var(--ink,#16263a)}
.npi-map select.auto{color:var(--sc-text-dim,#465366)}
.npi-map .row.set label{color:var(--green-deep,#154e36)}
.npi-maptools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:10px 0 4px}
.npi-maptools .npi-muted{margin:0}
.npi-mapactions{margin-top:18px;display:flex;gap:14px;align-items:center}
/* ============ Issue drill-down rows ============ */
.npi-drill{cursor:pointer}
.npi-drill:hover{background:color-mix(in srgb,var(--green-deep,#154e36) 4%,transparent)}
.npi-drill td:first-child::before{content:"▸ ";color:var(--sc-text-dim,#465366);
  font-size:11px}
.npi-drill.open td:first-child::before{content:"▾ "}
.npi-drillrows{background:var(--paper-hi,#fbf6e8)}
.npi-drillrows table{width:100%;border-collapse:collapse;font-size:12px;margin:4px 0}
.npi-drillrows th,.npi-drillrows td{padding:5px 8px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);text-align:left}
.npi-drillrows th{font-size:10px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--sc-text-dim,#465366)}
/* ============ Quality: grade block + dimension bars ============ */
.npi-grade{display:inline-flex;align-items:center;gap:16px;margin-top:14px;
  border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  padding:14px 22px;background:var(--paper-card,#fefcf3)}
.npi-grade .letter{font-family:var(--serif);font-size:38px;font-weight:700;
  line-height:1;letter-spacing:-.02em}
.npi-grade .meta{font-family:var(--sans);font-size:10.5px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--sc-text-dim,#465366);line-height:1.5}
.npi-grade .meta b{display:block;font-family:var(--mono);font-size:20px;
  font-weight:700;letter-spacing:-.01em;text-transform:none;
  font-variant-numeric:tabular-nums}
.npi-grade .good,.npi-dim .dv.good{color:var(--green-deep,#154e36)}
.npi-grade .warn,.npi-dim .dv.warn{color:var(--sc-warning,#b8732a)}
.npi-grade .bad,.npi-dim .dv.bad{color:var(--sc-negative,#b5321e)}
.npi-dims{max-width:680px;margin-top:14px}
.npi-dim{display:flex;align-items:center;gap:12px;margin:8px 0;flex-wrap:wrap}
.npi-dim .dl{width:130px;font-size:12.5px;font-weight:600}
.npi-dim .dtrack{flex:1;min-width:120px;height:9px;
  border-radius:var(--sc-r-1,2px);overflow:hidden;
  background:color-mix(in srgb,var(--ink,#16263a) 8%,transparent)}
.npi-dim .dtrack > i{display:block;height:100%;width:0}
.npi-dim .dv{width:56px;text-align:right;font-family:var(--mono);font-size:12px;
  font-weight:600;font-variant-numeric:tabular-nums}
.npi-dim .dd{flex:1;min-width:170px;font-size:11.5px;color:var(--sc-text-dim,#465366)}
.npi-dim i.good,.npi-hbar i.good{background:var(--green-deep,#154e36)}
.npi-dim i.warn,.npi-hbar i.warn{background:var(--sc-warning,#b8732a)}
.npi-dim i.bad,.npi-hbar i.bad{background:var(--sc-negative,#b5321e)}
/* inline per-column health bar (Overview) */
.npi-hbar{display:inline-flex;align-items:center;gap:8px;justify-content:flex-end}
.npi-hbar .track{width:56px;height:6px;border-radius:var(--sc-r-1,2px);flex:none;
  overflow:hidden;background:color-mix(in srgb,var(--ink,#16263a) 9%,transparent)}
.npi-hbar .track > i{display:block;height:100%;width:0}
.npi-hbar .pct{min-width:48px;text-align:right;font-variant-numeric:tabular-nums;
  font-family:var(--mono);font-size:12px;font-weight:600}
.npi-hbar .pct.good{color:var(--green-deep,#154e36)}
.npi-hbar .pct.warn{color:var(--sc-warning,#b8732a)}
.npi-hbar .pct.bad{color:var(--sc-negative,#b5321e)}
/* ============ Volume-integrity month bars ============ */
.npi-vbar{display:flex;align-items:flex-end;gap:3px;height:84px;margin-top:10px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac)}
.npi-vbar > i{flex:1;display:block;background:var(--green-deep,#154e36);
  opacity:.7;min-height:2px;height:2px}
.npi-vbar > i.peak{opacity:1}
.npi-vbar-cap{display:flex;justify-content:space-between;gap:10px;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--sc-text-dim,#465366);margin-top:5px}
.npi-vbar-cap .pk{color:var(--green-deep,#154e36);font-weight:600}
/* ============ Downloads: grouped action bars ============ */
.npi-dlgroup{border:1px solid var(--rule-soft,#ddd1ac);
  border-radius:var(--sc-r-2,4px);padding:16px 18px;margin-top:14px;
  background:var(--paper-card,#fefcf3)}
.npi-dlgroup > .lbl{font-family:var(--mono);font-size:10px;
  text-transform:uppercase;letter-spacing:.14em;
  color:var(--green-deep,#154e36);font-weight:600;margin-bottom:12px}
.npi-dlbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.npi-recform{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px}
.npi-recform .npi-muted{margin:0}
/* ============ Setup band (profiles / wishlist / reference packs) ============ */
.npi-box{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  background:var(--paper-card,#fefcf3);padding:18px 20px;margin-top:16px}
.npi-box .ck-section-header{margin:0 0 6px}
.npi-box .ck-section-header h2{font-size:19px}
.npi-profbox{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  background:var(--paper-card,#fefcf3);padding:16px;margin-top:10px}
.npi-profbox .hd{font-family:var(--serif);font-size:15px;font-weight:600;
  margin-bottom:8px}
.npi-prof-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.npi-prof-row .npi-muted{margin:0}
#npi-prof-rules{max-height:260px;overflow:auto;margin-top:6px;font-size:12px;
  columns:2;column-gap:24px}
#npi-prof-rules .r{break-inside:avoid;margin-bottom:3px}
.npi-prof-actions{margin-top:10px;display:flex;gap:14px;align-items:center;
  flex-wrap:wrap}
.npi-wishform{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
#npi-wish-details{width:100%;margin-top:8px;box-sizing:border-box}
.npi-wish-hd{font-size:12.5px;font-weight:600;margin:10px 0 2px}
.npi-wish-row{font-size:12.5px;padding:4px 0;
  border-top:1px solid var(--rule-soft,#ddd1ac)}
.npi-wish-row .npi-muted{margin:0;display:inline}
/* ============ Compact kit empty states inside panels ============ */
.npi-empty{padding:28px 24px;margin:16px auto}
.npi-empty .ck-empty-state-title{font-size:18px}
/* ============ Methodology footnote ============ */
.npi-note{max-width:880px;margin:30px auto 0;font-size:12px;
  color:var(--sc-text-dim,#465366);border-top:1px solid var(--rule-soft,#ddd1ac);
  padding-top:16px;line-height:1.65}
.npi-note code{font-family:var(--mono);font-size:11px}
/* ============ Shared focus ring ============ */
.npi-drop:focus-visible,.npi-tab:focus-visible,.npi-dl:focus-visible,
.npi-again:focus-visible,.npi-drill:focus-visible,.npi-input:focus-visible,
.npi-select:focus-visible,.npi-map select:focus-visible,
.npi-opt input:focus-visible{
  outline:2px solid var(--green-deep,#154e36);outline-offset:2px}
"""


def _help(label: str, text: str) -> str:
    """Kit ``.ck-help`` popover with a keyboard-focusable ``?`` trigger.

    Replaces the old title-attribute-only ``ⓘ`` hints, which were
    invisible to keyboard and touch users. Uses the shell's existing
    ``.ck-help`` CSS (focus-within + hover reveal) so no page JS is
    needed. Emits only the trigger + popover (no inline term) because
    the option label already carries the term text.
    """
    return (
        '<span class="ck-help">'
        '<button type="button" class="ck-help-trigger" '
        f'aria-label="About: {_html.escape(label)}" '
        'aria-expanded="false" tabindex="0">?</button>'
        '<span class="ck-help-popover" role="tooltip">'
        f'<span class="ck-help-term">{_html.escape(label)}</span>'
        f'<span class="ck-help-def">{_html.escape(text)}</span>'
        '</span>'
        '</span>'
    )


def _body() -> str:
    cat = _rule_catalog()
    n_flags = sum(1 for r in cat if r.get("kind") == "flag")
    n_repairs = sum(1 for r in cat if r.get("kind") == "repair")
    head = ck_editorial_head(
        # Consistency sweep: /npi-cleaner/analyze and /npi-cleaner/history
        # both carry "TOOLS · NPI CLAIMS CLEANER", so the hub page carries
        # the identical eyebrow and the cleaner → pivot → history trio
        # reads as one tool family (the eyebrow repeating the H1 tool name
        # follows the exports-page idiom).
        eyebrow="TOOLS · NPI CLAIMS CLEANER",
        title="NPI Claims Cleaner",
        meta=(f"OFFLINE ENGINE · {ck_fmt_number(n_flags)} SCREENS · "
              f"{ck_fmt_number(n_repairs)} REPAIRS · "
              f"{ck_fmt_number(len(_FORMATS))} FORMATS · NO PHI STORED"),
        lede_italic_phrase="Drop a claims file",
        lede_body=(
            " and get it back cleaned: every NPI checked against the official "
            "Luhn checksum, exact-duplicate rows removed, whitespace trimmed, "
            "and every missing or malformed billing-provider NPI flagged. "
            "Processed in memory — nothing is stored, and nothing leaves the "
            "server unless you opt into the live NPPES cross-check."),
        source_note=(
            "Deterministic v49 cleaning engine validated against CMS "
            "reference tables."),
        show_legend=False,
    )
    format_badges = "".join(ck_signal_badge(f) for f in _FORMATS)
    hint_online = _help(
        "Go online",
        "Uses PE Desk's own live public-data connectors. NPIs are verified "
        "against NPPES (active vs deactivated) and missing NPIs recovered "
        "from provider names; NDC and drug-name columns are resolved to "
        "RxNorm concepts and openFDA labels. Bounded, cached, opt-in.")
    hint_deep = _help(
        "Deep recovery",
        "Runs the complete Steps 0-8 recovery pipeline: live NPPES "
        "enrichment, CMS billers, Open Payments, 340B, entity resolution "
        "and statistical fill, then a multi-tab Excel report. Needs "
        "outbound network access and can take minutes; runs in the "
        "background with a timeout and never blocks the fast results.")
    hint_deid = _help(
        "De-identify patient PHI",
        "Masks patient-scoped identifiers only — patient name/address/"
        "phone/email and SSN are redacted, DOB is reduced to year, ZIP to "
        "its first three digits, and MRN/account numbers are replaced with "
        "a stable per-run token (same value → same token, so rows still "
        "link). Provider NPI and provider name are always kept intact — "
        "NPI recovery depends on them.")
    hint_profile = _help(
        "Cleaning profiles",
        "Named rule suites: disable rules that don't apply to this feed, "
        "mark known issues as accepted (still reported, no longer graded), "
        "and tune thresholds (timely-filing days, stale-date horizon, "
        "outlier fence). Stored on the server; pick one per upload.")
    mapping_head = ck_section_header(
        "Confirm columns", eyebrow="UPLOAD · STEP 2 OF 2")
    colhealth_head = ck_section_header(
        "Per-column NPI health", eyebrow="RESULTS · COLUMN SCAN")
    prov_valid = ck_provenance_tooltip(
        "Valid NPI", "Valid",
        explainer=("Exactly 10 digits and passing the Luhn check over the "
                   "constant prefix 80840 plus the first nine digits — the "
                   "same rule CMS/NPPES uses."))
    prov_checksum = ck_provenance_tooltip(
        "Checksum fail", "Checksum&nbsp;fail",
        explainer=("10 digits, but the final check digit disagrees with "
                   "the 80840 Luhn checksum — usually one mistyped digit."),
        inject_css=False)
    prov_health = ck_provenance_tooltip(
        "Column health", "Health",
        explainer=("Valid NPIs as a share of the column's filled cells. "
                   "Green at 99%+, amber at 90-99%, red below 90%."),
        inject_css=False)
    prov_blank = ck_provenance_tooltip(
        "Blank", "Blank",
        explainer=("Missing entirely — including cells that only held a "
                   "null token (NA / N/A / NULL) before normalization."),
        inject_css=False)
    prov_malformed = ck_provenance_tooltip(
        "Malformed", "Malformed",
        explainer=("Present but not 10 digits after trimming — truncated "
                   "IDs, embedded text, or Excel float mangling."),
        inject_css=False)
    method_link = ck_arrow_link("How these are computed", "#npi-method")
    # Section head, not ck_section_intro: a mid-body ck-section-intro
    # makes chartis_shell auto-prepend a second ck_page_title H1 above
    # the page's own ck_editorial_head H1 (the shell's missing-title
    # heuristic keys on the intro class), stacking two "NPI Claims
    # Cleaner" mastheads. The header + note pair also matches every
    # other section head on this page (Confirm columns, Feature
    # requests, Reference data packs).
    pop_intro = (
        ck_section_header(
            "What the file means, not just whether it's clean.",
            eyebrow="POPULATION · OFFLINE MARTS")
        + '<p class="npi-secnote">'
          "Where care happened, how lines group into visits, what "
          "conditions the population carries, whether any month of data "
          "is missing, and who codes hotter than the file. Computed "
          "offline from the cleaned table — the class of output "
          "Tuva-style pipelines need a warehouse for.</p>")
    wishlist_head = ck_section_header(
        "Missing something? Tell us and we'll build it.",
        eyebrow="FEEDBACK · BUILD BACKLOG")
    refdata_head = ck_section_header(
        "Reference data packs — pull the real code sets",
        eyebrow="REFERENCE DATA · AUTHORITATIVE SETS")
    history_link = ck_arrow_link("Run history", "/npi-cleaner/history")
    bridge_eyebrow = ck_eyebrow("NEXT STEP · ANALYSIS")
    setup_eyebrow = ck_eyebrow("CLEANER SETUP & FEEDBACK")
    catalog_link = ck_arrow_link("Browse the full data catalog",
                                 "/data/catalog")
    return f"""
{head}
<div class="npi-wrap">

  <div id="npi-stage-upload">
    <div class="npi-drop" id="npi-drop" tabindex="0" role="button"
         aria-label="Upload a claims file">
      <div class="cloud" aria-hidden="true">⤒</div>
      <div class="big">Drop a claims file to clean it</div>
      <div class="small">Drag it here, or <span class="pick">choose a file</span>.
        Processed in memory — nothing is stored.</div>
      <div class="npi-formats">
        {format_badges}
        <span>CSV/TSV to <strong>10&nbsp;GB</strong> · others to 200&nbsp;MB</span>
      </div>
    </div>
    <p class="npi-samplerow">New here?
      <a href="/npi-cleaner/sample" download>Try a sample file</a> —
      no upload needed.</p>
    <input type="file" id="npi-file" class="npi-hidden"
           accept=".csv,.tsv,.txt,.xlsx,.837,.835,.edi,.x12,.zip,text/csv,text/plain,application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
    <div class="npi-optbox">
      <div class="hd"><span class="t">Options</span>
        <span class="s">Sensible defaults — adjust before you upload.</span></div>
      <div class="npi-opts">
        <div class="npi-opt"><input type="checkbox" id="npi-dedupe" checked>
          <span class="npi-opt-body">
            <span class="npi-opt-t"><label for="npi-dedupe">Remove
              exact-duplicate rows</label></span>
            <span class="npi-opt-d">Drop byte-identical duplicate rows; every
              other row is preserved as-is.</span></span></div>
        <div class="npi-opt"><input type="checkbox" id="npi-enrich">
          <span class="npi-opt-body">
            <span class="npi-opt-t"><label for="npi-enrich">Go online —
              verify &amp; recover NPIs</label> {hint_online}</span>
            <span class="npi-opt-d">Cross-check against NPPES, recover missing
              billing NPIs, resolve drugs (RxNorm · openFDA).</span></span></div>
        <div class="npi-opt"><input type="checkbox" id="npi-deep">
          <span class="npi-opt-body">
            <span class="npi-opt-t"><label for="npi-deep">Deep recovery —
              full v49 pipeline</label> {hint_deep}</span>
            <span class="npi-opt-d">Networked Steps&nbsp;0–8 recovery; runs in
              the background and never blocks the fast results.</span></span></div>
        <div class="npi-opt"><input type="checkbox" id="npi-deid">
          <span class="npi-opt-body">
            <span class="npi-opt-t"><label for="npi-deid">De-identify patient
              PHI</label> {hint_deid}</span>
            <span class="npi-opt-d">Mask patient identifiers in the export;
              provider NPI &amp; name are kept intact.</span></span></div>
      </div>
      <div class="npi-optprofile">
        <label class="lab" for="npi-profile">Cleaning profile</label>
        <select id="npi-profile" class="npi-select">
          <option value="">(default rules)</option>
        </select>
        <button type="button" class="npi-again" id="npi-profile-new">Manage
          profiles…</button>
        {hint_profile}
      </div>
    </div>
    <div id="npi-profile-editor" class="npi-hidden npi-profbox">
      <div class="hd">Cleaning profiles</div>
      <div class="npi-prof-row">
        <input id="npi-prof-name" class="npi-input" placeholder="Profile name"
               aria-label="Profile name">
        <label class="npi-muted">timely-filing days
          <input id="npi-prof-timely" class="npi-input npi-prof-num"
                 type="number" value="365" min="30" max="1095"></label>
        <label class="npi-muted">stale after (years)
          <input id="npi-prof-stale" class="npi-input npi-prof-num"
                 type="number" value="10" min="1" max="50"></label>
        <label class="npi-muted">outlier fence (×IQR)
          <input id="npi-prof-iqr" class="npi-input npi-prof-num"
                 type="number" value="3" min="1.5" max="10" step="0.5"></label>
        <label class="npi-muted">dup window (days)
          <input id="npi-prof-dupwin" class="npi-input npi-prof-num"
                 type="number" value="3" min="1" max="30"></label>
      </div>
      <p class="npi-muted">Per rule: leave <em>on</em>, mark <em>accepted</em>
        (reported, not graded), or <em>off</em> (not checked at all).</p>
      <div id="npi-prof-rules"></div>
      <div class="npi-prof-actions">
        <button type="button" class="npi-dl sm" id="npi-prof-save">Save
          profile</button>
        <button type="button" class="npi-again" id="npi-prof-close">Close</button>
        <a class="npi-again" href="/npi-cleaner/api/profiles/export" download>
          Export all</a>
        <button type="button" class="npi-again" id="npi-prof-import">
          Import…</button>
        <input type="file" id="npi-prof-import-file" class="npi-hidden"
               accept=".json,application/json">
      </div>
      <p class="npi-muted" id="npi-prof-msg" aria-live="polite"></p>
    </div>
  </div>

  <div id="npi-stage-mapping" class="npi-hidden">
    {mapping_head}
    <p class="npi-muted" id="npi-map-file"></p>
    <div class="npi-maptools">
      <label class="npi-muted" for="npi-map-tpl">Mapping template:</label>
      <select id="npi-map-tpl" class="npi-select">
        <option value="">(none)</option></select>
      <input id="npi-map-tpl-name" class="npi-input"
        placeholder="Save as… e.g. Epic extract" aria-label="Template name">
      <button type="button" class="npi-again" id="npi-map-tpl-save">Save
        template</button>
      <span class="npi-muted" id="npi-map-tpl-msg" aria-live="polite"></span>
    </div>
    <div class="npi-map" id="npi-map-grid"></div>
    <div class="npi-mapactions">
      <button class="npi-dl" id="npi-map-clean">Clean file →</button>
      <button class="npi-again" id="npi-map-cancel">Cancel</button>
    </div>
  </div>

  <div id="npi-stage-progress" class="npi-hidden">
    <div class="npi-prog">
      <div class="npi-prog-head">
        <span class="npi-spin" aria-hidden="true"></span>
        <span class="npi-prog-title">Cleaning your file…</span>
      </div>
      <div class="npi-bar" id="npi-bar" role="progressbar" aria-valuemin="0"
           aria-valuemax="100" aria-valuenow="0"
           aria-label="Cleaning progress"><i id="npi-bar-fill"></i></div>
      <div class="npi-msg" id="npi-bar-msg" aria-live="polite">Uploading…</div>
      <div class="npi-msg npi-muted" id="npi-bar-eta"></div>
      <p class="npi-prog-note">The job runs on the server, so you can keep
        working — leave this tab open to watch progress. Large files can take a
        while; the bar and estimate update live.</p>
      <button type="button" class="npi-again npi-hidden npi-mt-sm"
              id="npi-cancel">Cancel this run</button>
    </div>
  </div>

  <div id="npi-stage-error" class="npi-hidden">
    <div class="npi-errbox">
      <div class="npi-erb-icon" aria-hidden="true">!</div>
      <div class="npi-erb-body">
        <div class="npi-erb-title">This file couldn't be cleaned</div>
        <div class="npi-erb-detail" id="npi-err-text"></div>
        <div class="npi-erb-actions">
          <button class="npi-dl" id="npi-err-again">Try another file</button>
          <a class="npi-again" href="/npi-cleaner/sample" download>or start
            with a sample</a>
        </div>
      </div>
    </div>
  </div>

  <div id="npi-stage-result" class="npi-hidden">
    <div class="npi-tabs" role="tablist" aria-label="Cleaning results">
      <button class="npi-tab is-active" id="npi-tab-overview" role="tab"
        aria-selected="true" aria-controls="npi-panel-overview"
        data-tab="overview">Overview</button>
      <button class="npi-tab" id="npi-tab-quality" role="tab" tabindex="-1"
        aria-selected="false" aria-controls="npi-panel-quality"
        data-tab="quality">Quality
        <span class="npi-tab-badge" id="tabbadge-quality"></span></button>
      <button class="npi-tab" id="npi-tab-issues" role="tab" tabindex="-1"
        aria-selected="false" aria-controls="npi-panel-issues"
        data-tab="issues">Issues &amp; fixes
        <span class="npi-tab-badge" id="tabbadge-issues"></span></button>
      <button class="npi-tab" id="npi-tab-population" role="tab" tabindex="-1"
        aria-selected="false" aria-controls="npi-panel-population"
        data-tab="population">Population
        <span class="npi-tab-badge" id="tabbadge-pop"></span></button>
      <button class="npi-tab" id="npi-tab-connectors" role="tab" tabindex="-1"
        aria-selected="false" aria-controls="npi-panel-connectors"
        data-tab="connectors">Live connectors
        <span class="npi-tab-badge" id="tabbadge-conn"></span></button>
      <button class="npi-tab" id="npi-tab-downloads" role="tab" tabindex="-1"
        aria-selected="false" aria-controls="npi-panel-downloads"
        data-tab="downloads">Downloads</button>
    </div>

    <section class="npi-bridge">
      <div class="npi-bridge-copy">
        {bridge_eyebrow}
        <div class="t">Slice this cleaned file by payer, provider and month.</div>
        <p class="d">Pivot analysis on the cleaned table, a print-ready DQ
          one-pager, and quality tracked across runs.</p>
      </div>
      <div class="npi-bridge-actions">
        <a class="npi-dl" id="npi-analyze" href="#">Open pivot analysis ↗</a>
        <a class="npi-dl npi-dl-alt" id="npi-exec" href="#" target="_blank">
          Executive report</a>
        {history_link}
      </div>
    </section>

    <section class="npi-panel is-active" data-panel="overview"
         id="npi-panel-overview" role="tabpanel"
         aria-labelledby="npi-tab-overview">
      <div class="npi-cards" id="npi-cards"></div>
      <div id="npi-warnings"></div>
      {colhealth_head}
      <div class="npi-scroll">
      <table class="npi-tbl">
        <thead><tr>
          <th scope="col">Column</th><th class="num" scope="col">Cells</th>
          <th class="num" scope="col">{prov_valid}</th>
          <th class="num" scope="col">{prov_blank}</th>
          <th class="num" scope="col">{prov_malformed}</th>
          <th class="num" scope="col">{prov_checksum}</th>
          <th class="num" scope="col">{prov_health}</th>
        </tr></thead>
        <tbody id="npi-col-rows"></tbody>
      </table>
      </div>
      <p class="npi-mt-sm">{method_link}</p>
      <div id="npi-repairs"></div>
      <div id="npi-sanity"></div>
    </section>

    <section class="npi-panel" data-panel="quality" id="npi-panel-quality"
         role="tabpanel" aria-labelledby="npi-tab-quality">
      <div id="npi-quality"></div>
    </section>

    <section class="npi-panel" data-panel="issues" id="npi-panel-issues"
         role="tabpanel" aria-labelledby="npi-tab-issues">
      <div id="npi-advanced"></div>
      <div id="npi-suggestions"></div>
    </section>

    <section class="npi-panel" data-panel="population" id="npi-panel-population"
         role="tabpanel" aria-labelledby="npi-tab-population">
      {pop_intro}
      <div id="npi-pop"></div>
    </section>

    <section class="npi-panel" data-panel="connectors" id="npi-panel-connectors"
         role="tabpanel" aria-labelledby="npi-tab-connectors">
      <div id="npi-conn-plan"></div>
      <div id="npi-deep-out"></div>
      <div id="npi-compliance"></div>
      <div id="npi-order-referring"></div>
      <div id="npi-nppes"></div>
      <div id="npi-connectors"></div>
      <div id="npi-catalog"></div>
    </section>

    <section class="npi-panel" data-panel="downloads" id="npi-panel-downloads"
         role="tabpanel" aria-labelledby="npi-tab-downloads">
      <div id="npi-recovered-note"></div>
      <div id="npi-deid-note"></div>
      <div class="npi-dlgroup">
        <div class="lbl">Download files</div>
        <div class="npi-dlbar">
          <a class="npi-dl" id="npi-dl" href="#" download>⤓ Download cleaned CSV</a>
          <a class="npi-dl npi-dl-alt" id="npi-dl-xlsx" href="#" download>
            ⤓ Download report (.xlsx)</a>
          <a class="npi-dl npi-dl-alt npi-hidden" id="npi-dl-companion"
             href="#" download>⤓ Corrections companion (.csv)</a>
          <a class="npi-dl npi-dl-alt npi-hidden" id="npi-dl-changelog"
             href="#" download>⤓ Change log — audit trail (.csv)</a>
          <a class="npi-dl npi-dl-alt npi-hidden" id="npi-dl-dict"
             href="#" download>⤓ Data dictionary (.csv)</a>
          <a class="npi-dl npi-dl-alt" id="npi-dl-bundle" href="#" download>
            ⤓ Everything (.zip)</a>
        </div>
      </div>
      <div id="npi-reconcile" class="npi-mt"></div>
      <p class="npi-mt">
        <button class="npi-again" id="npi-again">Clean another file</button></p>
    </section>
  </div>

  <div class="npi-setup">
    {setup_eyebrow}
    <section id="npi-wishlist" class="npi-box">
      {wishlist_head}
      <p class="npi-muted">A check your compliance team needs, a payer we
        don't recognize, a field the detector misses, a file format we don't
        read — log it here. Requests go on the cleaner's build backlog and
        get filled in.</p>
      <div class="npi-wishform">
        <select id="npi-wish-cat" class="npi-select"
                aria-label="Request category">
          <option value="rule">New check / rule</option>
          <option value="field">Field / column type</option>
          <option value="payer">Payer</option>
          <option value="format">File format</option>
          <option value="integration">Integration / connector</option>
          <option value="other">Something else</option>
        </select>
        <input id="npi-wish-title" class="npi-input grow"
               placeholder="One-line summary (required)" maxlength="120"
               aria-label="Request summary">
        <button type="button" class="npi-dl sm" id="npi-wish-add">Request</button>
      </div>
      <textarea id="npi-wish-details" class="npi-input" rows="2"
        maxlength="2000" aria-label="Request details"
        placeholder="Details (optional): what the data looks like, what you expect the cleaner to do"></textarea>
      <p id="npi-wish-msg" class="npi-muted" aria-live="polite"></p>
      <div id="npi-wish-list" class="npi-mt-sm"></div>
    </section>

    <section id="npi-refdata" class="npi-box">
      {refdata_head}
      <p class="npi-muted">The cleaner grades files out of the box with
        curated catalogs. Pull the authoritative public sets to go further:
        the full NUCC taxonomy, the complete ICD-10-CM and HCPCS Level II
        code sets (activates shaped-but-nonexistent-code flags), and the OIG
        exclusion list (activates automatic offline excluded-provider
        screening on every run). Downloads run on this server from nucc.org /
        cms.gov / oig.hhs.gov; each pack records its source, row count and
        SHA-256.</p>
      <div id="npi-refdata-list"><p class="npi-muted">Loading…</p></div>
      <p class="npi-mt-sm">{catalog_link}</p>
    </section>
  </div>

  <div class="npi-note" id="npi-method">
    <strong>What "cleaned" means.</strong> An NPI is <em>valid</em> when it is
    exactly 10 digits and passes the Luhn check over the constant prefix
    <code>80840</code> plus its first nine digits — the same rule CMS/NPPES
    uses. <em>Malformed</em> = present but not 10 digits; <em>checksum</em> =
    10 digits but the check digit is wrong; <em>blank</em> = missing. Rows and
    columns are preserved exactly; only surrounding whitespace is trimmed and
    byte-identical duplicate rows are dropped. Nothing is written to a
    database, and no data leaves this server unless you explicitly enable the
    live NPPES cross-check below.
    <br><br>
    <strong>Two engines.</strong> The scorecard and cleaned file above always
    run on a dependency-free stdlib pass. When the server has pandas available,
    the file is <em>also</em> run through the genuine, complete
    <code>NPI&nbsp;Recovery&nbsp;&amp;&nbsp;Cleaner v49</code> deterministic
    engine — <code>schema.standardize_any</code> +
    <code>clean_orchestrator.clean_all</code>. That applies safe deterministic
    repairs and runs every coding-edit and consistency screen (NCCI MUE, PTP
    pairs, ICD-10/DOS validity, age–sex, JW/JZ single-dose wastage,
    deactivated-NPI, and the money/date/role/units cross-field checks) against
    the CMS reference tables vendored with the package. Each issue is sized —
    rows, % of rows, dollar exposure, and a systematic-vs-random verdict — and
    every fixable row gets a suggested correction you can download as the
    corrections companion. Extended anomaly screens add Benford first-digit
    conformance on allowed amounts, rounding-pathology by group, per-unit rate
    outliers, and billing-provider concentration (HHI). The full networked
    recovery pipeline
    (<code>run_pipeline</code>, live NPPES/CMS Steps&nbsp;0–8) ships in the
    vendored package for batch/CLI use; see
    <code>rcm_mc/npi_cleaner/vendor_v49/README.md</code>.
    <br><br>
    <strong>Online mode (opt-in).</strong> Tick "Go online" and the cleaner
    lights up PE&nbsp;Desk's own live public-data connectors under the
    <em>Live connectors</em> tab:
    <strong>NPPES</strong> (<code>data_public.nppes_api_client</code>) verifies
    each distinct NPI (active vs. deactivated) and recovers a candidate NPI for
    rows with a provider/organization name but a missing billing NPI;
    <strong>RxNorm / RxNav</strong> and <strong>openFDA</strong>
    (<code>data_public.public_api_clients</code>) resolve NDC and drug-name
    columns to normalized RxCUI concepts and drug labels. The tab also lists
    every public-data source connected to the platform (NPPES, OIG LEIE, RxNav,
    openFDA, DailyMed, HRSA, Census, ClinicalTrials, and more) that can be
    enabled for enrichment. All lookups are de-duplicated, capped per run and
    cached; if the network is unavailable the connectors simply no-op and the
    offline results stand. No data leaves the server unless online mode is on.
  </div>
</div>
{ck_page_actions(glossary=False, methodology=False)}
"""


_EXTRA_JS = r"""
(function(){
  var $ = function(id){ return document.getElementById(id); };
  var drop=$("npi-drop"), fileIn=$("npi-file");
  var stUp=$("npi-stage-upload"), stMap=$("npi-stage-mapping"),
      stPr=$("npi-stage-progress"),
      stErr=$("npi-stage-error"), stRes=$("npi-stage-result");
  var poll=null, currentFile=null, detectRoles=[], currentJobId=null;

  function show(el){ el.classList.remove("npi-hidden"); }
  function hide(el){ el.classList.add("npi-hidden"); }
  function reset(){
    if(poll){ clearInterval(poll); poll=null; }
    hide(stMap); hide(stPr); hide(stErr); hide(stRes); show(stUp);
    fileIn.value=""; currentFile=null;
  }
  function fail(msg){
    if(poll){ clearInterval(poll); poll=null; }
    hide(stUp); hide(stMap); hide(stPr); hide(stRes);
    $("npi-err-text").textContent = msg || "Something went wrong.";
    show(stErr);
  }
  function fmt(n){ return (n==null?0:n).toLocaleString(); }
  // House numeric discipline (mirrors ck_fmt_currency / ck_fmt_percent):
  // dollars always carry 2 decimals inside their magnitude bucket, and
  // percentages always render at exactly 1 decimal.
  function money(n){ return "$"+Number(n==null?0:n).toLocaleString(
    undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); }
  function dollars(v){
    if(v==null) return "";
    if(v>=1e6) return "$"+(v/1e6).toFixed(2)+"M";
    if(v>=1e3) return "$"+(v/1e3).toFixed(2)+"K";
    return money(v);
  }
  function pct1(v){
    var n=Number(v==null?0:v);
    return (isNaN(n)?0:n).toFixed(1)+"%";
  }
  // After innerHTML lands, hydrate data-w / data-h bar geometry. Keeps
  // every dynamic width/height out of HTML style attributes so the bar
  // styling lives in one CSS class per tone.
  function applyBars(box){
    if(!box) return;
    box.querySelectorAll("[data-w]").forEach(function(el){
      var w=parseFloat(el.getAttribute("data-w"));
      if(!isNaN(w)) el.style.width=Math.max(0,Math.min(100,w))+"%";
    });
    box.querySelectorAll("[data-h]").forEach(function(el){
      var h=parseFloat(el.getAttribute("data-h"));
      if(!isNaN(h)) el.style.height=Math.max(0,Math.min(100,h))+"%";
    });
  }
  // Section header in the page's editorial idiom: optional mono eyebrow,
  // serif title, optional mono count, optional muted sub-line. One factory
  // for every JS-rendered section so the anatomy can't drift per renderer.
  function secHead(t, sub, eb, count){
    return '<header class="npi-sec">'+
      (eb?'<span class="eb">'+eb+'</span>':'')+
      '<h3>'+t+(count!=null && count!==''?'<span class="ct">'+count+'</span>':'')+
      '</h3></header>'+
      (sub?'<p class="npi-muted">'+sub+'</p>':'');
  }
  // Kit-classed empty state (mirrors ck_empty_state anatomy) for the
  // client-rendered panels. The shell already ships the .ck-empty-state CSS.
  function emptyCard(icon, title, body, ctaLabel, ctaHref){
    return '<div class="ck-empty-state npi-empty">'+
      (icon?'<div class="ck-empty-state-icon" aria-hidden="true">'+icon+'</div>':'')+
      '<h3 class="ck-empty-state-title">'+title+'</h3>'+
      (body?'<p class="ck-empty-state-body">'+body+'</p>':'')+
      ((ctaLabel&&ctaHref)?'<div class="ck-empty-state-actions">'+
        '<a class="ck-empty-state-cta" href="'+ctaHref+'">'+ctaLabel+'</a></div>':'')+
      '</div>';
  }
  // Kit-classed provenance hover (mirrors ck_provenance_tooltip's explainer
  // path; its CSS is injected by the server-rendered tooltips on this page).
  // value is pre-formatted display markup; label/explainer must be escaped
  // by the caller when user-derived.
  function provTT(value, label, explainer){
    return '<span class="ck-prov-tt" tabindex="0">'+
      '<span class="ck-prov-tt-value">'+value+'</span>'+
      '<span class="ck-prov-tt-icon" aria-hidden="true">i</span>'+
      '<span class="ck-prov-tt-card" role="tooltip">'+
      '<span class="ck-prov-tt-label">'+label+'</span>'+explainer+
      '</span></span>';
  }

  function healthClass(pct){ return pct>=99?"good":(pct>=90?"warn":"bad"); }

  function selectTab(name){
    document.querySelectorAll(".npi-tab").forEach(function(b){
      var on=b.getAttribute("data-tab")===name;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on?"true":"false");
      if(on){ b.removeAttribute("tabindex"); }
      else { b.setAttribute("tabindex","-1"); }
    });
    document.querySelectorAll(".npi-panel").forEach(function(p){
      p.classList.toggle("is-active", p.getAttribute("data-panel")===name); });
  }

  function render(s){
    var health=(s.health_pct!=null?s.health_pct:0);
    var cards=[
      {k:"Rows in", v:fmt(s.rows_in)},
      {k:"Rows out", v:fmt(s.rows_out)},
      {k:"Duplicates removed", v:fmt(s.duplicates_removed),
       t:s.duplicates_removed>0?"warn":"good",
       tag:s.duplicates_removed>0?["review","warning"]:["clean","positive"]},
      {k:"NPI health",
       v:provTT(pct1(health), "NPI health",
         "Valid NPIs as a share of filled NPI cells across every "+
         "NPI-shaped column — 10 digits passing the CMS 80840 Luhn check."),
       t:healthClass(health),
       tag:health>=99?["clean","positive"]:
           (health>=90?["review","warning"]:["attention","negative"])},
      {k:"Billing-NPI issues", v:fmt(s.billing_issues),
       t:s.billing_issues>0?"bad":"good",
       tag:s.billing_issues>0?["attention","negative"]:["clean","positive"]},
      {k:"Cells trimmed", v:fmt(s.cells_trimmed)}
    ];
    $("npi-cards").innerHTML = cards.map(function(c){
      return '<div class="npi-card"><div class="k">'+c.k+'</div>'+
        '<div class="v '+(c.t||'')+'">'+c.v+'</div>'+
        (c.tag?'<div class="tag"><span class="npi-chip tone-'+c.tag[1]+'">'+
          c.tag[0]+'</span></div>':'')+
        '</div>';
    }).join("");

    var w=$("npi-warnings"); w.innerHTML="";
    (s.warnings||[]).forEach(function(msg){
      var d=document.createElement("div"); d.className="npi-warn";
      d.textContent=msg; w.appendChild(d);
    });

    var rows="";
    var cs=s.column_stats||{};
    Object.keys(cs).forEach(function(col){
      var c=cs[col]; var cells=c.cells||0;
      var pct=cells?Math.round(1000*c.valid/cells)/10:0;
      var hc=healthClass(pct);
      var isBilling=(col===s.billing_column);
      rows+='<tr><td class="'+(isBilling?'billing':'')+'">'+esc(col)+
        (isBilling?'<span class="npi-badge">billing</span>':'')+'</td>'+
        '<td class="num">'+fmt(cells)+'</td>'+
        '<td class="num">'+fmt(c.valid)+'</td>'+
        '<td class="num">'+fmt(c.blank)+'</td>'+
        '<td class="num">'+fmt(c.malformed)+'</td>'+
        '<td class="num">'+fmt(c.checksum)+'</td>'+
        '<td class="num"><span class="npi-hbar">'+
          '<span class="track"><i class="'+hc+'" data-w="'+
          Math.max(2,Math.min(100,pct))+'"></i></span>'+
          '<span class="pct '+hc+'">'+pct1(pct)+'</span></span></td></tr>';
    });
    if(!rows){ rows='<tr><td colspan="7">'+emptyCard('◍',
      'No NPI column detected in this file.',
      'The cleaner looks for 10-digit NPI-shaped columns by header and by '+
      'value. Rename the billing-provider column (e.g. billing_npi) or map '+
      'it on the next upload.',
      'See what the cleaner looks for','#npi-method')+'</td></tr>'; }
    $("npi-col-rows").innerHTML=rows;
    applyBars($("npi-col-rows"));
    (s.rule_catalog||[]).forEach(function(r){ RULE_INFO[r.id]=r; });
    renderRepairs(s);
    rememberJob(currentJobId, s.out_name||"run");
    renderReconcile(s);
    renderSanity(s.sanity, s.worklists, s.download, s.accepted_rules||[]);
    renderQuality(s);
    $("tabbadge-quality").textContent = (s.quality&&s.quality.letter)||"";

    renderAdvanced(s.advanced);
    renderSuggestions(s.advanced);
    renderPopulation(s.population, s.download);
    $("tabbadge-pop").textContent = s.population
      ? String(Object.keys(s.population).length) : "";
    renderConnectorPlan(s.connector_plan);
    renderDeep(s.deep, s.download, s.deep_workbook_name);
    renderCompliance(s.compliance);
    renderOrderReferring(s.order_referring);
    renderNppes(s.nppes);
    renderConnectors(s.connectors);
    renderCatalog(s.catalog);

    // Tab badges: issue count + live-connector count.
    var nIssues=(s.advanced&&s.advanced.issues?s.advanced.issues.length:0)+
      (s.advanced&&s.advanced.suggestions_n?1:0);
    $("tabbadge-issues").textContent = nIssues? String(
      (s.advanced&&s.advanced.issues?s.advanced.issues.length:0)) : "";
    var nConn=(s.connectors?s.connectors.filter(function(c){return c.resolved>0}).length:0)+
      (s.nppes&&s.nppes.verify?1:0);
    $("tabbadge-conn").textContent = nConn? String(nConn) : "";

    $("npi-dl").setAttribute("href", s.download);
    $("npi-dl").setAttribute("download", s.out_name||"cleaned.csv");
    function showBtn(el, on){ el.classList.toggle("npi-hidden", !on); }
    var xbtn=$("npi-dl-xlsx");
    if(s.workbook_name){
      xbtn.setAttribute("href", s.download+"?fmt=xlsx");
      xbtn.setAttribute("download", s.workbook_name);
    }
    showBtn(xbtn, !!s.workbook_name);
    var cbtn=$("npi-dl-companion");
    if(s.companion_name){
      cbtn.setAttribute("href", s.download+"?fmt=companion");
      cbtn.setAttribute("download", s.companion_name);
    }
    showBtn(cbtn, !!s.companion_name);
    var lbtn=$("npi-dl-changelog");
    if(s.changelog_name){
      lbtn.setAttribute("href", s.download+"?fmt=changelog");
      lbtn.setAttribute("download", s.changelog_name);
    }
    showBtn(lbtn, !!s.changelog_name);
    var bbtn=$("npi-dl-bundle");
    bbtn.setAttribute("href", s.download+"?fmt=bundle");
    bbtn.setAttribute("download", "npi_clean_bundle.zip");
    var dbtn=$("npi-dl-dict");
    if(s.dictionary && s.dictionary.length){
      dbtn.setAttribute("href", s.download+"?fmt=dictionary");
      dbtn.setAttribute("download", "data_dictionary.csv");
    }
    showBtn(dbtn, !!(s.dictionary && s.dictionary.length));

    if(currentJobId){ $("npi-analyze").setAttribute("href",
      "/npi-cleaner/analyze/"+currentJobId);
      $("npi-exec").setAttribute("href",
      "/npi-cleaner/download/"+currentJobId+"?fmt=exec"); }

    var rn=$("npi-recovered-note");
    if(s.recovered_written>0){
      rn.innerHTML='<div class="npi-recovered"><strong>'+
        fmt(s.recovered_written)+' row'+(s.recovered_written===1?'':'s')+
        '</strong> had a billing NPI recovered from NPPES — written to a '+
        'new <code>recovered_billing_npi</code> column in the download '+
        '(originals preserved).</div>';
    } else { rn.innerHTML=""; }

    var dn=$("npi-deid-note");
    if(dn){
      if(s.deid && s.deid.cells>0){
        dn.innerHTML='<div class="npi-recovered">PHI de-identified — '+
          '<strong>'+fmt(s.deid.cells)+' patient cell'+
          (s.deid.cells===1?'':'s')+'</strong> masked across '+
          (s.deid.columns?s.deid.columns.length:0)+
          ' column'+((s.deid.columns&&s.deid.columns.length===1)?'':'s')+' ('+
          (s.deid.columns?s.deid.columns.map(esc).join(', '):'')+
          '). Provider NPI &amp; name left intact for recovery.</div>';
      } else if(s.deid){
        dn.innerHTML='<p class="npi-muted">'+
          'De-identify was on, but no patient-scoped PHI columns were detected '+
          'in this file — nothing to mask.</p>';
      } else { dn.innerHTML=""; }
    }

    // Always land on the Overview tab for a fresh result.
    selectTab("overview");
    hide(stUp); hide(stPr); hide(stErr); show(stRes);
  }

  function flagRow(label, sub, count){
    var hit = count>0;
    return '<div class="npi-flag"><div class="lab">'+label+
      (sub?'<small>'+sub+'</small>':'')+'</div>'+
      '<div class="cnt '+(hit?'hit':'clear')+'">'+
      (hit?fmt(count)+' flagged':'clear')+'</div></div>';
  }

  function drillTable(drill){
    var cols=drill.columns||[], rows=drill.rows||[];
    var h='<div class="npi-scroll"><table><thead><tr>';
    cols.forEach(function(c){ h+='<th>'+esc(c.replace(/_/g," "))+'</th>'; });
    h+='</tr></thead><tbody>';
    rows.forEach(function(r){
      h+='<tr>'; cols.forEach(function(c){ h+='<td>'+esc(r[c])+'</td>'; }); h+='</tr>';
    });
    h+='</tbody></table></div><p class="npi-fine">Showing up '+
      'to 15 offending rows.</p>';
    return h;
  }

  var REPAIR_LABELS={
    "whitespace-chars":"Non-breaking / zero-width spaces normalized",
    "collapse-space":"Collapsed internal whitespace",
    "mojibake":"Repaired mojibake (mis-encoded characters)",
    "leading-apostrophe":"Stripped Excel text-marker apostrophe",
    "null-token":"Unified null tokens (NA / N/A / NULL …) to blank",
    "npi-excel-float":"Fixed NPIs mangled to floats by Excel (…​.0)",
    "npi-strip-nondigits":"Stripped non-digits from NPIs",
    "money-normalize":"Normalized money ($ / commas / accounting negatives)",
    "date-excel-serial":"Converted Excel serial dates to ISO",
    "date-us-to-iso":"Converted US-format dates to ISO",
    "date-iso-trim":"Trimmed date-times to ISO date",
    "state-name-to-code":"Mapped state names to 2-letter codes",
    "state-upper":"Upper-cased state codes",
    "zip-pad":"Restored dropped leading zeros in ZIPs",
    "zip5+4":"Formatted ZIP+4",
    "zip-clean":"Cleaned ZIP formatting",
    "hcpcs-upper":"Upper-cased HCPCS/CPT codes",
    "sex-normalize":"Normalized sex/gender to M / F / U",
    "dx-upper":"Upper-cased ICD-10 diagnosis codes",
    "dx-decimal":"Inserted the ICD-10 decimal point (E1165 → E11.65)",
    "modifier-normalize":"Normalized claim-line modifiers (split · upper · dedup)",
    "phone-format":"Formatted phone/fax numbers",
    "taxonomy-upper":"Upper-cased provider taxonomy codes",
    "ndc-pad-11":"Padded NDC to 11-digit billing format (segment-aware)",
    "ndc-normalize-11":"Normalized NDC to 11-digit billing format",
    "revcode-pad":"Restored dropped leading zeros in revenue codes (450 → 0450)",
    "pos-pad":"Zero-padded 1-digit Place of Service codes",
    "provider-name-format":"Re-cased provider names (SMITH, JOHN A, MD → Smith, John A, MD)",
    "drg-pad":"Restored dropped leading zeros in MS-DRGs (87 → 087)",
    "state-from-zip":"Filled blank state from the ZIP code (deterministic ZIP3→state)",
    "name-from-nppes":"Filled blank provider name from the verified NPI's NPPES record",
    "state-from-nppes":"Filled blank state from the verified NPI's NPPES record",
    "taxonomy-from-nppes":"Filled blank taxonomy from the verified NPI's NPPES record"};

  // Takes the scorecard like its siblings (renderQuality/renderReconcile):
  // at 5 positional params, two of which shared a shape, a silent swap at
  // the call site would have rendered credential tallies as repair rules.
  function renderRepairs(s){
    var repairs=s.repairs, total=s.repairs_total, credentials=s.credentials,
        specialties=s.specialties, claims=s.claims;
    var box=$("npi-repairs");
    var keys=repairs?Object.keys(repairs):[];
    var ckeys=credentials?Object.keys(credentials):[];
    var specs=specialties||[];
    if(!keys.length && !ckeys.length && !specs.length && !claims){
      box.innerHTML=""; return; }
    var claimsHtml="";
    if(claims && claims.n_claims){
      claimsHtml=secHead('Claim rollup',
        fmt(claims.n_claims)+' distinct claims ('+
        esc(claims.column)+') · '+claims.avg_lines+' lines/claim avg · '+
        fmt(claims.max_lines)+' max'+
        (claims.charge?(' · per-claim charge '+
          money(claims.charge.median)+' median / '+money(claims.charge.max)+
          ' max'):'')+
        (claims.truncated?' · (rollup capped at 50,000 claims)':''));
    }
    var html="";
    if(keys.length){
      keys.sort(function(a,b){return repairs[b]-repairs[a];});
      html+=secHead('Cleaning fixes applied',
        fmt(total)+' deterministic normalizations written '+
        'to the cleaned file (originals were replaced in place).',
        'REPAIRS · APPLIED IN PLACE', keys.length);
      keys.forEach(function(k){
        html+=flagRow(REPAIR_LABELS[k]||k, '<span class="npi-pill">'+k+'</span>', repairs[k]);
      });
    }
    if(ckeys.length){
      ckeys.sort(function(a,b){return credentials[b]-credentials[a];});
      html+=secHead('Credential mix',
        'Clinical credentials parsed from provider-name '+
        'columns (cells naming each credential).')+
        '<div class="npi-mt-sm">'+
        ckeys.map(function(k){
          return '<span class="npi-pill blk">'+
            esc(k)+' · '+fmt(credentials[k])+'</span>';
        }).join("")+'</div>';
    }
    if(specs.length){
      html+=secHead('Specialty mix',
        'Top provider taxonomy codes on the cleaned rows '+
        '(NUCC display names where known).')+
        '<div class="npi-mt-sm">'+
        specs.map(function(s){
          return '<span class="npi-pill blk">'+
            esc(s.name||s.code)+' · '+fmt(s.n)+'</span>';
        }).join("")+'</div>';
    }
    box.innerHTML=html+claimsHtml;
  }

  var SANITY_LABELS={
    "allowed-exceeds-billed":"Allowed amount exceeds billed",
    "paid-exceeds-allowed":"Paid amount exceeds allowed",
    "negative-allowed":"Negative allowed amount",
    "negative-paid":"Negative paid amount",
    "nonpositive-units":"Units ≤ 0",
    "fractional-units":"Fractional (non-integer) units",
    "suspected-duplicate-claim":"Suspected duplicate claim (same provider · patient · date · code · amount)",
    "ndc-ambiguous-10digit":"Ambiguous 10-digit NDC (segmentation unknown — verify at source)",
    "date-in-future":"Impossible future date (service · birth · paid date after today)",
    "zip-state-mismatch":"ZIP prefix disagrees with the state code (verify address at source)",
    "hcpcs-malformed":"Malformed HCPCS/CPT code (not 5 digits, letter+4 digits, or 4 digits+letter)",
    "icd10-malformed":"Malformed ICD-10 diagnosis code (bad shape)",
    "money-unparseable":"Non-numeric value in an amount column (couldn't parse as money)",
    "sex-invalid":"Invalid sex/gender value (didn't resolve to M/F/U)",
    "taxonomy-malformed":"Malformed provider taxonomy code (not 10 alphanumeric characters)",
    "paid-exceeds-billed":"Paid amount exceeds billed",
    "service-before-birth":"Service date before the patient's date of birth",
    "discharge-before-admit":"Discharge date before the admission date",
    "date-stale":"Service date more than 10 years old (likely century/key error)",
    "pos-invalid":"Place of Service not in the CMS code set",
    "revenue-code-malformed":"Malformed revenue code (not 4 digits)",
    "charge-outlier":"Charge is a statistical outlier for its HCPCS code (beyond 3×IQR)",
    "mbi-malformed":"Malformed Medicare MBI (member ID fails the MBI position rules)",
    "condition-code-malformed":"Malformed UB-04 condition code (not 2 alphanumerics)",
    "occurrence-code-malformed":"Malformed UB-04 occurrence code (not 2 alphanumerics)",
    "value-code-malformed":"Malformed UB-04 value code (not 2 alphanumerics)",
    "near-duplicate-row":"Near-duplicate row (identical after case/space folding)",
    "jw-zero-units":"JW modifier (discarded drug) with no billed units",
    "bilateral-units":"Bilateral modifier 50 with more than 1 unit (MUE guidance)",
    "conflicting-amount-claim":"Same provider · patient · date · code billed at different amounts (re-bill signal)",
    "carc-invalid":"Invalid denial/adjustment reason code (not a CARC shape)",
    "drg-malformed":"Malformed MS-DRG (not a 3-digit code 001-999)",
    "anesthesia-units-implausible":"Anesthesia line billing more than 24 hours of time units",
    "revenue-tob-mismatch":"Room &amp; board revenue code on an outpatient type of bill",
    "possible-duplicate-service":"Same patient · provider · code again within the duplicate window"};
  var RULE_INFO={};
  function sevChip(sev){
    var tone=sev==="critical"?"negative":(sev==="warning"?"warning":"");
    return '<span class="npi-chip'+(tone?' tone-'+tone:'')+'">'+sev+'</span> ';
  }
  function renderSanity(sanity, worklists, dl, accepted){
    var acc={}; (accepted||[]).forEach(function(a){acc[a]=1;});
    var box=$("npi-sanity");
    var keys=sanity?Object.keys(sanity):[];
    if(!keys.length){ box.innerHTML=""; return; }
    var rank={critical:0,warning:1,info:2};
    keys.sort(function(a,b){
      var ra=rank[(RULE_INFO[a]||{}).severity]!=null?rank[(RULE_INFO[a]||{}).severity]:3,
          rb=rank[(RULE_INFO[b]||{}).severity]!=null?rank[(RULE_INFO[b]||{}).severity]:3;
      return ra!==rb ? ra-rb : sanity[b]-sanity[a];
    });
    var html=secHead('Data sanity flags',
      'Findings are reported, never auto-changed — '+
      'each has a per-rule worklist download of just the flagged rows.',
      'SCREENS · REPORT-ONLY', keys.length);
    keys.forEach(function(k){
      var info=RULE_INFO[k]||{};
      var label=(info.title||SANITY_LABELS[k]||k);
      if(acc[k]){ label='<span class="npi-accepted">'+label+
        ' <em class="npi-fine">(accepted — not graded)</em></span>'; }
      var sub=sevChip(info.severity||"info")+'<span class="npi-pill">'+k+'</span>'+
        (info.remediation?('<br><span class="npi-muted">'+esc(info.remediation)+
        '</span>'):'');
      if(worklists && worklists[k] && dl){
        sub+=' <a class="npi-wl" href="'+dl+'?fmt=worklist&rule='+
          encodeURIComponent(k)+'" download>⤓ worklist ('+
          fmt(worklists[k])+' rows)</a>';
      }
      html+=flagRow(label, sub, sanity[k]);
    });
    box.innerHTML=html;
  }

  var DIM_LABELS={
    completeness:["Completeness","filled cells / total cells"],
    validity:["Validity","values that can be right (codes · amounts · IDs)"],
    consistency:["Consistency","fields that agree with each other"],
    uniqueness:["Uniqueness","free of duplicate rows and repeat claims"],
    conformity:["Conformity","how little normalization the file needed"]};
  function renderQuality(s){
    var box=$("npi-quality"), q=s.quality;
    if(!q){
      box.innerHTML=emptyCard('◔','No quality data for this run.',
        'The five-dimension report card needs the scorecard counts — '+
        'streaming (10 GB) runs skip it by design.');
      return;
    }
    var toneCls=q.score>=85?'good':(q.score>=70?'warn':'bad');
    var html=secHead('Data-quality report card',
      'Five-dimension grade computed from the counts '+
      'on this page — every number is recomputable from the scorecard.',
      'QUALITY · GRADED');
    // Trend alerts: regressions vs the previous run of this same file.
    if(s.trend_alerts && s.trend_alerts.length){
      html+='<div class="npi-warn"><strong>'+
        'Changed since the last run of this file:</strong><ul>'+
        s.trend_alerts.map(function(a){ return '<li>'+esc(a)+'</li>'; })
        .join("")+'</ul></div>';
    }
    // Zip batch: per-file grades (the card above blends all rows).
    if(s.batch && s.batch.length){
      html+=secHead('Batch files',
        'Each file was cleaned separately; the '+
        'grade above blends all rows across the batch.',
        null, s.batch.length)+
        '<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>File</th><th class="num">Rows in</th><th class="num">Rows out</th>'+
        '<th class="num">Repairs</th><th class="num">Findings</th>'+
        '<th class="num">Grade</th></tr></thead><tbody>'+
        s.batch.map(function(b){
          return '<tr><td>'+esc(b.file)+'</td><td class="num">'+
            fmt(b.rows_in)+'</td><td class="num">'+fmt(b.rows_out)+
            '</td><td class="num">'+fmt(b.repairs)+'</td><td class="num">'+
            fmt(b.findings)+'</td><td class="num">'+esc(b.letter)+' · '+
            b.score+'</td></tr>';
        }).join("")+'</tbody></table></div>';
    }
    html+='<div class="npi-grade"><span class="letter '+toneCls+'">'+
      esc(q.letter)+'</span><span class="meta">overall grade'+
      '<b class="'+toneCls+'">'+provTT(q.score+' / 100', 'Overall grade',
        'Weighted blend of the five dimension scores below — every input '+
        'count is on this page, so the grade is recomputable by hand.')+
      '</b></span></div>';
    // Dimension bars.
    html+='<div class="npi-dims">';
    Object.keys(DIM_LABELS).forEach(function(k){
      var v=(q.dimensions&&q.dimensions[k]!=null)?q.dimensions[k]:0;
      var lab=DIM_LABELS[k];
      var c=v>=85?'good':(v>=70?'warn':'bad');
      html+='<div class="npi-dim"><span class="dl">'+lab[0]+'</span>'+
        '<span class="dtrack"><i class="'+c+'" data-w="'+
        Math.max(2,Math.min(100,v))+'"></i></span>'+
        '<span class="dv '+c+'">'+v.toFixed(1)+'%</span>'+
        '<span class="dd">'+lab[1]+'</span></div>';
    });
    html+='</div>';
    // Per-column fill-rate profile: only columns with blanks, worst first.
    var fills=(s.fill_rates||[]).filter(function(f){return f.pct<100;});
    if(fills.length){
      fills.sort(function(a,b){return a.pct-b.pct;});
      html+=secHead('Columns with blanks',
        'Fill rate per column (only columns below 100% '+
        'shown, emptiest first).', null, fills.length);
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Column</th><th class="num">Filled rows</th><th class="num">% filled</th>'+
        '</tr></thead><tbody>';
      fills.slice(0,12).forEach(function(f){
        var t=f.pct>=90?'':(f.pct>=60?' warn':' bad');
        html+='<tr><td>'+esc(f.column)+'</td><td class="num">'+fmt(f.filled)+
          '</td><td class="num'+t+'">'+f.pct.toFixed(1)+'%</td></tr>';
      });
      html+='</tbody></table></div>';
      if(fills.length>12){ html+='<p class="npi-muted">'+
        fmt(fills.length-12)+' more columns have blanks — see the .xlsx report.</p>'; }
    }
    // Payer-name variant clusters.
    var p=s.payer;
    if(p && p.multi_spelling && p.multi_spelling.length){
      html+=secHead('Payer spellings to reconcile',
        esc(p.column)+' has '+fmt(p.distinct_raw)+
        ' raw spellings across '+fmt(p.clusters)+' payer groups. Clusters below '+
        'contain 2+ spellings of what looks like the same payer (reported only '+
        '— nothing was rewritten).');
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Payer group</th><th class="num">Rows</th><th>Spellings seen</th>'+
        '</tr></thead><tbody>';
      p.multi_spelling.forEach(function(c){
        html+='<tr><td>'+esc(c.canonical)+'</td><td class="num">'+fmt(c.total)+
          '</td><td>'+c.variants.map(function(v){
            return esc(v.value)+' <span class="npi-fine">('+fmt(v.count)+')</span>';
          }).join(' · ')+'</td></tr>';
      });
      html+='</tbody></table></div>';
    }
    // Per-code charge outliers.
    if(s.outliers && s.outliers.length){
      html+=secHead('Charge outliers by procedure code',
        'Charges beyond 3×IQR fences within their HCPCS '+
        'code (codes seen 10+ times). Same quantile math as the box plot on '+
        'the analysis page.');
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>HCPCS</th><th class="num">Lines</th><th class="num">Outliers</th>'+
        '<th class="num">Median</th><th class="num">Max seen</th></tr></thead><tbody>';
      s.outliers.forEach(function(o){
        html+='<tr><td>'+esc(o.code)+'</td><td class="num">'+fmt(o.n)+
          '</td><td class="num">'+fmt(o.outliers)+'</td><td class="num">'+
          dollars(o.median)+'</td><td class="num">'+dollars(o.max)+'</td></tr>';
      });
      html+='</tbody></table></div>';
    }
    // Top denial / adjustment reasons.
    if(s.denials && s.denials.top && s.denials.top.length){
      html+=secHead('Top denial / adjustment reasons',
        esc(s.denials.column)+' — '+fmt(s.denials.distinct)+
        ' distinct codes. Highest-volume reasons below (CARC codes).'+
        (s.denials.preventable_pct!=null?(' <strong>'+
        pct1(s.denials.preventable_pct)+
        ' of the classified volume was preventable</strong> by a '+
        'pre-submission screen.'):''));
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Code</th><th class="num">Rows</th><th>Playbook</th><th>What to do</th>'+
        '</tr></thead><tbody>';
      var CAT_TONE={preventable:'negative',process:'warning',
        contractual:'',"patient-responsibility":''};
      s.denials.top.forEach(function(d){
        var tone=CAT_TONE[d.category];
        var cat=d.category?('<span class="npi-chip'+
          (tone?' tone-'+tone:'')+'">'+esc(d.category)+'</span>'):'';
        var act=d.action?esc(d.action)+(d.linked_rule?(' <span class="npi-pill">'+
          esc(d.linked_rule)+'</span>'):''):'';
        html+='<tr><td>'+esc(d.code)+'</td><td class="num">'+fmt(d.count)+
          '</td><td>'+cat+'</td><td class="npi-cell-sm">'+act+'</td></tr>';
      });
      html+='</tbody></table></div>';
    }
    // Per-payer quality split — which payer's feed is dirtiest.
    if(s.payer_quality && s.payer_quality.length){
      html+=secHead('Quality by payer',
        'Share of each payer&#39;s rows with at '+
        'least one finding, and that payer&#39;s top rules.');
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Payer</th><th class="num">Rows</th><th class="num">Flagged</th>'+
        '<th class="num">Clean %</th><th>Top rules</th></tr></thead><tbody>';
      s.payer_quality.forEach(function(p){
        var tone=p.clean_pct>=90?'good':(p.clean_pct>=70?'warn':'bad');
        var wl=(p.flagged>0 && s.download)?(' · <a class="npi-wl" href="'+
          s.download+'?fmt=worklist&payer='+encodeURIComponent(p.payer)+
          '" download>worklist</a>'):'';
        html+='<tr><td>'+esc(p.payer)+'</td><td class="num">'+fmt(p.rows)+
          '</td><td class="num">'+fmt(p.flagged)+'</td>'+
          '<td class="num '+tone+'">'+pct1(p.clean_pct)+
          '</td><td class="npi-cell-sm">'+
          (p.top_rules||[]).map(function(t){
            return esc(t.rule)+' ('+fmt(t.n)+')';
          }).join(", ")+wl+'</td></tr>';
      });
      html+='</tbody></table></div>';
    }
    // Structural findings.
    var st=s.structure;
    if(st && (st.duplicate_headers || st.empty_columns)){
      html+=secHead('File structure');
      if(st.duplicate_headers){
        html+='<div class="npi-warn">Duplicate column '+
          'headers (mapping is ambiguous): '+
          st.duplicate_headers.map(esc).join(', ')+'</div>';
      }
      if(st.empty_columns){
        html+='<div class="npi-warn">Columns that are '+
          '100% empty: '+st.empty_columns.map(esc).join(', ')+'</div>';
      }
    }
    // Audit trail summary. The change-log CSV is complete at any scale
    // (entries spill to disk during the run); truncated now only means
    // the server hit a disk error mid-spill.
    if(s.changes_logged){
      html+='<p class="npi-muted npi-mt"><strong>'+
        fmt(s.changes_logged)+' cell'+(s.changes_logged===1?'':'s')+
        ' changed in total</strong> — the full before/after audit trail is '+
        'on the Downloads tab'+(s.changelog_truncated
          ?' (log incomplete — the server ran out of disk while writing it)'
          :'')+'.</p>';
    }
    box.innerHTML=html;
    applyBars(box);
  }

  function renderAdvanced(adv){
    var box=$("npi-advanced");
    if(!adv){ box.innerHTML=""; return; }
    var html='<div class="npi-adv">';
    html+=secHead('Coding, consistency &amp; issue analysis', null,
      'ISSUES · SIZED &amp; VERDICTED');
    html+='<p class="npi-eng">real engine · '+esc(adv.engine||'')+
      (adv.repairs?(' · '+fmt(adv.repairs)+' deterministic repairs applied'):'')+
      '</p>';

    var issues=adv.issues||[];
    var irows=adv.issue_rows||{};
    if(issues.length){
      html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Issue</th><th class="num">Rows</th><th class="num">% rows</th>'+
        '<th class="num">$ exposure</th><th>Signal</th></tr></thead><tbody>';
      issues.forEach(function(it,ix){
        var sig=it.systematic||"";
        var tone=sig.indexOf("systematic")===0?"bad":
                 (sig.indexOf("random")===0?"":"warn");
        var drill=irows[it.issue];
        html+='<tr class="'+(drill?'npi-drill':'')+'" data-drill="'+ix+'"'+
          (drill?' tabindex="0" aria-expanded="false"':'')+'>'+
          '<td>'+esc(it.issue.replace(/_/g,' '))+'</td>'+
          '<td class="num">'+fmt(it.rows)+'</td>'+
          '<td class="num">'+(it.pct_rows!=null?it.pct_rows.toFixed(1)+'%':'')+'</td>'+
          '<td class="num">'+dollars(it.dollars)+'</td>'+
          '<td><span class="npi-sig '+tone+'">'+esc(sig)+'</span></td></tr>';
        if(drill){
          html+='<tr class="npi-drillrows npi-hidden" data-drillrows="'+ix+'"><td colspan="5">'+
            drillTable(drill)+'</td></tr>';
        }
      });
      html+='</tbody></table></div>';
    }

    var scr=adv.screens||{};
    var keys=Object.keys(scr);
    if(keys.length){
      html+=secHead('Screens run', null, null, keys.length);
      keys.forEach(function(k){
        html+=flagRow(k.replace(/_/g,' '), "", scr[k]);
      });
    }

    if(adv.suggestions_n>0){
      html+='<p class="npi-mono-note">'+
        fmt(adv.suggestions_n)+' row-level suggested corrections available '+
        '(current → suggested, with provenance) — download the corrections '+
        'companion below.</p>';
    }
    var ext=adv.extended||[];
    if(ext.length){
      html+=secHead('Extended anomaly screens');
      ext.forEach(function(e){
        var bad=/(deviate|flag|highly)/i.test(e.value);
        html+='<div class="npi-flag"><div class="lab">'+esc(e.label)+
          '<small>'+esc(e.note)+'</small></div>'+
          '<div class="cnt '+(bad?'hit':'')+'">'+esc(e.value)+'</div></div>';
      });
    }
    html+='</div>';
    box.innerHTML=html;
  }

  function renderNppes(n){
    var box=$("npi-nppes");
    if(!n){ box.innerHTML=""; return; }
    var html='<div class="npi-adv">'+
      secHead('Live NPPES verification &amp; recovery', null,
        'CONNECTOR · NPPES');
    if(n.error){
      html+='<div class="npi-warn">NPPES cross-check error: '+esc(n.error)+
        '</div></div>';
      box.innerHTML=html; return;
    }
    if(n.note && !n.verify){
      html+='<p class="npi-mono-note">'+esc(n.note)+'</p></div>';
      box.innerHTML=html; return;
    }
    html+='<p class="npi-eng">real connection · '+esc(n.source||'NPPES')+'</p>';

    var v=n.verify||{};
    html+='<div class="npi-cards tight">'+
      '<div class="npi-card"><div class="k">NPIs verified</div>'+
        '<div class="v">'+fmt(v.checked)+'</div></div>'+
      '<div class="npi-card"><div class="k">Active in NPPES</div>'+
        '<div class="v good">'+fmt(v.active)+'</div></div>'+
      '<div class="npi-card"><div class="k">Not found / deactivated</div>'+
        '<div class="v '+((v.not_found||0)>0?'bad':'good')+'">'+
        fmt(v.not_found)+'</div></div></div>';
    if(v.note){ html+='<p class="npi-mono-note">'+esc(v.note)+'</p>'; }
    if(n.filled_from_nppes){
      html+='<div class="npi-recovered">Filled <strong>'+
        fmt(n.filled_from_nppes)+
        ' blank provider name / state / taxonomy cell'+
        (n.filled_from_nppes===1?'':'s')+'</strong> from verified NPPES '+
        'records — audited in the change log.</div>';
    }

    // Per-NPI verdicts — the records were always fetched; now the user can
    // see WHICH NPIs are active, not found, or errored (not just counts).
    var recs=v.records||{};
    var keys=Object.keys(recs);
    if(keys.length){
      var flagged=keys.filter(function(k){
        return recs[k].status!=="active"; });
      var show=flagged.length?flagged:keys;   // lead with the problems
      show=show.slice(0,60);
      html+=secHead('NPI verdicts'+(flagged.length?' — '+flagged.length+
        ' need attention':''), null, null, show.length)+
        '<div class="npi-scroll npi-scroll--tall">'+
        '<table class="npi-tbl"><thead><tr><th>NPI</th><th>Status</th>'+
        '<th>Name</th><th>Taxonomy</th><th>State</th></tr></thead><tbody>';
      show.forEach(function(k){
        var rc=recs[k], bad=rc.status!=="active";
        html+='<tr><td class="'+(bad?'billing':'')+'">'+esc(k)+'</td>'+
          '<td><span class="npi-sig '+(bad?'bad':'')+'">'+esc(rc.status)+
          '</span></td><td>'+esc(rc.name||'')+'</td><td>'+
          esc(rc.taxonomy||'')+'</td><td>'+esc(rc.state||'')+'</td></tr>';
      });
      html+='</tbody></table></div>';
      if(show.length<keys.length){
        html+='<p class="npi-fine">Showing '+
          show.length+' of '+keys.length+' verified NPIs.</p>';
      }
    }

    var r=n.recover||{};
    var matches=(r.matches||[]).filter(function(m){
      return m.candidates && m.candidates.length; });
    if(matches.length){
      html+=secHead('Recovered NPI candidates', null, null, matches.length);
      matches.forEach(function(m){
        var c=m.candidates[0];
        html+='<div class="npi-cand"><span class="q">'+esc(m.query)+
          (m.state?' · '+esc(m.state):'')+'</span><span class="arrow">→</span>'+
          '<code>'+esc(c.npi)+'</code> '+esc(c.name)+
          ' <span class="rowref">(row '+esc(m.row)+')</span></div>';
      });
    } else if(r.note){
      html+='<p class="npi-mono-note">'+esc(r.note)+'</p>';
    }
    html+='</div>';
    box.innerHTML=html;
  }

  // Entity-escape INCLUDING quotes — names (profiles, templates, files)
  // land in attribute contexts, and the textContent trick left " alone.
  function esc(s){ return String(s==null?"":s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

  function renderPopulation(pop, download){
    var box=$("npi-pop");
    if(!pop){
      box.innerHTML=emptyCard('◔','No population marts for this run.',
        'They need service/claim columns (revenue code, type of bill, POS, '+
        'HCPCS, patient id, service dates, diagnoses). Streaming (10 GB) '+
        'runs skip them by design.');
      return;
    }
    var h="";
    if(pop.service_mix){
      h+=secHead("Service-category mix", "Every line classified by the "+
        "institutional-first ladder (type of bill → revenue code → place "+
        "of service → HCPCS range). Unclassified: "+
        pct1(pop.service_mix.unclassified_pct)+".",
        "MART · SERVICE MIX");
      h+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Category</th>'+
        '<th>Subcategory</th><th class="num">Lines</th>'+
        '<th class="num">% of file</th><th class="num">Charges</th>'+
        '</tr></thead><tbody>';
      pop.service_mix.categories.slice(0,14).forEach(function(c){
        h+='<tr><td>'+esc(c.category)+'</td><td>'+esc(c.subcategory)+
          '</td><td class="num">'+fmt(c.rows)+'</td><td class="num">'+
          pct1(c.pct)+'</td><td class="num">'+dollars(c.charges)+'</td></tr>';
      });
      h+='</tbody></table></div>';
    }
    if(pop.encounters){
      var e=pop.encounters;
      h+=secHead("Encounters", fmt(e.n_encounters)+" visits grouped from "+
        fmt(e.n_patients)+" patients (same patient, same setting, service "+
        "dates chaining with gaps ≤ 1 day"+
        (e.records_truncated?"; download capped":"")+").",
        "MART · VISITS");
      h+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Setting</th>'+
        '<th class="num">Encounters</th><th class="num">Avg lines</th>'+
        '<th class="num">Charges</th></tr></thead><tbody>';
      (e.by_category||[]).forEach(function(c){
        h+='<tr><td>'+esc(c.category)+'</td><td class="num">'+
          fmt(c.encounters)+'</td><td class="num">'+esc(c.avg_lines)+
          '</td><td class="num">'+dollars(c.charges)+'</td></tr>';
      });
      h+='</tbody></table></div>';
      if(e.readmissions){
        var r=e.readmissions;
        h+='<p class="npi-muted npi-mt-sm">30-day inpatient '+
          'readmissions: <strong>'+fmt(r.readmissions_30d)+'</strong> of '+
          fmt(r.inpatient_stays)+' stays ('+pct1(r.rate_pct)+').</p>';
      }
      h+='<p class="npi-mt-sm"><a class="npi-dl npi-dl-alt sm" '+
        'href="'+esc(download)+'?fmt=encounters" download>⤓ Encounters '+
        'roll-up (.csv)</a></p>';
    }
    if(pop.conditions){
      var c0=pop.conditions;
      h+=secHead("Chronic-condition prevalence",
        (c0.patient_grouping?fmt(c0.patients)+" distinct patients":
         "no patient column — per-row counts")+
        " · CCW-style ICD-10 prefix groups; reporting only, never a flag.",
        "MART · CONDITIONS");
      h+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
        '<th>Condition</th>'+
        '<th class="num">Patients</th><th class="num">Prevalence</th>'+
        '<th class="num">Rows</th></tr></thead><tbody>';
      c0.prevalence.slice(0,12).forEach(function(p){
        h+='<tr><td>'+esc(p.condition)+'</td><td class="num">'+
          fmt(p.patients)+'</td><td class="num">'+pct1(p.pct)+
          '</td><td class="num">'+fmt(p.rows)+'</td></tr>';
      });
      h+='</tbody></table></div>';
      if(c0.multimorbidity){
        var mm=c0.multimorbidity;
        h+='<p class="npi-muted npi-mt-sm">'+
          'Conditions per patient — 0: '+fmt(mm["0"])+' · 1: '+
          fmt(mm["1"])+' · 2: '+fmt(mm["2"])+' · 3+: '+fmt(mm["3+"])+
          '</p>';
      }
    }
    if(pop.volume){
      h+=secHead("Volume integrity (data loss over time)",
        "Rows, charges and patients by service month — a cliff usually "+
        "means a missing extract, not real utilization."+
        (pop.volume.median_observed_pmpm != null
          ? " Median observed PMPM (charges per patient with claims that "+
            "month): "+money(pop.volume.median_observed_pmpm)+"."
          : ""),
        "MART · VOLUME");
      (pop.volume.alerts||[]).forEach(function(a){
        h+='<div class="npi-warn">'+esc(a)+'</div>';
      });
      var months=pop.volume.months||[];
      var shown=months.slice(-36);
      var maxR=1, peak=null;
      shown.forEach(function(m){
        if(m.rows>maxR) maxR=m.rows;
        if(!peak || m.rows>peak.rows) peak=m;
      });
      h+='<div class="npi-vbar" role="img" aria-label="Rows by service month">';
      shown.forEach(function(m){
        var pct=Math.max(3, Math.round(100*m.rows/maxR));
        h+='<i data-h="'+pct+'"'+(peak && m.month===peak.month?' class="peak"':'')+
          ' title="'+esc(m.month)+': '+fmt(m.rows)+' rows"></i>';
      });
      h+='</div><div class="npi-vbar-cap">'+
        '<span>'+esc(shown.length?shown[0].month:"")+'</span>'+
        (peak?'<span class="pk">peak '+esc(peak.month)+' · '+
          fmt(peak.rows)+' rows</span>':'')+
        '<span>'+esc(shown.length?shown[shown.length-1].month:"")+'</span>'+
        '</div>';
    }
    if(pop.coding_intensity){
      var ci=pop.coding_intensity;
      h+=secHead("E&amp;M coding intensity",
        fmt(ci.established_visits)+" established office visits "+
        "(99211–99215) · file average level "+esc(ci.file_avg_level)+
        " · "+fmt(ci.providers_rated)+" providers with ≥ 20 visits rated "+
        "against the file's own mix.",
        "MART · CODING");
      if(ci.outliers && ci.outliers.length){
        h+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
          '<th>Billing NPI</th>'+
          '<th class="num">Visits</th><th class="num">Avg level</th>'+
          '<th class="num">Level 4–5 share</th></tr></thead><tbody>';
        ci.outliers.forEach(function(o){
          h+='<tr><td>'+esc(o.npi)+'</td><td class="num">'+fmt(o.visits)+
            '</td><td class="num">'+esc(o.avg_level)+
            '</td><td class="num">'+pct1(o.level_4_5_pct)+'</td></tr>';
        });
        h+='</tbody></table></div><p class="npi-muted">'+
          'High-intensity coders vs this file’s mix — '+
          'a documentation-review starting point, not an accusation.</p>';
      } else {
        h+='<section class="ck-affirm-empty"><h3>No hot coders in this '+
          'file.</h3><p>No provider codes materially hotter than the '+
          'file’s own E&amp;M mix — nothing to send to documentation '+
          'review.</p></section>';
      }
    }
    box.innerHTML = h || emptyCard('◔','Not enough claim columns for any mart.',
      'Population marts need service/claim columns — revenue code, type of '+
      'bill, POS, HCPCS, patient id, service dates or diagnoses.');
    applyBars(box);
  }

  function renderSuggestions(adv){
    var box=$("npi-suggestions");
    if(!adv || !adv.suggestions_sample || !adv.suggestions_sample.length){
      box.innerHTML=""; return; }
    var recs=adv.suggestions_sample, cols=Object.keys(recs[0]);
    var html=secHead('Suggested corrections',
      'Showing '+recs.length+' of '+fmt(adv.suggestions_n)+
      ' — full list in the corrections companion (Downloads tab).',
      'FIXABLE · CURRENT → SUGGESTED', adv.suggestions_n)+
      '<div class="npi-scroll"><table class="npi-tbl"><thead><tr>';
    cols.forEach(function(c){ html+='<th>'+esc(c.replace(/_/g," "))+'</th>'; });
    html+='</tr></thead><tbody>';
    recs.forEach(function(r){
      html+='<tr>';
      cols.forEach(function(c){ html+='<td>'+esc(r[c])+'</td>'; });
      html+='</tr>';
    });
    html+='</tbody></table></div>';
    box.innerHTML=html;
  }

  function renderCompliance(comp){
    var box=$("npi-compliance");
    if(!comp || !comp.length){ box.innerHTML=""; return; }
    var html=secHead('Compliance screening', null, 'SCREENS · EXCLUSIONS');
    comp.forEach(function(c){
      if(!c.label){ return; }
      var flag=(c.excluded>0)||(c.opted_out>0);
      html+='<div class="npi-conn"><div class="top">'+
        '<span class="nm">'+esc(c.label)+'</span>';
      if(c.id==="oig_leie"){
        html+='<span class="cnt'+(c.excluded>0?' bad':'')+'">'+
          (c.available?(fmt(c.excluded)+' excluded'):'not loaded')+'</span>';
      } else {
        html+='<span class="cnt'+(flag?' bad':'')+'">'+
          (c.available?(fmt(c.checked)+' screened'):'offline')+'</span>';
      }
      html+='</div><div class="src">'+esc(c.source||"")+'</div>';
      if(c.matches && c.matches.length){
        html+='<div class="nt bad">Excluded NPIs: '+
          c.matches.slice(0,8).map(function(m){return esc(m.npi);}).join(", ")+'</div>';
      }
      // PECOS per-NPI enrollment/opt-out verdicts — fetched all along,
      // now shown: enrollment gaps and opt-outs are the actionable rows.
      if(c.rows && c.rows.length){
        html+='<div class="npi-scroll"><table class="npi-tbl"><thead><tr>'+
          '<th>Billing NPI</th><th>Enrolled</th><th>Provider type</th>'+
          '<th>Opted out</th></tr></thead><tbody>';
        c.rows.forEach(function(rw){
          var bad=!rw.enrolled||rw.opted_out;
          html+='<tr><td class="'+(bad?'billing':'')+'">'+esc(rw.npi)+
            '</td><td><span class="npi-sig '+(rw.enrolled?'':'bad')+'">'+
            (rw.enrolled?'yes':'no')+'</span></td><td>'+
            esc(rw.provider_type||'')+'</td><td>'+
            (rw.opted_out?'<span class="npi-sig bad">yes</span>':'no')+
            '</td></tr>';
        });
        html+='</tbody></table></div>';
      }
      html+='<div class="nt">'+esc(c.note||"")+'</div></div>';
    });
    box.innerHTML=html;
  }

  // Ordering / referring provider eligibility — a claim denies when that
  // provider isn't active/enrolled, so it gets its own line, separate from
  // the billing NPI screens.
  function renderOrderReferring(o){
    var box=$("npi-order-referring");
    if(!box) return;
    if(!o || (o.checked==null && !o.error && !o.note)){ box.innerHTML=""; return; }
    var cols=(o.columns||[]).map(esc).join(", ");
    var html=secHead('Ordering / referring provider eligibility');
    if(o.error){ box.innerHTML=html+'<div class="npi-err">'+esc(o.error)+
      '</div>'; return; }
    var bad=(o.not_found||0);
    html+='<div class="npi-conn"><div class="top">'+
      '<span class="nm">'+(cols||'Ordering/referring NPI')+'</span>'+
      '<span class="cnt'+(bad?' bad':'')+'">'+fmt(o.active||0)+' active · '+
      fmt(bad)+' not found</span></div>'+
      '<div class="nt">'+esc(o.note||('Checked '+fmt(o.checked||0)+
      ' distinct ordering/referring NPIs against NPPES.'))+'</div></div>';
    box.innerHTML=html;
  }

  // NB: the output div is npi-deep-out — id "npi-deep" belongs to the
  // upload-stage checkbox, and getElementById on the old duplicate id
  // silently resolved to that checkbox, so deep results never rendered.
  function renderDeep(deep, dl, wbName){
    var box=$("npi-deep-out");
    if(!deep){ box.innerHTML=""; return; }
    var html='<div class="npi-conn"><div class="top">'+
      '<span class="nm">Deep recovery — full v49 pipeline</span>'+
      (deep.ok?'<span class="npi-chip tone-positive">completed</span>':'')+
      '</div>';
    if(deep.ok){
      html+='<div class="nt ok">Completed. '+
        (deep.stats&&Object.keys(deep.stats).length?
        Object.keys(deep.stats).length+' pipeline stats produced.':'')+'</div>';
      if(wbName){
        html+='<p class="npi-mt-sm"><a class="npi-dl sm" href="'+dl+
          '?fmt=deep" download="'+esc(wbName)+
          '">⤓ Download recovered workbook (.xlsx)</a></p>';
      }
    } else {
      html+='<div class="npi-warn">'+esc(deep.error||
        "Deep recovery did not complete.")+'</div>';
    }
    html+='</div>';
    box.innerHTML=html;
  }

  // Connector coverage plan — the engine decides, per file, which of its
  // ~20 public-data connectors actually apply (a claims-only file with no
  // drug columns won't touch RxNorm/openFDA). Rendering the full roster with
  // an explicit apply/idle verdict + reason turns "2 of 20 ran" from looking
  // broken into a legible explanation of exactly which sources fire and why.
  var PLAN_MODE={offline:"offline pass", network:"live network",
    deep:"deep pipeline"};
  function renderConnectorPlan(plan){
    var box=$("npi-conn-plan");
    if(!box){ return; }
    if(!plan || !plan.length){ box.innerHTML=""; return; }
    var applies=plan.filter(function(c){ return c && c.applies; }).length;
    var html='<div class="npi-plan"><div class="npi-plan-head">'+
      '<span class="t">Connector coverage for this file</span>'+
      '<span class="n"><b>'+fmt(applies)+'</b> of '+fmt(plan.length)+
      ' apply</span></div>';
    plan.forEach(function(c){
      c=c||{};
      var on=!!c.applies;
      var mode=PLAN_MODE[c.mode]||c.mode||"";
      var chip=on
        ? '<span class="npi-chip dot on">will run'+(mode?' · '+esc(mode):'')+'</span>'
        : '<span class="npi-chip dot off">not applicable</span>';
      html+='<div class="npi-plan-row'+(on?'':' idle')+'">'+
        '<span class="nm">'+esc(c.name||c.id||"")+'</span>'+chip+
        '<span class="rs">'+esc(c.reason||"")+'</span></div>';
    });
    html+='</div>';
    box.innerHTML=html;
  }

  function renderConnectors(conns){
    var box=$("npi-connectors");
    if(!conns || !conns.length){ box.innerHTML=""; return; }
    var html=secHead('Drug connectors (RxNorm · openFDA)');
    conns.forEach(function(c){
      if(!c.label){ return; }
      html+='<div class="npi-conn"><div class="top">'+
        '<span class="nm">'+esc(c.label)+'</span>'+
        '<span class="cnt">'+fmt(c.resolved||0)+' / '+fmt(c.queried||0)+' resolved</span>'+
        '</div><div class="src">'+esc(c.source||"")+'</div>';
      if(c.sample && c.sample.length){
        html+='<div class="nt">';
        c.sample.slice(0,6).forEach(function(s){
          if(s.rxcui!=null){
            html+='• '+esc(s.input)+' <span class="arrow">→</span> RxCUI '+
              '<code>'+esc(s.rxcui)+'</code> '+esc(s.name)+'<br>';
          } else {
            html+='• '+esc(s.ndc)+' <span class="arrow">→</span> '+
              esc(s.brand||s.generic)+' <span class="rowref">('+esc(s.labeler)+')</span><br>';
          }
        });
        html+='</div>';
      }
      html+='<div class="nt">'+esc(c.note||"")+'</div></div>';
    });
    box.innerHTML=html;
  }

  function renderCatalog(cat){
    var box=$("npi-catalog");
    if(!cat || !cat.length){ box.innerHTML=""; return; }
    var wired=cat.filter(function(s){ return s.cleaning_wired; }).length;
    var html=secHead('Connections available',
      '<strong>'+wired+'</strong> source'+
      (wired===1?"":"s")+' act on a cleaning run (enrich / deep / '+
      'reference packs); the other '+(cat.length-wired)+' are reachable '+
      'elsewhere in PE&nbsp;Desk and can be wired here on request '+
      '(use the "missing something?" card).',
      'PLATFORM · PUBLIC-DATA ESTATE', cat.length)+'<div class="npi-cat">';
    cat.forEach(function(s){
      var free=(s.cost||"").indexOf("free")===0;
      var badge=s.cleaning_wired
        ? '<span class="npi-badge">wired for cleaning</span>'
        : '';
      var doc=s.docs_url
        ? ' · <a href="'+esc(s.docs_url)+'" target="_blank" '+
          'rel="noopener">docs</a>'
        : '';
      html+='<div class="c'+(s.cleaning_wired?' on':'')+'">'+
        '<div class="n">'+esc(s.name)+badge+'</div>'+
        '<div class="o">'+esc(s.operator||"")+
        ' · <span class="'+(free?"free":"")+'">'+esc(s.cost||"")+
        '</span>'+doc+'</div></div>';
    });
    html+='</div>';
    box.innerHTML=html;
  }

  function toggleDrill(d){
    var ix=d.getAttribute("data-drill");
    var rows=document.querySelector('[data-drillrows="'+ix+'"]');
    if(rows){
      rows.classList.toggle("npi-hidden");
      var open=!rows.classList.contains("npi-hidden");
      d.classList.toggle("open", open);
      d.setAttribute("aria-expanded", open?"true":"false");
    }
  }
  function initTabs(){
    if(window.__npiTabsInit) return; window.__npiTabsInit=true;
    document.addEventListener("click", function(e){
      if(!e.target.closest) return;
      var t=e.target.closest(".npi-tab");
      if(t){ selectTab(t.getAttribute("data-tab")); return; }
      // Drill-down: clicking an issue row toggles its offending-rows table.
      var d=e.target.closest(".npi-drill");
      if(d){ toggleDrill(d); }
    });
    // Keyboard: arrow-key tab navigation + Enter/Space drill toggling.
    document.addEventListener("keydown", function(e){
      if(!e.target.closest) return;
      var t=e.target.closest(".npi-tab");
      if(t && (e.key==="ArrowRight"||e.key==="ArrowLeft"||
               e.key==="Home"||e.key==="End")){
        var tabs=Array.prototype.slice.call(
          document.querySelectorAll(".npi-tab"));
        var i=tabs.indexOf(t);
        var j=e.key==="ArrowRight"?(i+1)%tabs.length:
              e.key==="ArrowLeft"?(i-1+tabs.length)%tabs.length:
              e.key==="Home"?0:tabs.length-1;
        e.preventDefault();
        selectTab(tabs[j].getAttribute("data-tab"));
        tabs[j].focus();
        return;
      }
      var d=e.target.closest(".npi-drill");
      if(d && (e.key==="Enter"||e.key===" ")){
        e.preventDefault(); toggleDrill(d);
      }
    });
  }

  // ---- 837↔835 reconciliation: remember recent runs in THIS browser so
  // a claims run can be matched against its remittance run by claim id.
  function recentJobs(){
    try{ return JSON.parse(localStorage.getItem("npi_recent_jobs"))||[]; }
    catch(e){ return []; }
  }
  function rememberJob(id, name){
    if(!id) return;
    var list=recentJobs().filter(function(j){ return j.id!==id; });
    list.unshift({id:id, name:name||"run", ts:Date.now()});
    try{ localStorage.setItem("npi_recent_jobs",
      JSON.stringify(list.slice(0,10))); }catch(e){}
  }
  function renderReconcile(s){
    var box=$("npi-reconcile");
    var others=recentJobs().filter(function(j){ return j.id!==currentJobId; });
    if(!others.length){
      box.innerHTML=emptyCard('⇄','Nothing to reconcile yet.',
        'Clean the matching remittance (835) or claims (837) file next '+
        'and a reconcile option will appear here — unpaid claims, '+
        'paid-vs-billed variance, denial mix.');
      return;
    }
    var isRemit=(s.delimiter||"").indexOf("835")>=0;
    box.innerHTML=secHead('Reconcile against an earlier run',
      'Match claims to remittance on claim id: '+
      'unpaid claims, paid-vs-billed variance, denial mix.',
      'MATCH · 837 ↔ 835')+
      '<div class="npi-recform">'+
      '<select id="npi-rec-other" class="npi-select" '+
      'aria-label="Earlier run to reconcile against">'+
      others.map(function(j){
        return '<option value="'+esc(j.id)+'">'+esc(j.name)+'</option>';
      }).join("")+'</select> '+
      '<label class="npi-muted">'+
      '<input type="checkbox" id="npi-rec-remit"'+(isRemit?' checked':'')+
      '> this run is the remittance (835) side</label> '+
      '<button type="button" class="npi-dl sm" id="npi-rec-go">'+
      'Reconcile</button></div><div id="npi-rec-out" '+
      'class="npi-mt-sm"></div>';
    $("npi-rec-go").addEventListener("click", function(){
      var other=$("npi-rec-other").value;
      var thisIsRemit=$("npi-rec-remit").checked;
      var body=thisIsRemit?{a:other, b:currentJobId}
                          :{a:currentJobId, b:other};
      $("npi-rec-out").innerHTML='<p class="npi-muted">Matching…</p>';
      fetch("/npi-cleaner/api/reconcile", {method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(body)})
      .then(function(r){ return r.json(); })
      .then(renderReconResult)
      .catch(function(){ $("npi-rec-out").innerHTML=
        '<div class="npi-err">Reconcile failed.</div>'; });
    });
  }
  function renderReconResult(r){
    var out=$("npi-rec-out");
    if(r.error){ out.innerHTML='<div class="npi-err">'+esc(r.error)+
      '</div>'; return; }
    var h='<p class="npi-muted"><strong>'+
      fmt(r.matched)+'</strong> of '+fmt(r.claims_a)+' claims matched ('+
      pct1(r.match_rate_pct)+') · <strong>'+fmt(r.unpaid_count)+
      '</strong> with no remittance · billed '+money(r.billed_matched)+
      ' vs paid '+money(r.paid_matched)+' on matched claims (variance '+
      money(r.variance_total)+')'+
      (r.orphan_remits_count?(' · '+fmt(r.orphan_remits_count)+
      ' remit claim(s) not in the claims run'):'')+'</p>';
    if(r.unpaid && r.unpaid.length){
      h+='<h4 class="npi-subhd">'+
        'Claims with no remittance (top by billed)</h4>'+
        '<div class="npi-scroll"><table class="npi-tbl"><thead><tr><th>Claim</th>'+
        '<th class="num">Billed</th><th class="num">Lines</th></tr></thead>'+
        '<tbody>'+r.unpaid.slice(0,8).map(function(u){
          return '<tr><td>'+esc(u.claim)+'</td><td class="num">'+
            money(u.billed)+'</td><td class="num">'+fmt(u.lines)+'</td></tr>';
        }).join("")+'</tbody></table></div>';
    }
    if(r.top_variance && r.top_variance.length){
      h+='<h4 class="npi-subhd">'+
        'Largest paid-vs-billed variance (matched claims)</h4>'+
        '<div class="npi-scroll"><table class="npi-tbl"><thead><tr><th>Claim</th>'+
        '<th class="num">Billed</th><th class="num">Paid</th>'+
        '<th class="num">Δ</th><th>CARCs</th></tr></thead><tbody>'+
        r.top_variance.slice(0,8).map(function(v){
          return '<tr><td>'+esc(v.claim)+'</td><td class="num">'+
            money(v.billed)+'</td><td class="num">'+money(v.paid)+
            '</td><td class="num">'+money(v.delta)+'</td><td>'+
            (v.carcs||[]).map(esc).join(", ")+'</td></tr>';
        }).join("")+'</tbody></table></div>';
    }
    if(r.denials && r.denials.length){
      h+='<h4 class="npi-subhd">'+
        'Denial mix (remit side)</h4><div class="npi-mt-sm">'+
        r.denials.map(function(d){
          return '<span class="npi-pill blk" title="'+esc(d.action||"")+'">'+
            esc(d.code)+' · '+fmt(d.claims)+
            (d.category?(' ('+esc(d.category)+')'):'')+'</span>';
        }).join("")+'</div>';
    }
    out.innerHTML=h;
  }

  function fmtDur(s){
    if(s == null || s < 0) return "";
    if(s < 90) return Math.max(1, Math.round(s))+"s";
    if(s < 5400) return Math.round(s/60)+" min";
    return Math.floor(s/3600)+"h "+Math.round((s%3600)/60)+"m";
  }

  function watch(jobId){
    currentJobId=jobId;
    show($("npi-cancel"));
    poll=setInterval(function(){
      fetch("/npi-cleaner/status/"+jobId, {headers:{"Accept":"application/json"}})
        .then(function(r){ return r.json(); })
        .then(function(j){
          if(j.error){ hide($("npi-cancel")); fail(j.error); return; }
          var pctDone=Math.round((j.frac||0)*100);
          $("npi-bar-fill").style.width=pctDone+"%";
          var barEl=$("npi-bar");
          if(barEl){ barEl.setAttribute("aria-valuenow", pctDone); }
          $("npi-bar-msg").textContent=(j.msg||"Working")+" — "+pctDone+"%";
          $("npi-bar-eta").textContent = (j.eta_secs != null)
            ? "elapsed "+fmtDur(j.elapsed_secs)+
              " · about "+fmtDur(j.eta_secs)+" remaining"
            : "";
          if(j.done){
            clearInterval(poll); poll=null;
            hide($("npi-cancel"));
            $("npi-bar-eta").textContent="";
            if(j.scorecard){ render(Object.assign(j.scorecard,{download:j.download})); }
            else { fail("Cleaning finished without a result."); }
          }
        })
        .catch(function(e){ fail("Lost connection to the server."); });
    }, 400);
  }
  $("npi-cancel").addEventListener("click", function(){
    if(!currentJobId) return;
    var btn=this; btn.disabled=true;
    fetch("/npi-cleaner/cancel/"+currentJobId, {method:"POST"})
      .then(function(r){ return r.json(); })
      .then(function(){ btn.disabled=false; })
      .catch(function(){ btn.disabled=false; });
  });

  // Step 1 — a file is chosen: detect columns, then show the mapping editor.
  function chooseFile(file){
    if(!file) return;
    if(file.size > 10*1000*1000*1000){
      fail("File is larger than 10 GB. Split the extract and upload the "+
           "pieces, or run it through the rcm-mc npi-clean CLI."); return; }
    currentFile=file;
    hide(stUp); hide(stErr); hide(stRes); show(stPr);
    // Above the detect ceiling the server cleans in streaming chunks and
    // the column preview can't parse the body — skip the mapping step and
    // go straight to the (long-running) clean.
    if(file.size > 200*1000*1000){ upload(file, {}); return; }
    $("npi-bar-fill").style.width="3%";
    $("npi-bar-msg").textContent="Reading columns from "+file.name+"…";
    fetch("/npi-cleaner/detect", {
      method:"POST", headers:{"X-Filename":encodeURIComponent(file.name)},
      body:file
    })
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(!j || !j.available || !j.headers){ upload(file, {}); return; }
      renderMapping(file, j);
      $("npi-map-tpl-msg").textContent="";
      $("npi-map-tpl").value="";
      loadMapTemplates();
      hide(stPr); show(stMap);
    })
    .catch(function(){ upload(file, {}); });  // detector down → clean directly
  }

  function renderMapping(file, det){
    detectRoles = det.roles || [];
    $("npi-map-file").textContent =
      file.name+(det.sheet?" — sheet “"+det.sheet+"”":"")+
      " — "+det.headers.length+" columns detected. Adjust any the "+
      "auto-mapper got wrong, then clean.";
    var opts = '<option value="">(auto / none)</option>' +
      det.headers.map(function(h){
        return '<option value="'+encodeURIComponent(h)+'">'+
          esc(h)+'</option>'; }).join("");
    var html="";
    detectRoles.forEach(function(role){
      var cur = det.mapping[role.key] || "";
      html+='<div class="row'+(cur?' set':'')+'" data-role="'+esc(role.key)+'">'+
        '<label>'+esc(role.label)+'</label>'+
        '<select class="'+(cur?'':'auto')+'">'+opts+'</select></div>';
    });
    $("npi-map-grid").innerHTML=html;
    // Pre-select detected values.
    detectRoles.forEach(function(role){
      var cur = det.mapping[role.key] || "";
      var sel = $("npi-map-grid").querySelector('[data-role="'+role.key+'"] select');
      if(sel && cur){ sel.value=encodeURIComponent(cur); }
    });
  }

  function gatherOverrides(){
    var ov={};
    $("npi-map-grid").querySelectorAll(".row").forEach(function(row){
      var key=row.getAttribute("data-role");
      var sel=row.querySelector("select");
      if(sel && sel.value){ ov[key]=decodeURIComponent(sel.value); }
    });
    return ov;
  }

  // ---- Mapping templates: map a source system once, reuse per upload ----
  var MAPTPLS=[];
  function loadMapTemplates(){
    fetch("/npi-cleaner/api/mappings").then(function(r){ return r.json(); })
      .then(function(j){
        MAPTPLS=j.mappings||[];
        var sel=$("npi-map-tpl"); if(!sel) return;
        sel.innerHTML='<option value="">(none)</option>'+
          MAPTPLS.map(function(m){
            return '<option value="'+esc(m.name)+'">'+esc(m.name)+
              ' ('+m.roles+' roles)</option>'; }).join("");
      }).catch(function(){});
  }
  function applyMapTemplate(name){
    var tpl=null;
    MAPTPLS.forEach(function(m){ if(m.name===name) tpl=m; });
    if(!tpl) return;
    var applied=0;
    Object.keys(tpl.mapping).forEach(function(role){
      var row=$("npi-map-grid").querySelector('[data-role="'+role+'"]');
      if(!row) return;                         // role not in this detector
      var sel=row.querySelector("select");
      var want=encodeURIComponent(tpl.mapping[role]);
      for(var i=0;i<sel.options.length;i++){
        if(sel.options[i].value===want){ sel.value=want; applied++; break; }
      }                                        // header absent → left as-is
    });
    $("npi-map-tpl-msg").textContent=applied+
      " column"+(applied===1?"":"s")+" applied from “"+name+"”.";
  }
  $("npi-map-tpl").addEventListener("change", function(){
    if(this.value) applyMapTemplate(this.value);
  });
  $("npi-map-tpl-save").addEventListener("click", function(){
    var name=$("npi-map-tpl-name").value.trim();
    var msg=$("npi-map-tpl-msg");
    if(!name){ msg.textContent="Name the template first."; return; }
    var ov=gatherOverrides();
    if(!Object.keys(ov).length){
      msg.textContent="Pick at least one column before saving."; return; }
    fetch("/npi-cleaner/api/mappings", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:name, mapping:ov})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ msg.textContent=j.error; return; }
      msg.textContent="Saved “"+name+"”.";
      loadMapTemplates();
    })
    .catch(function(){ msg.textContent="Save failed."; });
  });

  // Step 2 — clean the held file with the confirmed overrides.
  function upload(file, overrides){
    if(!file) return;
    hide(stUp); hide(stMap); hide(stErr); hide(stRes); show(stPr);
    $("npi-bar-fill").style.width="5%";
    $("npi-bar-msg").textContent = (file.size > 200*1000*1000)
      ? "Uploading "+file.name+" ("+(file.size/1e9).toFixed(1)+" GB — "+
        "streaming mode; a multi-GB file can take hours. Keep this tab "+
        "open or note the URL; the job keeps running on the server)…"
      : "Uploading "+file.name+"…";
    var params=[];
    if(!$("npi-dedupe").checked) params.push("dedupe=0");
    if($("npi-enrich").checked) params.push("enrich=1");
    if($("npi-deep").checked) params.push("deep=1");
    if($("npi-deid").checked) params.push("deid=1");
    var qs = params.length ? "?"+params.join("&") : "";
    var headers={"X-Filename":encodeURIComponent(file.name)};
    var profSel=$("npi-profile");
    if(profSel && profSel.value){
      headers["X-Profile"]=encodeURIComponent(profSel.value); }
    if(overrides && Object.keys(overrides).length){
      headers["X-Overrides"]=encodeURIComponent(JSON.stringify(overrides));
    }
    fetch("/npi-cleaner/upload"+qs, {method:"POST", headers:headers, body:file})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ fail(j.error); return; }
      if(!j.job_id){ fail("Upload did not return a job id."); return; }
      watch(j.job_id);
    })
    .catch(function(e){ fail("Upload failed. Is the file under 10 GB, and "+
      "is the connection stable enough to send it?"); });
  }

  // ---- Wishlist: "missing something? tell us and we'll fill it in" ----
  function loadWishlist(){
    fetch("/npi-cleaner/api/wishlist").then(function(r){ return r.json(); })
      .then(function(j){
        var box=$("npi-wish-list"); if(!box) return;
        var reqs=j.requests||[];
        if(!reqs.length){ box.innerHTML=""; return; }
        var chip=function(s){
          var tone=s==="shipped"?"positive":s==="planned"?"warning":
                   s==="declined"?"":"accent";
          return '<span class="npi-chip'+(tone?' tone-'+tone:'')+'">'+
            esc(s)+'</span>'; };
        box.innerHTML=
          '<h4 class="npi-wish-hd">Requested ('+reqs.length+')</h4>'+
          reqs.slice(0,8).map(function(q){
            return '<div class="npi-wish-row">'+
              '<span class="npi-muted">['+esc(q.category)+']</span> '+
              esc(q.title)+' — '+chip(q.status)+'</div>';
          }).join("")+
          (reqs.length>8
            ? '<p class="npi-fine npi-mt-sm">…and '+(reqs.length-8)+' more</p>'
            : '');
      }).catch(function(){});
  }
  $("npi-wish-add").addEventListener("click", function(){
    var t=$("npi-wish-title").value.trim(), msg=$("npi-wish-msg");
    if(!t){ msg.textContent="Give the request a one-line summary first.";
            return; }
    fetch("/npi-cleaner/api/wishlist", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({category:$("npi-wish-cat").value, title:t,
                           details:$("npi-wish-details").value})})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(j.error){ msg.textContent=j.error; return; }
      msg.textContent="Logged — it’s on the build backlog.";
      $("npi-wish-title").value=""; $("npi-wish-details").value="";
      loadWishlist();
    })
    .catch(function(){ msg.textContent="Could not reach the server."; });
  });
  loadWishlist();

  // ---- Reference data packs: status + one-click pulls ----
  var refdataTimer=null;
  function loadRefdata(){
    fetch("/npi-cleaner/api/refdata").then(function(r){ return r.json(); })
      .then(function(j){
        var box=$("npi-refdata-list"); if(!box) return;
        var packs=j.packs||[];
        var pulling=false;
        var h='<div class="npi-scroll"><table class="npi-tbl"><thead><tr><th>Pack</th>'+
          '<th>Status</th><th>Enables</th><th></th></tr></thead><tbody>';
        packs.forEach(function(p){
          var st;
          if(p.pull && p.pull.state==="pulling"){
            st='<span class="npi-sig warn">pulling… </span>'; pulling=true;
          } else if(p.pull && p.pull.state==="error"){
            st='<span class="npi-sig bad" title="'+esc(p.pull.note)+
               '">pull failed</span>';
          } else if(p.installed){
            var d=p.fetched?new Date(p.fetched*1000)
              .toISOString().slice(0,10):"";
            st='<span class="npi-sig ok">'+fmt(p.rows)+' rows · '+
               esc(d)+'</span>';
          } else {
            st='<span class="npi-muted">not installed</span>';
          }
          h+='<tr><td><strong>'+esc(p.title)+'</strong><br>'+
            '<span class="npi-fine">'+esc(p.license)+'</span></td>'+
            '<td>'+st+'</td>'+
            '<td class="npi-cell-sm">'+esc(p.enables)+'</td>'+
            '<td><button class="npi-again npi-ref-pull" data-pack="'+
            esc(p.id)+'">'+(p.installed?"Refresh":"Pull")+
            '</button></td></tr>';
        });
        h+='</tbody></table></div>'+
          '<p class="npi-mt-sm"><button class="npi-again" '+
          'id="npi-ref-pull-all">Pull everything</button></p>';
        box.innerHTML=h;
        function startPull(pack){
          fetch("/npi-cleaner/api/refdata/pull", {method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({pack:pack})})
          .then(function(){ loadRefdata(); }).catch(function(){});
        }
        box.querySelectorAll(".npi-ref-pull").forEach(function(btn){
          btn.addEventListener("click", function(){
            startPull(this.getAttribute("data-pack")); });
        });
        var allBtn=$("npi-ref-pull-all");
        if(allBtn){ allBtn.addEventListener("click", function(){
          startPull("all"); }); }
        if(refdataTimer){ clearTimeout(refdataTimer); refdataTimer=null; }
        if(pulling){ refdataTimer=setTimeout(loadRefdata, 2500); }
      }).catch(function(){});
  }
  loadRefdata();

  initTabs();
  drop.addEventListener("click", function(){ fileIn.click(); });
  drop.addEventListener("keydown", function(e){
    if(e.key==="Enter"||e.key===" "){ e.preventDefault(); fileIn.click(); } });
  fileIn.addEventListener("change", function(){ chooseFile(fileIn.files[0]); });
  // ---- Cleaning profiles ----
  function loadProfiles(){
    fetch("/npi-cleaner/api/profiles").then(function(r){return r.json();})
      .then(function(j){
        var sel=$("npi-profile"); if(!sel) return;
        var cur=sel.value;
        sel.innerHTML='<option value="">(default rules)</option>'+
          (j.profiles||[]).map(function(p){
            return '<option value="'+esc(p.name)+'">'+esc(p.name)+'</option>';
          }).join("");
        sel.value=cur;
      }).catch(function(){});
  }
  function buildProfRules(){
    fetch("/npi-cleaner/api/rules").then(function(r){return r.json();})
      .then(function(j){
        var flags=(j.rules||[]).filter(function(r){return r.kind==="flag";});
        $("npi-prof-rules").innerHTML=flags.map(function(r){
          return '<div class="r" title="'+esc(r.description)+'">'+
            '<select data-rule="'+esc(r.id)+'" class="npi-select xs" '+
            'aria-label="'+esc(r.title)+'">'+
            '<option value="on">on</option>'+
            '<option value="accepted">accepted</option>'+
            '<option value="off">off</option></select> '+
            esc(r.title)+'</div>';
        }).join("");
      }).catch(function(){});
  }
  var pbtn=$("npi-profile-new");
  if(pbtn){ pbtn.addEventListener("click", function(){
    var ed=$("npi-profile-editor");
    ed.classList.toggle("npi-hidden");
    if(!ed.classList.contains("npi-hidden") &&
       !$("npi-prof-rules").innerHTML){ buildProfRules(); }
  }); }
  var pclose=$("npi-prof-close");
  if(pclose){ pclose.addEventListener("click", function(){
    $("npi-profile-editor").classList.add("npi-hidden"); }); }
  var psave=$("npi-prof-save");
  if(psave){ psave.addEventListener("click", function(){
    var name=($("npi-prof-name").value||"").trim();
    if(!name){ $("npi-prof-msg").textContent="Give the profile a name."; return; }
    var disabled=[], accepted=[];
    $("npi-prof-rules").querySelectorAll("select[data-rule]").forEach(function(s){
      if(s.value==="off") disabled.push(s.getAttribute("data-rule"));
      if(s.value==="accepted") accepted.push(s.getAttribute("data-rule"));
    });
    var cfg={disabled_rules:disabled, accepted_rules:accepted,
      thresholds:{timely_filing_days:parseInt($("npi-prof-timely").value,10)||365,
                  stale_years:parseInt($("npi-prof-stale").value,10)||10,
                  outlier_iqr_mult:parseFloat($("npi-prof-iqr").value)||3,
                  dup_window_days:parseInt($("npi-prof-dupwin").value,10)||3}};
    fetch("/npi-cleaner/api/profiles", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:name, config:cfg})})
      .then(function(r){return r.json();})
      .then(function(j){
        $("npi-prof-msg").textContent = j.ok ?
          ('Saved "'+name+'" — select it above for the next upload.') :
          (j.error||"Save failed.");
        loadProfiles();
        var sel=$("npi-profile"); if(sel && j.ok){ sel.value=name; }
      }).catch(function(){ $("npi-prof-msg").textContent="Save failed."; });
  }); }
  var pimp=$("npi-prof-import"), pimpFile=$("npi-prof-import-file");
  if(pimp && pimpFile){
    pimp.addEventListener("click", function(){ pimpFile.click(); });
    pimpFile.addEventListener("change", function(){
      var f=pimpFile.files[0]; if(!f) return;
      var rd=new FileReader();
      rd.onload=function(){
        var body;
        try{ body=JSON.parse(rd.result); }
        catch(e){ $("npi-prof-msg").textContent="Not valid JSON."; return; }
        fetch("/npi-cleaner/api/profiles/import", {method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify(body)})
        .then(function(r){ return r.json(); })
        .then(function(j){
          $("npi-prof-msg").textContent = j.error ? j.error :
            ("Imported "+j.imported+" profile(s)"+
             (j.errors&&j.errors.length?(" · "+j.errors.length+" skipped"):"")+".");
          loadProfiles();
        })
        .catch(function(){ $("npi-prof-msg").textContent="Import failed."; });
        pimpFile.value="";
      };
      rd.readAsText(f);
    });
  }
  loadProfiles();

  ["dragenter","dragover"].forEach(function(ev){
    drop.addEventListener(ev, function(e){ e.preventDefault();
      drop.classList.add("drag"); }); });
  ["dragleave","drop"].forEach(function(ev){
    drop.addEventListener(ev, function(e){ e.preventDefault();
      drop.classList.remove("drag"); }); });
  drop.addEventListener("drop", function(e){
    var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    chooseFile(f);
  });
  $("npi-map-clean").addEventListener("click", function(){
    upload(currentFile, gatherOverrides()); });
  $("npi-map-cancel").addEventListener("click", reset);
  $("npi-again").addEventListener("click", reset);
  $("npi-err-again").addEventListener("click", reset);
})();
"""


def render_npi_cleaner() -> str:
    """Full HTML for GET /npi-cleaner."""
    return chartis_shell(
        _body(),
        title="NPI Claims Cleaner",
        active_nav="TOOLS",
        breadcrumbs=[("Tools", None), ("NPI Cleaner", None)],
        extra_css=_EXTRA_CSS,
        extra_js=_EXTRA_JS,
    )
