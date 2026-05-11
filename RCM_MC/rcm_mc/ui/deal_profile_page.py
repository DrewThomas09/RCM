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
    P, chartis_shell, ck_eyebrow, ck_panel,
    ck_section_header, ck_section_intro, ck_signal_badge,
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
    return (
        f'<a data-rcm-deal-link '
        f'data-rcm-deal-href-base="{html.escape(a["href"], quote=True)}" '
        f'data-rcm-deal-params="{html.escape(params_json, quote=True)}" '
        f'data-rcm-deal-slug="{html.escape(slug)}" '
        f'href="{html.escape(a["href"])}" class="ck-dp-card">'
        '<div class="ck-dp-card-head">'
        f'<div class="ck-dp-card-title">{html.escape(a["label"])}</div>'
        f'{badge_html}'
        '</div>'
        f'<div class="ck-dp-card-detail">{html.escape(a["detail"])}</div>'
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
    def _tile(attr: str, label: str, sub_attr: str) -> str:
        return (
            '<div class="ck-dp-thesis-tile">'
            f'<div class="ck-dp-thesis-tile-label">{label}</div>'
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
        '<div class="ck-dp-market-tile-label">Target implied</div>'
        '<div data-rcm-market-target-mult class="ck-dp-market-tile-val">—</div>'
        '<div class="ck-dp-market-tile-sub">EV / EBITDA</div>'
        '</div>'
        '<div>'
        '<div class="ck-dp-market-tile-label">Peer median</div>'
        '<div data-rcm-market-peer-median class="ck-dp-market-tile-val">—</div>'
        '<div class="ck-dp-market-tile-sub" data-rcm-market-band-range></div>'
        '</div>'
        '<div>'
        '<div class="ck-dp-market-tile-label">Delta vs peer</div>'
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
        '<p class="ck-section-body">'
        '<a href="/diligence/deal" class="cad-btn">Pick Another Slug →</a>'
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
    thesis_panel = ck_panel(thesis_snapshot, title="Investment thesis")
    market_panel = ck_panel(market_context, title="Market context")
    lifecycle_panel = ck_panel(
        lifecycle, title="Diligence lifecycle",
    )
    form_panel = ck_panel(form, title="Deal parameters")
    return chartis_shell(
        _DP_STYLES + hero + thesis_panel + market_panel + pipeline_cta
        + lifecycle_panel + form_panel + grid_header + grid
        + bookmark_hint() + _inline_js(slug),
        f"Deal Profile — {slug}",
        active_nav="/diligence/deal",
        subtitle="One source of truth",
    )
