"""Market Scan page — /market-scan, fed by the connector estate bridge.

The scan stitches eleven sections of estate datasets into one
state-level brief (nine original sections plus the round-3 kidney &
dialysis market and outpatient facility universe). These tests pin the
three load-bearing behaviours:

  - with tiny seeded stores (built through the connectors' own tables
    modules, pointed at a temp dir via RCM_MC_CONNECTORS_DB) every
    section renders its real numbers;
  - with an empty store dir every section renders its honest
    "not ingested" note carrying the per-connector CLI one-liner, and no
    stray .db files are created;
  - params are clamped/validated (bogus state falls back to TX, bogus
    county FIPS is dropped, integer limits never 500), and the route
    serves over real HTTP with nav/palette wiring intact.

Env repoints (RCM_MC_CONNECTORS_ROOT / RCM_MC_CONNECTORS_DB) are
external-input knobs, not mocks of our own code; every test restores the
environment so the suite stays order-independent.
"""
from __future__ import annotations

import os
import socket
import tempfile
import unittest
from contextlib import closing

from rcm_mc.data_public import connector_estate as est
from rcm_mc.ui.data_public.market_scan_page import render_market_scan

_ENV_KEYS = ("RCM_MC_CONNECTORS_ROOT", "RCM_MC_CONNECTORS_DB")

_SECTION_TITLES = (
    "Demographics &amp; payor context",
    "Population health burden",
    "Provider shortage",
    "Medicare market",
    "Facility quality",
    "Industry money flow",
    "Research footprint",
    "Compliance exposure",
    "Healthcare labor market",
    "Kidney &amp; dialysis market",
    "Outpatient facility universe",
)

# One CLI module per section's empty-state one-liner (flags live in the
# page; the module path is the stable part worth pinning here).
_CLI_MODULES = (
    "connectors.census_acs.cli",
    "connectors.cdc_data.cli",
    "connectors.hrsa_data.cli",
    "connectors.cms_open_data.cli",
    "connectors.provider_data.cli",
    "connectors.open_payments.cli",
    "connectors.nih_reporter.cli",
    "connectors.oig_leie.cli",
    "connectors.bls_qcew.cli",
)


class _EnvGuard(unittest.TestCase):
    """Save/restore the bridge env knobs around every test."""

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in _ENV_KEYS}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _sf(dataset_id: str) -> str:
    row = est.dataset_row(dataset_id)
    assert row is not None, f"unknown dataset {dataset_id}"
    return row["source_filter"]


