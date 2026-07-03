"""
seller_request.py  (v44)
========================

Turns the tool's own gaps into a concrete ask. In a diligence process the most
useful output is often not what the data says but what is missing and why it
matters: which fields the extract lacks, which checks that blocks, and which
recoveries stay unverifiable as a result. This module assembles that into a
prioritized seller data request list, drawn entirely from signals the tool
already computed:

  the fixability manifest       fields whose absence made a screen unsupported or
                                left it unable to render a verdict
  the capture report            channels and drugs the panel structurally under
                                represents, where the seller's own data would fill
                                the picture
  two-method disagreements      recoveries where the extract lacks the evidence to
                                choose between two candidate billers

Each line states the field to request, why it matters (the specific check or
recovery it unblocks), and the dollars or rows at stake, so the ask is ranked by
impact rather than listed flat. Deterministic; no new inference.
"""
from __future__ import annotations

import pandas as pd


# field -> (what it unblocks, why it matters in diligence terms)
_FIELD_RATIONALE = {
    "diagnosis": ("ICD-10 date-of-service validity and age/sex conflict screens",
                  "without a diagnosis column those coding screens cannot run at all"),
    "modifiers": ("JW/JZ single-dose wastage verification",
                  "without a modifier column, missing-modifier exposure is unverifiable, "
                  "not absent"),
    "claim_status": ("closed-claims-only isolation",
                     "without an adjudication/status field, open and closed claims "
                     "cannot be separated, and open claims bias share and mono/combo mix"),
    "patient_age": ("age-based plausibility on maternity/newborn diagnoses",
                    "age conflicts cannot be judged without a patient age"),
    "patient_sex": ("sex-based plausibility screens",
                    "sex conflicts cannot be judged without patient sex"),
    "date": ("date-of-service validity, deactivated-NPI-on-DOS, claims-lag runout",
             "temporal checks and completion factors need a service or paid date"),
    "ndc": ("NOC/J-code disambiguation and drug normalization",
            "an 11-digit NDC resolves ambiguous J-codes to a specific product"),
    "billing_npi": ("direct billing-provider identification",
                    "recovery confidence is highest when at least some billing NPIs "
                    "are present to learn in-panel patterns from"),
}


def build_seller_request(fixability: pd.DataFrame = None,
                         capture: dict = None,
                         agreement_summary: pd.DataFrame = None,
                         coverage: pd.DataFrame = None) -> pd.DataFrame:
    """Assemble the prioritized seller data request list from the tool's gaps."""
    rows = []

    # ---- missing fields from the fixability manifest ----
    if fixability is not None and not fixability.empty:
        # a field is worth requesting if it is missing-required or missing-for-verdict
        need = {}
        for _, r in fixability.iterrows():
            for col in ("missing_required", "missing_for_verdict"):
                for f in str(r.get(col, "") or "").split(","):
                    f = f.strip()
                    if not f:
                        continue
                    need.setdefault(f, set()).add(r["fix"])
        for f, fixes in need.items():
            unblocks, why = _FIELD_RATIONALE.get(
                f, (f"the {f}-dependent checks", "needed to run those checks"))
            rows.append({
                "priority": "high" if f in ("diagnosis", "claim_status", "date") else "medium",
                "request": f"the {f} field",
                "unblocks": unblocks,
                "why_it_matters": why,
                "stakes": f"{len(fixes)} check(s): {', '.join(sorted(fixes))}",
            })

    # ---- capture blind spots ----
    if capture:
        ch = capture.get("channel_completeness")
        if isinstance(ch, pd.DataFrame) and "under_captured" in ch.columns:
            under = ch[ch["under_captured"]]
            for _, r in under.iterrows():
                rows.append({
                    "priority": "high" if r["channel"] in ("va_military", "cash") else "medium",
                    "request": f"complete {r['channel'].replace('_',' ')} claims or a payer-mix KPI",
                    "unblocks": "true-book sizing for a structurally under-captured channel",
                    "why_it_matters": (f"the panel captures this channel poorly, so "
                                       f"the {round(float(r.get('share_pct',0)),1)}% of visible "
                                       f"dollars here understates the true volume"),
                    "stakes": f"${float(r['dollars']):,.0f} visible; true amount larger",
                })
        dr = capture.get("drug_capture_flags")
        if isinstance(dr, pd.DataFrame) and "well_captured" in dr.columns:
            poor = dr[~dr["well_captured"]]
            if not poor.empty:
                poor_d = float(poor["dollars"].sum())
                rows.append({
                    "priority": "medium",
                    "request": "pharmacy-benefit / specialty-pharmacy claims feed",
                    "unblocks": "capture of self-administered and white-bag drugs",
                    "why_it_matters": ("a medical claims panel misses pharmacy-benefit "
                                       "drugs, so those are under-represented here"),
                    "stakes": f"${poor_d:,.0f} in poorly-captured drug codes",
                })

    # ---- two-method disagreements ----
    if agreement_summary is not None and not agreement_summary.empty:
        dis = agreement_summary[agreement_summary["agreement"] == "disagree"]
        if not dis.empty:
            d = float(dis["dollars"].sum())
            n = int(dis["rows"].sum())
            rows.append({
                "priority": "high" if d > 0 else "medium",
                "request": "billing provider name or TIN on claims where the biller is blank",
                "unblocks": "resolution of two-method recovery disagreements",
                "why_it_matters": ("the in-panel pattern and the CMS pool name different "
                                   "billers on these rows, and the extract lacks the field "
                                   "to break the tie"),
                "stakes": f"{n} rows, ${d:,.0f}, currently leads not facts",
            })

    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame([{
            "priority": "none",
            "request": "no additional fields required",
            "unblocks": "the delivered extract supports the checks that were run",
            "why_it_matters": "",
            "stakes": "",
        }])
        out.attrs["note"] = "The delivered extract was sufficient for the checks run."
        return out
    order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    out = out.sort_values("priority", key=lambda s: s.map(order)).reset_index(drop=True)
    out.attrs["note"] = (
        f"{len(out)} data requests, ranked by impact. Each names the field to ask "
        f"the seller for and the specific check or recovery it unblocks. This is the "
        f"list to send with the data-room follow-up.")
    return out
