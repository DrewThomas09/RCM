"""Editorial /login route renderer — "Deal Team Login · Centered Card".

Redesigned 2026-05-24 from the two-column editorial split to the
single-centered-card design handoff (cream field, 480px paper card, no page
chrome). This is a **skin swap over the existing auth flow** — it does NOT
change the data contract:

  - the sign-in form still POSTs to ``/api/login`` (CSRF-exempt; the
    server-side session/cookie flow in ``server.py`` is untouched),
  - the hidden ``next`` field still echoes the redirect target,
  - Request Access still switches server-side via ``?tab=request`` and POSTs
    to ``/login?tab=request`` (deterministic, back-button-safe — no JS state),
  - ``/forgot`` link and the ``cta-btn submit`` primary-button class are
    preserved so the existing contract tests stay green.

The only client JS is a tiny, login-scoped Show/Hide password toggle
(``type="button"`` — never submits). No external fonts/CDN/React/Babel: the
shell already loads Source Serif 4 / Inter / JetBrains Mono. Single sign-on
is rendered **disabled** because no SSO/SAML route exists in PEdesk — we do
not invent auth behavior.
"""
from __future__ import annotations

import html as _html
from typing import Optional

from rcm_mc.ui._chartis_kit import editorial_chartis_shell


_LOGIN_EXTRA_CSS = """
.pd-login-page{
  --pl-navy:#0d2336;--pl-navy2:#14304a;--pl-cream:#f4ecd9;--pl-paper:#fbf7ee;
  --pl-ink:#15202b;--pl-ink2:#2a3a4a;--pl-muted:#6a7480;--pl-muted2:#8b94a0;
  --pl-rule:#d9cfb8;--pl-green:#1f7a5a;--pl-amber:#b8842e;
  --pl-serif:'Source Serif 4',Georgia,serif;
  --pl-sans:'Inter Tight',Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;
  --pl-mono:'JetBrains Mono',ui-monospace,monospace;
  box-sizing:border-box;min-height:100vh;width:100%;
  display:flex;align-items:center;justify-content:center;padding:40px 16px;
  background-color:var(--pl-cream);
  background-image:
    radial-gradient(60% 50% at 50% 0%, rgba(255,255,255,.5), transparent 70%),
    radial-gradient(60% 50% at 50% 100%, rgba(13,35,54,.05), transparent 70%);
}
/* Short viewports scroll from the top instead of clipping the card. */
@media (max-height:720px){ .pd-login-page{align-items:flex-start;} }
.pd-login-page *{box-sizing:border-box;}

.pd-login-card{
  width:480px;max-width:100%;background:var(--pl-paper);
  border:1px solid var(--pl-rule);border-radius:4px;padding:56px 56px 44px;
  box-shadow:0 1px 0 rgba(0,0,0,.04),0 30px 60px -20px rgba(13,35,54,.18),
    0 16px 30px -16px rgba(13,35,54,.10);
  color:var(--pl-ink);
  font-family:var(--pl-sans);
}
@media (max-width:560px){
  .pd-login-card{width:calc(100% - 32px);padding:40px 28px 32px;}
}

.pd-login-eyebrow{
  font-family:var(--pl-mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--pl-green);margin:0 0 24px;
}
.pd-login-h1{
  font-family:var(--pl-serif);font-weight:400;font-size:44px;line-height:1.05;
  letter-spacing:-.02em;color:var(--pl-ink);margin:0 0 14px;
}
@media (max-width:560px){ .pd-login-h1{font-size:36px;} }
.pd-login-h1 em{font-style:italic;color:var(--pl-green);font-weight:400;}
.pd-login-sub{
  font-family:var(--pl-serif);font-size:15.5px;line-height:1.55;
  color:var(--pl-ink2);margin:0 0 36px;
}

/* Segmented control (server-side tabs rendered as anchors). */
.pd-login-seg{
  display:grid;grid-template-columns:1fr 1fr;background:var(--pl-cream);
  border:1px solid var(--pl-rule);border-radius:999px;padding:4px;margin:0 0 28px;
}
.pd-login-seg-btn{
  text-align:center;text-decoration:none;padding:10px 14px;border-radius:999px;
  font-family:var(--pl-mono);font-size:11.5px;letter-spacing:.10em;
  text-transform:uppercase;color:var(--pl-muted);
  transition:background .15s,color .15s;
}
.pd-login-seg-btn.on{background:var(--pl-navy);color:var(--pl-paper);}
.pd-login-seg-btn:focus-visible{outline:2px solid var(--pl-green);outline-offset:2px;}

.pd-login-field{margin:0 0 16px;position:relative;}
.pd-login-field label{
  display:block;font-family:var(--pl-mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--pl-muted2);margin:0 0 8px;
}
.pd-login-field input{
  width:100%;background:var(--pl-paper);border:1px solid var(--pl-rule);
  border-radius:4px;padding:14px;font-family:var(--pl-sans);font-size:15px;
  color:var(--pl-ink);
}
.pd-login-field input::placeholder{color:var(--pl-muted2);}
.pd-login-field input:focus{
  outline:none;border-color:var(--pl-green);box-shadow:0 0 0 3px rgba(31,122,90,.12);
}
.pd-login-pw input{padding-right:70px;}
.pd-login-show{
  position:absolute;right:12px;top:34px;background:var(--pl-cream);border:none;
  padding:4px 8px;border-radius:4px;cursor:pointer;
  font-family:var(--pl-mono);font-size:10.5px;letter-spacing:.10em;
  text-transform:uppercase;color:var(--pl-muted);
}
.pd-login-show:focus-visible{outline:2px solid var(--pl-green);outline-offset:2px;}

.pd-login-row{
  display:flex;justify-content:space-between;align-items:center;
  margin:6px 0 26px;font-family:var(--pl-sans);font-size:13px;color:var(--pl-ink2);
}
.pd-login-row label{display:flex;align-items:center;gap:8px;cursor:pointer;}
.pd-login-row input[type=checkbox]{accent-color:var(--pl-green);width:auto;}
.pd-login-row a{color:var(--pl-green);font-weight:500;text-decoration:none;}
.pd-login-row a:hover{text-decoration:underline;}
.pd-login-row a:focus-visible{outline:2px solid var(--pl-green);outline-offset:2px;}

.pd-login-page .cta-btn.submit,.pd-login-submit{
  width:100%;background:var(--pl-navy);color:var(--pl-paper);border:none;
  padding:16px;border-radius:4px;cursor:pointer;
  font-family:var(--pl-sans);font-size:14px;font-weight:600;letter-spacing:.02em;
}
.pd-login-page .cta-btn.submit:hover,.pd-login-submit:hover{background:var(--pl-navy2);}
.pd-login-page .cta-btn.submit:focus-visible,.pd-login-submit:focus-visible{
  outline:2px solid var(--pl-green);outline-offset:2px;
}

.pd-login-divider{
  display:flex;align-items:center;gap:12px;margin:22px 0 16px;
  font-family:var(--pl-mono);font-size:10.5px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--pl-muted);
}
.pd-login-divider::before,.pd-login-divider::after{
  content:"";flex:1;height:1px;background:var(--pl-rule);
}
.pd-login-sso{
  width:100%;display:flex;align-items:center;justify-content:center;gap:8px;
  background:var(--pl-paper);border:1px solid var(--pl-rule);border-radius:4px;
  padding:13px;font-family:var(--pl-sans);font-size:13.5px;color:var(--pl-ink2);
  cursor:not-allowed;opacity:.65;
}
.pd-login-sso-badge{
  font-family:var(--pl-mono);font-size:9px;letter-spacing:.12em;color:var(--pl-muted);
  border:1px solid var(--pl-rule);padding:2px 6px;border-radius:3px;
}

.pd-login-error{
  margin:0 0 18px;padding:12px 14px;border-left:3px solid var(--pl-amber);
  background:rgba(184,132,46,.10);border-radius:0 4px 4px 0;
  font-family:var(--pl-sans);font-size:12.5px;color:#6a4a12;
}
.pd-login-ok{
  margin:0;padding:14px 16px;border-left:3px solid var(--pl-green);
  background:rgba(31,122,90,.08);border-radius:0 4px 4px 0;
  font-family:var(--pl-serif);font-style:italic;color:var(--pl-green);
}
.pd-login-foot{
  margin:28px 0 0;font-family:var(--pl-serif);font-size:.86rem;font-style:italic;
  color:var(--pl-muted);
}
.pd-login-foot a{color:var(--pl-green);text-decoration:underline;}
""".strip()


