"""UI for the V2 healthcare snapshot ingestion tab.

Two server-rendered pages, both through ``chartis_shell`` so they match
the rest of the app:

- :func:`render_snapshot_upload` — the editorial upload surface (a
  drag-and-drop VDR dropzone with client-side size pre-checks and a
  processing state) plus the mandatory PHI warning.
- :func:`render_snapshot_result` — Data Confidence Score, KPI tiles,
  impact-ranked findings, and the Markdown memo with copy/download
  affordances. Renders **aggregates only** — no patient-level data
  ever reaches this surface (the SnapshotResult is already PHI-safe).

Typeset in the v5 chartis editorial language: ``ck_editorial_head``
masthead cadence, kit tokens with canonical fallbacks, page-scoped
``.hs-*`` classes (no inline ``style=`` attributes), and the same
dropzone idiom as the NPI Claims Cleaner (``rcm_mc/ui/npi_cleaner_page``).
"""
from __future__ import annotations

import html as _html
import re as _re
import urllib.parse as _urlparse
from typing import TYPE_CHECKING

from ..ui._chartis_kit import (
    chartis_shell,
    ck_affirm_empty,
    ck_arrow_link,
    ck_editorial_head,
    ck_fmt_currency,
    ck_fmt_number,
    ck_kpi_block,
    ck_page_actions,
    ck_provenance_tooltip,
    ck_section_header,
    ck_signal_badge,
)

if TYPE_CHECKING:  # avoid import cost / cycles at module load
    from .snapshot import SnapshotResult

_PHI_WARNING = (
    "Healthcare claims and remittance files may contain PHI. Upload "
    "de-identified data unless appropriate agreements and permissions are "
    "in place. Patient identifiers are tokenized on ingest; outputs are "
    "aggregate-only."
)

# Mirrors the multipart-body cap enforced by server.py:_parse_multipart
# (B146). The dropzone pre-checks File.size against this so a partner
# never has to learn the limit from a raw exception string.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Format chips — grouped families mirroring the ``accept=`` attribute
# below exactly, so the two can never drift apart.
_FORMAT_CHIPS = ("835", "837", "EDI / TXT", "CSV / TSV",
                 "XLSX / XLSM", "PARQUET", "ZIP VDR")
_ACCEPT_ATTR = ".edi,.txt,.835,.837,.csv,.tsv,.xlsx,.xlsm,.parquet,.zip"


# ---------------------------------------------------------------------------
# Page-scoped CSS — kit tokens with canonical fallbacks only.
# ---------------------------------------------------------------------------

