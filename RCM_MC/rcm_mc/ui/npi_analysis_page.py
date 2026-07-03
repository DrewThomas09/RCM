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
.an-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px;margin-bottom:14px}
.an-tile{border:1px solid var(--line,#d2ddd7);border-radius:12px;
  background:var(--panel,#fbfdfc);padding:12px 14px}
.an-tile .k{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-2,#4a5d57)}
.an-tile .v{font-size:22px;font-weight:680;letter-spacing:-.02em;margin-top:3px;
  font-variant-numeric:tabular-nums}
.an-views{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.an-views-lbl{font-size:12px;color:var(--ink-2,#4a5d57);font-weight:600}
.an-btn.vw{border-radius:20px;font-size:12px;padding:4px 11px}
.an-ptbl th.k{cursor:default}
.an-ptbl th.sortable{cursor:pointer}
.an-ptbl th.sortable:hover{color:var(--green-deep,#0c7c66)}
.an-ptbl th .arr{font-size:9px;margin-left:2px}
.an-scatter-ctl{display:none;gap:10px;align-items:center}
.an-scatter-ctl.on{display:flex}
.an-prof{border:1px solid var(--line,#d2ddd7);border-radius:12px;margin:6px 0 14px;
  overflow:auto;max-height:320px}
.an-prof table{border-collapse:collapse;width:100%;font-size:12px}
.an-prof th,.an-prof td{padding:5px 9px;border-bottom:1px solid var(--line-soft,#e7eeea);text-align:left;white-space:nowrap}
.an-prof th{background:var(--panel,#fbfdfc);position:sticky;top:0;font-weight:640;color:var(--ink-2,#4a5d57)}
.an-prof .bar{height:6px;border-radius:3px;background:var(--green-deep,#0c7c66);display:inline-block;vertical-align:middle}
.an-cf-badge{color:var(--green-deep,#0c7c66);font-size:10px;margin-left:3px}
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

  <div class="an-tiles" id="an-tiles"></div>

  <div class="an-views" id="an-views">
    <span class="an-views-lbl">Quick views:</span>
    <button class="an-btn vw" data-view="rows_by_billing">Claims by billing NPI</button>
    <button class="an-btn vw" data-view="amt_by_state">Allowed $ by state</button>
    <button class="an-btn vw" data-view="amt_by_hcpcs">Allowed $ by procedure</button>
    <button class="an-btn vw" data-view="count_by_payer">Claims by payer</button>
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
            <option value="heatmap">Heatmap</option>
            <option value="scatter">Scatter</option>
            <option value="correlation">Correlation matrix</option>
          </select></label>
        <label class="an-ctl">Top
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
        <div class="an-actions" style="margin:0">
          <button class="an-btn" id="an-reset">Reset</button>
          <button class="an-btn" id="an-png">Export chart PNG</button>
          <button class="an-btn prim" id="an-dl">Download pivot CSV</button>
        </div>
      </div>

      <div class="an-ctls" style="margin-top:-4px">
        <label class="an-ctl">Saved views
          <select id="an-views-sel"><option value="">—</option></select></label>
        <button class="an-btn" id="an-save-view">Save current view</button>
        <button class="an-btn" id="an-del-view">Delete</button>
        <span style="width:1px;height:20px;background:var(--line,#d2ddd7)"></span>
        <label class="an-ctl">New field
          <select id="an-cf-a"></select></label>
        <select id="an-cf-op" class="an-ctl">
          <option value="div">÷</option><option value="sub">−</option>
          <option value="mul">×</option><option value="add">+</option></select>
        <select id="an-cf-b"></select>
        <input id="an-cf-name" placeholder="name (optional)"
          style="padding:5px 7px;border:1px solid var(--line,#d2ddd7);border-radius:6px;font-size:12px;width:130px">
        <button class="an-btn" id="an-cf-add">Add field</button>
        <button class="an-btn" id="an-profile-toggle">Profile columns</button>
      </div>
      <div id="an-profile"></div>

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

  var DATA={columns:[],rows:[]}, NUM={}, COMPUTED={}, state={rows:[],cols:[],val:null,filters:{},
    agg:"count",chart:"bar",topn:12,pct:false,sortCol:null,sortDir:-1,
    sx:null,sy:null,scolor:null};

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
    populateScatterSelects();
    renderStats(); renderFields(); renderZones(); recompute();
  }).catch(function(){ $("an-meta").textContent="Could not load data."; });

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
    var tiles=[["Rows", (DATA.total_rows||DATA.rows.length).toLocaleString()]];
    var bi=colIdxByHint(["billingnpi","billnpi","npi"]);
    var dc=distinctCount(bi); if(dc!=null)tiles.push(["Distinct NPIs", dc.toLocaleString()]);
    var ai=colIdxByHint(["allowedamt","allowed","paidamt","chargeamt","billedamt"]);
    var sm=sumCol(ai); if(sm!=null)tiles.push(["Total $ (allowed)", "$"+fmtNum(sm)]);
    var si=colIdxByHint(["providerstate","state"]);
    var sc=distinctCount(si); if(sc!=null)tiles.push(["States", sc.toLocaleString()]);
    var hi=colIdxByHint(["hcpcs","cpt","proccode","procedurecode"]);
    var hc=distinctCount(hi); if(hc!=null)tiles.push(["Procedures", hc.toLocaleString()]);
    $("an-tiles").innerHTML=tiles.map(function(t){
      return '<div class="an-tile"><div class="k">'+esc(t[0])+'</div><div class="v">'+esc(t[1])+'</div></div>';
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
      var pct=DATA.rows.length?Math.round(filled/DATA.rows.length*100):0;
      var detail="";
      if(NUM[c]&&nums.length){ var mn=Math.min.apply(null,nums),mx=Math.max.apply(null,nums),
        mean=nums.reduce(function(a,b){return a+b;},0)/nums.length;
        detail=fmtNum(mn)+" / "+fmtNum(mx)+" / "+fmtNum(mean); }
      else { detail=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a];}).slice(0,3)
        .map(function(k){return esc(k||"(blank)")+" ("+counts[k]+")";}).join(", "); }
      h+='<tr><td><b>'+esc(c)+'</b>'+(COMPUTED[c]?'<span class="an-cf-badge">ƒ</span>':'')+'</td>'+
        '<td>'+(NUM[c]?"numeric":"text")+'</td><td>'+Object.keys(distinct).length.toLocaleString()+'</td>'+
        '<td><span class="bar" style="width:'+Math.max(2,pct*0.5)+'px"></span> '+pct+'%</td>'+
        '<td>'+detail+'</td></tr>';
    });
    h+='</tbody></table></div>'; box.innerHTML=h;
  }

  // ---- PNG export ----
  function exportPNG(){
    var svg=$("an-chart-box").querySelector("svg");
    if(!svg){ alert("PNG export works for bar/line/scatter charts (the heatmap is a table)."); return; }
    var xml=new XMLSerializer().serializeToString(svg);
    var vb=svg.getAttribute("viewBox").split(" "), W=parseFloat(vb[2]), H=parseFloat(vb[3]);
    var scale=2, canvas=document.createElement("canvas"); canvas.width=W*scale; canvas.height=H*scale;
    var img=new Image();
    img.onload=function(){ var ctx=canvas.getContext("2d");
      ctx.fillStyle=getComputedStyle(document.body).backgroundColor||"#fff";
      ctx.fillRect(0,0,canvas.width,canvas.height); ctx.scale(scale,scale); ctx.drawImage(img,0,0);
      var a=document.createElement("a"); a.href=canvas.toDataURL("image/png"); a.download="chart.png"; a.click(); };
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

  function renderTable(){
    if(!PIVOT||!PIVOT.rKeys.length){ $("an-ptbl").innerHTML='<div class="an-empty">No data for this pivot.</div>'; return; }
    var p=PIVOT, cols=p.cKeys, showTot=!p.singleCol;
    function arr(key){ return state.sortCol===key?('<span class="arr">'+(state.sortDir<0?"▼":"▲")+'</span>'):''; }
    var h='<table class="an-ptbl"><thead><tr>'+
      '<th class="k sortable" data-sort="__row__">'+esc(state.rows.join(" ▸ ")||"All")+arr("__row__")+'</th>';
    cols.forEach(function(c){ var lbl=p.singleCol?aggLabel():c;
      h+='<th class="sortable" data-sort="'+esc(c)+'">'+esc(lbl)+arr(c)+'</th>'; });
    if(showTot)h+='<th class="tot sortable" data-sort="__default__">Total'+
      (state.sortCol==null||state.sortCol==="__default__"?'<span class="arr">▼</span>':'')+'</th>';
    h+='</tr></thead><tbody>';
    var colTot={}; cols.forEach(function(c){colTot[c]=0;}); var grand=0;
    p.rKeys.forEach(function(rk){
      h+='<tr><td class="k">'+esc(rk)+'</td>';
      cols.forEach(function(c){ var v=p.aggVal(p.cells[rk+"||"+c]);
        colTot[c]+=(v||0); h+='<td>'+disp(v)+'</td>'; });
      if(showTot){ var rt=p.rowTotal(rk); grand+=(rt||0); h+='<td class="tot">'+disp(rt)+'</td>'; }
      h+='</tr>';
    });
    h+='<tr class="tot"><td class="k">Total</td>';
    cols.forEach(function(c){ h+='<td>'+disp(colTot[c])+'</td>'; });
    if(showTot)h+='<td class="tot">'+disp(grand)+'</td>';
    h+='</tr></tbody></table>';
    $("an-ptbl").innerHTML=h;
    $("an-ptbl").querySelectorAll("th.sortable").forEach(function(th){
      th.addEventListener("click",function(){ var key=th.getAttribute("data-sort");
        if(state.sortCol===key){ state.sortDir=-state.sortDir; } else { state.sortCol=key; state.sortDir=-1; }
        recompute(); });
    });
  }
  function aggLabel(){ return ({count:"Count",sum:"Sum",avg:"Average",min:"Min",max:"Max"})[state.agg]+
    (state.val?" of "+state.val:""); }

  function palette(){ var dark=matchMedia&&matchMedia("(prefers-color-scheme:dark)").matches;
    var t=document.documentElement.getAttribute("data-theme");
    dark=(t==="dark")||(t!=="light"&&dark);
    if(!dark)return PAL; var d=palDark(); return PAL.map(function(c){return d[c]||c;}); }

  function bindTips(box){
    var tip=$("an-tip");
    box.querySelectorAll("[data-tip]").forEach(function(el){
      el.addEventListener("mousemove",function(e){ tip.textContent=el.getAttribute("data-tip");
        tip.style.left=(e.clientX+12)+"px"; tip.style.top=(e.clientY+12)+"px"; tip.style.opacity="1"; });
      el.addEventListener("mouseleave",function(){ tip.style.opacity="0"; });
    });
  }

  function renderScatter(){
    var box=$("an-chart-box");
    var xi=DATA.columns.indexOf(state.sx||$("an-sx").value);
    var yi=DATA.columns.indexOf(state.sy||$("an-sy").value);
    var col=$("an-scolor").value, coli=col?DATA.columns.indexOf(col):-1;
    if(xi<0||yi<0){ box.innerHTML='<div class="an-empty">Pick two numeric fields for X and Y.</div>'; return; }
    var pts=[]; var cats={}, catList=[];
    for(var i=0;i<DATA.rows.length;i++){ var row=DATA.rows[i]; if(!passesFilters(row))continue;
      var x=num(row[xi]), y=num(row[yi]); var c=coli>=0?String(row[coli]):"";
      if(coli>=0 && !(c in cats)){ cats[c]=catList.length; catList.push(c); }
      pts.push([x,y,c]); }
    if(!pts.length){ box.innerHTML='<div class="an-empty">No points.</div>'; return; }
    var xs=pts.map(function(p){return p[0];}), ys=pts.map(function(p){return p[1];});
    var xmin=Math.min.apply(null,xs), xmax=Math.max.apply(null,xs);
    var ymin=Math.min.apply(null,ys), ymax=Math.max.apply(null,ys);
    if(xmax===xmin)xmax=xmin+1; if(ymax===ymin)ymax=ymin+1;
    var pal=palette();
    var W=Math.max(560,box.clientWidth-4),H=360,L=56,R=16,T=16,B=40, iw=W-L-R, ih=H-T-B;
    function sx(v){return L+(v-xmin)/(xmax-xmin)*iw;} function sy(v){return T+ih-(v-ymin)/(ymax-ymin)*ih;}
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="100%" preserveAspectRatio="xMidYMid meet">';
    for(var t=0;t<=4;t++){ var gy=T+ih-(t/4)*ih, gv=ymin+(ymax-ymin)*t/4;
      svg+='<line x1="'+L+'" y1="'+gy+'" x2="'+(W-R)+'" y2="'+gy+'" stroke="rgba(120,130,125,.15)"/>';
      svg+='<text x="'+(L-6)+'" y="'+(gy+3)+'" text-anchor="end" font-size="10" fill="rgba(120,130,125,.9)">'+fmtNum(gv)+'</text>'; }
    pts.slice(0,4000).forEach(function(pp){ var c=coli>=0?pal[cats[pp[2]]%pal.length]:pal[0];
      svg+='<circle cx="'+sx(pp[0]).toFixed(1)+'" cy="'+sy(pp[1]).toFixed(1)+'" r="3.2" fill="'+c+
        '" fill-opacity="0.6" data-tip="'+esc(state.sx+"="+fmtNum(pp[0])+", "+state.sy+"="+fmtNum(pp[1])+(pp[2]?" · "+pp[2]:""))+'"/>'; });
    svg+='<text x="'+(L+iw/2)+'" y="'+(H-6)+'" text-anchor="middle" font-size="11" fill="var(--ink-2,#4a5d57)">'+esc(state.sx)+'</text>';
    svg+='</svg>';
    var legend='';
    if(coli>=0 && catList.length>=2 && catList.length<=8){ legend='<div class="an-legend">'+catList.map(function(c,i){
      return '<span class="lg"><span class="sw" style="background:'+pal[i%pal.length]+'"></span>'+esc(c)+'</span>';}).join("")+'</div>'; }
    box.innerHTML='<div style="font-size:13px;font-weight:640;margin-bottom:6px">'+esc(state.sy)+' vs '+esc(state.sx)+
      ' ('+pts.length.toLocaleString()+' points)</div>'+svg+legend;
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
    if(cols.length<2){ box.innerHTML='<div class="an-empty">Need at least two '+
      'numeric fields for a correlation matrix (add measures or a computed field).</div>'; return; }
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
    // Diverging ramp (ColorBrewer RdBu): blue = negative, red = positive.
    var ramp=["#2166ac","#67a9cf","#d1e5f0","#f7f7f7","#fddbc7","#ef8a62","#b2182b"];
    function color(r){ if(r==null) return "transparent";
      var t=(r+1)/2, k=Math.max(0,Math.min(ramp.length-1, Math.round(t*(ramp.length-1)))); return ramp[k]; }
    var h='<div style="font-size:13px;font-weight:640;margin-bottom:6px">Pearson correlation'+
      (capped?' (first 12 numeric fields)':'')+'</div>';
    h+='<div style="overflow:auto"><table class="an-ptbl" style="border:0"><thead><tr><th class="k"></th>';
    cols.forEach(function(c){ h+='<th style="white-space:nowrap;font-weight:600;font-size:11px">'+esc(c)+'</th>'; });
    h+='</tr></thead><tbody>';
    cols.forEach(function(c,a){ h+='<tr><td class="k">'+esc(c)+'</td>';
      cols.forEach(function(_,b){ var rr=R[a][b], nn=N[a][b];
        var strong=rr!=null&&Math.abs(rr)>0.55;
        h+='<td style="background:'+color(rr)+';color:'+(strong?"#fff":"var(--ink,#1a2332)")+
          ';text-align:center;min-width:52px" data-tip="'+
          esc(c+" × "+cols[b]+": r="+(rr==null?"n/a":rr.toFixed(2))+" (n="+nn.toLocaleString()+")")+'">'+
          (rr==null?"·":rr.toFixed(2))+'</td>'; });
      h+='</tr>'; });
    h+='</tbody></table></div>';
    h+='<div class="an-legend" style="margin-top:8px;align-items:center">−1'+
      ramp.map(function(cl){return '<span class="sw" style="background:'+cl+';width:22px"></span>';}).join("")+
      '+1 &nbsp;<span style="color:var(--ink-2,#4a5d57)">blue negative · red positive</span></div>';
    box.innerHTML=h; bindTips(box);
  }

  function renderHeatmap(){
    var box=$("an-chart-box"), p=PIVOT;
    var rKeys=p.rKeys.slice(0, state.topn>0?state.topn:p.rKeys.length);
    var cols=p.singleCol?[aggLabel()]:p.cKeys;
    var maxV=0,minV=Infinity;
    rKeys.forEach(function(rk){ (p.singleCol?["__val"]:p.cKeys).forEach(function(ck){
      var v=p.aggVal(p.cells[rk+"||"+ck]); if(v!=null){maxV=Math.max(maxV,v);minV=Math.min(minV,v);} }); });
    if(minV===Infinity)minV=0; maxV=maxV||1;
    // sequential blue ramp (validated reference ramp)
    var ramp=["#eef4fc","#cde2fb","#9ec5f4","#6da7ec","#3987e5","#256abf","#184f95"];
    function color(v){ if(v==null)return "transparent"; var t=(v-minV)/((maxV-minV)||1);
      var idx=Math.min(ramp.length-1, Math.floor(t*(ramp.length-1))); return ramp[idx]; }
    var cw=Math.max(48, Math.min(120, (box.clientWidth-180)/cols.length));
    var h='<div style="font-size:13px;font-weight:640;margin-bottom:6px">'+esc(aggLabel())+' heatmap</div>';
    h+='<div style="overflow:auto"><table class="an-ptbl" style="border:0"><thead><tr><th class="k"></th>';
    cols.forEach(function(c){ h+='<th>'+esc(p.singleCol?"":c)+'</th>'; });
    h+='</tr></thead><tbody>';
    rKeys.forEach(function(rk){ h+='<tr><td class="k">'+esc(rk)+'</td>';
      (p.singleCol?["__val"]:p.cKeys).forEach(function(ck){ var v=p.aggVal(p.cells[rk+"||"+ck]);
        var bg=color(v); var dark=v!=null&&(v-minV)/((maxV-minV)||1)>0.6;
        h+='<td style="background:'+bg+';color:'+(dark?"#fff":"var(--ink)")+';text-align:center;min-width:'+cw+'px" '+
          'data-tip="'+esc(rk+" · "+(p.singleCol?aggLabel():ck)+": "+fmtNum(v))+'">'+disp(v)+'</td>'; });
      h+='</tr>'; });
    h+='</tbody></table></div>';
    box.innerHTML=h; bindTips(box);
  }

  function renderChart(){
    var box=$("an-chart-box");
    $("an-scatter-ctl").classList.toggle("on", state.chart==="scatter");
    if(state.chart==="scatter"){ return renderScatter(); }
    if(state.chart==="correlation"){ return renderCorrelation(); }
    if(!PIVOT||!PIVOT.rKeys.length){ box.innerHTML='<div class="an-empty">No chart.</div>'; return; }
    if(state.chart==="heatmap"){ return renderHeatmap(); }
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
  $("an-pct").addEventListener("change",function(){ state.pct=$("an-pct").checked; renderTable(); renderChart(); });
  ["an-sx","an-sy","an-scolor"].forEach(function(id){ $(id).addEventListener("change",function(){
    state.sx=$("an-sx").value; state.sy=$("an-sy").value; state.scolor=$("an-scolor").value; renderChart(); }); });
  document.querySelectorAll(".an-btn.vw").forEach(function(b){
    b.addEventListener("click",function(){ applyView(b.getAttribute("data-view")); }); });
  $("an-cf-add").addEventListener("click", addComputedField);
  $("an-profile-toggle").addEventListener("click", toggleProfile);
  $("an-png").addEventListener("click", exportPNG);
  $("an-save-view").addEventListener("click", function(){
    var name=prompt("Save this view as:"); if(!name)return;
    var v=loadViews(); v[name]=snapshotState(); saveViews(v); loadViewsList();
    $("an-views-sel").value=name; });
  $("an-views-sel").addEventListener("change", function(){
    var v=loadViews(), n=$("an-views-sel").value; if(n&&v[n])restoreState(v[n]); });
  $("an-del-view").addEventListener("click", function(){
    var n=$("an-views-sel").value; if(!n)return; var v=loadViews(); delete v[n];
    saveViews(v); loadViewsList(); });
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
