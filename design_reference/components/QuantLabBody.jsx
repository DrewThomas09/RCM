// SeekingChartis — Quant Lab body
// Faithful rebuild of rcm_mc/ui/quant_lab_page.py in our editorial visual
// language. Kind = "quant" hits this. Used inside ModulePage when the
// module catalog entry has kind === "quant".

/* global React */

function QuantLabBody() {
  return (
    <section style={{ padding: "28px 0 56px" }}>
      <div className="sc-container-wide" style={{ display: "flex", flexDirection: "column", gap: 28 }}>

        {/* Top-of-page summary KPIs (parity with render_quant_lab kpi strip) */}
        <QuantKPIs />

        {/* The Six Stacks — parity with "SeekingChartis Quant Stack" card */}
        <QuantStackGrid />

        {/* Bayesian calibration table */}
        <BayesianCalibrationCard />

        {/* DEA Efficiency Frontier */}
        <EfficiencyFrontierCard />

        {/* State Market Intelligence */}
        <StateMarketCard />

        {/* M/M/c RCM Queueing */}
        <QueueingCard />

      </div>
    </section>
  );
}

// ---------- KPI strip ----------

function QuantKPIs() {
  const kpis = [
    { v: "5,808",  l: "Hospitals" },
    { v: "52",     l: "Markets" },
    { v: "418",    l: "Frontier hospitals" },
    { v: "0.824",  l: "Distress AUC" },
    { v: "12",     l: "Quant models" },
    { v: "0",      l: "External deps" },
  ];
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(6, 1fr)",
      background: "#fff",
      border: "1px solid var(--sc-rule)",
    }}>
      {kpis.map((k, i) => (
        <div key={i} style={{
          padding: "18px 20px",
          borderLeft: i ? "1px solid var(--sc-rule)" : "none",
        }}>
          <div style={{
            fontFamily: "var(--sc-serif)", fontSize: 28, lineHeight: 1.05,
            color: "var(--sc-navy)", fontWeight: 500,
          }}>{k.v}</div>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 9.5, marginTop: 6,
            letterSpacing: "0.14em", textTransform: "uppercase",
            color: "var(--sc-text-faint)",
          }}>{k.l}</div>
        </div>
      ))}
    </div>
  );
}

// ---------- The Six Stacks ----------

