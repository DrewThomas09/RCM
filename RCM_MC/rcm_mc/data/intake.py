"""Interactive intake wizard: 11 prompts → validated ``actual.yaml``.

Collapses the 131-field config surface down to the decisions a diligence analyst
can realistically answer in 5 minutes, starting from a template and overwriting
only the inputs the user provides. Everything else inherits template defaults.

Public surface:

- :func:`run_intake` — orchestrator (callable from tests with an injected I/O).
- :func:`scale_blended_to_per_payer` — scale template per-payer values so the
  revenue-weighted mean matches the user's blended target.
- :func:`main` — argparse CLI entry point (registered as ``rcm-intake``).

The wizard never crashes on bad input: it re-prompts until valid or bails with a
clear message. On a non-TTY stdin it exits with guidance toward ``--template``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from ..infra.config import validate_config
from .sources import mark_observed


# Project-root-relative paths to the two templates we ship plus the shipped actual.
# Post-refactor: intake.py is in rcm_mc/data/, so parent.parent.parent
# is the project root where configs/ lives.
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES: Dict[str, Path] = {
    "community_hospital_500m": _PACKAGE_ROOT / "configs" / "templates" / "community_hospital_500m.yaml",
    "rural_critical_access": _PACKAGE_ROOT / "configs" / "templates" / "rural_critical_access.yaml",
    "actual": _PACKAGE_ROOT / "configs" / "actual.yaml",
}


# ── Pure logic ────────────────────────────────────────────────────────────────

def load_template(name: str) -> Dict[str, Any]:
    """Load a named template YAML as a fresh dict."""
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template '{name}'; choose from {sorted(TEMPLATES)}")
    path = TEMPLATES[name]
    if not path.is_file():
        raise FileNotFoundError(f"Template file missing: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _blended_mean(cfg: Dict[str, Any], metric_path: Tuple[str, ...]) -> Optional[float]:
    """Revenue-weighted blended mean of a per-payer metric.

    ``metric_path`` is a tuple of keys from the payer dict (e.g., ``("denials", "idr")``
    or ``("dar_clean_days",)``). Returns None if no payer has the metric.
    """
    payers = cfg.get("payers") or {}
    total_w = 0.0
    total_v = 0.0
    for pconf in payers.values():
        share = float(pconf.get("revenue_share") or 0.0)
        if share <= 0:
            continue
        node: Any = pconf
        for key in metric_path:
            if not isinstance(node, dict) or key not in node:
                node = None
                break
            node = node[key]
        if not isinstance(node, dict) or "mean" not in node:
            continue
        total_w += share
        total_v += share * float(node["mean"])
    if total_w <= 0:
        return None
    return total_v / total_w


def scale_blended_to_per_payer(
    cfg: Dict[str, Any],
    metric_path: Tuple[str, ...],
    target_blended: float,
    min_clamp: float = 0.0,
    max_clamp: float = 1.0,
) -> List[str]:
    """Scale each payer's ``metric_path.mean`` so the revenue-weighted mean lands on
    ``target_blended``. Preserves relative differences between payers.

    Returns the list of dotted paths actually touched (for source tagging).
    """
    current_blended = _blended_mean(cfg, metric_path)
    if current_blended is None or current_blended <= 0:
        return []
    factor = float(target_blended) / current_blended
    touched: List[str] = []
    payers = cfg.get("payers") or {}
    for payer_name, pconf in payers.items():
        node: Any = pconf
        for key in metric_path[:-1]:
            if not isinstance(node, dict) or key not in node:
                node = None
                break
            node = node[key]
        leaf_key = metric_path[-1]
        if not isinstance(node, dict) or leaf_key not in node:
            continue
        leaf = node[leaf_key]
        if not isinstance(leaf, dict) or "mean" not in leaf:
            continue
        new_mean = float(leaf["mean"]) * factor
        new_mean = max(min_clamp, min(max_clamp, new_mean))
        leaf["mean"] = new_mean
        touched.append(f"payers.{payer_name}." + ".".join(metric_path))
    return touched


def apply_intake_answers(cfg: Dict[str, Any], answers: Dict[str, Any]) -> List[str]:
    """Overwrite template fields with user answers and tag each as observed.

    Returns the list of dotted paths that were touched. ``answers`` keys:

    ``hospital_name``, ``hospital_ccn``, ``annual_revenue``, ``mix_medicare``,
    ``mix_medicaid``, ``mix_commercial``, ``idr_blended``, ``fwr_blended``,
    ``dar_blended``, ``ebitda_margin``, ``wacc``. Missing keys leave template
    defaults in place.

    ``hospital_ccn`` is pure metadata (no source-map tag, no monte-carlo
    effect) but it flows through to downstream tooling so the CLI can
    auto-generate peer sets when a CCN is present.
    """
    touched: List[str] = []

    hospital = cfg.setdefault("hospital", {})
    if "hospital_name" in answers:
        hospital["name"] = str(answers["hospital_name"])
    if "hospital_ccn" in answers and answers["hospital_ccn"]:
        hospital["ccn"] = str(answers["hospital_ccn"])
    if "annual_revenue" in answers:
        hospital["annual_revenue"] = float(answers["annual_revenue"])
        touched.append("hospital.annual_revenue")
    if "ebitda_margin" in answers:
        hospital["ebitda_margin"] = float(answers["ebitda_margin"])
        touched.append("hospital.ebitda_margin")

    econ = cfg.setdefault("economics", {})
    if "wacc" in answers:
        econ["wacc_annual"] = float(answers["wacc"])
        touched.append("economics.wacc_annual")

    # Revenue shares: Medicare / Medicaid / Commercial user-supplied; SelfPay = residual.
    if {"mix_medicare", "mix_medicaid", "mix_commercial"} <= set(answers):
        mm = float(answers["mix_medicare"])
        mmd = float(answers["mix_medicaid"])
        mc = float(answers["mix_commercial"])
        msp = max(0.0, 1.0 - mm - mmd - mc)
        new_mix = {"Medicare": mm, "Medicaid": mmd, "Commercial": mc, "SelfPay": msp}
        payers = cfg.setdefault("payers", {})
        for payer_name, share in new_mix.items():
            if payer_name in payers:
                payers[payer_name]["revenue_share"] = float(share)
                touched.append(f"payers.{payer_name}.revenue_share")

    # Blended IDR / FWR / DAR applied via proportional scaling so relative payer
    # differences in the template survive.
    if "idr_blended" in answers:
        touched += scale_blended_to_per_payer(
            cfg, ("denials", "idr"), float(answers["idr_blended"]),
            min_clamp=0.001, max_clamp=0.80,
        )
    if "fwr_blended" in answers:
        touched += scale_blended_to_per_payer(
            cfg, ("denials", "fwr"), float(answers["fwr_blended"]),
            min_clamp=0.001, max_clamp=0.95,
        )
    if "dar_blended" in answers:
        touched += scale_blended_to_per_payer(
            cfg, ("dar_clean_days",), float(answers["dar_blended"]),
            min_clamp=5.0, max_clamp=200.0,
        )

    # Tag each touched path as observed in the source map. The user provided the
    # number, so by definition it's target data / management input (vs a prior).
    for path in touched:
        mark_observed(cfg, path, note="provided via intake wizard")

    # Make sure _source_map has a sensible default for everything else.
    sm = cfg.setdefault("_source_map", {})
    if "_default" not in sm:
        sm["_default"] = "assumed"

    return touched


def run_intake(
    answers: Dict[str, Any],
    template_name: str = "community_hospital_500m",
    out_path: str = "actual.yaml",
    extra_observations: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Pure-logic path: template + answers → validated cfg → YAML on disk.

    ``extra_observations`` is an optional ``{dotted_path: source_note}`` map
    applied AFTER ``apply_intake_answers`` — used by the ``--from-ccn`` flow to
    stamp a specific "CMS HCRIS FY{Y}, CCN {X}" provenance note on HCRIS-
    sourced fields (overriding the default "provided via intake wizard" note).

    Callable from tests with a pre-built answers dict (no prompts).
    Raises ValueError if the resulting config doesn't validate.
    """
    cfg = load_template(template_name)
    apply_intake_answers(cfg, answers)
    if extra_observations:
        for path, note in extra_observations.items():
            mark_observed(cfg, path, note=note)
    validate_config(cfg)  # raises on malformed output
    out_abs = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
    with open(out_abs, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg


# ── Interactive shell ─────────────────────────────────────────────────────────

def _ask(
    prompt: str,
    default: Any,
    parser: Callable[[str], Any] = str,
    validator: Optional[Callable[[Any], Optional[str]]] = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> Any:
    """Prompt-and-validate loop. Re-prompts on parse/validation errors.

    ``validator`` returns an error message string (to reshow) or None on OK.
    """
    shown_default = "" if default is None else str(default)
    suffix = f" [{shown_default}]" if shown_default else ""
    while True:
        raw = input_fn(f"{prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            return default
        try:
            value = parser(raw)
        except (ValueError, TypeError) as exc:
            output_fn(f"  ! Can't read that ({exc}). Try again.")
            continue
        if validator is not None:
            err = validator(value)
            if err:
                output_fn(f"  ! {err}")
                continue
        return value


def _parse_percent(raw: str) -> float:
    """Accept '13', '13%', '0.13' — all mean 13%."""
    s = raw.strip().rstrip("%")
    v = float(s)
    if v > 1.0:
        v = v / 100.0
    return v


def _choose_template(
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> str:
    names = sorted(TEMPLATES)
    output_fn("")
    output_fn("Pick a starting template:")
    for i, n in enumerate(names, 1):
        output_fn(f"  {i}. {n}")
    def _parse(s: str) -> str:
        s = s.strip().lower()
        if s.isdigit():
            i = int(s)
            if 1 <= i <= len(names):
                return names[i - 1]
        if s in names:
            return s
        raise ValueError("not one of the options")
    return _ask(
        "Template choice",
        default="community_hospital_500m",
        parser=_parse,
        input_fn=input_fn,
        output_fn=output_fn,
    )


def _validator_range(lo: float, hi: float, label: str = "value") -> Callable[[Any], Optional[str]]:
    def _v(x: Any) -> Optional[str]:
        if x is None or x < lo or x > hi:
            return f"{label} must be between {lo} and {hi}"
        return None
    return _v


def _hcris_prefill_bundle(
    ccn: str,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> Optional[Dict[str, Any]]:
    """Look up CCN in CMS HCRIS, show confirmation prompt, return prefill bundle.

    Returns None if the CCN isn't found, or if the analyst declines the match.
    The returned dict has shape::

        {
            "answers": {"hospital_name": str, "annual_revenue": float,
                        "mix_medicare": float, "mix_medicaid": float},
            "note":         "CMS HCRIS FY2022, CCN 360180 (patient-day %)",
            "hcris_paths":  ["hospital.annual_revenue",
                             "payers.Medicare.revenue_share",
                             "payers.Medicaid.revenue_share"],
        }

    ``hcris_paths`` lists the :mod:`sources` dotted paths that the caller
    should overwrite with the HCRIS note after :func:`apply_intake_answers`
    has stamped its default wizard note on them.
    """
    # Imported lazily so a missing HCRIS data file doesn't break plain intake.
    from .hcris import lookup_by_ccn

    row = lookup_by_ccn(ccn)
    if row is None:
        output_fn(f"\n  ! CCN '{ccn}' not found in CMS HCRIS. Proceeding with full wizard.\n")
        return None

    fy = row.get("fiscal_year")
    ccn_clean = row.get("ccn") or ccn
    output_fn("")
    output_fn(f"Found in CMS HCRIS FY{int(fy)}:" if fy else "Found in CMS HCRIS:")
    output_fn(f"  CCN:           {ccn_clean}")
    output_fn(f"  Name:          {row.get('name', '?')}")
    loc = f"{row.get('city', '?')}, {row.get('state', '?')}"
    output_fn(f"  Location:      {loc}")
    if row.get("beds") is not None:
        output_fn(f"  Beds:          {int(row['beds']):,}")
    npsr = row.get("net_patient_revenue")
    if npsr is not None and npsr > 0:
        output_fn(f"  Net Pat Rev:   ${npsr/1e9:.2f}B")
    med_pct = row.get("medicare_day_pct")
    if med_pct is not None:
        output_fn(f"  Medicare day%: {med_pct*100:.1f}%")
    mcd_pct = row.get("medicaid_day_pct")
    if mcd_pct is not None:
        output_fn(f"  Medicaid day%: {mcd_pct*100:.1f}%")
    output_fn("")
    output_fn("Payer day-shares are a proxy for revenue mix. Accurate enough")
    output_fn("to seed, but override in the YAML if contract mix differs materially.")
    output_fn("")

    # Confirmation: Enter / "y" accepts; "n" declines.
    def _parse_yn(s: str) -> bool:
        t = s.strip().lower()
        if t in ("", "y", "yes"):
            return True
        if t in ("n", "no"):
            return False
        raise ValueError("answer y or n")

    use_it = _ask(
        "Use this as starting point? [Y/n]",
        default=None,   # None → no "[default]" suffix; _parse_yn handles empty as yes
        parser=_parse_yn,
        input_fn=input_fn, output_fn=output_fn,
    )
    if not use_it:
        output_fn("  (Declined — proceeding with full wizard.)\n")
        return None

    answers: Dict[str, Any] = {}
    hcris_paths: List[str] = []
    if ccn_clean:
        # Stamp the CCN onto the YAML so downstream peer-compare finds it.
        answers["hospital_ccn"] = str(ccn_clean)
    if row.get("name"):
        answers["hospital_name"] = str(row["name"])
        # hospital.name isn't in the source_map's meaningful-leaves set — no tag needed
    if npsr is not None and npsr > 0:
        answers["annual_revenue"] = float(npsr)
        hcris_paths.append("hospital.annual_revenue")
    if med_pct is not None and 0 <= med_pct < 1:
        answers["mix_medicare"] = float(med_pct)
        hcris_paths.append("payers.Medicare.revenue_share")
    if mcd_pct is not None and 0 <= mcd_pct < 1:
        answers["mix_medicaid"] = float(mcd_pct)
        hcris_paths.append("payers.Medicaid.revenue_share")

    note = f"CMS HCRIS FY{int(fy)}, CCN {ccn_clean} (patient-day %)" if fy else f"CMS HCRIS, CCN {ccn_clean}"
    return {"answers": answers, "note": note, "hcris_paths": hcris_paths}


def interactive_intake(
    out_path: str,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    ccn_prefill: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the interactive prompts and write ``out_path``. Returns the cfg.

    If ``ccn_prefill`` is provided, the wizard first looks the CCN up in CMS
    HCRIS, shows a confirmation, and (on accept) pre-fills hospital name,
    annual NPSR, and Medicare / Medicaid day-share. Skipped prompts are
    tagged ``observed`` with an "HCRIS" source note; remaining prompts are
    tagged with the default wizard note.
    """
    output_fn("")
    output_fn("RCM Monte Carlo — Intake Wizard")
    output_fn("─" * 60)

    # Optional CMS HCRIS pre-fill — runs BEFORE the template picker because
    # the HCRIS bundle only affects hospital-level answers, not the template.
    hcris_bundle: Optional[Dict[str, Any]] = None
    if ccn_prefill:
        hcris_bundle = _hcris_prefill_bundle(ccn_prefill, input_fn, output_fn)

    prefill_answers: Dict[str, Any] = dict(hcris_bundle["answers"]) if hcris_bundle else {}

    output_fn(
        "I'll ask the remaining questions. Press Enter to accept defaults, "
        "or Ctrl+C to quit without writing anything."
    )

    template_name = _choose_template(input_fn, output_fn)
    template = load_template(template_name)
    t_hosp = template.get("hospital", {}) or {}
    t_payers = template.get("payers", {}) or {}
    t_econ = template.get("economics", {}) or {}

    def _default_mix(name: str) -> float:
        return float((t_payers.get(name) or {}).get("revenue_share") or 0.0)

    output_fn("")
    answers: Dict[str, Any] = {}

    if "hospital_name" in prefill_answers:
        answers["hospital_name"] = prefill_answers["hospital_name"]
        output_fn(f"Hospital name: {answers['hospital_name']}  (from HCRIS)")
    else:
        answers["hospital_name"] = _ask(
            "Hospital / target name",
            default=t_hosp.get("name", "Target Hospital"),
            input_fn=input_fn, output_fn=output_fn,
        )

    if "annual_revenue" in prefill_answers:
        answers["annual_revenue"] = prefill_answers["annual_revenue"]
        output_fn(f"Annual NPSR: ${answers['annual_revenue']/1e9:.2f}B  (from HCRIS)")
    else:
        answers["annual_revenue"] = _ask(
            "Annual NPSR ($, e.g. 500000000)",
            default=float(t_hosp.get("annual_revenue") or 500_000_000),
            parser=lambda s: float(s.replace(",", "").replace("$", "")),
            validator=_validator_range(1e6, 1e11, "NPSR"),
            input_fn=input_fn, output_fn=output_fn,
        )

    output_fn("")
    output_fn("Payer mix (enter percentages; SelfPay auto-calculated as residual):")
    def _mix_validator(x: float) -> Optional[str]:
        if x < 0 or x > 1:
            return "share must be between 0 and 100%"
        return None

    if "mix_medicare" in prefill_answers:
        mm = float(prefill_answers["mix_medicare"])
        output_fn(f"  Medicare %: {mm*100:.1f}%  (from HCRIS day-share)")
    else:
        mm = _ask("Medicare %", default=_default_mix("Medicare"),
                  parser=_parse_percent, validator=_mix_validator,
                  input_fn=input_fn, output_fn=output_fn)
    if "mix_medicaid" in prefill_answers:
        mmd = float(prefill_answers["mix_medicaid"])
        output_fn(f"  Medicaid %: {mmd*100:.1f}%  (from HCRIS day-share)")
    else:
        mmd = _ask("Medicaid %", default=_default_mix("Medicaid"),
                   parser=_parse_percent, validator=_mix_validator,
                   input_fn=input_fn, output_fn=output_fn)
    mc = _ask("Commercial %", default=_default_mix("Commercial"),
              parser=_parse_percent, validator=_mix_validator,
              input_fn=input_fn, output_fn=output_fn)
    total = mm + mmd + mc
    if total > 1.0001:
        output_fn(f"  ! Mix exceeds 100% ({total*100:.1f}%). Re-prompting.")
        return interactive_intake(out_path, input_fn, output_fn, ccn_prefill=None)
    msp = max(0.0, 1.0 - total)
    output_fn(f"  → SelfPay (residual): {msp*100:.1f}%")
    answers.update({"mix_medicare": mm, "mix_medicaid": mmd, "mix_commercial": mc})

    output_fn("")
    output_fn("Operating KPIs (blended across payers; template distributes to each):")

    t_blend_idr = _blended_mean(template, ("denials", "idr")) or 0.13
    t_blend_fwr = _blended_mean(template, ("denials", "fwr")) or 0.30
    t_blend_dar = _blended_mean(template, ("dar_clean_days",)) or 45.0

    answers["idr_blended"] = _ask(
        "Blended initial denial rate (%)",
        default=round(t_blend_idr, 3),
        parser=_parse_percent,
        validator=_validator_range(0, 0.8, "IDR"),
        input_fn=input_fn, output_fn=output_fn,
    )
    answers["fwr_blended"] = _ask(
        "Blended final write-off rate (% of denials)",
        default=round(t_blend_fwr, 3),
        parser=_parse_percent,
        validator=_validator_range(0, 0.95, "FWR"),
        input_fn=input_fn, output_fn=output_fn,
    )
    answers["dar_blended"] = _ask(
        "Blended A/R days",
        default=round(t_blend_dar, 1),
        parser=float,
        validator=_validator_range(5, 200, "A/R days"),
        input_fn=input_fn, output_fn=output_fn,
    )

    output_fn("")
    output_fn("Financial context:")
    answers["ebitda_margin"] = _ask(
        "EBITDA margin (%)",
        default=float(t_hosp.get("ebitda_margin", 0.08)),
        parser=_parse_percent,
        validator=_validator_range(-0.5, 0.5, "EBITDA margin"),
        input_fn=input_fn, output_fn=output_fn,
    )
    answers["wacc"] = _ask(
        "WACC (%)",
        default=float(t_econ.get("wacc_annual", 0.12)),
        parser=_parse_percent,
        validator=_validator_range(0.01, 0.40, "WACC"),
        input_fn=input_fn, output_fn=output_fn,
    )

    # Pass through any prefill keys that aren't collected via prompts
    # (e.g. hospital_ccn — metadata for downstream peer-compare).
    for k, v in prefill_answers.items():
        answers.setdefault(k, v)

    output_fn("")
    output_fn("─" * 60)
    output_fn("Writing config with your inputs marked observed…")

    # HCRIS-sourced fields get a specific provenance note that overrides the
    # default "provided via intake wizard" stamp.
    extra_obs: Optional[Dict[str, str]] = None
    if hcris_bundle:
        extra_obs = {p: hcris_bundle["note"] for p in hcris_bundle["hcris_paths"]}

    cfg = run_intake(
        answers,
        template_name=template_name,
        out_path=out_path,
        extra_observations=extra_obs,
    )
    output_fn(f"  ✓ {os.path.abspath(out_path)}")
    if hcris_bundle:
        output_fn(f"  ✓ {len(hcris_bundle['hcris_paths'])} fields tagged from HCRIS provenance")
    output_fn("")
    output_fn("Next:")
    output_fn(f"  rcm-mc --actual {out_path} --benchmark configs/benchmark.yaml --outdir outputs")
    output_fn("")
    return cfg


# ── Name → CCN resolution (Brick 40) ────────────────────────────────────────

def _resolve_name_to_ccn(name: str) -> tuple:
    """Fuzzy-match ``name`` against CMS HCRIS, return ``(exit_code, ccn)``.

    Behavior:
    - Zero matches → exit_code=1, ccn=None, error printed to stderr
    - Exactly one match → exit_code=0, ccn=<resolved CCN>
    - Multiple matches → exit_code=2, ccn=None, top 5 candidates printed to
      stderr with guidance to re-run with an explicit --from-ccn

    Design: ambiguity is surfaced, not silently resolved. A diligence tool
    must not guess which "Memorial Hospital" the analyst meant — there are
    dozens and picking the wrong one corrupts the entire pipeline.
    """
    from .hcris import lookup_by_name

    matches = lookup_by_name(name, limit=5)
    if not matches:
        sys.stderr.write(
            f"No HCRIS match for {name!r}. Try a shorter search, or use "
            f"`rcm-lookup --name {name!r}` first to browse candidates.\n"
        )
        return (1, None)

    if len(matches) == 1:
        ccn = matches[0].get("ccn")
        sys.stderr.write(f"Resolved {name!r} → CCN {ccn} ({matches[0].get('name')})\n")
        return (0, ccn)

    sys.stderr.write(
        f"Multiple HCRIS matches for {name!r}. Re-run with "
        f"--from-ccn <exact CCN>:\n"
    )
    for m in matches:
        state = m.get("state") or "?"
        city = m.get("city") or "?"
        sys.stderr.write(
            f"  {m.get('ccn')}  {m.get('name')}  ({city}, {state})\n"
        )
    return (2, None)


# ── CLI entry ────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None, prog: str = "rcm-intake") -> int:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Interactive wizard: 11 prompts → validated actual.yaml.",
    )
    ap.add_argument(
        "--out", default="actual.yaml",
        help="Output YAML path (default: actual.yaml in cwd).",
    )
    ap.add_argument(
        "--from-ccn", default=None, metavar="CCN",
        help=(
            "Optional 6-digit Medicare Provider Number. Pre-fills hospital "
            "name, NPSR, and payer day-shares from CMS HCRIS before the wizard."
        ),
    )
    ap.add_argument(
        "--from-name", default=None, metavar="NAME",
        help=(
            "Optional hospital name (fuzzy match against CMS HCRIS). If a "
            "single match is found, its CCN is used as --from-ccn. If multiple, "
            "the top 5 matches are shown and the wizard exits so the analyst "
            "can re-run with a specific --from-ccn."
        ),
    )
    args = ap.parse_args(argv)

    # Resolve --from-name to a CCN *before* checking interactivity. The
    # fuzzy-search stage is purely non-interactive: if it fails / is ambiguous,
    # we report and exit without needing a TTY. This lets a scripted caller
    # pre-screen names before committing to an intake session.
    resolved_ccn = args.from_ccn
    if args.from_name and not args.from_ccn:
        code, ccn_or_none = _resolve_name_to_ccn(args.from_name)
        if code != 0:
            return code
        resolved_ccn = ccn_or_none

    if not sys.stdin.isatty():
        sys.stderr.write(
            "intake requires an interactive terminal. "
            "For non-interactive runs use `rcm-mc --template <name>` directly.\n"
        )
        return 2

    try:
        interactive_intake(args.out, ccn_prefill=resolved_ccn)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled. No file written.\n")
        return 130
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"intake failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
