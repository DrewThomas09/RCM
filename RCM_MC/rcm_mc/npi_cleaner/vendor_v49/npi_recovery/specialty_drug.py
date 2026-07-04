"""
specialty_drug.py  (v48)
========================

A data-driven model of which provider specialties bill which drugs, replacing the
hand-coded taxonomy gate with an empirical, graded plausibility. The taxonomy
coherence screen answers a binary question from a fixed prefix list: can this
specialty plausibly bill this drug. That is a hand-set rule. This model answers the
richer question from real billing frequencies: how plausible is it, on a continuous
scale, given how the drug is actually billed across specialties.

It fits from a utilization table, which can come from either:

  the public Medicare Physician and Other Practitioners PUF (NPI, provider type,
  HCPCS, service counts), which is not VRDC-restricted, or

  the RIF carrier census inside the VRDC enclave (performing physician specialty by
  HCPCS), which is the ground truth.

From that it builds, per drug, the specialty distribution P(specialty | drug), and
per specialty, the drug distribution P(drug | specialty), with add-one smoothing so
an unseen specialty-drug pair gets a small non-zero probability rather than a hard
zero. The plausibility score for a recovered NPI is where its specialty sits in the
drug's specialty distribution: a specialty that bills a large share of the drug
scores high, one that essentially never bills it scores low.

It ships with a clinically grounded PRIOR seed (not claimed to be real
frequencies): for the specialty drugs in the toolkit's scope, the set of
specialties that actually administer each drug, as a uniform prior over those
specialties. The point of the module is the refit from real data; the prior makes
it useful out of the box and is clearly labeled as a prior.

Everything is deterministic and hand-rolled.
"""
from __future__ import annotations

import os
import json
import pandas as pd
import numpy as np


# --------------------------------------------------------------------------- #
# clinically grounded PRIOR: specialties that administer each specialty drug.
# This is a prior over plausible billers, NOT measured frequencies. It is used
# only until the model is refit from real utilization. Taxonomy is by NUCC
# specialty label to stay readable; the model keys on whatever specialty label the
# utilization table uses.
# --------------------------------------------------------------------------- #
_PRIOR = {
    # HCPCS -> plausible administering specialties (equal prior weight)
    "J1745": ["Rheumatology", "Gastroenterology", "Neurology", "Hematology-Oncology",
              "Allergy/Immunology", "Internal Medicine", "Infectious Disease"],  # infliximab
    "J9312": ["Hematology-Oncology", "Rheumatology", "Neurology"],               # rituximab
    "J3357": ["Dermatology", "Gastroenterology", "Rheumatology"],                # ustekinumab SC
    "J2350": ["Neurology"],                                                       # ocrelizumab
    "J0129": ["Rheumatology", "Neurology"],                                       # abatacept
    "J1569": ["Neurology", "Hematology-Oncology", "Allergy/Immunology",
              "Rheumatology", "Internal Medicine"],                               # IVIG (gammagard)
    "J1561": ["Neurology", "Hematology-Oncology", "Allergy/Immunology",
              "Rheumatology", "Internal Medicine"],                               # IVIG (gamunex)
}

# specialties that essentially never administer clinician-infused specialty drugs
_IMPLAUSIBLE_SPECIALTIES = {
    "Dentist", "Podiatry", "Optometry", "Chiropractic", "Physical Therapy",
    "Occupational Therapy", "Audiology", "Speech Language Pathology",
}

_SMOOTHING = 1.0  # add-one (Laplace) smoothing on the specialty-drug counts


