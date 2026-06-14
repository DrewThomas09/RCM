"""PACK-01 Composite diligence pack.

Chains the core CDD exhibits into one deal screen: market sizing, the growth
bridge, payer mix, customer concentration, and regulatory flags. Rolls every
flag up into a single severity-ranked list (risk first) and a pack-level
reconciliation that holds only when every constituent exhibit reconciles. The
partner view stays clean and branded; the internal view carries every section's
assumptions and reconciliations.

This is an integration layer over the registered features. No new estimator and
no LLM: it composes the existing statistical exhibits.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .concentration import customer_concentration
from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .payer_mix import payer_mix
from .pvm_bridge import pvm_bridge
from .registry import CddFeature, register
from .regulatory_flags import regulatory_flags
from .tam_sam_som import tam_sam_som

FEATURE_ID = "PACK-01"
_SEVERITY_RANK = {"risk": 0, "warn": 1, "info": 2}


class DiligencePack:
    """An ordered set of CDD exhibits for one deal, with a flag roll-up."""

    def __init__(self, deal_name: str, exhibits: List[Exhibit]):
        self.deal_name = deal_name
        self.exhibits = exhibits

    def all_flags(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for ex in self.exhibits:
            for f in ex.flags:
                out.append({"feature_id": ex.feature_id, "code": f.code,
                            "severity": f.severity, "message": f.message})
        out.sort(key=lambda r: _SEVERITY_RANK.get(r["severity"], 9))
        return out

    def reconciled_all(self) -> bool:
        return all(ex.reconciled for ex in self.exhibits)

    def render(self, internal_mode: bool = False) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "internal_mode": bool(internal_mode),
            "exhibits": [ex.render(internal_mode=internal_mode) for ex in self.exhibits],
            "flags_rollup": self.all_flags(),
            "reconciled_all": self.reconciled_all(),
        }

    def summary_exhibit(self) -> Exhibit:
        """A registry-surface roll-up Exhibit summarizing the pack."""
        flags_roll = self.all_flags()
        # Pack-level flags mirror the constituent risk flags so they surface here.
        pack_flags = [
            Flag(code=f"{r['feature_id']}:{r['code']}", severity=r["severity"],
                 message=r["message"])
            for r in flags_roll if r["severity"] == "risk"
        ]
        per_section = [
            {"label": ex.feature_id, "value": len(ex.flags)} for ex in self.exhibits
        ]
        reconciliations = [
            Reconciliation(identity="every section in the pack reconciles",
                           lhs=1.0 if self.reconciled_all() else 0.0, rhs=1.0, tolerance=1e-9),
        ]
        footnote = Footnote(
            source="Composite of registered CDD exhibits",
            vintage="per section",
            assumptions=[
                "The pack composes market sizing, growth bridge, payer mix, concentration, and regulatory flags.",
                "Flags are rolled up severity-ranked, risk first.",
            ],
        )
        return Exhibit(
            feature_id=FEATURE_ID,
            title="Diligence pack summary",
            audience="both",
            series=[
                Series(name="Flags by section", kind="bar", points=per_section),
                Series(name="Section reconciliation detail", kind="bar", internal_only=True,
                       points=[{"label": ex.feature_id, "value": 1.0 if ex.reconciled else 0.0}
                               for ex in self.exhibits]),
            ],
            footnote=footnote,
            flags=pack_flags,
            reconciliations=reconciliations,
            summary=(
                f"{self.deal_name}: {len(self.exhibits)} sections, "
                f"{sum(1 for r in flags_roll if r['severity'] == 'risk')} red flag(s)."
            ),
            meta={
                "deal_name": self.deal_name,
                "section_ids": [ex.feature_id for ex in self.exhibits],
                "flags_rollup": flags_roll,
                "reconciled_all": self.reconciled_all(),
            },
        ).validate()


def build_diligence_pack(deal: Mapping[str, Any]) -> DiligencePack:
    """Build a diligence pack from a deal's input bundle.

    ``deal`` keys (all optional; sections are included when their inputs exist):
    name, tam (kwargs), pvm (kwargs), payer_mix (args), concentration (args),
    regulatory (target dict).
    """
    name = str(deal.get("name", "Target"))
    exhibits: List[Exhibit] = []

    if "tam" in deal:
        t = deal["tam"]
        exhibits.append(tam_sam_som(t["segments"], **{k: v for k, v in t.items() if k != "segments"}))
    if "pvm" in deal:
        p = deal["pvm"]
        exhibits.append(pvm_bridge(p["rows"], period1=p["period1"], period2=p["period2"],
                                   source=p.get("source", "Deal P&L"), vintage=p.get("vintage", "")))
    if "payer_mix" in deal:
        pm = deal["payer_mix"]
        exhibits.append(payer_mix(pm["period1"], pm.get("period2"),
                                  source=pm.get("source", "HCRIS S-3"), vintage=pm.get("vintage", "")))
    if "concentration" in deal:
        c = deal["concentration"]
        exhibits.append(customer_concentration(c["accounts"],
                                               source=c.get("source", "Revenue by account"),
                                               vintage=c.get("vintage", "")))
    if "regulatory" in deal:
        exhibits.append(regulatory_flags(deal["regulatory"], vintage=deal.get("vintage", "2026")))

    if not exhibits:
        raise ValueError("build_diligence_pack needs at least one section in the deal bundle")
    return DiligencePack(name, exhibits)


def _demo() -> Exhibit:
    deal = {
        "name": "Project Cedar",
        "tam": {
            "segments": [
                {"segment": "ASC", "unit_count": 500, "price": 20.0, "penetration_rate": 0.4},
                {"segment": "HOPD", "unit_count": 1000, "price": 10.0, "penetration_rate": 0.5},
            ],
            "sales_capacity_units": 600, "win_rate": 0.5, "top_down": 18000.0,
            "source": "Demo data room", "vintage": "2026",
        },
        "payer_mix": {
            "period1": {"Medicare": 40, "Medicaid": 50, "Commercial": 10},
            "source": "Demo HCRIS", "vintage": "2026",
        },
        "concentration": {
            "accounts": [{"account": "A", "revenue": 50}, {"account": "B", "revenue": 30},
                         {"account": "C", "revenue": 20}],
        },
        "regulatory": {"payer_mix": {"Medicaid": 0.50}, "state": "CA",
                       "subsector": "home-health"},
    }
    return build_diligence_pack(deal).summary_exhibit()


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Composite diligence pack",
        audience="both",
        demo=_demo,
    )
)
