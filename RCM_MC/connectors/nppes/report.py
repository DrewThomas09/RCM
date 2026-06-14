"""CDD market-structure brief generator.

Composes the `cdd` metrics into a single analyst-facing markdown deliverable
for a target thesis (a geography, optionally narrowed to a specialty). This
is the artifact that drops into an IC memo: how big the market is, how
consolidated it is, who the platforms are, how fragmented the long tail is
(roll-up runway), and what roster risk the revenue base carries.

Pure read-over-canonical-tables; no side effects. Returns a markdown string
(and a structured dict via ``market_brief_data`` for programmatic callers).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import cdd, systems as _systems


def market_brief_data(
    store: Any, *, geo_level: str = "state", geo: Optional[str] = None,
    classification: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the structured CDD signal for a market thesis."""
    tam = cdd.tam_by_taxonomy_geography(
        store, geo_level=geo_level, classification=classification, limit=500)
    if geo:
        tam = [r for r in tam if r["geo"] == geo]
    tam_total = sum(r["provider_count"] for r in tam)

    conc = cdd.market_concentration(
        store, geo_level=geo_level, classification=classification,
        min_providers=3, limit=500)
    if geo:
        conc = [r for r in conc if r["geo"] == geo]

    frag = cdd.fragmentation_scan(
        store, geo_level=geo_level, classification=classification,
        min_providers=5, limit=500)
    if geo:
        frag = [r for r in frag if r["geo"] == geo]

    growth = cdd.enumeration_trend(
        store, geo_level=geo_level, geo=geo, classification=classification)

    platforms = cdd.affiliation_footprint(store, min_confidence=0.5, limit=10)
    sys_all = _systems.health_systems(store, min_members=2, limit=100)
    if geo:
        sys_all = [s for s in sys_all if geo in s["states"]]
    targets = cdd.rollup_targets(
        store, classification=classification, geo_level=geo_level, geo=geo,
        max_captive=3, limit=25)
    roster = cdd.roster_integrity(store, geo_level=geo_level)

    avg_hhi = round(sum(r["hhi"] for r in conc) / len(conc), 1) if conc else None
    return {
        "scope": {"geo_level": geo_level, "geo": geo,
                  "classification": classification},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tam": {"total_providers": tam_total, "rows": tam[:25]},
        "concentration": {"avg_hhi": avg_hhi, "markets": conc[:15]},
        "fragmentation": frag[:15],
        "growth": growth,
        "platforms": platforms,
        "health_systems": sys_all[:15],
        "rollup_targets": targets,
        "roster": {k: v for k, v in roster.items() if k != "by_geo"},
    }


def _fmt_pct(v) -> str:
    return f"{v:.1f}%" if v is not None else "n/a"


