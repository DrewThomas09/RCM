"""CLI for the public deals corpus.

Usage (from repo root with venv active):
    python -m rcm_mc.data_public.corpus_cli seed        --db corpus.db
    python -m rcm_mc.data_public.corpus_cli stats       --db corpus.db
    python -m rcm_mc.data_public.corpus_cli query       --db corpus.db [--buyer KKR] [--year-min 2015]
    python -m rcm_mc.data_public.corpus_cli ingest      --db corpus.db --source pe_portfolios
    python -m rcm_mc.data_public.corpus_cli full-ingest --db corpus.db [--sec-edgar] [--live-pe]
    python -m rcm_mc.data_public.corpus_cli rates       --db corpus.db
    python -m rcm_mc.data_public.corpus_cli intel       --db corpus.db --deal-id seed_007
    python -m rcm_mc.data_public.corpus_cli sensitivity --db corpus.db --deal-id seed_008

Runs fully standalone — no server required.
"""
from __future__ import annotations

import argparse
import json
import sys

from .deals_corpus import DealsCorpus
from .base_rates import full_summary
from .normalizer import normalize_batch
from .pe_intelligence import full_intelligence_report


def _cmd_seed(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)
    n = corpus.seed(skip_if_populated=not args.force)
    stats = corpus.stats()
    print(f"Seeded {n} deals. Corpus now has {stats['total']} deals "
          f"({stats['with_moic']} with realized MOIC, {stats['with_irr']} with IRR).")


def _cmd_stats(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)
    stats = corpus.stats()
    print(json.dumps(stats, indent=2))


def _cmd_query(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)
    rows = corpus.list(
        buyer_contains=args.buyer,
        year_min=args.year_min,
        year_max=args.year_max,
        with_moic=args.with_moic,
        with_irr=args.with_irr,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        print(f"{'Deal':<55} {'Year':>4} {'EV $M':>8} {'MOIC':>6} {'IRR':>7} Buyer")
        print("-" * 110)
        for r in rows:
            moic = f"{r['realized_moic']:.2f}x" if r.get("realized_moic") else "  —   "
            irr  = f"{r['realized_irr']:.1%}"   if r.get("realized_irr")  else "   —   "
            ev   = f"${r['ev_mm']:,.0f}"         if r.get("ev_mm")         else "   —   "
            year = str(r.get("year") or "  —")
            print(f"{r['deal_name'][:54]:<55} {year:>4} {ev:>8} {moic:>6} {irr:>7} "
                  f"{(r.get('buyer') or '')[:30]}")
        print(f"\n{len(rows)} deals")


def _cmd_ingest(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)

    if args.source == "pe_portfolios":
        from .scrapers.pe_portfolios import scrape_all
        raw_deals = scrape_all()
    elif args.source == "sec_edgar":
        from .scrapers.sec_filings import scrape_recent_hospital_ma
        raw_deals = scrape_recent_hospital_ma(max_hits=50)
    elif args.source == "news":
        from .scrapers.news_deals import scrape_news_deals
        raw_deals = scrape_news_deals(max_articles=30)
    else:
        print(f"Unknown source '{args.source}'. Use: pe_portfolios, sec_edgar, news")
        sys.exit(1)

    normalized = normalize_batch(raw_deals)
    inserted = 0
    for deal in normalized:
        corpus.upsert(deal)
        inserted += 1
    print(f"Ingested {inserted} deals from {args.source}. "
          f"Corpus now has {corpus.stats()['total']} total.")


def _cmd_rates(args: argparse.Namespace) -> None:
    summary = full_summary(args.db)
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
        return

    ov = summary["overall"]
    moic = ov["moic"]
    irr = ov["irr"]
    print(f"\n=== Corpus Base Rates (n={ov['n_deals']} deals) ===")
    print(f"  MOIC  P25={moic['p25']:.2f}x  P50={moic['p50']:.2f}x  P75={moic['p75']:.2f}x  "
          f"(n={ov['n_with_moic']})")
    print(f"  IRR   P25={irr['p25']:.1%}  P50={irr['p50']:.1%}  P75={irr['p75']:.1%}  "
          f"(n={ov['n_with_irr']})")

    print("\n  By size:")
    for bucket, bm in summary["by_size"].items():
        m = bm["moic"]
        if m["p50"]:
            print(f"    {bucket:8s}: MOIC P50={m['p50']:.2f}x  (n={bm['n_deals']})")

    print("\n  By dominant payer:")
    for payer, bm in summary["by_dominant_payer"].items():
        m = bm["moic"]
        if m["p50"]:
            print(f"    {payer:12s}: MOIC P50={m['p50']:.2f}x  (n={bm['n_deals']})")


def _cmd_intel(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found in corpus.")
        sys.exit(1)

    assumptions: dict = {}
    if args.assumptions:
        try:
            assumptions = json.loads(args.assumptions)
        except json.JSONDecodeError:
            print("--assumptions must be a JSON object string, e.g. '{\"entry_debt_mm\": 3500}'")
            sys.exit(1)

    report = full_intelligence_report(deal, assumptions, args.db)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2, default=str))
        return

    print(f"\n=== PE Intelligence Report: {report.deal_name} ===")
    print(f"  Deal type  : {report.deal_type.value}")
    print(f"  Risk score : {report.risk_score}/10")

    r = report.reasonableness
    print(f"\n  Reasonableness:")
    print(f"    IRR  band  : {r.irr_band[0]:.1%} – {r.irr_band[1]:.1%}  in_band={r.irr_in_band}")
    print(f"    MOIC band  : {r.moic_band[0]:.2f}x – {r.moic_band[1]:.2f}x  in_band={r.moic_in_band}")
    if r.payer_adjusted_moic_ceiling:
        print(f"    Payer-adj MOIC ceiling: {r.payer_adjusted_moic_ceiling:.2f}x")
    if r.corpus_moic_p50:
        print(f"    Corpus MOIC P50       : {r.corpus_moic_p50:.2f}x")
    for w in r.warnings:
        print(f"    ⚠  {w}")

    if report.red_flags:
        print(f"\n  Red Flags ({len(report.red_flags)}):")
        for f in report.red_flags:
            print(f"    {f}")

    if report.lever_warnings:
        print(f"\n  Lever Timeframe Warnings ({len(report.lever_warnings)}):")
        for w in report.lever_warnings:
            print(f"    {w}")

    if report.heuristic_notes:
        print(f"\n  Heuristic Notes ({len(report.heuristic_notes)}):")
        for n in report.heuristic_notes:
            print(f"    • {n}")


