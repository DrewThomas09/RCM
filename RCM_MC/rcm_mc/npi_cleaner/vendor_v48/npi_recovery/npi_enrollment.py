"""
npi_enrollment.py  (v32)
========================

Joe's government-billing question is the live branch of the VRDC diagnosis, and it
needs a finer answer than v31's GOVERNMENT_PHARMACY vs COMMERCIAL_MEDICAL split. A
home-infusion pharmacy's Medicare volume attributes to three DIFFERENT enrollment
types, each keying a different CMS file:

  PART_D_PHARMACY   Part D (PDE) events key on the pharmacy NPI.
  DME_SUPPLIER      pump-and-drug claims through the DME benefit key on a
                    DMEPOS-enrolled supplier number.
  HIT_SUPPLIER      post-Cures home-infusion-therapy G-codes key on a separately
                    enrolled home-infusion-therapy supplier.

A finder list assembled from medical-claims presence can reconcile perfectly
against the client file and still miss the government-billing subset, which zeroes
out Part D and DME volume in VRDC while everything upstream looks validated. The
useful deliverable, as the report says, is not a flat NPI list but a mapping of
which entities are enrolled where, plus whether health-system joint-venture
entities bill under NPIs in neither roster.

This module builds that mapping from two signals per billing NPI: its NPPES
taxonomy (pharmacy 3335*/3336*, DMEPOS 332B*) and the claim channels actually
billed under it (HIT G/S codes, DME-channel codes, self-administered codes, from
deficit_diagnostics.classify_claim_channel). It then reconciles the enrollment
channels the pull covered against the ones it needed, and flags NPIs absent from a
supplied roster as JV / missing-entity candidates.

Deterministic and offline. Extends, does not replace, v31 npi_channel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from . import deficit_diagnostics as _dd
from . import npi_channel as _nc


# which CMS file each enrollment channel keys on
CHANNEL_FILE = {
    "PART_D_PHARMACY": "Part D PDE",
    "DME_SUPPLIER": "DMERC / DME MAC",
    "HIT_SUPPLIER": "HIT supplier (Part B)",
    "PARTB_MEDICAL": "Carrier / Outpatient",
}


def _digits(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return "".join(ch for ch in str(x) if ch.isdigit())


def _channel_to_enrollment(claim_channel: str) -> str:
    return {
        "HIT_PROF": "HIT_SUPPLIER",
        "DME_SUPPLY": "DME_SUPPLIER",
        "PARTD_SAD": "PART_D_PHARMACY",
        "PARTB_MEDICAL": "PARTB_MEDICAL",
    }.get(claim_channel, "PARTB_MEDICAL")


def map_enrollment_channels(std: pd.DataFrame, *, allowed=None, taxonomy_of=None,
                            ref_dir=None, roster_npis=None,
                            hcpcs_col: str = "hcpcs") -> pd.DataFrame:
    """One row per billing NPI: its taxonomy-implied supplier class, the enrollment
    channels observed from the codes billed under it, the CMS files those imply,
    dollars per channel, and whether it is absent from a supplied roster (a JV /
    missing-entity candidate)."""
    if "billing_npi" not in std.columns:
        return pd.DataFrame({"note": ["no billing_npi column; enrollment mapping skipped"]})

    n = len(std)
    npi = std["billing_npi"].map(_digits)
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0).to_numpy()
         if allowed is not None else np.ones(n))
    claim_channel = _dd.classify_claim_channel(std, ref_dir=ref_dir, hcpcs_col=hcpcs_col)
    enr = claim_channel.map(_channel_to_enrollment)
    taxmap = {_digits(k): str(v) for k, v in (taxonomy_of or {}).items()}
    roster = {_digits(x) for x in (roster_npis or set())}
    roster = {x for x in roster if len(x) == 10}

    work = pd.DataFrame({"npi": npi.to_numpy(), "allowed": a, "enr": enr.to_numpy()})
    work = work[work["npi"].str.len() > 0]
    if work.empty:
        return pd.DataFrame({"note": ["no usable billing NPIs after digit-cleaning"]})

    rows = []
    for code, g in work.groupby("npi", sort=False):
        tot = float(g["allowed"].sum())
        by_enr = g.groupby("enr")["allowed"].sum()
        channels = sorted(by_enr.index.tolist())
        tax_code = taxmap.get(code, "")
        sclass = _nc.supplier_class(tax_code)
        # taxonomy can add an enrollment channel even if no claim of that type is
        # in the medical panel (the whole point: the volume is in another file)
        implied = set(channels)
        if sclass == "PHARMACY":
            implied.add("PART_D_PHARMACY")
        if sclass == "DME":
            implied.add("DME_SUPPLIER")
        files = sorted({CHANNEL_FILE.get(c, "Carrier / Outpatient") for c in implied})
        rows.append({
            "billing_npi": code,
            "supplier_class": sclass,
            "taxonomy_code": tax_code,
            "enrollment_channels": ", ".join(sorted(implied)),
            "cms_files_implied": ", ".join(files),
            "n_claims": int(len(g)),
            "allowed": round(tot, 2),
            "part_d_pharmacy_allowed": round(float(by_enr.get("PART_D_PHARMACY", 0.0)), 2),
            "dme_supplier_allowed": round(float(by_enr.get("DME_SUPPLIER", 0.0)), 2),
            "hit_supplier_allowed": round(float(by_enr.get("HIT_SUPPLIER", 0.0)), 2),
            "partb_medical_allowed": round(float(by_enr.get("PARTB_MEDICAL", 0.0)), 2),
            "in_roster": (code in roster) if roster else np.nan,
            "jv_or_missing_candidate": (bool(code not in roster) if roster else False),
            "government_enrolled": bool(implied & {"PART_D_PHARMACY", "DME_SUPPLIER", "HIT_SUPPLIER"}),
        })
    out = pd.DataFrame(rows).sort_values(
        ["government_enrolled", "allowed"], ascending=[False, False]).reset_index(drop=True)
    out.attrs["note"] = (
        "enrollment_channels combine the NPI's taxonomy (pharmacy 3335*/3336*, DMEPOS 332B*) "
        "with the claim channels billed under it. cms_files_implied is where that entity's "
        "volume lives, so a finder list built from Carrier/Outpatient alone misses any NPI "
        "whose files are Part D PDE, DME MAC, or HIT. jv_or_missing_candidate flags NPIs absent "
        "from the supplied roster.")
    return out


def enrollment_file_coverage(enrollment_map: pd.DataFrame, *,
                             pull_files=("Carrier / Outpatient",)) -> pd.DataFrame:
    """Which CMS files the target's enrollment requires versus which the pull
    covered, with the dollars at risk in the missed files. This is the concrete
    reason a validated finder list can still zero out Part D and DME in VRDC."""
    if enrollment_map is None or "cms_files_implied" not in getattr(enrollment_map, "columns", []):
        return pd.DataFrame({"note": ["enrollment map unavailable; file-coverage skipped"]})
    pull = {str(x).strip() for x in pull_files}

    # per-channel dollars across all NPIs
    chan_dollars = {
        "Part D PDE": float(pd.to_numeric(enrollment_map.get("part_d_pharmacy_allowed", 0), errors="coerce").fillna(0).sum()),
        "DMERC / DME MAC": float(pd.to_numeric(enrollment_map.get("dme_supplier_allowed", 0), errors="coerce").fillna(0).sum()),
        "HIT supplier (Part B)": float(pd.to_numeric(enrollment_map.get("hit_supplier_allowed", 0), errors="coerce").fillna(0).sum()),
        "Carrier / Outpatient": float(pd.to_numeric(enrollment_map.get("partb_medical_allowed", 0), errors="coerce").fillna(0).sum()),
    }
    tot = sum(chan_dollars.values()) or 1.0
    rows = []
    for f, amt in sorted(chan_dollars.items(), key=lambda kv: kv[1], reverse=True):
        rows.append({
            "cms_file": f,
            "observed_allowed": round(amt, 2),
            "share_pct": round(amt / tot * 100, 1),
            "in_pull": f in pull,
        })
    missed = sum(amt for f, amt in chan_dollars.items() if f not in pull)
    out = pd.DataFrame(rows)
    out.attrs["missed_file_allowed"] = round(missed, 2)
    out.attrs["missed_file_pct"] = round(missed / tot * 100, 1)
    out.attrs["note"] = (
        "in_pull=False files carry volume the pull could not have captured. observed_allowed "
        "reflects only what appears in this panel; the true missed mass is larger when the "
        "government book lives entirely in an un-pulled file (that is the point of the "
        "diagnosis, not a contradiction).")
    return out
