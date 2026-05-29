"""Target Screener — the real Source workbench.

Route: GET /target-screener. The unified target-screening workbench for the
Source workflow:

    Source → Target Screener → evaluate → compare → just-missed scan
            → save screen → open profile / X-Ray → promote to Pipeline

Six screens, server-rendered, driven by ``?view=`` (main | inspector |
columns | compare | missed | saved). Recreated PEdesk-native from the
``workbench-full.html`` design handoff — NO iframe, NO external CDN fonts,
NO square-tile cartogram. The real US map (``render_us_geo_map``), the
vertical provider tables, compare, just-missed and saved-screen logic land in
the follow-up PRs (see docs/TARGET_SCREENER_WORKBENCH.md); this PR is the shell
+ navigation contract with clearly-labeled scaffolds for the not-yet-wired
screens.

Screens it searches: the real CMS/provider universes we have onboarded
(HCRIS hospitals, home health, hospice, SNF, dialysis, IRF, LTCH, provider
supply, market-only geographies). The historical deal corpus is NEVER an
active target universe — only ever a labeled benchmark/research reference.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional
from urllib.parse import quote as _uq

# ── Six workbench screens (the view= states) ─────────────────────────────
# group: "states" (01-03 workbench states) | "linked" (04-06 linked screens).
_VIEWS = [
    {"key": "main", "num": "01", "label": "Main", "emph": "Main",
     "sub": "SCREEN · MAP · TABLE", "group": "states"},
    {"key": "inspector", "num": "02", "label": "Inspector", "emph": "Inspector",
     "sub": "DRAWER · PEER · MARKET", "group": "states"},
    {"key": "columns", "num": "03", "label": "Columns", "emph": "Columns",
     "sub": "PICKER · METRIC DICT", "group": "states"},
    {"key": "compare", "num": "04", "label": "Compare", "emph": "Compare",
     "sub": "METRIC BY METRIC", "group": "linked"},
    {"key": "missed", "num": "05", "label": "Just missed", "emph": "missed",
     "sub": "MISS-DISTANCE SCAN", "group": "linked"},
    {"key": "saved", "num": "06", "label": "Saved screens", "emph": "Saved",
     "sub": "SHAREABLE · QUERY STATE", "group": "linked"},
]
_VIEW_KEYS = {v["key"] for v in _VIEWS}

# ── Vertical universes (separate screening modes) ────────────────────────
# ``live`` = a real loader is wired today; non-live verticals render an honest
# DATA REQUIRED / coming-soon state rather than fabricated rows.
_VERTICALS = [
    {"key": "hospitals", "label": "Hospitals", "universe": "HCRIS",
     "loader": "data.hcris", "live": True,
     "note": "CMS HCRIS cost-report universe — beds, revenue, margin, payer mix."},
    {"key": "home_health", "label": "Home Health", "universe": "CMS HHA",
     "loader": "data.home_health", "live": True,
     "note": "CMS Home Health Compare — providers, quality, CAHPS."},
    {"key": "hospice", "label": "Hospice", "universe": "CMS Hospice",
     "loader": "data.hospice", "live": True,
     "note": "CMS Hospice Compare — providers, quality, CAHPS."},
    {"key": "snf", "label": "SNF / Nursing", "universe": "CMS SNF",
     "loader": "data.snf", "live": True,
     "note": "CMS Nursing Home Compare — beds, SFF status, CHOW/ownership."},
    {"key": "dialysis", "label": "Dialysis", "universe": "CMS Dialysis",
     "loader": "data.dialysis", "live": True,
     "note": "CMS Dialysis Compare — stations, chain ownership, modalities."},
    {"key": "irf", "label": "IRF", "universe": "CMS IRF",
     "loader": "data.irf", "live": True,
     "note": "Inpatient Rehabilitation Facilities — providers, quality."},
    {"key": "ltch", "label": "LTCH", "universe": "CMS LTCH",
     "loader": "data.ltch", "live": True,
     "note": "Long-Term Care Hospitals — providers, quality."},
    {"key": "provider_supply", "label": "Provider Supply", "universe": "NPPES / supply",
     "loader": "data.provider_supply", "live": True,
     "note": "Physician / provider supply density by geography."},
    {"key": "market", "label": "Market (county/state)", "universe": "Public geo",
     "loader": "geo-intel", "live": True,
     "note": "Screen geographies (demographics, MA, SDOH, shortage) — not a "
             "provider, a market."},
]
_VERTICAL_KEYS = {v["key"] for v in _VERTICALS}

# Legacy modes preserved (backward compatible) — surfaced on Main as the three
# established ways into the SAME public universe; routes unchanged.
_MODES = [
    {"key": "sourcing", "label": "Thesis Sourcing", "href": "/source",
     "how": "Thesis-driven · ranks providers by fit to a thesis profile."},
    {"key": "hospital", "label": "Hospital Screener", "href": "/screen",
     "how": "Manual filters · you set the criteria."},
    {"key": "predictive", "label": "Predictive Screener", "href": "/predictive-screener",
     "how": "Model-ranked · scored over the public HCRIS universe."},
]

_CSS = """
/* 2026-05-28 layout redesign:
   - .tsw-meta CSS rule added (previously referenced but undefined,
     causing the title and subtitle inside each tab to render inline
     and produce the "overlapping text" the user reported).
   - .tsw-tab padding widened and column gap increased so the
     workbench-state numeral and the label stop touching.
   - .tsw-tab min-width raised so the 8-char subtitle has room.
   - Tier-4 style-sweep compliance: radii capped at 2px;
     decorative hover box-shadow on .ts-mode replaced with a
     subtle border-color shift (matches every other interactive
     card on the platform after the batch 30-43 sweep). */
/* 2026-05-28 wave-3 compaction: tabbar single-line. Group meta-labels
   ('Workbench states' / 'Linked screens') and per-tab subtitles are
   dropped; the two groups stay separated by a vertical hairline.
   Each tab is numeral + serif title only, ~108px wide vs the
   previous ~142px — six tabs comfortably fit in a single row at any
   reasonable viewport.
   Wave-7 sticky: the tabbar stays at top:58px (right below the
   chartis_shell topbar at top:0/height:58px) so the partner always
   sees the workbench navigation while scrolling through the ranked-
   providers table. z-index:30 stays below the topbar (z:50) and the
   subnav (z:40) but above all panel content. */
