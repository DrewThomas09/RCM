"""Market Reports — in-depth, honestly-sourced dossiers per healthcare subsector.

The TAM/SAM builder (``rcm_mc/diligence/tam_sam.py``) answers *how big*. The
industry deep-dives (``rcm_mc/diligence/industry_deep_dive.py``) answer *what
our real data says*. This subsystem answers the question an IC asks first and
last: **explain this industry to me — all the moving parts, the tacit knowledge
the operators live by, and where I confirm it against our own data.**

Each subsector gets one authored :class:`MarketReport` living in
``rcm_mc/market_reports/reports/<slug>.py``. Reports self-register on import;
:func:`all_reports` autoloads every module in that package. The
:data:`CANONICAL_SUBSECTORS` list carries all ~83 subsector slugs so the
``/market`` index can show *every* subsector even before its report module is
authored (missing ones render an honest "scaffold — coming soon" page, never a
404).

Honesty is the load-bearing invariant (this is a diligence tool). Every
quantitative claim carries a basis label:

  * ``SOURCED``     — derived from OUR data (deep-dive / corpus / CMS files);
                      the ``source_label`` says which.
  * ``GOV``         — a real government figure (CMS, MedPAC, USRDS, Census).
  * ``ACADEMIC``    — a real peer-reviewed / academic citation.
  * ``ILLUSTRATIVE``— modeled (e.g. from the TAM/SAM chain); the basis is named.

Never fabricate a precise figure without one of these.

────────────────────────────────────────────────────────────────────────────
HOW TO ADD ONE SUBSECTOR MODULE  (the fan-out recipe)
────────────────────────────────────────────────────────────────────────────
1. Pick the slug from :data:`CANONICAL_SUBSECTORS` (it is already the TAM/SAM
   template key AND the ``industry_deep_dive`` registry key — they line up 1:1).
2. Copy ``rcm_mc/market_reports/reports/hospice.py`` to ``<slug>.py``. It is the
   cleanest template: a deals-only deep-dive (most subsectors are), per-diem
   reimbursement, real MedPAC/CMS citations. (Use ``dialysis.py`` when your
   subsector has a rich vendored facility file — dialysis/home_health/hospice/
   snf/irf/ltch/hospitals do; check ``DEEP_DIVES`` in industry_deep_dive.py.)
3. Wire live figures: call ``live_figures_from_dive("<slug>")`` and drop the
   returned list into ``live_figures=``. It pulls SOURCED numbers (facility
   count, chain/for-profit share, corpus deal MOIC) straight from the matching
   ``*_deep_dive()`` — no hand-typed magnitudes.
4. Author the qualitative sections from real industry knowledge: reimbursement
   mechanics (PPS bundle / PDGM / per-diem caps / fee-schedule / bundles),
   regulatory rules (with source_url where you have it), consolidation, and the
   ``insider_lens`` — the non-obvious dynamics operators know and outsiders miss.
5. Set the ``tam_headline`` from the TAM/SAM top-down anchor (basis ``GOV`` when
   it is a published CMS/MedPAC number, ``ILLUSTRATIVE`` when it is the modeled
   chain value). Cite the growth as the modeled composite CAGR.
6. Wire ``connections`` with :func:`default_connections` (sizing build, deep-
   dive, deal history, target screener, connector datasets) plus any subsector-
   specific page route, and ``sources`` with real citations.
7. End the module with ``register(REPORT)``. That validates it and adds it to
   the registry; ``all_reports()`` will pick it up automatically. Add a
   ``tests/`` assertion only if you want to pin subsector-specific content.

Every ``$`` / ``%`` figure you introduce MUST travel with a basis label — use
the ``Segment.source_label`` / ``TamHeadline.basis_label`` / ``LiveFigure``
slots, never a bare number in prose.
"""
from __future__ import annotations

import pkgutil
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

