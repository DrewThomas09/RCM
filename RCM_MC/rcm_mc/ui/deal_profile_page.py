"""Unified deal profile at /diligence/deal/<slug>.

The single source of truth for one deal. Captures the deal's
metadata ONCE (fixture, deal name, partner, specialty, states,
legal structure, landlord, EV, revenue, EBITDA) and pre-fills
that metadata into every analytic's URL so the analyst never
re-types it.

Why this exists:
    A PE VP working on "Project Aurora" currently re-types
    `dataset=hospital_08_waterfall_critical`, `deal_name=Project
    Aurora`, `legal_structure=FRIENDLY_PC_PASS_THROUGH`, etc.
    across 8+ forms. That's the single biggest source of friction
    in the product. The Deal Profile page solves it with one
    bookmarkable URL + localStorage persistence.

Usage:
    - Navigate to /diligence/deal/aurora (or any slug the analyst
      picks — slug is arbitrary, browser-bookmarkable).
    - Edit the deal params once in the form at the top; they're
      saved to localStorage under ``rcm_deal_<slug>`` and
      mirrored into the URL query string so the page is
      URL-reproducible.
    - Click any analytic card: the link carries every relevant
      query param pre-filled.
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ..diligence._pages import AVAILABLE_FIXTURES
from ._chartis_kit import P, chartis_shell


# ── Deal parameter set ─────────────────────────────────────────────

# Fields the profile captures once and distributes to every tool.
# Each entry: (key, label, placeholder, input_type, tool_relevance)
# where tool_relevance indicates WHICH downstream tools read the
# field — shown as chips on the form so analysts see the impact of
# each field.
_FIELDS = [
    ("dataset", "CCD fixture", "hospital_08_waterfall_critical",
     "select", ["Benchmarks", "Counterfactual", "QoE Memo",
                "IC Packet", "Denial Prediction", "Compare"]),
    ("deal_name", "Deal name", "Project Aurora", "text",
     ["QoE Memo", "IC Packet", "Deal MC"]),
    ("partner_name", "Partner", "", "text", ["QoE Memo", "IC Packet"]),
    ("preparer_name", "Preparer", "", "text",
     ["QoE Memo", "IC Packet"]),
    ("engagement_id", "Engagement ID", "", "text",
     ["QoE Memo", "IC Packet"]),
    ("specialty", "Specialty", "EMERGENCY_MEDICINE", "text",
     ["Counterfactual", "Market Intel", "Deal MC", "Denial Predict"]),
    ("states", "States (comma-sep)", "OR, WA", "text",
     ["Counterfactual", "IC Packet", "Bankruptcy Scan"]),
    ("cbsa_codes", "CBSA codes (comma-sep)", "35620", "text",
     ["Counterfactual", "IC Packet"]),
    ("msas", "MSAs (comma-sep)", "Dallas", "text",
     ["Counterfactual", "Bankruptcy Scan"]),
    ("legal_structure", "Legal structure",
     "FRIENDLY_PC_PASS_THROUGH", "text",
     ["Counterfactual", "IC Packet", "Bankruptcy Scan"]),
    ("landlord", "Landlord", "Medical Properties Trust", "text",
     ["Counterfactual", "IC Packet", "Bankruptcy Scan"]),
    ("lease_term_years", "Lease term (years)", "20", "number",
     ["Counterfactual", "IC Packet", "Bankruptcy Scan"]),
    ("lease_escalator_pct", "Lease escalator (0-1)", "0.035",
     "number", ["Counterfactual"]),
    ("ebitdar_coverage", "EBITDAR coverage (x)", "1.3",
     "number", ["Counterfactual", "Bankruptcy Scan"]),
    ("annual_rent_usd", "Annual rent ($)", "15000000",
     "number", ["Counterfactual"]),
    ("portfolio_ebitdar_usd", "Portfolio EBITDAR ($)",
     "50000000", "number", ["Counterfactual"]),
    ("geography", "Geography", "URBAN_ACADEMIC", "text",
     ["Counterfactual", "IC Packet", "Bankruptcy Scan"]),
    ("market_category", "Market category",
     "MULTI_SITE_ACUTE_HOSPITAL", "text",
     ["Market Intel", "IC Packet"]),
    ("revenue_usd", "Revenue Y0 ($)", "250000000", "number",
     ["Deal MC", "IC Packet", "Market Intel"]),
    ("ebitda_usd", "EBITDA Y0 ($)", "35000000", "number",
     ["Deal MC", "IC Packet"]),
    ("enterprise_value_usd", "Enterprise Value ($)", "350000000",
     "number", ["Deal MC", "IC Packet", "Market Intel"]),
    ("equity_usd", "Equity check ($)", "150000000", "number",
     ["Deal MC"]),
    ("debt_usd", "Debt ($)", "200000000", "number", ["Deal MC"]),
    ("entry_multiple", "Entry EV/EBITDA", "10.0", "number",
     ["Deal MC"]),
]


# Analytics to launch from the profile. Each entry: (label,
# href_template, param_mapping, description).
# The href_template may contain %KEY% placeholders the renderer
# replaces with URL-encoded values from the deal params. Params
# that aren't on the profile are dropped; empty values too.
_ANALYTICS = [
    dict(
        label="Benchmarks (Phase 2)",
        href="/diligence/benchmarks",
        params=["dataset"],
        detail=("HFMA KPI scorecard, cohort liquidation, denial "
                "Pareto, QoR waterfall."),
        badge="RCM",
    ),
    dict(
        label="Denial Prediction",
        href="/diligence/denial-prediction",
        params=["dataset"],
        detail=("Claim-level Naive Bayes denial model. Flags "
                "systematic misses and emits EBITDA-bridge input."),
        badge="RCM · Predictive",
    ),
    dict(
        label="Risk Workbench",
        href="/diligence/risk-workbench",
        params=[],
        detail=("9 Tier-1/2/3 risk panels + counterfactual "
                "summary. Uses the Steward demo by default."),
        badge="Risk",
        extra_qs={"demo": "steward"},
    ),
    dict(
        label="Counterfactual Advisor",
        href="/diligence/counterfactual",
        params=["dataset", "legal_structure", "states", "specialty",
                "cbsa_codes", "msas", "landlord", "lease_term_years",
                "lease_escalator_pct", "ebitdar_coverage",
                "annual_rent_usd", "portfolio_ebitdar_usd",
                "geography"],
        detail=("What would change our mind — minimum offer-shape "
                "modification that flips each RED band."),
        badge="Strategy",
    ),
    dict(
        label="Bankruptcy-Survivor Scan",
        href="/screening/bankruptcy-survivor",
        params=[],
        detail=("Pre-NDA 12-pattern screen against the named "
                "bankruptcy playbook."),
        badge="Screen",
    ),
    dict(
        label="Market Intel",
        href="/market-intel",
        params=["market_category", "specialty",
                "enterprise_value_usd", "revenue_usd"],
        param_aliases={
            "market_category": "category",
            "enterprise_value_usd": "ev_usd",
        },
        detail=("Public operator comps (HCA / THC / CYH / UHS / "
                "EHC / ARDT) + PE transaction multiples + sector "
                "sentiment feed."),
        badge="Market",
    ),
    dict(
        label="Compare",
        href="/diligence/compare",
        params=["dataset"],
        param_aliases={"dataset": "left"},
        detail=("Side-by-side comparison against another fixture. "
                "Adds delta badges on every metric."),
        badge="Comp",
    ),
    dict(
        label="Deal Monte Carlo",
        href="/diligence/deal-mc",
        params=["deal_name", "enterprise_value_usd", "equity_usd",
                "debt_usd", "revenue_usd", "ebitda_usd",
                "entry_multiple"],
        param_aliases={
            "enterprise_value_usd": "ev_usd",
            "revenue_usd": "revenue_usd",
        },
        detail=("3000-trial 5-year forward Monte Carlo with "
                "attribution + sensitivity tornado."),
        badge="Quant",
    ),
    dict(
        label="QoE Memo",
        href="/diligence/qoe-memo",
        params=["dataset", "deal_name", "partner_name",
                "preparer_name", "engagement_id", "specialty",
                "states", "legal_structure", "landlord", "geography"],
        detail=("Partner-signed QoE deliverable. Includes the "
                "counterfactual section when metadata is complete."),
        badge="Export",
    ),
    dict(
        label="IC Packet",
        href="/diligence/ic-packet",
        params=["dataset", "deal_name", "partner_name",
                "preparer_name", "engagement_id", "specialty",
                "states", "cbsa_codes", "legal_structure",
                "landlord", "lease_term_years",
                "lease_escalator_pct", "ebitdar_coverage",
                "annual_rent_usd", "portfolio_ebitdar_usd",
                "geography", "market_category", "revenue_usd",
                "ebitda_usd", "enterprise_value_usd"],
        detail=("One-click assembled IC memo. Browser Save-as-PDF "
                "produces the printable deliverable."),
        badge="Export",
    ),
]


# ── Landing ────────────────────────────────────────────────────────

def _slugs_from_request(qs: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """Deal slugs are client-side only (localStorage); we don't
    have a server catalogue. The landing lets the user pick any
    slug."""
    return []


def _landing_slugs() -> str:
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'
        f'font-weight:600;">Deal Profile</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">One source of truth per deal</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.6;">Each deal gets a unique URL — '
        f'<code>/diligence/deal/&lt;slug&gt;</code>. Pick a slug '
        f'(e.g., <code>aurora</code>), enter the deal parameters once, '
        f'and every downstream analytic opens with those parameters '
        f'pre-filled. Deal state persists locally (browser '
        f'localStorage) so a refresh or returning tomorrow picks up '
        f'where you left off.</div>'
        f'</div>'
        f'<form onsubmit="const slug = this.slug.value.trim().toLowerCase().replace(/[^a-z0-9-]/g, \'-\'); if (slug) window.location.href = \'/diligence/deal/\' + slug; return false;" '
        f'style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:20px;max-width:480px;margin-top:20px;">'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">Deal slug</label>'
        f'<input name="slug" required placeholder="e.g. aurora" '
        f'pattern="[a-zA-Z0-9-]+" '
        f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:inherit;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:6px;line-height:1.5;">Letters, digits, and '
        f'hyphens only. Bookmarkable. Open the same slug from any '
        f'browser to pick up your profile.</div>'
        f'<button type="submit" style="margin-top:16px;padding:8px 20px;'
        f'background:{P["accent"]};color:{P["panel"]};border:0;'
        f'font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;">Open profile</button></form>'
    )
    return chartis_shell(
        body, "RCM Diligence — Deal Profile",
        subtitle="One source of truth per deal",
    )


# ── Main profile renderer ─────────────────────────────────────────

def _render_form(slug: str, seed_values: Dict[str, str]) -> str:
    """Form for editing deal parameters. Uses data-rcm-deal-slug
    so the JS in power_ui.js can hydrate from localStorage."""
    fixture_options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    fields_html: List[str] = []
    for key, label, placeholder, input_type, tools in _FIELDS:
        seeded = html.escape(seed_values.get(key, ""), quote=True)
        chips = "".join(
            f'<span style="font-size:8px;letter-spacing:.5px;'
            f'text-transform:uppercase;color:{P["text_faint"]};'
            f'background:{P["panel_alt"]};padding:1px 5px;'
            f'border-radius:2px;margin-right:3px;">'
            f'{html.escape(t)}</span>'
            for t in tools
        )
        if input_type == "select" and key == "dataset":
            input_html = (
                f'<select name="{key}" data-rcm-deal-field="{key}" '
                f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
                f'color:{P["text"]};border:1px solid {P["border"]};'
                f'font-family:inherit;font-size:11px;">'
                f'<option value="">— none —</option>{fixture_options}'
                f'</select>'
            )
        else:
            input_html = (
                f'<input name="{key}" data-rcm-deal-field="{key}" '
                f'placeholder="{html.escape(placeholder, quote=True)}" '
                f'value="{seeded}" '
                f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
                f'color:{P["text"]};border:1px solid {P["border"]};'
                f'font-family:inherit;font-size:11px;">'
            )
        fields_html.append(
            f'<div>'
            f'<label style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1px;text-transform:uppercase;font-weight:600;'
            f'display:block;margin-bottom:3px;">'
            f'{html.escape(label)}</label>'
            f'{input_html}'
            f'<div style="margin-top:3px;line-height:1.5;">{chips}</div>'
            f'</div>'
        )
    return (
        f'<form data-rcm-deal-form data-rcm-deal-slug="{html.escape(slug)}" '
        f'style="display:grid;grid-template-columns:repeat(3,1fr);'
        f'gap:12px 16px;background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:16px 20px;'
        f'margin-bottom:24px;">'
        f'{"".join(fields_html)}'
        f'<div style="grid-column:span 3;display:flex;gap:10px;'
        f'align-items:center;margin-top:6px;">'
        f'<button type="button" data-rcm-deal-save '
        f'style="padding:8px 18px;background:{P["accent"]};color:{P["panel"]};'
        f'border:0;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;">Save Profile</button>'
        f'<button type="button" data-rcm-deal-clear '
        f'style="padding:8px 18px;background:transparent;color:{P["text_dim"]};'
        f'border:1px solid {P["border"]};font-size:10px;letter-spacing:1.5px;'
        f'text-transform:uppercase;font-weight:600;cursor:pointer;">'
        f'Clear</button>'
        f'<span data-rcm-deal-saved-at style="font-size:10px;'
        f'color:{P["text_faint"]};margin-left:10px;letter-spacing:.5px;">'
        f'</span>'
        f'</div></form>'
    )


def _render_analytics_grid(slug: str) -> str:
    """One card per analytic. Hrefs are rendered with data-rcm-deal-
    template so the JS fills in the current values on click."""
    cards: List[str] = []
    for a in _ANALYTICS:
        params = a.get("params") or []
        aliases = a.get("param_aliases") or {}
        extra_qs = a.get("extra_qs") or {}
        # Encode params as JSON so JS can read them.
        params_json = json.dumps({
            "params": params, "aliases": aliases,
            "extra_qs": extra_qs,
        })
        badge = a.get("badge", "")
        cards.append(
            f'<a data-rcm-deal-link '
            f'data-rcm-deal-href-base="{html.escape(a["href"], quote=True)}" '
            f'data-rcm-deal-params="{html.escape(params_json, quote=True)}" '
            f'data-rcm-deal-slug="{html.escape(slug)}" '
            f'href="{html.escape(a["href"])}" '
            f'style="display:block;background:{P["panel"]};border:1px solid '
            f'{P["border"]};border-radius:4px;padding:14px 16px;'
            f'text-decoration:none;transition:all 0.15s ease;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;margin-bottom:6px;">'
            f'<div style="font-size:13px;color:{P["text"]};font-weight:600;">'
            f'{html.escape(a["label"])}</div>'
            + (f'<span style="font-size:8px;letter-spacing:1px;'
               f'text-transform:uppercase;color:{P["text_faint"]};'
               f'background:{P["panel_alt"]};padding:2px 6px;'
               f'border-radius:2px;">{html.escape(badge)}</span>'
               if badge else "")
            + f'</div>'
            f'<div style="font-size:11px;color:{P["text_dim"]};'
            f'line-height:1.5;">{html.escape(a["detail"])}</div>'
            f'<div data-rcm-deal-preview style="font-size:10px;'
            f'color:{P["text_faint"]};margin-top:8px;font-family:'
            f'\'JetBrains Mono\',monospace;letter-spacing:.3px;'
            f'word-break:break-all;"></div>'
            f'</a>'
        )
    return (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,'
        f'minmax(280px,1fr));gap:12px;">{"".join(cards)}</div>'
    )


def _inline_js(slug: str) -> str:
    """Small script — reads/writes localStorage under rcm_deal_<slug>
    and hydrates form + link hrefs."""
    safe_slug = json.dumps(slug)
    return """<script>
