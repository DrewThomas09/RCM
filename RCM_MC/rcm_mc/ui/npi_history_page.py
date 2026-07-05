"""Run-history page for the NPI Claims Cleaner (/npi-cleaner/history).

Longitudinal observability: quality-score trend across runs, a runs table,
and run-vs-run compare — "did the feed get better after the source fix?".
Data comes from /npi-cleaner/api/history (aggregate counts only, no PHI).
"""
from __future__ import annotations

from ._chartis_kit import chartis_shell, ck_page_title

_CSS = """
.nh-wrap{max-width:1100px}
.nh-trend{background:var(--panel,#fff);border:1px solid var(--line,#d2ddd7);
  border-radius:10px;padding:18px 20px;margin:14px 0}
.nh-tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
.nh-tbl th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-2,#4a5d57);text-align:left;padding:6px 8px;
  border-bottom:1px solid var(--line,#d2ddd7)}
.nh-tbl td{padding:7px 8px;border-bottom:1px solid
  color-mix(in srgb,var(--line,#d2ddd7) 55%,transparent)}
.nh-tbl .num{text-align:right;font-variant-numeric:tabular-nums}
.nh-grade{font-weight:700}
.nh-grade.A,.nh-grade.B{color:var(--green-deep,#0c7c66)}
.nh-grade.C{color:#b8732a}
.nh-grade.D,.nh-grade.F{color:#b5321e}
.nh-cmp{background:var(--panel,#fff);border:1px solid var(--line,#d2ddd7);
  border-radius:10px;padding:18px 20px;margin:16px 0;display:none}
.nh-cmp.on{display:block}
.nh-muted{color:var(--ink-2,#4a5d57);font-size:12.5px}
.nh-btn{border:1px solid var(--line,#d2ddd7);background:var(--panel,#fff);
  border-radius:7px;padding:5px 12px;font-size:12.5px;cursor:pointer}
.nh-btn.prim{background:var(--green-deep,#0c7c66);color:#fff;border:0}
.nh-delta-up{color:var(--green-deep,#0c7c66);font-weight:640}
.nh-delta-down{color:#b5321e;font-weight:640}
.nh-empty{padding:40px;text-align:center;color:var(--ink-2,#4a5d57)}
"""

