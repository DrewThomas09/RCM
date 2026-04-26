"""Editorial /forgot route renderer.

Matches docs/design-handoff/reference/03-forgot.html. Stylesheet links
/static/v3/chartis.css; the small extras specific to this page (the
.stage centred wrapper + the .ok success card with teal-soft fill)
are inlined as ``extra_css`` to keep the editorial CSS file lean.

The route is editorial-only: there is no legacy /forgot to fall back
to. POST submissions return the same page with ``success=True`` so
the user sees the inline confirmation card. Actual email sending is
out of Phase 1 scope (placeholder behavior matches the reference).
"""
from __future__ import annotations

import html as _html
from typing import Optional

from rcm_mc.ui._chartis_kit import editorial_chartis_shell


_FORGOT_EXTRA_CSS = """
.stage { max-width: 520px; margin: 0 auto; padding: 4rem 2rem; }
.stage h1 {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: 2.6rem; line-height: 1.05; letter-spacing: -0.018em;
  color: var(--ink); margin: 0 0 1rem;
}
.stage h1 em {
  font-style: italic; color: var(--teal-deep); font-weight: 400;
}
.stage .lede {
  font-family: "Source Serif 4", serif; font-size: 1.05rem;
  color: var(--muted); margin: 0 0 2rem;
}
.stage .help {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: .92rem; color: var(--muted); text-align: center;
  margin-top: 1.5rem;
}
.stage .help a { color: var(--teal-deep); text-decoration: underline; }
.stage .ok {
  margin-top: 1rem; padding: 1rem 1.25rem;
  background: var(--teal-soft); border-left: 3px solid var(--teal);
  font-family: "Source Serif 4", serif; font-style: italic;
  color: var(--teal-deep);
}
.stage .err {
  margin-top: 1rem; padding: 1rem 1.25rem;
  background: var(--red-soft); border-left: 3px solid var(--red);
  font-family: "Inter", sans-serif; font-size: .9rem;
  color: var(--red);
}
""".strip()


def render_forgot_page(
    *,
    error: Optional[str] = None,
    success: bool = False,
    submitted_email: Optional[str] = None,
) -> str:
    """Editorial /forgot — single-card recovery form.

    Args:
        error: When set, render an inline error card above the form.
        success: When True, render the inline success card and hide
                 the form. Reached via POST → re-render (no redirect)
                 so a refresh doesn't accidentally re-submit.
        submitted_email: Echoed in the success card so the user
                         sees which inbox they should check.
    """
    safe_email = _html.escape(submitted_email or "")
    err_html = (
        f'<div class="err">{_html.escape(error)}</div>'
        if error else ""
    )
    if success:
        body_html = (
            '<div class="card">'
            '<div class="ok">Recovery link sent'
            + (f' to <strong>{safe_email}</strong>' if safe_email else '')
            + '. Check your inbox — link expires in 30 minutes.</div>'
            '</div>'
            '<p class="help">'
            '<a href="/login">← Back to sign in</a>'
            '</p>'
        )
    else:
        body_html = (
            '<div class="card">'
            '<form method="POST" action="/forgot">'
            '<div class="field">'
            '<label for="forgot-email">Email</label>'
            f'<input type="email" id="forgot-email" name="email" '
            f'value="{safe_email}" placeholder="partner@firm.com" required '
            'autocomplete="email" autofocus/>'
            '</div>'
            f'{err_html}'
            '<button type="submit" class="cta-btn submit">'
            'Send recovery link →</button>'
            '</form>'
            '</div>'
            '<p class="help">'
            "Don't have an account? "
            '<a href="/login?tab=request">Request access</a>'
            '</p>'
        )

    inner = (
        '<div class="stage">'
        '<div class="eyebrow"><span>ACCOUNT RECOVERY</span>'
        '<span style="color:var(--faint);margin:0 .35rem">·</span>'
        '<span class="slug">/reset</span></div>'
        '<h1>Reset your<br/><em>password</em>.</h1>'
        '<p class="lede">Enter the email associated with your partner '
        "instance. We'll send a one-time recovery link.</p>"
        f'{body_html}'
        '</div>'
    )

    return editorial_chartis_shell(
        inner,
        title="Reset password",
        breadcrumbs=[
            ("Home", "/"),
            ("Sign in", "/login"),
            ("Reset password", None),
        ],
        show_chrome=False,    # /forgot has no topnav
        show_phi_banner=False,  # unauthenticated
        extra_css=_FORGOT_EXTRA_CSS,
    )
