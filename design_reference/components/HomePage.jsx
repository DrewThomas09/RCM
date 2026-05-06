// SeekingChartis — Signed-in Home dashboard (Variation B)
// Editorial chrome + Bloomberg-dense panels, reskinned in navy/teal/parchment.

/* global React */

// AppNav is replaced by <GlobalNav/> (components/GlobalNav.jsx). Kept as a no-op for compat.
function AppNav() { return null; }

function HomeHero() {
  return (
    <section style={{ background: "var(--sc-parchment)", padding: "48px 0 40px", borderBottom: "1px solid var(--sc-rule)" }}>
      <div className="sc-container-wide" style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 56, alignItems: "flex-end" }}>
        <div>
          <div className="sc-eyebrow" style={{ marginBottom: 18 }}>Partner landing · Tuesday, April 19</div>
          <h1 className="sc-h1" style={{ marginBottom: 14 }}>
            Good morning, Andrew.
          </h1>
          <p className="sc-lead">
            3 deals moved stage overnight. 2 critical alerts fired on Magnolia.
            The corpus added 11 benchmarkable entries since Friday.
          </p>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16,
          fontFamily: "var(--sc-mono)",
        }}>
          {[
            { v: "24", l: "active deals" },
            { v: "7", l: "unacked alerts", hot: true },
            { v: "6,024", l: "corpus hospitals" },
            { v: "278", l: "PE modules" },
          ].map(kpi => (
            <div key={kpi.l} style={{
              background: "#fff", border: "1px solid var(--sc-rule)",
              borderLeft: `3px solid ${kpi.hot ? "var(--sc-warning)" : "var(--sc-teal)"}`,
              padding: "14px 16px",
            }}>
              <div style={{ fontSize: 28, fontWeight: 600, color: "var(--sc-navy)", lineHeight: 1.1, fontFamily: "var(--sc-serif)" }}>{kpi.v}</div>
              <div style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--sc-text-faint)", marginTop: 4 }}>{kpi.l}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PipelineFunnel() {
  const stages = [
    { k: "Sourcing", n: 42, pct: 38.2 },
    { k: "Screened", n: 28, pct: 25.5 },
    { k: "IOI", n: 14, pct: 12.7 },
    { k: "LOI", n: 9, pct: 8.2 },
    { k: "Diligence", n: 11, pct: 10.0 },
    { k: "IC", n: 4, pct: 3.6 },
    { k: "Closed", n: 2, pct: 1.8 },
  ];
  return (
    <DataPanel code="FNL" title="Pipeline Funnel">
      {stages.map(s => (
        <BarRow key={s.k} label={s.k} value={s.n} pct={s.pct} color="var(--sc-teal)" />
      ))}
    </DataPanel>
  );
}

function ActiveAlerts() {
  const alerts = [
    { sev: "critical", kind: "covenant_breach", msg: "Magnolia: leverage ratio 7.4x exceeds 6.75x covenant", deal: "mag-2024", fired: "08:14" },
    { sev: "critical", kind: "payer_concentration", msg: "Cedar: UHC share rose to 38% (threshold 35%)", deal: "cedar-2023", fired: "07:32" },
    { sev: "high", kind: "denial_spike", msg: "Redwood: denial rate +220 bps MoM in behavioral", deal: "red-2024", fired: "Mon" },
    { sev: "high", kind: "ar_days", msg: "Linden: AR days at 61.4 (cohort median 48)", deal: "lin-2025", fired: "Mon" },
    { sev: "medium", kind: "data_stale", msg: "Sage: no HCRIS refresh in 94 days", deal: "sage-2023", fired: "Fri" },
  ];
  const sevColor = {
    critical: "var(--sc-critical)", high: "var(--sc-negative)",
    medium: "var(--sc-warning)", low: "var(--sc-text-dim)",
  };
  return (
    <DataPanel code="ALR" title="Active Alerts · 7 unacked">
      {alerts.map((a, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "auto 1fr auto",
          gap: 12, alignItems: "start",
          padding: "8px 0",
          borderBottom: i < alerts.length - 1 ? "1px solid var(--sc-rule)" : "none",
        }}>
          <span style={{
            fontFamily: "var(--sc-mono)", fontSize: 9, fontWeight: 700,
            letterSpacing: "0.12em", textTransform: "uppercase",
            color: sevColor[a.sev], width: 64, marginTop: 2,
          }}>{a.sev}</span>
          <div>
            <div style={{ fontSize: 13, color: "var(--sc-text)", marginBottom: 3 }}>{a.msg}</div>
            <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-text-faint)", letterSpacing: "0.05em" }}>
              {a.kind} · {a.deal}
            </div>
          </div>
          <span style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-text-faint)" }}>{a.fired}</span>
        </div>
      ))}
      <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--sc-rule)" }}>
        <a href="#" className="sc-btn-ghost" style={{ fontSize: 11 }}>All alerts →</a>
      </div>
    </DataPanel>
  );
}

