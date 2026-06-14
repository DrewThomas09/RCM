"""Infusion / clinician-administered drug J-code catalog, tied to disease.

The platform already had a 12-code marquee J-code ASP reference
(``cms_asp_pricing.INFUSION_HCPCS``). That answers "what does Medicare
pay per unit" but not the two questions an infusion diligence actually
turns on:

  1. **Site of care, and the change** — is this drug administered at
     HOPD, an ambulatory infusion suite (AIC), a physician office, or
     in the patient's HOME, and which way is the mix MOVING? The
     home/office migration out of the hospital is the entire thesis;
     every code migrates at a different speed.
  2. **Which disease does it treat** — a J-code is only demand if you
     tie it to its indication(s), the epidemiology of that disease, and
     therefore the size of the patient pool a platform can serve.

This module is the catalog that answers both. It is a DATA layer only —
public CMS facts (the HCPCS code, descriptor, billed unit) plus the
drug's FDA-labeled indication(s), a representative ICD-10 family, and a
published treated-prevalence anchor. The site-of-care mix is modeled by
labeled **archetype** (a drug class shares a migration pattern), with a
2018 anchor and a current anchor so the *change* is explicit and
recomputable — never a fabricated per-code time-series. The dollar
dimension (ASP payment limit) is filled in live from
``cms_asp_pricing`` by the analysis layer, not here.

Every magnitude is a labeled starting point for an engagement, not the
fund's proprietary research — the same honesty contract as the rest of
the infusion stack.
"""
from __future__ import annotations

from typing import Any, Dict, List

# ── Site-of-care archetypes ──────────────────────────────────────────
#
# A J-code's site-of-care mix is not unique per drug — it follows the
# migration pattern of its therapeutic class. Each archetype carries a
# 2018 anchor and a current (2024) anchor across the four sites; the
# *change* between them IS the "home vs office shift" the page reports.
# Shares are fractions summing to ~1.0. ``now`` = 2024, ``then`` = 2018.
# These are documented analyst anchors (NHIA / MedPAC site-of-care
# literature + payer site-of-care-steerage reporting), labeled as such —
# replace with a claims place-of-service time-series in diligence.

SOC_THEN_YEAR = 2018
SOC_NOW_YEAR = 2024

_SITE_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "ivig_home_shift": {
        "label": "IVIG / SCIG — strong home migration",
        "then": {"home": 0.28, "office": 0.12, "aic": 0.18, "hopd": 0.42},
        "now": {"home": 0.46, "office": 0.10, "aic": 0.24, "hopd": 0.20},
        "thesis": "Chronic, stable, SCIG self-/nurse-administered — the "
                  "fastest home-shifting category and the margin engine.",
    },
    "immunology_steered": {
        "label": "Immunology / IBD biologics — payer-steered out of HOPD",
        "then": {"home": 0.10, "office": 0.20, "aic": 0.22, "hopd": 0.48},
        "now": {"home": 0.18, "office": 0.16, "aic": 0.36, "hopd": 0.30},
        "thesis": "Site-of-care steerage + white-bagging push stable "
                  "biologic maintenance from HOPD into AIC then home.",
    },
    "ms_aic": {
        "label": "Neurology (MS) infusions — HOPD → ambulatory suite",
        "then": {"home": 0.04, "office": 0.10, "aic": 0.26, "hopd": 0.60},
        "now": {"home": 0.08, "office": 0.08, "aic": 0.46, "hopd": 0.38},
        "thesis": "High-acuity monitoring keeps these in a chair, but the "
                  "chair is migrating from hospital to freestanding AIC.",
    },
    "oncology_hopd": {
        "label": "Oncology (chemo / checkpoint) — sticky to HOPD/office",
        "then": {"home": 0.01, "office": 0.30, "aic": 0.14, "hopd": 0.55},
        "now": {"home": 0.02, "office": 0.34, "aic": 0.20, "hopd": 0.44},
        "thesis": "Acuity, toxicity monitoring, and oncologist control keep "
                  "these in HOPD / oncology office — slow, modest migration.",
    },
    "onc_support": {
        "label": "Oncology support (GCSF / bone) — office & AIC",
        "then": {"home": 0.03, "office": 0.46, "aic": 0.21, "hopd": 0.30},
        "now": {"home": 0.06, "office": 0.44, "aic": 0.30, "hopd": 0.20},
        "thesis": "Adjunctive, lower-acuity — on-body injectors and AIC "
                  "chairs pull these out of the hospital.",
    },
    "rare_home": {
        "label": "Enzyme-replacement / factor — home-heavy specialty",
        "then": {"home": 0.34, "office": 0.10, "aic": 0.16, "hopd": 0.40},
        "now": {"home": 0.52, "office": 0.08, "aic": 0.22, "hopd": 0.18},
        "thesis": "Lifelong rare-disease therapy, specialized handling — "
                  "ideal for home once tolerance is established.",
    },
    "pah_home": {
        "label": "PAH / continuous infusion — home-dominant",
        "then": {"home": 0.72, "office": 0.04, "aic": 0.06, "hopd": 0.18},
        "now": {"home": 0.82, "office": 0.03, "aic": 0.05, "hopd": 0.10},
        "thesis": "Continuous ambulatory-pump therapy — home is the only "
                  "practical site; near-fully migrated already.",
    },
    "asthma_office_home": {
        "label": "Respiratory / allergy biologics — office → home",
        "then": {"home": 0.20, "office": 0.62, "aic": 0.06, "hopd": 0.12},
        "now": {"home": 0.38, "office": 0.46, "aic": 0.08, "hopd": 0.08},
        "thesis": "Prefilled-syringe / autoinjector formulations move "
                  "stable patients from the allergist office to home.",
    },
    "hae_home": {
        "label": "Hereditary angioedema — home / self-administered",
        "then": {"home": 0.58, "office": 0.10, "aic": 0.08, "hopd": 0.24},
        "now": {"home": 0.74, "office": 0.06, "aic": 0.08, "hopd": 0.12},
        "thesis": "On-demand + prophylaxis therapy patients self-administer "
                  "at home; acute attacks still hit the ED/HOPD.",
    },
    "inotrope_home": {
        "label": "Advanced-HF inotropes — home palliative / bridge",
        "then": {"home": 0.55, "office": 0.03, "aic": 0.04, "hopd": 0.38},
        "now": {"home": 0.66, "office": 0.02, "aic": 0.04, "hopd": 0.28},
        "thesis": "Continuous milrinone/dobutamine via ambulatory pump — "
                  "home avoids a prolonged stage-D admission.",
    },
    "office_injectable": {
        "label": "Office-administered injectable — stable in office",
        "then": {"home": 0.05, "office": 0.84, "aic": 0.03, "hopd": 0.08},
        "now": {"home": 0.06, "office": 0.83, "aic": 0.04, "hopd": 0.07},
        "thesis": "Procedure-bound (e.g. intravitreal) — site is fixed by "
                  "the route of administration; little migration.",
    },
}


