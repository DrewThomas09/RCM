"""Run-history page for the NPI Claims Cleaner (/npi-cleaner/history).

Longitudinal observability: quality-score trend across runs, a runs table,
and run-vs-run compare — "did the feed get better after the source fix?".
Data comes from /npi-cleaner/api/history (aggregate counts only, no PHI).
"""
from __future__ import annotations

from ._chartis_kit import chartis_shell, ck_page_title

_CSS = """
.nh-wrap{max-width:1080px;margin:0 auto}
.nh-lede{color:var(--ink-2,#4a5d57);font-size:13px;line-height:1.6;
  max-width:680px;margin:2px 0 6px}
/* ============ Analytics cards ============ */
.nh-trend,.nh-cmp{background:var(--panel,#fbfdfc);
  border:1px solid var(--line,#d2ddd7);border-radius:14px;
  padding:18px 20px;margin:16px 0}
.nh-cmp{display:none}
.nh-cmp.on{display:block}
.nh-hd{font-size:14px;font-weight:660;letter-spacing:-.01em;
  color:var(--ink,#11201c);margin-bottom:4px}
.nh-sub{font-size:12.5px;color:var(--ink-2,#4a5d57);line-height:1.55;
  margin:0 0 12px}
.nh-muted{color:var(--ink-2,#4a5d57);font-size:12.5px;line-height:1.55}
/* ============ Per-rule control row ============ */
.nh-ctl{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:2px 0 12px}
.nh-ctl-lbl{font-size:11px;font-weight:680;text-transform:uppercase;
  letter-spacing:.05em;color:var(--ink-2,#4a5d57)}
/* ============ Runs table ============ */
.nh-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.nh-tbl{width:100%;border-collapse:collapse;font-size:13px;min-width:600px}
.nh-tbl th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-2,#4a5d57);font-weight:640;text-align:left;padding:9px 10px;
  border-bottom:1px solid var(--line,#d2ddd7);white-space:nowrap}
.nh-tbl td{padding:9px 10px;color:var(--ink,#11201c);
  border-bottom:1px solid var(--line-soft,#e7eeea)}
.nh-tbl .num{text-align:right;font-variant-numeric:tabular-nums;
  white-space:nowrap}
.nh-tbl tbody tr:nth-child(even){
  background:color-mix(in srgb,var(--ink,#11201c) 2.5%,transparent)}
.nh-tbl tbody tr:hover{
  background:color-mix(in srgb,var(--green-deep,#0c7c66) 6%,transparent)}
.nh-tbl tbody tr:has(.nh-empty):hover{background:transparent}
.nh-tbl input[type=checkbox]{width:15px;height:15px;cursor:pointer;
  accent-color:var(--green-deep,#0c7c66);vertical-align:middle}
.nh-grade{font-weight:700;font-variant-numeric:tabular-nums}
.nh-grade.A,.nh-grade.B{color:var(--green-deep,#0c7c66)}
.nh-grade.C{color:#b06a00}
.nh-grade.D,.nh-grade.F{color:#a8331f}
/* injected comparison / wishlist tables can scroll on narrow viewports */
#nh-cmp-body,#nh-wish-box{overflow-x:auto;-webkit-overflow-scrolling:touch}
/* ============ Buttons + selects ============ */
.nh-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:14px}
.nh-btn{display:inline-flex;align-items:center;gap:6px;font-family:inherit;
  border:1px solid var(--line,#d2ddd7);background:var(--panel,#fbfdfc);
  color:var(--ink,#11201c);border-radius:9px;padding:7px 14px;
  font-size:12.5px;font-weight:600;cursor:pointer;
  transition:background .14s ease,border-color .14s ease,color .14s ease}
.nh-btn:hover{border-color:color-mix(in srgb,var(--green-deep,#0c7c66) 40%,var(--line,#d2ddd7));
  background:color-mix(in srgb,var(--green-deep,#0c7c66) 5%,transparent)}
.nh-btn:focus-visible{outline:2px solid var(--green-deep,#0c7c66);outline-offset:2px}
.nh-btn:disabled{opacity:.5;cursor:not-allowed}
.nh-btn.prim{background:var(--green-deep,#0c7c66);color:#fff;border-color:transparent;
  font-weight:640}
.nh-btn.prim:hover{background:var(--green,#075a4a);color:#fff}
.nh-btn.prim:disabled:hover{background:var(--green-deep,#0c7c66)}
select.nh-btn{padding:7px 11px;max-width:340px}
/* ============ Deltas + empty ============ */
.nh-delta-up{color:var(--green-deep,#0c7c66);font-weight:640}
.nh-delta-down{color:#a8331f;font-weight:640}
.nh-cmp-lede{margin-bottom:10px;font-size:13px;color:var(--ink,#11201c);line-height:1.5}
.nh-empty{padding:34px 20px;text-align:center;color:var(--ink-2,#4a5d57);font-size:13px}
@media (max-width:640px){
  .nh-trend,.nh-cmp{padding:16px 15px}
}
"""

