"""Health-system master mapping — which system each hospital belongs to.

Why this module exists
----------------------
HCRIS gives us 6,123 facilities keyed by CCN (``data/hcris.py``) with
beds, payer mix and financials — and **no parent-system column**. CMS
does not publish one. Every hospital surface in the app therefore reads
the universe as 6,123 unrelated rows, which is not how a partner thinks
about it: they think "how many hospitals does Ascension run, how many of
them are behavioral, and which states". Answering that question meant
hand-counting off a screener export every time.

This module is the single place that answers it. It carries a curated
registry of US health systems, matches HCRIS facility names to that
registry, and rolls the result up to one row per system with hospital
counts, bed counts, state footprint and a facility-type mix (acute /
critical access / **behavioral** / rehab / LTACH / children's).

How the match works — and what it is not
----------------------------------------
Assignment is **name-based**, because the name is the only ownership
signal HCRIS carries. Each :class:`SystemDef` lists the brand strings
that appear in HCRIS names (including the abbreviations HCRIS itself
uses — ``SSH -`` for Select Specialty, ``KFH -`` for Kaiser Foundation
Hospitals, ``UH `` for University Hospitals). Where a brand is ambiguous
across unrelated systems — MERCY, BAPTIST, METHODIST, SAINT LUKE'S,
AURORA all name two or more unrelated organizations — the entry is
scoped with ``states`` so the match cannot leak across the country.

Consequences a reader must hold onto:

  - A hospital owned by a system but carrying a purely local name (much
    of Community Health Systems, Tenet and Steward) lands in
    **Independent / Unmapped**. Unmapped is "the name doesn't say", not
    "independent" — the page labels it that way.
  - Match precision is protected by ``states`` scoping and the
    longest-pattern-wins rule, so a wrong system is much less likely
    than a missing one. The mapping under-claims by design.
  - Every assigned row carries ``system_match`` (the pattern that fired)
    so any count on the page can be traced back to why a facility was
    pulled into a system.

Facility type comes from ``hcris._classify_series`` (CCN range first,
name keywords as fallback) — the same classifier the screeners use, so
"behavioral" means the same thing here as everywhere else. Behavioral
additionally catches name signals (BEHAVIORAL / PSYCH / BH / MENTAL
HEALTH) on facilities whose CCN range says otherwise, because a
psychiatric unit filed under a general CCN still reads as behavioral to
a partner screening the space.

Public API::

    assign_systems(df=None)   -> DataFrame (universe + system columns)
    build_system_map(df=None) -> HealthSystemMap (rollup, cached)
    system_hospitals(system_id, df=None) -> DataFrame
    candidate_clusters(df=None) -> list[CandidateCluster]
    registry_size() -> int
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .hcris import _classify_series, _get_latest_per_ccn

# ── Vocabulary ─────────────────────────────────────────────────────
#
# ``kind`` is the ownership model a partner underwrites against (a
# for-profit chain and a Catholic non-profit price and behave
# differently). ``focus`` is what the system actually operates — the
# facet that answers "show me the behavioral platforms".

KIND_FOR_PROFIT = "For-Profit"
KIND_NONPROFIT = "Non-Profit"
KIND_CATHOLIC = "Catholic Non-Profit"
KIND_ACADEMIC = "Academic"
KIND_GOVERNMENT = "Government"

FOCUS_ACUTE = "Acute"
FOCUS_BEHAVIORAL = "Behavioral"
FOCUS_REHAB = "Rehab"
FOCUS_LTACH = "LTACH"
FOCUS_CHILDRENS = "Children's"
FOCUS_MIXED = "Mixed"

# Facility-type labels as emitted by ``hcris._classify_series``.
TYPE_LABELS: Tuple[str, ...] = (
    "general", "critical_access", "psychiatric", "rehab",
    "ltach", "children", "other",
)

# Partner-facing names for those labels — the table headers.
TYPE_DISPLAY: Dict[str, str] = {
    "general": "Acute",
    "critical_access": "Critical Access",
    "psychiatric": "Behavioral",
    "rehab": "Rehab",
    "ltach": "LTACH",
    "children": "Children's",
    "other": "Other",
}


@dataclass(frozen=True)
class SystemDef:
    """One health system in the registry.

    ``patterns`` are normalized name fragments (see :func:`normalize_name`
    — upper-cased, punctuation stripped, ``ST``/``ST.`` expanded to
    ``SAINT``, ``&`` to ``AND``). A leading ``^`` anchors the pattern to
    the start of the facility name, which is how brands that are common
    words elsewhere (MERCY, TRINITY, MEMORIAL) stay precise.

    ``states`` restricts a pattern to a footprint. Required for every
    brand that names more than one unrelated organization; without it a
    Kentucky Baptist hospital gets counted into Baptist Health South
    Florida and the hospital count silently lies.
    """

    system_id: str
    name: str
    kind: str
    focus: str
    hq_state: str
    patterns: Tuple[str, ...]
    states: Tuple[str, ...] = ()
    exclude: Tuple[str, ...] = ()
    note: str = ""


# ── The registry ───────────────────────────────────────────────────
#
# Ordered roughly by hospital count. Entries earn their place by having
# a brand that actually appears in HCRIS facility names; a system whose
# hospitals all carry local names (much of CHS / Tenet / Steward) cannot
# be mapped from this data source and is deliberately absent rather than
# guessed at. Adding one is a one-line append — the rollup, the page and
# the coverage numbers all derive from this tuple.

SYSTEM_REGISTRY: Tuple[SystemDef, ...] = (
    # ── National for-profit acute chains ───────────────────────────
    SystemDef(
        "hca", "HCA Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "TN",
        patterns=(
            "^HCA", "^TRISTAR", "^MEDICAL CITY", "^SAINT DAVIDS",
            "^PARKRIDGE", "^RESEARCH MEDICAL CENTER", "^MENORAH MEDICAL",
            "^OVERLAND PARK REGIONAL", "^WESLEY MEDICAL CENTER",
            "^SUNRISE HOSPITAL", "^MOUNTAINVIEW HOSPITAL",
            "^SOUTHERN HILLS HOSPITAL",
            # MountainStar (Utah division) — local brands, state-scoped.
            "UT:^OGDEN REGIONAL", "UT:^SAINT MARKS HOSPITAL",
            "UT:^LONE PEAK HOSPITAL", "UT:^TIMPANOGOS REGIONAL",
            "UT:^BRIGHAM CITY COMMUNITY", "UT:^MOUNTAIN VIEW HOSPITAL",
            "UT:^CACHE VALLEY", "UT:^LAKEVIEW HOSPITAL",
        ),
        note="Largest US for-profit operator; many facilities rebranded "
             "to the HCA / Medical City / TriStar house brands.",
    ),
    SystemDef(
        "tenet", "Tenet Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "TX",
        patterns=("^THE HOSPITALS OF PROVIDENCE", "^HOSPITALS OF PROVIDENCE",
                  "MI:^DETROIT RECEIVING", "MI:^HARPER UNIVERSITY",
                  "MI:^SINAI GRACE", "MI:^DETROIT MEDICAL CENTER"),
        note="Tenet keeps acquired local names almost everywhere; only the "
             "explicitly branded facilities are reachable from HCRIS names.",
    ),
    SystemDef(
        "ardent", "Ardent Health Services", KIND_FOR_PROFIT, FOCUS_ACUTE, "TN",
        patterns=("OK:^HILLCREST HOSPITAL", "OK:^HILLCREST MEDICAL",
                  "NM:^LOVELACE", "^BSA HOSPITAL"),
    ),
    SystemDef(
        "prime", "Prime Healthcare", KIND_FOR_PROFIT, FOCUS_ACUTE, "CA",
        patterns=("^PRIME HEALTHCARE", "CA:^GARDEN GROVE HOSPITAL",
                  "CA:^SHASTA REGIONAL", "CA:^WEST ANAHEIM", "CA:^LA PALMA",
                  "CA:^HUNTINGTON BEACH HOSPITAL", "CA:^CENTINELA",
                  "CA:^CHINO VALLEY MEDICAL", "CA:^MONTCLAIR HOSPITAL",
                  "CA:^SHERMAN OAKS HOSPITAL", "CA:^SAN DIMAS COMMUNITY"),
    ),
    SystemDef(
        "uhs", "Universal Health Services", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "PA",
        patterns=("^UHS ", "^UBH ", "UNIVERSAL HEALTH SERVICES",
                  "TX:^SOUTH TEXAS HEALTH", "TX:^DOCTORS HOSPITAL OF LAREDO"),
        note="UHS runs the largest US behavioral estate; HCRIS carries "
             "several of them under the UHS / UBH abbreviations.",
    ),

    # ── Post-acute / specialty platforms ───────────────────────────
    SystemDef(
        "encompass", "Encompass Health", KIND_FOR_PROFIT, FOCUS_REHAB, "AL",
        patterns=("^ENCOMPASS",),
        note="Largest US inpatient-rehab operator — the single biggest "
             "name-matched system in the HCRIS universe.",
    ),
    SystemDef(
        "select_medical", "Select Medical", KIND_FOR_PROFIT, FOCUS_LTACH, "PA",
        patterns=("^SSH ", "^SELECT SPECIALTY", "^SELECT REHAB"),
        note="HCRIS abbreviates Select Specialty Hospital to 'SSH - <city>'.",
    ),
    SystemDef(
        "kindred", "ScionHealth / Kindred", KIND_FOR_PROFIT, FOCUS_LTACH, "KY",
        patterns=("^KINDRED", "^SCIONHEALTH"),
    ),
    SystemDef(
        "pam", "PAM Health", KIND_FOR_PROFIT, FOCUS_LTACH, "TX",
        patterns=("^PAM ",),
    ),
    SystemDef(
        "vibra", "Vibra Healthcare", KIND_FOR_PROFIT, FOCUS_LTACH, "PA",
        patterns=("^VIBRA",),
    ),
    SystemDef(
        "cornerstone", "Cornerstone Healthcare Group", KIND_FOR_PROFIT, FOCUS_LTACH, "TX",
        patterns=("^CORNERSTONE SPECIALTY", "^CORNERSTONE BH", "^CORNERSTONE HOSPITAL"),
    ),
    SystemDef(
        "ernest", "Ernest Health", KIND_FOR_PROFIT, FOCUS_REHAB, "NM",
        patterns=("^REHABILITATION HOSPITAL OF",),
        note="Ernest operates under 'Rehabilitation Hospital of <place>' "
             "naming; the pattern is anchored so it cannot swallow the "
             "generic rehab long tail.",
    ),
    SystemDef(
        "shriners", "Shriners Children's", KIND_NONPROFIT, FOCUS_CHILDRENS, "FL",
        patterns=("^SHRINERS",),
    ),

    # ── Behavioral platforms ───────────────────────────────────────
    SystemDef(
        "acadia", "Acadia Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "TN",
        patterns=("^ACADIA",),
    ),
    SystemDef(
        "oceans", "Oceans Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "LA",
        patterns=("^OCEANS",),
    ),
    SystemDef(
        "haven_bh", "Haven Behavioral Healthcare", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "TN",
        patterns=("^HAVEN BEHAVIORAL",),
    ),
    SystemDef(
        "signature_bh", "Signature Healthcare Services", KIND_FOR_PROFIT, FOCUS_BEHAVIORAL, "CA",
        patterns=("^AURORA BEHAVIORAL", "^AURORA SAN DIEGO", "^AURORA CHARTER OAK"),
        note="Trades as Aurora Behavioral Health — state-scoped away "
             "from Advocate Aurora in Wisconsin by the pattern itself.",
    ),
    SystemDef(
        "rogers_bh", "Rogers Behavioral Health", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "WI",
        patterns=("^ROGERS MEMORIAL", "^ROGERS BEHAVIORAL"),
    ),
    SystemDef(
        "sheppard_pratt", "Sheppard Pratt", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "MD",
        patterns=("^SHEPPARD PRATT", "^SHEPPARD AND ENOCH"),
    ),
    SystemDef(
        "brattleboro", "Brattleboro Retreat", KIND_NONPROFIT, FOCUS_BEHAVIORAL, "VT",
        patterns=("^BRATTLEBORO RETREAT",),
    ),

    # ── National Catholic / faith-based systems ────────────────────
    SystemDef(
        "ascension", "Ascension", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^ASCENSION", "TN:^SAINT THOMAS", "IL:^PRESENCE",
                  "AL:^SAINT VINCENTS", "KS:^VIA CHRISTI", "OK:^SAINT JOHN",
                  "MI:^SAINT JOHN HOSPITAL"),
        note="Many Ascension facilities still file under the legacy "
             "Saint Thomas / Presence / Via Christi brands.",
    ),
    SystemDef(
        "commonspirit", "CommonSpirit Health", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=(
            "^CHI ", "^CHI-", "^CATHOLIC HEALTH INITIATIVES", "^COMMONSPIRIT",
            "^CENTURA", "^DIGNITY HEALTH", "^MERCY HOSPITAL AND MEDICAL CENTER",
            "KY:^SAINT JOSEPH", "KY:^FLAGET MEMORIAL", "AR:^SAINT VINCENT",
            "TX:^SAINT LUKES",
        ),
        note="CHI + Dignity + Centura merged into CommonSpirit; HCRIS "
             "names still carry all three legacy brands.",
    ),
    SystemDef(
        "trinity", "Trinity Health", KIND_CATHOLIC, FOCUS_ACUTE, "MI",
        patterns=(
            "^TRINITY HEALTH", "^MERCYONE", "^SAINT JOSEPH MERCY",
            "^SAINT MARY MERCY", "^LOYOLA", "^GOTTLIEB", "^SAINT ALPHONSUS",
            "^MERCY HEALTH MUSKEGON", "OH:^MOUNT CARMEL",
        ),
        note="Bare '^TRINITY' is NOT a pattern here — Trinity Rock Island / "
             "Muscatine / Bettendorf are UnityPoint, and Trinity Hospital "
             "(CA) and Trinity Hospitals (ND) are unrelated again.",
    ),
    SystemDef(
        "chr_christus", "CHRISTUS Health", KIND_CATHOLIC, FOCUS_ACUTE, "TX",
        patterns=("^CHRISTUS",),
    ),
    SystemDef(
        "ssm", "SSM Health", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^SSM ", "^SSM-"),
    ),
    SystemDef(
        "mercy_mo", "Mercy (Chesterfield)", KIND_CATHOLIC, FOCUS_ACUTE, "MO",
        patterns=("^MERCY",),
        states=("MO", "AR", "OK", "KS"),
        note="Four-state Mercy footprint. MERCY is the single most "
             "over-loaded brand in HCRIS (77 facilities across at least "
             "six unrelated owners) — hence the hard state scope.",
    ),
    SystemDef(
        "bon_secours", "Bon Secours Mercy Health", KIND_CATHOLIC, FOCUS_ACUTE, "OH",
        patterns=("^BON SECOURS", "^MERCY HEALTH", "^MERCY ", "^SAINT ELIZABETH YOUNGSTOWN"),
        states=("OH", "KY", "VA", "SC"),
    ),
    SystemDef(
        "providence", "Providence", KIND_CATHOLIC, FOCUS_ACUTE, "WA",
        patterns=("^PROVIDENCE", "^SWEDISH MEDICAL", "^KADLEC", "^COVENANT HEALTH"),
        states=("WA", "OR", "CA", "AK", "MT", "TX", "NM"),
    ),
    SystemDef(
        "franciscan", "Franciscan Health", KIND_CATHOLIC, FOCUS_ACUTE, "IN",
        patterns=("^FRANCISCAN",),
        states=("IN", "IL"),
    ),
    SystemDef(
        "hshs", "Hospital Sisters Health System", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=("^HSHS",),
    ),
    SystemDef(
        "avera", "Avera Health", KIND_CATHOLIC, FOCUS_ACUTE, "SD",
        patterns=("^AVERA",),
    ),
    SystemDef(
        "adventhealth", "AdventHealth", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^ADVENTHEALTH", "^ADVENTIST HEALTH SYSTEM"),
    ),
    SystemDef(
        "adventist_health", "Adventist Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^ADVENTIST HEALTH",),
        states=("CA", "OR", "WA", "HI"),
    ),
    SystemDef(
        "adventist_md", "Adventist HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^ADVENTIST", "^AHC "),
        states=("MD",),
    ),

    # ── Large non-profit / regional systems ────────────────────────
    SystemDef(
        "kaiser", "Kaiser Permanente", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^KFH ", "^KFH-", "^KAISER"),
        note="HCRIS files Kaiser Foundation Hospitals as 'KFH - <city>'.",
    ),
    SystemDef(
        "sanford", "Sanford Health", KIND_NONPROFIT, FOCUS_ACUTE, "SD",
        patterns=("^SANFORD",),
    ),
    SystemDef(
        "banner", "Banner Health", KIND_NONPROFIT, FOCUS_ACUTE, "AZ",
        patterns=("^BANNER",),
    ),
    SystemDef(
        "advocate", "Advocate Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^ADVOCATE", "^AURORA", "^ATRIUM"),
        states=("IL", "WI", "NC", "SC", "GA", "AL"),
        note="Advocate Aurora + Atrium Health combination.",
    ),
    SystemDef(
        "baylor", "Baylor Scott & White Health", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^BAYLOR SCOTT", "^BAYLOR", "^SCOTT AND WHITE"),
        states=("TX",),
        exclude=("BAYLOR COLLEGE",),
    ),
    SystemDef(
        "texas_health", "Texas Health Resources", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^TEXAS HEALTH", "^TX HLTH"),
        states=("TX",),
    ),
    SystemDef(
        "memorial_hermann", "Memorial Hermann Health System", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^MEMORIAL HERMANN",),
    ),
    SystemDef(
        "houston_methodist", "Houston Methodist", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^HOUSTON METHODIST",),
    ),
    SystemDef(
        "methodist_dallas", "Methodist Health System (Dallas)", KIND_NONPROFIT, FOCUS_ACUTE, "TX",
        patterns=("^METHODIST ",),
        states=("TX",),
        exclude=("HOUSTON METHODIST",),
    ),
    SystemDef(
        "methodist_lebonheur", "Methodist Le Bonheur Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^METHODIST", "^LE BONHEUR"),
        states=("TN",),
    ),
    SystemDef(
        "nebraska_methodist", "Methodist Health System (Nebraska)", KIND_NONPROFIT, FOCUS_ACUTE, "NE",
        patterns=("^METHODIST", "^NEBRASKA METHODIST"),
        states=("NE",),
    ),
    SystemDef(
        "indiana_methodist", "Indiana University Health", KIND_ACADEMIC, FOCUS_ACUTE, "IN",
        patterns=("^INDIANA UNIVERSITY HEALTH", "^IU HEALTH"),
    ),
    SystemDef(
        "sutter", "Sutter Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SUTTER", "^CALIFORNIA PACIFIC MEDICAL", "^ALTA BATES"),
        states=("CA",),
    ),
    SystemDef(
        "scripps", "Scripps Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SCRIPPS",),
    ),
    SystemDef(
        "sharp", "Sharp HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^SHARP",),
        states=("CA",),
    ),
    SystemDef(
        "cedars", "Cedars-Sinai", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^CEDARS",),
    ),
    SystemDef(
        "memorialcare", "MemorialCare", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^MEMORIALCARE",),
    ),
    SystemDef(
        "intermountain", "Intermountain Health", KIND_NONPROFIT, FOCUS_ACUTE, "UT",
        patterns=(
            "^INTERMOUNTAIN", "^SAINT VINCENT HEALTHCARE",
            "^GOOD SAMARITAN MEDICAL CENTER",
            # Utah roster — Intermountain names its hospitals for the
            # valley they sit in, so the brand never appears in HCRIS.
            "UT:^UTAH VALLEY HOSPITAL", "UT:^MCKAY DEE", "UT:^LDS HOSPITAL",
            "UT:^CEDAR CITY HOSPITAL", "UT:^LOGAN REGIONAL",
            "UT:^AMERICAN FORK HOSPITAL", "UT:^ALTA VIEW", "UT:^RIVERTON HOSPITAL",
            "UT:^PARK CITY HOSPITAL", "UT:^LAYTON HOSPITAL",
            "UT:^SPANISH FORK HOSPITAL", "UT:^OREM COMMUNITY",
            "UT:^DELTA COMMUNITY", "UT:^FILLMORE COMMUNITY",
            "UT:^SANPETE VALLEY", "UT:^SEVIER VALLEY", "UT:^GARFIELD MEMORIAL",
            "UT:^HEBER VALLEY", "UT:^BEAR RIVER VALLEY",
            "UT:^SAINT GEORGE REGIONAL", "UT:^PRIMARY CHILDRENS",
            "ID:^CASSIA REGIONAL",
        ),
        states=("UT", "ID", "NV", "CO", "MT", "WY", "KS"),
    ),
    SystemDef(
        "ochsner", "Ochsner Health", KIND_NONPROFIT, FOCUS_ACUTE, "LA",
        patterns=("^OCHSNER",),
    ),
    SystemDef(
        "piedmont", "Piedmont Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^PIEDMONT",),
        states=("GA",),
    ),
    SystemDef(
        "wellstar", "Wellstar Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^WELLSTAR", "GA:^KENNESTONE", "GA:^COBB HOSPITAL",
                  "GA:^SPALDING REGIONAL", "GA:^SYLVAN GROVE"),
    ),
    SystemDef(
        "northside", "Northside Hospital", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^NORTHSIDE HOSPITAL",),
        states=("GA",),
    ),
    SystemDef(
        "prisma", "Prisma Health", KIND_NONPROFIT, FOCUS_ACUTE, "SC",
        patterns=("^PRISMA",),
    ),
    SystemDef(
        "novant", "Novant Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^NOVANT", "NC:^PRESBYTERIAN HOSPITAL", "NC:^FORSYTH MEDICAL"),
    ),
    SystemDef(
        "unc", "UNC Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^UNC ", "^UNIVERSITY OF NORTH CAROLINA"),
    ),
    SystemDef(
        "duke", "Duke Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^DUKE",),
    ),
    SystemDef(
        "cone", "Cone Health", KIND_NONPROFIT, FOCUS_ACUTE, "NC",
        patterns=("^CONE HEALTH", "MOSES H CONE", "NC:^ALAMANCE REGIONAL"),
    ),
    SystemDef(
        "sentara", "Sentara Health", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^SENTARA",),
    ),
    SystemDef(
        "inova", "Inova Health System", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^INOVA",),
    ),
    SystemDef(
        "vcu", "VCU Health", KIND_ACADEMIC, FOCUS_ACUTE, "VA",
        patterns=("^VCU ", "^VIRGINIA COMMONWEALTH"),
    ),
    SystemDef(
        "medstar", "MedStar Health", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^MEDSTAR",),
    ),
    SystemDef(
        "hopkins", "Johns Hopkins Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "MD",
        patterns=("^JOHNS HOPKINS", "^SUBURBAN HOSPITAL", "^SIBLEY MEMORIAL"),
    ),
    SystemDef(
        "lifebridge", "LifeBridge Health", KIND_NONPROFIT, FOCUS_ACUTE, "MD",
        patterns=("^LIFEBRIDGE", "^SINAI HOSPITAL OF BALTIMORE"),
    ),
    SystemDef(
        "umms", "University of Maryland Medical System", KIND_ACADEMIC, FOCUS_ACUTE, "MD",
        patterns=("^UNIVERSITY OF MARYLAND", "^UM ", "^UMMS"),
        states=("MD",),
    ),
    SystemDef(
        "christiana", "ChristianaCare", KIND_NONPROFIT, FOCUS_ACUTE, "DE",
        patterns=("^CHRISTIANA",),
    ),
    SystemDef(
        "nemours", "Nemours Children's Health", KIND_NONPROFIT, FOCUS_CHILDRENS, "FL",
        patterns=("^NEMOURS",),
    ),

    # ── Northeast ──────────────────────────────────────────────────
    SystemDef(
        "northwell", "Northwell Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^NORTHWELL", "^LONG ISLAND JEWISH", "^NORTH SHORE UNIVERSITY HOSPITAL",
                  "^LENOX HILL", "^STATEN ISLAND UNIVERSITY"),
        states=("NY",),
    ),
    SystemDef(
        "nyp", "NewYork-Presbyterian", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^NEW YORK PRESBYTERIAN", "^NEWYORK PRESBYTERIAN", "^NY PRESBYTERIAN"),
    ),
    SystemDef(
        "mount_sinai", "Mount Sinai Health System", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^MOUNT SINAI",),
        states=("NY",),
    ),
    SystemDef(
        "nyu", "NYU Langone Health", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^NYU",),
    ),
    SystemDef(
        "montefiore", "Montefiore Health System", KIND_ACADEMIC, FOCUS_ACUTE, "NY",
        patterns=("^MONTEFIORE",),
    ),
    SystemDef(
        "nyc_h_h", "NYC Health + Hospitals", KIND_GOVERNMENT, FOCUS_ACUTE, "NY",
        patterns=("^NYC HEALTH", "^NEW YORK CITY HEALTH AND HOSPITALS"),
    ),
    SystemDef(
        "rochester_regional", "Rochester Regional Health", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^ROCHESTER GENERAL", "^ROCHESTER REGIONAL", "^UNITED MEMORIAL MEDICAL"),
        states=("NY",),
    ),
    SystemDef(
        "bassett", "Bassett Healthcare Network", KIND_NONPROFIT, FOCUS_ACUTE, "NY",
        patterns=("^BASSETT",),
    ),
    SystemDef(
        "mass_general_brigham", "Mass General Brigham", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^MASSACHUSETTS GENERAL", "^BRIGHAM AND WOMEN", "^NEWTON WELLESLEY",
                  "^SALEM HOSPITAL", "^COOLEY DICKINSON", "^MASS GENERAL"),
        states=("MA", "NH"),
    ),
    SystemDef(
        "beth_israel_lahey", "Beth Israel Lahey Health", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^BETH ISRAEL", "^LAHEY", "^MOUNT AUBURN", "^WINCHESTER HOSPITAL"),
        states=("MA",),
    ),
    SystemDef(
        "umass", "UMass Memorial Health", KIND_ACADEMIC, FOCUS_ACUTE, "MA",
        patterns=("^UMASS", "^UMASS MEMORIAL"),
    ),
    SystemDef(
        "baystate", "Baystate Health", KIND_NONPROFIT, FOCUS_ACUTE, "MA",
        patterns=("^BAYSTATE",),
    ),
    SystemDef(
        "yale", "Yale New Haven Health", KIND_ACADEMIC, FOCUS_ACUTE, "CT",
        patterns=("^YALE", "^BRIDGEPORT HOSPITAL", "^GREENWICH HOSPITAL", "^LAWRENCE AND MEMORIAL"),
        states=("CT", "RI"),
    ),
    SystemDef(
        "hartford", "Hartford HealthCare", KIND_NONPROFIT, FOCUS_ACUTE, "CT",
        patterns=("^HARTFORD HOSPITAL", "^HARTFORD HEALTHCARE", "^BACKUS", "^WINDHAM"),
        states=("CT",),
    ),
    SystemDef(
        "dartmouth", "Dartmouth Health", KIND_ACADEMIC, FOCUS_ACUTE, "NH",
        patterns=("^DARTMOUTH", "^MARY HITCHCOCK"),
    ),
    SystemDef(
        "maine_health", "MaineHealth", KIND_NONPROFIT, FOCUS_ACUTE, "ME",
        patterns=("^MAINE MEDICAL", "^MAINEHEALTH", "^MAINEGENERAL"),
        states=("ME",),
    ),
    SystemDef(
        "hackensack", "Hackensack Meridian Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^HACKENSACK", "^JERSEY SHORE UNIVERSITY", "^OCEAN UNIVERSITY MEDICAL"),
        states=("NJ",),
    ),
    SystemDef(
        "rwjbarnabas", "RWJBarnabas Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^ROBERT WOOD JOHNSON", "^RWJ", "^BARNABAS", "^NEWARK BETH ISRAEL",
                  "^COMMUNITY MEDICAL CENTER"),
        states=("NJ",),
    ),
    SystemDef(
        "atlantic_health", "Atlantic Health System", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^MORRISTOWN MEDICAL", "^OVERLOOK MEDICAL", "^ATLANTIC HEALTH"),
        states=("NJ",),
    ),
    SystemDef(
        "virtua", "Virtua Health", KIND_NONPROFIT, FOCUS_ACUTE, "NJ",
        patterns=("^VIRTUA",),
    ),
    SystemDef(
        "upmc", "UPMC", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^UPMC",),
    ),
    SystemDef(
        "penn_medicine", "Penn Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^HOSPITAL OF THE UNIVERSITY OF PENNSYLVANIA", "^PENN PRESBYTERIAN",
                  "^PENNSYLVANIA HOSPITAL", "^LANCASTER GENERAL", "^CHESTER COUNTY HOSPITAL"),
        states=("PA", "NJ"),
    ),
    SystemDef(
        "jefferson", "Jefferson Health", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^JEFFERSON", "^THOMAS JEFFERSON", "^ABINGTON"),
        states=("PA", "NJ"),
    ),
    SystemDef(
        "temple", "Temple Health", KIND_ACADEMIC, FOCUS_ACUTE, "PA",
        patterns=("^TEMPLE",),
        states=("PA",),
    ),
    SystemDef(
        "geisinger", "Geisinger", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^GEISINGER",),
    ),
    SystemDef(
        "lehigh", "Lehigh Valley Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^LEHIGH VALLEY",),
    ),
    SystemDef(
        "st_lukes_pa", "St. Luke's University Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^SAINT LUKES",),
        states=("PA",),
    ),
    SystemDef(
        "wellspan", "WellSpan Health", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^WELLSPAN",),
    ),
    SystemDef(
        "ahn", "Allegheny Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^ALLEGHENY GENERAL", "^ALLEGHENY VALLEY", "^AHN ", "^FORBES HOSPITAL",
                  "^WEST PENN"),
        states=("PA",),
    ),
    SystemDef(
        "tower_health", "Tower Health", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^TOWER HEALTH", "^READING HOSPITAL", "^POTTSTOWN HOSPITAL"),
        states=("PA",),
    ),

    # ── Midwest ────────────────────────────────────────────────────
    SystemDef(
        "cleveland_clinic", "Cleveland Clinic", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        patterns=("^CLEVELAND CLINIC", "^FAIRVIEW HOSPITAL", "^HILLCREST HOSPITAL",
                  "^MARYMOUNT HOSPITAL", "^LUTHERAN HOSPITAL"),
        states=("OH", "FL"),
    ),
    SystemDef(
        "uh_ohio", "University Hospitals (Ohio)", KIND_ACADEMIC, FOCUS_ACUTE, "OH",
        patterns=("^UH ",),
        states=("OH",),
    ),
    SystemDef(
        "ohiohealth", "OhioHealth", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^OHIOHEALTH", "^RIVERSIDE METHODIST", "^GRANT MEDICAL CENTER"),
        states=("OH",),
    ),
    SystemDef(
        "promedica", "ProMedica", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^PROMEDICA",),
    ),
    SystemDef(
        "trihealth", "TriHealth", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^TRIHEALTH", "^BETHESDA NORTH", "^GOOD SAMARITAN HOSPITAL OF CINCINNATI"),
        states=("OH",),
    ),
    SystemDef(
        "premier_health", "Premier Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^MIAMI VALLEY", "^PREMIER HEALTH"),
        states=("OH",),
    ),
    SystemDef(
        "corewell", "Corewell Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^COREWELL", "^BEAUMONT", "^SPECTRUM HEALTH"),
        states=("MI",),
    ),
    SystemDef(
        "henry_ford", "Henry Ford Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^HENRY FORD",),
    ),
    SystemDef(
        "mclaren", "McLaren Health Care", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MCLAREN",),
    ),
    SystemDef(
        "munson", "Munson Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MUNSON",),
    ),
    SystemDef(
        "mymichigan", "MyMichigan Health", KIND_NONPROFIT, FOCUS_ACUTE, "MI",
        patterns=("^MYMICHIGAN",),
    ),
    SystemDef(
        "northwestern", "Northwestern Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "IL",
        patterns=("^NORTHWESTERN", "^CENTRAL DUPAGE", "^DELNOR"),
        states=("IL",),
    ),
    SystemDef(
        "endeavor", "Endeavor Health", KIND_NONPROFIT, FOCUS_ACUTE, "IL",
        patterns=("^ENDEAVOR", "^NORTHSHORE UNIVERSITY", "^EDWARD HOSPITAL", "^ELMHURST HOSPITAL"),
        states=("IL",),
    ),
    SystemDef(
        "rush", "Rush University System for Health", KIND_ACADEMIC, FOCUS_ACUTE, "IL",
        patterns=("^RUSH",),
        states=("IL",),
    ),
    SystemDef(
        "osf", "OSF HealthCare", KIND_CATHOLIC, FOCUS_ACUTE, "IL",
        patterns=("^OSF",),
    ),
    SystemDef(
        "carle", "Carle Health", KIND_NONPROFIT, FOCUS_ACUTE, "IL",
        patterns=("^CARLE",),
    ),
    SystemDef(
        "unitypoint", "UnityPoint Health", KIND_NONPROFIT, FOCUS_ACUTE, "IA",
        patterns=("^UNITYPOINT", "IA,IL:^TRINITY", "IA:^ALLEN HOSPITAL",
                  "IA:^ILES", "IA:^METHODIST WEST"),
        note="Quad-Cities and Fort Dodge facilities still file as TRINITY — "
             "the reason Trinity Health cannot claim a bare '^TRINITY'.",
    ),
    SystemDef(
        "univ_iowa", "University of Iowa Health Care", KIND_ACADEMIC, FOCUS_ACUTE, "IA",
        patterns=("^UNIVERSITY OF IOWA", "^UI HEALTH CARE"),
    ),
    SystemDef(
        "genesis_ia", "Genesis Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IA",
        patterns=("^GENESIS MEDICAL",),
        states=("IA", "IL"),
    ),
    SystemDef(
        "allina", "Allina Health", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^ALLINA", "^ABBOTT NORTHWESTERN", "^UNITED HOSPITAL", "^MERCY HOSPITAL MN"),
        states=("MN", "WI"),
    ),
    SystemDef(
        "fairview", "M Health Fairview", KIND_ACADEMIC, FOCUS_ACUTE, "MN",
        patterns=("^FAIRVIEW", "^M HEALTH"),
        states=("MN",),
    ),
    SystemDef(
        "healthpartners", "HealthPartners", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^HEALTHPARTNERS", "^REGIONS HOSPITAL", "^PARK NICOLLET"),
        states=("MN", "WI"),
    ),
    SystemDef(
        "essentia", "Essentia Health", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^ESSENTIA",),
    ),
    SystemDef(
        "cuyuna", "CentraCare", KIND_NONPROFIT, FOCUS_ACUTE, "MN",
        patterns=("^CENTRACARE", "^SAINT CLOUD HOSPITAL"),
        states=("MN",),
    ),
    SystemDef(
        "mayo", "Mayo Clinic", KIND_ACADEMIC, FOCUS_ACUTE, "MN",
        patterns=("^MAYO",),
    ),
    SystemDef(
        "aspirus", "Aspirus Health", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^ASPIRUS",),
    ),
    SystemDef(
        "froedtert", "Froedtert ThedaCare Health", KIND_ACADEMIC, FOCUS_ACUTE, "WI",
        patterns=("^FROEDTERT", "^THEDACARE"),
    ),
    SystemDef(
        "marshfield", "Marshfield Clinic Health System", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^MARSHFIELD",),
    ),
    SystemDef(
        "gundersen", "Emplify Health (Gundersen · Bellin)", KIND_NONPROFIT, FOCUS_ACUTE, "WI",
        patterns=("^GUNDERSEN", "^BELLIN"),
    ),
    SystemDef(
        "nebraska_medicine", "Nebraska Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "NE",
        patterns=("NE:NEBRASKA MEDICAL CENTER", "^NEBRASKA MEDICINE"),
    ),
    SystemDef(
        "bryan", "Bryan Health", KIND_NONPROFIT, FOCUS_ACUTE, "NE",
        patterns=("^BRYAN",),
        states=("NE",),
    ),
    SystemDef(
        "ku_health", "University of Kansas Health System", KIND_ACADEMIC, FOCUS_ACUTE, "KS",
        patterns=("^UNIVERSITY OF KANSAS",),
    ),
    SystemDef(
        "st_lukes_kc", "Saint Luke's Health System (Kansas City)", KIND_NONPROFIT, FOCUS_ACUTE, "MO",
        patterns=("^SAINT LUKES",),
        states=("MO", "KS"),
    ),
    SystemDef(
        "bjc", "BJC HealthCare", KIND_ACADEMIC, FOCUS_ACUTE, "MO",
        patterns=("^BARNES JEWISH", "^BJC", "^MISSOURI BAPTIST", "^CHRISTIAN HOSPITAL"),
        states=("MO", "IL"),
    ),
    SystemDef(
        "cox", "CoxHealth", KIND_NONPROFIT, FOCUS_ACUTE, "MO",
        patterns=("^COX ", "^COXHEALTH"),
        states=("MO",),
    ),

    # ── South / Southeast ──────────────────────────────────────────
    SystemDef(
        "uab", "UAB Health System", KIND_ACADEMIC, FOCUS_ACUTE, "AL",
        patterns=("^UAB",),
    ),
    SystemDef(
        "infirmary", "Infirmary Health", KIND_NONPROFIT, FOCUS_ACUTE, "AL",
        patterns=("^MOBILE INFIRMARY", "^INFIRMARY"),
        states=("AL",),
    ),
    SystemDef(
        "baptist_fl", "Baptist Health South Florida", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^BAPTIST",),
        states=("FL",),
    ),
    SystemDef(
        "baptist_ky", "Baptist Health (Kentucky)", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^BAPTIST",),
        states=("KY",),
    ),
    SystemDef(
        "baptist_memphis", "Baptist Memorial Health Care", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^BAPTIST MEMORIAL", "^BAPTIST MEM"),
        states=("TN", "MS", "AR"),
    ),
    SystemDef(
        "baptist_ar", "Baptist Health (Arkansas)", KIND_NONPROFIT, FOCUS_ACUTE, "AR",
        patterns=("^BAPTIST",),
        states=("AR",),
    ),
    SystemDef(
        "orlando_health", "Orlando Health", KIND_NONPROFIT, FOCUS_ACUTE, "FL",
        patterns=("^ORLANDO HEALTH",),
    ),
    SystemDef(
        "tampa_general", "Tampa General Hospital", KIND_ACADEMIC, FOCUS_ACUTE, "FL",
        patterns=("^TAMPA GENERAL",),
    ),
    SystemDef(
        "jackson_health", "Jackson Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^JACKSON MEMORIAL", "^JACKSON NORTH", "^JACKSON SOUTH", "^JACKSON WEST"),
        states=("FL",),
    ),
    SystemDef(
        "lee_health", "Lee Health", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^LEE MEMORIAL", "^LEE HEALTH", "^GULF COAST MEDICAL CENTER"),
        states=("FL",),
    ),
    SystemDef(
        "uf_health", "UF Health", KIND_ACADEMIC, FOCUS_ACUTE, "FL",
        patterns=("^UF HEALTH", "^SHANDS"),
    ),
    SystemDef(
        "vanderbilt", "Vanderbilt Health", KIND_ACADEMIC, FOCUS_ACUTE, "TN",
        patterns=("^VANDERBILT",),
    ),
    SystemDef(
        "ballad", "Ballad Health", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^BALLAD", "TN:^HOLSTON VALLEY", "TN:^JOHNSON CITY MEDICAL",
                  "TN:^BRISTOL REGIONAL", "TN:^INDIAN PATH", "VA:^NORTON COMMUNITY",
                  "VA:^LONESOME PINE", "VA:^JOHNSTON MEMORIAL"),
    ),
    SystemDef(
        "norton", "Norton Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^NORTON",),
        states=("KY", "IN"),
    ),
    SystemDef(
        "uofl", "UofL Health", KIND_ACADEMIC, FOCUS_ACUTE, "KY",
        patterns=("^UOFL", "^UNIVERSITY OF LOUISVILLE"),
    ),
    SystemDef(
        "lcmc", "LCMC Health", KIND_NONPROFIT, FOCUS_ACUTE, "LA",
        patterns=("^LCMC", "^TOURO INFIRMARY", "^EAST JEFFERSON GENERAL"),
        states=("LA",),
    ),
    SystemDef(
        "franciscan_missionaries", "Franciscan Missionaries of Our Lady", KIND_CATHOLIC, FOCUS_ACUTE, "LA",
        patterns=("^OUR LADY OF THE LAKE", "^OUR LADY OF LOURDES", "^SAINT FRANCIS MEDICAL CENTER"),
        states=("LA",),
    ),
    SystemDef(
        "ummc_ms", "University of Mississippi Medical Center", KIND_ACADEMIC, FOCUS_ACUTE, "MS",
        patterns=("^UNIVERSITY OF MISSISSIPPI",),
    ),
    SystemDef(
        "musc", "MUSC Health", KIND_ACADEMIC, FOCUS_ACUTE, "SC",
        patterns=("^MUSC",),
    ),
    SystemDef(
        "unm", "UNM Health", KIND_ACADEMIC, FOCUS_ACUTE, "NM",
        patterns=("^UNIVERSITY OF NEW MEXICO", "^UNM "),
    ),
    SystemDef(
        "presbyterian_nm", "Presbyterian Healthcare Services", KIND_NONPROFIT, FOCUS_ACUTE, "NM",
        patterns=("^PRESBYTERIAN",),
        states=("NM",),
    ),
    SystemDef(
        "ut_system", "UT Health (Texas)", KIND_ACADEMIC, FOCUS_ACUTE, "TX",
        patterns=("^UT ",),
        states=("TX",),
    ),
    SystemDef(
        "cook_childrens", "Cook Children's Health Care System", KIND_NONPROFIT, FOCUS_CHILDRENS, "TX",
        patterns=("^COOK CHILDRENS",),
    ),
    SystemDef(
        "harris_health", "Harris Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "TX",
        patterns=("^HARRIS HEALTH", "^BEN TAUB", "^LYNDON B JOHNSON"),
        states=("TX",),
    ),

    # ── West / Mountain ────────────────────────────────────────────
    SystemDef(
        "honorhealth", "HonorHealth", KIND_NONPROFIT, FOCUS_ACUTE, "AZ",
        patterns=("^HONORHEALTH",),
    ),
    SystemDef(
        "uchealth", "UCHealth", KIND_ACADEMIC, FOCUS_ACUTE, "CO",
        patterns=("^UCHEALTH", "^UNIVERSITY OF COLORADO"),
    ),
    SystemDef(
        "sclhealth", "Intermountain (SCL Health legacy)", KIND_CATHOLIC, FOCUS_ACUTE, "CO",
        patterns=("^SCL ", "^LUTHERAN MEDICAL CENTER", "^SAINT JOSEPH HOSPITAL DENVER"),
        states=("CO", "MT"),
    ),
    SystemDef(
        "billings", "Billings Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "MT",
        patterns=("^BILLINGS CLINIC",),
    ),
    SystemDef(
        "st_lukes_id", "St. Luke's Health System (Idaho)", KIND_NONPROFIT, FOCUS_ACUTE, "ID",
        patterns=("^SAINT LUKES",),
        states=("ID",),
    ),
    SystemDef(
        "multicare", "MultiCare Health System", KIND_NONPROFIT, FOCUS_ACUTE, "WA",
        patterns=("^MULTICARE", "^TACOMA GENERAL", "^GOOD SAMARITAN HOSPITAL PUYALLUP"),
        states=("WA",),
    ),
    SystemDef(
        "uw_medicine", "UW Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "WA",
        patterns=("^UNIVERSITY OF WASHINGTON", "^UW MEDICINE", "^HARBORVIEW"),
    ),
    SystemDef(
        "peacehealth", "PeaceHealth", KIND_CATHOLIC, FOCUS_ACUTE, "WA",
        patterns=("^PEACEHEALTH",),
    ),
    SystemDef(
        "confluence", "Confluence Health", KIND_NONPROFIT, FOCUS_ACUTE, "WA",
        patterns=("^CONFLUENCE", "WA:^CENTRAL WASHINGTON HOSPITAL"),
    ),
    SystemDef(
        "legacy", "Legacy Health", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^LEGACY",),
        states=("OR", "WA"),
    ),
    SystemDef(
        "ohsu", "OHSU Health", KIND_ACADEMIC, FOCUS_ACUTE, "OR",
        patterns=("^OHSU", "^OREGON HEALTH AND SCIENCE"),
    ),
    SystemDef(
        "samaritan_or", "Samaritan Health Services", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^SAMARITAN",),
        states=("OR",),
    ),
    SystemDef(
        "renown", "Renown Health", KIND_NONPROFIT, FOCUS_ACUTE, "NV",
        patterns=("^RENOWN",),
    ),
    SystemDef(
        "queens", "The Queen's Health System", KIND_NONPROFIT, FOCUS_ACUTE, "HI",
        patterns=("^QUEENS MEDICAL", "^THE QUEENS"),
        states=("HI",),
    ),
    SystemDef(
        "hawaii_pacific", "Hawai'i Pacific Health", KIND_NONPROFIT, FOCUS_ACUTE, "HI",
        patterns=("^STRAUB", "^KAPIOLANI", "^PALI MOMI", "^WILCOX"),
        states=("HI",),
    ),
    SystemDef(
        "alaska_native", "Alaska Native Tribal Health Consortium", KIND_GOVERNMENT, FOCUS_ACUTE, "AK",
        patterns=("^ALASKA NATIVE",),
    ),

    # ── University of California ───────────────────────────────────
    SystemDef(
        "uc_health", "University of California Health", KIND_ACADEMIC, FOCUS_ACUTE, "CA",
        patterns=("^UCSF", "^UCLA", "^UC SAN DIEGO", "^UC DAVIS", "^UC IRVINE",
                  "^UNIVERSITY OF CALIFORNIA", "^RONALD REAGAN"),
        states=("CA",),
    ),
    SystemDef(
        "stanford", "Stanford Health Care", KIND_ACADEMIC, FOCUS_ACUTE, "CA",
        patterns=("^STANFORD", "^LUCILE PACKARD"),
    ),
    SystemDef(
        "dignity_ca", "Dignity Health (CommonSpirit CA)", KIND_CATHOLIC, FOCUS_ACUTE, "CA",
        patterns=("^DIGNITY", "^MERCY GENERAL", "^MERCY SAN JUAN", "^SAINT JOSEPHS MEDICAL CENTER"),
        states=("CA", "NV"),
    ),
    SystemDef(
        "cedars_marina", "Providence Southern California", KIND_CATHOLIC, FOCUS_ACUTE, "CA",
        patterns=("^SAINT JOSEPH HOSPITAL ORANGE", "^HOAG", "^MISSION HOSPITAL"),
        states=("CA",),
    ),
    SystemDef(
        "pih", "PIH Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^PIH HEALTH",),
    ),
    SystemDef(
        "john_muir", "John Muir Health", KIND_NONPROFIT, FOCUS_ACUTE, "CA",
        patterns=("^JOHN MUIR",),
    ),

    # ── Regional systems surfaced by the unmapped long tail ────────
    #
    # Every entry below was added because the candidate-cluster scan
    # (see :func:`candidate_clusters`) showed two or more unmapped
    # facilities sharing a brand in one state. That scan is the intended
    # maintenance loop for this registry.
    SystemDef(
        "logan_health", "Logan Health", KIND_NONPROFIT, FOCUS_ACUTE, "MT",
        patterns=("^LOGAN HEALTH",),
    ),
    SystemDef(
        "monument", "Monument Health", KIND_NONPROFIT, FOCUS_ACUTE, "SD",
        patterns=("^MONUMENT HEALTH",),
    ),
    SystemDef(
        "broward", "Broward Health", KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("^BROWARD HEALTH",),
    ),
    SystemDef(
        "memorial_fl", "Memorial Healthcare System (South Broward)",
        KIND_GOVERNMENT, FOCUS_ACUTE, "FL",
        patterns=("FL:^MEMORIAL REGIONAL", "FL:^MEMORIAL HOSPITAL WEST",
                  "FL:^MEMORIAL HOSPITAL MIRAMAR", "FL:^MEMORIAL HOSPITAL PEMBROKE",
                  "FL:^JOE DIMAGGIO"),
    ),
    SystemDef(
        "kettering", "Kettering Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^KETTERING HEALTH", "OH:^SOIN MEDICAL"),
    ),
    SystemDef(
        "summa", "Summa Health", KIND_NONPROFIT, FOCUS_ACUTE, "OH",
        patterns=("^SUMMA",),
    ),
    SystemDef(
        "st_elizabeth_ky", "St. Elizabeth Healthcare", KIND_CATHOLIC, FOCUS_ACUTE, "KY",
        patterns=("^SAINT ELIZABETH",),
        states=("KY",),
    ),
    SystemDef(
        "arh", "Appalachian Regional Healthcare", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("ARH",),
        states=("KY", "WV"),
        note="Files as '<TOWN> ARH' — an unanchored pattern, safe only "
             "because of the word boundary and the two-state scope.",
    ),
    SystemDef(
        "owensboro", "Owensboro Health", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("^OWENSBORO HEALTH",),
    ),
    SystemDef(
        "med_center_health", "Med Center Health", KIND_NONPROFIT, FOCUS_ACUTE, "KY",
        patterns=("KY:^THE MEDICAL CENTER",),
    ),
    SystemDef(
        "saint_francis_ok", "Saint Francis Health System", KIND_CATHOLIC, FOCUS_ACUTE, "OK",
        patterns=("^SAINT FRANCIS",),
        states=("OK",),
    ),
    SystemDef(
        "st_charles_or", "St. Charles Health System", KIND_NONPROFIT, FOCUS_ACUTE, "OR",
        patterns=("^SAINT CHARLES",),
        states=("OR",),
    ),
    SystemDef(
        "noland", "Noland Health Services", KIND_NONPROFIT, FOCUS_LTACH, "AL",
        patterns=("^NOLAND",),
    ),
    SystemDef(
        "community_health_in", "Community Health Network", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("IN:^COMMUNITY HOSPITAL", "IN:^COMMUNITY HEALTH NETWORK",
                  "IN:^COMMUNITY HEART AND VASCULAR"),
    ),
    SystemDef(
        "parkview", "Parkview Health", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("^PARKVIEW",),
        states=("IN", "OH"),
    ),
    SystemDef(
        "beacon_in", "Beacon Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("IN:^MEMORIAL HOSPITAL OF SOUTH BEND", "IN:^ELKHART GENERAL",
                  "IN:^BEACON "),
    ),
    SystemDef(
        "deaconess", "Deaconess Health System", KIND_NONPROFIT, FOCUS_ACUTE, "IN",
        patterns=("^DEACONESS",),
        states=("IN", "KY", "IL"),
    ),
    SystemDef(
        "north_mississippi", "North Mississippi Health Services",
        KIND_NONPROFIT, FOCUS_ACUTE, "MS",
        patterns=("^NORTH MISSISSIPPI",),
    ),
    SystemDef(
        "great_plains_ks", "Great Plains Health Alliance", KIND_NONPROFIT, FOCUS_ACUTE, "KS",
        patterns=("^GREAT PLAINS",),
        states=("KS",),
    ),
    SystemDef(
        "wvu", "WVU Medicine", KIND_ACADEMIC, FOCUS_ACUTE, "WV",
        patterns=("^WVU", "^WEST VIRGINIA UNIVERSITY"),
    ),
    SystemDef(
        "ecu_health", "ECU Health", KIND_ACADEMIC, FOCUS_ACUTE, "NC",
        patterns=("^ECU HEALTH", "^VIDANT"),
    ),
    SystemDef(
        "nuvance", "Nuvance Health", KIND_NONPROFIT, FOCUS_ACUTE, "CT",
        patterns=("^DANBURY HOSPITAL", "^NORWALK HOSPITAL", "^VASSAR BROTHERS",
                  "^SHARON HOSPITAL", "^NORTHERN DUTCHESS"),
        states=("CT", "NY"),
    ),
    SystemDef(
        "catholic_health_buffalo", "Catholic Health (Buffalo)", KIND_CATHOLIC, FOCUS_ACUTE, "NY",
        patterns=("NY:^MERCY HOSPITAL OF BUFFALO", "NY:^SISTERS OF CHARITY",
                  "NY:^KENMORE MERCY", "NY:^MOUNT SAINT MARYS"),
    ),
    SystemDef(
        "guthrie", "The Guthrie Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "PA",
        patterns=("^GUTHRIE",),
    ),
    SystemDef(
        "carilion", "Carilion Clinic", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^CARILION",),
    ),
    SystemDef(
        "riverside_va", "Riverside Health", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("^RIVERSIDE",),
        states=("VA",),
    ),
    SystemDef(
        "valley_health_va", "Valley Health System", KIND_NONPROFIT, FOCUS_ACUTE, "VA",
        patterns=("VA,WV:^WINCHESTER MEDICAL", "VA,WV:^SHENANDOAH MEMORIAL",
                  "VA,WV:^WARREN MEMORIAL", "VA,WV:^PAGE MEMORIAL"),
    ),
    SystemDef(
        "erlanger", "Erlanger Health", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("^ERLANGER",),
    ),
    SystemDef(
        "covenant_tn", "Covenant Health (Tennessee)", KIND_NONPROFIT, FOCUS_ACUTE, "TN",
        patterns=("TN:^FORT SANDERS", "TN:^PARKWEST", "TN:^METHODIST MEDICAL CENTER OF OAK",
                  "TN:^LECONTE", "TN:^MORRISTOWN HAMBLEN", "TN:^ROANE MEDICAL"),
    ),
    SystemDef(
        "northeast_georgia", "Northeast Georgia Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^NORTHEAST GEORGIA",),
    ),
    SystemDef(
        "tanner", "Tanner Health System", KIND_NONPROFIT, FOCUS_ACUTE, "GA",
        patterns=("^TANNER",),
    ),
    SystemDef(
        "emory", "Emory Healthcare", KIND_ACADEMIC, FOCUS_ACUTE, "GA",
        patterns=("^EMORY",),
    ),
    SystemDef(
        "grady", "Grady Health System", KIND_GOVERNMENT, FOCUS_ACUTE, "GA",
        patterns=("^GRADY",),
        states=("GA",),
    ),
    SystemDef(
        "menonita", "Menonita Healthcare System", KIND_NONPROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL MENONITA",),
    ),
    SystemDef(
        "hima", "HIMA San Pablo", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL HIMA", "^HIMA SAN PABLO"),
    ),
    SystemDef(
        "san_pablo_pr", "San Pablo Health System", KIND_FOR_PROFIT, FOCUS_ACUTE, "PR",
        patterns=("^HOSPITAL SAN PABLO",),
    ),
)


# ── Name normalization + matching ──────────────────────────────────

_PUNCT_RE = re.compile(r"[^A-Z0-9]+")
_SAINT_RE = re.compile(r"\bST\b\.?")
_SPACE_RE = re.compile(r"\s+")


def normalize_name(raw: Any) -> str:
    """Upper-case, punctuation-stripped facility name used for matching.

    HCRIS names are truncated at ~36 characters and inconsistent about
    punctuation ("ST. MARY'S" / "ST MARYS" / "SAINT MARYS" all occur for
    the same brand), so matching on the raw string loses whole systems.
    Normalizing folds all three into ``SAINT MARYS``.
    """
    s = str(raw or "").upper().replace("&", " AND ")
    # Apostrophes are dropped, not spaced: "ST. MARY'S" has to fold onto
    # "ST MARYS", which is how HCRIS files the same hospital elsewhere.
    s = s.replace("'", "").replace("\u2019", "")
    s = _PUNCT_RE.sub(" ", s)
    s = _SAINT_RE.sub("SAINT", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def _compile_pattern(pattern: str) -> "re.Pattern[str]":
    """Compile one registry pattern into a word-bounded regex.

    ``^`` anchors to the start of the name. **Both ends of every pattern
    are word-bounded.** The first cut of this matcher compared with
    ``str.startswith`` and pulled CHINLE, CHINESE HOSPITAL, CHINO VALLEY
    and five children's hospitals into CommonSpirit off the ``CHI``
    brand — short brand abbreviations (CHI, UH, UT, UM, PAM, SSH) are
    only safe with a trailing boundary.
    """
    body = pattern.lstrip("^").strip()
    if not body:
        # Never-matching pattern — cheaper than special-casing at call sites.
        return re.compile(r"(?!)")
    prefix = "^" if pattern.startswith("^") else r"(?<![A-Z0-9])"
    return re.compile(prefix + re.escape(body) + r"(?![A-Z0-9])")


def _pattern_hits(norm: str, pattern: str) -> bool:
    """True if ``pattern`` matches ``norm``. Kept for direct/test use —
    the hot path goes through the precompiled index below."""
    return bool(_compile_pattern(pattern).search(norm))


# A pattern may carry its own state scope as a ``TX:`` / ``UT,ID:``
# prefix. This exists so a national system whose local brands are
# state-specific (HCA's MountainStar names in Utah, CommonSpirit's
# legacy Saint Joseph names in Kentucky) stays ONE row in the master
# mapping. Splitting them into per-state pseudo-systems would answer
# the "how many hospitals does this system run" question wrongly.
_PATTERN_SCOPE_RE = re.compile(r"^([A-Z]{2}(?:,[A-Z]{2})*):")


def _split_pattern(pattern: str) -> Tuple[Tuple[str, ...], str]:
    """Split ``"UT,ID:^ALTA VIEW"`` into ``(("UT", "ID"), "^ALTA VIEW")``."""
    m = _PATTERN_SCOPE_RE.match(pattern)
    if not m:
        return (), pattern
    return tuple(m.group(1).split(",")), pattern[m.end():]


@dataclass(frozen=True)
class _Compiled:
    """One registry pattern, ready to run against a normalized name."""

    sysdef: SystemDef
    raw: str
    regex: Any
    scope: Tuple[str, ...]
    specificity: int


def _build_index() -> Tuple[Tuple[_Compiled, ...], Dict[str, Tuple[_Compiled, ...]]]:
    """Precompile every pattern once, bucketed by state.

    Matching is O(rows x patterns) — 6,123 facilities against ~600
    patterns. Compiling inside the loop leaned on ``re``'s 512-entry
    cache, which thrashes at this pattern count and cost ~8s per cold
    page render; precompiling and pre-bucketing by state brings it under
    a second.
    """
    unscoped: List[_Compiled] = []
    by_state: Dict[str, List[_Compiled]] = {}
    for sysdef in SYSTEM_REGISTRY:
        for pattern in sysdef.patterns:
            scope, body = _split_pattern(pattern)
            entry = _Compiled(
                sysdef=sysdef,
                raw=pattern,
                regex=_compile_pattern(body),
                scope=scope or sysdef.states,
                specificity=len(body.lstrip("^")),
            )
            if entry.scope:
                for st in entry.scope:
                    by_state.setdefault(st, []).append(entry)
            else:
                unscoped.append(entry)
    return tuple(unscoped), {k: tuple(v) for k, v in by_state.items()}


_UNSCOPED_PATTERNS, _STATE_PATTERNS = _build_index()

_EXCLUDE_INDEX: Dict[str, Tuple[Any, ...]] = {
    s.system_id: tuple(_compile_pattern(x) for x in s.exclude)
    for s in SYSTEM_REGISTRY if s.exclude
}


def match_system(name: Any, state: Any = None) -> Tuple[Optional[SystemDef], str]:
    """Resolve one facility to a :class:`SystemDef`.

    Returns ``(system_def, matched_pattern)``, or ``(None, "")`` when the
    name carries no system brand. Longest matched pattern wins, so a
    facility matching both ``^MERCY`` (Mercy MO) and
    ``^MERCY HEALTH MUSKEGON`` (Trinity) resolves to Trinity — the more
    specific claim is the more trustworthy one. State-scoped entries win
    ties against unscoped ones for the same reason.
    """
    norm = normalize_name(name)
    if not norm:
        return None, ""
    st = str(state or "").upper().strip()
    best: Optional[SystemDef] = None
    best_pattern = ""
    best_key: Tuple[int, int] = (-1, -1)
    for entry in _STATE_PATTERNS.get(st, ()) + _UNSCOPED_PATTERNS:
        key = (entry.specificity, 1 if entry.scope else 0)
        if key <= best_key:
            continue
        if not entry.regex.search(norm):
            continue
        excludes = _EXCLUDE_INDEX.get(entry.sysdef.system_id)
        if excludes and any(x.search(norm) for x in excludes):
            continue
        best, best_pattern, best_key = entry.sysdef, entry.raw, key
    return best, best_pattern


# ── Behavioral detection ───────────────────────────────────────────

# Name signals that read as behavioral to a partner screening the space
# even when the CCN range says otherwise (a psych hospital filed under a
# general CCN, or a rehab CCN carrying a BH brand). "BH " is included
# because HCRIS abbreviates it that way ("CORNERSTONE BH EL DORADO").
_BEHAVIORAL_NAME_RE = re.compile(
    r"(?<![A-Z0-9])(?:BEHAVIORAL|PSYCHIATRIC|PSYCH|MENTAL HEALTH|BH)(?![A-Z0-9])"
)


def _behavioral_series(names: pd.Series, types: pd.Series) -> pd.Series:
    """True where a facility is behavioral by CCN range **or** by name."""
    by_ccn = types.eq("psychiatric")
    by_name = names.map(normalize_name).str.contains(_BEHAVIORAL_NAME_RE, na=False)
    return (by_ccn | by_name).fillna(False)


# ── Assignment over the universe ───────────────────────────────────

_SYSTEM_BY_ID: Dict[str, SystemDef] = {s.system_id: s for s in SYSTEM_REGISTRY}

UNMAPPED_ID = "_unmapped"
UNMAPPED_NAME = "Independent / Unmapped"


def registry_size() -> int:
    """Number of systems currently in the registry."""
    return len(SYSTEM_REGISTRY)


def get_system(system_id: str) -> Optional[SystemDef]:
    return _SYSTEM_BY_ID.get(str(system_id or ""))


def assign_systems(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Return the hospital universe with system + type columns attached.

    Added columns: ``system_id``, ``system_name``, ``system_kind``,
    ``system_focus``, ``system_match`` (the pattern that fired — the
    audit trail for every count on the page), ``facility_type``,
    ``facility_type_label``, ``is_behavioral``.

    Passing ``df=None`` reads the bundled universe through the process
    cache; the returned frame is always a copy, so callers may mutate.
    """
    if df is None:
        return _assigned_cached().copy()
    return _assign_universe(df)


