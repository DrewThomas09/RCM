"""Observed vs. assumed tagging for config parameters.

A diligence deliverable has to defend every number. This module classifies the
drivers of the model into three source categories:

- ``observed``   — sourced from target-hospital data (claims CSV, denials file, etc.)
- ``prior``      — industry benchmark from a cited source (HFMA, AHA, Kodiak, ...)
- ``assumed``    — analyst judgment with no external source

Configs carry an optional top-level ``_source_map`` dict. Keys are dotted paths
pointing at a "meaningful leaf" (a driver a partner might defend in IC). A
special ``_default`` entry sets the label for any unlisted path. The map also
supports ``{path}._note`` entries for free-text provenance (e.g., sample size).

Example ``_source_map``::

    _source_map:
      _default: assumed
      payers.Medicare.denials.idr: observed
      payers.Medicare.denials.idr._note: "denials_2024.csv, n=4,521"
      payers.Commercial.denials.fwr: prior

Meaningful leaves are defined explicitly (see ``iter_meaningful_paths``) rather
than auto-detected — that keeps the surface stable as the config schema evolves.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, Optional, Tuple

VALID_SOURCES = ("observed", "prior", "assumed")
_DEFAULT_KEY = "_default"


def _payer_is_active_for_denials(pconf: Dict[str, Any]) -> bool:
    return bool(pconf.get("include_denials", False)) and "denials" in pconf


def _payer_is_active_for_underpayments(pconf: Dict[str, Any]) -> bool:
    return bool(pconf.get("include_underpayments", False)) and "underpayments" in pconf


def iter_meaningful_paths(cfg: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    """Yield (dotted_path, raw_value) for every config parameter a partner would
    be asked to defend in an investment committee review.

    Intentionally a curated list rather than an exhaustive walk — the set of
    "numbers that matter" is stable even if the YAML schema grows new nooks.
    """
    hosp = cfg.get("hospital", {}) or {}
    if "annual_revenue" in hosp:
        yield "hospital.annual_revenue", hosp["annual_revenue"]
    if "ebitda_margin" in hosp:
        yield "hospital.ebitda_margin", hosp["ebitda_margin"]
    if "debt" in hosp:
        yield "hospital.debt", hosp["debt"]
    if "rcm_spend_annual" in hosp:
        yield "hospital.rcm_spend_annual", hosp["rcm_spend_annual"]

    econ = cfg.get("economics", {}) or {}
    if "wacc_annual" in econ:
        yield "economics.wacc_annual", econ["wacc_annual"]

    for payer_name, pconf in (cfg.get("payers") or {}).items():
        prefix = f"payers.{payer_name}"
        if "revenue_share" in pconf:
            yield f"{prefix}.revenue_share", pconf["revenue_share"]
        if "avg_claim_dollars" in pconf:
            yield f"{prefix}.avg_claim_dollars", pconf["avg_claim_dollars"]
        if isinstance(pconf.get("dar_clean_days"), dict) and "mean" in pconf["dar_clean_days"]:
            yield f"{prefix}.dar_clean_days", pconf["dar_clean_days"]["mean"]

        if _payer_is_active_for_denials(pconf):
            den = pconf["denials"]
            if isinstance(den.get("idr"), dict) and "mean" in den["idr"]:
                yield f"{prefix}.denials.idr", den["idr"]["mean"]
            if isinstance(den.get("fwr"), dict) and "mean" in den["fwr"]:
                yield f"{prefix}.denials.fwr", den["fwr"]["mean"]
            if isinstance(den.get("stage_mix"), dict):
                yield f"{prefix}.denials.stage_mix", den["stage_mix"]

        if _payer_is_active_for_underpayments(pconf):
            up = pconf["underpayments"]
            for k in ("upr", "severity", "recovery"):
                if isinstance(up.get(k), dict) and "mean" in up[k]:
                    yield f"{prefix}.underpayments.{k}", up[k]["mean"]


def _default_source(source_map: Optional[Dict[str, Any]]) -> str:
    if not source_map:
        return "assumed"
    default = source_map.get(_DEFAULT_KEY, "assumed")
    return default if default in VALID_SOURCES else "assumed"


def classify_sources(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Return ``{dotted_path: source_label}`` for every meaningful leaf.

    Any path missing from ``_source_map`` inherits ``_source_map._default``
    (falling back to ``"assumed"`` if no default is set). Invalid labels on
    explicit entries are demoted to the default rather than raising.
    """
    source_map = (cfg.get("_source_map") or {}) if isinstance(cfg.get("_source_map"), dict) else {}
    default = _default_source(source_map)
    out: Dict[str, str] = {}
    for path, _ in iter_meaningful_paths(cfg):
        explicit = source_map.get(path)
        if isinstance(explicit, str) and explicit in VALID_SOURCES:
            out[path] = explicit
        else:
            out[path] = default
    return out


def path_notes(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Return ``{dotted_path: note}`` for every path with a ``._note`` entry."""
    source_map = (cfg.get("_source_map") or {}) if isinstance(cfg.get("_source_map"), dict) else {}
    out: Dict[str, str] = {}
    for key, val in source_map.items():
        if isinstance(key, str) and key.endswith("._note") and isinstance(val, str):
            out[key[: -len("._note")]] = val
    return out


def summarize(classification: Dict[str, str]) -> Dict[str, int]:
    """Aggregate counts for a classification map."""
    counts = {"observed": 0, "prior": 0, "assumed": 0}
    for label in classification.values():
        if label in counts:
            counts[label] += 1
    counts["total"] = len(classification)
    return counts


def observed_fraction(classification: Dict[str, str]) -> float:
    """Share of meaningful inputs sourced from target data (0.0 to 1.0)."""
    total = len(classification)
    if total == 0:
        return 0.0
    observed = sum(1 for v in classification.values() if v == "observed")
    return observed / total


def confidence_grade(classification: Dict[str, str]) -> str:
    """Coarse A/B/C/D letter grade from observed share.

    Thresholds chosen to match the existing per-payer data_confidence grade
    (data_confidence.csv uses the same semantics for CSV-backed evidence).
    """
    frac = observed_fraction(classification)
    if frac >= 0.50:
        return "A"
    if frac >= 0.25:
        return "B"
    if frac >= 0.10:
        return "C"
    return "D"


def mark_observed(
    cfg: Dict[str, Any],
    path: str,
    note: Optional[str] = None,
) -> None:
    """Mark a dotted path as ``observed`` in the config's ``_source_map``.

    Used by calibration to auto-tag fields it overwrites from CSV data. Creates
    the ``_source_map`` container if it doesn't exist.
    """
    if not path:
        return
    sm = cfg.setdefault("_source_map", {})
    if not isinstance(sm, dict):
        # Malformed; replace rather than raise (analyst-facing robustness).
        cfg["_source_map"] = {}
        sm = cfg["_source_map"]
    sm[path] = "observed"
    if note:
        sm[f"{path}._note"] = str(note)
