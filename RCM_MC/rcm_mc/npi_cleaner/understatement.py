"""Claims-understatement cleaner + analyzer — *why claims understate the
business, and a labeled gross-up that corrects it*.

Why this module exists (the investment lens)
---------------------------------------------
A PE desk underwrites a healthcare-services target on three growth levers:

  * **VOLUME / demographics** — how many encounters, and is that growing.
  * **PRICE / reimbursement** — the realized rate per encounter, and its drift.
  * **SCALE / consolidation** — one owner getting bigger by rolling up NPIs.

When the underwriting data is a *claims extract*, the claims **systematically
understate** the true business on all three levers: denied and self-pay and
capitated encounters never reach a fee-for-service claim, the realized rate is
hidden behind billed-vs-paid and un-summed secondary payments, and one owner's
volume is fragmented across many NPIs/TINs so a roll-up's true scale looks
small. Underwrite off the low number and you misprice the deal.

This module (a) documents *why* claims understate — a structured
:data:`TAXONOMY` a partner reads to know what to ask for; (b) **detects** the
understatement in a cleaned claims file; and (c) produces a **labeled,
methodology-transparent gross-up** — every corrected figure carries its method,
its assumption, a low/base/high band, and the word ``MODELED``. It never
fabricates a "true" number as if it were observed: where the data cannot
support a gross-up, it emits a **diligence request** (what to ask the target
for) instead.

Honesty rails (mirrors ``vendor_v49/npi_recovery/coverage_grossup.py``)
----------------------------------------------------------------------
  * Every estimate is tagged ``MODELED`` and states the lever + assumption.
  * A band is shown wherever an assumption drives the number.
  * An *observed* de-duplication (owner roll-up when an owner column exists) is
    tagged ``OBSERVED``, never MODELED — it is arithmetic on real rows.
  * When the leg cannot be measured, the output is a diligence request, not a
    guessed figure.

Offline, deterministic, stdlib-only for the core math (no network, no LLM, no
new runtime deps). Column detection is *reused* from :mod:`.engine` so this
analyzer and the cleaner agree on what a billing NPI / amount / revenue-code
column is. Degrades gracefully on missing columns — it returns
"not detectable — request X" rather than raising.

Public surface::

    understatement.analyze(headers, rows, assumptions=...)   -> Result
    understatement.analyze_bytes(data, name, assumptions=...) -> Result
    understatement.analyze_frame(df, assumptions=...)         -> Result   (pandas)
    understatement.Assumptions(...)                           -> the knobs
    understatement.TAXONOMY                                   -> the cause list
    understatement.sample_claims_csv()                        -> a demo file
    understatement_report.build_report(result, name, ts)     -> HTML one-pager
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import engine

# The three growth levers a PE desk tracks. Every taxonomy entry and every
# finding is filed under exactly one of these so the scorecard reads per-lever.
LEVER_VOLUME = "VOLUME"
LEVER_PRICE = "PRICE"
LEVER_SCALE = "SCALE"
LEVERS = (LEVER_VOLUME, LEVER_PRICE, LEVER_SCALE)

# Status of a detection over the supplied file.
STATUS_DETECTED = "detected"          # a signal of this understatement is present
STATUS_CLEAN = "captured"             # the leg is present/counted in the extract
STATUS_NOT_DETECTABLE = "not_detectable"  # the columns needed aren't here → ask


# --------------------------------------------------------------------------- #
# 1. THE TAXONOMY — the documented "why claims understate", by lever.          #
#    This IS a deliverable: a partner reads it to know what to ask the target  #
#    for. Each entry states why it understates, how (if at all) to detect it   #
#    in a claims file, and how to correct it (method + the assumption the      #
#    correction rests on). ``magnitude`` is a coarse direction/size hint —     #
#    always an UNDERSTATEMENT (claims read low), never presented as measured.  #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Cause:
    """One documented reason a claims extract understates the true business.

    ``how_to_correct`` always names a METHOD and the ASSUMPTION it rests on —
    a gross-up with no stated assumption is a fabricated number, which this
    module refuses to emit."""
    id: str
    lever: str
    name: str
    why_it_understates: str
    how_to_detect: str
    how_to_correct: str
    magnitude: str  # coarse hint, e.g. "understates volume 5-15%"


TAXONOMY: Tuple[Cause, ...] = (
    # ---- VOLUME understatement ------------------------------------------- #
    Cause(
        "denied_lines_dropped", LEVER_VOLUME,
        "Denied / rejected lines dropped from counts",
        "Delivered care that a payer denied is real volume, but many extracts "
        "are pulled from a paid-claims/remittance view that silently excludes "
        "denied or zero-paid lines.",
        "A denial-reason (CARC) column, or paid==0 while billed>0 lines. If "
        "the file has neither denied nor zero-paid lines at all, denials were "
        "likely filtered upstream.",
        "Add back denied volume: observed x denial_rate/(1-denial_rate). "
        "ASSUMPTION: denied lines run ~denial_rate of delivered volume.",
        "understates volume ~5-15%",
    ),
    Cause(
        "cob_secondary_collapsed", LEVER_VOLUME,
        "Secondary-payer / COB legs collapsed or missing",
        "A single encounter can generate a primary AND a secondary "
        "(coordination-of-benefits) claim leg; a primary-only extract counts "
        "one and drops the other, or collapses both to one row.",
        "A payer-sequence / COB / secondary-payer column, or primary paid < "
        "allowed with a patient-responsibility remainder that a secondary "
        "later covered.",
        "De-duplicate encounters across payer legs for a clean count; do NOT "
        "add the legs as separate encounters. ASSUMPTION: leg-to-encounter "
        "mapping via claim id + service date.",
        "distorts volume; usually double-counts legs, undercounts encounters",
    ),
    Cause(
        "capitated_bundled_no_ffs", LEVER_VOLUME,
        "Capitated / global / bundled encounters generate no FFS claim",
        "Care under capitation, a global surgical period, or a bundled/episode "
        "payment produces no per-service fee-for-service claim, so a claims "
        "extract never sees those encounters.",
        "A whole payer or financial-class with paid==0 across the board "
        "(cap arrangement), or global-period modifiers. Largely NOT visible "
        "from FFS claims alone.",
        "Gross up with the target's capitated member-months / encounter logs "
        "(not in the claims). ASSUMPTION: capitated share supplied by target.",
        "understates volume where capitation/bundles are material",
    ),
    Cause(
        "self_pay_never_billed", LEVER_VOLUME,
        "Self-pay / cash-pay / uninsured encounters never billed to a payer",
        "Self-pay, cash-pay and uninsured encounters are frequently never "
        "submitted to any payer, so a payer-claims extract omits them entirely.",
        "A payer / financial-class value of self-pay/cash/uninsured. If the "
        "extract is payer-claims only, these are absent rather than labeled.",
        "Add back self-pay volume: observed x self_pay_share/(1-self_pay_share). "
        "ASSUMPTION: self-pay is self_pay_share of true encounters.",
        "understates volume ~3-12%",
    ),
    Cause(
        "preauth_denied_delivered", LEVER_VOLUME,
        "Pre-auth-denied care that was still delivered",
        "Care delivered after a prior-authorization denial (or without auth) "
        "may never be billed or may be written off, so it never appears as a "
        "paid claim.",
        "Not visible from a standard claims extract; a pre-auth/UM log is "
        "required.",
        "Request the UM / prior-auth system export. ASSUMPTION: none — this is "
        "a diligence request, not a computed gross-up.",
        "understates volume; size unknown without UM data",
    ),
    Cause(
        "encounter_vs_claim_gap", LEVER_VOLUME,
        "Encounter-vs-claim gap (claims != encounters)",
        "One encounter can yield several claim lines and one claim can span "
        "several encounters; counting claim LINES as encounters mis-states "
        "volume, usually low at the encounter grain.",
        "Lines-per-claim > 1 with a claim-id column; presence of both line and "
        "header grain.",
        "Roll lines up to claims/encounters via claim id + patient + service "
        "date. ASSUMPTION: claim id identifies the encounter.",
        "mis-states volume vs the encounter grain",
    ),
    Cause(
        "split_prof_facility_miscount", LEVER_VOLUME,
        "Split professional-vs-facility billing counted as one or neither",
        "A hospital-based encounter bills a professional (CMS-1500) claim and "
        "a facility (UB-04) claim separately; an extract from one system sees "
        "only one side, and a naive merge double-counts.",
        "Revenue-code / type-of-bill facility lines with no professional "
        "(HCPCS + office POS) counterpart, or vice-versa.",
        "Reconcile the two legs to one encounter; count facility and "
        "professional revenue on their own bases. ASSUMPTION: legs link via "
        "patient + service date.",
        "understates one leg's revenue and/or the encounter count",
    ),
    Cause(
        "ancillary_transport_dropped", LEVER_VOLUME,
        "Interfacility / transport / ancillary legs billed separately and dropped",
        "Ambulance/transport, anesthesia, pathology, DME and other ancillary "
        "legs are billed on separate claims, often by a different entity, and "
        "are dropped from a single-source extract.",
        "Ancillary revenue codes / HCPCS present or conspicuously absent for "
        "settings that require them (e.g. surgery with no anesthesia line).",
        "Add the ancillary legs from the other billing systems. ASSUMPTION: "
        "ancillary attach-rate supplied or benchmarked.",
        "understates volume and revenue of ancillary services",
    ),
    Cause(
        "claims_runout_truncation", LEVER_VOLUME,
        "Date-window truncation (claims lag / run-out) undercounts recent periods",
        "Claims are submitted and paid weeks-to-months after service, so the "
        "most recent months in an extract are incomplete — the freshest, most "
        "underwriting-relevant period reads artificially low.",
        "Service-date monthly volume that drops sharply in the final month(s) "
        "vs the trailing run-rate.",
        "Gross the recent period to full completion: recent x (1/completion - "
        "1) add-back. ASSUMPTION: completion-factor lag curve.",
        "understates the most recent 1-3 months materially",
    ),
    # ---- PRICE / REIMBURSEMENT understatement ---------------------------- #
    Cause(
        "billed_not_allowed_paid", LEVER_PRICE,
        "Using billed / charge instead of allowed or paid",
        "Billed charges are list-price fiction; the realized rate is the "
        "allowed/paid amount. A file that carries only billed cannot show the "
        "true reimbursement, and billed drift != rate drift.",
        "Which of billed / allowed / paid columns are present. Paid absent -> "
        "realized rate is not observable.",
        "Compute realized rate = paid per unit/encounter where paid exists; "
        "else request the remit (835) allowed/paid. ASSUMPTION: paid reflects "
        "the contracted rate.",
        "realized rate unobservable or mis-stated when only billed is present",
    ),
    Cause(
        "contractual_adjustment_hidden", LEVER_PRICE,
        "Contractual adjustments hide the true realized rate",
        "The write-down from billed to allowed (the contractual adjustment) is "
        "where the real rate lives; if the adjustment isn't in the file, the "
        "yield (paid/billed) looks like a discount rather than a negotiated "
        "rate.",
        "Presence of an allowed column alongside billed and paid; a "
        "billed-only file hides it.",
        "Derive realized yield = paid/billed and rate = paid/unit. ASSUMPTION: "
        "the adjustment equals billed - allowed.",
        "obscures the realized rate; not itself a dollar understatement",
    ),
    Cause(
        "cob_payment_not_summed", LEVER_PRICE,
        "Secondary / COB payments not summed into total paid",
        "Total realized reimbursement = primary paid + secondary paid + "
        "patient paid. An extract that carries only the primary payer's paid "
        "understates the realized rate per encounter.",
        "A secondary-payer paid column, or a patient-responsibility balance "
        "that was in fact collected.",
        "Corrected realized rate = observed rate x (1 + cob_uplift). "
        "ASSUMPTION: secondary+patient adds cob_uplift over primary paid.",
        "understates realized rate ~2-10%",
    ),
    Cause(
        "fee_schedule_lag", LEVER_PRICE,
        "Fee-schedule updates not yet reflected in the data window",
        "A rate increase effective mid-window (annual fee-schedule update, a "
        "renegotiated contract) is only partially reflected, so the average "
        "realized rate reads below the go-forward rate.",
        "Realized rate trend that steps up late in the window; effective-date "
        "metadata (not usually in claims).",
        "Reprice recent volume at the current fee schedule. ASSUMPTION: "
        "current schedule supplied by target.",
        "understates the go-forward rate when a raise is mid-window",
    ),
    Cause(
        "site_of_service_differential", LEVER_PRICE,
        "Site-of-service / facility-vs-office differential",
        "The same procedure reimburses differently in a facility vs an office "
        "(and carries a separate facility fee); mixing sites or reading only "
        "the professional side understates total reimbursement per service.",
        "Place-of-service mix vs a flat per-code rate; facility revenue codes "
        "present or absent.",
        "Price each service at its site-specific rate and add the facility fee "
        "leg. ASSUMPTION: site-of-service rate table supplied.",
        "understates reimbursement per service where facility fees apply",
    ),
    Cause(
        "sequestration_takeback", LEVER_PRICE,
        "Sequestration / take-back adjustments depress observed paid",
        "Medicare sequestration (a ~2% withhold) and later take-backs/recoups "
        "lower the observed paid below the contractual rate; reading paid "
        "at face understates the underlying negotiated rate.",
        "Adjustment/CARC codes for sequestration (CO-253) or recoupment; a "
        "small uniform haircut on Medicare paid.",
        "Add sequestration back to reach the contractual rate. ASSUMPTION: "
        "~2% Medicare withhold over the affected period.",
        "understates the contractual rate ~2% on affected Medicare volume",
    ),
    # ---- SCALE / CONSOLIDATION understatement ---------------------------- #
    Cause(
        "npi_tin_fragmentation", LEVER_SCALE,
        "One owner's volume fragmented across many NPIs and/or TINs",
        "A roll-up's true scale is the sum across every NPI/TIN it owns, but "
        "claims carry the billing NPI/TIN, so an owner that bills under dozens "
        "of NPIs looks like dozens of small providers.",
        "Distinct billing NPI count vs distinct TIN count vs distinct owner "
        "count (when an owner/parent column exists).",
        "De-fragment: group volume/charges to the OWNER (observed dedup when an "
        "owner column exists). ASSUMPTION: the ownership crosswalk is complete.",
        "understates per-owner scale by the NPIs-per-owner factor",
    ),
    Cause(
        "billing_vs_rendering_attribution", LEVER_SCALE,
        "Billing-provider vs rendering-provider attribution",
        "Attributing volume to the rendering individual scatters it across "
        "clinicians; attributing to the billing org concentrates it. Picking "
        "the wrong grain understates the entity's true scale.",
        "Both a billing NPI and a rendering NPI column present.",
        "Attribute to the billing entity for scale, to the rendering NPI for "
        "productivity. ASSUMPTION: billing NPI is the economic entity.",
        "mis-attributes scale between individual and entity",
    ),
    Cause(
        "org_vs_individual_npi_doublemap", LEVER_SCALE,
        "Org-NPI (type 2) vs individual-NPI (type 1) double-mapping",
        "The same volume can appear under a type-1 individual NPI and a type-2 "
        "organization NPI; counting both double-maps, counting one drops the "
        "other's scale.",
        "Distinct NPIs that split into individual vs organization types "
        "(requires an NPPES type lookup — not in the claim number itself).",
        "Map each NPI to its NPPES type and roll to the organization. "
        "ASSUMPTION: NPPES type-2 is the entity of record.",
        "double-maps or drops scale depending on grain chosen",
    ),
    Cause(
        "acquired_practice_old_tin", LEVER_SCALE,
        "Acquired-practice claims still under the old TIN",
        "After an acquisition, claims often bill under the seller's legacy "
        "TIN/NPI for months; attributing by billing TIN leaves that volume "
        "with the old owner and understates the acquirer's scale.",
        "TINs that appear only before an acquisition date, or a TIN not on the "
        "acquirer's roster (needs the deal/roster context).",
        "Re-map legacy TINs to the acquirer per the transaction timeline. "
        "ASSUMPTION: acquisition dates + TIN roster supplied.",
        "understates acquirer scale during the TIN-migration window",
    ),
    Cause(
        "chain_parent_attribution_absent", LEVER_SCALE,
        "Chain / parent attribution absent",
        "Claims carry no parent-company field, so franchise/chain/PE-platform "
        "scale is invisible unless an ownership crosswalk is joined in — each "
        "location reads as an independent small biller.",
        "No owner/parent/chain column present; only per-location NPIs/TINs.",
        "Join an ownership crosswalk (e.g. CMS PECOS ownership, HCRIS, target "
        "roster) to roll locations to the parent. ASSUMPTION: crosswalk "
        "supplied — diligence request, not a computed gross-up.",
        "understates platform scale entirely without a crosswalk",
    ),
)

# Fast lookup by id.
TAXONOMY_BY_ID: Dict[str, Cause] = {c.id: c for c in TAXONOMY}


def taxonomy_for_lever(lever: str) -> List[Cause]:
    return [c for c in TAXONOMY if c.lever == lever]


# --------------------------------------------------------------------------- #
# 2. ASSUMPTIONS — the knobs every gross-up states. Defaults are conservative  #
#    diligence conventions, NOT measured facts; each is surfaced on the        #
#    output next to the figure it drives.                                      #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Assumptions:
    """Gross-up knobs. Every default is a stated diligence convention, never a
    measured fact — the output prints the assumption beside the estimate.

    ``band_rel`` widens each assumption by +/- this fraction to produce the
    low/base/high band, so the fragility of the estimate is on the page."""
    denial_rate: float = 0.10          # denied share of delivered volume
    self_pay_share: float = 0.08       # self-pay share of true encounters
    cob_uplift: float = 0.05           # secondary+patient over primary paid
    runout_completion: float = 0.85    # completeness of the freshest period
    band_rel: float = 0.50             # +/- relative swing for the band

    def band(self, base: float) -> Tuple[float, float]:
        """Low/high for an assumption value under the relative band."""
        r = max(0.0, self.band_rel)
        return base * (1.0 - r), base * (1.0 + r)


def default_assumptions() -> Assumptions:
    return Assumptions()


# --------------------------------------------------------------------------- #
# 3. FINDINGS + GROSS-UPS — the typed outputs.                                 #
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    """The detection verdict for one taxonomy cause over the supplied file."""
    cause_id: str
    lever: str
    name: str
    status: str                       # detected | captured | not_detectable
    summary: str                      # plain-English, safe to render
    evidence: Dict[str, object] = field(default_factory=dict)
    diligence: Optional[str] = None   # the ask when not detectable


@dataclass
class GrossUp:
    """A corrected estimate. ``label`` is MODELED (assumption-driven) or
    OBSERVED (exact arithmetic on real rows). When ``computable`` is False the
    correction is a ``diligence`` request instead of an estimate."""
    kind: str                         # volume | realized_rate | scale
    label: str                        # "MODELED" | "OBSERVED"
    lever: str
    title: str
    basis: str                        # unit of the figures ("lines", "$/line"…)
    method: str
    assumption: str
    computable: bool
    observed: Optional[float] = None
    low: Optional[float] = None
    base: Optional[float] = None
    high: Optional[float] = None
    components: List[Dict[str, object]] = field(default_factory=list)
    note: str = ""
    diligence: Optional[str] = None


@dataclass
class Result:
    """The whole analysis: detected columns, per-cause findings, the three
    gross-ups, and the consolidated diligence request list."""
    n_rows: int
    columns: Dict[str, object]
    findings: List[Finding]
    grossups: Dict[str, GrossUp]
    diligence_requests: List[str]
    assumptions: Assumptions
    warnings: List[str] = field(default_factory=list)

    def findings_for_lever(self, lever: str) -> List[Finding]:
        return [f for f in self.findings if f.lever == lever]

    def as_dict(self) -> Dict[str, object]:
        """Plain-data view for JSON export and the renderer."""
        return {
            "n_rows": self.n_rows,
            "columns": self.columns,
            "assumptions": {
                "denial_rate": self.assumptions.denial_rate,
                "self_pay_share": self.assumptions.self_pay_share,
                "cob_uplift": self.assumptions.cob_uplift,
                "runout_completion": self.assumptions.runout_completion,
                "band_rel": self.assumptions.band_rel,
            },
            "findings": [
                {
                    "cause_id": f.cause_id, "lever": f.lever, "name": f.name,
                    "status": f.status, "summary": f.summary,
                    "evidence": f.evidence, "diligence": f.diligence,
                }
                for f in self.findings
            ],
            "grossups": {
                k: {
                    "kind": g.kind, "label": g.label, "lever": g.lever,
                    "title": g.title, "basis": g.basis, "method": g.method,
                    "assumption": g.assumption, "computable": g.computable,
                    "observed": g.observed, "low": g.low, "base": g.base,
                    "high": g.high, "components": g.components,
                    "note": g.note, "diligence": g.diligence,
                }
                for k, g in self.grossups.items()
            },
            "diligence_requests": self.diligence_requests,
            "warnings": self.warnings,
        }


# --------------------------------------------------------------------------- #
# Column detection — REUSES the engine's helpers so this analyzer and the      #
# cleaner agree on roles. Adds only the roles the cleaner doesn't surface      #
# (TIN, owner/parent, financial-class, payer-sequence).                        #
# --------------------------------------------------------------------------- #
_TIN_EXACT = {"tin", "ein", "taxid"}
_TIN_SUBSTR = ("taxid", "federaltax", "grouptin", "billingtin", "practicetin",
               "grouptaxid", "employerid")
_OWNER_SUBSTR = ("ownername", "owner", "parentorg", "parentname", "parentco",
                 "chainname", "chain", "healthsystem", "systemname",
                 "platform", "portfolioco", "affiliation", "entityname",
                 "grouppractice", "parentcompany", "roll up", "rollup")
_OWNER_EXCLUDE = ("patient", "guarantor", "subscriber", "member", "guardian",
                  "policy")
_FINCLASS_SUBSTR = ("financialclass", "finclass", "payertype", "payerclass",
                    "coveragetype", "insurancetype", "plantype", "claimtype")
_PAYERSEQ_SUBSTR = ("payersequence", "payerseq", "payerorder", "payerrank",
                    "payerpriority", "coordinationofbenefits", "cobindicator",
                    "claimfilingorder", "insuranceorder", "primarysecondary",
                    "payerlevel", "cob")
# Payer / financial-class VALUES that mark a self-pay / uninsured encounter.
_SELFPAY_VALUE_RE = re.compile(
    r"self[\s\-_]?pay|cash[\s\-_]?pay|uninsured|no[\s\-_]?insurance|"
    r"private[\s\-_]?pay|patient[\s\-_]?pay|self$", re.IGNORECASE)
# Payer / sequence VALUES that mark a non-primary (secondary/tertiary) leg.
_SECONDARY_VALUE_RE = re.compile(
    r"second|secndary|tertiary|\bcob\b|supplement|payer\s*2|payer2|"
    r"^s$|^t$|^2$|^3$", re.IGNORECASE)


def _detect_tin(headers: List[str]) -> Optional[int]:
    for i, h in enumerate(headers):
        k = engine._norm_key(h)
        if k in _TIN_EXACT or any(s in k for s in _TIN_SUBSTR):
            return i
        # A bare "...TIN" suffix (BillTIN, ProviderTIN) with no better match.
        if k.endswith("tin") and "routing" not in k:
            return i
    return None


def _detect_owner(headers: List[str]) -> Optional[int]:
    for i, h in enumerate(headers):
        k = engine._norm_key(h)
        if any(x in k for x in _OWNER_EXCLUDE):
            continue
        if any(s in k for s in _OWNER_SUBSTR):
            return i
    return None


def _detect_one_sub(headers: List[str], subs: Tuple[str, ...]) -> Optional[int]:
    for i, h in enumerate(headers):
        k = engine._norm_key(h)
        if any(s in k for s in subs):
            return i
    return None


def _detect_rendering(headers: List[str], npi_idx: List[int],
                      billing_idx: Optional[int]) -> Optional[int]:
    """A rendering/servicing/attending individual NPI column distinct from the
    billing NPI — the billing-vs-rendering attribution signal."""
    for i in npi_idx:
        if i == billing_idx:
            continue
        k = engine._norm_key(headers[i])
        if any(x in k for x in ("rendering", "servicing", "attending",
                                "performing", "individual")):
            return i
    return None


def _detect_columns(headers: List[str], rows: List[List[str]]
                    ) -> Dict[str, object]:
    """Detect every role the understatement analysis needs, reusing the
    engine's detectors where they exist."""
    npi_idx, billing_idx = engine._detect_npi_columns(headers)
    cols: Dict[str, object] = {
        "npi_idx": npi_idx,
        "billing_idx": billing_idx,
        "rendering_idx": _detect_rendering(headers, npi_idx, billing_idx),
        "billed_i": engine._detect_one(
            headers, ("billedamt", "billed", "chargeamt", "charge",
                      "submittedamt")),
        "allowed_i": engine._detect_one(headers, ("allowedamt", "allowed")),
        "paid_i": engine._detect_one(
            headers, ("paidamt", "paymentamt", "planpaid", "paid")),
        "units_i": engine._detect_one(
            headers, ("units", "unit", "quantity", "qty", "srvccnt")),
        "carc_i": engine._detect_one(headers, engine._CARC_HINTS),
        "payer_i": engine._detect_one(headers, engine._PAYER_HINTS),
        "dos_i": engine._detect_one(
            headers, ("dateofservice", "servicedate", "svcdate", "dos",
                      "fromdate", "servicefromdate")),
        "claim_i": engine._detect_one(
            headers, ("claimid", "claimnumber", "claimno", "claim", "iclaim")),
        "patient_i": engine._detect_one(
            headers, ("patientid", "memberid", "subscriberid",
                      "patientaccount", "patientacct", "patient", "beneid")),
        "rev_set": sorted({i for i, h in enumerate(headers)
                           if any(x in engine._norm_key(h)
                                  for x in engine._REV_HINTS)}),
        "pos_i": engine._detect_one(
            headers, ("placeofservice", "poscode", "pos")),
        "hcpcs_i": engine._detect_one(headers, engine._HCPCS_HINTS),
        "tin_i": _detect_tin(headers),
        "owner_i": _detect_owner(headers),
        "finclass_i": _detect_one_sub(headers, _FINCLASS_SUBSTR),
        "payerseq_i": _detect_one_sub(headers, _PAYERSEQ_SUBSTR),
    }
    return cols


