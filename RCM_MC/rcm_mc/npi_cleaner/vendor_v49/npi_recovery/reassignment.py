"""
reassignment.py  (v49)
======================

The PECOS reassignment graph: structural recovery of a blank billing NPI from the
actual mechanism of Medicare billing, rather than a statistical inference from
co-occurrence.

How billing actually works. An individual provider (a Type 1 NPI) reassigns the
right to bill Medicare to an organization (a Type 2 NPI): a group practice, an
infusion center, a hospital outpatient department. The claim goes out under the
organization's NPI as the billing provider, with the individual as the rendering
provider. CMS publishes this relationship in the Medicare Fee-For-Service Public
Provider Enrollment reassignment sub-file, which lists, for each individual, the
organizations they have reassigned to. It is public data.

Why this is the strongest recovery signal. Every other method in the toolkit infers
the billing NPI from patterns: who bills this drug for this referrer, in this
geography, at national scale. Reassignment does not infer it; it looks it up. If a
claim has a rendering NPI (RIF carrier data almost always does, as PRF_PHYSN_NPI)
and that individual reassigns to exactly one organization, the billing NPI is that
organization, at high confidence, from the enrollment structure itself. When the
individual reassigns to several organizations, the graph narrows recovery to that
structural candidate set, which the other methods then rank.

This module builds the graph, recovers billing NPIs from it, validates recovered
billers against it, and provides a third independent recovery method for the
two-method agreement machinery, making it three-method. It ships with a small
synthetic graph for out-of-box use and refits from the real PECOS file.

Deterministic, hand-rolled, offline.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


class ReassignmentGraph:
    """Bidirectional individual-to-organization reassignment relationships."""

    def __init__(self):
        self.ind_to_orgs = {}    # individual NPI -> {org NPI: reassignment count/weight}
        self.org_to_inds = {}    # org NPI -> set of individual NPIs
        self.org_names = {}      # org NPI -> legal business name
        self.fitted_from = "unfitted"

    def fit(self, df: pd.DataFrame, *, individual_col="individual_npi",
            org_col="org_npi", name_col=None, source="pecos") -> "ReassignmentGraph":
        """Build the graph from a PECOS reassignment table (one row per
        individual-to-organization reassignment)."""
        d = df[[individual_col, org_col]].copy()
        d.columns = ["ind", "org"]
        d["ind"] = d["ind"].astype("string").str.strip()
        d["org"] = d["org"].astype("string").str.strip()
        d = d[(d["ind"].notna()) & (d["org"].notna())
              & (d["ind"] != "") & (d["org"] != "")]
        names = None
        if name_col and name_col in df.columns:
            names = df[[org_col, name_col]].copy()
            names.columns = ["org", "name"]

        ind_to_orgs, org_to_inds = {}, {}
        for ind, org in zip(d["ind"], d["org"]):
            ind_to_orgs.setdefault(ind, {})
            ind_to_orgs[ind][org] = ind_to_orgs[ind].get(org, 0) + 1
            org_to_inds.setdefault(org, set()).add(ind)
        self.ind_to_orgs = ind_to_orgs
        self.org_to_inds = org_to_inds
        if names is not None:
            self.org_names = dict(zip(names["org"].astype(str), names["name"].astype(str)))
        self.fitted_from = source
        return self

    # ------------------------------------------------------------- lookups --
    def orgs_for_individual(self, npi) -> list:
        """Organizations an individual reassigns to, most frequent first."""
        d = self.ind_to_orgs.get(str(npi).strip(), {})
        return [o for o, _ in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))]

    def individuals_for_org(self, npi) -> set:
        return self.org_to_inds.get(str(npi).strip(), set())

    def reassigns_to(self, individual_npi, org_npi) -> bool:
        """Does this individual reassign to this organization? The structural
        validation of a recovered billing NPI."""
        return str(org_npi).strip() in self.ind_to_orgs.get(str(individual_npi).strip(), {})

    # ------------------------------------------------------------ recovery --
    def recover_billing_npi(self, rendering_npi) -> dict:
        """Structural recovery of the billing NPI for a rendering individual.

        Returns the recovered org, a confidence, and the candidate set. A single
        reassignment is high confidence; multiple reassignments narrow to a
        structural candidate set for the other methods to rank; no reassignment
        yields no recovery."""
        orgs = self.orgs_for_individual(rendering_npi)
        if not orgs:
            return {"recovered_npi": "", "confidence": 0.0, "basis": "no_reassignment",
                    "candidates": []}
        if len(orgs) == 1:
            return {"recovered_npi": orgs[0], "confidence": 0.95,
                    "basis": "single_reassignment", "candidates": orgs}
        # multiple orgs: pick the most frequent as the point estimate, but flag
        top = orgs[0]
        counts = self.ind_to_orgs.get(str(rendering_npi).strip(), {})
        share = counts[top] / sum(counts.values())
        return {"recovered_npi": top, "confidence": round(0.5 + 0.4 * share, 3),
                "basis": "multiple_reassignment", "candidates": orgs}


def recover_from_reassignment(std: pd.DataFrame, graph: ReassignmentGraph,
                              mapping=None) -> pd.DataFrame:
    """Recover blank billing NPIs from the reassignment graph using the rendering
    NPI. Operates on the rows where billing is blank and a rendering NPI exists.
    Returns one row per recovered blank with the structural recovery."""
    bcol = _resolve(std, mapping, "billing_npi", ("npi",))
    rcol = _resolve(std, mapping, "rendering_npi", ())
    if bcol is None or rcol is None:
        return pd.DataFrame({"note": [
            "reassignment recovery needs a billing NPI column and a rendering "
            "(performing) NPI column; RIF carrier data has both"]})
    blank = std[bcol].isna() | std[bcol].astype("string").str.strip().isin(["", "nan", "<NA>", "0"])
    has_rend = std[rcol].notna() & ~std[rcol].astype("string").str.strip().isin(["", "nan", "<NA>", "0"])
    sel = blank & has_rend
    rows = []
    for idx in std.index[sel]:
        rendering = std.at[idx, rcol]
        rec = graph.recover_billing_npi(rendering)
        if rec["recovered_npi"]:
            rows.append({"row": idx, "rendering_npi": rendering,
                         "recovered_billing_npi": rec["recovered_npi"],
                         "confidence": rec["confidence"], "basis": rec["basis"],
                         "n_candidates": len(rec["candidates"]),
                         "org_name": graph.org_names.get(rec["recovered_npi"], "")})
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(columns=["row", "rendering_npi", "recovered_billing_npi",
                                    "confidence", "basis", "n_candidates", "org_name"])
    n_single = int((out["basis"] == "single_reassignment").sum()) if not out.empty else 0
    out.attrs["note"] = (
        f"{len(out)} blank billing NPIs recovered from the PECOS reassignment graph "
        f"({graph.fitted_from}); {n_single} are single-reassignment, high-confidence "
        f"structural recoveries (the rendering physician bills through exactly one "
        f"organization). This is the actual billing structure, not a statistical guess.")
    return out


def validate_billers(pred: pd.DataFrame, std: pd.DataFrame, graph: ReassignmentGraph,
                     mapping=None) -> pd.DataFrame:
    """Structural validation of recovered billing NPIs: does the rendering
    physician on the claim actually reassign to the recovered organization? A
    recovered biller the rendering provider does not reassign to is a
    precision risk stronger than a taxonomy mismatch."""
    rcol = _resolve(std, mapping, "rendering_npi", ())
    if rcol is None or "recovered_npi" not in pred.columns:
        return pd.DataFrame({"note": [
            "reassignment validation needs a rendering NPI and recovered billers"]})
    rows = []
    for i in pred.index:
        rec_npi = str(pred.at[i, "recovered_npi"]) if pd.notna(pred.at[i, "recovered_npi"]) else ""
        orig = pred.at[i, "orig_row"] if "orig_row" in pred.columns else i
        rendering = std.at[orig, rcol] if orig in std.index else None
        if not rec_npi or rendering is None or pd.isna(rendering):
            continue
        # only judge when the graph knows the rendering individual
        known = str(rendering).strip() in graph.ind_to_orgs
        if not known:
            continue
        ok_link = graph.reassigns_to(rendering, rec_npi)
        rows.append({"row": orig, "rendering_npi": rendering,
                     "recovered_npi": rec_npi,
                     "reassignment_consistent": ok_link,
                     "verdict": "consistent" if ok_link else "inconsistent"})
    out = pd.DataFrame(rows)
    flagged = out[~out["reassignment_consistent"]].copy() if not out.empty else out
    out.attrs["note"] = (
        f"{len(flagged)} of {len(out)} recovered billers are structurally "
        f"inconsistent: the rendering physician does not reassign to the recovered "
        f"organization in the enrollment data. These are high-priority precision "
        f"risks." if not out.empty else "No recovered billers could be validated "
        f"against the reassignment graph (rendering NPIs not in the graph).")
    return flagged.reset_index(drop=True) if not out.empty else out


def add_to_agreement(agreement_tbl: pd.DataFrame, std: pd.DataFrame,
                     graph: ReassignmentGraph, mapping=None) -> pd.DataFrame:
    """Layer the structural reassignment method onto the v44 two-method agreement
    table, making it three-method. For each blank row already scored by the in-panel
    and CMS-pool methods, add the reassignment method's recovered org and a combined
    verdict. Reassignment is the tie-breaker and the authority: when it agrees with a
    statistical method, confidence is highest; when it contradicts both, the
    statistical guess is suspect.

    Returns the agreement table with method_c (reassignment) columns and an updated
    boost that rewards structural corroboration.
    """
    if agreement_tbl is None or agreement_tbl.empty:
        return agreement_tbl
    rcol = _resolve(std, mapping, "rendering_npi", ())
    out = agreement_tbl.copy()
    method_c, c_basis, three_state, new_boost = [], [], [], []
    for _, r in out.iterrows():
        row = r["row"]
        rendering = std.at[row, rcol] if (rcol and row in std.index) else None
        rec = graph.recover_billing_npi(rendering) if rendering is not None and pd.notna(rendering) else \
            {"recovered_npi": "", "basis": "no_rendering"}
        cnpi = rec["recovered_npi"]
        method_c.append(cnpi)
        c_basis.append(rec.get("basis", ""))
        a, b = r.get("method_a_npi", ""), r.get("method_b_npi", "")
        base_boost = r.get("agreement_boost", 1.0)
        if not cnpi:
            three_state.append(r.get("agreement", "") + "+no_structural")
            new_boost.append(base_boost)
            continue
        # structural method present: does it corroborate a statistical method?
        agrees_a = bool(a) and a == cnpi
        agrees_b = bool(b) and b == cnpi
        if agrees_a and agrees_b:
            three_state.append("all_three_agree")
            new_boost.append(1.25)
        elif agrees_a or agrees_b:
            three_state.append("structural_confirms_one")
            new_boost.append(1.2)
        else:
            # reassignment contradicts both statistical guesses: trust structure
            three_state.append("structural_overrides")
            new_boost.append(0.9)
        method_c[-1] = cnpi
    out["method_c_npi"] = method_c
    out["method_c_basis"] = c_basis
    out["three_method_state"] = three_state
    out["agreement_boost"] = new_boost
    n_all3 = sum(1 for s in three_state if s == "all_three_agree")
    n_override = sum(1 for s in three_state if s == "structural_overrides")
    out.attrs["note"] = (
        f"Three-method agreement: {n_all3} blanks where the in-panel pattern, the CMS "
        f"pool, and the PECOS reassignment structure all name the same organization "
        f"(the strongest possible recovery), and {n_override} where reassignment "
        f"contradicts both statistical guesses and should override them.")
    return out


def _resolve(std, mapping, canonical, fallbacks):
    if mapping and mapping.get(canonical) and mapping[canonical] in std.columns:
        return mapping[canonical]
    if canonical in std.columns:
        return canonical
    for f in fallbacks:
        if f in std.columns:
            return f
    return None


# --------------------------------------------------------------------------- #
# synthetic graph for out-of-box use; refit from the real PECOS file
# --------------------------------------------------------------------------- #
def demo_graph() -> ReassignmentGraph:
    """A small synthetic reassignment graph, clearly synthetic, for out-of-box use
    and testing. Refit from the CMS Medicare FFS Public Provider Enrollment
    reassignment sub-file for real relationships."""
    df = pd.DataFrame({
        "individual_npi": ["1003914151", "1999999984", "1720082779", "1184649620",
                           "1184649620"],
        "org_npi":        ["1184649626", "1184649626", "1558887711", "1558887711",
                           "1770009988"],
        "org_name":       ["Houston Infusion Group", "Houston Infusion Group",
                           "Bayou Neurology PA", "Bayou Neurology PA",
                           "Gulf Coast Rheumatology"],
    })
    return ReassignmentGraph().fit(df, name_col="org_name", source="synthetic_demo")
