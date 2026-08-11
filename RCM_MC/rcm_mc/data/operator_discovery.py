"""Multi-facility operators the system registry does not carry.

The gap this closes
-------------------
33,998 operating certified facilities reach no health system — 70% of
the register. They are not evenly spread: 29,276 of them are SNFs, home
health agencies and hospices, and post-acute is where the sponsor money
has gone for a decade. The ownership graph cannot help, because it works
from NPIs and only 60 of those 33,998 facilities carry one in the
bundled extracts.

What they do carry is a name and a CMS ownership type, and that turns
out to be enough.

Why exact names, and not the stem
---------------------------------
:func:`health_systems.candidate_clusters` already groups unmapped
facilities by their first two name tokens within a single state. That
shape cannot see the operators here, for two reasons. Multi-state is the
normal case — Caretenders runs 20 agencies across seven states, and a
state-scoped grouping sees seven unrelated pairs. And a two-token stem
is what manufactures ``GOOD SAMARITAN`` and ``SAINT JOSEPH`` as
"systems", which is the false-positive family this repo has already been
burned by twice.

So the grouping key here is the *whole* normalised name, less its legal
form: ``LIBERTY HOME CARE`` and ``LIBERTY HOME CARE LLC`` are one
operator that CMS certified under two spellings, and keeping them apart
reports a 7 and a 6 where a 13 exists. Beyond that suffix nothing is
trimmed. It is the strictest key available, it costs recall (a chain
that renames a branch splits in two), and after the prefix-matching
incidents that is the trade worth making.

What ownership type does, and what it does not
----------------------------------------------
Exact names alone are not proof. Eight hospitals named MEMORIAL HOSPITAL
across seven states are eight unrelated hospitals; twenty agencies named
CARETENDERS across seven states are one company.

Ownership type separates *those* two, structurally rather than
linguistically: a real operator files one ownership structure because it
is one, while facilities that merely share a name each file whatever
they independently are. MEMORIAL HOSPITAL spans four ownership families
and is refused; CARETENDERS is unanimously proprietary and is not.

**But the test is necessary, not sufficient, and the first cut of this
module claimed otherwise.** It said every classic collision family falls
out. That is false, and the counter-examples are the same family the
claim was about:

===============================  ===  ======  ==========  ============
group                              n  states  agreement   verdict
===============================  ===  ======  ==========  ============
SAINT FRANCIS HOSPITAL             7       7       1.00   accepted
SAINT MARY MEDICAL CENTER          6       4       1.00   accepted
SAINT LUKES HOSPITAL               4       4       1.00   accepted
MERCY HOSPITAL                     4       4       1.00   accepted
WASHINGTON COUNTY HOSPITAL         4       4       1.00   accepted
===============================  ===  ======  ==========  ============

Every Catholic hospital files "Voluntary non-profit - Church" and every
county hospital files "Government - Local", so agreement is unanimous
and carries no information whatsoever. SAINT LUKES HOSPITAL spanning
MN/NC/ND/OH is literally the UnityPoint collision from the second
shipped incident. The original test passed only because it asserted the
four families that had already been eyeballed — which is how a test
confirms the belief that produced it instead of checking it.

So the grade is separate from the filter
----------------------------------------
``is_confident`` answers "could these be one company at all" and rests
on ownership agreement. ``evidence_grade`` answers "does anything argue
against it", and only two things measurably do:

* the registry already maps this exact key to more than one system —
  ground truth on disk, and it refutes nine groups outright;
* the group is multi-state and acute-class — the naming tradition
  above, which the ownership test cannot see. All 43 such groups in
  this data are collisions on inspection, and not one is a real chain.

``distinct_sites`` is reported beside them, because 152 "two-facility"
groups are one address holding a home-health and a hospice licence.
That is one company — the grade is right — but it is one office, not a
two-site chain, and a reader sizing it needs to see which.

Name distinctiveness is reported and never enforced. A name whose
rarest token is common across the register (``AT HOME HEALTHCARE``) is
likelier a description than a brand — but ``PATIENT CARE`` is a real
company, and silently dropping it would hide a true operator to avoid
an obvious-on-inspection false one. The reviewer weighs it.

This is a queue, not a mapping
------------------------------
Nothing here writes ``system_id``. A strong group is a *candidate* —
evidence that some operator exists, none of what it is called on a cap
table. Promoting one into :data:`health_systems.SYSTEM_REGISTRY` is a
human edit, the same way
:func:`parent_resolution.ownership_disagreements` produces registry
edits rather than corrections applied in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .health_systems import UNMAPPED_ID, normalize_name

#: Share of a group that must agree on one ownership family before the
#: group is called confident. Set at four in five rather than unanimity
#: because a genuine chain does acquire the odd facility without
#: re-filing its ownership type, and CMS's own vocabulary drifts between
#: the SNF, HHA and hospice files.
MIN_OWNERSHIP_AGREEMENT = 0.80

#: Two facilities is a real signal when the name is distinctive and the
#: ownership agrees. It is also where most of the noise lives, so the
#: default is the honest floor and callers raise it to rank.
MIN_FACILITIES = 2

OPERATOR_COLUMNS: Tuple[str, ...] = (
    "operator_name", "facilities", "distinct_sites", "states", "state_list",
    "classes", "class_list", "ownership_family", "ownership_agreement",
    "name_distinctiveness", "is_confident", "evidence_grade", "weak_reason",
    "ccns",
)

#: CMS spells ownership differently in every file it publishes —
#: ``PROPRIETARY``, ``Proprietary``, ``For-Profit``, ``For profit -
#: Corporation``, ``For profit - Limited Liability company``. Grouping
#: on the raw string would score a chain that files two spellings of the
#: same thing as a disagreement, which is the opposite of the truth.
_OWNERSHIP_FAMILIES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    # Government first: "Government - Hospital District or Authority"
    # also contains none of the for-profit markers, but a local
    # government authority is not a proprietary corporation and the
    # order is what guarantees that.
    ("government", ("GOVERNMENT", "STATE", "COUNTY", "CITY", "MUNICIPAL",
                    "TRIBAL", "FEDERAL", "VETERAN", "DISTRICT")),
    ("nonprofit", ("NON PROFIT", "NON-PROFIT", "NONPROFIT", "VOLUNTARY",
                   "CHURCH", "RELIGIOUS", "CHARITABLE")),
    ("forprofit", ("PROPRIETARY", "FOR PROFIT", "FOR-PROFIT", "PARTNERSHIP",
                   "CORPORATION", "LIMITED LIABILITY", "INDIVIDUAL")),
    ("physician", ("PHYSICIAN",)),
)


#: Trailing tokens that name a legal form rather than a company. CMS
#: files carry both "LIBERTY HOME CARE" and "LIBERTY HOME CARE LLC" as
#: separate certifications of one operator, and grouping on the raw
#: normalised name splits it into a 7 and a 6 that each look like a
#: smaller company than the 13 that exists.
#:
#: ``CO`` and ``PA`` are deliberately absent even though both are real
#: legal forms. In this register they far more often end a place name —
#: ADVANCED CARE HOSPITAL OF WHITE **CO** is White County, ANGELS OF
#: CARE OF **PA** is Pennsylvania — and stripping them rewrites the
#: facility's identity. Keeping both costs two facilities out of 3,917.
_LEGAL_FORMS = frozenset({
    "INC", "INCORPORATED", "LLC", "LLP", "LP", "LTD", "CORP",
    "CORPORATION", "COMPANY", "PLLC", "PC", "PLC",
})


def _register() -> pd.DataFrame:
    """The whole certified register, from the memoized accessor.

    ``get_crosswalk`` rather than ``build_crosswalk``: the uncached build
    is 1.5 seconds over 48,510 rows, and the page panel asks for the
    register twice. Two rebuilds per render is three seconds of a
    partner's page load spent recomputing a frame that has not changed.
    """
    from .provider_crosswalk import SCOPE_ALL, get_crosswalk

    return get_crosswalk(scope=SCOPE_ALL)


def operator_key(name: Any) -> str:
    """The grouping key: a normalised name with its legal form removed.

    Stripped from the tail only, and repeatedly, because "FOO CARE LTD
    LLC" occurs. Position matters: a legal-form token is only a legal
    form at the end, and stripping one from the middle would take the
    CORP out of CORPUS CHRISTI.

    Never strips a name down to nothing: a facility certified as "LLC"
    keeps that as its key rather than joining a bucket of every other
    unnameable row.
    """
    tokens = normalize_name(name).split()
    while len(tokens) > 1 and tokens[-1] in _LEGAL_FORMS:
        tokens.pop()
    return " ".join(tokens)


def ownership_family(raw: Any) -> str:
    """Collapse a CMS ownership string to one of four families.

    Returns ``""`` for blanks and for CMS's ``-`` placeholder, which is
    not a family but an absence — counting it as one would let a group
    of facilities that all declined to answer look unanimous.
    """
    text = str(raw or "").strip().upper()
    if not text or text in ("-", "OTHER", "NOT AVAILABLE", "UNKNOWN"):
        return ""
    for family, markers in _OWNERSHIP_FAMILIES:
        if any(marker in text for marker in markers):
            return family
    return ""


@dataclass(frozen=True)
class DiscoveredOperator:
    """A group of facilities that look like one company."""

    name: str
    facilities: int
    states: Tuple[str, ...]
    classes: Tuple[str, ...]
    ownership_family: str
    ownership_agreement: float
    name_distinctiveness: float
    ccns: Tuple[str, ...]
    #: Distinct street addresses among the members. A "12-facility"
    #: group at one address is one office holding twelve certifications,
    #: not a twelve-site chain, and a reader sizing an acquisition needs
    #: to see which they are looking at.
    distinct_sites: int = 0
    #: Empty when nothing argues against the group. Set to the reason
    #: when something does — see :func:`_weak_reason`.
    weak_reason: str = ""

    @property
    def is_confident(self) -> bool:
        """Could these facilities be one company at all.

        Ownership agreement is a *necessary* test, not a sufficient one:
        it removes groups that provably cannot be one company, and says
        nothing about whether the rest are. See ``evidence_grade`` for
        the part that carries confidence.

        A single-state group is exempt. CMS publishes home health,
        hospice and SNF ownership in separate files that disagree about
        the same building — Weirton Medical Center's hospital, IRF and
        SNF file three different structures — so within one state an
        exact shared name outweighs a filing artefact.
        """
        if len(self.states) <= 1:
            return True
        return bool(self.ownership_family) and (
            self.ownership_agreement >= MIN_OWNERSHIP_AGREEMENT)

    @property
    def evidence_grade(self) -> str:
        """``strong`` unless something concrete argues against it."""
        return "weak" if self.weak_reason else "strong"

    @property
    def is_multi_state(self) -> bool:
        """Multi-state is corroboration, not a requirement.

        Millers Merry Manor runs twelve nursing homes in Indiana and
        nowhere else, and it is as real an operator as any of the
        seven-state agencies.
        """
        return len(self.states) > 1

    @property
    def is_multi_site(self) -> bool:
        return self.distinct_sites > 1


def _document_frequency(names: List[str]) -> Dict[str, float]:
    """Token -> the share of all facility names that contain it.

    Computed over the *whole* register rather than the unmapped subset.
    A token's rarity is a fact about healthcare naming, and measuring it
    only among the facilities that failed to match would make every
    token look rarer than it is.
    """
    total = len(names) or 1
    counts: Dict[str, int] = {}
    for name in names:
        for token in set(name.split()):
            counts[token] = counts.get(token, 0) + 1
    return {token: count / total for token, count in counts.items()}


def _distinctiveness(name: str, frequency: Dict[str, float]) -> float:
    """How unusual this name's rarest meaningful token is.

    Reported, never enforced — see the module docstring. Short tokens
    are skipped because "OF" and "AT" appear everywhere and would put
    every name at the same floor.
    """
    tokens = [t for t in name.split() if len(t) > 2]
    if not tokens:
        return 1.0
    return min(frequency.get(t, 0.0) for t in tokens)


#: Classes where a shared name is weak evidence of shared ownership.
#: American hospitals are named for patron saints, benefactors and
#: counties, and always have been — SAINT FRANCIS HOSPITAL exists in
#: seven states and WASHINGTON COUNTY HOSPITAL in four, none of them
#: related. Post-acute agencies are named by marketing departments.
_ACUTE_CLASSES = frozenset({"hospital", "irf", "ltch"})


def _site_key(record: Dict[str, Any]) -> Tuple[str, str]:
    """Street and city, flattened enough to tell two sites apart.

    Not an address normaliser and not trying to be — it only has to
    answer "is this the same building", so punctuation and case go and
    nothing else does. Under-merging here costs a group one apparent
    site; over-merging would claim a chain is one office.
    """
    def flatten(value: Any) -> str:
        return "".join(c for c in str(value or "").upper()
                       if c.isalnum() or c == " ").strip()

    return flatten(record.get("street")), flatten(record.get("city"))


def _registered_owners(crosswalk: pd.DataFrame) -> Dict[str, set]:
    """Operator key -> the registered systems that already hold it.

    The one piece of ground truth on disk. If a key is carried by
    facilities the registry has already mapped to *two different*
    systems, then that key is provably not one owner, whatever the
    unmapped facilities under it agree about.
    """
    owners: Dict[str, set] = {}
    if crosswalk.empty or not {"system_id", "name"} <= set(crosswalk.columns):
        # Both columns or nothing: zipping a present column against a
        # missing one's empty default yields no pairs at all, and the
        # probe would silently find no contrary evidence anywhere.
        return owners
    for name, system in zip(crosswalk["name"], crosswalk["system_id"],
                            strict=True):
        text = str(system or "")
        if not text or text == UNMAPPED_ID:
            continue
        key = operator_key(name)
        if key:
            owners.setdefault(key, set()).add(text)
    return owners


def _weak_reason(name: str, states: Tuple[str, ...], classes: Tuple[str, ...],
                 owners: Dict[str, set]) -> str:
    """What argues against this group being one company. "" if nothing.

    Two things do, and only two, because these are the two that could be
    measured rather than asserted.

    The first is contrary evidence: the registry itself already maps
    this exact key to more than one system. SAINT MARYS HOSPITAL is
    carried by Bon Secours, CommonSpirit, Mayo, MedStar and SSM, so the
    unmapped SAINT MARYS HOSPITALs are not a discovery, they are five
    more of the same collision. Nine groups are refuted this way.

    The second is the shape of that collision generalised. Hospitals
    sharing a name across state lines are the family this repo has
    twice shipped a bad matcher into, and the ownership test does not
    catch them: every Catholic hospital files "Voluntary non-profit -
    Church" and every county hospital files "Government - Local", so
    agreement is unanimous and carries no information at all. All 43
    multi-state acute-class groups in this data are collisions on
    inspection; not one is a real chain.
    """
    if len(owners.get(name, ())) > 1:
        return (f"the registry already maps this name to "
                f"{len(owners[name])} different systems")
    if len(states) > 1 and (set(classes) & _ACUTE_CLASSES):
        return ("hospitals in more than one state share a name far more "
                "often than an owner")
    return ""


def _unmapped_operating(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """The facilities in play: certified, still operating, no system.

    Closed facilities are excluded because a chain that no longer
    operates is not an acquisition target, and they would inflate every
    group's count with beds nobody can buy.
    """
    if crosswalk.empty or "name" not in crosswalk.columns:
        return crosswalk.iloc[0:0]
    system = crosswalk.get("system_id")
    if system is None:
        unmapped = pd.Series(True, index=crosswalk.index)
    else:
        text = system.astype(str)
        unmapped = text.eq("") | text.eq(UNMAPPED_ID)
    operating = crosswalk.get("is_operating")
    if operating is None:
        live = pd.Series(True, index=crosswalk.index)
    else:
        live = operating.astype(str).str.lower().isin(("true", "1"))
    return crosswalk[unmapped & live]


def discover_operators(
    crosswalk: Optional[pd.DataFrame] = None,
    *,
    min_facilities: int = MIN_FACILITIES,
    confident_only: bool = False,
) -> List[DiscoveredOperator]:
    """Groups of unmapped facilities that share an exact name.

    ``confident_only`` filters to the groups whose ownership agrees. It
    is off by default so that the rejected groups stay visible: the ones
    that fail are the ones worth reading, because a large group with
    four ownership families is either a name collision or a chain in the
    middle of being sold, and only a human can tell which.

    Against the bundled register the answer is memoized. The pass is
    seven seconds over 48,510 rows — normalising every name twice and
    grouping 33,998 records — and the page panel and the CSV route both
    ask for it on every request. Passing an explicit ``crosswalk``
    bypasses the cache, because then the input is the caller's and not
    the fixed one on disk.
    """
    if crosswalk is None:
        groups = list(_cached_discovery(min_facilities))
    else:
        groups = _discover(crosswalk, min_facilities)
    if confident_only:
        return [o for o in groups if o.is_confident]
    return groups


@lru_cache(maxsize=4)
def _cached_discovery(min_facilities: int) -> Tuple[DiscoveredOperator, ...]:
    """Memoized over the bundled register, keyed on the size floor.

    A tuple of frozen dataclasses rather than a list, so a caller that
    mutates what it gets back cannot corrupt the cache for the next
    request.
    """
    return tuple(_discover(_register(), min_facilities))


def _discover(crosswalk: pd.DataFrame,
              min_facilities: int) -> List[DiscoveredOperator]:
    """The pass itself, over whichever register it is handed."""
    frequency = _document_frequency(
        [operator_key(n) for n in crosswalk.get(
            "name", pd.Series(dtype=str)).astype(str)])
    owners = _registered_owners(crosswalk)

    rows = _unmapped_operating(crosswalk)
    if rows.empty:
        return []

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in rows.to_dict("records"):
        name = operator_key(record.get("name"))
        if name:
            grouped.setdefault(name, []).append(record)

    out: List[DiscoveredOperator] = []
    for name, members in grouped.items():
        if len(members) < min_facilities:
            continue
        families = [f for f in (ownership_family(m.get("cms_ownership"))
                                for m in members) if f]
        if families:
            counts: Dict[str, int] = {}
            for family in families:
                counts[family] = counts.get(family, 0) + 1
            # Ties break on the family name so a rebuild does not
            # reclassify a group.
            top = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
            family, agreement = top[0], top[1] / len(families)
        else:
            family, agreement = "", 0.0
        states = tuple(sorted({str(m.get("state") or "") for m in members}
                              - {""}))
        classes = tuple(sorted({str(m.get("provider_class") or "")
                                for m in members} - {""}))
        operator = DiscoveredOperator(
            name=name,
            facilities=len(members),
            states=states,
            classes=classes,
            ownership_family=family,
            ownership_agreement=agreement,
            name_distinctiveness=_distinctiveness(name, frequency),
            ccns=tuple(sorted({str(m.get("ccn") or "") for m in members}
                              - {""})),
            distinct_sites=len({_site_key(m) for m in members}),
            weak_reason=_weak_reason(name, states, classes, owners),
        )
        out.append(operator)
    out.sort(key=lambda o: (-o.facilities, -o.ownership_agreement, o.name))
    return out


def discovered_operator_frame(
    crosswalk: Optional[pd.DataFrame] = None,
    *,
    min_facilities: int = MIN_FACILITIES,
    confident_only: bool = False,
) -> pd.DataFrame:
    """:func:`discover_operators` as the frame the export and page use."""
    operators = discover_operators(crosswalk, min_facilities=min_facilities,
                                   confident_only=confident_only)
    if not operators:
        return pd.DataFrame(columns=list(OPERATOR_COLUMNS))
    return pd.DataFrame([{
        "operator_name": o.name,
        "facilities": o.facilities,
        "distinct_sites": o.distinct_sites,
        "states": len(o.states),
        "state_list": "|".join(o.states),
        "classes": len(o.classes),
        "class_list": "|".join(o.classes),
        "ownership_family": o.ownership_family,
        "ownership_agreement": round(o.ownership_agreement, 4),
        "name_distinctiveness": round(o.name_distinctiveness, 6),
        "is_confident": 1 if o.is_confident else 0,
        "evidence_grade": o.evidence_grade,
        "weak_reason": o.weak_reason,
        "ccns": "|".join(o.ccns),
    } for o in operators], columns=list(OPERATOR_COLUMNS))


def discovery_coverage(
    crosswalk: Optional[pd.DataFrame] = None, *,
    operators: Optional[List[DiscoveredOperator]] = None,
) -> Dict[str, Any]:
    """What the discovery pass found, and against what denominator.

    The denominator is the point twice over. "1,576 operators
    discovered" without "out of 33,998 unmapped facilities, of which
    3,981 are now in a named group" reads like the gap is closed when
    88% of it is not — and reporting the confident count without the
    strong one hides the 43 groups the evidence argues against.
    """
    if crosswalk is None:
        crosswalk = _register()
    rows = _unmapped_operating(crosswalk)
    if operators is None:
        operators = discover_operators(crosswalk)
    strong = [o for o in operators if o.is_confident
              and o.evidence_grade == "strong"]
    confident = [o for o in operators if o.is_confident]
    return {
        "unmapped_operating": len(rows),
        "candidate_groups": len(operators),
        "confident_groups": len(confident),
        "facilities_in_confident_groups": sum(o.facilities for o in confident),
        # The headline pair. Confident means "could be one company";
        # strong means "and nothing on disk argues against it". Reporting
        # only the first is how the patron-saint groups got counted as
        # discoveries in the first place.
        "strong_groups": len(strong),
        "facilities_in_strong_groups": sum(o.facilities for o in strong),
        "held_back_groups": len(confident) - len(strong),
        "multi_site_strong": sum(1 for o in strong if o.is_multi_site),
        "multi_state_confident": sum(1 for o in confident if o.is_multi_state),
        "largest": confident[0].name if confident else "",
        "by_class": _class_mix(confident),
    }


def _class_mix(operators: List[DiscoveredOperator]) -> Dict[str, int]:
    """Facilities in confident groups, by provider class.

    A group spanning home health and hospice counts in both, because it
    operates in both — the same multi-enrolment rule the taxonomy
    rollups use, and the same reason the numbers exceed the group count.
    """
    mix: Dict[str, int] = {}
    for operator in operators:
        for klass in operator.classes:
            mix[klass] = mix.get(klass, 0) + operator.facilities
    return dict(sorted(mix.items(), key=lambda kv: -kv[1]))