# --------------------------------------------------------------------------- #
# small numeric helpers (stdlib; mirror the cleaner's parsing + formatting)    #
# --------------------------------------------------------------------------- #
def _cell(row: List[str], i: Optional[int]) -> str:
    if i is None or i < 0 or i >= len(row):
        return ""
    return (row[i] or "").strip()


def _num(row: List[str], i: Optional[int]) -> Optional[float]:
    return engine._to_number(_cell(row, i))


def _month_of(raw: str) -> Optional[str]:
    """YYYY-MM for a date cell, normalizing via the cleaner's date parser so an
    un-normalized extract still buckets. None when unparseable."""
    if not raw:
        return None
    iso, _ = engine._clean_date_cell(raw)
    m = engine._DATE_ISO_RE.match(iso.strip()) if iso else None
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


# --------------------------------------------------------------------------- #
# 4. GROSS-UP ESTIMATORS — pure, deterministic, hand-computable.               #
# --------------------------------------------------------------------------- #
def grossup_volume(observed: int,
                   components: List[Dict[str, object]]) -> Dict[str, object]:
    """Combine additive volume add-backs into a low/base/high corrected count.

    Each component carries ``uplift_low``/``uplift_base``/``uplift_high`` (a
    fraction of the OBSERVED base). Uplifts are ADDED, never compounded, so the
    estimate is conservative and a partner can reproduce it from the visible
    numbers: estimate = observed x (1 + sum(uplift)). Counts are whole numbers.
    """
    obs = max(0, int(observed))
    s_low = sum(float(c["uplift_low"]) for c in components)
    s_base = sum(float(c["uplift_base"]) for c in components)
    s_high = sum(float(c["uplift_high"]) for c in components)
    return {
        "observed": obs,
        "low": round(obs * (1.0 + s_low)),
        "base": round(obs * (1.0 + s_base)),
        "high": round(obs * (1.0 + s_high)),
        "sum_uplift_base": s_base,
    }


