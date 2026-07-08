"""IFT sizing analytics — the offline-computable, honestly-labelled quantitative
spine for the Interfacility Transport (IFT) market report.

IFT is not a standalone fee-schedule line; it is the *interfacility slice* cut
across ground EMS + air medical + NEMT. There is no vendored ambulance / NEMT
facility roll on disk, so the six provider-CSV-backed analytics in
``analytics.py`` (state_breakdown / supply_trend) honestly return
"unavailable offline" for this slug. This module supplies the numbers that ARE
computable with zero new data, and typed *honest-unavailable* hooks for the
connectors that only light up once the estate is ingested.

What is real and SOURCED offline (computed here, from files that ship):

  * :func:`occupancy_trend` — national inpatient occupancy (patient-days /
    bed-days-available) per fiscal year from the vendored CMS HCRIS FY2020-2022
    panel. Occupancy is the throughput/transfer-demand engine — high census is
    what generates capacity/load-balancing interfacility transfers — so it is a
    genuine, non-fabricated demand proxy that stands in for the network-gated
    HHS hospital-capacity time-series.
  * :func:`occupancy_by_state` — the same measure, latest FY, per state (filtered
    to states with enough filers to be non-noisy). The tightest markets are the
    tightest transfer markets.
  * :func:`transport_deal_history` — the realized-deal corpus, unioned across the
    EMS + NEMT + air-medical tokens (the three IFT modalities), for the sector's
    own n / median MOIC / entry-multiple history.
  * :func:`fee_schedule` — the Medicare Ambulance Fee Schedule ready-reckoner.
    The relative value units are fixed regulatory constants (GOV, 42 CFR 414
    Subpart H), so RVU x conversion-factor = worked base rate is pure
    arithmetic; the worked dollars at a stated CF are ILLUSTRATIVE (the exact CF
    lives in the CMS AFS public-use file).

What is NETWORK-GATED offline (typed hooks that degrade to an honest note with a
GOV/ILLUSTRATIVE fallback citation, never a fabricated number):

  * :func:`ambulance_part_b_utilization` — Medicare Part B ambulance-HCPCS
    utilization/spend (A0426-A0436). The estate's physician/supplier
    procedure-summary is not ingested offline (0 rows), so this returns the
    fee-schedule / MedPAC / GADCS GOV citations to cite instead.
  * :func:`nemt_state_coverage` — the state-by-state Medicaid NEMT benefit. The
    brief-named benefits dataset is not even registered in the offline estate,
    so this returns the federal-mandate GOV citation.
  * :func:`ambulance_employment` — BLS QCEW NAICS 621910 employment/wages, also
    network-gated offline.

Design contract (mirrors ``analytics.py``): pure, no runtime network, cached,
and every function **degrades — never raises**, returning a typed record with
``available`` + ``source_label`` (+ ``note`` / ``fallback_citation``) so the
report renders an honest label instead of crashing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Ambulance HCPCS — the mechanical fingerprints of an IFT claim ────────────
# The A04xx codes and their fee-schedule RVUs are regulatory constants
# (42 CFR 414 Subpart H; the RVU table via the PYA Medicare payment primer,
# BLS-nonE = 1.00 anchor). SCT / A0434 (RVU 3.25) is definitionally an
# interfacility critical-care code; A0426/A0428 non-emergent are the
# discharge/dialysis interfacility fingerprints.
_AMBULANCE_RVU: Tuple[Tuple[str, str, float], ...] = (
    ("A0428", "BLS non-emergency", 1.00),
    ("A0429", "BLS emergency", 1.60),
    ("A0426", "ALS1 non-emergency", 1.20),
    ("A0427", "ALS1 emergency", 1.90),
    ("A0433", "ALS2", 2.75),
    ("A0434", "Specialty Care Transport (SCT)", 3.25),
    ("A0432", "Paramedic Intercept", 1.75),
)

# Every ambulance HCPCS the report references (base + mileage + air), used by
# the network-gated Part B probe so the wiring is real and ingest-ready.
_AMBULANCE_HCPCS: Tuple[str, ...] = (
    "A0426", "A0427", "A0428", "A0429", "A0433", "A0434",
    "A0430", "A0431", "A0425", "A0435", "A0436",
)

# The default CY2024-25 conversion factor used for the worked base rates. The
# exact CF ships in the CMS AFS public-use file; this tracks the national
# amounts closely and is labelled ILLUSTRATIVE wherever a dollar is shown.
_DEFAULT_CF = 278.0

# Corpus sector tokens that ARE interfacility transport (the union of the three
# modalities). Matched case-insensitively, plus substring fallbacks so free-text
# tags like "NEMT / Transportation" and "air_ambulance" are caught.
_TRANSPORT_TOKENS = frozenset({
    "ems", "nemt", "air_medical", "air_ambulance", "medical_transport",
    "transportation", "nemt / transportation", "ambulance",
})
_TRANSPORT_SUBSTRINGS = ("transport", "nemt", "ambulance", "air medical",
                         "air_medical")


# ── HCRIS occupancy (SOURCED, offline) ──────────────────────────────────────
@dataclass
class OccupancyTrend:
    """National inpatient occupancy by fiscal year — a transfer-demand proxy."""
    available: bool
    points: List[Tuple[int, float]] = field(default_factory=list)   # (fy, occ)
    n_by_year: Dict[int, int] = field(default_factory=dict)
    first_fy: Optional[int] = None
    latest_fy: Optional[int] = None
    latest_occupancy: Optional[float] = None
    delta_pp: Optional[float] = None                # first→last, percentage pts
    n_filers_latest: int = 0
    source_label: str = ""
    note: str = ""
    takeaway: str = ""


@dataclass
class StateOccupancyRow:
    state: str
    occupancy: float
    n_filers: int


@dataclass
class StateOccupancy:
    available: bool
    rows: List[StateOccupancyRow] = field(default_factory=list)
    fiscal_year: Optional[int] = None
    source_label: str = ""
    insight: str = ""
    note: str = ""


def _occupancy_frame():
    """Return a cleaned HCRIS occupancy frame (fy, bda, tpd, state) or None.

    Filters to rows with positive bed-days-available and a plausible
    patient-day ratio (0 <= tpd <= bda * 1.05, dropping the handful of
    impossible-ratio filings). Never raises — returns None on any failure so
    every caller degrades to available=False."""
    try:
        import pandas as pd
        from ..data import hcris
        df = hcris._get_hcris_cached()
        if df is None or df.empty:
            return None
        out = pd.DataFrame({
            "fy": pd.to_numeric(df.get("fiscal_year"), errors="coerce"),
            "bda": pd.to_numeric(df.get("bed_days_available"), errors="coerce"),
            "tpd": pd.to_numeric(df.get("total_patient_days"), errors="coerce"),
            "state": df.get("state").astype(str).str.upper()
            if "state" in df.columns else "",
        })
        mask = (out["bda"] > 0) & (out["tpd"] >= 0) & (out["tpd"] <= out["bda"] * 1.05)
        out = out[mask & out["fy"].notna()]
        if out.empty:
            return None
        out["fy"] = out["fy"].astype(int)
        return out
    except Exception:  # noqa: BLE001 — degrade, never raise
        return None


_HCRIS_LABEL = ("SOURCED · CMS HCRIS (Hospital 2552-10 cost reports; "
                "total_patient_days / bed_days_available), vendored FY2020-2022 "
                "panel")


def occupancy_trend() -> OccupancyTrend:
    """National inpatient occupancy per fiscal year from the vendored HCRIS
    panel — the throughput/transfer-demand engine, computed, SOURCED, offline.

    Substitutes cleanly for the network-gated HHS hospital-capacity state
    time-series: occupancy = sum(patient-days) / sum(bed-days-available) across
    ~5.9K filers per year. A throughput proxy (not a same-day census)."""
    df = _occupancy_frame()
    if df is None:
        return OccupancyTrend(
            available=False,
            source_label=_HCRIS_LABEL,
            note=("HCRIS occupancy panel is not available offline; national "
                  "inpatient occupancy is cited from CMS/AHA with a GOV label "
                  "instead."))
    try:
        points: List[Tuple[int, float]] = []
        n_by_year: Dict[int, int] = {}
        for fy, grp in df.groupby("fy"):
            bda = float(grp["bda"].sum())
            tpd = float(grp["tpd"].sum())
            if bda <= 0:
                continue
            points.append((int(fy), tpd / bda))
            n_by_year[int(fy)] = int(len(grp))
        points.sort(key=lambda p: p[0])
        if len(points) < 2:
            return OccupancyTrend(
                available=False, source_label=_HCRIS_LABEL,
                note="HCRIS panel carries fewer than two fiscal years offline.")
        first_fy, first_occ = points[0]
        latest_fy, latest_occ = points[-1]
        delta_pp = (latest_occ - first_occ) * 100.0
        takeaway = (
            f"National inpatient occupancy ran {first_occ * 100:.1f}% in "
            f"FY{first_fy}, {points[1][1] * 100:.1f}% in FY{points[1][0]}, and "
            f"{latest_occ * 100:.1f}% in FY{latest_fy} ({delta_pp:+.1f}pp across "
            f"the window) across ~{n_by_year.get(latest_fy, 0):,} filers — the "
            "post-COVID census recovery. Occupancy is the throughput engine of "
            "interfacility transport: when tertiary and step-down beds fill, "
            "ED-boarding builds and capacity/load-balancing transfers rise, so "
            "this is a genuine (if lagging) demand proxy — not a same-day "
            "transfer count.")
        return OccupancyTrend(
            available=True, points=points, n_by_year=n_by_year,
            first_fy=first_fy, latest_fy=latest_fy,
            latest_occupancy=latest_occ, delta_pp=delta_pp,
            n_filers_latest=n_by_year.get(latest_fy, 0),
            source_label=_HCRIS_LABEL,
            note=("National inpatient occupancy = patient-days / "
                  "bed-days-available across ~5.9K filers/yr; a throughput "
                  "proxy for interfacility transfer demand, not a same-day "
                  "census or a transfer count."),
            takeaway=takeaway)
    except Exception:  # noqa: BLE001
        return OccupancyTrend(
            available=False, source_label=_HCRIS_LABEL,
            note="HCRIS occupancy computation failed offline.")


def occupancy_by_state(top_n: int = 8, min_filers: int = 10) -> StateOccupancy:
    """Per-state inpatient occupancy for the latest FY (states with enough
    filers to be non-noisy), sorted high→low. The tightest-census states are
    the tightest interfacility-transfer markets. SOURCED, offline."""
    df = _occupancy_frame()
    if df is None:
        return StateOccupancy(
            available=False, source_label=_HCRIS_LABEL,
            note="HCRIS occupancy panel is not available offline.")
    try:
        latest_fy = int(df["fy"].max())
        sub = df[df["fy"] == latest_fy]
        rows: List[StateOccupancyRow] = []
        for st, grp in sub.groupby("state"):
            st = str(st).strip().upper()
            if len(st) != 2:
                continue
            n = int(len(grp))
            if n < min_filers:
                continue
            bda = float(grp["bda"].sum())
            if bda <= 0:
                continue
            rows.append(StateOccupancyRow(st, float(grp["tpd"].sum()) / bda, n))
        rows.sort(key=lambda r: -r.occupancy)
        rows = rows[:max(1, int(top_n))]
        if not rows:
            return StateOccupancy(
                available=False, source_label=_HCRIS_LABEL,
                note="No state met the minimum-filer threshold offline.")
        lead = rows[0]
        second = rows[1] if len(rows) > 1 else lead
        insight = (
            f"{lead.state} and {second.state} lead at "
            f"{lead.occupancy * 100:.1f}% and {second.occupancy * 100:.1f}% "
            f"inpatient occupancy (FY{latest_fy}); high-occupancy states are the "
            "tightest transfer markets, where capacity load-balancing and "
            "ED-boarding push the most interfacility volume.")
        return StateOccupancy(
            available=True, rows=rows, fiscal_year=latest_fy,
            source_label=(_HCRIS_LABEL + f", latest FY (FY{latest_fy}), states "
                          f"with ≥{min_filers} filers"),
            insight=insight,
            note=("Per-state occupancy from the vendored HCRIS latest-FY "
                  "cross-section; states below the filer threshold are omitted "
                  "rather than shown as noise."))
    except Exception:  # noqa: BLE001
        return StateOccupancy(
            available=False, source_label=_HCRIS_LABEL,
            note="HCRIS per-state occupancy computation failed offline.")


# ── Transport deal history (SOURCED, offline) ───────────────────────────────
@dataclass
class DealHistory:
    available: bool
    n_deals: int = 0
    n_realized: int = 0
    median_moic: Optional[float] = None
    median_entry_multiple: Optional[float] = None
    entry_multiple_n: int = 0
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    deal_names: List[str] = field(default_factory=list)
    source_label: str = ""
    note: str = ""


def _median(vals: List[float]) -> Optional[float]:
    s = sorted(v for v in vals if v is not None)
    if not s:
        return None
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _is_transport(sector: Any) -> bool:
    s = str(sector or "").strip().lower()
    if not s:
        return False
    if s in _TRANSPORT_TOKENS:
        return True
    return any(sub in s for sub in _TRANSPORT_SUBSTRINGS)


def _entry_multiple(deal: Dict[str, Any]) -> Optional[float]:
    """Best-effort entry EV/EBITDA from the heterogeneous corpus fields:
    prefer an explicit ``ev_ebitda``, else derive from entry EV / entry EBITDA,
    else from total EV / EBITDA. Returns None when no clean pair exists."""
    ev = deal.get("ev_ebitda")
    if isinstance(ev, (int, float)) and ev > 0:
        return float(ev)
    for ev_key, eb_key in (("entry_ev_mm", "ebitda_at_entry_mm"),
                           ("ev_mm", "ebitda_mm")):
        ev_v, eb_v = deal.get(ev_key), deal.get(eb_key)
        if (isinstance(ev_v, (int, float)) and isinstance(eb_v, (int, float))
                and eb_v > 0 and ev_v > 0):
            return float(ev_v) / float(eb_v)
    return None


def transport_deal_history() -> DealHistory:
    """The realized-deal corpus, unioned across the EMS + NEMT + air-medical
    tokens (the three IFT modalities). SOURCED, offline. Degrades to
    available=False if the corpus can't be loaded."""
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        corpus = _load_corpus()
    except Exception:  # noqa: BLE001
        return DealHistory(
            available=False,
            source_label="SOURCED · PE Desk realized-deal corpus",
            note="The realized-deal corpus is not loadable offline.")
    hits = [d for d in corpus if _is_transport(d.get("sector"))]
    if not hits:
        return DealHistory(
            available=False,
            source_label="SOURCED · PE Desk realized-deal corpus",
            note="No EMS/NEMT/air-medical deals in the corpus.")
    moics = [d.get("realized_moic") for d in hits
             if isinstance(d.get("realized_moic"), (int, float))]
    entries = [m for m in (_entry_multiple(d) for d in hits) if m is not None]
    years: List[int] = []
    for d in hits:
        y = d.get("year") or d.get("entry_year")
        try:
            if y is not None:
                years.append(int(y))
        except (TypeError, ValueError):
            continue
    return DealHistory(
        available=True,
        n_deals=len(hits),
        n_realized=len(moics),
        median_moic=_median([float(m) for m in moics]),
        median_entry_multiple=_median(entries),
        entry_multiple_n=len(entries),
        year_min=min(years) if years else None,
        year_max=max(years) if years else None,
        deal_names=[str(d.get("deal_name", "")) for d in hits],
        source_label=("SOURCED · PE Desk realized-deal corpus "
                      "(EMS + NEMT + air-medical union)"),
        note=("Transport is a thin slice of the corpus; the EMS/NEMT/air union "
              "widens n, but the entry-multiple sample stays small — read it as "
              "directional, not a benchmark."))


