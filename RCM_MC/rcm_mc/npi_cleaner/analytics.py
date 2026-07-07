"""Population analytics — the Tuva-class layer on top of cleaning.

Validation says whether a cell is *right*; these marts say what the file
*means*: where care happened (service categories), how lines roll up to
visits (encounters), what the population carries (chronic conditions),
whether any month of data is missing (volume integrity), how often
inpatients bounce back (30-day readmissions), and which providers code
hotter than the file (E&M coding intensity). The Tuva Project computes
this class of output as a dbt pipeline over a warehouse; here it runs on
the already-cleaned table in the same pass, no warehouse, no setup.

Everything is REPORT-ONLY and guarded: a failure in any mart leaves the
cleaning result untouched. Row values arrive post-de-identification, so
patient ids may already be stable tokens — grouping still works because
the masking is referentially consistent within a run.

All heuristics are deliberately documented and simple enough to audit:

  * Service categories follow the institutional-first ladder clearinghouses
    use: Type of Bill decides the setting when present, then revenue code,
    then place of service, then the HCPCS range.
  * An encounter is a patient's consecutive same-category service dates
    with gaps ≤ 1 day (inpatient spans use admit→discharge when present).
  * A 30-day readmission is an inpatient encounter starting 1–30 days
    after the patient's previous inpatient encounter ended.
  * Coding intensity compares each provider's established-visit E&M mix
    (99211–99215) against the file's own mix; the national Medicare mix
    is shown for context only.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

_DATE_LEN = 10  # ISO prefix "YYYY-MM-DD" — cells are already normalized


def _iso(v: str) -> Optional[date]:
    s = v.strip()[:_DATE_LEN]
    if len(s) != 10:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _money(v: str) -> float:
    try:
        return float(v.replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return 0.0


# ------------------------------------------------------------ service mix --
_EM_OFFICE = {"99202", "99203", "99204", "99205",
              "99211", "99212", "99213", "99214", "99215"}
_EM_ED = {"99281", "99282", "99283", "99284", "99285"}


def classify_line(rev: str, tob: str, pos: str, hcpcs: str) -> Tuple[str, str]:
    """(category, subcategory) for one claim line. Institutional-first
    ladder: TOB → revenue code → POS → HCPCS range → Unclassified."""
    rev3 = "".join(c for c in rev.strip() if c.isdigit())[-4:].lstrip("0")
    rev3 = rev3.zfill(3) if rev3 else ""
    pos2 = pos.strip().zfill(2) if pos.strip().isdigit() else ""
    code = hcpcs.strip().upper()

    tob_digits = tob.strip()
    if len(tob_digits) == 4 and tob_digits.startswith("0"):
        tob_digits = tob_digits[1:]
    fac = tob_digits[0] if len(tob_digits) == 3 and tob_digits.isdigit() else ""

    # 1. Type of Bill decides the institutional setting.
    if fac == "1":
        if rev3[:2] == "45" or code in _EM_ED:
            return "Outpatient", "Emergency department"
        cls = tob_digits[1]
        if cls in ("1", "2"):
            return "Inpatient", "Acute inpatient"
        return "Outpatient", "Hospital outpatient"
    if fac == "2":
        return "Inpatient", "Skilled nursing"
    if fac == "3":
        return "Home health", "Home health"
    if fac == "7":
        if tob_digits[1] == "2":
            return "Outpatient", "Dialysis"
        return "Outpatient", "Clinic"
    if fac == "8":
        if tob_digits[1] in ("1", "2"):
            return "Hospice", "Hospice"
        if tob_digits[1] == "3":
            return "Outpatient", "Ambulatory surgery"
        return "Outpatient", "Special facility"

    # 2. Revenue code (institutional line without a usable TOB).
    if rev3:
        r2 = rev3[:2]
        if r2 == "45":
            return "Outpatient", "Emergency department"
        if r2 in ("01", "02", "10", "11", "12", "13", "14", "15",
                  "16", "17", "20", "21") and rev3 != "001":
            return "Inpatient", "Acute inpatient"
        if r2 in ("30", "31"):
            return "Ancillary", "Laboratory"
        if r2 in ("32", "35", "40", "61"):
            return "Ancillary", "Imaging"
        if r2 == "25":
            return "Pharmacy", "Facility pharmacy"
        if r2 == "54":
            return "Ancillary", "Ambulance"
        if r2 in ("42", "43", "44"):
            return "Outpatient", "Therapies (PT/OT/ST)"
        if r2 in ("80", "81", "82", "83", "84", "85"):
            return "Outpatient", "Dialysis"
        if r2 in ("90", "91"):
            return "Behavioral health", "Behavioral health"
        return "Outpatient", "Hospital outpatient"

    # 3. Place of service (professional lines).
    if pos2:
        if pos2 == "23":
            return "Outpatient", "Emergency department"
        if pos2 == "20":
            return "Outpatient", "Urgent care"
        if pos2 == "11":
            return "Office", ("Office visit (E&M)" if code in _EM_OFFICE
                              else "Office — other")
        if pos2 == "21":
            return "Inpatient", "Acute inpatient (professional)"
        if pos2 in ("19", "22", "24"):
            return "Outpatient", ("Ambulatory surgery" if pos2 == "24"
                                  else "Hospital outpatient")
        if pos2 in ("31", "32"):
            return "Inpatient", "Skilled nursing"
        if pos2 == "34":
            return "Hospice", "Hospice"
        if pos2 == "12":
            return "Home health", "Home (services)"
        if pos2 in ("52", "53", "57", "58"):
            return "Behavioral health", "Behavioral health"
        if pos2 == "81":
            return "Ancillary", "Laboratory"
        if pos2 == "65":
            return "Outpatient", "Dialysis"

    # 4. HCPCS range.
    if code:
        if code in _EM_ED:
            return "Outpatient", "Emergency department"
        if code in _EM_OFFICE:
            return "Office", "Office visit (E&M)"
        if code[:1] == "J":
            return "Pharmacy", "Drugs (J-codes)"
        if code[:1] == "A" and code[1:2] == "0":
            return "Ancillary", "Ambulance"
        if code[:1] in ("E", "K") and code[1:].isdigit():
            return "Ancillary", "DME"
        if code.isdigit():
            n = int(code)
            if 70000 <= n <= 79999:
                return "Ancillary", "Imaging"
            if 80000 <= n <= 89999:
                return "Ancillary", "Laboratory"
            if 90832 <= n <= 90899:
                return "Behavioral health", "Behavioral health"
            if 10000 <= n <= 69999:
                return "Outpatient", "Procedures / surgery"

    return "Unclassified", "Unclassified"


def _service_mix(rows, rev_i, tob_i, pos_i, hcpcs_i,
                 billed_i) -> Optional[Dict[str, object]]:
    if rev_i is None and tob_i is None and pos_i is None and hcpcs_i is None:
        return None
    tally: Dict[Tuple[str, str], List[float]] = {}
    for row in rows:
        def _get(i):
            return row[i] if i is not None and i < len(row) else ""
        cat, sub = classify_line(_get(rev_i), _get(tob_i),
                                 _get(pos_i), _get(hcpcs_i))
        agg = tally.setdefault((cat, sub), [0, 0.0])
        agg[0] += 1
        if billed_i is not None and billed_i < len(row):
            agg[1] += _money(row[billed_i])
    total = sum(a[0] for a in tally.values()) or 1
    cats = [{"category": c, "subcategory": s, "rows": int(a[0]),
             "pct": round(100.0 * a[0] / total, 1),
             "charges": round(a[1], 2)}
            for (c, s), a in tally.items()]
    cats.sort(key=lambda d: -d["rows"])  # type: ignore[operator]
    unclass = sum(d["rows"] for d in cats
                  if d["category"] == "Unclassified")
    return {"categories": cats,
            "unclassified_pct": round(100.0 * unclass / total, 1)}


# ------------------------------------------------------------- encounters --
def _build_encounters(rows, patient_i, dos_i, admit_i, disch_i,
                      rev_i, tob_i, pos_i, hcpcs_i, billed_i,
                      cap: int = 200_000,
                      readmit_window: int = 30) -> Optional[Dict[str, object]]:
    """Group lines → encounters: per patient, same top category, service
    dates chaining with gaps ≤ 1 day. Inpatient lines widen the window to
    admit→discharge when those dates parse."""
    if patient_i is None or dos_i is None:
        return None

    per_patient: Dict[str, List[Tuple[date, date, str, float]]] = {}
    skipped = 0
    for row in rows:
        if patient_i >= len(row) or dos_i >= len(row):
            continue
        pt = row[patient_i].strip()
        d0 = _iso(row[dos_i])
        if not pt or d0 is None:
            skipped += 1
            continue

        def _get(i):
            return row[i] if i is not None and i < len(row) else ""
        cat, _sub = classify_line(_get(rev_i), _get(tob_i),
                                  _get(pos_i), _get(hcpcs_i))
        d1 = d0
        if cat == "Inpatient":
            a = _iso(_get(admit_i))
            d = _iso(_get(disch_i))
            if a and d and a <= d:
                d0, d1 = a, d
        chg = _money(row[billed_i]) if (billed_i is not None
                                        and billed_i < len(row)) else 0.0
        lst = per_patient.setdefault(pt, [])
        if len(lst) < 50_000:  # one runaway patient id can't own the RAM
            lst.append((d0, d1, cat, chg))

    if not per_patient:
        return None

    encounters: List[Dict[str, object]] = []
    n_enc = 0
    by_cat: Dict[str, List[float]] = {}
    inpatient_spans: Dict[str, List[Tuple[date, date, int]]] = {}
    for pt, lines in per_patient.items():
        lines.sort(key=lambda t: (t[2], t[0]))
        cur = None  # [cat, start, end, n_lines, charges]
        for d0, d1, cat, chg in lines:
            if (cur is not None and cat == cur[0]
                    and (d0 - cur[2]).days <= 1):
                cur[2] = max(cur[2], d1)
                cur[3] += 1
                cur[4] += chg
                continue
            if cur is not None:
                n_enc += 1
                agg = by_cat.setdefault(cur[0], [0, 0, 0.0])
                agg[0] += 1
                agg[1] += cur[3]
                agg[2] += cur[4]
                if cur[0] == "Inpatient":
                    inpatient_spans.setdefault(pt, []).append(
                        (cur[1], cur[2], n_enc))
                if len(encounters) < cap:
                    encounters.append({
                        "patient": pt, "category": cur[0],
                        "start": cur[1].isoformat(),
                        "end": cur[2].isoformat(),
                        "lines": cur[3], "charges": round(cur[4], 2)})
            cur = [cat, d0, d1, 1, chg]
        if cur is not None:
            n_enc += 1
            agg = by_cat.setdefault(cur[0], [0, 0, 0.0])
            agg[0] += 1
            agg[1] += cur[3]
            agg[2] += cur[4]
            if cur[0] == "Inpatient":
                inpatient_spans.setdefault(pt, []).append(
                    (cur[1], cur[2], n_enc))
            if len(encounters) < cap:
                encounters.append({
                    "patient": pt, "category": cur[0],
                    "start": cur[1].isoformat(),
                    "end": cur[2].isoformat(),
                    "lines": cur[3], "charges": round(cur[4], 2)})

    # N-day readmissions over the inpatient spans just built (window is
    # profile-tunable — CMS uses 30, some programs 60/90).
    readmit = None
    index_stays = sum(len(v) for v in inpatient_spans.values())
    if index_stays:
        n_readmit = 0
        for spans in inpatient_spans.values():
            spans.sort()
            for i in range(1, len(spans)):
                gap = (spans[i][0] - spans[i - 1][1]).days
                if 1 <= gap <= readmit_window:
                    n_readmit += 1
        readmit = {"inpatient_stays": index_stays,
                   "readmissions_30d": n_readmit,
                   "window_days": readmit_window,
                   "rate_pct": round(100.0 * n_readmit
                                     / max(index_stays, 1), 1)}

    summary = [{"category": c, "encounters": int(a[0]),
                "avg_lines": round(a[1] / max(a[0], 1), 2),
                "charges": round(a[2], 2)}
               for c, a in sorted(by_cat.items(),
                                  key=lambda kv: -kv[1][0])]
    return {"n_encounters": n_enc,
            "n_patients": len(per_patient),
            "by_category": summary,
            "skipped_rows": skipped,
            "records": encounters,
            "records_truncated": n_enc > len(encounters),
            "readmissions": readmit}


# -------------------------------------------------------------- conditions --
def _conditions(rows, dx_cols, patient_i) -> Optional[Dict[str, object]]:
    if not dx_cols:
        return None
    try:
        from . import refdata as _rd
    except Exception:  # noqa: BLE001
        return None

    per_patient: Dict[str, set] = {}
    row_hits: Dict[str, int] = {}
    for ri, row in enumerate(rows):
        pt = (row[patient_i].strip()
              if patient_i is not None and patient_i < len(row) else f"#r{ri}")
        for ci in dx_cols:
            if ci >= len(row) or not row[ci]:
                continue
            for name in _rd.chronic_conditions_for(row[ci]):
                row_hits[name] = row_hits.get(name, 0) + 1
                if pt:
                    per_patient.setdefault(pt, set()).add(name)
    if not row_hits:
        return None

    n_pat = len(per_patient)
    cond_pat: Dict[str, int] = {}
    multimorbid = {"0": 0, "1": 0, "2": 0, "3+": 0}
    for conds in per_patient.values():
        for c in conds:
            cond_pat[c] = cond_pat.get(c, 0) + 1
        k = len(conds)
        multimorbid["3+" if k >= 3 else str(k)] += 1
    prevalence = [{"condition": c,
                   "patients": cond_pat.get(c, 0),
                   "pct": round(100.0 * cond_pat.get(c, 0)
                                / max(n_pat, 1), 1),
                   "rows": row_hits.get(c, 0)}
                  for c in sorted(cond_pat,
                                  key=lambda c: -cond_pat[c])]
    return {"patients": n_pat,
            "patient_grouping": patient_i is not None,
            "prevalence": prevalence[:25],
            "multimorbidity": multimorbid}


# ---------------------------------------------------------- volume by month --
def _volume(rows, dos_i, billed_i, patient_i) -> Optional[Dict[str, object]]:
    if dos_i is None:
        return None
    months: Dict[str, List[object]] = {}
    for row in rows:
        if dos_i >= len(row):
            continue
        m = row[dos_i].strip()[:7]
        if len(m) != 7 or m[4] != "-" or not m[:4].isdigit():
            continue
        agg = months.setdefault(m, [0, 0.0, set()])
        agg[0] += 1
        if billed_i is not None and billed_i < len(row):
            agg[1] += _money(row[billed_i])
        if patient_i is not None and patient_i < len(row) and row[patient_i]:
            if len(agg[2]) < 500_000:
                agg[2].add(row[patient_i])
    if len(months) < 2:
        return None
    # Observed per-patient-per-month charge — the PMPM proxy a payer-side
    # analyst reaches for first. "Observed" because the denominator is
    # patients WITH claims that month, not an eligibility member count
    # (there is no eligibility file here), so it reads high vs true PMPM.
    series = [{"month": m, "rows": int(a[0]),
               "charges": round(a[1], 2),
               "patients": (len(a[2]) if patient_i is not None else None),
               "observed_pmpm": (round(a[1] / len(a[2]), 2)
                                 if a[2] else None)}
              for m, a in sorted(months.items())]

    # Data-loss detection: an interior month at < 40% of the median of its
    # 3 predecessors is a cliff — almost always a missing extract, not a
    # real utilization collapse. First/last months are partial by nature.
    alerts: List[str] = []
    counts = [s["rows"] for s in series]
    for i in range(3, len(counts) - 1):
        prior = sorted(counts[i - 3:i])[1]  # median of 3
        if prior >= 50 and counts[i] < 0.4 * prior:
            alerts.append(
                f"{series[i]['month']}: {counts[i]:,} rows vs a trailing "
                f"median of {prior:,} — looks like missing data, not a "
                "real volume drop.")
    pmpms = sorted(s["observed_pmpm"] for s in series
                   if s["observed_pmpm"] is not None)
    median_pmpm = (round(pmpms[len(pmpms) // 2], 2) if pmpms else None)
    return {"months": series, "alerts": alerts,
            "median_observed_pmpm": median_pmpm}


# --------------------------------------------------------- coding intensity --
_EM_LEVEL = {"99211": 1, "99212": 2, "99213": 3, "99214": 4, "99215": 5}
_MIN_VISITS = 20


def _coding_intensity(rows, hcpcs_i, npi_i,
                      basis: str = "billing") -> Optional[Dict[str, object]]:
    """``basis`` labels which provider grain ``npi_i`` is: 'rendering'
    (individual clinician — the grain that actually finds hot coders) or
    'billing' (pay-to organization — in group practices hundreds of
    clinicians collapse into one org NPI and the outlier screen washes
    out). Renderers caption from ``provider_basis`` so the output never
    overstates what was measured."""
    if hcpcs_i is None or npi_i is None:
        return None
    per_prov: Dict[str, List[int]] = {}
    file_mix = [0, 0, 0, 0, 0]
    for row in rows:
        if hcpcs_i >= len(row) or npi_i >= len(row):
            continue
        lvl = _EM_LEVEL.get(row[hcpcs_i].strip())
        if not lvl:
            continue
        file_mix[lvl - 1] += 1
        npi = row[npi_i].strip()
        if npi:
            mix = per_prov.setdefault(npi, [0, 0, 0, 0, 0])
            mix[lvl - 1] += 1
    n_visits = sum(file_mix)
    if n_visits < _MIN_VISITS * 2:
        return None
    file_avg = (sum((i + 1) * c for i, c in enumerate(file_mix))
                / max(n_visits, 1))

    outliers = []
    rated = 0
    for npi, mix in per_prov.items():
        n = sum(mix)
        if n < _MIN_VISITS:
            continue
        rated += 1
        avg = sum((i + 1) * c for i, c in enumerate(mix)) / n
        hi_share = (mix[3] + mix[4]) / n
        file_hi = (file_mix[3] + file_mix[4]) / max(n_visits, 1)
        if avg >= file_avg + 0.75 or (file_hi > 0
                                      and hi_share >= min(0.95, 3 * file_hi)):
            outliers.append({
                "npi": npi, "visits": n,
                "avg_level": round(avg, 2),
                "level_4_5_pct": round(100.0 * hi_share, 1),
                "mix": {f"9921{i + 1}": mix[i] for i in range(5)}})
    outliers.sort(key=lambda d: -d["avg_level"])  # type: ignore[operator]

    try:
        from . import refdata as _rd
        national = dict(_rd.EM_ESTABLISHED_NATIONAL_MIX)
    except Exception:  # noqa: BLE001
        national = None
    return {"established_visits": n_visits,
            "file_avg_level": round(file_avg, 2),
            "file_mix": {f"9921{i + 1}": file_mix[i] for i in range(5)},
            "providers_rated": rated,
            "provider_basis": basis,
            "outliers": outliers[:15],
            "national_mix": national}


# ------------------------------------------------------------------- build --
def build(headers: List[str], rows: List[List[str]], idx: Dict[str, object],
          ) -> Optional[Dict[str, object]]:
    """Compute every mart that has the columns it needs; skip the rest.
    ``idx`` carries the engine's detected column indices by role."""
    if not rows:
        return None
    rev_set = idx.get("rev_set") or set()
    rev_i = min(rev_set) if rev_set else None
    dx_set = idx.get("dx_set") or set()
    pos_set = idx.get("pos_set") or set()
    pos_i = min(pos_set) if pos_set else None

    out: Dict[str, object] = {}
    mix = _service_mix(rows, rev_i, idx.get("tob_i"), pos_i,
                       idx.get("hcpcs_i"), idx.get("billed_i"))
    if mix:
        out["service_mix"] = mix
    enc = _build_encounters(rows, idx.get("patient_i"), idx.get("dos_i"),
                            idx.get("admit_i"), idx.get("disch_i"),
                            rev_i, idx.get("tob_i"), pos_i,
                            idx.get("hcpcs_i"), idx.get("billed_i"),
                            readmit_window=int(
                                idx.get("readmit_window") or 30))
    if enc:
        out["encounters"] = enc
    cond = _conditions(rows, sorted(dx_set), idx.get("patient_i"))
    if cond:
        out["conditions"] = cond
    vol = _volume(rows, idx.get("dos_i"), idx.get("billed_i"),
                  idx.get("patient_i"))
    if vol:
        out["volume"] = vol
    # Coding intensity prefers the rendering/attending clinician column
    # ('rendering_i', when the engine detected one) over the billing org:
    # per-provider E&M mix at org grain converges to the file mix in group
    # practices, hiding exactly the hot coders the screen exists to find.
    _rend_i = idx.get("rendering_i")
    _prov_i = _rend_i if _rend_i is not None else idx.get("billing_idx")
    ci = _coding_intensity(rows, idx.get("hcpcs_i"), _prov_i,
                           basis=("rendering" if _rend_i is not None
                                  else "billing"))
    if ci:
        out["coding_intensity"] = ci
    return out or None


def encounters_csv(population: Dict[str, object]) -> Optional[str]:
    """The encounter roll-up as CSV text (?fmt=encounters download)."""
    enc = (population or {}).get("encounters")
    if not isinstance(enc, dict) or not enc.get("records"):
        return None
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["encounter", "patient", "category", "start", "end",
                "lines", "charges"])
    for i, r in enumerate(enc["records"], start=1):
        w.writerow([i, r["patient"], r["category"], r["start"],
                    r["end"], r["lines"], r["charges"]])
    return buf.getvalue()
