"""Payer-behavior signals that predict revenue compression.

Rule-based flags — not forecast models. Partners use these to
decide which payers to pressure-test in diligence Q&A.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class PayerBehaviorFinding:
    payer: str
    downcoding_rate: Optional[float]
    prior_auth_denial_rate: Optional[float]
    appeal_overturn_rate: Optional[float]
    severity: str                       # LOW | MEDIUM | HIGH | CRITICAL
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def detect_payer_behavior_signals(
    payer_metrics: Iterable[Dict[str, Any]],
) -> List[PayerBehaviorFinding]:
    """Return one :class:`PayerBehaviorFinding` per payer input.

    Each input dict:
        {payer, downcoding_rate, prior_auth_denial_rate,
         appeal_overturn_rate}
    """
    out: List[PayerBehaviorFinding] = []
    for row in payer_metrics:
        payer = str(row.get("payer", "UNKNOWN"))
        down = row.get("downcoding_rate")
        pa = row.get("prior_auth_denial_rate")
        overturn = row.get("appeal_overturn_rate")
        flags: List[str] = []
        sev = "LOW"
        if down is not None and down >= 0.15:
            flags.append(f"downcoding rate {down*100:.1f}%")
            sev = "HIGH"
        elif down is not None and down >= 0.08:
            flags.append(f"downcoding rate {down*100:.1f}%")
            sev = "MEDIUM"
        if pa is not None and pa >= 0.35:
            flags.append(f"prior-auth denial rate {pa*100:.1f}%")
            sev = "CRITICAL" if sev == "HIGH" else "HIGH"
        elif pa is not None and pa >= 0.20:
            flags.append(f"prior-auth denial rate {pa*100:.1f}%")
            sev = max((sev, "MEDIUM"), key=_order)
        if overturn is not None and overturn >= 0.65:
            # High overturn rate: payer is denying claims that
            # would be paid on appeal — intentional friction.
            flags.append(
                f"appeal overturn rate {overturn*100:.1f}% "
                "(payer denying payable claims)"
            )
            sev = max((sev, "HIGH"), key=_order)
        out.append(PayerBehaviorFinding(
            payer=payer,
            downcoding_rate=down,
            prior_auth_denial_rate=pa,
            appeal_overturn_rate=overturn,
            severity=sev,
            narrative="; ".join(flags) if flags
                     else "No red-flag signals detected.",
        ))
    return out


_SEV_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _order(s: str) -> int:
    return _SEV_ORDER.get(s, 0)
