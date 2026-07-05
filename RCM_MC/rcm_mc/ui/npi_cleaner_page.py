"""NPI Claims Cleaner — the ``/npi-cleaner`` tool page.

A drag-and-drop utility that runs a claims file through the offline NPI
cleaner (``rcm_mc.npi_cleaner.engine``): validate every NPI against the Luhn
check, de-duplicate exact rows, trim whitespace, flag missing / malformed /
checksum-failing billing NPIs, and hand back a cleaned CSV plus a scorecard.

Rendered inside ``chartis_shell`` (TOOLS nav) so it lives natively in the PE
Desk app. The upload → live-progress → download loop is pure client-side JS
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

from ._chartis_kit import chartis_shell, ck_editorial_head, ck_page_actions


_EXTRA_CSS = r"""
.npi-wrap{max-width:920px;margin:0 auto}
.npi-drop{
  border:2px dashed var(--line,#c9d6d0); border-radius:16px;
  background:var(--panel,#fbfdfc); padding:44px 28px; text-align:center;
  cursor:pointer; transition:border-color .15s ease, background .15s ease;
}
.npi-drop:hover,.npi-drop.drag{
  border-color:var(--green-deep,#0c7c66);
  background:color-mix(in srgb, var(--green-deep,#0c7c66) 5%, transparent);
}
.npi-drop .cloud{font-size:34px;line-height:1;margin-bottom:10px}
.npi-drop .big{font-size:17px;font-weight:640;letter-spacing:-.01em}
.npi-drop .small{font-size:12.5px;color:var(--ink-2,#4a5d57);margin-top:6px}
.npi-drop .pick{color:var(--green-deep,#0c7c66);text-decoration:underline;font-weight:600}
.npi-opts{display:flex;gap:18px;flex-wrap:wrap;justify-content:center;
  margin:16px 0 4px;font-size:13px;color:var(--ink-2,#4a5d57)}
.npi-opts label{display:flex;align-items:center;gap:7px;cursor:pointer}
.npi-hidden{display:none !important}
.npi-prog{margin-top:22px}
.npi-bar{height:10px;border-radius:6px;background:var(--line-soft,#e7eeea);overflow:hidden}
.npi-bar > i{display:block;height:100%;width:0;border-radius:6px;
  background:linear-gradient(90deg,var(--green,#0c7c66),var(--green-deep,#075a4a));
  transition:width .25s ease}
.npi-msg{font-size:12.5px;color:var(--ink-2,#4a5d57);margin-top:8px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.npi-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:12px;margin:22px 0}
.npi-card{border:1px solid var(--line,#d2ddd7);border-radius:12px;
  background:var(--panel,#fbfdfc);padding:14px 16px}
.npi-card .k{font-size:11px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-2,#4a5d57)}
.npi-card .v{font-size:26px;font-weight:680;letter-spacing:-.02em;margin-top:4px;
  font-variant-numeric:tabular-nums}
.npi-card .v.good{color:var(--green-deep,#0c7c66)}
.npi-card .v.warn{color:#b06a00}
.npi-card .v.bad{color:#a8331f}
.npi-tbl{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
.npi-tbl th,.npi-tbl td{padding:8px 10px;border-bottom:1px solid var(--line-soft,#e7eeea);text-align:left}
.npi-tbl th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-2,#4a5d57);font-weight:640}
.npi-tbl td.num{text-align:right;font-variant-numeric:tabular-nums}
.npi-tbl tr td.billing{font-weight:640}
.npi-badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:20px;
  background:color-mix(in srgb,var(--green-deep,#0c7c66) 12%,transparent);
  color:var(--green-deep,#0c7c66);margin-left:6px;vertical-align:middle}
.npi-dl{display:inline-flex;align-items:center;gap:8px;margin-top:6px;
  background:var(--green-deep,#0c7c66);color:#fff;text-decoration:none;
  padding:11px 20px;border-radius:10px;font-weight:640;font-size:14px}
.npi-dl:hover{background:var(--green,#075a4a)}
.npi-dl-alt{background:transparent;color:var(--green-deep,#0c7c66);
  border:1px solid var(--green-deep,#0c7c66)}
.npi-dl-alt:hover{background:color-mix(in srgb,var(--green-deep,#0c7c66) 8%,transparent);color:var(--green-deep,#0c7c66)}
.npi-recovered{border:1px solid #b7d9c9;background:#eef7f2;color:#0c5a45;
  border-radius:10px;padding:10px 14px;font-size:13px;margin-top:16px}
.npi-sig{font-size:11.5px}
.npi-sig.bad{color:#a8331f;font-weight:600}
.npi-sig.warn{color:#b06a00}
.npi-again{margin-left:14px;font-size:13px;color:var(--green-deep,#0c7c66);
  cursor:pointer;text-decoration:underline;background:none;border:0;padding:0}
.npi-err{border:1px solid #e2b8ae;background:#fbf1ee;color:#8a2a17;
  border-radius:10px;padding:12px 14px;font-size:13px;margin-top:16px}
.npi-warn{border:1px solid #e8d8ac;background:#fbf7ea;color:#7a5a12;
  border-radius:10px;padding:10px 14px;font-size:12.5px;margin-top:12px}
.npi-note{font-size:12px;color:var(--ink-2,#4a5d57);margin-top:26px;
  border-top:1px solid var(--line-soft,#e7eeea);padding-top:14px;line-height:1.6}
.npi-adv{margin-top:26px}
.npi-adv h3{margin:0 0 3px}
.npi-adv .eng{font-size:11.5px;color:var(--ink-2,#4a5d57);
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin-bottom:8px}
.npi-flag{display:flex;justify-content:space-between;gap:12px;align-items:baseline;
  padding:9px 12px;border:1px solid var(--line-soft,#e7eeea);border-radius:9px;
  margin-bottom:7px;background:var(--panel,#fbfdfc)}
.npi-flag .lab{font-weight:600;font-size:13px}
.npi-flag .lab small{display:block;font-weight:400;color:var(--ink-2,#4a5d57);
  font-size:11.5px;margin-top:2px}
.npi-flag .cnt{font-variant-numeric:tabular-nums;font-weight:680;font-size:15px;
  white-space:nowrap}
.npi-flag .cnt.hit{color:#a8331f}
.npi-flag .cnt.clear{color:var(--green-deep,#0c7c66)}
.npi-pill{display:inline-block;font-size:10.5px;font-family:ui-monospace,Menlo,monospace;
  padding:1px 6px;border-radius:5px;background:var(--line-soft,#e7eeea);
  color:var(--ink-2,#4a5d57);margin-right:6px}
.npi-hint{cursor:help;color:var(--green-deep,#0c7c66);font-size:12px;margin-left:2px}
.npi-nppes-note{font-size:12px;color:var(--ink-2,#4a5d57);margin:2px 0 10px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.npi-cand{border:1px solid var(--line-soft,#e7eeea);border-radius:9px;
  padding:9px 12px;margin-bottom:7px;background:var(--panel,#fbfdfc);font-size:13px}
.npi-cand .q{font-weight:640}
.npi-cand .arrow{color:var(--ink-2,#4a5d57);margin:0 6px}
.npi-cand code{font-family:ui-monospace,Menlo,monospace;
  background:color-mix(in srgb,var(--green-deep,#0c7c66) 10%,transparent);
  padding:1px 6px;border-radius:5px;color:var(--green-deep,#0c7c66);font-weight:640}
.npi-cand .rowref{font-size:11px;color:var(--ink-2,#4a5d57)}
.npi-tabs{display:flex;gap:2px;border-bottom:1px solid var(--line,#d2ddd7);
  margin-bottom:18px;flex-wrap:wrap}
.npi-tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
  padding:9px 14px;font-size:14px;font-weight:600;color:var(--ink-2,#4a5d57);
  cursor:pointer;margin-bottom:-1px}
.npi-tab:hover{color:var(--ink,#11201c)}
.npi-tab.is-active{color:var(--green-deep,#0c7c66);
  border-bottom-color:var(--green-deep,#0c7c66)}
.npi-tab-badge{display:inline-block;min-width:18px;font-size:11px;text-align:center;
  font-variant-numeric:tabular-nums;padding:0 5px;border-radius:9px;
  background:var(--line-soft,#e7eeea);color:var(--ink-2,#4a5d57);margin-left:4px}
.npi-tab-badge:empty{display:none}
.npi-panel{display:none}
.npi-panel.is-active{display:block}
.npi-conn{border:1px solid var(--line,#d2ddd7);border-radius:12px;
  padding:14px 16px;margin-bottom:12px;background:var(--panel,#fbfdfc)}
.npi-conn .top{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.npi-conn .nm{font-weight:660;font-size:14px}
.npi-conn .src{font-size:11px;color:var(--ink-2,#4a5d57);
  font-family:ui-monospace,Menlo,monospace}
.npi-conn .cnt{font-variant-numeric:tabular-nums;font-weight:680;font-size:15px;
  color:var(--green-deep,#0c7c66);white-space:nowrap}
.npi-conn .nt{font-size:12px;color:var(--ink-2,#4a5d57);margin-top:6px}
.npi-cat{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
  gap:8px;margin-top:10px}
.npi-cat .c{border:1px solid var(--line-soft,#e7eeea);border-radius:9px;
  padding:8px 11px;background:var(--panel,#fbfdfc)}
.npi-cat .c .n{font-size:12.5px;font-weight:600}
.npi-cat .c .o{font-size:11px;color:var(--ink-2,#4a5d57)}
.npi-cat .c .free{color:var(--green-deep,#0c7c66)}
.npi-muted{font-size:12.5px;color:var(--ink-2,#4a5d57);margin:14px 0}
.npi-map{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  gap:10px 16px;margin-top:6px}
.npi-map .row{display:flex;flex-direction:column;gap:3px}
.npi-map label{font-size:12px;font-weight:600;color:var(--ink,#11201c)}
.npi-map select{padding:7px 9px;border:1px solid var(--line,#d2ddd7);
  border-radius:8px;font-size:13px;background:var(--panel,#fbfdfc);color:var(--ink,#11201c)}
.npi-map select.auto{color:var(--ink-2,#4a5d57)}
.npi-map .row.set label{color:var(--green-deep,#0c7c66)}
.npi-drill{cursor:pointer}
.npi-drill:hover{background:color-mix(in srgb,var(--green-deep,#0c7c66) 4%,transparent)}
.npi-drill td:first-child::before{content:"▸ ";color:var(--ink-2,#4a5d57);font-size:11px}
.npi-drill.open td:first-child::before{content:"▾ "}
.npi-drillrows{background:var(--paper,#f3f7f5)}
.npi-drillrows table{width:100%;border-collapse:collapse;font-size:12px;margin:4px 0}
.npi-drillrows th,.npi-drillrows td{padding:5px 8px;border-bottom:1px solid var(--line-soft,#e7eeea);text-align:left}
.npi-drillrows th{font-size:10.5px;text-transform:uppercase;color:var(--ink-2,#4a5d57)}
"""


def _body() -> str:
    head = ck_editorial_head(
        eyebrow="TOOLS · DATA HYGIENE",
        title="NPI Claims Cleaner",
        meta="OFFLINE · STDLIB ENGINE · NO PHI STORED",
        lede_italic_phrase="Drop a claims file",
        lede_body=(
            " and get it back cleaned: every NPI checked against the official "
            "Luhn checksum, exact-duplicate rows removed, whitespace trimmed, "
            "and every missing or malformed billing-provider NPI flagged. "
            "Processed in memory — nothing is stored, and nothing leaves the "
            "server unless you opt into the live NPPES cross-check."),
        source_note=(
            "Deterministic v49 cleaning engine validated against CMS "
            "reference tables. Runs entirely on this server — no data "
            "leaves unless the live NPPES cross-check is enabled."),
        actions_html=ck_page_actions(glossary=False, methodology=False),
        show_legend=False,
    )
    return f"""
{head}
<div class="npi-wrap">

  <div id="npi-stage-upload">
    <div class="npi-drop" id="npi-drop" tabindex="0" role="button"
         aria-label="Upload a claims file">
      <div class="cloud">⤒</div>
      <div class="big">Drag a claims file here</div>
      <div class="small">or <span class="pick">choose a file</span> —
        CSV, TSV, Excel (.xlsx), X12 837/835 (.837/.835/.edi), or a
        <strong>.zip of files</strong> · CSV/TSV up to
        <strong>10&nbsp;GB</strong> (streamed in chunks; multi-hour jobs
        are fine), other formats up to 200&nbsp;MB ·
        <a href="/npi-cleaner/sample" class="pick" download>try a sample file</a></div>
    </div>
    <input type="file" id="npi-file" class="npi-hidden"
           accept=".csv,.tsv,.txt,.xlsx,.837,.835,.edi,.x12,.zip,text/csv,text/plain,application/zip,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
    <div class="npi-opts">
      <label><input type="checkbox" id="npi-dedupe" checked>
        Remove exact-duplicate rows</label>
      <label><input type="checkbox" id="npi-enrich">
        Go online — verify &amp; recover NPIs, resolve drugs (NPPES · RxNorm · openFDA)
        <span class="npi-hint" title="Uses PE Desk's own live public-data
connectors. NPIs are verified against NPPES (active vs deactivated) and missing
NPIs recovered from provider names; NDC and drug-name columns are resolved to
RxNorm concepts and openFDA labels. Bounded, cached, opt-in.">ⓘ</span></label>
      <label><input type="checkbox" id="npi-deep">
        Deep recovery — full v49 pipeline (networked, slower)
        <span class="npi-hint" title="Runs the complete Steps 0-8 recovery
pipeline: live NPPES enrichment, CMS billers, Open Payments, 340B, entity
resolution and statistical fill, then a multi-tab Excel report. Needs outbound
network access and can take minutes; runs in the background with a timeout and
never blocks the fast results.">ⓘ</span></label>
      <label><input type="checkbox" id="npi-deid">
        De-identify patient PHI in the export
        <span class="npi-hint" title="Masks patient-scoped identifiers only —
patient name/address/phone/email and SSN are redacted, DOB is reduced to year,
ZIP to its first three digits, and MRN/account numbers are replaced with a
stable per-run token (same value → same token, so rows still link). Provider
NPI and provider name are always kept intact — NPI recovery depends on them.">ⓘ</span></label>
      <label style="margin-left:2px">Cleaning profile
        <select id="npi-profile" style="margin-left:6px;font-size:12.5px">
          <option value="">(default rules)</option>
        </select>
        <button type="button" class="npi-again" id="npi-profile-new"
                style="margin-left:6px">manage…</button>
        <span class="npi-hint" title="Named rule suites: disable rules that
don't apply to this feed, mark known issues as accepted (still reported,
no longer graded), and tune thresholds (timely-filing days, stale-date
horizon, outlier fence). Stored on the server; pick one per upload.">ⓘ</span>
      </label>
    </div>
    <div id="npi-profile-editor" class="npi-hidden" style="border:1px solid
      var(--line,#d2ddd7);border-radius:8px;padding:14px;margin-top:10px">
      <div style="font-size:13px;font-weight:640;margin-bottom:8px">
        Cleaning profiles</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <input id="npi-prof-name" placeholder="profile name"
               style="font-size:12.5px;padding:4px 8px">
        <label class="npi-muted">timely-filing days
          <input id="npi-prof-timely" type="number" value="365" min="30"
                 max="1095" style="width:70px;font-size:12.5px"></label>
        <label class="npi-muted">stale after (years)
          <input id="npi-prof-stale" type="number" value="10" min="1"
                 max="50" style="width:55px;font-size:12.5px"></label>
        <label class="npi-muted">outlier fence (×IQR)
          <input id="npi-prof-iqr" type="number" value="3" min="1.5"
                 max="10" step="0.5" style="width:60px;font-size:12.5px"></label>
        <label class="npi-muted">dup window (days)
          <input id="npi-prof-dupwin" type="number" value="3" min="1"
                 max="30" style="width:55px;font-size:12.5px"></label>
      </div>
      <div class="npi-muted" style="margin-top:8px">Per rule: leave
        <em>on</em>, mark <em>accepted</em> (reported, not graded), or
        <em>off</em> (not checked at all).</div>
      <div id="npi-prof-rules" style="max-height:260px;overflow:auto;
        margin-top:6px;font-size:12px;columns:2;column-gap:24px"></div>
      <div style="margin-top:10px">
        <button type="button" class="npi-dl" id="npi-prof-save"
          style="font-size:12.5px;padding:6px 14px">Save profile</button>
        <button type="button" class="npi-again" id="npi-prof-close">close</button>
        <a class="npi-again" href="/npi-cleaner/api/profiles/export" download
           style="margin-left:12px;text-decoration:none;display:inline-block">
          export all</a>
        <button type="button" class="npi-again" id="npi-prof-import">
          import…</button>
        <input type="file" id="npi-prof-import-file" class="npi-hidden"
               accept=".json,application/json">
      </div>
      <div class="npi-muted" id="npi-prof-msg" style="margin-top:6px"></div>
    </div>
  </div>

  <div id="npi-stage-mapping" class="npi-hidden">
    <div class="ck-section-header"><h3 style="margin:0">Confirm columns</h3></div>
    <div class="npi-muted" id="npi-map-file"></div>
    <div style="margin:10px 0 4px">
      <label class="npi-muted" for="npi-map-tpl">Mapping template:</label>
      <select id="npi-map-tpl" style="font-size:12.5px;max-width:220px">
        <option value="">(none)</option></select>
      <input id="npi-map-tpl-name" placeholder="save as… e.g. Epic extract"
        style="font-size:12.5px;max-width:200px;margin-left:10px">
      <button type="button" class="npi-again" id="npi-map-tpl-save"
        style="font-size:12px">Save template</button>
      <span class="npi-muted" id="npi-map-tpl-msg"></span>
    </div>
    <div class="npi-map" id="npi-map-grid"></div>
    <div style="margin-top:18px">
      <button class="npi-dl" id="npi-map-clean">Clean file →</button>
      <button class="npi-again" id="npi-map-cancel">Cancel</button>
    </div>
  </div>

  <div id="npi-stage-progress" class="npi-hidden">
    <div class="npi-prog">
      <div class="npi-bar"><i id="npi-bar-fill"></i></div>
      <div class="npi-msg" id="npi-bar-msg">Uploading…</div>
      <div class="npi-msg npi-muted" id="npi-bar-eta"></div>
      <button type="button" class="npi-again npi-hidden" id="npi-cancel"
              style="margin-top:10px">Cancel this run</button>
    </div>
  </div>

  <div id="npi-stage-error" class="npi-hidden">
    <div class="npi-err" id="npi-err-text"></div>
    <button class="npi-again" id="npi-err-again">Try another file</button>
  </div>

  <div id="npi-stage-result" class="npi-hidden">
    <div class="npi-tabs" role="tablist">
      <button class="npi-tab is-active" data-tab="overview">Overview</button>
      <button class="npi-tab" data-tab="quality">Quality
        <span class="npi-tab-badge" id="tabbadge-quality"></span></button>
      <button class="npi-tab" data-tab="issues">Issues &amp; fixes
        <span class="npi-tab-badge" id="tabbadge-issues"></span></button>
      <button class="npi-tab" data-tab="population">Population
        <span class="npi-tab-badge" id="tabbadge-pop"></span></button>
      <button class="npi-tab" data-tab="connectors">Live connectors
        <span class="npi-tab-badge" id="tabbadge-conn"></span></button>
      <button class="npi-tab" data-tab="downloads">Downloads</button>
    </div>

    <div class="npi-panel is-active" data-panel="overview">
      <div class="npi-cards" id="npi-cards"></div>
      <div id="npi-warnings"></div>
      <div class="ck-section-header" style="margin-top:8px">
        <h3 style="margin:0">Per-column NPI health</h3>
      </div>
      <table class="npi-tbl">
        <thead><tr>
          <th>Column</th><th class="num">Cells</th><th class="num">Valid</th>
          <th class="num">Blank</th><th class="num">Malformed</th>
          <th class="num">Checksum&nbsp;fail</th><th class="num">Health</th>
        </tr></thead>
        <tbody id="npi-col-rows"></tbody>
      </table>
      <div id="npi-repairs"></div>
      <div id="npi-sanity"></div>
    </div>

    <div class="npi-panel" data-panel="quality">
      <div id="npi-quality"></div>
    </div>

    <div class="npi-panel" data-panel="issues">
      <div id="npi-advanced"></div>
      <div id="npi-suggestions"></div>
    </div>

    <div class="npi-panel" data-panel="population">
      <div class="npi-muted" style="font-size:12.5px;margin-bottom:10px">
        What the file <em>means</em>, not just whether it's clean: where care
        happened, how lines group into visits, what conditions the population
        carries, whether any month of data is missing, and who codes hotter
        than the file. Computed offline from the cleaned table — the class of
        output Tuva-style pipelines need a warehouse for.</div>
      <div id="npi-pop"></div>
    </div>

    <div class="npi-panel" data-panel="connectors">
      <div id="npi-deep"></div>
      <div id="npi-compliance"></div>
      <div id="npi-nppes"></div>
      <div id="npi-connectors"></div>
      <div id="npi-catalog"></div>
    </div>

    <div class="npi-panel" data-panel="downloads">
      <div id="npi-recovered-note"></div>
      <div id="npi-deid-note"></div>
      <div style="margin-top:4px;margin-bottom:14px">
        <a class="npi-dl" id="npi-analyze" href="#"
           style="background:var(--ink,#11201c)">📊 Open pivot analysis →</a>
        <a class="npi-dl npi-dl-alt" id="npi-exec" href="#" target="_blank"
           style="margin-left:10px">🖨 Executive report</a>
        <a class="npi-dl npi-dl-alt" href="/npi-cleaner/history"
           style="margin-left:10px">📈 Run history</a>
        <span class="npi-muted" style="margin-left:10px">Pivot analysis, a
          print-ready DQ one-pager, and quality tracked across runs.</span>
      </div>
      <div style="margin-top:8px">
        <a class="npi-dl" id="npi-dl" href="#" download>⤓ Download cleaned CSV</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-xlsx" href="#" download
           style="margin-left:10px">⤓ Download report (.xlsx)</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-companion" href="#" download
           style="margin-left:10px;display:none">⤓ Corrections companion (.csv)</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-changelog" href="#" download
           style="margin-left:10px;display:none">⤓ Change log — audit trail (.csv)</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-dict" href="#" download
           style="margin-left:10px;display:none">⤓ Data dictionary (.csv)</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-bundle" href="#" download
           style="margin-left:10px">⤓ Everything (.zip)</a>
      </div>
      <div id="npi-reconcile" style="margin-top:16px"></div>
      <div style="margin-top:16px">
        <button class="npi-again" id="npi-again">Clean another file</button>
      </div>
    </div>
  </div>

  <div id="npi-wishlist" style="border:1px solid var(--line,#d2ddd7);
      border-radius:8px;padding:16px;margin-top:22px">
    <div style="font-size:14px;font-weight:640;margin-bottom:4px">
      Missing something? Tell us and we'll build it.</div>
    <div class="npi-muted" style="font-size:12.5px;margin-bottom:10px">
      A check your compliance team needs, a payer we don't recognize, a
      field the detector misses, a file format we don't read — log it here.
      Requests go on the cleaner's build backlog and get filled in.</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <select id="npi-wish-cat" style="font-size:12.5px;padding:4px 6px">
        <option value="rule">New check / rule</option>
        <option value="field">Field / column type</option>
        <option value="payer">Payer</option>
        <option value="format">File format</option>
        <option value="integration">Integration / connector</option>
        <option value="other">Something else</option>
      </select>
      <input id="npi-wish-title" placeholder="one-line summary (required)"
             maxlength="120" style="flex:1;min-width:220px;font-size:12.5px;
             padding:4px 8px">
      <button type="button" class="npi-again" id="npi-wish-add">Request</button>
    </div>
    <textarea id="npi-wish-details" rows="2" maxlength="2000"
      placeholder="details (optional): what the data looks like, what you expect the cleaner to do"
      style="width:100%;margin-top:8px;font-size:12.5px;padding:6px 8px;
      box-sizing:border-box"></textarea>
    <div id="npi-wish-msg" class="npi-muted"
         style="font-size:12px;margin-top:6px"></div>
    <div id="npi-wish-list" style="margin-top:10px"></div>
  </div>

  <div id="npi-refdata" style="border:1px solid var(--line,#d2ddd7);
      border-radius:8px;padding:16px;margin-top:14px">
    <div style="font-size:14px;font-weight:640;margin-bottom:4px">
      Reference data packs — pull the real code sets</div>
    <div class="npi-muted" style="font-size:12.5px;margin-bottom:10px">
      The cleaner grades files out of the box with curated catalogs. Pull
      the authoritative public sets to go further: the full NUCC taxonomy,
      the complete ICD-10-CM and HCPCS Level II code sets (activates
      shaped-but-nonexistent-code flags), and the OIG exclusion list
      (activates automatic offline excluded-provider screening on every
      run). Downloads run on this server from nucc.org / cms.gov /
      oig.hhs.gov; each pack records its source, row count and SHA-256.</div>
    <div id="npi-refdata-list"><span class="npi-muted">Loading…</span></div>
  </div>

  <div class="npi-note">
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
    every public-data source wired into the platform (NPPES, OIG LEIE, RxNav,
    openFDA, DailyMed, HRSA, Census, ClinicalTrials, and more) that can be
    enabled for enrichment. All lookups are de-duplicated, capped per run and
    cached; if the network is unavailable the connectors simply no-op and the
    offline results stand. No data leaves the server unless online mode is on.
  </div>
</div>
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
  // Financial figures render with exactly 2 decimals per house style.
  function money(n){ return "$"+Number(n==null?0:n).toLocaleString(
    undefined, {minimumFractionDigits:2, maximumFractionDigits:2}); }

  function healthClass(pct){ return pct>=99?"good":(pct>=90?"warn":"bad"); }

  function render(s){
    var cards=[
      ["Rows in", fmt(s.rows_in), ""],
      ["Rows out", fmt(s.rows_out), ""],
      ["Duplicates removed", fmt(s.duplicates_removed),
        s.duplicates_removed>0?"warn":"good"],
      ["NPI health", (s.health_pct!=null?s.health_pct:0)+"%",
        healthClass(s.health_pct)],
      ["Billing-NPI issues", fmt(s.billing_issues),
        s.billing_issues>0?"bad":"good"],
      ["Cells trimmed", fmt(s.cells_trimmed), ""]
    ];
    $("npi-cards").innerHTML = cards.map(function(c){
      return '<div class="npi-card"><div class="k">'+c[0]+
        '</div><div class="v '+c[2]+'">'+c[1]+'</div></div>';
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
      var isBilling=(col===s.billing_column);
      rows+='<tr><td class="'+(isBilling?'billing':'')+'">'+col+
        (isBilling?'<span class="npi-badge">billing</span>':'')+'</td>'+
        '<td class="num">'+fmt(cells)+'</td>'+
        '<td class="num">'+fmt(c.valid)+'</td>'+
        '<td class="num">'+fmt(c.blank)+'</td>'+
        '<td class="num">'+fmt(c.malformed)+'</td>'+
        '<td class="num">'+fmt(c.checksum)+'</td>'+
        '<td class="num">'+pct+'%</td></tr>';
    });
    if(!rows){ rows='<tr><td colspan="7" style="color:var(--ink-2)">'+
      'No NPI column detected in this file.</td></tr>'; }
    $("npi-col-rows").innerHTML=rows;
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
    renderDeep(s.deep, s.download, s.deep_workbook_name);
    renderCompliance(s.compliance);
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
    var xbtn=$("npi-dl-xlsx");
    if(s.workbook_name){
      xbtn.setAttribute("href", s.download+"?fmt=xlsx");
      xbtn.setAttribute("download", s.workbook_name);
      xbtn.style.display="";
    } else { xbtn.style.display="none"; }
    var cbtn=$("npi-dl-companion");
    if(s.companion_name){
      cbtn.setAttribute("href", s.download+"?fmt=companion");
      cbtn.setAttribute("download", s.companion_name);
      cbtn.style.display="";
    } else { cbtn.style.display="none"; }
    var lbtn=$("npi-dl-changelog");
    if(s.changelog_name){
      lbtn.setAttribute("href", s.download+"?fmt=changelog");
      lbtn.setAttribute("download", s.changelog_name);
      lbtn.style.display="";
    } else { lbtn.style.display="none"; }
    var bbtn=$("npi-dl-bundle");
    bbtn.setAttribute("href", s.download+"?fmt=bundle");
    bbtn.setAttribute("download", "npi_clean_bundle.zip");
    var dbtn=$("npi-dl-dict");
    if(s.dictionary && s.dictionary.length){
      dbtn.setAttribute("href", s.download+"?fmt=dictionary");
      dbtn.setAttribute("download", "data_dictionary.csv");
      dbtn.style.display="";
    } else { dbtn.style.display="none"; }

    if(currentJobId){ $("npi-analyze").setAttribute("href",
      "/npi-cleaner/analyze/"+currentJobId);
      $("npi-exec").setAttribute("href",
      "/npi-cleaner/download/"+currentJobId+"?fmt=exec"); }

    var rn=$("npi-recovered-note");
    if(s.recovered_written>0){
      rn.innerHTML='<div class="npi-recovered">✓ '+fmt(s.recovered_written)+
        ' row'+(s.recovered_written===1?'':'s')+' had a billing NPI recovered '+
        'from NPPES — written to a new <code>recovered_billing_npi</code> '+
        'column in the download (originals preserved).</div>';
    } else { rn.innerHTML=""; }

    var dn=$("npi-deid-note");
    if(dn){
      if(s.deid && s.deid.cells>0){
        dn.innerHTML='<div class="npi-recovered">🛡 PHI de-identified — '+
          fmt(s.deid.cells)+' patient cell'+(s.deid.cells===1?'':'s')+
          ' masked across '+(s.deid.columns?s.deid.columns.length:0)+
          ' column'+((s.deid.columns&&s.deid.columns.length===1)?'':'s')+' ('+
          (s.deid.columns?s.deid.columns.map(esc).join(', '):'')+
          '). Provider NPI &amp; name left intact for recovery.</div>';
      } else if(s.deid){
        dn.innerHTML='<div class="npi-muted" style="margin-top:6px">'+
          'De-identify was on, but no patient-scoped PHI columns were detected '+
          'in this file — nothing to mask.</div>';
      } else { dn.innerHTML=""; }
    }

    // Always land on the Overview tab for a fresh result.
    document.querySelectorAll(".npi-tab").forEach(function(b){
      b.classList.toggle("is-active", b.getAttribute("data-tab")==="overview"); });
    document.querySelectorAll(".npi-panel").forEach(function(p){
      p.classList.toggle("is-active", p.getAttribute("data-panel")==="overview"); });
    hide(stUp); hide(stPr); hide(stErr); show(stRes);
  }

  function flagRow(label, sub, count){
    var hit = count>0;
    return '<div class="npi-flag"><div class="lab">'+label+
      (sub?'<small>'+sub+'</small>':'')+'</div>'+
      '<div class="cnt '+(hit?'hit':'clear')+'">'+
      (hit?fmt(count)+' flagged':'clear')+'</div></div>';
  }

  function dollars(v){
    if(v==null) return "";
    if(v>=1e6) return "$"+(v/1e6).toFixed(2)+"M";
    if(v>=1e3) return "$"+(v/1e3).toFixed(1)+"K";
    return "$"+Math.round(v);
  }

  function drillTable(drill){
    var cols=drill.columns||[], rows=drill.rows||[];
    var h='<table><thead><tr>';
    cols.forEach(function(c){ h+='<th>'+esc(c.replace(/_/g," "))+'</th>'; });
    h+='</tr></thead><tbody>';
    rows.forEach(function(r){
      h+='<tr>'; cols.forEach(function(c){ h+='<td>'+esc(r[c])+'</td>'; }); h+='</tr>';
    });
    h+='</tbody></table><div class="npi-muted" style="margin:2px 0">Showing up '+
      'to 15 offending rows.</div>';
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
    "drg-pad":"Restored dropped leading zeros in MS-DRGs (87 → 087)"};

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
      claimsHtml='<div class="ck-section-header" style="margin-top:20px">'+
        '<h3 style="margin:0">Claim rollup</h3></div>'+
        '<div class="npi-muted">'+fmt(claims.n_claims)+' distinct claims ('+
        esc(claims.column)+') · '+claims.avg_lines+' lines/claim avg · '+
        fmt(claims.max_lines)+' max'+
        (claims.charge?(' · per-claim charge '+
          money(claims.charge.median)+' median / '+money(claims.charge.max)+
          ' max'):'')+
        (claims.truncated?' · (rollup capped at 50,000 claims)':'')+
        '</div>';
    }
    var html="";
    if(keys.length){
      keys.sort(function(a,b){return repairs[b]-repairs[a];});
      html+='<div class="ck-section-header" style="margin-top:20px">'+
        '<h3 style="margin:0">Cleaning fixes applied</h3></div>'+
        '<div class="npi-muted">'+fmt(total)+' deterministic normalizations written '+
        'to the cleaned file (originals were replaced in place).</div>';
      keys.forEach(function(k){
        html+=flagRow(REPAIR_LABELS[k]||k, '<span class="npi-pill">'+k+'</span>', repairs[k]);
      });
    }
    if(ckeys.length){
      ckeys.sort(function(a,b){return credentials[b]-credentials[a];});
      html+='<div class="ck-section-header" style="margin-top:20px">'+
        '<h3 style="margin:0">Credential mix</h3></div>'+
        '<div class="npi-muted">Clinical credentials parsed from provider-name '+
        'columns (cells naming each credential).</div><div style="margin-top:8px">'+
        ckeys.map(function(k){
          return '<span class="npi-pill" style="margin:0 6px 6px 0;display:inline-block">'+
            esc(k)+' · '+fmt(credentials[k])+'</span>';
        }).join("")+'</div>';
    }
    if(specs.length){
      html+='<div class="ck-section-header" style="margin-top:20px">'+
        '<h3 style="margin:0">Specialty mix</h3></div>'+
        '<div class="npi-muted">Top provider taxonomy codes on the cleaned rows '+
        '(NUCC display names where known).</div><div style="margin-top:8px">'+
        specs.map(function(s){
          return '<span class="npi-pill" style="margin:0 6px 6px 0;display:inline-block">'+
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
    var c=sev==="critical"?"#b5321e":(sev==="warning"?"#b8732a":"#5b6770");
    return '<span style="display:inline-block;font-size:10px;font-weight:700;'+
      'text-transform:uppercase;letter-spacing:.05em;color:#fff;background:'+c+
      ';border-radius:4px;padding:1px 6px;margin-right:6px;vertical-align:middle">'+
      sev+'</span>';
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
    var html='<div class="ck-section-header" style="margin-top:20px">'+
      '<h3 style="margin:0">Data sanity flags</h3></div>'+
      '<div class="npi-muted">Findings are reported, never auto-changed — '+
      'each has a per-rule worklist download of just the flagged rows.</div>';
    keys.forEach(function(k){
      var info=RULE_INFO[k]||{};
      var label=(info.title||SANITY_LABELS[k]||k);
      if(acc[k]){ label='<span style="opacity:.55">'+label+
        ' <em style="font-size:11px">(accepted — not graded)</em></span>'; }
      var sub=sevChip(info.severity||"info")+'<span class="npi-pill">'+k+'</span>'+
        (info.remediation?('<br><span class="npi-muted">'+esc(info.remediation)+
        '</span>'):'');
      if(worklists && worklists[k] && dl){
        sub+=' <a href="'+dl+'?fmt=worklist&rule='+encodeURIComponent(k)+
          '" download style="font-size:11.5px">⤓ worklist ('+
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
    if(!q){ box.innerHTML='<div class="npi-muted">No quality data.</div>'; return; }
    var tone=q.score>=85?'var(--green-deep,#0c7c66)':
             (q.score>=70?'#b8732a':'#b5321e');
    var html='<div class="ck-section-header"><h3 style="margin:0">'+
      'Data-quality report card</h3></div>'+
      '<div class="npi-muted">Five-dimension grade computed from the counts '+
      'on this page — every number is recomputable from the scorecard.</div>';
    // Trend alerts: regressions vs the previous run of this same file.
    if(s.trend_alerts && s.trend_alerts.length){
      html+='<div class="npi-warn" style="margin-top:10px"><strong>'+
        'Changed since the last run of this file:</strong><ul style='+
        '"margin:6px 0 0 18px;padding:0">'+
        s.trend_alerts.map(function(a){ return '<li>'+esc(a)+'</li>'; })
        .join("")+'</ul></div>';
    }
    // Zip batch: per-file grades (the card above blends all rows).
    if(s.batch && s.batch.length){
      html+='<div class="ck-section-header" style="margin-top:14px">'+
        '<h3 style="margin:0">Batch files</h3></div>'+
        '<div class="npi-muted">Each file was cleaned separately; the '+
        'grade above blends all rows across the batch.</div>'+
        '<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>File</th><th class="num">Rows in</th><th class="num">Rows out</th>'+
        '<th class="num">Repairs</th><th class="num">Findings</th>'+
        '<th class="num">Grade</th></tr></thead><tbody>'+
        s.batch.map(function(b){
          return '<tr><td>'+esc(b.file)+'</td><td class="num">'+
            fmt(b.rows_in)+'</td><td class="num">'+fmt(b.rows_out)+
            '</td><td class="num">'+fmt(b.repairs)+'</td><td class="num">'+
            fmt(b.findings)+'</td><td class="num">'+esc(b.letter)+' · '+
            b.score+'</td></tr>';
        }).join("")+'</tbody></table>';
    }
    html+='<div class="npi-cards" style="margin-top:12px"><div class="npi-card">'+
      '<div class="k">Overall grade</div><div class="v" style="color:'+tone+'">'+
      q.letter+' · '+q.score+'</div></div></div>';
    // Dimension bars.
    html+='<div style="max-width:640px;margin-top:10px">';
    Object.keys(DIM_LABELS).forEach(function(k){
      var v=(q.dimensions&&q.dimensions[k]!=null)?q.dimensions[k]:0;
      var lab=DIM_LABELS[k];
      html+='<div style="display:flex;align-items:center;gap:10px;margin:7px 0">'+
        '<div style="width:130px;font-size:12.5px;font-weight:640">'+lab[0]+'</div>'+
        '<div style="flex:1;height:9px;border-radius:5px;background:'+
        'color-mix(in srgb,var(--ink,#11201c) 8%,transparent);overflow:hidden">'+
        '<div style="width:'+Math.max(2,Math.min(100,v))+'%;height:100%;background:'+
        (v>=85?'var(--green,#0c7c66)':(v>=70?'#b8732a':'#b5321e'))+'"></div></div>'+
        '<div class="num" style="width:52px;text-align:right;font-size:12.5px">'+
        v.toFixed(1)+'%</div>'+
        '<div class="npi-muted" style="width:280px;font-size:11.5px">'+lab[1]+'</div></div>';
    });
    html+='</div>';
    // Per-column fill-rate profile: only columns with blanks, worst first.
    var fills=(s.fill_rates||[]).filter(function(f){return f.pct<100;});
    if(fills.length){
      fills.sort(function(a,b){return a.pct-b.pct;});
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'Columns with blanks</h3></div>'+
        '<div class="npi-muted">Fill rate per column (only columns below 100% '+
        'shown, emptiest first).</div>';
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>Column</th><th class="num">Filled rows</th><th class="num">% filled</th>'+
        '</tr></thead><tbody>';
      fills.slice(0,12).forEach(function(f){
        var t=f.pct>=90?'':(f.pct>=60?' style="color:#b8732a"':' style="color:#b5321e"');
        html+='<tr><td>'+esc(f.column)+'</td><td class="num">'+fmt(f.filled)+
          '</td><td class="num"'+t+'>'+f.pct.toFixed(1)+'%</td></tr>';
      });
      html+='</tbody></table>';
      if(fills.length>12){ html+='<div class="npi-muted" style="margin-top:4px">'+
        fmt(fills.length-12)+' more columns have blanks — see the .xlsx report.</div>'; }
    }
    // Payer-name variant clusters.
    var p=s.payer;
    if(p && p.multi_spelling && p.multi_spelling.length){
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'Payer spellings to reconcile</h3></div>'+
        '<div class="npi-muted">'+esc(p.column)+' has '+fmt(p.distinct_raw)+
        ' raw spellings across '+fmt(p.clusters)+' payer groups. Clusters below '+
        'contain 2+ spellings of what looks like the same payer (reported only '+
        '— nothing was rewritten).</div>';
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>Payer group</th><th class="num">Rows</th><th>Spellings seen</th>'+
        '</tr></thead><tbody>';
      p.multi_spelling.forEach(function(c){
        html+='<tr><td>'+esc(c.canonical)+'</td><td class="num">'+fmt(c.total)+
          '</td><td>'+c.variants.map(function(v){
            return esc(v.value)+' <span class="npi-muted">('+fmt(v.count)+')</span>';
          }).join(' · ')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    // Per-code charge outliers.
    if(s.outliers && s.outliers.length){
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'Charge outliers by procedure code</h3></div>'+
        '<div class="npi-muted">Charges beyond 3×IQR fences within their HCPCS '+
        'code (codes seen 10+ times). Same quantile math as the box plot on '+
        'the analysis page.</div>';
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>HCPCS</th><th class="num">Lines</th><th class="num">Outliers</th>'+
        '<th class="num">Median</th><th class="num">Max seen</th></tr></thead><tbody>';
      s.outliers.forEach(function(o){
        html+='<tr><td>'+esc(o.code)+'</td><td class="num">'+fmt(o.n)+
          '</td><td class="num">'+fmt(o.outliers)+'</td><td class="num">'+
          dollars(o.median)+'</td><td class="num">'+dollars(o.max)+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    // Top denial / adjustment reasons.
    if(s.denials && s.denials.top && s.denials.top.length){
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'Top denial / adjustment reasons</h3></div>'+
        '<div class="npi-muted">'+esc(s.denials.column)+' — '+fmt(s.denials.distinct)+
        ' distinct codes. Highest-volume reasons below (CARC codes).'+
        (s.denials.preventable_pct!=null?(' <strong>'+s.denials.preventable_pct+
        '% of the classified volume was preventable</strong> by a '+
        'pre-submission screen.'):'')+'</div>';
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>Code</th><th class="num">Rows</th><th>Playbook</th><th>What to do</th>'+
        '</tr></thead><tbody>';
      var CAT_COLOR={preventable:'#b5321e',process:'#b8732a',
        contractual:'#5b6770','patient-responsibility':'#5b6770'};
      s.denials.top.forEach(function(d){
        var cat=d.category?('<span style="display:inline-block;font-size:10px;'+
          'font-weight:700;text-transform:uppercase;letter-spacing:.05em;'+
          'color:#fff;background:'+(CAT_COLOR[d.category]||'#5b6770')+
          ';border-radius:4px;padding:1px 7px">'+esc(d.category)+'</span>'):'';
        var act=d.action?esc(d.action)+(d.linked_rule?(' <span class="npi-pill">'+
          esc(d.linked_rule)+'</span>'):''):'';
        html+='<tr><td>'+esc(d.code)+'</td><td class="num">'+fmt(d.count)+
          '</td><td>'+cat+'</td><td style="font-size:12px">'+act+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    // Per-payer quality split — which payer's feed is dirtiest.
    if(s.payer_quality && s.payer_quality.length){
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'Quality by payer</h3></div>'+
        '<div class="npi-muted">Share of each payer&#39;s rows with at '+
        'least one finding, and that payer&#39;s top rules.</div>';
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>Payer</th><th class="num">Rows</th><th class="num">Flagged</th>'+
        '<th class="num">Clean %</th><th>Top rules</th></tr></thead><tbody>';
      s.payer_quality.forEach(function(p){
        var tone=p.clean_pct>=90?'var(--green-deep,#0c7c66)':
                 (p.clean_pct>=70?'#b8732a':'#b5321e');
        var wl=(p.flagged>0 && s.download)?(' · <a href="'+s.download+
          '?fmt=worklist&payer='+encodeURIComponent(p.payer)+
          '" download>worklist</a>'):'';
        html+='<tr><td>'+esc(p.payer)+'</td><td class="num">'+fmt(p.rows)+
          '</td><td class="num">'+fmt(p.flagged)+'</td>'+
          '<td class="num" style="color:'+tone+';font-weight:640">'+
          p.clean_pct+'%</td><td style="font-size:12px">'+
          (p.top_rules||[]).map(function(t){
            return esc(t.rule)+' ('+fmt(t.n)+')';
          }).join(", ")+wl+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    // Structural findings.
    var st=s.structure;
    if(st && (st.duplicate_headers || st.empty_columns)){
      html+='<div class="ck-section-header" style="margin-top:22px"><h3 style="margin:0">'+
        'File structure</h3></div>';
      if(st.duplicate_headers){
        html+='<div class="npi-warn" style="margin-top:6px">Duplicate column '+
          'headers (mapping is ambiguous): '+
          st.duplicate_headers.map(esc).join(', ')+'</div>';
      }
      if(st.empty_columns){
        html+='<div class="npi-warn" style="margin-top:6px">Columns that are '+
          '100% empty: '+st.empty_columns.map(esc).join(', ')+'</div>';
      }
    }
    // Audit trail summary.
    if(s.changes_logged){
      html+='<div class="npi-muted" style="margin-top:18px">🧾 '+
        fmt(s.changes_logged)+' cell'+(s.changes_logged===1?'':'s')+
        ' changed in total — the full before/after audit trail is on the '+
        'Downloads tab'+(s.changelog_truncated?' (log capped at 20,000 entries)':'')+'.</div>';
    }
    box.innerHTML=html;
  }

  function renderAdvanced(adv){
    var box=$("npi-advanced");
    if(!adv){ box.innerHTML=""; return; }
    var html='<div class="npi-adv">';
    html+='<div class="ck-section-header"><h3 style="margin:0">'+
      'Coding, consistency &amp; issue analysis</h3></div>';
    html+='<div class="eng">real engine · '+(adv.engine||'')+
      (adv.repairs?(' · '+fmt(adv.repairs)+' deterministic repairs applied'):'')+
      '</div>';

    var issues=adv.issues||[];
    var irows=adv.issue_rows||{};
    if(issues.length){
      html+='<table class="npi-tbl" style="margin-top:8px"><thead><tr>'+
        '<th>Issue</th><th class="num">Rows</th><th class="num">% rows</th>'+
        '<th class="num">$ exposure</th><th>Signal</th></tr></thead><tbody>';
      issues.forEach(function(it,ix){
        var sig=it.systematic||"";
        var tone=sig.indexOf("systematic")===0?"bad":
                 (sig.indexOf("random")===0?"":"warn");
        var drill=irows[it.issue];
        html+='<tr class="'+(drill?'npi-drill':'')+'" data-drill="'+ix+'">'+
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
      html+='</tbody></table>';
    }

    var scr=adv.screens||{};
    var keys=Object.keys(scr);
    if(keys.length){
      html+='<div style="margin:14px 0 4px;font-weight:640;font-size:13px">'+
        'Screens run</div>';
      keys.forEach(function(k){
        html+=flagRow(k.replace(/_/g,' '), "", scr[k]);
      });
    }

    if(adv.suggestions_n>0){
      html+='<div class="npi-nppes-note" style="margin-top:12px">'+
        fmt(adv.suggestions_n)+' row-level suggested corrections available '+
        '(current → suggested, with provenance) — download the corrections '+
        'companion below.</div>';
    }
    var ext=adv.extended||[];
    if(ext.length){
      html+='<div style="margin:16px 0 4px;font-weight:640;font-size:13px">'+
        'Extended anomaly screens</div>';
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
    var html='<div class="npi-adv"><div class="ck-section-header">'+
      '<h3 style="margin:0">Live NPPES verification &amp; recovery</h3></div>';
    if(n.error){
      html+='<div class="npi-warn">NPPES cross-check error: '+n.error+'</div></div>';
      box.innerHTML=html; return;
    }
    if(n.note && !n.verify){
      html+='<div class="npi-nppes-note">'+n.note+'</div></div>';
      box.innerHTML=html; return;
    }
    html+='<div class="eng">real connection · '+(n.source||'NPPES')+'</div>';

    var v=n.verify||{};
    html+='<div class="npi-cards" style="margin:10px 0 4px">'+
      '<div class="npi-card"><div class="k">NPIs verified</div>'+
        '<div class="v">'+fmt(v.checked)+'</div></div>'+
      '<div class="npi-card"><div class="k">Active in NPPES</div>'+
        '<div class="v good">'+fmt(v.active)+'</div></div>'+
      '<div class="npi-card"><div class="k">Not found / deactivated</div>'+
        '<div class="v '+((v.not_found||0)>0?'bad':'good')+'">'+
        fmt(v.not_found)+'</div></div></div>';
    if(v.note){ html+='<div class="npi-nppes-note">'+v.note+'</div>'; }

    var r=n.recover||{};
    var matches=(r.matches||[]).filter(function(m){
      return m.candidates && m.candidates.length; });
    if(matches.length){
      html+='<div style="margin:14px 0 4px;font-weight:640;font-size:13px">'+
        'Recovered NPI candidates ('+matches.length+')</div>';
      matches.forEach(function(m){
        var c=m.candidates[0];
        html+='<div class="npi-cand"><span class="q">'+m.query+
          (m.state?' · '+m.state:'')+'</span><span class="arrow">→</span>'+
          '<code>'+c.npi+'</code> '+c.name+
          ' <span class="rowref">(row '+m.row+')</span></div>';
      });
    } else if(r.note){
      html+='<div class="npi-nppes-note">'+r.note+'</div>';
    }
    html+='</div>';
    box.innerHTML=html;
  }

  // Entity-escape INCLUDING quotes — names (profiles, templates, files)
  // land in attribute contexts, and the textContent trick left " alone.
  function esc(s){ return String(s==null?"":s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

  function popHead(t, sub){
    return '<div class="ck-section-header" style="margin-top:18px">'+
      '<h3 style="margin:0">'+t+'</h3></div>'+
      (sub?'<div class="npi-muted" style="font-size:12px;margin:4px 0 8px">'+
        sub+'</div>':'');
  }

  function renderPopulation(pop, download){
    var box=$("npi-pop");
    if(!pop){
      box.innerHTML='<div class="npi-muted">No population marts for this '+
        'run — they need service/claim columns (revenue code, type of '+
        'bill, POS, HCPCS, patient id, service dates, diagnoses). '+
        'Streaming (10 GB) runs skip them by design.</div>';
      return;
    }
    var h="";
    if(pop.service_mix){
      h+=popHead("Service-category mix", "Every line classified by the "+
        "institutional-first ladder (type of bill → revenue code → place "+
        "of service → HCPCS range). Unclassified: "+
        esc(pop.service_mix.unclassified_pct)+"%.");
      h+='<table class="npi-tbl"><thead><tr><th>Category</th>'+
        '<th>Subcategory</th><th class="num">Lines</th>'+
        '<th class="num">% of file</th><th class="num">Charges</th>'+
        '</tr></thead><tbody>';
      pop.service_mix.categories.slice(0,14).forEach(function(c){
        h+='<tr><td>'+esc(c.category)+'</td><td>'+esc(c.subcategory)+
          '</td><td class="num">'+fmt(c.rows)+'</td><td class="num">'+
          esc(c.pct)+'%</td><td class="num">$'+fmt(c.charges)+'</td></tr>';
      });
      h+='</tbody></table>';
    }
    if(pop.encounters){
      var e=pop.encounters;
      h+=popHead("Encounters", fmt(e.n_encounters)+" visits grouped from "+
        fmt(e.n_patients)+" patients (same patient, same setting, service "+
        "dates chaining with gaps ≤ 1 day"+
        (e.records_truncated?"; download capped":"")+").");
      h+='<table class="npi-tbl"><thead><tr><th>Setting</th>'+
        '<th class="num">Encounters</th><th class="num">Avg lines</th>'+
        '<th class="num">Charges</th></tr></thead><tbody>';
      (e.by_category||[]).forEach(function(c){
        h+='<tr><td>'+esc(c.category)+'</td><td class="num">'+
          fmt(c.encounters)+'</td><td class="num">'+esc(c.avg_lines)+
          '</td><td class="num">$'+fmt(c.charges)+'</td></tr>';
      });
      h+='</tbody></table>';
      if(e.readmissions){
        var r=e.readmissions;
        h+='<div style="margin-top:8px;font-size:12.5px">30-day inpatient '+
          'readmissions: <strong>'+fmt(r.readmissions_30d)+'</strong> of '+
          fmt(r.inpatient_stays)+' stays ('+esc(r.rate_pct)+'%).</div>';
      }
      h+='<div style="margin-top:8px"><a class="npi-dl npi-dl-alt" '+
        'href="'+esc(download)+'?fmt=encounters" download>⤓ Encounters '+
        'roll-up (.csv)</a></div>';
    }
    if(pop.conditions){
      var c0=pop.conditions;
      h+=popHead("Chronic-condition prevalence",
        (c0.patient_grouping?fmt(c0.patients)+" distinct patients":
         "no patient column — per-row counts")+
        " · CCW-style ICD-10 prefix groups; reporting only, never a flag.");
      h+='<table class="npi-tbl"><thead><tr><th>Condition</th>'+
        '<th class="num">Patients</th><th class="num">Prevalence</th>'+
        '<th class="num">Rows</th></tr></thead><tbody>';
      c0.prevalence.slice(0,12).forEach(function(p){
        h+='<tr><td>'+esc(p.condition)+'</td><td class="num">'+
          fmt(p.patients)+'</td><td class="num">'+esc(p.pct)+
          '%</td><td class="num">'+fmt(p.rows)+'</td></tr>';
      });
      h+='</tbody></table>';
      if(c0.multimorbidity){
        var mm=c0.multimorbidity;
        h+='<div style="margin-top:6px;font-size:12.5px" class="npi-muted">'+
          'Conditions per patient — 0: '+fmt(mm["0"])+' · 1: '+
          fmt(mm["1"])+' · 2: '+fmt(mm["2"])+' · 3+: '+fmt(mm["3+"])+
          '</div>';
      }
    }
    if(pop.volume){
      h+=popHead("Volume integrity (data loss over time)",
        "Rows, charges and patients by service month — a cliff usually "+
        "means a missing extract, not real utilization."+
        (pop.volume.median_observed_pmpm != null
          ? " Median observed PMPM (charges per patient with claims that "+
            "month): $"+fmt(pop.volume.median_observed_pmpm)+"."
          : ""));
      (pop.volume.alerts||[]).forEach(function(a){
        h+='<div class="npi-warn">'+esc(a)+'</div>';
      });
      var months=pop.volume.months||[];
      var maxR=1;
      months.forEach(function(m){ if(m.rows>maxR) maxR=m.rows; });
      h+='<div style="display:flex;align-items:flex-end;gap:3px;'+
        'height:80px;margin-top:8px">';
      months.slice(-36).forEach(function(m){
        var pct=Math.max(3, Math.round(100*m.rows/maxR));
        h+='<div title="'+esc(m.month)+': '+fmt(m.rows)+' rows" '+
          'style="flex:1;background:var(--green-deep,#0c7c66);'+
          'opacity:.75;height:'+pct+'%"></div>';
      });
      h+='</div><div class="npi-muted" style="font-size:11px;'+
        'margin-top:2px">'+esc(months.length?months[0].month:"")+
        ' → '+esc(months.length?months[months.length-1].month:"")+'</div>';
    }
    if(pop.coding_intensity){
      var ci=pop.coding_intensity;
      h+=popHead("E&amp;M coding intensity",
        fmt(ci.established_visits)+" established office visits "+
        "(99211–99215) · file average level "+esc(ci.file_avg_level)+
        " · "+fmt(ci.providers_rated)+" providers with ≥ 20 visits rated "+
        "against the file's own mix.");
      if(ci.outliers && ci.outliers.length){
        h+='<table class="npi-tbl"><thead><tr><th>Billing NPI</th>'+
          '<th class="num">Visits</th><th class="num">Avg level</th>'+
          '<th class="num">Level 4–5 share</th></tr></thead><tbody>';
        ci.outliers.forEach(function(o){
          h+='<tr><td>'+esc(o.npi)+'</td><td class="num">'+fmt(o.visits)+
            '</td><td class="num">'+esc(o.avg_level)+
            '</td><td class="num">'+esc(o.level_4_5_pct)+'%</td></tr>';
        });
        h+='</tbody></table><div class="npi-muted" style="font-size:12px;'+
          'margin-top:4px">High-intensity coders vs this file’s mix — '+
          'a documentation-review starting point, not an accusation.</div>';
      } else {
        h+='<div class="npi-muted">No provider codes materially hotter '+
          'than the file’s own mix.</div>';
      }
    }
    box.innerHTML = h ||
      '<div class="npi-muted">Not enough claim columns for any mart.</div>';
  }

  function renderSuggestions(adv){
    var box=$("npi-suggestions");
    if(!adv || !adv.suggestions_sample || !adv.suggestions_sample.length){
      box.innerHTML=""; return; }
    var recs=adv.suggestions_sample, cols=Object.keys(recs[0]);
    var html='<div class="ck-section-header" style="margin-top:20px">'+
      '<h3 style="margin:0">Suggested corrections</h3></div>'+
      '<div class="npi-muted">Showing '+recs.length+' of '+fmt(adv.suggestions_n)+
      ' — full list in the corrections companion (Downloads tab).</div>'+
      '<div style="overflow-x:auto"><table class="npi-tbl"><thead><tr>';
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
    var html='<div class="ck-section-header" style="margin-top:6px">'+
      '<h3 style="margin:0">Compliance screening</h3></div>';
    comp.forEach(function(c){
      if(!c.label){ return; }
      var flag=(c.excluded>0)||(c.opted_out>0);
      html+='<div class="npi-conn"><div class="top">'+
        '<span class="nm">'+esc(c.label)+'</span>';
      if(c.id==="oig_leie"){
        html+='<span class="cnt '+(c.excluded>0?"":"")+'" style="'+
          (c.excluded>0?"color:#a8331f":"")+'">'+
          (c.available?(fmt(c.excluded)+' excluded'):'not loaded')+'</span>';
      } else {
        html+='<span class="cnt" style="'+(flag?"color:#a8331f":"")+'">'+
          (c.available?(fmt(c.checked)+' screened'):'offline')+'</span>';
      }
      html+='</div><div class="src">'+esc(c.source||"")+'</div>';
      if(c.matches && c.matches.length){
        html+='<div class="nt" style="color:#a8331f">Excluded NPIs: '+
          c.matches.slice(0,8).map(function(m){return esc(m.npi);}).join(", ")+'</div>';
      }
      html+='<div class="nt">'+esc(c.note||"")+'</div></div>';
    });
    box.innerHTML=html;
  }

  function renderDeep(deep, dl, wbName){
    var box=$("npi-deep");
    if(!deep){ box.innerHTML=""; return; }
    var html='<div class="npi-conn"><div class="top">'+
      '<span class="nm">Deep recovery — full v49 pipeline</span></div>';
    if(deep.ok){
      html+='<div class="nt" style="color:var(--green-deep,#0c7c66)">✓ '+
        'Completed. '+(deep.stats&&Object.keys(deep.stats).length?
        Object.keys(deep.stats).length+' pipeline stats produced.':'')+'</div>';
      if(wbName){
        html+='<div style="margin-top:8px"><a class="npi-dl" href="'+dl+
          '?fmt=deep" download="'+esc(wbName)+'">⤓ Download recovered workbook (.xlsx)</a></div>';
      }
    } else {
      html+='<div class="npi-warn" style="margin-top:6px">'+esc(deep.error||
        "Deep recovery did not complete.")+'</div>';
    }
    html+='</div>';
    box.innerHTML=html;
  }

  function renderConnectors(conns){
    var box=$("npi-connectors");
    if(!conns || !conns.length){ box.innerHTML=""; return; }
    var html='<div class="ck-section-header" style="margin-top:20px">'+
      '<h3 style="margin:0">Drug connectors (RxNorm · openFDA)</h3></div>';
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
    var html='<div class="ck-section-header" style="margin-top:22px">'+
      '<h3 style="margin:0">Connections available</h3></div>'+
      '<div class="npi-muted">'+cat.length+' public-data sources are wired into '+
      'PE&nbsp;Desk and can be enabled for enrichment.</div><div class="npi-cat">';
    cat.forEach(function(s){
      var free=(s.cost||"").indexOf("free")===0;
      html+='<div class="c"><div class="n">'+esc(s.name)+'</div>'+
        '<div class="o">'+esc(s.operator||"")+
        ' · <span class="'+(free?"free":"")+'">'+esc(s.cost||"")+'</span></div></div>';
    });
    html+='</div>';
    box.innerHTML=html;
  }

  function initTabs(){
    if(window.__npiTabsInit) return; window.__npiTabsInit=true;
    document.addEventListener("click", function(e){
      if(!e.target.closest) return;
      var t=e.target.closest(".npi-tab");
      if(t){
        var name=t.getAttribute("data-tab");
        document.querySelectorAll(".npi-tab").forEach(function(b){
          b.classList.toggle("is-active", b===t); });
        document.querySelectorAll(".npi-panel").forEach(function(p){
          p.classList.toggle("is-active", p.getAttribute("data-panel")===name); });
        return;
      }
      // Drill-down: clicking an issue row toggles its offending-rows table.
      var d=e.target.closest(".npi-drill");
      if(d){
        var ix=d.getAttribute("data-drill");
        var rows=document.querySelector('[data-drillrows="'+ix+'"]');
        if(rows){ rows.classList.toggle("npi-hidden");
          d.classList.toggle("open", !rows.classList.contains("npi-hidden")); }
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
      box.innerHTML='<div class="npi-muted">Clean the matching remittance '+
        '(835) or claims (837) file next and a <strong>reconcile</strong> '+
        'option will appear here.</div>';
      return;
    }
    var isRemit=(s.delimiter||"").indexOf("835")>=0;
    box.innerHTML='<div class="ck-section-header"><h3 style="margin:0">'+
      'Reconcile against an earlier run</h3></div>'+
      '<div class="npi-muted">Match claims to remittance on claim id: '+
      'unpaid claims, paid-vs-billed variance, denial mix.</div>'+
      '<div style="margin-top:8px">'+
      '<select id="npi-rec-other" style="font-size:12.5px;max-width:260px">'+
      others.map(function(j){
        return '<option value="'+esc(j.id)+'">'+esc(j.name)+'</option>';
      }).join("")+'</select> '+
      '<label class="npi-muted" style="margin-left:8px">'+
      '<input type="checkbox" id="npi-rec-remit"'+(isRemit?' checked':'')+
      '> this run is the remittance (835) side</label> '+
      '<button type="button" class="npi-dl" id="npi-rec-go" '+
      'style="font-size:12.5px;padding:5px 12px;margin-left:8px">'+
      'Reconcile</button></div><div id="npi-rec-out" '+
      'style="margin-top:10px"></div>';
    $("npi-rec-go").addEventListener("click", function(){
      var other=$("npi-rec-other").value;
      var thisIsRemit=$("npi-rec-remit").checked;
      var body=thisIsRemit?{a:other, b:currentJobId}
                          :{a:currentJobId, b:other};
      $("npi-rec-out").innerHTML='<div class="npi-muted">Matching…</div>';
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
    var h='<div style="font-size:13px;margin-bottom:6px"><strong>'+
      fmt(r.matched)+'</strong> of '+fmt(r.claims_a)+' claims matched ('+
      r.match_rate_pct+'%) · <strong>'+fmt(r.unpaid_count)+
      '</strong> with no remittance · billed '+money(r.billed_matched)+
      ' vs paid '+money(r.paid_matched)+' on matched claims (variance '+
      money(r.variance_total)+')'+
      (r.orphan_remits_count?(' · '+fmt(r.orphan_remits_count)+
      ' remit claim(s) not in the claims run'):'')+'</div>';
    if(r.unpaid && r.unpaid.length){
      h+='<div style="font-weight:640;font-size:12.5px;margin-top:6px">'+
        'Claims with no remittance (top by billed)</div>'+
        '<table class="npi-tbl"><thead><tr><th>Claim</th>'+
        '<th class="num">Billed</th><th class="num">Lines</th></tr></thead>'+
        '<tbody>'+r.unpaid.slice(0,8).map(function(u){
          return '<tr><td>'+esc(u.claim)+'</td><td class="num">'+
            money(u.billed)+'</td><td class="num">'+fmt(u.lines)+'</td></tr>';
        }).join("")+'</tbody></table>';
    }
    if(r.top_variance && r.top_variance.length){
      h+='<div style="font-weight:640;font-size:12.5px;margin-top:10px">'+
        'Largest paid-vs-billed variance (matched claims)</div>'+
        '<table class="npi-tbl"><thead><tr><th>Claim</th>'+
        '<th class="num">Billed</th><th class="num">Paid</th>'+
        '<th class="num">Δ</th><th>CARCs</th></tr></thead><tbody>'+
        r.top_variance.slice(0,8).map(function(v){
          return '<tr><td>'+esc(v.claim)+'</td><td class="num">'+
            money(v.billed)+'</td><td class="num">'+money(v.paid)+
            '</td><td class="num">'+money(v.delta)+'</td><td>'+
            (v.carcs||[]).map(esc).join(", ")+'</td></tr>';
        }).join("")+'</tbody></table>';
    }
    if(r.denials && r.denials.length){
      h+='<div style="font-weight:640;font-size:12.5px;margin-top:10px">'+
        'Denial mix (remit side)</div><div style="margin-top:6px">'+
        r.denials.map(function(d){
          return '<span class="npi-pill" style="margin:0 6px 6px 0;'+
            'display:inline-block" title="'+esc(d.action||"")+'">'+
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
          $("npi-bar-fill").style.width=Math.round((j.frac||0)*100)+"%";
          $("npi-bar-msg").textContent=(j.msg||"Working")+" — "+
            Math.round((j.frac||0)*100)+"%";
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
      file.name+" — "+det.headers.length+" columns detected. Adjust any the "+
      "auto-mapper got wrong, then clean.";
    var opts = '<option value="">(auto / none)</option>' +
      det.headers.map(function(h){
        return '<option value="'+encodeURIComponent(h)+'">'+
          h.replace(/</g,"&lt;")+'</option>'; }).join("");
    var html="";
    detectRoles.forEach(function(role){
      var cur = det.mapping[role.key] || "";
      html+='<div class="row'+(cur?' set':'')+'" data-role="'+role.key+'">'+
        '<label>'+role.label+'</label>'+
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
          var c=s==="shipped"?"#0a8a5f":s==="planned"?"#b8732a":
                s==="declined"?"#8a8f98":"#155752";
          return '<span style="color:'+c+';font-weight:600">'+esc(s)+
            '</span>'; };
        box.innerHTML=
          '<div style="font-size:12.5px;font-weight:640;margin-bottom:4px">'+
          'Requested ('+reqs.length+')</div>'+
          reqs.slice(0,8).map(function(q){
            return '<div style="font-size:12.5px;padding:3px 0;'+
              'border-top:1px solid var(--line,#e4e9e6)">'+
              '<span class="npi-muted">['+esc(q.category)+']</span> '+
              esc(q.title)+' — '+chip(q.status)+'</div>';
          }).join("")+
          (reqs.length>8
            ? '<div class="npi-muted" style="font-size:12px;padding-top:3px">'+
              '…and '+(reqs.length-8)+' more</div>'
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
        var h='<table class="npi-tbl"><thead><tr><th>Pack</th>'+
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
            st='<span class="npi-sig" style="color:var(--green-deep,'+
               '#0c7c66);font-weight:600">'+fmt(p.rows)+' rows · '+
               esc(d)+'</span>';
          } else {
            st='<span class="npi-muted">not installed</span>';
          }
          h+='<tr><td><strong>'+esc(p.title)+'</strong><br>'+
            '<span class="npi-muted" style="font-size:11px">'+
            esc(p.license)+'</span></td>'+
            '<td>'+st+'</td>'+
            '<td class="npi-muted" style="font-size:12px">'+
            esc(p.enables)+'</td>'+
            '<td><button class="npi-again npi-ref-pull" data-pack="'+
            esc(p.id)+'">'+(p.installed?"refresh":"pull")+
            '</button></td></tr>';
        });
        h+='</tbody></table>'+
          '<div style="margin-top:8px"><button class="npi-again" '+
          'id="npi-ref-pull-all">Pull everything</button></div>';
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
          return '<div style="break-inside:avoid;margin-bottom:3px" '+
            'title="'+esc(r.description)+'">'+
            '<select data-rule="'+esc(r.id)+'" style="font-size:11px">'+
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