# ── Controlled vocabularies ─────────────────────────────────────────────────
# A displayed number is only defensible if a partner can trace it to one of
# these. The renderer chips each figure with its basis so an LP reading an
# export never mistakes a modeled magnitude for a filed one.
BASIS_LABELS = ("SOURCED", "GOV", "ACADEMIC", "ILLUSTRATIVE")
SOURCE_KINDS = ("ACADEMIC", "GOV", "INDUSTRY", "INTERNAL")
CONNECTION_KINDS = (
    "sizing",     # the TAM/SAM builder for this subsector
    "deep-dive",  # the real-data industry deep-dive panels
    "deals",      # the corpus deal history for the sector
    "screener",   # the target screener filtered to this vertical
    "connector",  # a public-data connector dataset in the estate
    "page",       # another live app surface (CMS vertical page, market intel)
)
SEVERITIES = ("High", "Medium", "Low")

# Care-setting groupings for the editorial index — ordered as a partner would
# scan the post-acute → ambulatory → specialty → services spectrum.
CARE_SETTINGS: Tuple[str, ...] = (
    "Post-acute",
    "Ambulatory",
    "Physician services",
    "Dx & labs",
    "Pharmacy & infusion",
    "Behavioral",
    "Other services",
)


# ── Nested typed records ────────────────────────────────────────────────────
@dataclass
class TamHeadline:
    """The masthead market-size number. ``basis_label`` is mandatory."""
    value: float
    unit: str                       # "$B" | "$M" | "%"
    growth_pct: Optional[float]     # modeled/observed CAGR, 1dp when shown
    basis_label: str                # one of BASIS_LABELS
    basis_note: str = ""            # names the modeled basis / the source


@dataclass
class Segment:
    """A slice of the market with its own source label (never a bare number)."""
    name: str
    value: str                      # pre-worded, e.g. "$18.0B" or "62% of vol."
    source_label: str               # basis + short source, e.g. "GOV · MedPAC"


@dataclass
class Rule:
    name: str
    why_it_matters: str
    source_url: Optional[str] = None


@dataclass
class Kpi:
    metric: str
    typical_range: str
    why: str


@dataclass
class Risk:
    risk: str
    severity: str                   # one of SEVERITIES
    note: str


@dataclass
class Connection:
    label: str
    href: str
    kind: str                       # one of CONNECTION_KINDS


@dataclass
class Source:
    citation: str
    kind: str                       # one of SOURCE_KINDS
    url: Optional[str] = None


@dataclass
class LiveFigure:
    """A SOURCED figure pulled from our own data at render time."""
    label: str
    value: str
    source_label: str
    basis: str = "SOURCED"


@dataclass
class HowItWorks:
    value_chain: List[str]          # ordered steps from referral → cash
    sites_of_care: List[str]
    money_flow: str                 # paragraph
    key_players: str                # paragraph


@dataclass
class MarketSize:
    segments: List[Segment]
    growth_drivers: List[str]


@dataclass
class Reimbursement:
    payer_mix: Dict[str, float]     # label -> share in [0,1]
    rate_mechanics: List[str]       # PPS / PDGM / per-diem / fee-schedule ...
    reimbursement_risk: str         # paragraph


@dataclass
class Regulatory:
    rules: List[Rule]
    policy_watch: List[str]


@dataclass
class Competition:
    fragmentation: str              # paragraph
    consolidation: str              # paragraph
    pe_activity: str                # paragraph
    notable_players: List[str]
    hhi_or_share: Optional[str] = None


@dataclass
class UnitEconomics:
    kpis: List[Kpi]
    margin_profile: str             # paragraph


# ── Deep-section records (the "one hour and you have the whole idea" layer) ──
# All OPTIONAL on MarketReport (default None / empty) so existing modules keep
# validating; a figure-bearing record carries a basis label, checked below.
@dataclass
class GrowthLever:
    """One distinct engine of growth, with its mechanism and rough magnitude."""
    lever: str
    mechanism: str
    magnitude: str                  # e.g. "+1.8%/yr", "primary", "−1.5%/yr"
    basis: str = "ILLUSTRATIVE"     # one of BASIS_LABELS (magnitude's basis)


