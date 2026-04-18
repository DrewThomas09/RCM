"""Digital Front Door / Patient Experience Tracker.

Tracks patient portal adoption, online scheduling, reviews, NPS, digital
onboarding, telehealth utilization across portfolio — the "retail
experience" layer of healthcare consumerism.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class DigitalChannelAdoption:
    deal: str
    sector: str
    portal_registration_pct: float
    portal_active_90d_pct: float
    online_scheduling_pct: float
    mobile_app_adoption_pct: float
    ambient_ai_visits_pct: float
    digital_onboarding_pct: float


@dataclass
class PatientExperience:
    deal: str
    nps: int
    hcahps_composite: float
    google_rating: float
    google_reviews_count: int
    complaints_per_1k: float
    response_time_hours: float
    resolution_rate_pct: float


@dataclass
class TelehealthMetric:
    deal: str
    telehealth_visits_monthly_k: int
    pct_of_total_visits: float
    telehealth_revenue_m: float
    completion_rate_pct: float
    avg_duration_min: float
    patient_satisfaction: float


@dataclass
class DigitalSpend:
    category: str
    portfolio_spend_m: float
    yoy_growth_pct: float
    vendors: str
    typical_roi: str


@dataclass
class VendorAdoption:
    vendor: str
    category: str
    portfolio_deals: int
    users_k: int
    annual_cost_m: float
    status: str


@dataclass
class FunnelMetric:
    deal: str
    web_visits_monthly_k: int
    new_patient_inquiries: int
    inquiry_to_booking_pct: float
    book_to_visit_pct: float
    no_show_rate_pct: float
    cost_per_acquired: float


@dataclass
class DigitalResult:
    total_portcos: int
    weighted_portal_adoption_pct: float
    avg_nps: int
    total_telehealth_visits_monthly_k: int
    total_digital_spend_m: float
    avg_google_rating: float
    adoption: List[DigitalChannelAdoption]
    experience: List[PatientExperience]
    telehealth: List[TelehealthMetric]
    spend: List[DigitalSpend]
    vendors: List[VendorAdoption]
    funnels: List[FunnelMetric]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_adoption() -> List[DigitalChannelAdoption]:
    return [
        DigitalChannelAdoption("Project Cypress — GI Network", "Gastroenterology", 0.78, 0.52, 0.62, 0.38, 0.45, 0.52),
        DigitalChannelAdoption("Project Magnolia — MSK Platform", "MSK / Ortho", 0.72, 0.48, 0.58, 0.32, 0.35, 0.48),
        DigitalChannelAdoption("Project Redwood — Behavioral", "Behavioral Health", 0.65, 0.45, 0.55, 0.42, 0.22, 0.52),
        DigitalChannelAdoption("Project Laurel — Derma", "Dermatology", 0.82, 0.58, 0.72, 0.45, 0.38, 0.62),
        DigitalChannelAdoption("Project Cedar — Cardiology", "Cardiology", 0.75, 0.52, 0.60, 0.35, 0.48, 0.50),
        DigitalChannelAdoption("Project Willow — Fertility", "Fertility / IVF", 0.92, 0.78, 0.85, 0.72, 0.35, 0.78),
        DigitalChannelAdoption("Project Spruce — Radiology", "Radiology", 0.55, 0.32, 0.45, 0.18, 0.15, 0.38),
        DigitalChannelAdoption("Project Aspen — Eye Care", "Eye Care", 0.75, 0.52, 0.65, 0.38, 0.28, 0.55),
        DigitalChannelAdoption("Project Maple — Urology", "Urology", 0.68, 0.42, 0.55, 0.28, 0.35, 0.45),
        DigitalChannelAdoption("Project Ash — Infusion", "Infusion", 0.78, 0.58, 0.62, 0.35, 0.25, 0.58),
        DigitalChannelAdoption("Project Fir — Lab / Pathology", "Lab Services", 0.72, 0.48, 0.52, 0.32, 0.15, 0.45),
        DigitalChannelAdoption("Project Sage — Home Health", "Home Health", 0.45, 0.28, 0.15, 0.32, 0.18, 0.22),
        DigitalChannelAdoption("Project Linden — Behavioral", "Behavioral Health", 0.58, 0.38, 0.48, 0.35, 0.18, 0.42),
        DigitalChannelAdoption("Project Basil — Dental DSO", "Dental DSO", 0.72, 0.45, 0.68, 0.38, 0.25, 0.52),
        DigitalChannelAdoption("Project Thyme — Specialty Pharm", "Specialty Pharma", 0.82, 0.65, 0.72, 0.52, 0.22, 0.68),
    ]


def _build_experience() -> List[PatientExperience]:
    return [
        PatientExperience("Project Cypress — GI Network", 62, 4.4, 4.6, 8500, 2.5, 4.2, 0.92),
        PatientExperience("Project Magnolia — MSK Platform", 58, 4.3, 4.5, 6500, 2.8, 4.5, 0.90),
        PatientExperience("Project Redwood — Behavioral", 52, 4.1, 4.2, 3850, 5.2, 6.5, 0.82),
        PatientExperience("Project Laurel — Derma", 68, 4.5, 4.7, 12500, 1.8, 3.2, 0.94),
        PatientExperience("Project Cedar — Cardiology", 58, 4.3, 4.4, 5850, 3.2, 4.8, 0.90),
        PatientExperience("Project Willow — Fertility", 72, 4.7, 4.8, 4250, 1.5, 2.5, 0.96),
        PatientExperience("Project Spruce — Radiology", 42, 4.2, 4.3, 2850, 2.2, 5.5, 0.88),
        PatientExperience("Project Aspen — Eye Care", 62, 4.4, 4.5, 4850, 2.2, 3.8, 0.92),
        PatientExperience("Project Maple — Urology", 55, 4.2, 4.3, 2450, 3.0, 4.8, 0.88),
        PatientExperience("Project Ash — Infusion", 62, 4.5, 4.6, 1850, 2.0, 3.5, 0.93),
        PatientExperience("Project Fir — Lab / Pathology", 58, 4.4, 4.5, 5850, 2.5, 4.5, 0.90),
        PatientExperience("Project Sage — Home Health", 45, 4.0, 4.1, 3250, 6.5, 8.5, 0.80),
        PatientExperience("Project Linden — Behavioral", 48, 4.1, 4.2, 2850, 5.0, 7.0, 0.82),
        PatientExperience("Project Basil — Dental DSO", 55, 4.3, 4.4, 8500, 3.5, 5.2, 0.88),
    ]


def _build_telehealth() -> List[TelehealthMetric]:
    return [
        TelehealthMetric("Project Cypress — GI Network", 12, 0.14, 4.8, 0.92, 18.5, 4.5),
        TelehealthMetric("Project Magnolia — MSK Platform", 8, 0.08, 3.2, 0.88, 22.5, 4.3),
        TelehealthMetric("Project Redwood — Behavioral", 38, 0.48, 18.5, 0.88, 42.5, 4.4),
        TelehealthMetric("Project Laurel — Derma", 6, 0.12, 2.8, 0.90, 12.5, 4.6),
        TelehealthMetric("Project Cedar — Cardiology", 10, 0.10, 3.5, 0.90, 18.5, 4.4),
        TelehealthMetric("Project Willow — Fertility", 4, 0.12, 2.2, 0.92, 25.0, 4.7),
        TelehealthMetric("Project Spruce — Radiology", 2, 0.02, 0.8, 0.95, 8.5, 4.2),
        TelehealthMetric("Project Aspen — Eye Care", 2, 0.04, 0.6, 0.88, 15.5, 4.3),
        TelehealthMetric("Project Maple — Urology", 3, 0.08, 1.2, 0.88, 18.5, 4.2),
        TelehealthMetric("Project Ash — Infusion", 2, 0.03, 0.5, 0.92, 12.5, 4.4),
        TelehealthMetric("Project Linden — Behavioral", 22, 0.52, 10.5, 0.85, 45.5, 4.3),
        TelehealthMetric("Project Sage — Home Health", 12, 0.22, 3.8, 0.82, 28.5, 4.1),
    ]


def _build_spend() -> List[DigitalSpend]:
    return [
        DigitalSpend("Patient Portal + Patient App", 22.5, 0.15, "Epic MyChart, Athena Patient, Luma Health", "3-4x ROI on portal adoption + retention"),
        DigitalSpend("Online Scheduling + Open Access", 12.8, 0.22, "Zocdoc, Athena, Kyruus, Luma Health", "2-3x on new patient acquisition"),
        DigitalSpend("Telehealth Platform", 18.5, 0.12, "Zoom Healthcare, Doxy, Amwell, Epic Haiku", "high-ROI for behavioral / chronic"),
        DigitalSpend("Ambient AI Scribe", 14.5, 0.85, "Abridge, Notable, Nuance DAX, Suki", "3-6x ROI on physician productivity"),
        DigitalSpend("Review Management / Rep Mgmt", 4.2, 0.35, "Birdeye, Podium, Reputation.com, Press Ganey", "2-3x on new patient acquisition"),
        DigitalSpend("Digital Onboarding / Intake", 8.5, 0.48, "Phreesia, Clearwave, Relatient", "reduced intake time + downstream savings"),
        DigitalSpend("Website / SEO / Marketing Tech", 18.5, 0.18, "Invoca, Binary Fountain, WebMD Ignite, Brafton", "modest ROI; branding + digital funnel"),
        DigitalSpend("CRM / Patient Engagement", 12.5, 0.28, "Salesforce Health Cloud, athenaOne, QGenda", "lifts retention + referral velocity"),
        DigitalSpend("Price Transparency / Cost Estimator", 6.8, 0.35, "Epic Cost Estimate, Turquoise, Amitech", "required by law; modest lift in conversions"),
        DigitalSpend("RPM / Chronic Care Management", 11.2, 0.32, "CCM vendors, RPM device + platform mix", "MA tailwind; modest ROI but growing"),
    ]


def _build_vendors() -> List[VendorAdoption]:
    return [
        VendorAdoption("Epic MyChart", "Patient Portal", 10, 850, 18.5, "live production"),
        VendorAdoption("athenaOne Patient", "Patient Portal", 4, 185, 3.8, "live production"),
        VendorAdoption("Luma Health", "Patient Engagement / Messaging", 6, 125, 2.2, "live production"),
        VendorAdoption("Zocdoc", "Online Scheduling", 8, 285, 4.5, "live production"),
        VendorAdoption("Kyruus", "Provider Search / Scheduling", 5, 145, 3.2, "live production"),
        VendorAdoption("Phreesia", "Digital Intake", 7, 285, 5.8, "live production"),
        VendorAdoption("Clearwave", "Digital Intake / Check-in", 3, 85, 1.8, "live production"),
        VendorAdoption("Birdeye", "Review Management", 8, 0, 1.5, "live production"),
        VendorAdoption("Press Ganey", "Patient Satisfaction + Reviews", 11, 0, 2.5, "live production"),
        VendorAdoption("Zoom Healthcare", "Telehealth", 14, 455, 5.5, "live production"),
        VendorAdoption("Abridge", "Ambient Scribe", 2, 45, 2.2, "live production"),
        VendorAdoption("Notable Health", "Ambient / Clinical Workflow", 3, 58, 3.5, "live production"),
        VendorAdoption("Nuance DAX Copilot", "Ambient Scribe", 3, 45, 4.8, "live production"),
        VendorAdoption("Salesforce Health Cloud", "CRM / Engagement", 7, 185, 4.2, "live production"),
        VendorAdoption("Relatient", "Text-based Patient Engagement", 5, 0, 1.2, "live production"),
        VendorAdoption("Turquoise Health", "Price Transparency", 10, 0, 0.65, "live production"),
        VendorAdoption("Invoca", "Call Tracking + Analytics", 6, 0, 0.85, "live production"),
        VendorAdoption("Rad AI Continuum", "Radiology Workflow", 2, 45, 1.8, "pilot"),
    ]


def _build_funnels() -> List[FunnelMetric]:
    return [
        FunnelMetric("Project Cypress — GI Network", 185, 8500, 0.48, 0.82, 0.075, 125),
        FunnelMetric("Project Magnolia — MSK Platform", 125, 4850, 0.52, 0.78, 0.082, 185),
        FunnelMetric("Project Redwood — Behavioral", 85, 6250, 0.35, 0.72, 0.125, 145),
        FunnelMetric("Project Laurel — Derma", 285, 12500, 0.62, 0.88, 0.065, 85),
        FunnelMetric("Project Cedar — Cardiology", 95, 3850, 0.55, 0.85, 0.078, 165),
        FunnelMetric("Project Willow — Fertility", 185, 2850, 0.42, 0.82, 0.112, 285),
        FunnelMetric("Project Spruce — Radiology", 65, 5450, 0.62, 0.85, 0.062, 95),
        FunnelMetric("Project Aspen — Eye Care", 185, 6250, 0.48, 0.82, 0.098, 115),
        FunnelMetric("Project Maple — Urology", 45, 2250, 0.45, 0.78, 0.085, 142),
        FunnelMetric("Project Ash — Infusion", 32, 1250, 0.68, 0.92, 0.042, 185),
        FunnelMetric("Project Basil — Dental DSO", 225, 12500, 0.55, 0.82, 0.092, 102),
    ]


def compute_digital_front_door() -> DigitalResult:
    corpus = _load_corpus()
    adoption = _build_adoption()
    experience = _build_experience()
    telehealth = _build_telehealth()
    spend = _build_spend()
    vendors = _build_vendors()
    funnels = _build_funnels()

    wtd_portal = sum(a.portal_active_90d_pct for a in adoption) / len(adoption) if adoption else 0
    avg_nps = sum(e.nps for e in experience) / len(experience) if experience else 0
    total_th = sum(t.telehealth_visits_monthly_k for t in telehealth)
    total_spend = sum(s.portfolio_spend_m for s in spend)
    avg_rating = sum(e.google_rating for e in experience) / len(experience) if experience else 0

    return DigitalResult(
        total_portcos=len(adoption),
        weighted_portal_adoption_pct=round(wtd_portal, 4),
        avg_nps=int(round(avg_nps)),
        total_telehealth_visits_monthly_k=total_th,
        total_digital_spend_m=round(total_spend, 1),
        avg_google_rating=round(avg_rating, 2),
        adoption=adoption,
        experience=experience,
        telehealth=telehealth,
        spend=spend,
        vendors=vendors,
        funnels=funnels,
        corpus_deal_count=len(corpus),
    )
