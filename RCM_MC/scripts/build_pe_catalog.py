"""Generate a static catalog of the pe_intelligence analytic tools.

`rcm_mc/pe_intelligence/` holds ~276 modules of PE-diligence analytics, but
only ~8 are reachable in the UI — the rest are dark (built, tested, never
linked). This script introspects the package **by AST** (no imports — far too
slow / side-effect-prone to import 224 modules at request time) and emits a
static manifest `rcm_mc/pe_intelligence/_catalog.py` that the unified PE
Intelligence Library page (`/diligence/pe-library`) reads cheaply.

Per tool it records: slug, title, one-line purpose (module docstring), the
builder + render function names, the builder's first required input type, LOC,
a derived category, and whether the tool is already surfaced elsewhere in the
UI. Rerun after adding/retiring a pe_intelligence module.
"""
from __future__ import annotations

import ast
import pathlib
from typing import Dict, List, Tuple

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PEI = _ROOT / "rcm_mc" / "pe_intelligence"
_SERVER = (_ROOT / "rcm_mc" / "server.py").read_text(errors="replace")
_HUB = (_ROOT / "rcm_mc" / "ui" / "chartis" / "pe_intelligence_hub_page.py")

# Category inference from module-name keywords (ordered — first hit wins).
_CATEGORIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("Regulatory & reimbursement", (
        "regulatory", "reimbursement", "cliff", "obbba", "site_neutral",
        "sequestration", "pama", "340b", "hsr", "antitrust", "con_",
        "scope_of_practice", "medicaid", "ma_star", "rac_audit", "cms_rule",
        "state_ag", "sequestration", "multi_state")),
    ("EBITDA & quality of earnings", (
        "ebitda", "qofe", "qoe", "recurring", "normalization", "add_back",
        "addback", "cost_line", "cash_conversion", "quality")),
    ("Working capital & cash", ("working_capital", "wc_", "liquidity",
        "seasonality", "capex")),
    ("Valuation, debt & returns", (
        "irr", "moic", "lbo", "multiple", "reprice", "secondary",
        "dividend_recap", "vintage", "roic", "break_price", "debt",
        "refinanc", "cap_structure", "capital_structure", "bank_syndicate",
        "syndicate", "continuation_vehicle", "coinvest", "lp_waterfall")),
    ("Exit", ("exit_", "secondary_sale")),
    ("Management & people", (
        "management", "physician", "c_suite", "board", "labor", "staffing",
        "retention", "_comp", "comp_", "incentive", "rollover", "mip",
        "operating_partner", "bench_depth")),
    ("Thesis & archetype", (
        "thesis", "archetype", "bear", "smell", "unrealistic", "implausib",
        "sniff", "regime", "coherence", "sharpness")),
    ("Market, competition & growth", (
        "market", "competit", "bidder", "concentration", "white_space",
        "geographic", "local_market", "rollup", "platform", "add_on",
        "growth", "service_line", "patient_acquisition", "referral",
        "site_of_service", "outpatient", "de_novo", "payer_mix",
        "subsector", "pricing_power")),
    ("Process, IC & negotiation", (
        "ic_", "partner_", "memo", "briefing", "discussion", "negotiation",
        "loi", "reps", "closing", "signing", "data_room", "diligence_",
        "reference_check", "red_team", "red_flag", "process", "workstream",
        "seller", "banker", "letter", "earnout", "peg", "term_sheet",
        "deal_source", "deal_one_liner", "competing_deals", "priority")),
    ("Integration & value creation", (
        "integration", "synergy", "value_creation", "100_day", "hundred_day",
        "day_one", "governance", "vcp", "first_thirty", "first_sitdown",
        "quarterly_operating", "velocity", "scoreboard", "ma_pipeline",
        "ma_integration")),
    ("Risk, stress & post-close", (
        "stress", "risk", "shock", "covenant", "turnaround", "margin_of_safety",
        "post_close", "post_mortem", "pre_mortem", "tail", "drift",
        "compression", "haircut", "insurance", "tax", "tech_debt",
        "ehr_transition", "vbc", "feasibility", "clinical_outcome", "wage")),
    ("LP & fund", ("lp_", "fund_", "ilpa", "esg", "vintage_return")),
]