function PortfolioHealth() {
  const bands = [
    { l: "Healthy (≥70)", n: 14, pct: 58.3, c: "var(--sc-positive)" },
    { l: "Watchlist (40-69)", n: 7, pct: 29.2, c: "var(--sc-warning)" },
    { l: "At risk (<40)", n: 3, pct: 12.5, c: "var(--sc-negative)" },
  ];
  return (
    <DataPanel code="HLT" title="Portfolio Health">
      {/* Segmented bar */}
      <div style={{
        display: "flex", height: 28, marginBottom: 16, border: "1px solid var(--sc-rule)",
      }}>
        {bands.map(b => (
          <div key={b.l} style={{
            background: b.c, width: `${b.pct}%`,
            display: "grid", placeItems: "center",
            color: "#fff", fontFamily: "var(--sc-mono)", fontSize: 10, fontWeight: 700,
          }}>{b.n}</div>
        ))}
      </div>
      {bands.map(b => (
        <div key={b.l} style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "6px 0", fontFamily: "var(--sc-mono)", fontSize: 12,
          borderBottom: "1px solid var(--sc-rule)",
        }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 8, height: 8, background: b.c }}/>
            <span style={{ color: "var(--sc-text-dim)" }}>{b.l}</span>
          </span>
          <span>
            <span style={{ color: "var(--sc-text)", fontWeight: 600 }}>{b.n}</span>
            <span style={{ color: "var(--sc-text-faint)", marginLeft: 8 }}>{b.pct.toFixed(1)}%</span>
          </span>
        </div>
      ))}
      <div style={{ marginTop: 14, fontSize: 12, color: "var(--sc-text-dim)", fontStyle: "italic", lineHeight: 1.5 }}>
        Watchlist up 2 deals WoW — Redwood dropped 11 pts after denial spike.
      </div>
    </DataPanel>
  );
}

function RecentDeals({ onOpenAnalysis }) {
  const deals = [
    { name: "Magnolia Health Partners", stage: "Hold", score: 73, trend: "-4", hot: true },
    { name: "Cedar Capital — cardiology roll-up", stage: "Diligence", score: 81, trend: "+2", open: true },
    { name: "Redwood Behavioral Network", stage: "IC", score: 62, trend: "-11", hot: true },
    { name: "Sage Home Health", stage: "Hold", score: 68, trend: "+1" },
    { name: "Linden Pediatrics Platform", stage: "LOI", score: "—", trend: "—" },
    { name: "Juniper Imaging Partners", stage: "Screened", score: "—", trend: "—" },
  ];
  return (
    <DataPanel code="DLS" title="Recent Deals">
      <div style={{
        display: "grid", gridTemplateColumns: "1fr auto 60px 50px",
        fontFamily: "var(--sc-mono)", fontSize: 9, letterSpacing: "0.12em",
        textTransform: "uppercase", color: "var(--sc-text-faint)",
        padding: "4px 0 6px", borderBottom: "1px solid var(--sc-navy)",
      }}>
        <span>Deal</span><span>Stage</span><span style={{ textAlign: "right" }}>Health</span><span style={{ textAlign: "right" }}>Δ</span>
      </div>
      {deals.map((d, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "1fr auto 60px 50px",
          gap: 10, alignItems: "center", padding: "7px 0",
          borderBottom: i < deals.length - 1 ? "1px solid var(--sc-rule)" : "none",
          fontSize: 13,
        }}>
          <a
            href="#"
            onClick={(e) => { e.preventDefault(); onOpenAnalysis && onOpenAnalysis(); }}
            style={{ color: "var(--sc-teal-ink)", fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}
          >
            {d.hot && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--sc-warning)", flexShrink: 0 }}/>}
            {d.name}
          </a>
          <span style={{ fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sc-text-dim)" }}>{d.stage}</span>
          <span style={{ fontFamily: "var(--sc-mono)", textAlign: "right", fontWeight: 600, color: typeof d.score === "number" && d.score < 65 ? "var(--sc-warning)" : "var(--sc-text)" }}>{d.score}</span>
          <span style={{ fontFamily: "var(--sc-mono)", textAlign: "right", color: d.trend.startsWith("-") ? "var(--sc-negative)" : d.trend === "—" ? "var(--sc-text-faint)" : "var(--sc-positive)" }}>{d.trend}</span>
        </div>
      ))}
    </DataPanel>
  );
}

