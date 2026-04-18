"""Shared building blocks for chartis per-deal pages.

Kept deliberately small — only pieces that would otherwise be written
five or six times across the per-deal pages. Anything specific to one
page stays in that page's module.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .._chartis_kit import P


_PER_DEAL_NAV_ITEMS: List[Tuple[str, str]] = [
    ("Partner Review", "partner-review"),
    ("Red Flags", "red-flags"),
    ("Archetype", "archetype"),
    ("Investability", "investability"),
    ("Market Structure", "market-structure"),
    ("White Space", "white-space"),
    ("Stress Grid", "stress"),
    ("IC Packet", "ic-packet"),
]


def deal_header_nav(deal_id: str, *, active: str = "") -> str:
    """Render the cross-link header that appears on every per-deal
    brain page.

    ``active`` is the URL suffix of the current page (e.g. "archetype"
    for /deal/<id>/archetype) — the corresponding link is rendered dim
    so the partner can see where they are.
    """
    did = _html.escape(deal_id)
    parts: List[str] = [
        f'<a href="/deal/{did}" style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);font-size:10px;letter-spacing:0.10em;">'
        f'&larr; DEAL DASHBOARD</a>'
    ]
    for label, suffix in _PER_DEAL_NAV_ITEMS:
        is_active = suffix == active
        col = P["text_faint"] if is_active else P["accent"]
        arrow = "" if is_active else " →"
        parts.append(
            f'<span style="color:{P["text_faint"]};padding:0 6px;">·</span>'
            f'<a href="/deal/{did}/{suffix}" '
            f'style="color:{col};font-family:var(--ck-mono);font-size:10px;'
            f'letter-spacing:0.10em;">{_html.escape(label.upper())}{arrow}</a>'
        )
    parts.append(
        f'<span style="color:{P["text_faint"]};padding:0 6px;">·</span>'
        f'<a href="/analysis/{did}" style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);font-size:10px;letter-spacing:0.10em;">'
        f'WORKBENCH →</a>'
    )
    return (
        f'<div style="margin-bottom:14px;display:flex;flex-wrap:wrap;'
        f'align-items:center;">{"".join(parts)}</div>'
    )


def insufficient_data_banner(
    deal_id: str,
    *,
    title: str,
    error: str,
    missing_fields: Optional[List[str]] = None,
) -> str:
    """Red banner used whenever the brain cannot run on a deal.

    All six per-deal pages render this when
    ``_build_partner_review_context`` returns an error. The message is
    partner-actionable — says what to do next, not just 'failed'.
    """
    missing_list = (
        ", ".join(_html.escape(m) for m in missing_fields)
        if missing_fields else "—"
    )
    return (
        f'<div style="background:rgba(239,68,68,0.10);border:1px solid {P["negative"]};'
        f'border-radius:3px;padding:12px 14px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["negative"]};letter-spacing:0.12em;margin-bottom:4px;">'
        f'{_html.escape(title.upper())} UNAVAILABLE</div>'
        f'<div style="color:{P["text"]};font-size:12px;margin-bottom:6px;">'
        f'{_html.escape(error)}</div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;">'
        f'Missing: <span style="font-family:var(--ck-mono);color:{P["warning"]};">'
        f'{missing_list}</span></div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:6px;">'
        f'Open the <a href="/analysis/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};">analysis workbench</a> to finish '
        f'building the packet, or <a href="/deal/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};">return to the deal dashboard</a>.'
        f'</div></div>'
    )


def small_panel(title: str, body: str, *, code: str = "") -> str:
    """Standard panel wrapper for grouped content."""
    code_html = (
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'{_html.escape(code)}</span>' if code else ""
    )
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">{_html.escape(title)}{code_html}</div>'
        f'<div style="padding:12px 14px;">{body}</div>'
        f'</div>'
    )


def empty_note(msg: str) -> str:
    """Inline placeholder for sections with no data."""
    return (
        f'<p style="color:{P["text_faint"]};font-size:11px;'
        f'font-style:italic;margin:0;">{_html.escape(msg)}</p>'
    )


def fmt_pct(val: Any, *, digits: int = 1) -> str:
    """Render a fraction (0–1) as a percentage, or '—' on missing."""
    try:
        return f"{float(val) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_multiple(val: Any, *, digits: int = 2) -> str:
    """Render a multiplier (e.g. MOIC) with 'x' suffix."""
    try:
        return f"{float(val):.{digits}f}x"
    except (TypeError, ValueError):
        return "—"


def fmt_num(val: Any, *, digits: int = 2) -> str:
    """Render a raw number; '—' on missing."""
    try:
        return f"{float(val):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def kv_list(pairs: Iterable[Tuple[str, str]]) -> str:
    """Render a simple label/value list in the standard chartis style."""
    rows = []
    for k, v in pairs:
        rows.append(
            f'<div style="display:flex;gap:10px;padding:4px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11px;">'
            f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;letter-spacing:0.08em;width:180px;flex-shrink:0;">'
            f'{_html.escape(k)}</span>'
            f'<span style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;">{v}</span>'
            f'</div>'
        )
    return "".join(rows) if rows else empty_note("No fields.")


def bullet_list(items: Iterable[str], *, color: str = "") -> str:
    """Render a simple bullet list; skips empty strings."""
    li = []
    col = color or P["text"]
    for it in items:
        if not it:
            continue
        li.append(
            f'<li style="padding:3px 0;color:{col};font-size:11.5px;'
            f'line-height:1.55;">{_html.escape(str(it))}</li>'
        )
    if not li:
        return empty_note("None.")
    return (
        f'<ul style="list-style:none;padding:0;margin:0;">{"".join(li)}</ul>'
    )


def verdict_badge(label: str, *, color: str = P["text_faint"]) -> str:
    return (
        f'<span class="ck-sig" style="color:{color};'
        f'border:1px solid {color};background:rgba(255,255,255,0.02);">'
        f'{_html.escape(label)}</span>'
    )


def related_views_panel(deal_id: str, *, exclude: str = "") -> str:
    """Renders the "related views" strip used on /partner-review
    and other hub-like per-deal pages."""
    did = _html.escape(deal_id)
    cards = []
    for label, suffix in _PER_DEAL_NAV_ITEMS:
        if suffix == exclude:
            continue
        cards.append(
            f'<a href="/deal/{did}/{suffix}" '
            f'style="flex:1;min-width:140px;background:{P["panel"]};'
            f'border:1px solid {P["border"]};border-radius:3px;padding:10px;'
            f'text-decoration:none;">'
            f'<div style="font-family:var(--ck-mono);font-size:11px;'
            f'color:{P["accent"]};letter-spacing:0.05em;">'
            f'{_html.escape(label)} &rarr;</div>'
            f'</a>'
        )
    return (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px;">'
        f'{"".join(cards)}</div>'
    )


def flat_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Dict-or-attr traversal tolerant of missing keys/attrs."""
    cur = obj
    for k in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            cur = getattr(cur, k, None)
    return cur if cur is not None else default