@dataclass
class VolumeDriver:
    """The single dominant demand driver, isolated and analyzed."""
    driver: str                     # e.g. "ESRD prevalence"
    analysis: str                   # paragraph
    basis: str = "GOV"              # one of BASIS_LABELS


@dataclass
class CostDriver:
    """One line of the ranked cost structure — what actually moves margin."""
    driver: str                     # e.g. "Clinical labor"
    share_or_rank: str              # e.g. "~55% of cost" or "#1"
    note: str
    basis: str = "ILLUSTRATIVE"     # one of BASIS_LABELS


@dataclass
class CmsTrend:
    """A real trended CMS series + its written takeaway. The SERIES itself is
    computed at render time (``analytics.supply_trend(slug)``) so it stays
    SOURCED and never hand-typed; the author supplies the reading."""
    takeaway: str                   # "what this shows"
    source_label: str = ""          # renderer fills from analytics if blank
    chart_kind: str = "bars"        # bars | line


@dataclass
class MarketReport:
    """A complete, authored, honestly-sourced subsector dossier.

    Section fields mirror the ``/market/<slug>`` renderer 1:1. The nested
    dataclasses keep authoring typed (autocomplete + ``validate()``) so a
    fan-out author can copy a flagship and fill blanks without guessing shapes.
    """
    slug: str
    name: str
    one_line_def: str
    care_setting: str
    tam_headline: TamHeadline
    executive_summary: List[str]
    how_it_works: HowItWorks
    market_size: MarketSize
    reimbursement: Reimbursement
    regulatory: Regulatory
    competition: Competition
    unit_economics: UnitEconomics
    risks: List[Risk]
    diligence_questions: List[str]
    insider_lens: List[str]
    connections: List[Connection]
    sources: List[Source]
    naics: Optional[str] = None
    live_figures: List[LiveFigure] = field(default_factory=list)

    # ── Deep sections (all OPTIONAL — absent = fine, backward compatible) ────
    # The multi-year trajectory, the growth engine breakdown, the isolated
    # volume driver, the ranked cost structure, the real CMS trend + takeaway,
    # and an optional authored supplement to the computed state breakdown. The
    # state-breakdown TABLE + its computed insight always come from
    # ``analytics.state_breakdown(slug)`` at render; ``state_breakdown`` here is
    # only an optional authored note layered on top.
    trends: Optional[str] = None
    growth_levers: List[GrowthLever] = field(default_factory=list)
    volume_growth_driver: Optional[VolumeDriver] = None
    cost_drivers: List[CostDriver] = field(default_factory=list)
    cms_trend: Optional[CmsTrend] = None
    state_breakdown: Optional[str] = None

    # ── Integrity ──────────────────────────────────────────────────────────
    def validate(self) -> None:
        """Fail loudly at register time if the report violates the honesty or
        taxonomy contract. Called by :func:`register` so a broken report never
        reaches a partner surface silently."""
        errs: List[str] = []
        if self.slug not in _CANONICAL_SLUGS:
            errs.append(f"slug {self.slug!r} is not a canonical subsector")
        if self.care_setting not in CARE_SETTINGS:
            errs.append(f"care_setting {self.care_setting!r} not recognised")
        if _CANONICAL_SETTING.get(self.slug) not in (None, self.care_setting):
            errs.append(
                f"care_setting {self.care_setting!r} disagrees with the "
                f"canonical grouping {_CANONICAL_SETTING.get(self.slug)!r}")
        if self.tam_headline.basis_label not in BASIS_LABELS:
            errs.append(
                f"tam_headline.basis_label {self.tam_headline.basis_label!r} "
                f"not in {BASIS_LABELS}")
        if not (3 <= len(self.executive_summary) <= 8):
            errs.append("executive_summary must carry 3-8 takeaways")
        for seg in self.market_size.segments:
            if not seg.source_label.strip():
                errs.append(f"segment {seg.name!r} missing a source_label")
        for r in self.risks:
            if r.severity not in SEVERITIES:
                errs.append(f"risk {r.risk!r} severity {r.severity!r} invalid")
        for c in self.connections:
            if c.kind not in CONNECTION_KINDS:
                errs.append(f"connection {c.label!r} kind {c.kind!r} invalid")
        for s in self.sources:
            if s.kind not in SOURCE_KINDS:
                errs.append(f"source {s.citation!r} kind {s.kind!r} invalid")
        # Core qualitative sections must actually be authored.
        for label, val in (
            ("how_it_works.money_flow", self.how_it_works.money_flow),
            ("reimbursement.reimbursement_risk",
             self.reimbursement.reimbursement_risk),
            ("competition.fragmentation", self.competition.fragmentation),
            ("unit_economics.margin_profile", self.unit_economics.margin_profile),
        ):
            if not str(val).strip():
                errs.append(f"{label} is empty")
        if not self.insider_lens:
            errs.append("insider_lens must carry at least one non-obvious note")
        # ── Deep-section basis labels (checked only when present) ──
        for gl in self.growth_levers:
            if gl.basis not in BASIS_LABELS:
                errs.append(
                    f"growth_lever {gl.lever!r} basis {gl.basis!r} not in "
                    f"{BASIS_LABELS}")
            if not gl.lever.strip() or not gl.mechanism.strip():
                errs.append(f"growth_lever {gl.lever!r} missing lever/mechanism")
        if self.volume_growth_driver is not None:
            vd = self.volume_growth_driver
            if vd.basis not in BASIS_LABELS:
                errs.append(
                    f"volume_growth_driver basis {vd.basis!r} not in "
                    f"{BASIS_LABELS}")
            if not vd.driver.strip() or not vd.analysis.strip():
                errs.append("volume_growth_driver missing driver/analysis")
        for cd in self.cost_drivers:
            if cd.basis not in BASIS_LABELS:
                errs.append(
                    f"cost_driver {cd.driver!r} basis {cd.basis!r} not in "
                    f"{BASIS_LABELS}")
            if not cd.driver.strip() or not cd.share_or_rank.strip():
                errs.append(f"cost_driver {cd.driver!r} missing driver/share")
        if self.cms_trend is not None and not self.cms_trend.takeaway.strip():
            errs.append("cms_trend.takeaway is empty")
        if errs:
            raise ValueError(
                f"MarketReport({self.slug!r}) failed validation:\n  - "
                + "\n  - ".join(errs))