def _next_qs(next_url: str, *, extra: str = "") -> str:
    """Build a ``?...`` query preserving ``next`` (and optional extra)."""
    parts = []
    if extra:
        parts.append(extra)
    if next_url and next_url != "/":
        parts.append("next=" + _html.escape(next_url, quote=True))
    return ("?" + "&".join(parts)) if parts else ""


def _render_signin_form(*, error: Optional[str], next_url: str) -> str:
    err_html = (
        f'<div class="pd-login-error" role="alert">{_html.escape(error)}</div>'
        if error else ""
    )
    next_input = (
        f'<input type="hidden" name="next" value="{_html.escape(next_url, quote=True)}"/>'
        if next_url and next_url != "/" else ""
    )
    return (
        '<div id="signInForm">'
        f'{err_html}'
        '<form method="POST" action="/api/login">'
        f'{next_input}'
        '<div class="pd-login-field">'
        '<label for="login-email">Email or username</label>'
        # type="text" (not "email") so literal usernames like "demo" submit
        # cleanly; the DB column is `username`. inputmode keeps the mobile
        # keyboard helpful for the common email case.
        '<input type="text" id="login-email" name="username" '
        'placeholder="you@firm.com" required '
        'inputmode="email" autocomplete="username" autofocus/>'
        '</div>'
        '<div class="pd-login-field pd-login-pw">'
        '<label for="login-password">Password</label>'
        '<input type="password" id="login-password" name="password" '
        'placeholder="••••••••••••" required autocomplete="current-password"/>'
        '<button type="button" class="pd-login-show" data-pl-show '
        'aria-label="Show password" aria-pressed="false">Show</button>'
        '</div>'
        '<div class="pd-login-row">'
        '<label><input type="checkbox" name="remember" checked/> '
        'Remember this device</label>'
        '<a href="/forgot">Forgot password?</a>'
        '</div>'
        '<button type="submit" class="cta-btn submit pd-login-submit">'
        'Open deal workspace →</button>'
        '</form>'
        '</div>'
    )


