"""Command-line interface — the primary "give it a file and wait" experience.

    python recover_npis.py claims.xlsx
    python recover_npis.py claims.csv --out cleaned.xlsx --states TX,OK --top-hcpcs 60

Shows a live progress bar while it audits the file, routes every drug, pulls the
real CMS biller pools, imputes the missing NPIs, resolves operators in NPPES,
back-tests its own accuracy, and writes the formatted workbook.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
import pandas as pd

from npi_recovery import run_pipeline, write_report
from npi_recovery.report import write_filled
from npi_recovery.report import _pct, _money

try:
    from rich.console import Console
    from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                               TimeElapsedColumn)
    from rich.table import Table
    from rich.panel import Panel
    _RICH = True
except Exception:                                   # pragma: no cover
    _RICH = False


def _parse_impute(spec):
    if not spec:
        return None
    out = []
    for part in str(spec).split(","):
        if ":" in part:
            f, st = part.split(":", 1)
            out.append((f.strip(), st.strip()))
    return out or None


def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="recover_npis",
        description="Recover missing billing-provider NPIs from a claims file using "
                    "live CMS + NPPES public data, and write a cleaned, tabbed Excel workbook.")
    p.add_argument("input", nargs="?", default=None,
                   help="Path to the claims file (.xlsx, .xls, .csv, or .tsv).")
    p.add_argument("--health", action="store_true",
                   help="Run a live health check of every data source and exit.")
    p.add_argument("--serve", action="store_true",
                   help="Launch the drag-and-drop web interface in your browser.")
    p.add_argument("--port", type=int, default=8765,
                   help="Port for --serve (default 8765).")
    p.add_argument("--out", "-o", default=None,
                   help="Output .xlsx path (default: <input>_NPI_recovered.xlsx).")
    p.add_argument("--output", choices=["both", "verified", "statistical"], default="both",
                   help="Which deliverable to build. 'verified' = only the 100%%-direct-"
                        "lookup file (fastest: skips the statistical recovery). 'statistical' "
                        "= only the full-recovery file. 'both' (default) = write both.")
    p.add_argument("--top-hcpcs", type=int, default=40,
                   help="Cap CMS pulls to the N highest-blank-dollar HCPCS codes (default 40). "
                        "Use 0 for no cap (slower, more network).")
    p.add_argument("--states", default=None,
                   help="Comma-separated state filter for CMS pulls, e.g. TX,OK. "
                        "Default: every state present on the blank rows.")
    p.add_argument("--no-entity", action="store_true",
                   help="Skip NPPES entity resolution / operator rollup (faster).")
    p.add_argument("--no-splink", action="store_true",
                   help="Skip Splink probabilistic fuzzy entity linkage (v20). "
                        "Falls back to exact deterministic clustering. Auto-skipped "
                        "anyway if splink/duckdb are not installed.")
    p.add_argument("--no-audit", action="store_true",
                   help="Skip the connector health audit (v22). By default every run "
                        "probes all public APIs and writes a Connector_Status sheet.")
    p.add_argument("--no-analytics", action="store_true",
                   help="Skip the v25 readout analytics (referral concentration, submarket "
                        "landscape/saturation, target map, benefit-shift, formulary). These are "
                        "deterministic group-bys with no API calls and add only seconds.")
    p.add_argument("--submarket", choices=["zip3", "county"], default="zip3",
                   help="Submarket granularity for v25 analytics. Default zip3 (Komodo grain); "
                        "use county once a county-grain extract (e.g. VRDC) is available.")
    p.add_argument("--analytics-all-years", action="store_true",
                   help="v25 analytics: use all years instead of the latest single year "
                        "(default is latest year, since J-code coverage shifts make YoY noisy).")
    p.add_argument("--no-repair", action="store_true",
                   help="Skip field repair (invalid NPI / missing state / drug name / POS).")
    p.add_argument("--no-enrich", action="store_true",
                   help="Skip enrichment (NPPES provider directory + per-drug CMS cross-reference).")
    p.add_argument("--no-340b", action="store_true",
                   help="Skip 340B coverage enrichment.")
    p.add_argument("--no-bulk", action="store_true",
                   help="Skip v7 bulk local-table joins (deactivation, taxonomy); offline-safe.")
    p.add_argument("--hrsa-340b-file", default=None,
                   help="Path to an HRSA OPAIS Covered Entity export (.xlsx/.json) for "
                        "authoritative registered-340B status (otherwise taxonomy signal only).")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--national", dest="national", action="store_true", default=None,
                     help="Force national CMS pulls (one query per code, all states). "
                          "Best for multi-state / national extracts.")
    grp.add_argument("--regional", dest="national", action="store_false",
                     help="Force per-(code, state) CMS pulls. Best for a few states.")
    p.add_argument("--holdout", type=float, default=0.2,
                   help="Back-test holdout fraction (default 0.2).")
    p.add_argument("--map", default=None,
                   help="JSON overriding column detection, e.g. "
                        "'{\"billing_npi\":\"BillProvNPI\",\"hcpcs\":\"Code\"}'.")
    p.add_argument("--cache-dir", default=None,
                   help="Where to cache CMS/NPPES responses (default ./.npi_cache).")
    p.add_argument("--pharmacy-file", default=None,
                   help="Optional second extract billed through the PHARMACY (RX) benefit. "
                        "Standardised on the same schema + J-code list, tagged RX, and unioned "
                        "into the analytics so the channel the medical panel cannot see is added "
                        "back (Channel_Reconciliation). Auto-detected from INPUT/pharmacy/ by run.sh.")
    p.add_argument("--membership-index", default=None,
                   help="Optional covered-lives scaling for growth, as JSON {year: factor}, e.g. "
                        "'{\"2023\":1.0,\"2024\":1.06,\"2025\":1.11}'. Applied before YoY/CAGR so the "
                        "membership-adjusted read is reproducible. Default: no adjustment.")
    p.add_argument("--control-total", type=float, default=None,
                   help="v31: known control total for the target entity (stated revenue, or the sum "
                        "of an unblinded field). Reconciles the rebuilt panel against it "
                        "(Control_Total_Reconciliation / Control_Total_Exposure).")
    p.add_argument("--per-drug-control", default=None,
                   help="v31: optional per-molecule target dollars, as JSON {common_name: amount} or "
                        "a path to such a JSON file. Feeds gap-to-target in Capture_By_Drug.")
    p.add_argument("--gov-npi-list", default=None,
                   help="v31: CSV of the client's own government-billing NPIs (column npi/billing_npi). "
                        "Reconciles the panel's channel call against it (NPI_Government_Reconciliation). "
                        "Auto-detected from a *gov*npi*.csv in reference/ when omitted.")
    p.add_argument("--formulary", dest="formulary_path", default=None,
                   help="v31: CSV formulary override (key,kind,disposition,note) layered on the shipped "
                        "seed. Drives Formulary_Gate / Formulary_Exclusions_Review.")
    # v32: Onyx / Project Infusion comprehensive-report inputs (all optional).
    p.add_argument("--expected-total", type=float, default=None,
                   help="v32: management / Komodo expected total for the target. Drives the VRDC "
                        "ceiling report (redistributable vs upstream deficit) and the four-hypothesis "
                        "deficit diagnosis.")
    p.add_argument("--coverage-ratio", type=float, default=None,
                   help="v32: Komodo coverage ratio (e.g. 0.141) for the MA gross-up panel and its "
                        "sensitivity. Requires --ma-captured.")
    p.add_argument("--ma-captured", type=float, default=None,
                   help="v32: captured MA dollars to gross up by 1/coverage-ratio.")
    p.add_argument("--part-d-observed", type=float, default=None,
                   help="v32: observed Part D dollars, carried at face in the gross-up panel.")
    p.add_argument("--medicaid-observed", type=float, default=None,
                   help="v32: observed Medicaid dollars (flagged least stable) in the gross-up panel.")
    p.add_argument("--spend-floor", type=float, default=1_000_000.0,
                   help="v32: drug-grain spend floor for the frozen universe (default 1,000,000). "
                        "Defined once on panel spend and frozen across sources.")
    p.add_argument("--asp-crosswalk", default=None,
                   help="v32: CMS ASP NDC-to-HCPCS crosswalk CSV for the top-down code array. The "
                        "shipped example is used when omitted.")
    p.add_argument("--fda-ndc", default=None,
                   help="v32: FDA NDC directory CSV, folded into the top-down crosswalk.")
    p.add_argument("--dme-fee", default=None,
                   help="v32: DME drug fee-schedule CSV, folded into the top-down crosswalk.")
    p.add_argument("--formulary-codes", default=None,
                   help="v32: formulary code snapshot CSV (hcpcs/ndc columns) for the dual-flag "
                        "any-match membership (DualFlag_Membership, NDC_Gap_Targets).")
    p.add_argument("--therapy-map", default=None,
                   help="v32: client three-letter therapy-code mapping CSV "
                        "(molecule_token,therapy_code,acute_chronic,chronic_subclass). Client rows "
                        "win over the shipped seed.")
    p.add_argument("--roster-npis", default=None,
                   help="v32: finder-list NPIs CSV for enrollment JV / missing-entity flags. Falls "
                        "back to --gov-npi-list when omitted.")
    p.add_argument("--vrdc-suppressed", default=None,
                   help="v32: VRDC export CSV with suppressed cells (an 'allowed' column, optional "
                        "'row_total' and 'benes') to reconcile against the unsuppressed ceiling.")
    # v33: close the loop, pin the ratio, protect the fallback (all optional).
    p.add_argument("--surviving-roster", default=None,
                   help="v33: CSV of surviving (client-file) NPIs; with --roster-npis as the full "
                        "list, quantifies migration and the artificial-growth test.")
    p.add_argument("--komodo-ffs", default=None,
                   help="v33: CSV drug,dollars of Komodo FFS captured spend, calibrated per drug "
                        "against --vrdc-census (Komodo_FFS_Calibration, Mix_Parity).")
    p.add_argument("--vrdc-census", default=None,
                   help="v33: CSV drug,dollars of the VRDC 100 percent FFS census.")
    p.add_argument("--ma-encounters", default=None,
                   help="v33: CSV drug,units of MA encounter volumes for the proxy-priced MA "
                        "estimate (MA_Proxy_Estimate, MA_Triangulation).")
    p.add_argument("--ma-prices", default=None,
                   help="v33: CSV drug,dollars-per-unit to price MA encounters (FFS or ASP basis).")
    p.add_argument("--asp-limits", default=None,
                   help="v33: CSV hcpcs,dollars-per-unit ASP payment limits (ASP_Rate_Position; "
                        "also prices MA encounters when --ma-prices is absent).")
    p.add_argument("--ratio-components", default=None,
                   help="v33: CSV payer_class,captured,universe to decompose the stated coverage "
                        "ratio (Ratio_Decomposition).")
    p.add_argument("--medicaid-state-ratios", default=None,
                   help="v33: CSV state,ratio of managed-Medicaid coverage by state "
                        "(Medicaid_State_Grossup stability score).")
    p.add_argument("--management-ma", type=float, default=None,
                   help="v33: management's MA dollar figure, the third triangulation leg.")
    # v34: anticipate the next meeting (all optional; report-only unless noted).
    p.add_argument("--payer-aliases", default=None,
                   help="v34: CSV alias,parent extending the shipped payer alias seed for "
                        "payer normalization (Payer_Normalization_Audit, Payer_Mix_Normalized).")
    p.add_argument("--prior-rollup", default=None,
                   help="v34: last run's Common_Name_Rollup CSV; diffs every molecule run over "
                        "run and flags restatements (Restatement_Diff).")
    p.add_argument("--apply-netting", action="store_true",
                   help="v34 OPT-IN: drop exact duplicate rows and matched reversal pairs "
                        "before any analysis (Netting_Applied audit tab). Default is "
                        "report-only via Netting_Audit.")
    # v35: deterministic deep clean (report tabs always on; apply is opt-in).
    p.add_argument("--deep-clean", action="store_true",
                   help="v35 OPT-IN: apply the deterministic clean stages (text hygiene, "
                        "accounting-money parse, date parse incl Excel serials, "
                        "segment-aware NDC-11) before anything else, with a full "
                        "Cleaning_Ledger and conservation proof.")
    p.add_argument("--impute", default=None,
                   help="v35 OPT-IN with --deep-clean: comma list of field:strategy fills "
                        "to apply, e.g. units:rate_implied,state:from_zip3. Originals kept, "
                        "methods stamped. See Imputation_Options for the comparison first.")
    # v42: selectable single-purpose fixes. Pick exactly what you want; the tool
    # runs one thing at a time instead of the full monolithic pipeline.
    p.add_argument("--list-fixes", action="store_true",
                   help="v42: print the catalog of selectable data-quality fixes "
                        "(key, group, required columns, reference data) and exit.")
    p.add_argument("--fixability", action="store_true",
                   help="v42: profile the input and report which fixes are Supported / "
                        "Partial / Unsupported on THIS data, then exit. No fixes run.")
    p.add_argument("--fix", default=None,
                   help="v42: comma list of fix keys to run (see --list-fixes), e.g. "
                        "mue_units,icd_dos_validity,npi_deactivated. Runs ONLY those, "
                        "writes one focused workbook, and skips the full pipeline.")
    p.add_argument("--fix-refresh", action="store_true",
                   help="v42: with --fix, refresh the coding-edit reference data to the "
                        "current CMS quarter/fiscal year over the network before running.")
    p.add_argument("--clean-all", action="store_true",
                   help="v45: fix and clean most problems in one pass. Applies safe "
                        "deterministic repairs, runs every coding-edit and consistency "
                        "screen, writes a suggested correction with provenance for each "
                        "issue, analyzes each problem's size and concentration, and "
                        "produces a cleaning scorecard. Nothing judgemental is applied "
                        "automatically.")
    p.add_argument("--engine", choices=["auto", "duckdb", "pandas"], default="auto",
                   help="v46: compute backend. duckdb runs the coding screens and "
                        "aggregations in SQL for multi-GB files; pandas forces the "
                        "in-memory path; auto uses duckdb when available for large "
                        "inputs. Used with --clean-all and --profile.")
    p.add_argument("--profile", action="store_true",
                   help="v46: profile the input (per-column type, null rate, "
                        "cardinality, quality flags) and exit. Uses the SQL profiler "
                        "for large files.")
    p.add_argument("--export", default=None,
                   help="v46: with --clean-all, also export the cleaned data and "
                        "corrections to this format (parquet, csv, or json) alongside "
                        "the workbook, e.g. --export parquet.")
    return p.parse_args(argv)


def _run_with_progress(args, overrides, states):
    """Drive run_pipeline with a live rich progress bar; return the Result."""
    membership = None
    if getattr(args, "membership_index", None):
        try:
            membership = {int(k): float(v) for k, v in json.loads(args.membership_index).items()}
        except Exception:
            print("  (could not parse --membership-index JSON; ignoring)", flush=True)
            membership = None
    pharmacy = getattr(args, "pharmacy_file", None)
    # v31 client inputs (all optional; parse failures degrade to None honestly)
    control_total = getattr(args, "control_total", None)
    per_drug_control = None
    _pdc = getattr(args, "per_drug_control", None)
    if _pdc:
        try:
            if os.path.exists(_pdc):
                with open(_pdc) as _fh:
                    per_drug_control = {str(k): float(v) for k, v in json.load(_fh).items()}
            else:
                per_drug_control = {str(k): float(v) for k, v in json.loads(_pdc).items()}
        except Exception:
            print("  (could not parse --per-drug-control; ignoring)", flush=True)
            per_drug_control = None
    client_gov_npis = None
    _govp = getattr(args, "gov_npi_list", None)
    if _govp:
        try:
            from npi_recovery import npi_channel as _nc_cli
            client_gov_npis = _nc_cli.load_gov_npi_list(_govp) or None
            if not client_gov_npis:
                print("  (no usable NPIs in --gov-npi-list; ignoring)", flush=True)
        except Exception:
            client_gov_npis = None
    formulary_path = getattr(args, "formulary_path", None)
    # v32 inputs (all optional; path inputs threaded as-is, roster parsed to a set)
    roster_npis = None
    surviving_roster_set = None
    try:
        from npi_recovery import npi_channel as _nc_r
        _rp = getattr(args, "roster_npis", None)
        if _rp:
            roster_npis = _nc_r.load_gov_npi_list(_rp) or None
        _sp = getattr(args, "surviving_roster", None)
        if _sp:
            surviving_roster_set = _nc_r.load_gov_npi_list(_sp) or None
    except Exception:
        roster_npis, surviving_roster_set = roster_npis, None
    if not _RICH:
        print("Working (install 'rich' for a live progress bar)...", flush=True)
        last = {"t": 0.0}

        def cb(msg, frac):
            now = time.time()
            if now - last["t"] > 0.5 or frac >= 1.0:
                print(f"  [{frac*100:5.1f}%] {msg}", flush=True)
                last["t"] = now
        return run_pipeline(
            args.input, cache_dir=args.cache_dir, top_hcpcs=(args.top_hcpcs or None),
            states_filter=states, do_entity=not args.no_entity,
            holdout_frac=args.holdout, overrides=overrides, national=args.national,
            do_repair=not args.no_repair, do_enrich=not args.no_enrich,
            do_340b=not args.no_340b, hrsa_340b_file=args.hrsa_340b_file, do_bulk=not args.no_bulk, do_splink=not args.no_splink, do_health_audit=not args.no_audit, do_analytics=not args.no_analytics, analytics_granularity=args.submarket, analytics_latest_year_only=not args.analytics_all_years, pharmacy_path=pharmacy, membership_index=membership, control_total=control_total, per_drug_control=per_drug_control, client_gov_npis=client_gov_npis, formulary_path=formulary_path, expected_total=getattr(args,'expected_total',None), coverage_ratio=getattr(args,'coverage_ratio',None), ma_captured=getattr(args,'ma_captured',None), part_d_observed=getattr(args,'part_d_observed',None), medicaid_observed=getattr(args,'medicaid_observed',None), spend_floor=getattr(args,'spend_floor',1_000_000.0), asp_crosswalk=getattr(args,'asp_crosswalk',None), fda_ndc=getattr(args,'fda_ndc',None), dme_fee=getattr(args,'dme_fee',None), formulary_codes=getattr(args,'formulary_codes',None), therapy_map_path=getattr(args,'therapy_map',None), roster_npis=roster_npis, vrdc_suppressed=getattr(args,'vrdc_suppressed',None), surviving_roster=surviving_roster_set, komodo_ffs=getattr(args,'komodo_ffs',None), vrdc_census=getattr(args,'vrdc_census',None), ma_encounters=getattr(args,'ma_encounters',None), ma_prices=getattr(args,'ma_prices',None), asp_limits=getattr(args,'asp_limits',None), ratio_components=getattr(args,'ratio_components',None), medicaid_state_ratios=getattr(args,'medicaid_state_ratios',None), management_ma=getattr(args,'management_ma',None), payer_aliases=getattr(args,'payer_aliases',None), prior_rollup=getattr(args,'prior_rollup',None), apply_netting=bool(getattr(args,'apply_netting',False)), deep_clean=bool(getattr(args,'deep_clean',False)), impute=_parse_impute(getattr(args,'impute',None)), outputs=args.output, progress=cb)

    console = Console()
    result_box = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Starting", total=1000)

        def cb(msg, frac):
            progress.update(task, completed=int(frac * 1000), description=msg)

        result_box["r"] = run_pipeline(
            args.input, cache_dir=args.cache_dir, top_hcpcs=(args.top_hcpcs or None),
            states_filter=states, do_entity=not args.no_entity,
            holdout_frac=args.holdout, overrides=overrides, national=args.national,
            do_repair=not args.no_repair, do_enrich=not args.no_enrich,
            do_340b=not args.no_340b, hrsa_340b_file=args.hrsa_340b_file, do_bulk=not args.no_bulk, do_splink=not args.no_splink, do_health_audit=not args.no_audit, do_analytics=not args.no_analytics, analytics_granularity=args.submarket, analytics_latest_year_only=not args.analytics_all_years, pharmacy_path=pharmacy, membership_index=membership, control_total=control_total, per_drug_control=per_drug_control, client_gov_npis=client_gov_npis, formulary_path=formulary_path, expected_total=getattr(args,'expected_total',None), coverage_ratio=getattr(args,'coverage_ratio',None), ma_captured=getattr(args,'ma_captured',None), part_d_observed=getattr(args,'part_d_observed',None), medicaid_observed=getattr(args,'medicaid_observed',None), spend_floor=getattr(args,'spend_floor',1_000_000.0), asp_crosswalk=getattr(args,'asp_crosswalk',None), fda_ndc=getattr(args,'fda_ndc',None), dme_fee=getattr(args,'dme_fee',None), formulary_codes=getattr(args,'formulary_codes',None), therapy_map_path=getattr(args,'therapy_map',None), roster_npis=roster_npis, vrdc_suppressed=getattr(args,'vrdc_suppressed',None), surviving_roster=surviving_roster_set, komodo_ffs=getattr(args,'komodo_ffs',None), vrdc_census=getattr(args,'vrdc_census',None), ma_encounters=getattr(args,'ma_encounters',None), ma_prices=getattr(args,'ma_prices',None), asp_limits=getattr(args,'asp_limits',None), ratio_components=getattr(args,'ratio_components',None), medicaid_state_ratios=getattr(args,'medicaid_state_ratios',None), management_ma=getattr(args,'management_ma',None), payer_aliases=getattr(args,'payer_aliases',None), prior_rollup=getattr(args,'prior_rollup',None), apply_netting=bool(getattr(args,'apply_netting',False)), deep_clean=bool(getattr(args,'deep_clean',False)), impute=_parse_impute(getattr(args,'impute',None)), outputs=args.output, progress=cb)
        progress.update(task, completed=1000, description="Done")
    return result_box["r"]


def _print_summary(result, out_path, filled_path=None, closed_path=None, statfull_path=None):
    s = result.stats
    bt = result.bt
    cells_filled = s.get("cells_filled_total", 0)
    cells_na = s.get("cells_na_total", 0)
    dupes = s.get("rows_deduplicated", 0)
    if not _RICH:
        print("\n==== NPI Recovery — summary ====")
        print(f"Rows in file:                 {s['rows_total']:,}")
        print(f"Field repairs applied:        {s.get('rows_with_repairs',0):,} rows "
              f"({s.get('field_repairs_total',0):,} fixes)")
        print(f"Providers enriched (NPPES):   {s.get('providers_enriched',0):,} "
              f"({s.get('providers_found_in_nppes',0):,} found)")
        print(f"Missing a billing NPI:        {s['rows_blank_billing']:,} "
              f"({s['pct_rows_blank']}% of rows, {s['pct_dollars_blank']}% of $)")
        print(f"Billers recovered:            {s['rows_recovered']:,} "
              f"({s['pct_blanks_recovered']}% of blanks)")
        print(f"Cells filled in original:     {cells_filled:,}")
        print(f"Cells left as N/A:            {cells_na:,}")
        print(f"Duplicate rows removed:       {dupes:,}")
        print(f"\nReport written to:  {out_path}")
        if closed_path:
            print(f"  1. Closed Claims (observed + direct lookups): {closed_path}")
        if filled_path:
            print(f"  2. Recovered Claims (+ measured recovery):    {filled_path}")
        if statfull_path:
            print(f"  3. Statistically Filled (REQUIRES REVIEW):    {statfull_path}")
        return

    console = Console()
    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column(justify="left", style="bold")
    t.add_column(justify="right")
    t.add_row("Rows in file", f"{s['rows_total']:,}")
    t.add_row("Field repairs applied",
              f"{s.get('rows_with_repairs', 0):,} rows  ({s.get('field_repairs_total', 0):,} fixes)")
    t.add_row("Providers enriched (NPPES)",
              f"{s.get('providers_enriched', 0):,}  ({s.get('providers_found_in_nppes', 0):,} found)")
    t.add_row("Missing a billing NPI",
              f"{s['rows_blank_billing']:,}  ({s['pct_rows_blank']}% rows / {s['pct_dollars_blank']}% $)")
    t.add_row("Billers recovered",
              f"{s['rows_recovered']:,}  ({s['pct_blanks_recovered']}% of blanks)")
    t.add_row("[green]Cells filled in original[/green]", f"[green]{cells_filled:,}[/green]")
    t.add_row("Cells left as N/A (reported)", f"{cells_na:,}")
    t.add_row("Duplicate rows removed", f"{dupes:,}")
    t.add_row("Honest expected top-1", _pct(bt.get("honest_top1")))
    console.print()
    console.print(Panel(t, title="[bold green]NPI Recovery — summary",
                        subtitle=f"[dim]{out_path}", expand=False))
    if closed_path:
        console.print(f"[bold]1. Closed Claims[/bold] (observed + direct lookups): {closed_path}")
    if filled_path:
        console.print(f"[bold]2. Recovered Claims[/bold] (+ measured recovery): {filled_path}")
    if statfull_path:
        console.print(f"[bold yellow]3. Statistically Filled[/bold yellow] (REQUIRES REVIEW): {statfull_path}")
    console.print(f"[dim]Tiers 1->3 fill more but are less certain. See Cell_Census + Pivot_Landscape in the report.[/dim]")


def _print_health(rows):
    n_ok = sum(1 for r in rows if r["ok"])
    if not _RICH:
        print("\n==== Source health check ====")
        for r in rows:
            print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['source']:42} {r['detail']} ({r['seconds']}s)")
        print(f"\n{n_ok}/{len(rows)} sources healthy.")
        return
    console = Console()
    t = Table(title="Source health check")
    t.add_column("", justify="center")
    t.add_column("Source", style="bold")
    t.add_column("Detail")
    t.add_column("Time", justify="right")
    for r in rows:
        mark = "[green]PASS[/green]" if r["ok"] else "[red]FAIL[/red]"
        t.add_row(mark, r["source"], r["detail"], f"{r['seconds']}s")
    console.print()
    console.print(t)
    color = "green" if n_ok == len(rows) else ("yellow" if n_ok else "red")
    console.print(f"[bold {color}]{n_ok}/{len(rows)} sources healthy.[/bold {color}]")


def _run_profile(args, in_path):
    """v46: profile the input and print the per-column read. Uses the SQL profiler
    for large files when the engine is available."""
    from npi_recovery import profiling, engine
    import pandas as pd
    console = Console()
    use_engine = (args.engine in ("auto", "duckdb")) and engine.duckdb_available()
    suffix = in_path.suffix.lower()

    if use_engine and suffix in (".parquet", ".csv", ".tsv", ".txt", ".xlsx", ".xls", ".xlsm"):
        try:
            prof = engine.profile(str(in_path))
            frame = prof["columns"]
            console.print(f"\n[bold]Profile: {in_path.name}[/bold]  "
                          f"({prof['rows']:,} rows, SQL engine)")
        except Exception:
            use_engine = False
    if not use_engine:
        if suffix in (".xlsx", ".xls", ".xlsm"):
            df = pd.read_excel(str(in_path), dtype=str)
        elif suffix == ".parquet":
            df = pd.read_parquet(str(in_path))
        else:
            df = pd.read_csv(str(in_path), dtype=str)
        frame = profiling.profile_frame(df)
        console.print(f"\n[bold]Profile: {in_path.name}[/bold]  ({len(df):,} rows)")

    console.print(f"[dim]{frame.attrs.get('note','')}[/dim]\n")
    t = Table(header_style="bold")
    for c in frame.columns:
        t.add_column(str(c))
    for _, r in frame.head(60).iterrows():
        t.add_row(*[str(r[c]) for c in frame.columns])
    console.print(t)
    if args.out:
        frame.to_csv(args.out, index=False)
        console.print(f"\n[green]Profile written:[/green] {args.out}")
    return 0


def _run_clean_all(args, in_path):
    """v45 fix-and-clean-everything path: run the orchestrator and write a cleaning
    workbook (scorecard, issue analysis, suggested corrections, cleaned data)."""
    from npi_recovery import schema, clean_orchestrator, config
    import pandas as pd
    console = Console()

    suffix = in_path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        raw = pd.read_excel(str(in_path), dtype=str)
    elif suffix == ".parquet":
        raw = pd.read_parquet(str(in_path))
    else:
        from npi_recovery import preflight
        res = preflight.robust_read(str(in_path))
        raw = res[1] if isinstance(res, tuple) else res
    mapping, _rep = schema.detect_columns(raw)
    std = schema.standardize(raw, mapping)
    mapping = {k: k for k, v in mapping.items() if v is not None and k in std.columns}
    # v47: auto-detect Medicare RIF (VRDC/CCW) input and standardize accordingly
    try:
        std2, mapping2, srep = schema.standardize_any(raw)
        if str(srep.get("source_format", "")).startswith("rif:"):
            std, mapping = std2, mapping2
            console.print(f"[dim]Detected Medicare RIF input ({srep['source_format']}); "
                          f"{srep.get('fields_mapped','?')} canonical fields mapped from "
                          f"RIF variables.[/dim]")
    except Exception:
        pass

    console.print(f"\n[bold]Fix and clean: {in_path.name}[/bold]  ({len(std)} rows)")
    out = clean_orchestrator.clean_all(std, ref_dir=config.REF_DIR, mapping=mapping)

    # v46: on large inputs with the engine enabled, cross-check the SQL screens
    from npi_recovery import engine as _ENG
    if args.engine in ("auto", "duckdb") and _ENG.duckdb_available() and len(std) >= 500000:
        try:
            sql_screens = _ENG.run_screens_sql(str(in_path), ref_dir=config.REF_DIR, mapping=mapping)
            console.print(f"[dim]SQL engine cross-check on {len(std):,} rows: "
                          + ", ".join(f"{k}={len(v)}" for k, v in sql_screens.items()
                                      if 'row' in getattr(v, 'columns', []))
                          + "[/dim]")
        except Exception:
            pass

    sc = out["scorecard"]
    console.print(f"[dim]{sc.attrs.get('note','')}[/dim]\n")
    t = Table(header_style="bold", show_lines=False)
    for c in ("category", "detail", "issues", "rows_affected", "dollars_exposed"):
        t.add_column(c)
    for _, r in sc.iterrows():
        d = r["dollars_exposed"]
        t.add_row(r["category"], str(r["detail"]), str(int(r["issues"])),
                  str(int(r["rows_affected"])),
                  "" if pd.isna(d) else f"${float(d):,.0f}")
    console.print(t)

    summ = out["issue_summary"]
    if isinstance(summ, pd.DataFrame) and not summ.empty:
        console.print(f"\n[dim]{summ.attrs.get('note','')}[/dim]")

    # write the cleaning workbook
    out_path = Path(args.out) if args.out else in_path.with_name(in_path.stem + "_cleaned.xlsx")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_clean_workbook(str(out_path), out, in_path.name)
    console.print(f"\n[green]Cleaning workbook written:[/green] {out_path}")

    # v46: optional multi-format export of the cleaned data and corrections
    if getattr(args, "export", None):
        from npi_recovery import export as _EX
        exp_dir = str(out_path.with_suffix("")) + "_export"
        frames = {"cleaned": out.get("cleaned"), "suggestions": out.get("suggestions"),
                  "issue_analysis": out.get("issue_summary"),
                  "scorecard": out.get("scorecard")}
        man = _EX.export_result({k: v for k, v in frames.items()
                                 if isinstance(v, pd.DataFrame) and not v.empty},
                                exp_dir, fmt=args.export)
        console.print(f"[green]Exported {len(man)} frames as {args.export}:[/green] {exp_dir}")
    return 0


def _write_clean_workbook(path, out, source_name):
    """Write the cleaning outputs to a workbook: scorecard, issue analysis,
    suggested corrections, per-screen flags, and the cleaned data."""
    import pandas as pd
    engine = "xlsxwriter"
    try:
        import xlsxwriter  # noqa: F401
    except Exception:
        engine = "openpyxl"
    kwargs = {"engine": engine}
    if engine == "xlsxwriter":
        kwargs["engine_kwargs"] = {"options": {"constant_memory": True, "in_memory": True}}
    with pd.ExcelWriter(path, **kwargs) as xw:
        pd.DataFrame({"field": ["source_file", "rows"],
                      "value": [source_name, len(out.get("cleaned", []))]}).to_excel(
            xw, sheet_name="About", index=False)
        out["scorecard"].to_excel(xw, sheet_name="Cleaning_Scorecard", index=False)
        if isinstance(out.get("issue_summary"), pd.DataFrame) and not out["issue_summary"].empty:
            out["issue_summary"].to_excel(xw, sheet_name="Issue_Analysis", index=False)
        if isinstance(out.get("suggestions"), pd.DataFrame) and not out["suggestions"].empty:
            out["suggestions"].head(200000).to_excel(xw, sheet_name="Suggested_Corrections", index=False)
        used = {"About", "Cleaning_Scorecard", "Issue_Analysis", "Suggested_Corrections"}
        for name, r in (out.get("screens") or {}).items():
            if not isinstance(r, pd.DataFrame) or r.empty:
                continue
            sheet = f"flags_{name}"[:31]
            if sheet in used:
                continue
            used.add(sheet)
            r.head(100000).to_excel(xw, sheet_name=sheet, index=False)


def _run_selected_fixes(args, in_path):
    """v42 one-thing-at-a-time path: read the file, standardize columns, build the
    fixability manifest, optionally run the chosen fixes, and write a focused
    workbook. Never runs the full pipeline."""
    from npi_recovery import registry as R
    from npi_recovery import schema, focused_report
    console = Console()

    # read + standardize (schema-adaptive; Komodo ships no public dictionary)
    suffix = in_path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        raw = pd.read_excel(str(in_path), dtype=str)
    elif suffix == ".parquet":
        raw = pd.read_parquet(str(in_path))
    else:
        from npi_recovery import preflight
        res = preflight.robust_read(str(in_path))
        raw = res[1] if isinstance(res, tuple) else res
    overrides = json.loads(args.map) if getattr(args, "map", None) else None
    mapping, _report = schema.detect_columns(raw, overrides=overrides)
    std = schema.standardize(raw, mapping)
    # standardize emits canonical-named columns, so the mapping the fixes see is identity
    mapping = {k: k for k, v in mapping.items() if v is not None and k in std.columns}

    ref_dir = os.path.join(os.path.dirname(schema.__file__), "reference")
    ctx = {"ref_dir": ref_dir, "mapping": mapping}

    manifest = R.fixability(std, mapping)
    coverage = R.field_coverage(std, mapping)
    n_del = int(coverage["delivered"].sum())
    console.print(f"\n[bold]Fixability on {in_path.name}[/bold]  ({len(std)} rows; "
                  f"{n_del} of {len(coverage)} canonical fields carry data)")
    t = Table(header_style="bold", show_lines=False)
    for c in ("fix", "status", "kahn_category", "missing_required", "missing_for_verdict"):
        t.add_column(c)
    for _, r in manifest.iterrows():
        color = {"supported": "green", "partial": "yellow", "unsupported": "red"}[r["status"]]
        t.add_row(r["fix"], f"[{color}]{r['status']}[/{color}]", r["kahn_category"],
                  r["missing_required"], r["missing_for_verdict"])
    console.print(t)
    console.print(f"[dim]{manifest.attrs.get('note','')}[/dim]")

    if not getattr(args, "fix", None):
        # fixability-only preview; still emit a one-sheet workbook if --out given
        if args.out:
            focused_report.write_focused(str(Path(args.out)), std, manifest, {}, in_path.name, coverage=coverage)
            console.print(f"\nManifest written to {args.out}")
        return 0

    if getattr(args, "fix_refresh", False):
        try:
            from npi_recovery import refresh_reference
            refresh_reference.refresh_all(ref_dir, console=console)
        except Exception as e:
            console.print(f"[yellow]reference refresh skipped: {type(e).__name__}: {e}[/yellow]")

    keys = [k.strip() for k in args.fix.split(",") if k.strip()]
    results = R.run_selected(std, keys, ctx)
    console.print(f"\n[bold]Ran {len(keys)} fix(es):[/bold]")
    for k in keys:
        r = results.get(k, pd.DataFrame())
        note = (r.attrs.get("note") if hasattr(r, "attrs") and r.attrs.get("note")
                else (r["note"].iloc[0] if "note" in getattr(r, "columns", []) and len(r) else ""))
        console.print(f"  [cyan]{k}[/cyan]: {len(r)} rows  {note}")

    out_path = Path(args.out) if args.out else \
        in_path.with_name(in_path.stem + "_fixes.xlsx")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    focused_report.write_focused(str(out_path), std, manifest, results, in_path.name, coverage=coverage)
    console.print(f"\n[green]Focused workbook written:[/green] {out_path}")
    return 0


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.serve:
        from npi_recovery.webapp import serve
        serve(port=args.port)
        return 0

    if args.health:
        from npi_recovery.health import run_health_check
        rows = run_health_check(cache_dir=args.cache_dir)
        _print_health(rows)
        return 0 if all(r["ok"] for r in rows) else 1

    if getattr(args, "list_fixes", False):
        from npi_recovery import registry as R
        cat = R.list_modules()
        console = Console()
        for grp in R.GROUP_ORDER:
            sub = cat[cat["group"] == R.GROUP_LABELS[grp]]
            if sub.empty:
                continue
            t = Table(title=R.GROUP_LABELS[grp], show_lines=False, header_style="bold")
            for c in ("key", "kahn_category", "requires", "reference", "touches"):
                t.add_column(c)
            for _, r in sub.iterrows():
                t.add_row(r["key"], r["kahn_category"], r["requires"],
                          r["reference"], r["touches"])
            console.print(); console.print(t)
        console.print("\nRun a subset with:  --fix key1,key2   (add --fixability to preview)")
        return 0

    if not args.input:
        print("ERROR: provide a claims file, or use --health to check data sources.", file=sys.stderr)
        return 2

    # v46 profile path: profile the input and exit
    if getattr(args, "profile", False):
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
            return 2
        return _run_profile(args, in_path)

    # v42 selectable-fix path: profile and/or run only the chosen fixes, then exit
    # without touching the full pipeline. This is the one-thing-at-a-time mode.
    if getattr(args, "clean_all", False):
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
            return 2
        return _run_clean_all(args, in_path)

    if getattr(args, "fixability", False) or getattr(args, "fix", None):
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
            return 2
        return _run_selected_fixes(args, in_path)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        return 2

    overrides = None
    if args.map:
        try:
            overrides = json.loads(args.map)
        except json.JSONDecodeError as e:
            print(f"ERROR: --map is not valid JSON: {e}", file=sys.stderr)
            return 2

    states = None
    if args.states:
        states = [x.strip().upper() for x in args.states.split(",") if x.strip()]

    out_path = Path(args.out) if args.out else \
        in_path.with_name(in_path.stem + "_NPI_recovered.xlsx")

    try:
        result = _run_with_progress(args, overrides, states)
    except Exception as e:
        print(f"\nERROR during recovery: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(result, str(out_path))
    # v23: three certainty-tiered deliverables (each a superset of the one above):
    #   1_Closed_Claims        = observed + direct lookups only (no inference)
    #   2_Recovered_Claims     = + measured point-attributed recovery (~89% k-fold)
    #   3_Statistically_Filled = + best-guess estimates written in (REQUIRES REVIEW)
    which = (result.stats or {}).get("outputs", "both")
    stem = in_path.stem
    closed_path = filled_path = statfull_path = None

    def _write(tag, w, label):
        path = out_path.with_name(f"{stem}_{tag}.xlsx")
        try:
            write_filled(result, str(path), which=w)
            return path
        except Exception as e:
            print(f"(note: could not write the {label} file: {type(e).__name__}: {e})", file=sys.stderr)
            return None

    if which in ("both", "verified"):
        closed_path = _write("1_Closed_Claims", "verified", "Closed Claims")
    if which in ("both", "statistical"):
        filled_path = _write("2_Recovered_Claims", "statistical", "Recovered Claims")
        if not getattr(result, "filled_statistical_full", pd.DataFrame()).empty:
            statfull_path = _write("3_Statistically_Filled", "statistical_full", "Statistically Filled")
    _print_summary(result, out_path, filled_path, closed_path, statfull_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