# ── Canonical subsector taxonomy ────────────────────────────────────────────
# (slug, display_name, care_setting). Slugs are the TAM/SAM template keys AND
# the industry_deep_dive registry keys (they line up 1:1), so every subsector
# has a live sizing build and a deep-dive available for its connections. The
# tests pin that this set equals the deep-dive registry.
CANONICAL_SUBSECTORS: List[Tuple[str, str, str]] = [
    # ── Post-acute ──
    ("home_health", "Home Health", "Post-acute"),
    ("hospice", "Hospice", "Post-acute"),
    ("snf", "Skilled Nursing (SNF)", "Post-acute"),
    ("irf", "Inpatient Rehab (IRF)", "Post-acute"),
    ("ltch", "Long-Term Acute Care (LTCH)", "Post-acute"),
    ("hospital_at_home", "Hospital-at-Home", "Post-acute"),
    ("home_care", "Home Care", "Post-acute"),
    ("pace", "PACE", "Post-acute"),
    ("palliative", "Palliative", "Post-acute"),
    ("senior_living", "Senior Living", "Post-acute"),
    ("pediatric_home_health", "Pediatric PDN", "Post-acute"),
    ("wound_care", "Wound Care", "Post-acute"),
    # ── Ambulatory ──
    ("dialysis", "Dialysis", "Ambulatory"),
    ("asc", "Ambulatory Surgery (ASC)", "Ambulatory"),
    ("urgent_care", "Urgent Care", "Ambulatory"),
    ("retail_clinics", "Retail Clinics", "Ambulatory"),
    ("physical_therapy", "Physical Therapy", "Ambulatory"),
    ("medspa", "Medspa", "Ambulatory"),
    ("sleep", "Sleep", "Ambulatory"),
    ("occ_health", "Occupational Health", "Ambulatory"),
    ("vascular_access", "Vascular Access", "Ambulatory"),
    ("surgical_assist", "Surgical Assist", "Ambulatory"),
    ("virtual_primary_care", "Virtual Primary Care", "Ambulatory"),
    ("rpm", "Remote Patient Monitoring (RPM)", "Ambulatory"),
    ("care_navigation", "Care Navigation", "Ambulatory"),
    # ── Physician services ──
    ("physician_group", "Physician Groups", "Physician services"),
    ("fertility_ivf", "Fertility / IVF", "Physician services"),
    ("oncology", "Oncology", "Physician services"),
    ("cardiology", "Cardiology", "Physician services"),
    ("gastroenterology", "Gastroenterology (GI)", "Physician services"),
    ("orthopedics", "Orthopedics", "Physician services"),
    ("womens_health", "Women's Health", "Physician services"),
    ("podiatry", "Podiatry", "Physician services"),
    ("ent_allergy", "ENT & Allergy", "Physician services"),
    ("anesthesia", "Anesthesia", "Physician services"),
    ("dermatology", "Dermatology", "Physician services"),
    ("ophthalmology", "Ophthalmology", "Physician services"),
    ("vision", "Vision", "Physician services"),
    ("urology", "Urology", "Physician services"),
    ("rheumatology", "Rheumatology", "Physician services"),
    ("neurology", "Neurology", "Physician services"),
    ("endocrinology_obesity", "Endocrinology & Obesity", "Physician services"),
    ("pulmonology", "Pulmonology", "Physician services"),
    ("nephrology", "Nephrology", "Physician services"),
    ("pain_management", "Pain Management", "Physician services"),
    ("hospitalist", "Hospitalist", "Physician services"),
    ("dental", "Dental / DSO", "Physician services"),
    ("transplant_services", "Transplant Services", "Physician services"),
    # ── Dx & labs ──
    ("imaging", "Imaging", "Dx & labs"),
    ("clinical_labs", "Clinical Labs", "Dx & labs"),
    ("teleradiology", "Teleradiology", "Dx & labs"),
    ("mobile_diagnostics", "Mobile Diagnostics", "Dx & labs"),
    ("genetic_testing", "Genetic Testing", "Dx & labs"),
    ("plasma", "Plasma", "Dx & labs"),
    ("clinical_research", "Research Sites", "Dx & labs"),
    # ── Pharmacy & infusion ──
    ("infusion", "Infusion", "Pharmacy & infusion"),
    ("specialty_pharmacy", "Specialty Rx", "Pharmacy & infusion"),
    ("ltc_pharmacy", "LTC Pharmacy", "Pharmacy & infusion"),
    ("dme", "DME", "Pharmacy & infusion"),
    ("compounding_503b", "503B Compounding", "Pharmacy & infusion"),
    # ── Behavioral ──
    ("behavioral_health", "Behavioral Health", "Behavioral"),
    ("aba", "ABA / Autism", "Behavioral"),
    ("eating_disorders", "Eating Disorders", "Behavioral"),
    ("idd_services", "IDD Services", "Behavioral"),
    ("crisis_services", "Crisis Services", "Behavioral"),
    ("school_services", "School Services", "Behavioral"),
    # ── Other services ──
    ("hospitals", "Hospitals", "Other services"),
    ("ems", "EMS", "Other services"),
    ("air_medical", "Air Medical", "Other services"),
    ("veterinary", "Veterinary", "Other services"),
    ("rcm_services", "RCM Services", "Other services"),
    ("hit_consulting", "HIT Consulting", "Other services"),
    ("correctional_health", "Correctional Health", "Other services"),
    ("locum_staffing", "Locum Staffing", "Other services"),
    ("nemt", "NEMT", "Other services"),
    ("lop_medicine", "LOP Medicine", "Other services"),
    ("dental_labs", "Dental Labs", "Other services"),
    ("htm_clinical_engineering", "HTM / Clinical Engineering", "Other services"),
    ("interpretation", "Interpretation", "Other services"),
    ("roi_services", "ROI Services", "Other services"),
    ("sterile_processing", "Sterile Processing", "Other services"),
    ("perfusion", "Perfusion", "Other services"),
    ("orthotics_prosthetics", "Orthotics & Prosthetics (O&P)", "Other services"),
]