_EXTRA_CSS = r"""
/* Local shorthands for the kit type stacks (canonical tokens only). */
.hs-wrap{--mono:var(--sc-mono,'JetBrains Mono',monospace);
  --sans:var(--sc-sans,'Inter Tight',sans-serif);
  --serif:var(--sc-serif,'Source Serif 4',serif);
  max-width:920px;margin:0 auto}
.hs-wrap .ck-section-header{margin:28px 0 10px}
.hs-hidden{display:none !important}
.hs-fine{font-size:11.5px;color:var(--sc-text-faint,#7a8699);
  margin:14px 0 0;line-height:1.55}
/* ============ Toned notice band — PHI / error / neutral ============ */
.hs-note{border:1px solid var(--rule,#c9bf9c);
  border-left:3px solid var(--sc-text-faint,#7a8699);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:12px 16px;margin:0 0 var(--sc-s-5,18px);font-size:13px;
  line-height:1.55;color:var(--ink,#16263a)}
.hs-note .eb{display:block;font-family:var(--mono);font-size:10px;
  font-weight:600;letter-spacing:.13em;text-transform:uppercase;
  margin-bottom:4px;color:var(--sc-text-dim,#465366)}
.hs-note--warning{border-left-color:var(--sc-warning,#b8732a);
  background:color-mix(in srgb,var(--sc-warning,#b8732a) 5%,var(--paper-card,#fefcf3))}
.hs-note--warning .eb{color:var(--sc-warning,#b8732a)}
.hs-note--negative{border-left-color:var(--sc-negative,#b5321e);
  background:color-mix(in srgb,var(--sc-negative,#b5321e) 5%,var(--paper-card,#fefcf3))}
.hs-note--negative .eb{color:var(--sc-negative,#b5321e)}
.hs-note--neutral{border-left-color:var(--green-deep,#154e36)}
.hs-note--neutral .eb{color:var(--green-deep,#154e36)}
/* ============ Upload form card ============ */
.hs-form{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  background:var(--paper-card,#fefcf3);padding:22px 24px;margin-top:4px}
.hs-field{margin-bottom:16px}
.hs-label{display:block;font-size:12px;font-weight:600;
  color:var(--ink,#16263a);margin-bottom:5px;letter-spacing:.02em}
.hs-input{width:100%;max-width:420px;box-sizing:border-box;
  font-family:var(--sans);font-size:13px;padding:8px 10px;
  border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-1,2px);
  background:var(--paper,#ffffff);color:var(--ink,#16263a)}
.hs-input:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:1px}
/* ============ Dropzone — the NPI-cleaner idiom ============ */
.hs-drop{position:relative;
  border:1.5px dashed var(--rule,#c9bf9c);border-radius:6px;
  background:
    radial-gradient(130% 150% at 50% 0%,
      color-mix(in srgb,var(--green-deep,#154e36) 4%,transparent), transparent 58%),
    var(--paper-card,#fefcf3);
  padding:38px 26px;text-align:center;cursor:pointer;
  transition:border-color .16s ease, background .16s ease,
    box-shadow .16s ease, transform .16s ease}
.hs-drop:hover,.hs-drop.drag{border-color:var(--green-deep,#154e36);
  background:
    radial-gradient(130% 150% at 50% 0%,
      color-mix(in srgb,var(--green-deep,#154e36) 9%,transparent), transparent 60%),
    var(--paper-card,#fefcf3);
  box-shadow:0 8px 26px -14px color-mix(in srgb,var(--green-deep,#154e36) 60%,transparent)}
.hs-drop.drag{border-style:solid;transform:translateY(-1px)}
.hs-drop:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:2px}
.hs-drop .cloud{width:54px;height:54px;margin:0 auto 13px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:27px;line-height:1;color:var(--green-deep,#154e36);
  background:color-mix(in srgb,var(--green-deep,#154e36) 11%,transparent);
  transition:transform .16s ease, background .16s ease}
.hs-drop:hover .cloud,.hs-drop.drag .cloud{transform:translateY(-2px);
  background:color-mix(in srgb,var(--green-deep,#154e36) 17%,transparent)}
.hs-drop .big{font-family:var(--serif);font-size:19px;font-weight:600;
  letter-spacing:-.01em;color:var(--ink,#16263a)}
.hs-drop .small{font-size:12.5px;color:var(--sc-text-dim,#465366);
  margin-top:8px;line-height:1.6;max-width:440px;
  margin-left:auto;margin-right:auto}
.hs-drop .pick{color:var(--green-deep,#154e36);text-decoration:underline;
  text-underline-offset:2px;font-weight:600}
.hs-formats{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;
  align-items:center;margin-top:14px;font-size:11.5px;
  color:var(--sc-text-dim,#465366)}
.hs-formats .ck-badge{font-family:var(--mono);font-size:10px;
  letter-spacing:.05em}
/* Native input stays visible without JS (progressive enhancement);
   the enhanced dropzone hides it once the script has bound. */
.hs-native{display:block;margin-top:10px;font-size:12.5px;
  color:var(--sc-text-dim,#465366)}
.hs-js .hs-native{display:none}
/* ============ Selected files + size pre-check ============ */
.hs-file-list{list-style:none;margin:10px 0 0;padding:0}
.hs-file-list li{display:flex;justify-content:space-between;gap:12px;
  align-items:baseline;padding:7px 12px;margin-bottom:6px;font-size:12.5px;
  border:1px solid var(--rule-soft,#ddd1ac);border-radius:var(--sc-r-2,4px);
  background:var(--paper-card,#fefcf3)}
.hs-file-list .nm{font-weight:600;color:var(--ink,#16263a);
  word-break:break-all}
.hs-file-list .sz{font-family:var(--mono);font-size:11.5px;
  color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums;
  white-space:nowrap}
.hs-file-list li.over{
  border-color:color-mix(in srgb,var(--sc-negative,#b5321e) 45%,transparent);
  background:color-mix(in srgb,var(--sc-negative,#b5321e) 5%,var(--paper-card,#fefcf3))}
.hs-file-list li.over .sz{color:var(--sc-negative,#b5321e);font-weight:700}
.hs-size-err{border:1px solid color-mix(in srgb,var(--sc-negative,#b5321e) 35%,transparent);
  border-left:3px solid var(--sc-negative,#b5321e);
  background:color-mix(in srgb,var(--sc-negative,#b5321e) 6%,var(--paper-card,#fefcf3));
  color:color-mix(in srgb,var(--sc-negative,#b5321e) 80%,var(--ink,#16263a));
  border-radius:var(--sc-r-2,4px);padding:10px 14px;font-size:12.5px;
  margin:10px 0 0;line-height:1.5}
/* ============ Submit + processing state ============ */
.hs-actions{display:flex;gap:14px;align-items:center;flex-wrap:wrap;
  margin-top:18px}
.hs-submit{cursor:pointer}
.hs-submit:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:2px}
.hs-submit[disabled]{opacity:.55;cursor:not-allowed}
.hs-drop-count{font-family:var(--mono);font-size:11.5px;
  color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums}
.hs-prog{margin-top:18px;border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:18px 20px}
.hs-prog .hd{display:flex;align-items:center;gap:11px;margin-bottom:12px}
.hs-prog .spin{width:20px;height:20px;flex:none;border-radius:50%;
  border:2.5px solid color-mix(in srgb,var(--green-deep,#154e36) 22%,transparent);
  border-top-color:var(--green-deep,#154e36);
  animation:hs-spin .8s linear infinite}
@keyframes hs-spin{to{transform:rotate(360deg)}}
.hs-prog .t{font-family:var(--serif);font-size:16px;font-weight:600;
  letter-spacing:-.01em;color:var(--ink,#16263a)}
.hs-prog .bar{position:relative;height:9px;border-radius:var(--sc-r-1,2px);
  background:color-mix(in srgb,var(--ink,#16263a) 8%,transparent);
  overflow:hidden}
.hs-prog .bar i{position:absolute;top:0;bottom:0;left:-35%;width:35%;
  border-radius:inherit;
  background:linear-gradient(90deg,var(--green-2,#2d8964),var(--green-deep,#154e36));
  animation:hs-indet 1.4s ease-in-out infinite}
@keyframes hs-indet{0%{left:-35%}100%{left:100%}}
.hs-prog .note{font-family:var(--mono);font-size:11.5px;
  color:var(--sc-text-dim,#465366);margin:11px 0 0;line-height:1.6}
@media (prefers-reduced-motion:reduce){
  .hs-prog .spin,.hs-prog .bar i{animation:none}}
/* ============ Result: KPI tiles + confidence panel ============ */
.hs-kpis{margin:20px 0 6px}
.hs-neg{color:var(--sc-negative,#b5321e)}
.hs-score.good{color:var(--green-deep,#154e36)}
.hs-score.warn{color:var(--sc-warning,#b8732a)}
.hs-score.bad{color:var(--sc-negative,#b5321e)}
.hs-prov{font-family:var(--mono);font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--sc-text-faint,#7a8699);margin:8px 0 0}
.hs-conf{border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);background:var(--paper-card,#fefcf3);
  padding:16px 20px;margin:12px 0 8px}
.hs-conf.good{border-left:3px solid var(--green-deep,#154e36)}
.hs-conf.warn{border-left:3px solid var(--sc-warning,#b8732a)}
.hs-conf.bad{border-left:3px solid var(--sc-negative,#b5321e)}
.hs-conf .score-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.hs-conf .hs-score{font-family:var(--serif);font-size:30px;font-weight:600;
  letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.hs-conf .summaries{margin:10px 0 0;padding-left:18px;font-size:13px;
  line-height:1.6;color:var(--ink,#16263a)}
.hs-eb{display:block;font-family:var(--mono);font-size:10px;font-weight:600;
  letter-spacing:.13em;text-transform:uppercase;
  color:var(--green-deep,#154e36);margin:14px 0 6px}
.hs-iss{display:flex;gap:10px;align-items:baseline;padding:7px 0;
  border-top:1px solid var(--rule-soft,#ddd1ac);font-size:12.5px;
  color:var(--ink,#16263a)}
.hs-iss .m{flex:1;line-height:1.5}
.hs-iss .ct{font-family:var(--mono);font-size:11.5px;
  color:var(--sc-text-dim,#465366);font-variant-numeric:tabular-nums;
  white-space:nowrap}
.hs-iss--clear{color:var(--green-deep,#154e36);font-weight:600}
/* ============ Result: findings cards, ranked by impact ============ */
.hs-total{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
  font-family:var(--mono);font-size:12px;color:var(--sc-text-dim,#465366);
  font-variant-numeric:tabular-nums;margin:8px 0 14px}
.hs-total b{color:var(--ink,#16263a);font-weight:700}
.hs-find{border:1px solid var(--rule,#c9bf9c);border-radius:var(--sc-r-2,4px);
  background:var(--paper-card,#fefcf3);padding:16px 20px;margin-bottom:12px;
  transition:border-color .15s ease, box-shadow .15s ease}
.hs-find:hover{
  border-color:color-mix(in srgb,var(--green-deep,#154e36) 40%,var(--rule,#c9bf9c));
  box-shadow:0 1px 4px color-mix(in srgb,var(--green-deep,#154e36) 10%,transparent)}
.hs-find .top{display:flex;justify-content:space-between;gap:16px;
  align-items:flex-start;flex-wrap:wrap}
.hs-find .t{margin:0;font-family:var(--serif);font-size:17px;font-weight:600;
  letter-spacing:-.01em;color:var(--ink,#16263a);line-height:1.3}
.hs-find .impact{text-align:right;flex:none}
.hs-find .impact .v{display:block;font-family:var(--mono);font-size:18px;
  font-weight:700;font-variant-numeric:tabular-nums;
  color:var(--sc-negative,#b5321e)}
.hs-find .impact .v.na{color:var(--sc-text-faint,#7a8699);font-weight:500}
.hs-find .impact .l{display:block;font-family:var(--mono);font-size:9.5px;
  letter-spacing:.09em;text-transform:uppercase;
  color:var(--sc-text-faint,#7a8699);margin-top:2px}
.hs-find .meta{margin-top:8px}
.hs-find .sum{font-size:13.5px;line-height:1.6;color:var(--ink,#16263a);
  margin:10px 0 0;max-width:72ch}
.hs-find .cave{margin-top:12px;
  border-top:1px solid var(--rule-soft,#ddd1ac);padding-top:10px}
.hs-find .cave .hs-eb{margin:0 0 5px}
.hs-find .cave ul{margin:0;padding-left:18px;font-size:12.5px;
  line-height:1.6;color:var(--sc-text-dim,#465366)}
/* ============ Result: memo deliverable ============ */
.hs-memo-help{font-size:12.5px;color:var(--sc-text-dim,#465366);
  margin:6px 0 12px;line-height:1.55}
.hs-memo-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center;
  margin:0 0 12px}
.hs-btn{display:inline-flex;align-items:center;gap:8px;padding:9px 16px;
  font-family:var(--sans);font-size:12px;font-weight:600;
  letter-spacing:.06em;text-transform:uppercase;cursor:pointer;
  border:1px solid var(--green-deep,#154e36);
  border-radius:var(--sc-r-1,2px);background:var(--green-deep,#154e36);
  color:#fff;text-decoration:none;
  transition:background .12s ease,color .12s ease,border-color .12s ease}
.hs-btn:hover{background:var(--green-2,#2d8964);
  border-color:var(--green-2,#2d8964);color:#fff}
.hs-btn:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:2px}
.hs-btn.is-done{background:var(--sc-positive,#0a8a5f);
  border-color:var(--sc-positive,#0a8a5f)}
.hs-btn.is-fail{background:var(--sc-negative,#b5321e);
  border-color:var(--sc-negative,#b5321e)}
.hs-btn-alt{background:transparent;color:var(--green-deep,#154e36)}
.hs-btn-alt:hover{background:var(--green-deep,#154e36);color:#fff}
.hs-memo{background:var(--paper,#ffffff);border:1px solid var(--rule,#c9bf9c);
  border-radius:var(--sc-r-2,4px);padding:18px 20px;overflow:auto;
  font-family:var(--mono);font-size:12px;line-height:1.6;
  white-space:pre-wrap;color:var(--ink,#16263a);max-height:560px}
.hs-next{margin:22px 0 0;display:flex;gap:22px;flex-wrap:wrap}
@media print{
  .hs-memo-actions,.hs-next,.hs-prog{display:none !important}
  .hs-memo{max-height:none;border:none;padding:0}}
"""


