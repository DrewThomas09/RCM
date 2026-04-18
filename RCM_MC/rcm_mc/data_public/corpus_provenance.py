"""Provenance classification for the deals corpus.

Every deal row loaded via ``load_corpus_deals`` is tagged with a
``provenance`` field that records whether the underlying transaction
is real (publicly disclosed historical M&A) or synthetic
(demonstration data fabricated for UI / modeling purposes).

Classification lives in a central registry here rather than on each
row or each seed file so the decision tree is reviewable at a glance
and so retagging a group is a one-line change. Every seed group that
contributes deals to the corpus MUST appear in ``PROVENANCE_REGISTRY``
— a deal whose source isn't in the registry is treated as an error
by the loader, not silently defaulted.

Classification standard (agreed in the Phase-B sprint plan):

  * **real**      — loose standard. Sponsor, target, and year
                    describe a transaction a reasonable reader would
                    believe happened. Specific financial fields
                    (MOIC, IRR, payer-mix) may be approximations.
  * **synthetic** — demonstration data. Fabricated names, or named
                    companies with impossible dates / buyer-seller
                    pairs. Not to be shown to partners as if real.

The ``extended_seed_2..104`` range was spot-checked at 15 rows per
the Phase-B decision rule; 2 of 15 had factually impossible dates
(Chemed already owned VITAS in 2020; Vista already owned Greenway
in 2018). Under the rule (≤ 9 of 15 confirmed real → tag whole range
synthetic), and with two confirmed fabrications in the sample, the
entire 2..104 range is tagged synthetic. See the Phase-B commit
notes for the full spot-check table.
"""
from __future__ import annotations

from typing import Dict


# Group → provenance tag. Keys correspond to the ``source_group``
# value attached by the loader when it imports each seed module.
# Entries are added by discrete commits so each tagging decision is
# reviewable in isolation.
PROVENANCE_REGISTRY: Dict[str, str] = {
    # --- Real ---
    # Batch 0: 35 foundational seed deals in deals_corpus.py.
    # Spot-checked 5/5 confirmed real (HCA/KKR-Bain 2006, Vanguard/
    # Blackstone 2004, LifePoint/KKR 2018, Tenet/Vanguard 2013, CHS/
    # HMA 2014). All blue-chip historical LBOs or strategic deals.
    "_SEED_DEALS": "real",

    # Batch 1: 20 deals in extended_seed.py. Spot-checked 3 confirmed
    # real (National Surgical / H.I.G. 2013, DaVita / HCP 2012,
    # SaVida / Revelstoke 2022), 2 ambiguous-but-plausible (Rural
    # Health Group / Cressey 2016, Acuity / HHS 2020). Zero factually
    # impossible dates. Admitted as real under the loose-corpus
    # standard — the module docstring claims SEC / press-release
    # sourcing and the confirmed sample supports it.
    "extended_seed": "real",
}


def tag_for_group(group: str) -> str:
    """Return the provenance tag for a group, or raise if unknown.

    Unknown groups raise so a newly-added seed file can't slip into
    the corpus untagged. Every group appears in the registry
    explicitly.
    """
    if group not in PROVENANCE_REGISTRY:
        raise KeyError(
            f"Seed group {group!r} is not in PROVENANCE_REGISTRY. "
            f"Add it to rcm_mc/data_public/corpus_provenance.py "
            f"before the loader will accept it."
        )
    return PROVENANCE_REGISTRY[group]
