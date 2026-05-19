"""Editorial /login route renderer.

Repositioned 2026-05-19 from "PE fund operating system" framing to
"commercial diligence intelligence" — the platform is sold to
client-facing deal teams who build per-target profiles, not to
internal fund operating partners managing a hold portfolio. The
contract-test pins (`console-teaser` class, `cta-btn submit` button
class, POST to `/api/login`, `href="/forgot"`, server-side
`?tab=request` switching) are all preserved; only the copy + visual
polish change.

Tab switching (Sign In ↔ Request Access) is server-side via
``?tab=request`` — no JS state, no client-side framework. This keeps
behaviour deterministic and back-button-safe.
"""
from __future__ import annotations

import html as _html
from typing import Optional

from rcm_mc.ui._chartis_kit import editorial_chartis_shell


_LOGIN_EXTRA_CSS = """
.stage {
  display: grid; grid-template-columns: 1fr 1fr;
  min-height: calc(100vh - 72px - 80px);
}
/* Left panel — editorial position statement.
 * Subtle teal-ink stripe on the inside edge so the panel reads as
 * an editorial document instead of a flat split-screen. */
.panel-l {
  padding: 4rem 3rem;
  background: var(--paper);
  border-right: 1px solid var(--rule);
  display: flex; flex-direction: column; justify-content: space-between;
  position: relative;
}
.panel-l::before {
  content: "";
  position: absolute; top: 4rem; bottom: 4rem; left: 0;
  width: 3px;
  background: linear-gradient(
    180deg,
    var(--teal-deep) 0%,
    var(--teal) 55%,
    transparent 100%
  );
}
.panel-r {
  padding: 4rem 3rem;
  /* Cream-paper background so the right panel reads as the working
   * surface (where the form sits) vs the left's editorial surface. */
  background: var(--paper-pure);
}
.panel-l h1 {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: clamp(2.4rem, 4vw, 3.4rem); line-height: 1.05;
  letter-spacing: -0.022em; color: var(--ink); margin: 0 0 1rem;
}
.panel-l h1 em {
  font-style: italic; color: var(--teal-deep); font-weight: 400;
}
.panel-l .lede {
  font-family: "Source Serif 4", serif; font-size: 1.05rem;
  color: var(--muted); margin: 0 0 2rem; max-width: 48ch;
}
.panel-l .what-card {
  /* Sub-eyebrow + 3-line "what is this" card above the teaser.
   * Gives the page a real what-the-product-does block partners
   * read before signing in. Subtle teal-soft tint so the block
   * pops on the parchment background. */
  background: linear-gradient(
    135deg,
    var(--teal-soft) 0%,
    var(--paper) 70%
  );
  border: 1px solid var(--rule);
  border-left: 3px solid var(--teal-deep);
  padding: 1.1rem 1.4rem;
  margin-bottom: 1.5rem;
  font-family: "Source Serif 4", serif;
  font-size: .95rem; line-height: 1.55; color: var(--ink-2);
}
.panel-l .what-card .label {
  display: block;
  font-family: "JetBrains Mono", monospace;
  font-size: .68rem; font-weight: 600; letter-spacing: .12em;
  color: var(--teal-deep);
  text-transform: uppercase;
  margin-bottom: .4rem;
}

.console-teaser {
  background: var(--paper-pure); border: 1px solid var(--rule);
  padding: 1.5rem;
  position: relative;
}
.console-teaser::after {
  /* Tiny pulse dot in the corner so the card feels alive. */
  content: "";
  position: absolute; top: 1.2rem; right: 1.4rem;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 0 var(--green-soft);
  animation: ck-pulse 2.4s ease-out infinite;
}
@keyframes ck-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(63, 125, 77, 0.55); }
  50%      { box-shadow: 0 0 0 6px rgba(63, 125, 77, 0); }
}
.teaser-h {
  font-family: "Inter", sans-serif; font-size: .68rem;
  font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: var(--muted); margin-bottom: .9rem;
  display: flex; justify-content: space-between;
}
.teaser-h .src {
  font-family: "JetBrains Mono", monospace; text-transform: none;
  letter-spacing: 0; color: var(--teal-deep); font-size: .72rem;
}
.teaser-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: .58rem 0; border-bottom: 1px solid var(--border);
  font-family: "JetBrains Mono", monospace; font-size: .82rem;
}
.teaser-row:last-child { border-bottom: none; }
.teaser-row .lbl {
  font-family: "Inter", sans-serif; color: var(--muted); font-size: .85rem;
}
.teaser-row .v {
  color: var(--ink); font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.teaser-row .v.teal  { color: var(--teal-deep); }
.teaser-row .v.amber { color: var(--amber); }
.teaser-row .v.green { color: var(--green); }

.meta-stack {
  display: grid; gap: .55rem; padding-top: 2rem;
  border-top: 1px solid var(--rule);
}
.meta-stack .row {
  display: flex; justify-content: space-between;
  font-family: "JetBrains Mono", monospace; font-size: .76rem;
}
.meta-stack .k {
  font-family: "Inter", sans-serif; font-size: .68rem;
  font-weight: 700; letter-spacing: .14em; color: var(--muted);
}
.meta-stack .v { color: var(--ink); }

.form-wrap { max-width: 440px; }
.form-h {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: 1.85rem; line-height: 1.1; letter-spacing: -0.018em;
  color: var(--ink); margin: .75rem 0 .85rem;
}
.form-h em {
  font-style: italic; color: var(--teal-deep); font-weight: 400;
}
.form-sub {
  font-family: "Source Serif 4", serif; font-size: .98rem;
  color: var(--muted); margin: 0 0 1.75rem; max-width: 42ch;
}

.tabs {
  display: flex; gap: 1.5rem; border-bottom: 1px solid var(--rule);
  margin-bottom: 1.75rem;
}
.tabs .tab { display: inline-block; }

.field { margin-bottom: 1.1rem; }
.field label {
  display: block; font-family: "Inter", sans-serif; font-size: .68rem;
  font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: var(--muted); margin-bottom: .4rem;
}
.field input { width: 100%; }
.field-row {
  display: flex; justify-content: space-between; align-items: center;
  margin: .25rem 0 1.5rem; font-family: "Inter", sans-serif;
  font-size: .82rem; color: var(--muted);
}
.field-row label.check { display: flex; align-items: center; gap: .5rem; }
.field-row label.check input { width: auto; padding: 0; }
.field-row a {
  color: var(--teal-deep);
  border-bottom: 1px solid transparent;
  transition: border-color 0.12s;
}
.field-row a:hover { border-bottom-color: var(--teal-deep); }
.submit { width: 100%; }
/* Stronger hover state — gentle gradient + subtle lift so the
 * primary CTA reads as the next action. */
.cta-btn.submit {
  background: linear-gradient(
    180deg,
    var(--ink-2) 0%,
    var(--ink) 100%
  );
  transition: transform 0.08s, box-shadow 0.12s;
}
.cta-btn.submit:hover {
  background: var(--teal-deep);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(21, 87, 82, 0.18);
}

.footnote {
  margin-top: 2rem; font-family: "Source Serif 4", serif;
  font-size: .88rem; color: var(--muted); font-style: italic;
}
.footnote a { color: var(--teal-deep); text-decoration: underline; }

.req-ok {
  margin-top: 1.5rem; padding: 1rem 1.25rem;
  background: var(--teal-soft); border-left: 3px solid var(--teal);
  font-family: "Source Serif 4", serif; font-style: italic;
  color: var(--teal-deep);
}

.err {
  margin: 0 0 1rem; padding: .75rem 1rem;
  background: var(--red-soft); border-left: 3px solid var(--red);
  font-family: "Inter", sans-serif; font-size: .88rem; color: var(--red);
}

@media (max-width: 900px) {
  .stage { grid-template-columns: 1fr; }
  .panel-l {
    border-right: none; border-bottom: 1px solid var(--rule);
    padding: 3rem 1.5rem;
  }
  .panel-l::before { display: none; }
  .panel-r { padding: 3rem 1.5rem; }
}
""".strip()