# ---------------------------------------------------------------------------
# Page JS — vanilla, no dependencies. Upload: dropzone + size pre-check +
# double-submit guard + processing state. Result: copy-memo button.
# ---------------------------------------------------------------------------

_UPLOAD_JS = r"""
(function(){
  "use strict";
  var form = document.getElementById("hs-form");
  if (!form) return;
  var drop = document.getElementById("hs-drop");
  var input = document.getElementById("hs-files");
  var list = document.getElementById("hs-file-list");
  var err = document.getElementById("hs-size-err");
  var btn = document.getElementById("hs-submit");
  var prog = document.getElementById("hs-progress");
  var count = document.getElementById("hs-drop-count");
  if (!drop || !input || !btn) return;
  form.classList.add("hs-js");
  var MAX = __HS_MAX_BYTES__; /* mirrors the server's 10 MB multipart cap */
  function fmtSize(n){
    if (n >= 1048576) return (n / 1048576).toFixed(1) + " MB";
    if (n >= 1024) return (n / 1024).toFixed(0) + " KB";
    return n + " B";
  }
  function refresh(){
    list.innerHTML = "";
    err.textContent = "";
    err.classList.add("hs-hidden");
    var files = input.files || [];
    var total = 0, over = null, i, li, nm, sz;
    for (i = 0; i < files.length; i++) {
      total += files[i].size;
      li = document.createElement("li");
      nm = document.createElement("span");
      nm.className = "nm";
      nm.textContent = files[i].name;
      sz = document.createElement("span");
      sz.className = "sz";
      sz.textContent = fmtSize(files[i].size);
      li.appendChild(nm);
      li.appendChild(sz);
      if (files[i].size > MAX) { li.classList.add("over"); over = files[i]; }
      list.appendChild(li);
    }
    var blocked = false;
    if (over) {
      err.textContent = over.name + " is " + fmtSize(over.size) +
        " — the upload limit is 10 MB. Split the package or upload " +
        "individual 835/837 files.";
      blocked = true;
    } else if (total > MAX) {
      err.textContent = "Selected files total " + fmtSize(total) +
        " — the combined upload limit is 10 MB. Upload fewer files " +
        "at a time.";
      blocked = true;
    }
    if (blocked) err.classList.remove("hs-hidden");
    btn.disabled = blocked;
    if (count) {
      count.textContent = files.length
        ? files.length + " file" + (files.length > 1 ? "s" : "") +
          " selected · " + fmtSize(total)
        : "";
    }
  }
  drop.addEventListener("click", function(){ input.click(); });
  drop.addEventListener("keydown", function(e){
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
  });
  ["dragenter", "dragover"].forEach(function(ev){
    drop.addEventListener(ev, function(e){
      e.preventDefault(); drop.classList.add("drag");
    });
  });
  ["dragleave", "drop"].forEach(function(ev){
    drop.addEventListener(ev, function(e){
      e.preventDefault(); drop.classList.remove("drag");
    });
  });
  drop.addEventListener("drop", function(e){
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      try { input.files = e.dataTransfer.files; } catch (_ignore) {}
      refresh();
    }
  });
  input.addEventListener("change", refresh);
  var submitted = false;
  form.addEventListener("submit", function(e){
    if (btn.disabled || submitted) { e.preventDefault(); return; }
    submitted = true;
    btn.disabled = true;
    btn.textContent = "Analyzing…";
    if (prog) prog.classList.remove("hs-hidden");
  });
  /* Back-button from the result page restores this page from the
     back/forward cache with the closure state intact — without this
     reset the button stays disabled on "Analyzing…" forever. */
  window.addEventListener("pageshow", function(e){
    if (!e.persisted) return;
    submitted = false;
    btn.textContent = "Run revenue-leakage analysis";
    if (prog) prog.classList.add("hs-hidden");
    refresh();
  });
})();
""".replace("__HS_MAX_BYTES__", str(_MAX_UPLOAD_BYTES))

