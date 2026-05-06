// SeekingChartis — Marketing landing page (professional, minimal)

/* global React */

function MarketingHero({ imagery, onOpenPlatform }) {
  const ImgComp = imagery === "data" ? DataHero : imagery === "abstract" ? AbstractHero : PhotoPlaceholder;
  return (
    <section style={{ background: "var(--sc-parchment)", position: "relative" }}>
      <div className="sc-container-wide" style={{
        display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 80,
        padding: "72px 0 96px", alignItems: "center",
      }}>
        <div>
          <div className="sc-eyebrow" style={{ marginBottom: 28 }}>Healthcare PE Diligence Platform</div>
          <h1 className="sc-display" style={{ marginBottom: 32 }}>
            Purpose-built<br/>to codify partner<br/>judgment at scale.
          </h1>
          <p className="sc-lead" style={{ marginBottom: 36 }}>
            SeekingChartis is the diligence and portfolio-operations platform for
            healthcare-focused private equity. From screening to exit, 278
            partner-reflex modules run on 6,024 HCRIS hospitals and 2,878
            regression tests.
          </p>
          <div>
            <a href="#login" onClick={(e) => { e.preventDefault(); onOpenPlatform(); }} className="sc-btn sc-btn-primary">
              Open Platform
              <svg className="arrow" viewBox="0 0 12 12"><path d="M2 10 L10 2 M4 2 L10 2 L10 8" stroke="currentColor" strokeWidth="1.5" fill="none" /></svg>
            </a>
          </div>
        </div>
        <div style={{ paddingRight: 20, paddingTop: 20 }}>
          <ImgComp />
        </div>
      </div>
    </section>
  );
}