.tsw-tabs{display:flex;gap:0;overflow-x:auto;border:1px solid var(--sc-rule,#c9c1ac);
 border-radius:2px;background:var(--sc-paper-2,#f3eddb);margin:10px 0 14px;
 position:sticky;top:58px;z-index:30;}
.tsw-group{display:flex;}
.tsw-group + .tsw-group{border-left:1px solid var(--sc-rule,#c9c1ac);}
.tsw-tab{padding:8px 14px 7px;border-right:1px solid var(--sc-rule,#c9c1ac);
 display:flex;gap:8px;align-items:center;
 min-width:108px;text-decoration:none;background:var(--sc-paper-2,#f3eddb);}
.tsw-tab:last-child{border-right:0;}
.tsw-tab:hover{background:var(--sc-paper,#faf6ec);}
.tsw-tab.is-active{background:var(--sc-paper,#faf6ec);
 border-bottom:3px solid var(--sc-teal-deep,#0e3d39);padding-bottom:4px;}
.tsw-num{font-family:var(--sc-serif);font-style:italic;font-size:15px;line-height:1;
 color:var(--sc-teal,#155752);min-width:18px;text-align:center;}
.tsw-tab.is-active .tsw-num{color:var(--sc-teal-deep,#0e3d39);}
/* .tsw-meta wrapper retained (PR #1101 contract) but now holds only
   the title — the subtitle line is dropped. Keep it as flex so any
   future addition stacks cleanly. */
.tsw-meta{display:flex;flex-direction:column;gap:2px;min-width:0;}
.tsw-t{font-family:var(--sc-serif);font-size:13px;color:var(--sc-navy,#15202b);
 line-height:1.15;white-space:nowrap;}
.tsw-t em{font-style:italic;color:var(--sc-teal,#155752);}
.tsw-verticals{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 16px;}
.tsw-vert{font-family:var(--sc-mono);font-size:10px;letter-spacing:.03em;
 padding:4px 9px;border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;
 text-decoration:none;color:var(--sc-text,#2a3a4a);background:var(--sc-paper,#faf6ec);}
.tsw-vert:hover{border-color:var(--sc-teal,#155752);}
.tsw-vert.is-active{background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);border-color:var(--sc-navy,#15202b);}
.tsw-vert .u{opacity:.6;font-size:9px;}
/* Real provider-count badge on each universe chip — partner can
   compare scale (5,234 Hospitals vs 4,800 Hospice vs 15,200 SNF)
   without clicking into each. Source: live CMS loaders. */
.tsw-vert .n{margin-left:6px;padding:1px 5px;font-family:var(--sc-mono);
 font-size:9px;font-variant-numeric:tabular-nums;letter-spacing:.02em;
 background:var(--sc-bone,#ece5d6);color:var(--sc-text-dim,#6a7480);
 border-radius:2px;}
.tsw-vert.is-active .n{background:var(--sc-teal-deep,#0e3d39);color:#fff;}
.ts-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0;}
@media (max-width:900px){.ts-modes{grid-template-columns:1fr;}.tsw-tab{min-width:160px;}}
.ts-mode{display:flex;flex-direction:column;gap:4px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-top:2px solid var(--sc-teal,#155752);
 padding:9px 12px;text-decoration:none;
 transition:border-color 140ms ease;}
.ts-mode:hover{border-color:var(--sc-teal-deep,#0e3d39);}
.ts-mode.is-active{border-top-color:var(--sc-navy,#15202b);background:var(--sc-bone,#f3eddb);}
.ts-mode-label{font-family:var(--sc-serif);font-size:14px;color:var(--sc-navy,#15202b);line-height:1.2;}
.ts-mode-how{font-family:var(--sc-mono);font-size:10px;letter-spacing:.04em;
 color:var(--sc-text-dim,#6a7480);line-height:1.4;}
/* 2026-05-28 merged universe panel — three named sub-blocks (universe
   selector / active screen summary / pre-set entry points) inside
   one ck_panel. Each sub-block carries its own eyebrow lbl + prompt
   line + content, separated by a hairline rule so the user reads it
   as one coherent surface rather than three competing announcements. */
.ts-univ-block{padding:0 0 14px;margin:0 0 14px;
 border-bottom:1px solid var(--sc-rule,#c9c1ac);}
.ts-univ-block:last-child{padding-bottom:0;margin-bottom:0;border-bottom:0;}
.ts-univ-lbl{font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-teal,#155752);font-weight:700;
 margin-bottom:4px;}
.ts-univ-prompt{font-family:var(--sc-mono);font-size:11px;
 color:var(--sc-text-dim,#6a7480);margin-bottom:8px;}
.ts-univ-summary{font-family:var(--sc-serif);font-size:13.5px;line-height:1.55;
 color:var(--sc-text,#2a3a4a);margin:0 0 10px;max-width:80ch;}
.ts-univ-summary em{font-style:italic;color:var(--sc-text-dim,#6a7480);}
.ts-univ-code{font-family:var(--sc-mono);font-size:11px;
 color:var(--sc-text-dim,#6a7480);}
/* Active filter chip strip — every non-default query param renders
   as a removable chip in the Active-screen sub-block so partners can
   tell at a glance what's filtered (was buried in 4 different places
   pre-redesign). Each chip's href drops just that param. */
.ts-fchips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;
 margin:8px 0 0;}
.ts-fchips-lbl{font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);
 font-weight:700;margin-right:2px;}
.ts-fchip{display:inline-flex;align-items:center;gap:5px;
 padding:3px 6px 3px 8px;font-family:var(--sc-mono);font-size:10.5px;
 letter-spacing:.02em;text-decoration:none;
 background:var(--sc-bone,#ece5d6);color:var(--sc-text,#2a3a4a);
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;}
.ts-fchip:hover{background:#fff;border-color:var(--sc-warning,#b8732a);}
.ts-fchip-lbl{color:var(--sc-text-dim,#6a7480);text-transform:uppercase;
 letter-spacing:.06em;font-size:9px;font-weight:700;}
.ts-fchip-val{color:var(--sc-navy,#15202b);font-weight:600;}
.ts-fchip-x{color:var(--sc-text-faint,#8b94a0);font-size:13px;line-height:1;
 padding-left:2px;}
.ts-fchip:hover .ts-fchip-x{color:var(--sc-warning,#b8732a);}
.ts-fchip-clear{font-family:var(--sc-mono);font-size:10px;letter-spacing:.08em;
 text-transform:uppercase;color:var(--sc-warning,#b8732a);text-decoration:none;
 margin-left:6px;font-weight:600;}
.ts-fchip-clear:hover{text-decoration:underline;}
/* Top-N row-cap toggle above the table. Partners default to 150
   (the historical hard cap) but can focus on the strongest 10 / 25
   without scrolling. Each chip is a real GET link → bookmark-safe. */
.ts-topn{display:flex;flex-wrap:wrap;align-items:center;gap:5px;
 margin:0 0 8px;padding:6px 8px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;}
.ts-topn-lbl,.ts-topn-suffix{font-family:var(--sc-mono);font-size:9.5px;
 letter-spacing:.12em;text-transform:uppercase;
 color:var(--sc-text-faint,#8b94a0);font-weight:700;}
.ts-topn-suffix{margin-left:4px;}
.ts-topn-chip{display:inline-flex;align-items:center;justify-content:center;
 min-width:32px;padding:3px 9px;font-family:var(--sc-mono);font-size:11px;
 font-variant-numeric:tabular-nums;font-weight:600;text-decoration:none;
 color:var(--sc-text,#2a3a4a);background:#fff;
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;}
.ts-topn-chip:hover{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
.ts-topn-chip.is-active{background:var(--sc-navy,#15202b);color:#fff;
 border-color:var(--sc-navy,#15202b);}
/* Inline name/CCN/location filter input, lives in the same toolbar
   as the top-N chips so partners have all the table controls in one
   place. Pushed to the right by margin-left:auto so the chips own
   the left edge. */
.ts-topn-search{margin-left:auto;display:flex;align-items:center;gap:8px;
 flex:0 1 280px;min-width:180px;}
.ts-topn-search-input{flex:1;padding:5px 9px;font-family:var(--sc-sans,Inter Tight,sans-serif);
 font-size:12px;color:var(--sc-text,#2a3a4a);background:#fff;
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;}
.ts-topn-search-input:focus{outline:none;border-color:var(--sc-teal,#155752);
 box-shadow:0 0 0 1px var(--sc-teal,#155752);}
.ts-topn-search-input::placeholder{color:var(--sc-text-faint,#8b94a0);
 font-style:italic;}
.ts-topn-search-count{font-family:var(--sc-mono);font-size:10px;
 letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);
 font-variant-numeric:tabular-nums;white-space:nowrap;}
@media (max-width:720px){
  .ts-topn{flex-direction:column;align-items:stretch;}
  .ts-topn-search{margin-left:0;width:100%;flex:1 1 100%;}
}
/* Refine-filters disclosure (Min quality / Min size / Ownership).
   Collapsed by default — the form was ~50px of permanent chrome for
   a control most partners use once a session. <details open> when
   any filter inside is already active so the partner never loses
   state on a server round-trip. */
.ts-refine{margin:0 0 8px;padding:0;
 background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;}
.ts-refine-summary{padding:7px 12px;cursor:pointer;
 font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--sc-text-dim,#6a7480);font-weight:700;
 list-style:none;display:flex;align-items:center;gap:8px;}
.ts-refine-summary::-webkit-details-marker{display:none;}
.ts-refine-summary::before{content:"▸";font-size:11px;
 color:var(--sc-text-faint,#8b94a0);transition:transform 120ms ease;
 display:inline-block;width:10px;}
.ts-refine[open] .ts-refine-summary::before{transform:rotate(90deg);}
.ts-refine-summary:hover{color:var(--sc-teal,#155752);}
.ts-refine[open] .ts-refine-summary{border-bottom:1px solid var(--sc-rule,#c9c1ac);
 color:var(--sc-text,#2a3a4a);}
.ts-refine-form{padding:10px 12px 12px;}
.tsw-scaffold{background:var(--sc-paper,#faf6ec);border:1px dashed var(--sc-rule-2,#bfb6a2);
 border-radius:2px;padding:18px 20px;margin:14px 0;}
.tsw-scaffold h3{font-family:var(--sc-serif);font-size:14.5px;color:var(--sc-navy,#15202b);margin:0 0 6px;}
.tsw-scaffold .tag{font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-warning,#b8732a);}
.tsw-scaffold ul{margin:8px 0 0 18px;font-family:var(--sc-serif);font-size:13.5px;
 line-height:1.6;color:var(--sc-text,#2a3a4a);}
"""


# Map layers. ``provider_count`` is always real (derived from the active
# vertical's loader). Demographic/market layers link out to the geo-intel
# surfaces that own that real data rather than fabricating a shade here.
# ``geo`` maps the layer to a real ACS/CMS state metric (_MARKET_METRICS key)
# so the provider map can shade by real market demographics. Layers without a
# real per-state source stay as honest links out (no fabricated shade).
_LAYERS = [
    {"key": "provider_count", "label": "Provider count", "live": True},
    {"key": "age65", "label": "Age 65+", "live": True, "geo": "age_65_plus"},
    {"key": "income", "label": "Median HH income", "live": True, "geo": "median_income"},
    {"key": "uninsured", "label": "Uninsured %", "live": True, "geo": "uninsured_acs"},
    {"key": "ma_penetration", "label": "MA penetration", "live": False, "href": "/geo-intel"},
    {"key": "market_score", "label": "Market opportunity", "live": False, "href": "/market-intel/geo"},
]
_LAYER_BY_KEY = {ly["key"]: ly for ly in _LAYERS}


# Per-vertical table config: provider name attr, optional size metric, and
# the primary quality metric (key in the vertical's quality dict + label +
# whether higher is better). All real fields from the live CMS loaders.
_VERTICAL_TABLE = {
    "home_health": {"mod": "home_health", "pf": "load_home_health_providers",
                    "qf": "load_home_health_quality", "name": "provider_name",
                    "size": None, "q": ("star_rating", "Quality ★"), "src": "CMS Home Health Compare"},
    "hospice": {"mod": "hospice", "pf": "load_hospice_providers",
                "qf": "load_hospice_quality", "name": "facility_name",
                "size": None, "q": ("care_index_overall", "Care index"), "src": "CMS Hospice Compare"},
    "snf": {"mod": "snf", "pf": "load_snf_providers", "qf": "load_snf_quality",
            "name": "provider_name", "size": ("certified_beds", "Beds"),
            "q": ("overall_rating", "CMS ★"), "src": "CMS Nursing Home Compare"},
    "dialysis": {"mod": "dialysis", "pf": "load_dialysis_providers",
                 "qf": "load_dialysis_quality", "name": "facility_name",
                 "size": ("dialysis_stations", "Stations"),
                 "q": ("five_star", "5-star"), "src": "CMS Dialysis Compare"},
    "irf": {"mod": "irf", "pf": "load_irf_providers", "qf": "load_irf_quality",
            "name": "provider_name", "size": None,
            "q": ("dtc_rs_rate", "Disch→comm %"), "src": "CMS IRF Compare"},
    "ltch": {"mod": "ltch", "pf": "load_ltch_providers", "qf": "load_ltch_quality",
             "name": "provider_name", "size": None,
             "q": ("dtc_rs_rate", "Disch→comm %"), "src": "CMS LTCH Compare"},
}

_TABLE_LIMIT = 150
# Wave-5: user-pickable top-N for the ranked-providers table. 150 is
# the historical hard cap and stays the default; lower values let the
# partner focus on the strongest matches without scrolling, higher
# isn't useful here because the columns/inspector screens take over.
_TOP_N_CHOICES = (10, 25, 50, 100, 150)


def _q1(qs: Dict[str, List[str]], key: str, default: str = "") -> str:
    return (qs.get(key) or [default])[0].strip()


def _find_provider(ccn: str) -> Optional[Dict]:
    """Resolve a single CCN to its normalized row across every vertical
    (first match wins). Used by Compare, which only carries CCNs in
    ?compare=. Returns None if the CCN isn't in any live universe."""
    ccn = (ccn or "").strip()
    if not ccn:
        return None
    # Provider-dict verticals: O(1) dict lookup each.
    import importlib
    for vkey, cfg in _VERTICAL_TABLE.items():
        try:
            mod = importlib.import_module(f"..data.{cfg['mod']}", __package__)
            providers = getattr(mod, cfg["pf"])()
            p = providers.get(ccn)
            if p is None:
                continue
            quality = getattr(mod, cfg["qf"])() if hasattr(mod, cfg["qf"]) else {}
            qkey, qlabel = cfg["q"]
            size_attr, size_label = (cfg["size"] or (None, None))
            return {
                "ccn": ccn, "vertical": vkey,
                "name": str(getattr(p, cfg["name"], "") or "—"),
                "city": str(getattr(p, "city", "") or ""),
                "state": (getattr(p, "state", "") or "").strip().upper(),
                "ownership": str(getattr(p, "ownership", "") or "—"),
                "size": (_num_or_none(getattr(p, size_attr, None)) if size_attr else None),
                "size_label": size_label,
                "q": _num_or_none((quality.get(ccn, {}) or {}).get(qkey)),
                "q_label": qlabel, "q_pct": False, "source": cfg["src"],
            }
        except Exception:  # noqa: BLE001
            continue
    # Hospitals (HCRIS dataframe) — checked last (heavier).
    try:
        from ..data.hcris import load_hcris
        df = load_hcris()
        if df is not None and "ccn" in df.columns:
            m = df[df["ccn"].astype(str) == ccn]
            if not m.empty:
                r = m.iloc[0]
                return {
                    "ccn": ccn, "vertical": "hospitals",
                    "name": str(r.get("name", "") or "—"),
                    "city": str(r.get("city", "") or ""),
                    "state": str(r.get("state", "") or "").upper(),
                    "ownership": str(r.get("control_type", "") or "—"),
                    "size": _num_or_none(r.get("beds")), "size_label": "Beds",
                    "q": _num_or_none(r.get("operating_margin")),
                    "q_label": "Op margin", "q_pct": True, "source": "CMS HCRIS",
                }
    except Exception:  # noqa: BLE001
        pass
    return None


def _num_or_none(v) -> Optional[float]:
    """Coerce to float, returning None for None / NaN / non-numeric — so the
    table renders '—' rather than crashing or fabricating a value."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN != NaN


def _vertical_rows(vertical: str, state: str = "",
                   limit: Optional[int] = _TABLE_LIMIT) -> List[Dict]:
    """Normalized provider rows for the active vertical from the REAL loaders.
    Each row: ccn, name, city, state, ownership, size/size_label, q/q_label,
    source. Missing values are None (rendered '—'); never fabricated.
    ``limit=None`` returns the full universe (the just-missed scan needs it).
    """
    state = (state or "").upper()
    try:
        if vertical == "hospitals":
            from ..data.hcris import load_hcris
            df = load_hcris()
            if df is None or "ccn" not in df.columns:
                return []
            if state:
                df = df[df["state"].str.upper() == state]
            rows = []
            for _, r in (df if limit is None else df.head(800)).iterrows():
                margin = r.get("operating_margin")
                rows.append({
                    "ccn": str(r.get("ccn", "")), "name": str(r.get("name", "") or "—"),
                    "city": str(r.get("city", "") or ""), "state": str(r.get("state", "") or ""),
                    "ownership": str(r.get("control_type", "") or r.get("ownership", "") or "—"),
                    "size": _num_or_none(r.get("beds")), "size_label": "Beds",
                    "q": _num_or_none(margin),
                    "q_label": "Op margin", "q_pct": True, "source": "CMS HCRIS",
                })
            rows.sort(key=lambda x: (x["q"] is None, -(x["q"] or -9)))
            return rows[:limit] if limit else rows
        cfg = _VERTICAL_TABLE.get(vertical)
        if not cfg:
            return []
        import importlib
        mod = importlib.import_module(f"..data.{cfg['mod']}", __package__)
        providers = getattr(mod, cfg["pf"])()
        quality = getattr(mod, cfg["qf"])() if hasattr(mod, cfg["qf"]) else {}
        qkey, qlabel = cfg["q"]
        size_attr, size_label = (cfg["size"] or (None, None))
        rows = []
        for ccn, p in providers.items():
            st = (getattr(p, "state", "") or "").strip().upper()
            if state and st != state:
                continue
            qv = (quality.get(ccn, {}) or {}).get(qkey)
            rows.append({
                "ccn": str(ccn), "name": str(getattr(p, cfg["name"], "") or "—"),
                "city": str(getattr(p, "city", "") or ""), "state": st,
                "ownership": str(getattr(p, "ownership", "") or "—"),
                "size": (_num_or_none(getattr(p, size_attr, None)) if size_attr else None),
                "size_label": size_label, "q": _num_or_none(qv), "q_label": qlabel,
                "q_pct": False, "source": cfg["src"],
            })
        rows.sort(key=lambda x: (x["q"] is None, -(x["q"] if isinstance(x["q"], (int, float)) else -9)))
        return rows[:limit] if limit else rows
    except Exception:  # noqa: BLE001 — loader hiccup → honest empty table
        return []


def vertical_dataframe(vertical: str, state: str = ""):
    """A pandas DataFrame of the screened providers for CSV export — same
    real loader rows as the on-screen table, named columns, "—" for missing.
    Returns an empty DataFrame on unknown/failed verticals."""
    import pandas as pd
    rows = _vertical_rows(vertical, state, limit=None)
    if not rows:
        return pd.DataFrame()
    out = []
    for r in rows:
        out.append({
            "ccn": r["ccn"], "name": r["name"], "city": r["city"],
            "state": r["state"], "ownership": r["ownership"],
            (r.get("size_label") or "size"): (r["size"] if r.get("size") is not None else ""),
            (r["q_label"]): (r["q"] if r.get("q") is not None else ""),
            "source": r["source"], "vertical": vertical,
        })
    return pd.DataFrame(out)


def _provider_counts_by_state(vertical: str) -> Dict[str, int]:
    """Real provider counts per state for the active vertical, from the live
    CMS loaders. Returns {} on any load failure so the map shows an honest
    empty state rather than fabricated shading."""
    try:
        if vertical == "hospitals":
            from ..data.hcris import load_hcris
            df = load_hcris()
            if df is None or "state" not in df.columns:
                return {}
            vc = df.dropna(subset=["state"]).groupby(
                df["state"].str.upper())["ccn"].nunique()
            return {str(k): int(v) for k, v in vc.items() if str(k).strip()}
        _loaders = {
            "home_health": ("home_health", "load_home_health_providers"),
            "hospice": ("hospice", "load_hospice_providers"),
            "snf": ("snf", "load_snf_providers"),
            "dialysis": ("dialysis", "load_dialysis_providers"),
            "irf": ("irf", "load_irf_providers"),
            "ltch": ("ltch", "load_ltch_providers"),
        }
        if vertical in _loaders:
            mod_name, fn_name = _loaders[vertical]
            import importlib
            mod = importlib.import_module(f"..data.{mod_name}", __package__)
            providers = getattr(mod, fn_name)()
            counts: Dict[str, int] = {}
            for p in providers.values():
                st = (getattr(p, "state", "") or "").strip().upper()
                if st:
                    counts[st] = counts.get(st, 0) + 1
            return counts
    except Exception:  # noqa: BLE001 — any loader hiccup → honest empty map
        return {}
    return {}


def _href(view: str, qs: Dict[str, List[str]]) -> str:
    """Build a /target-screener link that switches view= but preserves the
    other shareable params (vertical/state/etc) — server-rendered state."""
    keep = {}
    for k in ("vertical", "state", "county", "metric", "layer", "ccn",
              "compare", "sort", "direction", "ownership", "provider_type"):
        v = _q1(qs, k)
        if v:
            keep[k] = v
    parts = [f"view={view}"] + [f"{k}={v}" for k, v in keep.items()]
    return "/target-screener?" + "&".join(parts)


def _vhref(vertical: str, qs: Dict[str, List[str]]) -> str:
    keep = {"vertical": vertical, "view": _q1(qs, "view", "main") or "main"}
    st = _q1(qs, "state")
    if st:
        keep["state"] = st
    return "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items())


def _tab_bar(active_view: str, qs: Dict[str, List[str]]) -> str:
    """Compact single-line tab bar.

    2026-05-28 wave-3 compaction: dropped the inline 'Workbench states /
    Linked screens' meta-labels and the per-tab subtitle line
    ('SCREEN · MAP · TABLE', 'DRAWER · PEER · MARKET', …). The
    subtitles repeated the panel titles found inside each view, and
    the meta-labels were nav-on-nav-on-nav. Tabs are now numeral +
    serif title only; the two groups stay separated by a vertical
    hairline so the workbench-vs-linked distinction reads visually
    without spending a row of text on it. Each tab also carries a
    title= attribute with the dropped subtitle so the discoverability
    moves into the hover affordance.
    """
    groups = ("states", "linked")
    html = ['<nav class="tsw-tabs" aria-label="Target Screener workbench screens">']
    for gkey in groups:
        html.append('<div class="tsw-group">')
        for v in (x for x in _VIEWS if x["group"] == gkey):
            cls = "tsw-tab is-active" if v["key"] == active_view else "tsw-tab"
            t = v["label"]
            if v["emph"] in t:
                t = t.replace(v["emph"], f'<em>{v["emph"]}</em>', 1)
            else:
                t = f'<em>{t}</em>'
            html.append(
                f'<a class="{cls}" href="{_href(v["key"], qs)}" '
                f'aria-current="{"page" if v["key"] == active_view else "false"}" '
                f'title="{v["sub"]}">'
                f'<span class="tsw-num">{v["num"]}</span>'
                f'<span class="tsw-meta"><span class="tsw-t">{t}</span></span></a>'
            )
        html.append('</div>')
    html.append('</nav>')
    return "".join(html)


@lru_cache(maxsize=16)
def _vertical_total(vertical: str) -> Optional[int]:
    """Return the real total provider count for a vertical, or None when
    the loader doesn't expose a sensible count (provider_supply/market
    are geo screens, not provider universes). Cached per-process so
    rendering the chip strip on every page load is cheap. Best-effort:
    any loader exception → None so the chip just hides its count
    rather than fabricating a number."""
    if vertical in ("provider_supply", "market"):
        return None
    counts = _provider_counts_by_state(vertical)
    if not counts:
        return None
    return int(sum(counts.values()))


def _vertical_chips_html(active_vertical: str, qs: Dict[str, List[str]]) -> str:
    """Just the chip strip — no surrounding prompt/label. Used by the
    merged universe panel which renders its own prompt inline.

    Each chip now carries a real provider-count badge so the partner
    can compare scale across universes at a glance (5,234 Hospitals vs
    4,800 Hospice vs 15,200 SNF) without having to click into each. The
    count comes from the real CMS loaders via _vertical_total — cached.
    Verticals without a provider universe (provider_supply, market)
    render no count rather than a fabricated one."""
    chips = []
    for v in _VERTICALS:
        cls = "tsw-vert is-active" if v["key"] == active_vertical else "tsw-vert"
        count = _vertical_total(v["key"])
        count_html = (
            f'<span class="n">{count:,}</span>' if count is not None else ""
        )
        chips.append(
            f'<a class="{cls}" href="{_vhref(v["key"], qs)}" title="{v["note"]}">'
            f'{v["label"]} <span class="u">{v["universe"]}</span>{count_html}</a>'
        )
    return '<div class="tsw-verticals">' + "".join(chips) + '</div>'


def _vertical_bar(active_vertical: str, qs: Dict[str, List[str]]) -> str:
    # Preserved for back-compat (used by some non-main views below).
    # Main view uses the merged universe panel instead.
    return ('<div style="font-family:var(--sc-mono);font-size:11px;'
            'letter-spacing:.08em;text-transform:uppercase;'
            'color:var(--sc-teal,#155752);font-weight:600;margin-bottom:7px;">'
            f'Screen which universe? &middot; {len(_VERTICALS)} CMS provider '
            'universes — toggle to switch</div>'
            + _vertical_chips_html(active_vertical, qs))


def _layer_chips_html(active_layer: str, qs: Dict[str, List[str]]) -> str:
    """Just the layer chips — no surrounding label/prompt. Used by the
    map-layer sub-block in the universe panel; previously inlined at
    the top of _render_map."""
    chips = []
    for ly in _LAYERS:
        if ly["live"]:
            keep = {"view": "main", "vertical": _q1(qs, "vertical", "hospitals"),
                    "layer": ly["key"]}
            st = _q1(qs, "state")
            if st:
                keep["state"] = st
            href = "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items())
            cls = "tsw-vert is-active" if ly["key"] == active_layer else "tsw-vert"
            chips.append(f'<a class="{cls}" href="{href}">{ly["label"]}</a>')
        else:
            # No fabricated shade — point at the surface that owns the real data.
            chips.append(
                f'<a class="tsw-vert" href="{ly["href"]}" '
                f'title="Lives on the geo/market intelligence surface (real data)">'
                f'{ly["label"]} <span class="u">↗ geo</span></a>')
    return '<div class="tsw-verticals">' + "".join(chips) + '</div>'


def _layer_subblock(qs: Dict[str, List[str]]) -> str:
    """Full Map-layer sub-block — eyebrow + prompt + chips. Renders in
    the universe panel right above the map so the partner picks
    universe → state filter → map shading layer in one continuous
    read, rather than scrolling down into the map panel to find it.
    The 'Map layer' label string is the load-bearing pin from
    test_layer_selector_present."""
    active_layer = _q1(qs, "layer", "provider_count") or "provider_count"
    return (
        '<div class="ts-univ-block">'
        '<div class="ts-univ-lbl">Map layer</div>'
        '<div class="ts-univ-prompt">'
        'Shade the map by a provider-density or market-context layer. '
        'Real data only — non-live layers link out to the surface that '
        'owns the real source rather than fabricating shade.'
        '</div>'
        + _layer_chips_html(active_layer, qs)
        + '</div>'
    )


# Back-compat wrapper. Some non-main views may still want a stand-alone
# bar; preserve the old "Map layer" label + chips shape.
def _layer_bar(active_layer: str, qs: Dict[str, List[str]]) -> str:
    return ('<div style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
            'text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin:2px 0 5px;">'
            'Map layer</div>' + _layer_chips_html(active_layer, qs))


def _render_map(vertical: str, qs: Dict[str, List[str]]) -> str:
    from .us_geo_map import render_us_geo_map
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    sel = _q1(qs, "state").upper()
    layer_key = _q1(qs, "layer", "provider_count") or "provider_count"
    ly = _LAYER_BY_KEY.get(layer_key)
    counts = _provider_counts_by_state(vertical)
    total = sum(counts.values())
    n_states = len(counts)
    if ly and ly.get("geo"):
        # Shade by a REAL market-demographic layer (ACS/CMS) overlaid on the
        # provider screen; the table below still lists providers.
        vals, mlabel, fmt, src = _geo_state_values("market", ly["geo"])
        map_html = render_us_geo_map(
            vals, metric_label=mlabel, value_format=fmt, selected_state=sel or None,
            map_title=f"{vinfo['label']} screen · {mlabel} market layer",
            exposure_label=f"{mlabel} (low&nbsp;→&nbsp;high)",
            caveat_text=(
                f"Real {src} — state-level {mlabel}, overlaid as market context on "
                f"the {vinfo['label']} screen. Click a state to filter providers; "
                f"the table below still lists {vinfo['label']} providers."),
            empty_message=f"No state-level {mlabel} available right now.")
        summary = (f'<p class="ck-section-body" style="margin:0 0 6px;">Map layer: '
                   f'<strong>{mlabel}</strong> (real {src}) as market context over '
                   f'the {vinfo["label"]} screen. The provider table below is '
                   f'unchanged — {total:,} providers across {n_states} states.</p>')
    else:
        map_html = render_us_geo_map(
            {k: float(v) for k, v in counts.items()},
            metric_label=f"{vinfo['label']} providers",
            value_format=lambda v: f"{int(v):,}",
            selected_state=sel or None,
            map_title=f"{vinfo['label']} provider density ({vinfo['universe']})",
            exposure_label=f"{vinfo['label']} provider count (low&nbsp;→&nbsp;high)",
            caveat_text=(
                f"Real CMS provider counts by state for the {vinfo['label']} "
                f"universe ({vinfo['universe']}). Click a state to filter the "
                "screen to it. Approximate Albers-projection SVG, not a precise "
                "facility-location map."),
            empty_message=(
                f"No state-level {vinfo['label']} provider counts available from "
                "the loader right now. Pick another vertical."),
        )
        summary = (f'<p class="ck-section-body" style="margin:0 0 6px;">'
                   f'{total:,} {vinfo["label"]} providers across {n_states} states '
                   f'(real {vinfo["universe"]} counts).</p>' if counts else "")
    # Click a state → server round-trip adding state= (server owns filter truth).
    listener = (
        "<script>(function(){document.addEventListener('us-map-select',"
        "function(e){var st=e&&e.detail&&e.detail.state;if(!st)return;"
        "var u=new URL(window.location.href);u.searchParams.set('state',st);"
        "u.searchParams.set('view','main');window.location.href=u.pathname+u.search;});"
        "})();</script>")
    filt = ""
    if sel:
        clear = _vhref(vertical, {})
        filt = (f'<p class="ck-section-body" style="margin:8px 0 0;">Filtered to '
                f'<strong>{sel}</strong> · <a class="ck-link" href="{clear}">clear '
                f'state filter</a>.</span></p>')
    # 2026-05-28 wave-4: layer bar moved up into the universe panel
    # (4th sub-block) so the partner picks universe → state filter →
    # map shading layer in one continuous read instead of scrolling
    # down into the visualization to find the shading control. The
    # map panel now contains just the summary + svg + click listener
    # + filter banner.
    return summary + map_html + listener + filt


def _fmt_q(row: Dict) -> str:
    v = row.get("q")
    if v is None:
        return '<span style="color:var(--sc-text-faint,#8b94a0)">—</span>'
    return f"{v:.1%}" if row.get("q_pct") else (f"{v:g}")


def _topn_toggle_html(vertical: str, qs: Dict[str, List[str]],
                      active_limit: int) -> str:
    """Render the 10/25/50/100/150 row-cap chip strip plus the inline
    client-side name-filter input, in a single toolbar above the table.

    Top-N chips are real GET links — server-rendered, bookmark-safe —
    and preserve every other relevant query param.

    The name-filter input is purely client-side: pure JS that toggles
    a hidden class on table rows whose data-ts-search blob doesn't
    contain the typed substring. No server round-trip, so typing
    feels instant in a 150-row table.
    """
    import html as _h
    # Carry-through params other than `limit`.
    keep_keys = ("state", "sort", "direction", "min_quality", "min_size",
                 "ownership", "hide", "compare", "layer")
    base = {"view": "main", "vertical": vertical}
    for k in keep_keys:
        v = _q1(qs, k)
        if v:
            base[k] = v

    chips = []
    for n in _TOP_N_CHOICES:
        q = dict(base)
        q["limit"] = str(n)
        href = "/target-screener?" + "&".join(
            f"{k}={_h.escape(str(v))}" for k, v in q.items()
        )
        cls = "ts-topn-chip is-active" if n == active_limit else "ts-topn-chip"
        chips.append(f'<a class="{cls}" href="{href}">{n}</a>')

    return (
        '<div class="ts-topn">'
        '<span class="ts-topn-lbl">Show top</span>'
        + "".join(chips)
        + '<span class="ts-topn-suffix">of matches</span>'
        # ── client-side instant name filter ─────────────────────
        '<span class="ts-topn-search">'
        '<input type="search" class="ts-topn-search-input" '
        'placeholder="Filter by name, CCN, city, state… (press /)" '
        'aria-label="Filter ranked providers by name, CCN, or location. '
        'Keyboard shortcut: press slash to focus, escape to clear and blur." '
        'data-ts-search-input>'
        '<span class="ts-topn-search-count" data-ts-search-count></span>'
        '</span>'
        '</div>'
        + _TS_SEARCH_JS
    )


# Idempotent install JS for the client-side row filter. Reads from
# every <tr data-ts-search="..."> in the page, hides rows that don't
# contain the typed substring, and updates the chip-counter.
#
# Wave-9 keyboard hotkeys:
#   - '/' anywhere on the page focuses the table search input
#     (standard GitHub/Slack/Linear pattern). Skipped when an
#     input/textarea/contenteditable already has focus so the
#     partner can keep typing in the Refine fields or any other form.
#   - ESC inside the search input clears the value, re-runs the
#     filter (revealing every row), then blurs so the partner can
#     scroll immediately.
_TS_SEARCH_JS = """
<script>
(function(){
  if (window.__rcmTsSearchInstalled) return;
  window.__rcmTsSearchInstalled = true;
  var ATTR = 'data-ts-search';
  function apply(input){
    var q = (input.value || '').trim().toLowerCase();
    var rows = document.querySelectorAll('tr['+ATTR+']');
    var shown = 0;
    rows.forEach(function(r){
      var blob = r.getAttribute(ATTR) || '';
      var match = !q || blob.indexOf(q) !== -1;
      r.style.display = match ? '' : 'none';
      if (match) shown++;
    });
    var c = input.parentNode.querySelector('[data-ts-search-count]');
    if (c){
      c.textContent = q ? (shown + ' of ' + rows.length) : '';
    }
  }
  document.addEventListener('input', function(e){
    var t = e.target;
    if (t && t.matches && t.matches('[data-ts-search-input]')) apply(t);
  });
  document.addEventListener('keydown', function(e){
    if (e.key !== '/') return;
    var a = document.activeElement;
    if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' ||
              a.isContentEditable)) return;
    var input = document.querySelector('[data-ts-search-input]');
    if (!input) return;
    e.preventDefault();
    input.focus();
    input.select();
  });
  document.addEventListener('keydown', function(e){
    if (e.key !== 'Escape') return;
    var t = e.target;
    if (!t || !t.matches || !t.matches('[data-ts-search-input]')) return;
    if (!t.value) { t.blur(); return; }
    t.value = '';
    apply(t);
    t.blur();
  });
})();
</script>
"""


def _render_table(vertical: str, qs: Dict[str, List[str]]) -> str:
    import html as _h
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    state = _q1(qs, "state").upper()
    # Load the full universe so the filters operate on everything, then cap
    # for display.
    all_rows = _vertical_rows(vertical, state, limit=None)
    if not all_rows:
        return (f'<p class="ck-section-body">No {vinfo["label"]} rows available '
                f'{("for " + state) if state else ""} from the loader right now. '
                f'Try another vertical or clear the state filter.</p>')
    total_universe = len(all_rows)
    # Apply the optional filter panel (min_quality / min_size / ownership).
    min_q = _f_or_none(qs, "min_quality")
    min_size = _f_or_none(qs, "min_size")
    own = _q1(qs, "ownership").strip().lower()
    rows = all_rows
    if min_q is not None:
        rows = [r for r in rows if isinstance(r.get("q"), (int, float)) and r["q"] >= min_q]
    if min_size is not None:
        rows = [r for r in rows if isinstance(r.get("size"), (int, float)) and r["size"] >= min_size]
    if own:
        rows = [r for r in rows if own in str(r.get("ownership", "")).lower()]
    n_matching = len(rows)
    # Wave-5: respect ?limit= from the top-N toggle. Validate against
    # the choice set so a hostile or stale URL can't ask for a
    # million rows; falls back to _TABLE_LIMIT (150) when absent or
    # invalid so existing behavior is unchanged on a clean page load.
    try:
        _limit_param = int(_q1(qs, "limit", str(_TABLE_LIMIT)))
    except ValueError:
        _limit_param = _TABLE_LIMIT
    if _limit_param not in _TOP_N_CHOICES:
        _limit_param = _TABLE_LIMIT
    row_limit = _limit_param
    rows = rows[:row_limit]

    size_label0 = (all_rows[0].get("size_label") or "Size")
    q_label0 = (all_rows[0].get("q_label") or "Quality")
    # Only offer a filter for a field this universe actually carries — a filter
    # on an all-empty field (e.g. hospitals' op margin / ownership in HCRIS)
    # does nothing, which read as "the top filters aren't working". Mirrors the
    # column-hiding: no data → no control.
    has_size_any = any(r.get("size") is not None for r in all_rows)
    has_q_any = any(r.get("q") is not None for r in all_rows)
    has_own_any = any(r.get("ownership") not in (None, "", "—") for r in all_rows)
    _inp = 'style="padding:4px 7px;border:1px solid var(--sc-rule,#c9c1ac);"'
    _lbl = 'style="font-family:var(--sc-mono);font-size:10px;"'
    # GET filter form (server-first, shareable). Keeps vertical/state/sort.
    #
    # Wave-8: wrap the form in a <details> so it collapses by default.
    # The form took ~50px of permanent vertical space even when no
    # refine-filters were active, dominating the table area for a
    # control most partners use once a session. <details> auto-opens
    # when any of its filters ARE active so the partner never loses
    # state. Active-filter chips in the universe panel still show
    # the partner what's filtered when the form is collapsed.
    refine_open = (min_q is not None or min_size is not None or own)
    summary_bits: List[str] = []
    if has_q_any:
        summary_bits.append(f"Min {q_label0.lower()}")
    if has_size_any:
        summary_bits.append(f"Min {size_label0.lower()}")
    if has_own_any:
        summary_bits.append("Ownership")
    refine_summary = (
        "Refine — " + " · ".join(summary_bits) if summary_bits
        else "Refine"
    )
    filter_form = (
        f'<details class="ts-refine"{" open" if refine_open else ""}>'
        f'<summary class="ts-refine-summary">{refine_summary}</summary>'
        '<form method="get" action="/target-screener" '
        'class="ts-refine-form" '
        'style="display:flex;gap:12px;'
        'align-items:flex-end;flex-wrap:wrap;margin:0;">'
        '<input type="hidden" name="view" value="main">'
        f'<input type="hidden" name="vertical" value="{vertical}">'
        + (f'<input type="hidden" name="state" value="{_h.escape(state)}">' if state else "")
        + (f'<label {_lbl}>Min {q_label0}'
           f'<br><input name="min_quality" value="{min_q if min_q is not None else ""}" size="6" '
           f'{_inp}></label>' if has_q_any else "")
        + (f'<label {_lbl}>Min {size_label0}'
           f'<br><input name="min_size" value="{min_size if min_size is not None else ""}" size="6" '
           f'{_inp}></label>' if has_size_any else "")
        + (f'<label {_lbl}>Ownership contains'
           f'<br><input name="ownership" value="{_h.escape(own)}" size="14" '
           f'{_inp}></label>' if has_own_any else "")
        + '<button type="submit" class="tsw-vert" style="cursor:pointer;">Apply filters</button>'
        + (f'<a class="ck-link" style="font-size:11px;" href="/target-screener?view=main&vertical={vertical}'
           + (f"&state={state}" if state else "") + '">clear</a>'
           if refine_open else "")
        + '</form>'
        '</details>'
    )
    size_label = size_label0
    q_label = q_label0
    if not rows:
        # Render the top-N toggle in the empty-state path too — the
        # partner may want to dial the cap back up after relaxing a
        # filter, and the toggle's chip-URLs already preserve all
        # the other params.
        top_n = _topn_toggle_html(vertical, qs, row_limit)
        return (filter_form + top_n
                + f'<p class="ck-section-body">No {vinfo["label"]} '
                f'providers match these filters (of {total_universe:,} in '
                f'{("scope " + state) if state else "the universe"}). Relax a '
                'filter — or open Just-missed to see who narrowly failed.</p>')
    has_size = any(r.get("size") is not None for r in rows)

    # Optional sort (?sort=name|location|size|quality & direction=asc|desc).
    # No sort param → keep the default quality-desc ranking from _vertical_rows.
    sort_key = _q1(qs, "sort").lower()
    direction = (_q1(qs, "direction").lower() or "desc")
    rev = direction != "asc"
    _keys = {
        "name": lambda r: (r.get("name") or "").lower(),
        "location": lambda r: (r.get("state") or "", (r.get("city") or "").lower()),
        "size": lambda r: (r.get("size") is None, -(r.get("size") or 0) if rev else (r.get("size") or 0)),
        "quality": lambda r: (r.get("q") is None, -(r.get("q") or 0) if rev else (r.get("q") or 0)),
    }
    if sort_key in _keys:
        if sort_key in ("name", "location"):
            rows = sorted(rows, key=_keys[sort_key], reverse=rev)
        else:  # numeric keys already fold direction into the key; None sinks last
            rows = sorted(rows, key=_keys[sort_key])

    # Optional column visibility (?hide=ownership,size,quality,source). Identity
    # (Provider) + Location + Open always show; the Columns screen toggles these.
    hide = {c for c in _q1(qs, "hide").split(",") if c}
    show_own = "ownership" not in hide
    show_size = has_size and "size" not in hide
    show_q = "quality" not in hide
    show_src = "source" not in hide
    # Force-hide a data column when this universe carries NO values for it
    # (e.g. hospitals report no ownership / operating margin in HCRIS). An
    # all-"—" column is dropped, never rendered blank — "the owner table
    # shouldn't be there if we can't give any information".
    def _has_any(field) -> bool:
        return any(r.get(field) not in (None, "", "—") for r in rows)
    if not _has_any("ownership"):
        show_own = False
    if has_size and not _has_any("size"):
        show_size = False
    if not _has_any("q"):
        show_q = False
    hide_param = ("&hide=" + ",".join(sorted(hide))) if hide else ""

    def _sh(label, col, align="left"):
        # Clickable header: sets sort=col and toggles asc/desc when re-clicked.
        nd = "asc" if (sort_key == col and direction == "desc") else "desc"
        keep = {"view": "main", "vertical": vertical, "sort": col, "direction": nd}
        if state:
            keep["state"] = state
        href = "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items()) + hide_param
        arrow = (" ▾" if direction == "desc" else " ▴") if sort_key == col else ""
        ta = f"text-align:{align};"
        return (f'<th style="padding:6px 8px;{ta}"><a class="ck-link" href="{href}">'
                f'{label}{arrow}</a></th>')

    head = (
        '<tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
        + _sh("Provider", "name")
        + _sh("Location", "location")
        + ('<th style="padding:6px 8px;text-align:left;">Ownership</th>' if show_own else "")
        + (_sh(size_label, "size", "right") if show_size else "")
        + (_sh(q_label, "quality", "right") if show_q else "")
        + ('<th style="padding:6px 8px;text-align:left;">Source</th>' if show_src else "")
        + '<th style="padding:6px 8px;text-align:left;">Open</th></tr>'
    )
    cur_cmp = [c for c in _q1(qs, "compare").split(",") if c]
    trs = []
    for r in rows:
        ccn = _h.escape(r["ccn"])
        xray = f'/diligence/xray?ccn={ccn}&vertical={vertical}'
        insp = _href("inspector", qs).split("?")[0] + f'?view=inspector&vertical={vertical}&ccn={ccn}'
        cmp_list = ",".join(dict.fromkeys(cur_cmp + [r["ccn"]]))  # append, de-dup
        cmp_href = f'/target-screener?view=compare&compare={cmp_list}'
        loc = _h.escape(", ".join([p for p in (r["city"], r["state"]) if p]) or "—")
        size_td = (f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">'
                   f'{int(r["size"]) if r.get("size") is not None else "—"}</td>') if show_size else ""
        own_td = (f'<td style="padding:5px 8px;">{_h.escape(str(r["ownership"]))}</td>'
                  if show_own else "")
        q_td = (f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">{_fmt_q(r)}</td>'
                if show_q else "")
        src_td = (f'<td style="padding:5px 8px;font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-dim,#6a7480);">{_h.escape(r["source"])}</td>'
                  if show_src else "")
        # Wave-6: data-ts-search carries a lowercased name+ccn+location
        # blob the client-side instant-filter input searches. Single
        # attribute → cheap selector lookup in the JS handler.
        search_blob = " ".join((
            (r.get("name") or ""),
            (r.get("ccn") or ""),
            (r.get("city") or ""),
            (r.get("state") or ""),
        )).lower()
        trs.append(
            f'<tr data-ts-search="{_h.escape(search_blob, quote=True)}" '
            'style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
            f'<td style="padding:5px 8px;font-weight:600;">{_h.escape(r["name"])}'
            f'<span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);"> · {ccn}</span></td>'
            f'<td style="padding:5px 8px;">{loc}</td>'
            f'{own_td}{size_td}{q_td}{src_td}'
            f'<td style="padding:5px 8px;white-space:nowrap;">'
            f'<a class="ts-act" href="{xray}">X-Ray</a>'
            f'<a class="ts-act" href="{insp}">Inspect</a>'
            f'<a class="ts-act" href="{cmp_href}">+Cmp</a></td>'
            '</tr>'
        )
    scope = f" · {state}" if state else ""
    filtered = (min_q is not None or min_size is not None or own)
    match_txt = (f"{n_matching:,} match of {total_universe:,}" if filtered
                 else f"{total_universe:,}")
    # Scoped editorial styling for the ranked table — a sticky shaded header,
    # zebra rows, row hover, tabular numerics, and the row actions rendered as
    # small chips (the bare "X-Ray · Inspect · +Cmp" text read as unformatted).
    table_css = (
        '<style>'
        '.ts-screen-table{width:100%;border-collapse:collapse;font-size:12.5px;'
        'font-family:var(--sc-sans,Inter Tight,sans-serif);}'
        '.ts-screen-table thead th{position:sticky;top:0;background:var(--sc-bone,#ece5d6);'
        'z-index:1;}'
        '.ts-screen-table tbody tr:nth-child(even){background:var(--sc-paper,#faf6ec);}'
        '.ts-screen-table tbody tr:hover{background:var(--sc-bone,#ece5d6);}'
        '.ts-screen-table td,.ts-screen-table th{vertical-align:middle;}'
        '.ts-act{display:inline-block;font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.03em;padding:2px 7px;border:1px solid var(--sc-rule,#c9c1ac);'
        'border-radius:3px;text-decoration:none;color:var(--sc-teal,#155752);'
        'background:#fff;margin:0 4px 0 0;white-space:nowrap;}'
        '.ts-act:hover{background:var(--sc-teal,#155752);color:#fff;'
        'border-color:var(--sc-teal,#155752);}'
        '</style>'
    )
    # Wave-5: top-N quick-toggle (10 / 25 / 50 / 100 / 150). Each chip
    # is a real GET link — server-rendered, shareable. Preserves the
    # current vertical / state / sort / direction / filters / hide
    # params; only flips ?limit=.
    top_n = _topn_toggle_html(vertical, qs, row_limit)
    return (
        table_css
        + filter_form
        + top_n
        + f'<p class="ck-section-body" style="margin:0 0 8px;">Showing {len(rows)} '
        f'of {match_txt} {vinfo["label"]} providers{scope} (ranked by '
        f'{q_label.lower()}; real {vinfo["universe"]} data, "—" = not reported). '
        f'Capped at {row_limit}.</p>'
        '<div style="overflow-x:auto;"><table class="ts-screen-table">'
        f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


# Market/geography verticals are screened at the STATE level (not individual
# providers). Each maps a (state -> value) layer + a ranked state table.
_MARKET_METRICS = [
    ("population", "Population", lambda v: f"{v/1e6:.2f}M"),
    ("age_65_plus", "Age 65+ %", lambda v: f"{v*100:.1f}%"),
    ("median_income", "Median income", lambda v: f"${v:,.0f}"),
    ("uninsured_acs", "Uninsured %", lambda v: f"{v*100:.1f}%"),
    ("provider_supply", "Provider supply", lambda v: f"{v:,.0f}"),
]


def _geo_state_values(vertical: str, metric: str):
    """Real (state -> value) map for a geography vertical. Returns
    (values, label, formatter, source). {} on failure → honest empty map."""
    try:
        if vertical == "provider_supply":
            from ..data.provider_supply import _state_type
            df = _state_type()
            g = df.groupby(df["state"].str.upper())["enrolled_count"].sum()
            return ({str(k): float(v) for k, v in g.items() if str(k).strip()},
                    "Medicare-enrolled providers", lambda v: f"{int(v):,}",
                    "CMS PECOS / provider enrollment")
        if vertical == "market":
            from ..data.state_demographics import STATE_ABBRS  # may not exist
    except Exception:  # noqa: BLE001
        pass
    if vertical == "market":
        try:
            from .us_geo_map import US_STATE_PATHS
            from .data_public.state_compare_page import _raw
            mk = next((m for m in _MARKET_METRICS if m[0] == metric), _MARKET_METRICS[0])
            vals = {}
            for st in US_STATE_PATHS.keys():
                v = (_raw(st) or {}).get(mk[0])
                if isinstance(v, (int, float)):
                    vals[st] = float(v)
            return vals, mk[1], mk[2], "ACS / CMS public geographic data"
        except Exception:  # noqa: BLE001
            return {}, "metric", (lambda v: f"{v:g}"), "public geo"
    return {}, "value", (lambda v: f"{v:g}"), "—"


def _render_geo_view(vertical: str, qs: Dict[str, List[str]], ck) -> str:
    import html as _h
    from .us_geo_map import render_us_geo_map
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    sel = _q1(qs, "state").upper()
    metric = _q1(qs, "metric") or ("population" if vertical == "market" else "supply")
    values, mlabel, fmt, source = _geo_state_values(vertical, metric)
    map_html = render_us_geo_map(
        values, metric_label=mlabel, value_format=fmt, selected_state=sel or None,
        map_title=f"{vinfo['label']} — {mlabel} by state",
        exposure_label=f"{mlabel} (low&nbsp;→&nbsp;high)",
        caveat_text=(f"Real {source} — state-level {mlabel}. This is a MARKET/"
                     "geography view, not individual providers. Click a state for "
                     "its market detail. Approximate Albers SVG."),
        empty_message=f"No state-level {mlabel} available right now.")
    # Metric selector for the market vertical.
    layer_bar = ""
    if vertical == "market":
        chips = []
        for key, lab, _f in _MARKET_METRICS:
            cls = "tsw-vert is-active" if key == metric else "tsw-vert"
            chips.append(f'<a class="{cls}" href="/target-screener?view=main&vertical=market&metric={key}'
                         + (f"&state={sel}" if sel else "") + f'">{lab}</a>')
        layer_bar = ('<div style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
                     'text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin:2px 0 5px;">'
                     'Market metric</div><div class="tsw-verticals">' + "".join(chips) + '</div>')
    # Ranked state table.
    rows = sorted(values.items(), key=lambda kv: -kv[1])
    trs = "".join(
        '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
        f'<td style="padding:5px 8px;font-weight:600;">{_h.escape(st)}</td>'
        f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">{fmt(v)}</td>'
        f'<td style="padding:5px 8px;"><a class="ck-link" href="/state-profile?state={_h.escape(st)}">market →</a> · '
        f'<a class="ck-link" href="/diligence/xray?state={_h.escape(st)}">X-Ray search →</a></td></tr>'
        for st, v in rows[:60]
    )
    table = ('<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
             '<thead><tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
             f'<th style="padding:6px 8px;">State</th><th style="padding:6px 8px;text-align:right;">{_h.escape(mlabel)}</th>'
             '<th style="padding:6px 8px;">Open</th></tr></thead>'
             f'<tbody>{trs}</tbody></table></div>') if rows else (
             '<p class="ck-section-body">No state-level values available.</p>')
    listener = (
        "<script>(function(){document.addEventListener('us-map-select',function(e){"
        "var st=e&&e.detail&&e.detail.state;if(!st)return;"
        "window.location.href='/state-profile?state='+encodeURIComponent(st);});})();</script>")
    # Real at-a-glance read of this market view (computed from the loaded
    # state values, no fabrication) — parity with the provider universes' KPI
    # strip so every screener universe opens informative.
    geo_kpis = ""
    if values:
        from ._chartis_kit import ck_kpi_block
        med = _median(list(values.values()))
        top_st, top_v = max(values.items(), key=lambda kv: kv[1])
        geo_kpis = (
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("States & territories", f"{len(values)}", "with data")
            + ck_kpi_block(f"Median {mlabel.lower()}",
                           fmt(med) if med is not None else "—", "across states")
            + ck_kpi_block("Highest", _h.escape(top_st), fmt(top_v))
            + '</div>')
    return (
        _vertical_bar(vertical, qs)
        + ck["panel"](
            f'<p class="ck-section-body" style="margin:0;"><strong>{vinfo["label"]}</strong> is a '
            f'<strong>market/geography</strong> view — it screens states (and, later, counties), '
            f'not individual providers. Real {source}. Click a state to open its '
            f'<a href="/geo-intel" class="ck-link">Geographic Intelligence</a> market detail.</p>'
            + geo_kpis,
            title="Market-level universe (not individual providers)")
        + ck["panel"](layer_bar + map_html + listener,
                      title=f"{mlabel} by state · click a state for market detail")
        + ck["panel"](table, title=f"States ranked by {mlabel}")
    )


def _scaffold(title: str, pr: str, bullets: List[str]) -> str:
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        f'<div class="tsw-scaffold"><span class="tag">Scaffold · wires in {pr}</span>'
        f'<h3>{title}</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:13.5px;color:var(--sc-text-dim,#6a7480);'
        f'margin:4px 0 0;">This workbench screen is structurally in place; its live data and '
        f'controls land in {pr}. Nothing fabricated is shown until then.</p>'
        f'<ul>{items}</ul></div>'
    )


def _active_filter_chips(vertical: str, qs: Dict[str, List[str]]) -> str:
    """Render every active filter on the page as a small removable chip.

    Pre-existing pain: state/min-quality/min-size/ownership filters were
    surfaced in four different places (state in the map summary, the
    other three only inside the table's filter form's clear-link, which
    only appeared if a filter was already applied). A partner couldn't
    glance at the top of the page and answer "what's filtered?".

    This helper builds one chip per non-default param. Each chip is a
    one-click "remove this filter" link — the href drops just that
    param while keeping every other current query value. A "Clear all
    filters" link follows when 2+ are active.
    """
    import html as _h
    state = _q1(qs, "state").upper()
    min_q = _q1(qs, "min_quality")
    min_size = _q1(qs, "min_size")
    own = _q1(qs, "ownership")
    sort_key = _q1(qs, "sort")

    # Catalog → label/value pairs.
    active: List[tuple] = []  # (param_key, chip_label, chip_value)
    if state:
        active.append(("state", "State", state))
    if min_q:
        active.append(("min_quality", "Min quality", min_q))
    if min_size:
        active.append(("min_size", "Min size", min_size))
    if own:
        active.append(("ownership", "Ownership", own))
    if sort_key:
        active.append(("sort", "Sort", sort_key))

    if not active:
        return ""

    # Server-first: every chip-remove link is a real URL the user can
    # bookmark. Same query state minus the one param being cleared.
    base_kept = {"view": "main", "vertical": vertical}

    def _remove_href(drop_key: str) -> str:
        kept = dict(base_kept)
        for k, _label, _val in active:
            if k == drop_key:
                continue
            kept[k] = _q1(qs, k)
        # Preserve sort direction whenever we keep sort.
        if "sort" in kept:
            dirn = _q1(qs, "direction")
            if dirn:
                kept["direction"] = dirn
        return "/target-screener?" + "&".join(
            f"{k}={_h.escape(str(v))}" for k, v in kept.items() if v
        )

    chips_html = "".join(
        f'<a class="ts-fchip" href="{_remove_href(k)}" '
        f'title="Remove the {_h.escape(lbl.lower())} filter">'
        f'<span class="ts-fchip-lbl">{_h.escape(lbl)}</span>'
        f'<span class="ts-fchip-val">{_h.escape(str(val))}</span>'
        f'<span class="ts-fchip-x" aria-hidden="true">×</span></a>'
        for k, lbl, val in active
    )
    clear_all = ""
    if len(active) >= 2:
        clear_all = (
            f'<a class="ts-fchip-clear" '
            f'href="/target-screener?view=main&vertical={vertical}">'
            f'Clear all filters</a>'
        )
    return (
        '<div class="ts-fchips" role="group" '
        'aria-label="Active filters">'
        f'<span class="ts-fchips-lbl">Active filters:</span>'
        f'{chips_html}{clear_all}'
        '</div>'
    )


def _universe_kpis(vertical: str, rows: List[Dict],
                   state_scope: str = "") -> str:
    """A computed at-a-glance read of the active universe — real counts from
    the loaded provider rows (no fabrication), so the screener is informative
    before any filter is applied. Only shows a metric when the universe
    actually carries it.

    Wave-10: ``state_scope`` (e.g. 'TX') rescopes the calculation to that
    state's providers and updates the sub-labels accordingly. Previously
    the KPI tiles always described the WHOLE universe ('6,123 providers /
    50 states'), even when the partner had filtered to TX — so the
    headline numbers were lying about what the table below was showing.
    """
    from ._chartis_kit import ck_kpi_block
    state_scope = (state_scope or "").upper()
    if state_scope:
        rows = [r for r in rows if (r.get("state") or "").upper() == state_scope]
    n = len(rows)
    if not n:
        return ""
    states = {r.get("state") for r in rows if r.get("state")}
    sizes = [r.get("size") for r in rows if isinstance(r.get("size"), (int, float))]
    qs_vals = [r.get("q") for r in rows if isinstance(r.get("q"), (int, float))]
    size_label = next((r.get("size_label") for r in rows if r.get("size_label")), None)
    q_label = next((r.get("q_label") for r in rows if r.get("q_label")), "Quality")
    # Sub-labels swap between the unfiltered-universe story and the
    # state-scoped story so the partner reads what they're seeing.
    scope_sub = f"in {state_scope}" if state_scope else "in this universe"
    blocks = [ck_kpi_block("Providers", f"{n:,}", scope_sub)]
    if not state_scope:
        # The "States & territories" tile is meaningless when the
        # universe is already scoped to one state — drop it instead
        # of rendering '1' which adds no information.
        blocks.append(ck_kpi_block("States & territories",
                                   f"{len(states)}", "CMS coverage"))
    if sizes:
        med = _median(sizes)
        med_sub = f"{len(sizes):,} reported"
        if state_scope:
            med_sub += f" · {state_scope}-only"
        blocks.append(ck_kpi_block(f"Median {size_label.lower()}",
                                   f"{med:,.0f}", med_sub))
    if qs_vals:
        pct = 100.0 * len(qs_vals) / n
        cov_sub = f"{len(qs_vals):,} of {n:,} report it"
        if state_scope:
            cov_sub += f" · {state_scope}-only"
        blocks.append(ck_kpi_block(f"{q_label} coverage", f"{pct:.0f}%",
                                   cov_sub))
    return f'<div class="ck-kpi-grid">{"".join(blocks)}</div>'


def _screen_main(vertical: str, qs: Dict[str, List[str]], ck) -> str:
    # Market/geography verticals screen states, not providers → geo view.
    if vertical in ("provider_supply", "market"):
        return _render_geo_view(vertical, qs, ck)
    active_mode = _q1(qs, "mode").lower()
    # 2026-05-28 better-fitted redesign: drop the "Open X →" footer
    # line from each mode card. The hover affordance (border-color
    # shift after batch 35) and the card-as-link semantics already
    # convey clickability; the extra mono ALL-CAPS line was the bulk
    # of each card's vertical footprint.
    cards = "".join(
        f'<a class="ts-mode{" is-active" if m["key"] == active_mode else ""}" '
        f'href="{m["href"]}">'
        f'<span class="ts-mode-label">{m["label"]}</span>'
        f'<span class="ts-mode-how">{m["how"]}</span></a>'
        for m in _MODES
    )
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])

    # 2026-05-28 better-fitted redesign: collapse the previous four
    # top-of-page panels (raw vertical bar + "Active universe" intro +
    # "Same universe, three ways in" + map) into a single "Choose a
    # universe & entry point" panel above the map and table.
    #
    # Why: the page was rendering navy-headered panels for the
    # universe-selector lead-in, the active-universe summary, AND the
    # entry-point mode cards — three full panels of CHROME before the
    # user reached the actual data. The user reported the page felt
    # "jumbled" and "split so weirdly", which traced directly to that
    # vertical stacking. One panel with three named sub-blocks
    # (universe / summary / entry points) reads as one coherent
    # control surface instead of three competing announcements.
    universe_panel = (
        # ── Sub-block 1: universe selector chips ──────────────
        '<div class="ts-univ-block">'
        '<div class="ts-univ-lbl">Universe</div>'
        '<div class="ts-univ-prompt">'
        f'Pick one of {len(_VERTICALS)} public CMS provider screens — '
        'toggle to switch:'
        '</div>'
        + _vertical_chips_html(vertical, qs)
        + '</div>'
        # ── Sub-block 2: active-universe summary + real KPIs +
        # any active filter chips (state / min-quality / etc.). The
        # filter chips render only when at least one filter is set,
        # so the sub-block stays clean on a fresh page load. Each
        # chip is a one-click "remove" link; "Clear all filters"
        # appears when 2+ chips are active.
        '<div class="ts-univ-block">'
        '<div class="ts-univ-lbl">Active screen</div>'
        f'<p class="ts-univ-summary">'
        f'<strong>{vinfo["label"]}</strong> &middot; '
        f'<span class="ts-univ-code">{vinfo["universe"]}</span>. '
        f'{vinfo["note"]} <em>Market data, not your deals.</em>'
        '</p>'
        + _universe_kpis(vertical, _vertical_rows(vertical, limit=None),
                         state_scope=_q1(qs, "state"))
        + _active_filter_chips(vertical, qs)
        + '</div>'
        # ── Sub-block 3: pre-set entry-point mode cards ───────
        '<div class="ts-univ-block">'
        '<div class="ts-univ-lbl">Or start with a pre-set entry point</div>'
        '<div class="ts-univ-prompt">'
        'All three run over the SAME public universe — pick the one that '
        'matches how you want to find candidates.'
        '</div>'
        f'<div class="ts-modes">{cards}</div>'
        '</div>'
        # ── Sub-block 4: map shading layer ──────────────────────
        # Sits at the END of the panel so it visually flows into the
        # map panel directly below. Previously inline at the top of
        # _render_map, which buried the control inside the
        # visualization — partners had to scroll into the map to
        # find it.
        + _layer_subblock(qs)
    )

    return (
        ck["panel"](universe_panel,
                    title="Choose a universe & entry point")
        + ck["panel"](_render_map(vertical, qs),
                      title="Provider density · click a state to filter")
        + ck["panel"](
            _render_table(vertical, qs)
            + (f'<p style="margin:10px 0 0;"><a class="ck-link" '
               f'href="/target-screener.csv?vertical={vertical}'
               + (f'&state={_q1(qs, "state").upper()}' if _q1(qs, "state") else "")
               + '">Download CSV (this screen) ↓</a></p>'),
            title="Ranked providers · real loader · X-Ray / Inspect / CSV")
        + ck["panel"](
            'Rank and score geographic markets first — '
            '<a href="/geo-intel" style="font-weight:600">Geographic Intelligence</a> '
            'and <a href="/market-intel/geo" style="font-weight:600">Geographic Market '
            'Intelligence &rarr;</a>. Then open a candidate\'s '
            '<a href="/diligence/hcris-xray" class="ck-link">HCRIS X-Ray</a> or '
            '<a href="/diligence/xray" class="ck-link">CMS X-Ray</a>, check its '
            'market, and <a href="/pipeline" class="ck-link">promote it to '
            'Pipeline</a>.',
            title="Screen the market, then the target · next steps")
    )


def _median(vals):
    vals = sorted(v for v in vals if isinstance(v, (int, float)))
    if not vals:
        return None
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2.0


def _guide_questions() -> List[str]:
    try:
        from ..assistant.context.suggested_questions import get_suggested_questions_for_page
        from ..assistant.context.manual_page_contexts import MANUAL_PAGE_CONTEXTS
        return get_suggested_questions_for_page(MANUAL_PAGE_CONTEXTS.get("/target-screener"))[:6]
    except Exception:  # noqa: BLE001
        return ["What does this page do?", "What data powers this result?"]


def _screen_inspector(qs, ck) -> str:
    import html as _h
    ccn = _q1(qs, "ccn")
    if not ccn:
        return _scaffold("Inspector — no target selected", "now", [
            "Open a row from Main (“Inspect”) or pass ?view=inspector&ccn=…&vertical=…",
            "Shows identity, source, key metrics, peer + market context, "
            "caveats, X-Ray / market links, and Guide questions — all real.",
        ])
    r = _find_provider(ccn)
    if not r:
        return (f'<p class="ck-section-body">CCN <code>{_h.escape(ccn)}</code> did '
                'not resolve to any live provider universe. Check the ID or pick '
                'a row from Main.</p>')
    vertical = r["vertical"]
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    state = r["state"]
    peers = _vertical_rows(vertical, state, limit=None)
    qvals = [p["q"] for p in peers if isinstance(p.get("q"), (int, float))]
    med = _median(qvals)
    rank_txt = "—"
    if isinstance(r.get("q"), (int, float)) and qvals:
        better = sum(1 for v in qvals if v <= r["q"])
        rank_txt = f"{100.0 * better / len(qvals):.0f}th percentile of {len(qvals)} {state} peers"
    q_label = r["q_label"]

    def _kv(label, val):
        return (f'<div style="display:flex;justify-content:space-between;gap:14px;'
                f'padding:5px 0;border-bottom:1px solid var(--sc-rule,#e4ddca);">'
                f'<span style="color:var(--sc-text-dim,#6a7480);">{label}</span>'
                f'<span style="font-weight:600;font-variant-numeric:tabular-nums;">{val}</span></div>')

    qcur = _fmt_q(r)
    qmed = (f"{med:.1%}" if (med is not None and r.get("q_pct")) else (f"{med:g}" if med is not None else "—"))
    identity = ck["panel"](
        f'<div style="font-family:var(--sc-serif);font-size:16px;color:var(--sc-navy,#15202b);">'
        f'{_h.escape(r["name"])}</div>'
        f'<div style="font-family:var(--sc-mono);font-size:10px;color:var(--sc-text-faint,#8b94a0);'
        f'margin-bottom:8px;">{_h.escape(ccn)} · {_h.escape(vertical)} · {_h.escape(vinfo["universe"])}</div>'
        + _kv("Location", _h.escape(", ".join([p for p in (r["city"], state) if p]) or "—"))
        + _kv("Ownership", _h.escape(str(r["ownership"])))
        + _kv(r.get("size_label") or "Size", f'{int(r["size"]):,}' if r.get("size") is not None else "—")
        + _kv(f"{q_label}", qcur)
        + _kv(f"{q_label} — {state} median", qmed)
        + _kv("Peer rank", rank_txt)
        + _kv("Source", f'<span style="font-family:var(--sc-mono);font-size:10px;">{_h.escape(r["source"])}</span>'),
        title="Selected target")
    links = ck["panel"](
        f'<a class="ck-link" href="/diligence/xray?ccn={_h.escape(ccn)}&vertical={vertical}">CMS X-Ray (full diligence) →</a><br>'
        + (f'<a class="ck-link" href="/diligence/hcris-xray?ccn={_h.escape(ccn)}">HCRIS X-Ray →</a><br>' if vertical == "hospitals" else "")
        + f'<a class="ck-link" href="/state-profile?state={state}">{state} market context →</a><br>'
        f'<a class="ck-link" href="/target-screener?view=compare&compare={_h.escape(ccn)}">Add to Compare →</a><br>'
        + (lambda slug, nm: (
            f'<a class="ck-link" href="/import?deal_id={_uq(slug)}&name={_uq(r["name"])}'
            f'{("&state=" + _uq(state)) if state else ""}">Promote to Pipeline '
            f'(prefilled deal) →</a>')
           )(f"{vertical}_{ccn}".lower().replace(" ", "_"), r["name"]),
        title="Open next")
    qs_list = "".join(f'<li>{_h.escape(q)}</li>' for q in _guide_questions())
    guide = ck["panel"](
        '<p class="ck-section-body" style="margin:0 0 6px;">Ask the Guide (drawer, top-right):</p>'
        f'<ul style="margin:0 0 0 18px;font-family:var(--sc-serif);font-size:13px;line-height:1.6;">{qs_list}</ul>',
        title="Guide")
    caveat = ('<p class="ck-section-body" style="font-style:italic;">Real CMS '
              f'{vinfo["universe"]} data; "—" = not reported. Peer rank is within '
              f'{state} for this vertical only — not a cross-vertical or investment '
              'judgment. No notes are fabricated.</p>')
    return identity + links + guide + caveat


def _quality_keys(vertical: str) -> List[str]:
    """The real extra quality-metric columns the vertical's loader exposes."""
    cfg = _VERTICAL_TABLE.get(vertical)
    if not cfg or not cfg.get("qf"):
        return []
    try:
        import importlib
        mod = importlib.import_module(f"..data.{cfg['mod']}", __package__)
        q = getattr(mod, cfg["qf"])()
        return list(next(iter(q.values())).keys()) if q else []
    except Exception:  # noqa: BLE001
        return []


def _screen_columns(qs, ck) -> str:
    import html as _h
    vertical = _q1(qs, "vertical", "hospitals") or "hospitals"
    if vertical not in _VERTICAL_KEYS:
        vertical = "hospitals"
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    rows = _vertical_rows(vertical, limit=None)
    n = len(rows) or 1
    src = vinfo["universe"]

    def _field_count(field) -> int:
        return sum(1 for r in rows if r.get(field) not in (None, "", "—"))

    def _avail(field) -> str:
        c = _field_count(field)
        pct = 100.0 * c / n
        return f'{c:,}/{len(rows):,} ({pct:.0f}%)'

    size_label = (rows[0].get("size_label") if rows and rows[0].get("size_label") else None)
    q_label = (rows[0]["q_label"] if rows else "Quality")
    # The columns the Main table currently surfaces, grouped by category, each
    # with its real source + a live availability count over the full universe.
    # Identity/Geography/Source are structural (always shown); the data columns
    # (ownership, size, quality) are only listed when this universe actually
    # carries them — a column CMS doesn't report (0 rows) is dropped entirely,
    # not shown at 0% (per "hide them entirely; an empty owner column shouldn't
    # be there"). _HIDDEN_ZERO is surfaced to the reader as a short footnote.
    cols = [
        ("Provider name", "Identity", "name", src),
        ("CCN", "Identity", "ccn", src),
        ("City", "Geography", "city", src),
        ("State", "Geography", "state", src),
    ]
    _hidden_zero: List[str] = []
    if _field_count("ownership") > 0:
        cols.append(("Ownership", "Ownership / consolidation", "ownership", src))
    else:
        _hidden_zero.append("Ownership")
    if size_label and _field_count("size") > 0:
        cols.append((size_label, "Size / operational", "size", src))
    elif size_label:
        _hidden_zero.append(size_label)
    if _field_count("q") > 0:
        cols.append((q_label, "Quality", "q", f"{src} quality"))
    else:
        _hidden_zero.append(q_label)
    cols.append(("Source", "Source / provenance", "source", "PEdesk provenance"))

    # Optional column visibility — these fields toggle on the Main table via
    # ?hide=. Identity/geography columns always show, so they read "always".
    state = _q1(qs, "state").upper()
    hide = {c for c in _q1(qs, "hide").split(",") if c}
    _toggle = {"ownership": "ownership", "size": "size", "q": "quality",
               "source": "source"}

    def _vis_cell(field) -> str:
        key = _toggle.get(field)
        if not key:
            return '<span style="color:var(--sc-text-faint,#8b94a0)">always</span>'
        hidden = key in hide
        new = (hide - {key}) if hidden else (hide | {key})
        base = f"/target-screener?view=main&vertical={vertical}"
        if state:
            base += f"&state={state}"
        if new:
            base += "&hide=" + ",".join(sorted(new))
        word = "Hidden · show" if hidden else "Shown · hide"
        return f'<a class="ck-link" href="{_h.escape(base)}">{word}</a>'

    # Group rows by category.
    from collections import OrderedDict
    groups: "OrderedDict[str, list]" = OrderedDict()
    for label, cat, field, source in cols:
        groups.setdefault(cat, []).append((label, field, source))

    body = []
    for cat, items in groups.items():
        trs = "".join(
            f'<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
            f'<td style="padding:5px 8px;font-weight:600;">{_h.escape(label)}</td>'
            f'<td style="padding:5px 8px;font-family:var(--sc-mono);font-size:10px;color:var(--sc-text-dim,#6a7480);">{_h.escape(source)}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">{_avail(field)}</td>'
            f'<td style="padding:5px 8px;font-size:11px;">{_vis_cell(field)}</td></tr>'
            for label, field, source in items
        )
        body.append(
            f'<h3 style="font-family:var(--sc-serif);font-size:15px;margin:14px 0 4px;color:var(--sc-navy,#15202b);">{_h.escape(cat)}</h3>'
            '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
            '<thead><tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
            '<th style="padding:6px 8px;">Column</th><th style="padding:6px 8px;">Source</th>'
            '<th style="padding:6px 8px;text-align:right;">Availability</th>'
            '<th style="padding:6px 8px;">On Main table</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div>'
        )

    extra_q = [k for k in _quality_keys(vertical) if k != _VERTICAL_TABLE.get(vertical, {}).get("q", ("",))[0]]
    extra = ""
    if extra_q:
        chips = " · ".join(_h.escape(k) for k in extra_q[:18])
        extra = (f'<h3 style="font-family:var(--sc-serif);font-size:15px;margin:14px 0 4px;color:var(--sc-navy,#15202b);">'
                 f'Additional {vinfo["label"]} quality columns available</h3>'
                 f'<p class="ck-section-body" style="margin:0;">From {src}, not yet surfaced in the '
                 f'table (real, available to add): <span style="font-family:var(--sc-mono);font-size:11px;">{chips}</span>.</p>')

    hidden_note = ""
    if _hidden_zero:
        hidden_note = (
            f'<p class="ck-section-body" style="margin:8px 0 0;color:'
            f'var(--sc-text-dim,#6a7480);font-size:11.5px;">Hidden for this '
            f'universe (CMS reports no values, so they\'re left off rather than '
            f'shown empty): '
            f'<span style="font-family:var(--sc-mono);font-size:11px;">'
            f'{_h.escape(", ".join(_hidden_zero))}</span>.</p>')
    return (
        f'<p class="ck-section-body" style="margin:0 0 8px;">Columns for the '
        f'<strong>{vinfo["label"]}</strong> universe ({src}), grouped by category '
        f'with real source + availability across {len(rows):,} providers. Columns '
        f'CMS doesn\'t report are dropped entirely — never shown at 0%.</p>'
        + "".join(body) + extra + hidden_note
    )


def _screen_compare(qs, ck) -> str:
    import html as _h
    comp = _q1(qs, "compare")
    ccns = [c.strip() for c in comp.split(",") if c.strip()][:6]
    if not ccns:
        return _scaffold("Compare basket (empty)", "now", [
            "Add targets from Main with “+ Compare”, or pass "
            "?compare=ccn1,ccn2,… (CCNs from any vertical).",
            "Same-vertical targets compare on every metric; cross-vertical "
            "targets compare only on shared metrics — vertical-specific rows "
            "show “not comparable”, never fabricated values.",
        ])
    found = [(c, _find_provider(c)) for c in ccns]
    cols = [(c, r) for c, r in found if r]
    missing = [c for c, r in found if not r]
    if not cols:
        return ('<p class="ck-section-body">None of the requested CCNs '
                f'({_h.escape(", ".join(ccns))}) resolved to a live provider '
                'universe. Check the IDs or add targets from Main.</p>')
    verticals = {r["vertical"] for _, r in cols}
    cross = len(verticals) > 1

    def _rm_link(drop):
        keep = [c for c, _ in cols if c != drop]
        return _href("compare", qs).split("?")[0] + (
            f'?view=compare&compare={",".join(keep)}' if keep else "?view=compare")

    # Header row: one column per provider with a remove (✕) control.
    ths = ['<th style="padding:6px 8px;text-align:left;">Metric</th>']
    for c, r in cols:
        ths.append(
            f'<th style="padding:6px 8px;text-align:left;vertical-align:top;">'
            f'{_h.escape(r["name"])}'
            f'<div style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);font-weight:400;">'
            f'{_h.escape(c)} · {_h.escape(r["vertical"])}</div>'
            f'<a class="ck-link" style="font-size:10px;" href="{_rm_link(c)}">✕ remove</a></th>')

    def _row(label, fn):
        tds = "".join(f'<td style="padding:5px 8px;">{fn(r)}</td>' for _, r in cols)
        return (f'<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
                f'<td style="padding:5px 8px;font-weight:600;">{label}</td>{tds}</tr>')

    def _q_cell(r):
        # Cross-vertical quality metrics aren't the same scale → label each;
        # if labels differ across the basket, say so rather than imply parity.
        val = _fmt_q(r)
        return f'{val} <span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);">{_h.escape(r["q_label"])}</span>'

    def _size_cell(r):
        if r.get("size") is None:
            return '<span style="color:var(--sc-text-faint,#8b94a0)">—</span>'
        return f'{int(r["size"]):,} <span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);">{_h.escape(r.get("size_label") or "")}</span>'

    rows_html = (
        _row("Vertical", lambda r: _h.escape(r["vertical"]))
        + _row("Location", lambda r: _h.escape(", ".join([p for p in (r["city"], r["state"]) if p]) or "—"))
        + _row("Ownership", lambda r: _h.escape(str(r["ownership"])))
        + _row("Size", _size_cell)
        + _row("Quality", _q_cell)
        + _row("Source", lambda r: f'<span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-dim,#6a7480);">{_h.escape(r["source"])}</span>')
        + _row("Open", lambda r: f'<a class="ck-link" href="/diligence/xray?ccn={_h.escape(r["ccn"])}&vertical={_h.escape(r["vertical"])}">CMS X-Ray →</a>')
    )
    note = ""
    if cross:
        note = ('<p class="ck-section-body" style="font-style:italic;margin:10px 0 0;">'
                'Cross-vertical comparison: only shared identity/size/quality rows '
                'are shown, and Size/Quality use each vertical&rsquo;s own metric '
                '(labeled per cell) — they are <strong>not directly comparable</strong> '
                'across verticals. Stick to one vertical for full metric parity.</p>')
    miss = ""
    if missing:
        miss = (f'<p class="ck-section-body" style="margin:8px 0 0;">Not found in any '
                f'live universe: {_h.escape(", ".join(missing))}.</p>')
    return (
        f'<p class="ck-section-body" style="margin:0 0 8px;">Comparing {len(cols)} '
        f'target(s){" across " + str(len(verticals)) + " verticals" if cross else ""}. '
        'Real CMS data; “—” = not reported.</p>'
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;'
        'font-size:12.5px;font-family:var(--sc-sans,Inter Tight,sans-serif);">'
        f'<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">{"".join(ths)}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>{note}{miss}'
    )


def _f_or_none(qs, key):
    v = _q1(qs, key)
    try:
        return float(v) if v != "" else None
    except ValueError:
        return None


def _screen_missed(qs, ck) -> str:
    import html as _h
    vertical = _q1(qs, "vertical", "hospitals") or "hospitals"
    if vertical not in _VERTICAL_KEYS:
        vertical = "hospitals"
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    state = _q1(qs, "state").upper()
    min_q = _f_or_none(qs, "min_quality")
    min_size = _f_or_none(qs, "min_size")

    rows = _vertical_rows(vertical, state, limit=None)
    q_label = (rows[0]["q_label"] if rows else "Quality")
    size_label = (rows[0].get("size_label") if rows and rows[0].get("size_label") else "Size")
    has_size = any(r.get("size") is not None for r in rows)

    # GET filter form (server-first, shareable). Hidden view/vertical keep state.
    form = (
        '<form method="get" action="/target-screener" class="tsw-verticals" '
        'style="align-items:flex-end;gap:14px;">'
        '<input type="hidden" name="view" value="missed">'
        f'<input type="hidden" name="vertical" value="{vertical}">'
        '<label style="font-family:var(--sc-mono);font-size:10px;">State'
        f'<br><input name="state" value="{_h.escape(state)}" size="3" '
        'style="font-family:var(--sc-mono);padding:3px 6px;"></label>'
        f'<label style="font-family:var(--sc-mono);font-size:10px;">Min {q_label}'
        f'<br><input name="min_quality" value="{min_q if min_q is not None else ""}" '
        'size="6" style="font-family:var(--sc-mono);padding:3px 6px;"></label>'
        + (f'<label style="font-family:var(--sc-mono);font-size:10px;">Min {size_label}'
           f'<br><input name="min_size" value="{min_size if min_size is not None else ""}" '
           'size="6" style="font-family:var(--sc-mono);padding:3px 6px;"></label>' if has_size else "")
        + '<button type="submit" class="tsw-vert" style="cursor:pointer;">Scan</button>'
        '</form>'
    )

    if min_q is None and min_size is None:
        return (form + '<p class="ck-section-body">Set a <strong>minimum '
                f'{q_label}</strong>' + (f' or <strong>minimum {size_label}</strong>'
                if has_size else "") + ' threshold and Scan. Just-missed surfaces real '
                f'{vinfo["label"]} providers that fail your filters by a single '
                'criterion — and flags those excluded only because a value is '
                '<em>missing</em> (not because they failed). No fabricated counts.</p>')

    # Evaluate each provider against the active numeric filters.
    just_missed, missing_data = [], []
    relax_q = relax_size = 0
    for r in rows:
        fails, dist_bits, miss_bits = [], [], []
        if min_q is not None:
            if r["q"] is None:
                miss_bits.append(f"{q_label} not reported")
            elif r["q"] < min_q:
                fails.append("q")
                dist_bits.append(f"{q_label} short by {min_q - r['q']:.3g}")
        if min_size is not None and has_size:
            if r.get("size") is None:
                miss_bits.append(f"{size_label} not reported")
            elif r["size"] < min_size:
                fails.append("size")
                dist_bits.append(f"{size_label} short by {min_size - r['size']:.0f}")
        if miss_bits and not fails:
            missing_data.append((r, miss_bits))
        elif len(fails) == 1:
            # near-miss distance for sorting (relative to threshold)
            if fails == ["q"]:
                d = (min_q - r["q"]) / (abs(min_q) or 1)
                relax_q += 1
            else:
                d = (min_size - r["size"]) / (abs(min_size) or 1)
                relax_size += 1
            just_missed.append((d, r, dist_bits))
    just_missed.sort(key=lambda t: t[0])

    relax_links = []
    if min_q is not None and relax_q:
        keep = {"view": "missed", "vertical": vertical}
        if state:
            keep["state"] = state
        if min_size is not None:
            keep["min_size"] = min_size
        href = "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items())
        relax_links.append(f'<a class="ck-link" href="{href}">Relax {q_label} → +{relax_q} providers</a>')
    if min_size is not None and relax_size:
        keep = {"view": "missed", "vertical": vertical}
        if state:
            keep["state"] = state
        if min_q is not None:
            keep["min_quality"] = min_q
        href = "/target-screener?" + "&".join(f"{k}={v}" for k, v in keep.items())
        relax_links.append(f'<a class="ck-link" href="{href}">Relax {size_label} → +{relax_size} providers</a>')

    def _row_html(r, bits):
        ccn = _h.escape(r["ccn"])
        cmp_href = f'/target-screener?view=compare&compare={ccn}'
        return (
            '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
            f'<td style="padding:5px 8px;font-weight:600;">{_h.escape(r["name"])}'
            f'<span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);"> · {ccn}</span></td>'
            f'<td style="padding:5px 8px;">{_h.escape(", ".join([p for p in (r["city"], r["state"]) if p]) or "—")}</td>'
            f'<td style="padding:5px 8px;color:var(--sc-warning,#b8732a);">{_h.escape("; ".join(bits))}</td>'
            f'<td style="padding:5px 8px;white-space:nowrap;">'
            f'<a class="ck-link" href="/diligence/xray?ccn={ccn}&vertical={vertical}">X-Ray</a> · '
            f'<a class="ck-link" href="{cmp_href}">+Cmp</a></td></tr>'
        )

    jm = "".join(_row_html(r, bits) for _, r, bits in just_missed[:50])
    md = "".join(_row_html(r, bits) for r, bits in missing_data[:30])
    out = [form]
    out.append(f'<p class="ck-section-body" style="margin:6px 0;"><strong>{len(just_missed)}</strong> '
               f'{vinfo["label"]} providers <em>just missed</em> by exactly one criterion'
               + (f' · {" · ".join(relax_links)}' if relax_links else "") + '.</p>')
    if jm:
        out.append('<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
                   '<thead><tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
                   '<th style="padding:6px 8px;">Provider</th><th style="padding:6px 8px;">Location</th>'
                   '<th style="padding:6px 8px;">Just missed because…</th><th style="padding:6px 8px;">Open</th></tr></thead>'
                   f'<tbody>{jm}</tbody></table></div>')
    else:
        out.append('<p class="ck-section-body">No single-criterion near-misses at these thresholds.</p>')
    if md:
        out.append(f'<p class="ck-section-body" style="margin:14px 0 4px;"><strong>Excluded only '
                   f'for missing data</strong> ({len(missing_data)}) — these were not failed, the '
                   f'value simply is not reported:</p>'
                   '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
                   '<thead><tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
                   '<th style="padding:6px 8px;">Provider</th><th style="padding:6px 8px;">Location</th>'
                   '<th style="padding:6px 8px;">Missing</th><th style="padding:6px 8px;">Open</th></tr></thead>'
                   f'<tbody>{md}</tbody></table></div>')
    return "".join(out)


_PRESET_SCREENS = [
    {"title": "SNF · TX · 4★ near-misses",
     "desc": "Texas nursing homes that just miss a 4-star overall rating.",
     "params": "view=missed&vertical=snf&state=TX&min_quality=4"},
    {"title": "Dialysis · CA",
     "desc": "California dialysis facilities ranked by 5-star score.",
     "params": "view=main&vertical=dialysis&state=CA"},
    {"title": "Home Health · FL",
     "desc": "Florida home-health agencies by quality star.",
     "params": "view=main&vertical=home_health&state=FL"},
    {"title": "Hospitals · TX",
     "desc": "Texas hospitals (HCRIS) ranked by operating margin.",
     "params": "view=main&vertical=hospitals&state=TX"},
    {"title": "Hospice · metric dictionary",
     "desc": "What hospice columns exist and how complete they are.",
     "params": "view=columns&vertical=hospice"},
]


def _screen_saved(qs, ck, saved: Optional[List[Dict]] = None, owner: str = "") -> str:
    import html as _h
    saved = saved or []
    # A screen IS its shareable URL. Build the current screen's link from the
    # active params (server-first state) — paste it anywhere to reopen.
    keep = {}
    for k in ("view", "vertical", "state", "county", "metric", "layer",
              "min_quality", "min_size", "ownership", "provider_type",
              "compare", "sort", "direction"):
        v = _q1(qs, k)
        if v:
            keep[k] = v
    keep.setdefault("view", "main")
    cur_qs = "&".join(f"{k}={_h.escape(v)}" for k, v in keep.items())
    cur_url = f"/target-screener?{cur_qs}"

    # Persisted, owner-scoped saved screens (real storage). When no user/owner
    # is resolvable, fall back to the honest shareable-URL-only state.
    saved_panel = ""
    if owner:
        if saved:
            cards = "".join(
                '<div style="display:flex;justify-content:space-between;gap:12px;align-items:center;'
                'padding:8px 0;border-bottom:1px solid var(--sc-rule,#e4ddca);">'
                f'<a class="ck-link" href="/target-screener?{_h.escape(s["query_params"])}">'
                f'{_h.escape(s["title"])}</a>'
                f'<span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);">'
                f'{_h.escape(str(s["created_at"])[:10])}</span>'
                f'<form method="post" action="/api/target-screener/delete" style="margin:0;">'
                f'<input type="hidden" name="id" value="{int(s["id"])}">'
                f'<button type="submit" class="ck-link" style="background:none;border:0;cursor:pointer;'
                f'font-size:11px;color:var(--sc-negative,#b5321e);">✕</button></form></div>'
                for s in saved
            )
        else:
            cards = ('<p class="ck-section-body" style="margin:0;">No saved screens yet — '
                     'name and save the current screen below.</p>')
        save_form = (
            '<form method="post" action="/api/target-screener/save" '
            'style="display:flex;gap:8px;align-items:flex-end;margin-top:10px;flex-wrap:wrap;">'
            f'<input type="hidden" name="query_params" value="{_h.escape(cur_qs)}">'
            '<label style="font-family:var(--sc-mono);font-size:10px;">Save current screen as'
            '<br><input name="title" required maxlength="160" placeholder="e.g. TX SNFs 4★" '
            'style="padding:5px 8px;border:1px solid var(--sc-rule,#c9c1ac);min-width:220px;"></label>'
            '<button type="submit" class="tsw-vert" style="cursor:pointer;">Save screen</button>'
            '</form>')
        saved_panel = ck["panel"](
            cards + save_form,
            title=f"Your saved screens ({len(saved)})")

    presets = "".join(
        f'<a class="ts-mode" href="/target-screener?{p["params"]}" '
        f'style="border-top-color:var(--sc-teal,#155752);">'
        f'<span class="ts-mode-label" style="font-size:16px;">{_h.escape(p["title"])}</span>'
        f'<span class="ts-mode-how">{_h.escape(p["desc"])}</span>'
        f'<span class="ts-mode-go">Open screen →</span></a>'
        for p in _PRESET_SCREENS
    )

    current = ck["panel"](
        '<p class="ck-section-body" style="margin:0 0 6px;">Your current screen '
        'is a shareable link — copy it to save or send:</p>'
        f'<input type="text" readonly value="{cur_url}" '
        'onclick="this.select()" style="width:100%;font-family:var(--sc-mono);'
        'font-size:11px;padding:7px 9px;border:1px solid var(--sc-rule,#c9c1ac);'
        'border-radius:2px;background:var(--sc-paper,#faf6ec);">'
        f'<p style="margin:6px 0 0;"><a class="ck-link" href="{cur_url}">Open this screen →</a></p>',
        title="Current screen (shareable URL)")

    preset_panel = ck["panel"](
        '<p class="ck-section-body" style="margin:0 0 8px;">Prebuilt screens — '
        'real query-param screens over live CMS data:</p>'
        f'<div class="ts-modes">{presets}</div>',
        title="Prebuilt screens")

    if owner:
        caveat = ck["panel"](
            '<p class="ck-section-body" style="margin:0;">Saved screens are now '
            'persisted per user (the <code>saved_screens</code> table). Each is a '
            'stored title + query string — open it to re-run live. Alerts on '
            'saved screens are <strong>not</strong> implemented; none are shown '
            '(no fake alerts).</p>',
            title="Persistence — live, owner-scoped")
    else:
        caveat = ck["panel"](
            '<p class="ck-section-body" style="margin:0;"><strong>Sign in to save '
            'named screens.</strong> Persistence is owner-scoped; without a '
            'session, screens are still fully usable as shareable URLs (above). '
            'No fake saved screens or alerts are shown.</p>',
            title="Persistence status — honest")

    return current + saved_panel + preset_panel + caveat


_SCREENS = {
    "inspector": _screen_inspector, "columns": _screen_columns,
    "compare": _screen_compare, "missed": _screen_missed, "saved": _screen_saved,
}


def render_target_screener(qs: Optional[Dict[str, List[str]]] = None,
                           *, saved: Optional[List[Dict]] = None,
                           owner: str = "") -> str:
    from ._chartis_kit import (chartis_shell, ck_page_title,
                               ck_panel, ck_source_purpose)
    qs = qs or {}
    view = _q1(qs, "view", "main")
    if view not in _VIEW_KEYS:
        view = "main"
    vertical = _q1(qs, "vertical", "hospitals")
    if vertical not in _VERTICAL_KEYS:
        vertical = "hospitals"
    ck = {"panel": ck_panel}

    # 2026-05-28 layout fix: drop the standalone CMS chip after the
    # title. The ck_source_purpose strip below already renders a CMS
    # PUBLIC DATA pill, so showing one here too produced the
    # "two CMS public data things" the user reported.
    title = ck_page_title(
        "Target Screener", eyebrow="SOURCE · /target-screener · WORKBENCH",
        meta="six screens · every public CMS/provider universe · same data, not your deals",
    )

    source_purpose = ck_source_purpose(
        purpose="Find acquisition targets across every public CMS/provider "
                "universe — hospitals, home health, hospice, SNF, dialysis, IRF, "
                "LTCH, provider supply, and markets — by filter, map, score, and "
                "just-missed scan, before committing diligence effort.",
        universe="cms",
        source="Real CMS / HCRIS / provider public universes (market data, not "
               "your deals). The historical deal corpus is never an active target.",
        next_action="Promote a result into the Pipeline to track it",
        next_href="/pipeline",
    )

    tab_bar = _tab_bar(view, qs)
    if view == "main":
        screen = _screen_main(vertical, qs, ck)
    elif view == "saved":
        screen = _screen_saved(qs, ck, saved=saved or [], owner=owner)
    else:
        screen = _SCREENS[view](qs, ck)

    # 2026-05-28 better-fitted redesign: drop the trailing
    # "One universe, one workbench" closer panel. Its content
    # ("market data, not your deals · Promote a result into the
    # Pipeline · Six screens") is already carried by the
    # source-purpose strip at the top of the page and by the
    # next-steps panel inside _screen_main — keeping it as the
    # final element repeated what the partner had already read
    # twice and ended the page on chrome instead of on the
    # next action.
    body = title + source_purpose + tab_bar + screen
    return chartis_shell(body, "Target Screener", active_nav="/target-screener",
                         extra_css=_CSS)