_RESULT_JS = r"""
(function(){
  "use strict";
  var btn = document.getElementById("hs-copy-btn");
  var pre = document.getElementById("hs-memo");
  if (!btn || !pre) return;
  btn.addEventListener("click", function(){
    var text = pre.textContent || "";
    function done(ok){
      btn.textContent = ok ? "Copied ✓" : "Copy failed";
      btn.classList.add(ok ? "is-done" : "is-fail");
      setTimeout(function(){
        btn.textContent = "Copy memo";
        btn.classList.remove("is-done", "is-fail");
      }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function(){ done(true); }, function(){ done(false); });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (_ignore) {}
      document.body.removeChild(ta);
      done(ok);
    }
  });
})();
"""


# ---------------------------------------------------------------------------
# Shared fragments
# ---------------------------------------------------------------------------

def _notice(tone: str, eyebrow: str, text: str, *, alert: bool = False) -> str:
    """Single toned notice band: warning (PHI), negative (errors, with
    ``role=alert`` so a failed-analysis re-render is announced to AT),
    or neutral (informational)."""
    role = ' role="alert"' if alert else ""
    return (
        f'<div class="hs-note hs-note--{tone}"{role}>'
        f'<span class="eb">{_html.escape(eyebrow)}</span>'
        f'{_html.escape(text)}</div>'
    )