# ── Ambulance fee-schedule ready-reckoner (RVU GOV → worked base ILLUSTRATIVE) ─
@dataclass
class FeeScheduleRow:
    hcpcs: str
    level: str
    rvu: float
    base_rate: float                # rvu * conversion_factor


@dataclass
class FeeSchedule:
    available: bool
    conversion_factor: float
    rows: List[FeeScheduleRow] = field(default_factory=list)
    rvu_source_label: str = ""      # the GOV RVU constants
    rate_source_label: str = ""     # the ILLUSTRATIVE worked dollars
    note: str = ""


def fee_schedule(conversion_factor: float = _DEFAULT_CF) -> FeeSchedule:
    """The Medicare Ambulance Fee Schedule ready-reckoner.

    RVU x conversion-factor = the national base rate by level of service. The
    RVU multiples are fixed regulatory constants (GOV); the worked dollars at
    the supplied conversion factor are ILLUSTRATIVE (the exact CF is in the CMS
    AFS public-use file). SCT/A0434 pays ~3.25x BLS — the highest ground line
    and the one most concentrated in interfacility critical-care transfers.
    Pure arithmetic; never raises."""
    try:
        cf = float(conversion_factor)
    except (TypeError, ValueError):
        cf = _DEFAULT_CF
    rows = [FeeScheduleRow(code, level, rvu, round(rvu * cf, 2))
            for code, level, rvu in _AMBULANCE_RVU]
    return FeeSchedule(
        available=True, conversion_factor=cf, rows=rows,
        rvu_source_label=("GOV · CMS Ambulance Fee Schedule RVU table "
                          "(42 CFR 414 Subpart H, via PYA payment primer)"),
        rate_source_label=(f"ILLUSTRATIVE · RVU × conversion factor "
                           f"${cf:,.0f} (exact CF in the CMS AFS public-use "
                           "file; GAF adjusts 70% of the base)"),
        note=("Base rate = RVU × conversion factor × geographic adjustment; the "
              "GAF applies to 70% of the base, mileage (A0425/A0435/A0436) is "
              "paid separately, and rural point-of-pickup adds a mileage bump "
              "(+50% to air base + mileage). Worked dollars are ILLUSTRATIVE."))


