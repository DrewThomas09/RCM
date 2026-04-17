"""IRS Form 990 cross-check for non-profit hospitals (~58% of US hospitals).

Non-profit 501(c)(3) hospitals file Form 990 annually. ProPublica's
Nonprofit Explorer exposes a free JSON API over that filing stack. This
module fetches a given EIN's 990 filings and cross-checks the headline
numbers against what HCRIS reports for the same fiscal year:

- Total revenue (990) vs net patient revenue (HCRIS)
- Total functional expenses (990) vs operating expenses (HCRIS)
- Net income derived from both

Any >15% variance is flagged for diligence follow-up.

CCN↔EIN mapping is currently analyst-supplied — there's no canonical CMS↔IRS
crosswalk. The analyst finds the EIN manually (30 seconds on the IRS
tax-exempt search) and passes it via ``--ein``. Auto-resolution is a
future brick.

No external dependencies — ``urllib`` from stdlib. Fetched responses are
cached on disk to avoid hammering ProPublica during repeat lookups.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────

_PROPUBLICA_URL = "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"

_CACHE_DIR_ENV = "RCM_MC_IRS990_CACHE"


def _cache_dir() -> Path:
    """Local on-disk cache for fetched 990 JSON. Configurable via env.

    Defaults to ``~/.cache/rcm_mc/irs990`` on POSIX; falls back to a temp
    directory if the home dir isn't writable.
    """
    override = os.environ.get(_CACHE_DIR_ENV)
    if override:
        return Path(override)
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        p = Path(home) / ".cache" / "rcm_mc" / "irs990"
    else:
        p = Path(tempfile.gettempdir()) / "rcm_mc_irs990"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _normalize_ein(ein: str) -> str:
    """Strip dashes/whitespace. IRS EINs are 9 digits; ProPublica wants bare digits."""
    s = re.sub(r"\D", "", str(ein or ""))
    return s


# ── Fetch ──────────────────────────────────────────────────────────────────

class IRS990FetchError(RuntimeError):
    """Raised on any failure fetching or parsing a 990 JSON payload."""


def fetch_990(ein: str, *, use_cache: bool = True, timeout: float = 15.0) -> Dict[str, Any]:
    """Fetch a non-profit's full 990 filing stack from ProPublica.

    Returns the parsed JSON payload. The shape documented at
    https://projects.propublica.org/nonprofits/api — the piece we care about
    is ``filings_with_data``, a list of per-year 990 returns.

    Cached to disk; pass ``use_cache=False`` to force a refresh.
    """
    normalized = _normalize_ein(ein)
    if len(normalized) != 9:
        raise IRS990FetchError(
            f"EIN must be 9 digits (got {len(normalized)}): {ein!r}"
        )

    cache_path = _cache_dir() / f"{normalized}.json"
    if use_cache and cache_path.is_file():
        try:
            with open(cache_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass  # fall through to live fetch

    url = _PROPUBLICA_URL.format(ein=normalized)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IRS990FetchError(f"EIN {normalized} not found on ProPublica (404)") from exc
        raise IRS990FetchError(f"HTTP {exc.code} fetching EIN {normalized}: {exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise IRS990FetchError(f"network error fetching EIN {normalized}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IRS990FetchError(f"malformed JSON from ProPublica for EIN {normalized}") from exc

    try:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # cache write is opportunistic
    return data


def filings_by_tax_year(data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """Extract ``{tax_year: filing_dict}`` from a ProPublica 990 payload.

    ProPublica returns filings under ``filings_with_data``; each has a
    ``tax_prd_yr`` field (4-digit fiscal year).
    """
    out: Dict[int, Dict[str, Any]] = {}
    for f in data.get("filings_with_data") or []:
        year = f.get("tax_prd_yr")
        if year is None:
            continue
        try:
            out[int(year)] = f
        except (TypeError, ValueError):
            continue
    return out


# ── Cross-check ────────────────────────────────────────────────────────────

# Map from our canonical HCRIS metric to the ProPublica filing field.
# ProPublica's field names change slightly across form versions; we try each.
_FIELD_MAP = {
    "total_revenue":   ("totrevenue", "totrev"),
    "total_expenses":  ("totfuncexpns", "totexpenses"),
    "net_income":      ("totrevlss", "netincfndrsng"),
}


def _first_numeric(obj: Dict[str, Any], keys: tuple) -> Optional[float]:
    for k in keys:
        v = obj.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


@dataclass
class CrossCheckReport:
    """Variance report for a single (HCRIS year, 990 year) pair."""
    hcris_fiscal_year: int
    irs_tax_year: int
    ein: str
    matched: bool                               # did we find a 990 for that year?
    hcris: Dict[str, Optional[float]] = field(default_factory=dict)
    irs:   Dict[str, Optional[float]] = field(default_factory=dict)
    variance_pct: Dict[str, Optional[float]] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hcris_fiscal_year": self.hcris_fiscal_year,
            "irs_tax_year": self.irs_tax_year,
            "ein": self.ein,
            "matched": self.matched,
            "hcris": self.hcris,
            "irs": self.irs,
            "variance_pct": self.variance_pct,
            "flags": self.flags,
        }


def _pct_variance(irs_val: Optional[float], hcris_val: Optional[float]) -> Optional[float]:
    """(irs - hcris) / hcris; None if either side missing or denominator 0."""
    if irs_val is None or hcris_val is None:
        return None
    if abs(hcris_val) < 1:
        return None
    return (irs_val - hcris_val) / hcris_val


def cross_check(
    hcris_row: Dict[str, Any],
    irs_data: Dict[str, Any],
    *,
    variance_threshold: float = 0.15,
) -> CrossCheckReport:
    """Compare a single HCRIS row against the matched-year 990 filing.

    Matching: we find the 990 for the same fiscal year as the HCRIS row.
    If no exact match, we fall back to the nearest year and record the gap
    in ``flags``.

    ``variance_threshold`` — fractional variance above which a flag is raised.
    """
    ein = _normalize_ein(str(irs_data.get("organization", {}).get("ein") or ""))
    hcris_year = int(hcris_row.get("fiscal_year") or 0)

    filings = filings_by_tax_year(irs_data)
    if not filings:
        return CrossCheckReport(
            hcris_fiscal_year=hcris_year,
            irs_tax_year=0,
            ein=ein,
            matched=False,
            flags=["No 990 filings parseable from ProPublica payload"],
        )

    # Prefer exact tax_year match; fall back to nearest
    if hcris_year in filings:
        matched_year = hcris_year
        matched_filing = filings[hcris_year]
        year_gap = 0
    else:
        matched_year = min(filings.keys(), key=lambda y: abs(y - hcris_year))
        matched_filing = filings[matched_year]
        year_gap = abs(matched_year - hcris_year)

    report = CrossCheckReport(
        hcris_fiscal_year=hcris_year,
        irs_tax_year=matched_year,
        ein=ein,
        matched=True,
    )

    if year_gap > 0:
        report.flags.append(
            f"No FY{hcris_year} 990 on file; falling back to FY{matched_year} "
            f"({year_gap}-year gap)"
        )

    # Pull values from each side
    hcris_vals = {
        "total_revenue":  hcris_row.get("net_patient_revenue"),
        "total_expenses": hcris_row.get("operating_expenses"),
        "net_income":     hcris_row.get("net_income"),
    }
    irs_vals = {
        metric: _first_numeric(matched_filing, keys)
        for metric, keys in _FIELD_MAP.items()
    }
    report.hcris = {k: (float(v) if v is not None else None) for k, v in hcris_vals.items()}
    report.irs = irs_vals

    # Variance + flags
    for metric in hcris_vals:
        v = _pct_variance(irs_vals.get(metric), hcris_vals.get(metric))
        report.variance_pct[metric] = v
        if v is not None and abs(v) >= variance_threshold:
            direction = "higher" if v > 0 else "lower"
            report.flags.append(
                f"{metric}: 990 is {abs(v)*100:.0f}% {direction} than HCRIS "
                f"({irs_vals[metric]:,.0f} vs {hcris_vals[metric]:,.0f})"
            )

    return report


def cross_check_ccn(
    ccn: str,
    ein: str,
    year: Optional[int] = None,
    *,
    fetch_fn=None,
) -> CrossCheckReport:
    """Convenience: resolve CCN → HCRIS row, fetch 990 for EIN, cross-check.

    ``fetch_fn`` is injected for tests. When ``None`` we dispatch to the
    module-level :func:`fetch_990` (lookup is done at call time so patches
    on the module attribute take effect).
    """
    from .hcris import lookup_by_ccn

    row = lookup_by_ccn(ccn, year=year)
    if row is None:
        raise ValueError(
            f"CCN {ccn!r} not found in HCRIS"
            + (f" for fiscal year {year}" if year else "")
        )
    fetcher = fetch_fn if fetch_fn is not None else fetch_990
    irs_data = fetcher(ein)
    return cross_check(row, irs_data)


def tag_990_filing(registry, filing: Dict[str, Any], *,
                   ein: str, metric_map: Optional[Dict[str, str]] = None,
                   ) -> None:
    """Provenance helper: record numeric fields from one 990 filing
    dict as IRS990 DataPoints on ``registry``.

    ``filing`` is one element of ``filings_with_data`` returned by
    :func:`fetch_990`. ``metric_map`` is an optional
    ``{filing_key: metric_name}`` so you can rename the 990's
    ``totrevenue`` → ``total_revenue``.

    Never raises — a bad filing shape silently skips.
    """
    try:
        tax_year = int(filing.get("tax_prd_yr") or filing.get("tax_yr") or 0)
    except Exception:  # noqa: BLE001
        tax_year = 0
    if not tax_year:
        return
    mapping = metric_map or {}
    for key, val in filing.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        metric_name = mapping.get(key, key)
        try:
            registry.record_irs990(
                value=v, metric_name=metric_name,
                ein=ein, tax_year=tax_year,
            )
        except Exception:  # noqa: BLE001
            continue
