"""
taxonomy_coherence.py  (v43)
============================

A recovered billing NPI is more trustworthy when the provider's specialty makes
sense for what was billed. A recovered NPI that resolves to a provider whose
taxonomy cannot plausibly bill the drug on the claim is probably a wrong
recovery. This module turns that intuition into a deterministic signal.

It is deliberately conservative. It only renders a verdict when it has both the
recovered NPI's taxonomy (from NPPES enrichment) and a reason to expect a
particular provider class (the billed HCPCS is a specialty-drug J-code that is
administered, not self-dispensed). Otherwise it returns neutral (0.5). It never
rejects a recovery on its own; it produces a coherence score that the recovery
model can weigh and that the review queue can surface.

Three outcomes per row:
  1.0  coherent    taxonomy is consistent with billing this drug
  0.0  incoherent  taxonomy is structurally implausible for this drug
  0.5  unknown     not enough evidence to judge (no taxonomy, or not a gated code)

Reference data:
  infusion_taxonomies.csv   NUCC taxonomy codes classed as infusion-capable
                            (AIC ambulatory infusion, AIS infusion pharmacy)
The physician taxonomies that administer buy-and-bill specialty drugs (medical
oncology, rheumatology, neurology, hematology, allergy/immunology, and the like)
are enumerated here from the NUCC code structure. This is a plausibility screen,
not a coverage determination.
"""
from __future__ import annotations

import os
import pandas as pd

# NUCC taxonomy prefixes for physician specialties that commonly administer
# clinician-infused / injected specialty drugs (buy-and-bill). Prefix match keeps
# this robust to the trailing digits that distinguish sub-specialties.
_ADMIN_PHYSICIAN_PREFIXES = (
    "207R",   # Internal Medicine (and subspecialties: 207RH heme, 207RI immun,
              # 207RR rheum, 207RX oncology-adjacent)
    "2080",   # Pediatrics (subspecialties incl. heme/onc, rheum, immunology)
    "2084",   # Neurology / Psychiatry & Neurology (208400000X etc.)
    "207Q",   # Family Medicine (can administer in-office)
    "207T",   # Neurological Surgery (rare, allowed)
    "207K",   # Allergy & Immunology
    "207N",   # Dermatology (biologics)
    "208U",   # Clinical Pharmacology
    "163W",   # Registered Nurse (infusion administration under supervision)
    "364S",   # Clinical Nurse Specialist
    "363L",   # Nurse Practitioner
    "261Q",   # Clinic/Center (many infusion clinics)
    "333600", # Pharmacy (supplier-billed)
    "3336",   # Pharmacy subclasses
    "251",    # Home health / agencies (home infusion)
    "3416",   # Ambulance/DME-adjacent suppliers (rare)
)

# Taxonomy prefixes that are structurally implausible as the biller of an
# infused specialty drug (non-administering, non-supplier provider types).
_IMPLAUSIBLE_PREFIXES = (
    "122300000X",  # Dentist
    "1223",        # Dental subclasses
    "152W",        # Optometrist
    "213E",        # Podiatrist
    "111N",        # Chiropractor
    "213",         # Podiatric medicine subclasses
    "156F",        # Technologist/technician, various
    "146",         # EMT / paramedic
    "225",         # Physical/occupational therapy, speech
    "231H",        # Audiologist
    "183500000X",  # Pharmacist (individual, not a billing supplier)
)


def _load_infusion_taxonomies(ref_dir):
    path = os.path.join(ref_dir or os.path.join(os.path.dirname(__file__), "reference"),
                        "infusion_taxonomies.csv")
    if not os.path.exists(path):
        return set()
    df = pd.read_csv(path, dtype=str)
    return set(df["taxonomy_code"].str.strip().str.upper())


def _is_gated_drug(hcpcs: str) -> bool:
    """A HCPCS that is a clinician-administered specialty drug (J-code, or Q/C
    biological), i.e. one where the biller should be an administering provider or
    a supplier. Oral/self-administered codes are not gated here."""
    if not hcpcs:
        return False
    h = str(hcpcs).strip().upper()
    return len(h) == 5 and h[0] in ("J", "Q", "C") and h[1:].isdigit()