def _assign_universe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        for col in ("system_id", "system_name", "system_kind", "system_focus",
                    "system_match", "facility_type", "facility_type_label"):
            out[col] = pd.Series(dtype=object)
        out["is_behavioral"] = pd.Series(dtype=bool)
        return out

    names = out["name"] if "name" in out.columns else pd.Series([""] * len(out), index=out.index)
    states = out["state"] if "state" in out.columns else pd.Series([""] * len(out), index=out.index)
    ccns = out["ccn"] if "ccn" in out.columns else pd.Series([""] * len(out), index=out.index)

    matches = [match_system(n, s) for n, s in zip(names, states)]
    out["system_id"] = [m[0].system_id if m[0] else UNMAPPED_ID for m in matches]
    out["system_name"] = [m[0].name if m[0] else UNMAPPED_NAME for m in matches]
    out["system_kind"] = [m[0].kind if m[0] else "" for m in matches]
    out["system_focus"] = [m[0].focus if m[0] else "" for m in matches]
    out["system_match"] = [m[1] for m in matches]

    types = _classify_series(ccns, names)
    out["facility_type"] = types
    out["facility_type_label"] = types.map(lambda t: TYPE_DISPLAY.get(t, "Other"))
    out["is_behavioral"] = _behavioral_series(names, types)
    return out


