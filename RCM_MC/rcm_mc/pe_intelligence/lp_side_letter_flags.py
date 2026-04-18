"""LP side-letter conformance checks.

LPs negotiate side letters with sponsors: concentration limits,
excluded sectors, reporting frequency, conflict disclosures, ESG
covenants. A deal that breaches a side letter requires explicit LPAC
waiver — and burns credibility.

This module encodes common side-letter restrictions and tests a
candidate deal against them. It is a lightweight conformance check,
not a full compliance engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SideLetterRule:
    id: str
    description: str
    rule_type: str            # "concentration" | "sector_excl" | "geography" | "esg" | "disclosure"
    lp_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "rule_type": self.rule_type,
            "lp_ids": list(self.lp_ids),
        }


@dataclass
class SideLetterSet:
    sector_exclusions: List[str] = field(default_factory=list)
    state_exclusions: List[str] = field(default_factory=list)
    max_single_deal_pct_of_fund: Optional[float] = None
    max_sector_pct_of_fund: Optional[float] = None
    max_govt_payer_pct: Optional[float] = None     # e.g. exclude deals > 70% govt
    no_tobacco: bool = False
    no_short_term_detention: bool = False
    no_fossil_fuels: bool = False
    reporting_monthly_required: bool = False
    rules: List[SideLetterRule] = field(default_factory=list)


@dataclass
class ConformanceFinding:
    rule_id: str
    passed: bool
    severity: str              # "info" | "warning" | "breach"
    detail: str
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
            "remediation": self.remediation,
        }


# ── Checks ──────────────────────────────────────────────────────────

def _check_sector_exclusion(
    deal_sector: Optional[str],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if not deal_sector or not sls.sector_exclusions:
        return None
    if deal_sector.lower() in [s.lower() for s in sls.sector_exclusions]:
        return ConformanceFinding(
            rule_id="sector_exclusion",
            passed=False, severity="breach",
            detail=f"Sector '{deal_sector}' is excluded by LP side letter.",
            remediation=("LPAC waiver required before proceeding. "
                         "If waiver denied, decline the deal."),
        )
    return ConformanceFinding(
        rule_id="sector_exclusion",
        passed=True, severity="info",
        detail=f"Sector '{deal_sector}' is not on the exclusion list.",
    )


def _check_state_exclusion(
    deal_state: Optional[str],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if not deal_state or not sls.state_exclusions:
        return None
    if deal_state.upper() in [s.upper() for s in sls.state_exclusions]:
        return ConformanceFinding(
            rule_id="state_exclusion",
            passed=False, severity="breach",
            detail=f"Deal located in excluded state '{deal_state}'.",
            remediation="LPAC waiver required.",
        )
    return None


def _check_deal_concentration(
    equity_check: Optional[float],
    fund_size: Optional[float],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if (equity_check is None or fund_size is None or fund_size <= 0
            or sls.max_single_deal_pct_of_fund is None):
        return None
    pct = equity_check / fund_size
    if pct > sls.max_single_deal_pct_of_fund:
        return ConformanceFinding(
            rule_id="deal_concentration",
            passed=False, severity="breach",
            detail=(f"Equity check {pct*100:.1f}% of fund exceeds LP cap "
                    f"of {sls.max_single_deal_pct_of_fund*100:.0f}%."),
            remediation="Co-invest syndication or reduce equity check.",
        )
    return ConformanceFinding(
        rule_id="deal_concentration",
        passed=True, severity="info",
        detail=f"Equity check {pct*100:.1f}% is within LP concentration limit.",
    )


def _check_govt_payer_cap(
    payer_mix: Optional[Dict[str, float]],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if not payer_mix or sls.max_govt_payer_pct is None:
        return None
    norm = {k.lower(): float(v) for k, v in payer_mix.items()}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    govt = norm.get("medicare", 0.0) + norm.get("medicaid", 0.0)
    if govt > sls.max_govt_payer_pct:
        return ConformanceFinding(
            rule_id="govt_payer_cap",
            passed=False, severity="warning",
            detail=(f"Government payer mix {govt*100:.0f}% exceeds LP "
                    f"comfort threshold of {sls.max_govt_payer_pct*100:.0f}%."),
            remediation="Document why this deal warrants an exception.",
        )
    return None


def _check_tobacco(
    deal_notes: Optional[str],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if not sls.no_tobacco or not deal_notes:
        return None
    if "tobacco" in deal_notes.lower():
        return ConformanceFinding(
            rule_id="no_tobacco",
            passed=False, severity="breach",
            detail="Deal notes mention tobacco exposure; LP exclusion triggered.",
            remediation="Confirm exposure scale; if material, decline.",
        )
    return None


def _check_short_term_detention(
    deal_notes: Optional[str],
    sls: SideLetterSet,
) -> Optional[ConformanceFinding]:
    if not sls.no_short_term_detention or not deal_notes:
        return None
    if any(k in deal_notes.lower() for k in ("detention", "incarceration", "jail")):
        return ConformanceFinding(
            rule_id="no_short_term_detention",
            passed=False, severity="breach",
            detail="Deal references short-term detention / incarceration services.",
            remediation="ESG screen excludes this category — decline.",
        )
    return None


# ── Orchestrator ────────────────────────────────────────────────────

def check_side_letters(
    *,
    sls: SideLetterSet,
    deal_sector: Optional[str] = None,
    deal_state: Optional[str] = None,
    equity_check: Optional[float] = None,
    fund_size: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
    deal_notes: Optional[str] = None,
) -> List[ConformanceFinding]:
    """Run every applicable conformance check; return findings."""
    findings: List[ConformanceFinding] = []
    for fn in (
        lambda: _check_sector_exclusion(deal_sector, sls),
        lambda: _check_state_exclusion(deal_state, sls),
        lambda: _check_deal_concentration(equity_check, fund_size, sls),
        lambda: _check_govt_payer_cap(payer_mix, sls),
        lambda: _check_tobacco(deal_notes, sls),
        lambda: _check_short_term_detention(deal_notes, sls),
    ):
        try:
            result = fn()
        except Exception:
            result = None
        if result is not None:
            findings.append(result)
    return findings


def has_breach(findings: List[ConformanceFinding]) -> bool:
    return any(f.severity == "breach" for f in findings)
