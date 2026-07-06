"""Market Scan — /market-scan. One-input market brief for PE deal work.

Input: a US state (2-letter postal, default TX) and an optional 5-digit
county FIPS. Output: an editorial market brief that stitches together
every relevant public dataset already ingested into the repo-root
connector estate (read through the read-only bridge
``rcm_mc.data_public.connector_estate`` — never a direct
``import connectors``, because that top-level name belongs to the
in-app NPPES package).

Eleven sections, each fed by one or more estate connectors:

  1. Demographics & payor context .... census_acs
  2. Population health burden ........ cdc_data (PLACES county)
  3. Provider shortage ............... hrsa_data (HPSA)
  4. Medicare market ................. cms_open_data (geo variation,
                                       market saturation, enrollment)
  5. Facility quality ................ provider_data (hospital + SNF stars)
  6. Industry money flow ............. open_payments (state totals)
  7. Research footprint .............. nih_reporter (projects)
  8. Compliance exposure ............. oig_leie (LEIE exclusions)
  9. Healthcare labor market ......... bls_qcew (QCEW wages/employment)
 10. Kidney & dialysis market ........ cdc_data (PLACES 2023 county CKD)
                                       + provider_data (dialysis facilities,
                                       state/national averages, ESRD QIP
                                       TPS, ICH-CAHPS state/national)
 11. Outpatient facility universe .... cms_open_data (both POS files,
                                       home infusion) + provider_data
                                       (ASC quality, DMEPOS suppliers)

Every section degrades independently: when its store/table has no rows
for the chosen state it renders a "not ingested" note carrying the exact
per-connector CLI one-liner (flags derived from each connector's cli.py,
not guessed) that would ingest that slice into
``$RCM_MC_CONNECTORS_DB`` (default ``<repo_root>/var/connectors``). The
page must render useful even with zero data — a scan against an empty
estate is a to-do list, not a 500.

Numbers follow house style: $ 2dp, % 1dp, integer counts undecorated.
Every numeric column in the estate is TEXT (the connectors store the
APIs' stringly payloads verbatim), so all numeric ranking/averaging here
parses floats in Python after a bounded adapter query — never a SQL
ORDER BY on a TEXT column, which would sort '9' above '25'.
"""
from __future__ import annotations

import contextlib
import html as _html
import re
from typing import Any

from rcm_mc.data_public import connector_estate as _estate
from rcm_mc.data_public.census_market import STATE_FIPS
from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_bar_row,
    ck_empty_state,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)

_ROUTE = "/market-scan"
_ESTATE_ROUTE = "/connector-estate"

_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

# CDC PLACES measures shown in the health-burden section, in editorial
# order (chronic burden first, then behaviors/access). Ids verified
# against the live PLACES county dataset (33 measure ids as of 2026-07).
_PLACES_MEASURES = [
    ("DIABETES", "Diagnosed diabetes"),
    ("OBESITY", "Obesity"),
    ("BPHIGH", "High blood pressure"),
    ("HIGHCHOL", "High cholesterol"),
    ("CHD", "Coronary heart disease"),
    ("COPD", "COPD"),
    ("DEPRESSION", "Depression"),
    ("CASTHMA", "Current asthma"),
    ("STROKE", "Stroke"),
    ("KIDNEY", "Chronic kidney disease"),
    ("CSMOKING", "Current smoking"),
    ("BINGE", "Binge drinking"),
    ("ACCESS2", "No health insurance (18-64)"),
    ("CHECKUP", "Routine checkup (past yr)"),
    ("GHLTH", "Fair or poor self-rated health"),
    ("CANCER", "Cancer (non-skin)"),
]

# OIG LEIE exclusion statute glosses (42 U.S.C. 1320a-7). The LEIE
# excltype column carries the bare statute cite; partners read the label.
_LEIE_TYPES = {
    "1128a1": "Program-related conviction",
    "1128a2": "Patient abuse or neglect",
    "1128a3": "Felony health-care fraud",
    "1128a4": "Felony controlled-substance conviction",
    "1128b1": "Misdemeanor health-care fraud",
    "1128b2": "Obstruction of an investigation",
    "1128b3": "Misdemeanor controlled-substance conviction",
    "1128b4": "License revocation or surrender",
    "1128b5": "Exclusion/suspension under federal/state program",
    "1128b6": "Excessive claims or unnecessary services",
    "1128b7": "Fraud, kickbacks, or prohibited activities",
    "1128b8": "Entity controlled by excluded individual",
    "1128b14": "Default on health-education loan",
    "1128b15": "Owned/controlled by excluded entity",
    "1128Aa": "CMP law violation",
}

_QCEW_INDUSTRIES = {
    "62": "Health care & social assistance (NAICS 62)",
    "621": "Ambulatory health care (NAICS 621)",
    "622": "Hospitals (NAICS 622)",
    "623": "Nursing & residential care (NAICS 623)",
}

# Provider-category glosses for the two Provider of Services files,
# mirroring the estate's /v1/lookup/facility-universe/{state} handler
# (connectors/cms_open_data/lookup.py — labels verified there against
# live samples 2026-07-06). Hospitals + the clinic categories live in
# the legacy QIES file; everything certified through iQIES (post-2023:
# HHA / SNF / hospice / ASC / ESRD, …) lands in the Internet QIES file
# under its own type-id scheme. Unknown codes render code-labelled
# rather than guessed.
_POS_QIES_CATEGORIES = {
    "01": "Hospital",
    "06": "Psychiatric Residential Treatment Facility",
    "12": "Rural Health Clinic",
    "19": "Community Mental Health Center",
    "21": "Federally Qualified Health Center",
}

_POS_IQIES_TYPES = {
    "3": "Home Health Agency",
    "5": "Portable X-Ray Supplier",
    "6": "Comprehensive Outpatient Rehabilitation Facility",
    "7": "ESRD Facility (dialysis)",
    "8": "ICF/IID",
    "10": "Outpatient Physical Therapy/Speech Pathology",
    "11": "Ambulatory Surgical Center",
    "12": "Hospice",
    "13": "Organ Procurement Organization",
    "20": "Skilled Nursing Facility / Nursing Facility",
}

# State-vs-national comparison columns for the two dialysis averages
# files. Some measures share a column name across both files, others
# suffix _state / _us — pairs verified against the live schemas in
# connectors/provider_data/tables.py (2fpu-cgbb / 2rkq-ygai).
_DIALYSIS_VS_NATIONAL = [
    ("Adult HD patients with Kt/V ≥ 1.2",
     "percentage_of_adult_hd_patients_with_ktv12",
     "percentage_of_adult_hd_patients_with_ktv12"),
    ("Adult PD patients with Kt/V ≥ 1.7",
     "percentage_of_adult_pd_patients_with_ktv17",
     "percentage_of_adult_pd_patients_with_ktv17"),
    ("Long-term catheter in use (90+ days)",
     "percentage_of_adult_patients_with_long_term_catheter_in_use",
     "percentage_of_adult_patients_with_long_term_catheter_in_use"),
    ("Patients with hemoglobin < 10 g/dL",
     "percentage_of_patients_with_hgb10_gdl_state",
     "percentage_of_patients_with_hgb10_gdl_us"),
]

# ICH-CAHPS linearized composite scores (0-100), same column names in
# the state (hanv-ru8h) and national (utgq-v46w) files.
_ICH_CAHPS_MEASURES = [
    ("Nephrologists' communication & caring",
     "linearized_score_of_nephrologists_communication_and_caring"),
    ("Quality of dialysis center care & operations",
     "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9"),
    ("Rating of the nephrologist",
     "linearized_score_of_rating_of_the_nephrologist"),
    ("Rating of the dialysis center staff",
     "linearized_score_of_rating_of_the_dialysis_center_staff"),
    ("Rating of the dialysis facility",
     "linearized_score_of_rating_of_the_dialysis_facility"),
]

