// SeekingChartis — ModulePage
// Generic, catalog-driven page shell. Given a module id from
// MODULES_CATALOG, renders a fully-fleshed, section-rich page
// with a navbar, breadcrumb, overview, layout-appropriate
// panels, and a footer.
//
// The content specialization (tables, bridges, heatmaps,
// wizards, etc.) is driven by module.kind.

/* global React, Wordmark, Breadcrumb, DataPanel, BarRow */

function ModuleNav({ onHome, onSignOut }) {
  return (
    <header style={{ background: "#fff", borderBottom: "1px solid var(--sc-rule)" }}>
      <div className="sc-container-wide" style={{
        display: "flex", alignItems: "center", padding: "18px 0", gap: 24,
      }}>
        <a href="#"
           onClick={(e) => { e.preventDefault(); onHome && onHome(); }}
           style={{ textDecoration: "none" }}>
          <Wordmark />
        </a>
        <div style={{ marginLeft: "auto", display: "flex", gap: 20, alignItems: "center" }}>
          <a href="#"
             onClick={(e) => { e.preventDefault(); onHome && onHome(); }}
             style={{
               fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
               letterSpacing: "0.12em", textTransform: "uppercase",
               color: "var(--sc-text-dim)",
             }}>
            ← Platform home
          </a>
          <a href="#"
             onClick={(e) => { e.preventDefault(); onSignOut && onSignOut(); }}
             style={{
               fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
               letterSpacing: "0.12em", textTransform: "uppercase",
               color: "var(--sc-text-dim)", whiteSpace: "nowrap",
             }}>
            Sign out
          </a>
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

function ModuleHero({ mod }) {
  return (
    <section style={{
      background: "var(--sc-parchment)", padding: "36px 0 30px",
      borderBottom: "1px solid var(--sc-rule)",
    }}>
      <div className="sc-container-wide">
        <div className="sc-eyebrow" style={{ marginBottom: 12 }}>
          {mod.groupName} · {mod.group} · <span style={{ fontFamily: "var(--sc-mono)" }}>{mod.route}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 40, alignItems: "flex-end" }}>
          <div>
            <h1 className="sc-h1" style={{ marginBottom: 10, fontSize: 46, lineHeight: 1.04 }}>{mod.title}</h1>
            <p className="sc-lead" style={{ maxWidth: 640 }}>{mod.tagline}</p>
          </div>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 11,
            color: "var(--sc-text-faint)", letterSpacing: "0.08em",
            textAlign: "right",
          }}>
            <div style={{ marginBottom: 4 }}>{`ID · ${mod.id.toUpperCase()}`}</div>
            <div style={{ marginBottom: 4 }}>{`KIND · ${mod.kind.toUpperCase()}`}</div>
            <div>{`STATUS · LIVE`}</div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Generic "Purpose" strip + auto-rendered Panels block.