def _seed_estate(db_dir: str) -> None:
    """Tiny-but-real stores for all nine scan connectors, via the estate's
    own store classes (no mocks — the same upsert path ingest uses)."""

    def upsert(connector: str, table: str, rows: list[dict]) -> None:
        adapter = est.adapter_for(connector)
        assert adapter is not None, f"no adapter for {connector}"
        store = adapter.open_store(os.path.join(db_dir, f"{connector}.db"))
        try:
            store.upsert(table, rows)
        finally:
            store.close()

    upsert("census_acs", "census_acs_state", [{
        "state_key": "48:2023", "state_fips": "48", "name": "Texas",
        "year": "2023", "total_pop": "30000000", "median_age": "35.5",
        "median_hh_income": "73035", "poverty_count": "4200000",
        "pop_65_plus": "3900000", "uninsured_rate": "16.6",
        "source_endpoint": _sf("census_acs_state_profile")}])
    upsert("census_acs", "census_acs_county", [
        {"county_key": "48201:2023", "fips5": "48201", "state_fips": "48",
         "county_fips": "201", "name": "Harris County, Texas",
         "year": "2023", "total_pop": "4760000", "median_age": "34.0",
         "median_hh_income": "70000", "poverty_count": "760000",
         "pop_65_plus": "530000", "uninsured_rate": "20.4",
         "source_endpoint": _sf("census_acs_county_profile")},
        {"county_key": "48113:2023", "fips5": "48113", "state_fips": "48",
         "county_fips": "113", "name": "Dallas County, Texas",
         "year": "2023", "total_pop": "2600000", "median_age": "33.8",
         "median_hh_income": "67000", "poverty_count": "440000",
         "pop_65_plus": "290000", "uninsured_rate": "21.9",
         "source_endpoint": _sf("census_acs_county_profile")},
    ])

    upsert("cdc_data", "cdc_places_county", [
        {"record_key": "tx:48201:DIABETES", "stateabbr": "TX",
         "locationname": "Harris", "locationid": "48201",
         "measureid": "DIABETES", "measure": "Diagnosed diabetes",
         "data_value_type": "Age-adjusted prevalence", "data_value": "13.0",
         "year": "2022", "source_endpoint": _sf("cdc_data_places_county")},
        {"record_key": "tx:48113:DIABETES", "stateabbr": "TX",
         "locationname": "Dallas", "locationid": "48113",
         "measureid": "DIABETES", "measure": "Diagnosed diabetes",
         "data_value_type": "Age-adjusted prevalence", "data_value": "12.0",
         "year": "2022", "source_endpoint": _sf("cdc_data_places_county")},
        {"record_key": "tx:48201:OBESITY", "stateabbr": "TX",
         "locationname": "Harris", "locationid": "48201",
         "measureid": "OBESITY", "measure": "Obesity",
         "data_value_type": "Age-adjusted prevalence", "data_value": "36.9",
         "year": "2022", "source_endpoint": _sf("cdc_data_places_county")},
    ])

    upsert("hrsa_data", "hrsa_hpsa", [
        {"hpsa_key": "pc:1", "hpsa_name": "GULF COAST COMMUNITY CLINIC",
         "hpsa_id": "1487654321", "designation_type": "HPSA Population",
         "hpsa_discipline_class": "Primary Care", "hpsa_score": "21",
         "primary_state_abbreviation": "TX", "hpsa_status": "Designated",
         "common_county_name": "Harris County, TX",
         "hpsa_designation_population": "123456",
         "source_endpoint": _sf("hrsa_data_hpsa_primary_care")},
        {"hpsa_key": "dh:1", "hpsa_name": "PANHANDLE DENTAL ACCESS",
         "hpsa_id": "6487654321", "designation_type": "Geographic HPSA",
         "hpsa_discipline_class": "Dental Health", "hpsa_score": "25",
         "primary_state_abbreviation": "TX", "hpsa_status": "Designated",
         "common_county_name": "Potter County, TX",
         "hpsa_designation_population": "54321",
         "source_endpoint": _sf("hrsa_data_hpsa_dental")},
    ])

    geo_sf = _sf("cms_open_data_geo_variation_state_county")
    upsert("cms_open_data", "cms_open_data_geo_variation_state_county", [
        {"row_key": "2023:State:48:All", "year": "2023",
         "bene_geo_lvl": "State", "bene_geo_desc": "TX", "bene_geo_cd": "48",
         "bene_age_lvl": "All", "benes_total_cnt": "4860770",
         "tot_mdcr_stdzd_pymt_pc": "13287.86", "ma_prtcptn_rate": "0.5663",
         "er_visits_per_1000_benes": "580.3558", "bene_dual_pct": "0.1075",
         "source_endpoint": geo_sf},
        {"row_key": "2023:County:48201:All", "year": "2023",
         "bene_geo_lvl": "County", "bene_geo_desc": "TX-Harris",
         "bene_geo_cd": "48201", "bene_age_lvl": "All",
         "benes_total_cnt": "641854", "tot_mdcr_stdzd_pymt_pc": "14110.48",
         "ma_prtcptn_rate": "0.6554", "er_visits_per_1000_benes": "553.4",
         "bene_dual_pct": "0.13", "source_endpoint": geo_sf},
        {"row_key": "2023:County:48113:All", "year": "2023",
         "bene_geo_lvl": "County", "bene_geo_desc": "TX-Dallas",
         "bene_geo_cd": "48113", "bene_age_lvl": "All",
         "benes_total_cnt": "359395", "tot_mdcr_stdzd_pymt_pc": "13839.13",
         "ma_prtcptn_rate": "0.5842", "er_visits_per_1000_benes": "569.1",
         "bene_dual_pct": "0.14", "source_endpoint": geo_sf},
    ])
    upsert("cms_open_data", "cms_open_data_market_saturation_state_county", [
        {"row_key": "2023:HH:TX", "reference_period": "2023-01-01 to 2023-12-31",
         "type_of_service": "Home Health", "aggregation_level": "STATE",
         "state": "TX", "county": "--ALL--", "state_fips": "48",
         "number_of_fee_for_service_beneficiaries": "2,394,063",
         "number_of_providers": "1,343",
         "average_number_of_users_per_provider": "165.2",
         "source_endpoint": _sf("cms_open_data_market_saturation_state_county")}])
    enr_sf = _sf("cms_open_data_medicare_monthly_enrollment")
    upsert("cms_open_data", "cms_open_data_medicare_monthly_enrollment", [
        {"row_key": "2022:Year:State:TX", "year": "2022", "month": "Year",
         "bene_geo_lvl": "State", "bene_state_abrvtn": "TX",
         "bene_state_desc": "Texas", "bene_county_desc": "Total",
         "bene_fips_cd": "48", "tot_benes": "4500000",
         "ma_and_oth_benes": "2300000", "source_endpoint": enr_sf},
        {"row_key": "2023:Year:State:TX", "year": "2023", "month": "Year",
         "bene_geo_lvl": "State", "bene_state_abrvtn": "TX",
         "bene_state_desc": "Texas", "bene_county_desc": "Total",
         "bene_fips_cd": "48", "tot_benes": "4639192",
         "ma_and_oth_benes": "2409926", "source_endpoint": enr_sf},
    ])

    upsert("provider_data", "hospital_general", [
        {"record_key": "450001", "facility_id": "450001",
         "facility_name": "HOUSTON METHODIST HOSPITAL", "state": "TX",
         "citytown": "HOUSTON", "hospital_overall_rating": "5",
         "source_endpoint": _sf("provider_data_hospital_general")},
        {"record_key": "450002", "facility_id": "450002",
         "facility_name": "SOME COUNTY MEDICAL CENTER", "state": "TX",
         "citytown": "DALLAS", "hospital_overall_rating": "3",
         "source_endpoint": _sf("provider_data_hospital_general")},
    ])
    upsert("provider_data", "nursing_home_provider_info", [
        {"record_key": "455001", "cms_certification_number_ccn": "455001",
         "provider_name": "BLUEBONNET CARE CENTER", "state": "TX",
         "citytown": "AUSTIN", "overall_rating": "4",
         "source_endpoint": _sf("provider_data_nursing_home_provider_info")}])

    op_sf = _sf("open_payments_state_payment_totals")
    upsert("open_payments", "op_state_payment_totals", [
        {"state_totals_key": "TX:2024:consulting:phys",
         "state_code": "TX", "state_name": "Texas",
         "nature_of_payment": "Consulting Fee",
         "recipient_type": "Covered Recipient Physician",
         "program_year": "2024",
         "total_payment_amount_physician": "39455687.05",
         "total_payment_amount_non_physician_practitioner": "1200000.00",
         "total_payment_amount_teaching_hospital": "0.00",
         "source_endpoint": op_sf},
        {"state_totals_key": "TX:2024:food:phys",
         "state_code": "TX", "state_name": "Texas",
         "nature_of_payment": "Food and Beverage",
         "recipient_type": "Covered Recipient Physician",
         "program_year": "2024",
         "total_payment_amount_physician": "27310000.00",
         "total_payment_amount_non_physician_practitioner": "0.00",
         "total_payment_amount_teaching_hospital": "0.00",
         "source_endpoint": op_sf},
    ])

    upsert("nih_reporter", "nih_projects", [
        {"appl_id": "11000001", "project_num": "5R01CA000001-01",
         "fiscal_year": "2025", "org_name": "BAYLOR COLLEGE OF MEDICINE",
         "org_state": "TX", "award_amount": "2450000",
         "project_title": "Oncology outcomes",
         "source_endpoint": _sf("nih_reporter_projects")},
        {"appl_id": "11000002", "project_num": "5R01HL000002-02",
         "fiscal_year": "2025", "org_name": "UT SOUTHWESTERN MEDICAL CENTER",
         "org_state": "TX", "award_amount": "5560000",
         "project_title": "Cardiology registry",
         "source_endpoint": _sf("nih_reporter_projects")},
    ])

    oig_sf = _sf("oig_leie_exclusions")
    upsert("oig_leie", "oig_exclusions", [
        {"exclusion_key": "tx:1", "lastname": "DOE", "firstname": "JANE",
         "busname": "", "specialty": "NURSE", "city": "HOUSTON",
         "state": "TX", "excltype": "1128a1", "excldate": "2025-04-20",
         "source_endpoint": oig_sf},
        {"exclusion_key": "tx:2", "lastname": "", "firstname": "",
         "busname": "ACME HOME HEALTH LLC", "specialty": "HOME HEALTH",
         "city": "DALLAS", "state": "TX", "excltype": "1128b8",
         "excldate": "2025-05-20", "source_endpoint": oig_sf},
    ])

    # ── round-3 seeds: kidney & dialysis market (section 10) ──────────
    ckd_sf = _sf("cdc_data_places_county_ckd")
    upsert("cdc_data", "cdc_places_county_ckd", [
        {"record_key": "tx:48201:KIDNEY:AgeAdjPrv", "stateabbr": "TX",
         "locationname": "Harris", "locationid": "48201",
         "measureid": "KIDNEY",
         "measure": "Chronic kidney disease among adults aged >=18 years",
         "data_value_type": "Age-adjusted prevalence",
         "datavaluetypeid": "AgeAdjPrv", "data_value": "3.1",
         "year": "2021", "source_endpoint": ckd_sf},
        {"record_key": "tx:48113:KIDNEY:AgeAdjPrv", "stateabbr": "TX",
         "locationname": "Dallas", "locationid": "48113",
         "measureid": "KIDNEY",
         "measure": "Chronic kidney disease among adults aged >=18 years",
         "data_value_type": "Age-adjusted prevalence",
         "datavaluetypeid": "AgeAdjPrv", "data_value": "2.9",
         "year": "2021", "source_endpoint": ckd_sf},
        # Crude-prevalence twin proves the page pins the age-adjusted
        # slice rather than averaging both value types together.
        {"record_key": "tx:48201:KIDNEY:CrdPrv", "stateabbr": "TX",
         "locationname": "Harris", "locationid": "48201",
         "measureid": "KIDNEY",
         "measure": "Chronic kidney disease among adults aged >=18 years",
         "data_value_type": "Crude prevalence",
         "datavaluetypeid": "CrdPrv", "data_value": "9.9",
         "year": "2021", "source_endpoint": ckd_sf},
    ])

    dial_sf = _sf("provider_data_dialysis_facilities")
    upsert("provider_data", "dialysis_facilities", [
        {"record_key": "452301", "cms_certification_number_ccn": "452301",
         "facility_name": "GULF COAST DIALYSIS", "state": "TX",
         "citytown": "HOUSTON", "five_star": "4.0",
         "profit_or_nonprofit": "Profit", "chain_organization": "DaVita",
         "of_dialysis_stations": "24", "source_endpoint": dial_sf},
        {"record_key": "452302", "cms_certification_number_ccn": "452302",
         "facility_name": "HILL COUNTRY KIDNEY CENTER", "state": "TX",
         "citytown": "AUSTIN", "five_star": "2.0",
         "profit_or_nonprofit": "Non-profit",
         "chain_organization": "Fresenius Medical Care",
         "of_dialysis_stations": "16", "source_endpoint": dial_sf},
    ])
    tps_sf = _sf("provider_data_esrd_qip_tps")
    upsert("provider_data", "esrd_qip_tps", [
        {"record_key": "452301", "cms_certification_number_ccn": "452301",
         "facility_name": "GULF COAST DIALYSIS", "state": "TX",
         "total_performance_score": "62",
         "state_average_total_performance_score": "54",
         "national_average_total_performance_score": "54",
         "payment_reduction_percentage": "0.0%", "source_endpoint": tps_sf},
        {"record_key": "452302", "cms_certification_number_ccn": "452302",
         "facility_name": "HILL COUNTRY KIDNEY CENTER", "state": "TX",
         "total_performance_score": "38",
         "state_average_total_performance_score": "54",
         "national_average_total_performance_score": "54",
         "payment_reduction_percentage": "1.0%", "source_endpoint": tps_sf},
    ])
    upsert("provider_data", "dialysis_state_averages", [
        {"record_key": "TX", "state": "TX",
         "percentage_of_adult_hd_patients_with_ktv12": "97.0",
         "percentage_of_adult_pd_patients_with_ktv17": "89.0",
         "percentage_of_adult_patients_with_long_term_catheter_in_use": "16.0",
         "percentage_of_patients_with_hgb10_gdl_state": "11.0",
         "source_endpoint": _sf("provider_data_dialysis_state_averages")}])
    upsert("provider_data", "dialysis_national_averages", [
        {"record_key": "NATION", "country": "NATION",
         "percentage_of_adult_hd_patients_with_ktv12": "96.0",
         "percentage_of_adult_pd_patients_with_ktv17": "88.0",
         "percentage_of_adult_patients_with_long_term_catheter_in_use": "19.0",
         "percentage_of_patients_with_hgb10_gdl_us": "12.0",
         "source_endpoint": _sf("provider_data_dialysis_national_averages")}])
    upsert("provider_data", "ich_cahps_state", [
        {"record_key": "TX", "state": "TX",
         "linearized_score_of_nephrologists_communication_and_caring": "81.0",
         "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9":
             "80.0",
         "linearized_score_of_rating_of_the_nephrologist": "84.0",
         "linearized_score_of_rating_of_the_dialysis_center_staff": "87.0",
         "linearized_score_of_rating_of_the_dialysis_facility": "88.0",
         "survey_response_rate": "21.0",
         "source_endpoint": _sf("provider_data_ich_cahps_state")}])
    upsert("provider_data", "ich_cahps_national", [
        {"record_key": "NATION", "country": "NATION",
         "linearized_score_of_nephrologists_communication_and_caring": "81.0",
         "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9":
             "81.0",
         "linearized_score_of_rating_of_the_nephrologist": "84.0",
         "linearized_score_of_rating_of_the_dialysis_center_staff": "87.0",
         "linearized_score_of_rating_of_the_dialysis_facility": "88.0",
         "survey_response_rate": "24.0",
         "source_endpoint": _sf("provider_data_ich_cahps_national")}])

    # ── round-3 seeds: outpatient facility universe (section 11) ──────
    qies_sf = _sf("cms_open_data_pos_qies")
    upsert("cms_open_data", "cms_open_data_pos_qies", [
        {"row_key": "450001", "prvdr_num": "450001",
         "fac_name": "HOUSTON GENERAL", "prvdr_ctgry_cd": "01",
         "pgm_trmntn_cd": "00", "state_cd": "TX", "city_name": "HOUSTON",
         "source_endpoint": qies_sf},
        {"row_key": "451302", "prvdr_num": "451302",
         "fac_name": "HILL COUNTRY RHC", "prvdr_ctgry_cd": "12",
         "pgm_trmntn_cd": "01", "state_cd": "TX", "city_name": "MARBLE FALLS",
         "source_endpoint": qies_sf},
        {"row_key": "450990", "prvdr_num": "450990",
         "fac_name": "GULF COAST COMMUNITY HEALTH", "prvdr_ctgry_cd": "21",
         "pgm_trmntn_cd": "00", "state_cd": "TX", "city_name": "GALVESTON",
         "source_endpoint": qies_sf},
    ])
    iqies_sf = _sf("cms_open_data_pos_internet_qies")
    upsert("cms_open_data", "cms_open_data_pos_internet_qies", [
        {"row_key": "457501", "prvdr_num": "457501",
         "fac_name": "BLUEBONNET HOME HEALTH", "prvdr_type_id": "3",
         "pgm_trmntn_cd": "00", "state_cd": "TX", "city_name": "AUSTIN",
         "source_endpoint": iqies_sf},
        {"row_key": "455001", "prvdr_num": "455001",
         "fac_name": "BLUEBONNET CARE CENTER", "prvdr_type_id": "20",
         "pgm_trmntn_cd": "00", "state_cd": "TX", "city_name": "AUSTIN",
         "source_endpoint": iqies_sf},
        {"row_key": "672001", "prvdr_num": "672001",
         "fac_name": "GULF COAST DIALYSIS", "prvdr_type_id": "7",
         "pgm_trmntn_cd": "00", "state_cd": "TX", "city_name": "HOUSTON",
         "source_endpoint": iqies_sf},
        {"row_key": "459901", "prvdr_num": "459901",
         "fac_name": "LONGHORN SURGERY CENTER", "prvdr_type_id": "11",
         "pgm_trmntn_cd": "01", "state_cd": "TX", "city_name": "DALLAS",
         "source_endpoint": iqies_sf},
    ])
    upsert("provider_data", "asc_quality_state", [
        {"record_key": "TX:2024", "state": "TX", "year": "2024",
         "avg_asc9_state_rate": "77.58", "avg_asc11_state_rate": "99.40",
         "avg_asc13_state_rate": "90.66", "avg_asc14_state_rate": "0.462",
         "source_endpoint": _sf("provider_data_asc_quality_state")}])
    upsert("provider_data", "asc_quality_national", [
        {"record_key": "2024", "year": "2024",
         "avg_asc9_nat_rate": "76.95", "avg_asc11_nat_rate": "86.52",
         "avg_asc13_nat_rate": "85.97", "avg_asc14_nat_rate": "0.312",
         "source_endpoint": _sf("provider_data_asc_quality_national")}])
    mes_sf = _sf("provider_data_medical_equipment_suppliers")
    upsert("provider_data", "medical_equipment_suppliers", [
        {"record_key": "1001", "provider_id": "1001",
         "businessname": "LONE STAR HOME MEDICAL", "practicecity": "HOUSTON",
         "practicestate": "TX", "source_endpoint": mes_sf},
        {"record_key": "1002", "provider_id": "1002",
         "businessname": "ALAMO DME SUPPLY", "practicecity": "SAN ANTONIO",
         "practicestate": "TX", "source_endpoint": mes_sf},
    ])
    upsert("cms_open_data", "cms_open_data_home_infusion_therapy_providers", [
        {"row_key": "O20201116001628:75201", "enrollment_id": "O20201116001628",
         "legal_business_name": "TEXAS INFUSION PARTNERS", "city": "DALLAS",
         "state": "TX", "zip_code": "75201",
         "source_endpoint":
             _sf("cms_open_data_home_infusion_therapy_providers")}])

    qcew_sf = _sf("bls_qcew_industry_area")
    upsert("bls_qcew", "qcew_industry_area", [
        {"qcew_key": "48000:622:5:2025:4", "area_fips": "48000",
         "own_code": "5", "industry_code": "622", "agglvl_code": "55",
         "year": "2025", "qtr": "4", "month3_emplvl": "385213",
         "avg_wkly_wage": "1602", "source_endpoint": qcew_sf},
        {"qcew_key": "48201:622:5:2025:4", "area_fips": "48201",
         "own_code": "5", "industry_code": "622", "agglvl_code": "75",
         "year": "2025", "qtr": "4", "month3_emplvl": "86188",
         "avg_wkly_wage": "1946", "source_endpoint": qcew_sf},
        {"qcew_key": "48113:622:5:2025:4", "area_fips": "48113",
         "own_code": "5", "industry_code": "622", "agglvl_code": "75",
         "year": "2025", "qtr": "4", "month3_emplvl": "46694",
         "avg_wkly_wage": "1774", "source_endpoint": qcew_sf},
    ])