def _cmd_full_ingest(args: argparse.Namespace) -> None:
    from .ingest_pipeline import run_full_ingest, print_ingest_report
    report = run_full_ingest(
        args.db,
        sec_edgar=args.sec_edgar,
        live_pe=args.live_pe,
        verbose=True,
    )
    print_ingest_report(report)
    if args.json:
        import json as _json
        print(_json.dumps(report.as_dict(), indent=2, default=str))


def _cmd_rcm(args: argparse.Namespace) -> None:
    from .rcm_benchmarks import (
        get_benchmarks, get_all_benchmarks, benchmark_deal,
        rcm_opportunity, benchmarks_table,
    )
    if args.deal_id:
        corpus = DealsCorpus(args.db)
        deal = corpus.get(args.deal_id)
        if not deal:
            print(f"Deal '{args.deal_id}' not found.")
            sys.exit(1)
        opp = rcm_opportunity(deal)
        if args.json:
            print(json.dumps(opp, indent=2, default=str))
        else:
            print(f"\n  RCM Opportunity: {opp['deal_name']}")
            print(f"  Segment : {opp['benchmark_label']}")
            print(f"  Revenue : ${opp.get('revenue_mm', 0):,.0f}M" if opp.get("revenue_mm") else "  Revenue : —")
            print(f"  Est. EBITDA uplift: ${opp['estimated_total_ebitda_uplift_mm']:,.1f}M "
                  f"({opp.get('uplift_pct_of_ebitda','?'):.1%} of EBITDA)"
                  if opp.get("uplift_pct_of_ebitda") else
                  f"  Est. EBITDA uplift: ${opp['estimated_total_ebitda_uplift_mm']:,.1f}M")
            for lever, detail in opp["lever_details"].items():
                uplift = detail.get("estimated_ebitda_uplift_mm", 0)
                if uplift > 0:
                    print(f"    • {lever}: +${uplift:.1f}M EBITDA")
    elif args.segment:
        bm = get_benchmarks(args.segment)
        if args.json:
            print(json.dumps(bm.as_dict(), indent=2))
        else:
            print(f"\n  Benchmarks: {bm.label}")
            print(f"    Denial rate P50    : {bm.initial_denial_rate_p50:.1%}")
            print(f"    Clean claim P50    : {bm.clean_claim_rate_p50:.1%}")
            print(f"    Days in AR P50     : {bm.days_in_ar_p50:.0f} days")
            print(f"    Collection rate P50: {bm.collection_rate_p50:.1%}")
            print(f"    Write-off P50      : {bm.write_off_pct_p50:.1%}")
    else:
        if args.json:
            all_bm = get_all_benchmarks()
            print(json.dumps({k: v.as_dict() for k, v in all_bm.items()}, indent=2))
        else:
            print(benchmarks_table())


