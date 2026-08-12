"""Vetting a proposed registry entry before it can join the registry.

Why this exists
---------------
:data:`health_systems.SYSTEM_REGISTRY` grew from 382 entries to 896 in a
single sweep — one pass per state over every certified facility the
registry did not map, grouping them by the brand in their name. That
scale is only safe if nothing is taken on trust, because this repo has
shipped a bad name matcher three times: ``startswith("CHI")`` pulled
CHINLE and CHINESE HOSPITAL into CommonSpirit; a bare ``^TRINITY``
claimed UnityPoint's hospitals; and ``^HARBORVIEW`` with no state scope
gave fourteen Southeast nursing homes to a Seattle academic centre.

So the gate here answers one question mechanically: **what does this
pattern actually claim?** Not what its author believes it claims. It
compiles the pattern exactly as the matcher will, runs it against the
whole register, and reports the facilities it reaches. Everything else
is a rule over that answer.

The four refusals, and why each one is a refusal
------------------------------------------------
*It reaches a facility another system already holds.* The proposal is
not adding coverage, it is overwriting an answer somebody already
curated. In the sweep this refused a bare ``^SAINT`` that would have
taken 256 mapped facilities from Ascension, CommonSpirit, Mayo and
others.

*It claims nothing.* Almost always a typo in the pattern, and a dead
entry is a maintenance cost with no coverage behind it.

*It is a collision-family prefix with no state scope.* MEMORIAL, SAINT,
MERCY, COUNTY and the rest are how American facilities are named, not
who owns them. Scoped to a state they are usable; unscoped they are the
exact shape of all three prior incidents.

*Its identifier or display name is already taken.* Two entries under one
name make every system-level rollup double count.

Two layers, and why one is not enough
-------------------------------------
This gate is mechanical. It cannot tell that ``^BROOKDALE`` is wrong,
because the facility it collides with — BROOKDALE HOSPITAL MEDICAL
CENTER in Brooklyn, which belongs to One Brooklyn Health — is itself
unmapped, so the pattern is not taking anything from anybody. The
proposal passes here and is refused by the invariants in
``tests/test_health_system_lookup.py``, which assert over the resulting
register rather than over the proposal: no single-market system reaching
across the country, no two systems holding one name in one town, no unit
disagreeing with its parent hospital.

Both layers earned their place in the same sweep. The gate caught a bare
``^SAINT`` reaching 302 mapped facilities, which no invariant would have
seen because the proposal never landed. The invariants caught
``^BROOKDALE`` and ``HOSPICE OF THE VALLEY``, which the gate cleared.
Run both.

What it deliberately does not check
-----------------------------------
Whether the operator is real. No source on disk can settle that, and
pretending otherwise would be worse than admitting it — so a proposal
that passes this gate is *mechanically safe*, not *verified true*. Real
review still has to happen, and :func:`dedupe_by_claim` exists because
even careful reviewers propose the same operator twice: the sweep found
Caretenders four times and Medical Services of America under three
different identifiers, and merging them by name would have missed it
because the names differed. They are merged by the facilities they
claim instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .health_systems import (
    SYSTEM_REGISTRY, UNMAPPED_ID, _split_pattern, _UNBOUNDED_PATTERN_LEN,
    normalize_name,
)

#: Name families this register uses for places, patrons and descriptions
#: rather than for owners. A pattern starting with one of these is only
#: usable inside a state scope — SAINT FRANCIS HOSPITAL exists in seven
#: states and WASHINGTON COUNTY HOSPITAL in four, none of them related.
COLLISION_FAMILIES: Tuple[str, ...] = (
    "MEMORIAL", "COMMUNITY", "SAINT", "MERCY", "GOOD SAMARITAN",
    "GOOD SHEPHERD", "TRINITY", "PROVIDENCE", "BAPTIST", "METHODIST",
    "PRESBYTERIAN", "LUTHERAN", "COUNTY", "REGIONAL", "GENERAL",
    "CHILDRENS", "UNIVERSITY", "VALLEY", "HOLY",
)


@dataclass(frozen=True)
class Proposal:
    """A candidate :class:`health_systems.SystemDef`, not yet trusted."""

    system_id: str
    name: str
    patterns: Tuple[str, ...]
    states: Tuple[str, ...] = ()
    kind: str = ""
    focus: str = ""
    hq_state: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Proposal":
        return cls(
            system_id=str(raw.get("system_id") or ""),
            name=str(raw.get("name") or ""),
            patterns=tuple(raw.get("patterns") or ()),
            states=tuple(str(s).upper() for s in (raw.get("states") or ())),
            kind=str(raw.get("kind") or ""),
            focus=str(raw.get("focus") or ""),
            hq_state=str(raw.get("hq_state") or ""),
        )


@dataclass(frozen=True)
class Verdict:
    """What a proposal would actually do to the register."""

    proposal: Proposal
    #: (ccn, normalized name, state, currently-held-by, class) per hit.
    claims: Tuple[Tuple[str, str, str, str, str], ...] = ()
    #: Facilities the pattern reaches that another system already holds.
    conflicts: Tuple[Tuple[str, str], ...] = ()
    refusals: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.refusals

    @property
    def facilities(self) -> int:
        return len(self.claims)

    @property
    def states_reached(self) -> Tuple[str, ...]:
        return tuple(sorted({c[2] for c in self.claims if c[2]}))


def compile_pattern(raw: str) -> Tuple[Tuple[str, ...], Any]:
    """Compile a registry pattern the way the matcher will.

    Deliberately reuses ``_split_pattern`` and mirrors the length rule in
    ``_compile_pattern`` rather than approximating either. A gate that
    compiles differently from the matcher is worse than no gate: it
    would clear patterns that behave differently in production, which is
    precisely the failure it is supposed to prevent.
    """
    scope, body = _split_pattern(raw)
    core = body.lstrip("^").strip()
    if not core:
        return scope, re.compile(r"(?!)")
    prefix = "^" if body.startswith("^") else r"(?<![A-Z0-9])"
    suffix = "" if len(core) >= _UNBOUNDED_PATTERN_LEN else r"(?![A-Z0-9])"
    return scope, re.compile(prefix + re.escape(core) + suffix)


def _register_rows(crosswalk: Optional[pd.DataFrame]) -> List[Tuple[str, ...]]:
    if crosswalk is None:
        from .provider_crosswalk import SCOPE_ALL, get_crosswalk

        crosswalk = get_crosswalk(scope=SCOPE_ALL)
    if crosswalk.empty:
        return []

    def column(name: str) -> pd.Series:
        if name in crosswalk.columns:
            return crosswalk[name].astype(str)
        return pd.Series([""] * len(crosswalk), index=crosswalk.index)

    return list(zip(column("ccn"),
                    [normalize_name(n) for n in column("name")],
                    column("state"), column("system_id"),
                    column("provider_class"), strict=True))


def check(proposal: Proposal, crosswalk: Optional[pd.DataFrame] = None,
          *, taken_ids: Optional[set] = None,
          taken_names: Optional[set] = None) -> Verdict:
    """Run one proposal against the whole register.

    ``taken_ids`` and ``taken_names`` default to the live registry, and
    are parameters so a caller vetting a batch can add the entries it
    has already accepted — otherwise the second proposal of the same
    operator in one batch passes, and two entries ship under one name.
    """
    if taken_ids is None:
        taken_ids = {s.system_id for s in SYSTEM_REGISTRY}
    if taken_names is None:
        taken_names = {s.name.strip().lower() for s in SYSTEM_REGISTRY}

    refusals: List[str] = []
    if proposal.system_id in taken_ids:
        refusals.append(f"system_id {proposal.system_id!r} is already taken")
    if proposal.name.strip().lower() in taken_names:
        refusals.append(f"display name {proposal.name!r} is already taken")

    rows = _register_rows(crosswalk)
    claims: List[Tuple[str, str, str, str, str]] = []
    conflicts: List[Tuple[str, str]] = []
    seen: set = set()
    for raw in proposal.patterns:
        pattern_scope, regex = compile_pattern(raw)
        allowed = {s.upper() for s in pattern_scope} or set(proposal.states)
        core = _split_pattern(raw)[1].lstrip("^").strip()
        if not allowed and any(core.startswith(f) for f in COLLISION_FAMILIES):
            refusals.append(
                f"pattern {raw!r} opens with a collision family and has no "
                f"state scope")
        for ccn, name, state, held, klass in rows:
            if not regex.search(name):
                continue
            if allowed and state.upper() not in allowed:
                continue
            if ccn not in seen:
                seen.add(ccn)
                claims.append((ccn, name, state, held, klass))
            if held and held != UNMAPPED_ID:
                conflicts.append((ccn, held))

    if not claims:
        refusals.append("matches no facility in the register")
    if conflicts:
        holders = sorted({h for _, h in conflicts})
        refusals.append(
            f"reaches {len(conflicts)} facilities already held by "
            f"{', '.join(holders[:4])}")

    return Verdict(proposal=proposal, claims=tuple(claims),
                   conflicts=tuple(dict.fromkeys(conflicts)),
                   refusals=tuple(dict.fromkeys(refusals)))


def check_batch(proposals: Sequence[Proposal],
                crosswalk: Optional[pd.DataFrame] = None) -> List[Verdict]:
    """Vet a batch, accumulating accepted identifiers as it goes."""
    taken_ids = {s.system_id for s in SYSTEM_REGISTRY}
    taken_names = {s.name.strip().lower() for s in SYSTEM_REGISTRY}
    out: List[Verdict] = []
    for proposal in proposals:
        verdict = check(proposal, crosswalk, taken_ids=taken_ids,
                        taken_names=taken_names)
        if verdict.ok:
            taken_ids.add(proposal.system_id)
            taken_names.add(proposal.name.strip().lower())
        out.append(verdict)
    return out


def dedupe_by_claim(verdicts: Sequence[Verdict]) -> List[Verdict]:
    """Collapse proposals that are the same operator under other names.

    Merged on the facilities they claim, never on the name. A state-by-
    state sweep finds a multi-state operator once per state it touches,
    and the identifiers do not agree: Medical Services of America came
    back as ``msa_medi_home``, ``medi_home_health`` and
    ``medi_home_msa``. Name-based dedup misses all three; claim-based
    dedup catches them because they reach the same CCNs.

    The survivor of each group is the one reaching the most facilities,
    ties broken on the shorter identifier so a rerun picks the same one.
    """
    usable = [v for v in verdicts if v.ok and v.claims]
    parent: Dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    owner: Dict[str, int] = {}
    for i, verdict in enumerate(usable):
        find(i)
        for ccn, *_ in verdict.claims:
            if ccn in owner:
                union(i, owner[ccn])
            else:
                owner[ccn] = i

    groups: Dict[int, List[int]] = {}
    for i in range(len(usable)):
        groups.setdefault(find(i), []).append(i)
    winners = [usable[max(members,
                          key=lambda i: (usable[i].facilities,
                                         -len(usable[i].proposal.system_id)))]
               for members in groups.values()]
    winners.sort(key=lambda v: (-v.facilities, v.proposal.system_id))
    return winners


def render_system_def(proposal: Proposal, *, kind_const: str,
                      focus_const: str, comment: str = "") -> str:
    """The proposal as source text for ``health_systems.py``.

    Emitted rather than hand-typed because 515 entries is more than
    anyone transcribes without a mistake, and a mistyped pattern is
    invisible until it claims something it should not.
    """
    def quoted(value: Any) -> str:
        return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'

    def tup(values: Sequence[str]) -> str:
        values = list(values)
        if not values:
            return "()"
        if len(values) == 1:
            return f"({quoted(values[0])},)"
        return "(" + ", ".join(quoted(v) for v in values) + ")"

    lines = ["    SystemDef("]
    if comment:
        for line in comment.splitlines():
            lines.insert(0, f"    # {line}".rstrip())
    lines.append(f"        {quoted(proposal.system_id)}, "
                 f"{quoted(proposal.name)},")
    lines.append(f"        {kind_const}, {focus_const}, "
                 f"{quoted(proposal.hq_state)},")
    lines.append(f"        patterns={tup(proposal.patterns)},")
    if proposal.states:
        lines.append(f"        states={tup(proposal.states)},")
    lines.append("    ),")
    return "\n".join(lines)


def summarise(verdicts: Sequence[Verdict]) -> Dict[str, Any]:
    """Counts a reviewer needs before accepting a batch."""
    accepted = [v for v in verdicts if v.ok]
    refused = [v for v in verdicts if not v.ok]
    # Categorised, not verbatim: the reason strings carry identifiers
    # and counts, so grouping on the raw text gives one bucket per
    # refusal and tells a reviewer nothing about the shape of the batch.
    reasons: Dict[str, int] = {}
    for verdict in refused:
        for reason in verdict.refusals:
            if "already taken" in reason:
                key = "identifier or name already taken"
            elif "already held by" in reason:
                key = "would take facilities from another system"
            elif "collision family" in reason:
                key = "collision family with no state scope"
            elif "no facility" in reason:
                key = "matches nothing"
            else:
                key = "other"
            reasons[key] = reasons.get(key, 0) + 1
    return {
        "proposed": len(verdicts),
        "accepted": len(accepted),
        "refused": len(refused),
        "facilities_claimed": sum(v.facilities for v in accepted),
        "refusal_reasons": reasons,
    }