function Deadlines() {
  const dues = [
    { due: "Today", title: "IC packet — Cedar cardiology", owner: "KM", overdue: false },
    { due: "Apr 20", title: "Redwood partner review draft", owner: "DO", overdue: false },
    { due: "Apr 22", title: "Magnolia covenant restructure memo", owner: "KM", overdue: false },
    { due: "Apr 17", title: "Sage quarterly LP digest", owner: "AR", overdue: true },
    { due: "Apr 23", title: "Linden 5-step intake review", owner: "MC", overdue: false },
  ];
  return (
    <DataPanel code="DDL" title="Upcoming Deadlines · 7 days">
      {dues.map((d, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "80px 1fr auto",
          gap: 12, alignItems: "baseline", padding: "7px 0",
          borderBottom: i < dues.length - 1 ? "1px solid var(--sc-rule)" : "none",
          fontSize: 13,
        }}>
          <span style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, fontWeight: 700,
            letterSpacing: "0.08em", textTransform: "uppercase",
            color: d.overdue ? "var(--sc-negative)" : "var(--sc-warning)",
          }}>{d.due}{d.overdue && " · OVERDUE"}</span>
          <a href="#" style={{ color: "var(--sc-text)" }}>{d.title}</a>
          <span style={{
            width: 26, height: 26, borderRadius: "50%",
            background: "var(--sc-navy)", color: "var(--sc-on-navy)",
            display: "grid", placeItems: "center",
            fontFamily: "var(--sc-mono)", fontSize: 9, fontWeight: 700,
          }}>{d.owner}</span>
        </div>
      ))}
    </DataPanel>
  );
}

