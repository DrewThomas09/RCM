"""Adapter that drives the *real* vendored NPI_Recovery_and_Cleaner v48 modules.

The uploaded zip is incomplete — 14 internal modules its code imports were not
in the archive (``pipeline``/``run_pipeline``, ``entity``, ``clean_pipeline``,
``issue_analysis``, ``impute``, ``fill``, ``rx_bridge``, ``specialty_drug``,
``common_name``, ``npi_channel``, ``deficit_diagnostics``, ``row_consistency``,
``run_manifest``, ``bulk``, ``prettyxl``), plus the CMS reference-data CSVs the
coding-edit screens read. So the full Steps 0–8 recovery pipeline and the
Excel report cannot run from what was delivered.

What *did* ship and runs offline with no missing deps are the field- and
cross-field validation screens. This adapter wires the genuine package code for
those — nothing here reimplements their logic:

  * ``field_validators.run_field_validation`` — NPI (length + Luhn), NDC,
    date, money, state, HCPCS field rules with a repairability verdict.
  * ``consistency.run_all`` — money ordering (paid ≤ allowed ≤ billed), date
    ordering, provider-role coherence, quantity vs days-supply.
  * ``dedup.netting_audit`` — reversal / netting audit when allowed + units
    are present.

Those functions expect a *standardized* frame with canonical column names, so
the adapter maps the uploaded headers onto the canonical fields (the same
fallbacks the screens themselves use) before calling them. Everything is
guarded: if pandas or any module is unavailable, ``run(...)`` returns ``None``
and the caller falls back to the stdlib engine.
"""
from __future__ import annotations

import io
import re
from typing import Dict, List, Optional


# Canonical field -> the header spellings we accept for it. Keys mirror the
# canonical names the vendored screens resolve (field_validators uses the
# canonical name directly; consistency/coding_edits use these + fallbacks).
_CANON_ALIASES: Dict[str, tuple] = {
    "billing_npi": ("billingnpi", "billingprovidernpi", "billnpi", "npi",
                    "providernpi", "payto_npi", "paytonpi"),
    "referring_npi": ("referringnpi", "refernpi", "referringprovidernpi"),
    "rendering_npi": ("renderingnpi", "rendnpi", "renderingprovidernpi",
                      "servicingnpi", "attendingnpi"),
    "allowed_amt": ("allowedamt", "allowed", "allowedamount", "alloweddollars"),
    "billed_amt": ("billedamt", "billed", "chargeamt", "charges", "charge",
                   "submittedamt", "billedamount"),
    "paid_amt": ("paidamt", "paid", "paymentamt", "planpaid", "paidamount"),
    "date": ("date", "dateofservice", "servicedate", "dos", "svcdate",
             "fromdate", "servicefromdate"),
    "paid_date": ("paiddate", "paymentdate", "adjudicationdate", "processeddate"),
    "state": ("state", "provstate", "providerstate", "patientstate", "st"),
    "hcpcs": ("hcpcs", "hcpcscpt", "cpt", "code", "procedurecode", "proccode"),
    "units": ("units", "unit", "quantity", "qty", "srvccnt", "servicecount"),
    "days_supply": ("dayssupply", "days", "dayssup", "supplydays"),
    "ndc": ("ndc", "ndc11", "ndccode", "drugndc"),
    "age": ("age", "patientage", "ageyears"),
    "sex": ("sex", "gender", "patientsex"),
}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def build_mapping(headers: List[str]) -> Dict[str, str]:
    """Map canonical field -> the actual header in this file (best effort).

    First-match-wins per canonical field, in the alias order above. A header is
    only claimed by one canonical field so we don't map two NPIs to the same
    column.
    """
    norm_to_header = {}
    for h in headers:
        norm_to_header.setdefault(_norm(h), h)
    claimed = set()
    mapping: Dict[str, str] = {}
    for canon, aliases in _CANON_ALIASES.items():
        for alias in aliases:
            hdr = norm_to_header.get(alias)
            if hdr is not None and hdr not in claimed:
                mapping[canon] = hdr
                claimed.add(hdr)
                break
    return mapping


def available() -> bool:
    """True when pandas and the runnable vendored modules import cleanly."""
    try:
        import pandas  # noqa: F401
        from .vendor_v48.npi_recovery import (  # noqa: F401
            field_validators, consistency, dedup,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def run(data: bytes, mapping: Optional[Dict[str, str]] = None) -> Optional[dict]:
    """Run the real field + consistency + netting screens on the upload.

    Returns a dict of real findings, or ``None`` if the engine is unavailable
    or the file cannot be framed. Never raises — a screen that lacks its inputs
    returns a note, which we surface rather than treat as an error.
    """
    try:
        import pandas as pd
        from .vendor_v48.npi_recovery import (
            field_validators as FV,
            consistency as CON,
            dedup as DD,
        )
    except Exception:  # noqa: BLE001
        return None

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")

    try:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python",
                         dtype=str, keep_default_na=False)
    except Exception:  # noqa: BLE001
        return None
    if df.empty or df.shape[1] == 0:
        return None

    headers = list(df.columns)
    mapping = mapping or build_mapping(headers)

    # field_validators.run_field_validation reads canonical column NAMES
    # directly (not via mapping), so present a renamed copy to it.
    std = df.copy()
    rename = {src: canon for canon, src in mapping.items() if src in std.columns}
    std_fv = std.rename(columns=rename)

    findings: dict = {"mapping": mapping, "field_rules": [],
                      "consistency": [], "netting": None}

    # ---- field-level rules (real) ----
    try:
        fr = FV.run_field_validation(std_fv)
        if "rule_id" in getattr(fr, "columns", []):
            for _, r in fr.iterrows():
                findings["field_rules"].append({
                    "field": str(r["field"]), "rule_id": str(r["rule_id"]),
                    "rows": int(r["rows"]), "repair": str(r["repair"]),
                })
    except Exception:  # noqa: BLE001
        pass

    # ---- cross-field consistency screens (real) ----
    try:
        screens = CON.run_all(std, mapping)
        for name, frame in screens.items():
            cols = getattr(frame, "columns", [])
            if "row" in cols:
                findings["consistency"].append({
                    "screen": name, "flagged": int(len(frame)),
                    "note": str(frame.attrs.get("note", "")),
                })
            else:
                note = ""
                if "note" in cols and len(frame):
                    note = str(frame.iloc[0]["note"])
                findings["consistency"].append({
                    "screen": name, "flagged": 0, "note": note,
                })
    except Exception:  # noqa: BLE001
        pass

    # ---- reversal / netting audit (real) ----
    try:
        allowed_c = mapping.get("allowed_amt")
        units_c = mapping.get("units")
        if allowed_c and units_c:
            audit = DD.netting_audit(std, allowed=allowed_c, units=units_c)
            if hasattr(audit, "__len__"):
                findings["netting"] = {
                    "pairs": int(len(audit)),
                    "note": str(getattr(audit, "attrs", {}).get("note", "")),
                }
    except Exception:  # noqa: BLE001
        pass

    findings["engine"] = "npi_recovery v48 (field_validators + consistency + dedup)"
    return findings
