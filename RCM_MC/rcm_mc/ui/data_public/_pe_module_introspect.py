"""Introspect ``rcm_mc.pe_intelligence`` at runtime for auto-rendering.

The partner-brain library has 275 modules that all follow the same
shape: docstring → Input dataclass → compute function → Report
dataclass (with ``partner_note`` and ``to_dict``) → render_markdown
function. This module walks the package and returns a structured
catalog so the directory page can enumerate them and the detail
page can auto-run them.

Kept minimal on purpose: no side effects, results cached per
process, tolerates modules that don't fit the pattern exactly.
"""
from __future__ import annotations

import ast
import dataclasses as _dc
import importlib
import inspect
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_INPUT_SUFFIXES = (
    "Inputs", "Input", "Context", "Signals", "Statement",
    "Bundle", "Request",
)
_COMPUTE_PREFIXES = (
    "analyze_", "assess_", "check_", "compute_", "detect_",
    "build_", "run_", "scan_", "synthesize_", "validate_",
    "match_", "project_", "recognize_", "evaluate_",
    "score_", "simulate_", "underwrite_", "model_",
    "map_", "diagnose_", "plan_", "fit_", "predict_",
    "forecast_", "rank_", "classify_", "allocate_",
    "apply_", "sequence_", "grade_", "size_", "select_",
    "identify_", "calibrate_", "quantify_", "screen_",
    "profile_", "draft_", "layer_", "walk_", "design_",
)
_RENDER_PREFIXES = ("render_",)


# A few intentional exclusions — orchestrators, helpers, re-exports,
# libraries of patterns that aren't individual callable analyses.
_SKIP_MODULES = {
    "__init__",
    "partner_review",          # already surfaced at /partner-brain/review
    "heuristics",              # the rule library itself (used by partner_review)
    "narrative",               # narrative composer (internal)
    "reasonableness",          # internal to partner_review
    "red_flags",               # internal to partner_review
    "valuation_checks",        # internal
    "memo_formats",            # format registry
    "narrative_styles",        # style registry
    "bear_patterns",           # pattern catalog
    "failure_archetype_library",  # catalog
    "named_failure_library",   # catalog (v2 is the callable one)
    "extra_heuristics",        # rule add-on
    "extra_red_flags",         # rule add-on
    "BEAR_PATTERNS",
}


@dataclass
class PEModuleEntry:
    name: str
    file_path: str
    docstring: str
    first_line: str
    categories: List[str] = field(default_factory=list)
    input_class: Optional[str] = None
    compute_fn: Optional[str] = None
    render_fn: Optional[str] = None
    report_class: Optional[str] = None
    all_classes: List[str] = field(default_factory=list)
    all_functions: List[str] = field(default_factory=list)
    importable: bool = True
    import_error: str = ""


def _guess_categories(name: str, docstring: str) -> List[str]:
    """Heuristic tag assignment for directory filtering."""
    text = (name + " " + docstring).lower()
    cats: List[str] = []
    tests = [
        ("valuation", ("valuation", "multiple", "exit_value", "pricing", "rollup_arbitrage", "secondary_sale")),
        ("ic-decision", ("ic_decision", "ic_memo", "ic_dialog", "red_team", "thesis_valid", "bear_book")),
        ("sniff", ("unrealistic", "on_face", "archetype", "sniff", "face_check")),
        ("100-day", ("day_one", "100_day", "100day", "post_close", "integration", "ehr_transition")),
        ("regulatory", ("regulatory", "site_neutral", "cms_rule", "obbba", "hsr", "antitrust", "oig", "rac", "pama", "medicaid_unwind")),
        ("failures", ("failure", "smell", "trap", "named_", "bridge_trap", "renegotiation_timing")),
        ("wc", ("working_capital", "cash_conversion", "peg_negotiat", "liquidity")),
        ("team", ("c_suite", "management_", "physician_retention", "comp_plan", "retention", "labor")),
        ("synthesis", ("synthesis", "sensitivity_grid", "concentration", "platform_vs")),
        ("rcm-payer", ("rcm_", "payer_mix", "ma_star", "vbc_", "lever_cascade")),
        ("process", ("banker_", "diligence", "loi_", "reverse_diligence", "process_")),
        ("business-model", ("ebitda_quality", "recurring_ebitda", "service_line", "contract_diligence")),
        ("debt", ("lbo_", "covenant_", "debt_", "leverage_")),
        ("lp-ops", ("lp_", "vintage_return", "fund_model", "continuation")),
        ("opportunity", ("outpatient_migration", "growth_algorithm", "peer_discovery", "white_space")),
        ("hold", ("continuation_vehicle", "hold_period", "earnout_design")),
        ("quality-esg", ("esg_", "quality_metric", "post_mortem")),
        ("vcp", ("value_creation", "vcp_", "three_year", "3_year")),
        ("exit", ("exit_", "buyer_fit", "buyer_type")),
    ]
    for cat, needles in tests:
        if any(n in text for n in needles):
            cats.append(cat)
    return cats or ["other"]