def market_brief_markdown(
    store: Any, *, geo_level: str = "state", geo: Optional[str] = None,
    classification: Optional[str] = None,
) -> str:
    """Render the CDD market-structure brief as markdown."""
    d = market_brief_data(store, geo_level=geo_level, geo=geo,
                          classification=classification)
    scope = d["scope"]
    title_geo = geo or f"all {geo_level}s"
    title_spec = classification or "all specialties"
    L: List[str] = [
        f"# Market-Structure Brief — {title_geo} · {title_spec}",
        "",
        f"_Generated {d['generated_at']} from the NPPES provider universe._  ",
        "_Methodology: provider counts from `dim_provider` × practice "
        "geography; HHI from captive-provider share (DOJ/FTC bands); "
        "affiliation heuristic per DECISIONS.md D6. Provider-share is a "
        "revenue proxy, not billed revenue._",
        "",
        "## 1. Market size (TAM spine)",
        f"- **Total providers in scope: {d['tam']['total_providers']:,}**",
        "",
        "| Geography | Specialty | Providers |",
        "|---|---|---:|",
    ]
    for r in d["tam"]["rows"][:15]:
        L.append(f"| {r['geo']} | {r['classification']} | {r['provider_count']:,} |")

    avg_hhi = d["concentration"]["avg_hhi"]
    L += ["", "## 2. Concentration (HHI)",
          f"- **Average HHI across scoped markets: {avg_hhi if avg_hhi is not None else 'n/a'}** "
          f"({cdd._hhi_band(avg_hhi) if avg_hhi is not None else 'n/a'})",
          "- DOJ/FTC bands: <1500 unconcentrated · 1500–2500 moderate · >2500 highly concentrated",
          "",
          "| Geography | Specialty | Providers | Firms | HHI | Top firm | Band |",
          "|---|---|---:|---:|---:|---:|---|"]
    for r in d["concentration"]["markets"][:10]:
        L.append(f"| {r['geo']} | {r['classification']} | {r['total_providers']:,} | "
                 f"{r['firm_count']:,} | {r['hhi']:.0f} | {_fmt_pct(r['top_firm_share_pct'])} | "
                 f"{r['concentration_band']} |")

    L += ["", "## 3. Fragmentation & roll-up runway",
          "_Higher roll-up score = fragmented (low HHI) + high independent "
          "share + enough firms to consolidate._",
          "",
          "| Geography | Specialty | Providers | Indep. share | HHI | Roll-up score |",
          "|---|---|---:|---:|---:|---:|"]
    for r in d["fragmentation"][:10]:
        L.append(f"| {r['geo']} | {r['classification']} | {r['total_providers']:,} | "
                 f"{_fmt_pct(r['independent_share_pct'])} | {r['hhi']:.0f} | "
                 f"{r['rollup_score']:.1f} |")

    if d["growth"]:
        recent = d["growth"][-1]
        L += ["", "## 3b. Provider growth (enumeration cohorts)",
              f"- Latest cohort year **{recent['year']}**: "
              f"+{recent['new_providers']:,} new / −{recent['deactivated']:,} "
              f"deactivated (net {recent['net_growth']:+,})",
              "",
              "| Year | New | Deactivated | Net | Cumulative |",
              "|---|---:|---:|---:|---:|"]
        for r in d["growth"]:
            L.append(f"| {r['year']} | {r['new_providers']:,} | "
                     f"{r['deactivated']:,} | {r['net_growth']:+,} | "
                     f"{r['cumulative_net']:,} |")

    L += ["", "## 4. Incumbent platforms (captive-volume proxy)",
          "| Organization | NPI | Captive providers | Avg confidence |",
          "|---|---|---:|---:|"]
    for r in d["platforms"][:10]:
        L.append(f"| {r['organization_name'] or '(unnamed)'} | {r['npi']} | "
                 f"{r['captive_providers']:,} | {r['avg_confidence']} |")

    if d.get("health_systems"):
        L += ["", "## 4b. Multi-site health systems (org→org clustering)",
              "_Heuristic: organizations clustered by shared brand/surname "
              "name token + corroborating signal (see `systems.py`)._",
              "",
              "| System | Member orgs | States | Captive providers | Cohesion |",
              "|---|---:|---|---:|---:|"]
        for s in d["health_systems"][:10]:
            L.append(f"| {s['system_name']} | {s['member_count']} | "
                     f"{', '.join(s['states'][:6])} | {s['captive_providers']:,} | "
                     f"{s['cohesion']} |")

    L += ["", "## 5. Roll-up candidates (sub-scale independents)",
          "| Organization | NPI | Geography | Captive providers |",
          "|---|---|---|---:|"]
    for r in d["rollup_targets"][:15]:
        L.append(f"| {r['organization_name'] or '(unnamed)'} | {r['npi']} | "
                 f"{r['geo']} | {r['captive_providers']} |")

    ro = d["roster"]
    L += ["", "## 6. Roster integrity (revenue-base risk)",
          f"- Providers: **{ro['total_providers']:,}** · "
          f"deactivated: **{ro['deactivated']:,}** "
          f"({_fmt_pct(ro['deactivation_rate_pct'])}) · "
          f"reactivated: **{ro['reactivated']:,}**",
          "- Terminated providers in a target's roster erode the revenue base; "
          "a deactivation rate well above the universe norm is a diligence flag.",
          ""]
    return "\n".join(L)