class SeededRenderTests(_EnvGuard):
    """Every section renders real numbers from tiny seeded stores."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        _seed_estate(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        super().setUp()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._tmp.name

    def test_all_sections_render_with_data(self):
        h = render_market_scan({"state": "TX"})
        for title in _SECTION_TITLES:
            self.assertIn(title, h, f"section {title!r} missing")
        # Section-by-section seeded markers.
        self.assertIn("30,000,000", h)                 # 1 state population
        self.assertIn("Harris County, Texas", h)       # 1 top-county table
        self.assertIn("Diagnosed diabetes", h)         # 2 PLACES measure
        self.assertIn("PANHANDLE DENTAL ACCESS", h)    # 3 worst HPSA row
        self.assertIn("$13,287.86", h)                 # 4 std spend / capita
        self.assertIn("Home Health", h)                # 4 saturation bar
        self.assertIn("Hospital overall star mix", h)  # 5 star mix
        self.assertIn("Consulting Fee", h)             # 6 payment nature
        self.assertIn("UT SOUTHWESTERN MEDICAL CENTER", h)  # 7 NIH org
        self.assertIn("1128a1", h)                     # 8 exclusion statute
        self.assertIn("Hospitals (NAICS 622)", h)      # 9 QCEW industry
        self.assertIn("$1,602.00", h)                  # 9 weekly wage 2dp
        # Section 10 — kidney & dialysis market.
        self.assertIn("state mean 3.0% across 2 counties", h)  # AgeAdjPrv only
        self.assertIn("measureid KIDNEY", h)           # 10 pinned release note
        self.assertIn("Dialysis facility five-star mix", h)
        self.assertIn("DaVita", h)                     # 10 chain bar
        self.assertIn("ESRD QIP total performance scores", h)
        self.assertIn("TX average 54 vs national 54", h)
        self.assertIn("Kt/V", h)                       # 10 clinical vs national
        self.assertIn("Rating of the dialysis facility", h)  # 10 ICH-CAHPS
        # Section 11 — outpatient facility universe.
        self.assertIn("Federally Qualified Health Center", h)  # QIES category
        self.assertIn("Ambulatory Surgical Center", h)         # iQIES type
        self.assertIn("ASC-11 Cataracts", h)
        self.assertIn("99.4%", h)                      # ASC state avg 1dp
        self.assertIn("86.5%", h)                      # ASC national avg 1dp
        self.assertIn("Medicare DMEPOS suppliers", h)
        self.assertIn("SAN ANTONIO", h)                # DME city bar
        self.assertIn("Home infusion therapy providers", h)

    def test_percentages_are_1dp_and_money_2dp(self):
        h = render_market_scan({"state": "TX"})
        self.assertIn("56.6%", h)     # MA participation from 0.5663
        self.assertIn("16.6%", h)     # uninsured rate
        self.assertIn("$67.97M", h)   # open payments total, 2dp/M

    def test_every_section_links_its_dataset_source(self):
        h = render_market_scan({"state": "TX"})
        for dataset_id in (
                "census_acs_county_profile", "cdc_data_places_county",
                "hrsa_data_hpsa_primary_care",
                "cms_open_data_geo_variation_state_county",
                "provider_data_hospital_general",
                "open_payments_state_payment_totals",
                "nih_reporter_projects", "oig_leie_exclusions",
                "bls_qcew_industry_area",
                "cdc_data_places_county_ckd",
                "provider_data_dialysis_facilities",
                "provider_data_dialysis_state_averages",
                "provider_data_dialysis_national_averages",
                "provider_data_esrd_qip_tps",
                "provider_data_ich_cahps_state",
                "provider_data_ich_cahps_national",
                "cms_open_data_pos_qies", "cms_open_data_pos_internet_qies",
                "provider_data_asc_quality_state",
                "provider_data_asc_quality_national",
                "provider_data_medical_equipment_suppliers",
                "cms_open_data_home_infusion_therapy_providers"):
            self.assertIn(f"/connector-estate?dataset={dataset_id}", h)

    def test_county_focus_scopes_sections(self):
        h = render_market_scan({"state": "TX", "county": "48201"})
        self.assertIn("County focus", h)
        self.assertIn("Harris", h)
        self.assertIn("county 48201", h)  # page meta carries the scope
        # Section 10's CKD block scopes to the county too.
        self.assertIn("CKD prevalence — county 48201", h)

    def test_bogus_county_is_dropped(self):
        for bogus in ("482", "abcde", "12345", "48201; DROP", "99999"):
            h = render_market_scan({"state": "TX", "county": bogus})
            self.assertNotIn(f"county {bogus}", h)
            self.assertIn("Market Scan", h)

    def test_bogus_state_falls_back_to_tx(self):
        for bogus in ("", "ZZ", "T'X", "<script>alert(1)</script>", "texas!"):
            h = render_market_scan({"state": bogus})
            self.assertIn("Texas (TX)", h)
            # The rejected input is never echoed back (raw or escaped).
            self.assertNotIn("alert(1)", h)
            self.assertNotIn("texas!", h)

    def test_limit_params_are_clamped_never_500(self):
        for params in (
                {"counties": "99999", "rows": "-5", "measures": "abc",
                 "orgs": str(10**9)},
                {"counties": "0", "rows": "0", "measures": "0", "orgs": "0"},
                {"rows": "1"}):
            h = render_market_scan({"state": "TX", **params})
            self.assertIn("Market Scan", h)
            for title in _SECTION_TITLES:
                self.assertIn(title, h)


class EmptyStoreTests(_EnvGuard):
    """Empty store dir → every section renders its ingest one-liner."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def test_all_sections_render_empty_states(self):
        h = render_market_scan({"state": "TX"})
        for title in _SECTION_TITLES:
            self.assertIn(title, h, f"section {title!r} missing")
        self.assertIn("not ingested", h)
        for module in _CLI_MODULES:
            self.assertIn(module, h, f"one-liner for {module} missing")
        # The census one-liner must carry the key prerequisite.
        self.assertIn("CENSUS_API_KEY", h)

    def test_empty_scan_creates_no_stray_files(self):
        render_market_scan({"state": "TX"})
        self.assertEqual(os.listdir(self._tmp.name), [])

    def test_one_liners_target_the_selected_state(self):
        h = render_market_scan({"state": "OH"})
        self.assertIn("--filter stateabbr=OH", h)
        self.assertIn("--state OH", h)
        self.assertIn("--filter state=OH", h)
        # Round-3 sections: each dataset's real filter column, verified
        # against live API samples (POS QIES is UPPER_CASE, iQIES is
        # lower_case, home infusion is Title Case, DMEPOS has no bare
        # state column).
        self.assertIn("--dataset places_county_ckd --filter stateabbr=OH", h)
        self.assertIn("--dataset dialysis_facilities --state OH", h)
        self.assertIn("--dataset esrd_qip_tps --state OH", h)
        self.assertIn("--dataset ich_cahps_state --state OH", h)
        self.assertIn("--filter STATE_CD=OH", h)
        self.assertIn("--filter state_cd=OH", h)
        self.assertIn("--dataset asc_quality_state --state OH", h)
        self.assertIn("--filter practicestate=OH", h)
        self.assertIn("--filter State=OH", h)