def _cmd_region(args: argparse.Namespace) -> None:
    from .regional_analysis import region_table, region_report, get_region_stats, find_regional_comps
    if args.deal_id:
        corpus = DealsCorpus(args.db)
        deal = corpus.get(args.deal_id)
        if not deal:
            print(f"Deal '{args.deal_id}' not found.")
            sys.exit(1)
        from .regional_analysis import classify_region
        region = classify_region(deal)
        comps = find_regional_comps(deal, args.db, n=args.n)
        if args.json:
            print(json.dumps({"region": region, "comps": comps}, indent=2, default=str))
        else:
            print(f"\n  Classified region: {region}")
            print(f"  Top {len(comps)} regional comparable deals:")
            for d in comps:
                moic = f"{d['realized_moic']:.2f}x" if d.get("realized_moic") else "—"
                print(f"    {d.get('deal_name','')[:55]}  MOIC={moic}")
    elif args.json:
        report = region_report(args.db)
        print(json.dumps(report.as_dict(), indent=2, default=str))
    else:
        print(region_table(args.db))


def _cmd_brief(args: argparse.Namespace) -> None:
    from .corpus_report import deal_brief, corpus_summary_report
    if args.corpus_summary:
        print(corpus_summary_report(args.db))
        return
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)
    overrides: dict = {}
    if args.assumptions:
        try:
            overrides = json.loads(args.assumptions)
        except json.JSONDecodeError:
            print("--assumptions must be JSON")
            sys.exit(1)
    entry_debt = overrides.pop("entry_debt_mm", None)
    print(deal_brief(deal, args.db, entry_debt_mm=entry_debt))


def _cmd_diligence(args: argparse.Namespace) -> None:
    from .diligence_checklist import build_checklist, checklist_text, checklist_json
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)

    overrides: dict = {}
    if args.assumptions:
        try:
            overrides = json.loads(args.assumptions)
        except json.JSONDecodeError:
            print("--assumptions must be JSON")
            sys.exit(1)

    entry_debt = overrides.pop("entry_debt_mm", None)
    checklist = build_checklist(deal, args.db, entry_debt_mm=entry_debt)

    if args.json:
        print(json.dumps(checklist_json(checklist), indent=2, default=str))
    else:
        print(checklist_text(checklist))


def _cmd_exit(args: argparse.Namespace) -> None:
    from .exit_modeling import (
        ExitAssumptions, model_all_exits, model_exit,
        exit_table, irr_sensitivity, ExitRoute,
    )
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)

    a_overrides: dict = {}
    if args.assumptions:
        try:
            a_overrides = json.loads(args.assumptions)
        except json.JSONDecodeError:
            print("--assumptions must be JSON, e.g. '{\"exit_multiple\": 10}'")
            sys.exit(1)

    assumptions = ExitAssumptions(**{k: v for k, v in a_overrides.items()
                                    if hasattr(ExitAssumptions, k)}) if a_overrides else ExitAssumptions()
    entry_debt = a_overrides.get("entry_debt_mm") or None

    if args.sensitivity:
        print(irr_sensitivity(deal, entry_debt))
        return

    results = model_all_exits(deal, entry_debt, assumptions)
    if args.json:
        import json as _json
        print(_json.dumps({k: v.as_dict() for k, v in results.items()}, indent=2, default=str))
    else:
        print(exit_table(results))