@lru_cache(maxsize=1)
def _assigned_cached() -> pd.DataFrame:
    """Assignment over the bundled universe, computed once per process.

    The page hits this on every render (master table, roster drill-down,
    candidate clusters); the bundled HCRIS extract only changes on a data
    refresh, so recomputing per request was pure waste.
    """
    return _assign_universe(_get_latest_per_ccn())


# ── Rollup ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SystemRollup:
    """One row of the master mapping — a system and what it operates."""

    system_id: str
    system_name: str
    kind: str
    focus: str
    hq_state: str
    hospitals: int
    beds: float
    net_patient_revenue: float
    states: Tuple[str, ...]
    type_counts: Dict[str, int]
    behavioral_hospitals: int
    note: str = ""

    @property
    def state_count(self) -> int:
        return len(self.states)

    @property
    def behavioral_share(self) -> float:
        """Share of the system's facilities that are behavioral (0–1)."""
        return (self.behavioral_hospitals / self.hospitals) if self.hospitals else 0.0

    @property
    def avg_beds(self) -> float:
        return (self.beds / self.hospitals) if self.hospitals else 0.0

    def type_count(self, label: str) -> int:
        return int(self.type_counts.get(label, 0))


@dataclass(frozen=True)
class CandidateCluster:
    """An unmapped name family that looks like a system we don't carry.

    Surfaced so the registry has a visible backlog instead of an
    invisible one: two or more unmapped facilities sharing a two-word
    name stem in the same state is usually a real local system.
    """

    stem: str
    state: str
    hospitals: int
    beds: float
    examples: Tuple[str, ...]


