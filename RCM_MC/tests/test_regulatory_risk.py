"""Tests for the RegulatoryRiskPacket: TF-IDF, topic classification,
target exposure scoring, and jurisdictional heatmap.
"""
from __future__ import annotations

import unittest


def _fixture_corpus():
    """Build a small corpus covering each of the four named threats
    plus a few unrelated documents."""
    from rcm_mc.regulatory import (
        RegulatoryCorpus, RegulatoryDocument,
    )
    c = RegulatoryCorpus()
    c.add(RegulatoryDocument(
        doc_id="FR-2026-001",
        source="federal_register",
        title="FTC Final Rule on Non-Compete Agreements",
        body="The Federal Trade Commission today issued a final rule "
             "banning most non-compete clauses for workers nationwide. "
             "The non-compete ban affects physician mobility, executive "
             "labor mobility, and existing restrictive covenants.",
        date="2026-01-15",
        states=[],
        citation="89 FR 38342",
        sector_tags=["physician_group", "mso"],
    ))
    c.add(RegulatoryDocument(
        doc_id="TX-HB1024",
        source="state_legislation",
        title="Texas HB 1024 — Certificate of Need Repeal",
        body="A bill to repeal the Texas Certificate of Need (CON) "
             "regime for ambulatory surgery centers and inpatient "
             "rehabilitation. Eliminates transaction review for "
             "material change in ownership.",
        date="2026-02-01",
        states=["TX"],
        citation="Texas HB 1024 (2026)",
        sector_tags=["hospital", "asc"],
    ))
    c.add(RegulatoryDocument(
        doc_id="CMS-OPPS-CY2026",
        source="cms_rule",
        title="CY2026 OPPS Final Rule — Site-Neutral Payment Expansion",
        body="CMS expands site-neutral payment to include drug "
             "administration services in off-campus provider-based "
             "departments. Hospital Outpatient Prospective Payment "
             "System rates align with physician fee schedule for "
             "the affected service categories.",
        date="2025-11-15",
        states=[],
        citation="89 FR 109754",
        sector_tags=["hospital"],
    ))
    c.add(RegulatoryDocument(
        doc_id="CMS-ACO-V28",
        source="cms_guidance",
        title="ACO REACH PY2026 Risk Adjustment Methodology",
        body="The PY2026 risk adjustment will fully transition to the "
             "V28 HCC model. ACOs should anticipate coding intensity "
             "factor of 5.9% applied to all risk scores. Direct "
             "Contracting legacy contracts continue under blended V24/V28.",
        date="2025-12-01",
        states=[],
        citation="CMS-FFS-2025-0042",
        sector_tags=["managed_care"],
    ))
    c.add(RegulatoryDocument(
        doc_id="OIG-Settlement-2025-77",
        source="oig_enforcement",
        title="Hospital Settles Stark Law Allegations for $14M",
        body="The hospital agreed to pay $14M to resolve allegations "
             "that physician compensation arrangements lacked "
             "documented FMV opinions, in violation of the Stark Law "
             "and the federal Anti-Kickback Statute.",
        date="2025-09-12",
        states=["NJ"],
        citation="OIG Civil Settlement 2025-77",
        sector_tags=["hospital"],
    ))
    # Unrelated document — should not match any of the named topics
    c.add(RegulatoryDocument(
        doc_id="MISC-001",
        source="federal_register",
        title="USDA Organic Certification Update",
        body="Updates to the National Organic Program standards for "
             "agricultural product labeling.",
        date="2026-01-08",
        sector_tags=["agriculture"],
    ))
    return c


# ── TF-IDF unit tests ────────────────────────────────────────────

class TestTfidf(unittest.TestCase):
    def test_drops_stopwords(self):
        from rcm_mc.regulatory.tfidf import tokenize
        toks = tokenize("The quick brown fox jumps over the lazy dog")
        self.assertNotIn("the", toks)
        self.assertIn("quick", toks)

    def test_idf_weights_distinctive_terms_higher(self):
        from rcm_mc.regulatory import compute_tfidf
        scores = compute_tfidf([
            ("d1", "noncompete physician mobility ftc"),
            ("d2", "hospital site-neutral payment opps"),
            ("d3", "noncompete enforcement"),
        ])
        # "site-neutral" appears in 1 doc → high IDF
        # "noncompete" appears in 2 docs → lower IDF
        self.assertGreater(scores["d2"]["site-neutral"],
                           scores["d1"]["noncompete"])


# ── Topic classification ────────────────────────────────────────

