"""Tests for the Phase-3 feature leakage audit.

These pin every per-(feature, target) verdict the regression page
will key off so a future refactor can't silently downgrade a known-
leaky combination to SAFE.

Headline cases to nail:
  - target = net_patient_revenue → revenue_per_bed / operating_margin
    / net_to_gross_ratio / revenue_per_day / net_income all LEAK
    (they're all derivatives of net_patient_revenue).
  - target = operating_margin → net_patient_revenue / operating_expenses
    / net_income all LEAK (target is derived from them).
  - target = occupancy_rate → only total_patient_days and
    bed_days_available LEAK (target's two formula inputs); other
    features are SAFE.
  - Unknown feature → UNKNOWN verdict, never silently SAFE.
"""
import unittest

from rcm_mc.finance.leakage import (
    PROVENANCE,
    FeatureProvenance,
    LeakageVerdict,
    atomic_inputs,
    audit_features,
    classify_feature_for_target,
    forecasting_safe_features,
)


class NetPatientRevenueTargetTests(unittest.TestCase):
    """When the partner picks NPR as the target, every NPR-derivative
    must be flagged LEAKS."""

    target = "net_patient_revenue"

    def _verdict(self, feature):
        return classify_feature_for_target(feature, self.target)

    def test_revenue_per_bed_leaks(self):
        v = self._verdict("revenue_per_bed")
        self.assertEqual(v.verdict, "LEAKS")
        self.assertEqual(v.severity, "critical")
        # Reason must call out the relationship
        self.assertIn("net_patient_revenue", v.reason.lower())

    def test_operating_margin_leaks(self):
        self.assertEqual(self._verdict("operating_margin").verdict, "LEAKS")

    def test_net_to_gross_ratio_leaks(self):
        self.assertEqual(self._verdict("net_to_gross_ratio").verdict, "LEAKS")

    def test_revenue_per_day_leaks(self):
        self.assertEqual(self._verdict("revenue_per_day").verdict, "LEAKS")

    def test_net_income_leaks(self):
        # net_income is a raw HCRIS column but its formula
        # (npr - opex + non-op) makes it derived for leakage
        # purposes. Important because partners think of it as raw
        # and would accidentally include it.
        v = self._verdict("net_income")
        self.assertEqual(v.verdict, "LEAKS")

    def test_beds_safe(self):
        # Beds is not derived from NPR and NPR is not derived from
        # beds — fitting NPR ~ beds is a real (if naïve) regression.
        v = self._verdict("beds")
        self.assertEqual(v.verdict, "SAFE")
        self.assertEqual(v.severity, "ok")

    def test_medicare_day_pct_safe(self):
        self.assertEqual(self._verdict("medicare_day_pct").verdict, "SAFE")

    def test_occupancy_rate_safe(self):
        # occupancy_rate is total_patient_days / bed_days_available
        # — no NPR in its formula. Safe to use as a NPR predictor.
        self.assertEqual(self._verdict("occupancy_rate").verdict, "SAFE")

    def test_self_target(self):
        v = self._verdict("net_patient_revenue")
        self.assertEqual(v.verdict, "SELF")
        self.assertEqual(v.severity, "critical")