class SpecialtyDrugModel:
    """Holds the fitted specialty-drug distributions and scores plausibility."""

    def __init__(self):
        self.drug_specialty = {}   # hcpcs -> {specialty: prob}
        self.specialty_drug = {}   # specialty -> {hcpcs: prob}
        self.specialty_prior = {}  # specialty -> overall share
        self.fitted_from = "unfitted"
        self.n_specialties = 0

    # ------------------------------------------------------------------ fit --
    def fit(self, util: pd.DataFrame, *, specialty_col="specialty", hcpcs_col="hcpcs",
            weight_col=None, source="utilization") -> "SpecialtyDrugModel":
        """Fit from a utilization table. weight_col is a service or provider count;
        if absent, each row counts once (one provider-drug observation)."""
        d = util[[specialty_col, hcpcs_col]].copy()
        d.columns = ["specialty", "hcpcs"]
        d["specialty"] = d["specialty"].astype(str).str.strip()
        d["hcpcs"] = d["hcpcs"].astype(str).str.strip().str.upper()
        w = (pd.to_numeric(util[weight_col], errors="coerce").fillna(0.0).to_numpy()
             if weight_col and weight_col in util.columns else np.ones(len(d)))
        d["w"] = w
        d = d[(d["specialty"] != "") & (d["hcpcs"] != "")]

        specialties = sorted(d["specialty"].unique())
        self.n_specialties = len(specialties)

        # P(specialty | drug) with add-one smoothing over the observed specialties
        self.drug_specialty = {}
        for hcpcs, grp in d.groupby("hcpcs"):
            counts = grp.groupby("specialty")["w"].sum()
            sm = counts.reindex(specialties, fill_value=0.0) + _SMOOTHING
            probs = sm / sm.sum()
            self.drug_specialty[hcpcs] = probs.to_dict()

        # P(drug | specialty)
        self.specialty_drug = {}
        for spec, grp in d.groupby("specialty"):
            counts = grp.groupby("hcpcs")["w"].sum()
            probs = counts / counts.sum()
            self.specialty_drug[spec] = probs.to_dict()

        # overall specialty prior
        tot = d.groupby("specialty")["w"].sum()
        self.specialty_prior = (tot / tot.sum()).to_dict()
        self.fitted_from = source
        return self

    def fit_prior(self) -> "SpecialtyDrugModel":
        """Build the model from the clinically grounded prior (uniform over the
        plausible specialties for each drug). Clearly a prior, not measured data."""
        rows = []
        for hcpcs, specs in _PRIOR.items():
            for s in specs:
                rows.append({"specialty": s, "hcpcs": hcpcs, "w": 1.0})
        util = pd.DataFrame(rows)
        self.fit(util, weight_col="w", source="clinical_prior")
        return self

    # ---------------------------------------------------------------- score --
    def plausibility(self, specialty: str, hcpcs: str) -> float:
        """How plausible is it that this specialty bills this drug, in [0,1].

        Defined as the specialty's share within the drug's specialty distribution,
        normalized against the top specialty for that drug, so the most common
        biller of the drug scores near 1 and a specialty that never bills it scores
        near 0. Returns 0.5 (neutral) when the drug is unknown to the model."""
        if not hcpcs:
            return 0.5
        h = str(hcpcs).strip().upper()
        s = str(specialty).strip()
        if s in _IMPLAUSIBLE_SPECIALTIES:
            return 0.0
        dist = self.drug_specialty.get(h)
        if not dist:
            return 0.5  # drug not in the model: no opinion
        p = dist.get(s)
        if p is None:
            # unseen specialty for a known drug: use the smoothed floor
            p = _SMOOTHING / (sum(dist.values()) * 0 + 1.0) if False else min(dist.values())
        top = max(dist.values())
        return round(float(p / top), 4) if top > 0 else 0.5

    def specialty_distribution(self, hcpcs: str, top_k=10) -> pd.DataFrame:
        """The specialty mix for a drug: who actually bills it. A useful standalone
        diligence read, not just a recovery input."""
        h = str(hcpcs).strip().upper()
        dist = self.drug_specialty.get(h)
        if not dist:
            return pd.DataFrame({"note": [f"{h} not in the model"]})
        s = pd.Series(dist).sort_values(ascending=False).head(top_k)
        out = pd.DataFrame({"specialty": s.index, "share_of_drug": s.to_numpy().round(4)})
        out.attrs["note"] = (f"Specialty mix for {h} ({self.fitted_from}). Shares sum "
                             f"to ~1 across all specialties; top {len(out)} shown.")
        return out

    # --------------------------------------------------------------- persist --
    def to_json(self, path):
        with open(path, "w") as f:
            json.dump({"drug_specialty": self.drug_specialty,
                       "specialty_drug": self.specialty_drug,
                       "specialty_prior": self.specialty_prior,
                       "fitted_from": self.fitted_from,
                       "n_specialties": self.n_specialties}, f)
        return path

    @classmethod
    def from_json(cls, path):
        m = cls()
        with open(path) as f:
            d = json.load(f)
        m.drug_specialty = d.get("drug_specialty", {})
        m.specialty_drug = d.get("specialty_drug", {})
        m.specialty_prior = d.get("specialty_prior", {})
        m.fitted_from = d.get("fitted_from", "loaded")
        m.n_specialties = d.get("n_specialties", 0)
        return m


# --------------------------------------------------------------------------- #
# module-level helpers that mirror taxonomy_coherence's interface so recovery can
# use the graded model in place of the hand-coded gate
# --------------------------------------------------------------------------- #
def default_model() -> SpecialtyDrugModel:
    """The prior-fitted model, for out-of-the-box use before a real refit."""
    return SpecialtyDrugModel().fit_prior()


