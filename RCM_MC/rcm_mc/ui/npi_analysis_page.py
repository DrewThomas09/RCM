"""Pivot / analysis workbench for a cleaned claims file — ``/npi-cleaner/analyze/<job>``.

A self-contained, Tableau-style pivot builder: assign any column to Rows,
Columns, Values (with Count / Sum / Avg / Min / Max) or Filters, and get a live
pivot table plus a chart (grouped bar / stacked bar / line) built with an
inline-SVG renderer — no chart library, CSP-safe. The cleaned rows are fetched
from ``/npi-cleaner/data/<job>`` (capped) and everything computes in the
browser, so pivoting and re-charting are instant.

Categorical palette is the validated dataviz reference set (blue / aqua /
yellow / violet / red / orange), CVD-separated; charts carry a legend for ≥2
series, direct value labels, hover tooltips, and a recessive grid. The pivot
table itself is the always-present table view.
"""
from __future__ import annotations

from ._chartis_kit import chartis_shell


_EXTRA_CSS = r"""
.an-wrap{max-width:1180px;margin:0 auto}
.an-bar{display:flex;justify-content:space-between;align-items:center;gap:12px;
  flex-wrap:wrap;margin-bottom:14px}
.an-back{font-size:13px;color:var(--green-deep,#0c7c66);text-decoration:none}
.an-back:hover{text-decoration:underline}
.an-meta{font-size:12px;color:var(--ink-2,#4a5d57);font-family:ui-monospace,Menlo,monospace}
.an-grid{display:grid;grid-template-columns:250px 1fr;gap:18px}
@media(max-width:820px){.an-grid{grid-template-columns:1fr}}
.an-fields{border:1px solid var(--line,#d2ddd7);border-radius:12px;
  background:var(--panel,#fbfdfc);padding:12px;max-height:70vh;overflow:auto}
.an-fields h4{margin:2px 0 8px;font-size:12px;text-transform:uppercase;
  letter-spacing:.04em;color:var(--ink-2,#4a5d57)}
.an-field{display:flex;align-items:center;justify-content:space-between;gap:6px;
  padding:5px 7px;border-radius:8px;font-size:12.5px}
.an-field:hover{background:color-mix(in srgb,var(--green-deep,#0c7c66) 5%,transparent)}
.an-field .fn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.an-field .num{color:var(--green-deep,#0c7c66);font-size:10px;margin-left:4px}
.an-field .btns{display:flex;gap:3px;flex:none}
.an-field button{appearance:none;border:1px solid var(--line,#d2ddd7);
  background:var(--paper,#f3f7f5);border-radius:5px;width:22px;height:22px;
  font-size:11px;font-weight:700;cursor:pointer;color:var(--ink-2,#4a5d57);padding:0}
.an-field button:hover{border-color:var(--green-deep,#0c7c66);color:var(--green-deep,#0c7c66)}
.an-zones{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:10px;margin-bottom:14px}
.an-zone{border:1px dashed var(--line,#c9d6d0);border-radius:10px;padding:9px 11px;
  background:var(--panel,#fbfdfc);min-height:56px}
.an-zone h5{margin:0 0 6px;font-size:11px;text-transform:uppercase;
  letter-spacing:.04em;color:var(--ink-2,#4a5d57)}
.an-chip{display:inline-flex;align-items:center;gap:5px;background:color-mix(in srgb,var(--green-deep,#0c7c66) 10%,transparent);
  color:var(--green-deep,#0c7c66);border-radius:20px;padding:2px 9px;font-size:12px;
  margin:2px 4px 2px 0;font-weight:600}
.an-chip b{cursor:pointer;font-weight:700}
.an-agg select,.an-ctl select{padding:4px 6px;border:1px solid var(--line,#d2ddd7);
  border-radius:6px;font-size:12px;background:var(--panel,#fbfdfc);color:var(--ink,#11201c)}
.an-ctls{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.an-ptbl-wrap{overflow:auto;border:1px solid var(--line,#d2ddd7);border-radius:12px;max-height:60vh}
table.an-ptbl{border-collapse:collapse;font-size:12.5px;width:100%}
.an-ptbl th,.an-ptbl td{padding:6px 10px;border-bottom:1px solid var(--line-soft,#e7eeea);
  border-right:1px solid var(--line-soft,#e7eeea);text-align:right;white-space:nowrap}
.an-ptbl th{background:var(--panel,#fbfdfc);position:sticky;top:0;font-weight:640;
  color:var(--ink-2,#4a5d57);text-align:right}
.an-ptbl th.k,.an-ptbl td.k{text-align:left;font-weight:600;color:var(--ink,#11201c);
  position:sticky;left:0;background:var(--panel,#fbfdfc)}
.an-ptbl tr.tot td{font-weight:700;background:color-mix(in srgb,var(--green-deep,#0c7c66) 6%,transparent)}
.an-ptbl td.tot{font-weight:700}
.an-chart{border:1px solid var(--line,#d2ddd7);border-radius:12px;padding:14px;
  margin-top:16px;background:var(--panel,#fbfdfc)}
.an-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:12px}
.an-legend .lg{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2,#4a5d57)}
.an-legend .sw{width:11px;height:11px;border-radius:3px}
.an-empty{color:var(--ink-2,#4a5d57);font-size:13px;padding:24px;text-align:center}
.an-tip{position:fixed;pointer-events:none;background:#11201c;color:#fff;
  font-size:11.5px;padding:5px 8px;border-radius:6px;opacity:0;transition:opacity .1s;
  z-index:50;white-space:nowrap;font-family:ui-monospace,Menlo,monospace}
.an-actions{display:flex;gap:10px;margin:10px 0}
.an-btn{appearance:none;border:1px solid var(--line,#d2ddd7);background:var(--paper,#f3f7f5);
  border-radius:8px;padding:6px 12px;font-size:12.5px;cursor:pointer;color:var(--ink,#11201c)}
.an-btn:hover{border-color:var(--green-deep,#0c7c66)}
.an-btn.prim{background:var(--green-deep,#0c7c66);color:#fff;border-color:var(--green-deep,#0c7c66)}
:root[data-theme="dark"] .an-tip{background:#000}
"""