def load_corpus_deals() -> List[Dict[str, Any]]:
    """Return the full 655-deal seed corpus (35 base + 620 extended).

    Mirrors the loader in ``ui/data_public/deals_library_page.py`` —
    kept here so every chartis portfolio-level page can call it
    without depending on that legacy module's private helper.
    """
    try:
        from ...data_public.deals_corpus import _SEED_DEALS
        from ...data_public.extended_seed import EXTENDED_SEED_DEALS
    except Exception:
        return []
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = __import__(
                f"rcm_mc.data_public.extended_seed_{i}",
                fromlist=[f"EXTENDED_SEED_DEALS_{i}"],
            )
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def safe_dict(x: Any) -> Dict[str, Any]:
    """Coerce to a dict when something might be a dataclass/None/dict."""
    if isinstance(x, dict):
        return x
    if x is None:
        return {}
    if hasattr(x, "to_dict"):
        try:
            out = x.to_dict() or {}
            if isinstance(out, dict):
                return out
        except Exception:
            pass
    return {}


# ── Page explainer (Phase 3) ─────────────────────────────────────────

# Auto-incrementing id so multiple explainers on one page don't
# collide on localStorage keys. Each explainer picks up a stable id
# from the route via the `page_key` param.
def render_page_explainer(
    what: str,
    *,
    scale: Optional[str] = None,
    use: Optional[str] = None,
    source: str = "",
    page_key: str = "",
) -> str:
    """Render the standardized "About this page" block.

    Every chartis page calls this at the top of its body, under the
    page title. Three sections:

      - WHAT  (required): one sentence describing what the page shows.
      - SCALE (optional): explicit interpretation of metric thresholds.
      - USE   (optional): one sentence on the action a partner takes.

    ``source`` renders as a muted "Source: ..." footer. Leave blank
    only for pages whose WHAT is purely descriptive (no interpretive
    claims).

    ``page_key`` is the route path (e.g. "deal-partner-review") that
    gets hashed into the localStorage key so collapse state persists
    per-page. Collision-safe across routes and between multiple
    explainers on the same page.

    Collapse toggle: a small "hide" button at the top-right flips a
    localStorage flag. On next load the block renders collapsed.
    JavaScript is added once per page (idempotent — loads the first
    explainer's script block; subsequent ones are no-ops).
    """
    key = _html.escape(page_key or "default")
    what_html = _html.escape(what)
    scale_html = (
        f'<div class="ck-explainer-subheading">Scale</div>'
        f'<p class="ck-explainer-body">{_html.escape(scale)}</p>'
        if scale else ""
    )
    use_html = (
        f'<div class="ck-explainer-subheading">How to use</div>'
        f'<p class="ck-explainer-body">{_html.escape(use)}</p>'
        if use else ""
    )
    source_html = (
        f'<div class="ck-explainer-source">Source: {_html.escape(source)}</div>'
        if source else ""
    )

    return (
        f'<div class="ck-explainer" data-page-key="{key}">'
        f'<div class="ck-explainer-header">'
        f'<span class="ck-explainer-title">About this page</span>'
        f'<button class="ck-explainer-toggle" type="button" '
        f'aria-label="Toggle explainer" '
        f'onclick="ckExplainerToggle(this)">hide</button>'
        f'</div>'
        f'<div class="ck-explainer-content">'
        f'<p class="ck-explainer-body ck-explainer-what">{what_html}</p>'
        f'{scale_html}'
        f'{use_html}'
        f'{source_html}'
        f'</div>'
        f'</div>'
        f'{_EXPLAINER_CSS_AND_JS}'
    )


