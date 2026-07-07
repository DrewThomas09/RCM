"""Canonical Provider Data Catalog tables + an idempotent SQLite store.

Thirty-six normalization targets:

  provider_data_catalog — every dataset in the DKAN metastore catalog
                          (234 live on 2026-07-06), keyed by the 4x4
                          ``identifier``. ``discover()`` syncs it.
  34 curated tables     — the flagship Care Compare datasets (hospitals,
                          nursing homes, SNF/HHA/hospice, dialysis +
                          ICH CAHPS + ESRD QIP, IRF/LTCH, clinicians,
                          ASC quality/OAS CAHPS, outpatient imaging,
                          equipment suppliers), each keyed by a composed
                          ``record_key`` built from the dataset's natural
                          id fields in the normalizer.
  provider_data_rows    — generic JSON rows for *any* catalog dataset,
                          keyed by ``"{dataset_key}:{row_idx}"``.

Curated column tuples below were locked from a LIVE sample of each
dataset's datastore on 2026-07-06 and snake-cased with
``normalize._snake`` (which also runs at ingest, so schema and mapping
cannot drift apart). Everything is stored TEXT except ``row_idx``
(declared INTEGER so paging order sorts numerically — SQLite's INTEGER
affinity converts the stringified value on insert, so the shared
``_coerce`` path stays untouched).

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the native id** so a re-run
never double-counts — idempotency is enforced at the table, not the
caller. All SQL is parameterised; the column lists below are the only
interpolated identifiers and they are module constants, never user input.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class TableDef:
    name: str
    pk: str
    columns: Tuple[str, ...]   # all columns incl. pk, in order
    # Columns that should carry INTEGER affinity instead of TEXT (used
    # only by provider_data_rows.row_idx so numeric ordering works).
    int_cols: Tuple[str, ...] = ()

    def create_sql(self) -> str:
        cols = []
        for c in self.columns:
            if c == self.pk:
                cols.append(f"{c} TEXT PRIMARY KEY")
            elif c in self.int_cols:
                cols.append(f"{c} INTEGER")
            else:
                cols.append(f"{c} TEXT")
        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n  " + ",\n  ".join(cols) + "\n)"

    def upsert_sql(self) -> str:
        cols = ", ".join(self.columns)
        placeholders = ", ".join("?" for _ in self.columns)
        updates = ", ".join(
            f"{c}=excluded.{c}" for c in self.columns if c != self.pk
        )
        return (
            f"INSERT INTO {self.name} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT({self.pk}) DO UPDATE SET {updates}"
        )


# ── Canonical schema ──────────────────────────────────────────────────
_META = ("source_endpoint", "ingested_at")

# Column tuples locked from a live sample of each dataset's datastore
# (GET /api/1/datastore/query/{identifier}/0?limit=2) on 2026-07-06,
# lower/snake-cased via normalize._snake. Regenerate by re-probing.
_CURATED_COLUMNS: Dict[str, Tuple[str, ...]] = {
    # xubh-q36u — 38 live columns
    "hospital_general": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "hospital_type",
        "hospital_ownership", "emergency_services",
        "meets_criteria_for_birthing_friendly_designation",
        "hospital_overall_rating", "hospital_overall_rating_footnote",
        "mort_group_measure_count", "count_of_facility_mort_measures",
        "count_of_mort_measures_better",
        "count_of_mort_measures_no_different",
        "count_of_mort_measures_worse", "mort_group_footnote",
        "safety_group_measure_count", "count_of_facility_safety_measures",
        "count_of_safety_measures_better",
        "count_of_safety_measures_no_different",
        "count_of_safety_measures_worse", "safety_group_footnote",
        "readm_group_measure_count", "count_of_facility_readm_measures",
        "count_of_readm_measures_better",
        "count_of_readm_measures_no_different",
        "count_of_readm_measures_worse", "readm_group_footnote",
        "pt_exp_group_measure_count", "count_of_facility_pt_exp_measures",
        "pt_exp_group_footnote", "te_group_measure_count",
        "count_of_facility_te_measures", "te_group_footnote",
    ),
    # dgck-syfz — 22 live columns
    "hcahps_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "hcahps_measure_id",
        "hcahps_question", "hcahps_answer_description",
        "patient_survey_star_rating", "patient_survey_star_rating_footnote",
        "hcahps_answer_percent", "hcahps_answer_percent_footnote",
        "hcahps_linear_mean_value", "number_of_completed_surveys",
        "number_of_completed_surveys_footnote",
        "survey_response_rate_percent",
        "survey_response_rate_percent_footnote", "start_date", "end_date",
    ),
    # ynj2-r877 — 18 live columns
    "complications_deaths_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "measure_id",
        "measure_name", "compared_to_national", "denominator", "score",
        "lower_estimate", "higher_estimate", "footnote", "start_date",
        "end_date",
    ),
    # yv7e-xc69 — 16 live columns
    "timely_effective_care_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "condition",
        "measure_id", "measure_name", "score", "sample", "footnote",
        "start_date", "end_date",
    ),
    # 632h-zaca — 20 live columns
    "unplanned_visits_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "measure_id",
        "measure_name", "compared_to_national", "denominator", "score",
        "lower_estimate", "higher_estimate", "number_of_patients",
        "number_of_patients_returned", "footnote", "start_date", "end_date",
    ),
    # rrqw-56er — 14 live columns
    "mspb_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "measure_id",
        "measure_name", "score", "footnote", "start_date", "end_date",
    ),
    # wkfw-kthe — 14 live columns
    "imaging_efficiency_hospital": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number", "measure_id",
        "measure_name", "score", "footnote", "start_date", "end_date",
    ),
    # 4pq5-n9py — 99 live columns
    "nursing_home_provider_info": (
        "cms_certification_number_ccn", "provider_name", "provider_address",
        "citytown", "state", "zip_code", "telephone_number",
        "provider_ssa_county_code", "countyparish", "urban",
        "ownership_type", "number_of_certified_beds",
        "average_number_of_residents_per_day",
        "average_number_of_residents_per_day_footnote", "provider_type",
        "provider_resides_in_hospital", "legal_business_name",
        "date_first_approved_to_provide_medicare_and_medicaid_services",
        "chain_name", "chain_id", "number_of_facilities_in_chain",
        "chain_average_overall_5star_rating",
        "chain_average_health_inspection_rating",
        "chain_average_staffing_rating", "chain_average_qm_rating",
        "continuing_care_retirement_community", "special_focus_status",
        "abuse_icon", "most_recent_health_inspection_more_than_2_years_ago",
        "provider_changed_ownership_in_last_12_months",
        "with_a_resident_and_family_council",
        "automatic_sprinkler_systems_in_all_required_areas",
        "overall_rating", "overall_rating_footnote",
        "health_inspection_rating", "health_inspection_rating_footnote",
        "qm_rating", "qm_rating_footnote", "longstay_qm_rating",
        "longstay_qm_rating_footnote", "shortstay_qm_rating",
        "shortstay_qm_rating_footnote", "staffing_rating",
        "staffing_rating_footnote", "reported_staffing_footnote",
        "physical_therapist_staffing_footnote",
        "reported_nurse_aide_staffing_hours_per_resident_per_day",
        "reported_lpn_staffing_hours_per_resident_per_day",
        "reported_rn_staffing_hours_per_resident_per_day",
        "reported_licensed_staffing_hours_per_resident_per_day",
        "reported_total_nurse_staffing_hours_per_resident_per_day",
        "total_number_of_nurse_staff_hours_per_resident_per_day_on_t_4a14",
        "registered_nurse_hours_per_resident_per_day_on_the_weekend",
        "reported_physical_therapist_staffing_hours_per_resident_per_day",
        "total_nursing_staff_turnover",
        "total_nursing_staff_turnover_footnote", "registered_nurse_turnover",
        "registered_nurse_turnover_footnote",
        "number_of_administrators_who_have_left_the_nursing_home",
        "administrator_turnover_footnote", "nursing_casemix_index",
        "nursing_casemix_index_ratio",
        "casemix_nurse_aide_staffing_hours_per_resident_per_day",
        "casemix_lpn_staffing_hours_per_resident_per_day",
        "casemix_rn_staffing_hours_per_resident_per_day",
        "casemix_total_nurse_staffing_hours_per_resident_per_day",
        "casemix_weekend_total_nurse_staffing_hours_per_resident_per_day",
        "adjusted_nurse_aide_staffing_hours_per_resident_per_day",
        "adjusted_lpn_staffing_hours_per_resident_per_day",
        "adjusted_rn_staffing_hours_per_resident_per_day",
        "adjusted_total_nurse_staffing_hours_per_resident_per_day",
        "adjusted_weekend_total_nurse_staffing_hours_per_resident_per_day",
        "rating_cycle_1_standard_survey_health_date",
        "rating_cycle_1_total_number_of_health_deficiencies",
        "rating_cycle_1_number_of_standard_health_deficiencies",
        "rating_cycle_1_number_of_complaint_health_deficiencies",
        "rating_cycle_1_health_deficiency_score",
        "rating_cycle_1_number_of_health_revisits",
        "rating_cycle_1_health_revisit_score",
        "rating_cycle_1_total_health_score",
        "rating_cycle_2_standard_health_survey_date",
        "rating_cycle_23_total_number_of_health_deficiencies",
        "rating_cycle_2_number_of_standard_health_deficiencies",
        "rating_cycle_23_number_of_complaint_health_deficiencies",
        "rating_cycle_23_health_deficiency_score",
        "rating_cycle_23_number_of_health_revisits",
        "rating_cycle_23_health_revisit_score",
        "rating_cycle_23_total_health_score",
        "total_weighted_health_survey_score",
        "number_of_citations_from_infection_control_inspections",
        "number_of_fines", "total_amount_of_fines_in_dollars",
        "number_of_payment_denials", "total_number_of_penalties", "location",
        "latitude", "longitude", "geocoding_footnote", "processing_date",
    ),
    # g6vv-u9sr — 14 live columns
    "nursing_home_penalties": (
        "cms_certification_number_ccn", "provider_name", "provider_address",
        "citytown", "state", "zip_code", "penalty_date", "penalty_type",
        "fine_id", "fine_amount", "payment_denial_start_date",
        "payment_denial_length_in_days", "location", "processing_date",
    ),
    # djen-97ju — 23 live columns
    "mds_quality_measures": (
        "cms_certification_number_ccn", "provider_name", "provider_address",
        "citytown", "state", "zip_code", "measure_code",
        "measure_description", "resident_type", "q1_measure_score",
        "footnote_for_q1_measure_score", "q2_measure_score",
        "footnote_for_q2_measure_score", "q3_measure_score",
        "footnote_for_q3_measure_score", "q4_measure_score",
        "footnote_for_q4_measure_score", "four_quarter_average_score",
        "footnote_for_four_quarter_average_score",
        "used_in_quality_measure_five_star_rating", "measure_period",
        "location", "processing_date",
    ),
    # fykj-qjee — 16 live columns
    "snf_qrp_provider": (
        "cms_certification_number_ccn", "provider_name", "address_line_1",
        "citytown", "state", "zip_code", "countyparish", "telephone_number",
        "cms_region", "measure_code", "score", "footnote", "start_date",
        "end_date", "measure_date_range", "location1",
    ),
    # 6jpm-sxkc — 96 live columns
    "home_health_agencies": (
        "state", "cms_certification_number_ccn", "provider_name", "address",
        "citytown", "zip_code", "telephone_number", "type_of_ownership",
        "offers_nursing_care_services", "offers_physical_therapy_services",
        "offers_occupational_therapy_services",
        "offers_speech_pathology_services", "offers_medical_social_services",
        "offers_home_health_aide_services", "certification_date",
        "quality_of_patient_care_star_rating",
        "footnote_for_quality_of_patient_care_star_rating",
        "numerator_for_how_often_the_home_health_team_began_their_pa_ada1",
        "denominator_for_how_often_the_home_health_team_began_their_9354",
        "how_often_the_home_health_team_began_their_patients_care_in_d440",
        "footnote_for_how_often_the_home_health_team_began_their_pat_6aee",
        "numerator_for_how_often_the_home_health_team_determined_whe_72da",
        "denominator_for_how_often_the_home_health_team_determined_w_81bc",
        "how_often_the_home_health_team_determined_whether_patients_4505",
        "footnote_for_how_often_the_home_health_team_determined_whet_5002",
        "numerator_for_how_often_patients_got_better_at_walking_or_m_3b64",
        "denominator_for_how_often_patients_got_better_at_walking_or_b3eb",
        "how_often_patients_got_better_at_walking_or_moving_around",
        "footnote_for_how_often_patients_got_better_at_walking_or_mo_e2ff",
        "numerator_for_how_often_patients_got_better_at_getting_in_a_e863",
        "denominator_for_how_often_patients_got_better_at_getting_in_4b7a",
        "how_often_patients_got_better_at_getting_in_and_out_of_bed",
        "footnote_for_how_often_patients_got_better_at_getting_in_an_7940",
        "numerator_for_how_often_patients_got_better_at_bathing",
        "denominator_for_how_often_patients_got_better_at_bathing",
        "how_often_patients_got_better_at_bathing",
        "footnote_for_how_often_patients_got_better_at_bathing",
        "numerator_for_how_often_patients_breathing_improved",
        "denominator_for_how_often_patients_breathing_improved",
        "how_often_patients_breathing_improved",
        "footnote_for_how_often_patients_breathing_improved",
        "numerator_for_how_often_patients_got_better_at_taking_their_2828",
        "denominator_for_how_often_patients_got_better_at_taking_the_0424",
        "how_often_patients_got_better_at_taking_their_drugs_correct_bd88",
        "footnote_for_how_often_patients_got_better_at_taking_their_dd00",
        "numerator_for_changes_in_skin_integrity_postacute_care_pres_bea9",
        "denominator_for_changes_in_skin_integrity_postacute_care_pr_7aaf",
        "changes_in_skin_integrity_postacute_care_pressure_ulcerinjury",
        "footnote_changes_in_skin_integrity_postacute_care_pressure_d758",
        "numerator_for_how_often_physicianrecommended_actions_to_add_ab2a",
        "denominator_for_how_often_physicianrecommended_actions_to_a_67ae",
        "how_often_physicianrecommended_actions_to_address_medicatio_cc88",
        "footnote_for_how_often_physicianrecommended_actions_to_addr_0c32",
        "numerator_for_percent_of_residents_experiencing_one_or_more_cca9",
        "denominator_for_percent_of_residents_experiencing_one_or_mo_e12a",
        "percent_of_residents_experiencing_one_or_more_falls_with_ma_34b8",
        "footnote_for_percent_of_residents_experiencing_one_or_more_4fe2",
        "numerator_for_discharge_function_score",
        "denominator_for_discharge_function_score",
        "discharge_function_score", "footnote_for_discharge_function_score",
        "numerator_for_transfer_of_health_information_to_the_provider",
        "denominator_for_transfer_of_health_information_to_the_provider",
        "transfer_of_health_information_to_the_provider",
        "footnote_for_transfer_of_health_information_to_the_provider",
        "numerator_for_transfer_of_health_information_to_the_patient",
        "denominator_for_transfer_of_health_information_to_the_patient",
        "transfer_of_health_information_to_the_patient",
        "footnote_for_transfer_of_health_information_to_the_patient",
        "dtc_numerator", "dtc_denominator", "dtc_observed_rate",
        "dtc_riskstandardized_rate", "dtc_riskstandardized_rate_lower_limit",
        "dtc_riskstandardized_rate_upper_limit",
        "dtc_performance_categorization",
        "footnote_for_dtc_riskstandardized_rate", "ppr_numerator",
        "ppr_denominator", "ppr_observed_rate", "ppr_riskstandardized_rate",
        "ppr_riskstandardized_rate_lower_limit",
        "ppr_riskstandardized_rate_upper_limit",
        "ppr_performance_categorization",
        "footnote_for_ppr_riskstandardized_rate", "pph_numerator",
        "pph_denominator", "pph_observed_rate", "pph_riskstandardized_rate",
        "pph_riskstandardized_rate_lower_limit",
        "pph_riskstandardized_rate_upper_limit",
        "pph_performance_categorization",
        "footnote_for_pph_riskstandardized_rate",
        "how_much_medicare_spends_on_an_episode_of_care_at_this_agen_56e6",
        "footnote_for_how_much_medicare_spends_on_an_episode_of_care_5dfd",
        "no_of_episodes_to_calc_how_much_medicare_spends_per_episode_4f4e",
    ),
    # 252m-zfp9 — 15 live columns
    "hospice_provider": (
        "cms_certification_number_ccn", "facility_name", "address_line_1",
        "address_line_2", "citytown", "state", "zip_code", "countyparish",
        "telephone_number", "cms_region", "measure_code", "measure_name",
        "score", "footnote", "measure_date_range",
    ),
    # yc9t-dgbk — 12 live columns
    "hospice_general": (
        "cms_certification_number_ccn", "facility_name", "address_line_1",
        "address_line_2", "citytown", "state", "zip_code", "countyparish",
        "telephone_number", "cms_region", "ownership_type",
        "certification_date",
    ),
    # 23ew-n7w9 — 142 live columns
    "dialysis_facilities": (
        "cms_certification_number_ccn", "network", "facility_name",
        "five_star_date", "five_star", "five_star_data_availability_code",
        "address_line_1", "address_line_2", "citytown", "state", "zip_code",
        "countyparish", "telephone_number", "profit_or_nonprofit",
        "chain_owned", "chain_organization", "late_shift",
        "of_dialysis_stations", "offers_incenter_hemodialysis",
        "offers_peritoneal_dialysis", "offers_home_hemodialysis_training",
        "certification_date", "claims_date", "eqrs_date", "smr_date",
        "patient_survival_category_text",
        "patient_survival_data_availability_code",
        "number_of_patients_included_in_survival_summary",
        "mortality_rate_facility",
        "mortality_rate_upper_confidence_limit_975",
        "mortality_rate_lower_confidence_limit_25", "shr_date",
        "patient_hospitalization_category_text",
        "patient_hospitalization_data_availability_code",
        "number_of_patients_included_in_hospitalization_summary",
        "hospitalization_rate_facility",
        "hospitalization_rate_upper_confidence_limit_975",
        "hospitalization_rate_lower_confidence_limit_25", "srr_date",
        "patient_hospital_readmission_category",
        "patient_hospital_readmission_data_availability_code",
        "number_of_hospitalizations_included_in_hospital_readmission_fc2b",
        "readmission_rate_facility",
        "readmission_rate_upper_confidence_limit_975",
        "readmission_rate_lower_confidence_limit_25", "strr_date",
        "patient_transfusion_category_text",
        "patient_transfusion_data_availability_code",
        "number_of_patients_included_in_the_transfusion_summary",
        "transfusion_rate_facility",
        "transfusion_rate_upper_confidence_limit_975",
        "transfusion_rate_lower_confidence_limit_25", "fyswr_date",
        "fyswr_category_text",
        "patient_transplant_waitlist_data_availability_code",
        "number_of_patients_in_this_facility_for_fyswr",
        "first_year_standardized_kidney_transplant_waitlist_ratio",
        "n_95_ci_upper_limit_for_fyswr", "n_95_ci_lower_limit_for_fyswr",
        "pppw_category_text",
        "patient_prevalent_transplant_waitlist_data_availability_code",
        "number_of_patients_for_pppw",
        "percentage_of_prevalent_patients_waitlisted_for_kidney_tran_ecca",
        "n_95_ci_upper_limit_for_pppw", "n_95_ci_lower_limit_for_pppw",
        "sedr_date", "sedr_category_text",
        "emergency_department_encounter_data_availability_code",
        "number_of_patients_included_in_sedr_summary",
        "standardized_ed_visits_ratio_facility",
        "sedr_upper_confidence_limit_975", "sedr_lower_confidence_limit_25",
        "ed30_date", "ed30_category_text",
        "emergency_department_encounter_ratio_occurring_within_30_da_f8e3",
        "number_of_hospitalizations_included_in_ed30_summary",
        "standardized_ed_visits_within_30_days_of_hospital_discharge_6307",
        "ed30_upper_confidence_limit_975", "ed30_lower_confidence_limit_25",
        "years_modality_switch_based_upon",
        "smosr_classification_category_facility",
        "modality_switch_data_availability_code",
        "smosr_number_of_eligible_patients_facility",
        "smosr_standardized_modality_switch_ratio_facility",
        "smosr_upper_confidence_limit_facility",
        "smosr_lower_confidence_limit_facility", "sir_date",
        "patient_infection_category_text",
        "patient_infection_data_availability_code",
        "standard_infection_ratio", "sir_upper_confidence_limit_975",
        "sir_lower_confidence_limit_25", "fistula_category_text",
        "fistula_data_availability_code",
        "number_of_patients_included_in_fistula_summary",
        "fistula_rate_facility", "fistula_rate_upper_confidence_limit_975",
        "fistula_rate_lower_confidence_limit_25",
        "hcp_vaccination_data_collection_dates",
        "hcp_vaccination_data_availability_code",
        "healthcare_worker_covid19_vaccination_adherence_percentage",
        "adult_hd_ktv_data_availability_code",
        "number_of_adult_hd_patients_with_ktv_data",
        "number_of_adult_hd_patientmonths_with_ktv_data",
        "percent_of_adult_hd_patients_with_ktv_12",
        "adult_pd_ktv_data_availability_code",
        "number_of_adult_pd_patients_with_ktv_data",
        "number_of_adult_pd_patientmonths_with_ktv_data",
        "percentage_of_adult_pd_pts_with_ktv_17",
        "pediatric_hd_ktv_data_availability_code",
        "number_of_pediatric_hd_patients_with_ktv_data",
        "number_of_pediatric_hd_patientmonths_with_ktv_data",
        "percentage_of_pediatric_hd_patients_with_ktv_12",
        "pediatric_pd_ktv_data_availability_code",
        "number_of_pediatric_pd_patients_with_ktv_data",
        "number_of_pediatric_pd_patientmonths_with_ktv_data",
        "percentage_of_pediatric_pd_patients_with_ktv18",
        "percentage_of_medicare_patients_with_hgb10_gdl",
        "hgb10_data_availability_code",
        "percentage_of_medicare_patients_with_hgb12_gdl",
        "hgb_12_data_availability_code",
        "number_of_dialysis_patients_with_hgb_data",
        "hypercalcemia_data_availability_code",
        "number_of_patients_in_hypercalcemia_summary",
        "number_of_patientmonths_in_hypercalcemia_summary",
        "percentage_of_adult_patients_with_hypercalcemia_serum_calci_044d",
        "serum_phosphorus_data_availability_code",
        "number_of_patients_in_serum_phosphorus_summary",
        "number_of_patientmonths_in_serum_phosphorus_summary",
        "percentage_of_adult_patients_with_serum_phosphorus_less_tha_c222",
        "percentage_of_adult_patients_with_serum_phosphorus_between_85e8",
        "percentage_of_adult_patients_with_serum_phosphorus_between_fad7",
        "percentage_of_adult_patients_with_serum_phosphorus_between_ff32",
        "percentage_of_adult_patients_with_serum_phosphorus_greater_d8e3",
        "long_term_catheter_data_availability_code",
        "number_of_patients_in_long_term_catheter_summary",
        "number_of_patient_months_in_long_term_catheter_summary",
        "percentage_of_adult_patients_with_long_term_catheter_in_use",
        "npcr_data_availability_code", "number_of_patients_in_npcr_summary",
        "number_of_patientmonths_in_npcr_summary",
        "percentage_of_pediatric_hd_patients_with_npcr",
    ),
    # 7t8x-u3ir — 12 live columns
    "irf_general": (
        "cms_certification_number_ccn", "provider_name", "address_line_1",
        "address_line_2", "citytown", "state", "zip_code", "countyparish",
        "telephone_number", "cms_region", "ownership_type",
        "certification_date",
    ),
    # azum-44iv — 13 live columns
    "ltch_general": (
        "cms_certification_number_ccn", "provider_name", "address_line_1",
        "address_line_2", "citytown", "state", "zip_code", "countyparish",
        "telephone_number", "cms_region", "ownership_type",
        "certification_date", "total_number_of_beds",
    ),
    # mj5m-pzi6 — 31 live columns
    "dac_national": (
        "npi", "ind_pac_id", "ind_enrl_id", "provider_last_name",
        "provider_first_name", "provider_middle_name", "suff", "gndr",
        "cred", "med_sch", "grd_yr", "pri_spec", "sec_spec_1", "sec_spec_2",
        "sec_spec_3", "sec_spec_4", "sec_spec_all", "telehlth",
        "facility_name", "org_pac_id", "num_org_mem", "adr_ln_1", "adr_ln_2",
        "ln_2_sprs", "citytown", "state", "zip_code", "telephone_number",
        "ind_assgn", "grp_assgn", "adrs_id",
    ),
    # 2fpu-cgbb — 49 live columns
    "dialysis_state_averages": (
        "state", "survival_better_than_expected_state",
        "survival_as_expected_state", "survival_worse_than_expected_state",
        "hospitalizations_better_than_expected_state",
        "hospitalizations_as_expected_state",
        "hospitalizations_worse_than_expected_state",
        "hospital_readmission_better_than_expected_state",
        "hospital_readmission_as_expected_state",
        "hospital_readmission_worse_than_expected_state",
        "transfusions_better_than_expected_state",
        "transfusions_as_expected_state",
        "transfusions_worse_than_expected_state",
        "infection_better_than_expected_state", "infection_as_expected_state",
        "infection_worse_than_expected_state",
        "percentage_of_adult_hd_patients_with_ktv12",
        "percentage_of_adult_pd_patients_with_ktv17",
        "percentage_of_pediatric_hd_patients_with_ktv12",
        "percentage_of_pediatric_pd_patients_with_ktv18",
        "percentage_of_pediatric_hd_patients_with_npcr_in_use",
        "fistula_rate_better_than_expected_state",
        "fistula_rate_as_expected_state",
        "fistula_rate_worse_than_expected_state",
        "percentage_of_adult_patients_with_long_term_catheter_in_use",
        "percentage_of_adult_patients_with_hypercalcemia_serum_calci_044d",
        "percentage_of_adult_patients_with_serum_phosphorus_less_tha_c222",
        "percentage_of_adult_patients_with_serum_phosphorus_between_85e8",
        "percentage_of_adult_patients_with_serum_phosphorus_between_fad7",
        "percentage_of_adult_patients_with_serum_phosphorus_between_ff32",
        "percentage_of_adult_patients_with_serum_phosphorus_greater_d8e3",
        "incident_patients_transplant_waitlisting_better_than_expect_49e4",
        "incident_patients_transplant_waitlisting_as_expected_state",
        "incident_patients_transplant_waitlisting_worse_than_expect_9b13",
        "prevalent_patients_transplant_waitlisting_better_than_expec_c046",
        "prevalent_patients_transplant_waitlisting_as_expected_state",
        "prevalent_patients_transplant_waitlisting_worse_than_expec_eeb0",
        "healthcare_worker_covid19_vaccination_adherence_percentage_state",
        "percentage_of_patients_with_hgb10_gdl_state",
        "percentage_of_patients_with_hgb12_gdl_state",
        "sedr_better_than_expected_state", "sedr_as_expected_state",
        "sedr_worse_than_expected_state", "ed30_better_than_expected_state",
        "ed30_as_expected_state", "ed30_worse_than_expected_state",
        "n_for_smsr_category_1_smsrbetter_than_expected_state",
        "n_for_smsr_category_2_smsras_expected_state",
        "n_for_smsr_category_3_smsrworse_than_expected_state",
    ),
    # 2rkq-ygai — 59 live columns
    "dialysis_national_averages": (
        "country", "transfusion_rate_us",
        "transfusions_better_than_expected_us", "transfusions_as_expected_us",
        "transfusions_worse_than_expected_us",
        "percentage_of_adult_hd_patients_with_ktv12",
        "percentage_of_adult_pd_patients_with_ktv17",
        "percentage_of_pediatric_hd_patients_with_ktv12",
        "percentage_of_pediatric_pd_patients_with_ktv18",
        "percentage_of_pediatric_hd_patients_with_npcr", "fistula_rate_us",
        "fistula_rate_better_than_expected_us", "fistula_rate_as_expected_us",
        "fistula_rate_worse_than_expected_us",
        "percentage_of_adult_patients_with_long_term_catheter_in_use",
        "percentage_of_adult_patients_with_hypercalcemia_serum_calci_044d",
        "percentage_of_adult_patients_with_serum_phosphorus_less_tha_c222",
        "percentage_of_adult_patients_with_serum_phosphorus_between_85e8",
        "percentage_of_adult_patients_with_serum_phosphorus_between_fad7",
        "percentage_of_adult_patients_with_serum_phosphorus_between_ff32",
        "percentage_of_adult_patients_with_serum_phosphorus_greater_d8e3",
        "hospitalization_rate_us", "hospitalizations_better_than_expected_us",
        "hospitalizations_as_expected_us",
        "hospitalizations_worse_than_expected_us", "readmission_rate_us",
        "hospital_readmission_better_than_expected_us",
        "hospital_readmission_as_expected_us",
        "hospital_readmission_worse_than_expected_us", "mortality_rate_us",
        "survival_better_than_expected_us", "survival_as_expected_us",
        "survival_worse_than_expected_us",
        "first_year_standardized_kidney_transplant_waitlist_ratio_us",
        "incident_patients_transplant_waitlisting_better_than_expec_a24d",
        "incident_patients_transplant_waitlisting_as_expected_us",
        "incident_patients_transplant_waitlisting_worse_than_expected_us",
        "percentage_of_prevalent_patients_waitlisted_for_kidney_tran_d2f6",
        "prevalent_patients_transplant_waitlisting_better_than_expec_c0cd",
        "prevalent_patients_transplant_waitlisting_as_expected_us",
        "prevalent_patients_transplant_waitlisting_worse_than_expec_e6e9",
        "healthcare_worker_covid19_vaccination_adherence_percentage_us",
        "percentage_of_patients_with_hgb10_gdl_us",
        "percentage_of_patients_with_hgb12_gdl_us",
        "infection_better_than_expected_us", "infection_as_expected_us",
        "infection_worse_than_expected_us", "standardized_ed_visits_ratio_us",
        "sedr_better_than_expected_us", "sedr_as_expected_us",
        "sedr_worse_than_expected_us",
        "standardized_ed_visits_within_30_days_of_hospital_discharge_d0c6",
        "ed30_better_than_expected_us", "ed30_as_expected_us",
        "ed30_worse_than_expected_us", "standardized_modality_switch_ratio",
        "n_for_smsr_category_1_smsrbetter_than_expected_us",
        "n_for_smsr_category_2_smsras_expected_us",
        "n_for_smsr_category_3_smsrworse_than_expected_us",
    ),
    # 59mq-zhts — 47 live columns
    "ich_cahps_facility": (
        "cms_certification_number_ccn", "network", "facility_name",
        "address_line_1", "address_line_2", "citytown", "state", "zip_code",
        "countyparish", "telephone_number", "profit_or_nonprofit",
        "chain_owned", "chain_organization", "ichcahps_date",
        "ichcahps_data_availability_code",
        "lower_box_percent_of_patientsnephrologists_communication_an_846c",
        "middle_box_percent_of_patientsnephrologists_communication_a_2b84",
        "top_box_percent_of_patientsnephrologists_communication_and_205e",
        "linearized_score_of_nephrologists_communication_and_caring",
        "star_rating_of_nephrologists_communication_and_caring",
        "lower_box_percent_of_patientsquality_of_dialysis_center_car_997a",
        "middle_box_percent_of_patientsquality_of_dialysis_center_ca_cf52",
        "top_box_percent_of_patientsquality_of_dialysis_center_care_0710",
        "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9",
        "star_rating_of_quality_of_dialysis_center_care_and_operations",
        "lower_box_percent_of_patientsproviding_information_to_patients",
        "top_box_percent_of_patients_providing_information_to_patients",
        "linearized_score_of_providing_information_to_patients",
        "star_rating_of_providing_information_to_patients",
        "lower_box_percent_of_patientsrating_of_the_nephrologist",
        "middle_box_percent_of_patients_rating_of_the_nephrologist",
        "top_box_percent_of_patients_rating_of_the_nephrologist",
        "linearized_score_of_rating_of_the_nephrologist",
        "star_rating_of_the_nephrologist",
        "lower_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "middle_box_percent_of_patientsrating_of_the_dialysis_center_78a1",
        "top_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "linearized_score_of_rating_of_the_dialysis_center_staff",
        "star_rating_of_the_dialysis_center_staff",
        "lower_box_percent_of_patientsrating_of_the_dialysis_facility",
        "middle_box_percent_of_patientsrating_of_the_dialysis_facility",
        "top_box_percent_of_patientsrating_of_the_dialysis_facility",
        "linearized_score_of_rating_of_the_dialysis_facility",
        "star_rating_of_the_dialysis_facility",
        "total_number_of_completed_interviews_from_the_fall_and_spri_6652",
        "ich_cahps_survey_of_patients_experiences_star_rating",
        "survey_response_rate",
    ),
    # hanv-ru8h — 26 live columns
    "ich_cahps_state": (
        "state",
        "lower_box_percent_of_patientsnephrologists_communication_an_846c",
        "middle_box_percent_of_patientsnephrologists_communication_a_2b84",
        "top_box_percent_of_patientsnephrologists_communication_and_205e",
        "linearized_score_of_nephrologists_communication_and_caring",
        "lower_box_percent_of_patientsquality_of_dialysis_center_car_997a",
        "middle_box_percent_of_patientsquality_of_dialysis_center_ca_cf52",
        "top_box_percent_of_patientsquality_of_dialysis_center_care_0710",
        "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9",
        "lower_box_percent_of_patientsproviding_information_to_patients",
        "top_box_percent_of_patients_providing_information_to_patients",
        "linearized_score_of_providing_information_to_patients",
        "lower_box_percent_of_patientsrating_of_the_nephrologist",
        "middle_box_percent_of_patients_rating_of_the_nephrologist",
        "top_box_percent_of_patients_rating_of_the_nephrologist",
        "linearized_score_of_rating_of_the_nephrologist",
        "lower_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "middle_box_percent_of_patientsrating_of_the_dialysis_center_78a1",
        "top_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "linearized_score_of_rating_of_the_dialysis_center_staff",
        "lower_box_percent_of_patientsrating_of_the_dialysis_facility",
        "middle_box_percent_of_patientsrating_of_the_dialysis_facility",
        "top_box_percent_of_patientsrating_of_the_dialysis_facility",
        "linearized_score_of_rating_of_the_dialysis_facility",
        "total_number_of_completed_interviews_from_the_fall_and_spri_6652",
        "survey_response_rate",
    ),
    # utgq-v46w — 26 live columns
    "ich_cahps_national": (
        "country",
        "lower_box_percent_of_patientsnephrologists_communication_an_846c",
        "middle_box_percent_of_patientsnephrologists_communication_a_2b84",
        "top_box_percent_of_patientsnephrologists_communication_and_205e",
        "linearized_score_of_nephrologists_communication_and_caring",
        "lower_box_percent_of_patientsquality_of_dialysis_center_car_997a",
        "middle_box_percent_of_patientsquality_of_dialysis_center_ca_cf52",
        "top_box_percent_of_patientsquality_of_dialysis_center_care_0710",
        "linearized_score_of_quality_of_dialysis_center_care_and_ope_92e9",
        "lower_box_percent_of_patientsproviding_information_to_patients",
        "top_box_percent_of_patients_providing_information_to_patients",
        "linearized_score_of_providing_information_to_patients",
        "lower_box_percent_of_patientsrating_of_the_nephrologist",
        "middle_box_percent_of_patients_rating_of_the_nephrologist",
        "top_box_percent_of_patients_rating_of_the_nephrologist",
        "linearized_score_of_rating_of_the_nephrologist",
        "lower_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "middle_box_percent_of_patientsrating_of_the_dialysis_center_78a1",
        "top_box_percent_of_patientsrating_of_the_dialysis_center_staff",
        "linearized_score_of_rating_of_the_dialysis_center_staff",
        "lower_box_percent_of_patientsrating_of_the_dialysis_facility",
        "middle_box_percent_of_patientsrating_of_the_dialysis_facility",
        "top_box_percent_of_patientsrating_of_the_dialysis_facility",
        "linearized_score_of_rating_of_the_dialysis_facility",
        "total_number_of_completed_interviews_from_the_fall_and_spri_6652",
        "survey_response_rate",
    ),
    # complete_qip_data — 140 live columns
    "esrd_qip_complete": (
        "facility_name", "cms_certification_number_ccn", "alternate_ccn",
        "address", "city", "state", "zip_code", "network",
        "longterm_catheter_measure_score",
        "longterm_catheter_reason_for_no_score_see_footnotes_file",
        "longterm_catheter_achievement_measure_rate",
        "number_of_patients_included_in_longterm_catheter_measure_sc_b8e0",
        "longterm_catheter_achievement_period_numerator",
        "longterm_catheter_achievement_period_denominator",
        "longterm_catheter_improvement_measure_rate",
        "longterm_catheter_improvement_period_numerator",
        "longterm_catheter_improvement_period_denominator",
        "longterm_catheter_measure_score_applied",
        "national_average_longterm_catheter_measure_score",
        "ktv_comprehensive_measure_score",
        "ktv_comprehensive_reason_for_no_score_see_footnotes_file",
        "ktv_comprehensive_achievement_measure_rate",
        "number_of_patients_included_in_ktv_comprehensive_measure_sc_6b75",
        "ktv_comprehensive_achievement_period_numerator",
        "ktv_comprehensive_achievement_period_denominator",
        "ktv_comprehensive_improvement_measure_rate",
        "ktv_comprehensive_improvement_period_numerator",
        "ktv_comprehensive_improvement_period_denominator",
        "ktv_comprehensive_measure_score_applied",
        "national_average_ktv_comprehensive_measure_score",
        "hypercalcemia_measure_score",
        "hypercalcemia_reason_for_no_score_see_footnotes_file",
        "national_average_hypercalcemia_measure_score",
        "nhsn_bsi_measure_score",
        "nhsn_bsi_reason_for_no_score_see_footnotes_file",
        "nhsn_bsi_achievement_measure_ratio",
        "number_of_patients_included_in_nhsn_bsi_measure_score_achie_429d",
        "nhsn_bsi_achievement_period_observed_event_number",
        "nhsn_bsi_achievement_period_expected_event_number",
        "nhsn_bsi_improvement_measure_ratio",
        "nhsn_bsi_improvement_period_observed_event_number",
        "nhsn_bsi_improvement_period_expected_event_number",
        "nhsn_bsi_measure_score_applied",
        "national_average_nhsn_bsi_measure_score",
        "nhsn_dialysis_event_reporting_measure_score",
        "nhsn_dialysis_event_reason_for_no_score_see_footnotes_file",
        "nhsn_dialysis_event_reporting_number_of_months_reported",
        "ich_cahps_measure_score",
        "ich_cahps_reason_for_no_score_see_footnotes_file",
        "ich_cahps_achievement_period_count_of_completed_surveys",
        "ich_cahps_improvement_period_count_of_completed_surveys",
        "ich_cahps_measure_score_applied",
        "national_average_ich_cahps_measure_score",
        "ich_cahps_neph_comm_and_caring_achievement_rate",
        "ich_cahps_neph_comm_and_caring_improvement_rate",
        "ich_cahps_neph_comm_and_caring_measure_score_applied",
        "ich_cahps_quality_of_dialysis_care_and_ops_achievement_rate",
        "ich_cahps_quality_of_dialysis_care_and_ops_improvement_rate",
        "ich_cahps_quality_of_dialysis_care_and_ops_measure_score_applied",
        "ich_cahps_providing_info_to_patients_achievement_rate",
        "ich_cahps_providing_info_to_patients_improvement_rate",
        "ich_cahps_providing_info_to_patients_measure_score_applied",
        "ich_cahps_overall_rating_of_neph_achievement_rate",
        "ich_cahps_overall_rating_of_neph_improvement_rate",
        "ich_cahps_overall_rating_of_neph_measure_score_applied",
        "ich_cahps_overall_rating_of_dialysis_staff_achievement_rate",
        "ich_cahps_overall_rating_of_dialysis_staff_improvement_rate",
        "ich_cahps_overall_rating_of_dialysis_staff_measure_score_applied",
        "ich_cahps_overall_rating_of_dialysis_facility_achievement_rate",
        "ich_cahps_overall_rating_of_dialysis_facility_improvement_rate",
        "ich_cahps_overall_rating_of_dialysis_facility_measure_score_1a36",
        "standardized_readmission_ratio_srr_measure_score",
        "srr_reason_for_no_score_see_footnotes_file",
        "srr_achievement_measure_ratio",
        "number_of_index_discharges_in_srr_achievement_period",
        "srr_achievement_period_numerator",
        "srr_achievement_period_denominator", "srr_improvement_measure_ratio",
        "srr_improvement_period_numerator",
        "srr_improvement_period_denominator", "srr_measure_score_applied",
        "national_average_srr_measure_score",
        "standardized_transfusion_ratio_strr_measure_score",
        "strr_reason_for_no_score_see_footnotes_file",
        "strr_achievement_measure_ratio",
        "number_of_patientyears_at_risk_in_strr_achievement_period",
        "strr_achievement_period_numerator",
        "strr_achievement_period_denominator",
        "strr_improvement_measure_ratio", "strr_improvement_period_numerator",
        "strr_improvement_period_denominator", "strr_measure_score_applied",
        "national_average_strr_measure_score",
        "standardized_hospitalization_ratio_shr_measure_score",
        "shr_reason_for_no_score_see_footnotes_file",
        "shr_achievement_measure_ratio",
        "number_of_patientyears_at_risk_in_shr_achievement_period",
        "shr_achievement_period_numerator",
        "shr_achievement_period_denominator", "shr_improvement_measure_ratio",
        "shr_improvement_period_numerator",
        "shr_improvement_period_denominator", "shr_measure_score_applied",
        "national_average_shr_measure_score",
        "clinical_depression_screening_and_followup_improvement_peri_aac8",
        "clinical_depression_screening_and_followup_improvement_peri_cd2c",
        "clinical_depression_screening_and_followup_achievement_peri_14bd",
        "clinical_depression_screening_and_followup_achievement_peri_a98a",
        "clinical_depression_screening_and_followup_improvement_meas_9566",
        "clinical_depression_screening_and_followup_achievement_meas_4d3e",
        "clinical_depression_screening_and_followup_measure_score",
        "clinical_depression_screening_and_followup_reason_for_no_sc_475f",
        "clinical_depression_screening_and_followup_measure_score_applied",
        "national_average_cd_measure_score", "medrec_measure_score",
        "medrec_reason_for_no_score_see_footnotes_file",
        "national_average_medrec_measure_score",
        "pppw_achievement_period_numerator",
        "pppw_achievement_period_denominator",
        "pppw_improvement_period_numerator",
        "pppw_improvement_period_denominator", "pppw_improvement_measure_rate",
        "pppw_achievement_measure_rate", "pppw_measure_score",
        "pppw_reason_for_no_score_see_footnotes_file",
        "pppw_measure_score_applied", "national_average_pppw_measure_score",
        "covid19_hcp_measure_score",
        "covid19_hcp_reason_for_no_score_see_footnotes_file",
        "covid19_hcp_number_of_months_reported",
        "national_average_covid19_hcp_measure_score", "fche_measure_score",
        "fche_reason_for_no_score_see_footnotes_file",
        "fche_number_of_domains_reported",
        "national_average_fche_measure_score", "total_performance_score",
        "py2026_payment_reduction_percentage", "cms_certification_date",
        "ownership_as_of_december_31_2024", "date_of_ownership_record_update",
    ),
    # tps — 12 live columns
    "esrd_qip_tps": (
        "facility_name", "cms_certification_number_ccn", "alternate_ccn",
        "address", "city", "state", "zip_code", "network",
        "total_performance_score", "state_average_total_performance_score",
        "national_average_total_performance_score",
        "payment_reduction_percentage",
    ),
    # pppw — 14 live columns
    "esrd_qip_pppw": (
        "facility_name", "cms_certification_number_ccn", "alternate_ccn",
        "address", "city", "state", "zip_code", "network", "measure_name",
        "achievement_measure_rate", "pppw_measure_score",
        "pppw_reason_for_no_score_see_footnotes_file",
        "state_average_pppw_measure_score",
        "national_average_pppw_measure_score",
    ),
    # 4jcv-atw7 — 47 live columns
    "asc_quality_facility": (
        "facility_name", "facility_id", "npi", "citytown", "state", "zip_code",
        "year", "asc1_rate", "asc1_footnote", "asc2_rate", "asc2_footnote",
        "asc3_rate", "asc3_footnote", "asc4_rate", "asc4_footnote",
        "asc9_rate", "asc9_footnote", "asc11_rate", "asc11_footnote",
        "asc12_total_cases", "asc12_performance_category", "asc12_rshv_rate",
        "asc12_interval_lower_limit", "asc12_interval_upper_limit",
        "asc12_footnote", "asc13_rate", "asc13_footnote", "asc14_rate",
        "asc14_footnote", "asc17_total_cases", "asc17_performance_category",
        "asc17_rshv_rate", "asc17_interval_lower_limit",
        "asc17_interval_upper_limit", "asc17_footnote", "asc18_total_cases",
        "asc18_performance_category", "asc18_rshv_rate",
        "asc18_interval_lower_limit", "asc18_interval_upper_limit",
        "asc18_footnote", "asc19_total_cases", "asc19_performance_category",
        "asc19_rshv_rate", "asc19_interval_lower_limit",
        "asc19_interval_upper_limit", "asc19_footnote",
    ),
    # axe7-s95e — 34 live columns
    "asc_quality_state": (
        "state", "year", "avg_asc1_state_rate", "median_asc1_state_rate",
        "avg_asc2_state_rate", "median_asc2_state_rate", "avg_asc3_state_rate",
        "median_asc3_state_rate", "avg_asc4_state_rate",
        "median_asc4_state_rate", "avg_asc9_state_rate",
        "median_asc9_state_rate", "avg_asc11_state_rate",
        "median_asc11_state_rate", "asc12_better", "asc12_no_different",
        "asc12_worse", "asc12_too_small", "avg_asc13_state_rate",
        "median_asc13_state_rate", "avg_asc14_state_rate",
        "median_asc14_state_rate", "asc17_better", "asc17_no_different",
        "asc17_worse", "asc17_too_small", "asc18_better", "asc18_no_different",
        "asc18_worse", "asc18_too_small", "asc19_better", "asc19_no_different",
        "asc19_worse", "asc19_too_small",
    ),
    # wue8-3vwe — 37 live columns
    "asc_quality_national": (
        "year", "avg_asc1_nat_rate", "median_asc1_nat_rate",
        "avg_asc2_nat_rate", "median_asc2_nat_rate", "avg_asc3_nat_rate",
        "median_asc3_nat_rate", "avg_asc4_nat_rate", "median_asc4_nat_rate",
        "avg_asc9_nat_rate", "median_asc9_nat_rate", "avg_asc11_nat_rate",
        "median_asc11_nat_rate", "asc12_nat_rate", "asc12_better",
        "asc12_no_different", "asc12_worse", "asc12_too_small",
        "avg_asc13_nat_rate", "median_asc13_nat_rate", "avg_asc14_nat_rate",
        "median_asc14_nat_rate", "asc17_nat_rate", "asc17_better",
        "asc17_no_different", "asc17_worse", "asc17_too_small",
        "asc18_nat_rate", "asc18_better", "asc18_no_different", "asc18_worse",
        "asc18_too_small", "asc19_nat_rate", "asc19_better",
        "asc19_no_different", "asc19_worse", "asc19_too_small",
    ),
    # 48nr-hqxx — 30 live columns
    "oas_cahps_asc_facility": (
        "facility_id", "facility_name", "address", "citytown", "state",
        "zip_code", "countyparish", "telephone_number",
        "patients_who_reported_that_staff_definitely_gave_care_in_a_2c9f",
        "patients_who_reported_that_staff_somewhat_gave_care_in_a_pr_1fa8",
        "patients_who_reported_that_staff_did_not_give_care_in_a_pro_9b71",
        "facilities_and_staff_linear_mean_score",
        "patients_who_reported_that_staff_definitely_communicated_ab_5eaa",
        "patients_who_reported_that_staff_somewhat_communicated_abou_eae8",
        "patients_who_reported_that_staff_did_not_communicate_about_f071",
        "communication_about_your_procedure_linear_mean_score",
        "patients_who_gave_the_facility_a_rating_of_9_or_10_on_a_sca_e274",
        "patients_who_gave_the_facility_a_rating_of_7_or_8_on_a_scal_cb89",
        "patients_who_gave_the_facility_a_rating_of_0_to_6_on_a_scal_5c23",
        "patients_rating_of_the_facility_linear_mean_score",
        "patients_who_reported_yes_they_would_definitely_recommend_t_2ec6",
        "patients_who_reported_probably_yes_they_would_recommend_the_747d",
        "patients_who_reported_no_they_would_not_recommend_the_facil_6d96",
        "patients_recommending_the_facility_linear_mean_score", "footnote",
        "number_of_sampled_patients", "number_of_completed_surveys",
        "survey_response_rate_percent", "start_date", "end_date",
    ),
    # tf3h-mrrs — 21 live columns
    "oas_cahps_asc_national": (
        "patients_who_reported_that_staff_definitely_gave_care_in_a_2c9f",
        "patients_who_reported_that_staff_somewhat_gave_care_in_a_pr_1fa8",
        "patients_who_reported_that_staff_did_not_give_care_in_a_pro_9b71",
        "facilities_and_staff_linear_mean_score",
        "patients_who_reported_that_staff_definitely_communicated_ab_5eaa",
        "patients_who_reported_that_staff_somewhat_communicated_abou_eae8",
        "patients_who_reported_that_staff_did_not_communicate_about_f071",
        "communication_about_your_procedure_linear_mean_score",
        "patients_who_gave_the_facility_a_rating_of_9_or_10_on_a_sca_e274",
        "patients_who_gave_the_facility_a_rating_of_7_or_8_on_a_scal_cb89",
        "patients_who_gave_the_facility_a_rating_of_0_to_6_on_a_scal_5c23",
        "patients_rating_of_the_facility_linear_mean_score",
        "patients_who_reported_yes_they_would_definitely_recommend_t_2ec6",
        "patients_who_reported_probably_yes_they_would_recommend_the_747d",
        "patients_who_reported_no_they_would_not_recommend_the_facil_6d96",
        "patients_recommending_the_facility_linear_mean_score",
        "number_of_sampled_patients", "number_of_completed_surveys",
        "survey_response_rate_percent", "start_date", "end_date",
    ),
    # if5v-4x48 — 7 live columns
    "imaging_efficiency_state": (
        "state", "measure_id", "measure_name", "score", "footnote",
        "start_date", "end_date",
    ),
    # di9i-zzrc — 6 live columns
    "imaging_efficiency_national": (
        "measure_id", "measure_name", "score", "footnote", "start_date",
        "end_date",
    ),
    # ct36-nrcq — 17 live columns
    "medical_equipment_suppliers": (
        "provider_id", "acceptsassignement", "participationbegindate",
        "businessname", "practicename", "practiceaddress1", "practiceaddress2",
        "practicecity", "practicestate", "practicezip9code", "telephonenumber",
        "specialitieslist", "providertypelist", "supplieslist", "latitude",
        "longitude", "is_contracted_for_cba",
    ),
}


def _curated_table(name: str) -> TableDef:
    """A curated table: composed ``record_key`` pk + live columns + meta."""
    return TableDef(name, "record_key",
                    ("record_key", *_CURATED_COLUMNS[name], *_META))


TABLES: Dict[str, TableDef] = {
    "provider_data_catalog": TableDef(
        "provider_data_catalog", "identifier",
        ("identifier", "title", "description", "themes", "keywords",
         "issued", "modified", "csv_url", "landing_page", *_META),
    ),
    **{name: _curated_table(name) for name in _CURATED_COLUMNS},
    "provider_data_rows": TableDef(
        "provider_data_rows", "row_key",
        ("row_key", "dataset_key", "row_idx", "row_json", "fetched_at",
         *_META),
        int_cols=("row_idx",),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = tuple(TABLES)


class ProviderDataStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the Provider Data SQLite file directly,
    mirroring the RCM-MC convention that a single store owns the
    connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer, one worker thread per request) can share the
        # connection. Writes only happen single-threaded in the pipeline, so
        # this does not introduce a write race; WAL + busy_timeout cover the
        # rest.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.ensure_schema()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        for tdef in TABLES.values():
            cur.execute(tdef.create_sql())
        # Helpful secondary indexes for the /v1/query + lookup paths: the
        # lookup nouns each resolve by facility id / CCN / NPI, and the
        # generic table is always sliced by dataset_key.
        for name, cols in _INDEXES:
            cur.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_{cols[-1]} "
                        f"ON {name}({', '.join(cols)})")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's native PK.

        Rows are dicts of column→value; missing columns default to NULL,
        extra keys are ignored. Returns the number of rows written.
        """
        if not rows:
            return 0
        tdef = TABLES[table]
        now = _utc_now()
        sql = tdef.upsert_sql()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            self.conn.executemany(sql, params)
        return len(params)

    def replace_slice(self, table: str, dataset_key: str,
                      rows: Sequence[Dict[str, Any]], *,
                      slice_sig: str = "") -> int:
        """Atomically replace ONE dataset's slice of a shared generic table.

        A re-fetch that returns fewer rows than the previous pull would,
        under plain upserts, strand the earlier pull's trailing
        ``row_idx`` rows — served intermixed with fresh rows and counted
        by every surface, with nothing flagging the mixed vintages. One
        transaction deletes exactly the slice being re-pulled and writes
        the fresh rows (mirroring ``oig_leie``'s replace-in-transaction
        semantics), so a reader never observes a half-replaced slice.

        Slice targeting matches the normalizer's key grammar: unfiltered
        pulls key ``{dataset_key}:{row_idx}`` (one colon segment) and
        filtered pulls ``{dataset_key}:{slice_sig}:{row_idx}`` — dataset
        keys are slugs/UUIDs (never contain ``:``) and signatures are
        fixed-length hex, so the LIKE shapes below classify exactly.
        Only meaningful for the generic ``*_rows`` table.
        """
        tdef = TABLES[table]
        for needed in ("row_key", "dataset_key", "row_idx"):
            if needed not in tdef.columns:
                raise ValueError(
                    f"replace_slice targets generic row tables; {table!r} "
                    f"has no {needed!r} column")
        sql = tdef.upsert_sql()
        now = _utc_now()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            if slice_sig:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':' || ? || ':%'",
                    (dataset_key, dataset_key, slice_sig))
            else:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':%' "
                    f"AND row_key NOT LIKE ? || ':%:%'",
                    (dataset_key, dataset_key, dataset_key))
            if params:
                self.conn.executemany(sql, params)
        return len(params)

    def count(self, table: str, where: str = "", args: Sequence[Any] = ()) -> int:
        sql = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            sql += f" WHERE {where}"
        row = self.conn.execute(sql, tuple(args)).fetchone()
        return int(row["n"]) if row else 0

    def fetchall(self, sql: str, args: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self.conn.execute(sql, tuple(args)).fetchall())

    def close(self) -> None:
        self.conn.close()


