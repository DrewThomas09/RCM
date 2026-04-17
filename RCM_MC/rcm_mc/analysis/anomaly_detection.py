"""
Step 78: Automated anomaly detection on calibration inputs.

Flags unusual values that may indicate data quality issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..infra.logger import logger


@dataclass
class AnomalyReport:
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, payer: str, metric: str, value: float, threshold: float, direction: str) -> None:
        self.warnings.append({
            "payer": payer,
            "metric": metric,
            "value": round(value, 4),
            "threshold": round(threshold, 4),
            "direction": direction,
        })

    def to_list(self) -> List[Dict[str, Any]]:
        return self.warnings

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def detect_anomalies(cfg: Dict[str, Any], min_observations: int = 30) -> AnomalyReport:
    """Check calibrated config for suspicious values."""
    report = AnomalyReport()

    for payer, pconf in cfg.get("payers", {}).items():
        if not isinstance(pconf, dict):
            continue

        if pconf.get("include_denials", False):
            d = pconf.get("denials", {})
            idr_mean = float(d.get("idr", {}).get("mean", 0))
            if idr_mean > 0.25:
                report.add(payer, "IDR", idr_mean, 0.25, "unusually high")
                logger.warning("Payer %s: IDR %.1f%% is unusually high (>25%%)", payer, idr_mean * 100)

            fwr_mean = float(d.get("fwr", {}).get("mean", 0))
            if fwr_mean > 0.50:
                report.add(payer, "FWR", fwr_mean, 0.50, "unusually high")
                logger.warning("Payer %s: FWR %.1f%% is unusually high (>50%%)", payer, fwr_mean * 100)

        dar_mean = float(pconf.get("dar_clean_days", {}).get("mean", 0))
        if dar_mean > 90:
            report.add(payer, "DAR", dar_mean, 90, "unusually high")
            logger.warning("Payer %s: DAR %.0f days is unusually high (>90)", payer, dar_mean)

        rs = float(pconf.get("revenue_share", 0))
        if rs > 0 and rs < 0.02:
            report.add(payer, "revenue_share", rs, 0.02, "very small share")

    return report