@dataclass(frozen=True)
class HealthSystemMap:
    """The whole master mapping — systems, coverage, and the long tail."""

    systems: Tuple[SystemRollup, ...]
    unmapped: SystemRollup
    total_hospitals: int
    total_beds: float
    mapped_hospitals: int
    total_behavioral: int
    states_covered: int
    type_totals: Dict[str, int]
    candidates: Tuple[CandidateCluster, ...] = ()

    @property
    def system_count(self) -> int:
        return len(self.systems)

    @property
    def coverage_pct(self) -> float:
        """Share of the universe assigned to a named system (0–100)."""
        if not self.total_hospitals:
            return 0.0
        return self.mapped_hospitals / self.total_hospitals * 100.0

    @property
    def multi_state_systems(self) -> int:
        return sum(1 for s in self.systems if s.state_count > 1)

    @property
    def behavioral_systems(self) -> int:
        """Systems that operate at least one behavioral facility."""
        return sum(1 for s in self.systems if s.behavioral_hospitals > 0)


def _rollup_group(
    system_id: str,
    system_name: str,
    kind: str,
    focus: str,
    hq_state: str,
    note: str,
    group: pd.DataFrame,
) -> SystemRollup:
    beds = float(pd.to_numeric(group.get("beds"), errors="coerce").fillna(0).sum())
    npr = float(pd.to_numeric(group.get("net_patient_revenue"), errors="coerce").fillna(0).sum())
    states = tuple(sorted({str(s).upper() for s in group.get("state", []) if str(s).strip()}))
    counts = group["facility_type"].value_counts().to_dict() if "facility_type" in group else {}
    type_counts = {label: int(counts.get(label, 0)) for label in TYPE_LABELS}
    behavioral = int(group["is_behavioral"].sum()) if "is_behavioral" in group else 0
    return SystemRollup(
        system_id=system_id,
        system_name=system_name,
        kind=kind,
        focus=focus,
        hq_state=hq_state,
        hospitals=len(group),
        beds=beds,
        net_patient_revenue=npr,
        states=states,
        type_counts=type_counts,
        behavioral_hospitals=behavioral,
        note=note,
    )