# ASC quality measures worth a state-vs-national read (percent-valued;
# the ASC-1..4 per-1,000 event rates are deliberately excluded so the
# whole table formats as house-style percentages).
_ASC_MEASURES = [
    ("ASC-9 Endoscopy — appropriate colonoscopy follow-up",
     "avg_asc9_state_rate", "avg_asc9_nat_rate"),
    ("ASC-11 Cataracts — improved visual function",
     "avg_asc11_state_rate", "avg_asc11_nat_rate"),
    ("ASC-13 Normothermia outcome",
     "avg_asc13_state_rate", "avg_asc13_nat_rate"),
    ("ASC-14 Unplanned anterior vitrectomy",
     "avg_asc14_state_rate", "avg_asc14_nat_rate"),
]


# ── tiny formatting/parsing helpers ─────────────────────────────────────


def _e(x: Any) -> str:
    return _html.escape(str(x if x is not None else ""))


def _clamp_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


def _f(x: Any) -> float | None:
    """Float from the estate's stringly numerics ('2,394,063', '11.06%')."""
    if x is None:
        return None
    s = str(x).strip().replace(",", "").replace("$", "").rstrip("%")
    if not s or s in {"-", "--", "*", "N/A", "NA"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _num(v: Any) -> str:
    """Integer count with thousands separators (no decimals — house style)."""
    n = _f(v)
    return f"{round(n):,}" if n is not None else "—"


def _money(v: Any) -> str:
    """Financial figure, always 2 decimal places (house style)."""
    n = _f(v)
    if n is None:
        return "—"
    a = abs(n)
    if a >= 1e9:
        return f"${n / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${n / 1e6:,.2f}M"
    return f"${n:,.2f}"


def _pct(v: Any, *, already_pct: bool = True) -> str:
    """Percentage, always 1 decimal place (house style)."""
    n = _f(v)
    if n is None:
        return "—"
    return f"{(n if already_pct else n * 100.0):.1f}%"


def _mono(text: Any) -> str:
    return (f'<span style="font-family:var(--ck-mono,monospace);'
            f'font-size:10.5px;">{_e(text)}</span>')


def _code_block(text: str) -> str:
    return (
        '<pre style="margin:4px 0 8px;padding:8px 12px;background:var(--sc-bone,#efe9dc);'
        'border:1px solid var(--ck-border,#d8d0bf);border-radius:3px;'
        'font-family:var(--ck-mono,monospace);font-size:11px;overflow-x:auto;'
        f'white-space:pre;">{_e(text)}</pre>')


def _source_line(dataset_ids: list[str]) -> str:
    """The per-section provenance footer: dataset_id links into the estate."""
    links = " · ".join(
        f'<a href="{_ESTATE_ROUTE}?dataset={_e(d)}" '
        f'style="color:var(--ck-accent,#155752);font-family:var(--ck-mono,monospace);'
        f'font-size:10px;">{_e(d)}</a>'
        for d in dataset_ids)
    owners = sorted({_estate.dataset_owner(d) or "" for d in dataset_ids} - {""})
    labels = ", ".join(_estate.connector_label(o) for o in owners)
    return (
        '<div style="margin:8px 0 0;font-size:10px;color:var(--ck-text-faint,#8b94a0);'
        f'font-family:var(--ck-mono,monospace);">Source: {links}'
        f'{" — " + _e(labels) if labels else ""}</div>')


def _not_ingested(what: str, one_liners: list[str], *, note: str = "") -> str:
    """Per-section empty state: honest, with the exact ingest one-liner(s)."""
    note_html = (
        f'<div style="font-size:10.5px;color:var(--ck-text-faint,#8b94a0);'
        f'margin:2px 0 6px;">{_e(note)}</div>' if note else "")
    return (
        '<div style="padding:10px 12px;border:1px dashed var(--ck-border,#d8d0bf);'
        'border-radius:3px;background:var(--ck-panel-alt,#f2eee4);margin:4px 0 8px;">'
        f'<div style="font-size:11.5px;color:var(--ck-text-dim,#56606f);'
        f'margin-bottom:6px;">{_e(what)} not ingested — run from the repo root:</div>'
        f'{note_html}'
        + "".join(_code_block(c) for c in one_liners)
        + "</div>")


def _panel(inner: str) -> str:
    return ('<div class="ck-panel" style="margin-bottom:16px;">'
            f'<div style="padding:10px 12px;">{inner}</div></div>')


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Striped mono table; cell values arrive pre-formatted AND pre-escaped."""
    ths = "".join(
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:.06em;">{_e(h)}</th>'
        for h in headers)
    trs = []
    for i, r in enumerate(rows):
        stripe = ' style="background:var(--sc-bone,#efe9dc)"' if i % 2 == 0 else ""
        tds = "".join(
            '<td style="padding:5px 10px;font-family:var(--ck-mono,monospace);'
            f'font-size:10.5px;font-variant-numeric:tabular-nums;">{c}</td>'
            for c in r)
        trs.append(f'<tr{stripe}>{tds}</tr>')
    return (
        '<div class="ck-table-wrap" style="overflow-x:auto;">'
        '<table class="ck-table" style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


# ── estate access ───────────────────────────────────────────────────────


def _query(dataset_id: str, filters: dict[str, Any] | None = None,
           limit: int = 1000) -> list[dict[str, Any]]:
    """Bounded rows for one dataset via the bridge's adapter handles.

    The bridge's ``sample_rows`` clamps at 100 rows — fine for a preview
    table, too small for ranking a state's 254 counties — so section
    queries go through ``open_store`` + the adapter's uniform ``query``
    (still the bridge's public surface, still parameterised SQL under a
    column whitelist). ``[]`` on any absence or QueryError.
    """
    owner = _estate.dataset_owner(dataset_id)
    if owner is None:
        return []
    handle = _estate.open_store(owner)
    if handle is None:
        return []
    adapter, store = handle
    try:
        res = adapter.query(store, dataset_id, filters=filters or {},
                            limit=max(1, min(int(limit), 1000)))
        return list(res.rows)
    except Exception:
        return []
    finally:
        with contextlib.suppress(Exception):
            store.close()


def _total(dataset_id: str, filters: dict[str, Any] | None = None) -> int:
    """Exact matching-row count for one dataset (0 on any absence).

    The bounded ``_query`` caps rows at 1000 — fine for mixes and
    rankings, but it understates headline counts (a big state's DMEPOS
    supplier file runs to thousands). ``QueryResult.total`` is the true
    COUNT(*) under the same whitelisted filters, at the cost of one
    LIMIT-1 probe.
    """
    owner = _estate.dataset_owner(dataset_id)
    handle = _estate.open_store(owner) if owner else None
    if handle is None:
        return 0
    adapter, store = handle
    try:
        return int(adapter.query(store, dataset_id, filters=filters or {},
                                 limit=1).total)
    except Exception:
        return 0
    finally:
        with contextlib.suppress(Exception):
            store.close()


def _bars(items: list[tuple[str, str, float]], *, tone: str = "teal") -> str:
    """ck_bar_row strip scaled to the max value; items = (label, value, n)."""
    if not items:
        return ""
    top = max(n for _, _, n in items) or 1.0
    return "".join(
        ck_bar_row(label[:60], value, n / top * 100.0, tone=tone)
        for label, value, n in items)


# ── section 1: demographics & payor context (census_acs) ───────────────


def _sec_demographics(state: str, fips: str, county: str, n_counties: int) -> str:
    state_rows = _query("census_acs_state_profile",
                        {"state_fips": fips}, limit=50)
    county_rows = _query("census_acs_county_profile",
                         {"state_fips": fips}, limit=1000)
    parts = [ck_section_header("Demographics & payor context",
                               eyebrow="01 · WHO LIVES HERE")]
    if not state_rows and not county_rows:
        parts.append(_not_ingested(
            "Census ACS profiles", [
                ("python3 -m connectors.census_acs.cli --db var/connectors/census_acs.db "
                 "fetch --dataset state_profile --year 2023"),
                ("python3 -m connectors.census_acs.cli --db var/connectors/census_acs.db "
                 f"fetch --dataset county_profile --year 2023 --state {fips}"),
            ],
            note="api.census.gov requires a free key on every data request — "
                 "export CENSUS_API_KEY first (https://api.census.gov/data/key_signup.html)."))
        parts.append(_source_line(["census_acs_state_profile",
                                   "census_acs_county_profile"]))
        return "".join(parts)

    inner: list[str] = []
    if state_rows:
        row = max(state_rows, key=lambda r: str(r.get("year") or ""))
        pop = _f(row.get("total_pop"))
        p65 = _f(row.get("pop_65_plus"))
        pov = _f(row.get("poverty_count"))
        share65 = (p65 / pop * 100.0) if pop and p65 is not None else None
        povr = (pov / pop * 100.0) if pop and pov is not None else None
        inner.append(
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("Population",
                           f'<span class="mn">{_num(row.get("total_pop"))}</span>',
                           f'ACS 5-yr {_e(row.get("year"))}')
            + ck_kpi_block("Age 65+",
                           f'<span class="mn">{_num(row.get("pop_65_plus"))}</span>',
                           f"{share65:.1f}% of population" if share65 is not None else "")
            + ck_kpi_block("Median HH income",
                           f'<span class="mn">{_money(row.get("median_hh_income"))}</span>',
                           "median household")
            + ck_kpi_block("Uninsured",
                           f'<span class="mn">{_pct(row.get("uninsured_rate"))}</span>',
                           "civilian noninstitutionalized")
            + ck_kpi_block("Poverty",
                           f'<span class="mn">{povr:.1f}%</span>' if povr is not None
                           else '<span class="mn">—</span>',
                           "population below poverty line")
            + "</div>")

    picked = [r for r in county_rows if county and str(r.get("fips5")) == county]
    if picked:
        row = max(picked, key=lambda r: str(r.get("year") or ""))
        inner.append(
            f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
            f'County focus — {_e(row.get("name"))}</div>')
        inner.append(_table(
            ["County", "Population", "65+", "Median HH income", "Uninsured", "Median age"],
            [[_e(row.get("name")), _num(row.get("total_pop")),
              _num(row.get("pop_65_plus")), _money(row.get("median_hh_income")),
              _pct(row.get("uninsured_rate")), _e(row.get("median_age"))]]))
    elif county_rows:
        ranked = sorted(county_rows,
                        key=lambda r: _f(r.get("total_pop")) or 0.0,
                        reverse=True)[:n_counties]
        inner.append(
            f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
            f'Top {len(ranked)} counties by population</div>')
        inner.append(_table(
            ["County", "FIPS", "Population", "65+", "Median HH income", "Uninsured"],
            [[_e(r.get("name")), _mono(r.get("fips5")), _num(r.get("total_pop")),
              _num(r.get("pop_65_plus")), _money(r.get("median_hh_income")),
              _pct(r.get("uninsured_rate"))] for r in ranked]))
    elif not state_rows:
        pass  # unreachable: guarded above
    if not county_rows:
        inner.append(_not_ingested(
            f"County profiles for {state}", [
                ("python3 -m connectors.census_acs.cli --db var/connectors/census_acs.db "
                 f"fetch --dataset county_profile --year 2023 --state {fips}"),
            ],
            note="Requires CENSUS_API_KEY in the environment."))
    parts.append(_panel("".join(inner)))
    parts.append(_source_line(["census_acs_state_profile",
                               "census_acs_county_profile"]))
    return "".join(parts)


# ── section 2: population health burden (cdc_data PLACES) ──────────────


def _sec_health_burden(state: str, county: str, n_measures: int) -> str:
    parts = [ck_section_header("Population health burden",
                               eyebrow="02 · WHAT THEY ARE SICK WITH")]
    base: dict[str, Any] = {"stateabbr": state,
                            "data_value_type": "Age-adjusted prevalence"}
    scope = "county" if county else "state"
    if county:
        base["locationid"] = county
    items: list[tuple[str, str, float]] = []
    n_counties = 0
    for mid, label in _PLACES_MEASURES[:n_measures]:
        rows = _query("cdc_data_places_county", {**base, "measureid": mid},
                      limit=1000)
        vals = [v for v in (_f(r.get("data_value")) for r in rows)
                if v is not None]
        if not vals:
            continue
        n_counties = max(n_counties, len(vals))
        avg = sum(vals) / len(vals)
        items.append((label, f"{avg:.1f}%", avg))
    if not items and county:
        # County slice may simply not be ingested — fall back to the state.
        return _sec_health_burden(state, "", n_measures)
    if not items:
        parts.append(_not_ingested(
            f"CDC PLACES county estimates for {state}", [
                ("python3 -m connectors.cdc_data.cli --db var/connectors/cdc_data.db "
                 f"fetch --dataset places_county --filter stateabbr={state} --max-pages 3"),
            ]))
    else:
        caption = (f"Prevalence for county {county}" if scope == "county"
                   else f"Mean age-adjusted prevalence across {n_counties} "
                        f"ingested {state} counties")
        parts.append(_panel(
            _bars(items, tone="warning")
            + f'<div style="font-size:10px;color:var(--ck-text-faint,#8b94a0);'
              f'margin-top:6px;font-family:var(--ck-mono,monospace);">{_e(caption)}'
              '</div>'))
    parts.append(_source_line(["cdc_data_places_county"]))
    return "".join(parts)


# ── section 3: provider shortage (hrsa_data HPSA) ───────────────────────


def _sec_provider_shortage(state: str, n_rows: int) -> str:
    parts = [ck_section_header("Provider shortage",
                               eyebrow="03 · WHERE CARE IS SHORT")]
    disciplines = [
        ("hrsa_data_hpsa_primary_care", "Primary Care"),
        ("hrsa_data_hpsa_dental", "Dental Health"),
        ("hrsa_data_hpsa_mental_health", "Mental Health"),
    ]
    # HPSA scores run 0-26 but are stored TEXT; prefilter to the high
    # score values with an IN-list so the 1000-row query cap cannot hide
    # the worst shortage areas, then rank numerically in Python.
    high_scores = [str(i) for i in range(10, 27)]
    counts: list[tuple[str, str, float]] = []
    worst: list[dict[str, Any]] = []
    for dataset_id, label in disciplines:
        f_designated = {"primary_state_abbreviation": state,
                        "hpsa_status": "Designated"}
        probe = _query(dataset_id, f_designated, limit=1)
        n = 0
        if probe:
            owner = _estate.dataset_owner(dataset_id)
            handle = _estate.open_store(owner) if owner else None
            if handle is not None:
                adapter, store = handle
                try:
                    n = int(adapter.query(store, dataset_id,
                                          filters=f_designated, limit=1).total)
                except Exception:
                    n = 0
                finally:
                    with contextlib.suppress(Exception):
                        store.close()
        if n:
            counts.append((label, f"{n:,}", float(n)))
        rows = _query(dataset_id,
                      {**f_designated, "hpsa_score__in": high_scores},
                      limit=1000)
        for r in rows:
            r["_discipline"] = label
        worst.extend(rows)
    if not counts and not worst:
        parts.append(_not_ingested(
            f"HRSA HPSA designations for {state}", [
                ("python3 -m connectors.hrsa_data.cli --root var/connectors "
                 "fetch --dataset hpsa_primary_care --full"),
                ("python3 -m connectors.hrsa_data.cli --root var/connectors "
                 "fetch --dataset hpsa_dental --full"),
                ("python3 -m connectors.hrsa_data.cli --root var/connectors "
                 "fetch --dataset hpsa_mental_health --full"),
            ]))
        parts.append(_source_line([d for d, _ in disciplines]))
        return "".join(parts)

    inner = [
        '<div style="margin:0 0 4px;font-size:11px;font-weight:700;">'
        'Designated shortage areas by discipline</div>',
        _bars(counts, tone="negative"),
    ]
    worst.sort(key=lambda r: _f(r.get("hpsa_score")) or 0.0, reverse=True)
    top = worst[:n_rows]
    if top:
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Worst {len(top)} shortage areas by HPSA score</div>')
        inner.append(_table(
            ["HPSA name", "Discipline", "Score", "Type", "County", "Population"],
            [[_e(str(r.get("hpsa_name") or "")[:52]), _e(r.get("_discipline")),
              _e(r.get("hpsa_score")), _e(r.get("designation_type")),
              _e(r.get("common_county_name") or r.get("county_equivalent_name")),
              _num(r.get("hpsa_designation_population"))] for r in top]))
    parts.append(_panel("".join(inner)))
    parts.append(_source_line([d for d, _ in disciplines]))
    return "".join(parts)


# ── section 4: Medicare market (cms_open_data) ─────────────────────────


def _sec_medicare(state: str, fips: str, county: str, n_rows: int) -> str:
    parts = [ck_section_header("Medicare market",
                               eyebrow="04 · WHAT MEDICARE PAYS")]
    inner: list[str] = []

    # 4a — geographic variation: state KPI strip + county ranking.
    geo_state = _query("cms_open_data_geo_variation_state_county",
                       {"bene_geo_lvl": "State", "bene_geo_desc": state,
                        "bene_age_lvl": "All"}, limit=100)
    geo_filter_cli = (
        "python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
        "--dataset geo_variation_state_county "
        "--filter 'filter[f1][path]=BENE_GEO_DESC' "
        "--filter 'filter[f1][operator]=STARTS_WITH' "
        f"--filter 'filter[f1][value]={state}' --filter YEAR=2023 --max-pages 2")
    if geo_state:
        row = max(geo_state, key=lambda r: str(r.get("year") or ""))
        inner.append(
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("Medicare benes",
                           f'<span class="mn">{_num(row.get("benes_total_cnt"))}</span>',
                           f'{_e(row.get("year"))} · all ages')
            + ck_kpi_block("Std. spend / capita",
                           f'<span class="mn">{_money(row.get("tot_mdcr_stdzd_pymt_pc"))}</span>',
                           "standardized, per beneficiary")
            + ck_kpi_block("MA participation",
                           f'<span class="mn">{_pct(row.get("ma_prtcptn_rate"), already_pct=False)}</span>',
                           "Medicare Advantage share")
            + ck_kpi_block("ED visits / 1k",
                           f'<span class="mn">{_num(row.get("er_visits_per_1000_benes"))}</span>',
                           "emergency department")
            + ck_kpi_block("Dual eligible",
                           f'<span class="mn">{_pct(row.get("bene_dual_pct"), already_pct=False)}</span>',
                           "Medicare-Medicaid duals")
            + "</div>")
        geo_counties = _query("cms_open_data_geo_variation_state_county",
                              {"bene_geo_lvl": "County",
                               "bene_geo_desc__like": f"{state}-%",
                               "bene_age_lvl": "All",
                               "year": str(row.get("year") or "")},
                              limit=1000)
        if county:
            geo_counties = [r for r in geo_counties
                            if str(r.get("bene_geo_cd")) == county] or geo_counties
        ranked = sorted(geo_counties,
                        key=lambda r: _f(r.get("benes_total_cnt")) or 0.0,
                        reverse=True)[:n_rows]
        if ranked:
            inner.append(
                f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
                f'{"County focus" if county and len(ranked) == 1 else f"Top {len(ranked)} counties by Medicare population"}'
                f' · {_e(ranked[0].get("year"))}</div>')
            inner.append(_table(
                ["County", "Benes", "Std. spend/capita", "MA share", "ED visits/1k"],
                [[_e(str(r.get("bene_geo_desc") or "").split("-", 1)[-1]),
                  _num(r.get("benes_total_cnt")),
                  _money(r.get("tot_mdcr_stdzd_pymt_pc")),
                  _pct(r.get("ma_prtcptn_rate"), already_pct=False),
                  _num(r.get("er_visits_per_1000_benes"))] for r in ranked]))
    else:
        inner.append(_not_ingested(
            f"Medicare geographic variation for {state}", [geo_filter_cli]))

    # 4b — market saturation: providers per service type at state level.
    sat = _query("cms_open_data_market_saturation_state_county",
                 {"state": state, "aggregation_level": "STATE"}, limit=1000)
    if sat:
        latest = max(str(r.get("reference_period") or "") for r in sat)
        by_svc: dict[str, dict[str, Any]] = {}
        for r in sat:
            if str(r.get("reference_period") or "") == latest:
                by_svc[str(r.get("type_of_service") or "")] = r
        items = []
        for svc, r in by_svc.items():
            n = _f(r.get("number_of_providers"))
            if n is None:
                continue
            upp = _f(r.get("average_number_of_users_per_provider"))
            items.append((svc, f"{int(n):,} prov · {int(upp or 0):,} users/prov", n))
        items.sort(key=lambda t: t[2], reverse=True)
        if items:
            inner.append(
                f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
                f'Provider saturation by service type · {_e(latest)}</div>')
            inner.append(_bars(items[:n_rows], tone="navy"))
    else:
        inner.append(_not_ingested(
            f"Market saturation for {state}", [
                ("python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
                 f"--dataset market_saturation_state_county --filter state={state} --max-pages 3"),
            ]))

    # 4c — enrollment trend: MA share of total benes by year (state grain).
    enr = _query("cms_open_data_medicare_monthly_enrollment",
                 {"bene_state_abrvtn": state, "bene_geo_lvl": "State",
                  "month": "Year"}, limit=200)
    if enr:
        years = sorted(enr, key=lambda r: str(r.get("year") or ""))[-8:]
        items = []
        for r in years:
            tot, ma = _f(r.get("tot_benes")), _f(r.get("ma_and_oth_benes"))
            if not tot or ma is None:
                continue
            share = ma / tot * 100.0
            items.append((str(r.get("year")), f"{share:.1f}% MA", share))
        if items:
            inner.append(
                '<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
                'Medicare Advantage share trend</div>')
            inner.append(_bars(items, tone="teal"))
    else:
        inner.append(_not_ingested(
            f"Medicare monthly enrollment for {state}", [
                ("python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
                 f"--dataset medicare_monthly_enrollment --filter BENE_STATE_ABRVTN={state} "
                 "--filter MONTH=Year --max-pages 4"),
            ]))
    parts.append(_panel("".join(inner)))
    parts.append(_source_line([
        "cms_open_data_geo_variation_state_county",
        "cms_open_data_market_saturation_state_county",
        "cms_open_data_medicare_monthly_enrollment"]))
    return "".join(parts)


# ── section 5: facility quality (provider_data) ─────────────────────────


def _star_mix(dataset_id: str, rating_col: str, state_col_value: str,
              label: str, tone: str) -> str:
    agg = _estate.aggregate(dataset_id, rating_col,
                            filters={"state": state_col_value}, limit=20)
    rows = agg.get("rows") or []
    if not rows:
        return ""
    by_rating: dict[str, int] = {}
    for r in rows:
        # Ratings arrive as "5" (hospital/SNF files) or "5.0" (dialysis
        # five_star) — normalize numerically, never string-match.
        num = _f(r.get(rating_col))
        key = (str(int(num)) if num is not None and num.is_integer()
               and 1.0 <= num <= 5.0 else "Not rated / n.a.")
        by_rating[key] = by_rating.get(key, 0) + int(r.get("count") or 0)
    total = sum(by_rating.values())
    rated = [(k, by_rating[k]) for k in ("5", "4", "3", "2", "1")
             if k in by_rating]
    weighted = sum(int(k) * n for k, n in rated)
    n_rated = sum(n for _, n in rated)
    avg = (weighted / n_rated) if n_rated else None
    items = [(f"{k} star", f"{n:,}", float(n)) for k, n in rated]
    if "Not rated / n.a." in by_rating:
        items.append(("Not rated / n.a.", f"{by_rating['Not rated / n.a.']:,}",
                      float(by_rating["Not rated / n.a."])))
    head = (f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'{_e(label)} · {total:,} facilities'
            + (f' · avg {avg:.2f} of rated' if avg is not None else "")
            + '</div>')
    return head + _bars(items, tone=tone)


def _sec_facility_quality(state: str, n_rows: int) -> str:
    parts = [ck_section_header("Facility quality",
                               eyebrow="05 · HOW GOOD IS THE PLANT")]
    hosp = _star_mix("provider_data_hospital_general",
                     "hospital_overall_rating", state,
                     "Hospital overall star mix", "teal")
    snf = _star_mix("provider_data_nursing_home_provider_info",
                    "overall_rating", state,
                    "Nursing home overall star mix", "navy")
    if not hosp and not snf:
        parts.append(_not_ingested(
            f"Care Compare facility data for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset hospital_general --state {state} --max-pages 3"),
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset nursing_home_provider_info --state {state} --max-pages 3"),
            ]))
    else:
        inner = [hosp or _not_ingested(
            f"Hospital general information for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset hospital_general --state {state} --max-pages 3")])]
        inner.append(snf or _not_ingested(
            f"Nursing home provider info for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset nursing_home_provider_info --state {state} --max-pages 3")]))
        parts.append(_panel("".join(inner)))
    parts.append(_source_line(["provider_data_hospital_general",
                               "provider_data_nursing_home_provider_info"]))
    return "".join(parts)


# ── section 6: industry money flow (open_payments) ──────────────────────


def _sec_money_flow(state: str, n_rows: int) -> str:
    parts = [ck_section_header("Industry money flow",
                               eyebrow="06 · WHO PAYS THE DOCTORS")]
    rows = _query("open_payments_state_payment_totals",
                  {"state_code": state}, limit=1000)
    if not rows:
        parts.append(_not_ingested(
            f"Open Payments state totals for {state}", [
                ("python3 -m connectors.open_payments.cli fetch "
                 "--db var/connectors/open_payments.db --dataset state_payment_totals"),
            ]))
        parts.append(_source_line(["open_payments_state_payment_totals"]))
        return "".join(parts)
    latest = max(str(r.get("program_year") or "") for r in rows)
    year_rows = [r for r in rows if str(r.get("program_year") or "") == latest]
    by_nature: dict[str, float] = {}
    total = 0.0
    for r in year_rows:
        amt = sum(v for v in (
            _f(r.get("total_payment_amount_physician")),
            _f(r.get("total_payment_amount_non_physician_practitioner")),
            _f(r.get("total_payment_amount_teaching_hospital"))) if v)
        nature = str(r.get("nature_of_payment") or "").strip() or "Unspecified"
        by_nature[nature] = by_nature.get(nature, 0.0) + amt
        total += amt
    items = sorted(((k, _money(v), v) for k, v in by_nature.items() if v > 0),
                   key=lambda t: t[2], reverse=True)[:n_rows]
    inner = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Total payments",
                       f'<span class="mn">{_money(total)}</span>',
                       f"program year {_e(latest)} · all recipient types")
        + ck_kpi_block("Payment natures",
                       f'<span class="mn">{len(by_nature)}</span>',
                       "Sunshine Act categories")
        + "</div>"
        + f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
          f'Top {len(items)} natures of payment · {_e(latest)}</div>'
        + _bars(items, tone="warning"))
    parts.append(_panel(inner))
    parts.append(_source_line(["open_payments_state_payment_totals"]))
    return "".join(parts)


# ── section 7: research footprint (nih_reporter) ────────────────────────


def _sec_research(state: str, n_orgs: int) -> str:
    parts = [ck_section_header("Research footprint",
                               eyebrow="07 · WHO WINS NIH MONEY")]
    rows = _query("nih_reporter_projects", {"org_state": state}, limit=1000)
    if not rows:
        parts.append(_not_ingested(
            f"NIH RePORTER projects for {state}", [
                ("python3 -m connectors.nih_reporter.cli --db var/connectors/nih_reporter.db "
                 f"fetch --dataset projects --state {state} --fiscal-year 2025 --max-pages 2"),
            ]))
        parts.append(_source_line(["nih_reporter_projects"]))
        return "".join(parts)
    by_org: dict[str, tuple[float, int]] = {}
    total = 0.0
    fys = set()
    for r in rows:
        org = str(r.get("org_name") or "").strip() or "Unknown organization"
        amt = _f(r.get("award_amount")) or 0.0
        prev = by_org.get(org, (0.0, 0))
        by_org[org] = (prev[0] + amt, prev[1] + 1)
        total += amt
        fy = str(r.get("fiscal_year") or "").strip()
        if fy:
            fys.add(fy)
    top = sorted(by_org.items(), key=lambda kv: kv[1][0], reverse=True)[:n_orgs]
    items = [(org, f"{_money(amt)} · {n} award{'s' if n != 1 else ''}", amt)
             for org, (amt, n) in top]
    fy_label = "-".join(sorted(fys)[:1] + sorted(fys)[-1:]) if fys else "—"
    inner = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("NIH awards",
                       f'<span class="mn">{_money(total)}</span>',
                       f"{len(rows):,} ingested projects · FY {_e(fy_label)}")
        + ck_kpi_block("Awardee orgs",
                       f'<span class="mn">{len(by_org):,}</span>',
                       "distinct organizations")
        + "</div>"
        + f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
          f'Top {len(items)} organizations by award total</div>'
        + _bars(items, tone="teal"))
    parts.append(_panel(inner))
    parts.append(_source_line(["nih_reporter_projects"]))
    return "".join(parts)


# ── section 8: compliance exposure (oig_leie) ───────────────────────────


def _sec_compliance(state: str, n_rows: int) -> str:
    parts = [ck_section_header("Compliance exposure",
                               eyebrow="08 · WHO IS EXCLUDED")]
    agg = _estate.aggregate("oig_leie_exclusions", "excltype",
                            filters={"state": state}, limit=100)
    arows = agg.get("rows") or []
    if not arows:
        parts.append(_not_ingested(
            f"OIG LEIE exclusions for {state}", [
                ("python3 -m connectors.oig_leie.cli --db var/connectors/oig_leie.db "
                 "fetch --dataset exclusions --max-rows 5000"),
            ]))
        parts.append(_source_line(["oig_leie_exclusions"]))
        return "".join(parts)
    total = sum(int(r.get("count") or 0) for r in arows)
    items = []
    for r in arows[:n_rows]:
        code = str(r.get("excltype") or "").strip() or "—"
        gloss = _LEIE_TYPES.get(code, "")
        label = f"{code} — {gloss}" if gloss else code
        n = int(r.get("count") or 0)
        items.append((label, f"{n:,}", float(n)))
    recent = _query("oig_leie_exclusions", {"state": state}, limit=1000)
    recent.sort(key=lambda r: str(r.get("excldate") or ""), reverse=True)
    latest = recent[:min(8, n_rows)]
    inner = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Exclusions on file",
                       f'<span class="mn">{total:,}</span>',
                       f"{state} individuals + entities in the ingested LEIE slice")
        + "</div>"
        + '<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
          'Exclusions by statute</div>'
        + _bars(items, tone="negative"))
    if latest:
        inner += (
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Most recent {len(latest)} exclusions</div>'
            + _table(
                ["Excluded party", "Specialty", "City", "Statute", "Date"],
                [[_e(f"{r.get('lastname', '')}, {r.get('firstname', '')}".strip(", ")
                     or r.get("busname") or "—"),
                  _e(r.get("specialty") or "—"), _e(r.get("city") or "—"),
                  _mono(r.get("excltype")), _mono(r.get("excldate"))]
                 for r in latest]))
    parts.append(_panel(inner))
    parts.append(_source_line(["oig_leie_exclusions"]))
    return "".join(parts)


# ── section 9: healthcare labor market (bls_qcew) ───────────────────────


def _county_name_map(state: str, fips: str) -> dict[str, str]:
    """FIPS5 → county name, from whichever geo dataset is ingested."""
    out: dict[str, str] = {}
    for r in _query("census_acs_county_profile", {"state_fips": fips},
                    limit=1000):
        f5, name = str(r.get("fips5") or ""), str(r.get("name") or "")
        if f5 and name:
            out[f5] = name.split(",")[0]
    if out:
        return out
    for r in _query("cms_open_data_geo_variation_state_county",
                    {"bene_geo_lvl": "County",
                     "bene_geo_desc__like": f"{state}-%"}, limit=1000):
        f5 = str(r.get("bene_geo_cd") or "")
        name = str(r.get("bene_geo_desc") or "").split("-", 1)[-1]
        if len(f5) == 5 and name:
            out.setdefault(f5, name)
    if out:
        return out
    for r in _query("cdc_data_places_county", {"stateabbr": state},
                    limit=1000):
        f5, name = str(r.get("locationid") or ""), str(r.get("locationname") or "")
        if len(f5) == 5 and name:
            out.setdefault(f5, name)
    return out


def _sec_labor(state: str, fips: str, n_rows: int) -> str:
    parts = [ck_section_header("Healthcare labor market",
                               eyebrow="09 · WHAT LABOR COSTS")]
    state_area = f"{fips}000"
    rows = _query("bls_qcew_industry_area",
                  {"area_fips__like": f"{fips}%"}, limit=1000)
    if not rows or not fips:
        parts.append(_not_ingested(
            f"BLS QCEW healthcare employment for {state}", [
                ("python3 -m connectors.bls_qcew.cli --db var/connectors/bls_qcew.db "
                 "fetch --dataset industry_area --industry 622 --max-rows 5000"),
                ("python3 -m connectors.bls_qcew.cli --db var/connectors/bls_qcew.db "
                 "fetch --dataset industry_area --industry 62 --max-rows 5000"),
            ],
            note="The QCEW industry file covers every US county in FIPS order; "
                 "raise --max-rows (or use --full) so the file reaches this state."))
        parts.append(_source_line(["bls_qcew_industry_area"]))
        return "".join(parts)

    period = max((str(r.get("year") or ""), str(r.get("qtr") or ""))
                 for r in rows)
    rows = [r for r in rows
            if (str(r.get("year") or ""), str(r.get("qtr") or "")) == period]
    # Private ownership (own_code 5) is the PE-relevant slice; fall back
    # to whatever ownership codes exist when 5 is absent.
    private = [r for r in rows if str(r.get("own_code")) == "5"] or rows
    kpis = []
    for r in private:
        if str(r.get("area_fips")) != state_area:
            continue
        ind = str(r.get("industry_code") or "")
        label = _QCEW_INDUSTRIES.get(ind, f"NAICS {ind}")
        kpis.append(ck_kpi_block(
            label,
            f'<span class="mn">{_num(r.get("month3_emplvl"))}</span>',
            f'jobs · avg weekly wage {_money(r.get("avg_wkly_wage"))} · '
            f'{_e(period[0])}Q{_e(period[1])}'))
    inner = ""
    if kpis:
        inner += '<div class="ck-kpi-grid">' + "".join(kpis) + "</div>"
    names = _county_name_map(state, fips)
    by_county: dict[str, tuple[float, float]] = {}
    for r in private:
        area = str(r.get("area_fips") or "")
        if area == state_area or not area.startswith(fips):
            continue
        emp = _f(r.get("month3_emplvl")) or 0.0
        wage = _f(r.get("avg_wkly_wage")) or 0.0
        prev = by_county.get(area, (0.0, 0.0))
        by_county[area] = (prev[0] + emp, max(prev[1], wage))
    ranked = sorted(by_county.items(), key=lambda kv: kv[1][0],
                    reverse=True)[:n_rows]
    items = [(names.get(area, f"FIPS {area}"),
              f"{int(emp):,} jobs · {_money(wage)}/wk", emp)
             for area, (emp, wage) in ranked if emp > 0]
    if items:
        inner += (
            f'<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
            f'Top {len(items)} counties by healthcare employment · '
            f'{_e(period[0])}Q{_e(period[1])}</div>'
            + _bars(items, tone="navy"))
    if not inner:
        inner = _not_ingested(
            f"BLS QCEW rows for {state} counties", [
                ("python3 -m connectors.bls_qcew.cli --db var/connectors/bls_qcew.db "
                 "fetch --dataset industry_area --industry 622 --max-rows 5000"),
            ])
    parts.append(_panel(inner))
    parts.append(_source_line(["bls_qcew_industry_area"]))
    return "".join(parts)


# ── section 10: kidney & dialysis market ────────────────────────────────


def _sec_kidney_dialysis(state: str, county: str, n_rows: int) -> str:
    parts = [ck_section_header("Kidney & dialysis market",
                               eyebrow="10 · WHERE KIDNEYS FAIL")]
    inner: list[str] = []

    # 10a — county CKD prevalence. Pinned to the PLACES 2023 county
    # release (h3ej-a9ec): measureid KIDNEY was dropped from the 2024 and
    # 2025 releases, so the currently-curated places_county no longer
    # carries it. The dataset's default_params pin the measure at fetch
    # time — every ingested row is already CKD-only.
    ckd_filters: dict[str, Any] = {"stateabbr": state,
                                   "data_value_type": "Age-adjusted prevalence"}
    county_scope = bool(county)
    if county:
        ckd_filters["locationid"] = county
    ckd = _query("cdc_data_places_county_ckd", ckd_filters, limit=1000)
    if not ckd and county:
        # County slice may simply not be ingested — fall back to the state.
        county_scope = False
        ckd = _query("cdc_data_places_county_ckd",
                     {"stateabbr": state,
                      "data_value_type": "Age-adjusted prevalence"},
                     limit=1000)
    if ckd:
        vals = [(str(r.get("locationname") or ""), v)
                for r in ckd
                if (v := _f(r.get("data_value"))) is not None]
        vals.sort(key=lambda t: t[1], reverse=True)
        year = max(str(r.get("year") or "") for r in ckd)
        mean = (sum(v for _, v in vals) / len(vals)) if vals else None
        head = (f"CKD prevalence — county {county}" if county_scope
                else f"Worst {min(n_rows, len(vals))} counties by CKD prevalence")
        inner.append(
            f'<div style="margin:0 0 4px;font-size:11px;font-weight:700;">'
            f'{_e(head)}'
            + (f' · state mean {mean:.1f}% across {len(vals)} counties'
               if mean is not None and not county_scope else "")
            + "</div>")
        inner.append(_bars(
            [(name, f"{v:.1f}%", v) for name, v in vals[:n_rows]],
            tone="warning"))
        inner.append(
            '<div style="font-size:10px;color:var(--ck-text-faint,#8b94a0);'
            'margin-top:6px;font-family:var(--ck-mono,monospace);">'
            f'Age-adjusted prevalence, adults 18+ · PLACES 2023 release '
            f'(measureid KIDNEY) · {_e(year)} estimates</div>')
    else:
        inner.append(_not_ingested(
            f"CDC PLACES county CKD prevalence for {state}", [
                ("python3 -m connectors.cdc_data.cli --db var/connectors/cdc_data.db "
                 f"fetch --dataset places_county_ckd --filter stateabbr={state} "
                 "--max-pages 2"),
            ],
            note="Pinned to the PLACES 2023 county release (h3ej-a9ec) — the last "
                 "vintage carrying measureid KIDNEY; the fetch pins the measure "
                 "automatically."))

    # 10b — dialysis capacity + star/ownership mix (Care Compare listing).
    fac = _query("provider_data_dialysis_facilities", {"state": state},
                 limit=1000)
    fac_cli = ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
               f"fetch --dataset dialysis_facilities --state {state} --max-pages 2")
    if fac:
        n_fac = _total("provider_data_dialysis_facilities",
                       {"state": state}) or len(fac)
        stations = sum(int(v) for v in
                       (_f(r.get("of_dialysis_stations")) for r in fac) if v)
        profit = sum(1 for r in fac
                     if str(r.get("profit_or_nonprofit") or "").strip().lower()
                     == "profit")
        by_chain: dict[str, int] = {}
        for r in fac:
            chain = str(r.get("chain_organization") or "").strip() or "Unknown"
            by_chain[chain] = by_chain.get(chain, 0) + 1
        chains = sorted(by_chain.items(), key=lambda kv: kv[1],
                        reverse=True)[:n_rows]
        inner.append(
            '<div class="ck-kpi-grid" style="margin-top:12px;">'
            + ck_kpi_block("Dialysis facilities",
                           f'<span class="mn">{n_fac:,}</span>',
                           "Care Compare certified facilities")
            + ck_kpi_block("Dialysis stations",
                           f'<span class="mn">{stations:,}</span>',
                           "in-center hemodialysis capacity")
            + ck_kpi_block("For-profit share",
                           f'<span class="mn">{profit / len(fac) * 100.0:.1f}%</span>',
                           f"of {len(fac):,} facilities")
            + "</div>")
        inner.append(_star_mix("provider_data_dialysis_facilities", "five_star",
                               state, "Dialysis facility five-star mix", "teal"))
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Top {len(chains)} chains by facility count</div>')
        inner.append(_bars(
            [(chain, f"{n:,}", float(n)) for chain, n in chains], tone="navy"))
    else:
        inner.append(_not_ingested(
            f"Dialysis facility listing for {state}", [fac_cli]))

    # 10c — ESRD QIP total performance score distribution (PY2026 files).
    tps = _query("provider_data_esrd_qip_tps", {"state": state}, limit=1000)
    if tps:
        scores = sorted(v for r in tps
                        if (v := _f(r.get("total_performance_score"))) is not None)
        no_score = len(tps) - len(scores)
        st_avg = _f(tps[0].get("state_average_total_performance_score"))
        nat_avg = _f(tps[0].get("national_average_total_performance_score"))
        items = []
        for label, lo, hi in (("TPS 80-100", 80.0, 100.5), ("TPS 60-79", 60.0, 80.0),
                              ("TPS 40-59", 40.0, 60.0), ("TPS 20-39", 20.0, 40.0),
                              ("TPS 0-19", 0.0, 20.0)):
            n = sum(1 for v in scores if lo <= v < hi)
            if n:
                items.append((label, f"{n:,}", float(n)))
        if no_score:
            items.append(("No score", f"{no_score:,}", float(no_score)))
        median = scores[len(scores) // 2] if scores else None
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'ESRD QIP total performance scores · PY2026 · '
            f'{len(tps):,} facilities'
            + (f' · median {median:.0f}' if median is not None else "")
            + "</div>")
        inner.append(_bars(items, tone="teal"))
        if st_avg is not None and nat_avg is not None:
            inner.append(
                '<div style="font-size:10px;color:var(--ck-text-faint,#8b94a0);'
                'margin-top:6px;font-family:var(--ck-mono,monospace);">'
                f'{_e(state)} average {st_avg:.0f} vs national {nat_avg:.0f}'
                "</div>")
    else:
        inner.append(_not_ingested(
            f"ESRD QIP total performance scores for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset esrd_qip_tps --state {state} --max-pages 2"),
            ]))

    # 10d — clinical care + patient experience, state vs national.
    st_rows = _query("provider_data_dialysis_state_averages",
                     {"state": state}, limit=10)
    nat_rows = _query("provider_data_dialysis_national_averages", {}, limit=10)
    if st_rows and nat_rows:
        srow, nrow = st_rows[0], nat_rows[0]
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Dialysis clinical care — {_e(state)} vs national</div>')
        inner.append(_table(
            ["Measure", state, "National"],
            [[_e(label), _pct(srow.get(sc)), _pct(nrow.get(nc))]
             for label, sc, nc in _DIALYSIS_VS_NATIONAL]))
    else:
        inner.append(_not_ingested(
            f"Dialysis state/national averages for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset dialysis_state_averages --state {state}"),
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 "fetch --dataset dialysis_national_averages"),
            ]))
    ich_st = _query("provider_data_ich_cahps_state", {"state": state}, limit=10)
    ich_nat = _query("provider_data_ich_cahps_national", {}, limit=10)
    if ich_st and ich_nat:
        srow, nrow = ich_st[0], ich_nat[0]
        rows = [[_e(label), _num(srow.get(col)), _num(nrow.get(col))]
                for label, col in _ICH_CAHPS_MEASURES]
        rows.append(["Survey response rate",
                     _pct(srow.get("survey_response_rate")),
                     _pct(nrow.get("survey_response_rate"))])
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Patient experience — ICH-CAHPS linearized scores (0-100), '
            f'{_e(state)} vs national</div>')
        inner.append(_table(["Measure", state, "National"], rows))
    else:
        inner.append(_not_ingested(
            f"ICH-CAHPS patient survey averages for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset ich_cahps_state --state {state}"),
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 "fetch --dataset ich_cahps_national"),
            ]))
    parts.append(_panel("".join(inner)))
    parts.append(_source_line([
        "cdc_data_places_county_ckd", "provider_data_dialysis_facilities",
        "provider_data_dialysis_state_averages",
        "provider_data_dialysis_national_averages", "provider_data_esrd_qip_tps",
        "provider_data_ich_cahps_state", "provider_data_ich_cahps_national"]))
    return "".join(parts)


# ── section 11: outpatient facility universe ────────────────────────────


def _pos_universe(dataset_id: str, code_col: str, labels: dict[str, str],
                  file_label: str, state: str
                  ) -> list[tuple[str, str, int, int]]:
    """(category, file, records, active) for one Provider of Services file.

    Mirrors the estate's /v1/lookup/facility-universe/{state} aggregation
    (connectors/cms_open_data/lookup.py) through the bridge's aggregate:
    every record counts — the POS files retain terminated providers —
    and "active" is the ``pgm_trmntn_cd = '00'`` slice.
    """
    agg = _estate.aggregate(dataset_id, code_col,
                            filters={"state_cd": state}, limit=100)
    rows = agg.get("rows") or []
    if not rows:
        return []
    active_agg = _estate.aggregate(
        dataset_id, code_col,
        filters={"state_cd": state, "pgm_trmntn_cd": "00"}, limit=100)
    active = {str(r.get(code_col) or ""): int(r.get("count") or 0)
              for r in (active_agg.get("rows") or [])}
    out = []
    for r in rows:
        code = str(r.get(code_col) or "")
        label = labels.get(code) or f"{file_label} category {code}"
        out.append((label, file_label, int(r.get("count") or 0),
                    active.get(code, 0)))
    return out


def _sec_outpatient_universe(state: str, n_rows: int) -> str:
    parts = [ck_section_header("Outpatient facility universe",
                               eyebrow="11 · WHERE OUTPATIENT CARE SITS")]
    inner: list[str] = []

    # 11a — certified-facility counts by category from BOTH POS files.
    qies_cli = ("python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
                f"--dataset pos_qies --filter STATE_CD={state} --size 2000 --max-pages 2")
    iqies_cli = ("python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
                 f"--dataset pos_internet_qies --filter state_cd={state} --size 2000 --max-pages 5")
    qies = _pos_universe("cms_open_data_pos_qies", "prvdr_ctgry_cd",
                         _POS_QIES_CATEGORIES, "QIES", state)
    iqies = _pos_universe("cms_open_data_pos_internet_qies", "prvdr_type_id",
                          _POS_IQIES_TYPES, "iQIES", state)
    if qies or iqies:
        ranked = sorted(qies + iqies, key=lambda t: t[2], reverse=True)
        total = sum(t[2] for t in ranked)
        active = sum(t[3] for t in ranked)
        inner.append(
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("Certified facility records",
                           f'<span class="mn">{total:,}</span>',
                           "both Provider of Services files · terminated retained")
            + ck_kpi_block("Active certifications",
                           f'<span class="mn">{active:,}</span>',
                           (f"{active / total * 100.0:.1f}% of records"
                            if total else ""))
            + "</div>")
        inner.append(
            '<div style="margin:10px 0 4px;font-size:11px;font-weight:700;">'
            "Certified facilities by provider category</div>")
        inner.append(_table(
            ["Provider category", "POS file", "Records", "Active"],
            [[_e(label), _mono(file_label), f"{records:,}", f"{act:,}"]
             for label, file_label, records, act in ranked]))
        if not qies:
            inner.append(_not_ingested(
                f"POS QIES file (hospitals / RHC / FQHC / CMHC) for {state}",
                [qies_cli],
                note="The legacy QIES file's API columns are UPPER_CASE — "
                     "filter on STATE_CD."))
        if not iqies:
            inner.append(_not_ingested(
                f"POS Internet QIES file (HHA / SNF / hospice / ASC / ESRD) "
                f"for {state}", [iqies_cli],
                note="The iQIES file's API columns are lower_case — "
                     "filter on state_cd."))
    else:
        inner.append(_not_ingested(
            f"Provider of Services files for {state}", [qies_cli, iqies_cli],
            note="Hospitals, RHCs, FQHCs and CMHCs live in the legacy QIES "
                 "file (UPPER_CASE columns, filter STATE_CD); HHAs, SNFs, "
                 "hospices, ASCs and ESRD facilities in the Internet QIES "
                 "file (lower_case columns, filter state_cd)."))

    # 11b — ASC quality, state vs national (latest ingested year).
    asc_st = _query("provider_data_asc_quality_state", {"state": state},
                    limit=100)
    asc_nat = _query("provider_data_asc_quality_national", {}, limit=100)
    if asc_st and asc_nat:
        srow = max(asc_st, key=lambda r: str(r.get("year") or ""))
        year = str(srow.get("year") or "")
        nrow = next((r for r in asc_nat if str(r.get("year") or "") == year),
                    max(asc_nat, key=lambda r: str(r.get("year") or "")))
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'ASC quality measures — {_e(state)} vs national · {_e(year)}</div>')
        inner.append(_table(
            ["Measure", f"{state} avg", "National avg"],
            [[_e(label), _pct(srow.get(sc)), _pct(nrow.get(nc))]
             for label, sc, nc in _ASC_MEASURES]))
    else:
        inner.append(_not_ingested(
            f"ASC quality state/national averages for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset asc_quality_state --state {state}"),
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 "fetch --dataset asc_quality_national"),
            ]))

    # 11c — Medicare DMEPOS suppliers (directory grain: one row per
    # supplier location; the state column is practicestate).
    n_dme = _total("provider_data_medical_equipment_suppliers",
                   {"practicestate": state})
    if n_dme:
        agg = _estate.aggregate("provider_data_medical_equipment_suppliers",
                                "practicecity",
                                filters={"practicestate": state}, limit=100)
        cities = [(str(r.get("practicecity") or "").strip() or "Unknown",
                   int(r.get("count") or 0))
                  for r in (agg.get("rows") or [])][:n_rows]
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Medicare DMEPOS suppliers · {n_dme:,} in {_e(state)} · '
            f'top {len(cities)} cities</div>')
        inner.append(_bars(
            [(city, f"{n:,}", float(n)) for city, n in cities], tone="navy"))
    else:
        inner.append(_not_ingested(
            f"Medical equipment suppliers for {state}", [
                ("python3 -m connectors.provider_data.cli --db var/connectors/provider_data.db "
                 f"fetch --dataset medical_equipment_suppliers "
                 f"--filter practicestate={state} --page-size 1500 --max-pages 3"),
            ],
            note="The DMEPOS supplier directory's state column is practicestate "
                 "(no bare state column)."))

    # 11d — home infusion therapy providers (PECOS enrollment slice).
    n_hit = _total("cms_open_data_home_infusion_therapy_providers",
                   {"state": state})
    if n_hit:
        agg = _estate.aggregate("cms_open_data_home_infusion_therapy_providers",
                                "city", filters={"state": state}, limit=100)
        cities = [(str(r.get("city") or "").strip() or "Unknown",
                   int(r.get("count") or 0))
                  for r in (agg.get("rows") or [])][:n_rows]
        inner.append(
            f'<div style="margin:12px 0 4px;font-size:11px;font-weight:700;">'
            f'Home infusion therapy providers · {n_hit:,} enrolled in '
            f'{_e(state)}</div>')
        inner.append(_bars(
            [(city, f"{n:,}", float(n)) for city, n in cities], tone="teal"))
    else:
        inner.append(_not_ingested(
            f"Home infusion therapy providers for {state}", [
                ("python3 -m connectors.cms_open_data.cli fetch --db var/connectors/cms_open_data.db "
                 f"--dataset home_infusion_therapy_providers --filter State={state} "
                 "--max-pages 1"),
            ],
            note="Fetch-time filters use the API's original Title-Case "
                 "column names (State)."))
    parts.append(_panel("".join(inner)))
    parts.append(_source_line([
        "cms_open_data_pos_qies", "cms_open_data_pos_internet_qies",
        "provider_data_asc_quality_state", "provider_data_asc_quality_national",
        "provider_data_medical_equipment_suppliers",
        "cms_open_data_home_infusion_therapy_providers"]))
    return "".join(parts)


# ── controls + page assembly ────────────────────────────────────────────


def _controls(state: str, county: str) -> str:
    options = "".join(
        f'<option value="{code}"{" selected" if code == state else ""}>'
        f'{code} — {_e(name)}</option>'
        for code, name in sorted(_STATE_NAMES.items()))
    return (
        f'<form method="get" action="{_ROUTE}" style="display:flex;gap:10px;'
        'align-items:flex-end;flex-wrap:wrap;margin:14px 0 18px;">'
        '<label style="display:flex;flex-direction:column;gap:3px;font-size:10px;'
        'text-transform:uppercase;letter-spacing:.08em;color:var(--ck-text-faint,#8b94a0);">'
        'State'
        f'<select name="state" style="padding:6px 10px;border:1px solid '
        f'var(--ck-border,#d8d0bf);border-radius:3px;font-size:12px;'
        f'font-family:var(--ck-mono,monospace);">{options}</select></label>'
        '<label style="display:flex;flex-direction:column;gap:3px;font-size:10px;'
        'text-transform:uppercase;letter-spacing:.08em;color:var(--ck-text-faint,#8b94a0);">'
        'County FIPS (optional)'
        f'<input type="text" name="county" value="{_e(county)}" placeholder="e.g. 48201" '
        'maxlength="5" style="padding:6px 10px;border:1px solid var(--ck-border,#d8d0bf);'
        'border-radius:3px;font-size:12px;width:110px;'
        'font-family:var(--ck-mono,monospace);" /></label>'
        '<button type="submit" style="padding:8px 18px;background:var(--ck-accent,#155752);'
        'color:#fff;border:none;border-radius:3px;font-size:12px;cursor:pointer;">'
        'Run scan</button></form>')


def render_market_scan(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    if not _estate.estate_available():
        body = ck_page_title(
            "Market Scan", eyebrow="Research · Public Data",
            meta="repo-root connectors/ estate not found on this deployment",
        ) + ck_empty_state(
            "Connector estate not available",
            "The market scan reads the repo-root connectors/ estate through "
            "the read-only bridge, and no estate is present on this "
            "deployment. Check out the full repository (the estate lives "
            "beside RCM_MC), then ingest it: python3 -m connectors.cli "
            "refresh --db var/connectors. Set RCM_MC_CONNECTORS_ROOT if the "
            "estate lives somewhere non-standard.",
            eyebrow="MARKET SCAN", icon="⌖")
        return chartis_shell(body, "Market Scan", active_nav=_ROUTE,
                             subtitle="PE-desk market brief — estate unavailable")

    raw_state = str(params.get("state", "") or "TX").strip().upper()
    state = raw_state if raw_state in STATE_FIPS else "TX"
    fips = STATE_FIPS[state]
    raw_county = str(params.get("county", "") or "").strip()
    county = raw_county if (re.fullmatch(r"\d{5}", raw_county)
                            and raw_county.startswith(fips)) else ""

    n_counties = _clamp_int(params.get("counties"), 10, 1, 25)
    n_rows = _clamp_int(params.get("rows"), 10, 1, 25)
    n_measures = _clamp_int(params.get("measures"), 10, 1, len(_PLACES_MEASURES))
    n_orgs = _clamp_int(params.get("orgs"), 10, 1, 20)

    state_name = _STATE_NAMES.get(state, state)
    ingested = _estate.ingested_counts()
    meta = (f"{state_name} ({state})"
            + (f" · county {county}" if county else "")
            + f" · fed by {len(ingested)} ingested connectors · "
              f"{sum(ingested.values()):,} rows on disk")

    sections = [
        _sec_demographics(state, fips, county, n_counties),
        _sec_health_burden(state, county, n_measures),
        _sec_provider_shortage(state, n_rows),
        _sec_medicare(state, fips, county, n_rows),
        _sec_facility_quality(state, n_rows),
        _sec_money_flow(state, n_rows),
        _sec_research(state, n_orgs),
        _sec_compliance(state, n_rows),
        _sec_labor(state, fips, n_rows),
        _sec_kidney_dialysis(state, county, n_rows),
        _sec_outpatient_universe(state, n_rows),
    ]
    body = (ck_page_title("Market Scan", eyebrow="Research · Public Data",
                          meta=meta)
            + _controls(state, county)
            + "".join(sections))
    return chartis_shell(
        body, "Market Scan", active_nav=_ROUTE,
        subtitle=f"PE-desk market brief · {state_name}")
