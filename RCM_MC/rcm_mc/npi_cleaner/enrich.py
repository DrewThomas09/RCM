"""Selectable claims enrichment — the layer that makes a cleaned file
analysis-ready, not just clean.

The cleaner validates and repairs; this module ADDS: new columns appended
to the cleaned output (so the pivot page can slice by them immediately)
plus small report marts (top codes and their trend, revenue by key billing
provider, MSA/metro mix, a Medicare benchmark). Everything here follows
the connector house rules established in ``connectors.py``:

  * **Opt-in per enrichment.** The page shows one checkbox per enrichment
    (``registry()``) and the upload carries the selected ids — nothing
    runs unrequested, and network enrichments never run on an offline
    selection.
  * **Bounded.** Live lookups run over DISTINCT values only, capped per
    run, highest-dollar first, so a 600k-row file costs at most
    ``_MAX_MEDICARE_CODES + _MAX_MEDICARE_PROVIDERS`` HTTP calls.
  * **Guarded.** A missing pack, a blocked host, or a schema change on
    the public API degrades to an honest per-enrichment note — never an
    exception into the cleaning pipeline, and never a silent "worked".
  * **Injectable transport.** Every network path accepts an ``opener`` so
    tests run on a fake transport and never touch the internet.

Enrichments, by what they add:

  * ``service_category``   — offline; ``service_category`` /
    ``service_subcategory`` columns via the analytics classification
    ladder (TOB → revenue code → POS → HCPCS range).
  * ``taxonomy_specialty`` — offline; ``specialty_name`` column from the
    NUCC taxonomy (full pack when installed, curated subset otherwise).
  * ``geo_msa``            — offline (zip_cbsa pack); ``cbsa_code`` /
    ``cbsa_name`` columns + the metro-area mix mart. The crosswalk teams
    otherwise paste in by hand before any geographic pivot.
  * ``top_codes_trend``    — offline mart; top HCPCS by volume and
    dollars with a first-half vs second-half trend verdict.
  * ``provider_revenue``   — offline mart; billed dollars by billing NPI
    (key-player sizing) + HHI concentration.
  * ``medicare_hcpcs_benchmark`` — live (data.cms.gov, Medicare
    Physician & Other Practitioners by Geography & Service, national);
    ``medicare_avg_allowed`` column + file-vs-Medicare ratio mart — the
    matching basis for grossing commercial claims up to Medicare-
    equivalent dollars using the CMS output rather than a flat factor.
  * ``medicare_provider_volume`` — live (same family, by Provider);
    each key billing NPI's national Medicare services / beneficiaries /
    payments, so file volume reads against the provider's Medicare book.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Callable

# Per-run caps: distinct HCPCS codes / billing NPIs sent to data.cms.gov.
_MAX_MEDICARE_CODES = 40
_MAX_MEDICARE_PROVIDERS = 25
_FETCH_TIMEOUT_S = 30

# data.cms.gov Data API endpoints (JSON). UUIDs are release-specific and
# roll with new vintages, so both accept an environment override — a
# stale default degrades to a per-run note, never a crash. The by-Provider
# default mirrors cms_api_client.DATASET_IDS["provider_utilization_2022"],
# inlined rather than imported: rcm_mc.data_public's package __init__
# pulls numpy/pandas, and this module must stay importable on the
# cleaner's stdlib-only deployments.
_CMS_GEO_SERVICE_URL = (
    "https://data.cms.gov/data-api/v1/dataset/"
    "6fea9d79-0129-4e4c-b1b8-23cd86a4f435/data")
_CMS_BY_PROVIDER_URL = (
    "https://data.cms.gov/data-api/v1/dataset/"
    "8889d81e-2ee7-448f-8713-f071038289bf/data")
_ENV_GEO_SERVICE = "RCM_MC_CMS_GEO_SERVICE_URL"
_ENV_BY_PROVIDER = "RCM_MC_CMS_BY_PROVIDER_URL"

_MONEY_RE = re.compile(r"[^0-9.\-]")

OFFLINE_IDS = ("service_category", "taxonomy_specialty", "geo_msa",
               "top_codes_trend", "provider_revenue")
NETWORK_IDS = ("medicare_hcpcs_benchmark", "medicare_provider_volume")
ALL_IDS = OFFLINE_IDS + NETWORK_IDS


def _money(v: object) -> float | None:
    s = _MONEY_RE.sub("", str(v or ""))
    if not s or s in ("-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _digits(v: object) -> str:
    return "".join(c for c in str(v or "") if c.isdigit())


def _cell(row: list[str], i: int | None) -> str:
    return row[i] if i is not None and i < len(row) else ""


def _zip_cbsa_installed() -> bool:
    try:
        from . import refdata_packs
        for p in refdata_packs.status():
            if p.get("id") == "zip_cbsa":
                return bool(p.get("installed"))
    except Exception:
        pass
    return False


def _by_provider_url() -> str:
    return os.environ.get(_ENV_BY_PROVIDER) or _CMS_BY_PROVIDER_URL


def _geo_service_url() -> str:
    return os.environ.get(_ENV_GEO_SERVICE) or _CMS_GEO_SERVICE_URL


# --------------------------------------------------------------- registry --
def registry() -> list[dict[str, object]]:
    """One entry per selectable enrichment for the page's checkbox panel.

    ``status`` is the honest availability claim: ``ready`` (will act on a
    run today), ``needs_data`` (applicable but its reference pack isn't
    installed), ``network`` (live opt-in — runs only when selected, on a
    host with outbound HTTPS). ``adds`` names the columns appended to the
    cleaned file so users know what the pivot gains before they run."""
    zip_ok = _zip_cbsa_installed()
    out: list[dict[str, object]] = [
        {"id": "service_category", "label": "Care-setting classification",
         "group": "offline",
         "description": ("Classify every line by the institutional-first "
                         "ladder (type of bill → revenue code → place of "
                         "service → HCPCS range) and write the setting "
                         "onto each row."),
         "adds": ["service_category", "service_subcategory"],
         "mode": "offline", "status": "ready", "default": True,
         "reason": "Runs offline on every file with any service column."},
        {"id": "taxonomy_specialty", "label": "Specialty names (NUCC)",
         "group": "offline",
         "description": ("Resolve provider taxonomy codes to display "
                         "specialty names — full NUCC catalog when the "
                         "taxonomy pack is installed, curated subset "
                         "otherwise."),
         "adds": ["specialty_name"],
         "mode": "offline", "status": "ready", "default": True,
         "reason": "Needs a taxonomy column; skipped silently without one."},
        {"id": "geo_msa", "label": "MSA / CBSA geography",
         "group": "offline",
         "description": ("Crosswalk ZIP codes to CBSA metro/micro areas "
                         "(Census ZCTA↔CBSA) so the file pivots by "
                         "market, and roll up the metro-area mix."),
         "adds": ["cbsa_code", "cbsa_name"],
         "mode": "offline",
         "status": "ready" if zip_ok else "needs_data",
         "default": zip_ok,
         "reason": ("ZIP→CBSA pack installed." if zip_ok else
                    "Pull the 'ZIP → CBSA/MSA crosswalk' reference pack "
                    "below to activate (one click, Census public file).")},
        {"id": "top_codes_trend", "label": "Top codes & trend",
         "group": "offline",
         "description": ("Top HCPCS codes by volume and dollars, with a "
                         "first-half vs second-half trend verdict per "
                         "code — the utilization narrative of the file."),
         "adds": [],
         "mode": "offline", "status": "ready", "default": True,
         "reason": "Report mart — needs a procedure-code column."},
        {"id": "provider_revenue", "label": "Key players — revenue sizing",
         "group": "offline",
         "description": ("Billed dollars by billing NPI with share of "
                         "file and HHI concentration — who the revenue "
                         "actually runs through."),
         "adds": [],
         "mode": "offline", "status": "ready", "default": True,
         "reason": "Report mart — needs billing NPI + an amount column."},
        {"id": "medicare_hcpcs_benchmark",
         "label": "Medicare rate benchmark (CMS)",
         "group": "network",
         "description": ("Match the file's top procedure codes to the "
                         "CMS national Medicare average allowed amount "
                         "(Physician & Other Practitioners, by Geography "
                         "& Service) — the matching basis for grossing "
                         "commercial claims up to Medicare-equivalent "
                         "dollars."),
         "adds": ["medicare_avg_allowed"],
         "mode": "network", "status": "network", "default": False,
         "reason": (f"Live data.cms.gov lookup, capped at "
                    f"{_MAX_MEDICARE_CODES} distinct codes "
                    "(highest-dollar first).")},
        {"id": "medicare_provider_volume",
         "label": "Medicare volumes for key providers (CMS)",
         "group": "network",
         "description": ("Pull each key billing NPI's national Medicare "
                         "services, beneficiaries and payments (by "
                         "Provider) so file volume reads against the "
                         "provider's Medicare book — sizing, not "
                         "guessing."),
         "adds": [],
         "mode": "network", "status": "network", "default": False,
         "reason": (f"Live data.cms.gov lookup, capped at "
                    f"{_MAX_MEDICARE_PROVIDERS} billing NPIs "
                    "(highest-dollar first).")},
    ]
    return out


def valid_ids(selected: list[str] | None) -> list[str]:
    """The subset of ``selected`` that names a real enrichment, original
    order preserved, duplicates dropped."""
    seen: list[str] = []
    for s in selected or []:
        sid = str(s or "").strip()
        if sid in ALL_IDS and sid not in seen:
            seen.append(sid)
    return seen


# ------------------------------------------------------------ network I/O --
def _fetch_json(url: str, opener: Callable | None = None) -> list[dict]:
    op = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={
        "User-Agent": "rcm-mc-npi-cleaner/1.0 (claims enrichment)",
        "Accept": "application/json"})
    with op(req, timeout=_FETCH_TIMEOUT_S) as resp:
        raw = resp.read()
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    return payload if isinstance(payload, list) else []


def _row_get(row: dict, *names: str) -> str | None:
    """Case-insensitive multi-alias field read — CMS column headers vary
    in case across releases."""
    lowered = {str(k).lower(): v for k, v in row.items()}
    for n in names:
        v = lowered.get(n.lower())
        if v is not None and str(v).strip() != "":
            return str(v)
    return None


# ------------------------------------------------------- column appliers --
def _apply_service_category(headers, rows, idx) -> dict | None:
    rev_set = idx.get("rev_set") or set()
    pos_set = idx.get("pos_set") or set()
    rev_i = min(rev_set) if rev_set else None
    pos_i = min(pos_set) if pos_set else None
    tob_i, hcpcs_i = idx.get("tob_i"), idx.get("hcpcs_i")
    if rev_i is None and tob_i is None and pos_i is None and hcpcs_i is None:
        return {"id": "service_category",
                "label": "Care-setting classification",
                "rows_enriched": 0, "columns_added": [],
                "note": "No service columns (TOB / revenue code / POS / "
                        "HCPCS) — nothing to classify."}
    from . import analytics as _analytics
    cats: list[str] = []
    subs: list[str] = []
    n = 0
    for row in rows:
        cat, sub = _analytics.classify_line(
            _cell(row, rev_i), _cell(row, tob_i),
            _cell(row, pos_i), _cell(row, hcpcs_i))
        cats.append(cat)
        subs.append(sub)
        if cat != "Unclassified":
            n += 1
    return {"id": "service_category",
            "label": "Care-setting classification",
            "rows_enriched": n,
            "columns_added": ["service_category", "service_subcategory"],
            "columns": [("service_category", cats),
                        ("service_subcategory", subs)],
            "note": f"{n:,} of {len(rows):,} lines classified to a care "
                    "setting."}


def _apply_taxonomy_specialty(headers, rows, idx) -> dict | None:
    taxo_set = idx.get("taxo_set") or set()
    if not taxo_set:
        return {"id": "taxonomy_specialty", "label": "Specialty names (NUCC)",
                "rows_enriched": 0, "columns_added": [],
                "note": "No taxonomy column in this file."}
    t_i = min(taxo_set)
    from . import refdata as _rd
    cache: dict[str, str] = {}
    vals: list[str] = []
    n = 0
    for row in rows:
        code = _cell(row, t_i).strip().upper()
        if not code:
            vals.append("")
            continue
        if code not in cache:
            cache[code] = _rd.taxonomy_specialty(code) or ""
        vals.append(cache[code])
        if cache[code]:
            n += 1
    resolved = sum(1 for v in cache.values() if v)
    return {"id": "taxonomy_specialty", "label": "Specialty names (NUCC)",
            "rows_enriched": n, "columns_added": ["specialty_name"],
            "columns": [("specialty_name", vals)],
            "note": f"{resolved} of {len(cache)} distinct taxonomy codes "
                    "resolved to a specialty name."}


def _apply_geo_msa(headers, rows, idx) -> dict | None:
    zip_set = idx.get("zip_set") or set()
    if not zip_set:
        return {"id": "geo_msa", "label": "MSA / CBSA geography",
                "rows_enriched": 0, "columns_added": [],
                "note": "No ZIP column in this file."}
    try:
        from . import refdata_packs
        lookup = refdata_packs.zip_cbsa_lookup()
    except Exception:
        lookup = None
    if not lookup:
        return {"id": "geo_msa", "label": "MSA / CBSA geography",
                "rows_enriched": 0, "columns_added": [],
                "note": "ZIP→CBSA pack not installed — pull the 'ZIP → "
                        "CBSA/MSA crosswalk' reference pack to activate."}
    z_i = min(zip_set)
    billed_i = idx.get("billed_i")
    codes: list[str] = []
    names: list[str] = []
    n = 0
    seen_zip = 0
    tally: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        z5 = _digits(_cell(row, z_i))[:5]
        hit = lookup.get(z5) if len(z5) == 5 else None
        if len(z5) == 5:
            seen_zip += 1
        if hit:
            codes.append(hit[0])
            names.append(hit[1])
            n += 1
            agg = tally.setdefault(hit, [0, 0.0])
        else:
            codes.append("")
            names.append("")
            agg = None
        if agg is not None:
            agg[0] += 1
            amt = _money(_cell(row, billed_i))
            if amt is not None:
                agg[1] += amt
    total_dollars = sum(a[1] for a in tally.values()) or 0.0
    areas = [{"cbsa": c, "name": nm, "lines": int(a[0]),
              "charges": round(a[1], 2),
              "pct_dollars": (round(100.0 * a[1] / total_dollars, 1)
                              if total_dollars else None)}
             for (c, nm), a in tally.items()]
    areas.sort(key=lambda d: (-(d["charges"] or 0), -d["lines"]))
    unmatched_pct = (round(100.0 * (seen_zip - n) / seen_zip, 1)
                     if seen_zip else None)
    return {"id": "geo_msa", "label": "MSA / CBSA geography",
            "rows_enriched": n,
            "columns_added": ["cbsa_code", "cbsa_name"],
            "columns": [("cbsa_code", codes), ("cbsa_name", names)],
            "mart": ("geography", {"areas": areas[:25],
                                   "n_areas": len(areas),
                                   "unmatched_pct": unmatched_pct}),
            "note": f"{n:,} of {seen_zip:,} ZIP-bearing lines mapped to "
                    f"{len(areas)} CBSA metro/micro areas."}


# --------------------------------------------------------------- marts --
def _mart_top_codes(headers, rows, idx) -> dict | None:
    hcpcs_i = idx.get("hcpcs_i")
    if hcpcs_i is None:
        return {"id": "top_codes_trend", "label": "Top codes & trend",
                "rows_enriched": 0, "columns_added": [],
                "note": "No procedure-code column in this file."}
    billed_i, dos_i = idx.get("billed_i"), idx.get("dos_i")
    per_code: dict[str, list[object]] = {}
    for row in rows:
        code = _cell(row, hcpcs_i).strip().upper()
        if not code:
            continue
        agg = per_code.setdefault(code, [0, 0.0, {}])
        agg[0] += 1
        amt = _money(_cell(row, billed_i))
        if amt is not None:
            agg[1] += amt
        if dos_i is not None:
            m = _cell(row, dos_i).strip()[:7]
            if len(m) == 7 and m[4] == "-" and m[:4].isdigit():
                agg[2][m] = agg[2].get(m, 0) + 1
    if not per_code:
        return {"id": "top_codes_trend", "label": "Top codes & trend",
                "rows_enriched": 0, "columns_added": [],
                "note": "Procedure column present but no codes parsed."}
    total_dollars = sum(a[1] for a in per_code.values()) or 0.0

    def _trend(months: dict[str, int]) -> dict | None:
        if len(months) < 4:
            return None
        keys = sorted(months)
        half = len(keys) // 2
        first = sum(months[k] for k in keys[:half]) / max(half, 1)
        second = (sum(months[k] for k in keys[half:])
                  / max(len(keys) - half, 1))
        if first <= 0:
            return None
        change = 100.0 * (second - first) / first
        direction = ("rising" if change >= 10
                     else "falling" if change <= -10 else "flat")
        return {"direction": direction, "change_pct": round(change, 1),
                "window": f"{keys[0]}–{keys[-1]}"}

    try:
        from . import refdata_packs as _packs
    except Exception:
        _packs = None
    ranked = sorted(per_code.items(), key=lambda kv: (-kv[1][1], -kv[1][0]))
    codes = []
    for code, agg in ranked[:20]:
        desc = None
        if _packs is not None:
            try:
                desc = _packs.hcpcs_display(code)
            except Exception:
                desc = None
        codes.append({
            "code": code, "description": desc or "",
            "lines": int(agg[0]), "charges": round(agg[1], 2),
            "pct_dollars": (round(100.0 * agg[1] / total_dollars, 1)
                            if total_dollars else None),
            "trend": _trend(agg[2]),
        })
    return {"id": "top_codes_trend", "label": "Top codes & trend",
            "rows_enriched": 0, "columns_added": [],
            "mart": ("top_codes", {"codes": codes,
                                   "distinct_codes": len(per_code)}),
            "note": f"{len(per_code):,} distinct procedure codes ranked "
                    "by billed dollars."}


def _mart_provider_revenue(headers, rows, idx) -> dict | None:
    billing_idx = idx.get("billing_idx")
    if billing_idx is None:
        return {"id": "provider_revenue",
                "label": "Key players — revenue sizing",
                "rows_enriched": 0, "columns_added": [],
                "note": "No billing NPI column in this file."}
    billed_i, name_i = idx.get("billed_i"), idx.get("name_idx")
    per_npi: dict[str, list[object]] = {}
    for row in rows:
        npi = _digits(_cell(row, billing_idx))
        if len(npi) != 10:
            continue
        agg = per_npi.setdefault(npi, [0, 0.0, ""])
        agg[0] += 1
        amt = _money(_cell(row, billed_i))
        if amt is not None:
            agg[1] += amt
        if not agg[2] and name_i is not None:
            agg[2] = _cell(row, name_i).strip()
    if not per_npi:
        return {"id": "provider_revenue",
                "label": "Key players — revenue sizing",
                "rows_enriched": 0, "columns_added": [],
                "note": "Billing column present but no 10-digit NPIs."}
    total = sum(a[1] for a in per_npi.values()) or 0.0
    hhi = (round(sum((100.0 * a[1] / total) ** 2
                     for a in per_npi.values()))
           if total else None)
    ranked = sorted(per_npi.items(), key=lambda kv: (-kv[1][1], -kv[1][0]))
    providers = [{"npi": npi, "name": a[2], "lines": int(a[0]),
                  "charges": round(a[1], 2),
                  "pct_dollars": (round(100.0 * a[1] / total, 1)
                                  if total else None)}
                 for npi, a in ranked[:15]]
    return {"id": "provider_revenue",
            "label": "Key players — revenue sizing",
            "rows_enriched": 0, "columns_added": [],
            "mart": ("provider_revenue",
                     {"providers": providers,
                      "n_providers": len(per_npi), "hhi": hhi}),
            "note": f"{len(per_npi):,} distinct billing NPIs; "
                    f"top {len(providers)} carry "
                    f"{sum(p['pct_dollars'] or 0 for p in providers):.1f}% "
                    "of billed dollars."}


# ---------------------------------------------------- Medicare (network) --
def _medicare_benchmark(headers, rows, idx, opener) -> dict | None:
    hcpcs_i = idx.get("hcpcs_i")
    if hcpcs_i is None:
        return {"id": "medicare_hcpcs_benchmark",
                "label": "Medicare rate benchmark (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": "No procedure-code column in this file."}
    billed_i = idx.get("billed_i")
    per_code: dict[str, list[float]] = {}
    for row in rows:
        code = _cell(row, hcpcs_i).strip().upper()
        if not code or not re.fullmatch(r"[A-Z0-9]{5}", code):
            continue
        agg = per_code.setdefault(code, [0, 0.0])
        agg[0] += 1
        amt = _money(_cell(row, billed_i))
        if amt is not None:
            agg[1] += amt
    if not per_code:
        return {"id": "medicare_hcpcs_benchmark",
                "label": "Medicare rate benchmark (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": "No HCPCS/CPT-shaped codes to benchmark."}
    base = _geo_service_url()
    ranked = sorted(per_code.items(), key=lambda kv: (-kv[1][1], -kv[1][0]))
    targets = [c for c, _a in ranked[:_MAX_MEDICARE_CODES]]
    bench: dict[str, dict] = {}
    errors = 0
    for code in targets:
        qs = urllib.parse.urlencode({
            "filter[Rndrng_Prvdr_Geo_Lvl]": "National",
            "filter[HCPCS_Cd]": code,
            "size": "10"})
        try:
            recs = _fetch_json(f"{base}?{qs}", opener)
        except Exception:
            errors += 1
            continue
        tot_srv = 0.0
        w_allowed = 0.0
        w_payment = 0.0
        for r in recs:
            if not isinstance(r, dict):
                continue
            srv = _money(_row_get(r, "Tot_Srvcs", "tot_srvcs")) or 0.0
            alw = _money(_row_get(r, "Avg_Mdcr_Alowd_Amt",
                                  "avg_mdcr_alowd_amt"))
            pay = _money(_row_get(r, "Avg_Mdcr_Pymt_Amt",
                                  "avg_mdcr_pymt_amt"))
            if alw is None:
                continue
            w = srv if srv > 0 else 1.0
            tot_srv += w
            w_allowed += alw * w
            if pay is not None:
                w_payment += pay * w
        if tot_srv > 0:
            bench[code] = {
                "avg_allowed": round(w_allowed / tot_srv, 2),
                "avg_payment": (round(w_payment / tot_srv, 2)
                                if w_payment else None),
                "services": int(tot_srv)}
    if targets and errors == len(targets):
        return {"id": "medicare_hcpcs_benchmark",
                "label": "Medicare rate benchmark (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": f"Could not reach data.cms.gov — all {errors} "
                        "code lookups failed (network/connectivity). Set "
                        f"{_ENV_GEO_SERVICE} if the dataset UUID rolled."}

    # Row-level column + rollup on matched lines.
    col: list[str] = []
    matched_lines = 0
    matched_dollars = 0.0
    equivalent = 0.0
    code_file: dict[str, list[float]] = {}
    for row in rows:
        code = _cell(row, hcpcs_i).strip().upper()
        b = bench.get(code)
        if not b:
            col.append("")
            continue
        col.append(f"{b['avg_allowed']:.2f}")
        matched_lines += 1
        equivalent += b["avg_allowed"]
        amt = _money(_cell(row, billed_i))
        if amt is not None:
            matched_dollars += amt
            cf = code_file.setdefault(code, [0, 0.0])
            cf[0] += 1
            cf[1] += amt
    pct = (round(100.0 * matched_dollars / equivalent, 1)
           if equivalent else None)
    codes_out = []
    for code, b in bench.items():
        cf = code_file.get(code)
        file_avg = (round(cf[1] / cf[0], 2) if cf and cf[0] else None)
        ratio = (round(file_avg / b["avg_allowed"], 2)
                 if file_avg is not None and b["avg_allowed"] else None)
        codes_out.append({
            "code": code, "file_avg_charge": file_avg,
            "medicare_avg_allowed": b["avg_allowed"],
            "medicare_avg_payment": b.get("avg_payment"),
            "medicare_services": b.get("services"),
            "ratio": ratio,
            "file_dollars": (round(cf[1], 2) if cf else None)})
    codes_out.sort(key=lambda d: -(d.get("file_dollars") or 0.0))
    note = (f"{len(bench)} of {len(targets)} codes matched the CMS "
            "national benchmark")
    if len(per_code) > len(targets):
        note += (f" (capped at {_MAX_MEDICARE_CODES} highest-dollar of "
                 f"{len(per_code):,} distinct codes)")
    if errors:
        note += f"; {errors} lookup errors (skipped)"
    return {"id": "medicare_hcpcs_benchmark",
            "label": "Medicare rate benchmark (CMS)",
            "rows_enriched": matched_lines,
            "columns_added": (["medicare_avg_allowed"] if bench else []),
            "columns": ([("medicare_avg_allowed", col)] if bench else []),
            "mart": ("medicare_benchmark", {
                "codes": codes_out[:20],
                "matched_lines": matched_lines,
                "matched_dollars": round(matched_dollars, 2),
                "medicare_equivalent_dollars": round(equivalent, 2),
                "pct_of_medicare": pct,
                "source": "Medicare Physician & Other Practitioners — by "
                          "Geography and Service (national), data.cms.gov",
                "note": "Medicare-equivalent dollars price each matched "
                        "line at the CMS national average allowed amount "
                        "— a gross-up basis from the CMS output, not a "
                        "flat factor."}),
            "note": note + "."}


def _medicare_provider_volume(headers, rows, idx, opener) -> dict | None:
    billing_idx = idx.get("billing_idx")
    if billing_idx is None:
        return {"id": "medicare_provider_volume",
                "label": "Medicare volumes for key providers (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": "No billing NPI column in this file."}
    base = _by_provider_url()
    if not base:
        return {"id": "medicare_provider_volume",
                "label": "Medicare volumes for key providers (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": "CMS by-Provider dataset endpoint unavailable — "
                        f"set {_ENV_BY_PROVIDER}."}
    billed_i = idx.get("billed_i")
    per_npi: dict[str, float] = {}
    for row in rows:
        npi = _digits(_cell(row, billing_idx))
        if len(npi) != 10:
            continue
        amt = _money(_cell(row, billed_i)) or 0.0
        per_npi[npi] = per_npi.get(npi, 0.0) + amt
    if not per_npi:
        return {"id": "medicare_provider_volume",
                "label": "Medicare volumes for key providers (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": "Billing column present but no 10-digit NPIs."}
    targets = [n for n, _d in sorted(per_npi.items(),
                                     key=lambda kv: -kv[1])
               ][:_MAX_MEDICARE_PROVIDERS]
    found: dict[str, dict] = {}
    errors = 0
    for npi in targets:
        qs = urllib.parse.urlencode({"filter[Rndrng_NPI]": npi, "size": "1"})
        try:
            recs = _fetch_json(f"{base}?{qs}", opener)
        except Exception:
            errors += 1
            continue
        if not recs or not isinstance(recs[0], dict):
            continue
        r = recs[0]
        found[npi] = {
            "npi": npi,
            "name": (_row_get(r, "Rndrng_Prvdr_Last_Org_Name",
                              "Rndrng_Prvdr_Org_Name") or ""),
            "provider_type": _row_get(r, "Rndrng_Prvdr_Type",
                                      "provider_type") or "",
            "state": _row_get(r, "Rndrng_Prvdr_State_Abrvtn",
                              "state") or "",
            "medicare_services": _money(_row_get(r, "Tot_Srvcs",
                                                 "total_services")),
            "medicare_benes": _money(_row_get(r, "Tot_Benes",
                                              "total_unique_benes")),
            "medicare_payment": _money(_row_get(
                r, "Tot_Mdcr_Pymt_Amt", "total_medicare_payment_amt")),
            "medicare_charges": _money(_row_get(
                r, "Tot_Sbmtd_Chrg", "total_submitted_chrg_amt")),
            "file_dollars": round(per_npi[npi], 2),
        }
    if targets and errors == len(targets):
        return {"id": "medicare_provider_volume",
                "label": "Medicare volumes for key providers (CMS)",
                "rows_enriched": 0, "columns_added": [],
                "note": f"Could not reach data.cms.gov — all {errors} "
                        "NPI lookups failed (network/connectivity). Set "
                        f"{_ENV_BY_PROVIDER} if the dataset UUID rolled."}
    note = (f"{len(found)} of {len(targets)} key billing NPIs matched a "
            "Medicare by-Provider record")
    if len(per_npi) > len(targets):
        note += (f" (capped at {_MAX_MEDICARE_PROVIDERS} highest-dollar "
                 f"of {len(per_npi):,} NPIs)")
    if errors:
        note += f"; {errors} lookup errors (skipped)"
    return {"id": "medicare_provider_volume",
            "label": "Medicare volumes for key providers (CMS)",
            "rows_enriched": len(found), "columns_added": [],
            "mart": ("medicare_providers", {
                "providers": sorted(found.values(),
                                    key=lambda d: -(d["file_dollars"] or 0)),
                "source": "Medicare Physician & Other Practitioners — by "
                          "Provider, data.cms.gov"}),
            "note": note + "."}


# ------------------------------------------------------------------ apply --
_APPLIERS = {
    "service_category": _apply_service_category,
    "taxonomy_specialty": _apply_taxonomy_specialty,
    "geo_msa": _apply_geo_msa,
    "top_codes_trend": _mart_top_codes,
    "provider_revenue": _mart_provider_revenue,
}
_NETWORK_APPLIERS = {
    "medicare_hcpcs_benchmark": _medicare_benchmark,
    "medicare_provider_volume": _medicare_provider_volume,
}


def apply(headers: list[str], rows: list[list[str]],
          idx: dict[str, object], selected: list[str], *,
          opener: Callable | None = None,
          progress: Callable[[str, float], None] | None = None,
          ) -> dict[str, object]:
    """Run the selected enrichments over the cleaned table.

    Returns ``{"added_headers", "added_columns", "marts", "results",
    "requested"}``. ``added_columns`` is column-major (one list per added
    header, aligned to ``rows``) — the engine appends them to the output
    so the pivot/workbook/CSV all gain the fields. Never raises for a
    single enrichment's failure; each failure becomes an honest note."""
    ids = valid_ids(selected)
    added_headers: list[str] = []
    added_columns: list[list[str]] = []
    marts: dict[str, object] = {}
    results: list[dict] = []
    existing = {str(h).strip().lower() for h in headers}

    def _unique(name: str) -> str:
        base = name
        k = 2
        while name.lower() in existing:
            name = f"{base}_{k}"
            k += 1
        existing.add(name.lower())
        return name

    n_ids = max(len(ids), 1)
    for pos, eid in enumerate(ids):
        if progress:
            progress(f"Enriching — {eid.replace('_', ' ')}",
                     0.86 + 0.03 * pos / n_ids)
        try:
            if eid in _NETWORK_APPLIERS:
                out = _NETWORK_APPLIERS[eid](headers, rows, idx, opener)
            else:
                out = _APPLIERS[eid](headers, rows, idx)
        except Exception as exc:
            out = {"id": eid, "label": eid,
                   "rows_enriched": 0, "columns_added": [],
                   "note": f"Enrichment failed: {type(exc).__name__}: "
                           f"{exc}"}
        if not out:
            continue
        cols = out.pop("columns", None) or []
        renamed: list[str] = []
        for name, values in cols:
            uname = _unique(str(name))
            renamed.append(uname)
            added_headers.append(uname)
            # Defensive alignment: a mismatched applier must not shear
            # the output table.
            vals = list(values)[:len(rows)]
            vals += [""] * (len(rows) - len(vals))
            added_columns.append(vals)
        if renamed:
            out["columns_added"] = renamed
        mart = out.pop("mart", None)
        if mart:
            marts[mart[0]] = mart[1]
        results.append(out)

    # Medicare provider volumes fold into the key-players mart when both
    # ran — one table, file dollars next to the Medicare book.
    mp = marts.get("medicare_providers")
    pr = marts.get("provider_revenue")
    if isinstance(mp, dict) and isinstance(pr, dict):
        by_npi = {p.get("npi"): p for p in (mp.get("providers") or [])
                  if isinstance(p, dict)}
        for p in (pr.get("providers") or []):
            hit = by_npi.get(p.get("npi"))
            if hit:
                p["medicare_services"] = hit.get("medicare_services")
                p["medicare_benes"] = hit.get("medicare_benes")
                p["medicare_payment"] = hit.get("medicare_payment")
                p["provider_type"] = hit.get("provider_type")

    return {"added_headers": added_headers,
            "added_columns": added_columns,
            "marts": marts, "results": results, "requested": ids}