class OperatingMarginTargetTests(unittest.TestCase):
    """Operating margin's inputs (NPR + opex) should LEAK when
    they're put on the RHS of an operating margin regression."""

    target = "operating_margin"

    def test_npr_leaks_when_target_is_margin(self):
        v = classify_feature_for_target("net_patient_revenue", self.target)
        self.assertEqual(v.verdict, "LEAKS")
        # The reason should call out "target is derived from this feature"
        self.assertIn("derived from this feature", v.reason)

    def test_opex_leaks_when_target_is_margin(self):
        self.assertEqual(
            classify_feature_for_target("operating_expenses",
                                        self.target).verdict,
            "LEAKS",
        )

    def test_net_income_formula_related_when_target_is_margin(self):
        # Phase-3.5 review fix: net_income and operating_margin both
        # depend on {npr, opex} but neither contains the other in
        # its formula. Direct-leak v1 algorithm classified this
        # SAFE (with a confusingly-named test). v1.1 introduces
        # FORMULA_RELATED to flag exactly this case — accounting-
        # identity cousins that aren't direct leaks but aren't
        # algebraically independent either.
        v = classify_feature_for_target("net_income", self.target)
        self.assertEqual(v.verdict, "FORMULA_RELATED")
        self.assertEqual(v.severity, "warning")
        # Reason must call out the shared inputs by name so the
        # partner understands WHY this is a soft warning
        self.assertIn("net_patient_revenue", v.reason)
        self.assertIn("operating_expenses", v.reason)

    def test_beds_safe_when_target_is_margin(self):
        self.assertEqual(
            classify_feature_for_target("beds", self.target).verdict,
            "SAFE",
        )


class OccupancyRateTargetTests(unittest.TestCase):
    """Occupancy = total_patient_days / bed_days_available — only
    those two inputs leak; everything else is safe."""

    target = "occupancy_rate"

    def test_total_patient_days_leaks(self):
        self.assertEqual(
            classify_feature_for_target("total_patient_days",
                                        self.target).verdict,
            "LEAKS",
        )

    def test_bed_days_available_leaks(self):
        self.assertEqual(
            classify_feature_for_target("bed_days_available",
                                        self.target).verdict,
            "LEAKS",
        )

    def test_npr_safe(self):
        self.assertEqual(
            classify_feature_for_target("net_patient_revenue",
                                        self.target).verdict,
            "SAFE",
        )

    def test_beds_safe(self):
        self.assertEqual(
            classify_feature_for_target("beds", self.target).verdict,
            "SAFE",
        )


class UnknownFeatureTests(unittest.TestCase):
    def test_unknown_feature_returns_unknown_not_safe(self):
        # Critically, an unknown feature must NOT be silently
        # classified as SAFE — caller has to make an explicit call.
        v = classify_feature_for_target("some_new_feature",
                                        "net_patient_revenue")
        self.assertEqual(v.verdict, "UNKNOWN")
        self.assertEqual(v.severity, "info")
        self.assertIn("provenance", v.reason.lower())

    def test_unknown_target_returns_unknown(self):
        v = classify_feature_for_target("beds", "some_new_target")
        self.assertEqual(v.verdict, "UNKNOWN")


class AuditFeaturesTests(unittest.TestCase):
    def test_audit_preserves_order(self):
        # Caller passes features in their preferred order; audit
        # returns verdicts in the same order so the UI can render
        # them in feature-input order.
        features = ["beds", "revenue_per_bed", "operating_margin"]
        verdicts = audit_features(features, "net_patient_revenue")
        self.assertEqual([v.feature for v in verdicts], features)

    def test_audit_returns_per_feature_verdicts(self):
        verdicts = audit_features(
            ["beds", "revenue_per_bed"],
            "net_patient_revenue",
        )
        self.assertEqual(verdicts[0].verdict, "SAFE")
        self.assertEqual(verdicts[1].verdict, "LEAKS")