# Single-shot CSS + JS appended on every explainer. The <style> block
# is load-safe to repeat (duplicate rules are identical); the
# <script> block is idempotent because the function name check
# guards against redeclaration.
_EXPLAINER_CSS_AND_JS = """
<style>
.ck-explainer {
  background: var(--ck-panel);
  border: 1px solid var(--ck-border);
  border-left: 3px solid var(--ck-accent);
  border-radius: 3px;
  padding: 10px 14px;
  margin-bottom: 14px;
}
.ck-explainer.collapsed .ck-explainer-content { display: none; }
.ck-explainer-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}
.ck-explainer-title {
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ck-text-faint);
}
.ck-explainer-toggle {
  background: transparent;
  border: 1px solid var(--ck-border);
  color: var(--ck-text-faint);
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 1px 7px;
  border-radius: 2px;
  cursor: pointer;
}
.ck-explainer-toggle:hover {
  border-color: var(--ck-accent);
  color: var(--ck-text);
}
.ck-explainer-body {
  color: var(--ck-text);
  font-size: 12px;
  line-height: 1.55;
  margin: 0 0 8px 0;
}
.ck-explainer-body:last-child { margin-bottom: 0; }
.ck-explainer-subheading {
  font-family: var(--ck-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ck-text-faint);
  margin-top: 4px;
  margin-bottom: 2px;
}
.ck-explainer-source {
  font-family: var(--ck-mono);
  font-size: 10px;
  color: var(--ck-text-faint);
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid var(--ck-border-dim);
}
</style>
<script>
if (typeof window.ckExplainerToggle === 'undefined') {
  window.ckExplainerToggle = function(btn) {
    var panel = btn.closest('.ck-explainer');
    if (!panel) return;
    var key = 'ck-explainer-collapsed:' + (panel.getAttribute('data-page-key') || 'default');
    if (panel.classList.contains('collapsed')) {
      panel.classList.remove('collapsed');
      btn.textContent = 'hide';
      try { localStorage.removeItem(key); } catch(e) {}
    } else {
      panel.classList.add('collapsed');
      btn.textContent = 'show';
      try { localStorage.setItem(key, '1'); } catch(e) {}
    }
  };
  // Restore collapsed state on load
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.ck-explainer').forEach(function(panel) {
      var key = 'ck-explainer-collapsed:' + (panel.getAttribute('data-page-key') || 'default');
      try {
        if (localStorage.getItem(key) === '1') {
          panel.classList.add('collapsed');
          var btn = panel.querySelector('.ck-explainer-toggle');
          if (btn) btn.textContent = 'show';
        }
      } catch(e) {}
    });
  });
}
</script>
"""
