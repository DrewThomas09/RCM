"""BOLSTER-05 Chart-pack rendering standards.

Enforces a uniform exhibit standard so every chart in the pack is defensible:
- mandatory machine-readable footnote with source, vintage, and key assumptions,
- IBCS green/red/blue waterfall convention (start and end blue, positive delta
  green, negative delta red),
- no em-dashes in any label or title (the exhibit copy linter already guards
  this; the validator double-checks the rendered payload),
- a stable structural snapshot for regression snapshot tests.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .exhibit import Exhibit

WATERFALL_TOL = 1e-9


def _has_dash(text: Any) -> bool:
    return isinstance(text, str) and ("—" in text or "–" in text)


def validate_standards(exhibit: Exhibit) -> List[str]:
    """Return a list of standards violations. Empty means the exhibit conforms."""
    violations: List[str] = []
    rendered = exhibit.render(internal_mode=True)

    fn = rendered.get("footnote")
    if not fn:
        violations.append("missing footnote")
    else:
        if not fn.get("source"):
            violations.append("footnote missing source")
        if not fn.get("vintage"):
            violations.append("footnote missing vintage")
        if not fn.get("assumptions"):
            violations.append("footnote missing key assumptions")

    if _has_dash(rendered.get("title")):
        violations.append("em-dash in title")
    if _has_dash(rendered.get("summary")):
        violations.append("em-dash in summary")

    for s in rendered.get("series", []):
        if _has_dash(s.get("name")):
            violations.append(f"em-dash in series name {s.get('name')!r}")
        for pt in s.get("points", []):
            if _has_dash(pt.get("label")):
                violations.append(f"em-dash in point label {pt.get('label')!r}")
        if s.get("kind") == "waterfall":
            violations.extend(_check_waterfall(s))
    return violations


def _check_waterfall(series: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    name = series.get("name")
    for pt in series.get("points", []):
        kind = pt.get("kind")
        color = pt.get("color")
        val = pt.get("value", 0.0)
        if kind in ("start", "end"):
            if color != "blue":
                out.append(f"{name}: {kind} point color {color!r} not blue")
        elif kind == "delta":
            expected = "green" if val >= -WATERFALL_TOL else "red"
            if color != expected:
                out.append(f"{name}: delta {pt.get('label')!r} color {color!r} not {expected}")
    return out


def snapshot_exhibit(exhibit: Exhibit) -> Dict[str, Any]:
    """A stable structural fingerprint for snapshot regression tests."""
    rendered = exhibit.render(internal_mode=True)
    return {
        "feature_id": rendered["feature_id"],
        "title": rendered["title"],
        "series": [
            {"name": s["name"], "kind": s["kind"],
             "n_points": len(s.get("points", [])),
             "internal_only": s.get("internal_only", False)}
            for s in rendered["series"]
        ],
        "flags": sorted(f["code"] for f in rendered["flags"]),
        "reconciliations": [r["identity"] for r in rendered["reconciliations"]],
        "footnote_keys": sorted(rendered["footnote"].keys()) if rendered["footnote"] else [],
    }


def audit_standards() -> Dict[str, List[str]]:
    """Validate standards across every registered feature."""
    from . import registry
    return {f.feature_id: validate_standards(f.demo()) for f in registry.all_features()}
