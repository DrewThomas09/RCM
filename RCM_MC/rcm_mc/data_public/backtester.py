"""Backtest platform predictions against realized public deal outcomes.

Compares projected IRR / MOIC from the platform's analysis runs (stored in
the main PortfolioStore runs table) against realized values in the public
deals corpus.  Matches are made on deal_name similarity and year overlap.

The backtester does NOT require a perfect identifier match — it uses fuzzy
name matching so that "LifePoint Health – KKR" in the corpus matches
"LifePoint KKR LBO" in the platform's internal deal name.

Public API:
    BacktestResult dataclass
    match_deals(store_db_path, corpus_db_path)  -> List[BacktestResult]
    summary_stats(results)                      -> dict
    print_report(results)                       -> None
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..portfolio.store import PortfolioStore


@dataclass
class BacktestResult:
    """One matched (platform run, corpus deal) pair with prediction error."""

    corpus_deal_name: str
    corpus_year: Optional[int]
    corpus_realized_moic: Optional[float]
    corpus_realized_irr: Optional[float]

    platform_deal_id: Optional[str]
    platform_deal_name: Optional[str]
    platform_run_id: Optional[int]
    platform_scenario: Optional[str]

    predicted_moic: Optional[float]    # from platform run summary_json
    predicted_irr: Optional[float]

    moic_error: Optional[float]        # predicted – realized
    irr_error: Optional[float]

    match_score: float = 0.0           # 0–1 fuzzy name similarity

    def as_dict(self) -> Dict[str, Any]:
        return {
            "corpus_deal_name": self.corpus_deal_name,
            "corpus_year": self.corpus_year,
            "corpus_realized_moic": self.corpus_realized_moic,
            "corpus_realized_irr": self.corpus_realized_irr,
            "platform_deal_id": self.platform_deal_id,
            "platform_deal_name": self.platform_deal_name,
            "platform_run_id": self.platform_run_id,
            "platform_scenario": self.platform_scenario,
            "predicted_moic": self.predicted_moic,
            "predicted_irr": self.predicted_irr,
            "moic_error": self.moic_error,
            "irr_error": self.irr_error,
            "match_score": round(self.match_score, 3),
        }


# ---------------------------------------------------------------------------
# Fuzzy name matching (stdlib only — no difflib to avoid import dependency)
# ---------------------------------------------------------------------------

def _tokenize(name: str) -> set:
    """Lower-case word tokens, stripping common stopwords."""
    stopwords = {
        "the", "a", "an", "and", "&", "of", "in", "for", "by",
        "llc", "inc", "corp", "co", "lp", "acquisition", "merger",
        "buyout", "healthcare", "health", "hospital",
    }
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    return {t for t in tokens if t not in stopwords}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 0.0
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union if union else 0.0


def _best_match(
    platform_deals: List[Tuple[str, str]],  # [(deal_id, name), ...]
    corpus_name: str,
    threshold: float = 0.20,
) -> Tuple[Optional[str], Optional[str], float]:
    """Return (deal_id, deal_name, score) for the best fuzzy match or (None, None, 0)."""
    best_id, best_name, best_score = None, None, 0.0
    for deal_id, name in platform_deals:
        score = _jaccard(name, corpus_name)
        if score > best_score:
            best_score = score
            best_id = deal_id
            best_name = name
    if best_score < threshold:
        return None, None, 0.0
    return best_id, best_name, best_score


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _load_corpus_deals(corpus_db_path: str) -> List[Any]:
    # Route through PortfolioStore (campaign target 4E, data_public
    # sweep, FINAL module): inherits busy_timeout=5000,
    # foreign_keys=ON, and Row factory — replacing the prior
    # _connect factory which set busy_timeout + row_factory by hand.
    with PortfolioStore(corpus_db_path).connect() as con:
        return con.execute(
            "SELECT * FROM public_deals "
            "WHERE realized_moic IS NOT NULL OR realized_irr IS NOT NULL"
        ).fetchall()


def _load_platform_deals(store_db_path: str) -> List[Tuple[str, str]]:
    """Return [(deal_id, name)] from the main PortfolioStore."""
    # Broad except: the recovery shape is "return empty when the
    # deals table doesn't exist (fresh store) or the read fails".
    # Used to be `except sqlite3.OperationalError`; broadening to
    # Exception lets the module fully drop the sqlite3 import.
    try:
        with PortfolioStore(store_db_path).connect() as con:
            rows = con.execute(
                "SELECT deal_id, name FROM deals WHERE archived_at IS NULL"
            ).fetchall()
        return [(r["deal_id"], r["name"]) for r in rows]
    except Exception:
        return []


def _load_latest_run(store_db_path: str, deal_id: str) -> Optional[Any]:
    """Return the most recent run row for a given deal_id."""
    try:
        with PortfolioStore(store_db_path).connect() as con:
            row = con.execute(
                "SELECT * FROM runs WHERE deal_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (deal_id,),
            ).fetchone()
        return row
    except Exception:
        return None


def _extract_predicted_returns(summary_json: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Pull predicted_moic and predicted_irr from a run's summary_json."""
    if not summary_json:
        return None, None
    try:
        s = json.loads(summary_json)
    except (json.JSONDecodeError, TypeError):
        return None, None

    # Try multiple key spellings used across platform versions
    moic = (
        s.get("moic") or s.get("gross_moic") or s.get("projected_moic")
        or s.get("pe_moic") or s.get("tvpi")
    )
    irr = (
        s.get("irr") or s.get("gross_irr") or s.get("projected_irr")
        or s.get("pe_irr") or s.get("lbo_irr")
    )
    return (float(moic) if moic is not None else None,
            float(irr)  if irr  is not None else None)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def match_deals(
    store_db_path: str,
    corpus_db_path: str,
    match_threshold: float = 0.20,
) -> List[BacktestResult]:
    """Match platform deals to corpus deals and compute prediction errors.

    For each corpus deal with a known realized outcome, attempt a fuzzy
    name match to a platform deal, then pull the platform's predicted return
    from the most recent analysis run.

    Returns one BacktestResult per corpus deal (whether matched or not).
    Unmatched corpus deals have platform_* fields set to None.
    """
    corpus_deals = _load_corpus_deals(corpus_db_path)
    platform_deals = _load_platform_deals(store_db_path)
    results: List[BacktestResult] = []

    for cd in corpus_deals:
        corpus_name = cd["deal_name"]
        corpus_year = cd["year"]
        realized_moic = cd["realized_moic"]
        realized_irr = cd["realized_irr"]

        deal_id, deal_name, score = _best_match(platform_deals, corpus_name, match_threshold)
        predicted_moic: Optional[float] = None
        predicted_irr: Optional[float] = None
        run_id: Optional[int] = None
        scenario: Optional[str] = None

        if deal_id:
            run = _load_latest_run(store_db_path, deal_id)
            if run:
                run_id = run["run_id"]
                scenario = run["scenario"]
                predicted_moic, predicted_irr = _extract_predicted_returns(run["summary_json"])

        moic_err = (
            (predicted_moic - realized_moic)
            if predicted_moic is not None and realized_moic is not None
            else None
        )
        irr_err = (
            (predicted_irr - realized_irr)
            if predicted_irr is not None and realized_irr is not None
            else None
        )

        results.append(
            BacktestResult(
                corpus_deal_name=corpus_name,
                corpus_year=corpus_year,
                corpus_realized_moic=realized_moic,
                corpus_realized_irr=realized_irr,
                platform_deal_id=deal_id,
                platform_deal_name=deal_name,
                platform_run_id=run_id,
                platform_scenario=scenario,
                predicted_moic=predicted_moic,
                predicted_irr=predicted_irr,
                moic_error=moic_err,
                irr_error=irr_err,
                match_score=score,
            )
        )

    return results