def _category(stem: str) -> str:
    for label, keys in _CATEGORIES:
        if any(k in stem for k in keys):
            return label
    return "Other analytics"


def _title(stem: str) -> str:
    # cliff_calendar_2026_2029 → "Cliff Calendar 2026 2029"; trim trailing years.
    words = stem.replace("_", " ").split()
    out = " ".join(w.upper() if w.isupper() else w.capitalize() for w in words)
    return out


def _first_required_type(fn: ast.FunctionDef) -> str:
    args = fn.args
    pos = list(args.posonlyargs) + list(args.args)
    n_def = len(args.defaults)
    required = pos[: len(pos) - n_def] if n_def else pos
    required = [a for a in required if a.arg != "self"]
    if not required:
        return ""
    ann = required[0].annotation
    if ann is None:
        return "?"
    try:
        return ast.unparse(ann)
    except Exception:  # noqa: BLE001
        return "?"


def _wired(stem: str, render_fn: str) -> bool:
    # Surfaced if the page module or its render fn is referenced by server.py
    # or named in the PE Intelligence hub catalog.
    if stem in _SERVER or render_fn in _SERVER:
        return True
    hub = _HUB.read_text(errors="replace") if _HUB.is_file() else ""
    return stem in hub


def build_catalog() -> List[Dict]:
    rows: List[Dict] = []
    for p in sorted(_PEI.glob("*.py")):
        if p.name.startswith("_"):
            continue
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except SyntaxError:
            continue
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        render = next((f for f in funcs if f.name.startswith("render_")
                       and f.name.endswith("_markdown")), None)
        if render is None:
            continue
        # Primary builder: first public func that isn't render_/list_ and has a
        # required arg (the input the tool computes from).
        builder = next((f for f in funcs
                        if not f.name.startswith(("_", "render", "list"))
                        and _first_required_type(f)), None)
        doc = ast.get_docstring(tree) or ""
        # Full first docstring line (the dash convention is inconsistent across
        # modules — sometimes "Title — desc", sometimes "Desc — tag" — so
        # stripping a prefix loses meaning; the title is shown separately).
        purpose = doc.strip().splitlines()[0] if doc.strip() else ""
        loc = p.read_text(errors="replace").count("\n")
        rows.append({
            "slug": p.stem,
            "title": _title(p.stem),
            "purpose": purpose[:180],
            "category": _category(p.stem),
            "builder": builder.name if builder else "",
            "render_fn": render.name,
            "input_type": _first_required_type(builder) if builder else "",
            "loc": loc,
            "wired": _wired(p.stem, render.name),
        })
    rows.sort(key=lambda r: (r["category"], -r["loc"]))
    return rows


def _write(rows: List[Dict]) -> pathlib.Path:
    dest = _PEI / "_catalog.py"
    lines = [
        '"""AUTO-GENERATED by scripts/build_pe_catalog.py — do not hand-edit.',
        "",
        "Static inventory of the pe_intelligence analytic tools, read by the",
        "PE Intelligence Library page. Rerun the script to refresh.",
        '"""',
        "from __future__ import annotations",
        "",
        "from typing import Dict, List",
        "",
        f"# {len(rows)} tools across "
        f"{len(set(r['category'] for r in rows))} categories.",
        "CATALOG: List[Dict] = [",
    ]
    for r in rows:
        lines.append("    {")
        for k in ("slug", "title", "purpose", "category", "builder",
                  "render_fn", "input_type"):
            lines.append(f"        {k!r}: {r[k]!r},")
        lines.append(f"        'loc': {r['loc']}, 'wired': {r['wired']},")
        lines.append("    },")
    lines.append("]")
    lines.append("")
    dest.write_text("\n".join(lines))
    return dest


def main() -> int:
    rows = build_catalog()
    dest = _write(rows)
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print(f"Cataloged {len(rows)} pe_intelligence tools → {dest}")
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4}  {c}")
    print(f"  wired already: {sum(1 for r in rows if r['wired'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