def _cmd_leverage(args: argparse.Namespace) -> None:
    from .leverage_analysis import model_leverage, covenant_headroom, leverage_table
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)

    overrides: dict = {}
    if args.assumptions:
        try:
            overrides = json.loads(args.assumptions)
        except json.JSONDecodeError:
            print("--assumptions must be a JSON object, e.g. '{\"interest_rate\": 0.085}'")
            sys.exit(1)

    profile = model_leverage(deal, overrides if overrides else None)

    if args.json:
        print(json.dumps(profile.as_dict(), indent=2, default=str))
    else:
        print(leverage_table(profile))
        ch = covenant_headroom(profile)
        print(f"\n  Min headroom: {ch['min_headroom_turns']:.2f}x turns (Year {ch['min_headroom_year']})")


def _cmd_vintage(args: argparse.Namespace) -> None:
    from .vintage_analysis import (
        vintage_table, vintage_report, entry_timing_assessment, get_vintage_stats
    )
    if args.year:
        if args.timing:
            result = entry_timing_assessment(args.year, args.db)
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"\nEntry Timing Assessment — {args.year}")
                print(f"  Cycle       : {result['cycle_label']} ({result['cycle']})")
                print(f"  Cycle MOIC P50  : {result['cycle_moic_p50']:.2f}x" if result.get("cycle_moic_p50") else "  Cycle MOIC P50  : —")
                print(f"  Overall MOIC P50: {result['overall_moic_p50']:.2f}x" if result.get("overall_moic_p50") else "  Overall MOIC P50: —")
                print(f"  Relative    : {result['relative_performance']}")
                for note in result["timing_notes"]:
                    print(f"    • {note}")
        else:
            vs = get_vintage_stats(args.year, args.db)
            if args.json:
                print(json.dumps(vs.as_dict(), indent=2))
            else:
                print(f"\nVintage {args.year} ({vs.cycle}): {vs.n_deals} deals")
                if vs.moic_p50:
                    print(f"  MOIC P50={vs.moic_p50:.2f}x  IRR P50={vs.irr_p50:.1%}" if vs.irr_p50 else f"  MOIC P50={vs.moic_p50:.2f}x")
    elif args.json:
        report = vintage_report(args.db)
        print(json.dumps(report.as_dict(), indent=2, default=str))
    else:
        print(vintage_table(args.db))


def _cmd_comps(args: argparse.Namespace) -> None:
    from .comparables import find_comparables, comparables_table
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)

    n = args.n
    if args.json:
        comps = find_comparables(deal, args.db, n=n)
        print(json.dumps([c.as_dict() for c in comps], indent=2, default=str))
    else:
        print(comparables_table(deal, args.db, n=n))


def _cmd_score(args: argparse.Namespace) -> None:
    from .deal_scorer import score_corpus, quality_report, score_deal
    corpus = DealsCorpus(args.db)

    if args.deal_id:
        deal = corpus.get(args.deal_id)
        if not deal:
            print(f"Deal '{args.deal_id}' not found.")
            sys.exit(1)
        s = score_deal(deal)
        if args.json:
            print(json.dumps(s.as_dict(), indent=2))
        else:
            print(f"\n  {s.deal_name}")
            print(f"  Grade: {s.grade}   Score: {s.total_score:.0f}/100")
            print(f"    Completeness : {s.completeness_score:.0f}/40")
            print(f"    Credibility  : {s.credibility_score:.0f}/40")
            print(f"    Source       : {s.source_score:.0f}/20")
            if s.issues:
                print(f"  Issues:")
                for iss in s.issues:
                    print(f"    • {iss}")
    elif args.json:
        scores = score_corpus(args.db)
        print(json.dumps([s.as_dict() for s in scores], indent=2))
    else:
        print(quality_report(args.db))


def _cmd_sensitivity(args: argparse.Namespace) -> None:
    corpus = DealsCorpus(args.db)
    deal = corpus.get(args.deal_id)
    if not deal:
        print(f"Deal '{args.deal_id}' not found.")
        sys.exit(1)

    from .payer_sensitivity import sensitivity_table, run_all_scenarios
    if args.json:
        results = run_all_scenarios(deal)
        import json as _json
        print(_json.dumps([r.as_dict() for r in results], indent=2, default=str))
    else:
        print(sensitivity_table(deal))