def grossup_realized_rate(observed_rate: float,
                          cob_uplift: float,
                          band: Tuple[float, float]) -> Dict[str, object]:
    """Corrected realized rate = observed x (1 + cob_uplift). The band varies
    the uplift. Dollars are 2dp at the render layer; kept full-precision here."""
    lo_u, hi_u = band
    return {
        "observed": observed_rate,
        "low": observed_rate * (1.0 + lo_u),
        "base": observed_rate * (1.0 + cob_uplift),
        "high": observed_rate * (1.0 + hi_u),
    }


# --------------------------------------------------------------------------- #
# per-lever detection + gross-up assembly                                      #
# --------------------------------------------------------------------------- #
def _denial_signal(rows, cols) -> Tuple[int, int, str]:
    """(#denied-looking lines, #zero-paid lines, mode). ``mode`` says which
    signal was usable: 'carc', 'zeropay', or 'none'."""
    carc_i = cols["carc_i"]
    billed_i, paid_i = cols["billed_i"], cols["paid_i"]
    denied = zero_paid = 0
    for row in rows:
        if carc_i is not None:
            v = _cell(row, carc_i)
            if v and engine._CARC_GROUP_RE.sub("", v.upper()) not in ("", "0"):
                denied += 1
        b, p = _num(row, billed_i), _num(row, paid_i)
        if b is not None and b > 0 and p is not None and abs(p) < 1e-9:
            zero_paid += 1
    if carc_i is not None:
        return denied, zero_paid, "carc"
    if billed_i is not None and paid_i is not None:
        return denied, zero_paid, "zeropay"
    return 0, 0, "none"