def _body(job_id: str, available: bool, src_name: str) -> str:
    if not available:
        return f"""
<div class="an-wrap">
  <div class="an-bar"><a class="an-back" href="/npi-cleaner">← Back to NPI Cleaner</a></div>
  <div class="an-empty">This analysis session has expired or the job was not
  found (the in-memory job store resets when the server restarts). Re-run the
  cleaner and open analysis again.</div>
</div>"""
    import html as _h
    safe_job = _h.escape(job_id)
    safe_name = _h.escape(src_name or "cleaned data")
    return f"""
<div class="an-wrap" data-job="{safe_job}">
  <div class="an-bar">
    <a class="an-back" href="/npi-cleaner">← Back to NPI Cleaner</a>
    <span class="an-meta" id="an-meta">Loading {safe_name}…</span>
  </div>

  <div class="an-grid">
    <div class="an-fields">
      <h4>Fields</h4>
      <div id="an-fieldlist"></div>
    </div>

    <div>
      <div class="an-zones">
        <div class="an-zone"><h5>Rows</h5><div id="zone-rows"></div></div>
        <div class="an-zone"><h5>Columns</h5><div id="zone-cols"></div></div>
        <div class="an-zone"><h5>Values</h5><div id="zone-vals"></div>
          <div class="an-agg" style="margin-top:6px">
            <select id="an-agg">
              <option value="count">Count</option>
              <option value="sum">Sum</option>
              <option value="avg">Average</option>
              <option value="min">Min</option>
              <option value="max">Max</option>
            </select>
          </div>
        </div>
        <div class="an-zone"><h5>Filters</h5><div id="zone-filters"></div>
          <div id="an-filter-values"></div></div>
      </div>

      <div class="an-ctls">
        <label class="an-ctl">Chart
          <select id="an-charttype">
            <option value="bar">Grouped bar</option>
            <option value="stacked">Stacked bar</option>
            <option value="line">Line</option>
          </select></label>
        <label class="an-ctl">Top
          <select id="an-topn">
            <option value="12">12 rows</option>
            <option value="20">20 rows</option>
            <option value="30">30 rows</option>
            <option value="0">All</option>
          </select></label>
        <div class="an-actions" style="margin:0">
          <button class="an-btn" id="an-reset">Reset</button>
          <button class="an-btn prim" id="an-dl">Download pivot CSV</button>
        </div>
      </div>

      <div class="an-chart" id="an-chart-box"></div>

      <div class="an-ptbl-wrap"><div id="an-ptbl"></div></div>
    </div>
  </div>
  <div class="an-tip" id="an-tip"></div>
</div>"""


