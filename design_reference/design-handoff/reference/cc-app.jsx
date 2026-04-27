// SeekingChartis Command Center — main app (editorial)
const { useState, useEffect, useMemo, createContext, useContext } = React;
const { Sparkline, CovenantPill, StagePill, NumberMaybe } = window.SC;
const D = window.PORTFOLIO;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "showHero": true,
  "showWhat": true,
  "showKPI": true,
  "showCatalog": true,
  "showPipeline": true,
  "showDeals": true,
  "showCovenants": true,
  "showDrag": true,
  "showInitiatives": true,
  "showAlerts": true,
  "showDeliverables": true
}/*EDITMODE-END*/;

// ---------------- shared selected-deal context ----------------
const DealCtx = createContext(null);
function useDeal() { return useContext(DealCtx); }

function App() {
  const [tweaks, setTweaks] = window.useTweaks ? window.useTweaks(TWEAK_DEFAULTS) : [TWEAK_DEFAULTS, ()=>{}];
  const [view, setView] = useState("ANALYSIS");
  const [stage, setStage] = useState("Hold");
  const [selectedDealId, setSelectedDealId] = useState("ccf_2026");
  const selected = D.deals.find(d => d.id === selectedDealId) || D.deals[0];

  return (
    <DealCtx.Provider value={{selected, setSelectedDealId}}>
      <Topbar view={view} setView={setView} />
      <Crumbs/>
      <div className="page">
        {tweaks.showHero && <PageHead/>}
        {tweaks.showWhat && <WhatBlock/>}
        {tweaks.showKPI && <KPIStrip/>}
        {tweaks.showCatalog && <MetricCatalog/>}
        <SelectedDealBar/>
        {tweaks.showPipeline && <Pipeline stage={stage} setStage={setStage}/>}
        {tweaks.showDeals && <DealsTable stage={stage}/>}
        {tweaks.showCovenants && <CovenantSection/>}
        {tweaks.showDrag && <DragSection/>}
        {tweaks.showInitiatives && <InitiativeSection/>}
        {tweaks.showAlerts && <AlertSection/>}
        {tweaks.showDeliverables && <DelivSection/>}
        <Footer/>
      </div>
      {window.TweaksPanel && (
        <window.TweaksPanel title="Tweaks">
          <window.TweakSection title="Sections">
            <window.TweakToggle label="Page header" value={tweaks.showHero} onChange={v=>setTweaks({showHero:v})}/>
            <window.TweakToggle label="What this page does" value={tweaks.showWhat} onChange={v=>setTweaks({showWhat:v})}/>
            <window.TweakToggle label="KPI strip" value={tweaks.showKPI} onChange={v=>setTweaks({showKPI:v})}/>
            <window.TweakToggle label="Metric catalog" value={tweaks.showCatalog} onChange={v=>setTweaks({showCatalog:v})}/>
            <window.TweakToggle label="Pipeline funnel" value={tweaks.showPipeline} onChange={v=>setTweaks({showPipeline:v})}/>
            <window.TweakToggle label="Deals table" value={tweaks.showDeals} onChange={v=>setTweaks({showDeals:v})}/>
            <window.TweakToggle label="Covenant heatmap" value={tweaks.showCovenants} onChange={v=>setTweaks({showCovenants:v})}/>
            <window.TweakToggle label="EBITDA drag" value={tweaks.showDrag} onChange={v=>setTweaks({showDrag:v})}/>
            <window.TweakToggle label="Initiatives" value={tweaks.showInitiatives} onChange={v=>setTweaks({showInitiatives:v})}/>
            <window.TweakToggle label="Alerts" value={tweaks.showAlerts} onChange={v=>setTweaks({showAlerts:v})}/>
            <window.TweakToggle label="Deliverables" value={tweaks.showDeliverables} onChange={v=>setTweaks({showDeliverables:v})}/>
          </window.TweakSection>
        </window.TweaksPanel>
      )}
    </DealCtx.Provider>
  );
}

