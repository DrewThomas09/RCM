"""CMS TEAM (Transforming Episode Accountability Model) calculator.

Per the CMS TEAM final rule (November 2024), 741 hospitals in 188
CBSAs are mandatorily enrolled starting 2026-01-01. Bundled
episodes: LEJR, SHFFT, spinal fusion, CABG, major bowel.

This module computes the projected P&L impact for an IPPS hospital
under Tracks 1/2/3. Inputs:

    cbsa_code           — target's CBSA (drives membership check)
    track               — 'track_1' | 'track_2' | 'track_3'
    annual_case_volume  — {episode: n_cases} e.g. {'LEJR': 400}
    per_case_variance_usd — optional {episode: delta_vs_benchmark}
                             If absent we use the CMS baseline
                             projection ($1,350 loss/case).

Banding:
    RED     — expected annual loss > $1M under current track
    YELLOW  — expected loss $250k–$1M
    GREEN   — expected gain OR loss < $250k
    UNKNOWN — CBSA not on the mandatory list
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .packet import RegulatoryBand, TEAMExposure, load_yaml


def _track_bounds(cfg: Dict[str, Any]) -> tuple[float, float]:
    up = float(cfg.get("upside_cap_pct", 0) or 0)
    down = float(cfg.get("downside_cap_pct", 0) or 0)
    return up, down


def compute_team_impact(
    *,
    cbsa_code: str,
    track: str = "track_2",
    annual_case_volume: Optional[Dict[str, int]] = None,
    per_case_variance_usd: Optional[Dict[str, float]] = None,
    hospital_performance_percentile: Optional[float] = None,
) -> TEAMExposure:
    """Project TEAM P&L impact for a single hospital.

    When ``per_case_variance_usd`` is absent, we use the CMS
    baseline projection ($1,350 loss/case) multiplied by volume.
    When it's present, we cap the per-case impact at the track's
    upside/downside limits (expressed as a % of baseline
    episode cost).

    ``hospital_performance_percentile``: optional [0, 1] — 0.0
    means 0th percentile (worst performer), 1.0 means 100th.
    Used only when per_case_variance_usd is absent, to scale the
    baseline loss projection (bad performers lose more).
    """
    content = load_yaml("team_cbsa_list")
    cbsas = {
        str(c["cbsa_code"]): c
        for c in content.get("mandatory_cbsas") or ()
    }
    tracks = content.get("tracks") or {}
    bundles = content.get("bundle_episodes") or {}
    baseline_proj = content.get("baseline_loss_projection") or {}

    cbsa_entry = cbsas.get(str(cbsa_code).strip())
    in_mandatory = cbsa_entry is not None

    if track not in tracks:
        raise ValueError(
            f"unknown track {track!r}; "
            f"expected one of {sorted(tracks.keys())}"
        )
    track_cfg = tracks[track]

    if not in_mandatory:
        return TEAMExposure(
            in_mandatory_cbsa=False,
            cbsa_code=cbsa_code,
            cbsa_name=None,
            track=track,
            annual_pnl_impact_usd=0.0,
            expected_loss_per_case_usd=0.0,
            mandatory_episodes=list(bundles.keys()),
            band=RegulatoryBand.UNKNOWN,
        )

    volume = annual_case_volume or {}
    total_cases = sum(int(v) for v in volume.values())

    if per_case_variance_usd:
        total_pnl = 0.0
        for ep, n_cases in volume.items():
            variance = float(per_case_variance_usd.get(ep, 0) or 0)
            episode_cfg = bundles.get(ep) or {}
            baseline_cost = float(
                episode_cfg.get("baseline_avg_episode_cost_usd", 0) or 0
            )
            # Cap per-case impact by the track's upside/downside.
            upside_cap, downside_cap = _track_bounds(track_cfg)
            cap_up = baseline_cost * upside_cap
            cap_down = -baseline_cost * downside_cap
            capped = max(min(variance, cap_up), cap_down)
            total_pnl += capped * int(n_cases)
        expected_loss_per_case = (
            -total_pnl / total_cases if total_cases > 0 else 0.0
        )
    else:
        # Use CMS baseline projection.
        base_loss = float(
            baseline_proj.get("avg_loss_per_case_usd", 1350)
        )
        # Scale by performance percentile when available.
        # 100th percentile → small LOSS (top performer near zero);
        # 0th → base_loss * 2 (worst performer). Centered so 50th
        # ≈ baseline.
        perf = hospital_performance_percentile
        if perf is not None:
            perf = max(0.0, min(1.0, float(perf)))
            scalar = 2.0 - 2.0 * perf           # [2..0]
            expected_loss_per_case = base_loss * scalar
        else:
            expected_loss_per_case = base_loss
        # Losses are subject to downside cap; cap per-case loss by
        # the WORST case episode's cap.
        _, downside_cap = _track_bounds(track_cfg)
        worst_cap = 0.0
        for ep in volume.keys():
            episode_cfg = bundles.get(ep) or {}
            baseline_cost = float(
                episode_cfg.get("baseline_avg_episode_cost_usd", 0) or 0
            )
            worst_cap = max(worst_cap, baseline_cost * downside_cap)
        if worst_cap > 0:
            expected_loss_per_case = min(
                expected_loss_per_case, worst_cap,
            )
        total_pnl = -expected_loss_per_case * total_cases

    # Banding on annual P&L impact (negative = loss).
    annual_loss = -total_pnl
    if annual_loss > 1_000_000:
        band = RegulatoryBand.RED
    elif annual_loss > 250_000:
        band = RegulatoryBand.YELLOW
    else:
        band = RegulatoryBand.GREEN

    return TEAMExposure(
        in_mandatory_cbsa=True,
        cbsa_code=str(cbsa_code),
        cbsa_name=str(cbsa_entry.get("name")) if cbsa_entry else None,
        track=track,
        annual_pnl_impact_usd=float(total_pnl),
        expected_loss_per_case_usd=float(expected_loss_per_case),
        mandatory_episodes=list(volume.keys()) or list(bundles.keys()),
        band=band,
    )


def is_cbsa_mandatory(cbsa_code: str) -> bool:
    """Lightweight membership check. Returns True when the CBSA is
    on the seeded mandatory list."""
    content = load_yaml("team_cbsa_list")
    codes = {
        str(c["cbsa_code"])
        for c in content.get("mandatory_cbsas") or ()
    }
    return str(cbsa_code).strip() in codes
