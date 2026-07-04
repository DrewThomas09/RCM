"""
rif_schema.py  (v47)
====================

Ingest Medicare Research Identifiable File (RIF) data, the schema used inside the
CMS Virtual Research Data Center (VRDC) and the Chronic Conditions Warehouse
(CCW). This is the 100% Medicare fee-for-service census, the ground truth a sampled
commercial panel gets calibrated against, and it uses column conventions entirely
different from a Komodo-style extract. This module recognizes which RIF file it is
looking at and maps its columns onto the toolkit's canonical model, so every screen,
recovery, and analytic that already runs on a commercial extract runs on VRDC data
without change.

Important operational note. VRDC is a secure enclave: RIF data cannot be exported
from it. This module is built to run inside the enclave, or on approved RIF-format
extracts, and it pairs with the CMS cell-suppression tool (rif_cleaning.py) so any
aggregate leaving the enclave suppresses small cells first. It is tested against
RIF-schema synthetic data, since real RIF data lives only in the enclave.

Supported RIF file types (the ones that matter for specialty-drug diligence):

  carrier      Part B physician/supplier claims. The core file for clinician
               administered drugs: performing physician, organization NPI, HCPCS,
               line allowed and paid, modifiers, referring physician, NDC.
  inpatient    Part A institutional inpatient. Facility org NPI, attending and
               operating physicians, principal diagnosis, revenue centers.
  outpatient   Part A institutional outpatient. Same institutional shape,
               outpatient revenue lines.
  pde          Part D prescription drug events. Prescriber, pharmacy, NDC,
               quantity, days supply, drug cost, plan and patient paid.

Column maps below use the standard CCW/RIF variable names. Where a RIF file carries
both a claim-level and a line-level version of a field, the line-level value is
mapped, because the toolkit operates at claim-line grain.
"""
from __future__ import annotations

import pandas as pd


# --------------------------------------------------------------------------- #
# RIF variable-name maps: canonical_field -> tuple of candidate RIF columns
# (checked in order; first present wins). Names are matched case-insensitively.
# --------------------------------------------------------------------------- #
_CARRIER_MAP = {
    "claim_id":       ("CLM_ID", "CARR_CLM_CNTL_NUM"),
    "patient_id":     ("BENE_ID", "DSYSRTKY"),
    "date":           ("LINE_1ST_EXPNS_DT", "CLM_FROM_DT", "CLM_THRU_DT"),
    "hcpcs":          ("HCPCS_CD", "CARR_CLM_HCPCS_CD"),
    "modifiers":      ("HCPCS_1ST_MDFR_CD", "HCPCS_2ND_MDFR_CD", "MDFR_CD1"),
    "rendering_npi":  ("PRF_PHYSN_NPI", "RNDRNG_PHYSN_NPI"),
    "billing_npi":    ("ORG_NPI_NUM", "CARR_CLM_BLG_NPI_NUM"),
    "referring_npi":  ("RFR_PHYSN_NPI", "RFR_NPI"),
    "allowed_amt":    ("LINE_ALOWD_CHRG_AMT",),
    "paid_amt":       ("LINE_NCH_PMT_AMT",),
    "billed_amt":     ("LINE_SBMTD_CHRG_AMT",),
    "units":          ("LINE_SRVC_CNT",),
    "diagnosis":      ("LINE_ICD_DGNS_CD", "ICD_DGNS_CD1", "PRNCPAL_DGNS_CD"),
    "ndc":            ("LINE_NDC_CD", "CLM_LINE_NDC_CD"),
    "pos":            ("LINE_PLACE_OF_SRVC_CD", "CARR_LINE_PLACE_OF_SRVC_CD"),
    "payer":          ("CARR_NUM",),  # carrier number as a payer proxy in FFS
}