function Topbar({ view, setView }) {
  const tabs = ["DEALS","ANALYSIS","PORTFOLIO","MARKET","TOOLS"];
  return (
    <header className="topbar">
      <a href="SeekingChartis.html" className="brand" style={{textDecoration:"none", color:"inherit"}}>
        <div className="brand-mark">SC</div>
        <div className="brand-name">Seeking<em>Chartis</em></div>
      </a>
      <nav className="topnav">
        {tabs.map(t => (
          <button key={t} className={view===t?"active":""} onClick={()=>setView(t)}>
            {t} <span className="caret">▾</span>
          </button>
        ))}
      </nav>
      <div className="topbar-right">
        <div className="search">
          <span className="ico">⌕</span>
          <input placeholder="Search deals, modules…"/>
          <span className="kbd">⌘K</span>
        </div>
        <a href="login.html" className="signin" style={{textDecoration:"none"}}>SIGN OUT</a>
      </div>
    </header>
  );
}

function Crumbs() {
  return (
    <div className="crumbs">
      <a href="#">Home</a><span className="sep">›</span>
      <a href="#">Portfolio &amp; diligence</a><span className="sep">›</span>
      <span className="here">Command center</span>
    </div>
  );
}

function PageHead() {
  return (
    <div className="pg-head">
      <div>
        <div className="eyebrow">
          <span>PORTFOLIO &amp; DILIGENCE</span><span className="dot">·</span>
          <span>FUND&nbsp;II</span><span className="dot">·</span>
          <span className="slug">/COMMAND-CENTER</span>
        </div>
        <h1 className="title">Command center</h1>
        <p className="lede">Hold-period rollup, active diligence, and screening flow — one canvas.</p>
      </div>
      <div className="meta-col">
        <div>ID <span className="dot">·</span> <span className="v">CCF-FUND2</span></div>
        <div>KIND <span className="dot">·</span> <span className="v">ROLLUP</span></div>
        <div>STATUS <span className="dot">·</span> <span className="v" style={{color:"var(--green)"}}>LIVE</span></div>
        <div>AS&nbsp;OF <span className="dot">·</span> <span className="v">{D.asOf}</span></div>
      </div>
    </div>
  );
}

function WhatBlock() {
  return (
    <div className="info-grid">
      <div className="info-block">
        <div className="micro">WHAT THIS PAGE DOES</div>
        <p>Weighted MOIC &amp; IRR · pipeline funnel · covenant heatmap · EBITDA drag decomposition · initiative variance · cross-deal playbook signals. The complete hold-period view in one place.</p>
      </div>
      <div className="sources-block">
        <div className="micro">SOURCES</div>
        <ul>
          <li>portfolio.db</li>
          <li>10_diligence_run/summary.csv</li>
          <li>33_portfolio_dashboard.html</li>
          <li>simulations.csv</li>
          <li>HCRIS · APCD · CMS-MA</li>
        </ul>
      </div>
    </div>
  );
}