_BODY = """
<div class="nh-wrap">
  {page_title}
  <div class="nh-muted">Every cleaning run records its aggregate scorecard
  (counts only — no claim rows, no PHI). Pick two runs to compare.</div>

  <div class="nh-trend">
    <div style="font-size:13px;font-weight:640;margin-bottom:6px">
      Quality-score trend</div>
    <div id="nh-trend-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <div class="nh-trend">
    <div style="font-size:13px;font-weight:640;margin-bottom:6px">
      Dimension trends</div>
    <div class="nh-muted" style="margin-bottom:8px">Each quality dimension
    across runs — which lever is moving the grade.</div>
    <div id="nh-dims-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <div class="nh-trend">
    <div style="font-size:13px;font-weight:640;margin-bottom:6px">
      Per-rule trend</div>
    <div class="nh-muted" style="margin-bottom:8px">Is a specific problem
    (bad codes, future dates, dupes …) getting better or worse across runs?
    <select id="nh-rule" class="nh-btn" style="margin-left:8px;max-width:320px">
    </select></div>
    <div id="nh-rule-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <table class="nh-tbl">
    <thead><tr>
      <th></th><th>When</th><th>File</th><th class="num">Rows in</th>
      <th class="num">Rows out</th><th class="num">Dupes</th>
      <th class="num">Changes</th><th class="num">Score</th><th>Grade</th>
    </tr></thead>
    <tbody id="nh-rows"><tr><td colspan="9" class="nh-empty">Loading…</td></tr>
    </tbody>
  </table>
  <div style="margin-top:12px">
    <button class="nh-btn prim" id="nh-compare" disabled>
      Compare selected runs</button>
    <a class="nh-btn" href="/npi-cleaner" style="text-decoration:none;
       display:inline-block;margin-left:8px">← Back to the cleaner</a>
  </div>

  <div class="nh-cmp" id="nh-cmp">
    <div style="font-size:13px;font-weight:640;margin-bottom:6px">
      Run comparison</div>
    <div id="nh-cmp-body"></div>
  </div>
</div>

<script>
(function(){
  "use strict";
  function $(id){ return document.getElementById(id); }
  function esc(s){ var d=document.createElement("div");
    d.textContent=(s==null?"":s); return d.innerHTML; }
  function fmt(n){ return (n==null?0:n).toLocaleString(); }
  function when(ts){ var d=new Date(ts*1000);
    return d.toISOString().slice(0,16).replace("T"," "); }

  var RUNS=[], picked=[];

  function renderTrend(){
    var box=$("nh-trend-box");
    if(RUNS.length<2){ box.innerHTML='<div class="nh-muted">Run the cleaner '+
      'at least twice to see a trend.</div>'; return; }
    var pts=RUNS.slice().reverse();   // oldest → newest
    var W=Math.max(560, box.clientWidth-8), H=140, L=34, R=10, T=10, B=22;
    var iw=W-L-R, ih=H-T-B, n=pts.length;
    function sx(i){ return L + (n===1?iw/2:(i/(n-1))*iw); }
    function sy(v){ return T + ih - (v/100)*ih; }
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" '+
      'preserveAspectRatio="xMidYMid meet">';
    [0,50,100].forEach(function(g){
      svg+='<line x1="'+L+'" y1="'+sy(g)+'" x2="'+(W-R)+'" y2="'+sy(g)+
        '" stroke="rgba(120,130,125,.18)"/>'+
        '<text x="'+(L-5)+'" y="'+(sy(g)+3)+'" text-anchor="end" '+
        'font-size="9" fill="rgba(120,130,125,.9)">'+g+'</text>'; });
    var d=pts.map(function(p,i){
      return (i?"L":"M")+sx(i).toFixed(1)+" "+sy(p.score).toFixed(1);
    }).join(" ");
    svg+='<path d="'+d+'" fill="none" stroke="#2a78d6" stroke-width="2"/>';
    pts.forEach(function(p,i){
      svg+='<circle cx="'+sx(i).toFixed(1)+'" cy="'+sy(p.score).toFixed(1)+
        '" r="3.4" fill="#2a78d6"><title>'+esc(p.file_name)+' — '+p.score+
        '</title></circle>'; });
    svg+='</svg>';
    box.innerHTML=svg;
  }

  var DIMS=["completeness","validity","consistency","uniqueness","conformity"];

  function renderDims(){
    var box=$("nh-dims-box");
    if(RUNS.length<2){
      box.innerHTML='<div class="nh-muted">Run the cleaner at least twice '+
        'to see dimension trends.</div>';
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
      html+='<div style="display:flex;align-items:center;gap:10px;'+
        'margin:3px 0">'+
        '<span style="width:110px;font-size:11px;text-transform:uppercase;'+
        'letter-spacing:.04em;color:var(--ink-2,#4a5d57)">'+dim+'</span>'+
        '<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'" height="'+H+'" '+
        'style="max-width:60%">'+
        '<line x1="'+P+'" y1="'+sy(100)+'" x2="'+(W-P)+'" y2="'+sy(100)+
        '" stroke="rgba(120,130,125,.15)"/>'+
        (d?'<path d="'+d.trim()+'" fill="none" stroke="#0c7c66" '+
        'stroke-width="1.6"/>':"")+
        '</svg>'+
        '<span class="num" style="font-size:12px;font-variant-numeric:'+
        'tabular-nums">'+(last==null?"—":last.toFixed(1))+'</span></div>';
    });
    box.innerHTML=html;
  }

  function renderRulePicker(){
    var sel=$("nh-rule"), box=$("nh-rule-box");
    var keys={}, list;
    RUNS.forEach(function(r){
      Object.keys(r.sanity||{}).forEach(function(k){ keys[k]=1; }); });
    list=Object.keys(keys).sort();
    if(RUNS.length<2 || !list.length){
      sel.style.display="none";
      box.innerHTML='<div class="nh-muted">Run the cleaner at least twice '+
        '(with findings) to trend a rule.</div>';
      return;
    }
    sel.innerHTML=list.map(function(k){
      return '<option value="'+esc(k)+'">'+esc(k)+'</option>'; }).join("");
    sel.addEventListener("change", function(){ renderRuleTrend(sel.value); });
    renderRuleTrend(list[0]);
  }

  function renderRuleTrend(rule){
    var box=$("nh-rule-box");
    var pts=RUNS.slice().reverse().map(function(r){   // oldest → newest
      return {v:(r.sanity||{})[rule]||0, f:r.file_name}; });
    var max=1;
    pts.forEach(function(p){ if(p.v>max) max=p.v; });
    var W=Math.max(560, box.clientWidth-8), H=120, L=34, R=10, T=10, B=10;
    var iw=W-L-R, ih=H-T-B, n=pts.length;
    var bw=Math.min(38, (iw/n)*0.6);
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" '+
      'preserveAspectRatio="xMidYMid meet">';
    [0,max].forEach(function(g){
      var y=T+ih-(g/max)*ih;
      svg+='<line x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+
        '" stroke="rgba(120,130,125,.18)"/>'+
        '<text x="'+(L-5)+'" y="'+(y+3)+'" text-anchor="end" font-size="9" '+
        'fill="rgba(120,130,125,.9)">'+g+'</text>'; });
    pts.forEach(function(p,i){
      var cx=L+(n===1?iw/2:(i/(n-1))*iw), h=(p.v/max)*ih;
      svg+='<rect x="'+(cx-bw/2).toFixed(1)+'" y="'+(T+ih-h).toFixed(1)+
        '" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" rx="2" '+
        'fill="#b8732a" opacity=".85"><title>'+esc(p.f)+' — '+p.v+
        '</title></rect>'; });
    svg+='</svg>';
    box.innerHTML=svg+'<div class="nh-muted" style="margin-top:4px">Rows '+
      'flagged by <b>'+esc(rule)+'</b> per run (oldest → newest).</div>';
  }

  function renderRows(){
    var tb=$("nh-rows");
    if(!RUNS.length){ tb.innerHTML='<tr><td colspan="9" class="nh-empty">'+
      'No runs yet — clean a file first.</td></tr>'; return; }
    tb.innerHTML=RUNS.map(function(r){
      return '<tr><td><input type="checkbox" data-run="'+esc(r.run_id)+
        '"></td><td>'+when(r.ts)+'</td><td>'+esc(r.file_name)+
        '</td><td class="num">'+fmt(r.rows_in)+'</td><td class="num">'+
        fmt(r.rows_out)+'</td><td class="num">'+fmt(r.dupes)+
        '</td><td class="num">'+fmt(r.changes)+'</td><td class="num">'+
        r.score+'</td><td><span class="nh-grade '+esc(r.letter)+'">'+
        esc(r.letter)+'</span></td></tr>';
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
        $("nh-compare").disabled = picked.length!==2;
      });
    });
  }

  function renderCompare(c){
    var box=$("nh-cmp"), body=$("nh-cmp-body");
    var up=c.score_delta>=0;
    var h='<div style="margin-bottom:8px">'+esc(c.a.file_name)+' ('+c.a.score+
      ') → '+esc(c.b.file_name)+' ('+c.b.score+') · '+
      '<span class="'+(up?'nh-delta-up':'nh-delta-down')+'">'+
      (up?'+':'')+c.score_delta+' points</span></div>';
    if(c.rule_delta.length){
      h+='<table class="nh-tbl"><thead><tr><th>Rule</th>'+
        '<th class="num">Run A</th><th class="num">Run B</th>'+
        '<th class="num">Δ</th></tr></thead><tbody>';
      c.rule_delta.forEach(function(d){
        var worse=d.delta>0;
        h+='<tr><td>'+esc(d.rule)+'</td><td class="num">'+fmt(d.a)+
          '</td><td class="num">'+fmt(d.b)+'</td><td class="num '+
          (worse?'nh-delta-down':'nh-delta-up')+'">'+(worse?'+':'')+
          d.delta+'</td></tr>';
      });
      h+='</tbody></table>';
    } else {
      h+='<div class="nh-muted">No per-rule differences between these runs.'+
        '</div>';
    }
    body.innerHTML=h; box.classList.add("on");
  }

  $("nh-compare").addEventListener("click", function(){
    if(picked.length!==2) return;
    fetch("/npi-cleaner/api/history/compare?a="+encodeURIComponent(picked[0])+
          "&b="+encodeURIComponent(picked[1]))
      .then(function(r){ return r.json(); })
      .then(function(j){ if(!j.error) renderCompare(j); });
  });

  fetch("/npi-cleaner/api/history").then(function(r){ return r.json(); })
    .then(function(j){ RUNS=j.runs||[]; renderTrend(); renderDims();
      renderRulePicker(); renderRows(); })
    .catch(function(){ $("nh-rows").innerHTML=
      '<tr><td colspan="9" class="nh-empty">Could not load history.</td></tr>'; });
})();
</script>
"""


def render_npi_history() -> str:
    title = ck_page_title("Cleaning run history",
                          eyebrow="TOOLS · NPI CLAIMS CLEANER",
                          meta="quality tracked across runs")
    # .replace, not .format — the embedded JS is full of literal braces.
    body = _BODY.replace("{page_title}", title)
    return chartis_shell(
        body,
        title="Run history — NPI Claims Cleaner",
        active_nav="TOOLS",
        breadcrumbs=[("Tools", None), ("NPI Cleaner", "/npi-cleaner"),
                     ("Run history", None)],
        extra_css=_CSS,
        code="rcm_mc/ui/npi_history_page.py",
    )
