// SeekingChartis — Login page

/* global React */

function LoginPage({ onLogin, onBack }) {
  const [email, setEmail] = React.useState("andrew@seekingchartis.com");
  const [password, setPassword] = React.useState("••••••••••••");
  const [submitting, setSubmitting] = React.useState(false);

  const submit = (e) => {
    e.preventDefault();
    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      onLogin && onLogin();
    }, 450);
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "grid",
      gridTemplateColumns: "1.05fr 1fr",
      background: "var(--sc-parchment)",
    }}>
      {/* Left panel — form */}
      <div style={{
        padding: "36px 72px 36px",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <a
            href="#"
            onClick={(e) => { e.preventDefault(); onBack && onBack(); }}
            style={{ textDecoration: "none" }}
          >
            <Wordmark />
          </a>
          <a
            href="#"
            onClick={(e) => { e.preventDefault(); onBack && onBack(); }}
            style={{
              fontFamily: "var(--sc-sans)", fontSize: 11, fontWeight: 600,
              letterSpacing: "0.14em", textTransform: "uppercase",
              color: "var(--sc-text-dim)",
            }}
          >
            ← Back to site
          </a>
        </div>

        <div style={{ flex: 1, display: "grid", placeItems: "center" }}>
          <div style={{ width: "100%", maxWidth: 440 }}>
            <div className="sc-eyebrow" style={{ marginBottom: 20 }}>Sign in · Partner access</div>
            <h1 className="sc-h1" style={{ marginBottom: 14, fontSize: 46 }}>
              Open the platform.
            </h1>
            <p style={{
              fontSize: 15, color: "var(--sc-text-dim)", marginBottom: 36, lineHeight: 1.55,
            }}>
              Continue to SeekingChartis — your deal corpus, partner-reflex modules, and
              portfolio health are a moment away.
            </p>

            <form onSubmit={submit}>
              <label style={{
                display: "block", marginBottom: 18,
              }}>
                <span style={{
                  fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
                  textTransform: "uppercase", color: "var(--sc-text-faint)", display: "block", marginBottom: 8,
                }}>Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: "100%", padding: "12px 14px",
                    border: "1px solid var(--sc-rule)",
                    fontFamily: "var(--sc-sans)", fontSize: 15,
                    color: "var(--sc-text)", background: "#ffffff",
                    outline: "none",
                  }}
                  onFocus={(e) => e.target.style.borderColor = "var(--sc-navy)"}
                  onBlur={(e) => e.target.style.borderColor = "var(--sc-rule)"}
                />
              </label>

              <label style={{ display: "block", marginBottom: 10 }}>
                <div style={{
                  display: "flex", justifyContent: "space-between", alignItems: "baseline",
                  marginBottom: 8,
                }}>
                  <span style={{
                    fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.14em",
                    textTransform: "uppercase", color: "var(--sc-text-faint)",
                  }}>Password</span>
                  <a href="#" style={{
                    fontSize: 12, color: "var(--sc-teal-ink)", fontWeight: 500,
                  }}>Forgot?</a>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: "100%", padding: "12px 14px",
                    border: "1px solid var(--sc-rule)",
                    fontFamily: "var(--sc-sans)", fontSize: 15,
                    color: "var(--sc-text)", background: "#ffffff",
                    outline: "none",
                  }}
                  onFocus={(e) => e.target.style.borderColor = "var(--sc-navy)"}
                  onBlur={(e) => e.target.style.borderColor = "var(--sc-rule)"}
                />
              </label>

              <label style={{
                display: "flex", alignItems: "center", gap: 8,
                fontSize: 13, color: "var(--sc-text-dim)", marginBottom: 26, cursor: "pointer",
              }}>
                <input type="checkbox" defaultChecked style={{ accentColor: "var(--sc-navy)" }} />
                Keep me signed in on this device
              </label>

              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: "100%",
                  background: "var(--sc-navy)", color: "#ffffff",
                  border: "1px solid var(--sc-navy)",
                  padding: "14px 18px",
                  fontFamily: "var(--sc-sans)", fontSize: 12, fontWeight: 700,
                  letterSpacing: "0.18em", textTransform: "uppercase",
                  cursor: submitting ? "wait" : "pointer",
                  display: "flex", justifyContent: "center", alignItems: "center", gap: 10,
                  opacity: submitting ? 0.7 : 1,
                }}
              >
                {submitting ? "Signing in…" : "Sign in"}
                {!submitting && (
                  <svg width="14" height="14" viewBox="0 0 12 12">
                    <path d="M2 10 L10 2 M4 2 L10 2 L10 8" stroke="currentColor" strokeWidth="1.5" fill="none" />
                  </svg>
                )}
              </button>
            </form>

            <div style={{
              marginTop: 24, fontSize: 13, color: "var(--sc-text-dim)",
              textAlign: "center",
            }}>
              Requesting access?{" "}
              <a href="#" style={{ color: "var(--sc-teal-ink)", fontWeight: 600 }}>
                Contact Andrew →
              </a>
            </div>
          </div>
        </div>

        <div style={{
          fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.12em",
          color: "var(--sc-text-faint)", textTransform: "uppercase",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>© 2026 SeekingChartis</span>
          <span>Chicago · UChicago</span>
        </div>
      </div>

      {/* Right panel — brand / data visual */}
      <div style={{
        background: "var(--sc-ink)", color: "#ffffff",
        position: "relative", overflow: "hidden",
        padding: "56px 60px",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
      }}>
        {/* Concentric backdrop */}
        <svg style={{ position: "absolute", right: -180, top: -180, opacity: 0.18 }}
          width="800" height="800" viewBox="0 0 100 100">
          {[10, 20, 30, 40, 50, 60, 70].map(r => (
            <circle key={r} cx="50" cy="50" r={r} fill="none"
              stroke="var(--sc-teal)" strokeWidth="0.2"/>
          ))}
        </svg>

        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.22em",
            textTransform: "uppercase", color: "var(--sc-teal-2)", marginBottom: 14,
          }}>— Corpus status</div>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 13, color: "var(--sc-on-navy-dim)",
            display: "grid", gridTemplateColumns: "auto 1fr", gap: "8px 20px",
          }}>
            <span style={{ color: "var(--sc-teal-2)" }}>● ONLINE</span>
            <span>52 API endpoints · 56 methods</span>
            <span style={{ color: "var(--sc-teal-2)" }}>● GREEN</span>
            <span>2,883 tests passing · 225 test files</span>
            <span style={{ color: "var(--sc-teal-2)" }}>● FRESH</span>
            <span>HCRIS refreshed 12h ago · /api/health/deep</span>
          </div>
        </div>

        <div style={{ position: "relative", zIndex: 1 }}>
          <blockquote style={{
            fontFamily: "var(--sc-serif)", fontSize: 30, fontWeight: 400,
            lineHeight: 1.3, letterSpacing: "-0.01em",
            color: "#ffffff", margin: 0, marginBottom: 24,
            textWrap: "pretty",
          }}>
            “Codify the twenty questions a partner asks in the first fifteen
            minutes of diligence.”
          </blockquote>
          <div style={{
            fontFamily: "var(--sc-mono)", fontSize: 10, letterSpacing: "0.18em",
            textTransform: "uppercase", color: "var(--sc-on-navy-dim)",
          }}>
            — Founding principle, SeekingChartis
          </div>
        </div>

        <div style={{
          position: "relative", zIndex: 1,
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20,
          borderTop: "1px solid var(--sc-navy-3)", paddingTop: 24,
        }}>
          {[
            { n: "52", l: "Endpoints" },
            { n: "241", l: "Sources" },
            { n: "2,883", l: "Tests" },
          ].map((s, i) => (
            <div key={i}>
              <div style={{
                fontFamily: "var(--sc-serif)", fontSize: 32, fontWeight: 400,
                color: "#ffffff", lineHeight: 1,
              }}>{s.n}</div>
              <div style={{
                fontFamily: "var(--sc-mono)", fontSize: 9, letterSpacing: "0.16em",
                textTransform: "uppercase", color: "var(--sc-on-navy-dim)", marginTop: 6,
              }}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { LoginPage });