function PEVerdicts() {
  const rows = [
    { deal: "Redwood Behavioral", rec: "PASS", crit: 3, head: "Payer concentration + unit-economic inversion; 2022 vintage cohort underwater at 68% base rate." },
    { deal: "Cedar cardiology", rec: "PROCEED_WITH_CAVEATS", crit: 1, head: "Model thesis holds; flag physician comp plan dilution risk post-close." },
    { deal: "Magnolia Health", rec: "PROCEED", crit: 0, head: "Covenant headroom narrow but recoverable. RCM playbook on track." },
  ];
  const recColor = {
    STRONG_PROCEED: "var(--sc-positive)",
    PROCEED: "var(--sc-text)",
    PROCEED_WITH_CAVEATS: "var(--sc-warning)",
    PASS: "var(--sc-negative)",
  };
  return (
    <DataPanel code="PRV" title="Partner-Review Verdicts · top 3">
      {rows.map((r, i) => (
        <div key={i} style={{
          padding: "10px 0",
          borderBottom: i < rows.length - 1 ? "1px solid var(--sc-rule)" : "none",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <a href="#" style={{ color: "var(--sc-teal-ink)", fontSize: 14, fontWeight: 600 }}>{r.deal}</a>
            <span style={{
              fontFamily: "var(--sc-mono)", fontSize: 10, fontWeight: 700,
              letterSpacing: "0.12em", color: recColor[r.rec],
              padding: "3px 8px", border: `1px solid ${recColor[r.rec]}`,
            }}>{r.rec.replace(/_/g, " ")}</span>
          </div>
          {r.crit > 0 && (
            <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-negative)", marginBottom: 4, letterSpacing: "0.05em" }}>
              {r.crit} critical flag{r.crit > 1 ? "s" : ""}
            </div>
          )}
          <div style={{ fontSize: 12, color: "var(--sc-text-dim)", lineHeight: 1.5 }}>{r.head}</div>
        </div>
      ))}
    </DataPanel>
  );
}

function CorpusInsights() {
  const recent = [
    { y: 2024, name: "HighPoint Surgery Centers" },
    { y: 2024, name: "Mariner Home Health Platform" },
    { y: 2023, name: "Evergreen Behavioral Network" },
    { y: 2023, name: "Bluff City Cardiology" },
    { y: 2022, name: "Westridge Imaging Group" },
  ];
  const vintages = [
    { y: 2016, moic: "3.24x", n: 18 },
    { y: 2017, moic: "2.91x", n: 22 },
    { y: 2015, moic: "2.74x", n: 14 },
    { y: 2018, moic: "2.42x", n: 26 },
    { y: 2019, moic: "2.08x", n: 31 },
  ];
  return (
    <DataPanel code="CPS" title="Corpus Insights">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div>
          <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em", color: "var(--sc-text-faint)", marginBottom: 10 }}>RECENT ENTRIES</div>
          {recent.map((d, i) => (
            <div key={i} style={{ display: "flex", gap: 12, padding: "4px 0", fontSize: 13, borderBottom: "1px solid var(--sc-rule)" }}>
              <span style={{ fontFamily: "var(--sc-mono)", color: "var(--sc-text-faint)", width: 40 }}>{d.y}</span>
              <span style={{ color: "var(--sc-text)" }}>{d.name}</span>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em", color: "var(--sc-text-faint)", marginBottom: 10 }}>TOP VINTAGES · MEAN MOIC</div>
          {vintages.map((v, i) => (
            <div key={i} style={{ display: "flex", gap: 12, padding: "4px 0", fontSize: 13, borderBottom: "1px solid var(--sc-rule)", alignItems: "center" }}>
              <span style={{ fontFamily: "var(--sc-mono)", color: "var(--sc-text-faint)", width: 40 }}>{v.y}</span>
              <span style={{ fontFamily: "var(--sc-mono)", fontWeight: 600, flex: 1 }}>{v.moic}</span>
              <span style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-text-faint)" }}>n={v.n}</span>
            </div>
          ))}
        </div>
      </div>
    </DataPanel>
  );
}

function PlatformPagesIndex({ onOpenAnalysis, onOpenModule }) {
  // Pull real modules from the catalog, grouped by group code.
  const catalog = window.MODULES_CATALOG || [];
  const groupMeta = {
    LFC: "Deal lifecycle", PRT: "Portfolio ops", ANL: "Analytics & models",
    MKT: "Market intelligence", TLS: "Tools & admin",
  };
  const byGroup = {};
  for (const m of catalog) {
    if (!byGroup[m.group]) byGroup[m.group] = [];
    byGroup[m.group].push(m);
  }
  const groups = Object.keys(groupMeta).map(code => ({
    title: groupMeta[code], code, items: byGroup[code] || [],
  }));
  return (
    <section style={{ background: "#ffffff", borderTop: "1px solid var(--sc-rule)", padding: "56px 0 64px" }}>
      <div className="sc-container-wide">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 28 }}>
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 10 }}>Platform index · 74 UI pages · 52 endpoints</div>
            <h2 className="sc-h2" style={{ fontSize: 28 }}>Every surface in RCM-MC, one jump away.</h2>
          </div>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 11,
            color: "var(--sc-text-faint)", letterSpacing: "0.12em", textTransform: "uppercase",
          }}>
            rcm_mc · v0.6.0
          </div>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: 16,
        }}>
          {groups.map(g => (
            <div key={g.code} style={{ border: "1px solid var(--sc-rule)" }}>
              <header style={{
                background: "var(--sc-navy)", color: "var(--sc-on-navy)",
                padding: "8px 12px",
                fontFamily: "var(--sc-mono)", fontSize: 10,
                letterSpacing: "0.14em", textTransform: "uppercase",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ color: "var(--sc-teal-2)", fontWeight: 700 }}>{g.code}</span>
                <span>{g.title}</span>
              </header>
              <div style={{ padding: "4px 0" }}>
                {g.items.map((it, i) => (
                  <a key={i}
                     href="#"
                     onClick={(e) => {
                       e.preventDefault();
                       if (it.open === "analysis" && onOpenAnalysis) { onOpenAnalysis(); return; }
                       if (onOpenModule) onOpenModule(it.id);
                     }}
                     style={{
                       display: "block", padding: "8px 12px",
                       borderBottom: i < g.items.length - 1 ? "1px solid var(--sc-rule)" : "none",
                       textDecoration: "none",
                     }}
                     onMouseEnter={(e) => e.currentTarget.style.background = "var(--sc-bone)"}
                     onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <div style={{
                      fontSize: 13, fontWeight: 600, color: "var(--sc-navy)",
                      marginBottom: 3,
                    }}>{it.title}</div>
                    <div style={{
                      fontFamily: "var(--sc-mono)", fontSize: 9,
                      color: "var(--sc-text-faint)", letterSpacing: "0.04em",
                      marginBottom: 4,
                    }}>{it.route}</div>
                    <div style={{ fontSize: 11, color: "var(--sc-text-dim)", lineHeight: 1.4 }}>{it.tagline}</div>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ------- Curated 6-card hero row -------
function QuickAccessRow({ onOpenModule, onOpenAnalysis, onOpenDirectory }) {
  const cards = [
    { id: "analysis",           label: "Deal workbench",    kicker: "LFC · Analyze",    copy: "Bloomberg-dense console for the active deal." },
    { id: "heatmap",            label: "Portfolio heatmap", kicker: "PRT · Monitor",    copy: "Health scores across every hold in one grid." },
    { id: "ic-packet",          label: "IC packet",         kicker: "LFC · Decide",     copy: "One-click investment committee narrative." },
    { id: "ebitda",             label: "EBITDA bridge",     kicker: "ANL · Model",      copy: "Value creation waterfall with sensitivity." },
    { id: "payer-intel",        label: "Payer intelligence",kicker: "MKT · Research",   copy: "Concentration, mix shift, and reimbursement." },
    { id: "command",            label: "Command center",    kicker: "TLS · Operate",    copy: "Global alerts, jobs, and system status." },
  ];
  return (
    <section style={{ background: "#fff", borderTop: "1px solid var(--sc-rule)", borderBottom: "1px solid var(--sc-rule)", padding: "36px 0 40px" }}>
      <div className="sc-container-wide">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 20, gap: 12, flexWrap: "wrap" }}>
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 8 }}>Quick access · the six surfaces you open most</div>
            <h2 className="sc-h2" style={{ fontSize: 22, margin: 0 }}>Jump back into work.</h2>
          </div>
          <a href="#directory"
             onClick={(e) => { e.preventDefault(); onOpenDirectory && onOpenDirectory(); }}
             style={{
               fontFamily: "var(--sc-mono)", fontSize: 10.5, fontWeight: 600,
               letterSpacing: "0.14em", textTransform: "uppercase",
               color: "var(--sc-teal-ink)", textDecoration: "none",
             }}>
            All 79 surfaces →
          </a>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: 14,
        }}>
          {cards.map((c) => (
            <a key={c.id}
               href="#"
               onClick={(e) => {
                 e.preventDefault();
                 if (c.id === "analysis" && onOpenAnalysis) { onOpenAnalysis(); return; }
                 onOpenModule && onOpenModule(c.id);
               }}
               style={{
                 display: "block", padding: "18px 18px 16px",
                 border: "1px solid var(--sc-rule)", background: "var(--sc-parchment)",
                 textDecoration: "none", transition: "background 120ms, border-color 120ms",
                 position: "relative",
               }}
               onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--sc-teal)"; e.currentTarget.style.background = "#fff"; }}
               onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--sc-rule)"; e.currentTarget.style.background = "var(--sc-parchment)"; }}
            >
              <div style={{
                fontFamily: "var(--sc-mono)", fontSize: 10,
                letterSpacing: "0.14em", textTransform: "uppercase",
                color: "var(--sc-teal-ink)", marginBottom: 10,
              }}>{c.kicker}</div>
              <div style={{
                fontFamily: "var(--sc-serif)", fontSize: 20, fontWeight: 500,
                color: "var(--sc-navy)", lineHeight: 1.2, marginBottom: 8,
              }}>{c.label}</div>
              <div style={{ fontSize: 12.5, color: "var(--sc-text-dim)", lineHeight: 1.5 }}>{c.copy}</div>
              <div style={{
                position: "absolute", right: 14, bottom: 12,
                fontFamily: "var(--sc-mono)", fontSize: 14, color: "var(--sc-teal)",
              }}>→</div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function HomePage({ onSignOut, onOpenAnalysis, onOpenModule, onOpenDirectory }) {
  return (
    <div style={{ background: "var(--sc-parchment)", minHeight: "100vh" }} data-open-analysis>
      <GlobalNav
        active="home"
        onHome={() => {}}
        onSignOut={onSignOut}
        onOpenModule={(id) => {
          if (id === "analysis" && onOpenAnalysis) { onOpenAnalysis(); return; }
          onOpenModule && onOpenModule(id);
        }}
        onOpenDirectory={onOpenDirectory}
      />
      <HomeHero onOpenAnalysis={onOpenAnalysis} />
      <QuickAccessRow
        onOpenModule={onOpenModule}
        onOpenAnalysis={onOpenAnalysis}
        onOpenDirectory={onOpenDirectory}
      />
      <section style={{ padding: "32px 0 64px" }}>
        <div className="sc-container-wide" style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 16,
        }}>
          <PipelineFunnel />
          <ActiveAlerts />
          <PortfolioHealth />
          <RecentDeals onOpenAnalysis={onOpenAnalysis} />
          <Deadlines />
          <PEVerdicts />
          <div style={{ gridColumn: "1 / -1" }}>
            <CorpusInsights />
          </div>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}

Object.assign(window, { HomePage, AppNav });