class ForecastingSafeFeaturesTests(unittest.TestCase):
    """Convenience helper that returns the leakage-filtered subset."""

    def test_drops_leaks_and_self(self):
        features = [
            "beds", "revenue_per_bed", "net_patient_revenue",
            "occupancy_rate", "operating_margin",
        ]
        safe = forecasting_safe_features(features, "net_patient_revenue")
        self.assertIn("beds", safe)
        self.assertIn("occupancy_rate", safe)
        # All three NPR-leaky features dropped
        self.assertNotIn("revenue_per_bed", safe)
        self.assertNotIn("net_patient_revenue", safe)  # SELF
        self.assertNotIn("operating_margin", safe)

    def test_preserves_unknown_features(self):
        # UNKNOWN should pass through — caller can decide what to
        # do with them. The page renders them with an "info" badge.
        features = ["beds", "some_new_feature"]
        safe = forecasting_safe_features(features, "net_patient_revenue")
        self.assertIn("some_new_feature", safe)

    def test_drop_explanation_only_default(self):
        # Add a temporary explanation-only feature to the registry
        # for this test; clean up via shadow registry
        from copy import deepcopy
        reg = deepcopy(PROVENANCE)
        from rcm_mc.finance.leakage import FeatureProvenance
        reg["audit_flag"] = FeatureProvenance(
            name="audit_flag",
            label="Audit Flag",
            inputs=frozenset(),
            explanation_only=True,
        )
        safe = forecasting_safe_features(
            ["beds", "audit_flag"], "net_patient_revenue",
            registry=reg,
        )
        self.assertIn("beds", safe)
        self.assertNotIn("audit_flag", safe)

    def test_keep_explanation_only_when_requested(self):
        from copy import deepcopy
        reg = deepcopy(PROVENANCE)
        from rcm_mc.finance.leakage import FeatureProvenance
        reg["audit_flag"] = FeatureProvenance(
            name="audit_flag",
            label="Audit Flag",
            inputs=frozenset(),
            explanation_only=True,
        )
        safe = forecasting_safe_features(
            ["beds", "audit_flag"], "net_patient_revenue",
            registry=reg, drop_explanation_only=False,
        )
        self.assertIn("audit_flag", safe)


class FormulaRelatedTests(unittest.TestCase):
    """Phase-3.5 review addition: catch accounting-identity cousins.

    Two features can both depend on the same raw HCRIS columns
    without one literally containing the other — operating_margin
    (npr, opex) and net_income (npr, opex) is the canonical case.
    The v1 direct-only classifier missed this; v1.1 surfaces it
    as FORMULA_RELATED with severity warning.
    """

    def test_full_overlap_returns_formula_related(self):
        # net_income.inputs = {npr, opex}, operating_margin.inputs =
        # {npr, opex}. Full overlap → FORMULA_RELATED.
        v = classify_feature_for_target("net_income", "operating_margin")
        self.assertEqual(v.verdict, "FORMULA_RELATED")
        self.assertEqual(v.severity, "warning")

    def test_partial_overlap_returns_formula_related(self):
        # revenue_per_bed.inputs = {npr, beds}, expense_per_bed.inputs
        # = {opex, beds}. Shared: {beds}. Partial overlap → still
        # FORMULA_RELATED (the warning reason will name the shared
        # input so the partner can judge severity).
        v = classify_feature_for_target("revenue_per_bed", "expense_per_bed")
        self.assertEqual(v.verdict, "FORMULA_RELATED")
        self.assertIn("beds", v.reason)

    def test_raw_column_vs_raw_column_stays_safe(self):
        # FORMULA_RELATED requires both sides to have non-empty
        # input sets. Two raw HCRIS columns (beds, medicare_day_pct)
        # have no formulas → SAFE, not FORMULA_RELATED.
        v = classify_feature_for_target("beds", "medicare_day_pct")
        self.assertEqual(v.verdict, "SAFE")

    def test_raw_column_vs_derived_column_no_shared_check(self):
        # Raw beds (inputs=∅) vs derived occupancy_rate (inputs=
        # {patient_days, bed_days}). No shared inputs → not
        # FORMULA_RELATED → SAFE.
        v = classify_feature_for_target("beds", "occupancy_rate")
        self.assertEqual(v.verdict, "SAFE")

    def test_direct_leak_beats_formula_related(self):
        # When target ∈ feature.inputs the direct LEAK check fires
        # first, even though shared inputs exist. revenue_per_bed
        # for target=net_patient_revenue should still be LEAKS,
        # not downgraded to FORMULA_RELATED.
        v = classify_feature_for_target("revenue_per_bed", "net_patient_revenue")
        self.assertEqual(v.verdict, "LEAKS")

    def test_payer_share_features_formula_related(self):
        # commercial_pct (inputs={medicare_day_pct, medicaid_day_pct})
        # vs payer_diversity (same inputs). Full overlap.
        v = classify_feature_for_target("commercial_pct", "payer_diversity")
        self.assertEqual(v.verdict, "FORMULA_RELATED")