function PurposeStrip({ mod }) {
  return (
    <section style={{ background: "#fff", padding: "28px 0 10px" }}>
      <div className="sc-container-wide" style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 48 }}>
        <div>
          <div className="sc-eyebrow" style={{ marginBottom: 10 }}>What this page does</div>
          <p style={{
            fontFamily: "var(--sc-serif)", fontSize: 20, lineHeight: 1.45,
            color: "var(--sc-text)", margin: 0, textWrap: "pretty",
          }}>
            {mod.purpose}
          </p>
        </div>
        <div style={{ border: "1px solid var(--sc-rule)", padding: 18, background: "var(--sc-bone)" }}>
          <div className="sc-eyebrow" style={{ marginBottom: 10 }}>Sources</div>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", fontFamily: "var(--sc-mono)", fontSize: 11.5, color: "var(--sc-text-dim)" }}>
            {(mod.sources || []).map((s, i) => (
              <li key={i} style={{ padding: "5px 0", borderBottom: i < mod.sources.length - 1 ? "1px dashed var(--sc-rule)" : "none" }}>· {s}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

// -------- kind-specific body renderers --------

function PanelsGrid({ panels, columns = 3 }) {
  if (!panels || !panels.length) return null;
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(auto-fit, minmax(280px, 1fr))`,
      gap: 14,
    }}>
      {panels.map((p, i) => (
        <div key={i} style={{ border: "1px solid var(--sc-rule)", background: "#fff" }}>
          <header style={{
            background: "var(--sc-navy)", color: "var(--sc-on-navy)",
            padding: "8px 12px",
            fontFamily: "var(--sc-mono)", fontSize: 10,
            letterSpacing: "0.14em", textTransform: "uppercase",
            display: "flex", justifyContent: "space-between",
          }}>
            <span style={{ color: "var(--sc-teal-2)", fontWeight: 700 }}>P{String(i + 1).padStart(2, "0")}</span>
            <span>{p.title}</span>
          </header>
          <div style={{ padding: 14, fontSize: 13, lineHeight: 1.5, color: "var(--sc-text)" }}>
            {p.body}
          </div>
        </div>
      ))}
    </div>
  );
}

// tiny deterministic pseudo-random (seeded by string)
function _seed(s) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0; return h; }
function _rnd(seed, i) { const x = Math.sin(seed + i * 9301) * 10000; return x - Math.floor(x); }

function TableFaux({ mod, rows = 10 }) {
  const cols = mod.columns || [];
  if (!cols.length) return null;
  const seed = _seed(mod.id);
  const data = Array.from({ length: rows }, (_, r) =>
    cols.map((c, ci) => {
      const low = c.toLowerCase();
      const v = _rnd(seed, r * 7 + ci);
      if (ci === 0) {
        const names = ["Cedar Health", "Magnolia Partners", "Harbor Valley", "Piedmont West", "Stonefield", "Blue Ridge", "Summit Regional", "Elkhorn Medical", "Meridian Health", "Fairview Partners"];
        return names[r % names.length];
      }
      if (/state|region/.test(low)) return ["TX","OH","NC","FL","PA","GA","MI","IN","WA","CO"][r % 10];
      if (/stage/.test(low)) return ["LOI","IC","Diligence","Hold","Closed"][r % 5];
      if (/verdict/.test(low)) return ["PASS","WATCH","PASS","FAIL","WATCH"][r % 5];
      if (/%|pct|rate|commercial/.test(low)) return (10 + v * 40).toFixed(1) + "%";
      if (/moic/.test(low)) return (1.4 + v * 2.0).toFixed(2) + "×";
      if (/irr/.test(low)) return (8 + v * 24).toFixed(1) + "%";
      if (/beds/.test(low)) return Math.floor(60 + v * 440);
      if (/score|composite/.test(low)) return Math.floor(45 + v * 50);
      if (/ev|entry|current/.test(low)) return "$" + (120 + Math.floor(v * 800)) + "M";
      if (/days/.test(low)) return (38 + v * 30).toFixed(1);
      if (/top signal/.test(low)) return ["Denial outlier", "AR drift", "Payer mix"][r % 3];
      if (/hospital/.test(low)) return ["Cedar Health","Magnolia Partners","Harbor Valley","Piedmont West","Stonefield","Blue Ridge","Summit","Elkhorn","Meridian","Fairview"][r % 10];
      if (/ccn/.test(low)) return String(300000 + Math.floor(v * 9999)).padStart(6,"0");
      if (/sponsor/.test(low)) return ["Artemis","Forge","Keel","Lantern","Ridgeline"][r % 5];
      if (/segment/.test(low)) return ["Community","Academic","Critical Access","LTAC","ASC","Behavioral","Physician Group","Home Health"][r % 8];
      return (1 + v * 99).toFixed(1);
    })
  );
  return (
    <div style={{ border: "1px solid var(--sc-rule)", background: "#fff", overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "var(--sc-mono)" }}>
        <thead>
          <tr style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy)" }}>
            {cols.map(c => (
              <th key={c} style={{
                padding: "10px 12px", textAlign: "left",
                fontFamily: "var(--sc-sans)", fontSize: 10, fontWeight: 600,
                letterSpacing: "0.12em", textTransform: "uppercase",
                color: "var(--sc-teal-2)",
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: "1px solid var(--sc-rule)", background: ri % 2 ? "var(--sc-bone)" : "#fff" }}>
              {row.map((v, ci) => (
                <td key={ci} style={{
                  padding: "8px 12px",
                  color: ci === 0 ? "var(--sc-navy)" : "var(--sc-text)",
                  fontWeight: ci === 0 ? 600 : 400,
                  fontFamily: ci === 0 ? "var(--sc-serif)" : "var(--sc-mono)",
                  fontSize: ci === 0 ? 13 : 12,
                }}>
                  {typeof v === "string" && /PASS|WATCH|FAIL/.test(v)
                    ? <span style={{
                        padding: "2px 8px", fontSize: 10, fontWeight: 700,
                        letterSpacing: "0.1em",
                        background: v === "PASS" ? "#0f5d54" : v === "FAIL" ? "#8c2a2e" : "#7a5a16",
                        color: "#fff",
                      }}>{v}</span>
                    : v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PresetsGrid({ mod }) {
  if (!mod.presets) return null;
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12,
    }}>
      {mod.presets.map((p, i) => (
        <div key={i} style={{ border: "1px solid var(--sc-rule)", background: "#fff", padding: "14px 16px" }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 9,
            color: "var(--sc-teal-ink)", letterSpacing: "0.14em", textTransform: "uppercase",
            marginBottom: 8,
          }}>Preset · {String(i + 1).padStart(2, "0")}</div>
          <div style={{
            fontFamily: "var(--sc-serif)", fontSize: 16, fontWeight: 600,
            color: "var(--sc-navy)", marginBottom: p.desc ? 6 : 0,
          }}>{p.name}</div>
          {p.desc && <div style={{ fontSize: 12, color: "var(--sc-text-dim)", lineHeight: 1.45 }}>{p.desc}</div>}
        </div>
      ))}
    </div>
  );
}

function WizardSteps({ mod }) {
  if (!mod.steps) return null;
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${mod.steps.length}, 1fr)`, gap: 0, border: "1px solid var(--sc-rule)" }}>
      {mod.steps.map((s, i) => (
        <div key={i} style={{
          padding: "18px 20px",
          background: i === 0 ? "var(--sc-navy)" : "#fff",
          color: i === 0 ? "var(--sc-on-navy)" : "var(--sc-text)",
          borderRight: i < mod.steps.length - 1 ? "1px solid var(--sc-rule)" : "none",
        }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
            color: i === 0 ? "var(--sc-teal-2)" : "var(--sc-text-faint)",
            marginBottom: 8,
          }}>STEP {String(s.n).padStart(2, "0")}</div>
          <div style={{
            fontFamily: "var(--sc-serif)", fontSize: 20, fontWeight: 600,
            color: i === 0 ? "var(--sc-on-navy)" : "var(--sc-navy)",
            marginBottom: 6,
          }}>{s.name}</div>
          <div style={{ fontSize: 12, lineHeight: 1.45, color: i === 0 ? "var(--sc-on-navy-faint)" : "var(--sc-text-dim)" }}>{s.body}</div>
        </div>
      ))}
    </div>
  );
}

