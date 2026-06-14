"""BOLSTER-02 Isolation-forest anomaly detection (hardened).

Pins the anomaly-detection spec: sklearn.ensemble.IsolationForest with an
explicit contamination, n_estimators at least 100, and a pinned random_state.
Use cases span billing and claims anomalies: coding outliers, outlier providers,
and QoE red flags. Each anomaly carries a score plus a human-readable reason,
the feature whose standardized deviation drove the flag. The reason is computed
statistically (a z-score), never via an LLM.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import numpy as np
from sklearn.ensemble import IsolationForest

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "BOLSTER-02"


def detect_anomalies(
    records: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
    *,
    id_key: str = "id",
    contamination: float = 0.1,
    n_estimators: int = 200,
    random_state: int = 42,
    source: str = "Billing or claims feature table",
    vintage: str = "",
    audience: str = "internal",
) -> Exhibit:
    """Flag anomalies with IsolationForest and attach a driving-feature reason.

    ``records``: rows carrying ``id_key`` and each name in ``feature_names``.
    """
    if not records:
        raise ValueError("detect_anomalies requires at least one record")
    if n_estimators < 100:
        raise ValueError("n_estimators must be at least 100")
    feature_names = list(feature_names)

    X = np.array([[float(r[f]) for f in feature_names] for r in records], dtype=float)
    ids = [r.get(id_key, i) for i, r in enumerate(records)]

    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds_safe = np.where(stds > 0, stds, 1.0)

    iso = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
    )
    preds = iso.fit_predict(X)  # -1 anomaly, 1 normal
    scores = iso.decision_function(X)  # lower is more anomalous

    rows: List[Dict[str, Any]] = []
    anomalies: List[Any] = []
    for i, rid in enumerate(ids):
        is_anom = preds[i] == -1
        z = (X[i] - means) / stds_safe
        top_idx = int(np.argmax(np.abs(z)))
        direction = "above" if z[top_idx] >= 0 else "below"
        reason = (
            f"{feature_names[top_idx]} is {abs(z[top_idx]):.1f} sigma {direction} the mean"
        )
        row = {
            "id": rid,
            "is_anomaly": bool(is_anom),
            "score": float(scores[i]),
            "top_feature": feature_names[top_idx],
            "top_z": float(z[top_idx]),
            "reason": reason if is_anom else "",
        }
        rows.append(row)
        if is_anom:
            anomalies.append(rid)

    n_flagged = len(anomalies)
    flags: List[Flag] = []
    if n_flagged:
        flags.append(Flag(
            code="anomalies_detected",
            severity="warn",
            message=f"{n_flagged} record(s) flagged as anomalies.",
            source=source,
        ))

    # Reconcile: flagged count equals the number of -1 predictions.
    reconciliations = [
        Reconciliation(identity="flagged count equals isolation-forest -1 predictions",
                       lhs=n_flagged, rhs=int(np.sum(preds == -1)), tolerance=1e-9),
    ]

    series = [
        Series(name="Anomaly flags", kind="bar", points=[
            {"label": str(r["id"]), "value": 1.0 if r["is_anomaly"] else 0.0,
             "reason": r["reason"]} for r in rows if r["is_anomaly"]
        ]),
        Series(name="Anomaly scores", kind="bar", internal_only=True, points=[
            {"label": str(r["id"]), "value": r["score"], "top_feature": r["top_feature"]}
            for r in rows
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            f"IsolationForest, contamination {contamination}, {n_estimators} trees, random_state {random_state}.",
            "Reasons are the top standardized feature deviation (z-score), computed statistically.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Anomaly detection",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{n_flagged} of {len(records)} records flagged as anomalies.",
        meta={
            "rows": rows,
            "anomaly_ids": anomalies,
            "n_flagged": n_flagged,
            "contamination": contamination,
            "n_estimators": n_estimators,
            "random_state": random_state,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    rng = np.random.default_rng(42)
    records = []
    for i in range(40):
        records.append({"id": f"prov{i}", "denial_rate": float(rng.normal(0.1, 0.02)),
                        "avg_charge": float(rng.normal(100, 10))})
    # Planted outlier providers.
    records.append({"id": "outlier_denial", "denial_rate": 0.9, "avg_charge": 100.0})
    records.append({"id": "outlier_charge", "denial_rate": 0.1, "avg_charge": 1000.0})
    return detect_anomalies(records, ["denial_rate", "avg_charge"],
                            contamination=0.1, source="Demo claims", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Isolation-forest anomaly detection (hardened)",
        audience="internal",
        demo=_demo,
    )
)
