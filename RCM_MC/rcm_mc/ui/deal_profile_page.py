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
from ._chartis_kit import (
    P, chartis_shell, ck_eyebrow, ck_help_tooltip, ck_next_section,
    ck_panel, ck_section_header, ck_section_intro, ck_signal_badge,
    ck_sticky_toc,
)
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
        '<div class="ck-dp-saved-empty">' +
        'No saved deals yet. Enter a slug above to ' +
        'create your first profile — it will appear here on subsequent ' +
        'visits.</div>';
      return;
    }
    var cards = deals.map(function(d) {
      var completion = Math.min(100, Math.round(d.filled / 24 * 100));
      var barColor = completion >= 75 ? 'var(--green)' :
        completion >= 40 ? 'var(--amber)' : 'var(--muted)';
      var name = (d.name || d.slug).replace(/</g, '&lt;');
      var slug = d.slug.replace(/</g, '&lt;');
      var safeSlug = encodeURIComponent(d.slug);
      return (
        '<div class="ck-dp-saved-card">' +
        '<div class="ck-dp-saved-row">' +
        '<div class="ck-dp-saved-slug">' + slug + '</div>' +
        '<div class="ck-dp-saved-rel">' + fmtRelative(d.saved_at) + '</div>' +
        '</div>' +
        '<div class="ck-dp-saved-name">' + name + '</div>' +
        '<div class="ck-dp-saved-bar">' +
        '<div class="ck-dp-saved-bar-fill" style="width:' + completion +
        '%;--bar-tone:' + barColor + ';"></div></div>' +
        '<div class="ck-dp-saved-progress">' + d.filled +
        ' of 24 fields · ' + completion + '% complete</div>' +
        '<div class="ck-dp-saved-actions">' +
        '<a href="/diligence/deal/' + safeSlug + '" ' +
        'class="ck-dp-saved-btn">Open</a>' +
        '<button type="button" data-rcm-duplicate="' + safeSlug + '" ' +
        'class="ck-dp-saved-btn-secondary">Duplicate</button>' +
        '<button type="button" data-rcm-delete="' + safeSlug + '" ' +
        'class="ck-dp-saved-btn-danger">Delete</button>' +
        '</div></div>'
      );
    }).join('');
    root.innerHTML =
      '<div class="ck-dp-saved-header">Your saved deals · ' +
      deals.length + ' local profile' +
      (deals.length === 1 ? '' : 's') + '</div>' +
      '<div class="ck-dp-saved-grid">' + cards + '</div>';
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


