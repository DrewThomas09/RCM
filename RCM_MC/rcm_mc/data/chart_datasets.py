"""Chart-ready aggregates from the vendored CMS provider snapshots.

The Chart Builder is paste-driven; this module gives it real platform
data with zero pasting — each dataset is a small, pre-aggregated TSV
(the same shape `parse_table` expects) built from the six vendored
provider files (SNF, home health, hospice, dialysis, IRF, LTCH). All
aggregation happens here, in the data layer, so the UI only ever sees
a finished table; results are cached per process because the vendored
snapshots are immutable.

No runtime network calls — these are the same one-time vendored CSVs
the Sector Intelligence verticals read.
"""
from __future__ import annotations

import csv
import functools
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

_DATA_DIR = Path(__file__).parent

# (key, sector label, providers csv)
_SECTORS: List[Tuple[str, str, str]] = [
    ("snf", "SNF / nursing homes", "snf_providers.csv"),
    ("home_health", "Home health", "home_health_providers.csv"),
    ("hospice", "Hospice", "hospice_providers.csv"),
    ("dialysis", "Dialysis", "dialysis_providers.csv"),
    ("irf", "IRF", "irf_providers.csv"),
    ("ltch", "LTCH", "ltch_providers.csv"),
]

_TOP_N_STATES = 12


@functools.lru_cache(maxsize=None)
def _rows(fname: str) -> Tuple[Dict[str, str], ...]:
    """Slim row dicts (state / ownership / the one numeric column we
    aggregate) — tuple so the cache value is immutable."""
    keep = ("state", "ownership", "certified_beds", "total_beds",
            "dialysis_stations", "source_date")
    out = []
    with open(_DATA_DIR / fname, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({k: (r.get(k) or "").strip() for k in keep})
    return tuple(out)


def _source_date(fname: str) -> str:
    rows = _rows(fname)
    return rows[0].get("source_date", "") if rows else ""


def _ownership_bucket(raw: str) -> str:
    """Collapse the per-file ownership vocabularies (e.g. 'For profit -
    Corporation', 'PROPRIETARY', 'For-Profit') into four buckets so the
    mix is comparable across sectors."""
    v = (raw or "").strip().lower()
    if not v:
        return "Other"
    if "non" in v and "profit" in v:
        return "Non-profit"
    if "profit" in v or "proprietary" in v:
        return "For-profit"
    if "gov" in v or "state" in v or "city" in v or "county" in v \
            or "federal" in v:
        return "Government"
    return "Other"


def _fmt_int(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"


def _top_states_tsv(fname: str, value_header: str,
                    numeric_col: "str | None" = None) -> str:
    """Top-N states + 'Other (k)' — by provider count, or by the sum of
    ``numeric_col`` when given (beds, stations)."""
    totals: Dict[str, float] = {}
    for r in _rows(fname):
        st = r["state"].upper()
        if not st:
            continue
        if numeric_col:
            try:
                v = float(r[numeric_col])
            except (KeyError, ValueError):
                continue
        else:
            v = 1.0
        totals[st] = totals.get(st, 0.0) + v
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    lines = [f"State\t{value_header}"]
    for st, v in ranked[:_TOP_N_STATES]:
        lines.append(f"{st}\t{_fmt_int(v)}")
    rest = ranked[_TOP_N_STATES:]
    if rest:
        lines.append(f"Other ({len(rest)})\t"
                     f"{_fmt_int(sum(v for _, v in rest))}")
    return "\n".join(lines)


def _providers_by_sector_tsv() -> str:
    lines = ["Sector\tProviders"]
    for _, label, fname in _SECTORS:
        lines.append(f"{label}\t{len(_rows(fname))}")
    return "\n".join(lines)


def _ownership_mix_tsv() -> str:
    buckets = ["For-profit", "Non-profit", "Government", "Other"]
    lines = ["Sector\t" + "\t".join(buckets)]
    for _, label, fname in _SECTORS:
        counts = {b: 0 for b in buckets}
        for r in _rows(fname):
            counts[_ownership_bucket(r["ownership"])] += 1
        lines.append(label + "\t" + "\t".join(str(counts[b])
                                              for b in buckets))
    return "\n".join(lines)


# key → (label, suggested chart type, builder)
_REGISTRY: Dict[str, Tuple[str, str, Callable[[], str]]] = {}


def _reg(key, label, chart, fn):
    _REGISTRY[key] = (label, chart, fn)


_reg("providers_by_sector", "Certified providers by sector", "pareto",
     _providers_by_sector_tsv)
_reg("ownership_mix", "Ownership mix by sector", "column_100",
     _ownership_mix_tsv)
_reg("snf_beds_by_state", "SNF certified beds by state", "bar",
     lambda: _top_states_tsv("snf_providers.csv", "Certified beds",
                             "certified_beds"))
_reg("dialysis_stations_by_state", "Dialysis stations by state", "bar",
     lambda: _top_states_tsv("dialysis_providers.csv", "Stations",
                             "dialysis_stations"))
for _key, _label, _fname in _SECTORS:
    _reg(f"{_key}_by_state", f"{_label} providers by state", "bar",
         (lambda f: lambda: _top_states_tsv(f, "Providers"))(_fname))


def list_chart_datasets() -> List[Dict[str, str]]:
    """The dataset menu — key / label / suggested chart, in registry
    order (cross-sector first, then per-sector state tables)."""
    return [{"key": k, "label": lab, "chart": ch}
            for k, (lab, ch, _) in _REGISTRY.items()]


@functools.lru_cache(maxsize=None)
def build_chart_dataset(key: str) -> Dict[str, str]:
    """Build one dataset: ``{label, chart, tsv, footnote}``. Unknown
    keys raise KeyError — callers present a fixed menu, so an unknown
    key is a programming error, not user input."""
    label, chart, fn = _REGISTRY[key]
    # Source line travels with the chart (every exhibit carries one).
    # Per-sector datasets cite that file's snapshot date; cross-sector
    # ones span six snapshots, so no single date is honest.
    fname = next((f for _, _, f in _SECTORS
                  if key.startswith(f.split("_providers")[0])), None)
    sd = _source_date(fname) if fname else ""
    foot = "Source: CMS provider files (vendored snapshot" + \
        (f", {sd})" if sd else "s)")
    return {"label": label, "chart": chart, "tsv": fn(),
            "footnote": foot}
