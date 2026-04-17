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
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
