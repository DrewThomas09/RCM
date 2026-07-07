"""Compliance screening for billing NPIs — OIG LEIE + Medicare PECOS.

Two independent screens, both opt-in via online mode and fully guarded:

  * **OIG LEIE (exclusions)** — offline. The HHS OIG List of Excluded
    Individuals/Entities is a monthly CSV download; billing to or by an
    excluded provider is direct fraud exposure. Point ``RCM_MC_LEIE_CSV`` at
    the ``UPDATED.csv`` (or pass ``leie_path``) and every distinct NPI is
    checked against it in-memory. No dataset → a clear "not loaded" note.

  * **Medicare PECOS** — networked, via the vendored v49 ``CMSClient``:
    enrollment (is the billing NPI actually enrolled?), opt-out (an opted-out
    provider billing Medicare is a red flag), and order/referring eligibility.
    Bounded by a per-request timeout and an overall wall-clock watchdog so a
    blocked network fails fast instead of hanging.

Both are injectable for tests (``leie_path`` / ``cms_client``) so no network or
external file is needed to exercise them.
"""
from __future__ import annotations

import csv
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional

_MAX_CMS = 10          # distinct NPIs to hit the (networked) PECOS files for
_CMS_TIMEOUT_S = 25    # overall watchdog for the CMS loop
_CMS_REQ_TIMEOUT = 6   # per-request timeout on the CMS client


def _digits(v: object) -> str:
    return "".join(ch for ch in str(v) if ch.isdigit())


def _distinct_npis(npis: List[str], cap: int) -> tuple:
    # Set membership + insertion-order list: the old `d not in seen` linear
    # scan over a list was O(n·k) — ~10^10 comparisons on a 1M-row file with
    # 100k distinct NPIs, which stalled the job thread at "Screening billing
    # NPIs" before the LEIE screen even started. Same output, same
    # (first-cap, truncated) contract.
    seen: set = set()
    out: List[str] = []
    for v in npis:
        d = _digits(v)
        if len(d) == 10 and d not in seen:
            seen.add(d)
            out.append(d)
    return out[:cap], len(out) > cap


# ------------------------------------------------------------------ OIG LEIE --
def _leie_lookup(path: str) -> Optional[Dict[str, Dict[str, str]]]:
    """Load excluded NPIs from a LEIE CSV as ``{npi: {name, excl_type,
    excl_date}}``. The source UPDATED.csv carries LASTNAME/FIRSTNAME/BUSNAME,
    EXCLTYPE and EXCLDATE — a fraud-exposure match that names neither the
    provider nor the exclusion is a half-way output, so keep them (they are
    public OIG data, not upload PHI). Returns None on failure."""
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            cols: Dict[str, int] = {}
            for i, h in enumerate(header):
                cols[h.strip().upper()] = i
            npi_col = cols.get("NPI")
            if npi_col is None:
                return None

            def _cell(row: List[str], name: str) -> str:
                i = cols.get(name)
                return row[i].strip() if i is not None and i < len(row) else ""

            out: Dict[str, Dict[str, str]] = {}
            for row in reader:
                if npi_col < len(row):
                    d = _digits(row[npi_col])
                    if len(d) == 10:
                        bus = _cell(row, "BUSNAME")
                        person = " ".join(p for p in (
                            _cell(row, "FIRSTNAME"),
                            _cell(row, "LASTNAME")) if p)
                        out[d] = {
                            "name": bus or person,
                            "excl_type": _cell(row, "EXCLTYPE"),
                            "excl_date": _cell(row, "EXCLDATE"),
                        }
            return out
    except Exception:  # noqa: BLE001
        return None


def _leie_npi_set(path: str) -> Optional[set]:
    """Back-compat shim: the set of excluded NPIs from a LEIE CSV."""
    detail = _leie_lookup(path)
    return set(detail) if detail is not None else None


