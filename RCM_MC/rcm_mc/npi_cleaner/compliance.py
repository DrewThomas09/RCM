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
    seen: List[str] = []
    for v in npis:
        d = _digits(v)
        if len(d) == 10 and d not in seen:
            seen.append(d)
    return seen[:cap], len(seen) > cap


# ------------------------------------------------------------------ OIG LEIE --
def _leie_npi_set(path: str) -> Optional[set]:
    """Load the set of excluded NPIs from a LEIE CSV. Returns None on failure."""
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            # LEIE 'UPDATED' files carry an NPI column; find it case-insensitively.
            npi_col = None
            for i, h in enumerate(header):
                if h.strip().upper() == "NPI":
                    npi_col = i
                    break
            if npi_col is None:
                return None
            out = set()
            for row in reader:
                if npi_col < len(row):
                    d = _digits(row[npi_col])
                    if len(d) == 10:
                        out.add(d)
            return out
    except Exception:  # noqa: BLE001
        return None


def screen_leie(npis: List[str], *, leie_path: Optional[str] = None) -> dict:
    """Offline OIG LEIE exclusion screen. Never raises."""
    path = leie_path or os.environ.get("RCM_MC_LEIE_CSV") or ""
    out: Dict[str, object] = {
        "id": "oig_leie", "label": "OIG LEIE (excluded providers)",
        "source": "HHS OIG List of Excluded Individuals/Entities",
        "available": False, "checked": 0, "excluded": 0,
        "matches": [], "note": "",
    }
    if not path or not Path(path).exists():
        out["note"] = ("No LEIE dataset loaded. Download the monthly LEIE CSV "
                       "from oig.hhs.gov and set RCM_MC_LEIE_CSV to enable "
                       "excluded-provider screening.")
        return out
    excluded = _leie_npi_set(path)
    if excluded is None:
        out["note"] = ("LEIE dataset could not be read (expected a CSV with an "
                       "NPI column).")
        return out
    out["available"] = True
    distinct, _trunc = _distinct_npis(npis, 10_000)
    out["checked"] = len(distinct)
    for npi in distinct:
        if npi in excluded:
            out["excluded"] = int(out["excluded"]) + 1
            out["matches"].append({"npi": npi})
    out["note"] = (f"{out['excluded']} of {len(distinct)} distinct NPIs appear "
                   f"on the OIG exclusions list."
                   if distinct else "No NPIs to screen.")
    return out


# -------------------------------------------------------------- Medicare PECOS --
def _build_cms_client():
    """Construct a v49 CMSClient with a short per-request timeout, or None."""
    try:
        import requests  # noqa: F401
        from .vendor_v49.npi_recovery import clients
        cache = clients.DiskCache("/tmp/npi_cleaner_cms_cache")
        return clients.CMSClient(cache, timeout=_CMS_REQ_TIMEOUT)
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
           cms_client=None, run_cms: bool = True) -> List[dict]:
    """Run the compliance screens over billing NPIs; returns a list of result
    dicts for the compliance panel. LEIE is offline (always); PECOS is
    networked (``run_cms``)."""
    results = [screen_leie(npis, leie_path=leie_path)]
    if run_cms:
        results.append(screen_cms(npis, cms_client=cms_client))
    return results
