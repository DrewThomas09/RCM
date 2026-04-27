// SeekingChartis — shared components (React + Babel)
// Chrome, nav, hero blocks, photo placeholders, data panel primitives

/* global React */

const { useState, useEffect, useRef } = React;

// -------- Brand mark — original SeekingChartis logo --------
// Silhouette-in-circle style (professional corporate mark), original geometry:
// an upward-pointing triangulated divider rule, referencing charting / discovery.
function SCMark({ size = 36, inverted = false, onSolidBg = false }) {
  // On solid navy surfaces (e.g. top bar in marketing): white ring, white mark.
  // On light surfaces (home, login): navy ring, navy mark.
  const stroke = inverted ? "#ffffff" : "var(--sc-navy)";
  const mark = inverted ? "#ffffff" : "var(--sc-navy)";
  const fillBg = onSolidBg ? "transparent" : (inverted ? "var(--sc-navy)" : "#ffffff");
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-label="SeekingChartis" style={{ flexShrink: 0 }}>
      {/* Outer ring */}
      <circle cx="24" cy="24" r="22" fill={fillBg} stroke={stroke} strokeWidth="1.5" />
      {/* Abstract mark: three ascending chart bars converging under a triangular roof
          — a chart's summit. Original composition. */}
      {/* Roof / summit triangle */}
      <path d="M24 11 L33 22 L15 22 Z" fill="none" stroke={mark} strokeWidth="1.6" strokeLinejoin="miter" />
      {/* Base rule */}
      <line x1="12" y1="35" x2="36" y2="35" stroke={mark} strokeWidth="1.6" />
      {/* Three ascending bars */}
      <rect x="15"   y="28" width="4" height="7" fill={mark} />
      <rect x="22"   y="25" width="4" height="10" fill={mark} />
      <rect x="29"   y="22" width="4" height="13" fill={mark} />
    </svg>
  );
}

function Wordmark({ inverted = false, size = "md" }) {
  const c = inverted ? "#ffffff" : "var(--sc-navy)";
  const markSize = size === "lg" ? 40 : size === "sm" ? 26 : 32;
  const fontSize = size === "lg" ? 26 : size === "sm" ? 17 : 21;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <SCMark inverted={inverted} size={markSize} onSolidBg={inverted} />
      <div style={{
        fontFamily: "var(--sc-serif)",
        fontWeight: 600,
        fontSize,
        letterSpacing: "-0.005em",
        color: c,
        lineHeight: 1,
      }}>
        Seeking<span style={{ fontStyle: "italic", fontWeight: 500 }}>Chartis</span>
      </div>
    </div>
  );
}

// -------- Top bar (marketing) --------
function MarketingNav({ onOpenPlatform }) {
  const items = [
    { k: "platform", label: "Platform" },
    { k: "corpus", label: "Corpus" },
    { k: "about", label: "About" },
  ];
  return (
    <header style={{
      background: "var(--sc-navy)",
      borderBottom: "1px solid var(--sc-navy-3)",
      position: "relative",
    }}>
      <div className="sc-container-wide" style={{
        display: "flex",
        alignItems: "center",
        padding: "20px 0",
        gap: 32,
      }}>
        <Wordmark inverted />
        <nav style={{ display: "flex", gap: 28, marginLeft: 48 }}>
          {items.map(it => (
            <a key={it.k} href="#" style={{
              fontFamily: "var(--sc-sans)",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#ffffff",
              opacity: 0.9,
              padding: "6px 0",
            }}>
              {it.label}
            </a>
          ))}
        </nav>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <a
            href="#login"
            onClick={(e) => { e.preventDefault(); onOpenPlatform && onOpenPlatform(); }}
            style={{
              fontFamily: "var(--sc-sans)",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "#ffffff",
              padding: "6px 0",
              opacity: 0.9,
            }}
          >
            Sign in
          </a>
          <a
            href="#login"
            onClick={(e) => { e.preventDefault(); onOpenPlatform && onOpenPlatform(); }}
            className="sc-btn"
            style={{
              background: "var(--sc-teal)",
              color: "var(--sc-ink)",
              borderColor: "var(--sc-teal)",
              fontSize: 11,
            }}
          >
            Open Platform
            <svg className="arrow" viewBox="0 0 12 12"><path d="M2 10 L10 2 M4 2 L10 2 L10 8" stroke="currentColor" strokeWidth="1.5" fill="none" /></svg>
          </a>
        </div>
      </div>
    </header>
  );
}

