// SeekingChartis Command Center — atoms (editorial)
const { useState, useMemo } = React;

function Sparkline({ data, color = "var(--teal)", fill = false }) {
  const w = 100, h = 22, pad = 2;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (data.length - 1);
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return [x, y];
  });
  const path = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{width:"100%",height:"100%",display:"block"}}>
      <path d={path} stroke={color} strokeWidth="1.25" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function CovenantPill({ status }) {
  if (status === "SAFE") return <span className="pill green"><span className="dot"/>Safe</span>;
  if (status === "WATCH") return <span className="pill amber"><span className="dot"/>Watch</span>;
  if (status === "TRIP") return <span className="pill red"><span className="dot"/>Trip</span>;
  return <span className="pill muted">—</span>;
}

function StagePill({ stage }) {
  const map = { Hold: "blue", IOI: "amber", LOI: "amber", Sourced: "muted", SPA: "blue", Closed: "green", Exit: "green", Screened: "muted" };
  return <span className={"pill " + (map[stage] || "muted")}>{stage}</span>;
}

function NumberMaybe({ v, format, tone }) {
  if (v === null || v === undefined) return <span style={{color:"var(--faint)"}}>—</span>;
  let s = v;
  if (format === "moic") s = v.toFixed(2) + "x";
  if (format === "pct")  s = (v * 100).toFixed(1) + "%";
  if (format === "ev")   s = "$" + v + "M";
  if (format === "drift") s = (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
  const color = tone === "green" ? "var(--green)" : tone === "amber" ? "var(--amber)" : tone === "red" ? "var(--red)" : "inherit";
  return <span style={{color, fontWeight: tone ? 600 : 500}}>{s}</span>;
}

window.SC = { Sparkline, CovenantPill, StagePill, NumberMaybe };
