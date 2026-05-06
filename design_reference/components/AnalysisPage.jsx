// SeekingChartis — Deal Analysis Workbench (Variation C)
// Dense Bloomberg-style console with editorial chrome.

/* global React */

function AnalysisTopBar({ onBack, onSignOut }) {
  return (
    <header style={{ background: "#fff", borderBottom: "1px solid var(--sc-rule)" }}>
      <div className="sc-container-wide" style={{
        display: "flex", alignItems: "center", padding: "16px 0", gap: 24,
      }}>
        <a href="#" onClick={(e) => { e.preventDefault(); onBack && onBack(); }} style={{ textDecoration: "none" }}>
          <Wordmark />
        </a>
        <a
          href="#"
          onClick={(e) => { e.preventDefault(); onBack && onBack(); }}
          style={{
            marginLeft: 24,
            fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
            letterSpacing: "0.14em", textTransform: "uppercase",
            color: "var(--sc-text-dim)",
          }}
        >← Home</a>
        <div style={{ marginLeft: "auto", display: "flex", gap: 18, alignItems: "center" }}>
          <a
            href="#"
            onClick={(e) => { e.preventDefault(); onSignOut && onSignOut(); }}
            style={{
              fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
              letterSpacing: "0.12em", textTransform: "uppercase",
              color: "var(--sc-text-dim)",
            }}
          >Sign out</a>
          <div style={{
            width: 34, height: 34, borderRadius: "50%",
            background: "var(--sc-navy)", color: "#ffffff",
            display: "grid", placeItems: "center",
            fontFamily: "var(--sc-serif)", fontSize: 13, fontWeight: 600,
          }}>AT</div>
        </div>
      </div>
    </header>
  );
}