def _cmd_cms(args: argparse.Namespace) -> None:
    """CMS market analytics pipeline — concentration, regime, stress, advisory memo."""
    import pandas as pd
    from .cms_market_analysis import run_market_analysis, analysis_summary_text
    from .market_concentration import concentration_table
    from .provider_regime import regime_table
    from .cms_stress_test import (
        provider_investability_summary, provider_stress_test,
        stress_scenario_grid, provider_operating_posture,
        stress_table, posture_table, provider_value_summary,
    )
    from .cms_opportunity_scoring import provider_screen, opportunity_table
    from .cms_advisory_memo import build_advisory_memo, quick_memo

    year = args.year
    state = args.state
    provider_type = getattr(args, "provider_type", None)

    # Always run the base analysis (uses local df=None → CMS API, or df if provided)
    report = run_market_analysis(
        year=year,
        state=state,
        provider_type=provider_type,
        max_pages=args.max_pages,
    )

    if report.row_count == 0:
        if report.errors:
            print("CMS API errors:")
            for e in report.errors:
                print(f"  {e}")
        else:
            print("No data returned from CMS API.")
        return

    if args.concentration:
        print(concentration_table(report.concentration))
        return

    if args.regime:
        print(regime_table(report.regimes))
        return

    if args.opportunity:
        print(opportunity_table(report.concentration))
        return

    if args.stress:
        # Build investability and run stress test
        # (report doesn't hold raw df; build a minimal investability from regimes)
        if not report.regimes.empty and "regime_rank_score" in report.regimes.columns:
            inv_df = report.regimes[["provider_type", "regime_rank_score"]].rename(
                columns={"regime_rank_score": "opportunity_score"}
            )
            inv_df["total_payment"] = 0.0
            inv = provider_investability_summary(inv_df, pd.DataFrame(), pd.DataFrame())
            stress = provider_stress_test(inv)
            grid = stress_scenario_grid(inv)
            posture = provider_operating_posture(
                inv, pd.DataFrame(), report.geo_dependency, grid
            )
            if args.json:
                print(json.dumps({
                    "stress": stress[["provider_type", "stress_adjusted_score"]].to_dict("records"),
                    "posture": posture[["provider_type", "operating_posture", "posture_score"]].to_dict("records"),
                }, indent=2, default=str))
            else:
                print(stress_table(grid))
                print(posture_table(posture))
        else:
            print("No regime data for stress test.")
        return

    if args.json:
        d = report.as_summary_dict()
        if not report.concentration.empty:
            d["concentration_top5"] = report.concentration.head(5).to_dict("records")
        if not report.regimes.empty:
            d["regimes_top5"] = (
                report.regimes[["provider_type", "regime", "regime_rank_score"]]
                .head(5)
                .to_dict("records")
            )
        print(json.dumps(d, indent=2, default=str))
        return

    # Default: print advisory memo
    print(analysis_summary_text(report))


def _cmd_health_check(args: argparse.Namespace) -> None:
    """Run corpus health check and report data quality issues."""
    from .corpus_health_check import check_corpus, health_check_text
    corpus = DealsCorpus(args.db)
    corpus.seed(skip_if_populated=True)
    deals = corpus.list(limit=10000)
    result = check_corpus(deals)
    if args.json:
        issues_raw = [
            {"source_id": i.source_id, "deal_name": i.deal_name,
             "check": i.check, "severity": i.severity, "detail": i.detail}
            for i in result.issues
        ]
        print(json.dumps({
            "total_deals": result.total_deals,
            "clean_deals": result.clean_deal_count,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "info_count": result.info_count,
            "duplicate_source_ids": result.duplicate_source_ids,
            "health_score": result.health_score,
            "issues": issues_raw,
        }, indent=2))
    else:
        print(health_check_text(result))
    if result.error_count > 0 and not args.no_fail:
        sys.exit(1)