function CapabilitiesGrid() {
  const items = [
    { num: "01", title: "Monte Carlo v2", body: "Correlated portfolio simulation with named-scenario compare. 10,000 draws per deal, calibrated against stored priors (IDR, FWR, DAR) at /api/calibration/priors." },
    { num: "02", title: "PE-math layer", body: "Bridge, MOIC, IRR, covenant headroom on every draw. EBITDA Bridge page (42k-line module) and waterfall / portfolio_bridge_page render from a single DealAnalysisPacket." },
    { num: "03", title: "Health + completeness", body: "Health score 0-100 with component breakdown. Profile completeness graded A/B/C/D against the 38-metric RCM registry. Live at /api/deals/<id>/health and /completeness." },
    { num: "04", title: "AI-augmented memos", body: "IC memos with per-section fact-checking against the packet. Document QA and multi-turn chat. Graceful template fallback when no LLM key is configured." },
  ];
  return (
    <section style={{ background: "var(--sc-parchment)", padding: "96px 0" }}>
      <div className="sc-container-wide">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 80, marginBottom: 56 }}>
          <div>
            <div className="sc-eyebrow" style={{ marginBottom: 20 }}>What we do</div>
            <h2 className="sc-h1">Four engines, one platform.</h2>
          </div>
          <p className="sc-lead" style={{ paddingTop: 40 }}>
            SeekingChartis / RCM-MC compresses the least-leveraged hours of
            healthcare PE diligence. 52 API endpoints, 56 methods, 241 source
            files, 2,883 passing tests, one SQLite file.
          </p>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
          gap: 0, borderTop: "1px solid var(--sc-rule-2)",
        }}>
          {items.map((it, i) => (
            <div key={i} style={{
              padding: "32px 28px 32px 0",
              borderRight: i < items.length - 1 ? "1px solid var(--sc-rule)" : "none",
              paddingLeft: i === 0 ? 0 : 28,
            }}>
              <div style={{
                fontFamily: "var(--sc-mono)", fontSize: 11,
                color: "var(--sc-teal-ink)", letterSpacing: "0.16em",
                marginBottom: 24,
              }}>— {it.num}</div>
              <h3 className="sc-h2" style={{ marginBottom: 14, fontSize: 22 }}>{it.title}</h3>
              <p className="sc-body" style={{ color: "var(--sc-text-dim)", fontSize: 14 }}>{it.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ModulesSection() {
  const stages = [
    { k: "Screen", desc: "Paste hospital names, ranked verdicts.", count: "GET /screen" },
    { k: "Source", desc: "Thesis-driven origination, 6K+ HCRIS.", count: "GET /source" },
    { k: "Diligence", desc: "5-step wizard, CCN lookup to upload.", count: "GET /new-deal" },
    { k: "Analyze", desc: "7-tab Bloomberg workbench.", count: "GET /analysis/<id>" },
    { k: "IC Prep", desc: "Checklist, memo, packet ZIP.", count: "GET /api/deals/<id>/checklist" },
    { k: "Hold", desc: "Notes, deadlines, variance, alerts.", count: "GET /deal/<id>" },
    { k: "Exit", desc: "Exit modeling + multiple decomp.", count: "GET /exit" },
  ];
  return (
    <section style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy)", padding: "96px 0" }}>
      <div className="sc-container-wide">
        <div style={{ marginBottom: 56 }}>
          <div className="sc-eyebrow on-navy" style={{ marginBottom: 20 }}>Platform modules</div>
          <h2 className="sc-h1" style={{ color: "var(--sc-on-navy)", maxWidth: "18ch" }}>
            Every stage of the deal lifecycle.
          </h2>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: `repeat(${stages.length}, 1fr)`,
          position: "relative", paddingTop: 24,
        }}>
          <div style={{
            position: "absolute", top: 32, left: "4%", right: "4%",
            height: 1, background: "var(--sc-navy-3)",
          }}/>
          {stages.map((s, i) => (
            <div key={s.k} style={{ padding: "0 12px", position: "relative" }}>
              <div style={{
                width: 14, height: 14, borderRadius: "50%",
                background: i === 3 ? "var(--sc-teal)" : "var(--sc-navy)",
                border: `2px solid var(--sc-teal)`,
                margin: "0 auto 24px", position: "relative", zIndex: 1,
              }}/>
              <div style={{
                fontFamily: "var(--sc-mono)", fontSize: 10,
                color: "var(--sc-teal-2)", letterSpacing: "0.14em",
                textAlign: "center", marginBottom: 10,
              }}>0{i+1}</div>
              <h3 style={{
                fontFamily: "var(--sc-serif)", fontSize: 22, fontWeight: 500,
                color: "var(--sc-on-navy)", textAlign: "center", marginBottom: 12,
              }}>{s.k}</h3>
              <p style={{
                fontSize: 13, color: "var(--sc-on-navy-dim)",
                textAlign: "center", lineHeight: 1.5, marginBottom: 12,
              }}>{s.desc}</p>
              <div style={{
                textAlign: "center", fontFamily: "var(--sc-mono)", fontSize: 10,
                color: "var(--sc-teal-2)", letterSpacing: "0.1em",
              }}>{s.count.toUpperCase()}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CorpusStats() {
  const stats = [
    { n: "52", label: "API endpoints · 56 methods", sub: "OpenAPI at /api/openapi.json · Swagger /api/docs" },
    { n: "241", label: "Source files · 74 UI pages", sub: "rcm_mc/ui/ covers every surface, one shell()" },
    { n: "2,883", label: "Tests passing", sub: "225 test files · Python 3.10+ · zero runtime deps beyond numpy, pandas" },
    { n: "78,678", label: "Lines · one .db file", sub: "SQLite WAL · stdlib http.server · no Flask, Docker, Redis" },
  ];
  return (
    <section style={{ background: "var(--sc-bone)", padding: "80px 0", borderTop: "1px solid var(--sc-rule)", borderBottom: "1px solid var(--sc-rule)" }}>
      <div className="sc-container-wide" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 40 }}>
        {stats.map((s, i) => (
          <div key={i} style={{ borderTop: "2px solid var(--sc-navy)", paddingTop: 24 }}>
            <div style={{
              fontFamily: "var(--sc-serif)", fontSize: 64, fontWeight: 400,
              color: "var(--sc-navy)", lineHeight: 1, letterSpacing: "-0.02em",
              marginBottom: 16,
            }}>{s.n}</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: "var(--sc-navy)", marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontSize: 13, color: "var(--sc-text-dim)" }}>{s.sub}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TeamSection() {
  return (
    <section style={{ background: "var(--sc-parchment)", padding: "96px 0" }}>
      <div className="sc-container-wide">
        <div style={{ marginBottom: 48 }}>
          <div className="sc-eyebrow" style={{ marginBottom: 20 }}>The team</div>
          <h2 className="sc-h1">Built by an incoming Chartis intern.</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 64, alignItems: "center" }}>
          <div style={{ maxWidth: 340 }}>
            <div style={{
              aspectRatio: "3 / 4",
              position: "relative",
              background: "var(--sc-navy)",
              clipPath: "polygon(6% 0%, 100% 0%, 100% 94%, 94% 100%, 0% 100%, 0% 6%)",
              boxShadow: "18px 18px 0 -2px var(--sc-teal)",
            }}>
              <img
                src="assets/andrew-portrait.jpeg"
                alt="Andrew Thomas"
                style={{
                  width: "100%", height: "100%", objectFit: "cover",
                  display: "block", filter: "saturate(0.95) contrast(1.02)",
                }}
              />
              <div style={{
                position: "absolute", bottom: 10, left: 10,
                fontFamily: "var(--sc-mono)", fontSize: 9,
                letterSpacing: "0.16em", color: "#e6f5f3",
                textTransform: "uppercase",
                background: "rgba(6,22,38,0.7)", padding: "4px 8px",
                borderLeft: "2px solid var(--sc-teal)",
              }}>Paris · 2024</div>
            </div>
          </div>
          <div>
            <div style={{ fontFamily: "var(--sc-serif)", fontSize: 36, fontWeight: 400, color: "var(--sc-navy)", marginBottom: 8, letterSpacing: "-0.01em" }}>
              Andrew Thomas
            </div>
            <div style={{
              fontFamily: "var(--sc-mono)", fontSize: 11,
              letterSpacing: "0.14em", textTransform: "uppercase",
              color: "var(--sc-teal-ink)", marginBottom: 28,
            }}>Founder · Incoming Chartis Intern</div>

            <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "10px 24px", fontSize: 15, color: "var(--sc-text)" }}>
              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sc-text-faint)", paddingTop: 3 }}>Institution</div>
              <div>The University of Chicago</div>

              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sc-text-faint)", paddingTop: 3 }}>Year</div>
              <div>Junior</div>

              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sc-text-faint)", paddingTop: 3 }}>Concentrations</div>
              <div>Economics · Astrophysics · Statistics</div>

              <div style={{ fontFamily: "var(--sc-mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--sc-text-faint)", paddingTop: 3 }}>Next</div>
              <div>Incoming Intern at Chartis</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ContactCTA({ onOpenPlatform }) {
  return (
    <section style={{
      background: "var(--sc-ink)", color: "var(--sc-on-navy)", padding: "96px 0",
      position: "relative", overflow: "hidden",
    }}>
      <svg style={{ position: "absolute", right: -120, top: -120, opacity: 0.1 }} width="600" height="600" viewBox="0 0 100 100">
        {[20,30,40,50].map(r => <circle key={r} cx="50" cy="50" r={r} fill="none" stroke="var(--sc-teal)" strokeWidth="0.3"/>)}
      </svg>
      <div className="sc-container-wide" style={{
        display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 80, alignItems: "center", position: "relative",
      }}>
        <div>
          <div className="sc-eyebrow on-navy" style={{ marginBottom: 20 }}>Contact</div>
          <h2 className="sc-display on-navy" style={{ fontSize: "clamp(36px, 4.2vw, 58px)", marginBottom: 28 }}>
            Open the platform.
          </h2>
          <p className="sc-lead" style={{ color: "var(--sc-on-navy-dim)", maxWidth: "50ch", marginBottom: 36 }}>
            Healthcare PE diligence, codified partner judgment, and the full
            corpus — one login away.
          </p>
          <a href="#login" onClick={(e) => { e.preventDefault(); onOpenPlatform(); }} className="sc-btn" style={{
            background: "var(--sc-teal)", color: "var(--sc-ink)", borderColor: "var(--sc-teal)",
          }}>
            Open Platform
            <svg className="arrow" viewBox="0 0 12 12"><path d="M2 10 L10 2 M4 2 L10 2 L10 8" stroke="currentColor" strokeWidth="1.5" fill="none" /></svg>
          </a>
        </div>
        <div style={{ fontFamily: "var(--sc-mono)", fontSize: 13, lineHeight: 2, color: "var(--sc-on-navy-dim)" }}>
          <div><span style={{ color: "var(--sc-teal-2)" }}>Chicago</span> — The University of Chicago</div>
          <div style={{ marginTop: 20 }}>andrew@seekingchartis.com</div>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer style={{ background: "var(--sc-navy)", color: "var(--sc-on-navy-dim)", padding: "40px 0 28px" }}>
      <div className="sc-container-wide" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: "var(--sc-mono)", fontSize: 11, color: "var(--sc-on-navy-faint)" }}>
        <Wordmark inverted />
        <div>© 2026 SeekingChartis — Andrew Thomas</div>
      </div>
    </footer>
  );
}

function MarketingPage({ imagery, onOpenPlatform }) {
  return (
    <div>
      <MarketingNav onOpenPlatform={onOpenPlatform} />
      <Breadcrumb trail={["Home", "Healthcare PE Platform"]} />
      <MarketingHero imagery={imagery} onOpenPlatform={onOpenPlatform} />
      <CapabilitiesGrid />
      <ModulesSection />
      <CorpusStats />
      <TeamSection />
      <ContactCTA onOpenPlatform={onOpenPlatform} />
      <SiteFooter />
    </div>
  );
}

Object.assign(window, { MarketingPage, SiteFooter });
