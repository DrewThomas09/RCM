"""
registry.py  (v42)
==================

The selectable-fix backbone. v40 and earlier ran one monolithic pipeline that
produced a 100+ sheet workbook every time. v42 turns each fix into a registered
FixModule the caller can select, so a run does exactly one thing (or a chosen
subset) instead of everything.

Three ideas, kept deliberately small and dependency-free:

1. FixModule: a declarative record of one data-quality fix. It names the fix,
   the canonical claim fields it REQUIRES, the reference data it needs, the Kahn
   data-quality category it belongs to, and a run() callable. It never imports
   its heavy dependencies at module load; run() imports them lazily so selecting
   one module does not drag in the others.

2. REGISTRY: the catalog of every fix v42 exposes, grouped so a menu / checkbox
   front-end can render categories.

3. fixability(std, mapping): given a standardized claims frame and the column
   mapping report, decide for every registered fix whether it is Supported,
   Partial, or Unsupported on THIS input, and say which columns each fix would
   touch. This is the "state upfront what it can and cannot fix" report, and it
   is what makes the tool project-agnostic: it reads the delivered columns and
   declares capability rather than assuming a schema.

Kahn categories (Kahn et al. 2016, operationalized by OHDSI DQD):
  conformance   value/format/relational integrity
  completeness  presence of required values
  plausibility  believability (range, temporal, cross-field)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional
import pandas as pd

CONFORMANCE = "conformance"
COMPLETENESS = "completeness"
PLAUSIBILITY = "plausibility"

# Selection groups a front-end can show as sections.
GROUP_CLAIMS = "claims_integrity"     # closed-claims netting, dup/reversal, plausibility
GROUP_CODING = "coding_edits"         # NCCI PTP/MUE, ICD-10 DOS validity, JW/JZ, age/sex
GROUP_PROVIDER = "provider_recovery"  # NPI validity, deactivation, recovery, enrichment
GROUP_NORMALIZE = "normalization"     # payer normalization, site-of-care
GROUP_DILIGENCE = "diligence_signal"  # taxonomy coherence, capture modeling, calibration


@dataclass(frozen=True)
class FixModule:
    """One selectable data-quality fix.

    key:        stable id used by the CLI / job spec (e.g. "mue_units").
    label:      human label for a menu.
    group:      one of the GROUP_* buckets.
    kahn:       Kahn DQ category the fix screens.
    requires:   canonical claim fields that MUST be present for the fix to run.
    optional:   fields that improve the fix but are not required.
    reference:  reference datasets the fix consumes ("" = none / self-contained).
    public:     whether every reference dataset is free/public.
    touches:    short description of what the fix writes or flags.
    run:        callable(std, ctx) -> pd.DataFrame (a result/audit frame).
    fixes:      whether the module can repair in place (True) or only flags (False).
    """
    key: str
    label: str
    group: str
    kahn: str
    requires: tuple
    reference: tuple
    touches: str
    run: Callable
    optional: tuple = ()
    verdict_needs: tuple = ()
    public: bool = True
    fixes: bool = False

    def support(self, present: set) -> str:
        """Supported / partial / unsupported against the fields that carry data.

        A fix with required fields is supported once all are present. Missing
        optional fields do not demote it, but missing verdict_needs fields do
        (to partial): those are the evidence without which the screen can only
        inventory rows, not render a pass/fail verdict (a JW/JZ screen with no
        modifier column cannot say a modifier is missing, only that it cannot
        check). Partial if some but not all required fields are present,
        unsupported if none are. A fix with NO required fields runs whenever an
        optional lift is present."""
        req = set(self.requires)
        if not req:
            if self.verdict_needs:
                return ("supported" if set(self.verdict_needs).issubset(present)
                        else "partial")
            if not self.optional or set(self.optional) & present:
                return "supported"
            return "partial"
        if req.issubset(present):
            if self.verdict_needs and not set(self.verdict_needs).issubset(present):
                return "partial"
            return "supported"
        if req & present:
            return "partial"
        return "unsupported"


# --------------------------------------------------------------------------- #
# Lazy run() wrappers. Each imports its module inside the function so that
# selecting one fix does not import the others (keeps single-fix runs light).
# --------------------------------------------------------------------------- #
def _run_mue(std, ctx):
    from . import coding_edits
    return coding_edits.mue_screen(std, ref_dir=ctx["ref_dir"])


def _run_ptp(std, ctx):
    from . import coding_edits
    return coding_edits.ptp_screen(std, ref_dir=ctx["ref_dir"])


def _run_icd_dos(std, ctx):
    from . import coding_edits
    return coding_edits.icd10_dos_validity(std, ref_dir=ctx["ref_dir"])


def _run_agesex(std, ctx):
    from . import coding_edits
    return coding_edits.age_sex_conflicts(std, ref_dir=ctx["ref_dir"])


def _run_jwjz(std, ctx):
    from . import coding_edits
    return coding_edits.jw_jz_wastage(std, ref_dir=ctx["ref_dir"])


def _run_deact(std, ctx):
    from . import coding_edits
    return coding_edits.deactivated_npi_screen(std, ref_dir=ctx["ref_dir"])


def _run_npi_valid(std, ctx):
    from . import field_validators as fv
    col = ctx["mapping"].get("billing_npi") or "billing_npi"
    if col not in std.columns:
        return pd.DataFrame({"note": ["no billing NPI column present"]})
    v = fv.validate_npi_series(std[col])
    out = pd.DataFrame({"row": std.index, "billing_npi": std[col].astype(str),
                        "blank": v["blank"].to_numpy(),
                        "bad_length": v["bad_length"].to_numpy(),
                        "luhn_fail": v["luhn_fail"].to_numpy(),
                        "valid": v["valid"].to_numpy()})
    flagged = out[~out["valid"]].copy()
    flagged.attrs["note"] = (
        f"{len(flagged)} of {len(out)} billing NPIs are blank, wrong length, or fail "
        f"the Luhn check.")
    return flagged.reset_index(drop=True)


def _run_plausibility(std, ctx):
    from . import row_consistency
    return row_consistency.run_row_consistency(std)


def _run_netting(std, ctx):
    from . import dedup
    netted, audit = dedup.apply_netting(std)
    audit.attrs["netted_rowcount"] = len(netted)
    return audit


def _run_payer(std, ctx):
    from . import payer_normalizer
    pcol = ctx["mapping"].get("payer") if ctx.get("mapping") else None
    pcol = pcol if (pcol and pcol in std.columns) else ("payer" if "payer" in std.columns else None)
    if pcol is None:
        return pd.DataFrame({"note": ["no payer column present"]})
    acol = (ctx["mapping"].get("allowed_amt") if ctx.get("mapping") else None) or "allowed_amt"
    allowed = pd.to_numeric(std[acol], errors="coerce") if acol in std.columns else pd.Series(
        [1.0] * len(std), index=std.index)
    return payer_normalizer.payer_mix_normalized(std, allowed=allowed, payer_col=pcol,
                                                 ref_dir=ctx["ref_dir"])


def _run_closed(std, ctx):
    from . import closed_claims
    return closed_claims.closed_claims_view(std, ctx)


def _run_capture(std, ctx):
    from . import capture_model
    rep = capture_model.capture_report(std, ref_dir=ctx["ref_dir"], mapping=ctx.get("mapping"))
    # surface the channel table as the primary frame; attach the rest
    ch = rep["channel_completeness"]
    ch.attrs["drug_capture_flags"] = rep["drug_capture_flags"]
    band = rep["implied_capture_band"]
    ch.attrs["implied_capture_band"] = band
    ch.attrs["note"] = band.get("note", ch.attrs.get("note", ""))
    return ch


def _run_taxonomy(std, ctx):
    from . import taxonomy_coherence as TC
    pred = ctx.get("recovery_pred")
    if pred is None or "recovered_npi" not in getattr(pred, "columns", []):
        return pd.DataFrame({"note": [
            "taxonomy coherence needs recovered NPIs; run the recovery pipeline first "
            "or pass a prediction frame. Nothing to screen in fix-only mode."]})
    return TC.coherence_screen(pred, std, ref_dir=ctx["ref_dir"],
                               mapping=ctx.get("mapping"),
                               directory=ctx.get("directory"))


def _run_calibration(std, ctx):
    from . import recovery_model as RM
    hold = ctx.get("holdout")
    if hold is None or "t1" not in getattr(hold, "columns", []):
        return pd.DataFrame({"note": [
            "calibration needs the back-test holdout (per-row stated confidence and "
            "the 0/1 outcome). Run the full pipeline with the back-test enabled; "
            "not available in fix-only mode."]})
    res = RM.fit_and_compare(hold, std=std, ref_dir=ctx["ref_dir"],
                             mapping=ctx.get("mapping"))
    if res.get("status") != "ok":
        return pd.DataFrame({"note": [f"calibration: {res.get('status')}"]})
    inc, mod = res["incumbent"], res["model"]
    out = pd.DataFrame([
        {"method": "incumbent_confidence", "brier": inc["brier"], "ece": inc["ece"],
         "auc": inc["auc"], "n": inc["n"]},
        {"method": "calibrated_model", "brier": mod["brier"], "ece": mod["ece"],
         "auc": mod["auc"], "n": mod["n"]},
    ])
    out.attrs["note"] = res["verdict"]
    out.attrs["reliability_incumbent"] = inc["reliability"]
    out.attrs["reliability_model"] = mod["reliability"]
    out.attrs["coefficients"] = res["coefficients"]
    return out


# --------------------------------------------------------------------------- #
# THE REGISTRY
# --------------------------------------------------------------------------- #
def _run_money_order(std, ctx):
    from . import consistency
    return consistency.money_ordering(std, ctx.get("mapping"))


def _run_date_order(std, ctx):
    from . import consistency
    return consistency.date_ordering(std, ctx.get("mapping"))


def _run_role_coherence(std, ctx):
    from . import consistency
    return consistency.npi_role_coherence(std, ctx.get("mapping"))


def _run_units_days(std, ctx):
    from . import consistency
    return consistency.units_days_supply(std, ctx.get("mapping"))


REGISTRY: tuple = (
    # ---- provider recovery ----
    FixModule("npi_validity", "NPI validity (Luhn + format)", GROUP_PROVIDER,
              CONFORMANCE, ("billing_npi",), (), "flags NPIs failing the 10-digit Luhn check",
              _run_npi_valid, fixes=False),
    FixModule("npi_deactivated", "Deactivated-NPI screen", GROUP_PROVIDER,
              CONFORMANCE, ("billing_npi",), ("nppes_deactivated_seed.csv",),
              "flags billing NPIs deactivated on/before the service date",
              _run_deact, optional=("date",), fixes=False),

    # ---- coding edits ----
    FixModule("mue_units", "MUE unit-cap screen (NCCI)", GROUP_CODING,
              PLAUSIBILITY, ("hcpcs", "units"), ("ncci_mue_seed.csv",),
              "flags units above the Medicare MUE cap, respecting the MAI",
              _run_mue, optional=("date",), fixes=False),
    FixModule("ptp_pairs", "PTP code-pair screen (NCCI)", GROUP_CODING,
              CONFORMANCE, ("hcpcs",), ("ncci_ptp_sample.csv",),
              "flags same-day column1/column2 code pairs not allowed together",
              _run_ptp, optional=("date", "billing_npi"), fixes=False),
    FixModule("icd_dos_validity", "ICD-10 date-of-service validity", GROUP_CODING,
              CONFORMANCE, ("diagnosis",), ("icd10cm_validity_seed.csv",),
              "flags diagnosis codes not valid in the fiscal year of service",
              _run_icd_dos, optional=("date",), fixes=False),
    FixModule("age_sex_conflict", "Age / sex code conflicts (MCE/IOCE)", GROUP_CODING,
              PLAUSIBILITY, ("diagnosis",), ("icd10cm_validity_seed.csv",),
              "flags maternity/newborn diagnoses against patient age or sex",
              _run_agesex, optional=("patient_age", "patient_sex"), fixes=False),
    FixModule("jw_jz_wastage", "JW/JZ single-dose wastage logic", GROUP_CODING,
              CONFORMANCE, ("hcpcs",), ("jw_jz_single_dose_seed.csv",),
              "flags single-dose drug lines missing the required JW or JZ modifier",
              _run_jwjz, optional=("units",), verdict_needs=("modifiers",), fixes=False),

    # ---- claims integrity ----
    FixModule("plausibility", "Impossible-value plausibility screen", GROUP_CLAIMS,
              PLAUSIBILITY, ("allowed_amt",), (),
              "flags negative dollars, future dates, zero-unit/positive-dollar rows",
              _run_plausibility, optional=("units", "date"), fixes=False),
    FixModule("netting", "Reversal / duplicate netting", GROUP_CLAIMS,
              PLAUSIBILITY, ("allowed_amt",), (),
              "nets matched reversal pairs and exact duplicates to final action",
              _run_netting, optional=("units", "hcpcs", "billing_npi"), fixes=True),
    FixModule("closed_claims", "Closed-claims-only view", GROUP_CLAIMS,
              COMPLETENESS, (), (),
              "restricts to adjudicated closed claims when a status field is present",
              _run_closed, optional=("date",), verdict_needs=("claim_status",), fixes=True),
    # v45 cross-field consistency screens
    FixModule("money_ordering", "Money ordering (paid<=allowed<=billed)", GROUP_CLAIMS,
              PLAUSIBILITY, ("allowed_amt",), (),
              "flags impossible orderings of paid, allowed, and billed amounts",
              _run_money_order, optional=("billed_amt", "paid_amt"),
              verdict_needs=("billed_amt",), fixes=False),
    FixModule("date_ordering", "Date ordering (service<=paid, not future)", GROUP_CLAIMS,
              PLAUSIBILITY, ("date",), (),
              "flags future service dates and paid-before-service orderings",
              _run_date_order, optional=("paid_date",), fixes=False),
    FixModule("npi_role_coherence", "Provider-role coherence", GROUP_CLAIMS,
              PLAUSIBILITY, ("billing_npi",), (),
              "flags impossible provider roles (referring equals billing)",
              _run_role_coherence, optional=("referring_npi", "rendering_npi"),
              verdict_needs=("referring_npi",), fixes=False),
    FixModule("units_days_supply", "Units vs days-supply consistency", GROUP_CLAIMS,
              PLAUSIBILITY, ("units",), (),
              "flags pharmacy quantity and days-supply off by more than 100x",
              _run_units_days, optional=("days_supply",),
              verdict_needs=("days_supply",), fixes=False),

    # ---- normalization ----
    FixModule("payer_normalize", "Payer name + channel normalization", GROUP_NORMALIZE,
              CONFORMANCE, ("payer",), ("payer_aliases_seed.csv",),
              "maps payer strings to a canonical payer and commercial/gov channel",
              _run_payer, public=True, fixes=True),

    # ---- diligence signal (v43) ----
    FixModule("capture_completeness", "Capture / completeness by channel and drug",
              GROUP_DILIGENCE, COMPLETENESS, ("payer",), ("jw_jz_single_dose_seed.csv",),
              "estimates what share of the true book the panel sees; flags blind spots",
              _run_capture, optional=("hcpcs", "allowed_amt"), fixes=False),
    FixModule("taxonomy_coherence", "Taxonomy coherence of recovered NPIs",
              GROUP_DILIGENCE, PLAUSIBILITY, ("hcpcs",), ("infusion_taxonomies.csv",),
              "flags recovered NPIs whose specialty cannot plausibly bill the drug",
              _run_taxonomy, fixes=False),
    FixModule("recovery_calibration", "Recovery confidence calibration + model",
              GROUP_DILIGENCE, PLAUSIBILITY, (), (),
              "measures whether stated recovery confidence is calibrated; fits a "
              "calibrated model and reports the head-to-head",
              _run_calibration, fixes=False),
)

REGISTRY_BY_KEY = {m.key: m for m in REGISTRY}
GROUP_ORDER = (GROUP_PROVIDER, GROUP_CODING, GROUP_CLAIMS, GROUP_NORMALIZE, GROUP_DILIGENCE)
GROUP_LABELS = {
    GROUP_PROVIDER: "Provider recovery",
    GROUP_CODING: "Coding edits",
    GROUP_CLAIMS: "Claims integrity",
    GROUP_NORMALIZE: "Normalization",
    GROUP_DILIGENCE: "Diligence signal",
}


def list_modules() -> pd.DataFrame:
    """The full catalog as a frame, for a menu or the docs."""
    rows = []
    for m in REGISTRY:
        rows.append({
            "key": m.key, "label": m.label, "group": GROUP_LABELS[m.group],
            "kahn_category": m.kahn, "requires": ", ".join(m.requires) or "(none)",
            "optional": ", ".join(m.optional) or "",
            "reference": ", ".join(m.reference) or "(self-contained)",
            "public_reference": m.public, "repairs_in_place": m.fixes,
            "touches": m.touches,
        })
    return pd.DataFrame(rows)


def _judgeable(std: pd.DataFrame) -> set:
    """Fields that actually carry data. schema.standardize() manufactures every
    canonical column (all-NA when the source never delivered it), so column
    existence proves nothing. A field is judgeable only if at least one non-null
    value is present. This is the difference between 'the pipeline created a
    diagnosis column' and 'the seller delivered diagnoses'."""
    return {c for c in std.columns if std[c].notna().any()}


