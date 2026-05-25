"""ClinicalTrials.gov trial-landscape aggregate — loader.

Reads the committed aggregate under ``rcm_mc/data/vendor/clinical_trials/``
(built by ``scripts/ingest_clinical_trials.py``). Public ClinicalTrials.gov
data; no runtime network.

Honesty: national registry counts (total / recruiting / interventional / by
phase) — a real trial-volume / site-demand signal. NOT this deal's sites or
revenue, and registry counts are not a financial figure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_DIR = Path(__file__).resolve().parent / "vendor" / "clinical_trials"


def clinical_trials_summary() -> Dict[str, Any]:
    p = _DIR / "clinical_trials_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def phase_breakdown() -> List[Dict[str, Any]]:
    s = clinical_trials_summary()
    ph = s.get("phases", {})
    labels = {"phase_1": "Phase 1", "phase_2": "Phase 2",
              "phase_3": "Phase 3", "phase_4": "Phase 4"}
    return [{"phase": labels.get(k, k), "count": int(v)} for k, v in ph.items()]


def clinical_trials_sources() -> List[Dict[str, str]]:
    import pandas as pd
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "clinicaltrials_gov"].to_dict("records")
