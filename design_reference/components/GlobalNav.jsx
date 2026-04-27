// SeekingChartis — Global navigation (compact dropdowns)
// Used on every signed-in surface: Home, Module pages, Analysis, Directory.
// Five top-level items, each opens a short menu (6–10 links).
// When a deal is open, caller can pass `dealContext` to swap in deal-scoped tabs.

/* global React, MODULES_CATALOG */

// ------- Curated menu structure (not every module — just the right 6-9 per menu) -------
const NAV_MENUS = [
  {
    id: "deals",
    label: "Deals",
    items: [
      { id: "screen",        caption: "Screener — discover targets" },
      { id: "source",        caption: "Source — ingested deals" },
      { id: "new-deal",      caption: "New deal — start diligence" },
      { id: "deal-dashboard",caption: "Deal dashboard" },
      { id: "pipeline",      caption: "Pipeline — funnel & stages", fallback: "source" },
      { id: "predictive-screener", caption: "Predictive screener — ML sourcing" },
      { id: "thesis-card",   caption: "Thesis card — 30-sec answer" },
      { id: "compare",       caption: "Compare — side-by-side" },
    ],
    footer: { label: "All deal surfaces →", filter: "LFC" },
  },
  {
    id: "analysis",
    label: "Analysis",
    items: [
      { id: "analysis",      caption: "Analysis workbench" },
      { id: "ebitda",        caption: "EBITDA bridge" },
      { id: "scenario-modeler", caption: "Scenario modeler" },
      { id: "ml-insights",   caption: "ML insights" },
      { id: "bayesian",      caption: "Bayesian calibration" },
      { id: "quant-lab",     caption: "Quant lab" },
      { id: "model-validation", caption: "Model validation" },
      { id: "waterfall",     caption: "Returns waterfall" },
    ],
    footer: { label: "All analytics →", filter: "ANL" },
  },
  {
    id: "portfolio",
    label: "Portfolio",
    items: [
      { id: "portfolio-overview", caption: "Portfolio overview" },
      { id: "heatmap",       caption: "Heatmap — health by deal" },
      { id: "hold",          caption: "Hold dashboard" },
      { id: "value-tracker", caption: "Value-creation tracker" },
      { id: "portfolio-mc",  caption: "Portfolio Monte Carlo" },
      { id: "portfolio-bridge", caption: "Portfolio bridge" },
      { id: "playbook",      caption: "Value-creation playbook" },
      { id: "lp-update",     caption: "LP digest" },
    ],
    footer: { label: "All portfolio surfaces →", filter: "PRT" },
  },
  {
    id: "market",
    label: "Market",
    items: [
      { id: "market-data",   caption: "Market data — national hospitals" },
      { id: "competitive",   caption: "Competitive intelligence" },
      { id: "payer-intel",   caption: "Payer intelligence" },
      { id: "rcm-benchmarks",caption: "RCM benchmarks" },
      { id: "hospital-profile", caption: "Hospital profile" },
      { id: "pe-intel-hub",  caption: "PE intelligence hub" },
      { id: "news",          caption: "News feed" },
      { id: "conference",    caption: "Conference roadmap" },
    ],
    footer: { label: "All market intel →", filter: "MKT" },
  },
  {
    id: "tools",
    label: "Tools",
    items: [
      { id: "command",       caption: "Command center" },
      { id: "data-explorer", caption: "Data explorer" },
      { id: "library",       caption: "Library" },
      { id: "provenance",    caption: "Provenance" },
      { id: "methodology",   caption: "Methodology" },
      { id: "quick-import",  caption: "Quick import" },
      { id: "team",          caption: "Team" },
      { id: "settings",      caption: "Settings" },
    ],
    footer: { label: "Full module directory →", directory: true },
  },
];

// Find the real module by id (or fall back gracefully).
function __resolveModule(id, fallback) {
  const all = (typeof window !== "undefined" ? window.MODULES_CATALOG : null) || [];
  return all.find(m => m.id === id) || (fallback ? all.find(m => m.id === fallback) : null);
}

