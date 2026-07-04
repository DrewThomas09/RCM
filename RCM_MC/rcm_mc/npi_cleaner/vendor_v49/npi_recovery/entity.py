"""Step 5: map recovered NPIs to names / taxonomy via NPPES, then roll sibling
NPIs up to a parent operator so platform roll-ups don't look artificially
fragmented.

v6 entity-continuity rewrite
============================
Churn in a claims panel rarely shows up as a *blank* biller — it shows up as a
*present-but-different* NPI after an acquisition or rebrand. The v5 rollup keyed
each NPI on a single best signal (authorized official, else mailing address,
else location). That misses the case the Vivo / CSI thesis turns on: an acquired
practice keeps billing under its own NPI and its own primary name, and the only
thread back to the parent is an NPPES *other / former / DBA name* (e.g. "CSI"
registered with the other-name "CLINICAL SPECIALTY INFUSIONS") or a shared HQ
mailing address.

So v6 clusters with union-find over *all* continuity signals at once:
  • shared authorized official,
  • shared mailing address, shared location address,
  • shared organization name OR other-org-name (the new signal) — i.e. one
    entity's primary name matching another entity's former / DBA name.

Two NPIs land in the same parent cluster if they share ANY of those. The rollup
records which signal(s) did the linking (`match_basis`) so the analyst can audit
a merge instead of trusting it blind. We also emit a legacy_NPI -> parent
crosswalk, and a confirm-or-deny HHI helper that recomputes within-cohort
concentration on entity-rolled vs raw NPIs — the test for "how much of the
1,084 -> 718 defragmentation is real vs an artifact of sibling NPIs."
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

# Legal-form suffixes only. We deliberately do NOT strip industry words
# ("PHARMACY", "INFUSION") — those carry the discriminating signal and stripping
# them would over-merge unrelated shops.
_LEGAL = re.compile(
    r"\b(L\.?L\.?C\.?|INC\.?|INCORPORATED|L\.?L\.?P\.?|L\.?P\.?|P\.?L\.?L\.?C\.?"
    r"|P\.?A\.?|P\.?C\.?|CORP\.?|CORPORATION|CO\.?|COMPANY|LTD\.?)\b"
)
_NAME_MIN = 6  # a normalized name shorter than this is too generic to link on


def _norm_name(s):
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _LEGAL.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:        # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _empty_outputs():
    ent = pd.DataFrame(columns=["npi", "name", "type", "taxonomy", "state",
                                "other_org_names", "parent_key",
                                "parent_operator", "match_basis"])
    rollup = pd.DataFrame(columns=["parent_operator", "npi_count", "example_npis",
                                   "match_basis", "dba_names", "taxonomy", "state"])
    return ent, rollup


def resolve_entities(recovered_npis, nppes, progress=None, max_workers=16,
                     enroll=None, do_pac=False):
    npis = sorted({str(n) for n in recovered_npis if n and str(n).strip()})
    total = max(len(npis), 1)

    def worker(npi):
        rec = nppes.lookup(npi)
        if not rec:
            rec = {"npi": npi, "name": "", "type": "", "taxonomy": "",
                   "loc_addr": "", "mail_addr": "", "official": "",
                   "city": "", "state": "", "other_org_names": ""}
        # Optional PECOS enrollment pull: PAC ID (PECOS_ASCT_CNTL_ID) is the
        # churn-proof entity key — it survives address changes, rebrands, and
        # DBA churn that defeat name/address matching. The enrollment org_name
        # is also folded in as another name alias. Cached, so the later
        # enrichment step reuses these lookups.
        rec.setdefault("pac_id", "")
        rec.setdefault("enroll_org", "")
        if do_pac and enroll is not None:
            try:
                en = enroll.enrollment_lookup(npi) or {}
                rec["pac_id"] = (en.get("pecos_id") or "").strip()
                rec["enroll_org"] = (en.get("org_name") or "").strip().upper()
            except Exception:
                pass
        return rec

    rows, done = [], 0
    if npis:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(worker, n) for n in npis]
            for fut in as_completed(futures):
                rows.append(fut.result())
                done += 1
                if progress and (done % 25 == 0 or done == total):
                    progress("Resolving entities", done / total)

    ent = pd.DataFrame(rows)
    if ent.empty:
        return _empty_outputs()
    for _col in ("other_org_names", "pac_id", "enroll_org"):
        if _col not in ent.columns:
            ent[_col] = ""
    ent = ent.sort_values("npi").reset_index(drop=True)

    # ---- build continuity signals -> union-find ----------------------------
    # key_to_npis maps a namespaced signal value to the NPIs that carry it.
    # A signal shared by >=2 NPIs links them; the namespace prefix records what
    # kind of link it was so we can report match_basis per cluster.
    key_to_npis = {}

    def _add(key, npi):
        key_to_npis.setdefault(key, set()).add(npi)

    for r in ent.itertuples(index=False):
        npi = str(r.npi)
        pac = (getattr(r, "pac_id", "") or "").strip()
        if pac:
            _add(("pac_id", pac), npi)        # churn-proof key
        off = (getattr(r, "official", "") or "").strip().upper()
        if off:
            _add(("official", off), npi)
        for addr_attr in ("mail_addr", "loc_addr"):
            val = (getattr(r, addr_attr, "") or "").strip()
            if val:
                _add(("address", val), npi)
        names = [getattr(r, "name", "") or "", getattr(r, "enroll_org", "") or ""]
        oon = getattr(r, "other_org_names", "") or ""
        names += [p for p in oon.split(";")]
        for nm in names:
            n = _norm_name(nm)
            if len(n) >= _NAME_MIN:
                _add(("name", n), npi)

    uf = _UnionFind()
    for npi in ent["npi"].astype(str):
        uf.find(npi)                      # ensure every NPI is a node
    basis_for_key = {}
    for (kind, _val), members in key_to_npis.items():
        if len(members) >= 2:
            members = list(members)
            for m in members[1:]:
                uf.union(members[0], m)
            basis_for_key[(kind, _val)] = members

    ent["parent_key"] = ent["npi"].astype(str).map(uf.find)

    # cluster-level match_basis: which signal kinds actually merged this cluster
    root_basis = {}
    for (kind, _val), members in basis_for_key.items():
        root = uf.find(members[0])
        root_basis.setdefault(root, set()).add(kind)
    ent["match_basis"] = ent["parent_key"].map(
        lambda rk: ", ".join(sorted(root_basis.get(rk, set()))) or "singleton")

    # parent label = most common non-empty primary name in the cluster,
    # tie-broken by longest; fall back to the lowest NPI.
    label_map = {}
    for rk, g in ent.groupby("parent_key"):
        names = [n for n in g["name"].tolist() if n]
        if names:
            best = max(set(names), key=lambda n: (names.count(n), len(n)))
        else:
            best = g["npi"].iloc[0]
        label_map[rk] = best
    ent["parent_operator"] = ent["parent_key"].map(label_map)

    def _dba(series):
        seen = []
        for cell in series:
            for part in str(cell or "").split(";"):
                p = part.strip()
                if p and p not in seen:
                    seen.append(p)
        return "; ".join(seen[:12])

    rollup = (ent.groupby("parent_operator")
              .agg(npi_count=("npi", "nunique"),
                   example_npis=("npi", lambda s: ";".join(sorted(set(s.astype(str)))[:8])),
                   match_basis=("match_basis", lambda s: ", ".join(
                       sorted({b for cell in s for b in str(cell).split(", ") if b and b != "singleton"})) or "singleton"),
                   dba_names=("other_org_names", _dba),
                   taxonomy=("taxonomy", lambda s: next((x for x in s if x), "")),
                   state=("state", lambda s: next((x for x in s if x), "")))
              .reset_index()
              .sort_values("npi_count", ascending=False)
              .reset_index(drop=True))

    keep = ["npi", "name", "type", "taxonomy", "state", "other_org_names",
            "pac_id", "parent_key", "parent_operator", "match_basis"]
    keep = [c for c in keep if c in ent.columns]
    return ent[keep], rollup


def make_crosswalk(ent_table):
    """legacy_NPI -> parent operator crosswalk. One row per NPI; the rows where
    parent_operator covers >1 NPI are the genuine roll-ups (multi_npi_parent =
    True). This is the artifact you join onto a claims panel before measuring
    share, so acquired/rebranded siblings collapse onto their parent."""
    if ent_table is None or ent_table.empty:
        return pd.DataFrame(columns=["legacy_npi", "name", "parent_operator",
                                     "parent_key", "match_basis",
                                     "parent_npi_count", "multi_npi_parent"])
    cw = ent_table.rename(columns={"npi": "legacy_npi"}).copy()
    counts = cw.groupby("parent_operator")["legacy_npi"].transform("nunique")
    cw["parent_npi_count"] = counts
    cw["multi_npi_parent"] = counts > 1
    cols = ["legacy_npi", "name", "parent_operator", "parent_key",
            "match_basis", "parent_npi_count", "multi_npi_parent"]
    cols = [c for c in cols if c in cw.columns]
    return (cw[cols]
            .sort_values(["parent_npi_count", "parent_operator", "legacy_npi"],
                         ascending=[False, True, True])
            .reset_index(drop=True))


def _label_and_rollup(ent):
    """Recompute parent_operator label + the rollup table from current
    parent_key assignments. Same logic resolve_entities uses inline; factored so
    merge_fuzzy_links can reuse it."""
    label_map = {}
    for rk, g in ent.groupby("parent_key"):
        names = [n for n in g["name"].tolist() if n]
        if names:
            best = max(set(names), key=lambda n: (names.count(n), len(n)))
        else:
            best = g["npi"].iloc[0]
        label_map[rk] = best
    ent["parent_operator"] = ent["parent_key"].map(label_map)

    def _dba(series):
        seen = []
        for cell in series:
            for part in str(cell or "").split(";"):
                p = part.strip()
                if p and p not in seen:
                    seen.append(p)
        return "; ".join(seen[:12])

    oon_col = "other_org_names" if "other_org_names" in ent.columns else None
    agg = dict(npi_count=("npi", "nunique"),
               example_npis=("npi", lambda s: ";".join(sorted(set(s.astype(str)))[:8])),
               match_basis=("match_basis", lambda s: ", ".join(
                   sorted({b for cell in s for b in str(cell).split(", ")
                           if b and b != "singleton"})) or "singleton"),
               taxonomy=("taxonomy", lambda s: next((x for x in s if x), "")),
               state=("state", lambda s: next((x for x in s if x), "")))
    if oon_col:
        agg["dba_names"] = (oon_col, _dba)
    rollup = (ent.groupby("parent_operator").agg(**agg)
              .reset_index().sort_values("npi_count", ascending=False)
              .reset_index(drop=True))
    return ent, rollup


def merge_fuzzy_links(ent_table, extra_edges):
    """Layer probabilistic (Splink) fuzzy edges ON TOP OF the deterministic
    clusters. Seeds union-find with the existing parent_key groups, then unions
    the fuzzy edges, then recomputes parent_operator / match_basis / rollup.

    Can only MERGE clusters, never split one — so the deterministic result is a
    floor and Splink only adds the near-miss links exact matching missed. Rows
    whose cluster grew via a fuzzy edge get "fuzzy" appended to match_basis so a
    reviewer can see (and audit) which merges were probabilistic.

    `extra_edges` — iterable of (npi_a, npi_b) from splink_entity.build_fuzzy_links.
    Returns (ent_table, rollup). No-op (returns inputs re-rolled) if no edges.
    """
    if ent_table is None or ent_table.empty:
        return ent_table, _empty_outputs()[1]
    ent = ent_table.copy()
    ent["npi"] = ent["npi"].astype(str)
    if "match_basis" not in ent.columns:
        ent["match_basis"] = "singleton"
    if not extra_edges:
        return _label_and_rollup(ent)

    valid = set(ent["npi"])
    uf = _UnionFind()
    for npi in ent["npi"]:
        uf.find(npi)
    # seed with the existing deterministic clusters
    for _rk, g in ent.groupby("parent_key"):
        npis = g["npi"].tolist()
        for m in npis[1:]:
            uf.union(npis[0], m)

    old_root = {n: uf.find(n) for n in ent["npi"]}
    touched_roots = set()
    for a, b in extra_edges:
        a, b = str(a), str(b)
        if a in valid and b in valid and uf.find(a) != uf.find(b):
            uf.union(a, b)
            touched_roots.add(uf.find(a))

    ent["parent_key"] = ent["npi"].map(uf.find)
    # mark clusters that actually grew via a fuzzy edge
    grew = {uf.find(n) for n in ent["npi"] if old_root[n] != uf.find(n)}
    grew |= touched_roots

    def _basis(row):
        base = str(row["match_basis"]) if row["match_basis"] else "singleton"
        if row["parent_key"] in grew:
            parts = [p for p in base.split(", ") if p and p != "singleton"]
            parts.append("fuzzy")
            return ", ".join(sorted(set(parts)))
        return base
    ent["match_basis"] = ent.apply(_basis, axis=1)
    return _label_and_rollup(ent)


def _hhi(shares_pct):
    """HHI from a series of percentage shares (0-100). Sum of squared shares."""
    return float((shares_pct.astype(float) ** 2).sum())


def hhi_entity_vs_raw(claims, npi_col, value_col, crosswalk, within=None):
    """Confirm-or-deny test for the defragmentation claim.

    Recomputes within-cohort concentration two ways on the SAME dollars:
      raw      — share by the billing NPI as it appears in the panel
      rolled   — share by parent operator (siblings collapsed via `crosswalk`)

    If a cohort is genuinely defragmenting, raw HHI < rolled HHI: rolling
    acquired siblings back onto their parents *recovers* concentration that the
    raw NPI view scattered. Returns a one-row-per-cohort frame with both HHIs,
    the delta, and operator counts.

    `claims`     — DataFrame of the cohort(s) you're measuring.
    `npi_col`    — billing-NPI column in `claims`.
    `value_col`  — dollars (or claim count) to weight share by.
    `crosswalk`  — output of make_crosswalk(); legacy_npi -> parent_operator.
    `within`     — optional grouping column (e.g. state / drug / year) to run the
                   test per cohort. None = one pooled cohort.

    Run this on the REAL claims file — it needs the actual within-cohort dollars,
    not the synthetic sample.
    """
    df = claims[[c for c in {npi_col, value_col, within} if c]].copy()
    cw = crosswalk.set_index("legacy_npi")["parent_operator"] if (
        crosswalk is not None and not crosswalk.empty) else pd.Series(dtype=object)
    df["_npi"] = df[npi_col].astype(str)
    df["_parent"] = df["_npi"].map(cw).fillna(df["_npi"])
    df["_val"] = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)

    def _one(sub, label):
        tot = sub["_val"].sum()
        if tot <= 0:
            return None
        raw = sub.groupby("_npi")["_val"].sum() / tot * 100.0
        rolled = sub.groupby("_parent")["_val"].sum() / tot * 100.0
        return {
            "cohort": label,
            "raw_operators": int(raw.shape[0]),
            "rolled_operators": int(rolled.shape[0]),
            "hhi_raw": round(_hhi(raw), 1),
            "hhi_rolled": round(_hhi(rolled), 1),
            "hhi_delta": round(_hhi(rolled) - _hhi(raw), 1),
        }

    out = []
    if within:
        for label, sub in df.groupby(within):
            row = _one(sub, str(label))
            if row:
                out.append(row)
    else:
        row = _one(df, "ALL")
        if row:
            out.append(row)
    return pd.DataFrame(out)