def _render_request_form(*, success: bool) -> str:
    if success:
        return (
            '<div class="pd-login-ok">'
            "Request received. A member of the team will reach out within "
            "one business day."
            '</div>'
        )
    return (
        '<div id="requestForm">'
        '<form method="POST" action="/login?tab=request">'
        '<div class="pd-login-field">'
        '<label for="req-email">Work email</label>'
        '<input type="email" id="req-email" name="email" '
        'placeholder="you@firm.com" required autocomplete="email"/>'
        '</div>'
        '<div class="pd-login-field">'
        '<label for="req-firm">Firm</label>'
        '<input type="text" id="req-firm" name="firm" '
        'placeholder="Strategy Group · Consulting Firm · Advisory" required '
        'autocomplete="organization"/>'
        '</div>'
        '<div class="pd-login-field">'
        '<label for="req-role">Role</label>'
        '<input type="text" id="req-role" name="role" '
        'placeholder="Director · Engagement Manager · Associate" '
        'autocomplete="organization-title"/>'
        '</div>'
        '<button type="submit" class="cta-btn submit pd-login-submit">'
        'Request Access →</button>'
        '</form>'
        '</div>'
    )


_SHOW_HIDE_JS = """
<script>
(function(){
  var btn=document.querySelector('[data-pl-show]');
  var inp=document.getElementById('login-password');
  if(!btn||!inp)return;
  btn.addEventListener('click',function(){
    var show=inp.type==='password';
    inp.type=show?'text':'password';
    btn.textContent=show?'Hide':'Show';
    btn.setAttribute('aria-pressed',show?'true':'false');
    btn.setAttribute('aria-label',show?'Hide password':'Show password');
    inp.focus();
  });
})();
</script>
""".strip()


def render_login_page(
    *,
    tab: str = "signin",
    error: Optional[str] = None,
    request_success: bool = False,
    next_url: str = "/",
) -> str:
    """Editorial /login — centered-card design.

    Args mirror the prior renderer (server.py calls are unchanged):
      tab: "signin" (default) or "request" (server-side switch).
      error: inline error block above the form when set.
      request_success: confirmation block in the request tab.
      next_url: redirect target, echoed into a hidden field for /api/login.
    """
    is_request_tab = (tab == "request")
    form_html = (
        _render_request_form(success=request_success) if is_request_tab
        else _render_signin_form(error=error, next_url=next_url)
    )

    signin_href = "/login" + _next_qs(next_url)
    request_href = "/login" + _next_qs(next_url, extra="tab=request")
    seg = (
        '<div class="pd-login-seg" role="tablist" aria-label="Login mode">'
        f'<a class="pd-login-seg-btn{"" if is_request_tab else " on"}" role="tab" '
        f'aria-selected="{"false" if is_request_tab else "true"}" '
        f'href="{signin_href}">Sign in</a>'
        f'<a class="pd-login-seg-btn{" on" if is_request_tab else ""}" role="tab" '
        f'aria-selected="{"true" if is_request_tab else "false"}" '
        f'href="{request_href}">Request access</a>'
        '</div>'
    )

    # Single sign-on: rendered disabled — PEdesk has no SSO/SAML route, so we
    # show the design's affordance without inventing auth behavior.
    sso = (
        '<div class="pd-login-divider">or continue with</div>'
        '<button type="button" class="pd-login-sso" disabled '
        'title="Single sign-on is not configured for this workspace.">'
        'Single sign-on <span class="pd-login-sso-badge">SAML</span></button>'
    )

    card = (
        '<div class="pd-login-page">'
        '<div class="pd-login-card">'
        '<div class="pd-login-eyebrow">DEAL TEAM LOGIN</div>'
        '<h1 class="pd-login-h1">Sign in to your <em>workspace</em>.</h1>'
        '<p class="pd-login-sub">Use your team credentials to open deal '
        'profiles, market briefs, and your source library.</p>'
        f'{seg}'
        f'{form_html}'
        f'{sso}'
        '<p class="pd-login-foot">Teams with private data feeds: see the '
        '<a href="/docs/deployment">deployment runbook</a> to wire up CRM, '
        'market data, or research connectors after sign-in.</p>'
        '</div>'
        '</div>'
        f'{_SHOW_HIDE_JS}'
    )

    return editorial_chartis_shell(
        card,
        title="Sign in",
        breadcrumbs=[("Home", "/"), ("Sign in", None)],
        show_chrome=False,
        show_phi_banner=False,
        extra_css=_LOGIN_EXTRA_CSS,
    )
