"""run_full_diligence — top-level synthesis entry point."""
from __future__ import annotations

from typing import Any

from .dossier import DiligenceDossier, SynthesisResult


def _safe_run(label: str, fn, result: SynthesisResult,
              missing_msg: str) -> Any:
    """Try to run a packet section; collect failures into
    missing_inputs so the result documents what was skipped."""
    try:
        out = fn()
    except Exception as exc:  # noqa: BLE001
        result.missing_inputs.append(
            f"{label}: {type(exc).__name__}: {exc}")
        return None
    if out is None:
        result.missing_inputs.append(missing_msg)
        return None
    result.sections_run.append(label)
    return out


def run_full_diligence(dossier: DiligenceDossier) -> SynthesisResult:
    """Run every applicable packet on the dossier.

    Each packet runs only if its required inputs are present;
    skipped packets are recorded in ``missing_inputs`` so the
    partner sees what's still needed for a complete view.
    """
    result = SynthesisResult(deal_name=dossier.deal_name)

    # ── 1. PayerNegotiationSimulator ─────────────────────────
    def _payer_neg():
        if not (dossier.pricing_store
                and dossier.target_npis
                and dossier.target_codes):
            return None
        from ..negotiation import (
            compute_outside_options, repeated_game_rate,
        )
        out = []
        for npi in dossier.target_npis[:5]:
            for code in dossier.target_codes[:5]:
                oo = compute_outside_options(
                    dossier.pricing_store, npi, code)
                if oo.rate_count == 0:
                    continue
                state = repeated_game_rate(
                    oo, payer_name="Composite",
                    payer_leverage=0.5,
                )
                out.append({
                    "npi": npi, "code": code,
                    "rate_count": oo.rate_count,
                    "p25": oo.p25, "p75": oo.p75,
                    "modeled_rate": state.negotiated_rate,
                })
        return out or None

    result.payer_negotiation = _safe_run(
        "payer_negotiation", _payer_neg, result,
        "payer_negotiation: needs pricing_store + target_npis + target_codes",
    )

    # ── 2. VBC Cohort LTV (Bridge v3) ────────────────────────
    def _ltv():
        if not (dossier.cohort and dossier.contract):
            return None
        from ..vbc import compute_cohort_ltv
        return compute_cohort_ltv(
            dossier.cohort, dossier.contract,
            horizon_years=5, starting_payment_year=2026,
        )
    result.cohort_ltv = _safe_run(
        "cohort_ltv", _ltv, result,
        "cohort_ltv: needs cohort + contract",
    )

    # ── 3. ReferralNetworkPacket ─────────────────────────────
    def _referral():
        if not (dossier.referral_graph and dossier.platform_orgs):
            return None
        from ..referral import compute_leakage, compute_key_person_risk
        return {
            "leakage": compute_leakage(
                dossier.referral_graph, dossier.platform_orgs),
            "key_person_risk": compute_key_person_risk(
                dossier.referral_graph, dossier.platform_orgs),
        }
    result.referral_leakage = _safe_run(
        "referral_leakage", _referral, result,
        "referral_leakage: needs referral_graph + platform_orgs",
    )

    # ── 4. RegulatoryRiskPacket ──────────────────────────────
    def _regulatory():
        if not dossier.regulatory_corpus:
            return None
        from ..regulatory import (
            TargetProfile, score_target_exposure,
            jurisdictional_heatmap,
        )
        target = TargetProfile(
            target_name=dossier.deal_name,
            sector=dossier.sector,
            states=dossier.states,
            ebitda_mm=dossier.ebitda_mm,
        )
        return {
            "exposure": score_target_exposure(
                target, dossier.regulatory_corpus),
            "heatmap": jurisdictional_heatmap(
                target, dossier.regulatory_corpus),
        }
    result.regulatory_exposure = _safe_run(
        "regulatory_exposure", _regulatory, result,
        "regulatory_exposure: needs regulatory_corpus",
    )

    # ── 5. QoE-AutoFlagger ───────────────────────────────────
    def _qoe():
        if not dossier.financial_panel:
            return None
        from ..qoe import run_qoe_flagger
        return run_qoe_flagger(dossier.financial_panel)
    result.qoe_result = _safe_run(
        "qoe", _qoe, result,
        "qoe: needs financial_panel",
    )

    # ── 6. BuyAndBuildOptimizer ──────────────────────────────
    def _bb():
        if not (dossier.platform and dossier.add_on_candidates):
            return None
        from ..buyandbuild import optimize_sequence
        return optimize_sequence(
            dossier.platform, dossier.add_on_candidates)
    result.buyandbuild_optimal = _safe_run(
        "buyandbuild", _bb, result,
        "buyandbuild: needs platform + add_on_candidates",
    )

    # ── 7. ExitReadinessPacket ───────────────────────────────
    def _exit():
        if not dossier.exit_target:
            return None
        from ..exit_readiness import run_exit_readiness_packet
        return run_exit_readiness_packet(dossier.exit_target)
    result.exit_readiness = _safe_run(
        "exit_readiness", _exit, result,
        "exit_readiness: needs exit_target",
    )

    # ── 8. VBC-ContractValuator ──────────────────────────────
    def _vbc_contracts():
        if not (dossier.cohort and dossier.program_ids):
            return None
        from ..vbc_contracts import (
            choose_optimal_track, StochasticInputs,
        )
        return choose_optimal_track(
            dossier.cohort,
            program_ids=dossier.program_ids,
            inputs=StochasticInputs(n_simulations=80, seed=7),
        )
    result.vbc_track_choice = _safe_run(
        "vbc_track_choice", _vbc_contracts, result,
        "vbc_track_choice: needs cohort + program_ids",
    )

    # ── 9. ESG-HealthcarePacket ──────────────────────────────
    def _esg():
        if not (dossier.facilities or dossier.workforce
                or dossier.governance_profile):
            return None
        from ..esg import (
            compute_dei_metrics, score_governance,
            compute_edci_scorecard, render_lp_disclosure,
        )
        dei = (compute_dei_metrics(dossier.workforce)
               if dossier.workforce else None)
        gov = (score_governance(dossier.governance_profile)
               if dossier.governance_profile else None)
        sc = compute_edci_scorecard(
            dossier.deal_name,
            facilities=dossier.facilities or None,
            dei=dei, governance=gov,
            issb_attested=dossier.issb_attested,
            cybersecurity_attested=dossier.cybersecurity_attested,
        )
        result.esg_disclosure_md = render_lp_disclosure(sc)
        return sc
    result.esg_scorecard = _safe_run(
        "esg_scorecard", _esg, result,
        "esg_scorecard: needs at least one of facilities, "
        "workforce, governance_profile",
    )

    # ── 10. DealComparablesEngine ────────────────────────────
    def _comparables():
        if not (dossier.deal_corpus and dossier.target_deal_profile):
            return None
        from ..comparables import run_comparables_engine
        return run_comparables_engine(
            dossier.deal_corpus,
            dossier.target_deal_profile,
            method=dossier.comparables_method,
            k_matches=dossier.comparables_k,
        )
    result.comparables = _safe_run(
        "comparables", _comparables, result,
        "comparables: needs deal_corpus + target_deal_profile",
    )

    # ── 11. IRR-Attribution Packet ───────────────────────────
    def _irr():
        if not dossier.realized_cashflows:
            return None
        from ..irr_attribution import (
            decompose_value_creation, render_lp_narrative,
        )
        attr = decompose_value_creation(dossier.realized_cashflows)
        result.irr_attribution_lp_md = render_lp_narrative(attr)
        return attr
    result.irr_attribution = _safe_run(
        "irr_attribution", _irr, result,
        "irr_attribution: needs realized_cashflows",
    )

    # ── 12. MonteCarloPacket v3 — joint tail healthcare shock ──
    def _joint_tail():
        if not dossier.run_joint_tail_shock:
            return None
        from ..montecarlo_v3 import joint_tail_healthcare_shock
        return joint_tail_healthcare_shock(
            n_samples=dossier.joint_tail_n_samples, seed=42,
        )
    result.joint_tail_shock = _safe_run(
        "joint_tail_shock", _joint_tail, result,
        "joint_tail_shock: needs run_joint_tail_shock=True",
    )

    # ── 13. SectorThemeDetector ───────────────────────────────
    def _themes():
        if not dossier.theme_documents:
            return None
        from ..sector_themes import (
            score_deal_against_themes, emerging_theme_heatmap,
            build_target_universe,
        )
        # Score each document; collect top theme matches
        matches_by_doc = {}
        for doc in dossier.theme_documents:
            matches_by_doc[doc.doc_id] = score_deal_against_themes(
                doc.text)
        result.theme_heatmap = emerging_theme_heatmap(
            dossier.theme_documents,
            granularity=dossier.theme_heatmap_granularity,
        )
        if dossier.thesis_theme_ids:
            result.target_universe = build_target_universe(
                dossier.theme_documents,
                thesis_theme_ids=dossier.thesis_theme_ids,
            )
        return matches_by_doc
    result.sector_themes = _safe_run(
        "sector_themes", _themes, result,
        "sector_themes: needs theme_documents",
    )

    return result