def _render_signin_form(*, error: Optional[str], next_url: str) -> str:
    err_html = (
        f'<div class="err">{_html.escape(error)}</div>'
        if error else ""
    )
    next_input = (
        f'<input type="hidden" name="next" value="{_html.escape(next_url)}"/>'
        if next_url and next_url != "/" else ""
    )
    return (
        '<div id="signInForm">'
        f'{err_html}'
        '<form method="POST" action="/api/login">'
        f'{next_input}'
        '<div class="field">'
        '<label for="login-email">Email or Username</label>'
        # type="text" not "email" so the seeded demo / partner
        # accounts (literal usernames like "demo") submit
        # cleanly. The DB column is `username` and the regex
        # at auth/auth.py:_USERNAME_RE accepts both bare names
        # and email-style strings. inputmode="email" keeps the
        # mobile keyboard helpful for the typical case.
        '<input type="text" id="login-email" name="username" '
        'placeholder="you@firm.com" required '
        'inputmode="email" autocomplete="username" autofocus/>'
        '</div>'
        '<div class="field">'
        '<label for="login-password">Password</label>'
        '<input type="password" id="login-password" name="password" '
        'placeholder="••••••••••••" required '
        'autocomplete="current-password"/>'
        '</div>'
        '<div class="field-row">'
        '<label class="check"><input type="checkbox" name="remember"/>'
        ' Remember this device</label>'
        '<a href="/forgot">Forgot password?</a>'
        '</div>'
        '<button type="submit" class="cta-btn submit">'
        'Open Deal Workspace →</button>'
        '</form>'
        '</div>'
    )