_DP_STYLES = f"""
<style>
.ck-dp-slug-form{{max-width:480px;}}
.ck-dp-recent-deals{{margin-top:1.75rem;max-width:960px;}}
.ck-dp-tool-chip{{font-size:8px;letter-spacing:.5px;text-transform:uppercase;
color:{P["text_faint"]};background:{P["panel_alt"]};padding:1px 5px;
border-radius:2px;margin-right:3px;}}
.ck-dp-input{{width:100%;padding:6px 8px;background:{P["panel_alt"]};
color:{P["text"]};border:1px solid {P["border"]};
font-family:inherit;font-size:11px;}}
.ck-dp-field-label{{font-size:9px;color:{P["text_faint"]};letter-spacing:1px;
text-transform:uppercase;font-weight:600;display:block;margin-bottom:3px;}}
.ck-dp-field-chips{{margin-top:3px;line-height:1.5;}}
.ck-dp-form{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px 16px;
background:{P["panel"]};border:1px solid {P["border"]};border-radius:4px;
padding:16px 20px;margin-bottom:24px;}}
.ck-dp-form-actions{{grid-column:span 3;display:flex;gap:10px;align-items:center;
margin-top:6px;}}
.ck-dp-btn-save{{padding:8px 18px;background:{P["accent"]};color:{P["panel"]};
border:0;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
font-weight:700;cursor:pointer;}}
.ck-dp-btn-clear{{padding:8px 18px;background:transparent;color:{P["text_dim"]};
border:1px solid {P["border"]};font-size:10px;letter-spacing:1.5px;
text-transform:uppercase;font-weight:600;cursor:pointer;}}
.ck-dp-saved-at{{font-size:10px;color:{P["text_faint"]};margin-left:10px;letter-spacing:.5px;}}
.ck-dp-card{{display:block;background:{P["panel"]};border:1px solid {P["border"]};
border-radius:4px;padding:14px 16px;text-decoration:none;
transition:transform 140ms ease,border-color 140ms ease,box-shadow 140ms ease;}}
.ck-dp-card:hover{{transform:translateY(-1px);border-color:{P["text_faint"]};
box-shadow:0 6px 18px rgba(0,0,0,0.30);}}
.ck-dp-card-head{{display:flex;justify-content:space-between;align-items:baseline;
margin-bottom:6px;}}
.ck-dp-card-title{{font-size:13px;color:{P["text"]};font-weight:600;letter-spacing:-.1px;}}
.ck-dp-card-badge{{font-size:8px;letter-spacing:1.1px;text-transform:uppercase;
color:{P["text_faint"]};background:{P["panel_alt"]};padding:2px 6px;
border-radius:2px;font-weight:700;}}
.ck-dp-card-detail{{font-size:11px;color:{P["text_dim"]};line-height:1.55;}}
.ck-dp-card-state{{margin-top:8px;font-family:"Source Serif 4",serif;
font-style:italic;font-size:10.5px;color:{P["text_faint"]};
display:flex;align-items:baseline;gap:6px;}}
.ck-dp-card-state[hidden]{{display:none !important;}}
.ck-dp-card-state-dot{{width:5px;height:5px;border-radius:50%;
background:{P["accent"]};display:inline-block;flex-shrink:0;}}
/* Diligence-questions inline editor. Partner-curated list inside a
 * ck_panel on the deal profile. Editorial: parchment surface +
 * serif italic body + mono caps timestamp + small inline form.
 * Hidden in @media print so working notes don't end up on LP
 * deliverables. */
.ck-dp-qs{{}}
.ck-dp-qs-intro{{margin-bottom:14px;}}
.ck-dp-qs-form{{display:flex;gap:10px;align-items:stretch;
margin-bottom:14px;}}
.ck-dp-qs-input{{flex:1;padding:9px 12px;
background:{P["panel_alt"]};color:{P["text"]};
border:1px solid {P["border"]};border-radius:3px;
font-family:"Source Serif 4",serif;font-size:13px;
transition:border-color 120ms ease, box-shadow 120ms ease;}}
.ck-dp-qs-input:focus{{outline:none;
border-color:{P["accent"]};
box-shadow:0 0 0 2px rgba(21,87,82,0.18);}}
.ck-dp-qs-cat{{padding:9px 10px;
background:{P["panel_alt"]};color:{P["text"]};
border:1px solid {P["border"]};border-radius:3px;
font-family:"Inter Tight",sans-serif;font-size:11px;font-weight:600;
letter-spacing:0.06em;cursor:pointer;
appearance:none;-webkit-appearance:none;
background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%236e7787' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E");
background-repeat:no-repeat;background-position:right 8px center;
padding-right:26px;}}
.ck-dp-qs-cat:focus{{outline:none;border-color:{P["accent"]};
box-shadow:0 0 0 2px rgba(21,87,82,0.18);}}
.ck-dp-qs-add{{padding:9px 16px;
background:{P["accent"]};color:#fff;border:0;border-radius:3px;
font-family:"Inter Tight",sans-serif;font-size:11px;font-weight:700;
letter-spacing:0.12em;text-transform:uppercase;cursor:pointer;
transition:filter 120ms ease;white-space:nowrap;}}
.ck-dp-qs-add:hover{{filter:brightness(1.08);}}
/* Category pill — small caps chip rendered before the question
 * text on each row. Six categories map to editorial tones from the
 * shared palette; "Other" stays neutral so unfamiliar inputs don't
 * grab visual weight. */
.ck-dp-qs-pill{{display:inline-block;padding:1px 7px;margin-right:8px;
font-family:"Inter Tight",sans-serif;font-size:9px;font-weight:700;
letter-spacing:0.16em;text-transform:uppercase;
border-radius:2px;vertical-align:1px;
border:1px solid currentColor;}}
.ck-dp-qs-pill.cat-financial{{color:{P["accent"]};}}
.ck-dp-qs-pill.cat-clinical{{color:{P["positive"]};}}
.ck-dp-qs-pill.cat-regulatory{{color:{P["warning"]};}}
.ck-dp-qs-pill.cat-legal{{color:{P["text_dim"]};}}
.ck-dp-qs-pill.cat-operational{{color:{P["text"]};}}
.ck-dp-qs-pill.cat-other{{color:{P["text_faint"]};}}
.ck-dp-qs-empty[hidden]{{display:none !important;}}
.ck-dp-qs-list{{list-style:none;margin:0;padding:0;}}
.ck-dp-qs-row{{display:grid;
grid-template-columns:24px 1fr auto auto;gap:12px;
align-items:baseline;padding:12px 0;
border-bottom:1px solid {P["border"]};}}
.ck-dp-qs-row:last-child{{border-bottom:0;}}
.ck-dp-qs-row-num{{font-family:"JetBrains Mono",monospace;
font-size:10px;font-weight:700;letter-spacing:0.12em;
color:{P["text_faint"]};text-align:right;
align-self:center;}}
.ck-dp-qs-row-text{{font-family:"Source Serif 4",serif;
font-size:14px;line-height:1.5;color:{P["text"]};
font-style:italic;}}
.ck-dp-qs-row.is-asked .ck-dp-qs-row-text{{
text-decoration:line-through;color:{P["text_faint"]};}}
.ck-dp-qs-row-ts{{font-family:"Source Serif 4",serif;font-style:italic;
font-size:11px;color:{P["text_faint"]};
align-self:center;white-space:nowrap;}}
.ck-dp-qs-row-actions{{display:flex;gap:6px;align-self:center;}}
.ck-dp-qs-row-btn{{background:none;border:1px solid {P["border"]};
border-radius:3px;padding:3px 8px;cursor:pointer;
font-family:"Inter Tight",sans-serif;font-size:9px;
font-weight:600;letter-spacing:0.12em;text-transform:uppercase;
color:{P["text_dim"]};
transition:border-color 120ms ease, color 120ms ease;}}
.ck-dp-qs-row-btn:hover{{border-color:{P["text"]};color:{P["text"]};}}
.ck-dp-qs-row-btn-asked.is-active{{
background:{P["positive"]};color:#fff;border-color:{P["positive"]};}}
.ck-dp-qs-row-btn-remove:hover{{
border-color:{P["negative"]};color:{P["negative"]};}}
.ck-dp-qs-meta-row{{display:flex;align-items:baseline;
justify-content:space-between;gap:14px;flex-wrap:wrap;
margin-top:14px;padding-top:12px;
border-top:1px solid {P["border"]};}}
.ck-dp-qs-meta-row[hidden]{{display:none !important;}}
.ck-dp-qs-meta{{font-family:"Source Serif 4",serif;
font-style:italic;font-size:11px;color:{P["text_faint"]};}}
.ck-dp-qs-export{{display:flex;align-items:baseline;
gap:6px;flex-wrap:wrap;}}
.ck-dp-qs-export-btn{{background:none;border:1px solid {P["border"]};
border-radius:3px;padding:5px 10px;cursor:pointer;
font-family:"Source Serif 4",serif;font-size:11.5px;
font-style:italic;color:{P["text_dim"]};
transition:border-color 120ms ease, color 120ms ease;}}
.ck-dp-qs-export-btn:hover{{border-color:{P["accent"]};
color:{P["accent"]};}}
.ck-dp-qs-export-toast{{font-family:"Source Serif 4",serif;
font-style:italic;font-size:11.5px;color:{P["positive"]};
margin-left:6px;align-self:center;
opacity:0;transition:opacity 200ms ease;}}
.ck-dp-qs-export-toast.is-visible{{opacity:1;}}
.ck-dp-qs-export-toast[hidden]{{display:none !important;}}
@media print {{.ck-dp-qs{{display:none !important;}}}}

/* "Compare with…" disclosure on the deal-profile hero. Editorial
   native <details>/<summary> styled with a serif label + JetBrains-
   Mono caret + parchment menu surface. JS populates the inner list
   from rcm_recent_deals (minus the current slug) on every open. */
.ck-dp-cmpw{{position:relative;display:inline-block;}}
.ck-dp-cmpw-summary{{list-style:none;cursor:pointer;
font-family:"Source Serif 4",serif;font-size:13.5px;
color:{P["accent"]};padding:6px 12px;border:1px solid {P["border"]};
border-radius:3px;background:{P["panel"]};
display:inline-flex;align-items:baseline;gap:6px;
transition:border-color 120ms ease, background 120ms ease;
user-select:none;}}
.ck-dp-cmpw-summary::-webkit-details-marker{{display:none;}}
.ck-dp-cmpw-summary:hover{{border-color:{P["accent"]};
background:{P["panel_alt"]};}}
.ck-dp-cmpw-caret{{font-family:"JetBrains Mono",monospace;
font-size:10px;color:{P["text_faint"]};
transition:transform 160ms ease;}}
.ck-dp-cmpw[open] .ck-dp-cmpw-caret{{transform:rotate(180deg);}}
.ck-dp-cmpw-menu{{position:absolute;top:calc(100% + 6px);left:0;
min-width:300px;max-width:400px;
background:{P["panel"]};border:1px solid {P["border"]};
border-radius:3px;box-shadow:0 12px 32px rgba(11,35,65,0.12);
padding:10px 0;z-index:20;
font-family:"Source Serif 4",serif;}}
.ck-dp-cmpw-empty{{padding:12px 16px;font-style:italic;
font-size:13px;color:{P["text_faint"]};max-width:34ch;
line-height:1.5;}}
.ck-dp-cmpw-list{{list-style:none;margin:0;padding:0;}}
.ck-dp-cmpw-row{{}}
.ck-dp-cmpw-link{{display:flex;align-items:baseline;
justify-content:space-between;gap:14px;
padding:10px 16px;text-decoration:none;color:inherit;
transition:background 120ms ease;}}
.ck-dp-cmpw-link:hover{{background:{P["panel_alt"]};}}
.ck-dp-cmpw-link-name{{font-size:14px;color:{P["text"]};
font-weight:500;}}
.ck-dp-cmpw-link-name em{{font-style:italic;color:{P["accent"]};}}
.ck-dp-cmpw-q{{font-family:"Inter Tight",sans-serif;font-size:9px;
font-weight:700;letter-spacing:0.14em;text-transform:uppercase;
color:{P["warning"]};border:1px solid currentColor;border-radius:2px;
padding:1px 6px;margin-left:8px;vertical-align:1px;
white-space:nowrap;}}
.ck-dp-cmpw-link-slug{{font-family:"JetBrains Mono",monospace;
font-size:10px;letter-spacing:0.12em;text-transform:uppercase;
color:{P["text_faint"]};}}
.ck-dp-cmpw-disabled{{padding:10px 16px;font-style:italic;
font-size:12px;color:{P["text_faint"]};
border-top:1px solid {P["border"]};margin-top:4px;
max-width:34ch;line-height:1.5;}}
@media print{{.ck-dp-cmpw{{display:none !important;}}}}

.ck-dp-pulse{{margin:16px 0 22px;padding:18px 22px;
background:{P["panel_alt"]};border:1px solid {P["border"]};
border-radius:4px;}}
.ck-dp-pulse[hidden]{{display:none !important;}}
.ck-dp-pulse-head{{display:flex;align-items:baseline;
justify-content:space-between;gap:14px;margin-bottom:14px;}}
.ck-dp-pulse-eyebrow{{font-family:"Inter Tight",sans-serif;
font-size:10px;font-weight:700;letter-spacing:1.4px;
text-transform:uppercase;color:{P["text_faint"]};}}
.ck-dp-pulse-meta{{font-family:"Source Serif 4",serif;
font-style:italic;font-size:12px;color:{P["text_faint"]};}}
.ck-dp-pulse-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:24px;
align-items:end;}}
.ck-dp-pulse-tile{{}}
.ck-dp-pulse-val{{font-family:"JetBrains Mono",monospace;
font-size:26px;font-weight:700;color:{P["text"]};line-height:1;
font-variant-numeric:tabular-nums;margin-bottom:8px;}}
.ck-dp-pulse-val-serif{{font-family:"Source Serif 4",serif;
font-weight:500;font-size:18px;letter-spacing:-0.005em;
color:{P["text"]};}}
.ck-dp-pulse-lbl{{font-family:"Inter Tight",sans-serif;
font-size:10px;font-weight:700;letter-spacing:1.4px;
text-transform:uppercase;color:{P["text_faint"]};margin-bottom:4px;}}
.ck-dp-pulse-sub{{font-family:"Source Serif 4",serif;font-style:italic;
font-size:11px;color:{P["text_faint"]};}}
.ck-dp-pulse-bar{{height:8px;background:{P["panel"]};
border:1px solid {P["border"]};border-radius:4px;overflow:hidden;
margin-bottom:8px;}}
.ck-dp-pulse-bar-fill{{height:100%;width:0%;
background:{P["accent"]};
transition:width 320ms ease;}}
@media print{{.ck-dp-pulse{{display:none !important;}}}}

.ck-dp-card{{position:relative;}}
.ck-dp-card-pin{{position:absolute;top:8px;right:8px;
background:none;border:0;padding:4px 6px;cursor:pointer;
font-size:14px;line-height:1;color:{P["text_faint"]};
transition:color 120ms ease, transform 120ms ease;
z-index:2;}}
.ck-dp-card-pin:hover{{color:{P["accent"]};transform:scale(1.1);}}
.ck-dp-card-pin[aria-pressed="true"]{{color:{P["accent"]};}}
.ck-dp-card-pin[aria-pressed="true"] .ck-dp-card-pin-icon::before{{content:"★";}}
.ck-dp-card-pin[aria-pressed="true"] .ck-dp-card-pin-icon{{font-size:0;}}
@media print {{.ck-dp-card-pin{{display:none !important;}}}}
.ck-dp-card-preview{{font-size:10px;color:{P["text_faint"]};margin-top:8px;
font-family:"JetBrains Mono",monospace;letter-spacing:.3px;word-break:break-all;}}
.ck-dp-phase-section{{margin-bottom:22px;}}
.ck-dp-phase-head{{display:flex;align-items:baseline;gap:12px;
margin-bottom:10px;padding-left:10px;border-left:3px solid {P["text_dim"]};}}
.ck-dp-phase-label{{font-size:11px;color:{P["text"]};font-weight:700;
letter-spacing:1.2px;text-transform:uppercase;}}
.ck-dp-phase-subtitle{{font-size:10px;color:{P["text_faint"]};font-style:italic;}}
.ck-dp-phase-spacer{{flex:1;}}
.ck-dp-phase-count{{font-size:10px;color:{P["text_faint"]};
letter-spacing:1px;font-variant-numeric:tabular-nums;}}
.ck-dp-card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;}}
.ck-dp-thesis-card{{margin-bottom:20px;background:{P["panel"]};
border:1px solid {P["border"]};border-radius:4px;padding:18px 22px;
position:relative;overflow:hidden;}}
.ck-dp-thesis-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:2px;background:linear-gradient(90deg,{P["accent"]},{P["positive"]});}}
.ck-dp-thesis-head{{display:flex;justify-content:space-between;
align-items:baseline;margin-bottom:14px;}}
.ck-dp-thesis-eyebrow{{font-size:10px;color:{P["text_faint"]};
letter-spacing:1.5px;text-transform:uppercase;font-weight:700;}}
.ck-dp-thesis-narrative{{font-size:13px;color:{P["text_dim"]};
line-height:1.55;margin-top:4px;max-width:720px;}}
.ck-dp-thesis-badge{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
font-weight:700;color:{P["text_faint"]};border:1px solid {P["border"]};
padding:3px 10px;border-radius:3px;}}
.ck-dp-thesis-tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:14px;margin-bottom:14px;}}
.ck-dp-thesis-tile-label{{font-size:9px;color:{P["text_faint"]};
letter-spacing:1.4px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.ck-dp-thesis-tile-val{{font-size:22px;color:{P["text"]};font-weight:700;
font-family:"JetBrains Mono",monospace;font-variant-numeric:tabular-nums;}}
.ck-dp-thesis-tile-sub{{font-size:10px;color:{P["text_faint"]};margin-top:2px;}}
.ck-dp-thesis-struct{{margin-top:6px;}}
.ck-dp-thesis-struct-head{{display:flex;justify-content:space-between;
align-items:baseline;margin-bottom:5px;}}
.ck-dp-thesis-struct-label{{font-size:9px;color:{P["text_faint"]};
letter-spacing:1.4px;text-transform:uppercase;font-weight:600;}}
.ck-dp-thesis-struct-legend{{font-size:10px;color:{P["text_faint"]};
font-family:"JetBrains Mono",monospace;}}
.ck-dp-thesis-struct-bar{{height:8px;background:{P["panel_alt"]};
border-radius:4px;overflow:hidden;display:flex;}}
.ck-dp-thesis-equity-bar{{height:100%;width:0%;background:{P["positive"]};
transition:width 250ms ease;}}
.ck-dp-thesis-debt-bar{{height:100%;width:0%;background:{P["warning"]};
transition:width 250ms ease;}}
.ck-dp-market-card{{margin-bottom:20px;background:{P["panel"]};
border:1px solid {P["border"]};border-radius:4px;padding:16px 20px;
position:relative;overflow:hidden;display:none;}}
.ck-dp-market-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:2px;background:linear-gradient(90deg,{P["accent"]},{P["warning"]});}}
.ck-dp-market-head{{display:flex;justify-content:space-between;
align-items:baseline;margin-bottom:10px;gap:12px;}}
.ck-dp-market-eyebrow{{font-size:10px;color:{P["text_faint"]};
letter-spacing:1.5px;text-transform:uppercase;font-weight:700;}}
.ck-dp-market-summary{{font-size:12.5px;color:{P["text_dim"]};
line-height:1.6;margin-top:4px;max-width:720px;}}
.ck-dp-market-assessment{{font-size:10px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;padding:4px 10px;
border:1px solid currentColor;border-radius:3px;
color:{P["text_faint"]};white-space:nowrap;}}
.ck-dp-market-tiles{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
gap:12px;margin-top:6px;}}
.ck-dp-market-tile-label{{font-size:9px;color:{P["text_faint"]};
letter-spacing:1.3px;text-transform:uppercase;font-weight:600;margin-bottom:3px;}}
.ck-dp-market-tile-val{{font-size:20px;color:{P["text"]};font-weight:700;
font-family:"JetBrains Mono",monospace;font-variant-numeric:tabular-nums;}}
.ck-dp-market-tile-sub{{font-size:9.5px;color:{P["text_faint"]};margin-top:2px;}}
.ck-dp-market-peers{{font-size:12px;color:{P["text"]};line-height:1.5;
font-family:"JetBrains Mono",monospace;}}
.ck-dp-lifecycle{{display:flex;gap:8px;margin-bottom:22px;flex-wrap:wrap;}}
.ck-dp-life-seg{{flex:1;padding:12px 14px;background:{P["panel"]};
border:1px solid {P["border"]};border-left:3px solid {P["text_dim"]};
border-radius:4px;position:relative;cursor:pointer;
transition:background 140ms ease, transform 140ms ease, box-shadow 140ms ease;}}
.ck-dp-life-seg:hover{{transform:translateY(-1px);
box-shadow:0 4px 12px rgba(0,0,0,0.06);}}
/* Lifecycle state markers: pending (faded), current (highlighted),
   done (muted-positive). The first phase renders as is-current by
   default; inline JS flips state classes from rcm_deal_<slug>_phase
   in localStorage so the partner's progression persists. */
.ck-dp-life-seg.is-pending{{opacity:.62;}}
.ck-dp-life-seg.is-current{{background:{P["panel_alt"]};
border-color:{P["accent"]};box-shadow:0 0 0 1px {P["accent"]} inset;}}
.ck-dp-life-seg.is-current .ck-dp-life-seg-num{{color:{P["accent"]};}}
.ck-dp-life-seg.is-done{{opacity:.78;}}
.ck-dp-life-seg.is-done::after{{content:"✓";position:absolute;
top:8px;right:10px;font-size:11px;color:{P["positive"]};font-weight:700;}}
.ck-dp-life-seg-head{{display:flex;justify-content:space-between;
align-items:baseline;margin-bottom:2px;}}
.ck-dp-life-seg-num{{font-size:9px;color:{P["text_faint"]};letter-spacing:1.2px;
font-family:"JetBrains Mono",monospace;font-weight:700;}}
.ck-dp-life-seg-count{{font-size:9px;color:{P["text_faint"]};letter-spacing:1px;}}
.ck-dp-life-seg-label{{font-size:11.5px;color:{P["text"]};font-weight:700;letter-spacing:.2px;}}
.ck-dp-life-seg-subtitle{{font-size:10px;color:{P["text_faint"]};line-height:1.4;margin-top:2px;}}
.ck-dp-saved-empty{{padding:1rem 1.25rem;background:var(--paper);
border:1px dashed var(--border);border-radius:3px;color:var(--muted);
font-size:.85rem;line-height:1.5;
font-family:"Source Serif 4",Georgia,serif;font-style:italic;}}
.ck-dp-saved-header{{font-size:10px;color:var(--muted);letter-spacing:1.5px;
text-transform:uppercase;font-weight:700;margin-bottom:10px;}}
.ck-dp-saved-grid{{display:grid;
grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;}}
.ck-dp-saved-card{{background:var(--bg);border:1px solid var(--paper-pure);
border-radius:4px;padding:14px 16px;
transition:border-color 140ms ease, box-shadow 140ms ease;}}
.ck-dp-saved-card:hover{{border-color:var(--muted);
box-shadow:0 4px 14px rgba(0,0,0,0.35);}}
.ck-dp-saved-row{{display:flex;justify-content:space-between;
align-items:baseline;gap:10px;margin-bottom:6px;}}
.ck-dp-saved-slug{{font-size:9px;color:var(--muted);letter-spacing:1.3px;
text-transform:uppercase;font-family:"JetBrains Mono",monospace;}}
.ck-dp-saved-rel{{font-size:9px;color:var(--muted);}}
.ck-dp-saved-name{{font-size:15px;color:var(--ink);font-weight:600;
line-height:1.25;margin-bottom:8px;}}
.ck-dp-saved-bar{{height:4px;background:var(--ink);border-radius:2px;
overflow:hidden;margin:8px 0 4px 0;}}
.ck-dp-saved-bar-fill{{height:100%;background:var(--bar-tone, var(--muted));}}
.ck-dp-saved-progress{{font-size:10px;color:var(--muted);margin-bottom:10px;}}
.ck-dp-saved-actions{{display:flex;gap:6px;flex-wrap:wrap;}}
.ck-dp-saved-btn,.ck-dp-saved-btn-secondary,.ck-dp-saved-btn-danger
{{padding:5px 10px;font-size:9px;letter-spacing:1.2px;text-transform:uppercase;
font-weight:700;border-radius:3px;
transition:filter 120ms ease, border-color 120ms ease;}}
.ck-dp-saved-btn{{background:var(--teal);color:var(--bg);border:0;
text-decoration:none;}}
.ck-dp-saved-btn:hover{{filter:brightness(1.08);}}
.ck-dp-saved-btn-secondary{{background:transparent;color:var(--teal);
border:1px solid var(--paper-pure);cursor:pointer;font-weight:600;}}
.ck-dp-saved-btn-secondary:hover{{border-color:var(--teal);}}
.ck-dp-saved-btn-danger{{background:transparent;color:var(--red);
border:1px solid var(--paper-pure);cursor:pointer;font-weight:600;}}
.ck-dp-saved-btn-danger:hover{{border-color:var(--red);}}
</style>
"""