class TestTopicClassification(unittest.TestCase):
    def test_ftc_noncompete_detected(self):
        from rcm_mc.regulatory import classify_document_topics
        text = ("FTC final rule on non-compete agreements affecting "
                "physician mobility nationwide.")
        matches = classify_document_topics(text)
        self.assertTrue(any(
            m.topic_id == "ftc_noncompete" for m in matches))

    def test_site_neutral_detected(self):
        from rcm_mc.regulatory import classify_document_topics
        text = ("CMS expands site-neutral payment to off-campus "
                "provider-based departments under OPPS.")
        matches = classify_document_topics(text)
        ids = {m.topic_id for m in matches}
        self.assertIn("site_neutral", ids)

    def test_unrelated_doc_returns_empty(self):
        from rcm_mc.regulatory import classify_document_topics
        text = "USDA organic certification standards update."
        matches = classify_document_topics(text)
        self.assertEqual(matches, [])


# ── Target exposure scoring ─────────────────────────────────────

class TestTargetExposure(unittest.TestCase):
    def test_hospital_sees_site_neutral_and_state_con(self):
        """A Texas hospital should pick up both the OPPS site-neutral
        topic (federal) AND the Texas CON repeal (state-anchored)."""
        from rcm_mc.regulatory import (
            TargetProfile, score_target_exposure,
        )
        target = TargetProfile(
            target_name="Memorial TX Hospital",
            sector="hospital",
            states=["TX"],
            ebitda_mm=80.0,
        )
        result = score_target_exposure(target, _fixture_corpus())
        topic_ids = {e.topic_id for e in result.topic_exposures}
        self.assertIn("site_neutral", topic_ids)
        self.assertIn("state_con_cpom", topic_ids)
        # Texas state match should yield non-trivial exposure
        con = next(e for e in result.topic_exposures
                   if e.topic_id == "state_con_cpom")
        self.assertGreater(con.ebitda_at_risk_mm, 0)

    def test_managed_care_target_sees_v28_cliff(self):
        from rcm_mc.regulatory import (
            TargetProfile, score_target_exposure,
        )
        target = TargetProfile(
            target_name="Friendly Health PCs",
            sector="managed_care",
            states=["TX", "FL"],
            ebitda_mm=40.0,
        )
        result = score_target_exposure(target, _fixture_corpus())
        topic_ids = {e.topic_id for e in result.topic_exposures}
        self.assertIn("v28_risk_cliff", topic_ids)
        v28 = next(e for e in result.topic_exposures
                   if e.topic_id == "v28_risk_cliff")
        # v28 has 10% sensitivity × 1 doc (density 0.33) × 0.7 fed jur
        # = 40 × 0.10 × 0.333 × 0.7 ≈ 0.93
        self.assertAlmostEqual(v28.ebitda_at_risk_mm, 0.933, places=2)

    def test_sector_filter_excludes_irrelevant_topics(self):
        """A managed-care target should NOT see the site-neutral topic
        (only applicable_sectors hospital/asc/imaging)."""
        from rcm_mc.regulatory import (
            TargetProfile, score_target_exposure,
        )
        target = TargetProfile(
            target_name="MA-Focused Group",
            sector="managed_care",
            states=["TX"],
            ebitda_mm=50.0,
        )
        result = score_target_exposure(target, _fixture_corpus())
        ids = {e.topic_id for e in result.topic_exposures}
        self.assertNotIn("site_neutral", ids)

    def test_total_at_risk_sums_topics(self):
        from rcm_mc.regulatory import (
            TargetProfile, score_target_exposure,
        )
        target = TargetProfile(
            target_name="Test", sector="hospital",
            states=["TX"], ebitda_mm=100.0)
        result = score_target_exposure(target, _fixture_corpus())
        topic_sum = sum(e.ebitda_at_risk_mm
                        for e in result.topic_exposures)
        self.assertAlmostEqual(
            result.total_at_risk_mm, topic_sum, places=2)


# ── Jurisdictional heatmap ──────────────────────────────────────

class TestHeatmap(unittest.TestCase):
    def test_heatmap_only_target_states(self):
        from rcm_mc.regulatory import (
            TargetProfile, jurisdictional_heatmap,
        )
        target = TargetProfile(
            target_name="MultiState Hospital",
            sector="hospital",
            states=["TX", "NJ"],
            ebitda_mm=120.0,
        )
        heatmap = jurisdictional_heatmap(target, _fixture_corpus())
        # Only TX + NJ in keys
        self.assertEqual(set(heatmap.keys()), {"TX", "NJ"})
        # Both states should have at least one topic with > 0 risk
        for state, topics in heatmap.items():
            self.assertGreater(sum(topics.values()), 0)


if __name__ == "__main__":
    unittest.main()
