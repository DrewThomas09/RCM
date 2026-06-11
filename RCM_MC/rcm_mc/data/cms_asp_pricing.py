"""CMS Part B ASP drug pricing — the buy-and-bill reimbursement basis.

Medicare Part B pays for clinician-administered (infused / injected)
drugs at the quarterly **Average Sales Price (ASP) + 6%** payment limit —
sequestered to roughly **ASP + 4.3%** since the 2% Medicare sequester
applies to the 80% Medicare-paid portion. That payment limit, against the
provider's actual acquisition cost (GOP/channel), is the entire
buy-and-bill spread an AIC or home-infusion operator earns on the drug.

This module exposes:

  • a curated, **verifiable** reference of the marquee infusion-drug
    HCPCS J-codes (immunology, neurology, oncology-support, IVIG) — the
    codes themselves and their descriptors are public CMS facts;
  • the ASP+6 / sequestered-ASP+4.3 payment mechanics as documented
    constants and pure functions; and
  • a best-effort **live** client for the CMS ASP Pricing file on
    data.cms.gov that returns the real per-unit payment limit per HCPCS
    when network egress is available.

No dollar amount is fabricated: the per-unit ASP payment limit is filled
in from the live file when reachable, and is ``None`` (shown as the
formula) offline. Only the public J-code → drug → descriptor facts are
vendored.
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Medicare Part B add-on to ASP and the post-sequester effective rate.
ASP_ADDON = 0.06            # statutory ASP + 6%
SEQUESTER = 0.02           # 2% Medicare sequester on the 80% federal share
# Effective add-on after sequester ≈ 6% − 2%×80% of (1+6%) ≈ 4.3%.
ASP_ADDON_SEQUESTERED = round(
    (1 + ASP_ADDON) * (1 - SEQUESTER * 0.8) - 1, 4)   # ≈ 0.0432

# CMS ASP Pricing file on data.cms.gov (quarterly). The dataset UUID
# rotates each quarter; this is a best-effort default and the fetch fails
# closed when the id is stale or egress is blocked.
ASP_DATASET_DEFAULT = ""   # resolved via the dataset search when empty
_CMS_DATA_API = "https://data.cms.gov/data-api/v1/dataset"
_CMS_SEARCH = "https://data.cms.gov/data.json"

#: Marquee infusion-drug HCPCS J-codes — public CMS facts (code +
#: descriptor + billed unit). Category/channel tag the infusion-diligence
#: relevance. Dollar pricing is NOT here — it comes from the live ASP file.
INFUSION_HCPCS: List[Dict[str, str]] = [
    {"hcpcs": "J1745", "drug": "Infliximab (Remicade)",
     "unit": "per 10 mg", "category": "Immunology (anti-TNF)",
     "channel": "AIC + home"},
    {"hcpcs": "J3380", "drug": "Vedolizumab (Entyvio)",
     "unit": "per 1 mg", "category": "Immunology (IBD)",
     "channel": "AIC"},
    {"hcpcs": "J9312", "drug": "Rituximab (Rituxan)",
     "unit": "per 10 mg", "category": "Immunology / oncology",
     "channel": "AIC / HOPD"},
    {"hcpcs": "J2350", "drug": "Ocrelizumab (Ocrevus)",
     "unit": "per 1 mg", "category": "Neurology (MS)",
     "channel": "AIC"},
    {"hcpcs": "J2323", "drug": "Natalizumab (Tysabri)",
     "unit": "per 1 mg", "category": "Neurology (MS) / IBD",
     "channel": "AIC"},
    {"hcpcs": "J0490", "drug": "Belimumab (Benlysta)",
     "unit": "per 10 mg", "category": "Immunology (lupus)",
     "channel": "AIC + home"},
    {"hcpcs": "J1300", "drug": "Eculizumab (Soliris)",
     "unit": "per 10 mg", "category": "Rare / complement",
     "channel": "AIC + home"},
    {"hcpcs": "J1569", "drug": "Immune globulin (Gammagard liquid)",
     "unit": "per 500 mg", "category": "IVIG",
     "channel": "AIC + home"},
    {"hcpcs": "J1599", "drug": "Immune globulin, NOS",
     "unit": "per 500 mg", "category": "IVIG",
     "channel": "AIC + home"},
    {"hcpcs": "J9035", "drug": "Bevacizumab (Avastin)",
     "unit": "per 10 mg", "category": "Oncology",
     "channel": "AIC / HOPD"},
    {"hcpcs": "J0897", "drug": "Denosumab (Prolia / Xgeva)",
     "unit": "per 1 mg", "category": "Oncology support / bone",
     "channel": "AIC + home"},
    {"hcpcs": "J2505", "drug": "Pegfilgrastim (Neulasta)",
     "unit": "per 6 mg", "category": "Oncology support (GCSF)",
     "channel": "AIC"},
]


def payment_limit(asp_per_unit: float, *, sequestered: bool = True) -> float:
    """ASP payment limit per unit = ASP × (1 + add-on). Sequestered uses
    the ≈4.3% effective add-on; statutory uses 6%."""
    addon = ASP_ADDON_SEQUESTERED if sequestered else ASP_ADDON
    return round(asp_per_unit * (1 + addon), 4)


def _to_float(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _resolve_asp_dataset(timeout: float = 20.0) -> str:
    """Find the current ASP Pricing dataset UUID from the CMS data.json
    catalog. Returns '' on any failure (caller falls back to formula)."""
    if ASP_DATASET_DEFAULT:
        return ASP_DATASET_DEFAULT
    from ._cms_download import ssl_context
    try:
        req = urllib.request.Request(
            _CMS_SEARCH, headers={"Accept": "application/json",
                                  "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            cat = json.loads(r.read().decode())
        best = ""
        for ds in cat.get("dataset", []):
            title = str(ds.get("title", "")).lower()
            if "asp" in title and "pricing" in title:
                for dist in ds.get("distribution", []):
                    url = str(dist.get("accessURL", "")
                              or dist.get("downloadURL", ""))
                    if "dataset/" in url:
                        best = url.split("dataset/")[1].split("/")[0]
                        break
            if best:
                break
        return best
    except Exception as exc:
        logger.warning("CMS ASP dataset resolve failed: %s", exc)
        return ""


def fetch_asp_pricing(
    hcpcs_codes: Optional[List[str]] = None,
    *,
    dataset: str = "",
    timeout: float = 20.0,
) -> Dict[str, float]:
    """Live per-unit ASP payment limit by HCPCS from the CMS ASP file.

    Returns ``{hcpcs: payment_limit_per_unit}``. Empty dict on any
    failure — the caller falls back to the ASP+6 formula with no
    fabricated dollar value.
    """
    ds = dataset or _resolve_asp_dataset(timeout=timeout)
    if not ds:
        return {}
    want = {c.upper() for c in (hcpcs_codes or [])} or None
    from ._cms_download import ssl_context
    out: Dict[str, float] = {}
    try:
        url = f"{_CMS_DATA_API}/{ds}/data?size=5000"
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            rows = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS ASP pricing API unavailable: %s", exc)
        return {}
    if not isinstance(rows, list):
        return {}
    for row in rows:
        code = ""
        price = None
        for k, v in row.items():
            kl = k.lower()
            if not code and ("hcpcs" in kl or kl in ("code",)):
                code = str(v).strip().upper()
            if price is None and ("payment" in kl or "limit" in kl
                                  or "asp" in kl):
                price = _to_float(v)
        if code and price is not None and (want is None or code in want):
            out[code] = price
    return out


@functools.lru_cache(maxsize=4)
def infusion_asp_reference() -> List[Dict[str, Any]]:
    """The infusion J-code reference with the live ASP payment limit
    filled in where reachable (else ``payment_limit_per_unit`` = None,
    shown as the formula). Cached per process."""
    codes = [c["hcpcs"] for c in INFUSION_HCPCS]
    live = fetch_asp_pricing(codes)
    out = []
    for c in INFUSION_HCPCS:
        asp_pay = live.get(c["hcpcs"])
        out.append({
            **c,
            "payment_limit_per_unit": asp_pay,
            "live": asp_pay is not None,
        })
    return out
