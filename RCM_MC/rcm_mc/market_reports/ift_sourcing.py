"""IFT sourcing prompts — Part 1 (the evidence-acquisition layer of the study).

Where :mod:`ift_diligence` carries the question tree and :mod:`ift_analytics` /
:mod:`ift_clinical_demand` size the market, THIS module carries the *sourcing
prompts*: the exact, scope-bounded research questions that go out to gather the
evidence — each one paired with the boundary line that keeps NEMT and 911 out,
its prioritized public sources, the real connector datasets on this platform
that feed it, and a live link to where the answer already lives (a sized page and
the matching diligence slide).

It is deliberately not a sizing module: it holds no dollar figures. The prompt
text is authored diligence knowledge (FRAMEWORK); the source citations are GOV /
ACADEMIC / INDUSTRY; the connector references resolve at read time against the
real :mod:`ift_connectors` estate so a renamed dataset degrades to nothing.

Design contract mirrors the rest of the IFT modules: frozen dataclasses, pure
functions that DEGRADE and never raise, and an honesty ``source_label`` on every
result.

Public API:
    scope_boundary() -> str
    sourcing_prompts() -> Tuple[SourcingPrompt, ...]
    priority_prompts() -> Tuple[int, ...]
    connector_evidence() -> Any            (re-exported from ift_diligence)
    sourcing_summary() -> Dict[str, Any]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Reuse the same live-surface link table + connector resolver the question
# architecture uses, so the two pages agree on where every answer lives.
from .ift_diligence import LINK, connector_evidence  # noqa: F401  (re-exported)


# The boundary line pasted into EVERY prompt — the single most important control,
# because without it the research drags NEMT and 911 back into the denominator.
SCOPE_BOUNDARY = (
    "Scope: US ground interfacility transport only — both endpoints are "
    "facilities. Exclude 911/scene response (origin modifier S or R), air "
    "ambulance, and Medicaid NEMT (wheelchair van, livery, rideshare). Where a "
    "source does not permit that cut, say so explicitly rather than substituting "
    "a broader figure. Label every figure with its year and whether it counts "
    "transports, claims, or dollars."
)


def scope_boundary() -> str:
    """The copy-paste boundary prefix for every sourcing prompt."""
    return SCOPE_BOUNDARY


def _links(*keys: str) -> Tuple[Tuple[str, str], ...]:
    """Resolve LINK keys to (label, href), dropping unknowns. A bare slide slug
    (``slide:<slug>``) resolves to the matching /ift-diligence anchor."""
    out: List[Tuple[str, str]] = []
    for k in keys:
        if k.startswith("slide:"):
            slug = k.split(":", 1)[1]
            out.append((f"Diligence slide — {slug}",
                        f"/ift-diligence#ifq-slide-{slug}"))
            continue
        hl = LINK.get(k)
        if hl:
            out.append((hl[1], hl[0]))
    return tuple(out)


@dataclass(frozen=True)
class SourcingPrompt:
    num: int
    slug: str
    title: str
    priority: bool                          # True for the "run these three" set
    why: str                                # one-line purpose
    prompt: str                             # the verbatim research prompt
    sources: Tuple[Tuple[str, str], ...]    # (citation, basis)
    connector_keys: Tuple[str, ...]         # ift_connectors keys feeding it
    answered_by: Tuple[Tuple[str, str], ...]  # (label, href) live surfaces

    @property
    def full_prompt(self) -> str:
        """Boundary line + prompt — the copy-paste unit."""
        return f"{SCOPE_BOUNDARY}\n\n{self.prompt}"


_PROMPTS: Tuple[SourcingPrompt, ...] = (
    SourcingPrompt(
        num=1, slug="denominator", title="The denominator and the IFT share",
        priority=False,
        why="Fix the total ground-ambulance count and carve out the interfacility "
            "share before anything else can be sized.",
        prompt=(
            "How many ground ambulance transports occur in the US annually, and "
            "what share are interfacility rather than 911/scene? Separate emergency "
            "from non-emergency interfacility. Prioritize CMS Ambulance Fee "
            "Schedule public use files, MedPAC Payment Basics (Ambulance), CMS "
            "Ground Ambulance Data Collection System reports, and AAA/AIMHI trend "
            "reports."),
        sources=(
            ("CMS Ambulance Fee Schedule public use files", "GOV"),
            ("MedPAC Payment Basics — Ambulance", "GOV"),
            ("CMS Ground Ambulance Data Collection System (GADCS) reports", "GOV"),
            ("AAA / AIMHI trend reports", "INDUSTRY"),
        ),
        connector_keys=("part_b_ambulance", "ambulance_market_saturation",
                        "ambulance_enrollment"),
        answered_by=_links("markets", "slide:taxonomy", "estate"),
    ),
    SourcingPrompt(
        num=2, slug="claims-method", title="The definitive claims method",
        priority=True,
        why="The method that survives the toughest diligence objection — proves "
            "the interfacility cut from claims, by origin/destination modifier.",
        prompt=(
            "Using CMS Medicare Part B carrier/supplier data, quantify annual "
            "volume and spend for A0426, A0428, A0427, A0429, A0433, A0434, and "
            "A0425 mileage. Then specify exactly what data is required to split "
            "those by origin/destination modifier so only claims with both "
            "endpoints in {H, N, E, G, J, D, I} count as interfacility. State which "
            "fields exist in the public use file versus the Limited Data Set or "
            "carrier claims."),
        sources=(
            ("CMS Medicare Part B carrier / supplier data (A0426-A0434, A0425)",
             "GOV"),
            ("CMS AFS public use file vs Limited Data Set vs carrier claims (origin/"
             "destination modifier fields)", "GOV"),
        ),
        connector_keys=("part_b_ambulance",),
        answered_by=_links("markets", "slide:definition", "estate"),
    ),
    SourcingPrompt(
        num=3, slug="growth", title="Growth rate — volume separated from price",
        priority=False,
        why="Isolate real volume growth from reimbursement inflation, and flag the "
            "policy breaks in the series.",
        prompt=(
            "What is the historical and projected growth rate of non-emergency "
            "interfacility ground transport volume? Isolate volume growth from "
            "price growth. Cite HHS-OIG OEI-09-12-00350 for the 2002-2011 "
            "utilization trend and MedPAC's mandated ground ambulance report. Flag "
            "where a series is discontinued or where RSNAT prior authorization "
            "broke the trend line."),
        sources=(
            ("HHS-OIG OEI-09-12-00350 (2002-2011 utilization trend)", "GOV"),
            ("MedPAC mandated ground ambulance report", "GOV"),
            ("RSNAT prior-authorization program (series break)", "GOV"),
        ),
        connector_keys=("part_b_ambulance", "ambulance_market_saturation"),
        answered_by=_links("markets", "research", "slide:strategic-capability"),
    ),
    SourcingPrompt(
        num=4, slug="prevalence", title="Prevalence per admission",
        priority=True,
        why="The core prevalence proof — what share of admissions transfer or "
            "discharge to a setting that needs an ambulance.",
        prompt=(
            "What percentage of US inpatient admissions result in transfer to "
            "another acute hospital, and what percentage are discharged to a "
            "post-acute facility requiring ambulance transport? Use AHRQ HCUP NIS "
            "discharge disposition codes. Break out the conditions with the highest "
            "transfer rates — acute MI, stroke, trauma, sepsis."),
        sources=(
            ("AHRQ HCUP NIS — discharge disposition codes", "GOV"),
            ("Condition-level transfer rates (acute MI, stroke, trauma, sepsis)",
             "ACADEMIC"),
        ),
        connector_keys=("chronic_disease", "hospital_service_area",
                        "icd10_validation"),
        answered_by=_links("clinical", "slide:patient-journey"),
    ),
    SourcingPrompt(
        num=5, slug="ed-transfers", title="ED-origin transfers",
        priority=False,
        why="Count the ED-to-acute transfer stream and refresh the stale 1.9M "
            "figure with a dated, current-vintage number.",
        prompt=(
            "How many ED encounters per year are transferred to another acute care "
            "hospital? Use CDC NHAMCS and AHRQ HCUP NEDS. The commonly cited 1.9M "
            "figure traces to 2009 data — find the most recent year available and "
            "state the vintage."),
        sources=(
            ("CDC NHAMCS", "GOV"),
            ("AHRQ HCUP NEDS", "GOV"),
        ),
        connector_keys=("hospital_service_area", "hospital_universe"),
        answered_by=_links("clinical", "slide:patient-journey"),
    ),
    SourcingPrompt(
        num=6, slug="post-acute", title="The post-acute backbone",
        priority=True,
        why="The actual non-emergency volume engine — hospital-to-post-acute "
            "discharge legs and the stretcher-eligible share.",
        prompt=(
            "Quantify annual US discharges from acute hospitals to SNF, IRF, LTCH, "
            "and hospice. Estimate what share require stretcher-based ambulance "
            "transport versus wheelchair van or private vehicle. Sources: MedPAC "
            "March report post-acute chapters, CMS Care Compare provider files, AHA "
            "Annual Survey."),
        sources=(
            ("MedPAC March report — post-acute chapters (SNF/IRF/LTCH/hospice)",
             "GOV"),
            ("CMS Care Compare provider files", "GOV"),
            ("AHA Annual Survey", "INDUSTRY"),
        ),
        connector_keys=("postacute_universe", "hospital_universe",
                        "dialysis_facilities"),
        answered_by=_links("clinical", "markets", "slide:patient-journey"),
    ),
    SourcingPrompt(
        num=7, slug="demographics", title="The demographic engine",
        priority=False,
        why="Turn the aging curve into a volume-weighted blended CAGR on the "
            "conditions that actually generate transfers.",
        prompt=(
            "Project US population by age band (65-74, 75-84, 85+) through 2035 "
            "from Census projections. Apply those CAGRs to the condition-level "
            "hospitalization volumes that generate interfacility transfers — hip "
            "fracture, stroke, heart failure, sepsis, hospice enrollment — holding "
            "incidence constant. Output a volume-weighted blended CAGR and show the "
            "arithmetic."),
        sources=(
            ("US Census population projections (age bands to 2035)", "GOV"),
            ("Condition-level hospitalization volumes (hip fx, stroke, HF, sepsis)",
             "ACADEMIC"),
        ),
        connector_keys=("aging_demand", "chronic_disease", "dialysis_demand"),
        answered_by=_links("clinical", "slide:patient-journey"),
    ),
    SourcingPrompt(
        num=8, slug="throughput", title="The throughput driver",
        priority=False,
        why="Show that hospital throughput pressure is pushing transport demand — "
            "with direction, magnitude, and reporting lag for each series.",
        prompt=(
            "Compile evidence that hospital throughput pressure is increasing "
            "transport demand: national inpatient occupancy trend (CMS HCRIS), ED "
            "boarding prevalence and duration, and change in LOS for post-acute "
            "discharges. Include the AHA discharge delay report and Canellas et "
            "al., Annals of Emergency Medicine, 2024. Give direction, magnitude, "
            "and reporting lag for each."),
        sources=(
            ("CMS HCRIS — national inpatient occupancy trend", "GOV"),
            ("AHA discharge delay report", "INDUSTRY"),
            ("Canellas et al., Annals of Emergency Medicine, 2024 (ED boarding)",
             "ACADEMIC"),
        ),
        connector_keys=("hospital_capacity", "hospital_service_area"),
        answered_by=_links("markets", "slide:challenges"),
    ),
    SourcingPrompt(
        num=9, slug="spend-index", title="Why IFT over-indexes on spend",
        priority=False,
        why="Prove the interfacility book earns more per transport than a 911/scene "
            "book, from the RVU ladder and the SCT definition.",
        prompt=(
            "Demonstrate that interfacility transport over-indexes on Medicare "
            "spend relative to volume. Use the 42 CFR 414.610 RVU table (BLS "
            "non-emergency 1.00 through SCT 3.25), confirm SCT (A0434) is "
            "definitionally interfacility under 42 CFR 414.605, and quantify the "
            "spend-per-transport gap between an interfacility book and a 911/scene "
            "book."),
        sources=(
            ("42 CFR 414.610 — ambulance RVU table (BLS 1.00 - SCT 3.25)", "GOV"),
            ("42 CFR 414.605 — SCT (A0434) definitionally interfacility", "GOV"),
        ),
        connector_keys=("part_b_ambulance", "ambulance_coverage"),
        answered_by=_links("markets", "slide:taxonomy"),
    ),
    SourcingPrompt(
        num=10, slug="rsnat", title="The policy discontinuity (RSNAT)",
        priority=False,
        why="Establish that today's non-emergency book is discharge / up-transfer "
            "work — not the scheduled-dialysis market regulators dismantled.",
        prompt=(
            "Explain how RSNAT prior authorization (nationwide since 2021) changed "
            "the composition of non-emergency ambulance transport. Quantify the "
            "reduction in repetitive scheduled dialysis volume and spend. The "
            "purpose is to establish that today's 'non-emergency' ambulance market "
            "is interfacility discharge and up-transfer work, not the scheduled "
            "dialysis book regulators dismantled."),
        sources=(
            ("RSNAT prior authorization (nationwide since 2021)", "GOV"),
            ("MedPAC / OIG repetitive scheduled non-emergency ambulance findings",
             "GOV"),
        ),
        connector_keys=("part_b_ambulance", "nemt_managed_care", "dialysis_demand"),
        answered_by=_links("research", "markets", "slide:definition"),
    ),
)


def sourcing_prompts() -> Tuple[SourcingPrompt, ...]:
    """The 10 scope-bounded sourcing prompts (Part 1). Never raises."""
    return _PROMPTS


def priority_prompts() -> Tuple[int, ...]:
    """The 'if you only run three' set — prevalence proven by a method that
    survives diligence."""
    return tuple(p.num for p in _PROMPTS if p.priority)


def sourcing_summary() -> Dict[str, Any]:
    """Counts for the page header / meta line. Never raises."""
    ce = connector_evidence()
    used_keys = set()
    n_sources = 0
    for p in _PROMPTS:
        used_keys.update(p.connector_keys)
        n_sources += len(p.sources)
    resolved = [k for k in used_keys
                if ce.available and k in ce.probes_by_key]
    return {
        "n_prompts": len(_PROMPTS),
        "n_priority": len(priority_prompts()),
        "priority_set": list(priority_prompts()),
        "n_sources": n_sources,
        "n_connectors_used": len(resolved),
        "part": 1,
    }