def summary_stats(results: List[BacktestResult]) -> Dict[str, Any]:
    """Aggregate error statistics across all BacktestResult instances."""
    matched = [r for r in results if r.platform_deal_id is not None]
    moic_errors = [r.moic_error for r in matched if r.moic_error is not None]
    irr_errors  = [r.irr_error  for r in matched if r.irr_error  is not None]

    def _stats(vals: List[float]) -> Dict[str, Any]:
        if not vals:
            return {"n": 0, "mean": None, "mae": None, "rmse": None}
        n = len(vals)
        mean = sum(vals) / n
        mae = sum(abs(v) for v in vals) / n
        rmse = (sum(v * v for v in vals) / n) ** 0.5
        return {"n": n, "mean": round(mean, 4), "mae": round(mae, 4), "rmse": round(rmse, 4)}

    return {
        "total_corpus_deals": len(results),
        "matched_to_platform": len(matched),
        "match_rate": round(len(matched) / len(results), 3) if results else 0.0,
        "moic_error_stats": _stats(moic_errors),
        "irr_error_stats": _stats(irr_errors),
    }


def print_report(results: List[BacktestResult]) -> None:
    """Print a human-readable backtest report to stdout."""
    stats = summary_stats(results)
    print("\n=== Backtest Report ===")
    print(f"  Corpus deals with realized outcomes: {stats['total_corpus_deals']}")
    print(f"  Matched to platform deals:           {stats['matched_to_platform']} "
          f"({stats['match_rate']:.0%})")

    ms = stats["moic_error_stats"]
    if ms["n"]:
        print(f"\n  MOIC prediction error (n={ms['n']}):")
        print(f"    Mean error : {ms['mean']:+.3f}x")
        print(f"    MAE        : {ms['mae']:.3f}x")
        print(f"    RMSE       : {ms['rmse']:.3f}x")

    es = stats["irr_error_stats"]
    if es["n"]:
        print(f"\n  IRR prediction error (n={es['n']}):")
        print(f"    Mean error : {es['mean']:+.2%}")
        print(f"    MAE        : {es['mae']:.2%}")
        print(f"    RMSE       : {es['rmse']:.2%}")

    print("\n  Per-deal matches:")
    for r in sorted(results, key=lambda x: x.match_score, reverse=True):
        if r.platform_deal_id:
            moic_s = (
                f"{r.predicted_moic:.2f}x vs {r.corpus_realized_moic:.2f}x "
                f"(err={r.moic_error:+.2f}x)"
                if r.predicted_moic is not None and r.corpus_realized_moic is not None
                else "no prediction"
            )
            print(f"    [{r.match_score:.2f}] {r.corpus_deal_name[:45]:45s} → {r.platform_deal_name} | {moic_s}")
