"""Governance scoring — CPOM/MSO transparency + board independence.

Healthcare PE deals frequently use a Friendly-PC / MSO structure
to comply with state Corporate Practice of Medicine (CPOM) rules.
LPs increasingly want this disclosed transparently; some states
(NY, NJ, MA, CA) have intensified scrutiny in 2024-2025.

Scores three governance dimensions:

  1. CPOM/MSO transparency — is the structure disclosed?
  2. Board independence — % of board independent of the sponsor
  3. Audit + compliance — annual third-party audit, compliance
     officer named, anonymous reporting channel.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GovernanceProfile:
    """Inputs the diligence team verifies during management
    presentations + data-room review."""
    has_cpom_msot_structure: bool = False     # uses Friendly-PC?
    cpom_structure_disclosed: bool = False    # disclosed in financials?
    annual_third_party_audit: bool = False
    named_compliance_officer: bool = False
    anonymous_reporting_channel: bool = False
    board_total: int = 0
    board_independent: int = 0
    related_party_transactions_disclosed: bool = False


@dataclass
class GovernanceScore:
    cpom_transparency: float       # 0-1
    board_independence: float      # 0-1
    audit_compliance: float        # 0-1
    composite: float               # 0-1, equally weighted


def score_governance(profile: GovernanceProfile) -> GovernanceScore:
    # CPOM transparency: 1.0 if no MSO structure (no need to
    # disclose); 1.0 if MSO + disclosed; 0.3 if MSO + undisclosed.
    if not profile.has_cpom_msot_structure:
        cpom = 1.0
    elif profile.cpom_structure_disclosed:
        cpom = 1.0
    else:
        cpom = 0.30

    # Board independence: % of board independent.
    if profile.board_total <= 0:
        board = 0.0
    else:
        board = profile.board_independent / profile.board_total

    # Audit + compliance: 3 yes/no checks averaged
    audit_components = [
        1.0 if profile.annual_third_party_audit else 0.0,
        1.0 if profile.named_compliance_officer else 0.0,
        1.0 if profile.anonymous_reporting_channel else 0.0,
    ]
    audit = sum(audit_components) / len(audit_components)

    composite = (cpom + board + audit) / 3.0
    return GovernanceScore(
        cpom_transparency=round(cpom, 3),
        board_independence=round(board, 3),
        audit_compliance=round(audit, 3),
        composite=round(composite, 3),
    )