def _issue_tone(severity: str) -> str:
    """Map data-quality issue severities (INFO/WARN/ERROR — and legacy
    low/medium/high strings) onto kit badge tones."""
    return {
        "error": "negative", "high": "negative",
        "warn": "warning", "warning": "warning", "medium": "warning",
        "info": "neutral", "low": "neutral",
    }.get((severity or "").strip().lower(), "neutral")


def _confidence_tone(confidence: str) -> str:
    """Finding-confidence ("high"|"medium"|"low") → kit badge tone."""
    return {"high": "positive", "medium": "warning"}.get(
        (confidence or "").strip().lower(), "neutral")


def _score_cls(score: int) -> str:
    return "good" if score >= 85 else "warn" if score >= 70 else "bad"


# ---------------------------------------------------------------------------
# Upload page
# ---------------------------------------------------------------------------

def render_snapshot_upload(*, notice: str = "", error: str = "") -> str:
    head = ck_editorial_head(
        eyebrow="RCM DILIGENCE · SNAPSHOT INGEST",
        title="Healthcare Snapshot — Revenue-Leakage Diligence",
        meta=(f"835/837 · {len(_FORMAT_CHIPS)} FORMAT FAMILIES · "
              "10 MB CAP · PHI TOKENIZED · NOTHING STORED"),
        lede_italic_phrase="Upload a VDR package",
        lede_body=(
            " — 835 remittances, 837 claims, or a .zip drop — and the "
            "snapshot pipeline parses it in memory, reconciles 837&harr;835, "
            "scores data confidence, and returns ranked revenue-leakage "
            "findings with a Markdown diligence memo."),
        source_note=("Snapshot pipeline v2 — patient identifiers tokenized "
                     "on ingest; every output is aggregate-only."),
        # Legend on: every RCM DILIGENCE masthead carries the 4-dot
        # live/computed honesty key (ingest, benchmarks, checklist, …).
    )
    chips = "".join(ck_signal_badge(c) for c in _FORMAT_CHIPS)
    parts = [
        head,
        '<div class="hs-wrap">',
        _notice("warning", "PHI notice", _PHI_WARNING),
    ]
    if error:
        parts.append(_notice("negative", "Upload error", error, alert=True))
    if notice:
        parts.append(_notice("neutral", "Notice", notice))
    parts.append(
        '<form method="POST" action="/diligence/snapshot" '
        'enctype="multipart/form-data" class="hs-form" id="hs-form">'
        '<div class="hs-field">'
        '<label class="hs-label" for="hs-deal-name">Deal / target name</label>'
        '<input type="text" id="hs-deal-name" name="deal_name" '
        'class="hs-input" placeholder="Project Atlas" autocomplete="off">'
        '</div>'
        '<label class="hs-label" for="hs-files">VDR files</label>'
        '<div class="hs-drop" id="hs-drop" tabindex="0" role="button" '
        'aria-label="Upload VDR files — press Enter to choose files">'
        '<div class="cloud" aria-hidden="true">&#10514;</div>'
        '<div class="big">Drop the VDR package here</div>'
        '<div class="small">Drag 835/837 remittance-and-claims files or a '
        '.zip VDR package here, or <span class="pick">choose files</span>. '
        'Parsed in memory — nothing is stored.</div>'
        f'<div class="hs-formats">{chips}'
        '<span class="cap">Up to <strong>10&nbsp;MB</strong> per upload</span>'
        '</div>'
        '</div>'
        f'<input type="file" id="hs-files" name="files" multiple '
        f'accept="{_ACCEPT_ATTR}" aria-label="VDR files" class="hs-native">'
        '<p class="hs-size-err hs-hidden" id="hs-size-err" role="alert"></p>'
        '<ul class="hs-file-list" id="hs-file-list"></ul>'
        '<div class="hs-actions">'
        '<button type="submit" class="sc-btn sc-btn-primary hs-submit" '
        'id="hs-submit">Run revenue-leakage analysis</button>'
        '<span class="hs-drop-count" id="hs-drop-count" aria-live="polite">'
        '</span>'
        '</div>'
        '<div class="hs-prog hs-hidden" id="hs-progress" aria-live="polite">'
        '<div class="hd"><span class="spin" aria-hidden="true"></span>'
        '<span class="t">Analyzing the snapshot&hellip;</span></div>'
        '<div class="bar"><i></i></div>'
        '<p class="note">Parsing 835/837 files and reconciling claims in '
        'memory — aggregates only, nothing is stored. Large packages can '
        'take a few seconds; leave this page open.</p>'
        '</div>'
        '<p class="hs-fine">Analysis runs in-memory and returns findings '
        'plus a Markdown memo — nothing is written to the database.</p>'
        '</form>'
        '</div>')
    # Standard action pills at the page bottom — same placement and flags
    # as the rest of the diligence family.
    parts.append(ck_page_actions())
    return chartis_shell(
        "\n".join(parts), "RCM Diligence — Healthcare Snapshot",
        subtitle="Snapshot-based 835/837 revenue-leakage diligence",
        active_nav="/diligence/snapshot",
        extra_css=_EXTRA_CSS, extra_js=_UPLOAD_JS)