// ---------------- KPI strip — paired viz + dataset ----------------
function KPIStrip() {
  const [hover, setHover] = useState(null);
  const active = hover ? D.kpis.find(k => k.id === hover) : D.kpis[1]; // weighted MOIC default
  return (
    <div className="pair kpi-pair">
      <div className="viz">
        <div className="micro" style={{marginBottom: ".75rem"}}>FUND-LEVEL KPIs · 7-QUARTER TRACK</div>
        <div className="kpi-strip">
          {D.kpis.map(k => (
            <div key={k.id}
                 className={"kpi-cell " + (active && active.id === k.id ? "on" : "")}
                 onMouseEnter={()=>setHover(k.id)}
                 onMouseLeave={()=>setHover(null)}>
              <div className={"kv " + (k.tone || "")}>{k.value}</div>
              <div className="kl">{k.label}</div>
              <div className={"kd " + (k.dir || "")}>{k.delta}</div>
              <div className="spark"><Sparkline data={k.spark} color={
                k.tone === "green" ? "var(--green)" : k.tone === "amber" ? "var(--amber)" : k.tone === "red" ? "var(--red)" : "var(--teal)"
              }/></div>
            </div>
          ))}
        </div>
      </div>
      <div className="data">
        <div className="data-h">
          <span>{active ? active.label.toUpperCase() : "WEIGHTED MOIC"} · QUARTERLY</span>
          <span className="src">portfolio.db</span>
        </div>
        <table>
          <thead><tr><th>Quarter</th><th className="r">Value</th><th className="r">Δ q/q</th></tr></thead>
          <tbody>
            {(active ? active.spark : []).map((v, i, arr) => {
              const prev = i > 0 ? arr[i-1] : null;
              const delta = prev != null ? v - prev : null;
              const q = ["Q4'24","Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26"][i];
              const isLast = i === arr.length - 1;
              return (
                <tr key={i} className={isLast ? "hot" : ""}>
                  <td className="lbl">{q}</td>
                  <td className="r">{typeof v === "number" ? v.toFixed(active && active.id === "irr" ? 1 : 2) : v}</td>
                  <td className="r" style={{color: delta == null ? "var(--faint)" : delta > 0 ? "var(--green)" : delta < 0 ? "var(--red)" : "var(--muted)"}}>
                    {delta == null ? "—" : (delta > 0 ? "+" : "") + delta.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- Metric catalog (replaces generic disciplines) ----------------
function MetricCatalog() {
  const groups = [
    { ttl: "RETURNS", lvl: "fund", items: [
      { l: "Weighted MOIC", v: "2.69x", anchor: "kpi" },
      { l: "Weighted IRR",  v: "21.9%", anchor: "kpi" },
      { l: "DPI",           v: "0.42x", anchor: "kpi" },
      { l: "TVPI",          v: "2.69x", anchor: "kpi" },
    ]},
    { ttl: "RCM DRAG", lvl: "deal", items: [
      { l: "Denial write-off",     v: "$14.6M", anchor: "drag" },
      { l: "DAR carry cost",       v: "$1.4M",  anchor: "drag" },
      { l: "Underpayment leakage", v: "$1.7M",  anchor: "drag" },
      { l: "Recovery cost",        v: "$0.2M",  anchor: "drag" },
    ]},
    { ttl: "COVENANTS", lvl: "deal", items: [
      { l: "Net leverage",     v: "6.1x · WATCH",  anchor: "cov" },
      { l: "Interest coverage",v: "2.2x · WATCH",  anchor: "cov" },
      { l: "Days cash",        v: "84d · SAFE",    anchor: "cov" },
      { l: "EBITDA / Plan",    v: "87% · WATCH",   anchor: "cov" },
    ]},
    { ttl: "INITIATIVES", lvl: "deal", items: [
      { l: "Coding & CDI",       v: "−10.0%", anchor: "init" },
      { l: "Prior auth reform",  v: "+28.0%", anchor: "init" },
      { l: "Denials workflow",   v: "+6.4%",  anchor: "init" },
      { l: "Underpay recovery",  v: "−15.2%", anchor: "init" },
    ]},
  ];
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">METRIC CATALOG</div>
          <h2>Every number<br/>on this page</h2>
        </div>
        <p className="desc">Cross-reference of fund- and deal-level metrics with their visualization anchors below. Click any row to scroll its source.</p>
      </div>
      <div className="catalog">
        {groups.map(g => (
          <div key={g.ttl} className="cat-col">
            <div className="cat-h">
              <span className="ttl">{g.ttl}</span>
              <span className={"lvl " + g.lvl}>{g.lvl === "fund" ? "FUND" : "DEAL"}</span>
            </div>
            <table>
              <tbody>
                {g.items.map((it, i) => (
                  <tr key={i}><td className="lbl">{it.l}</td><td className="r v">{it.v}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------- Selected deal bar ----------------
function SelectedDealBar() {
  const { selected, setSelectedDealId } = useDeal();
  const heldDeals = D.deals.filter(d => d.stage === "Hold" || d.stage === "IOI" || d.stage === "Sourced");
  return (
    <div className="deal-bar">
      <div>
        <div className="lbl">FOCUSED DEAL</div>
        <div style={{display:"flex", alignItems:"baseline", gap:"1rem"}}>
          <span className="nm">{selected.name}</span>
          <span className="id">{selected.id}</span>
        </div>
      </div>
      <div>
        <div className="lbl">STAGE</div>
        <div className="v"><StagePill stage={selected.stage}/></div>
      </div>
      <div>
        <div className="lbl">ENTRY EV</div>
        <div className="v">{selected.ev ? "$" + selected.ev + "M" : "—"}</div>
      </div>
      <div>
        <div className="lbl">MOIC · IRR</div>
        <div className="v">
          {selected.moic ? selected.moic.toFixed(2) + "x" : "—"}
          <span style={{color:"var(--faint)", margin:"0 .5rem"}}>·</span>
          {selected.irr ? (selected.irr*100).toFixed(1) + "%" : "—"}
        </div>
      </div>
      <div className="switch">
        {heldDeals.map(d => (
          <button key={d.id} className={d.id === selected.id ? "active" : ""} onClick={()=>setSelectedDealId(d.id)}>
            {d.id.split("_")[0].toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------- Pipeline — paired with dataset ----------------
function Pipeline({ stage, setStage }) {
  const max = Math.max(...D.funnel.map(d => d.count));
  const conv = D.funnel.map((s, i, arr) => i === 0 ? null : (s.count / arr[i-1].count));
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">PIPELINE FLOW</div>
          <h2>Sourced through hold</h2>
        </div>
        <p className="desc">Click a stage to filter the deal table beneath. Bar widths are stage-relative; conversion is to-prior-stage.</p>
      </div>
      <div className="pair">
        <div className="viz">
          <div className="pipeline">
            {D.funnel.map(s => (
              <div key={s.stage} className={"stage " + (stage===s.stage?"active":"")} onClick={()=>setStage(s.stage)}>
                <div className="nm">{s.stage}</div>
                <div className="ct">{s.count}</div>
                <div className="ev">{s.ev}</div>
                <div className="bar"><i style={{width: (s.count/max)*100 + "%"}}/></div>
              </div>
            ))}
          </div>
        </div>
        <div className="data">
          <div className="data-h"><span>FUNNEL CONVERSION</span><span className="src">portfolio.db / funnel</span></div>
          <table>
            <thead><tr><th>Stage</th><th className="r">N</th><th className="r">EV</th><th className="r">→ prior</th></tr></thead>
            <tbody>
              {D.funnel.map((s, i) => (
                <tr key={s.stage} className={stage === s.stage ? "hot" : ""}>
                  <td className="lbl">{s.stage}</td>
                  <td className="r">{s.count}</td>
                  <td className="r">{s.ev}</td>
                  <td className="r" style={{color: conv[i] == null ? "var(--faint)" : conv[i] < 0.5 ? "var(--amber)" : "var(--green)"}}>
                    {conv[i] == null ? "—" : (conv[i]*100).toFixed(0) + "%"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DealsTable({ stage }) {
  const { selected, setSelectedDealId } = useDeal();
  const filtered = D.deals.filter(d => stage === "Hold" ? d.stage === "Hold" : stage === "IOI" ? d.stage === "IOI" : stage === "Sourced" ? d.stage === "Sourced" : true);
  return (
    <div className="tbl-wrap">
      <div className="tbl-h">
        <h3>Latest snapshot — {stage === "Hold" ? "Held deals" : stage}</h3>
        <span className="meta">{filtered.length} of {D.deals.length} · {D.asOf} · click row to focus</span>
      </div>
      <table className="t">
        <thead>
          <tr>
            <th>Deal</th><th>Stage</th><th style={{textAlign:"right"}}>Entry EV</th>
            <th style={{textAlign:"right"}}>MOIC</th><th style={{textAlign:"right"}}>IRR</th>
            <th>Covenant</th><th style={{textAlign:"right"}}>Drift</th>
            <th>Headline</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(d => (
            <tr key={d.id} onClick={()=>setSelectedDealId(d.id)}
                style={{cursor:"pointer", background: d.id === selected.id ? "var(--bg-tint)" : "transparent"}}>
              <td>
                <div className="deal-id">{d.id} {d.id === selected.id && <span style={{color:"var(--teal)"}}>●</span>}</div>
                <div className="deal-nm">{d.name}</div>
              </td>
              <td><StagePill stage={d.stage}/></td>
              <td className="num">{d.ev ? "$" + d.ev + "M" : "—"}</td>
              <td className="num"><NumberMaybe v={d.moic} format="moic" tone={d.moic && d.moic >= 2 ? "green" : null}/></td>
              <td className="num"><NumberMaybe v={d.irr} format="pct" tone={d.irr && d.irr >= 0.20 ? "green" : "amber"}/></td>
              <td><CovenantPill status={d.covenant}/></td>
              <td className="num"><NumberMaybe v={d.drift} format="drift" tone={d.drift === null ? null : d.drift < -15 ? "red" : d.drift < -5 ? "amber" : "green"}/></td>
              <td><span className="hl">{d.headline}</span></td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan="8" style={{textAlign:"center", padding:"2.5rem", color:"var(--muted)", fontStyle:"italic"}}>No deals at this stage.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ---------------- Covenants — paired with dataset ----------------
function CovenantSection() {
  const { selected } = useDeal();
  // count of safe/watch/trip per row
  const totals = D.covenants.rows.map(r => {
    const c = { safe: 0, watch: 0, trip: 0 };
    r.cells.forEach(([k]) => c[k]++);
    return c;
  });
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">COVENANT &amp; RATIO HEATMAP</div>
          <h2>Eight quarters,<br/>six covenants</h2>
        </div>
        <p className="desc">Trailing 8-quarter view for <span className="mono" style={{fontSize:".85em"}}>{selected.id}</span>. Bands are calibrated against trip thresholds; trend column shows movement Q-1 → Q.</p>
      </div>
      <div className="pair">
        <div className="viz">
          <div className="heat">
            <div className="heat-row h-head">
              <div></div>
              {D.covenants.quarters.map(q => <div key={q} className="heat-h">{q}</div>)}
              <div className="heat-h" style={{textAlign:"right"}}>Trend</div>
            </div>
            {D.covenants.rows.map((r, i) => (
              <div key={i} className="heat-row">
                <div className="heat-l">{r.name}<span className="sub">{r.sub}</span></div>
                {r.cells.map((c, j) => (
                  <div key={j} className={"heat-cell h-" + c[0]}>{c[1]}</div>
                ))}
                <div className={"heat-trend " + (r.trend.startsWith("−") || r.trend.startsWith("-") ? "down" : "up")}>{r.trend}</div>
              </div>
            ))}
            <div className="heat-foot">
              <span><i style={{background:"var(--green-soft)", borderColor:"var(--green)"}}></i>Safe</span>
              <span><i style={{background:"var(--amber-soft)", borderColor:"var(--amber)"}}></i>Watch — within 10% of trigger</span>
              <span><i style={{background:"var(--red-soft)", borderColor:"var(--red)"}}></i>Trip</span>
            </div>
          </div>
        </div>
        <div className="data">
          <div className="data-h"><span>QUARTER STATE COUNTS</span><span className="src">{selected.id}.covenants</span></div>
          <table>
            <thead><tr><th>Covenant</th><th className="r">Safe</th><th className="r">Watch</th><th className="r">Trip</th><th className="r">Trend</th></tr></thead>
            <tbody>
              {D.covenants.rows.map((r, i) => {
                const isStress = totals[i].watch >= 4 || totals[i].trip > 0;
                return (
                  <tr key={i} className={isStress ? "hot" : ""}>
                    <td className="lbl">{r.name}</td>
                    <td className="r" style={{color:"var(--green)"}}>{totals[i].safe}</td>
                    <td className="r" style={{color:"var(--amber)"}}>{totals[i].watch}</td>
                    <td className="r" style={{color:"var(--red)"}}>{totals[i].trip || "—"}</td>
                    <td className="r" style={{color: r.trend.startsWith("−") || r.trend.startsWith("-") ? "var(--red)" : "var(--green)"}}>{r.trend}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------------- EBITDA Drag — paired bar + table + recovery ----------------
function DragSection() {
  const { selected } = useDeal();
  const total = D.drag.items.reduce((s, x) => s + x.pct, 0);
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">EBITDA DRAG MODEL</div>
          <h2>Where the<br/>$24.4M is going</h2>
        </div>
        <p className="desc">Source-attributed lift on actual_rcm_ebitda_impact for <span className="mono" style={{fontSize:".85em"}}>{selected.id}</span> (per <span className="mono" style={{fontSize:".85em"}}>10_diligence_run/summary.csv</span>).</p>
      </div>
      <div className="pair">
        <div className="viz">
          <h3 style={{margin:"0 0 .25rem", fontFamily:"'Source Serif 4', serif", fontWeight: 400, fontSize:"1.2rem"}}>Drag decomposition</h3>
          <p className="sub" style={{color:"var(--muted)", fontSize:".82rem", margin:"0 0 1.25rem"}}>Median per-hospital impact across simulations</p>
          <div className="drag-bar">
            {D.drag.items.map((it, i) => (
              <i key={i} style={{width: it.pct + "%", background: it.color}} title={`${it.label} ${it.pct}%`}/>
            ))}
          </div>
          <div className="drag-rows">
            {D.drag.items.map((it, i) => (
              <div key={i} className="r">
                <span className="swatch" style={{background: it.color}}/>
                <span className="lbl">{it.label}</span>
                <span className="pct">{it.pct.toFixed(1)}%</span>
                <span className="vl">{it.val}</span>
              </div>
            ))}
          </div>
          <div style={{marginTop:"1.5rem", paddingTop:"1rem", borderTop:"1px solid var(--border)"}}>
            <h3 style={{margin:"0 0 .25rem", fontFamily:"'Source Serif 4', serif", fontWeight: 400, fontSize:"1.05rem"}}>Recovery trajectory</h3>
            <p className="sub" style={{color:"var(--muted)", fontSize:".78rem", margin:"0 0 .5rem"}}>Modeled actual vs benchmark RCM EBITDA impact, 8 quarters</p>
            <div style={{height: 70}}>
              <Sparkline data={[24.3,24.0,23.6,23.1,22.5,22.0,21.4,20.8]} color="var(--teal)"/>
            </div>
            <div className="recovery-stats" style={{marginTop:".5rem"}}>
              <div className="rstat accent"><div className="l">Current actual</div><div className="v">$20.8M</div></div>
              <div className="rstat green"><div className="l">Benchmark</div><div className="v">$6.8M</div></div>
            </div>
          </div>
        </div>
        <div className="data">
          <div className="data-h"><span>DRAG DECOMPOSITION · RAW</span><span className="src">summary.csv</span></div>
          <table>
            <thead><tr><th>Component</th><th className="r">% of total</th><th className="r">$ impact</th></tr></thead>
            <tbody>
              {D.drag.items.map((it, i) => (
                <tr key={i} className={it.pct > 50 ? "hot" : ""}>
                  <td className="lbl">
                    <span style={{display:"inline-block", width:8, height:8, background: it.color, marginRight:".5rem", verticalAlign:"middle"}}/>
                    {it.label}
                  </td>
                  <td className="r">{it.pct.toFixed(1)}%</td>
                  <td className="r" style={{fontWeight: 600}}>{it.val}</td>
                </tr>
              ))}
              <tr style={{borderTop: "2px solid var(--ink)"}}>
                <td className="lbl" style={{fontWeight: 700, color:"var(--ink)"}}>Σ Total</td>
                <td className="r" style={{fontWeight: 700}}>{total.toFixed(1)}%</td>
                <td className="r" style={{fontWeight: 700}}>$20.1M</td>
              </tr>
            </tbody>
          </table>
          <div className="data-h" style={{borderTop: "1px solid var(--border)"}}><span>RECOVERY · QUARTERLY</span><span className="src">simulations.csv</span></div>
          <table>
            <thead><tr><th>Q</th><th className="r">Actual</th><th className="r">vs Q-1</th></tr></thead>
            <tbody>
              {[24.3,24.0,23.6,23.1,22.5,22.0,21.4,20.8].map((v, i, a) => {
                const d = i > 0 ? v - a[i-1] : null;
                const q = D.covenants.quarters[i];
                return (
                  <tr key={i} className={i === a.length - 1 ? "hot" : ""}>
                    <td className="lbl">{q}</td>
                    <td className="r">${v.toFixed(1)}M</td>
                    <td className="r" style={{color: d == null ? "var(--faint)" : d < 0 ? "var(--green)" : "var(--red)"}}>
                      {d == null ? "—" : (d > 0 ? "+" : "") + d.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <div className="recovery-note" style={{marginTop:"1rem", background:"var(--paper-pure)", border:"1px solid var(--rule)", padding:"1rem 1.5rem"}}>
        Closing the gap by ~50% over 4 quarters drives <b>+$7.0M EBITDA</b> at hold — base case.
      </div>
    </div>
  );
}

// ---------------- Initiatives — paired chart + table ----------------
function InitiativeSection() {
  const { selected } = useDeal();
  const items = D.initiatives.filter(it => it.deal === selected.id);
  const display = items.length > 0 ? items : D.initiatives;
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">INITIATIVE TRACKER</div>
          <h2>Forty-seven<br/>levers, by variance</h2>
        </div>
        <p className="desc">Sorted by absolute variance to plan for <span className="mono" style={{fontSize:".85em"}}>{selected.id}</span>. When the same initiative repeats across deals with the same sign, it's a playbook gap — not a deal-specific issue.</p>
      </div>
      <div className="pair">
        <div className="viz">
          <div className="init">
            <div className="init-row head">
              <div></div>
              <div className="head-l">Initiative</div>
              <div className="head-l">Deal</div>
              <div className="head-l r">Actual</div>
              <div className="head-l r">Variance</div>
              <div className="head-l r">Progress</div>
            </div>
            {display.map((it, i) => (
              <div key={i} className="init-row">
                <div className={"ico-wrap " + it.tone}>{it.tone === "g" ? "✓" : it.tone === "a" ? "!" : "✕"}</div>
                <div className="nm">{it.name}</div>
                <div className="deal">{it.deal}</div>
                <div className="num">{it.actual}</div>
                <div className="num" style={{color: Math.abs(it.variance) > 15 ? "var(--red)" : Math.abs(it.variance) > 5 ? "var(--amber)" : "var(--green)", fontWeight: 600}}>
                  {it.variance > 0 ? "+" : ""}{it.variance.toFixed(1)}%
                </div>
                <div className="progress-line">
                  <div className="bar"><i className={it.tone} style={{width: it.progress + "%"}}/></div>
                  <span className="pct">{it.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="data">
          <div className="data-h"><span>VARIANCE DISTRIBUTION</span><span className="src">initiatives.csv</span></div>
          <div style={{padding:"1.25rem"}}>
            <VarianceDot data={display}/>
          </div>
          <div className="data-h" style={{borderTop:"1px solid var(--border)"}}><span>PLAYBOOK SIGNALS</span><span className="src">cross-deal</span></div>
          <table>
            <tbody>
              <tr><td className="lbl">Lagging (variance &gt; ±15%)</td><td className="r" style={{color:"var(--red)"}}>{display.filter(it => Math.abs(it.variance) > 15).length}</td></tr>
              <tr><td className="lbl">On-watch (5–15%)</td><td className="r" style={{color:"var(--amber)"}}>{display.filter(it => Math.abs(it.variance) > 5 && Math.abs(it.variance) <= 15).length}</td></tr>
              <tr><td className="lbl">On-plan (&lt; 5%)</td><td className="r" style={{color:"var(--green)"}}>{display.filter(it => Math.abs(it.variance) <= 5).length}</td></tr>
              <tr className="hot"><td className="lbl" style={{fontWeight: 700}}>Avg progress</td><td className="r" style={{fontWeight: 700}}>{Math.round(display.reduce((s,x)=>s+x.progress,0)/display.length)}%</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// dot plot for variance
function VarianceDot({ data }) {
  const w = 100, h = 60;
  const min = -30, max = 30;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{width:"100%", height:60, display:"block"}}>
      {/* axis */}
      <line x1="0" y1={h/2} x2={w} y2={h/2} stroke="var(--border)" strokeWidth=".5"/>
      {/* zero line */}
      <line x1={w/2} y1="6" x2={w/2} y2={h-6} stroke="var(--ink)" strokeWidth=".4"/>
      {/* ±5%, ±15% gridlines */}
      {[-15,-5,5,15].map(t => {
        const x = ((t - min) / (max - min)) * w;
        return <line key={t} x1={x} y1="10" x2={x} y2={h-10} stroke="var(--border)" strokeWidth=".3" strokeDasharray="1 1"/>;
      })}
      {/* dots */}
      {data.map((it, i) => {
        const x = ((it.variance - min) / (max - min)) * w;
        const c = Math.abs(it.variance) > 15 ? "var(--red)" : Math.abs(it.variance) > 5 ? "var(--amber)" : "var(--green)";
        return <circle key={i} cx={x} cy={h/2} r="2" fill={c} fillOpacity="0.7" stroke={c} strokeWidth=".5"/>;
      })}
      {/* labels */}
      <text x="0" y={h-1} fontFamily="JetBrains Mono" fontSize="3.5" fill="var(--faint)">−30%</text>
      <text x={w/2} y={h-1} textAnchor="middle" fontFamily="JetBrains Mono" fontSize="3.5" fill="var(--faint)">0</text>
      <text x={w} y={h-1} textAnchor="end" fontFamily="JetBrains Mono" fontSize="3.5" fill="var(--faint)">+30%</text>
    </svg>
  );
}

// ---------------- Alerts — paired with summary ----------------
function AlertSection() {
  const counts = { red: D.alerts.filter(a => a.tone === "red").length, amber: D.alerts.filter(a => a.tone === "amber").length, blue: D.alerts.filter(a => a.tone === "blue").length };
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">WATCH &amp; ESCALATE</div>
          <h2>What needs<br/>your attention</h2>
        </div>
        <p className="desc">Triggered by variance, freshness, and playbook-recurrence rules. Each carries a one-click drilldown into the underlying source.</p>
      </div>
      <div className="pair">
        <div className="viz">
          {D.alerts.map((a, i) => (
            <div key={i} className={"alert " + a.tone}>
              <div className="ico">{a.tone === "amber" ? "▲" : a.tone === "red" ? "✕" : "ℹ"}</div>
              <div className="body">
                <div className="ttl">{a.title}</div>
                <p>{a.desc}</p>
              </div>
              <span className="cta">{a.cta}</span>
            </div>
          ))}
        </div>
        <div className="data">
          <div className="data-h"><span>ALERT TRIAGE · LAST 7d</span><span className="src">alerts.json</span></div>
          <table>
            <tbody>
              <tr><td className="lbl"><span style={{color:"var(--red)"}}>● </span>Critical</td><td className="r" style={{fontWeight: 600}}>{counts.red}</td></tr>
              <tr className={counts.amber > 0 ? "hot" : ""}><td className="lbl"><span style={{color:"var(--amber)"}}>● </span>Warning</td><td className="r" style={{fontWeight: 600}}>{counts.amber}</td></tr>
              <tr><td className="lbl"><span style={{color:"var(--blue, var(--accent))"}}>● </span>Info</td><td className="r" style={{fontWeight: 600}}>{counts.blue}</td></tr>
            </tbody>
          </table>
          <div className="data-h" style={{borderTop:"1px solid var(--border)"}}><span>RULES FIRED</span><span className="src">rules.py</span></div>
          <table>
            <tbody>
              <tr><td className="lbl">variance.cumulative_drift &gt; 25%</td><td className="r">1</td></tr>
              <tr><td className="lbl">freshness.hcris_pending</td><td className="r">1</td></tr>
              <tr className="hot"><td className="lbl">playbook.recurrence ≥ 2</td><td className="r">1</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DelivSection() {
  const cls = { HTML: "", CSV: "csv", JSON: "json", XLS: "xls" };
  const counts = D.deliverables.reduce((acc, d) => { acc[d.kind] = (acc[d.kind] || 0) + 1; return acc; }, {});
  return (
    <div>
      <div className="sect">
        <div>
          <div className="micro">DELIVERABLES</div>
          <h2>Partner-facing<br/>artifacts</h2>
        </div>
        <p className="desc">Drop-in compatible with the existing <span className="mono" style={{fontSize:".85em"}}>output v1/</span> structure. Filenames and provenance are unchanged.</p>
      </div>
      <div className="pair">
        <div className="viz" style={{padding: 0}}>
          <div className="deliv-grid" style={{border:"none"}}>
            {D.deliverables.map((f, i) => (
              <div key={i} className="deliv">
                <span className={"kind " + (cls[f.kind] || "")}>{f.kind}</span>
                <div className="nm">{f.name}</div>
                <div className="meta"><span>{f.size}</span><span>{D.asOf}</span></div>
              </div>
            ))}
          </div>
        </div>
        <div className="data">
          <div className="data-h"><span>OUTPUT MANIFEST</span><span className="src">output v1/</span></div>
          <table>
            <tbody>
              {Object.entries(counts).map(([k, v]) => (
                <tr key={k}><td className="lbl">{k}</td><td className="r" style={{fontWeight: 600}}>{v}</td></tr>
              ))}
              <tr className="hot"><td className="lbl" style={{fontWeight: 700}}>Σ Total files</td><td className="r" style={{fontWeight: 700}}>{D.deliverables.length}</td></tr>
            </tbody>
          </table>
          <div className="data-h" style={{borderTop:"1px solid var(--border)"}}><span>TOTAL SIZE</span><span className="src">disk</span></div>
          <table>
            <tbody>
              <tr><td className="lbl">Compressed</td><td className="r">141 KB</td></tr>
              <tr><td className="lbl">Uncompressed</td><td className="r">412 KB</td></tr>
              <tr><td className="lbl">Generated</td><td className="r">{D.asOf}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer>
      <span>Seeking<em>Chartis</em> v1.0.0 — Healthcare diligence, instrument-grade</span>
      <span className="mono" style={{fontSize:".75rem"}}>HCRIS · APCD · CMS-MA · simulations.csv · portfolio.db</span>
    </footer>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
