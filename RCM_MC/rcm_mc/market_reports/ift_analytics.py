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