def _render_request_form(*, success: bool) -> str:
    if success:
        return (
            '<div class="req-ok">'
            "Request received. A member of the team will reach out within "
            "one business day."
            '</div>'
        )
    return (
        '<div id="requestForm">'
        '<form method="POST" action="/login?tab=request">'
        '<div class="field">'
        '<label for="req-email">Work email</label>'
        '<input type="email" id="req-email" name="email" '
        'placeholder="you@firm.com" required autocomplete="email"/>'
        '</div>'
        '<div class="field">'
        '<label for="req-firm">Firm</label>'
        '<input type="text" id="req-firm" name="firm" '
        'placeholder="Strategy Group · Consulting Firm · Advisory" required '
        'autocomplete="organization"/>'
        '</div>'
        '<div class="field">'
        '<label for="req-role">Role</label>'
        '<input type="text" id="req-role" name="role" '
        'placeholder="Director · Engagement Manager · Associate" '
        'autocomplete="organization-title"/>'
        '</div>'
        '<button type="submit" class="cta-btn submit">'
        'Request Access →</button>'
        '</form>'
        '</div>'
    )


def render_login_page(
    *,
    tab: str = "signin",
    error: Optional[str] = None,
    request_success: bool = False,
    next_url: str = "/",
) -> str:
    """Editorial /login — split layout with sign-in / request-access tabs.

    Args:
        tab: "signin" (default) or "request" — controls which form is
             rendered (server-side, no JS state).
        error: When set, renders an inline error block above the form.
        request_success: When True (POST /login?tab=request), shows the
                         confirmation block in the request form.
        next_url: Target after successful login. Echoed into a hidden
                  field on the form so /api/login can redirect there.
    """
    is_request_tab = (tab == "request")
    signin_form = _render_signin_form(error=error, next_url=next_url) if not is_request_tab else ""
    request_form = _render_request_form(success=request_success) if is_request_tab else ""

    tabs_html = (
        '<div class="tabs">'
        f'<a href="/login" class="tab{"" if is_request_tab else " active"}">Sign In</a>'
        f'<a href="/login?tab=request" class="tab{" active" if is_request_tab else ""}">'
        'Request Access</a>'
        '</div>'
    )

    panel_r = (
        '<div class="panel-r">'
        '<div class="form-wrap">'
        '<div class="micro">DEAL TEAM LOGIN</div>'
        '<h2 class="form-h">Sign in to your<br/><em>workspace</em>.</h2>'
        '<p class="form-sub">Use your team credentials to open your '
        'deal profiles, market briefs, and source library.</p>'
        f'{tabs_html}'
        f'{request_form if is_request_tab else signin_form}'
        '<p class="footnote">'
        'Teams with private data feeds: see the '
        '<a href="/docs/deployment">deployment runbook</a> to wire up '
        'CRM, market data, or research connectors after sign-in.</p>'
        '</div>'
        '</div>'
    )

    panel_l = (
        '<div class="panel-l">'
        '<div>'
        '<div class="eyebrow">'
        '<span>COMMERCIAL DILIGENCE</span>'
        '<span class="dot" style="margin:0 .35rem;color:var(--faint)">·</span>'
        '<span>INTELLIGENCE LAYER</span>'
        '<span class="dot" style="margin:0 .35rem;color:var(--faint)">·</span>'
        '<span class="slug">/v1.0.0</span>'
        '</div>'
        '<h1>Open the<br/><em>deal</em>.</h1>'
        '<p class="lede">Each deal team gets a dedicated workspace. '
        'Profiles persist locally — refresh or return tomorrow and '
        'pick up exactly where the diligence left off.</p>'
        '<div class="what-card">'
        '<span class="label">What this is</span>'
        'Commercial diligence intelligence for client-facing deal '
        'teams. Build living target-company profiles with market '
        'research, customer signals, benchmarks, competitive context, '
        'client priorities, and source-backed notes — organized '
        'around the deal at hand, not buried in old decks or '
        'one-off spreadsheets.'
        '</div>'
        '<div class="console-teaser">'
        '<div class="teaser-h"><span>YOUR LAST SESSION</span>'
        '<span class="src">deal.profile</span></div>'
        '<div class="teaser-row"><span class="lbl">Active deal profiles</span>'
        '<span class="v teal">4</span></div>'
        '<div class="teaser-row"><span class="lbl">Market briefs in progress</span>'
        '<span class="v teal">7</span></div>'
        '<div class="teaser-row"><span class="lbl">Client priorities flagged</span>'
        '<span class="v amber">2 of 6</span></div>'
        '<div class="teaser-row"><span class="lbl">Source-backed claims</span>'
        '<span class="v">38 cited · 12 pending</span></div>'
        '<div class="teaser-row"><span class="lbl">Last accessed</span>'
        '<span class="v">2026-04-15</span></div>'
        '</div>'
        '</div>'
        '<div class="meta-stack">'
        '<div class="row"><span class="k">WORKSPACE</span>'
        '<span class="v">CCF-DILIGENCE</span></div>'
        '<div class="row"><span class="k">REGION</span>'
        '<span class="v">us-east-1</span></div>'
        '<div class="row"><span class="k">DATA</span>'
        '<span class="v">Public sources only — no PHI</span></div>'
        '<div class="row"><span class="k">STATUS</span>'
        '<span class="v" style="color:var(--green)">● OPERATIONAL</span></div>'
        '</div>'
        '</div>'
    )

    return editorial_chartis_shell(
        f'<div class="stage">{panel_l}{panel_r}</div>',
        title="Sign in",
        breadcrumbs=[("Home", "/"), ("Sign in", None)],
        show_chrome=False,
        show_phi_banner=False,
        extra_css=_LOGIN_EXTRA_CSS,
    )
