// SeekingChartis — Module Directory (editorial rebuild)
// Reachable from any menu's "All X surfaces →" footer, from Tools →
// "Full module directory →", and from ⌘K.
//
// Layout per group:
//   • Section header with group letterform, name, count, short blurb
//   • Left column: 2-3 FEATURED cards with inline mini-visualizations
//     (sparkline, distribution, bridge, heatmap pips) hand-picked per group
//   • Right column: compact list of remaining modules (title + route only)

/* global React, MODULES_CATALOG */

const GROUP_META = {
  LFC: {
    label: "Deal lifecycle",
    tint: "#0f5e5a",
    blurb: "From first screen to IC approval. Sourcing, diligence packets, and partner-review decisions.",
    featured: ["analysis", "ic-packet", "red-flags", "thesis-card"],
  },
  ANL: {
    label: "Analytics & models",
    tint: "#6d4b97",
    blurb: "The quant stack. Monte Carlo, EBITDA bridges, Bayesian calibration, causal inference.",
    featured: ["ebitda", "scenario-modeler", "bayesian", "waterfall"],
  },
  PRT: {
    label: "Portfolio ops",
    tint: "#b36a2e",
    blurb: "Live health across every hold. Value-creation tracking, LP digests, cross-portfolio Monte Carlo.",
    featured: ["heatmap", "portfolio-mc", "value-tracker", "hold"],
  },
  MKT: {
    label: "Market intelligence",
    tint: "#2a5d8f",
    blurb: "The corpus. 5,808 hospitals, payer mix, denial trends, sponsor track records, news.",
    featured: ["payer-intel", "rcm-benchmarks", "competitive", "pe-intel-hub"],
  },
  TLS: {
    label: "Tools & admin",
    tint: "#5c6b78",
    blurb: "Command center, data explorer, library, provenance, and platform administration.",
    featured: ["command", "data-explorer", "library", "provenance"],
  },
};

// ===== small visualization primitives used on featured cards =====

function DirSparkline({ values, color = "var(--sc-teal)", height = 34 }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * 100;
    const y = 100 - ((v - min) / range) * 100;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none"
         style={{ width: "100%", height, display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke"/>
      <polyline points={`0,100 ${pts} 100,100`} fill={color} fillOpacity="0.12" stroke="none"/>
    </svg>
  );
}

function DirDistribution({ bins, color = "var(--sc-teal)", height = 34 }) {
  const max = Math.max(...bins);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height }}>
      {bins.map((v, i) => (
        <div key={i} style={{
          flex: 1, height: `${(v / max) * 100}%`,
          background: color, opacity: 0.35 + (v / max) * 0.65,
        }} />
      ))}
    </div>
  );
}

function DirBridgeBars({ steps }) {
  // Tiny EBITDA-bridge: 5-6 ±bars on a baseline
  const max = Math.max(...steps.map(s => Math.abs(s.v)));
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 3, height: 34 }}>
      {steps.map((s, i) => {
        const h = (Math.abs(s.v) / max) * 100;
        const isUp = s.v >= 0;
        return (
          <div key={i} style={{ flex: 1, display: "flex", alignItems: "center", height: "100%" }}>
            <div style={{
              width: "100%",
              height: `${h}%`,
              background: isUp ? "var(--sc-positive)" : "var(--sc-negative)",
              opacity: 0.85,
              alignSelf: isUp ? "flex-start" : "flex-end",
            }}/>
          </div>
        );
      })}
    </div>
  );
}