# ---------------------------------------------------------------------------
# Result page
# ---------------------------------------------------------------------------

def _confidence_panel(result: "SnapshotResult") -> str:
    c = result.confidence
    tone = _score_cls(c.score)
    score_html = ck_provenance_tooltip(
        "Data Confidence",
        f'<span class="hs-score {tone}">{c.score}/100</span>',
        explainer=(
            "Scored 0-100 from reconciliation checks on the parsed "
            "snapshot: 837↔835 match rate, unmatched submissions, "
            "duplicate claims, unmapped adjustment codes, and field "
            "completeness. Higher means the leakage figures rest on "
            "cleaner data."))
    summaries = "".join(
        f'<li>{_html.escape(s)}</li>' for s in c.summaries)
    summaries_html = (
        f'<ul class="summaries">{summaries}</ul>' if summaries else "")
    if c.issues:
        rows = "".join(
            '<div class="hs-iss">'
            + ck_signal_badge(i.severity, tone=_issue_tone(i.severity))
            + f'<span class="m">{_html.escape(i.message)}</span>'
            + (f'<span class="ct">n={i.count:,}</span>'
               if getattr(i, "count", None) else "")
            + '</div>'
            for i in c.issues)
    else:
        rows = ('<div class="hs-iss hs-iss--clear">'
                'No data-quality issues flagged.</div>')
    return (
        f'<section class="hs-conf {tone}">'
        f'<div class="score-row">{score_html}</div>'
        f'{summaries_html}'
        '<span class="hs-eb">Open issues</span>'
        f'{rows}'
        '</section>')