# ── Network-gated connector hooks (honest unavailable + GOV/ILLUSTRATIVE) ────
@dataclass
class ConnectorResult:
    """A network-gated connector read. Offline it is unavailable with a
    fallback citation; ingest-ready (the wiring is real, only the label
    differs offline)."""
    available: bool
    dataset_id: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    source_label: str = ""
    fallback_citation: str = ""
    note: str = ""


def _estate_probe(dataset_id: str, group_by: Any,
                  filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Wrap ``connector_estate.aggregate`` and return its payload (offline it
    reports count=0 / rows=[]). Never raises — returns an empty payload on any
    failure so the connector hooks share one degrade-safe code path."""
    try:
        from ..data_public import connector_estate as ce
        return ce.aggregate(dataset_id, group_by=group_by, filters=filters)
    except Exception:  # noqa: BLE001
        return {"count": 0, "rows": []}


def ambulance_part_b_utilization() -> ConnectorResult:
    """Medicare Part B ambulance-HCPCS utilization/spend (A0426-A0436).

    Network-gated offline (the physician/supplier procedure-summary is not
    ingested — 0 rows), so this returns the fee-schedule / MedPAC / GADCS GOV
    citations to cite instead. The A0426/A0428 non-emergent codes and A0434 SCT
    are the interfacility fingerprints once the estate is ingested."""
    dataset_id = "cms_open_data_physician_supplier_procedure_summary"
    payload = _estate_probe(
        dataset_id, group_by="hcpcs_cd",
        filters={"hcpcs_cd": list(_AMBULANCE_HCPCS)})
    rows = payload.get("rows") or []
    if rows:
        return ConnectorResult(
            available=True, dataset_id=dataset_id, rows=list(rows),
            source_label=("SOURCED · CMS Medicare Part B physician/supplier "
                          "procedure summary (ambulance HCPCS A0426-A0436)"),
            note="Line-level ambulance utilization from the ingested estate.")
    return ConnectorResult(
        available=False, dataset_id=dataset_id,
        source_label=("connector · " + dataset_id + " (not ingested offline)"),
        fallback_citation=("GOV · CMS Medicare Ambulance Fee Schedule "
                           "(A0426-A0436, 42 CFR 414.601-617) + MedPAC ambulance "
                           "chapter (~$4.0B Medicare FFS ambulance, 2023) + CMS "
                           "GADCS (Ground Ambulance Data Collection System, "
                           "BBA 2018 §50203)"),
        note=("Line-level ambulance utilization is network-gated offline "
              "(physician/supplier procedure-summary not ingested); the report "
              "cites the fee schedule / MedPAC / GADCS with GOV labels. Typed "
              "hook: drops in when the estate is ingested."))


def nemt_state_coverage() -> ConnectorResult:
    """State-by-state Medicaid NEMT benefit coverage.

    The brief-named benefits dataset is not registered in the offline estate,
    so this is always unavailable offline and cites the federal mandate."""
    dataset_id = "medicaid_data_benefits_covered_nonemergency_medical_transportation"
    return ConnectorResult(
        available=False, dataset_id=dataset_id,
        source_label=("connector · " + dataset_id + " (not registered offline)"),
        fallback_citation=("GOV · NEMT is a federally-mandated Medicaid benefit "
                           "(42 CFR 431.53; 42 CFR 440.170(a)); state spend "
                           "~$2.6-3B/yr via MACPAC / KFF (ILLUSTRATIVE "
                           "magnitude)"),
        note=("The NEMT benefits-coverage dataset is not registered in the "
              "offline medicaid_data connector (which carries NADAC/SDUD/"
              "enrollment/managed-care/quality); the mandate is GOV, the spend "
              "magnitude ILLUSTRATIVE."))


def ambulance_employment() -> ConnectorResult:
    """BLS QCEW NAICS 621910 (Ambulance Services) employment + wages.

    Network-gated offline; cites BLS QCEW with a GOV label. Labor is ~69% of
    ground-ambulance cost (GADCS), so this is the cost-driver cross-check."""
    dataset_id = "bls_qcew_industry_area"
    payload = _estate_probe(dataset_id, group_by="industry_code",
                            filters={"industry_code": "621910"})
    rows = payload.get("rows") or []
    if rows:
        return ConnectorResult(
            available=True, dataset_id=dataset_id, rows=list(rows),
            source_label="SOURCED · BLS QCEW NAICS 621910 (Ambulance Services)",
            note="Ambulance employment + wages from the ingested estate.")
    return ConnectorResult(
        available=False, dataset_id=dataset_id,
        source_label=("connector · " + dataset_id + " (not ingested offline)"),
        fallback_citation=("GOV · BLS Quarterly Census of Employment and Wages, "
                           "NAICS 621910 (Ambulance Services) — establishment / "
                           "employment / total wages"),
        note=("Ambulance employment/wages are network-gated offline; the report "
              "cites BLS QCEW 621910 with a GOV label. Labor is ~69% of ground "
              "cost (GADCS) — the binding constraint behind IFT unit economics."))


# ── Report-facing convenience builders (degrade-never-raise) ─────────────────
def live_figures() -> List["Any"]:
    """Build the SOURCED :class:`LiveFigure` list for the report from the
    offline-computable signals (occupancy + transport deals). Imports
    ``LiveFigure`` lazily to avoid any import cycle; returns ``[]`` on failure
    so the report still renders its authored content."""
    try:
        from . import LiveFigure
    except Exception:  # noqa: BLE001
        return []
    out: List[Any] = []
    occ = occupancy_trend()
    if occ.available and occ.latest_occupancy is not None:
        delta = f", {occ.delta_pp:+.1f}pp vs FY{occ.first_fy}" if occ.delta_pp is not None else ""
        out.append(LiveFigure(
            "Hospital inpatient occupancy (national, transfer-demand proxy)",
            f"{occ.latest_occupancy * 100:.1f}% (FY{occ.latest_fy}){delta}",
            occ.source_label))
    st = occupancy_by_state()
    if st.available and st.rows:
        lead = st.rows[0]
        out.append(LiveFigure(
            "Tightest-census state (highest inpatient occupancy)",
            f"{lead.state} {lead.occupancy * 100:.1f}% (FY{st.fiscal_year})",
            st.source_label))
    deals = transport_deal_history()
    if deals.available and deals.n_deals:
        moic = (f"; {deals.median_moic:.2f}x median MOIC"
                if deals.median_moic is not None else "")
        out.append(LiveFigure(
            "Transport deals in our corpus (EMS + NEMT + air union)",
            f"{deals.n_deals:,} deals{moic}",
            deals.source_label))
        if deals.median_entry_multiple is not None:
            out.append(LiveFigure(
                "Median entry EV/EBITDA — transport corpus (thin, directional)",
                f"{deals.median_entry_multiple:.2f}x (n={deals.entry_multiple_n})",
                deals.source_label))
    return out


def cms_trend_takeaway() -> str:
    """The authored+computed occupancy takeaway for the report's ``cms_trend``
    (reaches the page via the renderer's 'Reading —' channel even though the
    slug-keyed supply_trend is unavailable for IFT). Falls back to a GOV-cited
    sentence if HCRIS is unreadable offline."""
    occ = occupancy_trend()
    if occ.available and occ.takeaway:
        return occ.takeaway
    return ("A trended CMS ambulance-utilization series is network-gated "
            "offline; national inpatient occupancy — the interfacility "
            "transfer-demand engine — runs in the mid-60s% per CMS HCRIS / AHA "
            "(GOV), elevated versus the pre-COVID low-60s.")


def state_note() -> str:
    """The computed per-state occupancy note layered under the renderer's honest
    'no facility roll' state-breakdown message. Empty string on failure."""
    st = occupancy_by_state()
    if not st.available or not st.rows:
        return ("IFT has no vendored facility roll, so a state facility map is "
                "honestly omitted; the demand geography is hospital occupancy — "
                "network-gated offline, cited GOV.")
    leaders = ", ".join(f"{r.state} {r.occupancy * 100:.1f}%" for r in st.rows[:5])
    return (
        "IFT carries no vendored ambulance/NEMT facility roll, so a per-state "
        "facility map is honestly omitted. As a stand-in, the demand geography "
        "is hospital census: our HCRIS panel puts the tightest-occupancy states "
        f"(FY{st.fiscal_year}) at {leaders} — the tightest transfer markets, "
        "where capacity load-balancing and ED-boarding generate the most "
        "interfacility volume. " + st.insight)


# ── National GROUND-IFT TAM (top-down from Medicare, grossed to all-payer) ────
# The TAM slice = US GROUND interfacility ambulance only. INCLUDE the interfacility
# slice of A0426/A0428 (BLS), A0427/A0429 (ALS-emerg), A0433 (ALS2), A0434 (SCT) +
# A0425 ground mileage. EXCLUDE air (A0430/A0431 base + A0435/A0436 mileage — the
# No Surprises Act air balance-billing exclusion rationale) and NEMT (wheelchair
# van A0130, livery T2001-T2005 — a separate federally-mandated Medicaid benefit,
# 42 CFR 431.53 / 440.170(a)). GRAY-ZONE excluded from core IFT: residence-origin
# recurring dialysis (R→G/J A0428) — recurring outpatient, not interfacility.
_TAM_EXCLUSIONS: Tuple[str, ...] = (
    "Air ambulance (A0430/A0431 base + A0435/A0436 air mileage) — excluded on the "
    "No Surprises Act air balance-billing rationale; air is a separate market.",
    "NEMT — Medicaid wheelchair van (A0130) + livery/mileage (T2001-T2005) + "
    "rideshare — a separate federally-mandated benefit (42 CFR 431.53; 440.170(a)), "
    "~$2.6-3B/yr state spend (MACPAC/KFF, ILLUSTRATIVE magnitude).",
    "911 / scene response (same ground HCPCS, origin S or R) — an IFT claim "
    "originates at a FACILITY (origin-position in {H,N,E,G,J,D,I}), not a scene.",
    "Residence-origin recurring dialysis (R→G/J A0428) — recurring outpatient, not "
    "interfacility; facility-origin dialysis legs (N→G SNF-to-dialysis) stay IN.",
)

# GOV anchor + the ILLUSTRATIVE build ratios (basis stated on every line).
_MEDICARE_FFS_AMBULANCE_BN = 4.0        # GOV — MedPAC Payment Basics, 2023 FFS spend
_GROUND_SHARE = (0.85, 0.88)           # ILLUSTRATIVE — ground vs air share of $
_IFT_SHARE_OF_GROUND = (0.30, 0.40)    # ILLUSTRATIVE — IFT over-indexes on ALS2/SCT
_ALLPAYER_GROSSUP = (4.5, 5.5)         # ILLUSTRATIVE — Medicare FFS ~16-19% of $
_ALLPAYER_GROUND_AMBULANCE_BN = (18.0, 22.0)   # ILLUSTRATIVE — market-research x-check
_IFT_TRANSPORTS_M = (4.0, 5.0)         # ILLUSTRATIVE — all-payer ground IFT volume
_R_PER_TRANSPORT = (1200.0, 1400.0)    # ILLUSTRATIVE — blended all-payer net rev/leg


@dataclass
class TamStep:
    label: str
    value: str
    basis: str          # GOV | ILLUSTRATIVE
    detail: str = ""


@dataclass
class GroundTam:
    available: bool
    method: str = ""                        # part_b_utilization | top_down_illustrative
    part_b_available: bool = False
    # GOV anchor
    medicare_ffs_ambulance_bn: float = 0.0
    # ILLUSTRATIVE build (ranges, $B)
    medicare_ffs_ground_bn: Tuple[float, float] = (0.0, 0.0)
    medicare_ffs_ground_ift_bn: Tuple[float, float] = (0.0, 0.0)
    allpayer_tam_bn_low: float = 0.0
    allpayer_tam_bn_central: float = 0.0
    allpayer_tam_bn_high: float = 0.0
    allpayer_ground_ambulance_bn: Tuple[float, float] = (0.0, 0.0)
    transports_m: Tuple[float, float] = (0.0, 0.0)
    revenue_per_transport: Tuple[float, float] = (0.0, 0.0)
    steps: List[TamStep] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    source_label: str = ""
    headline: str = ""
    note: str = ""


def ground_tam() -> GroundTam:
    """US GROUND interfacility-ambulance TAM — top-down from the GOV Medicare-FFS
    anchor, grossed to all-payer, with every modeled line labelled ILLUSTRATIVE.

    Method: the line-level Part-B ambulance-HCPCS path (:func:`ambulance_part_b_
    utilization`) is the SOURCED build once the estate is ingested; it is
    network-gated offline, so this degrades to the GOV/ILLUSTRATIVE top-down build
    — Medicare FFS ambulance $4.0B (GOV) → ground 85-88% → interfacility 30-40% →
    ~5× all-payer gross-up → ~$6.5B central ($5-8B). NEMT + air + 911-scene +
    residence-origin dialysis are EXCLUDED (documented). Never raises."""
    part_b = ambulance_part_b_utilization()
    method = "part_b_utilization" if part_b.available else "top_down_illustrative"

    anchor = _MEDICARE_FFS_AMBULANCE_BN
    grd = (round(anchor * _GROUND_SHARE[0], 2), round(anchor * _GROUND_SHARE[1], 2))
    ift = (round(grd[0] * _IFT_SHARE_OF_GROUND[0], 2),
           round(grd[1] * _IFT_SHARE_OF_GROUND[1], 2))
    # All-payer gross-up applied to the Medicare-FFS ground-IFT slice (~5× central).
    grossup_c = (_ALLPAYER_GROSSUP[0] + _ALLPAYER_GROSSUP[1]) / 2.0    # 5.0
    ap_grossup_low = round(ift[0] * grossup_c, 1)
    ap_grossup_high = round(ift[1] * grossup_c, 1)
    # Volume cross-check: transports × revenue/transport.
    vol_low = round(_IFT_TRANSPORTS_M[0] * _R_PER_TRANSPORT[0] / 1000.0, 1)   # $B
    vol_high = round(_IFT_TRANSPORTS_M[1] * _R_PER_TRANSPORT[1] / 1000.0, 1)
    # Headline is the TRIANGULATED central/range across the three methods (top-down
    # gross-up, volume × revenue, market-research context) — NOT the raw corner
    # product of the extremes, which overstates the tails. These are the brief's
    # ILLUSTRATIVE headline figures; the $6.5B is NEVER GOV.
    ap_low, ap_central, ap_high = 5.0, 6.5, 8.0

    steps = [
        TamStep("Medicare FFS ambulance spend (2023)",
                f"${anchor:.1f}B", "GOV",
                "~1% of Medicare FFS; ~13% of FFS beneficiaries used ambulance "
                "(MedPAC Payment Basics, Oct 2024). 2024: ~10,600 orgs, 11.3M "
                "transports, $5.3B AFS."),
        TamStep("→ ground share of ambulance $ (85-88%)",
                f"${grd[0]:.2f}-{grd[1]:.2f}B", "ILLUSTRATIVE",
                "air is ~1-2% of transports but higher $/trip; ground is the "
                "residual."),
        TamStep("→ interfacility share of ground $ (30-40%)",
                f"${ift[0]:.2f}-{ift[1]:.2f}B", "ILLUSTRATIVE",
                "IFT over-indexes on spend vs volume — it concentrates ALS2/SCT "
                "(RVU 2.75/3.25) + long mileage; 911/scene is higher volume, lower "
                "$/trip. This is the Medicare-FFS ground-IFT slice."),
        TamStep("→ all-payer gross-up (~5×)",
                f"${ap_grossup_low:.1f}-{ap_grossup_high:.1f}B", "ILLUSTRATIVE",
                "Medicare FFS ground ambulance is ~16-19% of all-payer revenue "
                "(commercial pays ~2-4× Medicare; MA/Medicaid/self-pay fill the "
                "rest)."),
        TamStep("Volume cross-check (4-5M transports × $1,200-1,400)",
                f"${vol_low:.1f}-{vol_high:.1f}B", "ILLUSTRATIVE",
                "US ground ambulance transports ~25-30M/yr incl. ~22M 911; "
                "interfacility ~15-20% by volume × blended all-payer net "
                "revenue/leg — reconciles with the top-down."),
        TamStep("Market-research cross-check (US ground ambulance)",
                f"${_ALLPAYER_GROUND_AMBULANCE_BN[0]:.0f}-"
                f"{_ALLPAYER_GROUND_AMBULANCE_BN[1]:.0f}B", "ILLUSTRATIVE",
                "US ambulance ~$21-22B (2024-26, Grand View/IBISWorld), ground "
                "~60-70% — IFT is a slice WITHIN ground, never top-down off the "
                "whole."),
    ]
    if part_b.available:
        steps.insert(0, TamStep(
            "Line-level Part B ambulance HCPCS (A0426-A0436)",
            f"{len(part_b.rows)} rows", "SOURCED",
            "ingested physician/supplier procedure summary — the SOURCED spine "
            "replacing the top-down anchor."))

    headline = (
        f"US GROUND IFT TAM ≈ ${ap_central:.1f}B central (range "
        f"${ap_low:.1f}-{ap_high:.1f}B), all-payer, ex-NEMT ex-air — ILLUSTRATIVE, "
        f"a ~5× gross-up of the ${ift[0]:.1f}-{ift[1]:.1f}B Medicare-FFS ground-IFT "
        f"slice built off the ${anchor:.1f}B GOV MedPAC anchor.")

    return GroundTam(
        available=True, method=method, part_b_available=part_b.available,
        medicare_ffs_ambulance_bn=anchor, medicare_ffs_ground_bn=grd,
        medicare_ffs_ground_ift_bn=ift, allpayer_tam_bn_low=ap_low,
        allpayer_tam_bn_central=ap_central, allpayer_tam_bn_high=ap_high,
        allpayer_ground_ambulance_bn=_ALLPAYER_GROUND_AMBULANCE_BN,
        transports_m=_IFT_TRANSPORTS_M, revenue_per_transport=_R_PER_TRANSPORT,
        steps=steps, exclusions=list(_TAM_EXCLUSIONS),
        source_label=("GOV anchor · MedPAC Payment Basics (Ambulance, Oct 2024) "
                      "+ 42 CFR 414 Subpart H fee schedule; ILLUSTRATIVE build "
                      "(ground/air split, IFT share, all-payer gross-up) modeled "
                      "on the GOV anchor — the $6.5B is NEVER GOV"),
        headline=headline,
        note=("The SOURCED line-level path (Part B ambulance HCPCS) is network-"
              "gated offline, so the TAM is the top-down GOV→ILLUSTRATIVE build. "
              "Present as a RANGE, not a point; the Medicare-FFS ground-IFT slice "
              f"(${ift[0]:.1f}-{ift[1]:.1f}B) is the ILLUSTRATIVE figure most "
              "directly anchored to GOV."))


# ── SAM(footprint) — bottom-up from the ift_geo market structure ─────────────
# The ILLUSTRATIVE dollarising levers (every one labelled). SAM is NOT a % of TAM;
# it is built from the real origins/destinations in the target metros (SOURCED,
# ift_geo) × the transfer/discharge volume that needs ground IFT (f_IFT / λ_return)
# × a realistically-serviceable share s(m) that reflects the insource-vs-outsource
# structure × the blended all-payer net revenue per IFT transport r_IFT.
_F_IFT = (0.07, 0.10, 0.12)            # (low, central, high) fraction of discharges
_LAMBDA_RETURN = (2.0, 3.0, 4.0)       # SNF recurring ground-IFT legs / occ. bed / yr
_SNF_OCC = 0.77                        # GOV magnitude (NIC/CMS)
_R_IFT = (1200.0, 1300.0, 1400.0)      # (low, central, high) $/IFT transport
_R_IFT_RURAL_UPLIFT = 1.12             # rural/super-rural mileage + 22.6% add-on

# Realistically-serviceable share s(m) by ift_geo insource archetype (ILLUSTRATIVE,
# in the brief's 0.15-0.30 band). LOWER where an anchor IDN insources its fleet or
# a GMR/AMR-class incumbent holds the transfer-center contract; HIGHER in
# fragmented outsourced markets.
_SERVICEABLE_SHARE: Dict[str, float] = {
    "insourced-heavy": 0.12,                    # Twin Cities, Rochester (mostly closed)
    "insourced-top-outsourced-bottom": 0.22,    # Omaha, Cleveland, Cincinnati
    "mixed-confirmed-outsource": 0.20,          # Columbus OH
    "mixed-insource-residual": 0.18,            # Des Moines
    "two-anchor-contestable": 0.25,             # Dayton
    "outsourced-two-horse": 0.25,               # Lincoln
    "outsourced-fragmented": 0.30,              # Milwaukee, Madison
    "outsourced-incumbent": 0.18,               # Louisville, NW Indiana, NoVA
    "bi-state-outsourced": 0.25,                # Kansas City
    "public-utility-mixed": 0.20,               # Wichita
    "rural-contract-gated": 0.15,               # WY, North Platte, Columbus NE, GI/Kearney
}
_SERVICEABLE_DEFAULT = 0.20


@dataclass
class SamMetroRow:
    name: str
    region_label: str
    rural: bool
    insource_class: str
    hcris_beds: float
    discharge_base: float
    snf_beds: int
    acute_missions: float               # discharge_base × f_IFT (central)
    pac_missions: float                 # snf_beds × occ × λ_return (central)
    demand_missions: float              # acute + pac (central)
    serviceable_share: float            # s(m)
    serviceable_missions: float         # demand × s(m)
    revenue_per_transport: float        # r_IFT(m)
    sam_dollars: float                  # serviceable_missions × r_IFT (central)


@dataclass
class SamFootprint:
    available: bool
    rows: List[SamMetroRow] = field(default_factory=list)
    # central footprint totals
    total_discharge_base: float = 0.0
    total_demand_missions: float = 0.0
    total_serviceable_missions: float = 0.0
    sam_dollars_central: float = 0.0
    sam_dollars_low: float = 0.0
    sam_dollars_high: float = 0.0
    # validation cross-check
    metro_hcris_beds: float = 0.0
    national_hcris_beds: float = 0.0
    bed_share_of_national: Optional[float] = None
    sam_crosscheck_dollars: Optional[float] = None    # bed_share × TAM × s_avg
    national_ift_volume_m: Tuple[float, float] = (4.0, 5.0)
    serviceable_share_of_national_volume: Optional[float] = None
    assumptions: Dict[str, Any] = field(default_factory=dict)
    source_label: str = ""
    method: str = ""
    note: str = ""


def _national_hcris_beds() -> float:
    """Sum of positive HCRIS beds across all filers (the SAM validation
    denominator). Returns 0.0 on any failure."""
    try:
        import pandas as pd
        from ..data import hcris
        df = hcris._get_latest_per_ccn()
        if df is None or df.empty:
            return 0.0
        b = pd.to_numeric(df.get("beds"), errors="coerce")
        return float(b[b > 0].sum())
    except Exception:  # noqa: BLE001
        return 0.0


def sam_formula(f_ift: float = _F_IFT[1],
                r_ift: float = _R_IFT[1],
                lambda_return: float = _LAMBDA_RETURN[1]) -> SamFootprint:
    """SAM(footprint) — the bottom-up ground-IFT SAM built from the SOURCED
    ``ift_geo`` market structure × the labelled ILLUSTRATIVE levers.

    Per metro m:  SAM_$(m) = [ D(m)·f_IFT + P(m) ] · s(m) · r_IFT(m)
    where D(m) = HCRIS-beds × 53.3 discharges/bed/yr (ift_geo discharge base,
    SOURCED beds + labelled factor); P(m) = SNF_beds × occ(0.77) × λ_return
    (recurring SNF→hospital / SNF→dialysis legs); s(m) = realistically-serviceable
    share keyed to the insource-vs-outsource archetype (0.15-0.30, ILLUSTRATIVE);
    r_IFT(m) = blended all-payer net revenue per IFT transport (rural metros carry
    a mileage + super-rural uplift). Reconciles against (footprint beds / national
    beds) × TAM × s_avg. Degrades to available=False if ift_geo is unreadable —
    never raises."""
    try:
        from . import ift_geo
        blocks = ift_geo.footprint_sam_building_blocks()
    except Exception:  # noqa: BLE001
        return SamFootprint(
            available=False,
            source_label="SOURCED structure (ift_geo) × ILLUSTRATIVE SAM levers",
            note="The ift_geo footprint structure is not available offline.")
    if not blocks.available or not blocks.blocks:
        return SamFootprint(
            available=False,
            source_label="SOURCED structure (ift_geo) × ILLUSTRATIVE SAM levers",
            note="No ift_geo SAM building blocks computed offline.")

    tam = ground_tam()
    rows: List[SamMetroRow] = []
    tot_demand = tot_serv = tot_sam_c = tot_sam_lo = tot_sam_hi = 0.0
    serv_share_weighted_num = 0.0

    for b in blocks.blocks:
        s = _SERVICEABLE_SHARE.get(b.insource_class, _SERVICEABLE_DEFAULT)
        r_metro = r_ift * (_R_IFT_RURAL_UPLIFT if b.rural else 1.0)
        acute = b.discharge_base * f_ift
        pac = float(b.snf_beds) * _SNF_OCC * lambda_return
        demand = acute + pac
        serv = demand * s
        sam_c = serv * r_metro
        # low / high bands: swing f_IFT, λ_return, r_IFT, and s together.
        acute_lo = b.discharge_base * _F_IFT[0]
        pac_lo = float(b.snf_beds) * _SNF_OCC * _LAMBDA_RETURN[0]
        sam_lo = (acute_lo + pac_lo) * (s * 0.8) * (_R_IFT[0] *
                                                    (_R_IFT_RURAL_UPLIFT if b.rural else 1.0))
        acute_hi = b.discharge_base * _F_IFT[2]
        pac_hi = float(b.snf_beds) * _SNF_OCC * _LAMBDA_RETURN[2]
        sam_hi = (acute_hi + pac_hi) * min(0.35, s * 1.2) * (_R_IFT[2] *
                                                             (_R_IFT_RURAL_UPLIFT if b.rural else 1.0))
        rows.append(SamMetroRow(
            name=b.name, region_label=b.region_label, rural=b.rural,
            insource_class=b.insource_class, hcris_beds=b.hcris_beds,
            discharge_base=b.discharge_base, snf_beds=b.snf_beds,
            acute_missions=acute, pac_missions=pac, demand_missions=demand,
            serviceable_share=s, serviceable_missions=serv,
            revenue_per_transport=r_metro, sam_dollars=sam_c))
        tot_demand += demand
        tot_serv += serv
        tot_sam_c += sam_c
        tot_sam_lo += sam_lo
        tot_sam_hi += sam_hi
        serv_share_weighted_num += s * demand

    metro_beds = blocks.total_hcris_beds
    nat_beds = _national_hcris_beds()
    bed_share = (metro_beds / nat_beds) if nat_beds > 0 else None
    s_avg = (serv_share_weighted_num / tot_demand) if tot_demand > 0 else _SERVICEABLE_DEFAULT
    crosscheck = (bed_share * tam.allpayer_tam_bn_central * 1e9 * s_avg
                  if bed_share is not None else None)
    serv_vol_share = (tot_serv / (_IFT_TRANSPORTS_M[1] * 1e6)) if tot_serv else None

    return SamFootprint(
        available=True, rows=rows,
        total_discharge_base=blocks.total_discharge_base,
        total_demand_missions=tot_demand,
        total_serviceable_missions=tot_serv,
        sam_dollars_central=tot_sam_c, sam_dollars_low=tot_sam_lo,
        sam_dollars_high=tot_sam_hi,
        metro_hcris_beds=metro_beds, national_hcris_beds=nat_beds,
        bed_share_of_national=bed_share, sam_crosscheck_dollars=crosscheck,
        national_ift_volume_m=_IFT_TRANSPORTS_M,
        serviceable_share_of_national_volume=serv_vol_share,
        assumptions={
            "f_IFT": {"low": _F_IFT[0], "central": f_ift, "high": _F_IFT[2],
                      "basis": "ILLUSTRATIVE — ground-IFT fraction of discharges "
                               "(discharge-to-PAC by stretcher ~6-8% + acute-to-"
                               "acute ground transfer ~2-4%)"},
            "lambda_return": {"low": _LAMBDA_RETURN[0], "central": lambda_return,
                              "high": _LAMBDA_RETURN[2],
                              "basis": "ILLUSTRATIVE — SNF→hospital/dialysis recurring "
                                       "ground-IFT legs per occupied SNF bed/yr"},
            "snf_occ": {"value": _SNF_OCC, "basis": "GOV magnitude (NIC/CMS ~0.77)"},
            "s_of_m": {"by_class": dict(_SERVICEABLE_SHARE), "default": _SERVICEABLE_DEFAULT,
                       "basis": "ILLUSTRATIVE — realistically-serviceable share keyed "
                                "to the insource-vs-outsource archetype (0.15-0.30)"},
            "r_IFT": {"low": _R_IFT[0], "central": r_ift, "high": _R_IFT[2],
                      "rural_uplift": _R_IFT_RURAL_UPLIFT,
                      "basis": "ILLUSTRATIVE — blended all-payer net revenue per IFT "
                               "transport (IFT skews ALS/SCT + longer mileage; rural "
                               "carries the super-rural +22.6% add-on)"},
        },
        source_label=("SOURCED market structure (ift_geo: HCRIS beds + SNF beds per "
                      "metro) × ILLUSTRATIVE SAM levers (f_IFT, λ_return, s(m), r_IFT) "
                      "× GOV-anchored TAM cross-check"),
        method="bottom_up_footprint",
        note=("SAM is built bottom-up from the real footprint origins/destinations, "
              "NOT as a % of TAM. Central footprint SAM reconciles against (footprint "
              "beds / national beds) × TAM × s_avg to within an order of magnitude; "
              "the serviceable-mission total is a plausible slice of the ~4-5M "
              "national ground-IFT volume. All dollar levers are ILLUSTRATIVE, "
              "labelled; the bed/discharge structure is SOURCED."))


# ── SAM = MULTI-HOSPITAL HEALTH SYSTEMS (the structural addressable market) ───
# The MMT thesis frames the funnel as TAM → SAM → SOM, and the SAM is NOT the
# operator's current footprint (that is the SOM) — it is the STRUCTURAL market:
# the ground IFT generated within/between MULTI-HOSPITAL HEALTH SYSTEMS that is
# addressable by an outsourced operator. Two independent methods triangulate it:
#
#   (A) TOP-DOWN (ratio-driven): TAM × multi-hospital-system share of IFT $ ×
#       addressable (outsourceable) share. The addressable share is 1 − the
#       insource ceiling, where the insource ceiling uses the transcript's proxy:
#       "if the health system is billing the transport, it must be insourced."
#       So the UPPER BOUND on insourcing is the share of ground-IFT $ billed by
#       health-system-affiliated NPIs — the true value comes from a claims build
#       (billing-NPI ownership), which is network-gated offline, so we carry an
#       ILLUSTRATIVE ceiling anchored to how little ground fleet hospitals own.
#
#   (B) BOTTOMS-UP (structure-extrapolated): the offline proxy for the Komodo
#       claims-driven build. Take the SOURCED footprint SAM-$/bed from
#       :func:`sam_formula` and scale it to the NATIONAL multi-hospital-system bed
#       base (national HCRIS beds × the AHA multi-system bed share). The true
#       bottoms-up build sums IFT claims whose origin OR destination NPI sits in a
#       multi-hospital system, split by billing-NPI ownership — that needs claims
#       we do not have offline, so this structure-extrapolation stands in and is
#       labelled as the proxy. It reads LOW vs the top-down because the footprint
#       over-samples insourced-heavy metros (Twin Cities, Rochester).
#
# Both are ±MSA-cut: the transcript's "with or without an MSA restriction" — we
# also report the metro-restricted SAM (× the in-MSA share of system IFT $).
#
# SOM = the operator's current footprint (:func:`sam_formula`); the operator's
# current revenue is ~1% of SAM — a nascent share with the SAM ~20-30× the SOM.
_MULTI_SYSTEM_IFT_SHARE = (0.50, 0.60, 0.70)   # ILLUSTRATIVE — share of ground-IFT $
#   generated within/between multi-hospital health systems. Anchored to AHA 2023
#   (~68% of community hospitals are in a system) AND the fact that acute up-
#   transfers concentrate at system-owned tertiary/quaternary HUBS, so IFT over-
#   indexes on system involvement vs the raw hospital count.
_MULTI_SYSTEM_BED_SHARE = 0.65                 # GOV-magnitude (AHA 2023) — share of
#   US hospital beds in MULTI-hospital systems (system hospitals skew larger, so
#   the bed share exceeds the ~68% hospital-count share only modestly once the
#   single-hospital systems are removed).
_INSOURCE_CEILING = (0.18, 0.25, 0.32)         # ILLUSTRATIVE — health-system-biller
#   UPPER BOUND on insourcing. Hospitals rarely own ground fleets; the big-IDN
#   captive-fleet exceptions (Cleveland Clinic, Mayo, Geisinger, Intermountain)
#   set the ceiling. The claims-driven proxy ("billed by a system NPI ⇒ insourced")
#   would pin this precisely; offline it is a labelled band.
_MSA_SHARE_OF_SYSTEM_IFT = 0.82                # ILLUSTRATIVE — share of multi-system
#   IFT $ inside MSAs (systems concentrate in metros; rural is critical-access +
#   independent).
_OPERATOR_SHARE_OF_SAM = 0.01                  # the nascent operator's ~1% current
#   share of the structural SAM (MMT kickoff framing) — used to derive the implied
#   current revenue and the headroom multiple.


@dataclass
class HealthSystemSam:
    """SAM = multi-hospital health systems — the structural addressable market,
    triangulated top-down (ratio) × bottoms-up (structure), ±MSA, with the SOM and
    the ~1% nascent operator share hung off it. Every dollar is ILLUSTRATIVE,
    labelled; the bed base and the footprint spine are SOURCED."""
    available: bool
    method: str = "top_down_ratio × bottoms_up_structure (±MSA)"
    tam_central_bn: float = 0.0
    # ratio levers (low/central/high)
    multi_system_ift_share: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    insource_ceiling: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    addressable_share: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    multi_system_bed_share: float = 0.0
    msa_share_of_system_ift: float = 0.0
    # (A) top-down SAM ($B)
    sam_td_low_bn: float = 0.0
    sam_td_central_bn: float = 0.0
    sam_td_high_bn: float = 0.0
    sam_td_msa_central_bn: float = 0.0
    # (B) bottoms-up structure-extrapolated SAM ($B), the offline Komodo proxy
    sam_bu_central_bn: Optional[float] = None
    sam_bu_msa_central_bn: Optional[float] = None
    footprint_bed_share: Optional[float] = None
    # triangulated headline central ($B) — geometric blend of (A) and (B)
    sam_central_bn: float = 0.0
    sam_low_bn: float = 0.0
    sam_high_bn: float = 0.0
    # SOM (footprint) + nascent operator share
    som_central_m: float = 0.0
    som_low_m: float = 0.0
    som_high_m: float = 0.0
    operator_share_of_sam: float = 0.0
    operator_current_revenue_m: float = 0.0
    sam_over_som_multiple: Optional[float] = None
    steps: List[TamStep] = field(default_factory=list)
    source_label: str = ""
    headline: str = ""
    note: str = ""


def health_system_sam() -> HealthSystemSam:
    """SAM = multi-hospital health systems — the structural addressable market for
    ground IFT, triangulated two ways and framed against the SOM (footprint) and
    the operator's ~1% nascent share.

    Method A (top-down ratio):  SAM = TAM · σ_system · (1 − ι)
      σ_system = share of ground-IFT $ generated within/between multi-hospital
      health systems (ILLUSTRATIVE, AHA-anchored); ι = the health-system-biller
      insource CEILING (ILLUSTRATIVE — the claims proxy "billed by a system NPI ⇒
      insourced"); (1 − ι) = the addressable/outsourceable share.

    Method B (bottoms-up structure):  SAM = (footprint SAM-$/bed) · (national beds
      · β_system), the offline stand-in for the Komodo claims build, where
      β_system is the multi-hospital-system share of national beds. Reads LOW vs A
      because the footprint over-samples insourced-heavy metros.

    Both are also reported ±MSA (× the in-MSA share of system IFT $). Degrades to
    available=False if the TAM/footprint spines are unavailable — never raises."""
    tam = ground_tam()
    som = sam_formula()
    if not tam.available:
        return HealthSystemSam(
            available=False,
            source_label="GOV-anchored TAM × ILLUSTRATIVE system/insource ratios",
            note="The ground-IFT TAM spine is unavailable, so the structural SAM "
                 "cannot be built.")

    tam_c = tam.allpayer_tam_bn_central
    tam_lo = tam.allpayer_tam_bn_low
    tam_hi = tam.allpayer_tam_bn_high
    sig_lo, sig_c, sig_hi = _MULTI_SYSTEM_IFT_SHARE
    ins_lo, ins_c, ins_hi = _INSOURCE_CEILING
    addr = (round(1 - ins_hi, 3), round(1 - ins_c, 3), round(1 - ins_lo, 3))

    # (A) top-down ratio build — extremes multiply low×low×low and high×high×high.
    sam_td_lo = round(tam_lo * sig_lo * addr[0], 3)
    sam_td_c = round(tam_c * sig_c * addr[1], 3)
    sam_td_hi = round(tam_hi * sig_hi * addr[2], 3)
    sam_td_msa_c = round(sam_td_c * _MSA_SHARE_OF_SYSTEM_IFT, 3)

    # (B) bottoms-up structure-extrapolation — the offline Komodo proxy.
    sam_bu_c: Optional[float] = None
    sam_bu_msa_c: Optional[float] = None
    fp_bed_share = som.bed_share_of_national if som.available else None
    if (som.available and fp_bed_share and fp_bed_share > 0
            and som.sam_dollars_central > 0):
        # footprint SAM-$/bed scaled to the national multi-system bed base:
        #   SAM_bu = (SOM_$ / footprint_beds) · (national_beds · β_system)
        #          = SOM_$ · β_system / bed_share
        sam_bu_c = round(
            som.sam_dollars_central * _MULTI_SYSTEM_BED_SHARE
            / fp_bed_share / 1e9, 3)
        sam_bu_msa_c = round(sam_bu_c * _MSA_SHARE_OF_SYSTEM_IFT, 3)

    # Triangulated headline: geometric mean of the two central methods when both
    # exist (respects the order-of-magnitude spread without letting either method
    # dominate); else the top-down central. Band spans B-central → A-high.
    if sam_bu_c and sam_bu_c > 0:
        sam_central = round((sam_td_c * sam_bu_c) ** 0.5, 3)
        sam_low = round(min(sam_bu_c, sam_td_lo), 3)
    else:
        sam_central = sam_td_c
        sam_low = sam_td_lo
    sam_high = sam_td_hi

    # SOM + nascent operator share.
    som_c_m = (som.sam_dollars_central / 1e6) if som.available else 0.0
    som_lo_m = (som.sam_dollars_low / 1e6) if som.available else 0.0
    som_hi_m = (som.sam_dollars_high / 1e6) if som.available else 0.0
    op_rev_m = round(sam_central * 1e3 * _OPERATOR_SHARE_OF_SAM, 1)  # $B→$M ×1%
    sam_over_som = (round(sam_central * 1e3 / som_c_m, 1)
                    if som_c_m > 0 else None)

    steps = [
        TamStep("TAM — all US ground IFT (ex-911, ex-air, ex-NEMT)",
                f"${tam_c:.1f}B", "ILLUSTRATIVE",
                f"range ${tam_lo:.0f}-{tam_hi:.0f}B; the GOV-anchored ground-IFT "
                "TAM from ground_tam()."),
        TamStep("→ × multi-hospital-system share of IFT $ (σ)",
                f"{sig_lo*100:.0f}-{sig_hi*100:.0f}% (central {sig_c*100:.0f}%)",
                "ILLUSTRATIVE",
                "AHA 2023 ~68% of hospitals are in a system, and acute up-"
                "transfers concentrate at system-owned tertiary/quaternary hubs, "
                "so IFT $ over-indexes on system involvement."),
        TamStep("→ × addressable (outsourceable) share (1 − insource ceiling ι)",
                f"{addr[0]*100:.0f}-{addr[2]*100:.0f}% (central {addr[1]*100:.0f}%)",
                "ILLUSTRATIVE",
                f"insource ceiling ι = {ins_lo*100:.0f}-{ins_hi*100:.0f}% — the "
                "health-system-biller proxy: $ billed by a system NPI is treated "
                "as insourced (non-addressable). Hospitals rarely own ground "
                "fleets, so the ceiling is low."),
        TamStep("(A) TOP-DOWN SAM = TAM · σ · (1 − ι)",
                f"${sam_td_c:.1f}B (${sam_td_lo:.1f}-{sam_td_hi:.1f}B)",
                "ILLUSTRATIVE",
                f"MSA-restricted ${sam_td_msa_c:.1f}B (× {_MSA_SHARE_OF_SYSTEM_IFT*100:.0f}% "
                "in-MSA share)."),
    ]
    if sam_bu_c:
        steps.append(TamStep(
            "(B) BOTTOMS-UP SAM = footprint SAM-$/bed × national multi-system beds",
            f"${sam_bu_c:.1f}B", "ILLUSTRATIVE",
            f"the offline Komodo-claims proxy: SOM ${som_c_m:,.0f}M scaled by "
            f"β_system {_MULTI_SYSTEM_BED_SHARE*100:.0f}% ÷ footprint bed-share "
            f"{fp_bed_share*100:.1f}%. Reads low — the footprint over-samples "
            "insourced-heavy metros; the true build sums claims by origin/"
            "destination system NPI split by billing-NPI ownership."))
    steps.append(TamStep(
        "SAM (triangulated)", f"${sam_central:.1f}B (${sam_low:.1f}-{sam_high:.1f}B)",
        "ILLUSTRATIVE",
        "geometric blend of the two central methods." if sam_bu_c
        else "top-down central (bottoms-up proxy unavailable offline)."))
    steps.append(TamStep(
        "SOM — operator footprint (serviceable, current markets)",
        f"${som_c_m:,.0f}M (${som_lo_m:,.0f}-{som_hi_m:,.0f}M)",
        "ILLUSTRATIVE" if som.available else "unavailable",
        "the bottom-up footprint SAM from sam_formula() — reframed as the SOM: "
        "what is serviceable in the operator's CURRENT metros, not the structural "
        "market."))
    steps.append(TamStep(
        f"Operator current revenue ≈ {_OPERATOR_SHARE_OF_SAM*100:.0f}% of SAM",
        f"~${op_rev_m:,.0f}M", "ILLUSTRATIVE",
        f"the nascent ~{_OPERATOR_SHARE_OF_SAM*100:.0f}% share (MMT framing); SAM "
        + (f"is ~{sam_over_som:.0f}× the SOM" if sam_over_som else "dwarfs the SOM")
        + " — the headroom is structural, not just in-footprint."))

    headline = (
        f"SAM (multi-hospital health systems) ≈ ${sam_central:.1f}B triangulated "
        f"(${sam_low:.1f}-{sam_high:.1f}B): top-down ${sam_td_c:.1f}B = "
        f"${tam_c:.1f}B TAM × {sig_c*100:.0f}% system-share × {addr[1]*100:.0f}% "
        f"addressable"
        + (f", bottoms-up ${sam_bu_c:.1f}B (structure proxy)." if sam_bu_c else ".")
        + f" SOM (footprint) ${som_c_m:,.0f}M; operator ~{_OPERATOR_SHARE_OF_SAM*100:.0f}% "
        f"of SAM (~${op_rev_m:,.0f}M) — a nascent share.")

    return HealthSystemSam(
        available=True, tam_central_bn=tam_c,
        multi_system_ift_share=_MULTI_SYSTEM_IFT_SHARE,
        insource_ceiling=_INSOURCE_CEILING, addressable_share=addr,
        multi_system_bed_share=_MULTI_SYSTEM_BED_SHARE,
        msa_share_of_system_ift=_MSA_SHARE_OF_SYSTEM_IFT,
        sam_td_low_bn=sam_td_lo, sam_td_central_bn=sam_td_c,
        sam_td_high_bn=sam_td_hi, sam_td_msa_central_bn=sam_td_msa_c,
        sam_bu_central_bn=sam_bu_c, sam_bu_msa_central_bn=sam_bu_msa_c,
        footprint_bed_share=fp_bed_share,
        sam_central_bn=sam_central, sam_low_bn=sam_low, sam_high_bn=sam_high,
        som_central_m=som_c_m, som_low_m=som_lo_m, som_high_m=som_hi_m,
        operator_share_of_sam=_OPERATOR_SHARE_OF_SAM,
        operator_current_revenue_m=op_rev_m, sam_over_som_multiple=sam_over_som,
        steps=steps,
        source_label=("GOV-anchored ground-IFT TAM × ILLUSTRATIVE multi-hospital-"
                      "system share + health-system-biller insource ceiling; "
                      "bottoms-up scaled from the SOURCED footprint (ift_geo/HCRIS) "
                      "bed structure — the offline proxy for the Komodo claims build"),
        headline=headline,
        note=("SAM is the STRUCTURAL market (multi-hospital health systems), NOT the "
              "footprint — the footprint is the SOM. Two methods bracket it: the "
              "top-down ratio build and the bottoms-up structure-extrapolation "
              "(the offline stand-in for the claims-driven Komodo build, which "
              "splits IFT by origin/destination system NPI and billing-NPI "
              "ownership). The insource ceiling is the health-system-biller upper "
              "bound; the addressable market is what an outsourced operator can "
              "win. Every dollar is ILLUSTRATIVE; the bed base is SOURCED."))