# (table, index columns) pairs — module constants, never user input.
_INDEXES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("provider_data_catalog", ("title",)),
    ("hospital_general", ("facility_id",)),
    ("hospital_general", ("state",)),
    ("hcahps_hospital", ("facility_id",)),
    ("nursing_home_provider_info", ("cms_certification_number_ccn",)),
    ("nursing_home_provider_info", ("state",)),
    ("home_health_agencies", ("cms_certification_number_ccn",)),
    ("hospice_general", ("cms_certification_number_ccn",)),
    ("dialysis_facilities", ("cms_certification_number_ccn",)),
    ("dac_national", ("npi",)),
    ("ich_cahps_facility", ("cms_certification_number_ccn",)),
    ("esrd_qip_complete", ("cms_certification_number_ccn",)),
    ("esrd_qip_tps", ("cms_certification_number_ccn",)),
    ("esrd_qip_pppw", ("cms_certification_number_ccn",)),
    ("asc_quality_facility", ("facility_id",)),
    ("asc_quality_facility", ("npi",)),
    ("oas_cahps_asc_facility", ("facility_id",)),
    ("medical_equipment_suppliers", ("provider_id",)),
    ("medical_equipment_suppliers", ("practicestate",)),
    ("provider_data_rows", ("dataset_key",)),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _coerce(value: Any) -> Any:
    """SQLite stores TEXT; coerce lists/dicts to JSON and scalars to str.

    None stays None (NULL). We keep everything TEXT so the uniform
    ``/v1/query`` layer has one type model — numeric comparisons there
    cast explicitly. (row_idx is declared INTEGER: its stringified value
    regains integer storage through SQLite's INTEGER column affinity.)
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
