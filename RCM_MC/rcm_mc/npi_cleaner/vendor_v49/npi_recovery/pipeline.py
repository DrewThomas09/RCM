"""End-to-end orchestration of Steps 0-8. Pure logic + a progress callback;
the CLI and the Streamlit app both call run_pipeline()."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, candidates, config, entity, enrich, excelio, fill, grossup, hrsa340b, infer, repair, schema, splink_entity
from .clients import CMSClient, DiskCache, NPPESClient, RxNormClient, CMSAffiliationClient, CMSHospitalClient
from . import cms_rates
from .impute import ReferralImputer
from .routers import Router

GROSSUP_REASONS = {"sad", "noc", "no_partb_presence", "no_candidate"}


@dataclass
class Result:
    raw: pd.DataFrame
    std: pd.DataFrame
    mapping: dict
    map_report: pd.DataFrame
    coverage: pd.DataFrame
    coverage_before: pd.DataFrame
    repairs_log: pd.DataFrame
    blank_profile: pd.DataFrame
    route_map: pd.DataFrame
    pool_table: pd.DataFrame
    recovery: pd.DataFrame          # one row per blank
    cleaned: pd.DataFrame           # original + repaired fields + recovery columns
    entity_table: pd.DataFrame
    entity_rollup: pd.DataFrame
    provider_directory: pd.DataFrame
    drug_reference: pd.DataFrame
    coverage_340b: pd.DataFrame
    bt: dict
    grossup_table: pd.DataFrame
    filled: pd.DataFrame = field(default_factory=pd.DataFrame)        # original cols, filled + deduped
    entity_crosswalk: pd.DataFrame = field(default_factory=pd.DataFrame)  # legacy_NPI -> parent operator
    fill_summary: pd.DataFrame = field(default_factory=pd.DataFrame)  # per-column reduction
    fill_gaps: pd.DataFrame = field(default_factory=pd.DataFrame)     # cells left N/A + reason
    filled_verified: pd.DataFrame = field(default_factory=pd.DataFrame)       # direct-lookup-only output
    fill_summary_verified: pd.DataFrame = field(default_factory=pd.DataFrame)
    fill_gaps_verified: pd.DataFrame = field(default_factory=pd.DataFrame)
    blank_decomposition: pd.DataFrame = field(default_factory=pd.DataFrame)  # Ryan's 3-way blank split
    stats: dict = field(default_factory=dict)
    connector_status: list = field(default_factory=list)  # v22: per-API audit (health probe rows)
    filled_statistical_full: pd.DataFrame = field(default_factory=pd.DataFrame)  # v23: tier-3 (estimates)
    backtest_by_operator: pd.DataFrame = field(default_factory=pd.DataFrame)  # v23: per-operator leaderboard
    analytics: dict = field(default_factory=dict)  # v25: readout cuts {sheet_name: DataFrame}
    prob_calibration: dict = field(default_factory=dict)  # v43: confidence calibration + model head-to-head
    taxonomy_flags: pd.DataFrame = field(default_factory=pd.DataFrame)  # v43: incoherent recovered NPIs
    capture: dict = field(default_factory=dict)  # v43: channel/drug capture + implied band
    agreement: pd.DataFrame = field(default_factory=pd.DataFrame)  # v44: two-method agreement per blank
    agreement_summary: pd.DataFrame = field(default_factory=pd.DataFrame)  # v44: agreement rollup
    disagreement_queue: pd.DataFrame = field(default_factory=pd.DataFrame)  # v44: disagreements to review
    evidence_ledger: pd.DataFrame = field(default_factory=pd.DataFrame)  # v44: per-value audit record
    seller_request: pd.DataFrame = field(default_factory=pd.DataFrame)  # v44: prioritized data-request list
    run_manifest: dict = field(default_factory=dict)  # v44: reproducibility record
    calibrated_applied: bool = False  # v44: whether the gated calibrated swap fired
    specialty_drug_mix: pd.DataFrame = field(default_factory=pd.DataFrame)  # v48: who bills each top drug
    reassignment_recovery: pd.DataFrame = field(default_factory=pd.DataFrame)  # v49: structural billing-NPI recovery


def _noop(_msg, _frac):
    pass


def _load_mue_file(path):
    """Load an optional CMS MUE table -> {hcpcs: max_units_per_day}. Accepts any
    CSV/XLSX with an HCPCS-like column and a units/MUE column (case-insensitive).
    MUE values are published quarterly by CMS as a download, not via the API, so
    this is a supply-your-own-file hook like the 340B OPAIS loader."""
    try:
        p = str(path)
        df = pd.read_excel(p, dtype=str) if p.lower().endswith((".xlsx", ".xls")) else pd.read_csv(p, dtype=str)
    except Exception:
        return None
    if df.empty:
        return None
    cols = {c.lower().strip(): c for c in df.columns}
    code_col = next((cols[k] for k in cols if "hcpcs" in k or "code" in k), None)
    mue_col = next((cols[k] for k in cols if "mue" in k or "unit" in k or "max" in k), None)
    if not code_col or not mue_col:
        return None
    out = {}
    for _, r in df.iterrows():
        code = str(r.get(code_col, "")).strip().upper()
        val = pd.to_numeric(r.get(mue_col), errors="coerce")
        if code and pd.notna(val):
            out[code] = float(val)
    return out or None


def run_pipeline(input_path, *, cache_dir=None, top_hcpcs=40, states_filter=None,
                 do_entity=True, do_enrich=True, enrich_max_npis=2000,
                 holdout_frac=0.2, overrides=None, national=None,
                 do_repair=True, do_340b=True, hrsa_340b_file=None, mue_file=None,
                 do_fill=True, fill_max_npis=100000, do_pac_entity=True, do_infer=True,
                 do_bulk=True, bulk_cache=None, do_calibrate=True,
                 do_connectors=True, connector_max_npis=4000, connector_max_drugs=500,
                 do_open_payments=True,
                 do_splink=True,
                 do_health_audit=True,
                 do_analytics=True, analytics_granularity="zip3",
                 analytics_latest_year_only=True,
                 pharmacy_path=None, membership_index=None,
                 control_total=None, per_drug_control=None, client_gov_npis=None,
                 formulary_path=None,
                 expected_total=None, coverage_ratio=None, spend_floor=1_000_000.0,
                 asp_crosswalk=None, fda_ndc=None, dme_fee=None,
                 formulary_codes=None, therapy_map_path=None, roster_npis=None,
                 vrdc_suppressed=None, part_d_observed=None, medicaid_observed=None,
                 ma_captured=None,
                 surviving_roster=None, komodo_ffs=None, vrdc_census=None,
                 ma_encounters=None, ma_prices=None, asp_limits=None,
                 ratio_components=None, medicaid_state_ratios=None, management_ma=None,
                 payer_aliases=None, prior_rollup=None, apply_netting=False,
                 deep_clean=False, impute=None,
                 outputs="both", progress=None):
    progress = progress or _noop
    # which deliverable(s) to build. verified-only skips the entire statistical
    # recovery stack (inference, k-fold backtest, calibration, gross-up) — none
    # of which the verified output uses — so it runs much faster.
    outputs = (outputs or "both").lower()
    if outputs not in ("both", "verified", "statistical"):
        outputs = "both"
    want_verified = outputs != "statistical"
    want_statistical = outputs != "verified"
    # v44: the run options worth recording in the reproducibility manifest
    options_for_manifest = {
        "outputs": outputs, "top_hcpcs": top_hcpcs, "do_bulk": bool(do_bulk),
        "do_340b": bool(do_340b), "do_entity": bool(do_entity),
        "do_calibrate": bool(do_calibrate), "apply_netting": bool(apply_netting),
        "deep_clean": bool(deep_clean),
    }
    do_infer = do_infer and want_statistical
    # v20: probabilistic fuzzy entity linkage (Splink). Layers on top of the
    # deterministic union-find; auto-disabled if Splink/DuckDB aren't installed
    # so the one-command run is unchanged. Counts surfaced in the entity rollup
    # (match_basis == "fuzzy") and the progress log.
    use_splink = bool(do_splink and do_entity and splink_entity.splink_available())
    splink_info = {"available": splink_entity.splink_available(),
                   "version": splink_entity.splink_version(),
                   "enabled": use_splink, "fuzzy_edges": 0, "extra_merges": 0}
    cache = DiskCache(cache_dir or config.DEFAULT_CACHE_DIR)
    cms = CMSClient(cache)
    nppes = NPPESClient(cache)
    rxnorm = RxNormClient(cache)
    asp = cms_rates.ASPClient(cache)
    router = Router()

    # -- Step 0: read, detect schema, audit --------------------------------
    progress("Reading file", 0.02)
    preflight_facts = None
    coercion_tab = None
    try:
        raw = excelio.read_claims(input_path)
    except Exception as _read_err:
        # v36: the normal reader died; fall back to the resilient reader and
        # record every decision it made. A hard failure still names the layer.
        from . import preflight as _pf36
        raw, preflight_facts = _pf36.robust_read(input_path)
        if raw is None:
            raise RuntimeError(
                "input unreadable even under preflight fallback; see facts: "
                + "; ".join(f"{r['decision']}={r['value']}"
                            for _, r in preflight_facts.iterrows())) from _read_err
    try:
        from . import preflight as _pf36c
        coercion_tab = _pf36c.coercion_report(raw)
        if preflight_facts is None:
            preflight_facts = pd.DataFrame(
                [{"decision": "reader", "value": "standard reader succeeded"}])
    except Exception:
        pass
    rows_in_file = len(raw)  # authoritative input count — the number every tab must agree on
    mapping, report = schema.detect_columns(raw, overrides=overrides)
    # v36: near-miss diagnosis for anything the mapper could not place.
    column_diag_tab = None
    try:
        from . import preflight as _pf36d
        _unmatched = [k for k, v in report.items() if not v[1]]
        if _unmatched:
            column_diag_tab = _pf36d.column_diagnosis(list(raw.columns))
    except Exception:
        pass
    std = schema.standardize(raw, mapping)
    std["_claim_source"] = "medical"
    coverage_before = schema.coverage_summary(std)
    map_report = pd.DataFrame(
        [{"canonical_field": k, "matched_column": (v[1] if v[1] else "(none)"), "match_type": v[0]}
         for k, v in report.items()])

    # -- Step 0.6 (v29): pharmacy / RX dual-feed --------------------------
    # If a separate pharmacy-benefit extract is supplied, standardise it on the
    # SAME schema + J-code reference list and tag _claim_source. It is NOT unioned
    # into the recovery frame: pharmacy-benefit claims have no medical billing NPI
    # to recover (the "never populated by design" bucket), so the recovery /
    # backtest / cleaned stack stays medical-only. The pharmacy feed flows into the
    # ANALYTICS frame (channel reconciliation, growth, site, case-mix), where
    # adding the channel back is what flips the same-store decline — the readout's
    # "that erases the losses".
    std_pharmacy = None
    pharmacy_dedup = pd.DataFrame()
    if pharmacy_path:
        try:
            from . import pharmacy_feed as _pf
            progress("Reading pharmacy feed", 0.03)
            std_ph, _ph_map = _pf.read_and_standardize(pharmacy_path, overrides=overrides,
                                                       rxnorm=rxnorm, ref_dir=config.REF_DIR,
                                                       progress=lambda m, f: progress(f"Pharmacy bridge: {m}", 0.035))
            if do_repair:
                std_ph, _ph_rep, _ = repair.repair_frame(std_ph)
            std_pharmacy = std_ph
        except Exception as _e:
            pharmacy_dedup = pd.DataFrame({"metric": [f"pharmacy feed skipped: {type(_e).__name__}: {_e}"],
                                           "value": [""]})

    # -- Step 0.42 (v35, opt-in): deterministic deep clean BEFORE anything
    # else touches the frame. Apply stages only (text hygiene, money parse,
    # date parse, NDC-11); ledger and conservation proof become tabs.
    clean_ledger_tab = None
    clean_recon_tab = None
    if deep_clean:
        try:
            from . import clean_pipeline as _cp_dc
            std, _led_dc, _ = _cp_dc.run_cleaning(std, impute=(impute or None))
            clean_ledger_tab = _led_dc
            clean_recon_tab = _cp_dc.reconciliation_frame(_led_dc)
        except Exception as _e:
            clean_ledger_tab = pd.DataFrame(
                {"stage": [f"deep clean skipped: {type(_e).__name__}: {_e}"]})

    # -- Step 0.45 (v34, opt-in): net exact duplicates and matched reversal
    # pairs BEFORE anything downstream sums them. Report-only by default; this
    # block runs only under --apply-netting and stashes the audit.
    netting_applied_audit = None
    if apply_netting:
        try:
            from . import dedup as _dd_net
            _a_col = "allowed_amt" if "allowed_amt" in std.columns else None
            if _a_col:
                std, netting_applied_audit = _dd_net.apply_netting(std)
                std = std.reset_index(drop=True)
        except Exception as _e:
            netting_applied_audit = pd.DataFrame(
                {"metric": [f"netting skipped: {type(_e).__name__}: {_e}"], "value": [""]})

    # -- Step 0.5: repair fixable fields (invalid NPI, missing state, etc.) -
    progress("Repairing fields", 0.05)
    if do_repair:
        mue_map = _load_mue_file(mue_file) if mue_file else None
        std, repairs_log, repairs_per_row = repair.repair_frame(std, mue_map=mue_map)
    else:
        repairs_log = pd.DataFrame(columns=["repair", "field", "rows_fixed", "method", "example"])
        repairs_per_row = pd.Series("", index=std.index)
        std["billing_npi_original"] = std.get("billing_npi")
        std["billing_npi_invalid"] = False
        std["repairs_applied"] = ""
    coverage = schema.coverage_summary(std)

    # -- Step 0.7: NDC drug-identity (fills blank drug names, flags miscoding) --
    # Runs BEFORE routing so an NDC-resolved generic name lets the NOC router
    # classify an otherwise-unclassifiable J3490/J3590 line. Pure upside: a
    # present drug name is never overwritten, only flagged on disagreement.
    ndc_info = {}
    if do_bulk and "ndc" in std.columns and not std["ndc"].isna().all():
        progress("NDC drug-identity join", 0.085)
        std, ndc_info = enrich.apply_ndc_enrichment(std, cache_dir=bulk_cache)

    n = len(std)
    if n == 0:
        progress("Done", 1.0)
        empty = pd.DataFrame()
        return Result(
            raw=raw, std=std, mapping=mapping, map_report=map_report,
            coverage=coverage, coverage_before=coverage_before, repairs_log=repairs_log,
            blank_profile=empty, route_map=empty, pool_table=empty, recovery=empty,
            cleaned=raw.copy(), entity_table=empty, entity_rollup=empty,
            provider_directory=empty, drug_reference=empty, coverage_340b=empty,
            bt={}, grossup_table=empty,
            stats={"rows_total": 0, "rows_blank_billing": 0, "rows_recovered": 0,
                   "rows_with_repairs": 0, "field_repairs_total": 0,
                   "note": "The file had column headers but no data rows."})
    blank_mask = std["is_blank_billing"]
    n_blank = int(blank_mask.sum())
    tot_dollars = float(std["allowed_amt"].fillna(0).sum())
    blank_dollars = float(std.loc[blank_mask, "allowed_amt"].fillna(0).sum())
    progress("Auditing blanks", 0.08)

    # -- Steps 1+2: benefit + channel routing ------------------------------
    route_map = router.route_frame(std)
    benefit_of = dict(zip(route_map["hcpcs"].astype(str), route_map["benefit"]))
    channel_of = dict(zip(route_map["hcpcs"].astype(str), route_map["channel"]))

    blanks = std[blank_mask].copy()
    blanks["benefit"] = blanks["hcpcs"].map(lambda h: benefit_of.get(str(h), "part_b"))
    blanks["channel"] = blanks["hcpcs"].map(lambda h: channel_of.get(str(h), "physician"))

    blank_profile = (blanks.assign(_amt=blanks["allowed_amt"].fillna(0))
                     .groupby(["channel", "benefit"], dropna=False)
                     .agg(rows=("hcpcs", "size"), dollars=("_amt", "sum"))
                     .reset_index().sort_values("dollars", ascending=False))

    # -- Step 3: candidate pools (network) ---------------------------------
    def cand_prog(msg, f):
        progress(msg, 0.10 + 0.45 * f)
    pools, pool_table, no_partb, code_desc = candidates.build_candidate_pools(
        std, router, route_map, cms, progress=cand_prog,
        top_hcpcs=top_hcpcs, states_filter=states_filter, national=national)

    # Backfill any still-missing drug names using the live CMS descriptions.
    if code_desc and "drug_name" in std and "hcpcs" in std:
        desc = {str(k).upper(): v for k, v in code_desc.items() if v}
        dn = std["drug_name"].astype("string")
        need = dn.isna() | (dn.str.strip() == "")
        dn_fill = std.loc[need, "hcpcs"].map(lambda h: desc.get(str(h).upper(), pd.NA))
        got = dn_fill[dn_fill.notna()]
        if len(got):
            std.loc[got.index, "drug_name"] = got.values

    # -- Step 4: imputation -------------------------------------------------
    progress("Imputing billers", 0.58)
    imp = ReferralImputer().fit(std, pools=pools)
    pred = imp.predict(blanks)
    rec = blanks[["orig_row", "hcpcs", "drug_name", "referring_npi", "pos",
                  "zip3", "state", "allowed_amt", "units", "benefit", "channel"]].copy()
    rec = rec.join(pred)
    rec = rec.rename(columns={"allowed_amt": "blank_allowed", "units": "blank_units"})
    # guarantee the prediction columns exist (predict() may omit them when blanks
    # is empty, e.g. a file with no missing billing NPIs)
    for _c, _default in [("recovered_npi", pd.NA), ("recovered_top3", ""),
                         ("tier", pd.NA), ("tier_source", ""), ("attribution", ""),
                         ("confidence", pd.NA), ("support", pd.NA),
                         ("margin", pd.NA), ("demoted_near_tie", False), ("demote_reason", ""),
                         ("recovered_name", ""), ("recovered_operator", "")]:
        if _c not in rec.columns:
            rec[_c] = _default

    # assign final reason; null the biller for non-attributable slices
    def decide_reason(r):
        if r["benefit"] == "sad":
            return "sad"
        if r["benefit"] == "noc" and (pd.isna(r["recovered_npi"]) or r["tier_source"] != "in_panel"):
            return "noc"
        if str(r["hcpcs"]) in no_partb and r["tier_source"] != "in_panel":
            return "no_partb_presence"
        if pd.isna(r["recovered_npi"]):
            return "no_candidate"
        return "recovered"
    rec["reason"] = (rec.apply(decide_reason, axis=1) if len(rec)
                     else pd.Series(dtype="object"))
    nonattr = rec["reason"].isin(GROSSUP_REASONS)
    rec.loc[nonattr, ["recovered_npi", "recovered_top3", "recovered_name"]] = [pd.NA, "", ""]
    rec["mix_tier"] = np.where(nonattr, rec["reason"], rec["tier"])

    # -- Step 5: entity resolution -----------------------------------------
    if do_entity:
        def ent_prog(msg, f):
            progress(msg, 0.66 + 0.08 * f)
        ent_table, ent_rollup = entity.resolve_entities(
            rec.loc[rec["reason"] == "recovered", "recovered_npi"].dropna().tolist(),
            nppes, progress=ent_prog, enroll=cms, do_pac=do_pac_entity)
        if use_splink and not ent_table.empty:
            try:
                progress("Fuzzy entity linkage (Splink)", 0.735)
                edges = splink_entity.build_fuzzy_links(
                    ent_table["npi"].astype(str).tolist(), nppes)
                if edges:
                    before = ent_table["parent_operator"].nunique()
                    ent_table, ent_rollup = entity.merge_fuzzy_links(ent_table, edges)
                    after = ent_table["parent_operator"].nunique()
                    splink_info["fuzzy_edges"] += len(edges)
                    splink_info["extra_merges"] += max(0, before - after)
            except Exception as e:
                progress(f"(splink linkage skipped: {type(e).__name__})", 0.74)
        ent_crosswalk = entity.make_crosswalk(ent_table)
        name_map = dict(zip(ent_table["npi"].astype(str), ent_table["name"])) if not ent_table.empty else {}
        op_map = dict(zip(ent_table["npi"].astype(str), ent_table["parent_operator"])) if not ent_table.empty else {}
        rec["recovered_name"] = rec["recovered_npi"].map(lambda x: name_map.get(str(x), "")) .fillna("")
        rec["recovered_operator"] = rec["recovered_npi"].map(lambda x: op_map.get(str(x), "")).fillna("")
    else:
        ent_table = pd.DataFrame(); ent_rollup = pd.DataFrame(); ent_crosswalk = pd.DataFrame()
        rec["recovered_operator"] = ""

    # -- Step 5.4: two-hop / group inference (continuity + cluster) ---------
    # Borrow a biller from sibling rows for attributable blanks the point
    # imputer did not confidently resolve. These land in the billing column but
    # are tiered "inferred" (labelled distinctly, never a direct lookup). Runs
    # AFTER the entity rollup so cluster dominance is computed on rolled
    # operators; the gap/dominance guards live in infer.py.
    n_inf_cont = n_inf_clust = 0
    if do_infer and len(rec):
        progress("Group inference", 0.75)
        eligible = rec.index[(rec["benefit"] == "part_b") & (rec["attribution"] != "point")]
        inf_tier_name = {"inferred_continuity": "INF_continuity", "inferred_cluster": "INF_cluster"}

        def _apply_inferred(idxs, npi_series, tier, conf_series=None):
            for i in idxs:
                npi_val = str(npi_series.loc[i])
                rec.at[i, "recovered_npi"] = npi_val
                rec.at[i, "recovered_top3"] = npi_val
                rec.at[i, "attribution"] = tier
                rec.at[i, "reason"] = "recovered"
                rec.at[i, "tier"] = inf_tier_name[tier]
                rec.at[i, "tier_source"] = "inference"
                rec.at[i, "mix_tier"] = inf_tier_name[tier]
                rec.at[i, "demote_reason"] = ""
                if conf_series is not None and i in conf_series.index and pd.notna(conf_series.loc[i]):
                    rec.at[i, "confidence"] = float(conf_series.loc[i])

        cont = infer.infer_continuity(std, eligible)
        if not cont.empty:
            ci = [i for i in cont.index if i in set(eligible)]
            _apply_inferred(ci, cont["inferred_npi"], "inferred_continuity")
            n_inf_cont = len(ci)
            eligible = eligible.difference(cont.index)

        clust_crosswalk = ent_crosswalk
        if do_entity:
            # Roll the POPULATED billers that sit in clusters with eligible
            # blanks, so cluster dominance collapses sibling NPIs of one operator
            # (the CSI/Vivo case) instead of seeing them as competitors. Bounded
            # + cached, so it reuses the Step-5 lookups.
            pop_billers = infer.relevant_populated_billers(std, eligible)
            if pop_billers and len(pop_billers) <= config.INFER_ROLLUP_CAP:
                recovered_set = set(rec.loc[rec["reason"] == "recovered", "recovered_npi"].dropna().astype(str))
                ext_tbl, _ = entity.resolve_entities(sorted(pop_billers | recovered_set),
                                                     nppes, enroll=cms, do_pac=do_pac_entity)
                clust_crosswalk = entity.make_crosswalk(ext_tbl)

        clust = infer.infer_cluster(std, eligible, crosswalk=clust_crosswalk)
        if not clust.empty:
            cl = [i for i in clust.index if i in set(eligible)]
            _apply_inferred(cl, clust["inferred_npi"], "inferred_cluster", clust["dominance"])
            n_inf_clust = len(cl)

    # -- Step 5.5: enrichment (pull from every source) ---------------------
    bulk_info = {}
    if do_enrich:
        # distinct billing NPIs = original-valid + recovered
        orig_valid = std.loc[~std["is_blank_billing"] & std["billing_npi"].notna(), "billing_npi"].astype(str)
        recovered = rec.loc[rec["reason"] == "recovered", "recovered_npi"].dropna().astype(str)
        all_npis = pd.concat([orig_valid, recovered])
        distinct = all_npis.value_counts()
        if len(distinct) > enrich_max_npis:
            distinct = distinct.head(enrich_max_npis)
        def enr_prog(msg, f):
            progress(msg, 0.74 + 0.10 * f)
        provider_directory = enrich.build_provider_directory(distinct.index.tolist(), nppes, progress=enr_prog, cms=cms)
        # v7: enrich the directory from bulk LOCAL tables by vectorized join
        # (deactivation status, specialty grouping) — one merge each, not per-NPI
        # calls. Fail-soft, so an offline run just skips these columns.
        if do_bulk and not provider_directory.empty:
            provider_directory, bulk_info = enrich.apply_bulk_enrichment(
                provider_directory, cache_dir=bulk_cache, progress=progress)
        def dref_prog(msg, f):
            progress(msg, 0.84 + 0.04 * f)
        drug_reference = enrich.build_drug_reference(
            std, route_map, cms, code_desc=code_desc, progress=dref_prog,
            top_n=(top_hcpcs or 40), asp=asp)
    else:
        provider_directory = pd.DataFrame()
        drug_reference = pd.DataFrame()

    # -- Step 5.6: 340B coverage (fill blank 340B spots) -------------------
    coverage_340b = pd.DataFrame()
    if do_340b and not provider_directory.empty:
        progress("Resolving 340B status", 0.88)
        # (a) taxonomy-based eligibility signal from NPPES (always on)
        b340 = hrsa340b.build_340b_directory(provider_directory)
        # (b) authoritative registered status if an OPAIS file was supplied
        if hrsa_340b_file:
            opais_df, opais_note = hrsa340b.load_opais_file(hrsa_340b_file)
            names_by_npi = dict(zip(provider_directory["NPI"].astype(str),
                                    provider_directory["Provider_Name"]))
            reg = hrsa340b.match_registered_340b(b340["NPI"].astype(str).tolist(),
                                                 names_by_npi, opais_df)
            if not reg.empty:
                b340 = b340.merge(reg, on="NPI", how="left")
        # merge the 340B block onto the provider directory (keyed by NPI)
        provider_directory = provider_directory.merge(b340, on="NPI", how="left")
        coverage_340b = b340
        # flag 340B-arbitrage drugs on the drug reference
        if not drug_reference.empty and "HCPCS" in drug_reference:
            drug_reference["B340_Arbitrage_Flag"] = drug_reference["HCPCS"].map(hrsa340b.arbitrage_flag)

    # -- Step 6: masking backtest ------------------------------------------
    bt = {}
    if want_statistical and len(rec):
        progress("Back-testing accuracy", 0.90)
        bt_input = rec[["mix_tier", "blank_allowed"]].rename(columns={"mix_tier": "tier"}).copy()
        # carry the drug so the backtest can be honest about blanks that sit in
        # drugs the non-blank rows barely cover (pharmacy-benefit, military/VA).
        try:
            _bidx = std.index[std["is_blank_billing"]]
            if len(_bidx) == len(bt_input) and "hcpcs" in std.columns:
                bt_input["hcpcs"] = std.loc[_bidx, "hcpcs"].astype(str).values
        except Exception:
            pass
        bt = backtest.run_backtest(std, pools, bt_input, holdout_frac=holdout_frac, n_folds=config.BACKTEST_FOLDS)

    # -- Step 6.5: calibration — measured holdout accuracy overrides the tier
    # ranking. A point tier that underperforms on held-out rows is demoted to
    # best-guess, so the billing column reflects what the data actually supports.
    tier_measured, tier_spread = {}, {}
    calib_demoted = []
    if do_calibrate and want_statistical and isinstance(bt.get("per_tier"), pd.DataFrame) and not bt["per_tier"].empty and len(rec):
        pt = bt["per_tier"]
        tier_measured = {str(t): float(a) for t, a in zip(pt["tier"], pt["top1_acc"])}
        tier_spread = {str(t): float(s) for t, s in zip(pt["tier"], pt.get("top1_std", pd.Series([0.0] * len(pt))))}
        tier_rows = {str(t): int(n) for t, n in zip(pt["tier"], pt["rows"])}
        point_tiers = set(config.POINT_MIN_OBS.keys())
        for tname in point_tiers:
            acc, n = tier_measured.get(tname), tier_rows.get(tname, 0)
            if acc is None or n < config.CALIBRATION_MIN_HOLDOUT or acc >= config.POINT_MIN_MEASURED_ACC:
                continue
            sel = (rec["attribution"] == "point") & (rec["tier"].astype(str) == tname)
            if sel.any():
                tag = f"calibration_acc_{acc:.2f}<{config.POINT_MIN_MEASURED_ACC}"
                rec.loc[sel, "attribution"] = "distributional"
                rec.loc[sel, "demoted_near_tie"] = True
                prior = rec.loc[sel, "demote_reason"].astype(str).replace("nan", "")
                rec.loc[sel, "demote_reason"] = [(p + ";" + tag).lstrip(";") for p in prior]
                calib_demoted.append({"tier": tname, "measured_top1": round(acc, 3),
                                      "rows_demoted": int(sel.sum())})

    # -- Step 6.6 (v43): probability calibration + taxonomy coherence -------
    # Beyond demoting weak tiers, measure whether the STATED confidence is
    # calibrated, and fit a calibrated model as a head-to-head. Also screen the
    # recovered NPIs for taxonomy coherence against the billed drug. Both are
    # additive diagnostics; neither changes the recovered values.
    prob_calib = None
    taxonomy_flags = None
    if want_statistical and isinstance(bt.get("holdout_detail"), pd.DataFrame) and \
            "confidence" in bt["holdout_detail"].columns and len(bt["holdout_detail"]) >= 80:
        try:
            from . import recovery_model as _RM
            prob_calib = _RM.fit_and_compare(bt["holdout_detail"], std=std, mapping=mapping)
        except Exception as _e:
            prob_calib = {"status": f"error: {type(_e).__name__}: {_e}"}
    if want_statistical and len(rec) and "recovered_npi" in rec.columns:
        try:
            from . import taxonomy_coherence as _TC
            _tax_dir = None
            if isinstance(provider_directory, pd.DataFrame) and "NPI" in provider_directory.columns \
                    and "Taxonomy_Code" in provider_directory.columns:
                _tax_dir = {str(r["NPI"]): {"taxonomy_code": r["Taxonomy_Code"]}
                            for _, r in provider_directory.iterrows()}
            taxonomy_flags = _TC.coherence_screen(rec, std, ref_dir=config.REF_DIR,
                                                  mapping=mapping, directory=_tax_dir)
        except Exception:
            taxonomy_flags = None

    # -- Step 6.7 (v44): two-method agreement, gated calibrated swap, ledger -
    # Recover each blank two independent ways (in-panel pattern vs CMS pool) and
    # treat agreement as a precision signal; substitute the calibrated probability
    # for the reported confidence only when it wins on this file's holdout; and
    # assemble the evidence ledger. None of this fabricates a recovery; it
    # annotates, gates, and audits what recovery already produced.
    agreement_tbl = pd.DataFrame()
    agreement_roll = pd.DataFrame()
    disagreement_q = pd.DataFrame()
    evidence_ledger = pd.DataFrame()
    calib_applied = False
    reassignment_recovery = pd.DataFrame()
    if want_statistical and len(rec):
        try:
            from . import agreement as _AG
            blank_idx = std[std["billing_npi"].isna()].index
            agreement_tbl = _AG.two_method_table(std, imp, blank_idx)
            # v49: layer the PECOS reassignment structural method (third method)
            # when a rendering NPI is present (e.g. RIF carrier data)
            if "rendering_npi" in std.columns:
                try:
                    from . import reassignment as _RA
                    _graph = _RA.demo_graph()  # refit from real PECOS file in production
                    agreement_tbl = _RA.add_to_agreement(agreement_tbl, std, _graph, mapping)
                    reassignment_recovery = _RA.recover_from_reassignment(std, _graph, mapping)
                except Exception:
                    reassignment_recovery = pd.DataFrame()
            agreement_roll = _AG.agreement_summary(agreement_tbl, std, mapping)
            disagreement_q = _AG.disagreement_queue(agreement_tbl, std, mapping)
        except Exception:
            agreement_tbl = pd.DataFrame()

    # gated calibrated-probability swap: only if the model beat the incumbent on
    # this file's holdout (both Brier and ECE), write a calibrated_confidence
    # column and mark it applied. The incumbent confidence is always kept too.
    calib_probs_for_ledger = None
    if want_statistical and isinstance(prob_calib, dict) and prob_calib.get("model_wins"):
        try:
            from . import recovery_model as _RM2
            _feats = _RM2.build_features(rec, std=std, ref_dir=config.REF_DIR, mapping=mapping)
            _mdl = _RM2.CalibratedRecoveryModel().fit(
                _RM2.build_features(bt["holdout_detail"], std=std, mapping=mapping),
                bt["holdout_detail"]["t1"].astype(float))
            _p = _mdl.predict_proba(_feats)
            # apply the two-method agreement boost, clipped to [0,1]
            if not agreement_tbl.empty:
                _boost_map = dict(zip(agreement_tbl["row"], agreement_tbl["agreement_boost"]))
                _b = rec["orig_row"].map(_boost_map).fillna(1.0).to_numpy()
                _p = np.clip(_p * _b, 0.0, 1.0)
            rec["calibrated_confidence"] = np.round(_p, 4)
            calib_probs_for_ledger = _p
            calib_applied = True
        except Exception:
            calib_applied = False

    if want_statistical and len(rec):
        try:
            from . import ledger as _LED
            from . import run_manifest as _RMAN
            _vint = _RMAN._reference_vintages(config.REF_DIR)
            evidence_ledger = _LED.build_ledger(
                rec, repairs_log, agreement_tbl,
                calib_probs=calib_probs_for_ledger,
                vintages={"cms_utilization": _vint.get("NCCI MUE", "")}, mapping=mapping)
        except Exception:
            evidence_ledger = pd.DataFrame()
    grossup_table = pd.DataFrame()
    if want_statistical:
        progress("Sizing coverage gross-up", 0.92)
        grossup_table = grossup.build_grossup(std, rec, route_map)

    # -- Step 8: assemble cleaned claims -----------------------------------
    progress("Writing cleaned claims", 0.94)
    cleaned = _assemble_cleaned(raw, std, rec, mapping, repairs_per_row)

    # referring-NPI verification against the Order and Referring file: is each
    # referring/ordering provider actually eligible to refer for Part B? (capped)
    ref_verified = 0
    if do_enrich and "referring_npi" in std.columns:
        ref = std["referring_npi"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
        distinct_ref = [n for n in pd.unique(ref) if config.npi_is_valid(n)]
        distinct_ref = distinct_ref[:min(enrich_max_npis, 300)]
        vmap = {}
        if distinct_ref:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=16) as _ex:
                _futs = {_ex.submit(cms.order_referring_lookup, n): n for n in distinct_ref}
                for _f in as_completed(_futs):
                    vmap[_futs[_f]] = _f.result()
        ref_verified = sum(1 for v in vmap.values() if v.get("in_order_referring"))
        cleaned["Referring_In_OrderRefer"] = ref.map(
            lambda n: vmap.get(n, {}).get("in_order_referring")).values
        cleaned["Referring_Eligible_PartB"] = ref.map(
            lambda n: vmap.get(n, {}).get("can_refer_partb")).values

    # join 340B status onto each row via its final billing NPI
    if not coverage_340b.empty:
        keep = [c for c in ["NPI", "B340_Eligibility_Signal", "B340_Entity_Class",
                            "B340_Registered", "B340_ID", "B340_Entity_Type_Desc"]
                if c in coverage_340b.columns]
        b = coverage_340b[keep].drop_duplicates("NPI").rename(columns={"NPI": "_npi"})
        cleaned = cleaned.merge(b, how="left", left_on="Billing_NPI_Final", right_on="_npi")
        cleaned.drop(columns=["_npi"], inplace=True, errors="ignore")

    # -- Step 8.5: fill missing cells in the ORIGINAL file + dedupe ---------
    filled = pd.DataFrame()
    fill_summary = pd.DataFrame()
    filled_statistical_full = pd.DataFrame()
    bt_by_operator = pd.DataFrame()
    fill_gaps = pd.DataFrame()
    filled_verified = pd.DataFrame()
    fill_summary_verified = pd.DataFrame()
    fill_gaps_verified = pd.DataFrame()
    # v36: analytics reads these even when do_fill is off; default them so a
    # fill-less run cannot UnboundLocalError the whole analytics stage.
    parent_map, parent_size = {}, {}
    drug_ident, affil_map, owner_map, paid_map = {}, {}, {}, {}
    if do_fill:
        progress("Filling missing cells", 0.95)
        # every distinct NPI we may need: final billing (orig-valid + recovered) + referring
        bills = cleaned["Billing_NPI_Final"].astype("string") if "Billing_NPI_Final" in cleaned else pd.Series(dtype="string")
        refs = std["referring_npi"].astype("string") if "referring_npi" in std else pd.Series(dtype="string")
        want = pd.concat([bills, refs], ignore_index=True).dropna()
        want = [s for s in pd.unique(want) if config.npi_is_valid(s)]
        if len(want) > fill_max_npis:
            want = want[:fill_max_npis]
        def idx_prog(msg, f):
            progress(msg, 0.95 + 0.03 * f)
        npi_index = enrich.build_npi_index(want, nppes, progress=idx_prog)
        # v8: a final billing NPI deactivated AS OF the service date couldn't have
        # billed the claim — for a recovered biller that means the guess is wrong,
        # for an original it's a data anomaly. Build the lookup from the v7 bulk
        # table (cached) and let fill flag those rows for review.
        deactivated_map = {}
        if do_bulk:
            from . import bulk as _bulk
            _dt = _bulk.get_table("deactivated_npi", cache_dir=bulk_cache)
            _ddf = _dt.ensure() if _dt is not None else None
            if _ddf is not None and "npi" in _ddf.columns:
                deactivated_map = dict(zip(_ddf["npi"].astype(str), _ddf.get("deactivation_date", "")))
        # v11: authoritative direct-lookup enrichment for the verified build —
        # RxNorm drug identity (NDC/name -> ingredient + ATC class) and the CMS
        # Facility Affiliation file (NPI -> facility type + CCN). Nothing inferred.
        drug_ident, affil_map, owner_map = {}, {}, {}
        if do_connectors:
            def _con_prog(msg, f):
                progress(msg, max(0.90, min(0.99, f)))
            rxnorm = RxNormClient(cache)
            affil = CMSAffiliationClient(cache)
            hospital = CMSHospitalClient(cache)
            try:
                drug_ident, affil_map, owner_map = enrich.build_verified_connectors(
                    std, mapping, rxnorm=rxnorm, affil=affil, hospital=hospital,
                    npi_index=npi_index, max_drugs=connector_max_drugs,
                    max_npis=connector_max_npis, progress=_con_prog)
            except Exception as e:
                progress(f"(connector enrichment skipped: {type(e).__name__})", 0.94)
        # v18: CMS Open Payments — free signal for the referring/prescriber gap.
        # The physicians a drug-maker pays are the ones who prescribe/refer it, so
        # this both narrows blank referrers and flags maker<->referrer relationships.
        paid_map = {}
        if do_connectors and do_open_payments:
            try:
                from . import openpayments
                op = openpayments.OpenPaymentsClient(cache)
                _sc = (std.get("state", pd.Series(dtype=str)).dropna().astype(str))
                _sc = _sc[_sc.str.len() == 2]
                op_states = list(_sc.value_counts().head(2).index)  # top-2 states by volume
                paid_map = openpayments.build_paid_map(
                    op, drug_ident, op_states, max_drugs=connector_max_drugs,
                    progress=lambda m, f: progress(m, max(0.94, min(0.99, 0.94 + 0.04 * f))))
            except Exception as e:
                progress(f"(open payments skipped: {type(e).__name__})", 0.95)
        # v17: roll up EVERY final billing NPI (original + recovered) to its parent
        # operator, so the cleaned output carries a clean economic-owner column.
        # Reuses cached NPPES records, so it is mostly free after the directory build.
        parent_map, parent_size = {}, {}
        if do_entity and "Billing_NPI_Final" in cleaned.columns:
            try:
                all_bill = [s for s in cleaned["Billing_NPI_Final"].dropna().astype(str).unique()
                            if config.npi_is_valid(s)]
                if all_bill:
                    full_ent, _ = entity.resolve_entities(all_bill, nppes, enroll=cms, do_pac=False)
                    if use_splink and not full_ent.empty:
                        try:
                            fedges = splink_entity.build_fuzzy_links(
                                full_ent["npi"].astype(str).tolist(), nppes)
                            if fedges:
                                full_ent, _ = entity.merge_fuzzy_links(full_ent, fedges)
                        except Exception:
                            pass
                    if not full_ent.empty and "parent_operator" in full_ent.columns:
                        parent_map = dict(zip(full_ent["npi"].astype(str), full_ent["parent_operator"]))
                        sz = full_ent.groupby("parent_operator")["npi"].nunique()
                        parent_size = {npi: int(sz.get(op, 1)) for npi, op in parent_map.items()}
            except Exception as e:
                progress(f"(parent rollup skipped: {type(e).__name__})", 0.95)
        if want_statistical:
            filled, fill_summary, fill_gaps = fill.fill_workbook(raw, std, cleaned, mapping, npi_index, route_map=route_map, tier_acc=tier_measured, tier_std=tier_spread, deactivated_map=deactivated_map, drug_ident=drug_ident, affil_map=affil_map, owner_map=owner_map, parent_map=parent_map, parent_size=parent_size, paid_map=paid_map, mode="statistical")
        # verified output: direct authoritative lookups only — no inference, no
        # statistical recovery; a blank billing NPI stays N/A.
        if want_verified:
            filled_verified, fill_summary_verified, fill_gaps_verified = fill.fill_workbook(
                raw, std, cleaned, mapping, npi_index, route_map=route_map,
                drug_ident=drug_ident, affil_map=affil_map, owner_map=owner_map,
                parent_map=parent_map, parent_size=parent_size, paid_map=paid_map,
                deactivated_map=deactivated_map, mode="verified")

        # v23: tier-3 escalation — write the distributional best-guess into the
        # cells (with review flags) so the majority of missing billing cells carry
        # a value. Reuses the already-fetched directory; no new API calls.
        if want_statistical and not filled.empty:
            try:
                from . import tiers
                filled_statistical_full = tiers.escalate_to_statistical_full(
                    filled, provider_directory, mapping)
            except Exception as e:
                progress(f"(tier-3 escalation skipped: {type(e).__name__})", 0.96)
                filled_statistical_full = filled.copy()

        # v23: operator-stratified backtest leaderboard + inherit the operator's
        # measured reliability onto every recovered/best-guess row. Pure measurement.
        if want_statistical and bt.get("holdout_detail") is not None and not filled.empty:
            try:
                bt_by_operator = backtest.operator_leaderboard(
                    bt.get("holdout_detail"), bt.get("per_tier"),
                    parent_map, parent_size, filled=filled, mapping=mapping)
            except Exception as e:
                progress(f"(operator leaderboard skipped: {type(e).__name__})", 0.97)
                bt_by_operator = pd.DataFrame()
            prec_map, verd_map = {}, {}
            if not bt_by_operator.empty:
                for _, r in bt_by_operator.iterrows():
                    op = str(r.get("parent_operator", ""))
                    prec_map[op] = r.get("precision_top1", "")
                    verd_map[op] = r.get("verdict", "")
            # inherit onto each output frame independently (a hiccup on one must
            # not leave the other unpopulated); columns always exist.
            for _df in (filled, filled_statistical_full):
                if _df is None or _df.empty:
                    continue
                try:
                    _df["_Operator_Recovery_Precision"] = "\u2014"
                    _df["_Operator_Recovery_Verdict"] = "\u2014"
                    if verd_map and "_Billing_Parent_Group" in _df.columns and "_NPI_Source" in _df.columns:
                        src = _df["_NPI_Source"].astype("string").str.lower().fillna("")
                        recov = src.str.startswith(("recovered", "inferred", "best-guess", "statistical"))
                        grp = _df["_Billing_Parent_Group"].astype(str)
                        _df.loc[recov, "_Operator_Recovery_Verdict"] = grp[recov].map(verd_map).fillna("")
                        _df.loc[recov, "_Operator_Recovery_Precision"] = grp[recov].map(prec_map).fillna("")
                        unm = _df["_Operator_Recovery_Verdict"] == "UNMEASURABLE"
                        _df.loc[unm, "_Operator_Recovery_Precision"] = ""
                except Exception as e:
                    progress(f"(operator inherit skipped: {type(e).__name__})", 0.97)

    n_recovered = int((rec["reason"] == "recovered").sum())
    rec_dollars = float(rec.loc[rec["reason"] == "recovered", "blank_allowed"].fillna(0).sum())
    n_point = int(((rec["reason"] == "recovered") & (rec["attribution"] == "point")).sum())
    # how many recoveries were demoted out of the billing column for being a
    # near-tie (the "not 50/50" gate firing) — surfaced so the honest number is
    # visible, not hidden.
    n_demoted = int(rec["demoted_near_tie"].fillna(False).sum()) if "demoted_near_tie" in rec.columns else 0
    n_reversal = int(std["is_reversal"].fillna(False).sum()) if "is_reversal" in std.columns else 0
    n_mod_340b = int(std["mod_340b"].fillna(False).sum()) if "mod_340b" in std.columns else 0
    n_mod_waste = int(std["mod_wastage"].fillna(False).sum()) if "mod_wastage" in std.columns else 0
    n_units_imputed = int(std["units_imputed"].fillna(False).sum()) if "units_imputed" in std.columns else 0
    n_units_over_mue = int(std["units_over_mue"].fillna(False).sum()) if "units_over_mue" in std.columns else 0
    n_repaired_rows = int((repairs_per_row.fillna("").astype(str).str.len() > 0).sum())
    n_repairs_total = int(repairs_log["rows_fixed"].sum()) if not repairs_log.empty else 0
    n_providers = int(len(provider_directory))
    n_found = int(provider_directory["Found_In_NPPES"].sum()) if not provider_directory.empty else 0
    n_340b_signal = int((coverage_340b["B340_Eligibility_Signal"].astype(str).str.len() > 0).sum()) \
        if not coverage_340b.empty else 0
    n_340b_reg = int((coverage_340b.get("B340_Registered", pd.Series(dtype=str)).astype(str) == "Yes").sum()) \
        if not coverage_340b.empty else 0
    n_enrolled = int(provider_directory.get("Medicare_Enrolled", pd.Series(dtype=bool)).fillna(False).sum()) \
        if not provider_directory.empty else 0
    n_opted_out = int(provider_directory.get("Opted_Out_Medicare", pd.Series(dtype=bool)).fillna(False).sum()) \
        if not provider_directory.empty else 0

    def _fa(key, default=0):
        return fill_summary.attrs.get(key, default) if not fill_summary.empty else default

    stats = {
        "outputs": outputs,
        "rows_total": rows_in_file,
        "rows_blank_billing": n_blank,
        "pct_rows_blank": round(100 * n_blank / rows_in_file, 1) if rows_in_file else 0,
        "dollars_total": tot_dollars,
        "dollars_blank": blank_dollars,
        "pct_dollars_blank": round(100 * blank_dollars / tot_dollars, 1) if tot_dollars else 0,
        "rows_recovered": n_recovered,
        "pct_blanks_recovered": round(100 * n_recovered / n_blank, 1) if n_blank else 0,
        "dollars_recovered": rec_dollars,
        "rows_point_attribution": n_point,
        "rows_inferred_cluster": int(n_inf_clust),
        "rows_inferred_continuity": int(n_inf_cont),
        "billers_deactivated": int(bulk_info.get("deactivated_npi", {}).get("rows_flagged", 0)),
        "rows_billing_npi_deactivated_asof_service": (
            int((filled["_NPI_Deactivated"].astype(str).str.len() > 0).sum())
            if do_fill and "_NPI_Deactivated" in filled.columns else 0),
        "rows_demoted_near_tie": n_demoted,
        "rows_demoted_calibration": int(sum(d["rows_demoted"] for d in calib_demoted)),
        "calibration_demoted_tiers": calib_demoted,
        "rows_reversal_adjustment": n_reversal,
        "rows_340b_modifier": n_mod_340b,
        "rows_wastage_modifier": n_mod_waste,
        "rows_units_imputed": n_units_imputed,
        "ndc_drug_name_filled": int(ndc_info.get("drug_name_filled_from_ndc", 0)),
        "ndc_drug_mismatch_flagged": int(ndc_info.get("ndc_drug_mismatch_flagged", 0)),
        "rows_units_over_mue": n_units_over_mue,
        "rows_grossup": int(nonattr.sum()),
        "rows_with_repairs": n_repaired_rows,
        "field_repairs_total": n_repairs_total,
        "providers_enriched": n_providers,
        "providers_found_in_nppes": n_found,
        "providers_medicare_enrolled": n_enrolled,
        "providers_opted_out": n_opted_out,
        "referring_npis_verified": ref_verified,
        "drugs_referenced": int(len(drug_reference)),
        "providers_340b_signal": n_340b_signal,
        "providers_340b_registered": n_340b_reg,
        "honest_top1": bt.get("honest_top1"),
        "honest_top3": bt.get("honest_top3"),
        "holdout_top1": bt.get("holdout_top1"),
        "rows_deduplicated": int(fill_summary.attrs.get("n_dupes_removed", 0)) if not fill_summary.empty else 0,
        "filled_rows_out": int(fill_summary.attrs.get("rows_out", 0)) if not fill_summary.empty else 0,
        "cells_filled_total": int(fill_summary["filled"].sum()) if not fill_summary.empty else 0,
        "cells_na_total": int(fill_summary["still_NA"].sum()) if not fill_summary.empty else 0,
        # Honest billing-NPI confidence split (dollar-weighted). cells_filled_total
        # above counts only HIGH-confidence (point) fills now — distributional
        # guesses are deliberately not written to the billing column — so these
        # keys make the three channels explicit rather than blending them.
        "bill_high_rows": int(_fa("bill_high_rows", 0)),
        "bill_high_dollars": float(_fa("bill_high_dollars", 0.0)),
        "bill_high_pct_dollars": float(_fa("bill_high_pct_dollars", 0.0)),
        "bill_lowguess_rows": int(_fa("bill_lowguess_rows", 0)),
        "bill_lowguess_dollars": float(_fa("bill_lowguess_dollars", 0.0)),
        "bill_lowguess_pct_dollars": float(_fa("bill_lowguess_pct_dollars", 0.0)),
        "bill_notattributed_rows": int(_fa("bill_na_rows", 0)),
        "bill_notattributed_dollars": float(_fa("bill_na_dollars", 0.0)),
        "bill_notattributed_pct_dollars": float(_fa("bill_na_pct_dollars", 0.0)),
        "entity_parents": int(ent_rollup["npi_count"].gt(1).sum()) if not ent_rollup.empty else 0,
        "cms_physician_url": cms.latest_api_url(config.DATASET_TITLES["physician_provider"]),
    }
    # v22: connector audit. Independently probes EVERY public API the tool relies
    # on (bounded, cached) so the output documents which connectors are live and
    # how they responded — "are all the APIs being used and reachable?", answered
    # in the deliverable. Default on; --no-audit skips it.
    conn_status = []
    if do_health_audit:
        progress("Auditing data connectors", 0.99)
        try:
            from . import health
            conn_status = health.run_health_check(cache_dir=cache_dir)
        except Exception as e:
            conn_status = [{"source": "health audit", "ok": False,
                            "detail": f"{type(e).__name__}: {e}", "seconds": 0.0}]
    # v25: readout analytics (deal-team cuts). Deterministic group-bys over the
    # frame we already have in memory; no new API calls. Gated, single-year by
    # default, county-ready. Never fatal: failures land as a note sheet.
    analytics_sheets = {}
    if do_analytics:
        progress("Building readout analytics", 0.995)
        try:
            from . import analytics as _an
            _final = cleaned["Billing_NPI_Final"] if "Billing_NPI_Final" in cleaned.columns else None

            # v30: bring the pharmacy dispensing NPIs into the provider directory
            # (their taxonomy drives the AIS site classification) and roll them up
            # to an operator, extending parent_map. Runs before taxonomy_of is built.
            _pharm_attr_sheet = None
            _rx_cov_sheet = None
            if std_pharmacy is not None:
                try:
                    from . import pharmacy_feed as _pf
                    _pharm_dir, parent_map, _pharm_cov = _pf.enrich_and_attribute(
                        std_pharmacy, nppes=nppes, cms=cms,
                        provider_directory=provider_directory, parent_map=parent_map,
                        progress=lambda m, f: progress(f"Pharmacy NPIs: {m}", 0.9945))
                    if _pharm_dir is not None and len(_pharm_dir):
                        provider_directory = (pd.concat([provider_directory, _pharm_dir], ignore_index=True)
                                              .drop_duplicates(subset=["NPI"], keep="first")
                                              if provider_directory is not None and len(provider_directory)
                                              else _pharm_dir)
                    _pharm_attr_sheet = _pharm_cov
                except Exception as _e:
                    _pharm_attr_sheet = pd.DataFrame(
                        {"note": [f"pharmacy NPI enrichment skipped: {type(_e).__name__}: {_e}"]})

            # v29: billing-provider taxonomy map (npi -> taxonomy code) from the
            # enriched NPPES directory, so the site reclassifier can read
            # infusion-clinic / infusion-pharmacy / home taxonomies.
            taxonomy_of = None
            try:
                pd_dir = provider_directory
                if pd_dir is not None and len(pd_dir) and "NPI" in pd_dir.columns and "Taxonomy_Code" in pd_dir.columns:
                    taxonomy_of = {"".join(ch for ch in str(k) if ch.isdigit()): str(v)
                                   for k, v in zip(pd_dir["NPI"], pd_dir["Taxonomy_Code"]) if str(v).strip()}
            except Exception:
                taxonomy_of = None

            # v29: analytics frame = medical std, plus the pharmacy feed unioned in
            # when present (recovery stays medical-only; analytics see both channels).
            std_analytics = std
            if std_pharmacy is not None:
                try:
                    from . import pharmacy_feed as _pf
                    std_analytics, pharmacy_dedup = _pf.union_feeds(std, std_pharmacy)
                except Exception:
                    std_analytics = std
                    if "_claim_source" not in std_analytics.columns:
                        std_analytics = std_analytics.assign(_claim_source="medical")
                # v30: resolve the UNION so medical rows carry the same drug_class_rx
                # as pharmacy rows (pharmacy already resolved at read time; this pass
                # is idempotent and classes the medical J-code rows for the
                # per-molecule dual-channel reconciliation).
                try:
                    from . import rx_bridge as _rxb
                    std_analytics = _rxb.resolve_feed(std_analytics, rxnorm=rxnorm,
                                                      ref_dir=config.REF_DIR)
                    _rx_cov_sheet = _rxb.bridge_summary(std_analytics)
                except Exception:
                    pass
                # align the recovered-NPI vector to the union (pharmacy rows carry
                # their own billing NPI; nothing was recovered for them)
                if _final is not None:
                    _pad = pd.Series(pd.NA, index=range(len(std_analytics) - len(_final)))
                    _final = pd.concat([pd.Series(np.asarray(_final)), _pad], ignore_index=True)

            # v31: resolve optional client inputs (offline-safe: missing -> None).
            _client_gov = client_gov_npis
            try:
                from . import npi_channel as _nc31
                if _client_gov is None:
                    _loaded = _nc31.load_gov_npi_list(config.REF_DIR)
                    _client_gov = _loaded or None
            except Exception:
                _client_gov = client_gov_npis
            _formulary_spec = None
            try:
                from . import formulary as _fm31
                _formulary_spec = _fm31.load_formulary(formulary_path or config.REF_DIR)
            except Exception:
                _formulary_spec = None

            analytics_sheets = _an.build_analytics(
                std_analytics, _final, parent_map, drug_ident,
                granularity=analytics_granularity,
                latest_year_only=analytics_latest_year_only,
                taxonomy_of=taxonomy_of, membership_index=membership_index,
                ref_dir=config.REF_DIR,
                control_total=control_total, per_drug_control=per_drug_control,
                formulary=_formulary_spec, client_gov_npis=_client_gov,
                expected_total=expected_total, coverage_ratio=coverage_ratio,
                spend_floor=spend_floor, asp_crosswalk=asp_crosswalk, fda_ndc=fda_ndc,
                dme_fee=dme_fee, formulary_codes=formulary_codes,
                therapy_map_path=therapy_map_path,
                roster_npis=(roster_npis if roster_npis is not None else _client_gov),
                vrdc_suppressed=vrdc_suppressed, part_d_observed=part_d_observed,
                medicaid_observed=medicaid_observed, ma_captured=ma_captured,
                surviving_roster=surviving_roster, komodo_ffs=komodo_ffs,
                vrdc_census=vrdc_census, ma_encounters=ma_encounters,
                ma_prices=ma_prices, asp_limits=asp_limits,
                ratio_components=ratio_components,
                medicaid_state_ratios=medicaid_state_ratios, management_ma=management_ma,
                payer_aliases=payer_aliases, prior_rollup=prior_rollup,
                progress=lambda m, f: progress(f"Analytics: {m}", 0.995))
            if pharmacy_dedup is not None and len(pharmacy_dedup):
                analytics_sheets["Pharmacy_Feed_Reconciliation"] = pharmacy_dedup
            if netting_applied_audit is not None:
                analytics_sheets["Netting_Applied"] = netting_applied_audit
            if clean_ledger_tab is not None:
                analytics_sheets["Cleaning_Ledger"] = clean_ledger_tab
            if clean_recon_tab is not None:
                analytics_sheets["Clean_Reconciliation"] = clean_recon_tab

            # v30 sheets captured before the dict was reassigned by build_analytics
            if _rx_cov_sheet is not None:
                analytics_sheets["Rx_Bridge_Coverage"] = _rx_cov_sheet
            if _pharm_attr_sheet is not None:
                analytics_sheets["Pharmacy_Provider_Attribution"] = _pharm_attr_sheet
        except Exception as e:
            analytics_sheets = {"Analytics_Note": pd.DataFrame(
                {"note": [f"analytics skipped: {type(e).__name__}: {e}"]})}

        # v26: VRDC-free market sizing. Connector-bound (needs real Medicare
        # volume), so only when connectors are on. Bottom-up payer-segment build.
        if do_connectors:
            try:
                from . import market_sizing as _ms
                _state = "TX"
                if "state" in std.columns and std["state"].notna().any():
                    _sv = std["state"].dropna().astype(str)
                    if len(_sv):
                        _state = _sv.mode().iloc[0]
                # panel Medicare allowed by HCPCS, for the capture cross-check
                _pm_med = None
                if "payer" in std.columns and "hcpcs" in std.columns and std["payer"].notna().any():
                    _med = std[std["payer"].astype(str).str.contains("medicare", case=False, na=False)]
                    if len(_med):
                        _pm_med = (pd.to_numeric(_med.get("allowed_amt"), errors="coerce").fillna(0.0)
                                   .groupby(_med["hcpcs"].astype(str)).sum().to_dict())
                progress("VRDC-free market sizing", 0.997)
                _est, _method = _ms.build_market_size(
                    std, cms, state=_state, panel_medicare_by_hcpcs=_pm_med,
                    progress=lambda m, f: progress(f"Sizing: {m}", 0.997))
                analytics_sheets["Market_Size_Estimate"] = _est
                analytics_sheets["Market_Size_Method"] = _method
            except Exception as e:
                analytics_sheets["Market_Size_Estimate"] = pd.DataFrame(
                    {"note": [f"market sizing skipped: {type(e).__name__}: {e}"]})

            # v27: cross-state market attractiveness (Phase 2 geographic screen).
            # One Market Saturation call per state; bounded comparator set so it
            # stays fast. Medicare FFS proxy, clearly labeled.
            try:
                from . import market_sizing as _ms2
                _focus = [_state] + [s for s in ["TX", "FL", "CA", "AZ", "GA", "NC", "TN", "NY"]
                                     if s != _state]
                _focus = list(dict.fromkeys(_focus))[:8]
                # top infusion HCPCS by panel allowed $ -> the codes the score is built on
                _top_codes = []
                if "hcpcs" in std.columns:
                    _ha = (pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
                           .groupby(std["hcpcs"].astype("string")).sum()
                           .sort_values(ascending=False))
                    _top_codes = [c for c in _ha.index.tolist() if isinstance(c, str) and c.strip()][:8]
                progress("Cross-state attractiveness", 0.998)
                _att, _attm = _ms2.build_market_attractiveness(
                    cms, _focus, _top_codes,
                    progress=lambda m, f: progress(f"Attractiveness: {m}", 0.998))
                analytics_sheets["Market_Attractiveness"] = _att
                analytics_sheets["Market_Attractiveness_Method"] = _attm
            except Exception as e:
                analytics_sheets["Market_Attractiveness"] = pd.DataFrame(
                    {"note": [f"attractiveness skipped: {type(e).__name__}: {e}"]})

            # v28/v29: pharmacy-benefit section. v28 estimates it from the CMS
            # Part D / Part B ratio per dual-channel drug. v29: if a real pharmacy
            # feed was supplied, its MEASURED dollars (by HCPCS) supersede the
            # estimate for the matched drug classes.
            try:
                from . import market_sizing as _ms3
                progress("Pharmacy-benefit gross-up", 0.999)
                _obs = None
                if std_pharmacy is not None and "hcpcs" in std_pharmacy.columns:
                    _obs = (pd.to_numeric(std_pharmacy.get("allowed_amt"), errors="coerce").fillna(0.0)
                            .groupby(std_pharmacy["hcpcs"].astype("string").str.upper()).sum().to_dict())
                _ph, _phm = _ms3.build_pharmacy_benefit_grossup(
                    cms, std, pharmacy_observed_by_hcpcs=_obs,
                    progress=lambda m, f: progress(f"Pharmacy: {m}", 0.999))
                analytics_sheets["Pharmacy_Benefit_Estimate"] = _ph
                analytics_sheets["Pharmacy_Benefit_Method"] = _phm
            except Exception as e:
                analytics_sheets["Pharmacy_Benefit_Estimate"] = pd.DataFrame(
                    {"note": [f"pharmacy gross-up skipped: {type(e).__name__}: {e}"]})
    progress("Done", 1.0)
    # -- v36: preflight tabs attach UNCONDITIONALLY so they survive any
    # analytics failure; then the run-report layer LAST so it covers everything.
    try:
        if isinstance(analytics_sheets, dict):
            if preflight_facts is not None:
                analytics_sheets["Preflight_Report"] = preflight_facts
            if coercion_tab is not None:
                analytics_sheets["Coercion_Casualties"] = coercion_tab
            if column_diag_tab is not None:
                analytics_sheets["Column_Diagnosis"] = column_diag_tab
    except Exception:
        pass
    try:
        from . import run_report as _rr36
        from . import __version__ as _v36
        if isinstance(analytics_sheets, dict):
            _rr36.attach_run_report(
                analytics_sheets, version=_v36,
                input_name=str(input_path), n_rows=rows_in_file,
                flags=("deep_clean" if deep_clean else "")
                      + (" apply_netting" if apply_netting else ""))
    except Exception as _e:
        try:
            analytics_sheets["Run_Manifest"] = pd.DataFrame(
                {"note": [f"run report skipped: {type(_e).__name__}: {_e}"]})
        except Exception:
            pass

    return Result(raw=raw, std=std, mapping=mapping, map_report=map_report,
                  coverage=coverage, coverage_before=coverage_before, repairs_log=repairs_log,
                  blank_profile=blank_profile, route_map=route_map,
                  pool_table=pool_table, recovery=rec, cleaned=cleaned,
                  entity_table=ent_table, entity_rollup=ent_rollup,
                  provider_directory=provider_directory, drug_reference=drug_reference,
                  coverage_340b=coverage_340b,
                  bt=bt, grossup_table=grossup_table,
                  blank_decomposition=_blank_decomposition(rec),
                  filled=filled, fill_summary=fill_summary, fill_gaps=fill_gaps,
                  filled_verified=filled_verified, fill_summary_verified=fill_summary_verified,
                  fill_gaps_verified=fill_gaps_verified,
                  entity_crosswalk=ent_crosswalk,
                  stats=stats, connector_status=conn_status,
                  filled_statistical_full=filled_statistical_full,
                  backtest_by_operator=bt_by_operator,
                  analytics=analytics_sheets,
                  prob_calibration=(prob_calib or {}),
                  taxonomy_flags=(taxonomy_flags if isinstance(taxonomy_flags, pd.DataFrame)
                                  else pd.DataFrame()),
                  capture=_capture_safe(std, mapping),
                  agreement=agreement_tbl,
                  agreement_summary=agreement_roll,
                  disagreement_queue=disagreement_q,
                  evidence_ledger=evidence_ledger,
                  seller_request=_seller_request_safe(mapping, std, agreement_roll),
                  run_manifest=_manifest_safe(input_path, options_for_manifest),
                  calibrated_applied=calib_applied,
                  specialty_drug_mix=_specialty_drug_mix_safe(std, mapping),
                  reassignment_recovery=(reassignment_recovery
                                         if isinstance(reassignment_recovery, pd.DataFrame)
                                         else pd.DataFrame()))


def _capture_safe(std, mapping):
    """Capture/completeness report, guarded so a failure never breaks a run."""
    try:
        from . import capture_model
        return capture_model.capture_report(std, ref_dir=config.REF_DIR, mapping=mapping)
    except Exception:
        return {}


def _seller_request_safe(mapping, std, agreement_roll):
    """Seller data request list from fixability + capture + agreement gaps."""
    try:
        from . import registry as _R
        from . import capture_model as _CAP
        from . import seller_request as _SR
        fixa = _R.fixability(std, mapping)
        cap = _CAP.capture_report(std, ref_dir=config.REF_DIR, mapping=mapping)
        return _SR.build_seller_request(fixability=fixa, capture=cap,
                                        agreement_summary=agreement_roll)
    except Exception:
        return pd.DataFrame()


def _manifest_safe(input_path, options):
    """Run manifest with reference vintages, guarded."""
    try:
        from . import run_manifest as _RMAN
        from . import __version__ as _v
        return _RMAN.build_manifest(input_path, _v, ref_dir=config.REF_DIR,
                                    options=options or {})
    except Exception:
        return {}


def _specialty_drug_mix_safe(std, mapping):
    """v48: the specialty mix for the top drugs in the book, from the prior model
    (refittable from real utilization). A standalone read of who bills each drug."""
    try:
        from . import specialty_drug as SD
        model = SD.default_model()
        hcol = (mapping or {}).get("hcpcs", "hcpcs")
        hcol = hcol if hcol in std.columns else ("hcpcs" if "hcpcs" in std.columns else None)
        if hcol is None:
            return pd.DataFrame()
        acol = (mapping or {}).get("allowed_amt", "allowed_amt")
        acol = acol if acol in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)
        top = (std.groupby(std[hcol].astype(str).str.upper())[acol].sum().sort_values(ascending=False)
               if acol else std[hcol].astype(str).str.upper().value_counts())
        frames = []
        for hcpcs in list(top.index)[:15]:
            dist = model.specialty_distribution(hcpcs)
            if "specialty" in dist.columns:
                dist = dist.copy()
                dist.insert(0, "hcpcs", hcpcs)
                frames.append(dist)
        if not frames:
            return pd.DataFrame()
        out = pd.concat(frames, ignore_index=True)
        out.attrs["note"] = (f"Specialty mix for the top drugs, from the {model.fitted_from} "
                             f"model. Refit from real Medicare utilization or RIF carrier "
                             f"data for measured frequencies. Shows who bills each drug, a "
                             f"check on recovered billers and a market read.")
        return out
    except Exception:
        return pd.DataFrame()


def _blank_decomposition(rec):
    """Ryan's reframe, quantified: a blank billing NPI is not one problem but
    several structurally different ones, and only the recoverable slice should be
    filled — at graded confidence. This rolls the per-blank `reason`/`attribution`
    into named buckets with rows and dollars so the conflation is visible."""
    cols = ["bucket", "ryan_reason", "rows", "dollars", "pct_dollars", "what_happens_to_it"]
    if rec is None or rec.empty:
        return pd.DataFrame(columns=cols)
    r = rec.copy()
    r["_amt"] = pd.to_numeric(r.get("blank_allowed", 0), errors="coerce").fillna(0).clip(lower=0)
    pharm = {"sad", "no_partb_presence", "noc"}

    def _bucket(row):
        rs, at = row.get("reason"), row.get("attribution")
        if rs == "recovered":
            return ("1. Filled — point match", "RECOVERABLE (referral / identifier match)",
                    "Written into the billing-NPI column. Point-attributed, so it survives diligence.") \
                if at == "point" else \
                   ("2. Best guess — distributional", "RECOVERABLE (referral / identifier match)",
                    "Written ONLY to a separate, labeled best-guess column. Never derives name/affiliation/entity.")
        if rs in pharm:
            return ("3. N/A by design — pharmacy / non-medical",
                    "NEVER POPULATED BY DESIGN (pharmacy benefit — no medical NPI exists)",
                    "Left empty on purpose. No medical biller exists; inventing one is wrong. A closed-claims "
                    "filter does NOT populate these — they are blank in closed claims too.")
        return ("4. No public match — residual",
                "GENUINELY MISSING or still OPEN (no public path)",
                "Left empty. Either still adjudicating or unrecoverable from public data; close with the CIM / "
                "data room, not a public source or a guess.")

    bb = r.apply(_bucket, axis=1, result_type="expand")
    r["bucket"], r["ryan_reason"], r["what_happens_to_it"] = bb[0], bb[1], bb[2]
    g = (r.groupby(["bucket", "ryan_reason", "what_happens_to_it"], sort=True)
         .agg(rows=("_amt", "size"), dollars=("_amt", "sum")).reset_index())
    tot = float(g["dollars"].sum()) or 1.0
    g["pct_dollars"] = (100.0 * g["dollars"] / tot).round(1)
    g["dollars"] = g["dollars"].round(0)
    return g[cols].sort_values("bucket").reset_index(drop=True)


def _assemble_cleaned(raw, std, rec, mapping, repairs_per_row=None):
    """Return the original rows with (a) repaired field values written back into
    their mapped columns, (b) the recovered billing NPI, and (c) audit columns."""
    cleaned = raw.copy()
    rec_idx = rec.set_index(std.loc[std["is_blank_billing"]].index)
    status_map = {
        "recovered": None, "sad": "not_attributed_partD", "noc": "not_attributed_NOC",
        "no_partb_presence": "not_attributed_no_partB", "no_candidate": "not_attributed_no_candidate",
    }
    bill_col = mapping.get("billing_npi")

    # (a) write repaired values back into the mapped original columns, so the
    # delivered file is genuinely cleaned (state/drug name/HCPCS/POS). Billing
    # NPI is handled separately so we can keep the original alongside the final.
    for canon in ("state", "drug_name", "hcpcs", "pos", "units", "allowed_amt"):
        col = mapping.get(canon)
        if col and col in cleaned.columns and canon in std.columns:
            repaired = std[canon]
            cleaned[col] = repaired.where(repaired.notna(), cleaned[col]).values

    final, status, tier, conf, top3, oper, note = ({} for _ in range(7))
    for idx, r in rec_idx.iterrows():
        reason = r["reason"]
        if reason == "recovered":
            final[idx] = r["recovered_npi"]
            status[idx] = f"recovered_{r['attribution']}"
        else:
            final[idx] = pd.NA
            status[idx] = status_map.get(reason, reason)
        tier[idx] = r["tier"]
        conf[idx] = r["confidence"]
        top3[idx] = r["recovered_top3"]
        oper[idx] = r.get("recovered_operator", "")
        note[idx] = r["reason"]

    orig_bill = std["billing_npi_original"] if "billing_npi_original" in std.columns else \
        (cleaned[bill_col] if (bill_col and bill_col in cleaned.columns) else pd.Series([pd.NA] * len(cleaned), index=cleaned.index))
    cleaned["Billing_NPI_Original"] = orig_bill.values
    cleaned["Billing_NPI_Final"] = orig_bill.where(orig_bill.notna(), pd.NA).values
    # for invalid-NPI rows the original is bad; final should come from recovery
    if "billing_npi_invalid" in std.columns:
        invalid = std["billing_npi_invalid"].fillna(False).values
        cleaned.loc[invalid, "Billing_NPI_Final"] = pd.NA
    cleaned["Recovery_Status"] = "original"
    for idx in rec_idx.index:
        cleaned.at[idx, "Billing_NPI_Final"] = final.get(idx, pd.NA)
        cleaned.at[idx, "Recovery_Status"] = status.get(idx, "original")
    cleaned["Recovery_Tier"] = pd.Series(tier)
    cleaned["Recovery_Confidence"] = pd.Series(conf)
    cleaned["Recovery_Top3_NPIs"] = pd.Series(top3)
    cleaned["Recovered_Operator"] = pd.Series(oper)
    cleaned["Recovery_Reason"] = pd.Series(note)
    if repairs_per_row is not None:
        cleaned["Repairs_Applied"] = repairs_per_row.reindex(cleaned.index).fillna("").values
    return cleaned