_CANONICAL_SLUGS = {s for s, _, _ in CANONICAL_SUBSECTORS}
_CANONICAL_NAME = {s: n for s, n, _ in CANONICAL_SUBSECTORS}
_CANONICAL_SETTING = {s: c for s, _, c in CANONICAL_SUBSECTORS}


def canonical_slugs() -> List[str]:
    return [s for s, _, _ in CANONICAL_SUBSECTORS]


def display_name(slug: str) -> str:
    return _CANONICAL_NAME.get(slug, slug.replace("_", " ").title())


def care_setting_for(slug: str) -> Optional[str]:
    return _CANONICAL_SETTING.get(slug)


def subsectors_by_setting() -> Dict[str, List[Tuple[str, str]]]:
    """Ordered {care_setting: [(slug, display_name), ...]} for the index."""
    out: Dict[str, List[Tuple[str, str]]] = {c: [] for c in CARE_SETTINGS}
    for slug, name, setting in CANONICAL_SUBSECTORS:
        out.setdefault(setting, []).append((slug, name))
    return out


# ── Registry + autoloader ───────────────────────────────────────────────────
_REGISTRY: Dict[str, MarketReport] = {}
_AUTOLOADED = False
_AUTOLOAD_ERRORS: List[Tuple[str, str]] = []