// ------- The main component -------
function GlobalNav({
  active,                   // "home" | "directory" | moduleId
  dealContext = null,       // { dealName, active: "overview"|"workbench"|"ic"|... } | null
  onHome,
  onSignOut,
  onOpenModule,
  onOpenDirectory,
  onOpenDealTab,
  user = { initials: "AT", name: "Andrew Thomas" },
}) {
  const [openMenu, setOpenMenu] = React.useState(null);
  const wrapperRef = React.useRef(null);

  // Close on outside click / escape
  React.useEffect(() => {
    function onDoc(e) {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target)) setOpenMenu(null);
    }
    function onKey(e) { if (e.key === "Escape") setOpenMenu(null); }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  function handleItem(itemId, fallback) {
    setOpenMenu(null);
    const mod = __resolveModule(itemId, fallback);
    if (mod && onOpenModule) onOpenModule(mod.id);
  }

  return (
    <header ref={wrapperRef} style={{
      background: "#fff",
      borderBottom: "1px solid var(--sc-rule)",
      position: "relative",
      zIndex: 40,
    }}>
      <div className="sc-container-wide" style={{
        display: "flex", alignItems: "center", padding: "14px 0", gap: 28,
      }}>
        {/* Wordmark (click → home) */}
        <a href="#home" onClick={(e) => { e.preventDefault(); onHome && onHome(); }}
           style={{ textDecoration: "none", flex: "0 0 auto" }}>
          <Wordmark />
        </a>

        {/* Menus */}
        <nav style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {NAV_MENUS.map(menu => {
            const isOpen = openMenu === menu.id;
            const isActive = isOpen ||
              (active && menu.items.some(i => i.id === active));
            return (
              <div key={menu.id} style={{ position: "relative" }}>
                <button
                  type="button"
                  onClick={() => setOpenMenu(isOpen ? null : menu.id)}
                  onMouseEnter={() => { if (openMenu) setOpenMenu(menu.id); }}
                  style={{
                    background: "transparent",
                    border: 0,
                    padding: "10px 14px",
                    fontFamily: "var(--sc-sans)",
                    fontSize: 12.5,
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: isActive ? "var(--sc-navy)" : "var(--sc-text-dim)",
                    cursor: "pointer",
                    borderBottom: `2px solid ${isActive ? "var(--sc-teal)" : "transparent"}`,
                    marginBottom: -1,
                  }}
                >
                  {menu.label}
                  <span style={{
                    display: "inline-block", marginLeft: 6, fontSize: 9,
                    transform: isOpen ? "rotate(180deg)" : "none",
                    transition: "transform 140ms",
                  }}>▾</span>
                </button>

                {isOpen && (
                  <MenuDropdown
                    menu={menu}
                    onItem={handleItem}
                    onFooter={() => {
                      setOpenMenu(null);
                      if (menu.footer && menu.footer.directory) {
                        onOpenDirectory && onOpenDirectory();
                      } else if (menu.footer && menu.footer.filter) {
                        onOpenDirectory && onOpenDirectory(menu.footer.filter);
                      }
                    }}
                  />
                )}
              </div>
            );
          })}
        </nav>

        {/* Right cluster: search + account */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center" }}>
          <div className="sc-search-chip" style={{
            display: "flex", alignItems: "center", gap: 8, flexWrap: "nowrap",
            padding: "7px 11px", border: "1px solid var(--sc-rule)",
            flex: "1 1 auto", minWidth: 0, maxWidth: 260,
            color: "var(--sc-text-faint)", overflow: "hidden",
          }}>
            <svg width="13" height="13" viewBox="0 0 16 16" style={{ flex: "0 0 auto" }}>
              <circle cx="7" cy="7" r="5" stroke="currentColor" fill="none" strokeWidth="1.5"/>
              <path d="M11 11 L14 14" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span style={{ fontFamily: "var(--sc-mono)", fontSize: 11.5, letterSpacing: "0.04em", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: "1 1 auto" }}>
              Search deals, modules…
            </span>
            <span style={{ fontFamily: "var(--sc-mono)", fontSize: 9.5, color: "var(--sc-text-faint)", flex: "0 0 auto" }}>⌘K</span>
          </div>

          <a href="#signout"
             onClick={(e) => { e.preventDefault(); onSignOut && onSignOut(); }}
             style={{
               fontFamily: "var(--sc-sans)", fontSize: 10.5, fontWeight: 600,
               letterSpacing: "0.12em", textTransform: "uppercase",
               color: "var(--sc-text-dim)", whiteSpace: "nowrap", textDecoration: "none",
             }}>
            Sign out
          </a>
          <div title={user.name} style={{
            width: 32, height: 32, borderRadius: "50%",
            background: "var(--sc-navy)", color: "#fff",
            display: "grid", placeItems: "center",
            fontFamily: "var(--sc-serif)", fontSize: 12, fontWeight: 600,
          }}>{user.initials}</div>
        </div>
      </div>

      {/* Deal-context sub-nav (when a deal is open) */}
      {dealContext && (
        <DealContextBar deal={dealContext} onOpenDealTab={onOpenDealTab} />
      )}
    </header>
  );
}

// ------- The dropdown itself -------
function MenuDropdown({ menu, onItem, onFooter }) {
  return (
    <div style={{
      position: "absolute",
      top: "calc(100% + 1px)",
      left: 0,
      width: 320,
      background: "#fff",
      border: "1px solid var(--sc-rule)",
      borderTop: "2px solid var(--sc-teal)",
      boxShadow: "0 14px 40px -18px rgba(11,35,65,0.22)",
      padding: "12px 0 8px",
      zIndex: 50,
    }}>
      <div style={{
        padding: "2px 18px 10px",
        fontFamily: "var(--sc-mono)",
        fontSize: 9.5,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        color: "var(--sc-text-faint)",
      }}>
        {menu.label} · {menu.items.length} surfaces
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {menu.items.map(item => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onItem(item.id, item.fallback)}
              style={{
                width: "100%",
                background: "transparent",
                border: 0,
                textAlign: "left",
                padding: "9px 18px",
                fontFamily: "var(--sc-sans)",
                fontSize: 13,
                color: "var(--sc-text)",
                cursor: "pointer",
                display: "flex",
                alignItems: "baseline",
                gap: 10,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "var(--sc-bone)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
            >
              <span>{item.caption}</span>
            </button>
          </li>
        ))}
      </ul>
      {menu.footer && (
        <>
          <hr className="sc-rule" style={{ margin: "8px 18px" }} />
          <button
            type="button"
            onClick={onFooter}
            style={{
              width: "calc(100% - 36px)",
              margin: "0 18px 4px",
              background: "transparent",
              border: 0,
              textAlign: "left",
              padding: "6px 0",
              fontFamily: "var(--sc-mono)",
              fontSize: 10.5,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--sc-teal-ink)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {menu.footer.label}
          </button>
        </>
      )}
    </div>
  );
}

// ------- Deal-context sub-bar -------
// When a deal is open, a second row of tabs scoped to that deal.
const DEAL_TABS = [
  { id: "deal-dashboard", label: "Overview" },
  { id: "analysis",       label: "Workbench" },
  { id: "ic-packet",      label: "IC Packet" },
  { id: "red-flags",      label: "Red Flags" },
  { id: "white-space",    label: "White Space" },
  { id: "stress",         label: "Stress" },
  { id: "investability",  label: "Exit Readiness" },
  { id: "deal-timeline",  label: "Timeline" },
];

function DealContextBar({ deal, onOpenDealTab }) {
  const active = deal.active || "deal-dashboard";
  return (
    <div style={{
      background: "var(--sc-ink)",
      color: "#fff",
      borderTop: "1px solid var(--sc-navy-2)",
    }}>
      <div className="sc-container-wide" style={{
        display: "flex", alignItems: "center", padding: "0 0", gap: 2,
        overflowX: "auto",
      }}>
        <div style={{
          padding: "10px 18px 10px 0",
          fontFamily: "var(--sc-mono)",
          fontSize: 10,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--sc-teal-2)",
          whiteSpace: "nowrap",
          borderRight: "1px solid var(--sc-navy-2)",
          marginRight: 8,
        }}>
          <span style={{ color: "var(--sc-on-navy-faint)" }}>Deal · </span>
          <span style={{ color: "#fff", fontWeight: 600 }}>{deal.dealName}</span>
        </div>
        {DEAL_TABS.map(t => {
          const isActive = active === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onOpenDealTab && onOpenDealTab(t.id)}
              style={{
                background: "transparent",
                border: 0,
                padding: "10px 14px",
                fontFamily: "var(--sc-sans)",
                fontSize: 11.5,
                fontWeight: 600,
                letterSpacing: "0.09em",
                textTransform: "uppercase",
                color: isActive ? "#fff" : "var(--sc-on-navy-faint)",
                cursor: "pointer",
                borderBottom: `2px solid ${isActive ? "var(--sc-teal)" : "transparent"}`,
                whiteSpace: "nowrap",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

Object.assign(window, { GlobalNav, NAV_MENUS, DEAL_TABS });
