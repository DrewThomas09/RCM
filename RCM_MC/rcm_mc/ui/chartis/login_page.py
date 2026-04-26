"""Editorial /login route renderer.

Matches docs/design-handoff/reference/02-login.html.

Critical invariant: the sign-in form's POST target is unchanged
(``/api/login``). Only the page CONTAINING the form is reskinned. The
auth-round-trip contract test (``test_login_round_trip``) passes
because the cookie-setting endpoint is identical to legacy.

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
.panel-l {
  padding: 4rem 3rem;
  background: var(--paper);
  border-right: 1px solid var(--rule);
  display: flex; flex-direction: column; justify-content: space-between;
}
.panel-r { padding: 4rem 3rem; }
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

.console-teaser {
  background: var(--paper-pure); border: 1px solid var(--rule);
  padding: 1.5rem;
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
  padding: .55rem 0; border-bottom: 1px solid var(--border);
  font-family: "JetBrains Mono", monospace; font-size: .82rem;
}
.teaser-row:last-child { border-bottom: none; }
.teaser-row .lbl {
  font-family: "Inter", sans-serif; color: var(--muted); font-size: .85rem;
}
.teaser-row .v { color: var(--ink); font-weight: 600; }
.teaser-row .v.green { color: var(--green); }
.teaser-row .v.amber { color: var(--amber); }

.meta-stack {
  display: grid; gap: .55rem; padding-top: 2rem; border-top: 1px solid var(--rule);
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
  color: var(--muted); margin: 0 0 1.75rem;
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
.field-row a { color: var(--teal-deep); }
.submit { width: 100%; }

.divider {
  text-align: center; margin: 2rem 0 1rem; font-family: "Inter", sans-serif;
  font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
  color: var(--faint); position: relative;
}
.divider::before, .divider::after {
  content: ""; position: absolute; top: 50%; width: calc(50% - 5rem);
  height: 1px; background: var(--border);
}
.divider::before { left: 0; }
.divider::after { right: 0; }

.sso { display: grid; gap: .6rem; }
.sso button {
  display: flex; align-items: center; gap: .8rem;
  padding: .8rem 1rem; border: 1px solid var(--border); background: var(--paper-pure);
  font-family: "Inter", sans-serif; font-size: .9rem; color: var(--ink);
  cursor: pointer; border-radius: 0; text-align: left;
}
.sso button:hover { border-color: var(--teal); background: var(--bg); }
.sso button .ico {
  width: 24px; height: 24px; display: inline-flex; align-items: center;
  justify-content: center; font-family: "Source Serif 4", serif;
  font-weight: 700; color: var(--teal-deep);
  border: 1px solid var(--border);
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
  .panel-l { border-right: none; border-bottom: 1px solid var(--rule); padding: 3rem 1.5rem; }
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
        '<label for="login-email">Email</label>'
        '<input type="email" id="login-email" name="username" '
        'placeholder="partner@firm.com" required '
        'autocomplete="email" autofocus/>'
        '</div>'
        '<div class="field">'
        '<label for="login-password">Password</label>'
        '<input type="password" id="login-password" name="password" '
        'placeholder="••••••••••••" required autocomplete="current-password"/>'
        '</div>'
        '<div class="field-row">'
        '<label class="check"><input type="checkbox" name="remember"/>'
        ' Remember this device</label>'
        '<a href="/forgot">Forgot password?</a>'
        '</div>'
        '<button type="submit" class="cta-btn submit">'
        'Open Command Center →</button>'
        '</form>'
        '<div class="divider">or continue with</div>'
        '<div class="sso">'
        '<button type="button" disabled title="SSO not configured in Phase 1">'
        '<span class="ico">G</span> Google Workspace</button>'
        '<button type="button" disabled title="SSO not configured in Phase 1">'
        '<span class="ico">M</span> Microsoft Entra ID</button>'
        '<button type="button" disabled title="SSO not configured in Phase 1">'
        '<span class="ico">S</span> SAML SSO</button>'
        '</div>'
        '</div>'
    )


def _render_request_form(*, success: bool) -> str:
    if success:
        return (
            '<div class="req-ok">'
            "Request received. We'll be in touch within one business day."
            '</div>'
        )
    return (
        '<div id="requestForm">'
        '<form method="POST" action="/login?tab=request">'
        '<div class="field">'
        '<label for="req-email">Work email</label>'
        '<input type="email" id="req-email" name="email" '
        'placeholder="partner@firm.com" required autocomplete="email"/>'
        '</div>'
        '<div class="field">'
        '<label for="req-firm">Firm</label>'
        '<input type="text" id="req-firm" name="firm" '
        'placeholder="Healthcare Opportunity Fund II" required '
        'autocomplete="organization"/>'
        '</div>'
        '<div class="field">'
        '<label for="req-role">Role</label>'
        '<input type="text" id="req-role" name="role" '
        'placeholder="Partner · Operating Partner · Analyst" '
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
        '<div class="micro">PARTNER LOGIN</div>'
        '<h2 class="form-h">Sign in to your<br/><em>instance</em>.</h2>'
        '<p class="form-sub">Use your partner credentials, or '
        'continue with single sign-on.</p>'
        f'{tabs_html}'
        f'{request_form if is_request_tab else signin_form}'
        '<p class="footnote">'
        'Public data only — no PHI permitted on this instance. '
        'Partners with private feeds: see your '
        '<a href="/docs/deployment">deployment runbook</a> to enable '
        'connectors after sign-in.</p>'
        '</div>'
        '</div>'
    )

    panel_l = (
        '<div class="panel-l">'
        '<div>'
        '<div class="eyebrow">'
        '<span>PARTNER ACCESS</span>'
        '<span class="dot" style="margin:0 .35rem;color:var(--faint)">·</span>'
        '<span>FUND II</span>'
        '<span class="dot" style="margin:0 .35rem;color:var(--faint)">·</span>'
        '<span class="slug">/v1.0.0</span>'
        '</div>'
        '<h1>Open the<br/><em>console</em>.</h1>'
        '<p class="lede">Each partner gets a dedicated instance. State '
        'persists locally — refresh or return tomorrow and pick up '
        'exactly where you left off.</p>'
        '<div class="console-teaser">'
        '<div class="teaser-h"><span>YOUR LAST SESSION</span>'
        '<span class="src">portfolio.db</span></div>'
        '<div class="teaser-row"><span class="lbl">Weighted MOIC</span>'
        '<span class="v green">2.69x</span></div>'
        '<div class="teaser-row"><span class="lbl">Weighted IRR</span>'
        '<span class="v amber">21.9%</span></div>'
        '<div class="teaser-row"><span class="lbl">Covenants on watch</span>'
        '<span class="v amber">2 of 6</span></div>'
        '<div class="teaser-row"><span class="lbl">EBITDA drag identified</span>'
        '<span class="v">$24.4M</span></div>'
        '<div class="teaser-row"><span class="lbl">Last accessed</span>'
        '<span class="v">2026-04-15</span></div>'
        '</div>'
        '</div>'
        '<div class="meta-stack">'
        '<div class="row"><span class="k">INSTANCE</span><span class="v">CCF-FUND2</span></div>'
        '<div class="row"><span class="k">REGION</span><span class="v">us-east-1</span></div>'
        '<div class="row"><span class="k">DATA</span><span class="v">Public only — no PHI</span></div>'
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