function WorkbenchHeader() {
  return (
    <section style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy)", padding: "28px 0 24px" }}>
      <div className="sc-container-wide">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
          <div>
            <div className="sc-eyebrow on-navy" style={{ marginBottom: 14 }}>Deal Workbench · CED-2023-047</div>
            <h1 style={{ fontFamily: "var(--sc-serif)", fontSize: 40, fontWeight: 400, color: "var(--sc-on-navy)", letterSpacing: "-0.01em" }}>
              Cedar Capital — cardiology roll-up
            </h1>
            <div style={{ fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-on-navy-dim)", marginTop: 10, letterSpacing: "0.06em" }}>
              DILIGENCE · 5 platforms · 22 sites · Phoenix + Tucson MSA · CCN 030085, 030112, +3
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <a href="#" className="sc-btn sc-btn-outline-light" style={{ fontSize: 11 }}>Export IC packet</a>
            <a href="#" className="sc-btn" style={{
              background: "var(--sc-teal)", color: "var(--sc-ink)", borderColor: "var(--sc-teal)", fontSize: 11,
            }}>Generate memo →</a>
          </div>
        </div>

        {/* Tab strip */}
        <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--sc-navy-3)", marginTop: 20 }}>
          {["Overview", "RCM Profile", "EBITDA Bridge", "Monte Carlo", "Scenarios", "Risk & Diligence", "Provenance"].map((t, i) => (
            <div key={t} style={{
              padding: "10px 18px",
              fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
              letterSpacing: "0.12em", textTransform: "uppercase",
              color: i === 0 ? "var(--sc-teal-2)" : "var(--sc-on-navy-dim)",
              borderBottom: i === 0 ? "2px solid var(--sc-teal)" : "2px solid transparent",
              cursor: "pointer",
            }}>{t}</div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HeadlineKPIs() {
  const kpis = [
    { l: "Entry multiple", v: "9.8x", s: "EBITDA · base case", tone: "neutral" },
    { l: "Base MOIC (P50)", v: "2.64x", s: "5-year hold", tone: "positive" },
    { l: "Base IRR (P50)", v: "21.4%", s: "Gross, levered", tone: "positive" },
    { l: "Covenant headroom", v: "128 bps", s: "leverage · narrow", tone: "warning" },
    { l: "Partner verdict", v: "PROCEED", s: "with caveats", tone: "warning" },
    { l: "Health score", v: "81", s: "top quartile", tone: "positive" },
  ];
  const toneColor = {
    positive: "var(--sc-positive)", warning: "var(--sc-warning)",
    negative: "var(--sc-negative)", neutral: "var(--sc-navy)",
  };
  return (
    <div className="sc-container-wide" style={{ marginTop: -28, marginBottom: 24, position: "relative", zIndex: 1 }}>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(6, 1fr)",
        background: "#fff", border: "1px solid var(--sc-rule)", boxShadow: "var(--sc-shadow-2)",
      }}>
        {kpis.map((k, i) => (
          <div key={i} style={{
            padding: "20px 20px",
            borderRight: i < kpis.length - 1 ? "1px solid var(--sc-rule)" : "none",
            borderTop: `3px solid ${toneColor[k.tone]}`,
          }}>
            <div style={{
              fontFamily: "var(--sc-mono)", fontSize: 9,
              letterSpacing: "0.14em", textTransform: "uppercase",
              color: "var(--sc-text-faint)", marginBottom: 10,
            }}>{k.l}</div>
            <div style={{
              fontFamily: "var(--sc-serif)", fontSize: 32, fontWeight: 500,
              color: toneColor[k.tone], letterSpacing: "-0.01em", lineHeight: 1,
            }}>{k.v}</div>
            <div style={{ fontSize: 11, color: "var(--sc-text-dim)", marginTop: 8 }}>{k.s}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Monte Carlo distribution chart
function MCDistribution() {
  // Pre-computed bins (roughly normal around 2.64x MOIC)
  const bins = [3, 6, 10, 18, 32, 54, 78, 95, 112, 128, 134, 128, 112, 90, 68, 48, 32, 20, 12, 6];
  const max = Math.max(...bins);
  const p50 = 9; // index of median
  const p90 = 14;
  const p10 = 4;
  return (
    <div>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(20, 1fr)",
        gap: 2, height: 140, alignItems: "end",
      }}>
        {bins.map((b, i) => {
          let col = "var(--sc-navy-3)";
          if (i >= p10 && i <= p90) col = "#3a6fb0";
          if (i === p50) col = "var(--sc-teal)";
          return <div key={i} style={{ height: `${(b / max) * 100}%`, background: col }}/>;
        })}
      </div>
      {/* Axis */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        marginTop: 8, fontFamily: "var(--sc-mono)", fontSize: 10,
        color: "var(--sc-text-faint)", letterSpacing: "0.06em",
      }}>
        <span>1.2x</span><span>P10 · 1.8x</span>
        <span style={{ color: "var(--sc-teal-ink)", fontWeight: 700 }}>P50 · 2.64x</span>
        <span>P90 · 3.4x</span><span>4.1x</span>
      </div>
      <div style={{
        marginTop: 14, padding: 12, background: "var(--sc-bone)",
        fontSize: 12, color: "var(--sc-text-dim)", lineHeight: 1.55,
      }}>
        <strong style={{ color: "var(--sc-navy)" }}>10,000 draws.</strong> Probability of MOIC ≥ 2.0x: <span className="sc-num" style={{ color: "var(--sc-positive)", fontWeight: 700 }}>81.4%</span>.
        Probability of covenant breach in years 2-3: <span className="sc-num" style={{ color: "var(--sc-warning)", fontWeight: 700 }}>14.2%</span>.
      </div>
    </div>
  );
}

// EBITDA bridge
function EbitdaBridge() {
  const steps = [
    { l: "LTM EBITDA", v: 42.1, from: 0 },
    { l: "Same-site growth", v: 4.8, from: 42.1 },
    { l: "RCM recovery", v: 3.2, from: 46.9 },
    { l: "Site adds (3)", v: 6.4, from: 50.1 },
    { l: "Denovo ramp", v: 2.1, from: 56.5 },
    { l: "Payer mix shift", v: -1.6, from: 58.6 },
    { l: "Year-5 EBITDA", v: 57.0, from: 0 },
  ];
  const max = 62;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 180 }}>
        {steps.map((s, i) => {
          const isTotal = i === 0 || i === steps.length - 1;
          const col = isTotal ? "var(--sc-navy)" : s.v > 0 ? "var(--sc-teal)" : "var(--sc-negative)";
          const h = isTotal ? (s.v / max) * 100 : (Math.abs(s.v) / max) * 100;
          const bottom = isTotal ? 0 : (s.v > 0 ? (s.from / max) * 100 : ((s.from + s.v) / max) * 100);
          return (
            <div key={i} style={{
              flex: 1, position: "relative", height: "100%",
              display: "flex", flexDirection: "column", justifyContent: "flex-end",
            }}>
              <div style={{
                position: "absolute", bottom: `${bottom}%`,
                left: 0, right: 0, height: `${h}%`,
                background: col,
              }}/>
              <div style={{
                position: "absolute", bottom: `calc(${bottom + h}% + 4px)`,
                left: 0, right: 0, textAlign: "center",
                fontFamily: "var(--sc-mono)", fontSize: 11, fontWeight: 700,
                color: s.v < 0 ? "var(--sc-negative)" : "var(--sc-text)",
              }}>{s.v > 0 ? "+" : ""}{s.v.toFixed(1)}</div>
            </div>
          );
        })}
      </div>
      <div style={{
        display: "flex", gap: 8, marginTop: 10,
        borderTop: "1px solid var(--sc-rule)", paddingTop: 8,
      }}>
        {steps.map((s, i) => (
          <div key={i} style={{
            flex: 1, textAlign: "center",
            fontFamily: "var(--sc-mono)", fontSize: 9,
            color: "var(--sc-text-faint)", letterSpacing: "0.08em",
            textTransform: "uppercase", lineHeight: 1.3,
          }}>{s.l}</div>
        ))}
      </div>
    </div>
  );
}

// Risk matrix
function RiskMatrix() {
  const risks = [
    { k: "Payer concentration", prob: "M", imp: "H", tone: "warning" },
    { k: "Physician comp dilution", prob: "H", imp: "M", tone: "warning" },
    { k: "Anti-kickback exposure", prob: "L", imp: "H", tone: "neutral" },
    { k: "Covenant trip yr 2-3", prob: "M", imp: "M", tone: "warning" },
    { k: "RCM vendor transition", prob: "H", imp: "L", tone: "neutral" },
    { k: "Denovo ramp slip", prob: "M", imp: "M", tone: "neutral" },
  ];
  const toneMap = {
    critical: "var(--sc-critical)", warning: "var(--sc-warning)",
    neutral: "var(--sc-navy-3)", positive: "var(--sc-positive)",
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 40px 40px 60px",
        fontFamily: "var(--sc-mono)", fontSize: 9, letterSpacing: "0.12em",
        color: "var(--sc-text-faint)", textTransform: "uppercase",
        padding: "0 0 6px", borderBottom: "1px solid var(--sc-navy)",
      }}>
        <span>Risk</span>
        <span style={{ textAlign: "center" }}>Prob</span>
        <span style={{ textAlign: "center" }}>Imp</span>
        <span style={{ textAlign: "right" }}>Score</span>
      </div>
      {risks.map((r, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "1fr 40px 40px 60px",
          padding: "8px 0", alignItems: "center", fontSize: 13,
          borderBottom: "1px solid var(--sc-rule)",
        }}>
          <span style={{ color: "var(--sc-text)" }}>{r.k}</span>
          <span style={{ fontFamily: "var(--sc-mono)", textAlign: "center", fontWeight: 700, color: "var(--sc-text-dim)" }}>{r.prob}</span>
          <span style={{ fontFamily: "var(--sc-mono)", textAlign: "center", fontWeight: 700, color: "var(--sc-text-dim)" }}>{r.imp}</span>
          <span style={{
            fontFamily: "var(--sc-mono)", textAlign: "right", fontSize: 10, fontWeight: 700,
            letterSpacing: "0.1em", textTransform: "uppercase", color: toneMap[r.tone],
          }}>{r.tone}</span>
        </div>
      ))}
    </div>
  );
}