def _pick_compute_and_input(tree: ast.Module) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """From the AST, pick the best (compute_fn, input_class, render_fn)
    triple. Uses name heuristics only — does not execute the module."""
    classes = [n for n in ast.iter_child_nodes(tree)
               if isinstance(n, ast.ClassDef) and not n.name.startswith("_")]
    funcs = [n for n in ast.iter_child_nodes(tree)
             if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]

    input_class = None
    for c in classes:
        if any(c.name.endswith(s) for s in _INPUT_SUFFIXES):
            input_class = c.name
            break

    compute_fn = None
    # Prefer functions whose signature takes the input_class as first arg
    if input_class:
        for f in funcs:
            args = f.args.args
            if not args:
                continue
            ann = args[0].annotation
            if isinstance(ann, ast.Name) and ann.id == input_class:
                compute_fn = f.name
                break
    if compute_fn is None:
        # Fall back: first function with a "compute-like" prefix
        for f in funcs:
            if any(f.name.startswith(p) for p in _COMPUTE_PREFIXES):
                compute_fn = f.name
                break
    if compute_fn is None and funcs:
        # Last resort: first non-render public function
        for f in funcs:
            if not any(f.name.startswith(p) for p in _RENDER_PREFIXES):
                compute_fn = f.name
                break

    render_fn = None
    for f in funcs:
        if any(f.name.startswith(p) for p in _RENDER_PREFIXES):
            render_fn = f.name
            break

    return compute_fn, input_class, render_fn


def _pick_report_class(tree: ast.Module, compute_fn: Optional[str]) -> Optional[str]:
    """Best guess at the Report dataclass (the compute_fn's return)."""
    if compute_fn is None:
        return None
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, ast.FunctionDef) and n.name == compute_fn:
            ret = n.returns
            if isinstance(ret, ast.Name):
                return ret.id
            if isinstance(ret, ast.Subscript):
                # e.g., List[ConsistencyFinding]
                v = ret.value
                if isinstance(v, ast.Name):
                    return v.id
    # Fallback: class whose name ends with "Report"
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, ast.ClassDef) and n.name.endswith("Report"):
            return n.name
    return None


_CACHE: Dict[str, List[PEModuleEntry]] = {}


def catalog_pe_intelligence() -> List[PEModuleEntry]:
    """Return the full catalog of ``rcm_mc.pe_intelligence`` modules.

    Uses AST inspection only — does not import the modules. Cached
    per process so repeated page loads are cheap."""
    cache_key = "pe_intelligence"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        pkg = importlib.import_module("rcm_mc.pe_intelligence")
        pkg_path = pathlib.Path(pkg.__file__).parent
    except Exception:  # noqa: BLE001
        return []

    entries: List[PEModuleEntry] = []
    for fp in sorted(pkg_path.glob("*.py")):
        stem = fp.stem
        if stem in _SKIP_MODULES:
            continue
        try:
            src = fp.read_text()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue

        doc = ast.get_docstring(tree) or ""
        first_line = (doc.split("\n", 1)[0].strip() if doc else "")

        classes = [
            n.name for n in ast.iter_child_nodes(tree)
            if isinstance(n, ast.ClassDef) and not n.name.startswith("_")
        ]
        funcs = [
            n.name for n in ast.iter_child_nodes(tree)
            if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
        ]

        compute_fn, input_class, render_fn = _pick_compute_and_input(tree)
        report_class = _pick_report_class(tree, compute_fn)

        entries.append(PEModuleEntry(
            name=stem,
            file_path=str(fp),
            docstring=doc,
            first_line=first_line,
            categories=_guess_categories(stem, doc),
            input_class=input_class,
            compute_fn=compute_fn,
            render_fn=render_fn,
            report_class=report_class,
            all_classes=classes,
            all_functions=funcs,
        ))

    _CACHE[cache_key] = entries
    return entries