def plausibility_series(pred: pd.DataFrame, std: pd.DataFrame, model: SpecialtyDrugModel,
                        mapping=None, specialty_lookup: dict = None) -> pd.Series:
    """Per-row plausibility for each recovered NPI against the billed drug. Needs
    the recovered NPI's specialty, from a supplied {npi: specialty} lookup or a
    'recovered_specialty' column on pred, else neutral."""
    n = len(pred)
    hc_col = None
    for c in ("hcpcs", "hcpcs_cpt", "code"):
        if std is not None and c in std.columns:
            hc_col = c
            break
    if mapping and mapping.get("hcpcs") in (std.columns if std is not None else []):
        hc_col = mapping["hcpcs"]
    hcpcs = (std[hc_col].astype(str).to_numpy() if hc_col is not None
             else np.array([""] * n))

    npis = pred.get("recovered_npi", pd.Series([None] * n)).astype("string").fillna("")
    if "recovered_specialty" in pred.columns:
        specs = pred["recovered_specialty"].astype("string").fillna("")
    elif specialty_lookup:
        specs = npis.map(lambda x: specialty_lookup.get(x, ""))
    else:
        specs = pd.Series([""] * n)

    out = []
    for i in range(n):
        out.append(model.plausibility(specs.iloc[i] if i < len(specs) else "",
                                      hcpcs[i] if i < len(hcpcs) else ""))
    return pd.Series(out, index=pred.index, dtype=float)


def plausibility_screen(pred: pd.DataFrame, std: pd.DataFrame, model: SpecialtyDrugModel = None,
                        mapping=None, specialty_lookup: dict = None,
                        threshold=0.1) -> pd.DataFrame:
    """Flag recovered NPIs whose specialty is an implausible biller of the drug,
    graded by the model. Lower score = less plausible. Returns the flagged rows."""
    model = model or default_model()
    score = plausibility_series(pred, std, model, mapping=mapping,
                                specialty_lookup=specialty_lookup)
    hc_col = next((c for c in ("hcpcs", "hcpcs_cpt", "code")
                   if std is not None and c in std.columns), None)
    out = pd.DataFrame({
        "row": pred.index,
        "recovered_npi": pred.get("recovered_npi"),
        "hcpcs": std[hc_col].to_numpy() if hc_col else "",
        "plausibility": score,
    })
    flagged = out[(out["plausibility"] < threshold)].copy()
    n_judged = int((score != 0.5).sum())
    flagged.attrs["note"] = (
        f"{len(flagged)} recovered NPIs have a specialty that is an implausible biller "
        f"of the drug (plausibility < {threshold}), out of {n_judged} judged, using the "
        f"{model.fitted_from} model. Lower plausibility means the recovered biller's "
        f"specialty rarely or never bills this drug in the utilization data. These are "
        f"recovery-precision risks.")
    flagged.attrs["source"] = f"specialty-drug model ({model.fitted_from})"
    return flagged.reset_index(drop=True)


def build_utilization_from_rif(rif_std: pd.DataFrame, specialty_lookup: dict = None) -> pd.DataFrame:
    """Turn standardized RIF carrier data into a utilization table for fitting:
    performing physician specialty by HCPCS with a service-count weight. The
    specialty comes from a {npi: specialty} lookup (NPPES) applied to the rendering
    NPI, or a 'rendering_specialty' column if already enriched."""
    if "hcpcs" not in rif_std.columns:
        return pd.DataFrame(columns=["specialty", "hcpcs", "w"])
    rcol = "rendering_npi" if "rendering_npi" in rif_std.columns else None
    if "rendering_specialty" in rif_std.columns:
        spec = rif_std["rendering_specialty"].astype(str)
    elif rcol and specialty_lookup:
        spec = rif_std[rcol].astype("string").map(lambda x: specialty_lookup.get(str(x), ""))
    else:
        return pd.DataFrame(columns=["specialty", "hcpcs", "w"])
    w = (pd.to_numeric(rif_std["units"], errors="coerce").fillna(1.0)
         if "units" in rif_std.columns else pd.Series(np.ones(len(rif_std))))
    util = pd.DataFrame({"specialty": spec.to_numpy(), "hcpcs": rif_std["hcpcs"].astype(str).to_numpy(),
                         "w": w.to_numpy()})
    return util[(util["specialty"].astype(str) != "") & (util["specialty"].astype(str) != "nan")]