function QuantStackGrid() {
  const stacks = [
    { name: "Econometrics", items: [
      "OLS with VIF + state R²",
      "Ridge regression + elastic net",
      "Per-hospital residual analysis",
      "Cross-sectional price elasticity",
    ]},
    { name: "Biostatistics", items: [
      "Beta-Binomial partial pooling",
      "Gamma-Lognormal hierarchies",
      "Survival / hazard for margin runway",
      "Missing-data scoring (MNAR)",
    ]},
    { name: "Operations research", items: [
      "M/M/c queueing (Erlang C)",
      "Little's Law backlog analysis",
      "DEA efficiency frontier",
      "Staffing optimization",
    ]},
    { name: "Machine learning", items: [
      "K-means hospital clustering",
      "Logistic distress prediction",
      "Ensemble (Ridge + k-NN + median)",
      "Conformal prediction intervals",
    ]},
    { name: "Causal inference", items: [
      "Interrupted Time Series",
      "Difference-in-Differences",
      "Counterfactual estimation",
      "Cross-deal learning / shrinkage",
    ]},
    { name: "Simulation", items: [
      "Two-source Monte Carlo",
      "Latin Hypercube sampling",
      "Correlated lever draws",
      "P10 / P50 / P90 distributions",
    ]},
  ];
  return (
    <div>
      <SectionHead
        kicker="The stack"
        title="Six disciplines, one platform"
        blurb="Everything on this page is computed in-process from the corpus — no SaaS dependencies, no external model calls."
      />
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 0,
        border: "1px solid var(--sc-rule)",
        background: "#fff",
      }}>
        {stacks.map((s, i) => (
          <div key={s.name} style={{
            padding: "18px 20px 20px",
            borderRight: (i % 3 !== 2) ? "1px solid var(--sc-rule)" : "none",
            borderBottom: (i < 3) ? "1px solid var(--sc-rule)" : "none",
          }}>
            <div style={{
              fontFamily: "var(--sc-mono)", fontSize: 10,
              letterSpacing: "0.16em", textTransform: "uppercase",
              color: "var(--sc-teal-ink)", fontWeight: 700,
              marginBottom: 10,
            }}>{s.name}</div>
            <ul style={{
              margin: 0, padding: 0, listStyle: "none",
              fontFamily: "var(--sc-sans)", fontSize: 13,
              color: "var(--sc-text)", lineHeight: 1.55,
            }}>
              {s.items.map((it, j) => (
                <li key={j} style={{
                  padding: "4px 0",
                  borderBottom: j < s.items.length - 1 ? "1px dashed var(--sc-rule)" : "none",
                }}>{it}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Bayesian calibration (tight-data → prior shrinkage chart) ----------

function BayesianCalibrationCard() {
  const rows = [
    { label: "Strong data (n=500)", obs: 0.12, n: 500, post: 0.121, ci: [0.108, 0.134], shrink: 0.05, q: "A" },
    { label: "Moderate data (n=50)", obs: 0.12, n: 50,  post: 0.114, ci: [0.089, 0.141], shrink: 0.28, q: "B" },
    { label: "Weak data (n=5)",      obs: 0.12, n: 5,   post: 0.094, ci: [0.060, 0.135], shrink: 0.74, q: "C" },
    { label: "No data (prior only)", obs: null, n: 0,   post: 0.085, ci: [0.055, 0.122], shrink: 1.00, q: "D" },
    { label: "Low observed (n=100)", obs: 0.03, n: 100, post: 0.042, ci: [0.028, 0.061], shrink: 0.32, q: "B" },
    { label: "High observed (n=100)",obs: 0.25, n: 100, post: 0.232, ci: [0.197, 0.270], shrink: 0.17, q: "A" },
  ];

  // Scale 0 to 0.30 for the distribution band row
  const scaleMin = 0;
  const scaleMax = 0.30;
  const pct = (v) => ((v - scaleMin) / (scaleMax - scaleMin)) * 100;
  const prior = 0.085;

  return (
    <div>
      <SectionHead
        kicker="Biostatistics · Beta–Binomial partial pooling"
        title="Denial rate calibration"
        blurb="Posterior shrinks toward the peer-group prior (8.5% for medium hospitals) as sample size falls. The band below each row shows the 90% credible interval; the dot is the posterior mean."
      />
      <div style={{
        background: "#fff", border: "1px solid var(--sc-rule)",
        padding: "18px 20px",
      }}>
        {/* Axis */}
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 80px 80px", gap: 16, marginBottom: 8 }}>
          <div/>
          <div style={{ position: "relative", height: 20 }}>
            {[0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30].map((t) => (
              <div key={t} style={{
                position: "absolute", left: `${pct(t)}%`, top: 6,
                fontFamily: "var(--sc-mono)", fontSize: 9.5,
                letterSpacing: "0.08em", color: "var(--sc-text-faint)",
                transform: "translateX(-50%)",
              }}>{(t * 100).toFixed(0)}%</div>
            ))}
            {/* Prior marker */}
            <div style={{
              position: "absolute", left: `${pct(prior)}%`, top: 0, bottom: -260,
              borderLeft: "1px dashed var(--sc-teal)",
            }}/>
            <div style={{
              position: "absolute", left: `${pct(prior)}%`, top: -14,
              fontFamily: "var(--sc-mono)", fontSize: 9, fontWeight: 700,
              letterSpacing: "0.1em", color: "var(--sc-teal-ink)",
              transform: "translateX(-50%)", whiteSpace: "nowrap",
            }}>PRIOR 8.5%</div>
          </div>
          <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 9.5, letterSpacing: "0.12em", color: "var(--sc-text-faint)" }}>SHRINK</div>
          <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 9.5, letterSpacing: "0.12em", color: "var(--sc-text-faint)" }}>QUALITY</div>
        </div>

        {rows.map((r, i) => (
          <div key={i} style={{
            display: "grid", gridTemplateColumns: "220px 1fr 80px 80px",
            gap: 16, alignItems: "center",
            padding: "10px 0",
            borderTop: i ? "1px dashed var(--sc-rule)" : "1px solid var(--sc-rule)",
          }}>
            <div>
              <div style={{ fontFamily: "var(--sc-serif)", fontSize: 14, color: "var(--sc-navy)" }}>{r.label}</div>
              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10.5, color: "var(--sc-text-faint)", marginTop: 2 }}>
                {r.obs == null ? "observed — / n 0" : `observed ${(r.obs * 100).toFixed(1)}% · n ${r.n}`}
              </div>
            </div>

            {/* Band + posterior dot */}
            <div style={{ position: "relative", height: 22 }}>
              <div style={{
                position: "absolute", top: 9, left: 0, right: 0, height: 1,
                background: "var(--sc-rule)",
              }}/>
              <div style={{
                position: "absolute", top: 6, height: 8,
                left: `${pct(r.ci[0])}%`,
                width: `${pct(r.ci[1]) - pct(r.ci[0])}%`,
                background: qualityTint(r.q), opacity: 0.35,
              }}/>
              {r.obs != null && (
                <div style={{
                  position: "absolute", top: 5, left: `calc(${pct(r.obs)}% - 4px)`,
                  width: 8, height: 10, border: "1.5px solid var(--sc-text-dim)",
                  background: "transparent",
                }} title="Observed"/>
              )}
              <div style={{
                position: "absolute", top: 4, left: `calc(${pct(r.post)}% - 6px)`,
                width: 12, height: 12, borderRadius: "50%",
                background: qualityTint(r.q),
                border: "2px solid #fff",
                boxShadow: "0 0 0 1px rgba(11,35,65,0.4)",
              }} title={`Posterior ${(r.post*100).toFixed(1)}%`}/>
            </div>

            <div style={{
              textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600,
              color: r.shrink < 0.3 ? "var(--sc-positive)"
                   : r.shrink < 0.7 ? "#b36a2e"
                   : "var(--sc-negative)",
            }}>{(r.shrink * 100).toFixed(0)}%</div>
            <div style={{
              textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600,
              color: "var(--sc-navy)",
            }}>{r.q}</div>
          </div>
        ))}

        {/* Legend */}
        <div style={{
          display: "flex", gap: 24, marginTop: 14, paddingTop: 12,
          borderTop: "1px solid var(--sc-rule)",
          fontFamily: "var(--sc-mono)", fontSize: 10.5, color: "var(--sc-text-dim)",
          letterSpacing: "0.04em",
        }}>
          <LegendDot color="var(--sc-positive)" label="Posterior mean" filled/>
          <LegendDot color="var(--sc-text-dim)" label="Observed rate" square/>
          <LegendDot color="var(--sc-teal)" label="Prior · peer group" dashed/>
          <span style={{ color: "var(--sc-text-faint)" }}>Band = 90% credible interval</span>
        </div>
      </div>
    </div>
  );
}