_STOP_STEM_WORDS = frozenset({
    "THE", "OF", "AND", "AT", "FOR", "A", "AN",
})


def candidate_clusters(
    df: Optional[pd.DataFrame] = None,
    *,
    min_hospitals: int = 2,
    limit: int = 40,
) -> List[CandidateCluster]:
    """Unmapped name families that look like systems the registry misses.

    Groups unmapped facilities by (first two meaningful name tokens,
    state). This is the maintenance queue for :data:`SYSTEM_REGISTRY` —
    it is deliberately *not* used to assign systems, because a shared
    name stem is evidence of a candidate, not proof of ownership.
    """
    assigned = assign_systems(df)
    rest = assigned[assigned["system_id"] == UNMAPPED_ID]
    if rest.empty:
        return []
    stems: List[str] = []
    for raw in rest["name"]:
        toks = [t for t in normalize_name(raw).split() if t not in _STOP_STEM_WORDS]
        stems.append(" ".join(toks[:2]) if len(toks) >= 2 else (toks[0] if toks else ""))
    rest = rest.assign(_stem=stems)
    rest = rest[rest["_stem"].astype(bool)]
    out: List[CandidateCluster] = []
    for (stem, state), group in rest.groupby(["_stem", "state"], sort=False):
        if len(group) < min_hospitals:
            continue
        out.append(CandidateCluster(
            stem=str(stem),
            state=str(state),
            hospitals=len(group),
            beds=float(pd.to_numeric(group["beds"], errors="coerce").fillna(0).sum()),
            examples=tuple(str(x) for x in group["name"].head(3)),
        ))
    out.sort(key=lambda c: (-c.hospitals, -c.beds, c.stem))
    return out[:limit]


