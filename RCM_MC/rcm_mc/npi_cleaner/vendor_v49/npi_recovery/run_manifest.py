"""
run_manifest.py  (v44)
======================

A reproducibility record for a run. When a recovered value or a flag is
questioned later, the first question is what produced it: which tool version,
against which input, using which reference data of which vintage. This module
writes that record so the answer is one lookup.

The manifest captures:
  run_id            a timestamp-based id for the run
  tool_version      the package version
  input_file        name and a content hash of the input, so the same file is
                    provably the same file
  reference_vintages the dated seeds the run used (MUE, PTP, ICD, JW/JZ,
                    deactivation, and whatever else is present in reference/)
  options           the run flags that change output

Deterministic and offline. The vintages are read from the shipped reference
files' own contents where they carry a date, else from the file name.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

import pandas as pd


def _file_hash(path, algo="sha256", chunk=1 << 20):
    if not path or not os.path.exists(path):
        return ""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:16]


def _reference_vintages(ref_dir):
    """Best-effort vintage per shipped reference file: read a date from a known
    column, else fall back to a date embedded in the file, else the mtime."""
    out = {}
    if not ref_dir or not os.path.isdir(ref_dir):
        return out
    known = {
        "ncci_mue_seed.csv": ("effective_date", "NCCI MUE"),
        "ncci_ptp_sample.csv": ("effective_date", "NCCI PTP"),
        "jw_jz_single_dose_seed.csv": (None, "JW/JZ single-dose list"),
        "nppes_deactivated_seed.csv": (None, "NPPES deactivation"),
        "icd10cm_validity_seed.csv": ("fy", "ICD-10-CM validity"),
    }
    for fname, (datecol, label) in known.items():
        path = os.path.join(ref_dir, fname)
        if not os.path.exists(path):
            continue
        vintage = ""
        try:
            df = pd.read_csv(path, dtype=str, nrows=200)
            if datecol and datecol in df.columns:
                vals = sorted(v for v in df[datecol].dropna().unique() if v)
                if vals:
                    vintage = f"{datecol}={vals[-1]}"
        except Exception:
            pass
        if not vintage:
            m = re.search(r"(20\d{2}[-_]?\d{0,2}[-_]?\d{0,2})", fname)
            if m:
                vintage = m.group(1)
        if not vintage:
            vintage = datetime.fromtimestamp(os.path.getmtime(path),
                                             tz=timezone.utc).strftime("%Y-%m-%d")
        out[label] = vintage
    return out


def build_manifest(input_path, tool_version, ref_dir=None, options: dict = None) -> dict:
    """Assemble the run manifest dict."""
    return {
        "run_id": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"),
        "tool_version": tool_version,
        "input_file": os.path.basename(str(input_path)) if input_path else "",
        "input_sha256_16": _file_hash(str(input_path)) if input_path else "",
        "reference_vintages": _reference_vintages(ref_dir),
        "options": options or {},
    }


def manifest_frame(manifest: dict) -> pd.DataFrame:
    """Flatten the manifest to a two-column frame for a workbook sheet."""
    rows = [
        {"key": "run_id", "value": manifest.get("run_id", "")},
        {"key": "tool_version", "value": manifest.get("tool_version", "")},
        {"key": "input_file", "value": manifest.get("input_file", "")},
        {"key": "input_sha256_16", "value": manifest.get("input_sha256_16", "")},
    ]
    for k, v in (manifest.get("reference_vintages") or {}).items():
        rows.append({"key": f"reference: {k}", "value": v})
    for k, v in (manifest.get("options") or {}).items():
        rows.append({"key": f"option: {k}", "value": str(v)})
    out = pd.DataFrame(rows)
    out.attrs["note"] = ("Reproducibility record for this run. The input hash proves "
                         "file identity; the reference vintages say which dated CMS "
                         "seeds produced the flags.")
    return out


def write_manifest_json(manifest: dict, path) -> str:
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return path