function DiligenceChecklist() {
  const items = [
    { k: "HCRIS 3-year pre-fill complete", status: "done" },
    { k: "CMS Care Compare quality scores ingested", status: "done" },
    { k: "Payer contract summary uploaded", status: "done" },
    { k: "QoE report (Ernst draft v2)", status: "done" },
    { k: "Physician comp plan analysis", status: "progress" },
    { k: "Anti-kickback legal memo (Kirkland)", status: "progress" },
    { k: "Site-level denial drill-down", status: "todo" },
    { k: "Partner review sign-off", status: "todo" },
  ];
  const icon = {
    done: <span style={{ color: "var(--sc-positive)", fontWeight: 700 }}>✓</span>,
    progress: <span style={{ color: "var(--sc-warning)", fontWeight: 700 }}>◐</span>,
    todo: <span style={{ color: "var(--sc-text-faint)", fontWeight: 700 }}>○</span>,
  };
  return (
    <div>
      {items.map((it, i) => (
        <div key={i} style={{
          display: "flex", gap: 12, padding: "7px 0", alignItems: "center", fontSize: 13,
          borderBottom: i < items.length - 1 ? "1px solid var(--sc-rule)" : "none",
        }}>
          <span style={{ width: 18, textAlign: "center", fontFamily: "var(--sc-mono)" }}>{icon[it.status]}</span>
          <span style={{ flex: 1, color: it.status === "done" ? "var(--sc-text-dim)" : "var(--sc-text)", textDecoration: it.status === "done" ? "line-through" : "none" }}>{it.k}</span>
        </div>
      ))}
      <div style={{
        marginTop: 14, padding: 12, background: "var(--sc-bone)",
        fontFamily: "var(--sc-mono)", fontSize: 11,
      }}>
        <span style={{ color: "var(--sc-text-faint)", letterSpacing: "0.1em", textTransform: "uppercase" }}>IC READINESS · </span>
        <span style={{ color: "var(--sc-warning)", fontWeight: 700 }}>62% complete</span>
        <span style={{ color: "var(--sc-text-dim)", marginLeft: 8 }}> — 3 items outstanding</span>
      </div>
    </div>
  );
}

