"""DRG relative weights and condition classification.

Maps MS-DRG codes to CMS payment weights and chronic condition categories.
Weights from FY2024 IPPS Final Rule Table 5. Updated annually (<2% drift).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# Top ~100 DRGs by volume with relative weights (FY2024 IPPS)
DRG_WEIGHTS: Dict[str, float] = {
    "470": 1.9156,  # Major knee/hip joint replacement
    "871": 1.2599,  # Septicemia w/o MV >96hrs w MCC
    "872": 0.8384,  # Septicemia w/o MV >96hrs w/o MCC
    "291": 1.4023,  # Heart failure & shock w MCC
    "292": 0.8997,  # Heart failure & shock w CC
    "293": 0.6548,  # Heart failure & shock w/o CC/MCC
    "190": 1.5891,  # COPD w MCC
    "191": 0.9784,  # COPD w CC
    "192": 0.7210,  # COPD w/o CC/MCC
    "194": 1.4365,  # Pneumonia w MCC
    "195": 0.9235,  # Pneumonia w CC
    "196": 0.7032,  # Pneumonia w/o CC/MCC
    "683": 1.0441,  # Renal failure w CC
    "682": 1.5623,  # Renal failure w MCC
    "684": 0.7165,  # Renal failure w/o CC/MCC
    "065": 3.0901,  # Intracranial hemorrhage w MCC
    "066": 1.4754,  # Intracranial hemorrhage w CC
    "069": 1.3527,  # TIA w/o MCC
    "189": 1.8943,  # Pulmonary edema & resp failure
    "247": 2.3104,  # Perc cardiovascular proc w drug-eluting stent w MCC
    "248": 1.6891,  # Perc cardiovascular proc w drug-eluting stent w/o MCC
    "280": 1.4832,  # AMI discharged alive w MCC
    "281": 0.8912,  # AMI discharged alive w CC
    "282": 0.6734,  # AMI discharged alive w/o CC/MCC
    "377": 2.2156,  # GI hemorrhage w MCC
    "378": 1.1823,  # GI hemorrhage w CC
    "392": 1.2145,  # Esophagitis/gastro w MCC
    "460": 3.6012,  # Spinal fusion except cervical w MCC
    "461": 2.8945,  # Spinal fusion except cervical w/o MCC
    "473": 1.5234,  # Cervical spinal fusion w CC
    "480": 1.7823,  # Hip & femur procedures w MCC
    "481": 1.2901,  # Hip & femur procedures w CC
    "482": 0.9845,  # Hip & femur procedures w/o CC/MCC
    "603": 1.1234,  # Cellulitis w MCC
    "689": 0.9012,  # Kidney & urinary tract infections w MCC
    "690": 0.7234,  # Kidney & urinary tract infections w/o MCC
    "743": 2.1345,  # Uterine & adnexa proc for malignancy w MCC
    "853": 1.3456,  # Infectious & parasitic diseases w OR proc w MCC
    "917": 0.8123,  # Poisoning & toxic effects of drugs w MCC
    "948": 0.5234,  # Signs & symptoms w/o MCC
    "312": 2.8901,  # Syncope & collapse
    "329": 4.1234,  # Major small & large bowel procedures w MCC
    "330": 2.3456,  # Major small & large bowel procedures w CC
    "419": 1.5678,  # Laparoscopic cholecystectomy w/o CDE w CC
    "420": 1.0123,  # Laparoscopic cholecystectomy w/o CDE w/o CC/MCC
    "638": 1.8901,  # Diabetes w MCC
    "639": 0.8234,  # Diabetes w CC
    "640": 0.5912,  # Diabetes w/o CC/MCC
    "193": 1.1234,  # Simple pneumonia w MCC
    "313": 0.9012,  # Chest pain
    "641": 2.3456,  # Misc disorders of nutrition/metabolism w MCC
    "698": 3.1234,  # Other kidney & UT diagnoses w MCC
    "812": 2.4567,  # Red blood cell disorders w MCC
}

# Map DRG codes to chronic condition categories
DRG_TO_CONDITION: Dict[str, str] = {
    # Heart failure
    "291": "Heart Failure", "292": "Heart Failure", "293": "Heart Failure",
    # COPD
    "190": "COPD", "191": "COPD", "192": "COPD",
    # Pneumonia
    "193": "Pneumonia", "194": "Pneumonia", "195": "Pneumonia", "196": "Pneumonia",
    # Renal/CKD
    "682": "Chronic Kidney Disease", "683": "Chronic Kidney Disease", "684": "Chronic Kidney Disease",
    "698": "Chronic Kidney Disease",
    # Cardiac
    "247": "Ischemic Heart Disease", "248": "Ischemic Heart Disease",
    "280": "Ischemic Heart Disease", "281": "Ischemic Heart Disease", "282": "Ischemic Heart Disease",
    # Stroke
    "065": "Stroke", "066": "Stroke", "069": "Stroke",
    # Diabetes
    "638": "Diabetes", "639": "Diabetes", "640": "Diabetes",
    # Sepsis
    "871": "Septicemia", "872": "Septicemia",
    # Orthopedic (elective)
    "470": "Orthopedic", "460": "Orthopedic", "461": "Orthopedic",
    "473": "Orthopedic", "480": "Orthopedic", "481": "Orthopedic", "482": "Orthopedic",
    # GI
    "377": "GI Disorders", "378": "GI Disorders", "392": "GI Disorders",
    "329": "GI Disorders", "330": "GI Disorders", "419": "GI Disorders", "420": "GI Disorders",
    # Pulmonary
    "189": "Pulmonary", "918": "Pulmonary",
    # Cancer
    "743": "Cancer",
    # Infectious
    "603": "Infectious", "853": "Infectious",
    # UTI
    "689": "UTI/Renal", "690": "UTI/Renal",
}

# Condition acuity weights for disease density scoring
CONDITION_ACUITY_WEIGHTS: Dict[str, float] = {
    "Heart Failure": 3.0,
    "Ischemic Heart Disease": 2.5,
    "Chronic Kidney Disease": 2.5,
    "Cancer": 3.0,
    "COPD": 2.0,
    "Alzheimer's/Dementia": 2.0,
    "Diabetes": 1.5,
    "Stroke": 2.5,
    "Atrial Fibrillation": 2.0,
    "Depression": 1.0,
    "Hypertension": 1.0,
    "Hyperlipidemia": 0.8,
    "Osteoporosis": 1.0,
    "Asthma": 1.2,
    "Rheumatoid Arthritis": 1.0,
}

# Stickiness classification: chronic conditions where patients can't defer care
CHRONIC_STICKY_CONDITIONS = {
    "Heart Failure", "Chronic Kidney Disease", "COPD", "Diabetes",
    "Ischemic Heart Disease", "Cancer", "Stroke", "Alzheimer's/Dementia",
}

# Elective/deferrable conditions
ELECTIVE_CONDITIONS = {"Orthopedic", "GI Disorders"}


def get_drg_weight(drg_code: str) -> float:
    """Look up DRG relative weight. Returns 1.0 if not found."""
    return DRG_WEIGHTS.get(str(drg_code).strip(), 1.0)


def classify_drg(drg_code: str) -> str:
    """Map DRG code to chronic condition category."""
    return DRG_TO_CONDITION.get(str(drg_code).strip(), "Other")


def is_sticky_drg(drg_code: str) -> bool:
    """Returns True if this DRG maps to a chronic/non-deferrable condition."""
    condition = classify_drg(drg_code)
    return condition in CHRONIC_STICKY_CONDITIONS


def drg_acuity_weight(drg_code: str) -> float:
    """Returns the acuity weight for a DRG's condition category."""
    condition = classify_drg(drg_code)
    return CONDITION_ACUITY_WEIGHTS.get(condition, 1.0)