def _findings_section(result: "SnapshotResult") -> str:
    header = ck_section_header(
        "Findings", eyebrow="REVENUE LEAKAGE · RANKED BY IMPACT",
        count=len(result.findings))
    if not result.findings:
        return header + ck_affirm_empty(
            headline="No leakage findings",
            body=("The snapshot parsed cleanly and no revenue-leakage "
                  "patterns crossed the reporting threshold."),
            cta_text="Run another snapshot",
            cta_href="/diligence/snapshot")
    ranked = sorted(
        result.findings,
        key=lambda f: (f.estimated_impact_amount is None,
                       -(f.estimated_impact_amount or 0.0)))
    impacts = [f.estimated_impact_amount for f in ranked
               if f.estimated_impact_amount is not None]
    unquantified = len(ranked) - len(impacts)
    total_bits = [f'<b>{len(ranked)}</b> finding'
                  + ("s" if len(ranked) != 1 else "")]
    if impacts:
        total_bits.append(
            f'est. <b>{ck_fmt_currency(sum(impacts), precision=2)}</b> '
            'combined (directional)')
    if unquantified:
        total_bits.append(f'{unquantified} unquantified')
    total_strip = ('<div class="hs-total">'
                   + " · ".join(total_bits) + '</div>')
    cards = []
    for f in ranked:
        if f.estimated_impact_amount is not None:
            impact_html = (
                '<span class="v">'
                f'{ck_fmt_currency(f.estimated_impact_amount, precision=2)}'
                '</span><span class="l">est. impact</span>')
        else:
            impact_html = ('<span class="v na">—</span>'
                           '<span class="l">not quantified</span>')
        badge = ck_signal_badge(
            f"{f.confidence} confidence",
            tone=_confidence_tone(f.confidence))
        caveats = "".join(
            f'<li>{_html.escape(lim)}</li>' for lim in f.limitations)
        caveats_html = (
            '<div class="cave"><span class="hs-eb">Caveats</span>'
            f'<ul>{caveats}</ul></div>') if caveats else ""
        cards.append(
            '<article class="hs-find">'
            '<div class="top">'
            f'<h3 class="t">{_html.escape(f.title)}</h3>'
            f'<div class="impact">{impact_html}</div>'
            '</div>'
            f'<div class="meta">{badge}</div>'
            f'<p class="sum">{_html.escape(f.summary)}</p>'
            f'{caveats_html}'
            '</article>')
    return header + total_strip + "".join(cards)