function PartnerNarrative() {
  return (
    <div style={{
      background: "var(--sc-ink)", color: "var(--sc-on-navy)", padding: "28px 32px",
      borderLeft: "3px solid var(--sc-teal)",
    }}>
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 10,
        letterSpacing: "0.14em", textTransform: "uppercase",
        color: "var(--sc-teal-2)", marginBottom: 14,
      }}>Partner review · auto-generated</div>
      <blockquote style={{
        fontFamily: "var(--sc-serif)", fontSize: 20, fontStyle: "italic",
        lineHeight: 1.5, color: "var(--sc-on-navy)", marginBottom: 20,
      }}>
        “Thesis of margin recovery through sub-scale consolidation is validated
        by the corpus — 14 comparable cardiology roll-ups in 2018-2022 hit
        2.4x+ MOIC at similar entry multiples. Flag for IC: physician comp
        plan conversion is the single largest integration risk. Model
        assumes 85% retention; we've seen 72% in the base rates.”
      </blockquote>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        paddingTop: 14, borderTop: "1px solid var(--sc-navy-3)",
        fontFamily: "var(--sc-mono)", fontSize: 11, color: "var(--sc-on-navy-dim)", letterSpacing: "0.06em",
      }}>
        <span>Verdict: <span style={{ color: "var(--sc-warning)", fontWeight: 700, letterSpacing: "0.14em" }}>PROCEED WITH CAVEATS</span></span>
        <span>Heuristics fired: 4 · Critical: 1 · Confidence: 0.78</span>
      </div>
    </div>
  );
}

function AnalysisPage({ onBack, onSignOut, onOpenModule, onOpenDirectory }) {
  return (
    <div style={{ background: "var(--sc-parchment)", minHeight: "100vh" }}>
      <GlobalNav
        active="analysis"
        dealContext={{ dealName: "Cedar cardiology roll-up", active: "analysis" }}
        onHome={onBack}
        onSignOut={onSignOut}
        onOpenModule={(id) => {
          if (id === "analysis") return;
          onOpenModule && onOpenModule(id);
        }}
        onOpenDirectory={onOpenDirectory}
        onOpenDealTab={(id) => {
          if (id === "analysis") return;
          onOpenModule && onOpenModule(id);
        }}
      />
      <Breadcrumb trail={["Home", "Deals", "Cedar cardiology", "Analysis"]} />
      <WorkbenchHeader />
      <HeadlineKPIs />
      <section style={{ paddingBottom: 48 }}>
        <div className="sc-container-wide" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <DataPanel code="MCS" title="Monte Carlo · MOIC distribution" style={{ gridColumn: "1 / -1" }}>
            <MCDistribution />
          </DataPanel>
          <DataPanel code="BRG" title="EBITDA Bridge · entry → year-5 P50">
            <EbitdaBridge />
          </DataPanel>
          <DataPanel code="RSK" title="Risk Matrix">
            <RiskMatrix />
          </DataPanel>
          <DataPanel code="DDL" title="Diligence Checklist">
            <DiligenceChecklist />
          </DataPanel>
          <DataPanel code="COM" title="Top-3 comparable deals">
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {[
                { n: "Desert Cardiology Partners", y: 2019, moic: "2.71x", irr: "19.4%" },
                { n: "Sonoran Heart Institute", y: 2020, moic: "2.48x", irr: "18.1%" },
                { n: "Piedmont Cardiovascular", y: 2018, moic: "2.34x", irr: "17.8%" },
              ].map((c, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: "1fr 50px 70px 70px",
                  padding: "10px 0", gap: 10, alignItems: "baseline",
                  borderBottom: "1px solid var(--sc-rule)", fontSize: 13,
                }}>
                  <a href="#" style={{ color: "var(--sc-teal-ink)" }}>{c.n}</a>
                  <span className="sc-num" style={{ color: "var(--sc-text-faint)" }}>{c.y}</span>
                  <span className="sc-num" style={{ textAlign: "right", fontWeight: 600 }}>{c.moic}</span>
                  <span className="sc-num" style={{ textAlign: "right", color: "var(--sc-positive)", fontWeight: 600 }}>{c.irr}</span>
                </div>
              ))}
              <div style={{ fontSize: 12, color: "var(--sc-text-dim)", marginTop: 10, fontStyle: "italic" }}>
                Cohort-weighted mean · n=14 · 2018-2022 vintages
              </div>
            </div>
          </DataPanel>
          <div style={{ gridColumn: "1 / -1" }}>
            <PartnerNarrative />
          </div>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}

Object.assign(window, { AnalysisPage });