function DirHeatmapPips({ values, cols = 8, rows = 4 }) {
  // 32 cells, colored by value: green→amber→red
  const cells = values.slice(0, cols * rows);
  const color = (v) => {
    if (v >= 0.7) return "#2d8f5a";
    if (v >= 0.55) return "#5aa37a";
    if (v >= 0.4) return "#d4a13b";
    if (v >= 0.25) return "#c5603a";
    return "#a13b2a";
  };
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${cols}, 1fr)`,
      gap: 2, height: 34,
    }}>
      {cells.map((v, i) => (
        <div key={i} style={{ background: color(v) }}/>
      ))}
    </div>
  );
}

function DirDonut({ pct = 62, color = "var(--sc-teal)", size = 34 }) {
  const r = 16;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" style={{ display: "block" }}>
      <circle cx="20" cy="20" r={r} fill="none" stroke="var(--sc-rule)" strokeWidth="4"/>
      <circle cx="20" cy="20" r={r} fill="none" stroke={color} strokeWidth="4"
              strokeDasharray={`${(pct / 100) * c} ${c}`}
              transform="rotate(-90 20 20)"/>
    </svg>
  );
}

// Map featured module id → what visualization to show and which numbers to pin
const FEATURED_VIZ = {
  // LFC
  "analysis": {
    viz: <DirSparkline values={[52, 48, 55, 61, 58, 66, 72, 68, 74, 81]} />,
    stats: [["Active runs", "12"], ["Median MOIC", "2.41×"], ["P05 IRR", "7.2%"]],
  },
  "ic-packet": {
    viz: <DirDonut pct={78} color="#0f5e5a" />,
    stats: [["Auto-sections", "9"], ["Avg gen time", "14s"], ["Packets ready", "4"]],
  },
  "red-flags": {
    viz: <DirDistribution bins={[3, 2, 5, 7, 4, 2, 1]} color="var(--sc-negative)" />,
    stats: [["Critical open", "3"], ["Deal coverage", "19/24"], ["Median per deal", "4.2"]],
  },
  "thesis-card": {
    viz: <DirSparkline values={[40, 44, 51, 58, 63, 70, 74, 72, 78, 82]} color="#0f5e5a" />,
    stats: [["Thesis grade", "B+"], ["Confidence", "0.71"], ["Sources", "32"]],
  },
  // ANL
  "ebitda": {
    viz: <DirBridgeBars steps={[{v:1},{v:0.6},{v:-0.3},{v:0.8},{v:0.4},{v:-0.2}]} />,
    stats: [["Entry EBITDA", "$14.2M"], ["Y-5 P50", "$26.8M"], ["CAGR", "13.6%"]],
  },
  "scenario-modeler": {
    viz: <DirSparkline values={[2.1, 2.3, 2.0, 2.4, 2.6, 2.5, 2.8, 2.7, 2.9, 3.1]} color="#6d4b97" />,
    stats: [["Scenarios", "14"], ["Median MOIC", "2.6×"], ["Downside IRR", "9.1%"]],
  },
  "bayesian": {
    viz: <DirDistribution bins={[1,2,4,7,10,12,10,7,4,2,1]} color="#6d4b97" />,
    stats: [["Hospitals", "5,808"], ["Shrinkage", "0.42"], ["ELPD", "-612"]],
  },
  "waterfall": {
    viz: <DirBridgeBars steps={[{v:1},{v:0.7},{v:0.5},{v:0.3},{v:0.2}]} />,
    stats: [["Gross MOIC", "2.74×"], ["Net MOIC", "2.31×"], ["Carry split", "20/80"]],
  },
  // PRT
  "heatmap": {
    viz: <DirHeatmapPips values={[
      0.82,0.78,0.72,0.68,0.61,0.55,0.48,0.42,
      0.76,0.71,0.66,0.59,0.52,0.45,0.38,0.31,
      0.69,0.63,0.58,0.51,0.44,0.36,0.29,0.24,
      0.58,0.52,0.46,0.39,0.33,0.27,0.22,0.18,
    ]} />,
    stats: [["Deals green", "14"], ["Watchlist", "7"], ["At risk", "3"]],
  },
  "portfolio-mc": {
    viz: <DirDistribution bins={[1,2,3,5,7,10,9,7,5,3,2,1]} color="#b36a2e" />,
    stats: [["Fund MOIC P50", "2.58×"], ["Paths", "100k"], ["Loss ratio P05", "8%"]],
  },
  "value-tracker": {
    viz: <DirSparkline values={[100, 104, 109, 115, 118, 124, 130, 134, 141, 148]} color="#b36a2e" />,
    stats: [["Initiatives", "42"], ["Bridge Y-5", "+$12.6M"], ["Hit rate", "68%"]],
  },
  "hold": {
    viz: <DirDonut pct={61} color="#b36a2e" />,
    stats: [["Holds", "24"], ["Median age", "2.8y"], ["Exit-ready", "6"]],
  },
  // MKT
  "payer-intel": {
    viz: <DirHeatmapPips values={[
      0.42,0.38,0.35,0.31,0.28,0.24,0.21,0.18,
      0.52,0.48,0.44,0.39,0.34,0.29,0.25,0.22,
      0.67,0.62,0.55,0.48,0.41,0.35,0.30,0.26,
      0.71,0.68,0.61,0.54,0.47,0.40,0.34,0.29,
    ]} />,
    stats: [["Payers tracked", "1,204"], ["Concentration flags", "22"], ["YoY shift", "+3.1%"]],
  },
  "rcm-benchmarks": {
    viz: <DirSparkline values={[48, 46, 49, 52, 51, 55, 58, 56, 59, 61]} color="#2a5d8f" />,
    stats: [["AR days median", "48.2"], ["Denial rate", "11.4%"], ["Cohort n", "655"]],
  },
  "competitive": {
    viz: <DirDistribution bins={[3,5,7,9,8,6,4,2]} color="#2a5d8f" />,
    stats: [["Operators mapped", "312"], ["Adjacency score", "0.62"], ["HHI median", "0.18"]],
  },
  "pe-intel-hub": {
    viz: <DirSparkline values={[2.1, 2.2, 2.5, 2.3, 2.6, 2.4, 2.7, 2.8, 2.6, 2.9]} color="#2a5d8f" />,
    stats: [["Sponsors", "189"], ["Deals indexed", "2,410"], ["Live signals", "34"]],
  },
  // TLS
  "command": {
    viz: <DirSparkline values={[22,18,26,14,20,24,17,12,19,15]} color="#5c6b78" />,
    stats: [["Jobs running", "7"], ["Alerts routed", "118"], ["Uptime 30d", "99.97%"]],
  },
  "data-explorer": {
    viz: <DirDistribution bins={[4, 6, 9, 12, 10, 8, 5, 3]} color="#5c6b78" />,
    stats: [["Tables", "142"], ["Saved views", "38"], ["Exports / wk", "56"]],
  },
  "library": {
    viz: <DirDonut pct={84} color="#5c6b78" />,
    stats: [["Documents", "1,862"], ["Indexed", "1,561"], ["Citations", "3.4k"]],
  },
  "provenance": {
    viz: <DirBridgeBars steps={[{v:1},{v:0.8},{v:0.6},{v:0.4}]} />,
    stats: [["Numbers tracked", "41,288"], ["Sources", "287"], ["Unresolved", "0.4%"]],
  },
};

function DirectoryPage({
  initialFilter = null,
  onHome,
  onSignOut,
  onOpenModule,
  onOpenDirectory,
}) {
  const all = (typeof window !== "undefined" ? window.MODULES_CATALOG : null) || [];
  const [filter, setFilter] = React.useState(initialFilter);
  const [query, setQuery] = React.useState("");

  React.useEffect(() => { setFilter(initialFilter); }, [initialFilter]);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return all.filter(m => {
      if (filter && m.group !== filter) return false;
      if (!q) return true;
      return (
        m.title.toLowerCase().includes(q) ||
        (m.purpose || "").toLowerCase().includes(q) ||
        (m.route || "").toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q)
      );
    });
  }, [all, filter, query]);

  const byGroup = React.useMemo(() => {
    const map = {};
    filtered.forEach(m => { (map[m.group] = map[m.group] || []).push(m); });
    return map;
  }, [filtered]);

  const groupOrder = ["LFC", "ANL", "PRT", "MKT", "TLS"];

  return (
    <div style={{ background: "var(--sc-parchment)", minHeight: "100vh" }}>
      <GlobalNav
        active="directory"
        onHome={onHome}
        onSignOut={onSignOut}
        onOpenModule={onOpenModule}
        onOpenDirectory={onOpenDirectory}
      />

      {/* Title */}
      <section className="sc-container-wide" style={{ padding: "44px 0 20px" }}>
        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 11,
          letterSpacing: "0.18em", textTransform: "uppercase",
          color: "var(--sc-teal-ink)", marginBottom: 12,
        }}>
          Module directory · {all.length} surfaces · 52 API endpoints
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(280px, 1fr)", gap: 40, alignItems: "end" }}>
          <h1 style={{
            fontFamily: "var(--sc-serif)", fontSize: 44, lineHeight: 1.06,
            color: "var(--sc-navy)", margin: 0, fontWeight: 500,
            letterSpacing: "-0.01em",
          }}>
            Every surface in the platform,<br/>
            <span style={{ color: "var(--sc-teal-ink)", fontStyle: "italic" }}>curated and live</span>.
          </h1>
          <p style={{
            fontFamily: "var(--sc-sans)", fontSize: 14.5,
            color: "var(--sc-text-dim)", margin: 0, lineHeight: 1.55,
          }}>
            Each section leads with the surfaces you'll open most — with live readouts from the
            underlying model — then lists the full inventory. Everything here maps 1-to-1 to a
            Python renderer in the RCM-MC repo.
          </p>
        </div>
      </section>

      {/* Controls */}
      <section className="sc-container-wide" style={{ paddingBottom: 12 }}>
        <div style={{
          display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
          borderTop: "1px solid var(--sc-rule)",
          borderBottom: "1px solid var(--sc-rule)",
          padding: "14px 0",
        }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <FilterChip active={!filter} onClick={() => setFilter(null)}>
              All ({all.length})
            </FilterChip>
            {groupOrder.map(g => {
              const count = all.filter(m => m.group === g).length;
              return (
                <FilterChip key={g} active={filter === g} onClick={() => setFilter(g)} tint={GROUP_META[g].tint}>
                  {GROUP_META[g].label} ({count})
                </FilterChip>
              );
            })}
          </div>
          <div style={{ flex: "1 1 220px", minWidth: 220, marginLeft: "auto" }}>
            <input type="text" placeholder="Search title, purpose, route, id…"
                   value={query} onChange={(e) => setQuery(e.target.value)}
                   style={{
                     width: "100%", padding: "9px 12px",
                     border: "1px solid var(--sc-rule)", background: "#fff",
                     fontFamily: "var(--sc-mono)", fontSize: 12,
                     color: "var(--sc-text)", outline: "none",
                   }}/>
          </div>
        </div>
      </section>

      {/* Sections */}
      <section className="sc-container-wide" style={{ paddingBottom: 80 }}>
        {filtered.length === 0 && (
          <div style={{ padding: "40px 0", textAlign: "center",
                        fontFamily: "var(--sc-mono)", fontSize: 12, color: "var(--sc-text-faint)" }}>
            No modules match your search.
          </div>
        )}
        {groupOrder.map(g => {
          const list = byGroup[g];
          if (!list || !list.length) return null;
          return (
            <GroupSection
              key={g}
              groupCode={g}
              groupMeta={GROUP_META[g]}
              modules={list}
              onOpenModule={onOpenModule}
              filterActive={!!filter || !!query.trim()}
            />
          );
        })}
      </section>
    </div>
  );
}

function GroupSection({ groupCode, groupMeta, modules, onOpenModule, filterActive }) {
  // Featured ids picked per group
  const featuredIds = groupMeta.featured || [];
  const inSet = new Set(featuredIds);
  const featured = featuredIds
    .map(id => modules.find(m => m.id === id))
    .filter(Boolean);
  const rest = modules.filter(m => !inSet.has(m.id));

  // If the user has narrowed via filter/search, featured may be empty —
  // in that case just show everything as a dense list (no left rail)
  const showFeatured = featured.length > 0 && !filterActive;

  return (
    <div style={{ marginTop: 44, paddingTop: 16 }}>
      <GroupHeader code={groupCode} meta={groupMeta} total={modules.length} />
      <div style={{
        display: "grid",
        gridTemplateColumns: showFeatured ? "minmax(0, 1.15fr) minmax(0, 1fr)" : "1fr",
        gap: 28,
        marginTop: 18,
      }}>
        {showFeatured && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {featured.map(m => (
              <FeaturedCard key={m.id} mod={m} tint={groupMeta.tint} onClick={() => onOpenModule && onOpenModule(m.id)} />
            ))}
          </div>
        )}
        <div>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10,
            letterSpacing: "0.16em", textTransform: "uppercase",
            color: "var(--sc-text-faint)", marginBottom: 8,
          }}>
            {showFeatured ? `Also in ${groupMeta.label.toLowerCase()}` : `All ${groupMeta.label.toLowerCase()}`}
          </div>
          <div style={{ borderTop: "1px solid var(--sc-rule)" }}>
            {(showFeatured ? rest : modules).map((m, i, arr) => (
              <CompactRow
                key={m.id}
                mod={m}
                tint={groupMeta.tint}
                onClick={() => onOpenModule && onOpenModule(m.id)}
                last={i === arr.length - 1}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function GroupHeader({ code, meta, total }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "auto minmax(0, 1fr) auto",
      gap: 20, alignItems: "center",
      borderBottom: "1px solid var(--sc-rule)",
      padding: "0 0 16px",
    }}>
      {/* Oversize letterform */}
      <div style={{
        fontFamily: "var(--sc-serif)",
        fontSize: 60, lineHeight: 0.9,
        color: meta.tint, letterSpacing: "-0.02em",
        fontWeight: 400, fontStyle: "italic",
        paddingRight: 6,
      }}>
        {code.charAt(0).toLowerCase()}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 10,
          letterSpacing: "0.18em", textTransform: "uppercase",
          color: meta.tint, fontWeight: 700, marginBottom: 4,
        }}>
          {code} · section
        </div>
        <h2 style={{
          fontFamily: "var(--sc-serif)", fontSize: 26, lineHeight: 1.1,
          fontWeight: 500, color: "var(--sc-navy)", margin: 0,
        }}>{meta.label}</h2>
        <p style={{
          margin: "6px 0 0", fontFamily: "var(--sc-sans)",
          fontSize: 13.5, color: "var(--sc-text-dim)", maxWidth: 640, lineHeight: 1.5,
        }}>{meta.blurb}</p>
      </div>
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 11,
        letterSpacing: "0.14em", textTransform: "uppercase",
        color: "var(--sc-text-faint)", whiteSpace: "nowrap",
      }}>
        {total} surface{total !== 1 ? "s" : ""}
      </div>
    </div>
  );
}

function FeaturedCard({ mod, tint, onClick }) {
  const viz = FEATURED_VIZ[mod.id];
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: "flex", flexDirection: "column", textAlign: "left",
        background: "#fff", border: "1px solid var(--sc-rule)",
        borderTop: `3px solid ${tint}`, padding: "16px 16px 14px",
        cursor: "pointer", transition: "box-shadow 120ms, transform 120ms",
        minHeight: 220,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 10px 30px -18px rgba(11,35,65,0.35)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
    >
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 9.5,
        letterSpacing: "0.14em", textTransform: "uppercase",
        color: "var(--sc-text-faint)", marginBottom: 6,
      }}>
        {mod.group}·{(mod.id || "").toUpperCase()} <span style={{ color: tint, marginLeft: 4 }}>· featured</span>
      </div>
      <div style={{
        fontFamily: "var(--sc-serif)", fontSize: 20, fontWeight: 500,
        color: "var(--sc-navy)", lineHeight: 1.2, marginBottom: 4,
      }}>{mod.title}</div>
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 10.5,
        color: tint, marginBottom: 10, letterSpacing: "0.04em",
      }}>{mod.route || "—"}</div>

      {/* Live viz */}
      {viz && (
        <div style={{
          background: "var(--sc-parchment)",
          border: "1px solid var(--sc-rule)",
          padding: "10px 12px", marginBottom: 10,
        }}>
          <div style={{ marginBottom: 8 }}>{viz.viz}</div>
          <div style={{
            display: "grid",
            gridTemplateColumns: `repeat(${viz.stats.length}, 1fr)`,
            gap: 8,
            borderTop: "1px solid var(--sc-rule)", paddingTop: 8,
          }}>
            {viz.stats.map(([lbl, v], i) => (
              <div key={i}>
                <div style={{
                  fontFamily: "var(--sc-mono)", fontSize: 8.5,
                  letterSpacing: "0.12em", textTransform: "uppercase",
                  color: "var(--sc-text-faint)",
                }}>{lbl}</div>
                <div style={{
                  fontFamily: "var(--sc-mono)", fontSize: 13, fontWeight: 600,
                  color: "var(--sc-navy)", marginTop: 2,
                }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{
        fontFamily: "var(--sc-sans)", fontSize: 12.5,
        color: "var(--sc-text-dim)", lineHeight: 1.5,
        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
        overflow: "hidden", marginTop: "auto",
      }}>
        {mod.purpose || ""}
      </div>
    </button>
  );
}

function CompactRow({ mod, tint, onClick, last }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 12, alignItems: "baseline", width: "100%",
        background: "transparent", border: 0,
        borderBottom: last ? "none" : "1px solid var(--sc-rule)",
        padding: "12px 0", textAlign: "left", cursor: "pointer",
        transition: "background 100ms, padding 100ms",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(47,179,173,0.06)"; e.currentTarget.style.paddingLeft = "8px"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.paddingLeft = "0"; }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontFamily: "var(--sc-serif)", fontSize: 15, fontWeight: 500,
          color: "var(--sc-navy)", lineHeight: 1.2,
        }}>{mod.title}</div>
        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 10.5, letterSpacing: "0.04em",
          color: tint, marginTop: 3,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{mod.route || "—"}</div>
      </div>
      <div style={{
        fontFamily: "var(--sc-mono)", fontSize: 9.5,
        letterSpacing: "0.14em", color: "var(--sc-text-faint)",
        whiteSpace: "nowrap",
      }}>{(mod.id || "").toUpperCase()} →</div>
    </button>
  );
}

function FilterChip({ active, onClick, children, tint }) {
  return (
    <button type="button" onClick={onClick}
      style={{
        background: active ? "var(--sc-navy)" : "#fff",
        color: active ? "#fff" : "var(--sc-text)",
        border: `1px solid ${active ? "var(--sc-navy)" : "var(--sc-rule)"}`,
        padding: "6px 12px",
        fontFamily: "var(--sc-mono)", fontSize: 10.5,
        letterSpacing: "0.1em", textTransform: "uppercase",
        fontWeight: 600, cursor: "pointer",
        borderLeft: active && tint ? `3px solid ${tint}` : undefined,
      }}>
      {children}
    </button>
  );
}

Object.assign(window, { DirectoryPage });