def field_coverage(std: pd.DataFrame, mapping: Optional[dict] = None) -> pd.DataFrame:
    """Per-field delivery report: which canonical fields carry real data, how many
    rows, and what share. This is what 'the seller delivered X' actually means."""
    mapped = {k: v for k, v in (mapping or {}).items() if v}
    rows = []
    n = len(std)
    for c in std.columns:
        if c == "orig_row":
            continue
        nn = int(std[c].notna().sum())
        rows.append({"field": c,
                     "delivered": nn > 0,
                     "non_null_rows": nn,
                     "coverage_pct": round(100.0 * nn / n, 1) if n else 0.0,
                     "source_column": mapped.get(c, "")})
    out = pd.DataFrame(rows).sort_values(["delivered", "field"],
                                         ascending=[False, True]).reset_index(drop=True)
    out.attrs["note"] = (f"{int(out['delivered'].sum())} of {len(out)} canonical "
                         f"fields carry data in this file.")
    return out


def fixability(std: pd.DataFrame, mapping: Optional[dict] = None) -> pd.DataFrame:
    """State upfront which fixes are Supported / Partial / Unsupported on THIS
    input, and what each would touch. Capability is decided from fields that
    actually carry data (see _judgeable), never from manufactured all-NA
    canonical columns. Column-name-agnostic by design: Komodo ships no public
    dictionary, so capability is decided from the delivered data, not an assumed
    schema."""
    present = _judgeable(std)
    rows = []
    for m in REGISTRY:
        status = m.support(present)
        missing_req = sorted(set(m.requires) - present)
        missing_opt = sorted(set(m.optional) - present)
        missing_verdict = sorted(set(m.verdict_needs) - present)
        rows.append({
            "key": m.key, "fix": m.label, "group": GROUP_LABELS[m.group],
            "kahn_category": m.kahn, "status": status,
            "missing_required": ", ".join(missing_req),
            "missing_optional": ", ".join(missing_opt),
            "missing_for_verdict": ", ".join(missing_verdict),
            "reference_needed": ", ".join(m.reference) or "(none)",
            "would_touch": m.touches,
        })
    out = pd.DataFrame(rows)
    n_ok = int((out["status"] == "supported").sum())
    out.attrs["note"] = (
        f"{n_ok} of {len(out)} fixes supported on this input; "
        f"{int((out['status']=='partial').sum())} partial, "
        f"{int((out['status']=='unsupported').sum())} unsupported.")
    return out


def run_selected(std: pd.DataFrame, keys, ctx: dict) -> dict:
    """Run exactly the selected fixes and return {key: result_frame}. Unknown or
    unsupported keys are reported rather than silently skipped. ctx carries
    ref_dir and the column mapping. This is the one-thing-at-a-time executor."""
    present = _judgeable(std)
    out = {}
    for k in keys:
        m = REGISTRY_BY_KEY.get(k)
        if m is None:
            out[k] = pd.DataFrame({"note": [f"unknown fix key: {k}"]})
            continue
        if m.support(present) == "unsupported":
            need = ", ".join(sorted(set(m.requires) - present))
            out[k] = pd.DataFrame({"note": [f"unsupported on this input; missing: {need}"]})
            continue
        try:
            out[k] = m.run(std, ctx)
        except Exception as e:                                  # pragma: no cover
            out[k] = pd.DataFrame({"note": [f"{m.key} error: {type(e).__name__}: {e}"]})
    return out
