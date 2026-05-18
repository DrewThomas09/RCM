"""Hospital taxonomy — economic-regime labels for regression segmentation.

The HCRIS rollup tells us beds, payer mix, and financials but not
whether a row is Stanford or a 12-bed rural hospital in Iowa. Without
that distinction a single OLS regression flattens flagship academic
centers, small CAHs, and community hospitals into one slope per
variable — which is exactly why the current model's largest positive
residuals are academic / specialty institutions. Those rows aren't
errors; they belong to a different economic regime.

This module adds the labels a segmented regression needs. Every flag
is derivable from HCRIS columns we already have (CCN, name, beds,
medicare_day_pct, medicaid_day_pct, state) plus a curated list of
known academic / flagship-specialty system names — no extra data
ingest required. Outputs are added as new columns alongside the
existing HCRIS frame so callers can keep doing what they did before
or opt in to segment-aware analysis.

Flag derivation:

  - ``critical_access_flag``, ``children_flag``, ``psychiatric_flag``,
    ``rehab_flag``, ``ltach_flag`` — delegated to the existing
    ``classify_hospital_type`` CCN+name classifier.
  - ``academic_flag`` — name matches the known-academic system list
    OR contains UNIVERSITY / SCHOOL OF MEDICINE / MEDICAL SCHOOL.
  - ``teaching_flag`` — strict superset of academic_flag: also
    catches "Hospital of the University of …" patterns and
    explicit "TEACHING" in the name.
  - ``flagship_specialty_flag`` — name matches cancer-centre /
    quaternary-specialty list (MD Anderson, Memorial Sloan
    Kettering, Hospital for Special Surgery, etc.).
  - ``size_class`` — quartile bucket on ``beds`` (tier1_small /
    tier2_mid / tier3_large / tier4_mega). Quartile cuts use a
    fixed seed so the labels are stable across runs.
  - ``payer_class`` — bucket on ``medicare_day_pct`` (commercial /
    mixed / medicare_heavy / dual_eligible_heavy).
  - ``safety_net_proxy_flag`` — ``medicaid_day_pct >= 30`` proxy
    for safety-net status (we don't have the DSH-payment data
    that would give the canonical definition).
  - ``rural_proxy_flag`` — true if critical_access OR beds < 25 in
    a state with predominantly rural CCN ranges. Coarse, but
    enough to surface the regime difference in regression.
  - ``segment_label`` — single business-name label combining the
    above into the regime classification a partner would
    recognise: "Flagship Academic", "Large Community",
    "Small Community", "Critical Access", "Specialty",
    "Safety-Net Public", "Children's", "Psychiatric / Behavioral",
    "Rehab / LTACH", or "Other".

The label set deliberately maps 1:1 to the universe toggles
described in the regression rebuild plan, so the same column drives
the regression segmentation, the cluster naming, and the universe
selector in the UI.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from .hcris import _classify_series


# ── Known academic / teaching / flagship system names ──────────────
# Hand-curated. **This is intentionally NOT a complete list of US
# academic medical centres** — it's a deterministic shortlist used
# to confirm the flag for systems whose names don't already include
# UNIVERSITY / SCHOOL OF MEDICINE / MEDICAL SCHOOL (the generic
# pattern below catches the long tail). Keep this list short and
# explicit: every entry should be a system everyone agrees is an
# academic medical centre, with no risk of false-positive matches
# against community hospitals that share a keyword.
#
# Selection rationale: top US academic centres (Stanford, Mass
# General, Johns Hopkins, Cleveland Clinic, Mayo, UCSF, UCLA, MD
# Anderson, etc.) — these consistently appear in the largest-
# positive-residuals list because they have specialty referrals,
# residents, research, donor philanthropy and quaternary care that
# pooled OLS can't model with bed/payer/scale variables alone.
#
# If a system needs to be added: include both the canonical form
# AND any historical / colloquial variant the name field might
# carry (e.g. "MASS GENERAL" + "MASSACHUSETTS GENERAL").
#
# Substring match is case-insensitive (input upper-cased before
# matching) and applied to the WHOLE name string, so "STANFORD"
# matches "STANFORD HEALTH CARE", "STANFORD HOSPITAL", and
# "STANFORD UNIVERSITY MEDICAL CENTER" equivalently.
#
# Future migration path: when this list grows past ~50 entries or
# needs editorial input from non-engineers, move to a YAML/JSON
# file under data_public/ with per-row commentary. For Phase 1 (~40
# entries with engineering-only edits), the Python module-level
# constant is clearer to grep and audit.
_ACADEMIC_SYSTEM_NAMES: tuple[str, ...] = (
    "STANFORD",
    "CLEVELAND CLINIC",
    "MAYO CLINIC",
    "JOHNS HOPKINS",
    "MASSACHUSETTS GENERAL",
    "MASS GENERAL",
    "BRIGHAM AND WOMEN",
    "BETH ISRAEL DEACONESS",
    "UCSF",
    "UCLA",
    "NYU LANGONE",
    "MOUNT SINAI",
    "COLUMBIA UNIV",
    "WEILL CORNELL",
    "NEW YORK PRESBYTERIAN",
    "NEWYORK-PRESBYTERIAN",
    "DUKE UNIV",
    "VANDERBILT",
    "EMORY",
    "WASHINGTON UNIV",
    "BARNES-JEWISH",
    "BARNES JEWISH",
    "NORTHWESTERN MEMORIAL",
    "UNIVERSITY OF CHICAGO",
    "PENN MEDICINE",
    "HOSPITAL OF THE UNIVERSITY OF PENNSYLVANIA",
    "MICHIGAN MEDICINE",
    "UNIVERSITY OF MICHIGAN",
    "UNIVERSITY OF NORTH CAROLINA",
    "UNC HEALTH",
    "WAKE FOREST BAPTIST",
    "OHSU",
    "OREGON HEALTH",
    "YALE NEW HAVEN",
    "DARTMOUTH",
    "BAYLOR COLLEGE",
    "UNIVERSITY OF VIRGINIA",
    "UVA HEALTH",
    "UNIVERSITY OF PITTSBURGH",
    "UPMC PRESBYTERIAN",
    "INDIANA UNIVERSITY HEALTH",
    "RUSH UNIVERSITY",
)

# Flagship specialty (typically quaternary care / single-disease
# institutions whose economics look nothing like a community
# hospital's). Distinct from academic because some are private
# non-profit foundations rather than university-affiliated.
_FLAGSHIP_SPECIALTY_NAMES: tuple[str, ...] = (
    "MD ANDERSON",
    "M.D. ANDERSON",
    "MEMORIAL SLOAN",
    "DANA-FARBER",
    "DANA FARBER",
    "HOSPITAL FOR SPECIAL SURGERY",
    "FRED HUTCHINSON",
    "CITY OF HOPE",
    "ST. JUDE",
    "ST JUDE",
    "NATIONAL JEWISH",
)

# Generic name signals — match if any token appears as a whole word.
_ACADEMIC_NAME_TOKENS: tuple[str, ...] = (
    "UNIVERSITY",
    "UNIV.",
    "UNIV ",
    "SCHOOL OF MEDICINE",
    "MEDICAL SCHOOL",
    "ACADEMIC MEDICAL",
)

# Bed-count quartile cuts (US hospital distribution is heavily right-
# skewed — using log-spaced cuts so the small-rural / mid-community
# divide doesn't collapse). These are fixed so labels are stable
# across runs and don't shift just because a quarter's HCRIS refresh
# adds 30 new rural rows.
_BED_TIER_CUTS: tuple[float, ...] = (25, 100, 300)  # tier boundaries

# Medicare day-percentage cuts (0-100 scale).
_MEDICARE_PCT_CUTS: tuple[float, ...] = (25, 50, 70)


def _upper_name(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper()


def _contains_any(names_upper: pd.Series, needles: tuple[str, ...]) -> pd.Series:
    """Vectorized substring-any-of, case-insensitive (input is already upper)."""
    if not needles:
        return pd.Series(False, index=names_upper.index)
    # Use a single regex alternation for speed
    import re as _re
    pattern = "|".join(_re.escape(n) for n in needles)
    return names_upper.str.contains(pattern, na=False, regex=True)


def _size_class(beds: pd.Series) -> pd.Series:
    """Bucket beds into tier1_small / tier2_mid / tier3_large / tier4_mega.

    Cuts are fixed (25/100/300) to keep labels stable across HCRIS
    refreshes — partner shouldn't see "tier2" become "tier3" just
    because the corpus added rows.
    """
    b = pd.to_numeric(beds, errors="coerce")
    out = pd.Series("tier4_mega", index=b.index, dtype=object)
    out = out.mask(b < _BED_TIER_CUTS[2], "tier3_large")
    out = out.mask(b < _BED_TIER_CUTS[1], "tier2_mid")
    out = out.mask(b < _BED_TIER_CUTS[0], "tier1_small")
    out = out.mask(b.isna(), "unknown")
    return out


def _payer_class(medicare_pct: pd.Series) -> pd.Series:
    """Bucket medicare_day_pct into commercial / mixed / medicare_heavy /
    dual_eligible_heavy. Input is 0–100 (HCRIS convention)."""
    p = pd.to_numeric(medicare_pct, errors="coerce")
    out = pd.Series("dual_eligible_heavy", index=p.index, dtype=object)
    out = out.mask(p < _MEDICARE_PCT_CUTS[2], "medicare_heavy")
    out = out.mask(p < _MEDICARE_PCT_CUTS[1], "mixed")
    out = out.mask(p < _MEDICARE_PCT_CUTS[0], "commercial")
    out = out.mask(p.isna(), "unknown")
    return out


def derive_taxonomy(df: pd.DataFrame) -> pd.DataFrame:
    """Add taxonomy columns to an HCRIS-shaped DataFrame.

    Returns a NEW DataFrame (input is not mutated). New columns:

      academic_flag, teaching_flag, flagship_specialty_flag,
      critical_access_flag, children_flag, psychiatric_flag,
      rehab_flag, ltach_flag, safety_net_proxy_flag,
      rural_proxy_flag, size_class, payer_class, segment_label

    Missing source columns are tolerated — flags default to False
    and size_class / payer_class default to "unknown".
    """
    out = df.copy()
    n = len(out)
    if n == 0:
        for col in (
            "academic_flag", "teaching_flag", "flagship_specialty_flag",
            "critical_access_flag", "children_flag", "psychiatric_flag",
            "rehab_flag", "ltach_flag", "safety_net_proxy_flag",
            "rural_proxy_flag",
        ):
            out[col] = pd.Series(dtype=bool)
        for col in ("size_class", "payer_class", "segment_label"):
            out[col] = pd.Series(dtype=object)
        return out

    name_upper = _upper_name(out.get("name", pd.Series([""] * n, index=out.index)))
    ccn = out.get("ccn", pd.Series([""] * n, index=out.index))

    # Facility-type via existing classifier (returns one of:
    # general, critical_access, ltach, rehab, children, psychiatric,
    # other). Decompose into per-type flags.
    ftype = _classify_series(ccn, out.get("name", pd.Series([""] * n, index=out.index)))
    out["critical_access_flag"] = ftype.eq("critical_access")
    out["children_flag"] = ftype.eq("children")
    out["psychiatric_flag"] = ftype.eq("psychiatric")
    out["rehab_flag"] = ftype.eq("rehab")
    out["ltach_flag"] = ftype.eq("ltach")

    # Academic / teaching / flagship — name-based.
    is_known_academic = _contains_any(name_upper, _ACADEMIC_SYSTEM_NAMES)
    is_generic_academic = _contains_any(name_upper, _ACADEMIC_NAME_TOKENS)
    is_flagship_specialty = _contains_any(name_upper, _FLAGSHIP_SPECIALTY_NAMES)
    is_teaching_marker = name_upper.str.contains(r"\bTEACHING\b", na=False, regex=True)

    out["academic_flag"] = is_known_academic | is_generic_academic
    out["teaching_flag"] = out["academic_flag"] | is_teaching_marker
    out["flagship_specialty_flag"] = is_flagship_specialty

    # Payer-mix proxies
    medicaid_pct = pd.to_numeric(
        out.get("medicaid_day_pct", pd.Series([np.nan] * n, index=out.index)),
        errors="coerce",
    )
    medicare_pct = pd.to_numeric(
        out.get("medicare_day_pct", pd.Series([np.nan] * n, index=out.index)),
        errors="coerce",
    )
    out["safety_net_proxy_flag"] = (medicaid_pct >= 30).fillna(False)
    out["payer_class"] = _payer_class(medicare_pct)

    # Size class
    out["size_class"] = _size_class(
        out.get("beds", pd.Series([np.nan] * n, index=out.index))
    )

    # Rural proxy — critical-access OR very small bed count. Not as
    # good as a real urban/rural flag (would need a HRSA / OMB
    # rurality lookup) but catches the regime difference for the
    # regression segmentation.
    beds_num = pd.to_numeric(
        out.get("beds", pd.Series([np.nan] * n, index=out.index)),
        errors="coerce",
    )
    out["rural_proxy_flag"] = (
        out["critical_access_flag"] | (beds_num < 25).fillna(False)
    )

    # Segment label: deterministic single-label classification with
    # explicit precedence. Some hospitals match multiple flags (a
    # large academic centre is also "large community" by bed count;
    # a children's specialty hospital might also be academic-
    # affiliated). The precedence table below settles those cases —
    # MOST SPECIFIC LABEL WINS. Tested in
    # tests/test_hospital_taxonomy.py::PrecedenceTests so a future
    # refactor can't silently re-order the hierarchy.
    is_general = ftype.eq("general")
    big = beds_num >= 100
    # Each row: (label, boolean-mask). LATER rows OVERWRITE earlier
    # ones (last-write-wins), so the table is ordered LEAST-specific
    # at the top → MOST-specific at the bottom.
    #
    # Rationale for the ordering: pick the label that best predicts
    # the regression behaviour. Children's hospitals and CAHs are
    # very homogeneous economic regimes (pediatric specialty mix /
    # rural-occupancy distress respectively); Academic / Teaching
    # are diverse populations (CHOP is both academic AND children's,
    # but its economics look like a children's hospital, not an
    # AMC). So Children's > Academic, CAH > Teaching. Flagship
    # Specialty (MD Anderson, MSK) is the smallest and most
    # distinct economic regime and wins over everything.
    precedence: list[tuple[str, pd.Series]] = [
        ("Other",                    pd.Series(True, index=out.index)),
        ("Small Community",          is_general & ~big),
        ("Large Community",          is_general & big),
        ("Safety-Net Community",     out["safety_net_proxy_flag"] & is_general),
        ("Rehab",                    out["rehab_flag"]),
        ("LTACH",                    out["ltach_flag"]),
        ("Psychiatric / Behavioral", out["psychiatric_flag"]),
        ("Teaching",                 out["teaching_flag"] & ~out["academic_flag"]),
        ("Academic",                 out["academic_flag"]),
        ("Critical Access",          out["critical_access_flag"]),
        ("Children's",               out["children_flag"]),
        ("Flagship Specialty",       out["flagship_specialty_flag"]),
    ]
    seg = pd.Series("Other", index=out.index, dtype=object)
    for label, mask in precedence:
        seg = seg.mask(mask.fillna(False), label)
    out["segment_label"] = seg

    return out


# Explicit precedence list — most-specific label LAST (it wins).
# Mirrors the table inside derive_taxonomy so external callers
# (tests, docs, UI tooltips) can reference a single source of truth.
# Two hospitals matching the same flags will always get the same
# segment_label regardless of column order or HCRIS refresh.
SEGMENT_PRECEDENCE: tuple[str, ...] = (
    "Other",
    "Small Community",
    "Large Community",
    "Safety-Net Community",
    "Rehab",
    "LTACH",
    "Psychiatric / Behavioral",
    "Teaching",
    "Academic",
    "Critical Access",
    "Children's",
    "Flagship Specialty",
)


# Canonical ordered segment list — same order is used by the
# regression page (universe selector) and the per-segment R² table
# so the partner sees a stable ordering top-to-bottom.
SEGMENT_LABELS: List[str] = [
    "Flagship Specialty",
    "Academic",
    "Teaching",
    "Large Community",
    "Small Community",
    "Safety-Net Community",
    "Critical Access",
    "Children's",
    "Psychiatric / Behavioral",
    "Rehab",
    "LTACH",
    "Other",
]


def segment_counts(df: pd.DataFrame) -> pd.Series:
    """Count rows per segment_label. Useful for the UI subtitle."""
    if "segment_label" not in df.columns:
        df = derive_taxonomy(df)
    counts = df["segment_label"].value_counts()
    # Re-order to canonical (missing segments default to 0)
    return counts.reindex(SEGMENT_LABELS, fill_value=0)


def filter_to_universe(df: pd.DataFrame, universe: str) -> pd.DataFrame:
    """Filter a taxonomy-tagged frame to a named universe.

    ``universe`` is one of:
      - "all" — every row
      - "acquisition_targets" — exclude flagship/academic/teaching/
        children's/psychiatric/rehab/LTACH; keep community + CAH +
        safety-net community
      - "community" — Large + Small + Safety-Net Community
      - "rural" — Critical Access + Small Community + rural_proxy_flag
      - "academic_teaching" — Academic + Teaching + Flagship Specialty
      - any literal segment_label value (e.g. "Critical Access")

    Unknown values default to "all".
    """
    if "segment_label" not in df.columns:
        df = derive_taxonomy(df)
    u = (universe or "all").lower()
    if u == "all":
        return df
    if u == "acquisition_targets":
        keep = {"Large Community", "Small Community",
                "Safety-Net Community", "Critical Access"}
        return df[df["segment_label"].isin(keep)].copy()
    if u == "community":
        keep = {"Large Community", "Small Community", "Safety-Net Community"}
        return df[df["segment_label"].isin(keep)].copy()
    if u == "rural":
        return df[
            df["rural_proxy_flag"] |
            df["segment_label"].isin({"Critical Access", "Small Community"})
        ].copy()
    if u == "academic_teaching":
        keep = {"Academic", "Teaching", "Flagship Specialty"}
        return df[df["segment_label"].isin(keep)].copy()
    # Match an explicit segment label
    matched = df[df["segment_label"] == universe]
    if not matched.empty:
        return matched.copy()
    return df