def _cmd_export(args: argparse.Namespace) -> None:
    """Export the full corpus to CSV, JSON, or Markdown."""
    from .corpus_export import to_csv, to_json, to_markdown
    corpus = DealsCorpus(args.db)
    corpus.seed(skip_if_populated=True)
    deals = corpus.list(limit=10000)
    fmt = args.format.lower()
    if fmt == "csv":
        out = to_csv(deals, path=args.output)
        if not args.output:
            print(out)
        else:
            print(f"Exported {len(deals)} deals to {args.output}")
    elif fmt == "json":
        out = to_json(deals, path=args.output)
        if not args.output:
            print(out)
        else:
            print(f"Exported {len(deals)} deals to {args.output}")
    elif fmt in ("markdown", "md"):
        out = to_markdown(deals)
        if args.output:
            import pathlib
            pathlib.Path(args.output).write_text(out)
            print(f"Exported {len(deals)} deals to {args.output}")
        else:
            print(out)
    else:
        print(f"Unknown format '{fmt}'. Use: csv, json, markdown")
        sys.exit(1)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="corpus",
        description="Public hospital M&A deals corpus CLI",
    )
    parser.add_argument("--db", default="corpus.db", help="Path to corpus SQLite file")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # seed
    s = sub.add_parser("seed", help="Load built-in seed deals into the corpus")
    s.add_argument("--force", action="store_true", help="Re-seed even if already populated")

    # stats
    sub.add_parser("stats", help="Print corpus statistics as JSON")

    # query
    q = sub.add_parser("query", help="Query deals with optional filters")
    q.add_argument("--buyer", default=None)
    q.add_argument("--year-min", type=int, default=None, dest="year_min")
    q.add_argument("--year-max", type=int, default=None, dest="year_max")
    q.add_argument("--with-moic", action="store_true", dest="with_moic")
    q.add_argument("--with-irr", action="store_true", dest="with_irr")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--json", action="store_true")

    # ingest
    i = sub.add_parser("ingest", help="Ingest deals from an external source")
    i.add_argument("--source", required=True,
                   choices=["pe_portfolios", "sec_edgar", "news"])

    # rates
    r = sub.add_parser("rates", help="Print P25/P50/P75 base rates from corpus")
    r.add_argument("--json", action="store_true")

    # intel
    n = sub.add_parser("intel", help="Run PE intelligence report on a corpus deal")
    n.add_argument("--deal-id", required=True, dest="deal_id")
    n.add_argument("--assumptions", default=None,
                   help="JSON string of model assumptions, e.g. '{\"entry_debt_mm\": 3500}'")
    n.add_argument("--json", action="store_true")

    # full-ingest
    fi = sub.add_parser("full-ingest", help="Run full corpus ingest pipeline (all sources)")
    fi.add_argument("--sec-edgar", action="store_true", dest="sec_edgar",
                    help="Include live SEC EDGAR scrape")
    fi.add_argument("--live-pe", action="store_true", dest="live_pe",
                    help="Include live PE firm portfolio scrape")
    fi.add_argument("--json", action="store_true")

    # sensitivity
    sv = sub.add_parser("sensitivity", help="Run payer-mix sensitivity analysis on a deal")
    sv.add_argument("--deal-id", required=True, dest="deal_id")
    sv.add_argument("--json", action="store_true")

    # rcm
    rcm = sub.add_parser("rcm", help="RCM benchmarks and opportunity sizing for a deal")
    rcm.add_argument("--deal-id", default=None, dest="deal_id",
                     help="Score RCM opportunity for a corpus deal")
    rcm.add_argument("--segment", default=None,
                     help="Show benchmarks for a specific segment "
                          "(community/academic/asc/behavioral/ltac/home_health/physician_group)")
    rcm.add_argument("--json", action="store_true")

    # region
    rg = sub.add_parser("region", help="Regional return analysis or classify a deal's region")
    rg.add_argument("--deal-id", default=None, dest="deal_id",
                    help="Classify a deal's region + show regional comps")
    rg.add_argument("--n", type=int, default=5, help="Number of regional comps to show")
    rg.add_argument("--json", action="store_true")

    # brief
    br = sub.add_parser("brief", help="One-page deal brief (all modules) for IC review")
    br.add_argument("--deal-id", default=None, dest="deal_id",
                    help="Corpus deal ID (omit to use --corpus-summary)")
    br.add_argument("--corpus-summary", action="store_true", dest="corpus_summary",
                    help="Print corpus-level summary report instead of a deal brief")
    br.add_argument("--assumptions", default=None,
                    help="JSON overrides, e.g. '{\"entry_debt_mm\": 2000}'")

    # diligence
    dil = sub.add_parser("diligence", help="Full IC diligence checklist for a corpus deal")
    dil.add_argument("--deal-id", required=True, dest="deal_id")
    dil.add_argument("--assumptions", default=None,
                     help="JSON overrides, e.g. '{\"entry_debt_mm\": 2000}'")
    dil.add_argument("--json", action="store_true")

    # exit
    ex = sub.add_parser("exit", help="Model exit scenarios and IRR/MOIC for a deal")
    ex.add_argument("--deal-id", required=True, dest="deal_id")
    ex.add_argument("--assumptions", default=None,
                    help="JSON overrides, e.g. '{\"exit_multiple\": 10, \"hold_years\": 4}'")
    ex.add_argument("--sensitivity", action="store_true",
                    help="Print IRR sensitivity table (exit multiple × hold years)")
    ex.add_argument("--json", action="store_true")

    # leverage
    lv = sub.add_parser("leverage", help="Model leverage structure and covenant headroom for a deal")
    lv.add_argument("--deal-id", required=True, dest="deal_id")
    lv.add_argument("--assumptions", default=None,
                    help="JSON overrides, e.g. '{\"interest_rate\": 0.085}'")
    lv.add_argument("--json", action="store_true")

    # vintage
    vt = sub.add_parser("vintage", help="Vintage year return analysis and entry timing")
    vt.add_argument("--year", type=int, default=None, help="Specific entry year to analyse")
    vt.add_argument("--timing", action="store_true",
                    help="Show entry timing assessment (requires --year)")
    vt.add_argument("--json", action="store_true")

    # comps
    cp = sub.add_parser("comps", help="Find comparable closed deals from the corpus")
    cp.add_argument("--deal-id", required=True, dest="deal_id")
    cp.add_argument("--n", type=int, default=5, help="Number of comparables to return")
    cp.add_argument("--json", action="store_true")

    # score
    sc = sub.add_parser("score", help="Score deal data quality (0-100, A-F grade)")
    sc.add_argument("--deal-id", default=None, dest="deal_id",
                    help="Score a single deal; omit for full corpus report")
    sc.add_argument("--json", action="store_true")

    # health-check
    hc = sub.add_parser("health-check", help="Run corpus data quality health check")
    hc.add_argument("--json", action="store_true", help="Output as JSON")
    hc.add_argument("--no-fail", action="store_true", dest="no_fail",
                    help="Exit 0 even when errors are found (default: exit 1 on errors)")

    # export
    ex2 = sub.add_parser("export", help="Export corpus to CSV, JSON, or Markdown")
    ex2.add_argument("--format", default="csv", choices=["csv", "json", "markdown", "md"],
                     help="Output format (default: csv)")
    ex2.add_argument("--output", default=None, help="Output file path (default: stdout)")

    # cms
    cm = sub.add_parser("cms", help="CMS market analytics (concentration, regime, stress, memo)")
    cm.add_argument("--year", type=int, default=2021, help="CMS dataset year (2021 or 2022)")
    cm.add_argument("--state", default=None, help="Two-letter state filter (e.g. TX)")
    cm.add_argument("--provider-type", default=None, dest="provider_type",
                    help="Provider type filter (e.g. 'Cardiology')")
    cm.add_argument("--max-pages", type=int, default=4, dest="max_pages",
                    help="Max CMS API pages to fetch (5000 rows/page)")
    cm.add_argument("--concentration", action="store_true",
                    help="Print market concentration table (HHI, CR3, CR5)")
    cm.add_argument("--regime", action="store_true",
                    help="Print provider regime classification table")
    cm.add_argument("--stress", action="store_true",
                    help="Print stress-test + operating posture table")
    cm.add_argument("--opportunity", action="store_true",
                    help="Print opportunity scores table")
    cm.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)

    dispatch = {
        "seed": _cmd_seed,
        "stats": _cmd_stats,
        "query": _cmd_query,
        "ingest": _cmd_ingest,
        "full-ingest": _cmd_full_ingest,
        "rates": _cmd_rates,
        "intel": _cmd_intel,
        "sensitivity": _cmd_sensitivity,
        "score": _cmd_score,
        "comps": _cmd_comps,
        "vintage": _cmd_vintage,
        "leverage": _cmd_leverage,
        "exit": _cmd_exit,
        "diligence": _cmd_diligence,
        "brief": _cmd_brief,
        "region": _cmd_region,
        "rcm": _cmd_rcm,
        "cms": _cmd_cms,
        "health-check": _cmd_health_check,
        "export": _cmd_export,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