def _landing_slugs() -> str:
    """Editorial deal-profile landing — eyebrow + serif h2 + intro,
    then a slug-entry card and (JS-populated) recent-deals grid.
    """
    intro = ck_section_intro(
        eyebrow="DEAL PROFILE",
        headline="One source of truth per deal.",
        italic_word="truth",
        body=(
            "Each deal gets a unique URL — /diligence/deal/<slug>. "
            "Pick a slug (e.g., 'aurora'), enter the deal parameters "
            "once, and every downstream analytic opens with them "
            "pre-filled. Deal state persists locally so a refresh "
            "or returning tomorrow picks up where you left off."
        ),
    )
    form_inner = (
        '<form class="ck-dp-slug-form" '
        'onsubmit="const slug = this.slug.value.trim().toLowerCase()'
        ".replace(/[^a-z0-9-]/g, '-'); if (slug) "
        'window.location.href = \'/diligence/deal/\' + slug; return false;">'
        '<div class="cad-field">'
        '<label>Deal slug</label>'
        '<input class="cad-input" name="slug" required '
        'placeholder="e.g. aurora" pattern="[a-zA-Z0-9-]+">'
        '</div>'
        '<p class="ck-eyebrow">'
        'Letters, digits, and hyphens only. Bookmarkable. Open the same '
        'slug from any browser to pick up your profile.</p>'
        '<button type="submit" class="cad-btn cad-btn-primary">Open profile</button>'
        '</form>'
    )
    body = (
        _DP_STYLES
        + intro
        + ck_panel(form_inner, title="New profile")
        + '<div data-rcm-recent-deals class="ck-dp-recent-deals"></div>'
        + f'{_LANDING_JS}'
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
            f'<span class="ck-dp-tool-chip">{html.escape(t)}</span>'
            for t in tools
        )
        if input_type == "select" and key == "dataset":
            input_html = (
                f'<select name="{key}" data-rcm-deal-field="{key}" class="ck-dp-input">'
                f'<option value="">— none —</option>{fixture_options}'
                '</select>'
            )
        else:
            input_html = (
                f'<input name="{key}" data-rcm-deal-field="{key}" '
                f'placeholder="{html.escape(placeholder, quote=True)}" '
                f'value="{seeded}" class="ck-dp-input">'
            )
        fields_html.append(
            '<div class="ck-dp-field">'
            f'<label class="ck-dp-field-label">{html.escape(label)}</label>'
            f'{input_html}'
            f'<div class="ck-dp-field-chips">{chips}</div>'
            '</div>'
        )
    return (
        f'<form data-rcm-deal-form data-rcm-deal-slug="{html.escape(slug)}" '
        f'class="ck-dp-form">'
        f'{"".join(fields_html)}'
        '<div class="ck-dp-form-actions">'
        '<button type="button" data-rcm-deal-save class="ck-dp-btn-save">'
        'Save Profile</button>'
        '<button type="button" data-rcm-deal-clear class="ck-dp-btn-clear">'
        'Clear</button>'
        '<span data-rcm-deal-saved-at class="ck-dp-saved-at"></span>'
        '</div></form>'
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
    badge_html = ck_signal_badge(html.escape(badge), tone="neutral") if badge else ""
    # tool_key — used as the localStorage entry per (deal, analytic)
    # so the state badge can show "Last viewed N hr ago" when a
    # partner returns to a deal they were working on. Use the href
    # as the stable identifier (one tool ↔ one href).
    tool_key = a["href"]
    # Pin button — partners curate frequently-used tools into
    # localStorage["rcm_pinned_tools"]; the /app dashboard reads
    # this list and renders a "Pinned tools" rail above the
    # opportunities section. The button is styled as an editorial
    # star (☆ unpinned / ★ pinned) and JS toggles class + state.
    pin_button = (
        '<button type="button" class="ck-dp-card-pin" '
        f'data-rcm-pin-toggle '
        f'data-rcm-pin-href="{html.escape(a["href"], quote=True)}" '
        f'data-rcm-pin-label="{html.escape(a["label"], quote=True)}" '
        f'data-rcm-pin-phase="{html.escape(a.get("phase", "DILIGENCE"))}" '
        'aria-label="Pin this analytic" aria-pressed="false">'
        '<span aria-hidden="true" class="ck-dp-card-pin-icon">☆</span>'
        '</button>'
    )
    return (
        f'<a data-rcm-deal-link '
        f'data-rcm-deal-href-base="{html.escape(a["href"], quote=True)}" '
        f'data-rcm-deal-params="{html.escape(params_json, quote=True)}" '
        f'data-rcm-deal-slug="{html.escape(slug)}" '
        f'data-rcm-tool-key="{html.escape(tool_key, quote=True)}" '
        f'href="{html.escape(a["href"])}" class="ck-dp-card">'
        f'{pin_button}'
        '<div class="ck-dp-card-head">'
        f'<div class="ck-dp-card-title">{html.escape(a["label"])}</div>'
        f'{badge_html}'
        '</div>'
        f'<div class="ck-dp-card-detail">{html.escape(a["detail"])}</div>'
        '<div data-rcm-tool-state class="ck-dp-card-state" hidden></div>'
        '<div data-rcm-deal-preview class="ck-dp-card-preview"></div>'
        '</a>'
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
        n_count = len(by_phase[phase])
        eyebrow = (
            f"{html.escape(meta['label']).upper()} · "
            f"{n_count} {'ANALYTIC' if n_count == 1 else 'ANALYTICS'}"
        )
        sections.append(
            ck_section_header(
                html.escape(meta["subtitle"]) or html.escape(meta["label"]),
                eyebrow=eyebrow,
            )
            + '<div class="ck-dp-card-grid">'
            + "".join(tile_htmls) +
            '</div>'
        )
    return "".join(sections)


def _render_thesis_snapshot(slug: str) -> str:
    """The visual investment story — live-updated from localStorage."""
    # Jargon glosses for each tile label — partners new to PE finance
    # see [?] next to "Entry EV / EBITDA" and get the editorial gloss
    # rather than needing a separate glossary.
    _TILE_HELP = {
        "Enterprise value": {
            "definition": (
                "Total cost to buy the company free of capital "
                "structure — equity check plus assumed debt minus "
                "cash. The headline number the seller asks for."
            ),
        },
        "Revenue Y0": {
            "definition": (
                "Net Patient Revenue at close — billed services "
                "minus contractual allowances, bad debt, charity "
                "care. The cash-realisable top line on day one."
            ),
            "citation": "HFMA Glossary",
        },
        "EBITDA Y0": {
            "definition": (
                "Earnings before interest, taxes, depreciation, "
                "amortization at close. The operating cash-flow "
                "proxy PE partners price against."
            ),
        },
        "Entry EV / EBITDA": {
            "definition": (
                "The deal's entry multiple — enterprise value "
                "divided by Year-0 EBITDA. Compare to the public-"
                "comp band on /market-intel/seeking-alpha and the "
                "PE-transaction band for the specialty."
            ),
        },
    }

    def _tile(attr: str, label: str, sub_attr: str) -> str:
        help_meta = _TILE_HELP.get(label)
        if help_meta:
            label_html = ck_help_tooltip(
                label,
                help_meta["definition"],
                citation=help_meta.get("citation"),
            )
        else:
            label_html = html.escape(label)
        return (
            '<div class="ck-dp-thesis-tile">'
            f'<div class="ck-dp-thesis-tile-label">{label_html}</div>'
            f'<div data-{attr} class="ck-dp-thesis-tile-val">—</div>'
            f'<div class="ck-dp-thesis-tile-sub" data-{sub_attr}></div>'
            '</div>'
        )
    return (
        '<div data-rcm-thesis-snapshot class="ck-dp-thesis-card">'
        '<div class="ck-dp-thesis-head">'
        '<div>'
        + ck_eyebrow("Investment Thesis")
        + '<div class="ck-dp-thesis-narrative" data-rcm-thesis-narrative>'
        'Enter deal parameters below to populate the thesis snapshot.'
        '</div>'
        '</div>'
        '<div data-rcm-thesis-badge class="ck-dp-thesis-badge">Awaiting inputs</div>'
        '</div>'
        '<div class="ck-dp-thesis-tiles">'
        + _tile("rcm-thesis-ev", "Enterprise value", "rcm-thesis-ev-sub")
        + _tile("rcm-thesis-revenue", "Revenue Y0", "rcm-thesis-rev-sub")
        + _tile("rcm-thesis-ebitda", "EBITDA Y0", "rcm-thesis-margin-sub")
        + _tile("rcm-thesis-multiple", "Entry EV / EBITDA", "rcm-thesis-mult-sub")
        + '</div>'
        '<div class="ck-dp-thesis-struct">'
        '<div class="ck-dp-thesis-struct-head">'
        '<div class="ck-dp-thesis-struct-label">Capital structure</div>'
        '<div class="ck-dp-thesis-struct-legend" data-rcm-thesis-struct-legend>'
        '— equity · — debt</div>'
        '</div>'
        '<div class="ck-dp-thesis-struct-bar">'
        '<div data-rcm-thesis-equity-bar class="ck-dp-thesis-equity-bar"></div>'
        '<div data-rcm-thesis-debt-bar class="ck-dp-thesis-debt-bar"></div>'
        '</div></div></div>'
    )


def _render_market_context(slug: str) -> str:
    """Live market-context card — JS fetches the peer snapshot from
    ``/api/market-intel/peer-snapshot`` whenever the user changes the
    market_category, enterprise_value_usd, revenue_usd, or ebitda_usd
    fields.  Surfaces target-vs-peer multiple delta + named top peers
    + sentiment + assessment band."""
    return (
        '<div data-rcm-market-context class="ck-dp-market-card">'
        '<div class="ck-dp-market-head">'
        '<div>'
        + ck_eyebrow("Market Context · live from public comps")
        +
        '<div data-rcm-market-summary class="ck-dp-market-summary"></div>'
        '</div>'
        '<div data-rcm-market-assessment class="ck-dp-market-assessment">—</div>'
        '</div>'
        '<div class="ck-dp-market-tiles">'
        '<div>'
        '<div class="ck-dp-market-tile-label">'
        + ck_help_tooltip(
            "Target implied",
            "The implied entry multiple for this deal — "
            "enterprise value divided by Year-0 EBITDA. Compare "
            "to the peer median on the right tile.",
        )
        + '</div>'
        '<div data-rcm-market-target-mult class="ck-dp-market-tile-val">—</div>'
        '<div class="ck-dp-market-tile-sub">EV / EBITDA</div>'
        '</div>'
        '<div>'
        '<div class="ck-dp-market-tile-label">'
        + ck_help_tooltip(
            "Peer median",
            "Median EV/EBITDA across public-comp hospitals in the "
            "same sub-sector. The band shown below the value spans "
            "the 25th-75th percentile.",
            citation="rcm_mc/market_intel/category_bands",
        )
        + '</div>'
        '<div data-rcm-market-peer-median class="ck-dp-market-tile-val">—</div>'
        '<div class="ck-dp-market-tile-sub" data-rcm-market-band-range></div>'
        '</div>'
        '<div>'
        '<div class="ck-dp-market-tile-label">'
        + ck_help_tooltip(
            "Delta vs peer",
            "Target implied multiple minus the peer median. Positive "
            "= paying a premium; negative = paying a discount. Each "
            "turn of EBITDA is one multiple point — so +1.0x on a "
            "$10M EBITDA deal is $10M of extra purchase price.",
        )
        + '</div>'
        '<div data-rcm-market-delta class="ck-dp-market-tile-val">—</div>'
        '<div class="ck-dp-market-tile-sub">turns of EBITDA</div>'
        '</div>'
        '<div>'
        '<div class="ck-dp-market-tile-label">Closest peers</div>'
        '<div data-rcm-market-peers class="ck-dp-market-peers">—</div>'
        '</div>'
        '</div></div>'
    )


def _render_lifecycle_ribbon(slug: str) -> str:
    """5-phase lifecycle progress visual.

    Segments: Screening → Diligence → Risk → Financial → Delivery.

    The first phase renders with the ``is-current`` state class so
    partners see a default progression marker on a fresh deal. The
    inline JS (``_inline_js``) reads ``rcm_deal_<slug>_phase`` from
    localStorage and shifts the marker forward when the partner
    flags a phase as complete, giving a manual but persistent sense
    of progress across sessions.
    """
    order = ("SCREENING", "DILIGENCE", "RISK", "FINANCIAL", "DELIVERY")
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
        # Default state classes: first phase = current, rest = pending.
        # JS will overwrite based on localStorage after page load.
        state_cls = " is-current" if i == 0 else " is-pending"
        segments.append(
            f'<div data-rcm-phase="{phase}" '
            f'class="ck-dp-life-seg{state_cls}" '
            f'style="border-left-color:{tone_color};">'
            '<div class="ck-dp-life-seg-head">'
            f'<div class="ck-dp-life-seg-num">{i + 1:02d}</div>'
            f'<div class="ck-dp-life-seg-count">{count} '
            f'{"analytic" if count == 1 else "analytics"}</div>'
            '</div>'
            f'<div class="ck-dp-life-seg-label">{html.escape(meta["label"])}</div>'
            f'<div class="ck-dp-life-seg-subtitle">{html.escape(meta["subtitle"])}</div>'
            '</div>'
        )
    return f'<div class="ck-dp-lifecycle">{"".join(segments)}</div>'


def _render_diligence_questions(slug: str) -> str:
    """Inline diligence-questions editor — partner-curated list of
    questions to ask the seller, persisted to
    ``rcm_deal_<slug>_questions`` localStorage.

    Each row carries:
      - serif italic question text
      - editorial timestamp
      - mark-asked toggle (strikethrough in done state)
      - remove button
    Plus an inline `<input>` + "Add question →" CTA at the top.

    No server round-trip — purely a partner-side memo system. Stays
    editorial: parchment surface, serif body, italic accents,
    Source-Serif italic for empty state. Hidden in print so the
    LP-facing IC deliverables don't carry working notes.
    """
    return (
        '<div class="ck-dp-qs" data-rcm-dp-qs '
        f'data-rcm-qs-slug="{html.escape(slug)}">'
        '<div class="ck-dp-qs-intro">'
        '<p class="ck-section-body">'
        'Questions you want answered before IC. Persists in your '
        'browser, one list per deal. Mark each <em>asked</em> when '
        'the seller responds; remove items that get answered in '
        'follow-up documents.'
        '</p>'
        '</div>'
        '<form class="ck-dp-qs-form" data-rcm-qs-form>'
        '<input class="ck-dp-qs-input" data-rcm-qs-input '
        'placeholder="e.g. What share of NPR comes from out-of-network rates?" '
        'maxlength="280" autocomplete="off"/>'
        '<select class="ck-dp-qs-cat" data-rcm-qs-cat '
        'aria-label="Question category">'
        '<option value="financial">Financial</option>'
        '<option value="clinical">Clinical</option>'
        '<option value="regulatory">Regulatory</option>'
        '<option value="legal">Legal</option>'
        '<option value="operational">Operational</option>'
        '<option value="other">Other</option>'
        '</select>'
        '<button type="submit" class="ck-dp-qs-add" '
        'data-rcm-qs-add>Add question →</button>'
        '</form>'
        '<div class="ck-dp-qs-empty" data-rcm-qs-empty hidden>'
        '<p class="ck-section-body" style="font-style:italic;">'
        'No questions yet. Diligence is a conversation — start by '
        'noting one thing you\'d need to hear from the seller '
        'before underwriting.'
        '</p>'
        '</div>'
        '<ol class="ck-dp-qs-list" data-rcm-qs-list></ol>'
        '<div class="ck-dp-qs-meta-row" data-rcm-qs-meta-row hidden>'
        '<div class="ck-dp-qs-meta" data-rcm-qs-meta></div>'
        '<div class="ck-dp-qs-export">'
        '<button type="button" class="ck-dp-qs-export-btn" '
        'data-rcm-qs-copy-md>Copy as Markdown</button>'
        '<button type="button" class="ck-dp-qs-export-btn" '
        'data-rcm-qs-copy-md-open>Copy open only</button>'
        '<button type="button" class="ck-dp-qs-export-btn" '
        'data-rcm-qs-csv>Download CSV</button>'
        '<span class="ck-dp-qs-export-toast" '
        'data-rcm-qs-toast hidden></span>'
        '</div>'
        '</div>'
        '</div>'
    )


def _render_diligence_pulse(slug: str) -> str:
    """Server-emitted placeholder for the diligence pulse composite.

    Renders a hidden parchment section with three tiles — tools
    opened, last touched, progress bar — that inline JS hydrates
    from ``rcm_deal_<slug>_visited`` on DOMContentLoaded. The pulse
    only appears once a partner has actually opened at least one
    analytic on this deal; first-time visits see nothing extra.

    The label for "Last touched" needs to map an href back to a
    human-readable analytic title. That map is computed at render
    time from ``_ANALYTICS`` (the deal-profile's tool catalog) and
    inlined as ``window.RCM_DP_TOOL_LABELS`` so the JS can resolve
    href → label without a round-trip.
    """
    # Build href → label + total count from the analytics list
    tool_labels = {a["href"]: a["label"] for a in _ANALYTICS}
    return (
        '<section class="ck-dp-pulse" data-rcm-dp-pulse hidden>'
        '<div class="ck-dp-pulse-head">'
        '<span class="ck-dp-pulse-eyebrow">Diligence pulse</span>'
        '<span class="ck-dp-pulse-meta" data-rcm-pulse-meta></span>'
        '</div>'
        '<div class="ck-dp-pulse-grid">'
        '<div class="ck-dp-pulse-tile">'
        '<div class="ck-dp-pulse-val" data-rcm-pulse-count>0</div>'
        '<div class="ck-dp-pulse-lbl">Tools opened</div>'
        f'<div class="ck-dp-pulse-sub">of {len(_ANALYTICS)} analytics</div>'
        '</div>'
        '<div class="ck-dp-pulse-tile">'
        '<div class="ck-dp-pulse-val ck-dp-pulse-val-serif" '
        'data-rcm-pulse-last>—</div>'
        '<div class="ck-dp-pulse-lbl">Last touched</div>'
        '<div class="ck-dp-pulse-sub" '
        'data-rcm-pulse-last-ts></div>'
        '</div>'
        '<div class="ck-dp-pulse-tile">'
        '<div class="ck-dp-pulse-bar">'
        '<div class="ck-dp-pulse-bar-fill" '
        'data-rcm-pulse-bar-fill></div>'
        '</div>'
        '<div class="ck-dp-pulse-lbl">Diligence progress</div>'
        '<div class="ck-dp-pulse-sub" '
        'data-rcm-pulse-pct>0%</div>'
        '</div>'
        '</div>'
        '</section>'
        '<script>window.RCM_DP_TOOL_LABELS='
        + json.dumps(tool_labels)
        + f';window.RCM_DP_TOOL_TOTAL={len(_ANALYTICS)};'
        '</script>'
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
        badge.style.color = 'var(--muted)';
        badge.style.borderColor = 'var(--paper-pure)';
      } else if (ev != null && rev != null && ebitda != null) {
        badge.textContent = 'Ready for pipeline';
        badge.style.color = 'var(--green)';
        badge.style.borderColor = 'var(--green)';
      } else {
        badge.textContent = completion + ' of 24 fields';
        badge.style.color = 'var(--amber)';
        badge.style.borderColor = 'var(--amber)';
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
        deltaEl.style.color = 'var(--muted)';
      } else {
        var dv = snap.delta_vs_median_turns;
        deltaEl.textContent = (dv > 0 ? '+' : '') + dv.toFixed(2) + 'x';
        deltaEl.style.color = dv > 0.5 ? 'var(--red)'
          : dv < -0.5 ? 'var(--green)' : 'var(--muted)';
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
        'DISCOUNT': 'var(--green)',
        'IN-LINE': 'var(--teal)',
        'PREMIUM': 'var(--red)',
      }[snap.assessment] || 'var(--muted)';
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

  // ── Lifecycle ribbon: read/write current phase to localStorage ──
  // Each click on a phase tile cycles its state pending → current →
  // done → pending. The current phase is also written to
  // `rcm_deal_<slug>_phase` so the partner's progress persists
  // across sessions and other surfaces can read it.
  var phaseKey = "rcm_deal_" + slug + "_phase";
  var phaseOrder = ["SCREENING","DILIGENCE","RISK","FINANCIAL","DELIVERY"];
  function paintLifecycle() {
    var current = localStorage.getItem(phaseKey) || "SCREENING";
    var currentIdx = phaseOrder.indexOf(current);
    if (currentIdx < 0) currentIdx = 0;
    document.querySelectorAll("[data-rcm-phase]").forEach(function(el) {
      var phase = el.getAttribute("data-rcm-phase");
      var idx = phaseOrder.indexOf(phase);
      el.classList.remove("is-pending","is-current","is-done");
      if (idx < currentIdx)        el.classList.add("is-done");
      else if (idx === currentIdx) el.classList.add("is-current");
      else                          el.classList.add("is-pending");
    });
  }
  document.addEventListener("click", function(e) {
    var tile = e.target.closest && e.target.closest("[data-rcm-phase]");
    if (!tile) return;
    var phase = tile.getAttribute("data-rcm-phase");
    var current = localStorage.getItem(phaseKey) || "SCREENING";
    // Clicking the current phase advances; clicking any other phase
    // jumps directly to it. Lets partners move forward (most common)
    // or back-fill if they skipped a step.
    if (phase === current) {
      var nextIdx = phaseOrder.indexOf(current) + 1;
      if (nextIdx < phaseOrder.length) {
        localStorage.setItem(phaseKey, phaseOrder[nextIdx]);
      }
    } else {
      localStorage.setItem(phaseKey, phase);
    }
    paintLifecycle();
  });
  document.addEventListener("DOMContentLoaded", paintLifecycle);

  // Analytic-card state badges — read per-tool last-viewed timestamps
  // from rcm_deal_<slug>_visited and paint each card's state line.
  // Click on a card records the visit so subsequent loads of the
  // deal-profile show "Last viewed N min ago" right under the title.
  // Gives partners visible recency context per analytic without
  // needing them to leave the profile to check.
  var visitedKey = "rcm_deal_" + slug + "_visited";
  function relTime(ts) {
    if (!ts) return "";
    var d = Math.round((Date.now() - ts) / 60000);
    if (d < 1) return "just now";
    if (d < 60) return d + " min ago";
    if (d < 1440) return Math.round(d / 60) + " hr ago";
    return Math.round(d / 1440) + " d ago";
  }
  function paintToolStates() {
    var raw;
    try { raw = localStorage.getItem(visitedKey); } catch (e) { raw = null; }
    var rows = {};
    if (raw) { try { rows = JSON.parse(raw) || {}; } catch (e) { rows = {}; } }
    document.querySelectorAll("[data-rcm-tool-key]").forEach(function(card) {
      var key = card.getAttribute("data-rcm-tool-key");
      var state = card.querySelector("[data-rcm-tool-state]");
      if (!state) return;
      var ts = rows[key];
      if (!ts) { state.hidden = true; return; }
      state.innerHTML =
        '<span class="ck-dp-card-state-dot" aria-hidden="true"></span>'
        + 'Last viewed ' + relTime(ts);
      state.hidden = false;
    });
  }
  document.addEventListener("DOMContentLoaded", paintToolStates);
  document.addEventListener("click", function(e) {
    var card = e.target.closest && e.target.closest("[data-rcm-tool-key]");
    if (!card) return;
    // The pin button lives inside the card link — don't record a
    // visit when the partner is pinning, only when they click the
    // card itself to navigate.
    if (e.target.closest("[data-rcm-pin-toggle]")) return;
    var key = card.getAttribute("data-rcm-tool-key");
    if (!key) return;
    try {
      var raw = localStorage.getItem(visitedKey);
      var rows = raw ? JSON.parse(raw) : {};
      if (!rows || typeof rows !== "object") rows = {};
      rows[key] = Date.now();
      localStorage.setItem(visitedKey, JSON.stringify(rows));
    } catch (err) { /* quota / disabled — ignore */ }
  });

  // Diligence questions — partner-curated list of questions to
  // ask the seller, persisted to rcm_deal_<slug>_questions
  // localStorage. Add via form submit; toggle-asked + remove via
  // small buttons; relative timestamp in italic Source-Serif.
  // No server round-trip — purely a partner-side memo system.
  var qsKey = "rcm_deal_" + slug + "_questions";
  function loadQs() {
    try {
      var raw = localStorage.getItem(qsKey);
      var rows = raw ? JSON.parse(raw) : [];
      return Array.isArray(rows) ? rows : [];
    } catch (e) { return []; }
  }
  function saveQs(rows) {
    try { localStorage.setItem(qsKey, JSON.stringify(rows)); }
    catch (e) { /* quota — ignore */ }
  }
  function qsRel(ts) {
    if (!ts) return "";
    var d = Math.round((Date.now() - ts) / 60000);
    if (d < 1) return "just now";
    if (d < 60) return d + " min ago";
    if (d < 1440) return Math.round(d / 60) + " hr ago";
    return Math.round(d / 1440) + " d ago";
  }
  function escQ(s) {
    var d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }
  function paintQs() {
    var root = document.querySelector("[data-rcm-dp-qs]");
    if (!root) return;
    var list = root.querySelector("[data-rcm-qs-list]");
    var empty = root.querySelector("[data-rcm-qs-empty]");
    var meta = root.querySelector("[data-rcm-qs-meta]");
    if (!list) return;
    var rows = loadQs();
    if (rows.length === 0) {
      list.innerHTML = "";
      if (empty) empty.hidden = false;
      var metaRow0 = root.querySelector("[data-rcm-qs-meta-row]");
      if (metaRow0) metaRow0.hidden = true;
      return;
    }
    if (empty) empty.hidden = true;
    var CAT_LABELS = {
      financial: "Fin", clinical: "Clin", regulatory: "Reg",
      legal: "Leg", operational: "Ops", other: "Other",
    };
    list.innerHTML = rows.map(function(r, i) {
      var stateCls = r.asked ? " is-asked" : "";
      var btnCls = r.asked ? " is-active" : "";
      var cat = (r.category || "financial").toLowerCase();
      if (!CAT_LABELS[cat]) cat = "other";
      var pill = '<span class="ck-dp-qs-pill cat-' + cat + '">' +
        escQ(CAT_LABELS[cat]) + '</span>';
      return '<li class="ck-dp-qs-row' + stateCls + '" ' +
        'data-rcm-qs-id="' + escQ(r.id) + '">' +
        '<span class="ck-dp-qs-row-num">' +
        String(i + 1).padStart(2, "0") + '</span>' +
        '<span class="ck-dp-qs-row-text">' + pill +
        escQ(r.text) + '</span>' +
        '<span class="ck-dp-qs-row-ts">' + qsRel(r.ts) + '</span>' +
        '<span class="ck-dp-qs-row-actions">' +
        '<button type="button" class="ck-dp-qs-row-btn ' +
        'ck-dp-qs-row-btn-asked' + btnCls + '" ' +
        'data-rcm-qs-ask>' + (r.asked ? "Asked ✓" : "Mark asked") +
        '</button>' +
        '<button type="button" class="ck-dp-qs-row-btn ' +
        'ck-dp-qs-row-btn-remove" data-rcm-qs-remove>Remove</button>' +
        '</span></li>';
    }).join("");
    var nOpen = rows.filter(function(r) { return !r.asked; }).length;
    var metaRow = root.querySelector("[data-rcm-qs-meta-row]");
    if (meta) {
      // Editorial meta line: "5 total · 2 still open · 3 Fin · 1 Clin · 1 Reg"
      var counts = {};
      rows.forEach(function(r) {
        var c = (r.category || "financial").toLowerCase();
        if (!CAT_LABELS[c]) c = "other";
        counts[c] = (counts[c] || 0) + 1;
      });
      var catParts = Object.keys(counts).map(function(c) {
        return counts[c] + " " + CAT_LABELS[c];
      });
      var openPhrase = nOpen + " still open";
      var head = rows.length + " total · " + openPhrase;
      meta.textContent = catParts.length
        ? head + " · " + catParts.join(" · ")
        : head;
    }
    if (metaRow) metaRow.hidden = false;
  }
  document.addEventListener("DOMContentLoaded", paintQs);
  document.addEventListener("submit", function(e) {
    var form = e.target.closest && e.target.closest("[data-rcm-qs-form]");
    if (!form) return;
    e.preventDefault();
    var input = form.querySelector("[data-rcm-qs-input]");
    var catSel = form.querySelector("[data-rcm-qs-cat]");
    if (!input) return;
    var text = (input.value || "").trim();
    if (!text) return;
    var category = (catSel && catSel.value) ? catSel.value : "financial";
    var rows = loadQs();
    rows.unshift({
      id: "q" + Date.now() + Math.random().toString(36).slice(2, 6),
      text: text, ts: Date.now(), asked: false,
      category: category,
    });
    saveQs(rows);
    input.value = "";
    // Keep the category sticky — partners often add several
    // questions in the same area, so leave the select where they
    // last set it instead of resetting to the default.
    paintQs();
  });
  // ── Export handlers ──
  // Three small editorial buttons next to the meta line let
  // partners hand the question list off to the seller as Markdown
  // (default, all rows) or just the open subset, or download a
  // CSV with category + status + timestamp columns. All client-
  // side via Blob + clipboard APIs — no server roundtrip.
  function qsToast(msg) {
    var t = document.querySelector("[data-rcm-qs-toast]");
    if (!t) return;
    t.textContent = msg;
    t.hidden = false;
    t.classList.add("is-visible");
    setTimeout(function() {
      t.classList.remove("is-visible");
      setTimeout(function() { t.hidden = true; }, 220);
    }, 1600);
  }
  function qsCsvCell(v) {
    var s = String(v == null ? "" : v);
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }
  function qsBuildMarkdown(openOnly) {
    var rows = loadQs();
    if (openOnly) rows = rows.filter(function(r) { return !r.asked; });
    if (rows.length === 0) return "";
    var CAT_LABELS_FULL = {
      financial: "Financial", clinical: "Clinical",
      regulatory: "Regulatory", legal: "Legal",
      operational: "Operational", other: "Other",
    };
    var lines = [
      "# Diligence questions — " + slug,
      "",
      "_" + rows.length + " question" + (rows.length === 1 ? "" : "s") +
        (openOnly ? " (open only)" : "") + ", exported " +
        new Date().toISOString().slice(0, 10) + "._",
      "",
    ];
    rows.forEach(function(r, i) {
      var c = (r.category || "financial").toLowerCase();
      if (!CAT_LABELS_FULL[c]) c = "other";
      var asked = r.asked ? " ✓ asked" : "";
      lines.push(
        (i + 1) + ". **[" + CAT_LABELS_FULL[c] + "]**" + asked + " — " +
        r.text
      );
    });
    return lines.join("\n");
  }
  function qsBuildCsv() {
    var rows = loadQs();
    var header = "slug,category,status,question,added_at";
    var body = rows.map(function(r) {
      var c = (r.category || "financial").toLowerCase();
      var status = r.asked ? "asked" : "open";
      var iso = new Date(r.ts || 0).toISOString();
      return [
        qsCsvCell(slug), qsCsvCell(c), qsCsvCell(status),
        qsCsvCell(r.text || ""), qsCsvCell(iso),
      ].join(",");
    });
    return header + "\n" + body.join("\n");
  }
  function qsCopyToClipboard(text) {
    if (!text) { qsToast("Nothing to copy."); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function() {
        qsToast("Copied to clipboard.");
      }).catch(function() { qsToast("Copy failed."); });
    } else {
      // Old-browser fallback
      var ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); qsToast("Copied to clipboard."); }
      catch (e) { qsToast("Copy failed."); }
      document.body.removeChild(ta);
    }
  }
  function qsDownloadCsv() {
    var csv = qsBuildCsv();
    if (!csv || csv.split("\n").length < 2) {
      qsToast("Nothing to export."); return;
    }
    var blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "diligence-questions-" + slug + ".csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    qsToast("CSV downloaded.");
  }
  document.addEventListener("click", function(e) {
    if (e.target.closest && e.target.closest("[data-rcm-qs-copy-md]")) {
      qsCopyToClipboard(qsBuildMarkdown(false));
    } else if (e.target.closest && e.target.closest("[data-rcm-qs-copy-md-open]")) {
      qsCopyToClipboard(qsBuildMarkdown(true));
    } else if (e.target.closest && e.target.closest("[data-rcm-qs-csv]")) {
      qsDownloadCsv();
    }
  });

  document.addEventListener("click", function(e) {
    var row = e.target.closest && e.target.closest("[data-rcm-qs-id]");
    if (!row) return;
    var id = row.getAttribute("data-rcm-qs-id");
    var ask = e.target.closest("[data-rcm-qs-ask]");
    var rem = e.target.closest("[data-rcm-qs-remove]");
    if (!ask && !rem) return;
    var rows = loadQs();
    if (ask) {
      rows = rows.map(function(r) {
        if (r.id === id) r.asked = !r.asked;
        return r;
      });
    } else if (rem) {
      rows = rows.filter(function(r) { return r.id !== id; });
    }
    saveQs(rows);
    paintQs();
  });

  // "Compare with…" disclosure — populate the menu from
  // rcm_recent_deals every time the disclosure opens so newly-viewed
  // deals show up immediately. Each row links to /diligence/compare
  // with both datasets when available; falls back to the picker
  // when either side is missing a dataset. The current slug is
  // excluded from the list (no compare-to-self).
  function escHtml(s) {
    var d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }
  function paintCompareWith() {
    var details = document.querySelector("[data-rcm-cmpw]");
    if (!details) return;
    var thisSlug = details.getAttribute("data-rcm-cmpw-slug") || slug;
    var list = details.querySelector("[data-rcm-cmpw-list]");
    var empty = details.querySelector("[data-rcm-cmpw-empty]");
    if (!list) return;
    var rows = [];
    try {
      var raw = localStorage.getItem("rcm_recent_deals");
      rows = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(rows)) rows = [];
    } catch (e) { rows = []; }
    rows = rows.filter(function(r) {
      return r && r.slug && r.slug !== thisSlug;
    }).slice(0, 5);
    var thisDataset = "";
    try {
      var prof = localStorage.getItem("rcm_deal_" + thisSlug);
      if (prof) {
        var p = JSON.parse(prof);
        thisDataset = (p && p.dataset) ? p.dataset : "";
      }
    } catch (e) { thisDataset = ""; }
    if (rows.length === 0) {
      if (empty) empty.hidden = false;
      list.innerHTML = "";
      return;
    }
    if (empty) empty.hidden = true;
    list.innerHTML = rows.map(function(r) {
      var dsRight = "";
      try {
        var raw2 = localStorage.getItem("rcm_deal_" + r.slug);
        if (raw2) {
          var p2 = JSON.parse(raw2);
          dsRight = (p2 && p2.dataset) ? p2.dataset : "";
        }
      } catch (e) { dsRight = ""; }
      var href;
      if (thisDataset && dsRight) {
        href = "/diligence/compare?left=" +
          encodeURIComponent(thisDataset) + "&right=" +
          encodeURIComponent(dsRight);
      } else {
        href = "/diligence/compare";
      }
      // Open-questions chip — surface Q load on candidate compare
      // targets so partners see "Hawthorne · 5 open qs" before
      // committing to the comparison. Same shape as the /app
      // recently-viewed rail's chip; chip omitted when the candidate
      // deal has zero open questions.
      var qOpen = 0;
      try {
        var qRaw = localStorage.getItem("rcm_deal_" + r.slug + "_questions");
        if (qRaw) {
          var qList = JSON.parse(qRaw);
          if (Array.isArray(qList)) {
            qOpen = qList.filter(function(q) { return q && !q.asked; }).length;
          }
        }
      } catch (e) { qOpen = 0; }
      var qChip = qOpen > 0
        ? '<span class="ck-dp-cmpw-q">' + qOpen + ' open ' +
            (qOpen === 1 ? 'q' : 'qs') + '</span>'
        : '';
      return '<li class="ck-dp-cmpw-row">' +
        '<a class="ck-dp-cmpw-link" href="' + escHtml(href) + '">' +
        '<span class="ck-dp-cmpw-link-name">' +
        '<em>' + escHtml(r.name || r.slug) + '</em>' +
        qChip +
        '</span>' +
        '<span class="ck-dp-cmpw-link-slug">' + escHtml(r.slug) +
        '</span>' +
        '</a></li>';
    }).join("");
    // If THIS deal has no dataset stored, show a small italic
    // editorial note explaining the picker fallback.
    if (!thisDataset) {
      var existing = details.querySelector(".ck-dp-cmpw-disabled");
      if (!existing) {
        var note = document.createElement("div");
        note.className = "ck-dp-cmpw-disabled";
        note.textContent =
          "Save the deal-profile dataset to enable direct " +
          "side-by-side. Without it, the comparison opens the picker.";
        details.querySelector("[data-rcm-cmpw-menu]").appendChild(note);
      }
    }
  }
  // Repaint every time the disclosure opens (rcm_recent_deals can
  // change between visits to the deal-profile)
  var cmpwDetails = document.querySelector("[data-rcm-cmpw]");
  if (cmpwDetails) {
    cmpwDetails.addEventListener("toggle", function() {
      if (cmpwDetails.open) paintCompareWith();
    });
    // Paint once on load so the keyboard-only path also works
    document.addEventListener("DOMContentLoaded", paintCompareWith);
  }

  // Diligence pulse — hydrate from the same visited map. Three
  // tiles: tools opened, last touched (label + relative ts),
  // progress bar (count / total). Section stays hidden until at
  // least one tool has been visited.
  function paintDiligencePulse() {
    var sec = document.querySelector("[data-rcm-dp-pulse]");
    if (!sec) return;
    var rows = {};
    try {
      var raw = localStorage.getItem(visitedKey);
      if (raw) rows = JSON.parse(raw) || {};
    } catch (e) { rows = {}; }
    var entries = Object.keys(rows).map(function(href) {
      return { href: href, ts: rows[href] };
    });
    if (!entries.length) { sec.hidden = true; return; }
    var count = entries.length;
    var total = (window.RCM_DP_TOOL_TOTAL || 22);
    var labels = (window.RCM_DP_TOOL_LABELS || {});
    entries.sort(function(a, b) { return b.ts - a.ts; });
    var lastTs = entries[0].ts;
    var lastLabel = labels[entries[0].href] || entries[0].href;
    var d = Math.round((Date.now() - lastTs) / 60000);
    var rel = d < 1 ? "just now"
      : d < 60 ? d + " min ago"
      : d < 1440 ? Math.round(d / 60) + " hr ago"
      : Math.round(d / 1440) + " d ago";
    var pct = Math.round((count / total) * 100);
    var pctClamped = Math.max(0, Math.min(100, pct));
    var cnt = sec.querySelector("[data-rcm-pulse-count]");
    if (cnt) cnt.textContent = String(count);
    var lastEl = sec.querySelector("[data-rcm-pulse-last]");
    if (lastEl) lastEl.textContent = lastLabel;
    var lastTsEl = sec.querySelector("[data-rcm-pulse-last-ts]");
    if (lastTsEl) lastTsEl.textContent = rel;
    var pctEl = sec.querySelector("[data-rcm-pulse-pct]");
    if (pctEl) pctEl.textContent = pct + "% of " + total;
    var fill = sec.querySelector("[data-rcm-pulse-bar-fill]");
    if (fill) fill.style.width = pctClamped + "%";
    var meta = sec.querySelector("[data-rcm-pulse-meta]");
    if (meta) {
      meta.textContent = "from your visit history on " + slug;
    }
    sec.hidden = false;
  }
  document.addEventListener("DOMContentLoaded", paintDiligencePulse);

  // Pinned tools — partner-curated favorites stored in
  // localStorage["rcm_pinned_tools"] as [{href, label, phase}] and
  // rendered by the /app dashboard's pinned-tools rail. The pin
  // button in each analytic card toggles membership; clicking the
  // star NEVER navigates (preventDefault) so partners can pin
  // without leaving the deal profile.
  var PIN_KEY = "rcm_pinned_tools";
  var PIN_MAX = 6;
  function loadPins() {
    try {
      var raw = localStorage.getItem(PIN_KEY);
      var rows = raw ? JSON.parse(raw) : [];
      return Array.isArray(rows) ? rows : [];
    } catch (e) { return []; }
  }
  function savePins(rows) {
    try { localStorage.setItem(PIN_KEY, JSON.stringify(rows)); }
    catch (e) { /* quota — ignore */ }
  }
  function paintPins() {
    var pinned = loadPins();
    var pinnedHrefs = {};
    pinned.forEach(function(p) { if (p && p.href) pinnedHrefs[p.href] = true; });
    document.querySelectorAll("[data-rcm-pin-toggle]").forEach(function(btn) {
      var href = btn.getAttribute("data-rcm-pin-href");
      btn.setAttribute("aria-pressed", pinnedHrefs[href] ? "true" : "false");
    });
  }
  document.addEventListener("DOMContentLoaded", paintPins);
  document.addEventListener("click", function(e) {
    var btn = e.target.closest && e.target.closest("[data-rcm-pin-toggle]");
    if (!btn) return;
    // Stop link navigation — clicking the star pins, doesn't open
    e.preventDefault();
    e.stopPropagation();
    var href = btn.getAttribute("data-rcm-pin-href");
    var label = btn.getAttribute("data-rcm-pin-label");
    var phase = btn.getAttribute("data-rcm-pin-phase") || "DILIGENCE";
    var rows = loadPins().filter(function(p) { return p && p.href !== href; });
    var isUnpin = btn.getAttribute("aria-pressed") === "true";
    if (!isUnpin) {
      rows.unshift({ href: href, label: label, phase: phase });
      if (rows.length > PIN_MAX) rows = rows.slice(0, PIN_MAX);
    }
    savePins(rows);
    paintPins();
  });

  // Push this slug onto the "recently viewed" deals index so the /app
  // recently-viewed rail can show one-click re-entry to deals in
  // progress. Keep the most recent 8 entries; the rail itself slices
  // to 5 visible — a small buffer protects against accidental clears.
  function pushRecent() {
    try {
      var idxKey = "rcm_recent_deals";
      var raw = localStorage.getItem(idxKey);
      var rows = [];
      if (raw) { try { rows = JSON.parse(raw); } catch (e) { rows = []; } }
      if (!Array.isArray(rows)) rows = [];
      var profile = localStorage.getItem(storageKey);
      var name = slug;
      if (profile) {
        try { var p = JSON.parse(profile); if (p && p.deal_name) name = p.deal_name; }
        catch (e) {}
      }
      rows = rows.filter(function(r) { return r && r.slug !== slug; });
      rows.unshift({ slug: slug, name: name, ts: Date.now() });
      if (rows.length > 8) rows = rows.slice(0, 8);
      localStorage.setItem(idxKey, JSON.stringify(rows));
    } catch (e) { /* quota / disabled storage — ignore */ }
  }
  document.addEventListener("DOMContentLoaded", pushRecent);
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

    hero = ck_section_intro(
        eyebrow="DEAL PROFILE",
        headline=(
            f'<span data-rcm-deal-display-name>{html.escape(slug)}</span>'
        ),
        italic_word=html.escape(slug),
        body=(
            f"slug: {html.escape(slug)} · persisted to browser "
            "localStorage. Enter deal parameters once. Save Profile "
            "stores them in your browser. Every analytic link below "
            "pre-fills the relevant parameters — click any card and "
            "the tool opens with your deal context already populated."
        ),
    ) + (
        '<p class="ck-section-body" style="display:flex;gap:14px;'
        'align-items:baseline;flex-wrap:wrap;">'
        '<a href="/diligence/deal" class="cad-btn">'
        'Pick Another Slug →</a>'
        # "Compare with…" disclosure — partners pick a recently-
        # viewed deal as the right-hand side of a side-by-side
        # comparison without leaving the profile. JS populates the
        # list from rcm_recent_deals on every open so newly-viewed
        # deals show up immediately. The current slug is filtered
        # out of the list so partners can't compare a deal to
        # itself.
        '<details class="ck-dp-cmpw" '
        f'data-rcm-cmpw data-rcm-cmpw-slug="{html.escape(slug)}">'
        '<summary class="ck-dp-cmpw-summary">'
        'Compare with… '
        '<span aria-hidden="true" class="ck-dp-cmpw-caret">▾</span>'
        '</summary>'
        '<div class="ck-dp-cmpw-menu" data-rcm-cmpw-menu>'
        '<div class="ck-dp-cmpw-empty" data-rcm-cmpw-empty hidden>'
        'No other deals open yet. Visit a second deal to enable '
        'side-by-side.</div>'
        '<ol class="ck-dp-cmpw-list" data-rcm-cmpw-list></ol>'
        '</div>'
        '</details>'
        '</p>'
    )
    # Prominent "Run Full Pipeline" CTA — the single highest-leverage
    # button on the page.
    pipeline_cta = ck_panel(
        '<p class="ck-section-body">'
        '<strong>One-button full diligence chain.</strong> '
        'Runs bankruptcy scan → CCD ingest → HFMA benchmarks → denial '
        'prediction → PPAM → counterfactual → Steward → cyber → '
        'deal autopsy → Deal MC in one step. Feeds IC Packet with '
        'every headline number.</p>'
        '<p class="ck-section-body">'
        '<a data-rcm-run-pipeline href="/diligence/thesis-pipeline" '
        'class="cad-btn cad-btn-primary">▶ Run Full Pipeline</a>'
        '</p>',
        title="Thesis Pipeline",
    )
    thesis_snapshot = _render_thesis_snapshot(slug)
    market_context = _render_market_context(slug)
    lifecycle = _render_lifecycle_ribbon(slug)
    form = _render_form(slug, seed_values)
    grid = _render_analytics_grid(slug)
    grid_header = ck_section_header(
        "Open in Analytic · grouped by lifecycle phase",
        eyebrow="ANALYTICS",
    )
    thesis_panel = ck_panel(
        thesis_snapshot, title="Investment thesis",
        anchor_id="dp-thesis",
    )
    market_panel = ck_panel(
        market_context, title="Market context",
        anchor_id="dp-market",
    )
    lifecycle_panel = ck_panel(
        lifecycle, title="Diligence lifecycle",
        anchor_id="dp-lifecycle",
    )
    form_panel = ck_panel(
        form, title="Deal parameters",
        anchor_id="dp-params",
    )
    questions_panel = ck_panel(
        _render_diligence_questions(slug),
        title="Diligence questions",
        anchor_id="dp-questions",
    )
    # Sticky right-rail table of contents — the deal profile is the
    # central diligence surface partners return to. The TOC lets
    # them jump straight to Analytics or Deal parameters without
    # scrolling past the hero. Questions panel was added in Phase O
    # between Deal parameters and Analytics so partners curate
    # questions adjacent to where they entered the deal context.
    toc = ck_sticky_toc([
        {"id": "dp-thesis",    "title": "Investment thesis"},
        {"id": "dp-market",    "title": "Market context"},
        {"id": "dp-pipeline",  "title": "Thesis Pipeline"},
        {"id": "dp-lifecycle", "title": "Diligence lifecycle"},
        {"id": "dp-params",    "title": "Deal parameters"},
        {"id": "dp-questions", "title": "Diligence questions"},
        {"id": "dp-analytics", "title": "Analytics"},
    ])
    # Wrap pipeline_cta + grid_header so they pick up anchors too —
    # they're not ck_panels but partners still expect "Thesis Pipeline"
    # and "Analytics" to be jump targets.
    pipeline_block = (
        f'<section id="dp-pipeline">{pipeline_cta}</section>'
    )
    grid_block = (
        f'<section id="dp-analytics">{grid_header}{grid}</section>'
    )
    pulse = _render_diligence_pulse(slug)
    next_up = ck_next_section(
        "Open the diligence checklist",
        "/diligence/checklist",
        eyebrow="Continue —",
        italic_word="checklist",
    )
    return chartis_shell(
        _DP_STYLES + hero + pulse
        + '<div class="ck-toc-layout">'
        + toc
        + '<div class="ck-toc-content">'
        + thesis_panel + market_panel + pipeline_block
        + lifecycle_panel + form_panel + questions_panel + grid_block
        + '</div></div>'
        + bookmark_hint() + next_up + _inline_js(slug),
        f"Deal Profile — {slug}",
        active_nav="/diligence/deal",
        subtitle="One source of truth",
    )
