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
            "Engine: rcm_mc/npi_cleaner/engine.py (stdlib) + the complete "
            "NPI_Recovery_and_Cleaner v49 deterministic engine "
            "(clean_orchestrator.clean_all) on CMS reference tables."),
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
        CSV, TSV, or Excel (.xlsx) · up to 10&nbsp;MB ·
        <a href="/npi-cleaner/sample" class="pick" download>try a sample file</a></div>
    </div>
    <input type="file" id="npi-file" class="npi-hidden"
           accept=".csv,.tsv,.txt,.xlsx,text/csv,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
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
    </div>
  </div>

  <div id="npi-stage-mapping" class="npi-hidden">
    <div class="ck-section-header"><h3 style="margin:0">Confirm columns</h3></div>
    <div class="npi-muted" id="npi-map-file"></div>
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
    </div>
  </div>

  <div id="npi-stage-error" class="npi-hidden">
    <div class="npi-err" id="npi-err-text"></div>
    <button class="npi-again" id="npi-err-again">Try another file</button>
  </div>

  <div id="npi-stage-result" class="npi-hidden">
    <div class="npi-tabs" role="tablist">
      <button class="npi-tab is-active" data-tab="overview">Overview</button>
      <button class="npi-tab" data-tab="issues">Issues &amp; fixes
        <span class="npi-tab-badge" id="tabbadge-issues"></span></button>
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

    <div class="npi-panel" data-panel="issues">
      <div id="npi-advanced"></div>
      <div id="npi-suggestions"></div>
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
        <span class="npi-muted" style="margin-left:10px">Build pivot tables and
          charts from the cleaned data — like a mini Tableau.</span>
      </div>
      <div style="margin-top:8px">
        <a class="npi-dl" id="npi-dl" href="#" download>⤓ Download cleaned CSV</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-xlsx" href="#" download
           style="margin-left:10px">⤓ Download report (.xlsx)</a>
        <a class="npi-dl npi-dl-alt" id="npi-dl-companion" href="#" download
           style="margin-left:10px;display:none">⤓ Corrections companion (.csv)</a>
      </div>
      <div style="margin-top:16px">
        <button class="npi-again" id="npi-again">Clean another file</button>
      </div>
    </div>
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
    renderRepairs(s.repairs, s.repairs_total);
    renderSanity(s.sanity);

    renderAdvanced(s.advanced);
    renderSuggestions(s.advanced);
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

    if(currentJobId){ $("npi-analyze").setAttribute("href",
      "/npi-cleaner/analyze/"+currentJobId); }

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
    "ndc-normalize-11":"Normalized NDC to 11-digit billing format"};

  function renderRepairs(repairs, total){
    var box=$("npi-repairs");
    var keys=repairs?Object.keys(repairs):[];
    if(!keys.length){ box.innerHTML=""; return; }
    keys.sort(function(a,b){return repairs[b]-repairs[a];});
    var html='<div class="ck-section-header" style="margin-top:20px">'+
      '<h3 style="margin:0">Cleaning fixes applied</h3></div>'+
      '<div class="npi-muted">'+fmt(total)+' deterministic normalizations written '+
      'to the cleaned file (originals were replaced in place).</div>';
    keys.forEach(function(k){
      html+=flagRow(REPAIR_LABELS[k]||k, '<span class="npi-pill">'+k+'</span>', repairs[k]);
    });
    box.innerHTML=html;
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
    "zip-state-mismatch":"ZIP prefix disagrees with the state code (verify address at source)"};
  function renderSanity(sanity){
    var box=$("npi-sanity");
    var keys=sanity?Object.keys(sanity):[];
    if(!keys.length){ box.innerHTML=""; return; }
    keys.sort(function(a,b){return sanity[b]-sanity[a];});
    var html='<div class="ck-section-header" style="margin-top:20px">'+
      '<h3 style="margin:0">Data sanity flags</h3></div>'+
      '<div class="npi-muted">Impossible cross-field values found (reported, not '+
      'auto-changed — verify at the source).</div>';
    keys.forEach(function(k){
      html+=flagRow(SANITY_LABELS[k]||k, '<span class="npi-pill">'+k+'</span>', sanity[k]);
    });
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

  function esc(s){ var d=document.createElement("div"); d.textContent=(s==null?"":s); return d.innerHTML; }

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

  function watch(jobId){
    currentJobId=jobId;
    poll=setInterval(function(){
      fetch("/npi-cleaner/status/"+jobId, {headers:{"Accept":"application/json"}})
        .then(function(r){ return r.json(); })
        .then(function(j){
          if(j.error){ fail(j.error); return; }
          $("npi-bar-fill").style.width=Math.round((j.frac||0)*100)+"%";
          $("npi-bar-msg").textContent=(j.msg||"Working")+" — "+
            Math.round((j.frac||0)*100)+"%";
          if(j.done){
            clearInterval(poll); poll=null;
            if(j.scorecard){ render(Object.assign(j.scorecard,{download:j.download})); }
            else { fail("Cleaning finished without a result."); }
          }
        })
        .catch(function(e){ fail("Lost connection to the server."); });
    }, 400);
  }

  // Step 1 — a file is chosen: detect columns, then show the mapping editor.
  function chooseFile(file){
    if(!file) return;
    if(file.size > 10*1024*1024){ fail("File is larger than 10 MB."); return; }
    currentFile=file;
    hide(stUp); hide(stErr); hide(stRes); show(stPr);
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

  // Step 2 — clean the held file with the confirmed overrides.
  function upload(file, overrides){
    if(!file) return;
    hide(stUp); hide(stMap); hide(stErr); hide(stRes); show(stPr);
    $("npi-bar-fill").style.width="5%";
    $("npi-bar-msg").textContent="Uploading "+file.name+"…";
    var params=[];
    if(!$("npi-dedupe").checked) params.push("dedupe=0");
    if($("npi-enrich").checked) params.push("enrich=1");
    if($("npi-deep").checked) params.push("deep=1");
    if($("npi-deid").checked) params.push("deid=1");
    var qs = params.length ? "?"+params.join("&") : "";
    var headers={"X-Filename":encodeURIComponent(file.name)};
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
    .catch(function(e){ fail("Upload failed. Is the file under 10 MB?"); });
  }

  initTabs();
  drop.addEventListener("click", function(){ fileIn.click(); });
  drop.addEventListener("keydown", function(e){
    if(e.key==="Enter"||e.key===" "){ e.preventDefault(); fileIn.click(); } });
  fileIn.addEventListener("change", function(){ chooseFile(fileIn.files[0]); });
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
        code="rcm_mc/ui/npi_cleaner_page.py",
    )
