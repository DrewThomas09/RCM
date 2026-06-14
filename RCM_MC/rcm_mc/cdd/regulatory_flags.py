"""NEW-17 Regulatory-flag module.

A deterministic rules engine that raises diligence flags for current healthcare
PE themes from a target's attributes. No LLM scoring; every flag is a rule with
a one-line rationale and a source plus vintage. Themes:

- OBBBA Medicaid exposure: heavy-Medicaid models face Medicaid funding risk.
- MA RAF compression: Medicare Advantage exposure under V28 and CY2027.
- Site-of-care shift exposure: facility subsectors losing volume to ASC and home.
- 340B conversion-factor drag: 340B covered entities face margin compression.
- State PE oversight: mini-HSR, material-change-notification, or CPOM-MSO states.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-17"

MEDICAID_HEAVY_THRESHOLD = 0.40
MA_EXPOSURE_THRESHOLD = 0.30

# Subsectors materially exposed to the site-of-care shift.
SITE_OF_CARE_SUBSECTORS = {
    "hospital", "hopd", "inpatient", "acute", "surgery", "asc-host", "imaging",
}

# States with PE oversight: mini-HSR / material-change-notification / CPOM-MSO.
STATE_OVERSIGHT: Dict[str, str] = {
    "CA": "CPOM enforcement and material-change review",
    "MA": "material-change notification (HPC)",
    "NY": "material-transaction notification",
    "IL": "health-care transaction notice",
    "OR": "material-change-transaction review",
    "WA": "material-change notification",
    "CT": "transaction notice and AG review",
    "NV": "material-change notice",
    "MN": "AG transaction review",
    "RI": "Hospital Conversions Act review",
    "NM": "transaction review",
    "CO": "material-change notice",
    "IN": "health-care entity notice",
}


def regulatory_flags(
    target: Mapping[str, Any],
    *,
    source: str = "Diligence rules engine",
    vintage: str = "2026",
    audience: str = "both",
) -> Exhibit:
    """Apply the deterministic rules engine to a target's attributes.

    ``target``: {payer_mix: {payer: share}, state, subsector, ma_exposure,
    is_340b}.
    """
    payer_mix = target.get("payer_mix", {}) or {}
    state = str(target.get("state", "")).upper()
    subsector = str(target.get("subsector", "")).lower()
    ma_exposure = float(target.get("ma_exposure", 0.0))
    is_340b = bool(target.get("is_340b", False))
    medicaid_share = float(payer_mix.get("Medicaid", 0.0))

    flags: List[Flag] = []
    rule_trace: List[Dict[str, Any]] = []

    def _trace(code, fired, detail):
        rule_trace.append({"rule": code, "fired": fired, "detail": detail})

    # Rule 1: OBBBA Medicaid exposure.
    fired = medicaid_share >= MEDICAID_HEAVY_THRESHOLD
    if fired:
        flags.append(Flag(
            code="obbba_medicaid_exposure",
            severity="risk",
            message=(
                f"Medicaid is {medicaid_share*100:.0f} percent of payer mix. OBBBA "
                "Medicaid funding changes put heavy-Medicaid models at risk."
            ),
            source="OBBBA 2025",
        ))
    _trace("obbba_medicaid_exposure", fired, f"medicaid_share={medicaid_share}")

    # Rule 2: MA RAF compression.
    fired = ma_exposure >= MA_EXPOSURE_THRESHOLD
    if fired:
        flags.append(Flag(
            code="ma_raf_compression",
            severity="warn",
            message=(
                f"Medicare Advantage exposure is {ma_exposure*100:.0f} percent. V28 "
                "and the CY2027 phase-in compress RAF scores and revenue."
            ),
            source="CMS-HCC V28, CY2027",
        ))
    _trace("ma_raf_compression", fired, f"ma_exposure={ma_exposure}")

    # Rule 3: Site-of-care shift exposure.
    fired = subsector in SITE_OF_CARE_SUBSECTORS
    if fired:
        flags.append(Flag(
            code="site_of_care_shift_exposure",
            severity="warn",
            message=(
                f"Subsector {subsector} is exposed to volume migration toward ASC and the home."
            ),
            source="CY2026 OPPS/ASC final rule",
        ))
    _trace("site_of_care_shift_exposure", fired, f"subsector={subsector}")

    # Rule 4: 340B conversion-factor drag.
    if is_340b:
        flags.append(Flag(
            code="drug_340b_drag",
            severity="warn",
            message="340B covered entity: conversion-factor and remedy changes drag drug margin.",
            source="HRSA 340B, CMS remedy rule",
        ))
    _trace("drug_340b_drag", is_340b, f"is_340b={is_340b}")

    # Rule 5: State PE oversight.
    fired = state in STATE_OVERSIGHT
    if fired:
        flags.append(Flag(
            code="state_pe_oversight",
            severity="risk",
            message=(
                f"State {state} has PE oversight: {STATE_OVERSIGHT[state]}. Deal may "
                "require notice or review."
            ),
            source="State transaction-oversight statutes",
        ))
    _trace("state_pe_oversight", fired, f"state={state}")

    reconciliations = [
        Reconciliation(
            identity="flag count equals number of fired rules",
            lhs=len(flags),
            rhs=sum(1 for t in rule_trace if t["fired"]),
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="Regulatory flags", kind="bar", points=[
            {"label": f.code, "severity": f.severity, "rationale": f.message} for f in flags
        ]),
        Series(name="Rule trace", kind="bar", internal_only=True, points=rule_trace),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Each flag is a deterministic rule, not a model score.",
            "Thresholds: Medicaid at or above 40 percent, MA exposure at or above 30 percent.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Regulatory diligence flags",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{len(flags)} regulatory flag(s) raised.",
        meta={
            "flags": [f.to_dict() for f in flags],
            "rule_trace": rule_trace,
            "fired_codes": [f.code for f in flags],
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    target = {
        "payer_mix": {"Medicaid": 0.60, "Medicare": 0.20, "Commercial": 0.20},
        "state": "CA",
        "subsector": "home-health",
        "ma_exposure": 0.05,
        "is_340b": False,
    }
    return regulatory_flags(target, source="Demo rules engine", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Regulatory-flag module",
        audience="both",
        demo=_demo,
    )
)