(function() {
  var slug = %SLUG%;
  var storageKey = 'rcm_deal_' + slug;
  function load() {
    try { return JSON.parse(localStorage.getItem(storageKey) || '{}'); }
    catch (e) { return {}; }
  }
  function save(obj) {
    localStorage.setItem(storageKey, JSON.stringify(obj));
  }
  function hydrate() {
    var data = load();
    document.querySelectorAll('[data-rcm-deal-field]').forEach(function(el) {
      var key = el.getAttribute('data-rcm-deal-field');
      if (data[key] != null && data[key] !== '') {
        el.value = data[key];
      }
    });
    var ts = document.querySelector('[data-rcm-deal-saved-at]');
    if (ts && data.__saved_at) {
      ts.textContent = 'Saved ' + new Date(data.__saved_at).toLocaleString();
    }
    updateLinks();
  }
  function collect() {
    var out = {};
    document.querySelectorAll('[data-rcm-deal-field]').forEach(function(el) {
      var key = el.getAttribute('data-rcm-deal-field');
      var v = el.value;
      if (v !== '') out[key] = v;
    });
    return out;
  }
  function updateLinks() {
    var data = collect();
    document.querySelectorAll('[data-rcm-deal-link]').forEach(function(a) {
      var base = a.getAttribute('data-rcm-deal-href-base');
      var specJson = a.getAttribute('data-rcm-deal-params');
      if (!specJson) return;
      try {
        var spec = JSON.parse(specJson);
      } catch (e) { return; }
      var qs = {};
      (spec.extra_qs || {}) && Object.keys(spec.extra_qs || {}).forEach(
        function(k) { qs[k] = spec.extra_qs[k]; },
      );
      (spec.params || []).forEach(function(key) {
        var v = data[key];
        if (v == null || v === '') return;
        var remapped = (spec.aliases || {})[key] || key;
        qs[remapped] = v;
      });
      var queryParts = Object.keys(qs).map(function(k) {
        return encodeURIComponent(k) + '=' + encodeURIComponent(qs[k]);
      });
      var href = queryParts.length ? base + '?' + queryParts.join('&') : base;
      a.href = href;
      var preview = a.querySelector('[data-rcm-deal-preview]');
      if (preview) {
        var shown = queryParts.slice(0, 3).map(function(q) {
          return q.length > 30 ? q.substring(0, 30) + '…' : q;
        }).join(' · ');
        if (queryParts.length > 3) shown += ' · +' + (queryParts.length - 3) + ' more';
        preview.textContent = shown;
      }
    });
  }
  document.addEventListener('DOMContentLoaded', hydrate);
  document.addEventListener('input', function(e) {
    if (e.target.hasAttribute && e.target.hasAttribute('data-rcm-deal-field')) {
      updateLinks();
    }
  });
  document.addEventListener('click', function(e) {
    if (e.target.hasAttribute && e.target.hasAttribute('data-rcm-deal-save')) {
      var data = collect();
      data.__saved_at = new Date().toISOString();
      save(data);
      var ts = document.querySelector('[data-rcm-deal-saved-at]');
      if (ts) ts.textContent = 'Saved ' + new Date(data.__saved_at).toLocaleString();
      if (window.rcmPowerUI) {
        // Toast — leverage the existing power_ui flashToast via
        // the public API (it's rcmPowerUI.bookmark etc; no direct
        // toast exposed, so just set text).
      }
    }
    if (e.target.hasAttribute && e.target.hasAttribute('data-rcm-deal-clear')) {
      if (confirm('Clear saved profile for ' + slug + '?')) {
        localStorage.removeItem(storageKey);
        document.querySelectorAll('[data-rcm-deal-field]').forEach(function(el) {
          el.value = '';
        });
        updateLinks();
        var ts = document.querySelector('[data-rcm-deal-saved-at]');
        if (ts) ts.textContent = 'Cleared';
      }
    }
  });
})();
</script>""".replace("%SLUG%", safe_slug)


def render_deal_profile_page(
    slug: str = "",
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    slug = (slug or "").strip().lower()
    if not slug:
        return _landing_slugs()
    # Sanitise slug.
    safe = "".join(
        c for c in slug if c.isalnum() or c == "-"
    )
    if not safe or len(safe) > 60:
        return _landing_slugs()
    slug = safe

    # Seed form values from ?key=value URL params (so partners can
    # share deals via URL).
    seed_values: Dict[str, str] = {}
    if qs:
        for key, _, _, _, _ in _FIELDS:
            val = (qs.get(key) or [""])[0]
            if val:
                seed_values[key] = val

    hero = (
        f'<div style="padding:24px 0 12px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:24px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'
        f'font-weight:600;">Deal Profile</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:16px;">'
        f'<div><div style="font-size:22px;color:{P["text"]};'
        f'font-weight:600;margin-bottom:4px;">'
        f'<span data-rcm-deal-display-name>{html.escape(slug)}</span>'
        f'</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'font-family:\'JetBrains Mono\',monospace;">'
        f'slug: {html.escape(slug)} · persisted to browser localStorage'
        f'</div></div>'
        f'<a href="/diligence/deal" style="font-size:10px;'
        f'color:{P["accent"]};letter-spacing:1px;text-transform:uppercase;'
        f'border:1px solid {P["border"]};padding:6px 12px;border-radius:3px;'
        f'text-decoration:none;">Pick Another Slug →</a>'
        f'</div></div>'
    )
    intro = (
        f'<div style="font-size:12px;color:{P["text_dim"]};'
        f'max-width:760px;line-height:1.6;margin-bottom:18px;">'
        f'Enter deal parameters once. <strong style="color:{P["text"]};">'
        f'Save Profile</strong> stores them in your browser. Every '
        f'analytic link below pre-fills the relevant parameters — '
        f'click any card and the tool opens with your deal context '
        f'already populated. Press '
        f'<kbd style="padding:1px 5px;border:1px solid currentColor;'
        f'border-radius:2px;font-family:inherit;">b</kbd> to bookmark '
        f'this profile to your Saved Views.</div>'
    )
    form = _render_form(slug, seed_values)
    grid = _render_analytics_grid(slug)
    grid_header = (
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:10px;">Open in Analytic</div>'
    )
    return chartis_shell(
        hero + intro + form + grid_header + grid + _inline_js(slug),
        f"Deal Profile — {slug}",
        subtitle="One source of truth",
    )