def _selfpay_signal(rows, cols) -> Tuple[int, str]:
    """(#self-pay lines, mode). mode: 'payer'/'finclass'/'none'."""
    payer_i, fin_i = cols["payer_i"], cols["finclass_i"]
    col = fin_i if fin_i is not None else payer_i
    if col is None:
        return 0, "none"
    n = sum(1 for row in rows if _SELFPAY_VALUE_RE.search(_cell(row, col)))
    return n, ("finclass" if fin_i is not None else "payer")


def _secondary_signal(rows, cols) -> Tuple[int, str]:
    """(#non-primary legs, mode). Prefers a payer-sequence column, else scans
    payer values for secondary/tertiary spellings."""
    seq_i, payer_i = cols["payerseq_i"], cols["payer_i"]
    if seq_i is not None:
        n = sum(1 for row in rows if _SECONDARY_VALUE_RE.search(_cell(row, seq_i)))
        return n, "sequence"
    return 0, "none"


def _monthly_counts(rows, cols) -> List[Tuple[str, int]]:
    dos_i = cols["dos_i"]
    if dos_i is None:
        return []
    buckets: Dict[str, int] = {}
    for row in rows:
        m = _month_of(_cell(row, dos_i))
        if m:
            buckets[m] = buckets.get(m, 0) + 1
    return sorted(buckets.items())