function qualityTint(q) {
  if (q === "A") return "#2d8f5a";
  if (q === "B") return "#5aa37a";
  if (q === "C") return "#d4a13b";
  if (q === "D") return "#a13b2a";
  return "var(--sc-teal)";
}

function LegendDot({ color, label, filled, square, dashed }) {
  let marker;
  if (dashed) {
    marker = <div style={{ width: 18, height: 2, background: "transparent",
      borderTop: `2px dashed ${color}`, margin: "0 4px" }}/>;
  } else if (square) {
    marker = <div style={{ width: 10, height: 10, border: `1.5px solid ${color}` }}/>;
  } else {
    marker = <div style={{ width: 10, height: 10, borderRadius: "50%",
      background: filled ? color : "transparent", border: `2px solid ${color}` }}/>;
  }
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      {marker}
      <span>{label}</span>
    </span>
  );
}

// ---------- DEA Efficiency Frontier ----------

function EfficiencyFrontierCard() {
  // Deterministic scatter + labeled frontier hospitals
  const hospitals = [
    { n: "Cedar Valley Medical",      st: "TX", score: 1.000, p: 100, frontier: true },
    { n: "Piedmont Regional",         st: "GA", score: 1.000, p: 100, frontier: true },
    { n: "Summit Health Center",      st: "CO", score: 0.987, p: 99,  frontier: false },
    { n: "Harbor Valley Medical",     st: "WA", score: 0.952, p: 97,  frontier: false },
    { n: "Stonefield Community",      st: "OH", score: 0.894, p: 93,  frontier: false },
    { n: "Blue Ridge General",        st: "VA", score: 0.831, p: 88,  frontier: false },
    { n: "Magnolia Health System",    st: "AL", score: 0.742, p: 78,  frontier: false },
    { n: "Elkhorn Baptist",           st: "NE", score: 0.681, p: 71,  frontier: false },
    { n: "Westbrook Memorial",        st: "MN", score: 0.522, p: 48,  frontier: false },
    { n: "Fairview County",           st: "KY", score: 0.411, p: 32,  frontier: false },
    { n: "Mesa Desert Hospital",      st: "AZ", score: 0.287, p: 18,  frontier: false },
    { n: "Coastal Lincoln",           st: "NC", score: 0.231, p: 12,  frontier: false },
  ];

  // Synthetic (inputs, outputs) scatter points, seeded from hospital index
  const pts = hospitals.map((h, i) => {
    const x = 20 + ((i * 13) % 100) * 0.8 + Math.sin(i) * 4;
    const y = 40 + h.score * 50 + Math.cos(i * 2) * 3;
    return { ...h, x, y };
  });

  // Frontier = top-left envelope: approximate
  const frontierPts = [...pts].sort((a, b) => a.x - b.x).filter(p => p.score > 0.88);

  return (
    <div>
      <SectionHead
        kicker="Operations research · DEA"
        title="Operational efficiency frontier"
        blurb="Hospitals on the frontier (gold) use the lowest inputs — beds + operating expenses — relative to output (net patient revenue + patient days). The rest are benchmarked against that envelope."
      />
      <div style={{
        background: "#fff", border: "1px solid var(--sc-rule)",
        display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) minmax(280px, 1fr)", gap: 0,
      }}>
        {/* Scatter */}
        <div style={{ padding: "18px 20px", borderRight: "1px solid var(--sc-rule)" }}>
          <svg viewBox="0 0 400 280" style={{ width: "100%", height: 280 }}>
            {/* gridlines */}
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((t, i) => (
              <line key={i} x1="40" y1={40 + (1 - t) * 200} x2="390" y2={40 + (1 - t) * 200}
                stroke="var(--sc-rule)" strokeDasharray="3 4"/>
            ))}
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((t, i) => (
              <text key={`yt${i}`} x="34" y={44 + (1 - t) * 200}
                textAnchor="end" fontFamily="var(--sc-mono)" fontSize="9"
                fill="var(--sc-text-faint)">{t.toFixed(1)}</text>
            ))}
            {/* axis labels */}
            <text x="6" y="140" transform="rotate(-90 6 140)"
              fontFamily="var(--sc-mono)" fontSize="9" fill="var(--sc-text-faint)"
              letterSpacing="1">EFFICIENCY SCORE</text>
            <text x="220" y="274" textAnchor="middle"
              fontFamily="var(--sc-mono)" fontSize="9" fill="var(--sc-text-faint)"
              letterSpacing="1">COMPOSITE INPUT USE (BEDS + OPEX)</text>

            {/* frontier envelope path */}
            {frontierPts.length > 1 && (
              <path
                d={`M 40,240 ${frontierPts.map(p => `L ${40 + p.x * 3},${40 + (1 - p.score) * 200}`).join(" ")} L 390,240 Z`}
                fill="#d4a13b" fillOpacity="0.10" stroke="none"
              />
            )}
            {frontierPts.length > 1 && (
              <polyline
                points={frontierPts.map(p => `${40 + p.x * 3},${40 + (1 - p.score) * 200}`).join(" ")}
                fill="none" stroke="#b8871f" strokeWidth="1.5"
              />
            )}

            {/* points */}
            {pts.map((p, i) => (
              <g key={i}>
                <circle
                  cx={40 + p.x * 3}
                  cy={40 + (1 - p.score) * 200}
                  r={p.frontier ? 6 : 4}
                  fill={p.frontier ? "#d4a13b" : "var(--sc-teal)"}
                  stroke="#fff"
                  strokeWidth="1.5"
                  opacity={p.frontier ? 1 : 0.75}
                />
                {p.frontier && (
                  <text x={40 + p.x * 3 + 9} y={40 + (1 - p.score) * 200 + 3}
                    fontFamily="var(--sc-mono)" fontSize="9"
                    fill="var(--sc-navy)" fontWeight="600">
                    {p.n.split(" ")[0]}
                  </text>
                )}
              </g>
            ))}
          </svg>
        </div>

        {/* Top-of-list */}
        <div style={{ padding: "18px 20px" }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10,
            letterSpacing: "0.16em", textTransform: "uppercase",
            color: "var(--sc-text-faint)", marginBottom: 10,
          }}>Top 12 · efficiency rank</div>
          <div style={{ borderTop: "1px solid var(--sc-rule)" }}>
            {hospitals.map((h, i) => (
              <div key={i} style={{
                display: "grid",
                gridTemplateColumns: "22px 1fr 36px 58px 20px",
                gap: 8, alignItems: "baseline",
                padding: "8px 0",
                borderBottom: "1px dashed var(--sc-rule)",
              }}>
                <span style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-text-faint)" }}>{String(i + 1).padStart(2, "0")}</span>
                <span style={{ fontFamily: "var(--sc-serif)", fontSize: 13, color: "var(--sc-navy)" }}>{h.n}</span>
                <span style={{ fontFamily: "var(--sc-mono)", fontSize: 10.5, color: "var(--sc-text-faint)" }}>{h.st}</span>
                <span style={{
                  fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600,
                  color: h.score >= 0.8 ? "var(--sc-positive)" : h.score >= 0.5 ? "#b36a2e" : "var(--sc-negative)",
                  textAlign: "right",
                }}>{h.score.toFixed(3)}</span>
                <span style={{ color: "#d4a13b", fontSize: 13 }}>{h.frontier ? "★" : ""}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- State Market Intelligence (dense table) ----------

function StateMarketCard() {
  const rows = [
    { st: "TX", n: 412, rev: "$68.2B", margin: 0.058, hhi: 842,  conc: "Fragmented",    inv: "78 (B)", distress: 0.11 },
    { st: "CA", n: 389, rev: "$91.6B", margin: 0.042, hhi: 621,  conc: "Fragmented",    inv: "72 (B)", distress: 0.14 },
    { st: "FL", n: 314, rev: "$52.4B", margin: 0.074, hhi: 1140, conc: "Moderate",      inv: "82 (A)", distress: 0.09 },
    { st: "NY", n: 228, rev: "$64.1B", margin: 0.029, hhi: 1820, conc: "Moderate",      inv: "64 (C)", distress: 0.19 },
    { st: "GA", n: 168, rev: "$21.8B", margin: 0.061, hhi: 1462, conc: "Moderate",      inv: "75 (B)", distress: 0.12 },
    { st: "OH", n: 201, rev: "$28.9B", margin: 0.045, hhi: 988,  conc: "Fragmented",    inv: "69 (C)", distress: 0.16 },
    { st: "PA", n: 196, rev: "$34.2B", margin: 0.038, hhi: 1304, conc: "Moderate",      inv: "66 (C)", distress: 0.18 },
    { st: "IL", n: 184, rev: "$27.7B", margin: 0.034, hhi: 1518, conc: "Moderate",      inv: "62 (C)", distress: 0.21 },
    { st: "NC", n: 162, rev: "$22.3B", margin: 0.069, hhi: 1684, conc: "Moderate",      inv: "79 (B)", distress: 0.10 },
    { st: "AZ", n:  98, rev: "$14.8B", margin: 0.081, hhi: 2610, conc: "Concentrated",  inv: "84 (A)", distress: 0.08 },
    { st: "WA", n: 112, rev: "$19.4B", margin: 0.063, hhi: 2184, conc: "Concentrated",  inv: "77 (B)", distress: 0.11 },
    { st: "CO", n:  94, rev: "$13.1B", margin: 0.072, hhi: 1892, conc: "Moderate",      inv: "80 (A)", distress: 0.09 },
  ];
  const gradeColor = (s) => {
    if (s.startsWith("8") || s.startsWith("9") || s.startsWith("10")) return "var(--sc-positive)";
    if (s.startsWith("7")) return "var(--sc-positive)";
    if (s.startsWith("6")) return "#b36a2e";
    return "var(--sc-negative)";
  };
  return (
    <div>
      <SectionHead
        kicker="Market intelligence · 52 states"
        title="State market map"
        blurb="HHI (Herfindahl–Hirschman Index) quantifies concentration: >2500 highly concentrated, 1500-2500 moderate, <1500 fragmented. Investability combines market depth, growth, health, and payer quality."
      />
      <div style={{
        background: "#fff", border: "1px solid var(--sc-rule)",
        overflow: "hidden",
      }}>
        {/* Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "46px 72px 92px 94px 80px 132px 96px 86px",
          columnGap: 14,
          padding: "10px 18px",
          background: "var(--sc-bone)",
          borderBottom: "1px solid var(--sc-rule)",
          fontFamily: "var(--sc-mono)", fontSize: 9.5,
          letterSpacing: "0.14em", textTransform: "uppercase",
          color: "var(--sc-text-faint)", fontWeight: 700,
        }}>
          <div>State</div>
          <div style={{ textAlign: "right" }}>Hosp.</div>
          <div style={{ textAlign: "right" }}>Revenue</div>
          <div style={{ textAlign: "right" }}>Med. margin</div>
          <div style={{ textAlign: "right" }}>HHI</div>
          <div>Concentration</div>
          <div style={{ textAlign: "right" }}>Invest.</div>
          <div style={{ textAlign: "right" }}>Distress</div>
        </div>
        {rows.map((r, i) => (
          <div key={r.st} style={{
            display: "grid",
            gridTemplateColumns: "46px 72px 92px 94px 80px 132px 96px 86px",
            columnGap: 14,
            padding: "10px 18px",
            borderBottom: i < rows.length - 1 ? "1px dashed var(--sc-rule)" : "none",
            alignItems: "baseline",
          }}>
            <div style={{ fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 700, color: "var(--sc-teal-ink)" }}>{r.st}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.n}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.rev}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: r.margin >= 0.05 ? "var(--sc-positive)" : "var(--sc-negative)" }}>{(r.margin * 100).toFixed(1)}%</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.hhi.toLocaleString()}</div>
            <div style={{ fontFamily: "var(--sc-sans)", fontSize: 12, color: "var(--sc-text-dim)" }}>{r.conc}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600, color: gradeColor(r.inv) }}>{r.inv}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-negative)" }}>{(r.distress * 100).toFixed(0)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- M/M/c Queueing Analysis ----------

function QueueingCard() {
  const rows = [
    { q: "Authorization",       arr: 140, servers: 6,  util: 0.92, wait: 2.4, sla: 0.31, rec: 8, status: "BOTTLENECK" },
    { q: "Charge capture",      arr: 210, servers: 10, util: 0.78, wait: 1.1, sla: 0.09, rec: 10, status: "OK" },
    { q: "Coding review",       arr: 180, servers: 8,  util: 0.85, wait: 1.8, sla: 0.18, rec: 9, status: "WATCH" },
    { q: "Claims scrub",        arr: 240, servers: 12, util: 0.71, wait: 0.7, sla: 0.04, rec: 12, status: "OK" },
    { q: "Denial rework",       arr: 96,  servers: 4,  util: 0.88, wait: 3.2, sla: 0.27, rec: 6, status: "BOTTLENECK" },
    { q: "AR follow-up",        arr: 165, servers: 9,  util: 0.74, wait: 1.3, sla: 0.08, rec: 9, status: "OK" },
    { q: "Patient statements",  arr: 220, servers: 10, util: 0.81, wait: 1.5, sla: 0.12, rec: 11, status: "WATCH" },
  ];
  const statusColor = (s) => s === "BOTTLENECK" ? "var(--sc-negative)"
    : s === "WATCH" ? "#b36a2e" : "var(--sc-positive)";
  return (
    <div>
      <SectionHead
        kicker="Operations research · M/M/c queues"
        title="RCM queueing analysis"
        blurb="Each RCM workqueue modeled as M/M/c via Erlang C + Little's Law. Utilization > 85% flags a bottleneck; recommended staffing brings SLA breach below 5%."
      />
      <div style={{ background: "#fff", border: "1px solid var(--sc-rule)" }}>
        {/* Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 80px 62px 92px 84px 96px 80px 114px",
          columnGap: 14,
          padding: "10px 18px",
          background: "var(--sc-bone)",
          borderBottom: "1px solid var(--sc-rule)",
          fontFamily: "var(--sc-mono)", fontSize: 9.5,
          letterSpacing: "0.14em", textTransform: "uppercase",
          color: "var(--sc-text-faint)", fontWeight: 700,
        }}>
          <div>Queue</div>
          <div style={{ textAlign: "right" }}>Arrivals</div>
          <div style={{ textAlign: "right" }}>Staff</div>
          <div style={{ textAlign: "right" }}>Utilization</div>
          <div style={{ textAlign: "right" }}>Avg wait</div>
          <div style={{ textAlign: "right" }}>SLA breach</div>
          <div style={{ textAlign: "right" }}>Rec.</div>
          <div>Status</div>
        </div>
        {rows.map((r, i) => (
          <div key={r.q} style={{
            display: "grid",
            gridTemplateColumns: "1.4fr 80px 62px 92px 84px 96px 80px 114px",
            columnGap: 14,
            padding: "12px 18px",
            borderBottom: i < rows.length - 1 ? "1px dashed var(--sc-rule)" : "none",
            alignItems: "center",
          }}>
            <div style={{ fontFamily: "var(--sc-serif)", fontSize: 14, color: "var(--sc-navy)" }}>{r.q}</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.arr}/day</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.servers}</div>

            {/* utilization bar */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
              <div style={{ flex: "1 1 auto", maxWidth: 40, background: "var(--sc-parchment)", height: 10, border: "1px solid var(--sc-rule)" }}>
                <div style={{
                  width: `${r.util * 100}%`, height: "100%",
                  background: r.util > 0.85 ? "var(--sc-negative)"
                             : r.util > 0.7 ? "#b36a2e" : "var(--sc-positive)",
                }}/>
              </div>
              <span style={{ fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600, minWidth: 30, textAlign: "right", color: r.util > 0.85 ? "var(--sc-negative)" : r.util > 0.7 ? "#b36a2e" : "var(--sc-positive)" }}>
                {(r.util * 100).toFixed(0)}%
              </span>
            </div>

            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text)" }}>{r.wait.toFixed(1)}d</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, color: r.sla > 0.2 ? "var(--sc-negative)" : r.sla > 0.05 ? "#b36a2e" : "var(--sc-positive)" }}>{(r.sla * 100).toFixed(0)}%</div>
            <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 12, fontWeight: 600, color: "var(--sc-navy)" }}>{r.rec}</div>
            <div style={{
              fontFamily: "var(--sc-mono)", fontSize: 10,
              letterSpacing: "0.12em", fontWeight: 700,
              color: statusColor(r.status),
            }}>{r.status}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Shared section head ----------

function SectionHead({ kicker, title, blurb }) {
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1.4fr)",
      gap: 40, alignItems: "baseline", marginBottom: 14,
    }}>
      <div>
        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 10,
          letterSpacing: "0.16em", textTransform: "uppercase",
          color: "var(--sc-teal-ink)", fontWeight: 700,
          marginBottom: 6,
        }}>{kicker}</div>
        <h2 style={{
          fontFamily: "var(--sc-serif)", fontSize: 24, lineHeight: 1.15,
          fontWeight: 500, color: "var(--sc-navy)", margin: 0,
          letterSpacing: "-0.005em",
        }}>{title}</h2>
      </div>
      <p style={{
        margin: 0, fontFamily: "var(--sc-sans)", fontSize: 13.5,
        color: "var(--sc-text-dim)", lineHeight: 1.55, maxWidth: 640,
      }}>{blurb}</p>
    </div>
  );
}

Object.assign(window, { QuantLabBody });