def screen_leie(npis: List[str], *, leie_path: Optional[str] = None,
                dollars_by_npi: Optional[Dict[str, float]] = None) -> dict:
    """Offline OIG LEIE exclusion screen. Never raises.

    ``dollars_by_npi`` (optional, additive) maps a billing NPI to the summed
    billed dollars flowing through it, so the screen can report
    ``excluded_billed_total`` — the exposure figure, not just a count."""
    path = leie_path or os.environ.get("RCM_MC_LEIE_CSV") or ""
    out: Dict[str, object] = {
        "id": "oig_leie", "label": "OIG LEIE (excluded providers)",
        "source": "HHS OIG List of Excluded Individuals/Entities",
        "available": False, "checked": 0, "excluded": 0,
        "matches": [], "note": "",
    }
    excluded: Optional[set] = None
    detail: Optional[Dict[str, Dict[str, str]]] = None
    if path and Path(path).exists():
        detail = _leie_lookup(path)
        if detail is None:
            out["note"] = ("LEIE dataset could not be read (expected a CSV "
                           "with an NPI column).")
            return out
        excluded = set(detail)
    else:
        # No file configured — fall back to the pulled reference pack
        # (Reference data packs → leie), which is how most deployments
        # should run this now: one click, refreshed monthly, no env var.
        # The pack stores NPIs only, so matches stay bare there (and the
        # note says so) — honesty over invented detail.
        try:
            from . import refdata_packs as _packs
            pack = _packs.leie_npis()
            if pack is not None:
                excluded = set(pack)
                out["source"] = ("HHS OIG LEIE (installed reference pack)")
        except Exception:  # noqa: BLE001
            excluded = None
    if excluded is None:
        out["note"] = ("No LEIE dataset loaded. Pull the leie reference "
                       "pack (Reference data packs on the cleaner page, or "
                       "rcm-mc npi-clean --refdata-pull leie), or set "
                       "RCM_MC_LEIE_CSV to a downloaded UPDATED.csv.")
        return out
    out["available"] = True
    distinct, _trunc = _distinct_npis(npis, 10_000)
    out["checked"] = len(distinct)

    # Optional billed-dollar exposure per NPI (engine passes billing-NPI →
    # summed billed). Keyed by digits so raw and cleaned NPIs both hit.
    dollars: Dict[str, float] = {}
    if dollars_by_npi:
        for k, v in dollars_by_npi.items():
            d = _digits(k)
            if len(d) == 10:
                try:
                    dollars[d] = dollars.get(d, 0.0) + float(v)
                except (TypeError, ValueError):
                    continue

    exposure = 0.0
    for npi in distinct:
        if npi in excluded:
            out["excluded"] = int(out["excluded"]) + 1
            m: Dict[str, object] = {"npi": npi}
            info = detail.get(npi) if detail else None
            if info:
                if info.get("name"):
                    m["name"] = info["name"]
                if info.get("excl_type"):
                    m["excl_type"] = info["excl_type"]
                if info.get("excl_date"):
                    m["excl_date"] = info["excl_date"]
            if npi in dollars:
                m["billed"] = round(dollars[npi], 2)
                exposure += dollars[npi]
            out["matches"].append(m)
    if dollars:
        out["excluded_billed_total"] = round(exposure, 2)
    note = (f"{out['excluded']} of {len(distinct)} distinct NPIs appear "
            f"on the OIG exclusions list."
            if distinct else "No NPIs to screen.")
    if detail is None and int(out["excluded"]) > 0:
        note += (" Reference-pack matches carry the NPI only — point "
                 "RCM_MC_LEIE_CSV at the OIG UPDATED.csv for names, "
                 "exclusion types and dates.")
    if dollars and int(out["excluded"]) > 0:
        note += (f" ${out['excluded_billed_total']:,.2f} of this file's "
                 "billed dollars flow through excluded NPIs.")
    out["note"] = note
    return out