def _median(vals: List[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _analyze_volume(rows, cols, A: Assumptions
                    ) -> Tuple[List[Finding], GrossUp, List[str]]:
    findings: List[Finding] = []
    components: List[Dict[str, object]] = []
    diligence: List[str] = []
    n = len(rows)

    # -- denied lines dropped ------------------------------------------------
    denied, zero_paid, mode = _denial_signal(rows, cols)
    if mode == "none":
        findings.append(Finding(
            "denied_lines_dropped", LEVER_VOLUME,
            TAXONOMY_BY_ID["denied_lines_dropped"].name, STATUS_NOT_DETECTABLE,
            "No denial-reason (CARC) column and no billed/paid pair — cannot "
            "tell whether denied lines were dropped from this extract.",
            {"mode": mode},
            "Request a denial/adjustment (CARC) column or the paid amount so "
            "denied and zero-paid lines can be counted."))
        diligence.append(
            "Denials: supply a CARC / denial-reason column (or paid amount) — "
            "confirm whether the extract is paid-claims-only (denials dropped).")
        # Extract may be paid-only: apply a MODELED add-back for dropped denials.
        u = A.denial_rate / (1.0 - A.denial_rate)
        lo_a, hi_a = A.band(A.denial_rate)
        components.append({
            "id": "denied_lines_dropped", "label": "denied add-back",
            "method": "observed x denial_rate/(1-denial_rate)",
            "assumption": f"denial_rate={A.denial_rate:.1%} of delivered volume",
            "uplift_base": u,
            "uplift_low": lo_a / (1.0 - lo_a),
            "uplift_high": hi_a / (1.0 - hi_a),
        })
    else:
        present = denied if mode == "carc" else zero_paid
        if present > 0:
            findings.append(Finding(
                "denied_lines_dropped", LEVER_VOLUME,
                TAXONOMY_BY_ID["denied_lines_dropped"].name, STATUS_CLEAN,
                f"{present:,} denied/zero-paid lines ({_pct(present, n)}) are "
                f"present and counted in this extract via the {mode} signal; "
                "no volume add-back for dropped denials.",
                {"mode": mode, "denied_lines": present,
                 "denied_pct": _pctf(present, n)}))
        else:
            findings.append(Finding(
                "denied_lines_dropped", LEVER_VOLUME,
                TAXONOMY_BY_ID["denied_lines_dropped"].name, STATUS_DETECTED,
                f"A {mode} signal exists but ZERO denied/zero-paid lines were "
                "found — denials were likely filtered upstream; volume "
                "understated by the dropped denials.",
                {"mode": mode, "denied_lines": 0}))
            u = A.denial_rate / (1.0 - A.denial_rate)
            lo_a, hi_a = A.band(A.denial_rate)
            components.append({
                "id": "denied_lines_dropped", "label": "denied add-back",
                "method": "observed x denial_rate/(1-denial_rate)",
                "assumption": f"denial_rate={A.denial_rate:.1%} of delivered "
                              "volume (extract shows no denials)",
                "uplift_base": u,
                "uplift_low": lo_a / (1.0 - lo_a),
                "uplift_high": hi_a / (1.0 - hi_a),
            })

    # -- self-pay never billed ----------------------------------------------
    sp_n, sp_mode = _selfpay_signal(rows, cols)
    if sp_mode == "none":
        findings.append(Finding(
            "self_pay_never_billed", LEVER_VOLUME,
            TAXONOMY_BY_ID["self_pay_never_billed"].name, STATUS_NOT_DETECTABLE,
            "No payer or financial-class column — self-pay/uninsured "
            "encounters cannot be identified and are likely absent from a "
            "payer-claims extract.",
            {"mode": sp_mode},
            "Self-pay: supply payer / financial-class, or the target's "
            "self-pay encounter log — payer claims omit never-billed self-pay."))
        diligence.append(
            "Self-pay: no payer/financial-class column — request self-pay "
            "encounter volume from the target's practice-management system.")
        u = A.self_pay_share / (1.0 - A.self_pay_share)
        lo_a, hi_a = A.band(A.self_pay_share)
        components.append({
            "id": "self_pay_never_billed", "label": "self-pay add-back",
            "method": "observed x self_pay_share/(1-self_pay_share)",
            "assumption": f"self_pay_share={A.self_pay_share:.1%} of true "
                          "encounters, absent from payer claims",
            "uplift_base": u,
            "uplift_low": lo_a / (1.0 - lo_a),
            "uplift_high": hi_a / (1.0 - hi_a),
        })
    elif sp_n > 0:
        findings.append(Finding(
            "self_pay_never_billed", LEVER_VOLUME,
            TAXONOMY_BY_ID["self_pay_never_billed"].name, STATUS_CLEAN,
            f"{sp_n:,} self-pay lines ({_pct(sp_n, n)}) are labeled and "
            f"present via the {sp_mode} column; still confirm no never-billed "
            "self-pay sits outside the extract.",
            {"mode": sp_mode, "self_pay_lines": sp_n,
             "self_pay_pct": _pctf(sp_n, n)}))
    else:
        findings.append(Finding(
            "self_pay_never_billed", LEVER_VOLUME,
            TAXONOMY_BY_ID["self_pay_never_billed"].name, STATUS_DETECTED,
            f"A {sp_mode} column exists but ZERO self-pay lines were found — "
            "self-pay encounters are likely never billed and thus missing.",
            {"mode": sp_mode, "self_pay_lines": 0}))
        u = A.self_pay_share / (1.0 - A.self_pay_share)
        lo_a, hi_a = A.band(A.self_pay_share)
        components.append({
            "id": "self_pay_never_billed", "label": "self-pay add-back",
            "method": "observed x self_pay_share/(1-self_pay_share)",
            "assumption": f"self_pay_share={A.self_pay_share:.1%} of true "
                          "encounters (none labeled in extract)",
            "uplift_base": u,
            "uplift_low": lo_a / (1.0 - lo_a),
            "uplift_high": hi_a / (1.0 - hi_a),
        })

    # -- claims run-out / recent-period truncation --------------------------
    months = _monthly_counts(rows, cols)
    if not months or len(months) < 3:
        findings.append(Finding(
            "claims_runout_truncation", LEVER_VOLUME,
            TAXONOMY_BY_ID["claims_runout_truncation"].name,
            STATUS_NOT_DETECTABLE,
            "Fewer than 3 months of service dates (or no date column) — run-out "
            "in the freshest period cannot be assessed.",
            {"months": len(months)},
            "Run-out: supply >=6 months of service dates and the paid-through "
            "date so the completion curve can be estimated."))
        diligence.append(
            "Run-out: date window too short — request the paid-through date and "
            ">=6 months of service dates to size claims-lag truncation.")
    else:
        last_m, last_c = months[-1]
        prior = [c for _, c in months[:-1]]
        med = _median([float(x) for x in prior])
        if med > 0 and last_c < 0.6 * med:
            addback_lines = last_c * (1.0 / A.runout_completion - 1.0)
            u = addback_lines / max(1, len(rows))
            lo_c, hi_c = A.band(A.runout_completion)
            # Completion is a share, so cap at 100%; a LOWER completion means a
            # LARGER add-back, so the band is inverted (high completion → low
            # estimate).
            hi_c = min(1.0, hi_c)
            lo_c = max(0.05, lo_c)
            findings.append(Finding(
                "claims_runout_truncation", LEVER_VOLUME,
                TAXONOMY_BY_ID["claims_runout_truncation"].name,
                STATUS_DETECTED,
                f"Final month {last_m} has {last_c:,} lines vs a "
                f"{med:,.0f}-line trailing median — the freshest period looks "
                "incomplete (claims run-out).",
                {"final_month": last_m, "final_lines": last_c,
                 "trailing_median": round(med, 1)}))
            components.append({
                "id": "claims_runout_truncation", "label": "run-out add-back",
                "method": "recent x (1/completion - 1), spread over the file",
                "assumption": f"completion={A.runout_completion:.0%} in the "
                              "freshest period",
                "uplift_base": u,
                "uplift_low": (last_c * (1.0 / hi_c - 1.0)) / max(1, len(rows)),
                "uplift_high": (last_c * (1.0 / lo_c - 1.0)) / max(1, len(rows)),
            })
        else:
            findings.append(Finding(
                "claims_runout_truncation", LEVER_VOLUME,
                TAXONOMY_BY_ID["claims_runout_truncation"].name, STATUS_CLEAN,
                f"Final month {last_m} ({last_c:,} lines) is within the "
                "trailing run-rate — no obvious run-out truncation.",
                {"final_month": last_m, "final_lines": last_c,
                 "trailing_median": round(med, 1)}))

    # -- secondary / COB legs (volume grain) --------------------------------
    sec_n, sec_mode = _secondary_signal(rows, cols)
    if sec_mode == "none":
        findings.append(Finding(
            "cob_secondary_collapsed", LEVER_VOLUME,
            TAXONOMY_BY_ID["cob_secondary_collapsed"].name,
            STATUS_NOT_DETECTABLE,
            "No payer-sequence / COB column — cannot tell if secondary legs "
            "are present, missing, or collapsed into the primary.",
            {"mode": sec_mode},
            "COB: supply a payer-sequence/COB indicator so primary vs "
            "secondary legs can be separated for a clean encounter count."))
        diligence.append(
            "COB legs: no payer-sequence column — request it to de-duplicate "
            "primary/secondary legs to encounters (avoid double-counting).")
    elif sec_n > 0:
        findings.append(Finding(
            "cob_secondary_collapsed", LEVER_VOLUME,
            TAXONOMY_BY_ID["cob_secondary_collapsed"].name, STATUS_DETECTED,
            f"{sec_n:,} non-primary (secondary/tertiary) legs are present via "
            f"the {sec_mode} column — counting legs as encounters would "
            "double-count; roll legs up by claim id + service date.",
            {"mode": sec_mode, "secondary_legs": sec_n}))
    else:
        findings.append(Finding(
            "cob_secondary_collapsed", LEVER_VOLUME,
            TAXONOMY_BY_ID["cob_secondary_collapsed"].name, STATUS_CLEAN,
            f"A {sec_mode} column exists and all legs read primary — no "
            "secondary-leg double-count risk in this extract.",
            {"mode": sec_mode, "secondary_legs": 0}))

    # -- split professional vs facility -------------------------------------
    rev_set = cols["rev_set"]
    pos_i, hcpcs_i = cols["pos_i"], cols["hcpcs_i"]
    if rev_set or pos_i is not None:
        fac = prof = 0
        rev_i = rev_set[0] if rev_set else None
        for row in rows:
            has_rev = bool(_cell(row, rev_i)) if rev_i is not None else False
            pos = _cell(row, pos_i)
            has_hcpcs = bool(_cell(row, hcpcs_i)) if hcpcs_i is not None else False
            if has_rev:
                fac += 1
            elif has_hcpcs and pos in ("11", "22", "19", "49", "20"):
                prof += 1
        if fac and prof:
            findings.append(Finding(
                "split_prof_facility_miscount", LEVER_VOLUME,
                TAXONOMY_BY_ID["split_prof_facility_miscount"].name,
                STATUS_DETECTED,
                f"{fac:,} facility (revenue-code) lines and {prof:,} "
                "professional lines coexist — reconcile the two legs to one "
                "encounter and count each revenue base separately.",
                {"facility_lines": fac, "professional_lines": prof}))
        elif fac and not prof:
            findings.append(Finding(
                "split_prof_facility_miscount", LEVER_VOLUME,
                TAXONOMY_BY_ID["split_prof_facility_miscount"].name,
                STATUS_DETECTED,
                f"{fac:,} facility (revenue-code) lines but no professional "
                "counterpart in this extract — the professional leg is billed "
                "elsewhere and is missing.",
                {"facility_lines": fac, "professional_lines": 0}))
        else:
            findings.append(Finding(
                "split_prof_facility_miscount", LEVER_VOLUME,
                TAXONOMY_BY_ID["split_prof_facility_miscount"].name,
                STATUS_CLEAN,
                "No facility revenue-code lines detected — this reads as a "
                "professional (CMS-1500) extract; confirm no facility leg is "
                "billed separately.",
                {"facility_lines": fac, "professional_lines": prof}))
    else:
        findings.append(Finding(
            "split_prof_facility_miscount", LEVER_VOLUME,
            TAXONOMY_BY_ID["split_prof_facility_miscount"].name,
            STATUS_NOT_DETECTABLE,
            "No revenue-code or place-of-service column — cannot separate "
            "facility from professional lines.",
            {},
            "Split billing: supply revenue code / type-of-bill / place-of-"
            "service to reconcile professional vs facility legs."))
        diligence.append(
            "Split prof/facility: no rev-code/POS column — request both the "
            "professional (1500) and facility (UB-04) extracts.")

    # Causes that a standard FFS claims file cannot show at all → pure asks.
    for cid, ask in (
        ("capitated_bundled_no_ffs",
         "Capitation/bundles: request capitated member-months and encounter "
         "logs — capitated/global/bundled care generates no FFS claim."),
        ("preauth_denied_delivered",
         "Pre-auth: request the UM/prior-auth log — auth-denied care that was "
         "delivered never appears as a paid claim."),
        ("ancillary_transport_dropped",
         "Ancillary: request transport/anesthesia/path/DME extracts — these "
         "legs bill separately and are dropped from a single-source pull."),
    ):
        findings.append(Finding(
            cid, LEVER_VOLUME, TAXONOMY_BY_ID[cid].name, STATUS_NOT_DETECTABLE,
            TAXONOMY_BY_ID[cid].why_it_understates,
            {}, ask))
        diligence.append(ask)

    # Encounter-vs-claim grain finding (informational; roll-up if claim id).
    claim_i, patient_i = cols["claim_i"], cols["patient_i"]
    if claim_i is not None:
        seen: Dict[str, int] = {}
        for row in rows:
            cid = _cell(row, claim_i)
            if cid:
                seen[cid] = seen.get(cid, 0) + 1
        n_claims = len(seen)
        lpc = (sum(seen.values()) / n_claims) if n_claims else 0.0
        findings.append(Finding(
            "encounter_vs_claim_gap", LEVER_VOLUME,
            TAXONOMY_BY_ID["encounter_vs_claim_gap"].name,
            STATUS_DETECTED if lpc > 1.05 else STATUS_CLEAN,
            f"{len(rows):,} lines roll up to {n_claims:,} claims "
            f"({lpc:.2f} lines/claim) — count encounters at the claim grain, "
            "not the line grain.",
            {"n_lines": len(rows), "n_claims": n_claims,
             "lines_per_claim": round(lpc, 2)}))
    else:
        findings.append(Finding(
            "encounter_vs_claim_gap", LEVER_VOLUME,
            TAXONOMY_BY_ID["encounter_vs_claim_gap"].name,
            STATUS_NOT_DETECTABLE,
            "No claim-id column — cannot roll lines up to claims/encounters; "
            "line counts overstate lines but say nothing about encounters.",
            {},
            "Encounter grain: supply a claim-id (and patient-id) so lines can "
            "be rolled up to encounters."))
        diligence.append(
            "Encounter grain: no claim-id column — request claim id + patient "
            "id to count encounters rather than lines.")

    # Assemble the volume gross-up (or a diligence-only stub).
    observed = len(rows)
    if components:
        g = grossup_volume(observed, components)
        gu = GrossUp(
            kind="volume", label="MODELED", lever=LEVER_VOLUME,
            title="Corrected delivered-volume estimate (lines)",
            basis="claim lines",
            method="observed x (1 + sum of add-back uplifts); add-backs are "
                   "additive, not compounded",
            assumption="; ".join(str(c["assumption"]) for c in components),
            computable=True,
            observed=float(observed),
            low=float(g["low"]), base=float(g["base"]), high=float(g["high"]),
            components=components,
            note="MODELED add-backs for legs claims commonly omit. Each "
                 "component states its method + assumption; the band varies "
                 "each assumption by +/-{:.0%}.".format(A.band_rel))
    else:
        gu = GrossUp(
            kind="volume", label="MODELED", lever=LEVER_VOLUME,
            title="Corrected delivered-volume estimate (lines)",
            basis="claim lines", method="n/a", assumption="n/a",
            computable=False, observed=float(observed),
            note="No dropped-leg signal fired — volume in this extract looks "
                 "complete for the legs testable here.",
            diligence="Confirm capitated, self-pay, pre-auth-denied and "
                      "ancillary volume against the target's systems before "
                      "treating the observed line count as complete.")
    return findings, gu, diligence


def _analyze_price(rows, cols, A: Assumptions
                   ) -> Tuple[List[Finding], GrossUp, List[str]]:
    findings: List[Finding] = []
    diligence: List[str] = []
    billed_i, allowed_i, paid_i = cols["billed_i"], cols["allowed_i"], cols["paid_i"]
    units_i = cols["units_i"]

    has = {"billed": billed_i is not None, "allowed": allowed_i is not None,
           "paid": paid_i is not None}

    # billed vs allowed vs paid presence
    present = [k for k, v in has.items() if v] or ["none"]
    findings.append(Finding(
        "billed_not_allowed_paid", LEVER_PRICE,
        TAXONOMY_BY_ID["billed_not_allowed_paid"].name,
        STATUS_CLEAN if has["paid"] else STATUS_DETECTED,
        "Amount columns present: " + ", ".join(present) + ". "
        + ("Realized rate is observable from paid." if has["paid"]
           else "No paid column — the realized rate is NOT observable; "
                "billed/allowed overstate reimbursement."),
        {"has_billed": has["billed"], "has_allowed": has["allowed"],
         "has_paid": has["paid"]}))
    if not has["paid"]:
        diligence.append(
            "Realized rate: no paid column — request the remittance (835) "
            "allowed & paid amounts; billed overstates and cannot show yield.")

    # contractual adjustment visibility
    findings.append(Finding(
        "contractual_adjustment_hidden", LEVER_PRICE,
        TAXONOMY_BY_ID["contractual_adjustment_hidden"].name,
        STATUS_CLEAN if (has["billed"] and has["allowed"]) else STATUS_DETECTED,
        ("billed and allowed both present — the contractual adjustment "
         "(billed - allowed) is derivable."
         if has["billed"] and has["allowed"] else
         "billed and allowed are not both present — the contractual "
         "adjustment (and thus the realized rate) is hidden."),
        {"has_billed": has["billed"], "has_allowed": has["allowed"]}))
    if not (has["billed"] and has["allowed"]):
        diligence.append(
            "Contractual adjustment: supply billed AND allowed so the "
            "write-down to the negotiated rate is visible.")

    # secondary / COB payments not summed → the realized-rate gross-up
    sec_n, sec_mode = _secondary_signal(rows, cols)
    _cob_ask = ("COB payments: confirm total paid sums primary + secondary + "
                "patient, or supply the secondary-payer paid column.")
    cob_finding_status = STATUS_DETECTED if sec_mode != "none" else STATUS_NOT_DETECTABLE
    findings.append(Finding(
        "cob_payment_not_summed", LEVER_PRICE,
        TAXONOMY_BY_ID["cob_payment_not_summed"].name, cob_finding_status,
        ("Secondary legs exist; if only primary paid is summed, the realized "
         "rate per encounter is understated." if sec_mode != "none" else
         "No payer-sequence column — cannot confirm whether secondary/patient "
         "payments are summed into total paid."),
        {"mode": sec_mode, "secondary_legs": sec_n},
        diligence=(_cob_ask if sec_mode == "none" else None)))
    if sec_mode == "none":
        diligence.append(_cob_ask)

    # the remaining PRICE causes are context/rate-table asks
    for cid, ask in (
        ("fee_schedule_lag",
         "Fee-schedule lag: supply the current fee schedule and its effective "
         "date to reprice recent volume to the go-forward rate."),
        ("site_of_service_differential",
         "Site of service: supply the site-specific rate table and facility-"
         "fee legs so per-service reimbursement isn't understated."),
        ("sequestration_takeback",
         "Sequestration/take-backs: confirm whether paid is net of the ~2% "
         "Medicare withhold and any recoupments before reading it as the "
         "contractual rate."),
    ):
        findings.append(Finding(
            cid, LEVER_PRICE, TAXONOMY_BY_ID[cid].name, STATUS_NOT_DETECTABLE,
            TAXONOMY_BY_ID[cid].why_it_understates, {}, ask))
        diligence.append(ask)

    # Realized-rate gross-up: computable only when paid exists.
    if has["paid"]:
        tot_paid = 0.0
        tot_units = 0.0
        lines = 0
        for row in rows:
            p = _num(row, paid_i)
            if p is None:
                continue
            tot_paid += p
            lines += 1
            u = _num(row, units_i) if units_i is not None else None
            tot_units += (u if (u is not None and u > 0) else 1.0)
        basis_unit = "unit" if units_i is not None else "line"
        denom = tot_units if units_i is not None else float(max(1, lines))
        observed_rate = tot_paid / denom if denom else 0.0
        band = A.band(A.cob_uplift)
        rr = grossup_realized_rate(observed_rate, A.cob_uplift, band)
        gu = GrossUp(
            kind="realized_rate", label="MODELED", lever=LEVER_PRICE,
            title=f"Corrected realized rate ($ paid per {basis_unit})",
            basis=f"$ paid per {basis_unit}",
            method="observed paid-per-{0} x (1 + cob_uplift)".format(basis_unit),
            assumption=f"cob_uplift={A.cob_uplift:.1%} for secondary + patient "
                       "payments not summed into observed paid",
            computable=True,
            observed=observed_rate,
            low=rr["low"], base=rr["base"], high=rr["high"],
            note="Observed rate is real; the uplift is MODELED. Band varies "
                 "cob_uplift by +/-{:.0%}. If paid already sums all payers, "
                 "the uplift is 0.".format(A.band_rel))
    else:
        gu = GrossUp(
            kind="realized_rate", label="MODELED", lever=LEVER_PRICE,
            title="Corrected realized rate", basis="$ paid per unit",
            method="n/a", assumption="n/a", computable=False,
            note="No paid column — the realized rate cannot be computed from "
                 "this extract.",
            diligence="Request remittance (835) allowed & paid amounts; the "
                      "realized rate is unobservable from billed alone.")
    return findings, gu, diligence


def _analyze_scale(rows, cols, A: Assumptions
                   ) -> Tuple[List[Finding], GrossUp, List[str]]:
    findings: List[Finding] = []
    diligence: List[str] = []
    billing_idx = cols["billing_idx"]
    tin_i, owner_i = cols["tin_i"], cols["owner_i"]
    rendering_idx = cols["rendering_idx"]
    billed_i, paid_i = cols["billed_i"], cols["paid_i"]

    # distinct NPI / TIN / owner counts
    npis: set = set()
    tins: set = set()
    owners: set = set()
    for row in rows:
        b = _cell(row, billing_idx)
        if b:
            npis.add(engine._digits(b) or b)
        t = _cell(row, tin_i)
        if t:
            tins.add(t)
        o = _cell(row, owner_i)
        if o:
            owners.add(o)
    n_npi, n_tin, n_owner = len(npis), len(tins), len(owners)

    if billing_idx is None:
        findings.append(Finding(
            "npi_tin_fragmentation", LEVER_SCALE,
            TAXONOMY_BY_ID["npi_tin_fragmentation"].name,
            STATUS_NOT_DETECTABLE,
            "No billing NPI column — cannot assess NPI/TIN fragmentation.",
            {},
            "Fragmentation: supply the billing NPI (and TIN) so distinct "
            "billers can be counted and rolled to an owner."))
        diligence.append(
            "Fragmentation: no billing NPI column — request billing NPI + TIN.")
    else:
        frag_bits = [f"{n_npi:,} distinct billing NPIs"]
        if tin_i is not None:
            frag_bits.append(f"{n_tin:,} distinct TINs")
        if owner_i is not None:
            frag_bits.append(f"{n_owner:,} distinct owners")
        npis_per_owner = (n_npi / n_owner) if n_owner else None
        has_grouping = owner_i is not None or tin_i is not None
        detected = (owner_i is not None and npis_per_owner is not None
                    and npis_per_owner > 1.5) or (
                    tin_i is not None and n_tin and n_npi / max(1, n_tin) > 1.5)
        _frag_dilig = None
        if detected:
            status = STATUS_DETECTED
            tail = (f" — ~{npis_per_owner:.1f} NPIs per owner; per-owner scale "
                    "is understated at the NPI grain." if npis_per_owner
                    else " — more NPIs than TINs; roll to the owner for scale.")
        elif has_grouping:
            status = STATUS_CLEAN
            tail = ". Roll to the owner/TIN to see true scale."
        elif n_npi > 1:
            # Multiple distinct billers but NO owner/TIN column — we cannot tell
            # whether they are one owner or many. Honest verdict: not detectable.
            status = STATUS_NOT_DETECTABLE
            tail = (". No owner/TIN column — cannot tell if these are one "
                    "owner or many; true per-owner scale needs a crosswalk.")
            _frag_dilig = ("Fragmentation: distinct NPIs present but no "
                           "owner/TIN column — supply an ownership crosswalk to "
                           "roll NPIs to their owner.")
            diligence.append(_frag_dilig)
        else:
            status = STATUS_CLEAN
            tail = ". Single billing NPI — no fragmentation in this extract."
        findings.append(Finding(
            "npi_tin_fragmentation", LEVER_SCALE,
            TAXONOMY_BY_ID["npi_tin_fragmentation"].name, status,
            ", ".join(frag_bits) + tail,
            {"distinct_npis": n_npi, "distinct_tins": n_tin,
             "distinct_owners": n_owner,
             "npis_per_owner": round(npis_per_owner, 2) if npis_per_owner else None},
            diligence=_frag_dilig))

    # billing vs rendering attribution
    if billing_idx is not None and rendering_idx is not None:
        findings.append(Finding(
            "billing_vs_rendering_attribution", LEVER_SCALE,
            TAXONOMY_BY_ID["billing_vs_rendering_attribution"].name,
            STATUS_DETECTED,
            "Both a billing and a rendering NPI column exist — attribute to "
            "the billing entity for scale, to the rendering NPI for "
            "productivity; mixing the two mis-states scale.",
            {"billing_column": cols_headername(cols, "billing_idx"),
             "rendering_column": cols_headername(cols, "rendering_idx")}))
    else:
        findings.append(Finding(
            "billing_vs_rendering_attribution", LEVER_SCALE,
            TAXONOMY_BY_ID["billing_vs_rendering_attribution"].name,
            STATUS_NOT_DETECTABLE,
            "Only one provider-NPI grain present — cannot compare "
            "billing-entity vs rendering-individual attribution.",
            {},
            "Attribution: supply both billing and rendering NPI to separate "
            "entity scale from individual productivity."))

    # org vs individual double-map — needs NPPES type (not in the number)
    findings.append(Finding(
        "org_vs_individual_npi_doublemap", LEVER_SCALE,
        TAXONOMY_BY_ID["org_vs_individual_npi_doublemap"].name,
        STATUS_NOT_DETECTABLE,
        "NPI type-1 vs type-2 cannot be read from the claim number; an NPPES "
        "type lookup is required to avoid double-mapping org and individual "
        "volume.",
        {"distinct_npis": n_npi},
        "Org/individual: run the distinct NPIs through NPPES to tag type-1 vs "
        "type-2 and roll to the organization."))
    diligence.append(
        "Org/individual NPI: cross-map distinct NPIs to NPPES entity type to "
        "avoid double-mapping type-1 and type-2 volume.")

    # acquired-practice old TIN + chain/parent attribution → context asks
    for cid, ask in (
        ("acquired_practice_old_tin",
         "Acquired TINs: supply acquisition dates and the acquirer's TIN "
         "roster to re-map legacy TINs to the acquirer."),
        ("chain_parent_attribution_absent",
         "Ownership crosswalk: supply a parent/chain crosswalk (PECOS "
         "ownership, HCRIS, or the target roster) to roll locations to the "
         "platform — claims carry no parent field."),
    ):
        st = STATUS_NOT_DETECTABLE
        # If an owner column IS present, chain attribution is at least partly
        # available; note that.
        extra = {}
        if cid == "chain_parent_attribution_absent" and owner_i is not None:
            st = STATUS_CLEAN
            findings.append(Finding(
                cid, LEVER_SCALE, TAXONOMY_BY_ID[cid].name, st,
                "An owner/parent column IS present — chain roll-up is possible "
                "from this extract (still validate crosswalk completeness).",
                {"owner_column": cols_headername(cols, "owner_i")}))
            continue
        findings.append(Finding(
            cid, LEVER_SCALE, TAXONOMY_BY_ID[cid].name, st,
            TAXONOMY_BY_ID[cid].why_it_understates, extra, ask))
        diligence.append(ask)

    # De-fragmented SCALE view.
    if owner_i is not None and billing_idx is not None:
        # OBSERVED roll-up: group real volume/charges to the owner. This is
        # arithmetic on real rows, so it is labeled OBSERVED, not MODELED.
        per_owner_lines: Dict[str, int] = {}
        per_owner_charge: Dict[str, float] = {}
        amt_i = billed_i if billed_i is not None else paid_i
        for row in rows:
            o = _cell(row, owner_i) or "(blank owner)"
            per_owner_lines[o] = per_owner_lines.get(o, 0) + 1
            a = _num(row, amt_i) if amt_i is not None else None
            if a is not None:
                per_owner_charge[o] = per_owner_charge.get(o, 0.0) + a
        top = sorted(per_owner_lines.items(), key=lambda kv: -kv[1])[:10]
        comps = [{"owner": o, "lines": c,
                  "charges": round(per_owner_charge.get(o, 0.0), 2)}
                 for o, c in top]
        roll = (n_npi / n_owner) if n_owner else 1.0
        gu = GrossUp(
            kind="scale", label="OBSERVED", lever=LEVER_SCALE,
            title="De-fragmented scale — distinct billing NPIs rolled to owners",
            basis="distinct billing NPIs rolled to owners (per-owner lines and "
                  "dollars in the breakdown below)",
            method="group observed rows by the owner column (exact dedup of "
                   "NPIs/TINs to their owner)",
            assumption="the ownership crosswalk in the owner column is complete "
                       "and correct",
            computable=True,
            observed=float(n_npi),
            base=float(n_owner),
            note="OBSERVED roll-up: {0} distinct billing NPIs collapse to {1} "
                 "owner(s) (~{2:.1f}x). Figures are real sums, not modeled — "
                 "only the crosswalk completeness is an assumption.".format(
                     n_npi, n_owner, roll),
            components=comps)
    else:
        gu = GrossUp(
            kind="scale", label="MODELED", lever=LEVER_SCALE,
            title="De-fragmented scale", basis="distinct billers",
            method="n/a", assumption="n/a", computable=False,
            observed=float(n_npi),
            note="{0} distinct billing NPIs".format(n_npi)
                 + (f" across {n_tin} TINs" if tin_i is not None else "")
                 + " — but NO owner/parent column, so the true per-owner scale "
                   "cannot be computed without an external ownership crosswalk.",
            diligence="Supply an ownership crosswalk (PECOS ownership, HCRIS, "
                      "or the target roster) mapping every NPI/TIN to its "
                      "owner; do NOT infer an owner count from claims alone.")
    return findings, gu, diligence


def cols_headername(cols: Dict[str, object], key: str) -> Optional[str]:
    """Header name behind a detected index, for evidence dicts. Needs the
    headers stashed on ``cols`` under ``_headers``."""
    headers = cols.get("_headers") or []
    i = cols.get(key)
    if isinstance(i, int) and 0 <= i < len(headers):
        return headers[i]
    return None


# --------------------------------------------------------------------------- #
# formatting helpers (dollars 2dp / pct 1dp / counts no decimals)             #
# --------------------------------------------------------------------------- #
def _pctf(n: float, d: float) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _pct(n: float, d: float) -> str:
    return f"{_pctf(n, d):.1f}%"


# --------------------------------------------------------------------------- #
# 5. PUBLIC ENTRY POINTS                                                       #
# --------------------------------------------------------------------------- #
def analyze(headers: List[str], rows: List[List[str]], *,
            assumptions: Optional[Assumptions] = None) -> Result:
    """Detect understatement + build the three gross-ups over a cleaned claims
    table (``headers`` + list-of-lists ``rows``). Deterministic and offline.

    Degrades gracefully: a missing column yields a ``not_detectable`` finding
    and a diligence request, never an exception."""
    A = assumptions or default_assumptions()
    headers = [str(h) for h in (headers or [])]
    rows = rows or []
    warnings: List[str] = []
    if not headers:
        warnings.append("No header row — nothing to analyze.")
        return Result(0, {}, [], {}, [], A, warnings)

    cols = _detect_columns(headers, rows)
    cols["_headers"] = headers

    v_find, v_gu, v_dil = _analyze_volume(rows, cols, A)
    p_find, p_gu, p_dil = _analyze_price(rows, cols, A)
    s_find, s_gu, s_dil = _analyze_scale(rows, cols, A)

    findings = v_find + p_find + s_find
    grossups = {"volume": v_gu, "realized_rate": p_gu, "scale": s_gu}
    diligence = v_dil + p_dil + s_dil

    # A readable column map for the scorecard (header names, not indices).
    col_map = {
        "billing_npi": cols_headername(cols, "billing_idx"),
        "rendering_npi": cols_headername(cols, "rendering_idx"),
        "billed": cols_headername(cols, "billed_i"),
        "allowed": cols_headername(cols, "allowed_i"),
        "paid": cols_headername(cols, "paid_i"),
        "units": cols_headername(cols, "units_i"),
        "denial_carc": cols_headername(cols, "carc_i"),
        "payer": cols_headername(cols, "payer_i"),
        "payer_sequence": cols_headername(cols, "payerseq_i"),
        "financial_class": cols_headername(cols, "finclass_i"),
        "tin": cols_headername(cols, "tin_i"),
        "owner": cols_headername(cols, "owner_i"),
        "claim_id": cols_headername(cols, "claim_i"),
        "service_date": cols_headername(cols, "dos_i"),
        "revenue_code": (headers[cols["rev_set"][0]]
                         if cols["rev_set"] else None),
    }
    return Result(len(rows), col_map, findings, grossups, diligence, A,
                  warnings)


def analyze_bytes(data: bytes, src_name: str = "claims.csv", *,
                  assumptions: Optional[Assumptions] = None) -> Result:
    """Read a delimited/xlsx/x12 claims file (via the engine's reader) and
    analyze it end-to-end. This is the file-in front door."""
    headers, rows, _fmt, _note = engine._read_table(data)
    return analyze(headers, rows, assumptions=assumptions)


def analyze_frame(df, *, assumptions: Optional[Assumptions] = None) -> Result:
    """Analyze a pandas DataFrame of already-cleaned claims. Columns become
    headers; every cell is stringified (the detectors and parsers are
    string-based, matching how a CSV extract arrives)."""
    headers = [str(c) for c in df.columns]
    rows = [["" if v is None else str(v) for v in rec]
            for rec in df.itertuples(index=False, name=None)]
    return analyze(headers, rows, assumptions=assumptions)


def sample_claims_csv() -> str:
    """A small synthetic claims file that exhibits several understatement
    causes at once: denied lines, a self-pay leg, a secondary-payer leg,
    NPI/TIN fragmentation under one owner, a facility (revenue-code) leg
    alongside professional lines, and a billed-only row. NPIs are Luhn-valid
    synthetic examples — not real providers.
    """
    return (
        "ClaimID,PayerSequence,PayerName,FinancialClass,BillingNPI,"
        "RenderingNPI,BillingTIN,OwnerName,RevenueCode,HCPCS,PlaceOfService,"
        "Units,BilledAmt,AllowedAmt,PaidAmt,DenialCode,DateOfService\n"
        # professional lines under owner "Summit Health Partners", 3 NPIs/TINs
        "2001,Primary,Aetna,COMMERCIAL,1679576722,1234567893,88-1110001,"
        "Summit Health Partners,,99213,11,1,420,300,240,,2024-01-11\n"
        "2002,Primary,Aetna,COMMERCIAL,1245319599,1234567893,88-1110002,"
        "Summit Health Partners,,99214,11,1,600,420,336,,2024-01-19\n"
        "2003,Primary,UnitedHealthcare,COMMERCIAL,1699999984,1234567893,"
        "88-1110003,Summit Health Partners,,99215,11,1,850,600,480,,2024-02-03\n"
        # a denied line (CARC present, zero paid)
        "2004,Primary,Aetna,COMMERCIAL,1679576722,1234567893,88-1110001,"
        "Summit Health Partners,,99213,11,1,420,0,0,CO-197,2024-02-14\n"
        # self-pay encounter, never billed to a payer
        "2005,Primary,Self Pay,SELFPAY,1245319599,1234567893,88-1110002,"
        "Summit Health Partners,,99213,11,1,180,0,0,,2024-02-20\n"
        # a secondary (COB) leg on an earlier encounter
        "2002,Secondary,Medicare,COMMERCIAL,1245319599,1234567893,88-1110002,"
        "Summit Health Partners,,99214,11,1,600,84,60,,2024-01-27\n"
        # a facility (revenue-code) leg — the professional side is billed above
        "2006,Primary,Aetna,COMMERCIAL,1699999984,1234567893,88-1110003,"
        "Summit Health Partners,0450,,22,1,1200,900,720,,2024-02-08\n"
        # billed-only row (allowed/paid blank) — realized rate hidden
        "2007,Primary,Cigna,COMMERCIAL,1679576722,1234567893,88-1110001,"
        "Summit Health Partners,,99214,11,1,600,,,,2024-03-01\n"
        # a fresh, run-out-thin final month
        "2008,Primary,Aetna,COMMERCIAL,1679576722,1234567893,88-1110001,"
        "Summit Health Partners,,99213,11,1,420,300,240,,2024-04-02\n"
    )