// -------- Breadcrumb --------
function Breadcrumb({ trail }) {
  return (
    <div style={{
      background: "#eef1f5",
      borderBottom: "1px solid var(--sc-rule)",
    }}>
      <div className="sc-container-wide" style={{ padding: "14px 0", display: "flex", gap: 10, alignItems: "center", fontSize: 12 }}>
        {trail.map((t, i) => (
          <React.Fragment key={i}>
            <a href="#" style={{
              color: i === trail.length - 1 ? "var(--sc-text)" : "var(--sc-teal-ink)",
              fontWeight: i === trail.length - 1 ? 600 : 500,
              letterSpacing: "0.02em",
            }}>{t}</a>
            {i < trail.length - 1 && (
              <svg width="8" height="8" viewBox="0 0 10 10"><path d="M3 1 L7 5 L3 9" stroke="var(--sc-text-faint)" strokeWidth="1.5" fill="none"/></svg>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// -------- Hero imagery placeholders — 3 styles --------
// "Photo" style: striped SVG placeholder with a caption
function PhotoPlaceholder({ label = "Advisors in session", ratio = "4 / 3" }) {
  return (
    <div className="sc-frame" style={{ aspectRatio: ratio, position: "relative" }}>
      <svg width="100%" height="100%" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice"
        style={{
          width: "100%", height: "100%",
          clipPath: "polygon(8% 0%, 100% 0%, 100% 92%, 92% 100%, 0% 100%, 0% 8%)",
        }}>
        <defs>
          <pattern id="stripes" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(135)">
            <rect width="8" height="8" fill="#1d3c69"/>
            <rect width="4" height="8" fill="#22436f"/>
          </pattern>
          <radialGradient id="ph-vig" cx="45%" cy="55%" r="75%">
            <stop offset="0%" stopColor="#2a5689" stopOpacity="0.9"/>
            <stop offset="100%" stopColor="#0b2341" stopOpacity="1"/>
          </radialGradient>
        </defs>
        <rect width="400" height="300" fill="url(#stripes)"/>
        <rect width="400" height="300" fill="url(#ph-vig)"/>
        {/* A couple of abstract silhouette blobs to suggest "people at a table" */}
        <ellipse cx="130" cy="200" rx="55" ry="70" fill="#0b2341" opacity="0.6"/>
        <ellipse cx="220" cy="185" rx="48" ry="62" fill="#0b2341" opacity="0.55"/>
        <ellipse cx="305" cy="195" rx="50" ry="65" fill="#0b2341" opacity="0.55"/>
        <rect x="0" y="245" width="400" height="55" fill="#061626" opacity="0.5"/>
      </svg>
      <div style={{
        position: "absolute",
        bottom: 12, left: 12,
        fontFamily: "var(--sc-mono)",
        fontSize: 10,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: "#c2e4e2",
        background: "rgba(6,22,38,0.6)",
        padding: "4px 8px",
        borderLeft: "2px solid var(--sc-teal)",
      }}>
        [ Photo placeholder — {label} ]
      </div>
    </div>
  );
}

// "Data" hero — an abstract market map / network
function DataHero() {
  // Deterministic scattered nodes
  const nodes = [
    [0.12, 0.22], [0.28, 0.15], [0.44, 0.35], [0.58, 0.22], [0.72, 0.48], [0.86, 0.32],
    [0.18, 0.55], [0.32, 0.68], [0.48, 0.58], [0.62, 0.72], [0.78, 0.65], [0.88, 0.78],
    [0.22, 0.85], [0.38, 0.88], [0.54, 0.82], [0.68, 0.92],
  ];
  const edges = [
    [0, 2], [0, 1], [1, 3], [2, 4], [3, 5], [4, 5], [2, 6], [4, 7], [6, 7], [7, 8],
    [8, 9], [9, 10], [10, 11], [8, 12], [12, 13], [13, 14], [14, 15], [9, 14], [6, 8],
  ];
  return (
    <div className="sc-frame" style={{ aspectRatio: "4 / 3", background: "var(--sc-ink)", position: "relative" }}>
      <svg width="100%" height="100%" viewBox="0 0 400 300" preserveAspectRatio="none"
        style={{
          width: "100%", height: "100%",
          clipPath: "polygon(8% 0%, 100% 0%, 100% 92%, 92% 100%, 0% 100%, 0% 8%)",
        }}>
        <defs>
          <linearGradient id="dh-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#132e53"/>
            <stop offset="100%" stopColor="#061626"/>
          </linearGradient>
          <pattern id="dh-grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1d3c69" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="400" height="300" fill="url(#dh-bg)"/>
        <rect width="400" height="300" fill="url(#dh-grid)" opacity="0.6"/>
        {/* Edges */}
        {edges.map(([a, b], i) => {
          const [x1, y1] = nodes[a], [x2, y2] = nodes[b];
          return <line key={i} x1={x1 * 400} y1={y1 * 300} x2={x2 * 400} y2={y2 * 300}
            stroke="var(--sc-teal)" strokeOpacity="0.4" strokeWidth="1"/>;
        })}
        {/* Nodes */}
        {nodes.map(([x, y], i) => {
          const r = i % 4 === 0 ? 5 : i % 3 === 0 ? 4 : 3;
          const active = i === 4 || i === 8;
          return (
            <g key={i}>
              {active && <circle cx={x*400} cy={y*300} r={r+6} fill="var(--sc-teal)" opacity="0.18"/>}
              <circle cx={x * 400} cy={y * 300} r={r}
                fill={active ? "var(--sc-teal)" : "#6fb3ae"}
                opacity={active ? 1 : 0.75}/>
            </g>
          );
        })}
        {/* Floating label */}
        <g transform="translate(230, 130)">
          <rect x="0" y="0" width="130" height="46" fill="#061626" stroke="var(--sc-teal)" strokeWidth="1"/>
          <text x="10" y="18" fontFamily="var(--sc-mono)" fontSize="9" fill="#66c8c3" letterSpacing="2">MSA • PHOENIX</text>
          <text x="10" y="36" fontFamily="var(--sc-mono)" fontSize="12" fill="#e9eef5" fontWeight="600">142 hospitals · 6 signals</text>
        </g>
      </svg>
      <div style={{
        position: "absolute",
        bottom: 12, left: 12,
        fontFamily: "var(--sc-mono)",
        fontSize: 10,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
        color: "#c2e4e2",
        background: "rgba(6,22,38,0.6)",
        padding: "4px 8px",
        borderLeft: "2px solid var(--sc-teal)",
      }}>
        [ Corpus map — 6,024 hospitals ]
      </div>
    </div>
  );
}

// "Abstract" hero — geometric composition
function AbstractHero() {
  return (
    <div className="sc-frame" style={{ aspectRatio: "4 / 3", background: "var(--sc-navy)", position: "relative" }}>
      <svg width="100%" height="100%" viewBox="0 0 400 300" preserveAspectRatio="none"
        style={{
          width: "100%", height: "100%",
          clipPath: "polygon(8% 0%, 100% 0%, 100% 92%, 92% 100%, 0% 100%, 0% 8%)",
        }}>
        <rect width="400" height="300" fill="var(--sc-navy)"/>
        {/* Concentric arcs (compass motif) */}
        {[60, 100, 140, 180, 220].map((r, i) => (
          <circle key={r} cx="280" cy="200" r={r} fill="none"
            stroke="var(--sc-teal)" strokeOpacity={0.15 + i * 0.08} strokeWidth={i === 4 ? 2 : 1}/>
        ))}
        {/* Bar chart motif lower-left */}
        {[
          [40, 60], [70, 90], [100, 40], [130, 110], [160, 75]
        ].map(([x, h], i) => (
          <rect key={i} x={x} y={260 - h} width="20" height={h}
            fill={i === 2 ? "var(--sc-teal)" : "#2a4d7a"}/>
        ))}
        {/* Radial arrow */}
        <path d="M280 200 L360 120" stroke="var(--sc-teal)" strokeWidth="2"/>
        <circle cx="280" cy="200" r="5" fill="var(--sc-teal)"/>
        <path d="M360 120 L352 115 L355 128 Z" fill="var(--sc-teal)"/>
      </svg>
    </div>
  );
}

// -------- Bloomberg-dense data panel (for hybrid surfaces) --------
function DataPanel({ code, title, children, style = {} }) {
  return (
    <section style={{
      background: "#fff",
      border: "1px solid var(--sc-rule)",
      ...style,
    }}>
      <header style={{
        background: "var(--sc-navy)",
        color: "var(--sc-on-navy)",
        padding: "9px 14px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "nowrap",
        minWidth: 0,
        fontFamily: "var(--sc-mono)",
        fontSize: 10.5,
        letterSpacing: "0.14em",
        textTransform: "uppercase",
      }}>
        <span style={{ color: "var(--sc-teal-2)", fontWeight: 700, flex: "0 0 auto" }}>{code}</span>
        <span style={{ color: "var(--sc-on-navy)", flex: "1 1 auto", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</span>
        <span style={{ color: "var(--sc-on-navy-faint)", fontSize: 9, flex: "0 0 auto" }}>LIVE</span>
      </header>
      <div style={{ padding: 14 }}>{children}</div>
    </section>
  );
}

// A tiny bar row
function BarRow({ label, value, pct, color = "var(--sc-teal)", fmt = "n", unit = "" }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "120px 40px 1fr 56px",
      gap: 10,
      alignItems: "center",
      padding: "5px 0",
      fontSize: 12,
      fontFamily: "var(--sc-mono)",
    }}>
      <span style={{ color: "var(--sc-text-dim)" }}>{label}</span>
      <span style={{ textAlign: "right", color: "var(--sc-text)", fontWeight: 600 }}>{value}{unit}</span>
      <span style={{ height: 5, background: "var(--sc-bone)", position: "relative" }}>
        <span style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${Math.max(2, pct)}%`, background: color,
        }}/>
      </span>
      <span style={{ textAlign: "right", color: "var(--sc-text-faint)", fontSize: 11 }}>{pct.toFixed(1)}%</span>
    </div>
  );
}

Object.assign(window, {
  SCMark, Wordmark, MarketingNav, Breadcrumb,
  PhotoPlaceholder, DataHero, AbstractHero,
  DataPanel, BarRow,
});