class StrictModeTests(unittest.TestCase):
    """The 'strict' kwarg on forecasting_safe_features drops
    FORMULA_RELATED features too. Default (strict=False) keeps them
    because a feature that shares an input with the target can
    still carry real signal.
    """

    def test_default_keeps_formula_related(self):
        # net_income for target=operating_margin is FORMULA_RELATED;
        # default forecasting_safe_features should KEEP it.
        safe = forecasting_safe_features(
            ["beds", "net_income"], "operating_margin",
        )
        self.assertIn("net_income", safe)
        self.assertIn("beds", safe)

    def test_strict_drops_formula_related(self):
        safe = forecasting_safe_features(
            ["beds", "net_income"], "operating_margin", strict=True,
        )
        self.assertNotIn("net_income", safe)
        self.assertIn("beds", safe)

    def test_strict_still_drops_self_and_leaks(self):
        # Strict mode is additive — still drops SELF and LEAKS.
        safe = forecasting_safe_features(
            ["beds", "revenue_per_bed", "net_patient_revenue"],
            "net_patient_revenue", strict=True,
        )
        self.assertIn("beds", safe)
        self.assertNotIn("revenue_per_bed", safe)
        self.assertNotIn("net_patient_revenue", safe)


class RegistryCoverageTests(unittest.TestCase):
    """Canary: every feature listed in regression_page._HCRIS_METRICS
    and _COMPUTED_HCRIS should have a PROVENANCE record. If a new
    feature gets added to the page without a leakage entry, this test
    fails so the developer remembers to update the registry.
    """

    def test_all_hcris_metrics_in_registry(self):
        from rcm_mc.ui.regression_page import (
            _HCRIS_METRICS, _COMPUTED_HCRIS,
        )
        missing = []
        for name, _ in _HCRIS_METRICS + _COMPUTED_HCRIS:
            if name not in PROVENANCE:
                missing.append(name)
        self.assertEqual(
            missing, [],
            f"Features in regression_page but not in leakage "
            f"PROVENANCE: {missing}. Add a FeatureProvenance entry "
            f"to rcm_mc/finance/leakage.py.",
        )


class AtomicInputsTests(unittest.TestCase):
    """The atomic-input walk underpins transitive FORMULA_RELATED
    detection. Pin the contract: returns {self} for raw columns,
    walks chains for derived features, terminates on cycles."""

    def test_raw_column_returns_itself(self):
        self.assertEqual(atomic_inputs("beds"), frozenset({"beds"}))
        self.assertEqual(
            atomic_inputs("net_patient_revenue"),
            frozenset({"net_patient_revenue"}),
        )

    def test_one_hop_returns_direct_inputs(self):
        # revenue_per_bed = npr / beds (1 hop deep)
        self.assertEqual(
            atomic_inputs("revenue_per_bed"),
            frozenset({"net_patient_revenue", "beds"}),
        )

    def test_two_hop_chain_walks_through(self):
        # margin_per_bed = operating_margin × bed-scale
        # operating_margin = (npr - opex) / npr
        # → atomic ancestors: {npr, opex, beds}
        self.assertEqual(
            atomic_inputs("margin_per_bed"),
            frozenset({
                "net_patient_revenue", "operating_expenses", "beds",
            }),
        )

    def test_cycle_does_not_loop_forever(self):
        # Synthetic registry with A→B→A would otherwise infinite-loop.
        # The visited-set guard returns empty on the second visit.
        reg = {
            "A": FeatureProvenance(
                name="A", label="A", inputs=frozenset({"B"}),
            ),
            "B": FeatureProvenance(
                name="B", label="B", inputs=frozenset({"A"}),
            ),
        }
        # Should terminate, returning something (whatever it can
        # reach in the bounded walk; specifically NOT an infinite
        # loop or RecursionError).
        result = atomic_inputs("A", reg)
        self.assertIsInstance(result, frozenset)

    def test_max_depth_bounds_walk(self):
        # Chain of 12 → max_depth=8 truncates before reaching atom.
        chain = {}
        for i in range(12):
            chain[f"L{i}"] = FeatureProvenance(
                name=f"L{i}", label=f"L{i}",
                inputs=(
                    frozenset({f"L{i+1}"}) if i < 11
                    else frozenset()  # L11 is raw
                ),
            )
        # Bounded walk shouldn't crash; just returns whatever it
        # could enumerate within max_depth=8.
        result = atomic_inputs("L0", chain, max_depth=8)
        self.assertIsInstance(result, frozenset)