class UnavailableEstateTests(_EnvGuard):
    def test_full_page_empty_state_when_estate_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RCM_MC_CONNECTORS_ROOT"] = tmp  # no connectors/_spi.py
            h = render_market_scan({})
            self.assertIn("Connector estate not available", h)
            self.assertIn("ck-empty-state", h)
            self.assertIn("connectors.cli", h)


class HttpRouteTests(_EnvGuard):
    @classmethod
    def setUpClass(cls):
        import threading
        import time

        from rcm_mc.server import build_server

        cls._stores = tempfile.TemporaryDirectory()
        _seed_estate(cls._stores.name)
        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            cls._port = s.getsockname()[1]
        srv, _ = build_server(port=cls._port,
                              db_path=os.path.join(cls._tmp.name, "p.db"),
                              host="127.0.0.1")
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()
        cls._stores.cleanup()

    def setUp(self):
        super().setUp()
        os.environ["RCM_MC_CONNECTORS_DB"] = self._stores.name

    def _get(self, path):
        import urllib.error
        import urllib.request
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{path}", timeout=10)
        except urllib.error.HTTPError as exc:
            return exc

    def test_serves_200_with_every_section(self):
        resp = self._get("/market-scan")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Market Scan", body)
        for title in _SECTION_TITLES:
            self.assertIn(title, body)

    def test_state_and_county_params_serve_200(self):
        resp = self._get("/market-scan?state=TX&county=48201&rows=5")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("county 48201", body)
        self.assertIn("Harris", body)

    def test_hostile_params_serve_200_not_500(self):
        resp = self._get("/market-scan?state=%3Cscript%3E&county=..%2F..&rows=1e9")
        self.assertEqual(resp.status, 200)
        self.assertNotIn("<script>alert", resp.read().decode())


class WiringTests(unittest.TestCase):
    def test_route_in_nav_palette_and_breadcrumb(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES,
            _SUB_NAV,
            _resolve_sub_section,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/market-scan", routes)
        research = {e["href"] for e in _SUB_NAV["research"]}
        self.assertIn("/market-scan", research)
        self.assertEqual(_resolve_sub_section("/market-scan"), "research")


if __name__ == "__main__":
    unittest.main()
