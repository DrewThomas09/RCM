"""Read-only join validation against openFDA's drug NDCs.

The NDC→RxCUI crosswalk only earns its keep if it actually joins to the
NDC-keyed records other sources carry. openFDA's vendored drug-shortage
snapshot (``rcm_mc/data/vendor/drug_data/fda_drug_shortages.csv``) carries a
``package_ndc`` column — exactly the kind of NDC-keyed record that has to tie
back to a molecule. We read it **read-only** (we never modify openFDA's tables;
that connector is out of scope) and report the share of its NDCs that resolve
through our crosswalk after canonical normalization.

The match rate is reported, not asserted to a threshold: with the offline seed
only a few NDCs overlap, so the value of this check is that the *plumbing*
works end-to-end (normalize → join → rate), which is what makes a live backfill
trustworthy.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from . import store as st
from .normalize import normalize_ndc, NdcNormalizationError

# openFDA's vendored drug snapshot — read-only join source.
_OPENFDA_SHORTAGES = (
    Path(__file__).resolve().parents[2]
    / "data" / "vendor" / "drug_data" / "fda_drug_shortages.csv"
)


def _read_openfda_package_ndcs(path: Path = _OPENFDA_SHORTAGES) -> List[str]:
    """Pull distinct non-empty package_ndc values from openFDA's snapshot."""
    if not path.is_file():
        return []
    out: List[str] = []
    seen = set()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            ndc = str(r.get("package_ndc", "")).strip()
            if ndc and ndc not in seen:
                seen.add(ndc)
                out.append(ndc)
    return out


def openfda_ndc_match_rate(store: Any,
                           path: Path = _OPENFDA_SHORTAGES) -> Dict[str, Any]:
    """Report the crosswalk match rate against openFDA's drug NDCs.

    Returns ``{openfda_ndcs, normalizable, matched, match_rate, unmatched_sample}``
    where ``match_rate`` is matched / normalizable in [0, 1].
    """
    raw_ndcs = _read_openfda_package_ndcs(path)
    normalizable: List[str] = []
    bad = 0
    for raw in raw_ndcs:
        try:
            normalizable.append(normalize_ndc(raw))
        except NdcNormalizationError:
            bad += 1

    matched = 0
    unmatched_sample: List[str] = []
    with store.connect() as con:
        st.ensure_tables(con)
        for ndc_11 in normalizable:
            row = con.execute(
                "SELECT 1 FROM xwalk_ndc_rxcui WHERE ndc_11 = ?", (ndc_11,)
            ).fetchone()
            if row:
                matched += 1
            elif len(unmatched_sample) < 10:
                unmatched_sample.append(ndc_11)

    denom = len(normalizable)
    rate = round(matched / denom, 4) if denom else 0.0
    return {
        "openfda_ndcs": len(raw_ndcs),
        "unnormalizable": bad,
        "normalizable": denom,
        "matched": matched,
        "match_rate": rate,
        "unmatched_sample": unmatched_sample,
    }