_BODY = """
<div class="nh-wrap">
  {page_title}
  <p class="nh-lede">Every cleaning run records its aggregate scorecard
  (counts only — no claim rows, no PHI). Pick two runs below to compare.</p>

  <div class="nh-trend">
    <div class="nh-hd">Quality-score trend</div>
    <div class="nh-sub">Overall grade across every run, oldest to newest.</div>
    <div id="nh-trend-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <div class="nh-trend">
    <div class="nh-hd">Dimension trends</div>
    <div class="nh-sub">Each quality dimension across runs — which lever is
    moving the grade.</div>
    <div id="nh-dims-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <div class="nh-trend">
    <div class="nh-hd">Per-rule trend</div>
    <div class="nh-sub">Is a specific problem (bad codes, future dates,
    dupes …) getting better or worse across runs?</div>
    <div class="nh-ctl">
      <label class="nh-ctl-lbl" for="nh-rule">Rule</label>
      <select id="nh-rule" class="nh-btn"></select>
    </div>
    <div id="nh-rule-box"><div class="nh-empty">Loading…</div></div>
  </div>

  <div class="nh-trend">
    <div class="nh-hd">All runs</div>
    <div class="nh-sub">Tick two runs, then compare them side by side.</div>
    <div class="nh-scroll">
      <table class="nh-tbl">
        <thead><tr>
          <th></th><th>When</th><th>File</th><th class="num">Rows in</th>
          <th class="num">Rows out</th><th class="num">Dupes</th>
          <th class="num">Changes</th><th class="num">Score</th><th>Grade</th>
        </tr></thead>
        <tbody id="nh-rows">
          <tr><td colspan="9" class="nh-empty">Loading…</td></tr>
        </tbody>
      </table>
    </div>
    <div class="nh-actions">
      <button class="nh-btn prim" id="nh-compare" disabled>
        Compare selected runs</button>
      <a class="nh-btn" href="/npi-cleaner">← Back to the cleaner</a>
    </div>
  </div>

  <div class="nh-cmp" id="nh-cmp">
    <div class="nh-hd">Run comparison</div>
    <div id="nh-cmp-body"></div>
  </div>

  <div class="nh-trend" id="nh-wishlist">
    <div class="nh-hd">Build backlog — "missing something?" requests</div>
    <div class="nh-sub">Everything users asked the cleaner to add (from the
    card on the cleaner page). Triage here: open → planned →
    shipped / declined.</div>
    <div id="nh-wish-box"><div class="nh-empty">Loading…</div></div>
  </div>
</div>

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
    svg+='<path d="'+d+'" fill="none" stroke="#0c7c66" stroke-width="2"/>';
    pts.forEach(function(p,i){
      svg+='<circle cx="'+sx(i).toFixed(1)+'" cy="'+sy(p.score).toFixed(1)+
        '" r="3.4" fill="#0c7c66"><title>'+esc(p.file_name)+' — '+p.score+
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
      var ctl=sel.closest(".nh-ctl"); if(ctl) ctl.style.display="none";
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
        'fill="#b06a00" opacity=".85"><title>'+esc(p.f)+' — '+p.v+
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
    var h='<div class="nh-cmp-lede">'+esc(c.a.file_name)+' ('+c.a.score+
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

  // ---- Wishlist triage: move requests through the build backlog ----
  var WISH_STATUSES=["open","planned","shipped","declined"];
  function loadWishlist(){
    fetch("/npi-cleaner/api/wishlist").then(function(r){ return r.json(); })
      .then(function(j){
        var box=$("nh-wish-box"), reqs=j.requests||[];
        if(!reqs.length){
          box.innerHTML='<div class="nh-empty">No requests yet — the card '+
            'on the cleaner page feeds this backlog.</div>';
          return;
        }
        var h='<table class="nh-tbl"><thead><tr><th>When</th>'+
          '<th>Category</th><th>Request</th><th>Details</th>'+
          '<th>Status</th><th></th></tr></thead><tbody>';
        reqs.forEach(function(q){
          var opts=WISH_STATUSES.map(function(s){
            return '<option value="'+s+'"'+(s===q.status?' selected':'')+
              '>'+s+'</option>'; }).join("");
          h+='<tr><td>'+when(q.created)+'</td><td>'+esc(q.category)+
            '</td><td>'+esc(q.title)+'</td><td class="nh-muted">'+
            esc(q.details)+'</td><td><select class="nh-btn nh-wish-status" '+
            'data-id="'+q.id+'">'+opts+'</select></td>'+
            '<td><button class="nh-btn nh-wish-del" data-id="'+q.id+
            '">delete</button></td></tr>';
        });
        h+='</tbody></table>';
        box.innerHTML=h;
        box.querySelectorAll(".nh-wish-status").forEach(function(sel){
          sel.addEventListener("change", function(){
            fetch("/npi-cleaner/api/wishlist/status", {method:"POST",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({id:+this.getAttribute("data-id"),
                                   status:this.value})})
              .then(function(){ loadWishlist(); }).catch(function(){});
          });
        });
        box.querySelectorAll(".nh-wish-del").forEach(function(btn){
          btn.addEventListener("click", function(){
            fetch("/npi-cleaner/api/wishlist/delete", {method:"POST",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({id:+this.getAttribute("data-id")})})
              .then(function(){ loadWishlist(); }).catch(function(){});
          });
        });
      })
      .catch(function(){ $("nh-wish-box").innerHTML=
        '<div class="nh-empty">Could not load the backlog.</div>'; });
  }
  loadWishlist();

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
    )