_EXTRA_JS = r"""
(function(){
  var $=function(id){return document.getElementById(id);};
  var PAL=["#2a78d6","#1baf7a","#eda100","#4a3aa7","#e34948","#eb6834","#e87ba4","#008300"];
  function palDark(){var d={"#2a78d6":"#3987e5","#1baf7a":"#199e70","#eda100":"#c98500",
    "#4a3aa7":"#9085e9","#e34948":"#e66767","#eb6834":"#d95926","#e87ba4":"#d55181"};return d;}
  var wrap=document.querySelector(".an-wrap"); if(!wrap) return;
  var job=wrap.getAttribute("data-job"); if(!job) return;

  var DATA={columns:[],rows:[]}, NUM={}, state={rows:[],cols:[],val:null,filters:{},
    agg:"count",chart:"bar",topn:12};

  function esc(s){var d=document.createElement("div");d.textContent=(s==null?"":s);return d.innerHTML;}
  function isNum(v){ if(v===""||v==null) return false; return !isNaN(parseFloat(v))&&isFinite(v.replace?v.replace(/[,$]/g,""):v); }
  function num(v){ var n=parseFloat(String(v).replace(/[,$]/g,"")); return isNaN(n)?0:n; }
  function fmtNum(n){ if(n==null||isNaN(n)) return ""; var a=Math.abs(n);
    if(a>=1e9)return (n/1e9).toFixed(2)+"B"; if(a>=1e6)return (n/1e6).toFixed(2)+"M";
    if(a>=1e3)return (n/1e3).toFixed(1)+"K"; return (Math.round(n*100)/100).toLocaleString(); }

  fetch("/npi-cleaner/data/"+job).then(function(r){return r.json();}).then(function(j){
    if(j.error){ $("an-meta").textContent=j.error; return; }
    DATA=j; detectNumeric();
    $("an-meta").textContent=(j.total_rows||j.rows.length).toLocaleString()+
      " rows × "+j.columns.length+" columns"+(j.truncated?" (showing first "+j.rows.length.toLocaleString()+")":"");
    // sensible defaults: first text col as Rows, count as value
    var firstText=j.columns.find(function(c,i){return !NUM[c];});
    if(firstText){ state.rows=[firstText]; }
    renderFields(); renderZones(); recompute();
  }).catch(function(){ $("an-meta").textContent="Could not load data."; });

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
        '<button data-f="'+esc(c)+'" data-z="rows" title="Rows">R</button>'+
        '<button data-f="'+esc(c)+'" data-z="cols" title="Columns">C</button>'+
        '<button data-f="'+esc(c)+'" data-z="vals" title="Values">V</button>'+
        '<button data-f="'+esc(c)+'" data-z="filters" title="Filter">F</button>'+
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

  function chip(f){ return '<span class="an-chip">'+esc(f)+' <b data-x="'+esc(f)+'">×</b></span>'; }
  function renderZones(){
    $("zone-rows").innerHTML=state.rows.map(chip).join("")||'<span class="an-empty" style="padding:2px;font-size:12px">drag a field via R</span>';
    $("zone-cols").innerHTML=state.cols.map(chip).join("");
    $("zone-vals").innerHTML=state.val?chip(state.val):'<span class="an-empty" style="padding:2px;font-size:12px">count of rows</span>';
    var fk=Object.keys(state.filters);
    $("zone-filters").innerHTML=fk.map(chip).join("");
    $("an-agg").value=state.agg;
    document.querySelectorAll(".an-chip b").forEach(function(x){
      x.addEventListener("click",function(){ unassign(x.getAttribute("data-x")); });
    });
    renderFilterValues();
  }

  function distinct(field){
    var ci=DATA.columns.indexOf(field), s={};
    for(var i=0;i<DATA.rows.length;i++){ s[DATA.rows[i][ci]]=1; }
    return Object.keys(s).sort();
  }
  function renderFilterValues(){
    var fk=Object.keys(state.filters); var html="";
    fk.forEach(function(f){
      var vals=distinct(f).slice(0,200);
      html+='<div style="margin-top:6px"><div style="font-size:11px;color:var(--ink-2)">'+esc(f)+'</div>'+
        '<select multiple size="4" data-filter="'+esc(f)+'" style="width:100%;font-size:12px">'+
        vals.map(function(v){var sel=(state.filters[f]&&state.filters[f].indexOf(v)>=0)?" selected":"";
          return '<option value="'+esc(v)+'"'+sel+'>'+esc(v||"(blank)")+'</option>';}).join("")+'</select></div>';
    });
    $("an-filter-values").innerHTML=html;
    $("an-filter-values").querySelectorAll("select").forEach(function(sel){
      sel.addEventListener("change",function(){
        var f=sel.getAttribute("data-filter");
        var chosen=Array.prototype.map.call(sel.selectedOptions,function(o){return o.value;});
        state.filters[f]=chosen.length?chosen:null; recompute();
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
    rKeys.sort(function(a,b){return (rowTotal(b)||0)-(rowTotal(a)||0);});
    cKeys.sort();
    PIVOT={rKeys:rKeys,cKeys:cKeys,cells:cells,aggVal:aggVal,rowTotal:rowTotal,
           singleCol:(colIdx<0)};
    renderTable(); renderChart();
  }

  function renderTable(){
    if(!PIVOT||!PIVOT.rKeys.length){ $("an-ptbl").innerHTML='<div class="an-empty">No data for this pivot.</div>'; return; }
    var p=PIVOT, cols=p.cKeys, showTot=!p.singleCol;
    var h='<table class="an-ptbl"><thead><tr><th class="k">'+esc(state.rows.join(" ▸ ")||"All")+'</th>';
    cols.forEach(function(c){ h+='<th>'+esc(p.singleCol?aggLabel():c)+'</th>'; });
    if(showTot)h+='<th class="tot">Total</th>';
    h+='</tr></thead><tbody>';
    var colTot={}; cols.forEach(function(c){colTot[c]=0;}); var grand=0;
    p.rKeys.forEach(function(rk){
      h+='<tr><td class="k">'+esc(rk)+'</td>';
      cols.forEach(function(c){ var v=p.aggVal(p.cells[rk+"||"+c]);
        colTot[c]+=(v||0); h+='<td>'+(v==null?"":fmtNum(v))+'</td>'; });
      if(showTot){ var rt=p.rowTotal(rk); grand+=(rt||0); h+='<td class="tot">'+fmtNum(rt)+'</td>'; }
      h+='</tr>';
    });
    h+='<tr class="tot"><td class="k">Total</td>';
    cols.forEach(function(c){ h+='<td>'+fmtNum(colTot[c])+'</td>'; });
    if(showTot)h+='<td class="tot">'+fmtNum(grand)+'</td>';
    h+='</tr></tbody></table>';
    $("an-ptbl").innerHTML=h;
  }
  function aggLabel(){ return ({count:"Count",sum:"Sum",avg:"Average",min:"Min",max:"Max"})[state.agg]+
    (state.val?" of "+state.val:""); }

  function palette(){ var dark=matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches;
    var t=document.documentElement.getAttribute("data-theme");
    dark=(t==="dark")||(t!=="light"&&dark);
    if(!dark)return PAL; var d=palDark(); return PAL.map(function(c){return d[c]||c;}); }

  function renderChart(){
    var box=$("an-chart-box");
    if(!PIVOT||!PIVOT.rKeys.length){ box.innerHTML='<div class="an-empty">No chart.</div>'; return; }
    var p=PIVOT, topn=state.topn>0?state.topn:p.rKeys.length;
    var rKeys=p.rKeys.slice(0,topn);
    var series=p.singleCol?[aggLabel()]:p.cKeys;
    var valOf=function(rk,si){ var ck=p.singleCol?"__val":p.cKeys[si]; return p.aggVal(p.cells[rk+"||"+ck])||0; };
    var pal=palette();
    var W=Math.max(560, box.clientWidth-4), H=340, L=54, R=16, T=16, B=84;
    var iw=W-L-R, ih=H-T-B;
    // scale
    var maxV=0;
    rKeys.forEach(function(rk,ri){ if(state.chart==="stacked"){ var s=0; series.forEach(function(_,si){s+=valOf(rk,si);}); maxV=Math.max(maxV,s);}
      else series.forEach(function(_,si){maxV=Math.max(maxV,valOf(rk,si));}); });
    maxV=maxV||1; var ticks=4;
    function sy(v){ return T+ih-(v/maxV)*ih; }
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" preserveAspectRatio="xMidYMid meet" font-family="Inter,system-ui,sans-serif">';
    // gridlines
    for(var t=0;t<=ticks;t++){ var gv=maxV*t/ticks, gy=sy(gv);
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" stroke="'+
        'rgba(120,130,125,.18)" stroke-width="1"/>';
      svg+='<text x="'+(L-6)+'" y="'+(gy+3)+'" text-anchor="end" font-size="10" fill="rgba(120,130,125,.9)">'+fmtNum(gv)+'</text>'; }
    var bw=iw/rKeys.length, tips=[];
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
      } else { // grouped
        var gw=bw*0.8/series.length;
        series.forEach(function(sname,si){ var v=valOf(rk,si);
          var bx=x0+bw*0.1+si*gw, by=sy(v);
          svg+='<rect x="'+bx+'" y="'+by+'" width="'+Math.max(1,gw-2)+'" height="'+Math.max(0,(T+ih)-by)+
            '" fill="'+pal[si%pal.length]+'" rx="3" data-tip="'+esc(rk+" · "+sname+": "+fmtNum(v))+'"/>';
        });
      }
      // x label
      var lab=rk.length>14?rk.slice(0,13)+"…":rk;
      svg+='<text x="'+(x0+bw/2)+'" y="'+(T+ih+14)+'" text-anchor="end" font-size="10" '+
        'fill="var(--ink-2,#4a5d57)" transform="rotate(-35 '+(x0+bw/2)+' '+(T+ih+14)+')">'+esc(lab)+'</text>';
    });
    if(state.chart==="line"){
      series.forEach(function(sname,si){ var pts=[];
        rKeys.forEach(function(rk,ri){ var v=valOf(rk,si); pts.push([L+ri*bw+bw/2, sy(v)]); });
        var d=pts.map(function(pp,i){return (i?"L":"M")+pp[0]+" "+pp[1];}).join(" ");
        svg+='<path d="'+d+'" fill="none" stroke="'+pal[si%pal.length]+'" stroke-width="2"/>';
        pts.forEach(function(pp,ri){ svg+='<circle cx="'+pp[0]+'" cy="'+pp[1]+'" r="3.5" fill="'+
          pal[si%pal.length]+'" stroke="var(--panel,#fff)" stroke-width="1.5" data-tip="'+
          esc(rKeys[ri]+" · "+sname+": "+fmtNum(valOf(rKeys[ri],si)))+'"/>'; });
      });
    }
    // axis baseline
    svg+='<line x1="'+L+'" y1="'+(T+ih)+'" x2="'+(W-R)+'" y2="'+(T+ih)+'" stroke="rgba(120,130,125,.5)" stroke-width="1"/>';
    svg+='</svg>';
    var legend='';
    if(series.length>=2){ legend='<div class="an-legend">'+series.map(function(s,si){
      return '<span class="lg"><span class="sw" style="background:'+pal[si%pal.length]+'"></span>'+esc(s)+'</span>'; }).join("")+'</div>'; }
    box.innerHTML='<div style="font-size:13px;font-weight:640;margin-bottom:6px">'+esc(aggLabel())+
      (state.cols.length?" by "+esc(state.rows.join(", ")||"all")+" × "+esc(state.cols[0]):" by "+esc(state.rows.join(", ")||"all"))+
      '</div>'+svg+legend;
    // hover
    var tip=$("an-tip");
    box.querySelectorAll("[data-tip]").forEach(function(el){
      el.addEventListener("mousemove",function(e){ tip.textContent=el.getAttribute("data-tip");
        tip.style.left=(e.clientX+12)+"px"; tip.style.top=(e.clientY+12)+"px"; tip.style.opacity="1"; });
      el.addEventListener("mouseleave",function(){ tip.style.opacity="0"; });
    });
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
  $("an-topn").addEventListener("change",function(){ state.topn=parseInt($("an-topn").value,10); renderChart(); });
  $("an-reset").addEventListener("click",function(){ state.rows=[];state.cols=[];state.val=null;
    state.filters={};state.agg="count"; renderZones(); recompute(); });
  $("an-dl").addEventListener("click",function(){ var csv=pivotCSV();
    var a=document.createElement("a"); a.href="data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
    a.download="pivot.csv"; a.click(); });
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
        code="rcm_mc/ui/npi_analysis_page.py",
    )