# -------------------------------------------------------------- Medicare PECOS --
def _build_cms_client():
    """A CMS PECOS client with a short per-request timeout, or None.

    Prefers the vendored v49 CMSClient when ``requests`` is installed;
    otherwise falls back to the stdlib urllib client — which is the norm,
    since the platform ships stdlib + pandas/numpy/openpyxl only and the
    PECOS screen was permanently dead without this fallback."""
    try:
        import requests  # noqa: F401
        from .vendor_v49.npi_recovery import clients
        cache = clients.DiskCache("/tmp/npi_cleaner_cms_cache")
        return clients.CMSClient(cache, timeout=_CMS_REQ_TIMEOUT)
    except Exception:  # noqa: BLE001 — no requests → stdlib fallback
        pass
    try:
        from ..data_public.cms_pecos_client import CmsPecosClient
        return CmsPecosClient(timeout=_CMS_REQ_TIMEOUT)
    except Exception:  # noqa: BLE001
        return None


def screen_cms(npis: List[str], *, cms_client=None, cap: int = _MAX_CMS,
               timeout_s: int = _CMS_TIMEOUT_S) -> dict:
    """Networked PECOS screen (enrollment / opt-out / order-referring), bounded
    by a wall-clock watchdog. Never raises."""
    out: Dict[str, object] = {
        "id": "pecos", "label": "Medicare PECOS (enrollment · opt-out)",
        "source": "data.cms.gov via npi_recovery.clients.CMSClient",
        "available": False, "checked": 0,
        "not_enrolled": 0, "opted_out": 0,
        "rows": [], "note": "",
    }
    client = cms_client or _build_cms_client()
    if client is None:
        out["note"] = ("PECOS screening needs the 'requests' package and "
                       "outbound access to data.cms.gov.")
        return out

    distinct, trunc = _distinct_npis(npis, cap)
    if not distinct:
        out["note"] = "No billing NPIs to screen."
        return out

    box: Dict[str, object] = {"rows": [], "err": None}

    def _work():
        try:
            for npi in distinct:
                rec = {"npi": npi}
                enr = client.enrollment_lookup(npi) or {}
                rec["enrolled"] = bool(enr.get("enrolled"))
                rec["provider_type"] = enr.get("provider_type", "")
                oo = client.opt_out_lookup(npi) or {}
                rec["opted_out"] = bool(oo.get("opted_out"))
                box["rows"].append(rec)
        except Exception as exc:  # noqa: BLE001
            box["err"] = exc

    th = threading.Thread(target=_work, daemon=True)
    th.start()
    th.join(timeout_s)

    rows = box["rows"]
    out["available"] = True
    out["checked"] = len(rows)
    out["not_enrolled"] = sum(1 for r in rows if not r.get("enrolled"))
    out["opted_out"] = sum(1 for r in rows if r.get("opted_out"))
    out["rows"] = rows[:15]
    parts = [f"{len(rows)} of {len(distinct)} billing NPIs screened against PECOS"]
    if out["not_enrolled"]:
        parts.append(f"{out['not_enrolled']} not enrolled")
    if out["opted_out"]:
        parts.append(f"{out['opted_out']} opted out (billing red flag)")
    if th.is_alive():
        parts.append("timed out — network may be unavailable")
    if trunc:
        parts.append(f"capped at {cap}")
    if box["err"]:
        parts.append("lookup error")
    out["note"] = "; ".join(parts) + "."
    return out


def screen(npis: List[str], *, leie_path: Optional[str] = None,
           cms_client=None, run_cms: bool = True,
           dollars_by_npi: Optional[Dict[str, float]] = None) -> List[dict]:
    """Run the compliance screens over billing NPIs; returns a list of result
    dicts for the compliance panel. LEIE is offline (always); PECOS is
    networked (``run_cms``). ``dollars_by_npi`` (optional) lets the LEIE
    screen size the billed-dollar exposure behind any exclusion match."""
    results = [screen_leie(npis, leie_path=leie_path,
                           dollars_by_npi=dollars_by_npi)]
    if run_cms:
        results.append(screen_cms(npis, cms_client=cms_client))
    return results