class TransitiveFormulaRelatedTests(unittest.TestCase):
    """Multi-hop FORMULA_RELATED detection. PR #232 added the 1-hop
    check (direct .inputs intersection); this catches the 2+ hop
    chains the 1-hop check misses.

    Concrete case: margin_per_bed shares atomic inputs {npr, opex,
    beds} with operating_margin's atomic inputs {npr, opex}. Direct
    .inputs of margin_per_bed = {operating_margin, beds}, which
    doesn't intersect operating_margin.inputs = {npr, opex} —
    so the 1-hop check would say SAFE. Transitive must catch it.
    """

    def test_margin_per_bed_vs_revenue_per_day_is_transitive(self):
        # margin_per_bed.inputs = {operating_margin, beds}
        # revenue_per_day.inputs = {npr, total_patient_days}
        # Direct shared = ∅
        # margin_per_bed atomic = {npr, opex, beds}
        # revenue_per_day atomic = {npr, total_patient_days}
        # Atomic shared = {npr} → transitive FORMULA_RELATED
        v = classify_feature_for_target(
            "margin_per_bed", "revenue_per_day",
        )
        self.assertEqual(v.verdict, "FORMULA_RELATED")
        self.assertTrue(
            v.transitive,
            "should be transitive — direct .inputs don't overlap, "
            "the chain only emerges via the atomic walk through "
            "operating_margin",
        )
        self.assertIn("Transitive", v.reason)

    def test_one_hop_formula_related_not_marked_transitive(self):
        # revenue_per_bed.inputs = {npr, beds}
        # operating_margin.inputs = {npr, opex}
        # Direct shared = {npr} → 1-hop FORMULA_RELATED, not transitive.
        v = classify_feature_for_target(
            "revenue_per_bed", "operating_margin",
        )
        self.assertEqual(v.verdict, "FORMULA_RELATED")
        self.assertFalse(v.transitive)

    def test_direct_leak_still_wins_over_transitive(self):
        # margin_per_bed has operating_margin in its direct inputs.
        # Rule 3 (target ∈ feature.inputs) must short-circuit before
        # the atomic walk; otherwise we'd downgrade a critical LEAK
        # to a warning-severity FORMULA_RELATED.
        v = classify_feature_for_target(
            "margin_per_bed", "operating_margin",
        )
        self.assertEqual(v.verdict, "LEAKS")
        self.assertEqual(v.severity, "critical")

    def test_truly_unrelated_features_stay_safe(self):
        # occupancy_rate.inputs = {total_patient_days, bed_days}
        # commercial_pct.inputs = {medicare_day_pct, medicaid_day_pct}
        # Atomic: no overlap at all → SAFE.
        v = classify_feature_for_target(
            "occupancy_rate", "commercial_pct",
        )
        self.assertEqual(v.verdict, "SAFE")
        self.assertFalse(v.transitive)


if __name__ == "__main__":
    unittest.main()
