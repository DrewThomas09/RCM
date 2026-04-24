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
from .power_ui import bookmark_hint


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
        label="Thesis Pipeline",
        phase="WORKSPACE",
        href="/diligence/thesis-pipeline",
        params=["dataset", "deal_name", "specialty", "states",
                "legal_structure", "landlord", "lease_term_years",
                "lease_escalator_pct", "ebitdar_coverage",
                "annual_rent_usd", "enterprise_value_usd",
                "equity_check_usd", "debt_usd", "revenue_usd",
                "ebitda_usd", "entry_multiple", "market_category",
                "oon_revenue_share", "ehr_vendor"],
        param_aliases={
            "enterprise_value_usd": "enterprise_value_usd",
            "equity_check_usd": "equity_check_usd",
            "revenue_usd": "revenue_year0_usd",
            "ebitda_usd": "ebitda_year0_usd",
        },
        detail=("One-button full diligence chain — runs bankruptcy "
                "scan, CCD, benchmarks, denial prediction, PPAM, "
                "counterfactual, Steward, cyber, autopsy, deal MC. "
                "Closes the loop from diligence to investment math."),
        badge="Pipeline",
    ),
    dict(
        label="Diligence Checklist",
        phase="WORKSPACE",
        href="/diligence/checklist",
        params=[],
        detail=("Orchestration layer — coverage %, open P0/P1 "
                "questions, auto-tracked from live analytics. "
                "The analyst's daily workspace."),
        badge="Workspace",
    ),
    dict(
        label="Benchmarks (Phase 2)",
        phase="DILIGENCE",
        href="/diligence/benchmarks",
        params=["dataset"],
        detail=("HFMA KPI scorecard, cohort liquidation, denial "
                "Pareto, QoR waterfall."),
        badge="RCM",
    ),
    dict(
        label="Denial Prediction",
        phase="DILIGENCE",
        href="/diligence/denial-prediction",
        params=["dataset"],
        detail=("Claim-level Naive Bayes denial model. Flags "
                "systematic misses and emits EBITDA-bridge input."),
        badge="RCM · Predictive",
    ),
    dict(
        label="Risk Workbench",
        phase="RISK",
        href="/diligence/risk-workbench",
        params=[],
        detail=("9 Tier-1/2/3 risk panels + counterfactual "
                "summary. Uses the Steward demo by default."),
        badge="Risk",
        extra_qs={"demo": "steward"},
    ),
    dict(
        label="Counterfactual Advisor",
        phase="FINANCIAL",
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
        phase="SCREENING",
        href="/screening/bankruptcy-survivor",
        params=[],
        detail=("Pre-NDA 12-pattern screen against the named "
                "bankruptcy playbook."),
        badge="Screen",
    ),
    dict(
        label="Market Intel",
        phase="FINANCIAL",
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
        phase="DILIGENCE",
        href="/diligence/compare",
        params=["dataset"],
        param_aliases={"dataset": "left"},
        detail=("Side-by-side comparison against another fixture. "
                "Adds delta badges on every metric."),
        badge="Comp",
    ),
    dict(
        label="HCRIS Peer X-Ray",
        phase="SCREENING",
        href="/diligence/hcris-xray",
        params=["deal_name"],
        param_aliases={"deal_name": "name"},
        detail=(
            "Point-and-click peer benchmarking against 17,000+ "
            "filed Medicare cost reports. Pick any hospital by "
            "CCN or name, get instant variance analysis against "
            "the 25-50 true peer hospitals across 15 RCM / cost / "
            "margin / payer-mix metrics. The replacement for a "
            "$80K/yr CapIQ subscription on this use case."
        ),
        badge="Public Data",
    ),
    dict(
        label="Payer Mix Stress",
        phase="DILIGENCE",
        href="/diligence/payer-stress",
        params=[
            "deal_name", "revenue_usd", "ebitda_usd",
        ],
        param_aliases={
            "deal_name": "target_name",
            "revenue_usd": "total_npr_usd",
            "ebitda_usd": "total_ebitda_usd",
        },
        detail=(
            "Stress-tests the target's commercial + government "
            "payer portfolio against empirical rate-movement "
            "priors for 19 major US payers. Concentration "
            "amplifier × per-payer Monte Carlo × 5-year horizon. "
            "Outputs P10 EBITDA drag, worst-exposed payer, and "
            "the payer-contract renewal calendar."
        ),
        badge="Stress",
    ),
    dict(
        label="Bear Case Auto-Gen",
        phase="FINANCIAL",
        href="/diligence/bear-case",
        params=[
            "dataset", "deal_name", "specialty",
            "revenue_year0_usd", "ebitda_year0_usd",
            "enterprise_value_usd", "equity_check_usd", "debt_usd",
            "medicare_share", "landlord", "hopd_revenue_annual_usd",
        ],
        param_aliases={"deal_name": "deal_name"},
        detail=(
            "Pulls evidence from Regulatory Calendar × Covenant "
            "Stress × Bridge Audit × Deal MC × Autopsy × Exit "
            "Timing and auto-synthesizes the IC-memo counter-"
            "narrative partners spend 3-5 hours writing by hand. "
            "Citation keys map to source modules; output is a "
            "print-ready memo section."
        ),
        badge="Synthesis",
    ),
    dict(
        label="Bridge Auto-Auditor",
        phase="DILIGENCE",
        href="/diligence/bridge-audit",
        params=["deal_name"],
        param_aliases={"deal_name": "target_name"},
        detail=(
            "Paste the banker's EBITDA bridge and get an instant "
            "risk-adjusted rebuild against ~3,000 historical RCM "
            "initiative realizations. Returns overstated/unsupported "
            "lever verdicts, a counter-bid recommendation, and an "
            "earn-out alternative structured on the overstated gap."
        ),
        badge="Negotiation",
    ),
    dict(
        label="Covenant Stress",
        phase="FINANCIAL",
        href="/diligence/covenant-stress",
        params=[
            "deal_name", "ebitda_usd", "debt_usd", "revolver_usd",
        ],
        param_aliases={
            "deal_name": "deal_name",
            "ebitda_usd": "ebitda_y0",
            "debt_usd": "total_debt_usd",
        },
        detail=(
            "Capital stack × covenant package × Deal MC cone → "
            "per-quarter breach probability curves + equity cure "
            "sizing.  Combined with the Regulatory Calendar overlay, "
            "shows exactly when a CMS cut tightens the leverage "
            "covenant — the answer spreadsheets can't produce."
        ),
        badge="Credit",
    ),
    dict(
        label="Regulatory Calendar",
        phase="DILIGENCE",
        href="/diligence/regulatory-calendar",
        params=[
            "deal_name", "revenue_usd", "ebitda_usd",
            "specialty", "ma_mix_pct", "commercial_payer_share",
        ],
        param_aliases={"deal_name": "target_name"},
        detail=("Gantt-style kill-switch timeline — maps each named "
                "thesis driver to the specific calendar date a CMS / "
                "OIG / FTC / DOJ / NSA-IDR rulemaking event damages "
                "or kills it. Produces an EBITDA bridge overlay that "
                "feeds Deal MC and Exit Timing."),
        badge="Calendar",
    ),
    dict(
        label="Exit Timing",
        phase="FINANCIAL",
        href="/diligence/exit-timing",
        params=["deal_name", "equity_usd", "debt_usd", "ebitda_usd",
                "market_category"],
        param_aliases={
            "deal_name": "target_name",
            "equity_usd": "equity_check_usd",
            "debt_usd": "debt_year0_usd",
            "ebitda_usd": "ebitda_year0_usd",
        },
        detail=("When + to whom — IRR × MOIC curve across candidate "
                "exit years 2-7 and buyer-fit scoring for strategic "
                "/ PE secondary / IPO. Predictive exit path."),
        badge="Predictive",
    ),
    dict(
        label="Deal Monte Carlo",
        phase="FINANCIAL",
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
        label="Deal Autopsy",
        phase="SCREENING",
        href="/diligence/deal-autopsy",
        params=["dataset", "lease_intensity", "ebitdar_stress",
                "dar_stress", "regulatory_exposure",
                "physician_concentration"],
        detail=("Rank the target against a curated library of "
                "historical PE healthcare failures and exits. Surfaces "
                "'you're about to do X again' signature matches."),
        badge="Pattern",
    ),
    dict(
        label="Physician Attrition",
        phase="DILIGENCE",
        href="/diligence/physician-attrition",
        params=["deal_name"],
        param_aliases={"deal_name": "target_name"},
        detail=("Per-provider flight-risk probability with named "
                "retention recommendations + bond sizing. Feeds the "
                "EBITDA bridge's physician-attrition lever."),
        badge="Predictive",
    ),
    dict(
        label="Management Scorecard",
        phase="DILIGENCE",
        href="/diligence/management",
        params=["deal_name", "ebitda_usd"],
        param_aliases={
            "deal_name": "target_name",
            "ebitda_usd": "guidance_ebitda_usd",
        },
        detail=("Scored per-executive diligence — forecast "
                "reliability × comp × tenure × prior-role "
                "reputation. Surfaces the guidance haircut that "
                "feeds the EBITDA bridge."),
        badge="Team",
    ),
    dict(
        label="Provider Economics",
        phase="DILIGENCE",
        href="/diligence/physician-eu",
        params=["deal_name"],
        param_aliases={"deal_name": "target_name"},
        detail=("Per-provider economic unit — ranked contribution "
                "margin, FMV-neutral projection, 'drop these named "
                "loss-makers at close' EBITDA uplift lever."),
        badge="Economic",
    ),
    dict(
        label="QoE Memo",
        phase="DELIVERY",
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
        phase="DELIVERY",
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


_LANDING_JS = r"""<script>
(function() {
  // Enumerate localStorage for saved deal profiles and render a
  // "recent deals" grid so returning users see their work.
  function loadSavedDeals() {
    var out = [];
    for (var i = 0; i < localStorage.length; i++) {
      var key = localStorage.key(i);
      if (!key || !key.startsWith('rcm_deal_')) continue;
      var slug = key.substring('rcm_deal_'.length);
      if (!slug) continue;
      var raw = localStorage.getItem(key);
      if (!raw) continue;
      var data = {};
      try { data = JSON.parse(raw) || {}; } catch (e) { continue; }
      var filled = Object.keys(data).filter(function(k) {
        return k !== '__saved_at' && data[k] !== '' && data[k] != null;
      }).length;
      out.push({
        slug: slug,
        name: data.deal_name || slug,
        saved_at: data.__saved_at || null,
        filled: filled,
        data: data,
      });
    }
    out.sort(function(a, b) {
      return (b.saved_at || '').localeCompare(a.saved_at || '');
    });
    return out;
  }

  function fmtRelative(iso) {
    if (!iso) return 'never saved';
    var t = new Date(iso).getTime();
    if (isNaN(t)) return iso;
    var delta = (Date.now() - t) / 1000;
    if (delta < 60) return 'just now';
    if (delta < 3600) return Math.floor(delta / 60) + ' min ago';
    if (delta < 86400) return Math.floor(delta / 3600) + ' hr ago';
    if (delta < 604800) return Math.floor(delta / 86400) + ' days ago';
    return new Date(iso).toLocaleDateString();
  }

  function render() {
    var root = document.querySelector('[data-rcm-recent-deals]');
    if (!root) return;
    var deals = loadSavedDeals();
    if (deals.length === 0) {
      root.innerHTML =
        '<div style="padding:14px 16px;background:var(--ck-panel,#111827);' +
        'border:1px dashed var(--ck-border,#1e293b);border-radius:4px;' +
        'color:var(--ck-text-dim,#94a3b8);font-size:12px;line-height:1.6;' +
        'font-style:italic;">No saved deals yet. Enter a slug above to ' +
        'create your first profile — it will appear here on subsequent ' +
        'visits.</div>';
      return;
    }
    var cards = deals.map(function(d) {
      var completion = Math.min(100, Math.round(d.filled / 24 * 100));
      var barColor = completion >= 75 ? '#10b981' :
        completion >= 40 ? '#f59e0b' : '#94a3b8';
      var name = (d.name || d.slug).replace(/</g, '&lt;');
      var slug = d.slug.replace(/</g, '&lt;');
      var safeSlug = encodeURIComponent(d.slug);
      return (
        '<div style="background:#111827;border:1px solid #1e293b;' +
        'border-radius:4px;padding:14px 16px;' +
        'transition:border-color 140ms ease, box-shadow 140ms ease;" ' +
        'onmouseover="this.style.borderColor=\'#64748b\';' +
        'this.style.boxShadow=\'0 4px 14px rgba(0,0,0,0.35)\'" ' +
        'onmouseout="this.style.borderColor=\'#1e293b\';' +
        'this.style.boxShadow=\'none\'">' +
        '<div style="display:flex;justify-content:space-between;' +
        'align-items:baseline;gap:10px;margin-bottom:6px;">' +
        '<div style="font-size:9px;color:#64748b;letter-spacing:1.3px;' +
        'text-transform:uppercase;font-family:\'JetBrains Mono\',monospace;">' +
        slug + '</div>' +
        '<div style="font-size:9px;color:#64748b;">' +
        fmtRelative(d.saved_at) + '</div>' +
        '</div>' +
        '<div style="font-size:15px;color:#e2e8f0;font-weight:600;' +
        'line-height:1.25;margin-bottom:8px;">' + name + '</div>' +
        '<div style="height:4px;background:#0f1a2e;border-radius:2px;' +
        'overflow:hidden;margin:8px 0 4px 0;">' +
        '<div style="height:100%;width:' + completion + '%;' +
        'background:' + barColor + ';"></div></div>' +
        '<div style="font-size:10px;color:#64748b;margin-bottom:10px;">' +
        d.filled + ' of 24 fields · ' + completion + '% complete</div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;">' +
        '<a href="/diligence/deal/' + safeSlug + '" ' +
        'style="padding:5px 10px;background:#3b82f6;color:#0a0e17;' +
        'border:0;font-size:9px;letter-spacing:1.2px;' +
        'text-transform:uppercase;font-weight:700;text-decoration:none;' +
        'border-radius:3px;">Open</a>' +
        '<button type="button" data-rcm-duplicate="' + safeSlug + '" ' +
        'style="padding:5px 10px;background:transparent;color:#3b82f6;' +
        'border:1px solid #1e293b;font-size:9px;letter-spacing:1.2px;' +
        'text-transform:uppercase;font-weight:600;cursor:pointer;' +
        'border-radius:3px;">Duplicate</button>' +
        '<button type="button" data-rcm-delete="' + safeSlug + '" ' +
        'style="padding:5px 10px;background:transparent;color:#ef4444;' +
        'border:1px solid #1e293b;font-size:9px;letter-spacing:1.2px;' +
        'text-transform:uppercase;font-weight:600;cursor:pointer;' +
        'border-radius:3px;">Delete</button>' +
        '</div></div>'
      );
    }).join('');
    root.innerHTML =
      '<div style="font-size:10px;color:#64748b;' +
      'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;' +
      'margin-bottom:10px;">Your saved deals · ' + deals.length +
      ' local profile' + (deals.length === 1 ? '' : 's') + '</div>' +
      '<div style="display:grid;grid-template-columns:' +
      'repeat(auto-fill,minmax(240px,1fr));gap:10px;">' + cards + '</div>';
  }

  document.addEventListener('DOMContentLoaded', render);
  document.addEventListener('click', function(e) {
    var dup = e.target.closest && e.target.closest('[data-rcm-duplicate]');
    if (dup) {
      var srcSlug = decodeURIComponent(dup.getAttribute('data-rcm-duplicate'));
      var newSlug = prompt(
        'Duplicate "' + srcSlug + '" as which slug?',
        srcSlug + '-copy',
      );
      if (!newSlug) return;
      newSlug = newSlug.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-');
      if (!newSlug) return;
      var src = localStorage.getItem('rcm_deal_' + srcSlug);
      if (src) {
        try {
          var data = JSON.parse(src);
          data.__saved_at = new Date().toISOString();
          localStorage.setItem('rcm_deal_' + newSlug, JSON.stringify(data));
          render();
        } catch (err) {}
      }
      return;
    }
    var del = e.target.closest && e.target.closest('[data-rcm-delete]');
    if (del) {
      var delSlug = decodeURIComponent(del.getAttribute('data-rcm-delete'));
      if (confirm('Delete saved profile "' + delSlug + '"?')) {
        localStorage.removeItem('rcm_deal_' + delSlug);
        render();
      }
    }
  });
})();
</script>"""


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
        # Recent deals block — JS populates from localStorage.
        f'<div style="margin-top:28px;max-width:960px;" '
        f'data-rcm-recent-deals></div>'
        f'{_LANDING_JS}'
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


_PHASE_ORDER = (
    "WORKSPACE", "SCREENING", "DILIGENCE", "RISK",
    "FINANCIAL", "DELIVERY",
)

_PHASE_META: Dict[str, Dict[str, str]] = {
    "WORKSPACE": {
        "label": "Workspace",
        "subtitle": "one-button orchestration + checklist",
        "tone": "accent",
    },
    "SCREENING": {
        "label": "Screening",
        "subtitle": "pre-NDA go / no-go",
        "tone": "text_dim",
    },
    "DILIGENCE": {
        "label": "Diligence",
        "subtitle": "CCD + predictive analytics",
        "tone": "positive",
    },
    "RISK": {
        "label": "Risk Workbench",
        "subtitle": "Tier 1–3 panels",
        "tone": "warning",
    },
    "FINANCIAL": {
        "label": "Financial synthesis",
        "subtitle": "bridge + Monte Carlo + market",
        "tone": "accent",
    },
    "DELIVERY": {
        "label": "Deliverables",
        "subtitle": "partner-signed exports",
        "tone": "positive",
    },
}


def _analytic_card(slug: str, a: Dict[str, Any]) -> str:
    params = a.get("params") or []
    aliases = a.get("param_aliases") or {}
    extra_qs = a.get("extra_qs") or {}
    params_json = json.dumps({
        "params": params, "aliases": aliases, "extra_qs": extra_qs,
    })
    badge = a.get("badge", "")
    return (
        f'<a data-rcm-deal-link '
        f'data-rcm-deal-href-base="{html.escape(a["href"], quote=True)}" '
        f'data-rcm-deal-params="{html.escape(params_json, quote=True)}" '
        f'data-rcm-deal-slug="{html.escape(slug)}" '
        f'href="{html.escape(a["href"])}" '
        f'style="display:block;background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:14px 16px;'
        f'text-decoration:none;transition:transform 140ms ease, '
        f'border-color 140ms ease, box-shadow 140ms ease;" '
        f'onmouseover="this.style.transform=\'translateY(-1px)\';'
        f'this.style.borderColor=\'{P["text_faint"]}\';'
        f'this.style.boxShadow=\'0 6px 18px rgba(0,0,0,0.30)\';" '
        f'onmouseout="this.style.transform=\'translateY(0)\';'
        f'this.style.borderColor=\'{P["border"]}\';'
        f'this.style.boxShadow=\'none\';">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:6px;">'
        f'<div style="font-size:13px;color:{P["text"]};font-weight:600;'
        f'letter-spacing:-.1px;">'
        f'{html.escape(a["label"])}</div>'
        + (f'<span style="font-size:8px;letter-spacing:1.1px;'
           f'text-transform:uppercase;color:{P["text_faint"]};'
           f'background:{P["panel_alt"]};padding:2px 6px;'
           f'border-radius:2px;font-weight:700;">{html.escape(badge)}</span>'
           if badge else "")
        + f'</div>'
        f'<div style="font-size:11px;color:{P["text_dim"]};'
        f'line-height:1.55;">{html.escape(a["detail"])}</div>'
        f'<div data-rcm-deal-preview style="font-size:10px;'
        f'color:{P["text_faint"]};margin-top:8px;font-family:'
        f'\'JetBrains Mono\',monospace;letter-spacing:.3px;'
        f'word-break:break-all;"></div>'
        f'</a>'
    )


def _render_analytics_grid(slug: str) -> str:
    """Phase-grouped analytic cards.  Phases render as a section
    header with subtitle + tone-colored accent bar, then a grid
    of cards.  Gives the analyst a clear lifecycle-ordered path
    through the tool."""
    # Bucket analytics by phase
    by_phase: Dict[str, List[Dict[str, Any]]] = {}
    for a in _ANALYTICS:
        phase = a.get("phase", "DILIGENCE")
        by_phase.setdefault(phase, []).append(a)

    sections: List[str] = []
    for phase in _PHASE_ORDER:
        if phase not in by_phase:
            continue
        meta = _PHASE_META.get(phase, {"label": phase, "subtitle": "", "tone": "text_dim"})
        tone_color = P.get(meta["tone"], P["text_dim"])
        tile_htmls = [
            _analytic_card(slug, a) for a in by_phase[phase]
        ]
        sections.append(
            f'<div style="margin-bottom:22px;">'
            f'<div style="display:flex;align-items:baseline;gap:12px;'
            f'margin-bottom:10px;padding-left:10px;'
            f'border-left:3px solid {tone_color};">'
            f'<div style="font-size:11px;color:{P["text"]};font-weight:700;'
            f'letter-spacing:1.2px;text-transform:uppercase;">'
            f'{html.escape(meta["label"])}</div>'
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'font-style:italic;">{html.escape(meta["subtitle"])}</div>'
            f'<div style="flex:1;"></div>'
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'letter-spacing:1px;font-variant-numeric:tabular-nums;">'
            f'{len(by_phase[phase])} '
            f'{"analytic" if len(by_phase[phase]) == 1 else "analytics"}'
            f'</div>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fill,'
            f'minmax(280px,1fr));gap:12px;">'
            + "".join(tile_htmls) +
            f'</div>'
            f'</div>'
        )
    return "".join(sections)


def _render_thesis_snapshot(slug: str) -> str:
    """The visual investment story — live-updated from localStorage.

    Shows 4 KPI tiles (EV / Revenue / EBITDA / Implied EV/EBITDA),
    a deal-structure bar (equity vs debt), and a one-sentence
    auto-thesis.  All values are populated by the inline JS from
    localStorage; empty-state shows "Enter deal parameters below".
    """
    return (
        f'<div data-rcm-thesis-snapshot style="margin-bottom:20px;'
        f'background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:18px 22px;position:relative;'
        f'overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{P["accent"]},{P["positive"]});">'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:14px;">'
        f'<div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">'
        f'Investment Thesis</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.55;margin-top:4px;max-width:720px;" '
        f'data-rcm-thesis-narrative>'
        f'Enter deal parameters below to populate the thesis snapshot.'
        f'</div>'
        f'</div>'
        f'<div data-rcm-thesis-badge style="font-size:9px;'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:700;'
        f'color:{P["text_faint"]};border:1px solid {P["border"]};'
        f'padding:3px 10px;border-radius:3px;">Awaiting inputs</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        f'minmax(160px,1fr));gap:14px;margin-bottom:14px;">'
        # EV tile
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.4px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">Enterprise value</div>'
        f'<div data-rcm-thesis-ev '
        f'style="font-size:22px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:2px;" data-rcm-thesis-ev-sub></div>'
        f'</div>'
        # Revenue tile
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.4px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">Revenue Y0</div>'
        f'<div data-rcm-thesis-revenue '
        f'style="font-size:22px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:2px;" data-rcm-thesis-rev-sub></div>'
        f'</div>'
        # EBITDA tile
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.4px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">EBITDA Y0</div>'
        f'<div data-rcm-thesis-ebitda '
        f'style="font-size:22px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:2px;" data-rcm-thesis-margin-sub></div>'
        f'</div>'
        # Multiple tile
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.4px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">Entry EV / EBITDA</div>'
        f'<div data-rcm-thesis-multiple '
        f'style="font-size:22px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:2px;" data-rcm-thesis-mult-sub></div>'
        f'</div>'
        f'</div>'
        # Equity / Debt structure bar
        f'<div style="margin-top:6px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:5px;">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.4px;text-transform:uppercase;font-weight:600;">'
        f'Capital structure</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'font-family:\'JetBrains Mono\',monospace;" '
        f'data-rcm-thesis-struct-legend>— equity · — debt</div>'
        f'</div>'
        f'<div style="height:8px;background:{P["panel_alt"]};'
        f'border-radius:4px;overflow:hidden;display:flex;">'
        f'<div data-rcm-thesis-equity-bar '
        f'style="height:100%;width:0%;background:{P["positive"]};'
        f'transition:width 250ms ease;"></div>'
        f'<div data-rcm-thesis-debt-bar '
        f'style="height:100%;width:0%;background:{P["warning"]};'
        f'transition:width 250ms ease;"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _render_market_context(slug: str) -> str:
    """Live market-context card — JS fetches the peer snapshot from
    ``/api/market-intel/peer-snapshot`` whenever the user changes the
    market_category, enterprise_value_usd, revenue_usd, or ebitda_usd
    fields.  Surfaces target-vs-peer multiple delta + named top peers
    + sentiment + assessment band."""
    return (
        f'<div data-rcm-market-context style="margin-bottom:20px;'
        f'background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:16px 20px;position:relative;'
        f'overflow:hidden;display:none;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{P["accent"]},{P["warning"]});">'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:10px;gap:12px;">'
        f'<div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">'
        f'Market Context · live from public comps</div>'
        f'<div data-rcm-market-summary '
        f'style="font-size:12.5px;color:{P["text_dim"]};line-height:1.6;'
        f'margin-top:4px;max-width:720px;"></div>'
        f'</div>'
        f'<div data-rcm-market-assessment style="font-size:10px;'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:700;'
        f'padding:4px 10px;border:1px solid currentColor;border-radius:3px;'
        f'color:{P["text_faint"]};white-space:nowrap;">—</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        f'minmax(140px,1fr));gap:12px;margin-top:6px;">'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:3px;">Target implied</div>'
        f'<div data-rcm-market-target-mult '
        f'style="font-size:20px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:9.5px;color:{P["text_faint"]};'
        f'margin-top:2px;">EV / EBITDA</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:3px;">Peer median</div>'
        f'<div data-rcm-market-peer-median '
        f'style="font-size:20px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:9.5px;color:{P["text_faint"]};'
        f'margin-top:2px;" data-rcm-market-band-range></div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:3px;">Delta vs peer</div>'
        f'<div data-rcm-market-delta '
        f'style="font-size:20px;font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;">—</div>'
        f'<div style="font-size:9.5px;color:{P["text_faint"]};'
        f'margin-top:2px;">turns of EBITDA</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.3px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:3px;">Closest peers</div>'
        f'<div data-rcm-market-peers '
        f'style="font-size:12px;color:{P["text"]};line-height:1.5;'
        f'font-family:\'JetBrains Mono\',monospace;">—</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _render_lifecycle_ribbon(slug: str) -> str:
    """5-phase lifecycle progress visual.

    Segments: Screening → Diligence → Risk → Financial → Delivery.
    Each segment shows the phase name, subtitle, and analytic count.
    Inline JS can later color-code based on checklist coverage.
    """
    order = ("SCREENING", "DILIGENCE", "RISK", "FINANCIAL", "DELIVERY")
    # Count analytics per phase for the badge
    per_phase: Dict[str, int] = {}
    for a in _ANALYTICS:
        per_phase[a.get("phase", "DILIGENCE")] = (
            per_phase.get(a.get("phase", "DILIGENCE"), 0) + 1
        )
    segments: List[str] = []
    for i, phase in enumerate(order):
        meta = _PHASE_META[phase]
        tone_color = P.get(meta["tone"], P["text_dim"])
        count = per_phase.get(phase, 0)
        segments.append(
            f'<div data-rcm-phase="{phase}" '
            f'style="flex:1;padding:12px 14px;background:{P["panel"]};'
            f'border:1px solid {P["border"]};border-left:3px solid {tone_color};'
            f'border-radius:4px;position:relative;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;margin-bottom:2px;">'
            f'<div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.2px;font-family:\'JetBrains Mono\',monospace;'
            f'font-weight:700;">{i + 1:02d}</div>'
            f'<div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1px;">{count} '
            f'{"analytic" if count == 1 else "analytics"}</div>'
            f'</div>'
            f'<div style="font-size:11.5px;color:{P["text"]};font-weight:700;'
            f'letter-spacing:.2px;">{html.escape(meta["label"])}</div>'
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'line-height:1.4;margin-top:2px;">'
            f'{html.escape(meta["subtitle"])}</div>'
            f'</div>'
        )
    return (
        f'<div style="display:flex;gap:8px;margin-bottom:22px;'
        f'flex-wrap:wrap;">{"".join(segments)}</div>'
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
  function updateThesisSnapshot(data) {
    function fmtUSD(n) {
      if (n == null || isNaN(n)) return '—';
      var abs = Math.abs(n);
      if (abs >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
      if (abs >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
      if (abs >= 1e3) return '$' + (n / 1e3).toFixed(0) + 'K';
      return '$' + n.toFixed(0);
    }
    var num = function(k) {
      var v = parseFloat(data[k]);
      return isNaN(v) ? null : v;
    };
    var ev = num('enterprise_value_usd');
    var equity = num('equity_usd');
    var debt = num('debt_usd');
    var rev = num('revenue_usd');
    var ebitda = num('ebitda_usd');
    var mult = num('entry_multiple');
    var impliedMult = (ev != null && ebitda != null && ebitda > 0)
      ? (ev / ebitda) : null;

    var setText = function(sel, txt) {
      var el = document.querySelector(sel);
      if (el) el.textContent = txt;
    };
    var setWidth = function(sel, pct) {
      var el = document.querySelector(sel);
      if (el) el.style.width = Math.max(0, Math.min(100, pct)) + '%';
    };

    setText('[data-rcm-thesis-ev]', fmtUSD(ev));
    setText('[data-rcm-thesis-revenue]', fmtUSD(rev));
    setText('[data-rcm-thesis-ebitda]', fmtUSD(ebitda));
    // EV sub-line: equity + debt share
    var evSub = '';
    if (equity != null && debt != null && ev != null && ev > 0) {
      evSub = 'equity ' + Math.round(equity / ev * 100) + '% · debt ' +
        Math.round(debt / ev * 100) + '%';
    }
    setText('[data-rcm-thesis-ev-sub]', evSub);
    // Revenue sub-line: states + specialty if available
    var revSub = [data.specialty, (data.states || '').split(',')[0]]
      .filter(Boolean).join(' · ');
    setText('[data-rcm-thesis-rev-sub]', revSub);
    // EBITDA margin sub-line
    var marginSub = '';
    if (ebitda != null && rev != null && rev > 0) {
      marginSub = 'margin ' + (ebitda / rev * 100).toFixed(1) + '%';
    }
    setText('[data-rcm-thesis-margin-sub]', marginSub);
    // Entry multiple
    if (mult != null) {
      setText('[data-rcm-thesis-multiple]', mult.toFixed(1) + 'x');
      if (impliedMult != null && Math.abs(impliedMult - mult) > 0.5) {
        setText('[data-rcm-thesis-mult-sub]',
          'implied ' + impliedMult.toFixed(1) + 'x from EV/EBITDA');
      } else {
        setText('[data-rcm-thesis-mult-sub]', '');
      }
    } else if (impliedMult != null) {
      setText('[data-rcm-thesis-multiple]', impliedMult.toFixed(1) + 'x');
      setText('[data-rcm-thesis-mult-sub]', 'derived from EV ÷ EBITDA');
    } else {
      setText('[data-rcm-thesis-multiple]', '—');
      setText('[data-rcm-thesis-mult-sub]', '');
    }
    // Capital structure bar
    if (equity != null && debt != null && (equity + debt) > 0) {
      var total = equity + debt;
      setWidth('[data-rcm-thesis-equity-bar]', equity / total * 100);
      setWidth('[data-rcm-thesis-debt-bar]', debt / total * 100);
      setText('[data-rcm-thesis-struct-legend]',
        fmtUSD(equity) + ' equity · ' + fmtUSD(debt) + ' debt');
    } else {
      setWidth('[data-rcm-thesis-equity-bar]', 0);
      setWidth('[data-rcm-thesis-debt-bar]', 0);
      setText('[data-rcm-thesis-struct-legend]', '— equity · — debt');
    }
    // One-line auto-thesis narrative
    var bits = [];
    if (data.deal_name) bits.push(data.deal_name);
    var sizing = [];
    if (rev != null) sizing.push(fmtUSD(rev) + ' revenue');
    if (ebitda != null) sizing.push(fmtUSD(ebitda) + ' EBITDA');
    if (sizing.length) bits.push(sizing.join(' / '));
    var loc = [];
    if (data.specialty) loc.push(data.specialty.replace(/_/g, ' ').toLowerCase());
    if (data.states) loc.push('in ' + data.states);
    if (loc.length) bits.push(loc.join(' '));
    if (data.landlord) bits.push(data.landlord + ' tenant');
    var narrative = bits.length
      ? bits.join(' · ') + '.'
      : 'Enter deal parameters below to populate the thesis snapshot.';
    setText('[data-rcm-thesis-narrative]', narrative);
    // Badge — colored by stage of input completeness
    var badge = document.querySelector('[data-rcm-thesis-badge]');
    if (badge) {
      var keys = Object.keys(data).filter(function(k) {
        return k !== '__saved_at' && data[k] !== '' && data[k] != null;
      });
      var completion = keys.length;
      if (completion === 0) {
        badge.textContent = 'Awaiting inputs';
        badge.style.color = '#64748b';
        badge.style.borderColor = '#1e293b';
      } else if (ev != null && rev != null && ebitda != null) {
        badge.textContent = 'Ready for pipeline';
        badge.style.color = '#10b981';
        badge.style.borderColor = '#10b981';
      } else {
        badge.textContent = completion + ' of 24 fields';
        badge.style.color = '#f59e0b';
        badge.style.borderColor = '#f59e0b';
      }
    }
  }

  // ── Market Context (live peer snapshot) ────────────────────
  var marketCtxTimer = null;
  var marketCtxLastKey = '';
  function updateMarketContext(data) {
    var el = document.querySelector('[data-rcm-market-context]');
    if (!el) return;
    var category = data.market_category || '';
    var ev = data.enterprise_value_usd || '';
    var rev = data.revenue_usd || '';
    var ebitda = data.ebitda_usd || '';
    var specialty = data.specialty || '';
    if (!category || (!ev && !rev)) {
      el.style.display = 'none';
      return;
    }
    // Debounce: only fetch when inputs actually change.
    var key = [category, ev, rev, ebitda, specialty].join('|');
    if (key === marketCtxLastKey) return;
    marketCtxLastKey = key;
    clearTimeout(marketCtxTimer);
    marketCtxTimer = setTimeout(function() {
      var qs = new URLSearchParams({
        category: category,
      });
      if (ev) qs.set('ev_usd', ev);
      if (rev) qs.set('revenue_usd', rev);
      if (ebitda) qs.set('ebitda_usd', ebitda);
      if (specialty) qs.set('specialty', specialty);
      fetch('/api/market-intel/peer-snapshot?' + qs.toString())
        .then(function(r) { return r.json(); })
        .then(function(snap) {
          renderMarketContext(snap);
        })
        .catch(function() {
          el.style.display = 'none';
        });
    }, 250);
  }

  function renderMarketContext(snap) {
    var el = document.querySelector('[data-rcm-market-context]');
    if (!el) return;
    if (!snap || snap.assessment === 'NO_DATA') {
      el.style.display = 'none';
      return;
    }
    el.style.display = 'block';
    var setText = function(sel, txt) {
      var n = document.querySelector(sel);
      if (n) n.textContent = txt;
    };
    setText('[data-rcm-market-summary]', snap.summary || '');
    setText(
      '[data-rcm-market-target-mult]',
      snap.target_implied_multiple != null
        ? snap.target_implied_multiple.toFixed(2) + 'x' : '—',
    );
    setText(
      '[data-rcm-market-peer-median]',
      snap.peer_median_ev_ebitda != null
        ? snap.peer_median_ev_ebitda.toFixed(2) + 'x' : '—',
    );
    setText(
      '[data-rcm-market-band-range]',
      (snap.peer_p25_ev_ebitda != null && snap.peer_p75_ev_ebitda != null)
        ? 'p25–p75 ' + snap.peer_p25_ev_ebitda.toFixed(1) + 'x – ' +
          snap.peer_p75_ev_ebitda.toFixed(1) + 'x'
        : '',
    );
    var deltaEl = document.querySelector('[data-rcm-market-delta]');
    if (deltaEl) {
      if (snap.delta_vs_median_turns == null) {
        deltaEl.textContent = '—';
        deltaEl.style.color = '#94a3b8';
      } else {
        var dv = snap.delta_vs_median_turns;
        deltaEl.textContent = (dv > 0 ? '+' : '') + dv.toFixed(2) + 'x';
        deltaEl.style.color = dv > 0.5 ? '#ef4444'
          : dv < -0.5 ? '#10b981' : '#94a3b8';
      }
    }
    var peerNames = (snap.peers || []).map(function(p) {
      return p.ticker + ' ' + p.ev_ebitda_multiple.toFixed(1) + 'x';
    }).join(' · ');
    setText('[data-rcm-market-peers]', peerNames || '—');
    // Assessment pill
    var asEl = document.querySelector('[data-rcm-market-assessment]');
    if (asEl) {
      asEl.textContent = snap.assessment || '—';
      asEl.style.color = {
        'DISCOUNT': '#10b981',
        'IN-LINE': '#3b82f6',
        'PREMIUM': '#ef4444',
      }[snap.assessment] || '#94a3b8';
    }
  }

  function updateLinks() {
    var data = collect();
    // Thesis snapshot live update
    updateThesisSnapshot(data);
    // Market context live update
    updateMarketContext(data);
    // Special-case the Run-Pipeline CTA: it wants every param the
    // pipeline accepts, so we encode the full profile.
    var pipelineCta = document.querySelector('[data-rcm-run-pipeline]');
    if (pipelineCta) {
      var pipelineQs = [];
      Object.keys(data).forEach(function(k) {
        if (k === '__saved_at') return;
        var v = data[k];
        if (v == null || v === '') return;
        // The pipeline renderer accepts both *_usd and *_year0_usd
        // aliases; send the canonical key names.
        pipelineQs.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
      });
      pipelineCta.href = pipelineQs.length
        ? '/diligence/thesis-pipeline?' + pipelineQs.join('&')
        : '/diligence/thesis-pipeline';
    }
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
    # Prominent "Run Full Pipeline" CTA — the single highest-leverage
    # button on the page.  Inline JS reads localStorage for this
    # slug and builds the pipeline URL with all fields pre-seeded.
    pipeline_cta = (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["accent"]};border-radius:4px;padding:16px 20px;'
        f'margin-bottom:20px;display:flex;justify-content:space-between;'
        f'align-items:center;gap:16px;flex-wrap:wrap;position:relative;'
        f'overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{P["positive"]},{P["accent"]});">'
        f'</div>'
        f'<div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;">'
        f'Thesis Pipeline</div>'
        f'<div style="font-size:16px;color:{P["text"]};font-weight:600;'
        f'margin-top:2px;">One-button full diligence chain</div>'
        f'<div style="font-size:11px;color:{P["text_dim"]};margin-top:4px;'
        f'line-height:1.5;max-width:600px;">'
        f'Runs bankruptcy scan → CCD ingest → HFMA benchmarks → denial '
        f'prediction → PPAM → counterfactual → Steward → cyber → '
        f'deal autopsy → Deal MC in one step. Feeds IC Packet with '
        f'every headline number.</div>'
        f'</div>'
        f'<a data-rcm-run-pipeline href="/diligence/thesis-pipeline" '
        f'style="padding:12px 22px;background:{P["accent"]};'
        f'color:{P["panel"]};border:0;font-size:11px;letter-spacing:1.5px;'
        f'text-transform:uppercase;font-weight:700;cursor:pointer;'
        f'border-radius:3px;text-decoration:none;white-space:nowrap;">'
        f'▶ Run Full Pipeline</a>'
        f'</div>'
    )
    thesis_snapshot = _render_thesis_snapshot(slug)
    market_context = _render_market_context(slug)
    lifecycle = _render_lifecycle_ribbon(slug)
    form = _render_form(slug, seed_values)
    grid = _render_analytics_grid(slug)
    grid_header = (
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:14px;margin-top:10px;">'
        f'Open in Analytic · grouped by lifecycle phase</div>'
    )
    return chartis_shell(
        hero + intro + thesis_snapshot + market_context + pipeline_cta
        + lifecycle + form + grid_header + grid
        + bookmark_hint() + _inline_js(slug),
        f"Deal Profile — {slug}",
        subtitle="One source of truth",
    )