def register(report: MarketReport) -> MarketReport:
    """Validate and register a report. Call at the bottom of each subsector
    module: ``register(REPORT)``. Returns the report so it can double as a
    module-level binding. Re-registering a slug replaces it (module reloads in
    tests stay idempotent)."""
    report.validate()
    _REGISTRY[report.slug] = report
    return report


def _autoload() -> None:
    """Import every module under ``reports/`` so each report self-registers.

    Runs once per process (gated on ``_AUTOLOADED``). After
    :func:`reset_for_tests` clears the registry, an already-imported module is
    cached in ``sys.modules`` and a plain import would NOT re-run its
    ``register(REPORT)`` — so we reload it, which re-executes the module body
    and repopulates the registry. A module that raises is recorded in
    ``_AUTOLOAD_ERRORS`` and skipped — the index must never 500 because one
    subsector is broken."""
    global _AUTOLOADED
    if _AUTOLOADED:
        return
    _AUTOLOADED = True
    import importlib
    import sys
    from . import reports as _reports_pkg
    for mod in pkgutil.iter_modules(_reports_pkg.__path__):
        if mod.name.startswith("_"):
            continue
        modname = f"{__name__}.reports.{mod.name}"
        try:
            existing = sys.modules.get(modname)
            if existing is not None:
                importlib.reload(existing)
            else:
                import_module(modname)
        except Exception as exc:  # noqa: BLE001 — one bad report can't nuke all
            _AUTOLOAD_ERRORS.append((mod.name, repr(exc)))


def reset_for_tests() -> None:
    """Clear the registry + autoload latch so a test can force a fresh load."""
    global _AUTOLOADED
    _REGISTRY.clear()
    _AUTOLOAD_ERRORS.clear()
    _AUTOLOADED = False


def all_reports() -> Dict[str, MarketReport]:
    """Autoload the reports package and return {slug: MarketReport}."""
    _autoload()
    return dict(_REGISTRY)