def render_snapshot_result(result: "SnapshotResult", *,
                           deal_name: str = "Target") -> str:
    t = result.analytics.totals
    c = result.confidence
    safe_deal = _html.escape(deal_name)
    n_findings = len(result.findings)
    leakage = ck_fmt_currency(t.potentially_preventable_leakage, precision=2)
    head = ck_editorial_head(
        eyebrow="RCM DILIGENCE · SNAPSHOT FINDINGS",
        title=f"Revenue-Leakage Findings — {safe_deal}",
        meta=(f"{t.claim_count:,} CLAIM LINE{'S' if t.claim_count != 1 else ''}"
              f" · {n_findings} FINDING{'S' if n_findings != 1 else ''} · "
              f"CONFIDENCE {c.score}/100"),
        lede_italic_phrase=f"{deal_name} shows",
        lede_body=(
            f" {_html.escape(leakage)} of potentially preventable leakage "
            f"across {t.claim_count:,} claim lines "
            f"({_html.escape(ck_fmt_currency(t.gross_charges, precision=2))} "
            "gross charges). Figures are directional, aggregate-only, and "
            "subject to validation against source systems."),
        # ck_editorial_head prepends "Source: " — lead with the artifact,
        # not another label, so the line doesn't read "Source: Parser: …".
        source_note=("835/837 snapshot · parser "
                     f"{result.parser_used or 'auto-detect'} · aggregates "
                     "only — no patient-level data is displayed."),
        # Legend on + no masthead action pills: matches every other
        # RCM DILIGENCE masthead (the pills land at the page bottom).
    )
    score_tone = _score_cls(c.score)
    # ck_kpi_block value/sub are trusted server markup (B2 exemption in
    # _chartis_kit) — everything passed below is a kit-formatted numeric
    # or fixed copy, never user input.
    kpis = (
        '<div class="ck-kpi-grid hs-kpis">'
        + ck_kpi_block("Claim lines", ck_fmt_number(t.claim_count),
                       "835/837 merged")
        + ck_kpi_block("Gross charges",
                       ck_fmt_currency(t.gross_charges, precision=2),
                       "billed amount")
        + ck_kpi_block(
            "Preventable leakage",
            f'<span class="hs-neg">{leakage}</span>',
            "potentially preventable · directional")
        + ck_kpi_block(
            "Data Confidence",
            f'<span class="hs-score {score_tone}">{c.score}/100</span>',
            "reconciliation-scored")
        + '</div>')
    memo_slug = _re.sub(r"[^a-z0-9]+", "-", deal_name.lower()).strip("-") \
        or "target"
    memo_uri = ("data:text/markdown;charset=utf-8,"
                + _urlparse.quote(result.memo_markdown))
    memo = (
        ck_section_header("Diligence memo", eyebrow="DELIVERABLE · MARKDOWN")
        + '<p class="hs-memo-help">Drop the memo into the deal workstream '
        'or IC packet — copy it to the clipboard, or download the .md to '
        'preserve formatting.</p>'
        '<div class="hs-memo-actions">'
        '<button type="button" class="hs-btn" id="hs-copy-btn">'
        'Copy memo</button>'
        f'<a class="hs-btn hs-btn-alt" href="{memo_uri}" '
        f'download="{memo_slug}-leakage-memo.md">Download .md</a>'
        '</div>'
        f'<pre class="hs-memo" id="hs-memo">'
        f'{_html.escape(result.memo_markdown)}</pre>')
    parts = [
        head,
        '<div class="hs-wrap">',
        kpis,
        _notice(
            "neutral", "Aggregate output only",
            "No patient-level data is displayed. Figures are directional "
            "and subject to validation."),
        ck_section_header("Data confidence",
                          eyebrow="RECONCILIATION · 837↔835"),
        _confidence_panel(result),
        _findings_section(result),
        memo,
        '<p class="hs-next">'
        + ck_arrow_link("Run another snapshot", "/diligence/snapshot")
        + ck_arrow_link("Open the diligence workspace", "/diligence")
        + '</p>',
        '</div>',
        # Standard action pills at the page bottom — same placement and
        # flags as the rest of the diligence family.
        ck_page_actions(),
    ]
    return chartis_shell(
        "\n".join(parts), "RCM Diligence — Revenue-Leakage Findings",
        subtitle="Snapshot-based 835/837 revenue-leakage diligence",
        active_nav="/diligence/snapshot",
        extra_css=_EXTRA_CSS, extra_js=_RESULT_JS)