_INPATIENT_MAP = {
    "claim_id":       ("CLM_ID",),
    "patient_id":     ("BENE_ID", "DSYSRTKY"),
    "date":           ("CLM_FROM_DT", "CLM_ADMSN_DT", "CLM_THRU_DT"),
    "billing_npi":    ("ORG_NPI_NUM", "PRVDR_NUM"),
    "rendering_npi":  ("AT_PHYSN_NPI", "OP_PHYSN_NPI"),
    "referring_npi":  ("OT_PHYSN_NPI",),
    "diagnosis":      ("PRNCPAL_DGNS_CD", "ICD_DGNS_CD1"),
    "hcpcs":          ("HCPCS_CD",),
    "billed_amt":     ("CLM_TOT_CHRG_AMT",),
    "paid_amt":       ("CLM_PMT_AMT", "CLM_PPS_CPTL_FSP_AMT"),
    "units":          ("REV_CNTR_UNIT_CNT",),
    "pos":            ("REV_CNTR",),  # revenue center stands in for site on institutional
}

_OUTPATIENT_MAP = {
    "claim_id":       ("CLM_ID",),
    "patient_id":     ("BENE_ID", "DSYSRTKY"),
    "date":           ("CLM_FROM_DT", "CLM_THRU_DT"),
    "billing_npi":    ("ORG_NPI_NUM", "PRVDR_NUM"),
    "rendering_npi":  ("AT_PHYSN_NPI", "OP_PHYSN_NPI"),
    "referring_npi":  ("OT_PHYSN_NPI",),
    "diagnosis":      ("PRNCPAL_DGNS_CD", "ICD_DGNS_CD1", "RSN_VISIT_CD1"),
    "hcpcs":          ("HCPCS_CD",),
    "modifiers":      ("HCPCS_1ST_MDFR_CD", "HCPCS_2ND_MDFR_CD"),
    "allowed_amt":    ("REV_CNTR_PMT_AMT_AMT", "REV_CNTR_ALOWD_AMT"),
    "billed_amt":     ("REV_CNTR_TOT_CHRG_AMT", "CLM_TOT_CHRG_AMT"),
    "paid_amt":       ("CLM_PMT_AMT",),
    "units":          ("REV_CNTR_UNIT_CNT",),
    "ndc":            ("REV_CNTR_NDC_QTY_QLFR_CD", "CLM_LINE_NDC_CD"),
    "pos":            ("REV_CNTR",),
}

_PDE_MAP = {
    "claim_id":       ("PDE_ID", "RX_SRVC_RFRNC_NUM"),
    "patient_id":     ("BENE_ID", "DSYSRTKY"),
    "date":           ("SRVC_DT",),
    "ndc":            ("PROD_SRVC_ID",),
    "units":          ("QTY_DSPNSD_NUM",),
    "days_supply":    ("DAYS_SUPLY_NUM",),
    "referring_npi":  ("PRSCRBR_ID",),   # prescriber, the referring analog for drugs
    "billing_npi":    ("SRVC_PRVDR_ID", "PHRMCY_SRVC_TYPE_CD"),  # dispensing pharmacy
    "billed_amt":     ("TOT_RX_CST_AMT",),
    "paid_amt":       ("CVRD_D_PLAN_PD_AMT",),
    "ingredient_cost": ("INGRDNT_COST_AMT",),
    "dispensing_fee": ("DSPNSNG_FEE_AMT",),
    "payer":          ("PLAN_CNTRCT_REC_ID", "PLAN_BENFT_PKG_ID"),
}

_MAPS = {
    "carrier": _CARRIER_MAP,
    "inpatient": _INPATIENT_MAP,
    "outpatient": _OUTPATIENT_MAP,
    "pde": _PDE_MAP,
}

# signature columns that identify each RIF file type (presence-based detection)
_SIGNATURES = {
    "pde": ("PDE_ID", "PROD_SRVC_ID", "DAYS_SUPLY_NUM", "QTY_DSPNSD_NUM", "PRSCRBR_ID"),
    "carrier": ("CARR_CLM_HCPCS_CD", "LINE_ALOWD_CHRG_AMT", "PRF_PHYSN_NPI",
                "LINE_NCH_PMT_AMT", "CARR_NUM"),
    "inpatient": ("CLM_PPS_CPTL_FSP_AMT", "AT_PHYSN_NPI", "CLM_ADMSN_DT",
                  "PRNCPAL_DGNS_CD", "NCH_BENE_DSCHRG_DT"),
    "outpatient": ("REV_CNTR_PMT_AMT_AMT", "REV_CNTR_TOT_CHRG_AMT", "RSN_VISIT_CD1"),
}