def _taxonomy_verdict(tax: str, infusion_codes: set) -> float:
    if not tax:
        return 0.5
    t = str(tax).strip().upper()
    if not t:
        return 0.5
    if t in infusion_codes:
        return 1.0
    if any(t.startswith(p) for p in _IMPLAUSIBLE_PREFIXES):
        return 0.0
    if any(t.startswith(p) for p in _ADMIN_PHYSICIAN_PREFIXES):
        return 1.0
    return 0.5  # unknown specialty: do not penalize


def coherence_series(pred: pd.DataFrame, std: pd.DataFrame, ref_dir=None,
                     mapping=None, directory: dict = None) -> pd.Series:
    """Per-row coherence score (1 / 0 / 0.5) for each recovered NPI against the
    billed HCPCS. Needs the recovered NPI's taxonomy, taken from a supplied
    NPPES directory dict {npi: {taxonomy_code}} when available, else from a
    'recovered_taxonomy' column on pred, else neutral."""
    infusion_codes = _load_infusion_taxonomies(ref_dir)
    n = len(pred)
    hc_col = None
    for c in ("hcpcs", "hcpcs_cpt", "code"):
        if std is not None and c in std.columns:
            hc_col = c
            break
    if mapping and mapping.get("hcpcs") in (std.columns if std is not None else []):
        hc_col = mapping["hcpcs"]
    hcpcs = (std[hc_col].astype(str).to_numpy() if hc_col is not None
             else pd.Series([""] * n).to_numpy())

    # resolve taxonomy for each recovered NPI
    npis = pred.get("recovered_npi", pd.Series([None] * n)).astype("string").fillna("")
    if "recovered_taxonomy" in pred.columns:
        taxes = pred["recovered_taxonomy"].astype("string").fillna("")
    elif directory:
        taxes = npis.map(lambda x: (directory.get(x, {}) or {}).get("taxonomy_code", ""))
    else:
        taxes = pd.Series([""] * n)

    out = []
    for i in range(n):
        if not _is_gated_drug(hcpcs[i] if i < len(hcpcs) else ""):
            out.append(0.5)          # not a gated drug: no opinion
            continue
        out.append(_taxonomy_verdict(taxes.iloc[i] if i < len(taxes) else "",
                                     infusion_codes))
    return pd.Series(out, index=pred.index, dtype=float)


def coherence_screen(pred: pd.DataFrame, std: pd.DataFrame, ref_dir=None,
                     mapping=None, directory: dict = None) -> pd.DataFrame:
    """Diligence view: the incoherent recoveries, the ones worth a second look.
    Returns rows where a recovered NPI's taxonomy is structurally implausible for
    the billed drug."""
    score = coherence_series(pred, std, ref_dir=ref_dir, mapping=mapping,
                             directory=directory)
    hc_col = next((c for c in ("hcpcs", "hcpcs_cpt", "code")
                   if std is not None and c in std.columns), None)
    out = pd.DataFrame({
        "row": pred.index,
        "recovered_npi": pred.get("recovered_npi"),
        "hcpcs": std[hc_col].to_numpy() if hc_col else "",
        "coherence": score,
        "verdict": pd.Series(score).map({1.0: "coherent", 0.0: "incoherent"}).fillna("unknown"),
    })
    flagged = out[out["coherence"] == 0.0].copy()
    n_judged = int((score != 0.5).sum())
    flagged.attrs["note"] = (
        f"{len(flagged)} recovered NPIs have a taxonomy structurally implausible "
        f"for the billed specialty drug, out of {n_judged} judged. These are "
        f"recovery-precision risks: the recovered biller likely does not administer "
        f"this drug. Unjudged rows lacked a taxonomy or a gated HCPCS.")
    flagged.attrs["source"] = "NUCC taxonomy structure + infusion_taxonomies.csv"
    return flagged.reset_index(drop=True)
