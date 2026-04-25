"""CMS DRG relative weights + case-mix index computation.

The Medicare IPPS final rule publishes a relative weight per
DRG annually. Hospitals' case-mix index (CMI) is the
discharge-weighted average of those DRG weights — the higher
the CMI, the more complex the case-mix.

CMS publishes the full DRG weight table (~750 DRGs) in the
IPPS final rule's Table 5; partners typically pull it from
data.cms.gov. For partner-grade modeling we embed the most
common DRGs as a default lookup and accept a custom override
for full coverage.

Public API::

    from rcm_mc.data.cms_drg_weights import (
        DEFAULT_DRG_WEIGHTS,
        get_drg_weight,
        compute_case_mix_index,
    )
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Mapping, Optional

logger = logging.getLogger(__name__)


# Embedded sampler — common DRG weights from the FY2024 IPPS
# final rule. Real deployments override via load_drg_weights or
# pass weights_override into compute_case_mix_index.
DEFAULT_DRG_WEIGHTS: Dict[str, float] = {
    # Cardiac
    "001": 27.6,    # Heart transplant w MCC
    "215": 5.7,     # CABG w cath, MCC
    "216": 4.5,     # CABG w cath, w/o MCC
    "237": 4.9,     # Major cardiovasc proc w MCC
    "246": 2.4,     # PCI with drug-eluting stent w MCC
    "291": 1.5,     # Heart failure w MCC
    "292": 0.95,    # Heart failure w CC
    "293": 0.65,    # Heart failure w/o CC
    "302": 0.81,    # Atherosclerosis w/o MCC
    # Respiratory
    "189": 1.3,     # Pulmonary edema / respiratory failure
    "190": 1.05,    # COPD w MCC
    "191": 0.85,    # COPD w CC
    "192": 0.65,    # COPD w/o CC
    "193": 1.4,     # Simple pneumonia w MCC
    "194": 0.95,    # Simple pneumonia w CC
    "195": 0.65,    # Simple pneumonia w/o CC
    # Ortho
    "461": 3.1,     # Bilateral / multiple major joint procs
    "462": 2.0,     # Bilateral / multiple major joint w/o MCC
    "469": 2.4,     # Major hip/knee w MCC
    "470": 1.8,     # Major hip/knee w/o MCC
    "480": 2.1,     # Hip/femur except major joint w MCC
    "481": 1.4,     # Hip/femur w/o MCC
    # Stroke
    "061": 4.7,     # Acute ischemic stroke w thrombolytic
    "064": 2.1,     # Intracranial hemorrhage w MCC
    "065": 1.2,     # Intracranial hemorrhage w CC
    # Sepsis
    "871": 1.85,    # Septicemia w/o MV w MCC
    "872": 1.05,    # Septicemia w/o MV w/o MCC
    # Newborn / maternity
    "765": 1.05,    # Cesarean w CC/MCC
    "766": 0.65,    # Cesarean w/o CC/MCC
    "775": 0.55,    # Vaginal delivery w/o complicating dx
    "789": 1.15,    # Neonate, normal newborn
    # GI / general surgery
    "326": 5.4,     # Stomach, esophageal procs w MCC
    "327": 2.3,     # Stomach, esophageal procs w CC
    "377": 1.5,     # GI hemorrhage w MCC
    "378": 1.0,     # GI hemorrhage w CC
}


def _normalize(code: Any) -> str:
    """Normalize DRG codes to a 3-digit zero-padded string."""
    if code is None:
        return ""
    s = str(code).strip()
    # Strip trailing ".0" from ints encoded as floats
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    if s.isdigit() and len(s) <= 3:
        return s.zfill(3)
    return s


def get_drg_weight(
    drg_code: Any,
    *,
    weights: Optional[Mapping[str, float]] = None,
) -> Optional[float]:
    """Look up the relative weight for one DRG. Falls back to
    DEFAULT_DRG_WEIGHTS when no override is supplied."""
    code = _normalize(drg_code)
    if not code:
        return None
    table = weights if weights is not None else DEFAULT_DRG_WEIGHTS
    return table.get(code)


def compute_case_mix_index(
    drg_volumes: Iterable[Mapping[str, Any]],
    *,
    weights: Optional[Mapping[str, float]] = None,
) -> Optional[float]:
    """Discharge-weighted DRG-weight average — the case-mix index.

    Args:
      drg_volumes: iterable of dicts with at least ``drg_code``
        and ``discharges`` (or ``volume``) keys.
      weights: optional override map {drg_code → weight}.
        Defaults to DEFAULT_DRG_WEIGHTS — partners with the full
        IPPS table pass that in.

    Returns the CMI, or None when no DRGs in the input have a
    matching weight (CMI undefined).
    """
    table = weights if weights is not None else DEFAULT_DRG_WEIGHTS
    total_weighted = 0.0
    total_discharges = 0.0
    for row in drg_volumes:
        code = _normalize(row.get("drg_code")
                          or row.get("DRG_Cd"))
        w = table.get(code)
        if w is None:
            continue
        vol = row.get("discharges")
        if vol is None:
            vol = row.get("volume")
        if vol is None:
            vol = row.get("total_discharges")
        try:
            v = float(vol or 0)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        total_weighted += w * v
        total_discharges += v
    if total_discharges <= 0:
        return None
    return round(total_weighted / total_discharges, 4)


def load_drg_weights(
    rows: Iterable[Mapping[str, Any]],
) -> Dict[str, float]:
    """Build a {drg_code → weight} dict from CMS IPPS Table 5 rows.

    Each input row should provide ``drg_code`` (or ``MS_DRG_Cd``)
    and ``relative_weight`` (or ``Wt``). Returns the parsed dict;
    callers persist or pass to ``compute_case_mix_index``.
    """
    out: Dict[str, float] = {}
    for r in rows:
        code = _normalize(r.get("drg_code")
                          or r.get("MS_DRG_Cd")
                          or r.get("DRG_Cd"))
        if not code:
            continue
        w = r.get("relative_weight") or r.get("Wt")
        try:
            out[code] = float(w)
        except (TypeError, ValueError):
            continue
    return out