def find_entry(module_name: str) -> Optional[PEModuleEntry]:
    for e in catalog_pe_intelligence():
        if e.name == module_name:
            return e
    return None


def try_construct_default(cls: Any) -> Optional[Any]:
    """Attempt to construct an instance of a dataclass with its defaults.

    Returns None if required fields lack defaults or if construction
    raises. Used by the detail page to auto-run ``compute(defaults)``
    for modules whose Input is fully defaulted."""
    if cls is None or not _dc.is_dataclass(cls):
        return None
    try:
        return cls()
    except TypeError:
        return None


def run_module_default(module_name: str) -> Dict[str, Any]:
    """Import the module, find its compute function + input class,
    construct defaults if possible, and return a report dict.

    Returns a dict with keys:
        ok: bool
        report_dict: Optional[dict]
        report_type: Optional[str]
        markdown: Optional[str]
        reason: str  — human-readable reason when ok=False
    """
    out: Dict[str, Any] = {
        "ok": False,
        "report_dict": None,
        "report_type": None,
        "markdown": None,
        "reason": "",
    }
    entry = find_entry(module_name)
    if entry is None:
        out["reason"] = f"module '{module_name}' not in catalog"
        return out
    if entry.compute_fn is None:
        out["reason"] = "no compute function detected"
        return out

    try:
        mod = importlib.import_module(f"rcm_mc.pe_intelligence.{module_name}")
    except Exception as exc:  # noqa: BLE001
        out["reason"] = f"import error: {exc}"
        return out

    compute = getattr(mod, entry.compute_fn, None)
    if compute is None:
        out["reason"] = f"compute fn {entry.compute_fn!r} not found after import"
        return out

    input_obj = None
    if entry.input_class:
        input_cls = getattr(mod, entry.input_class, None)
        input_obj = try_construct_default(input_cls)
        if input_obj is None:
            out["reason"] = (
                f"input class {entry.input_class!r} has required fields; "
                f"auto-run requires a demo input builder"
            )
            return out

    try:
        if input_obj is not None:
            report = compute(input_obj)
        else:
            # Zero-arg compute function (rare but exists for catalog-style modules)
            sig = inspect.signature(compute)
            if len(sig.parameters) == 0:
                report = compute()
            else:
                out["reason"] = (
                    f"compute fn {entry.compute_fn!r} requires args but no "
                    f"input dataclass was detected"
                )
                return out
    except Exception as exc:  # noqa: BLE001
        out["reason"] = f"compute raised {type(exc).__name__}: {exc}"
        return out

    # Serialize the report.
    report_type = type(report).__name__
    report_dict: Optional[Dict[str, Any]] = None
    if hasattr(report, "to_dict"):
        try:
            rd = report.to_dict()
            if isinstance(rd, dict):
                report_dict = rd
        except Exception:  # noqa: BLE001
            report_dict = None
    if report_dict is None and _dc.is_dataclass(report):
        try:
            report_dict = _dc.asdict(report)
        except Exception:  # noqa: BLE001
            report_dict = None
    if report_dict is None and isinstance(report, dict):
        report_dict = report
    if report_dict is None and isinstance(report, list):
        # List of findings — wrap into a dict for display.
        report_dict = {"items": [
            _dc.asdict(x) if _dc.is_dataclass(x) else (
                x.to_dict() if hasattr(x, "to_dict") else str(x)
            ) for x in report
        ]}

    markdown: Optional[str] = None
    if entry.render_fn:
        render = getattr(mod, entry.render_fn, None)
        if render is not None:
            try:
                out_val = render(report)
                if isinstance(out_val, str):
                    markdown = out_val
            except Exception:  # noqa: BLE001
                markdown = None

    out["ok"] = True
    out["report_dict"] = report_dict
    out["report_type"] = report_type
    out["markdown"] = markdown
    return out