def build_system_map(df: Optional[pd.DataFrame] = None) -> HealthSystemMap:
    """Roll the assigned universe up to one row per health system."""
    assigned = assign_systems(df)
    if assigned.empty:
        empty = SystemRollup(UNMAPPED_ID, UNMAPPED_NAME, "", "", "", 0, 0.0, 0.0,
                             (), {label: 0 for label in TYPE_LABELS}, 0)
        return HealthSystemMap((), empty, 0, 0.0, 0, 0, 0,
                               {label: 0 for label in TYPE_LABELS})

    rollups: List[SystemRollup] = []
    unmapped: Optional[SystemRollup] = None
    for system_id, group in assigned.groupby("system_id", sort=False):
        sysdef = _SYSTEM_BY_ID.get(str(system_id))
        if sysdef is None:
            unmapped = _rollup_group(UNMAPPED_ID, UNMAPPED_NAME, "", "", "",
                                     "", group)
            continue
        rollups.append(_rollup_group(
            sysdef.system_id, sysdef.name, sysdef.kind, sysdef.focus,
            sysdef.hq_state, sysdef.note, group,
        ))
    rollups.sort(key=lambda s: (-s.hospitals, -s.beds, s.system_name))

    if unmapped is None:
        unmapped = SystemRollup(UNMAPPED_ID, UNMAPPED_NAME, "", "", "", 0, 0.0,
                                0.0, (), {label: 0 for label in TYPE_LABELS}, 0)

    counts = assigned["facility_type"].value_counts().to_dict()
    type_totals = {label: int(counts.get(label, 0)) for label in TYPE_LABELS}
    states_covered = len({str(s).upper() for s in assigned["state"] if str(s).strip()})

    return HealthSystemMap(
        systems=tuple(rollups),
        unmapped=unmapped,
        total_hospitals=len(assigned),
        total_beds=float(pd.to_numeric(assigned["beds"], errors="coerce").fillna(0).sum()),
        mapped_hospitals=int(len(assigned) - unmapped.hospitals),
        total_behavioral=int(assigned["is_behavioral"].sum()),
        states_covered=states_covered,
        type_totals=type_totals,
        candidates=tuple(candidate_clusters(df)),
    )


@lru_cache(maxsize=1)
def _cached_map() -> HealthSystemMap:
    """Cached rollup over the bundled universe.

    The rollup walks 6,123 rows × ~180 registry entries; at ~0.5s that is
    too slow to redo on every page render, and the underlying HCRIS
    extract only changes on a data refresh.
    """
    return build_system_map(None)


def get_system_map(df: Optional[pd.DataFrame] = None) -> HealthSystemMap:
    """Rollup for the page. Uses the cache when reading the bundled universe."""
    if df is None:
        return _cached_map()
    return build_system_map(df)


def system_hospitals(
    system_id: str,
    df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Facility roster for one system, largest first."""
    assigned = assign_systems(df)
    rows = assigned[assigned["system_id"] == str(system_id)]
    if rows.empty:
        return rows
    beds = pd.to_numeric(rows["beds"], errors="coerce").fillna(0)
    return rows.assign(_beds=beds).sort_values("_beds", ascending=False).drop(columns="_beds")


def _clear_cache() -> None:
    """Test hook — drop the memoized assignment + rollup."""
    _assigned_cached.cache_clear()
    _cached_map.cache_clear()
