"""Curated catalog of healthcare policy shocks worth evaluating.

The same pattern as ``payer_stress/payer_library.py``: a hand-curated,
documented set of records the analyst can read and edit in one place.
Each :class:`PolicyShock` names a real, dated regulatory change, the
diligence question it raises, who is exposed (the treatment-group
definition), the expected sign of the effect, and the revenue base the
ATT should be applied to in :func:`policy_ebitda_overlay`.

These are the "policy shocks" the brief flags as IC-grade questions:
the OBBBA Medicaid changes, the CY2027 MA rate path, and the PFS
conversion-factor move. The records do NOT bake in an effect size —
the whole point is to estimate it from a panel via
:func:`estimate_did`. They scope the natural experiment and document
the source, calibration, and refresh cadence.

SCOPE: dates and provisions reflect public rulemaking/law as of the
2026 diligence cycle; refresh when CMS publishes a final rule or the
statute is amended. Always confirm the effective date against the
Federal Register / statute before relying on a record.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

CITATION_KEY = "PS2"
SOURCE_MODULE = "diligence.policy_shock"


class ExpectedSign(str, Enum):
    NEGATIVE = "NEGATIVE"     # policy expected to reduce the outcome
    POSITIVE = "POSITIVE"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class PolicyShock:
    """One dated policy change set up as a natural experiment."""
    shock_id: str
    name: str
    effective_date: str               # ISO; the treatment date
    agency: str
    diligence_question: str
    treatment_definition: str         # who is in the treatment group
    exposed_revenue_basis: str        # what revenue the ATT applies to
    expected_sign: ExpectedSign
    source: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shock_id": self.shock_id,
            "name": self.name,
            "effective_date": self.effective_date,
            "agency": self.agency,
            "diligence_question": self.diligence_question,
            "treatment_definition": self.treatment_definition,
            "exposed_revenue_basis": self.exposed_revenue_basis,
            "expected_sign": self.expected_sign.value,
            "source": self.source,
            "notes": self.notes,
            "source_module": SOURCE_MODULE,
            "citation_key": CITATION_KEY,
        }


POLICY_SHOCKS: Tuple[PolicyShock, ...] = (
    PolicyShock(
        shock_id="OBBBA_MEDICAID",
        name="OBBBA Medicaid eligibility / work-requirement changes",
        effective_date="2027-01-01",
        agency="Congress / CMS",
        diligence_question=(
            "How much Medicaid volume and revenue does the asset lose as "
            "redeterminations and work requirements compress enrollment in "
            "expansion states?"
        ),
        treatment_definition=(
            "Facilities/markets in Medicaid-expansion states with high "
            "expansion-population mix; controls are otherwise-similar "
            "markets in non-expansion or low-exposure states."
        ),
        exposed_revenue_basis="Medicaid net patient revenue",
        expected_sign=ExpectedSign.NEGATIVE,
        source=(
            "One Big Beautiful Bill Act Medicaid provisions; CMS "
            "redetermination guidance. Confirm effective dates per state."
        ),
        notes=(
            "Phased by state; treat the dominant effective date for the "
            "target's footprint as the treatment period and segment by "
            "state if timing is staggered."
        ),
    ),
    PolicyShock(
        shock_id="MA_RATE_CY2027",
        name="CY2027 Medicare Advantage rate / V28 phase-in",
        effective_date="2027-01-01",
        agency="CMS",
        diligence_question=(
            "What does the next MA rate notice plus the final year of the "
            "V28 risk-model phase-in do to per-member revenue for "
            "MA-exposed providers and risk-bearing entities?"
        ),
        treatment_definition=(
            "Providers/MSOs with high MA or MA-risk revenue share; controls "
            "are FFS-dominant peers with minimal MA exposure."
        ),
        exposed_revenue_basis="Medicare Advantage premium / capitation revenue",
        expected_sign=ExpectedSign.NEGATIVE,
        source=(
            "CMS CY Rate Announcement; CMS-HCC V28 three-year phase-in "
            "(see diligence.risk_adjustment for the risk model)."
        ),
        notes=(
            "Pairs with the risk_adjustment module: V28 compression lowers "
            "coded RAF, which the rate notice then prices."
        ),
    ),
    PolicyShock(
        shock_id="PFS_CY2027",
        name="CY2027 Physician Fee Schedule conversion-factor change",
        effective_date="2027-01-01",
        agency="CMS",
        diligence_question=(
            "How does the PFS conversion-factor move (and any specialty "
            "RVU reweighting) hit physician-practice and MSO professional "
            "revenue?"
        ),
        treatment_definition=(
            "Practices/specialties with high Part B professional revenue "
            "exposed to the conversion-factor change; controls are "
            "facility-fee- or specialty-protected peers."
        ),
        exposed_revenue_basis="Medicare Part B professional (PFS) revenue",
        expected_sign=ExpectedSign.AMBIGUOUS,
        source=(
            "CMS PFS Final Rule conversion factor; specialty RVU impact "
            "tables in the rule."
        ),
        notes=(
            "Sign is ambiguous: the conversion-factor cut is negative, but "
            "specialty reweighting and any statutory update can offset by "
            "specialty — estimate, don't assume."
        ),
    ),
    PolicyShock(
        shock_id="SITE_NEUTRAL",
        name="Site-neutral payment expansion (HOPD → physician-office rate)",
        effective_date="2027-01-01",
        agency="CMS / Congress",
        diligence_question=(
            "How much outpatient facility revenue is at risk if more HOPD "
            "services are repriced to the lower physician-office rate?"
        ),
        treatment_definition=(
            "Hospital outpatient departments / off-campus PBDs billing the "
            "affected codes; controls are ASCs or sites already at the "
            "site-neutral rate."
        ),
        exposed_revenue_basis="Hospital outpatient (OPPS) facility revenue",
        expected_sign=ExpectedSign.NEGATIVE,
        source="CMS OPPS rulemaking; site-neutral legislative proposals.",
        notes="Confirm which code families are in scope for the final rule.",
    ),
)

_BY_ID: Dict[str, PolicyShock] = {s.shock_id: s for s in POLICY_SHOCKS}


def get_policy(shock_id: str) -> Optional[PolicyShock]:
    return _BY_ID.get(shock_id)


def list_policies() -> List[PolicyShock]:
    return list(POLICY_SHOCKS)