def _upper_cols(df):
    return {c.upper(): c for c in df.columns}


def detect_rif_type(df: pd.DataFrame) -> tuple:
    """Return (rif_type, score, evidence) for the best-matching RIF file type, or
    (None, 0, {}) if the frame does not look like RIF. Detection is by how many of
    each type's signature columns are present."""
    cols = set(_upper_cols(df).keys())
    scores = {}
    for rtype, sig in _SIGNATURES.items():
        hits = [c for c in sig if c in cols]
        scores[rtype] = (len(hits), hits)
    best = max(scores, key=lambda k: scores[k][0])
    n_hits = scores[best][0]
    if n_hits < 2:
        return None, 0, {"scores": {k: v[0] for k, v in scores.items()}}
    return best, n_hits, {"matched_columns": scores[best][1],
                          "scores": {k: v[0] for k, v in scores.items()}}


def is_rif(df: pd.DataFrame) -> bool:
    rtype, _, _ = detect_rif_type(df)
    return rtype is not None


def rif_column_mapping(df: pd.DataFrame, rif_type: str = None) -> tuple:
    """Build a canonical->real-column mapping for a RIF frame. Returns
    (mapping, rif_type, report). The mapping is in the same shape schema.standardize
    expects, so downstream code is identical to the commercial path."""
    if rif_type is None:
        rif_type, _, _ = detect_rif_type(df)
    if rif_type is None or rif_type not in _MAPS:
        return {}, None, {"status": "not_rif"}
    upper = _upper_cols(df)
    field_map = _MAPS[rif_type]
    mapping = {}
    resolved = {}
    for canonical, candidates in field_map.items():
        for cand in candidates:
            if cand.upper() in upper:
                mapping[canonical] = upper[cand.upper()]
                resolved[canonical] = cand
                break
    report = {"status": "ok", "rif_type": rif_type,
              "fields_mapped": len(mapping), "resolved": resolved,
              "unmapped_canonical": [c for c in field_map if c not in mapping]}
    return mapping, rif_type, report


def standardize_rif(df: pd.DataFrame, rif_type: str = None) -> tuple:
    """Standardize a RIF frame into the canonical model. Returns (std, rif_type,
    report). Renames RIF columns to canonical names, preserves an orig_row index,
    and coerces the money and count fields to numeric.

    This deliberately reuses the canonical field names so that coding_edits,
    consistency, recovery, capture, and every analytic run unchanged on VRDC data.
    """
    mapping, rtype, report = rif_column_mapping(df, rif_type)
    if rtype is None:
        return df.copy(), None, report
    std = pd.DataFrame(index=df.index)
    std["orig_row"] = range(len(df))
    for canonical, real in mapping.items():
        std[canonical] = df[real]
    # numeric coercion for the fields the screens expect numeric
    for numcol in ("allowed_amt", "paid_amt", "billed_amt", "units", "days_supply",
                   "ingredient_cost", "dispensing_fee"):
        if numcol in std.columns:
            std[numcol] = pd.to_numeric(std[numcol], errors="coerce")
    # NDC and HCPCS hygiene
    if "hcpcs" in std.columns:
        std["hcpcs"] = std["hcpcs"].astype("string").str.strip().str.upper()
    if "ndc" in std.columns:
        std["ndc"] = std["ndc"].astype("string").str.replace(r"\D", "", regex=True)
    report["rows"] = len(std)
    report["note"] = (
        f"RIF {rtype} file standardized: {report['fields_mapped']} canonical fields "
        f"mapped from RIF variables. The data now runs through the same screens, "
        f"recovery, and analytics as a commercial extract. Source is Medicare FFS "
        f"census (VRDC/CCW), so it is the FFS ground truth for calibrating a panel.")
    return std, rtype, report