function HeatmapFaux({ mod }) {
  const cols = (mod.columns || []).slice(1); // drop the leading "Deal" label col
  const deals = ["Cedar", "Magnolia", "Harbor Valley", "Piedmont", "Stonefield", "Blue Ridge", "Summit", "Elkhorn"];
  const seed = _seed(mod.id);
  const cell = (r, c) => {
    const v = _rnd(seed, r * 13 + c * 7);
    const band = v < 0.33 ? "bad" : v > 0.66 ? "good" : "neutral";
    const colors = { bad: "#8c2a2e", neutral: "#7a5a16", good: "#0f5d54" };
    return { v, band, color: colors[band] };
  };
  return (
    <div style={{ border: "1px solid var(--sc-rule)", background: "#fff", overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "var(--sc-mono)" }}>
        <thead>
          <tr style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy)" }}>
            <th style={{ padding: "10px 12px", textAlign: "left", fontFamily: "var(--sc-sans)", fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--sc-teal-2)" }}>Deal</th>
            {cols.map(c => (
              <th key={c} style={{ padding: "10px 8px", textAlign: "center", fontFamily: "var(--sc-sans)", fontSize: 9, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--sc-teal-2)" }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {deals.map((d, ri) => (
            <tr key={d} style={{ borderBottom: "1px solid var(--sc-rule)" }}>
              <td style={{ padding: "10px 12px", fontFamily: "var(--sc-serif)", fontSize: 13, fontWeight: 600, color: "var(--sc-navy)" }}>{d}</td>
              {cols.map((c, ci) => {
                const k = cell(ri, ci);
                return (
                  <td key={c} style={{ padding: 2, textAlign: "center" }}>
                    <div style={{
                      height: 34, background: k.color, color: "#fff",
                      display: "grid", placeItems: "center",
                      fontFamily: "var(--sc-mono)", fontSize: 11, fontWeight: 600,
                    }}>
                      {(k.v * 100).toFixed(0)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BridgeFaux({ mod }) {
  const levers = mod.levers || [
    "Denial reduction",
    "Days-in-AR compression",
    "AR>90d cleanup",
    "Net collection rate",
    "Clean claim rate",
    "Cost-to-collect",
    "Payer mix shift",
  ];
  const seed = _seed(mod.id);
  let running = 42; // starting EBITDA in $M
  const bars = [{ label: "Current EBITDA", value: running, delta: 0, kind: "base" }];
  for (const l of levers) {
    const d = 1 + _rnd(seed, l.length) * 4;
    running += d;
    bars.push({ label: l, value: running, delta: d, kind: "lever" });
  }
  bars.push({ label: "Run-rate EBITDA", value: running, delta: 0, kind: "total" });
  const max = running * 1.1;
  return (
    <div style={{ border: "1px solid var(--sc-rule)", background: "#fff", padding: 20 }}>
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
        color: "var(--sc-text-faint)", textTransform: "uppercase", marginBottom: 14,
      }}>7-Lever EBITDA waterfall · $M</div>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-end", height: 240 }}>
        {bars.map((b, i) => {
          const h = (b.value / max) * 220;
          const color = b.kind === "base" ? "var(--sc-navy)"
            : b.kind === "total" ? "var(--sc-teal-ink)"
            : "var(--sc-teal)";
          return (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <div style={{
                fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-navy)",
                fontWeight: 600,
              }}>{b.value.toFixed(1)}</div>
              <div style={{ width: "100%", maxWidth: 64, height: h, background: color, position: "relative" }}>
                {b.delta > 0 && (
                  <span style={{
                    position: "absolute", top: -18, left: "50%", transform: "translateX(-50%)",
                    fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-teal-ink)",
                  }}>+{b.delta.toFixed(1)}</span>
                )}
              </div>
              <div style={{
                fontSize: 10, color: "var(--sc-text-dim)", textAlign: "center", lineHeight: 1.2,
                maxWidth: 84, height: 30,
              }}>{b.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LongFormSections({ mod }) {
  if (!mod.sections) return null;
  return (
    <div style={{ border: "1px solid var(--sc-rule)", background: "#fff" }}>
      {mod.sections.map((s, i) => (
        <div key={i} style={{
          padding: "18px 20px",
          borderBottom: i < mod.sections.length - 1 ? "1px solid var(--sc-rule)" : "none",
          display: "grid", gridTemplateColumns: "60px 1fr", gap: 16, alignItems: "baseline",
        }}>
          <div style={{ fontFamily: "var(--sc-mono)", fontSize: 10, color: "var(--sc-text-faint)", letterSpacing: "0.12em" }}>§{String(i + 1).padStart(2, "0")}</div>
          <div>
            <div style={{ fontFamily: "var(--sc-serif)", fontSize: 20, color: "var(--sc-navy)", fontWeight: 600, marginBottom: 4 }}>{s}</div>
            <div style={{ fontSize: 12, color: "var(--sc-text-faint)", fontFamily: "var(--sc-mono)", letterSpacing: "0.06em" }}>Auto-generated · fact-checked · edit in place</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function VerdictBanner({ mod }) {
  return (
    <div style={{
      border: "1px solid var(--sc-rule)",
      background: "linear-gradient(90deg, var(--sc-navy), var(--sc-navy-2))",
      color: "var(--sc-on-navy)",
      padding: "22px 28px",
      display: "grid", gridTemplateColumns: "1fr auto", gap: 20, alignItems: "center",
    }}>
      <div>
        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
          color: "var(--sc-teal-2)", textTransform: "uppercase", marginBottom: 8,
        }}>IC Recommendation · Cedar Health Partners</div>
        <div style={{
          fontFamily: "var(--sc-serif)", fontSize: 34, fontWeight: 600,
          color: "#fff", marginBottom: 8, letterSpacing: "-0.01em",
        }}>PROCEED WITH CAVEATS</div>
        <div style={{ fontFamily: "var(--sc-serif)", fontSize: 15, fontStyle: "italic", color: "var(--sc-on-navy-faint)", maxWidth: 640 }}>
          Composite 73 · denial profile is an outlier but within the Southeast community cohort. Two reasonableness bands flag STRETCH on commercial rate assumptions. Clean closeable.
        </div>
      </div>
      <div style={{ textAlign: "right", fontFamily: "var(--sc-mono)", fontSize: 11, color: "var(--sc-teal-2)" }}>
        <div>SCORE · 73 / 100</div>
        <div>REGIME · EMERGING · VOLATILE</div>
        <div>ARCHETYPE · BUY-AND-BUILD</div>
      </div>
    </div>
  );
}

function RedFlagList({ mod }) {
  const flags = [
    { sev: "CRITICAL", label: "Denial spike Q3", detail: "Commercial initial-denial rose from 7.2% → 11.8% vs peer 8.1%. No documented reason in data room." },
    { sev: "HIGH", label: "AR > 90d drift", detail: "Aged AR > 90d climbed 4.1pp trailing 2 quarters — in the top decile for drift." },
    { sev: "HIGH", label: "Commercial rate assumption STRETCH", detail: "Thesis assumes +3.8% commercial uplift; benchmark shows -0.4% median renegotiation in subsector." },
    { sev: "MEDIUM", label: "Case-mix index compression", detail: "CMI down 0.03 YoY; consistent with service-line exit not documented in CIM." },
    { sev: "MEDIUM", label: "Clean-claim below P25", detail: "91.4% vs segment P25 of 93.1% — fixable with RCM ops investment." },
    { sev: "LOW", label: "Management retention risk", detail: "CFO departure post-close noted in Q&A; no named successor." },
  ];
  const color = (s) => ({ CRITICAL: "#8c2a2e", HIGH: "#c44a30", MEDIUM: "#7a5a16", LOW: "var(--sc-text-dim)" }[s]);
  return (
    <div style={{ border: "1px solid var(--sc-rule)", background: "#fff" }}>
      {flags.map((f, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "110px 1fr", gap: 16,
          padding: "16px 20px", borderBottom: i < flags.length - 1 ? "1px solid var(--sc-rule)" : "none",
          alignItems: "baseline",
        }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
            background: color(f.sev), color: "#fff", padding: "4px 8px", textAlign: "center", fontWeight: 700,
          }}>{f.sev}</div>
          <div>
            <div style={{ fontFamily: "var(--sc-serif)", fontSize: 17, fontWeight: 600, color: "var(--sc-navy)", marginBottom: 4 }}>{f.label}</div>
            <div style={{ fontSize: 13, color: "var(--sc-text-dim)", lineHeight: 1.5 }}>{f.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function KpiBar({ kpis }) {
  return (
    <div style={{
      display: "grid", gridTemplateColumns: `repeat(${kpis.length}, 1fr)`, gap: 0,
      border: "1px solid var(--sc-rule)", background: "#fff",
    }}>
      {kpis.map((k, i) => (
        <div key={i} style={{
          padding: "18px 20px",
          borderRight: i < kpis.length - 1 ? "1px solid var(--sc-rule)" : "none",
        }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
            color: "var(--sc-text-faint)", textTransform: "uppercase", marginBottom: 8,
          }}>{k.label}</div>
          <div style={{
            fontFamily: "var(--sc-serif)", fontSize: 30, fontWeight: 600,
            color: "var(--sc-navy)", letterSpacing: "-0.01em", lineHeight: 1,
            marginBottom: 4,
          }}>{k.value}</div>
          <div style={{ fontSize: 11, color: k.delta && k.delta.startsWith("+") ? "var(--sc-teal-ink)" : "var(--sc-text-faint)" }}>{k.delta || k.sub}</div>
        </div>
      ))}
    </div>
  );
}

function ProvenancePalette({ mod }) {
  if (!mod.sources_palette) return null;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
      {mod.sources_palette.map((s, i) => (
        <div key={i} style={{ border: "1px solid var(--sc-rule)", background: "#fff", padding: "14px 16px" }}>
          <div style={{
            display: "inline-block", padding: "3px 10px", fontSize: 10, fontWeight: 700,
            fontFamily: "var(--sc-mono)", letterSpacing: "0.12em",
            background: s.trust === "high" ? "var(--sc-navy)" : "#7a5a16",
            color: "#fff", marginBottom: 10,
          }}>{s.label}</div>
          <div style={{ fontFamily: "var(--sc-serif)", fontSize: 15, fontWeight: 500, color: "var(--sc-navy)", marginBottom: 4 }}>{s.desc}</div>
          <div style={{ fontSize: 11, color: "var(--sc-text-faint)" }}>Trust · {s.trust}</div>
        </div>
      ))}
    </div>
  );
}

function RelatedPages({ mod, onNavigate }) {
  const sameGroup = (window.MODULES_CATALOG || [])
    .filter(m => m.group === mod.group && m.id !== mod.id)
    .slice(0, 6);
  if (!sameGroup.length) return null;
  return (
    <section style={{ background: "var(--sc-parchment)", borderTop: "1px solid var(--sc-rule)", padding: "48px 0" }}>
      <div className="sc-container-wide">
        <div className="sc-eyebrow" style={{ marginBottom: 18 }}>Related · {mod.groupName}</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
          {sameGroup.map(m => (
            <a key={m.id} href="#"
               onClick={(e) => { e.preventDefault(); onNavigate && onNavigate(m.id); }}
               style={{
                 border: "1px solid var(--sc-rule)", background: "#fff",
                 padding: "14px 16px", textDecoration: "none", display: "block",
               }}
               onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--sc-navy)"}
               onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--sc-rule)"}>
              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 9, color: "var(--sc-teal-ink)", letterSpacing: "0.14em", marginBottom: 6 }}>{m.route}</div>
              <div style={{ fontFamily: "var(--sc-serif)", fontSize: 17, fontWeight: 600, color: "var(--sc-navy)", marginBottom: 4 }}>{m.title}</div>
              <div style={{ fontSize: 12, color: "var(--sc-text-dim)", lineHeight: 1.4 }}>{m.tagline}</div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

// -------- Page body by kind --------

function ModuleBody({ mod, onOpenAnalysis }) {
  // Rich dedicated bodies for specific kinds — short-circuit the generic layout.
  if (mod.kind === "quant" && typeof QuantLabBody !== "undefined") {
    return <QuantLabBody />;
  }
  const kpisFor = (mod) => {
    const k = (l, v, d) => ({ label: l, value: v, delta: d });
    switch (mod.kind) {
      case "screener":
      case "filter-list":
        return [k("Universe", "5,808"), k("Matches", "184", "+12 vs last run"), k("Avg. composite", "64"), k("Verdicts (PASS)", "47")];
      case "deal-dashboard":
      case "deal-verdict":
      case "deal-score":
      case "deal-classifier":
      case "whitespace":
      case "stress":
      case "market":
        return [k("Composite", "73"), k("Stage", "Diligence"), k("Hold yr", "1.2"), k("Health", "B+", "trending up")];
      case "dashboard":
      case "portfolio-rollup":
        return [k("Deals", "12"), k("Fund MOIC", "1.8×"), k("Fund IRR", "21.3%"), k("On-plan", "9 / 12")];
      case "heatmap":
        return [k("Deals", "8"), k("Metrics", "8"), k("Cells", "64"), k("Red cells", "11")];
      case "monte-carlo":
        return [k("Paths", "10,000"), k("P50 MOIC", "1.92×"), k("P5 MOIC", "1.10×"), k("P95 MOIC", "3.24×")];
      case "bridge":
        return [k("Levers", "7"), k("Δ EBITDA", "+$18.4M", "+38% vs today"), k("IRR p50", "22.6%"), k("MOIC p50", "2.14×")];
      case "backtest":
        return [k("Corpus deals", "655"), k("Matched", "481"), k("RMSE MOIC", "0.34"), k("Prediction CI", "89%")];
      case "bayesian":
        return [k("Metrics calibrated", "14"), k("Data score", "B"), k("Shrinkage", "0.42"), k("Credible 95%", "All positive")];
      default:
        return [k("Sources", (mod.sources || []).length.toString()), k("Panels", (mod.panels || []).length.toString() || "—"), k("Status", "Live"), k("Version", "v0.6.0")];
    }
  };
  const kpis = kpisFor(mod);

  return (
    <section style={{ padding: "28px 0 56px" }}>
      <div className="sc-container-wide" style={{ display: "flex", flexDirection: "column", gap: 24 }}>

        <KpiBar kpis={kpis} />

        {/* Kind-specific hero body */}
        {mod.kind === "workbench" && (
          <>
            <VerdictBanner mod={mod} />
            <div style={{ display: "flex", gap: 12, alignItems: "center", padding: "14px 16px", background: "var(--sc-bone)", border: "1px solid var(--sc-rule)" }}>
              <span style={{ fontFamily: "var(--sc-serif)", fontSize: 14, fontStyle: "italic", color: "var(--sc-text)" }}>
                This route has a dedicated workbench surface.
              </span>
              <a href="#" onClick={(e) => { e.preventDefault(); onOpenAnalysis && onOpenAnalysis(); }}
                 style={{
                   marginLeft: "auto", background: "var(--sc-teal-ink)", color: "#fff",
                   padding: "10px 18px", fontSize: 11, fontWeight: 600,
                   letterSpacing: "0.12em", textTransform: "uppercase",
                   textDecoration: "none",
                 }}>
                Open 6-tab workbench →
              </a>
            </div>
          </>
        )}

        {mod.kind === "deal-verdict" && <VerdictBanner mod={mod} />}
        {mod.kind === "red-flags" && <RedFlagList mod={mod} />}
        {mod.kind === "bridge" && <BridgeFaux mod={mod} />}
        {mod.kind === "heatmap" && <HeatmapFaux mod={mod} />}

        {(mod.kind === "wizard" && mod.steps) && <WizardSteps mod={mod} />}

        {/* Panels block */}
        {mod.panels && mod.panels.length > 0 && (
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 14 }}>Panels on this page</div>
            <PanelsGrid panels={mod.panels} />
          </div>
        )}

        {/* Table-style surfaces */}
        {(mod.kind === "screener" || mod.kind === "filter-list" ||
          mod.kind === "portfolio-rollup" || mod.kind === "hold" ||
          mod.kind === "sponsor" || mod.kind === "benchmarks" ||
          mod.kind === "compare") && (
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 14 }}>Result set</div>
            <TableFaux mod={mod} rows={mod.kind === "sponsor" ? 10 : 9} />
          </div>
        )}

        {/* Presets */}
        {mod.presets && (
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 14 }}>Presets</div>
            <PresetsGrid mod={mod} />
          </div>
        )}

        {/* Long-form sections */}
        {mod.sections && (
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 14 }}>Sections</div>
            <LongFormSections mod={mod} />
          </div>
        )}

        {/* Provenance palette */}
        {mod.sources_palette && (
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 14 }}>Source palette</div>
            <ProvenancePalette mod={mod} />
          </div>
        )}
      </div>
    </section>
  );
}

function ModuleFooter() {
  return (
    <footer style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy)", padding: "24px 0" }}>
      <div className="sc-container-wide" style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--sc-mono)", fontSize: 11, color: "var(--sc-on-navy-faint)", letterSpacing: "0.08em" }}>
        <span>SeekingChartis · rcm_mc v0.6.0</span>
        <span>Healthcare PE Diligence Platform</span>
      </div>
    </footer>
  );
}

// Deal-scoped module ids trigger the deal-context sub-bar.
const DEAL_SCOPED_IDS = new Set([
  "deal-dashboard", "analysis", "ic-packet", "red-flags", "white-space",
  "stress", "investability", "archetype", "market-structure",
  "partner-review", "ic-memo", "thesis-card", "deal-timeline",
  "deal-quick-view", "predictive-screener", "diligence-questions",
]);

function ModulePage({ moduleId, onHome, onSignOut, onNavigate, onOpenAnalysis, onOpenDirectory }) {
  const mod = (window.MODULES_CATALOG || []).find(m => m.id === moduleId);
  if (!mod) {
    return (
      <div style={{ padding: 40 }}>
        <p>Module <code>{moduleId}</code> not found.</p>
        <a href="#" onClick={(e) => { e.preventDefault(); onHome && onHome(); }}>← Home</a>
      </div>
    );
  }

  // Show the deal-context bar iff this module is scoped to a single deal.
  const isDealScoped = DEAL_SCOPED_IDS.has(mod.id);
  const dealContext = isDealScoped
    ? { dealName: "Magnolia Health Partners", active: mod.id }
    : null;

  return (
    <div style={{ background: "var(--sc-parchment)", minHeight: "100vh" }}>
      <GlobalNav
        active={mod.id}
        dealContext={dealContext}
        onHome={onHome}
        onSignOut={onSignOut}
        onOpenModule={(id) => {
          if (id === "analysis" && onOpenAnalysis) { onOpenAnalysis(); return; }
          onNavigate && onNavigate(id);
        }}
        onOpenDirectory={onOpenDirectory}
        onOpenDealTab={(id) => {
          if (id === "analysis" && onOpenAnalysis) { onOpenAnalysis(); return; }
          onNavigate && onNavigate(id);
        }}
      />
      <Breadcrumb trail={["Home", mod.groupName, mod.title]} />
      <ModuleHero mod={mod} />
      <PurposeStrip mod={mod} />
      <ModuleBody mod={mod} onOpenAnalysis={onOpenAnalysis} />
      <RelatedPages mod={mod} onNavigate={onNavigate} />
      <ModuleFooter />
    </div>
  );
}

Object.assign(window, { ModulePage });