def site_archetypes() -> Dict[str, Dict[str, Any]]:
    """The labeled site-of-care archetypes (with 2018 + current anchors)."""
    return {k: dict(v) for k, v in _SITE_ARCHETYPES.items()}


# ── The J-code → drug → disease catalog ──────────────────────────────
#
# Fields per entry:
#   hcpcs       public HCPCS J/Q-code
#   drug        brand (descriptor)
#   unit        billed unit (CMS descriptor)
#   drug_class  therapeutic class
#   soc         site-of-care archetype key (above)
#   diseases    FDA-labeled indication(s) — the disease tie
#   icd10       representative ICD-10 family/code(s)
#   epi_per_100k treated-prevalence anchor (per 100k of the denominator)
#   epi_basis   the published source/rationale for the rate
#   denominator "population" | "seniors" (which base the rate applies to)
#   biosimilar  True if a biosimilar (an ASP-erosion / drug-margin flag)
#   note        diligence-relevant colour
#
# Codes + descriptors are public CMS facts; indications are the FDA
# label; epi rates are labeled published anchors. Illustrative.

_CATALOG: List[Dict[str, Any]] = [
    # ── Immunology / IBD (anti-TNF, integrin, IL) ────────────────────
    {"hcpcs": "J1745", "drug": "Infliximab (Remicade)", "unit": "per 10 mg",
     "drug_class": "Immunology (anti-TNF)", "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Crohn's disease",
                  "Ulcerative colitis", "Psoriatic arthritis",
                  "Ankylosing spondylitis", "Plaque psoriasis"],
     "icd10": ["M05-M06", "K50", "K51", "L40.5"], "epi_per_100k": 60.0,
     "epi_basis": "Autoimmune-biologic treated pool on IV anti-TNF "
                  "(ACR / Crohn's & Colitis Foundation prevalence)",
     "denominator": "population", "biosimilar": False,
     "note": "The anchor buy-and-bill biologic — biosimilar-eroded ASP."},
    {"hcpcs": "Q5103", "drug": "Infliximab-dyyb (Inflectra)",
     "unit": "per 10 mg", "drug_class": "Immunology (anti-TNF biosimilar)",
     "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Crohn's disease",
                  "Ulcerative colitis"], "icd10": ["M05-M06", "K50", "K51"],
     "epi_per_100k": 18.0,
     "epi_basis": "Biosimilar share of the IV infliximab pool",
     "denominator": "population", "biosimilar": True,
     "note": "First infliximab biosimilar — the ASP-deflation driver."},
    {"hcpcs": "Q5104", "drug": "Infliximab-abda (Renflexis)",
     "unit": "per 10 mg", "drug_class": "Immunology (anti-TNF biosimilar)",
     "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Crohn's disease",
                  "Ulcerative colitis"], "icd10": ["M05-M06", "K50", "K51"],
     "epi_per_100k": 14.0, "epi_basis": "Biosimilar share of IV infliximab",
     "denominator": "population", "biosimilar": True,
     "note": "Second infliximab biosimilar — competes on contracted price."},
    {"hcpcs": "J3380", "drug": "Vedolizumab (Entyvio)", "unit": "per 1 mg",
     "drug_class": "Immunology (gut-selective integrin)",
     "soc": "immunology_steered",
     "diseases": ["Crohn's disease", "Ulcerative colitis"],
     "icd10": ["K50", "K51"], "epi_per_100k": 22.0,
     "epi_basis": "IBD biologic-treated prevalence (gut-selective share)",
     "denominator": "population", "biosimilar": False,
     "note": "Gut-selective IBD anchor — heavy site-of-care steerage."},
    {"hcpcs": "J3357", "drug": "Ustekinumab (Stelara)", "unit": "per 1 mg",
     "drug_class": "Immunology (IL-12/23)", "soc": "immunology_steered",
     "diseases": ["Crohn's disease", "Ulcerative colitis",
                  "Plaque psoriasis", "Psoriatic arthritis"],
     "icd10": ["K50", "K51", "L40"], "epi_per_100k": 26.0,
     "epi_basis": "IL-12/23 treated psoriasis + IBD pool",
     "denominator": "population", "biosimilar": False,
     "note": "IV induction then SC — biosimilars launching, ASP at risk."},
    {"hcpcs": "J3262", "drug": "Tocilizumab (Actemra)", "unit": "per 1 mg",
     "drug_class": "Immunology (IL-6)", "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Giant cell arteritis",
                  "Cytokine release syndrome"],
     "icd10": ["M05-M06", "M31.6"], "epi_per_100k": 16.0,
     "epi_basis": "IL-6 inhibitor treated RA + GCA pool",
     "denominator": "population", "biosimilar": False,
     "note": "RA + GCA; IV and SC forms."},
    {"hcpcs": "J0129", "drug": "Abatacept (Orencia)", "unit": "per 10 mg",
     "drug_class": "Immunology (T-cell co-stim)", "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Psoriatic arthritis",
                  "Juvenile idiopathic arthritis"],
     "icd10": ["M05-M06", "M08"], "epi_per_100k": 14.0,
     "epi_basis": "T-cell co-stimulation-blocker treated RA pool",
     "denominator": "population", "biosimilar": False,
     "note": "IV q4wk maintenance — AIC/home steerage candidate."},
    {"hcpcs": "J1602", "drug": "Golimumab (Simponi Aria)", "unit": "per 1 mg",
     "drug_class": "Immunology (anti-TNF)", "soc": "immunology_steered",
     "diseases": ["Rheumatoid arthritis", "Psoriatic arthritis",
                  "Ankylosing spondylitis"], "icd10": ["M05-M06", "M45"],
     "epi_per_100k": 9.0, "epi_basis": "IV anti-TNF treated rheumatology pool",
     "denominator": "population", "biosimilar": False,
     "note": "IV-only anti-TNF formulation."},
    {"hcpcs": "J0490", "drug": "Belimumab (Benlysta)", "unit": "per 10 mg",
     "drug_class": "Immunology (BLyS / lupus)", "soc": "immunology_steered",
     "diseases": ["Systemic lupus erythematosus", "Lupus nephritis"],
     "icd10": ["M32"], "epi_per_100k": 13.0,
     "epi_basis": "SLE prevalence ≈73/100k × treated-on-biologic share "
                  "(Lupus Foundation / CDC)",
     "denominator": "population", "biosimilar": False,
     "note": "Lupus — IV and SC; chronic recurring volume."},

    # ── Neurology (MS / CIDP / NMOSD / migraine) ─────────────────────
    {"hcpcs": "J2350", "drug": "Ocrelizumab (Ocrevus)", "unit": "per 1 mg",
     "drug_class": "Neurology (anti-CD20, MS)", "soc": "ms_aic",
     "diseases": ["Multiple sclerosis (RRMS)",
                  "Primary progressive MS"], "icd10": ["G35"],
     "epi_per_100k": 30.0,
     "epi_basis": "MS prevalence ≈300/100k × anti-CD20 treated share "
                  "(National MS Society)",
     "denominator": "population", "biosimilar": False,
     "note": "Dominant MS infusion — q6mo; AIC chair migration."},
    {"hcpcs": "J2323", "drug": "Natalizumab (Tysabri)", "unit": "per 1 mg",
     "drug_class": "Neurology (integrin, MS/IBD)", "soc": "ms_aic",
     "diseases": ["Multiple sclerosis (RRMS)", "Crohn's disease"],
     "icd10": ["G35", "K50"], "epi_per_100k": 14.0,
     "epi_basis": "MS + Crohn's natalizumab-treated share (PML-monitored)",
     "denominator": "population", "biosimilar": False,
     "note": "q4wk; REMS/PML monitoring keeps it chair-bound."},
    {"hcpcs": "J1823", "drug": "Inebilizumab (Uplizna)", "unit": "per 1 mg",
     "drug_class": "Neurology (anti-CD19, NMOSD)", "soc": "ms_aic",
     "diseases": ["Neuromyelitis optica spectrum disorder"],
     "icd10": ["G36.0"], "epi_per_100k": 1.0,
     "epi_basis": "NMOSD prevalence ≈1-2/100k (rare; Guthy-Jackson)",
     "denominator": "population", "biosimilar": False,
     "note": "Rare anti-CD19; ultra-orphan, high cost per patient."},
    {"hcpcs": "J3032", "drug": "Eptinezumab (Vyepti)", "unit": "per 1 mg",
     "drug_class": "Neurology (anti-CGRP, migraine)", "soc": "ms_aic",
     "diseases": ["Chronic migraine prevention"], "icd10": ["G43.7"],
     "epi_per_100k": 40.0,
     "epi_basis": "Chronic-migraine prevalence × IV-CGRP treated share",
     "denominator": "population", "biosimilar": False,
     "note": "IV q3mo migraine prophylaxis — newest AIC volume driver."},

    # ── IVIG / SCIG (the home margin engine) ─────────────────────────
    {"hcpcs": "J1569", "drug": "Immune globulin (Gammagard liquid)",
     "unit": "per 500 mg", "drug_class": "Immune globulin (IVIG)",
     "soc": "ivig_home_shift",
     "diseases": ["Primary immunodeficiency", "CIDP",
                  "Multifocal motor neuropathy"],
     "icd10": ["D80-D83", "G61.81"], "epi_per_100k": 18.0,
     "epi_basis": "PI ≈25-40/100k + CIDP ≈8.9/100k treated-IG share (IDF)",
     "denominator": "population", "biosimilar": False,
     "note": "Flagship IVIG — chronic, the richest home category."},
    {"hcpcs": "J1561", "drug": "Immune globulin (Gamunex-C / Gammaked)",
     "unit": "per 500 mg", "drug_class": "Immune globulin (IVIG/SCIG)",
     "soc": "ivig_home_shift",
     "diseases": ["Primary immunodeficiency", "CIDP",
                  "Idiopathic thrombocytopenic purpura"],
     "icd10": ["D80-D83", "G61.81", "D69.3"], "epi_per_100k": 15.0,
     "epi_basis": "Treated PI/CIDP/ITP IG-product share",
     "denominator": "population", "biosimilar": False,
     "note": "IV + subcutaneous label — SCIG is the home-shift wedge."},
    {"hcpcs": "J1459", "drug": "Immune globulin (Privigen)",
     "unit": "per 500 mg", "drug_class": "Immune globulin (IVIG)",
     "soc": "ivig_home_shift",
     "diseases": ["Primary immunodeficiency", "ITP", "CIDP"],
     "icd10": ["D80-D83", "D69.3", "G61.81"], "epi_per_100k": 12.0,
     "epi_basis": "Treated PI/ITP/CIDP IG-product share",
     "denominator": "population", "biosimilar": False,
     "note": "High-volume IVIG product; supply-constrained category."},
    {"hcpcs": "J1599", "drug": "Immune globulin, NOS", "unit": "per 500 mg",
     "drug_class": "Immune globulin (IVIG)", "soc": "ivig_home_shift",
     "diseases": ["Primary immunodeficiency", "Secondary immunodeficiency"],
     "icd10": ["D80-D83", "D84.8"], "epi_per_100k": 10.0,
     "epi_basis": "Unspecified-IG fallback share of the IG pool",
     "denominator": "population", "biosimilar": False,
     "note": "Catch-all IG code — appears when product not specified."},

    # ── Oncology (cytotoxic / checkpoint / targeted) ─────────────────
    {"hcpcs": "J9312", "drug": "Rituximab (Rituxan)", "unit": "per 10 mg",
     "drug_class": "Oncology / immunology (anti-CD20)", "soc": "oncology_hopd",
     "diseases": ["Non-Hodgkin lymphoma", "CLL", "Rheumatoid arthritis",
                  "Granulomatosis with polyangiitis"],
     "icd10": ["C82-C85", "C91.1", "M05-M06"], "epi_per_100k": 28.0,
     "epi_basis": "NHL/CLL/RA/GPA rituximab-treated pool (SEER + ACR)",
     "denominator": "population", "biosimilar": False,
     "note": "Onc + immunology crossover; biosimilar-eroded."},
    {"hcpcs": "Q5115", "drug": "Rituximab-abbs (Truxima)", "unit": "per 10 mg",
     "drug_class": "Oncology (anti-CD20 biosimilar)", "soc": "oncology_hopd",
     "diseases": ["Non-Hodgkin lymphoma", "CLL"],
     "icd10": ["C82-C85", "C91.1"], "epi_per_100k": 9.0,
     "epi_basis": "Biosimilar share of the rituximab pool",
     "denominator": "population", "biosimilar": True,
     "note": "Rituximab biosimilar — onc ASP-deflation driver."},
    {"hcpcs": "J9035", "drug": "Bevacizumab (Avastin)", "unit": "per 10 mg",
     "drug_class": "Oncology (anti-VEGF)", "soc": "oncology_hopd",
     "diseases": ["Colorectal cancer", "Non-small-cell lung cancer",
                  "Glioblastoma", "Renal cell carcinoma"],
     "icd10": ["C18", "C34", "C71"], "epi_per_100k": 24.0,
     "epi_basis": "Multi-tumor bevacizumab-treated pool (SEER incidence)",
     "denominator": "population", "biosimilar": False,
     "note": "Broad solid-tumor anti-VEGF; biosimilar-eroded."},
    {"hcpcs": "Q5107", "drug": "Bevacizumab-awwb (Mvasi)", "unit": "per 10 mg",
     "drug_class": "Oncology (anti-VEGF biosimilar)", "soc": "oncology_hopd",
     "diseases": ["Colorectal cancer", "Non-small-cell lung cancer"],
     "icd10": ["C18", "C34"], "epi_per_100k": 11.0,
     "epi_basis": "Biosimilar share of the bevacizumab pool",
     "denominator": "population", "biosimilar": True,
     "note": "Bevacizumab biosimilar."},
    {"hcpcs": "J9355", "drug": "Trastuzumab (Herceptin)", "unit": "per 10 mg",
     "drug_class": "Oncology (anti-HER2)", "soc": "oncology_hopd",
     "diseases": ["HER2+ breast cancer", "HER2+ gastric cancer"],
     "icd10": ["C50", "C16"], "epi_per_100k": 16.0,
     "epi_basis": "HER2+ breast/gastric treated pool (SEER × HER2+ share)",
     "denominator": "population", "biosimilar": False,
     "note": "HER2 anchor; biosimilar-eroded; SC form available."},
    {"hcpcs": "J9271", "drug": "Pembrolizumab (Keytruda)", "unit": "per 1 mg",
     "drug_class": "Oncology (PD-1 checkpoint)", "soc": "oncology_hopd",
     "diseases": ["Melanoma", "Non-small-cell lung cancer",
                  "Head & neck cancer", "Many solid tumors"],
     "icd10": ["C43", "C34", "C76.0"], "epi_per_100k": 34.0,
     "epi_basis": "Broad checkpoint-treated solid-tumor pool (SEER)",
     "denominator": "population", "biosimilar": False,
     "note": "Largest-spend oncology infusion; HOPD/office-bound."},
    {"hcpcs": "J9299", "drug": "Nivolumab (Opdivo)", "unit": "per 1 mg",
     "drug_class": "Oncology (PD-1 checkpoint)", "soc": "oncology_hopd",
     "diseases": ["Melanoma", "Non-small-cell lung cancer",
                  "Renal cell carcinoma"], "icd10": ["C43", "C34", "C64"],
     "epi_per_100k": 22.0, "epi_basis": "Checkpoint-treated solid-tumor pool",
     "denominator": "population", "biosimilar": False,
     "note": "Second checkpoint anchor; high acuity."},
    {"hcpcs": "J9145", "drug": "Daratumumab (Darzalex)", "unit": "per 10 mg",
     "drug_class": "Oncology (anti-CD38, myeloma)", "soc": "oncology_hopd",
     "diseases": ["Multiple myeloma"], "icd10": ["C90.0"],
     "epi_per_100k": 7.0,
     "epi_basis": "Multiple-myeloma prevalence × daratumumab-treated share",
     "denominator": "seniors", "biosimilar": False,
     "note": "Myeloma — older-skewing; SC form (Faspro) shifts the site."},

    # ── Oncology support (GCSF / bone / anemia) ──────────────────────
    {"hcpcs": "J2505", "drug": "Pegfilgrastim (Neulasta)", "unit": "per 6 mg",
     "drug_class": "Oncology support (GCSF)", "soc": "onc_support",
     "diseases": ["Chemotherapy-induced neutropenia"], "icd10": ["D70.1"],
     "epi_per_100k": 30.0,
     "epi_basis": "Chemo patients at FN risk on prophylactic GCSF (NCCN)",
     "denominator": "population", "biosimilar": False,
     "note": "On-body injector moves this out of the chair — home wedge."},
    {"hcpcs": "J1442", "drug": "Filgrastim (Neupogen)", "unit": "per 1 mcg",
     "drug_class": "Oncology support (GCSF)", "soc": "onc_support",
     "diseases": ["Chemotherapy-induced neutropenia",
                  "Severe chronic neutropenia"], "icd10": ["D70.1", "D70.0"],
     "epi_per_100k": 14.0, "epi_basis": "Daily-GCSF treated chemo pool",
     "denominator": "population", "biosimilar": False,
     "note": "Daily GCSF; biosimilar-eroded category."},
    {"hcpcs": "J0897", "drug": "Denosumab (Prolia / Xgeva)",
     "unit": "per 1 mg", "drug_class": "Oncology support / bone",
     "soc": "onc_support",
     "diseases": ["Osteoporosis", "Bone metastases",
                  "Giant cell tumor of bone"], "icd10": ["M81", "C79.5"],
     "epi_per_100k": 120.0,
     "epi_basis": "Treated osteoporosis (high prevalence) + bone-mets pool",
     "denominator": "seniors", "biosimilar": False,
     "note": "SC q6mo — large, recurring, home-administrable panel."},
    {"hcpcs": "J2796", "drug": "Romiplostim (Nplate)", "unit": "per 10 mcg",
     "drug_class": "Hematology (TPO, ITP)", "soc": "onc_support",
     "diseases": ["Immune thrombocytopenia"], "icd10": ["D69.3"],
     "epi_per_100k": 6.0,
     "epi_basis": "ITP prevalence ≈9-12/100k × TPO-treated share",
     "denominator": "population", "biosimilar": False,
     "note": "Weekly SC ITP therapy — home self-administration."},

    # ── Rare disease — enzyme replacement / complement / factor ──────
    {"hcpcs": "J1786", "drug": "Imiglucerase (Cerezyme)", "unit": "per 1 unit",
     "drug_class": "Enzyme replacement (Gaucher)", "soc": "rare_home",
     "diseases": ["Gaucher disease (type 1)"], "icd10": ["E75.22"],
     "epi_per_100k": 0.6, "epi_basis": "Gaucher prevalence ≈1/40k (NORD)",
     "denominator": "population", "biosimilar": False,
     "note": "Ultra-high-cost ERT; lifelong; home-infusible."},
    {"hcpcs": "J0180", "drug": "Agalsidase beta (Fabrazyme)",
     "unit": "per 1 mg", "drug_class": "Enzyme replacement (Fabry)",
     "soc": "rare_home", "diseases": ["Fabry disease"], "icd10": ["E75.21"],
     "epi_per_100k": 0.5, "epi_basis": "Fabry prevalence ≈1/40k-1/60k (NORD)",
     "denominator": "population", "biosimilar": False,
     "note": "q2wk ERT; high-touch home niche."},
    {"hcpcs": "J0221", "drug": "Alglucosidase alfa (Lumizyme)",
     "unit": "per 10 mg", "drug_class": "Enzyme replacement (Pompe)",
     "soc": "rare_home", "diseases": ["Pompe disease"], "icd10": ["E74.02"],
     "epi_per_100k": 0.3, "epi_basis": "Pompe prevalence ≈1/40k (NORD)",
     "denominator": "population", "biosimilar": False,
     "note": "q2wk lifelong ERT — ultra-orphan."},
    {"hcpcs": "J1743", "drug": "Idursulfase (Elaprase)", "unit": "per 1 mg",
     "drug_class": "Enzyme replacement (MPS II)", "soc": "rare_home",
     "diseases": ["Hunter syndrome (MPS II)"], "icd10": ["E76.1"],
     "epi_per_100k": 0.1, "epi_basis": "MPS II prevalence ≈1/162k (NORD)",
     "denominator": "population", "biosimilar": False,
     "note": "Weekly ERT; pediatric-onset rare disease."},
    {"hcpcs": "J1300", "drug": "Eculizumab (Soliris)", "unit": "per 10 mg",
     "drug_class": "Complement inhibitor (C5)", "soc": "rare_home",
     "diseases": ["Paroxysmal nocturnal hemoglobinuria",
                  "Atypical HUS", "Generalized myasthenia gravis",
                  "NMOSD"], "icd10": ["D59.5", "D59.3", "G70.0"],
     "epi_per_100k": 1.5,
     "epi_basis": "PNH + aHUS + gMG complement-treated pool (rare)",
     "denominator": "population", "biosimilar": False,
     "note": "q2wk complement inhibitor — among the costliest drugs."},
    {"hcpcs": "J1303", "drug": "Ravulizumab (Ultomiris)", "unit": "per 10 mg",
     "drug_class": "Complement inhibitor (C5)", "soc": "rare_home",
     "diseases": ["Paroxysmal nocturnal hemoglobinuria", "Atypical HUS",
                  "Generalized myasthenia gravis"],
     "icd10": ["D59.5", "D59.3", "G70.0"], "epi_per_100k": 1.2,
     "epi_basis": "Long-acting C5 share of the complement pool",
     "denominator": "population", "biosimilar": False,
     "note": "q8wk successor to eculizumab — fewer infusions."},
    {"hcpcs": "J7170", "drug": "Emicizumab (Hemlibra)", "unit": "per 0.5 mg",
     "drug_class": "Hemophilia (factor mimetic)", "soc": "rare_home",
     "diseases": ["Hemophilia A"], "icd10": ["D66"], "epi_per_100k": 2.0,
     "epi_basis": "Hemophilia A prevalence ≈ male births; treated pool (NHF)",
     "denominator": "population", "biosimilar": False,
     "note": "SC prophylaxis — home self-administration standard."},
    {"hcpcs": "J7192", "drug": "Factor VIII, recombinant", "unit": "per IU",
     "drug_class": "Hemophilia (factor VIII)", "soc": "rare_home",
     "diseases": ["Hemophilia A"], "icd10": ["D66"], "epi_per_100k": 4.0,
     "epi_basis": "Hemophilia A treated factor pool (NHF / ATHN)",
     "denominator": "population", "biosimilar": False,
     "note": "Home factor infusion — the original home-infusion market."},
    {"hcpcs": "J7202", "drug": "Factor IX (Alprolix)", "unit": "per IU",
     "drug_class": "Hemophilia (factor IX)", "soc": "rare_home",
     "diseases": ["Hemophilia B"], "icd10": ["D67"], "epi_per_100k": 1.0,
     "epi_basis": "Hemophilia B treated factor pool (NHF / ATHN)",
     "denominator": "population", "biosimilar": False,
     "note": "Extended-half-life factor IX — home prophylaxis."},
    {"hcpcs": "J0791", "drug": "Crizanlizumab (Adakveo)", "unit": "per 5 mg",
     "drug_class": "Hematology (P-selectin, SCD)", "soc": "rare_home",
     "diseases": ["Sickle cell disease (VOC prevention)"],
     "icd10": ["D57.0", "D57.1"], "epi_per_100k": 10.0,
     "epi_basis": "Sickle-cell-disease prevalence × treated share (CDC)",
     "denominator": "population", "biosimilar": False,
     "note": "Monthly IV VOC prophylaxis — AIC/home candidate."},

    # ── Hereditary angioedema (HAE) ──────────────────────────────────
    {"hcpcs": "J0597", "drug": "C1 esterase inhibitor (Berinert)",
     "unit": "per 10 units", "drug_class": "HAE (C1-INH)", "soc": "hae_home",
     "diseases": ["Hereditary angioedema (acute attack)"],
     "icd10": ["D84.1"], "epi_per_100k": 2.0,
     "epi_basis": "HAE prevalence ≈1/50k (US HAE Association)",
     "denominator": "population", "biosimilar": False,
     "note": "On-demand HAE attack therapy — patient self-administers."},
    {"hcpcs": "J0596", "drug": "C1 esterase inhibitor, recomb (Ruconest)",
     "unit": "per 10 units", "drug_class": "HAE (C1-INH)", "soc": "hae_home",
     "diseases": ["Hereditary angioedema (acute attack)"],
     "icd10": ["D84.1"], "epi_per_100k": 1.0,
     "epi_basis": "Recombinant C1-INH share of the HAE pool",
     "denominator": "population", "biosimilar": False,
     "note": "Recombinant C1-INH on-demand therapy."},

    # ── Respiratory / allergy biologics ──────────────────────────────
    {"hcpcs": "J2357", "drug": "Omalizumab (Xolair)", "unit": "per 5 mg",
     "drug_class": "Respiratory (anti-IgE)", "soc": "asthma_office_home",
     "diseases": ["Severe allergic asthma", "Chronic urticaria",
                  "Nasal polyps"], "icd10": ["J45", "L50.1"],
     "epi_per_100k": 40.0,
     "epi_basis": "Severe-asthma + chronic-urticaria treated-on-biologic pool",
     "denominator": "population", "biosimilar": False,
     "note": "SC q2-4wk — prefilled syringe enables home."},
    {"hcpcs": "J2182", "drug": "Mepolizumab (Nucala)", "unit": "per 1 mg",
     "drug_class": "Respiratory (anti-IL-5)", "soc": "asthma_office_home",
     "diseases": ["Severe eosinophilic asthma", "EGPA", "HES"],
     "icd10": ["J45", "M30.1"], "epi_per_100k": 22.0,
     "epi_basis": "Severe-eosinophilic-asthma treated-on-IL5 pool",
     "denominator": "population", "biosimilar": False,
     "note": "Autoinjector available — office-to-home shift."},
    {"hcpcs": "J0517", "drug": "Benralizumab (Fasenra)", "unit": "per 1 mg",
     "drug_class": "Respiratory (anti-IL-5R)", "soc": "asthma_office_home",
     "diseases": ["Severe eosinophilic asthma"], "icd10": ["J45"],
     "epi_per_100k": 18.0,
     "epi_basis": "Severe-eosinophilic-asthma treated-on-IL5R pool",
     "denominator": "population", "biosimilar": False,
     "note": "q8wk after loading — autoinjector home option."},

    # ── PAH / pulmonary (continuous infusion) ────────────────────────
    {"hcpcs": "J3285", "drug": "Treprostinil (Remodulin)", "unit": "per 1 mg",
     "drug_class": "PAH (prostacyclin)", "soc": "pah_home",
     "diseases": ["Pulmonary arterial hypertension"], "icd10": ["I27.0",
                                                                 "I27.2"],
     "epi_per_100k": 3.0,
     "epi_basis": "PAH prevalence ≈15-50/million × parenteral-treated share",
     "denominator": "population", "biosimilar": False,
     "note": "Continuous SC/IV ambulatory pump — home-dominant by design."},
    {"hcpcs": "J1325", "drug": "Epoprostenol (Flolan / Veletri)",
     "unit": "per 0.5 mg", "drug_class": "PAH (prostacyclin)",
     "soc": "pah_home", "diseases": ["Pulmonary arterial hypertension"],
     "icd10": ["I27.0", "I27.2"], "epi_per_100k": 1.5,
     "epi_basis": "Continuous-IV-epoprostenol share of the PAH pool",
     "denominator": "population", "biosimilar": False,
     "note": "Continuous central-line IV — highest-acuity home infusion."},

    # ── Advanced heart failure (home inotropes) ──────────────────────
    {"hcpcs": "J2260", "drug": "Milrinone", "unit": "per 5 mg",
     "drug_class": "Cardiology (inotrope)", "soc": "inotrope_home",
     "diseases": ["Stage-D heart failure (bridge / palliative)"],
     "icd10": ["I50.84", "I50.9"], "epi_per_100k": 4.0,
     "epi_basis": "Stage-D HF on home inotropes — small senior subset (HFSA)",
     "denominator": "seniors", "biosimilar": False,
     "note": "Continuous ambulatory-pump inotrope — home palliative/bridge."},

    # ── Office-bound injectable (route-fixed) ────────────────────────
    {"hcpcs": "J0178", "drug": "Aflibercept (Eylea)", "unit": "per 1 mg",
     "drug_class": "Ophthalmology (anti-VEGF, intravitreal)",
     "soc": "office_injectable",
     "diseases": ["Wet age-related macular degeneration",
                  "Diabetic macular edema", "Retinal vein occlusion"],
     "icd10": ["H35.32", "E11.311"], "epi_per_100k": 90.0,
     "epi_basis": "Wet-AMD + DME treated-on-anti-VEGF pool (AAO)",
     "denominator": "seniors", "biosimilar": False,
     "note": "Intravitreal — site fixed by route; retina-office only."},
]


def jcode_catalog() -> List[Dict[str, Any]]:
    """The full infusion J-code → drug → disease catalog (copies)."""
    return [dict(c) for c in _CATALOG]


def jcode_by_code(code: str) -> "Dict[str, Any] | None":
    """Look up a single catalog entry by HCPCS code (case-insensitive)."""
    c = (code or "").strip().upper()
    for row in _CATALOG:
        if row["hcpcs"].upper() == c:
            return dict(row)
    return None


def disease_index() -> Dict[str, List[str]]:
    """Inverted index: disease → the J-codes that treat it."""
    out: Dict[str, List[str]] = {}
    for row in _CATALOG:
        for dz in row["diseases"]:
            out.setdefault(dz, []).append(row["hcpcs"])
    return dict(sorted(out.items(), key=lambda kv: -len(kv[1])))


def drug_classes() -> List[str]:
    """Distinct therapeutic classes present in the catalog (sorted)."""
    return sorted({row["drug_class"] for row in _CATALOG})
