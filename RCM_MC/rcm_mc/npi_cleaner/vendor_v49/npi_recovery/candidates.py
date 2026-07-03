"""Step 3: build the candidate biller pool.

For each distinct drug code on the attributable blank rows, assemble the real
set of Medicare providers/suppliers who bill that code -- the plausible-biller
universe (including operators absent from the panel) and the denominator for
the empirical benefit check: a code with ~no Part-B presence anywhere is
effectively non-attributable and is routed to gross-up even if it was not on
the SAD seed.

Two strategies, chosen automatically by scale:
  - regional  : one CMS query per (code, state). Few API calls when the file
    covers a handful of states.
  - national  : one CMS query per code (all states at once), then sliced by
    state in memory. Far fewer calls when the file is national (the data team's
    larger extract), which is where per-(code, state) would explode.
"""

import pandas as pd

# Above this many distinct states on the blanks, the national strategy (one
# pull per code) is cheaper than per-(code, state).
NATIONAL_STATE_THRESHOLD = 12


def build_candidate_pools(std, router, route_map, cms, progress=None,
                          top_hcpcs=None, states_filter=None, national=None):
    """Returns (pools, pool_table, no_partb_codes, code_desc)."""
    blanks = std[std["is_blank_billing"]].copy()
    pool_cols = ["hcpcs", "drug_name", "benefit", "channel", "scope",
                 "candidates", "states_used"]
    if blanks.empty:
        return {}, pd.DataFrame(columns=pool_cols), [], {}
    benefit_of = dict(zip(route_map["hcpcs"].astype(str), route_map["benefit"]))
    channel_of = dict(zip(route_map["hcpcs"].astype(str), route_map["channel"]))

    attributable = blanks[blanks["hcpcs"].map(lambda h: benefit_of.get(str(h)) in ("part_b", "noc"))]
    attributable = attributable[attributable["hcpcs"].notna()]

    blank_states = sorted({s for s in attributable["state"].dropna().unique() if str(s).strip()})
    if states_filter:
        blank_states = [s for s in blank_states if s in set(states_filter)]

    code_dollars = (attributable.assign(_amt=attributable["allowed_amt"].fillna(0))
                    .groupby("hcpcs")["_amt"].sum().sort_values(ascending=False))
    codes = [str(c) for c in code_dollars.index]
    if top_hcpcs:
        codes = codes[:top_hcpcs]

    if national is None:
        national = len(blank_states) > NATIONAL_STATE_THRESHOLD or not blank_states

    pools, frames, code_presence, code_desc = {}, [], {}, {}
    state_set = set(blank_states)
    total = max(len(codes), 1)

    # Fetch each code's biller pool concurrently — these are independent network
    # calls, and on a real book there are dozens of codes across many states, so
    # this is the single biggest speedup on the statistical path. The CMS client
    # uses a shared session + pickle-per-key cache, both thread-safe.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(code):
        channel = channel_of.get(code, "physician")
        out = {"code": code, "pools": {}, "presence": 0, "desc": None, "frame": None}
        if national:
            if channel == "dme":
                full = cms.dme_billers_by_hcpcs(code)
            else:
                full, desc = cms.billers_by_hcpcs(code)
                if desc:
                    out["desc"] = desc
                if full.empty:
                    full = cms.dme_billers_by_hcpcs(code)
            out["presence"] = len(full)
            target_states = state_set or set(full["state"].dropna().unique())
            for st in target_states:
                sub = full[full["state"].astype(str) == str(st)]
                if not sub.empty:
                    out["pools"][(code, str(st))] = sub.reset_index(drop=True)
            if not full.empty:
                top = full.head(15).copy()
                top.insert(0, "hcpcs", code)
                out["frame"] = top
        else:
            sub_frames = []
            for st in blank_states:
                if channel == "dme":
                    pool = cms.billers_dme(code, st)
                else:
                    pool = cms.billers_physician(code, st)
                    if pool.empty:
                        pool = cms.billers_dme(code, st)
                out["pools"][(code, str(st))] = pool
                out["presence"] += len(pool)
                if not pool.empty:
                    top = pool.head(15).copy()
                    top.insert(0, "hcpcs", code)
                    sub_frames.append(top)
            if sub_frames:
                out["frame"] = pd.concat(sub_frames, ignore_index=True)
        return out

    workers = min(6, max(1, len(codes)))
    done = 0
    # Prime the shared CMS catalog + dataset URLs ONCE before going parallel, so
    # the workers don't all stampede /data.json (which triggers 429 rate-limits).
    try:
        from . import config as _cfg
        warm_titles = [t for t in (_cfg.DATASET_TITLES.get("physician_provider"),
                                   _cfg.DATASET_TITLES.get("dme_supplier")) if t]
        if hasattr(cms, "warm"):
            cms.warm(warm_titles)
    except Exception:
        pass
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_one, code) for code in codes]
        for fu in as_completed(futs):
            r = fu.result()
            code = r["code"]
            pools.update(r["pools"])
            code_presence[code] = code_presence.get(code, 0) + r["presence"]
            if r["desc"]:
                code_desc[code] = r["desc"]
            if r["frame"] is not None:
                frames.append(r["frame"])
            done += 1
            if progress:
                progress(f"CMS pools ({done}/{total})", done / total)

    pool_cols = ["hcpcs", "state", "npi", "name", "type", "zip5", "place", "srvcs", "allowed", "channel"]
    if frames:
        pool_table = pd.concat(frames, ignore_index=True)
        pool_table = pool_table[[c for c in pool_cols if c in pool_table.columns]]
    else:
        pool_table = pd.DataFrame(columns=pool_cols)

    no_partb_codes = {c for c, cnt in code_presence.items() if cnt == 0}
    return pools, pool_table, no_partb_codes, code_desc
