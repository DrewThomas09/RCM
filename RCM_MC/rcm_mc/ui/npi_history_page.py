"""Run-history page for the NPI Claims Cleaner (/npi-cleaner/history).

Longitudinal observability: quality-score trend across runs, a runs table,
and run-vs-run compare — "did the feed get better after the source fix?".
Data comes from /npi-cleaner/api/history (aggregate counts only, no PHI).

Layout follows the v5 editorial cadence: Tier-1 masthead
(``ck_editorial_head``) with real run counts, then the run ledger FIRST
(the page's primary content, with run-over-run score deltas and grade
chips), the hidden comparison panel, the three trend charts, and the
internal feature-request backlog last. All chart colors ride the kit
tokens via CSS classes — no inline styles, no off-palette hexes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ._chartis_kit import (
    chartis_shell,
    ck_arrow_link,
    ck_editorial_head,
    ck_fmt_number,
    ck_page_actions,
    ck_provenance_tooltip,
    ck_section_header,
)

_CSS = """
/* ============ Section rhythm ============ */
.nh-sec{margin:0 0 var(--sc-s-6,28px)}
.nh-sub{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;
  line-height:1.6;color:var(--ink-2,#2b3e54);max-width:72ch;
  margin:-4px 0 16px}
.nh-sub em{font-style:italic;color:var(--green-deep,#154e36)}
/* ============ Figure panels (charts) ============ */
.nh-figure{background:var(--paper-card,#fefcf3);
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;
  padding:16px 18px;margin:0}
.nh-fig-caption{font-family:var(--sc-mono,monospace);font-size:10px;
  letter-spacing:.08em;text-transform:uppercase;color:#5C6878;
  margin-top:10px}
/* ============ Loading / hidden ============ */
.nh-loading{font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-2,#2b3e54);opacity:.7;padding:26px 14px;
  text-align:center}
.nh-hide{display:none !important}
.nh-visually-hidden{position:absolute;width:1px;height:1px;padding:0;
  margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;
  border:0}
/* ============ Runs table ============ */
.nh-scroll{overflow:auto;max-height:560px;-webkit-overflow-scrolling:touch;
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;
  background:var(--paper-card,#fefcf3)}
.nh-tbl{min-width:780px}
.nh-tbl tbody tr:hover td{background:var(--paper-hi,#fbf6e8)}
.nh-tbl input[type=checkbox]{width:15px;height:15px;cursor:pointer;
  accent-color:var(--green-deep,#154e36);vertical-align:middle}
/* injected comparison / wishlist tables can scroll on narrow viewports */
#nh-cmp-body,#nh-wish-box{overflow-x:auto;-webkit-overflow-scrolling:touch}
/* ============ Deltas / quiet cells ============ */
.nh-delta-up{color:var(--sc-positive,#0a8a5f);font-weight:600}
.nh-delta-down{color:var(--sc-negative,#b5321e);font-weight:600}
.nh-quiet{color:var(--sc-text-faint,#7a8699)}
.nh-detail-cell{color:var(--ink-2,#2b3e54);font-size:12.5px}
/* ============ Buttons + selects (kit geometry: 2px radius) ============ */
.nh-actions{display:flex;flex-wrap:wrap;gap:14px;align-items:center;
  margin-top:14px}
.nh-hint{font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-2,#2b3e54)}
.nh-btn{display:inline-flex;align-items:center;gap:6px;
  font-family:var(--sc-sans,'Inter Tight',sans-serif);font-size:12px;
  font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;
  padding:8px 14px;cursor:pointer;
  transition:background .12s ease,border-color .12s ease,color .12s ease}
.nh-btn:hover{border-color:var(--green-deep,#154e36);
  color:var(--green-deep,#154e36)}
.nh-btn:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:2px}
.nh-btn:disabled{opacity:.45;cursor:not-allowed}
.nh-btn.prim{background:var(--sc-navy,#0b2341);
  border-color:var(--sc-navy,#0b2341);color:#fff}
.nh-btn.prim:hover{background:var(--sc-teal,#155752);
  border-color:var(--sc-teal,#155752);color:#fff}
.nh-btn.prim:disabled:hover{background:var(--sc-navy,#0b2341);
  border-color:var(--sc-navy,#0b2341)}
select.nh-select{text-transform:none;letter-spacing:0;font-weight:500;
  padding:7px 10px;max-width:340px}
/* ============ Per-rule control row ============ */
.nh-ctl{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  margin:0 0 12px}
.nh-ctl-lbl{font-family:var(--sc-mono,monospace);font-size:10px;
  font-weight:600;text-transform:uppercase;letter-spacing:.08em;
  color:var(--ink-2,#2b3e54)}
/* ============ Comparison panel ============ */
.nh-cmp{display:none}
.nh-cmp.on{display:block;margin:0 0 var(--sc-s-6,28px)}
.nh-cmp:focus{outline:none}
.nh-cmp-lede{font-family:var(--sc-serif,Georgia,serif);font-size:14.5px;
  line-height:1.6;color:var(--ink,#16263a);margin:0 0 12px}
.nh-cmp-lede em{color:var(--green-deep,#154e36)}
/* ============ Wishlist note (POST-failure surface) ============ */
.nh-note{font-family:var(--sc-mono,monospace);font-size:11px;
  letter-spacing:.04em;color:var(--sc-negative,#b5321e);margin:0 0 10px}
.nh-note:empty{display:none}
/* ============ Compact kit empty states inside boxes ============ */
.nh-empty-compact{padding:26px 22px;margin:10px auto;gap:8px}
.nh-empty-compact .ck-empty-state-title{font-size:17px}
.nh-empty-compact .ck-empty-state-body{font-size:13px}
/* ============ Dimension sparkline rows ============ */
.nh-dim-row{display:flex;align-items:center;gap:12px;margin:4px 0}
.nh-dim-lbl{flex:none;width:110px;font-family:var(--sc-mono,monospace);
  font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-2,#2b3e54)}
.nh-dim-svg{max-width:60%;height:auto}
.nh-dim-val{margin-left:auto;font-family:var(--sc-mono,monospace);
  font-size:12px;font-variant-numeric:tabular-nums;
  color:var(--ink,#16263a)}
/* ============ Chart marks — README editorial chart palette ============ */
.nh-grid{stroke:#E8E0D0}
.nh-ax{fill:#5C6878;font-family:var(--sc-mono,monospace);font-size:9px}
.nh-line{fill:none;stroke:var(--green-deep,#154e36);stroke-width:2}
.nh-dot{fill:var(--green-deep,#154e36)}
.nh-last-lbl{fill:var(--green-deep,#154e36);
  font-family:var(--sc-mono,monospace);font-size:10px;font-weight:600}
.nh-spark{fill:none;stroke:var(--green-deep,#154e36);stroke-width:1.6}
.nh-bar{fill:var(--sc-warning,#b8732a);opacity:.85}
.nh-bar-lbl{fill:#5C6878;font-family:var(--sc-mono,monospace);
  font-size:8.5px}
@media (max-width:640px){
  .nh-figure{padding:12px}
}
@media print{
  .nh-figure svg{print-color-adjust:exact;-webkit-print-color-adjust:exact}
}
"""

_BODY = """
{editorial_head}

<section class="nh-sec" aria-label="All runs">
  {runs_header}
  <p class="nh-sub">Every run&rsquo;s aggregate scorecard, newest first
  &mdash; <em>tick two runs</em> to compare them side by side.
  {score_prov} is the weighted blend of five quality dimensions,
  {grade_prov} its letter band, and {delta_prov} the movement against
  the previous run.</p>
  <div class="nh-scroll">
    <table class="ck-table ck-table-sticky-head nh-tbl">
      <thead><tr>
        <th scope="col"><span class="nh-visually-hidden">Select for
          comparison</span></th>
        <th scope="col">When (UTC)</th>
        <th scope="col">File</th>
        <th scope="col" class="align-right">Rows in</th>
        <th scope="col" class="align-right">Rows out</th>
        <th scope="col" class="align-right">Dupes</th>
        <th scope="col" class="align-right">Changes</th>
        <th scope="col" class="align-right">Score /100</th>
        <th scope="col" class="align-right">&Delta; score</th>
        <th scope="col">Grade</th>
      </tr></thead>
      <tbody id="nh-rows">
        <tr><td colspan="10" class="nh-loading">Loading run
          history&hellip;</td></tr>
      </tbody>
    </table>
  </div>
  <div class="nh-actions">
    <button class="nh-btn prim" id="nh-compare" disabled>
      Compare selected runs</button>
    <span class="nh-hint" id="nh-pick-hint" aria-live="polite">Pick 2
      runs to compare &middot; 0 selected</span>
    {back_link}
  </div>
</section>

<section class="nh-cmp" id="nh-cmp" tabindex="-1"
         aria-label="Run comparison">
  {cmp_header}
  <div id="nh-cmp-body"></div>
</section>

<section class="nh-sec" aria-label="Quality-score trend">
  {trend_header}
  <p class="nh-sub">Overall grade across every run, oldest to newest
  &mdash; the page&rsquo;s one question: <em>did the feed get
  better?</em></p>
  <figure class="nh-figure">
    <div id="nh-trend-box"><div class="nh-loading">Loading&hellip;</div></div>
  </figure>
</section>

<section class="nh-sec" aria-label="Dimension trends">
  {dims_header}
  <p class="nh-sub">Each quality dimension across runs &mdash; which
  lever is moving the grade.</p>
  <figure class="nh-figure">
    <div id="nh-dims-box"><div class="nh-loading">Loading&hellip;</div></div>
  </figure>
</section>

<section class="nh-sec" aria-label="Per-rule trend">
  {rule_header}
  <p class="nh-sub">Is a specific problem (bad codes, future dates,
  dupes &hellip;) getting better or worse across runs?</p>
  <figure class="nh-figure">
    <div class="nh-ctl">
      <label class="nh-ctl-lbl" for="nh-rule">Rule</label>
      <select id="nh-rule" class="nh-btn nh-select"></select>
    </div>
    <div id="nh-rule-box"><div class="nh-loading">Loading&hellip;</div></div>
  </figure>
</section>

<section class="nh-sec" id="nh-wishlist" aria-label="Feature requests">
  {wish_header}
  <p class="nh-sub">Internal triage of &ldquo;missing something?&rdquo;
  requests filed from the cleaner page: open &rarr; planned &rarr;
  shipped / declined.</p>
  <div id="nh-wish-note" class="nh-note" role="status"
       aria-live="polite"></div>
  <div id="nh-wish-box"><div class="nh-loading">Loading&hellip;</div></div>
</section>

<script>
(function(){
  "use strict";
  function $(id){ return document.getElementById(id); }
  // Entity-escape INCLUDING quotes — file names render into attribute
  // contexts (checkbox data-run, option values).
  function esc(s){ return String(s==null?"":s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
  function fmt(n){ return (n==null?0:n).toLocaleString(); }
  function when(ts){ var d=new Date(ts*1000);
    return d.toISOString().slice(0,16).replace("T"," "); }

  // Kit empty-state markup (classes are global once chartis_shell
  // renders) — every arg here is a static literal from this file,
  // never user data.
  function emptyBlock(eyebrow, title, body, ctaLabel, ctaHref, warn){
    return '<div class="ck-empty-state '+
      (warn?'ck-empty-state-warning ':'')+'nh-empty-compact">'+
      (eyebrow?'<div class="ck-eyebrow">'+eyebrow+'</div>':'')+
      '<div class="ck-empty-state-title">'+title+'</div>'+
      (body?'<p class="ck-empty-state-body">'+body+'</p>':'')+
      ((ctaLabel&&ctaHref)?'<div class="ck-empty-state-actions">'+
        '<a class="ck-empty-state-cta" href="'+ctaHref+'">'+ctaLabel+
        '</a></div>':'')+
      '</div>';
  }

  function gradeChip(letter){
    var t=(letter==="A"||letter==="B")?"positive":
          (letter==="C")?"warning":
          (letter==="D"||letter==="F")?"negative":"neutral";
    return '<span class="ck-badge tone-'+t+'">'+esc(letter)+'</span>';
  }

  var RUNS=[], picked=[], currentRule=null;

  function renderTrend(){
    var box=$("nh-trend-box");
    if(RUNS.length<2){
      box.innerHTML=emptyBlock("QUALITY-SCORE TREND",
        "Not enough runs to trend",
        "Run the cleaner at least twice and the composite score will "+
        "chart here, oldest to newest.",
        RUNS.length?"Clean another file":"Clean a file",
        "/npi-cleaner", false);
      return;
    }
    var pts=RUNS.slice().reverse();   // oldest → newest
    var last=pts[pts.length-1].score;
    var W=Math.max(560, box.clientWidth-8), H=150, L=36, R=46, T=14, B=24;
    var iw=W-L-R, ih=H-T-B, n=pts.length;
    function sx(i){ return L + (n===1?iw/2:(i/(n-1))*iw); }
    function sy(v){ return T + ih - (v/100)*ih; }
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" '+
      'preserveAspectRatio="xMidYMid meet" role="img" '+
      'aria-label="Quality score across '+n+' runs, latest '+last+
      ' of 100">';
    [0,50,100].forEach(function(g){
      svg+='<line class="nh-grid" x1="'+L+'" y1="'+sy(g)+'" x2="'+(W-R)+
        '" y2="'+sy(g)+'"/>'+
        '<text class="nh-ax" x="'+(L-6)+'" y="'+(sy(g)+3)+
        '" text-anchor="end">'+g+'</text>'; });
    var d=pts.map(function(p,i){
      return (i?"L":"M")+sx(i).toFixed(1)+" "+sy(p.score).toFixed(1);
    }).join(" ");
    svg+='<path class="nh-line" d="'+d+'"/>';
    pts.forEach(function(p,i){
      svg+='<circle class="nh-dot" cx="'+sx(i).toFixed(1)+'" cy="'+
        sy(p.score).toFixed(1)+'" r="3.4"><title>'+esc(p.file_name)+
        ' — '+p.score+'</title></circle>'; });
    svg+='<text class="nh-last-lbl" x="'+(W-R+8)+'" y="'+(sy(last)+3)+
      '" text-anchor="start">'+last+'</text>';
    svg+='</svg>';
    box.innerHTML=svg+'<div class="nh-fig-caption">Overall score /100 '+
      '&middot; oldest &rarr; newest &middot; latest '+last+'</div>';
  }

  var DIMS=["completeness","validity","consistency","uniqueness","conformity"];

  function renderDims(){
    var box=$("nh-dims-box");
    if(RUNS.length<2){
      box.innerHTML=emptyBlock("DIMENSION TRENDS",
        "Not enough runs to trend",
        "Dimension sparklines need at least two runs of the cleaner.",
        null, null, false);
      return;
    }
    var pts=RUNS.slice().reverse();   // oldest → newest
    var html="";
    DIMS.forEach(function(dim){
      var vals=pts.map(function(r){
        var v=(r.dimensions||{})[dim];
        return (typeof v==="number")?v:null;
      });
      var W=240, H=34, P=3, n=vals.length;
      function sx(i){ return P+(n===1?(W-2*P)/2:(i/(n-1))*(W-2*P)); }
      function sy(v){ return P+(H-2*P)-(v/100)*(H-2*P); }
      var d="", started=false;
      vals.forEach(function(v,i){
        if(v==null) return;
        d+=(started?"L":"M")+sx(i).toFixed(1)+" "+sy(v).toFixed(1)+" ";
        started=true;
      });
      var last=null;
      for(var i=vals.length-1;i>=0;i--){
        if(vals[i]!=null){ last=vals[i]; break; } }
      html+='<div class="nh-dim-row">'+
        '<span class="nh-dim-lbl">'+dim+'</span>'+
        '<svg class="nh-dim-svg" viewBox="0 0 '+W+' '+H+'" width="'+W+
        '" height="'+H+'" role="img" aria-label="'+dim+' across '+n+
        ' runs'+(last==null?'':', latest '+last.toFixed(1)+' of 100')+'">'+
        '<line class="nh-grid" x1="'+P+'" y1="'+sy(100)+'" x2="'+(W-P)+
        '" y2="'+sy(100)+'"/>'+
        (d?'<path class="nh-spark" d="'+d.trim()+'"/>':"")+
        '</svg>'+
        '<span class="nh-dim-val">'+
        (last==null?"—":last.toFixed(1))+'</span></div>';
    });
    box.innerHTML=html+'<div class="nh-fig-caption">Latest value at '+
      'right &middot; each dimension /100 &middot; oldest &rarr; '+
      'newest</div>';
  }

  function renderRulePicker(){
    var sel=$("nh-rule"), box=$("nh-rule-box");
    var keys={}, list;
    RUNS.forEach(function(r){
      Object.keys(r.sanity||{}).forEach(function(k){ keys[k]=1; }); });
    list=Object.keys(keys).sort();
    var ctl=sel.closest(".nh-ctl");
    if(RUNS.length<2 || !list.length){
      if(ctl) ctl.classList.add("nh-hide");
      box.innerHTML=emptyBlock("PER-RULE TREND",
        "Not enough runs to trend a rule",
        "Run the cleaner at least twice (with findings) and pick a "+
        "rule to trend here.", null, null, false);
      return;
    }
    if(ctl) ctl.classList.remove("nh-hide");
    sel.innerHTML=list.map(function(k){
      return '<option value="'+esc(k)+'">'+esc(k)+'</option>'; }).join("");
    sel.addEventListener("change", function(){ renderRuleTrend(sel.value); });
    renderRuleTrend(list[0]);
  }

  function renderRuleTrend(rule){
    currentRule=rule;
    var box=$("nh-rule-box");
    var pts=RUNS.slice().reverse().map(function(r){   // oldest → newest
      return {v:(r.sanity||{})[rule]||0, f:r.file_name}; });
    var max=1;
    pts.forEach(function(p){ if(p.v>max) max=p.v; });
    var W=Math.max(560, box.clientWidth-8), H=130, L=36, R=12, T=16, B=12;
    var iw=W-L-R, ih=H-T-B, n=pts.length;
    var bw=Math.min(38, (iw/n)*0.6);
    var lastV=pts[n-1].v;
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" '+
      'preserveAspectRatio="xMidYMid meet" role="img" '+
      'aria-label="Rows flagged by '+esc(rule)+' across '+n+
      ' runs, latest '+lastV+'">';
    var half=Math.round(max/2);
    var gs=[0]; if(half>0&&half<max) gs.push(half); gs.push(max);
    gs.forEach(function(g){
      var y=T+ih-(g/max)*ih;
      svg+='<line class="nh-grid" x1="'+L+'" y1="'+y+'" x2="'+(W-R)+
        '" y2="'+y+'"/>'+
        '<text class="nh-ax" x="'+(L-6)+'" y="'+(y+3)+
        '" text-anchor="end">'+g+'</text>'; });
    pts.forEach(function(p,i){
      var cx=L+(n===1?iw/2:(i/(n-1))*iw), h=(p.v/max)*ih;
      svg+='<rect class="nh-bar" x="'+(cx-bw/2).toFixed(1)+'" y="'+
        (T+ih-h).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+
        h.toFixed(1)+'" rx="1"><title>'+esc(p.f)+' — '+p.v+
        '</title></rect>';
      if(n<=24 || i===n-1){
        svg+='<text class="nh-bar-lbl" x="'+cx.toFixed(1)+'" y="'+
          (T+ih-h-3).toFixed(1)+'" text-anchor="middle">'+p.v+'</text>';
      }
    });
    svg+='</svg>';
    box.innerHTML=svg+'<div class="nh-fig-caption">Rows flagged by '+
      esc(rule)+' per run &middot; oldest &rarr; newest</div>';
  }

  function updateCompareState(){
    $("nh-compare").disabled = picked.length!==2;
    var hint=$("nh-pick-hint");
    if(hint){ hint.textContent = (picked.length===2)
      ? "2 of 2 selected — ready to compare"
      : "Pick 2 runs to compare · "+picked.length+" selected"; }
  }

  function renderRows(){
    var tb=$("nh-rows");
    if(!RUNS.length){
      tb.innerHTML='<tr><td colspan="10">'+
        emptyBlock("RUN HISTORY", "No cleaning runs yet",
          "Run the cleaner on a claims file and its scorecard will "+
          "appear here — aggregates only, no claim rows, no PHI.",
          "Clean a file", "/npi-cleaner", false)+'</td></tr>';
      return;
    }
    tb.innerHTML=RUNS.map(function(r,i){
      var prev=RUNS[i+1], dHtml;   // newest-first: i+1 is the prior run
      if(!prev){
        dHtml='<span class="nh-quiet" title="Oldest recorded run '+
          '— no baseline">—</span>';
      } else {
        var d=r.score-prev.score;
        if(d>0){ dHtml='<span class="nh-delta-up">+'+d+'&nbsp;&#9650;</span>'; }
        else if(d<0){ dHtml='<span class="nh-delta-down">'+d+'&nbsp;&#9660;</span>'; }
        else { dHtml='<span class="nh-quiet">&plusmn;0</span>'; }
      }
      return '<tr><td><input type="checkbox" data-run="'+esc(r.run_id)+
        '" aria-label="Select run '+esc(r.file_name)+' '+when(r.ts)+
        ' for comparison"></td>'+
        '<td class="sc-num">'+when(r.ts)+'</td>'+
        '<td>'+esc(r.file_name)+'</td>'+
        '<td class="align-right sc-num">'+fmt(r.rows_in)+'</td>'+
        '<td class="align-right sc-num">'+fmt(r.rows_out)+'</td>'+
        '<td class="align-right sc-num">'+fmt(r.dupes)+'</td>'+
        '<td class="align-right sc-num">'+fmt(r.changes)+'</td>'+
        '<td class="align-right sc-num">'+r.score+'</td>'+
        '<td class="align-right sc-num">'+dHtml+'</td>'+
        '<td>'+gradeChip(r.letter)+'</td></tr>';
    }).join("");
    tb.querySelectorAll("input[type=checkbox]").forEach(function(cb){
      cb.addEventListener("change", function(){
        var id=cb.getAttribute("data-run");
        if(cb.checked){ picked.push(id); } else {
          picked=picked.filter(function(x){return x!==id;}); }
        if(picked.length>2){
          var drop=picked.shift();
          var el=tb.querySelector('input[data-run="'+drop+'"]');
          if(el) el.checked=false;
        }
        updateCompareState();
      });
    });
  }

  function renderCompareError(){
    var box=$("nh-cmp");
    $("nh-cmp-body").innerHTML=emptyBlock("COMPARE FAILED",
      "Could not compare those runs",
      "One of the runs may have been pruned, or the connection "+
      "dropped. Re-pick two runs and try again.", null, null, true);
    box.classList.add("on");
    box.scrollIntoView({behavior:"smooth"});
  }

  function renderCompare(c){
    var box=$("nh-cmp"), body=$("nh-cmp-body");
    var up=c.score_delta>=0;
    var h='<p class="nh-cmp-lede"><em>'+esc(c.a.file_name)+'</em> ('+
      when(c.a.ts)+' UTC &middot; score '+c.a.score+') &rarr; <em>'+
      esc(c.b.file_name)+'</em> ('+when(c.b.ts)+' UTC &middot; score '+
      c.b.score+') &middot; <span class="'+
      (up?'nh-delta-up':'nh-delta-down')+'">'+
      (up?'+':'')+c.score_delta+' points</span></p>';
    if(c.rule_delta.length){
      h+='<table class="ck-table"><thead><tr><th scope="col">Rule</th>'+
        '<th scope="col" class="align-right">Earlier run</th>'+
        '<th scope="col" class="align-right">Later run</th>'+
        '<th scope="col" class="align-right">&Delta;</th></tr></thead><tbody>';
      c.rule_delta.forEach(function(d){
        var worse=d.delta>0;
        h+='<tr><td>'+esc(d.rule)+'</td>'+
          '<td class="align-right sc-num">'+fmt(d.a)+'</td>'+
          '<td class="align-right sc-num">'+fmt(d.b)+'</td>'+
          '<td class="align-right sc-num '+
          (worse?'nh-delta-down':'nh-delta-up')+'">'+(worse?'+':'')+
          d.delta+'</td></tr>';
      });
      h+='</tbody></table>'+
        '<div class="nh-fig-caption">&Delta; = later minus earlier '+
        '&middot; positive = more rows flagged (worse)</div>';
    } else {
      h+=emptyBlock("RULE DELTAS", "No per-rule differences",
        "These two runs flag exactly the same counts on every rule.",
        null, null, false);
    }
    body.innerHTML=h; box.classList.add("on");
    box.scrollIntoView({behavior:"smooth"});
    try{ box.focus({preventScroll:true}); }catch(e){ box.focus(); }
  }

  $("nh-compare").addEventListener("click", function(){
    if(picked.length!==2) return;
    // Compare chronologically: a = earlier run, b = later run, so the
    // Δ column always reads "later minus earlier" regardless of the
    // order the boxes were ticked.
    var byId={};
    RUNS.forEach(function(r){ byId[r.run_id]=r; });
    var pair=picked.slice().sort(function(x,y){
      return ((byId[x]||{}).ts||0)-((byId[y]||{}).ts||0); });
    fetch("/npi-cleaner/api/history/compare?a="+encodeURIComponent(pair[0])+
          "&b="+encodeURIComponent(pair[1]))
      .then(function(r){ return r.json(); })
      .then(function(j){
        if(j.error){ renderCompareError(); return; }
        renderCompare(j);
      })
      .catch(renderCompareError);
  });

  // ---- Wishlist triage: move requests through the build backlog ----
  var WISH_STATUSES=["open","planned","shipped","declined"];
  var WISH_TONES={open:"neutral",planned:"warning",
                  shipped:"positive",declined:"negative"};
  function wishFail(){ var n=$("nh-wish-note"); if(n) n.textContent=
    "Update failed — the change was not saved. Check the connection "+
    "and try again."; }
  function wishOk(){ var n=$("nh-wish-note"); if(n) n.textContent=""; }
  function loadWishlist(){
    fetch("/npi-cleaner/api/wishlist").then(function(r){ return r.json(); })
      .then(function(j){
        var box=$("nh-wish-box"), reqs=j.requests||[];
        if(!reqs.length){
          box.innerHTML=emptyBlock("BACKLOG EMPTY", "No requests yet",
            "The “Missing something?” card on the cleaner "+
            "page feeds this backlog.",
            "Open the cleaner", "/npi-cleaner", false);
          return;
        }
        var h='<table class="ck-table"><thead><tr>'+
          '<th scope="col">When (UTC)</th>'+
          '<th scope="col">Category</th>'+
          '<th scope="col">Request</th>'+
          '<th scope="col">Details</th>'+
          '<th scope="col">Status</th>'+
          '<th scope="col">Set status</th>'+
          '<th scope="col"><span class="nh-visually-hidden">Actions'+
          '</span></th></tr></thead><tbody>';
        reqs.forEach(function(q){
          var opts=WISH_STATUSES.map(function(s){
            return '<option value="'+s+'"'+(s===q.status?' selected':'')+
              '>'+s.charAt(0).toUpperCase()+s.slice(1)+'</option>'; }).join("");
          var tone=WISH_TONES[q.status]||"neutral";
          h+='<tr><td class="sc-num">'+when(q.created)+'</td>'+
            '<td>'+esc(q.category)+'</td>'+
            '<td>'+esc(q.title)+'</td>'+
            '<td class="nh-detail-cell">'+esc(q.details)+'</td>'+
            '<td><span class="ck-badge tone-'+tone+'">'+esc(q.status)+
            '</span></td>'+
            '<td><select class="nh-btn nh-select nh-wish-status" '+
            'data-id="'+q.id+'" aria-label="Status for request '+
            esc(q.title)+'">'+opts+'</select></td>'+
            '<td><button class="nh-btn nh-wish-del" data-id="'+q.id+
            '" aria-label="Remove request '+esc(q.title)+
            '">Remove</button></td></tr>';
        });
        h+='</tbody></table>';
        box.innerHTML=h;
        box.querySelectorAll(".nh-wish-status").forEach(function(sel){
          sel.addEventListener("change", function(){
            fetch("/npi-cleaner/api/wishlist/status", {method:"POST",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({id:+this.getAttribute("data-id"),
                                   status:this.value})})
              .then(function(r){ return r.json(); })
              .then(function(j){
                if(j&&j.ok===false){ wishFail(); } else { wishOk(); }
                loadWishlist(); })
              .catch(wishFail);
          });
        });
        box.querySelectorAll(".nh-wish-del").forEach(function(btn){
          btn.addEventListener("click", function(){
            if(!window.confirm("Remove this request permanently?")) return;
            fetch("/npi-cleaner/api/wishlist/delete", {method:"POST",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({id:+this.getAttribute("data-id")})})
              .then(function(r){ return r.json(); })
              .then(function(j){
                if(j&&j.ok===false){ wishFail(); } else { wishOk(); }
                loadWishlist(); })
              .catch(wishFail);
          });
        });
      })
      .catch(function(){ $("nh-wish-box").innerHTML=
        emptyBlock("BUILD BACKLOG", "Could not load the backlog",
          "The wishlist API did not respond. Reload the page to retry.",
          "Back to the cleaner", "/npi-cleaner", true); });
  }
  loadWishlist();

  // Charts remeasure on resize — a debounce keeps the SVG rebuild off
  // the hot path while dragging the window edge.
  var resizeT=null;
  window.addEventListener("resize", function(){
    if(RUNS.length<2) return;
    clearTimeout(resizeT);
    resizeT=setTimeout(function(){
      renderTrend();
      if(currentRule) renderRuleTrend(currentRule);
    }, 160);
  });

  fetch("/npi-cleaner/api/history").then(function(r){ return r.json(); })
    .then(function(j){ RUNS=j.runs||[]; renderTrend(); renderDims();
      renderRulePicker(); renderRows(); })
    .catch(function(){
      $("nh-rows").innerHTML='<tr><td colspan="10">'+
        emptyBlock("RUN HISTORY", "Could not load history.",
          "The history API did not respond. Reload the page to retry, "+
          "or head back to the cleaner.",
          "Back to the cleaner", "/npi-cleaner", true)+'</td></tr>';
      ["nh-trend-box","nh-dims-box","nh-rule-box"].forEach(function(id){
        var el=$(id);
        if(el) el.innerHTML=emptyBlock(null, "Could not load history.",
          null, null, null, true);
      });
      // No data → the Rule picker has nothing to offer; hide its row so
      // an empty enabled <select> doesn't sit above the error card.
      var ctl=document.querySelector(".nh-ctl");
      if(ctl) ctl.classList.add("nh-hide");
    });
})();
</script>
"""


def render_npi_history() -> str:
    # Real counts for the masthead meta strip — both stores are guarded
    # (they return [] on any storage failure), so render never 500s.
    try:
        from ..npi_cleaner.history import list_runs
        runs = list_runs(50)
    except Exception:  # noqa: BLE001 — observability never blocks the page
        runs = []
    try:
        from ..npi_cleaner.wishlist import list_requests
        n_wish = len(list_requests())
    except Exception:  # noqa: BLE001
        n_wish = 0
    n_runs = len(runs)
    if runs:
        last_day = datetime.fromtimestamp(
            float(runs[0]["ts"]), tz=timezone.utc).strftime("%Y-%m-%d")
        meta = (f"{ck_fmt_number(n_runs)} RUNS RECORDED · LATEST SCORE "
                f"{ck_fmt_number(runs[0]['score'])}/100 · LAST RUN "
                f"{last_day} UTC · AGGREGATES ONLY — NO PHI")
    else:
        meta = "NO RUNS RECORDED YET · AGGREGATES ONLY — NO PHI"

    head = ck_editorial_head(
        eyebrow="TOOLS · NPI CLAIMS CLEANER",
        title="Cleaning run history",
        meta=meta,
        lede_italic_phrase="Quality tracked across runs,",
        lede_body=(
            " not just within one file — every cleaning run records its "
            "aggregate scorecard (counts only: no claim rows, no PHI). "
            "Scan the ledger below, then pick two runs to see exactly "
            "which rules moved."),
        # Masthead carries only the page-specific quick link; the standard
        # ck_page_actions row lands at the page bottom, matching the
        # site-wide placement (exports, source, diligence family).
        actions_html='<a href="/npi-cleaner">← Back to NPI Cleaner</a>',
        show_legend=False,
    )

    # "Explain this number" hovers on the ledger's three derived columns.
    # Thresholds/weights mirror engine.quality() — keep in lockstep.
    score_prov = ck_provenance_tooltip(
        "Score /100", "Score",
        explainer=(
            "Weighted blend of the five data-quality dimensions — "
            "completeness 25%, validity 25%, consistency 20%, "
            "uniqueness 15%, conformity 15% — rounded to a 0-100 "
            "composite. Deterministic: recomputable from the visible "
            "counts."))
    grade_prov = ck_provenance_tooltip(
        "Grade", "Grade",
        explainer=(
            "Letter band on the composite score: A at 93+, B at 85+, "
            "C at 70+, D at 55+, F below 55."),
        inject_css=False)
    delta_prov = ck_provenance_tooltip(
        "Δ score", "Δ score",
        explainer=(
            "Score movement vs the chronologically previous run — "
            "positive means the feed improved. The oldest recorded run "
            "shows a dash (no baseline)."),
        inject_css=False)

    runs_header = ck_section_header(
        "All runs", "RUN LEDGER · NEWEST FIRST", n_runs)
    cmp_header = ck_section_header(
        "Run comparison", "SIDE BY SIDE · EARLIER → LATER")
    trend_header = ck_section_header(
        "Quality-score trend", "TREND · COMPOSITE SCORE /100")
    dims_header = ck_section_header(
        "Dimension trends", "TREND · FIVE DIMENSIONS /100")
    rule_header = ck_section_header(
        "Per-rule trend", "TREND · ONE RULE ACROSS RUNS")
    wish_header = ck_section_header(
        "Feature requests", "FEEDBACK · BUILD BACKLOG", n_wish)
    back_link = ck_arrow_link("Back to the cleaner", "/npi-cleaner")

    # .replace, not .format — the embedded JS is full of literal braces.
    body = (
        _BODY
        .replace("{editorial_head}", head)
        .replace("{runs_header}", runs_header)
        .replace("{score_prov}", score_prov)
        .replace("{grade_prov}", grade_prov)
        .replace("{delta_prov}", delta_prov)
        .replace("{back_link}", back_link)
        .replace("{cmp_header}", cmp_header)
        .replace("{trend_header}", trend_header)
        .replace("{dims_header}", dims_header)
        .replace("{rule_header}", rule_header)
        .replace("{wish_header}", wish_header)
    )
    # Standard action pills at the page bottom — same placement as every
    # other editorial page (the masthead only carries the back link).
    body = body + ck_page_actions(glossary=False, methodology=False)
    return chartis_shell(
        body,
        title="Run history — NPI Claims Cleaner",
        active_nav="TOOLS",
        breadcrumbs=[("Tools", None), ("NPI Cleaner", "/npi-cleaner"),
                     ("Run history", None)],
        extra_css=_CSS,
    )