def report_for(slug: str) -> Optional[MarketReport]:
    """The authored report for ``slug``, or ``None`` when only a scaffold
    exists yet. Never raises on an unknown slug."""
    _autoload()
    return _REGISTRY.get(slug)


def autoload_errors() -> List[Tuple[str, str]]:
    _autoload()
    return list(_AUTOLOAD_ERRORS)


# ── Shared wiring helpers for report authors ────────────────────────────────
def live_figures_from_dive(slug: str) -> List[LiveFigure]:
    """Pull SOURCED headline figures from the matching ``*_deep_dive()``.

    This is the one place a report touches our live data. It degrades to ``[]``
    when the dive is unavailable (offline / file missing) so a report still
    renders its authored qualitative content. Every returned figure is basis
    ``SOURCED`` with the dive's own source string.
    """
    try:
        from ..diligence.industry_deep_dive import deep_dive_for
    except Exception:  # noqa: BLE001
        return []
    dive = deep_dive_for(slug)
    if not dive:
        return []
    out: List[LiveFigure] = []
    fac_src = dive.get("facility_source") or "our vendored provider file"
    n_fac = dive.get("n_facilities")
    if n_fac:
        out.append(LiveFigure(
            "Facilities in our universe", f"{n_fac:,}",
            f"SOURCED · {fac_src}"))
    pool_label = dive.get("pool_label")
    n_pool = dive.get("n_independent")
    if pool_label and n_pool:
        share = (n_pool / n_fac) if n_fac else None
        val = f"{n_pool:,}" + (f" ({share * 100:.1f}%)" if share else "")
        out.append(LiveFigure(
            f"{pool_label} pool (the acquirable whitespace)", val,
            f"SOURCED · {fac_src}"))
    duo = dive.get("duopoly_share")
    if duo:
        out.append(LiveFigure(
            "Top-2 chain share", f"{duo * 100:.1f}%",
            "SOURCED · chain concentration in our facility file"))
    sd = dive.get("sector_deals") or {}
    if sd.get("n"):
        out.append(LiveFigure(
            "Corpus deals in this sector", f"{sd['n']:,}",
            "SOURCED · PE Desk realized-deal corpus"))
        if sd.get("median_moic") is not None:
            out.append(LiveFigure(
                "Median realized MOIC (corpus)", f"{sd['median_moic']:.2f}x",
                f"SOURCED · {sd.get('n_realized', 0)} realized corpus deals"))
        if sd.get("median_entry_multiple") is not None:
            out.append(LiveFigure(
                "Median entry EV/EBITDA (corpus)",
                f"{sd['median_entry_multiple']:.1f}x",
                "SOURCED · PE Desk corpus, entry multiples"))
    return out


def default_connections(
    slug: str,
    *,
    deals_sector: str,
    connectors: Optional[List[Tuple[str, str]]] = None,
    extra_pages: Optional[List[Tuple[str, str]]] = None,
) -> List[Connection]:
    """The standard connection set every subsector shares, plus optional
    subsector-specific connector datasets and app pages.

    ``connectors`` is a list of ``(dataset_id, label)`` for the public-data
    estate (``/connector-estate?dataset=<id>``). ``extra_pages`` is a list of
    ``(href, label)`` for live app surfaces (a CMS vertical page, market intel).
    """
    conns: List[Connection] = [
        Connection("Size it: TAM/SAM builder + real-data deep-dive panels",
                   f"/diligence/tam-sam?template={slug}", "sizing"),
        Connection("Deal history: realized corpus deals in this sector",
                   f"/deal-search?sector={deals_sector}", "deals"),
        Connection("Screen targets in this vertical",
                   f"/target-screener?vertical={slug}", "screener"),
    ]
    for href, label in (extra_pages or []):
        conns.append(Connection(label, href, "page"))
    for dataset_id, label in (connectors or []):
        conns.append(Connection(
            label, f"/connector-estate?dataset={dataset_id}", "connector"))
    return conns
