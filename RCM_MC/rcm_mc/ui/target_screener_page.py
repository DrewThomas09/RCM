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

from typing import Dict, List, Optional

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
.tsw-tabs{display:flex;gap:0;overflow-x:auto;border:1px solid var(--sc-rule,#c9c1ac);
 border-radius:3px;background:var(--sc-paper-2,#f3eddb);margin:14px 0 18px;}
.tsw-group{display:flex;}
.tsw-group + .tsw-group{border-left:1px solid var(--sc-rule,#c9c1ac);}
.tsw-glabel{padding:0 12px;font-family:var(--sc-mono);font-size:8px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);align-self:center;
 background:var(--sc-paper-3,#ece5d6);border-right:1px solid var(--sc-rule,#c9c1ac);
 line-height:1.3;}
.tsw-tab{padding:11px 16px 9px;border-right:1px solid var(--sc-rule,#c9c1ac);
 display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:center;
 min-width:170px;text-decoration:none;background:var(--sc-paper-2,#f3eddb);}
.tsw-tab:last-child{border-right:0;}
.tsw-tab:hover{background:var(--sc-paper,#faf6ec);}
.tsw-tab.is-active{background:var(--sc-paper,#faf6ec);border-bottom:3px solid var(--sc-teal-deep,#0e3d39);padding-bottom:6px;}
.tsw-num{font-family:var(--sc-serif);font-style:italic;font-size:21px;line-height:1;
 color:var(--sc-teal,#155752);width:22px;text-align:center;}
.tsw-tab.is-active .tsw-num{color:var(--sc-teal-deep,#0e3d39);}
.tsw-t{font-family:var(--sc-serif);font-size:14.5px;color:var(--sc-navy,#15202b);line-height:1.1;}
.tsw-t em{font-style:italic;color:var(--sc-teal,#155752);}
.tsw-s{font-family:var(--sc-mono);font-size:8px;letter-spacing:.1em;text-transform:uppercase;
 color:var(--sc-text-faint,#8b94a0);margin-top:3px;}
.tsw-verticals{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 16px;}
.tsw-vert{font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.04em;
 padding:5px 11px;border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;
 text-decoration:none;color:var(--sc-text,#2a3a4a);background:var(--sc-paper,#faf6ec);}
.tsw-vert:hover{border-color:var(--sc-teal,#155752);}
.tsw-vert.is-active{background:var(--sc-navy,#15202b);color:var(--sc-paper,#faf6ec);border-color:var(--sc-navy,#15202b);}
.tsw-vert .u{opacity:.6;font-size:9px;}
.ts-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:6px 0 var(--sc-s-5);}
@media (max-width:900px){.ts-modes{grid-template-columns:1fr;}.tsw-tab{min-width:140px;}}
.ts-mode{display:flex;flex-direction:column;gap:7px;background:var(--sc-paper,#faf6ec);
 border:1px solid var(--sc-rule,#c9c1ac);border-top:3px solid var(--sc-teal,#155752);
 padding:15px 17px;text-decoration:none;}
.ts-mode:hover{box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,.14));}
.ts-mode.is-active{border-top-color:var(--sc-navy,#15202b);background:var(--sc-bone,#f3eddb);}
.ts-mode-label{font-family:var(--sc-serif);font-size:19px;color:var(--sc-navy,#15202b);line-height:1.1;}
.ts-mode-how{font-family:var(--sc-mono);font-size:10px;letter-spacing:.04em;color:var(--sc-text-dim,#6a7480);}
.ts-mode-go{margin-top:auto;font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-teal,#155752);}
.tsw-scaffold{background:var(--sc-paper,#faf6ec);border:1px dashed var(--sc-rule-2,#bfb6a2);
 border-radius:3px;padding:18px 20px;margin:14px 0;}
.tsw-scaffold h3{font-family:var(--sc-serif);font-size:17px;color:var(--sc-navy,#15202b);margin:0 0 6px;}
.tsw-scaffold .tag{font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-warning,#b8732a);}
.tsw-scaffold ul{margin:8px 0 0 18px;font-family:var(--sc-serif);font-size:13.5px;
 line-height:1.6;color:var(--sc-text,#2a3a4a);}
"""


# Map layers. ``provider_count`` is always real (derived from the active
# vertical's loader). Demographic/market layers link out to the geo-intel
# surfaces that own that real data rather than fabricating a shade here.
_LAYERS = [
    {"key": "provider_count", "label": "Provider count", "live": True},
    {"key": "age65", "label": "Age 65+", "live": False, "href": "/geo-intel"},
    {"key": "income", "label": "Median HH income", "live": False, "href": "/geo-intel"},
    {"key": "uninsured", "label": "Uninsured %", "live": False, "href": "/geo-intel"},
    {"key": "ma_penetration", "label": "MA penetration", "live": False, "href": "/geo-intel"},
    {"key": "market_score", "label": "Market opportunity", "live": False, "href": "/market-intel/geo"},
]


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
    groups = {"states": "Workbench<br>states", "linked": "Linked<br>screens"}
    html = ['<nav class="tsw-tabs" aria-label="Target Screener workbench screens">']
    for gkey, glabel in groups.items():
        html.append(f'<div class="tsw-group"><div class="tsw-glabel">{glabel}</div>')
        for v in (x for x in _VIEWS if x["group"] == gkey):
            cls = "tsw-tab is-active" if v["key"] == active_view else "tsw-tab"
            t = v["label"]
            if v["emph"] in t:
                t = t.replace(v["emph"], f'<em>{v["emph"]}</em>', 1)
            else:
                t = f'<em>{t}</em>'
            html.append(
                f'<a class="{cls}" href="{_href(v["key"], qs)}" '
                f'aria-current="{"page" if v["key"] == active_view else "false"}">'
                f'<span class="tsw-num">{v["num"]}</span>'
                f'<span class="tsw-meta"><span class="tsw-t">{t}</span>'
                f'<span class="tsw-s">{v["sub"]}</span></span></a>'
            )
        html.append('</div>')
    html.append('</nav>')
    return "".join(html)


def _vertical_bar(active_vertical: str, qs: Dict[str, List[str]]) -> str:
    chips = []
    for v in _VERTICALS:
        cls = "tsw-vert is-active" if v["key"] == active_vertical else "tsw-vert"
        chips.append(
            f'<a class="{cls}" href="{_vhref(v["key"], qs)}" title="{v["note"]}">'
            f'{v["label"]} <span class="u">{v["universe"]}</span></a>'
        )
    return ('<div style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
            'text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin-bottom:5px;">'
            'Vertical / universe</div><div class="tsw-verticals">' + "".join(chips) + '</div>')


def _layer_bar(active_layer: str, qs: Dict[str, List[str]]) -> str:
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
    return ('<div style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
            'text-transform:uppercase;color:var(--sc-text-faint,#8b94a0);margin:2px 0 5px;">'
            'Map layer</div><div class="tsw-verticals">' + "".join(chips) + '</div>')


def _render_map(vertical: str, qs: Dict[str, List[str]]) -> str:
    from .us_geo_map import render_us_geo_map
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    sel = _q1(qs, "state").upper()
    counts = _provider_counts_by_state(vertical)
    total = sum(counts.values())
    n_states = len(counts)
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
            "the loader right now. Pick another vertical, or open the table "
            "(PR 4) once the loader is wired for this universe."),
    )
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
                f'state filter</a>. <span style="opacity:.7">Table filter applies '
                f'in PR 4.</span></p>')
    summary = (f'<p class="ck-section-body" style="margin:0 0 6px;">'
               f'{total:,} {vinfo["label"]} providers across {n_states} states '
               f'(real {vinfo["universe"]} counts).</p>' if counts else "")
    return (_layer_bar(_q1(qs, "layer", "provider_count") or "provider_count", qs)
            + summary + map_html + listener + filt)


def _fmt_q(row: Dict) -> str:
    v = row.get("q")
    if v is None:
        return '<span style="color:var(--sc-text-faint,#8b94a0)">—</span>'
    return f"{v:.1%}" if row.get("q_pct") else (f"{v:g}")


def _render_table(vertical: str, qs: Dict[str, List[str]]) -> str:
    import html as _h
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    state = _q1(qs, "state").upper()
    rows = _vertical_rows(vertical, state)
    if not rows:
        return (f'<p class="ck-section-body">No {vinfo["label"]} rows available '
                f'{("for " + state) if state else ""} from the loader right now. '
                f'Try another vertical or clear the state filter.</p>')
    has_size = any(r.get("size") is not None for r in rows)
    size_label = rows[0].get("size_label") or "Size"
    q_label = rows[0].get("q_label") or "Quality"
    head = (
        '<tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
        '<th style="padding:6px 8px;">Provider</th>'
        '<th style="padding:6px 8px;">Location</th>'
        '<th style="padding:6px 8px;">Ownership</th>'
        + (f'<th style="padding:6px 8px;text-align:right;">{size_label}</th>' if has_size else "")
        + f'<th style="padding:6px 8px;text-align:right;">{q_label}</th>'
        '<th style="padding:6px 8px;">Source</th>'
        '<th style="padding:6px 8px;">Open</th></tr>'
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
                   f'{int(r["size"]) if r.get("size") is not None else "—"}</td>') if has_size else ""
        trs.append(
            '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
            f'<td style="padding:5px 8px;font-weight:600;">{_h.escape(r["name"])}'
            f'<span style="font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-faint,#8b94a0);"> · {ccn}</span></td>'
            f'<td style="padding:5px 8px;">{loc}</td>'
            f'<td style="padding:5px 8px;">{_h.escape(str(r["ownership"]))}</td>'
            f'{size_td}'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">{_fmt_q(r)}</td>'
            f'<td style="padding:5px 8px;font-family:var(--sc-mono);font-size:9px;color:var(--sc-text-dim,#6a7480);">{_h.escape(r["source"])}</td>'
            f'<td style="padding:5px 8px;white-space:nowrap;">'
            f'<a class="ck-link" href="{xray}">X-Ray</a> · '
            f'<a class="ck-link" href="{insp}">Inspect</a> · '
            f'<a class="ck-link" href="{cmp_href}">+Cmp</a></td>'
            '</tr>'
        )
    scope = f" · {state}" if state else ""
    return (
        f'<p class="ck-section-body" style="margin:0 0 8px;">Showing {len(rows)} '
        f'{vinfo["label"]} providers{scope} (ranked by {q_label.lower()}; real '
        f'{vinfo["universe"]} data, "—" = not reported). Capped at {_TABLE_LIMIT}.</p>'
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;'
        'font-size:12.5px;font-family:var(--sc-sans,Inter Tight,sans-serif);">'
        f'<thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></div>'
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


def _screen_main(vertical: str, qs: Dict[str, List[str]], ck) -> str:
    active_mode = _q1(qs, "mode").lower()
    cards = "".join(
        f'<a class="ts-mode{" is-active" if m["key"] == active_mode else ""}" '
        f'href="{m["href"]}">'
        f'<span class="ts-mode-label">{m["label"]}</span>'
        f'<span class="ts-mode-how">{m["how"]}</span>'
        f'<span class="ts-mode-go">Open {m["label"]} &rarr;</span></a>'
        for m in _MODES
    )
    vinfo = next((v for v in _VERTICALS if v["key"] == vertical), _VERTICALS[0])
    return (
        _vertical_bar(vertical, qs)
        + ck["panel"](
            f'<p class="ck-section-body" style="margin:0;">Screening '
            f'<strong>{vinfo["label"]}</strong> &middot; <span style="font-family:var(--sc-mono);'
            f'font-size:11px;">{vinfo["universe"]}</span>. {vinfo["note"]} '
            f'This is market data, not your deals.</p>',
            title="Active universe")
        + ck["panel"](_render_map(vertical, qs),
                      title="Provider density · click a state to filter")
        + ck["panel"](_render_table(vertical, qs),
                      title="Ranked providers · real loader · X-Ray / Inspect")
        + ck["panel"](
            '<p class="ck-section-body">Three established ways into the SAME '
            'public universe — preserved and unchanged:</p>'
            f'<div class="ts-modes">{cards}</div>',
            title="Same universe, three ways in")
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
        f'<div style="font-family:var(--sc-serif);font-size:20px;color:var(--sc-navy,#15202b);">'
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
        + f'<a class="ck-link" href="/geo-intel?state={state}">{state} market context →</a><br>'
        f'<a class="ck-link" href="/target-screener?view=compare&compare={_h.escape(ccn)}">Add to Compare →</a><br>'
        f'<a class="ck-link" href="/pipeline">Promote to Pipeline →</a>',
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

    def _avail(field) -> str:
        c = sum(1 for r in rows if r.get(field) not in (None, "", "—"))
        pct = 100.0 * c / n
        return f'{c:,}/{len(rows):,} ({pct:.0f}%)'

    size_label = (rows[0].get("size_label") if rows and rows[0].get("size_label") else None)
    q_label = (rows[0]["q_label"] if rows else "Quality")
    # The columns the Main table currently surfaces, grouped by category, each
    # with its real source + a live availability count over the full universe.
    cols = [
        ("Provider name", "Identity", "name", src),
        ("CCN", "Identity", "ccn", src),
        ("City", "Geography", "city", src),
        ("State", "Geography", "state", src),
        ("Ownership", "Ownership / consolidation", "ownership", src),
    ]
    if size_label:
        cols.append((size_label, "Size / operational", "size", src))
    cols.append((q_label, "Quality", "q", f"{src} quality"))
    cols.append(("Source", "Source / provenance", "source", "PEdesk provenance"))

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
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;">{_avail(field)}</td></tr>'
            for label, field, source in items
        )
        body.append(
            f'<h3 style="font-family:var(--sc-serif);font-size:15px;margin:14px 0 4px;color:var(--sc-navy,#15202b);">{_h.escape(cat)}</h3>'
            '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12.5px;">'
            '<thead><tr style="text-align:left;border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
            '<th style="padding:6px 8px;">Column</th><th style="padding:6px 8px;">Source</th>'
            '<th style="padding:6px 8px;text-align:right;">Availability</th></tr></thead>'
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

    return (
        f'<p class="ck-section-body" style="margin:0 0 8px;">Columns for the '
        f'<strong>{vinfo["label"]}</strong> universe ({src}), grouped by category '
        f'with real source + availability across {len(rows):,} providers. A column '
        f'with no source is never shown; "{q_label}" availability reflects how many '
        f'providers actually report it.</p>' + "".join(body) + extra
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


def _screen_saved(qs, ck) -> str:
    import html as _h
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

    caveat = ck["panel"](
        '<p class="ck-section-body" style="margin:0;"><strong>Named / starred '
        'saved-screen persistence is not wired yet.</strong> Screens today are '
        'shareable URLs (server-first state) — fully functional, just not stored '
        'under a title with a last-run timestamp or alerts. No fake saved '
        'screens or alerts are shown.</p>'
        '<p class="ck-section-body" style="margin:8px 0 0;font-family:var(--sc-mono);'
        'font-size:11px;color:var(--sc-text-dim,#6a7480);">Future storage schema '
        '(documented for wiring): saved_screens(id, owner, title, vertical, '
        'query_params TEXT, created_at, last_run_at, result_count, alert_enabled). '
        'Until then the URL is the source of truth.</p>',
        title="Persistence status — honest")

    return current + preset_panel + caveat


_SCREENS = {
    "inspector": _screen_inspector, "columns": _screen_columns,
    "compare": _screen_compare, "missed": _screen_missed, "saved": _screen_saved,
}


def render_target_screener(qs: Optional[Dict[str, List[str]]] = None) -> str:
    from ._chartis_kit import (chartis_shell, ck_data_universe, ck_page_title,
                               ck_panel, ck_source_purpose)
    qs = qs or {}
    view = _q1(qs, "view", "main")
    if view not in _VIEW_KEYS:
        view = "main"
    vertical = _q1(qs, "vertical", "hospitals")
    if vertical not in _VERTICAL_KEYS:
        vertical = "hospitals"
    ck = {"panel": ck_panel}

    title = ck_page_title(
        "Target Screener", eyebrow="SOURCE · /target-screener · WORKBENCH",
        meta="six screens · every public CMS/provider universe · same data, not your deals",
    ) + '<div style="margin:8px 0 0;">' + ck_data_universe("cms") + '</div>'

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
    else:
        screen = _SCREENS[view](qs, ck)

    note = (
        '<p class="ck-section-body" style="font-style:italic;max-width:80ch;">'
        'All screening runs over the same public CMS/provider universes — this '
        'is market data, not your deals. Promote a result into the Pipeline to '
        'start tracking it. (Six screens; press a tab to switch.)</p>'
    )

    body = (
        title + source_purpose + tab_bar + screen
        + ck_panel(note, title="One universe, one workbench")
    )
    return chartis_shell(body, "Target Screener", active_nav="/target-screener",
                         extra_css=_CSS)
