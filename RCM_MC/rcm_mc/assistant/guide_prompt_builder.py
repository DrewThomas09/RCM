"""Strict read-only prompt builder for the local PEdesk Guide.

Turns a ``GuideContextPacket`` into a system prompt + a compacted
user prompt for a local model. The model is instructed to answer ONLY
from the supplied context and never to take actions. Nothing here calls
a model, mutates state, or runs diligence logic — it only formats text.
"""
from __future__ import annotations

import re
from typing import List

from .context.guide_context_packet import GuideContextPacket

# Visible chain-of-thought blocks some models emit; stripped before return.
_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)
_DANGLING_THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*\Z", re.IGNORECASE | re.DOTALL)
_REPETITIVE_PREAMBLE_RE = re.compile(
    r"^\s*(based on (the )?(provided |supplied |given )?context[,:]?\s*)",
    re.IGNORECASE,
)

_OMITTED_NOTE = "Some context was omitted for length."

# The standard `intended_users` value applied by `_ctx()` to the 91%
# of pages that don't customise it. Used by the prompt builder to
# decide whether to emit an `Intended users:` clause (skipped when
# the value matches this default — the system prompt already implies
# the PE-deal-team audience).
_DEFAULT_INTENDED_USERS = [
    "PE deal team (partners, principals, associates).",
]


def _bullets(items: List[str], limit: int = 0) -> str:
    vals = [str(i).strip() for i in (items or []) if str(i).strip()]
    if limit and len(vals) > limit:
        vals = vals[:limit] + ["… (trimmed)"]
    return "\n".join(f"- {v}" for v in vals) if vals else "- (none documented)"


def _dot(value: str) -> str:
    """Strip trailing whitespace and any trailing ``.`` / ``;`` / ``,`` so
    callers can append their own period without producing a 'foo..' or
    'foo.;' artifact in the prompt. The registry content commonly ends in a
    period; the prompt templates also end clauses in a period — the two
    used to collide. Idempotent; safe on empty input."""
    v = (value or "").rstrip()
    while v and v[-1] in ".;,":
        v = v[:-1].rstrip()
    return v


def _policy_summary(packet: GuideContextPacket) -> str:
    pol = packet.read_only_policy or {}
    allowed = pol.get("allowed_behavior") or []
    disallowed = pol.get("disallowed_behavior") or []
    lines = [pol.get("identity", "PEdesk Guide is a read-only assistant.")]
    if allowed:
        lines.append("MAY: " + "; ".join(str(a) for a in allowed) + ".")
    if disallowed:
        lines.append("MUST NOT: " + "; ".join(str(d) for d in disallowed) + ".")
    if pol.get("default_uncertainty_message"):
        lines.append(
            "When unsure, say: \"" + str(pol["default_uncertainty_message"])
            + "\""
        )
    return "\n".join(lines)


def build_guide_system_prompt(packet: GuideContextPacket) -> str:
    """The behavioral contract + answer rules for the local model."""
    return (
        _policy_summary(packet)
        + "\n\n"
        "ANSWER RULES:\n"
        "1. Answer ONLY from the PEdesk Guide context provided in the user "
        "message. Do not use outside knowledge to fill gaps.\n"
        "2. If the context is insufficient, say so plainly — do not guess.\n"
        "3. Do not invent formulas. Do not invent data lineage or sources.\n"
        "4. Do not claim a page/number is IC-ready, validated, or real-time "
        "unless the context explicitly says so.\n"
        "5. Distinguish observed target data from estimates, benchmarks, "
        "demo/fixture data, and unknown data, exactly as the context labels "
        "them.\n"
        "6. You may explain pages, metrics, data sources, model intent, why a "
        "number matters, limitations, and related pages — and you may go "
        "further and ANALYZE: connect the provided context into an "
        "interpretation (what it implies for the deal/thesis, the key driver or "
        "risk, how a figure compares to its benchmark or caveat) and suggest "
        "what a diligence analyst would check next or which related PEdesk page "
        "to open. This interpretation is analysis, NOT a buy/sell/hold call "
        "(rule 7 still applies). Ground every claim in the provided context.\n"
        "7. You may NOT modify data, run models, change assumptions, create "
        "tasks, submit forms, send messages, create exports, or make final "
        "investment recommendations.\n"
        "8. Be concise and practical; use PE-diligence language but stay "
        "understandable.\n"
        "9. Do NOT expose chain-of-thought or internal reasoning. Do NOT emit "
        "<think> tags. Return only the final answer.\n"
        "10. If an 'Additional local Guide context (retrieved)' block is "
        "present, treat the current-page context as PRIMARY and those "
        "snippets as supporting reference (definitions, methodology, related "
        "sources). They are not this deal's data unless their own text says "
        "so. If retrieved context conflicts with the page context, say the "
        "source context needs review. When you use them, add a short plain-"
        "text line like: 'Guide context used: Metric Registry — Denial "
        "Rate.'\n"
        "11. If an 'On-screen figures' block is present, those are the exact "
        "values the user is currently looking at on this page. You MAY "
        "reference and analyze them (compare a figure to its benchmark or "
        "caveat, flag the driver/risk, note what's notable) — but treat them "
        "as DISPLAYED, not re-validated: they carry this page's data "
        "confidence, so never call them IC-ready, validated, or real-time "
        "unless the context says so, and never invent figures that aren't in "
        "that block. If an on-screen value looks inconsistent with the page's "
        "stated data confidence or a metric's caveat, say so plainly.\n\n"
        "ANSWER STYLE (how to write the answer):\n"
        "- Open with a direct 1-2 sentence answer to the exact question. Never "
        "open with filler such as 'Based on the provided context' or "
        "'According to the information given'.\n"
        "- Add short bullets only when they make the answer clearer; skip them "
        "for simple questions. Keep the whole answer tight — usually under 150 "
        "words — and never pad.\n"
        "- When it fits (explaining a metric, data source, or page), use these "
        "plain labels: What it means · Where it comes from · Why it matters · "
        "Caveat · Related PEdesk pages. Do not force this shape when it does "
        "not fit.\n"
        "- State confidence honestly in one short clause: if the context is "
        "thin, benchmarked, estimated, demo/fixture, or missing, say so rather "
        "than guessing.\n"
        "- Act like a sharp diligence analyst, not a glossary: after the direct "
        "answer, when it helps, add the 'so what' — the implication, the main "
        "driver or risk, and one concrete next step or related PEdesk page to "
        "check. If a figure you'd want isn't in the context, say what you'd "
        "need rather than inventing it.\n"
        "- When retrieved Guide context informed the answer, name the source "
        "title in-line (e.g. 'per the Metric Registry — Denial Rate')."
    )


def packet_to_prompt_context(
    packet: GuideContextPacket, max_chars: int = 12000
) -> str:
    """Render the packet into a compact context block for the prompt.

    Builds a full rendering first; if it exceeds ``max_chars`` it rebuilds
    a compact version (metric/source detail trimmed to labels) while always
    keeping limitations and missing_context_notes, and appends an omission
    note. A final hard truncation guards the cap.
    """
    full = _render_context(packet, compact=False)
    if len(full) <= max_chars:
        return full
    compact = _render_context(packet, compact=True)
    compact += "\n\n" + _OMITTED_NOTE
    if len(compact) > max_chars:
        compact = compact[: max_chars - len(_OMITTED_NOTE) - 2].rstrip() + (
            "\n" + _OMITTED_NOTE
        )
    return compact


def _render_context(packet: GuideContextPacket, compact: bool) -> str:
    pc = packet.page_context
    out: List[str] = []
    out.append("=== PEdesk Guide context ===")
    out.append(f"Route: {packet.normalized_route}")
    out.append(f"Context quality: {packet.context_quality}")
    if packet.fallback_message:
        out.append(f"Note: {packet.fallback_message}")

    if pc is not None:
        list_limit = 4 if compact else 0
        out.append(f"Page title: {pc.title}")
        out.append(f"Category: {pc.category.value}")
        out.append(f"Source confidence: {pc.source_confidence.value}")
        out.append(f"Data confidence: {pc.data_confidence.value}")
        # 52 PageContexts have short_description == primary_purpose (the
        # _BATCH7 / _BATCH8 loops set both to the same _sd literal). Emitting
        # both produces a wasted-context duplicate; collapse to one labelled
        # line when they match so the prompt stays tight without losing
        # information.
        sd = (pc.short_description or "").strip()
        pp = (pc.primary_purpose or "").strip()
        if sd and sd == pp:
            out.append(f"Page description / primary purpose: {sd}")
        else:
            out.append(f"Short description: {pc.short_description}")
            out.append(f"Primary purpose: {pc.primary_purpose}")
        out.append(f"Why it matters: {pc.why_it_matters}")
        # intended_users: the standard 91% of pages carry the default
        # "PE deal team (partners, principals, associates)." which the
        # system prompt already implies. Surface ONLY when the page
        # specifies a more targeted persona (e.g. /portfolio/monte-carlo
        # → "Partners and LP-reporting staff assessing fund-level risk.";
        # /ebitda-bridge → "Deal team underwriting an RCM value-creation
        # thesis."). Lets the Guide tailor answers for the few pages
        # whose audience is sharper than the default, without bloating
        # the prompt for the 91% default case.
        iu = list(pc.intended_users or [])
        if iu and iu != _DEFAULT_INTENDED_USERS:
            out.append(f"Intended users: {'; '.join(_dot(u) for u in iu)}.")
        if not compact:
            out.append("Inputs:\n" + _bullets(pc.inputs))
            out.append("Outputs:\n" + _bullets(pc.outputs))
            # model_logic_summary is the page-specific 'how does this
            # actually compute X?' description. PR #1235-#1244 drained
            # the NEEDS placeholder across all 360 pages, so every page
            # carries a real, page-specific computation description.
            # Skipped in compact mode and when truly empty (the
            # invariant test forbids _NEEDS so empty would be rare).
            mls = (pc.model_logic_summary or "").strip()
            if mls and "needs source" not in mls.lower():
                out.append(f"Model logic: {mls}")
        out.append("Key metrics:\n" + _bullets(pc.key_metrics, list_limit))
        # data_sources (free-form prose) describes HOW sources combine
        # on the page — e.g. 'Illustrative HEI/Star scorecard + real
        # CDC PLACES SDOH overlay.' The per-source contexts (resolved
        # via data_source_ids) carry each source's cadence / provenance,
        # but the page-level prose explains the BLEND. Useful for the
        # 155 pages whose data_source_ids is empty (the prose is the
        # only source signal) and adds shape for the rest. Skipped
        # when truly empty or NEEDS placeholder.
        ds_prose = [
            v for v in (pc.data_sources or [])
            if v and "needs source" not in (v or "").lower()
        ]
        if ds_prose:
            out.append("Data sources:\n" + _bullets(ds_prose, list_limit))
        # diligence_use_cases is the direct answer to "what would I use
        # this page for in diligence?" — every page has it populated
        # after PR #1256 (the list-fields drain). Surfacing it lets the
        # Guide give a concrete answer instead of paraphrasing why_it_matters.
        # Skipped only when truly empty (which the invariant test now
        # forbids on new pages anyway).
        if pc.diligence_use_cases:
            out.append("Diligence use cases:\n" + _bullets(
                pc.diligence_use_cases, list_limit
            ))
        out.append(
            "Interpretation guidance:\n" + _bullets(pc.interpretation_guidance)
        )
        # Limitations + missing notes are NEVER trimmed.
        out.append("Page limitations:\n" + _bullets(pc.limitations))
        out.append("Related PEdesk routes:\n" + _bullets(pc.related_routes,
                                                          list_limit))
        # Route-specific notes_for_assistant — most pages carry only the
        # standard 3-line _BASE_NOTES (already covered by the system
        # prompt's policy section). A small set of parameterized pages
        # (e.g. /my/AT, /diligence/risk-workbench, /market-data/state/CA)
        # have extra notes describing how the trailing path segment maps
        # to a parameter or how a ?demo= flag changes the meaning.
        # _ctx() in manual_page_contexts.py uses the convention
        # `_BASE_NOTES + custom`, so anything beyond index 3 is the
        # route-specific layer. Emit only those — surfaces the custom
        # clarifications without bloating the prompt with the standard
        # boilerplate that the system prompt already carries.
        route_notes = list(pc.notes_for_assistant or [])[3:]
        if route_notes:
            out.append(
                "Route-specific assistant notes:\n" + _bullets(route_notes)
            )

    if packet.metric_contexts:
        out.append("--- Metric contexts ---")
        for m in packet.metric_contexts:
            if compact:
                out.append(f"- {m.label} ({m.metric_id})")
            else:
                # common_misread is the highest-leverage field per token: one
                # tight sentence describing the classic mistake when reading
                # this number. Include it directly so the model doesn't have
                # to fish it out of RAG retrieval. Guard against the legacy
                # placeholder so we never push "Needs source documentation."
                # into the prompt.
                misread = _dot(m.common_misread)
                misread_line = (
                    f" Common misread: {misread}."
                    if misread and "needs source" not in misread.lower()
                    else ""
                )
                # diligence_interpretation answers "how should I read this for
                # diligence" — populated on every metric. Same placeholder
                # guard as common_misread.
                diligence = _dot(m.diligence_interpretation)
                diligence_line = (
                    f" Diligence read: {diligence}."
                    if diligence and "needs source" not in diligence.lower()
                    else ""
                )
                # related_metrics lets the model hop between paired concepts
                # (e.g. denial_rate ↔ net_collection_rate ↔
                # underpayment_rate). PR #1258's
                # TestMetricsHaveRelatedMetrics::test_no_metric_has_empty
                # guarantees every metric ships ≥1 entry and they all
                # resolve. Surfacing it as a short comma-separated list
                # adds 30-50 chars per metric — well within the prompt
                # budget for typical pages.
                rel_metrics = [
                    str(r).strip() for r in (m.related_metrics or [])
                    if str(r).strip()
                ]
                rel_metrics_line = (
                    f" Related metrics: {', '.join(rel_metrics)}."
                    if rel_metrics
                    else ""
                )
                # related_routes on the metric points to OTHER PEdesk
                # pages that discuss this metric — distinct from the
                # page's own related_routes block. Lets the Guide say
                # 'to dig deeper into denial_rate, see
                # /diligence/denial-prediction'. Every metric has at
                # least 2 (locked by TestMetricsHaveTwoOrMoreRelatedRoutes).
                rel_routes = [
                    str(r).strip() for r in (m.related_routes or [])
                    if str(r).strip()
                ]
                rel_routes_line = (
                    f" Discussed on: {', '.join(rel_routes)}."
                    if rel_routes
                    else ""
                )
                # Metric values commonly end in a period — strip and let
                # the templates add their own terminator to avoid '..'
                # artifacts where Caveats / Related metrics meet.
                caveats = (
                    '; '.join(_dot(c) for c in m.caveats)
                    if m.caveats else "none"
                )
                out.append(
                    f"- {m.label} ({m.metric_id}): {_dot(m.definition)}. "
                    f"Formula: {_dot(m.formula)} [{m.formula_confidence.value}]. "
                    f"Why it matters: {_dot(m.why_it_matters)}."
                    f"{diligence_line}"
                    f"{misread_line} "
                    f"Caveats: {caveats}."
                    f"{rel_metrics_line}"
                    f"{rel_routes_line}"
                )

    if packet.data_source_contexts:
        out.append("--- Data source contexts ---")
        for s in packet.data_source_contexts:
            if compact:
                out.append(f"- {s.label} ({s.source_id})")
            else:
                # ic_ready is the direct answer to "Is this IC-ready?" —
                # partners ask this constantly. PR #1267 set the flag
                # explicitly on every source (True / False, never None),
                # so we emit a 'yes' / 'no' clause whenever the source
                # supplies it. The clause is a fact about the source's
                # IC-readiness contract, not a recommendation.
                if s.ic_ready is True:
                    ic_line = " IC-ready: yes (stand-alone basis for IC)."
                elif s.ic_ready is False:
                    ic_line = " IC-ready: no (needs to be paired with other data)."
                else:
                    ic_line = ""
                # provenance_notes tells the partner WHAT TO CITE when
                # using this source — dataset id, release year, filing
                # type, etc. PR #1262 drained every NEEDS placeholder here;
                # surfacing it lets the model answer 'where does this come
                # from / what should I cite?' directly. Guard against the
                # legacy placeholder defensively.
                prov = _dot(s.provenance_notes)
                prov_line = (
                    f" Provenance: {prov}."
                    if prov and "needs source" not in prov.lower()
                    else ""
                )
                # strengths describes what this source is positively good
                # at (e.g. cms_hcris: 'Comprehensive, free, comparable
                # across all US hospitals.'). PR #1262 drained the lone
                # NEEDS placeholder; every source now carries real
                # strengths. Surfacing the list complements description
                # (what it IS) + limitations (what it is NOT) with what
                # it is GOOD AT. Filtered defensively against any stale
                # legacy placeholder.
                strengths = [
                    _dot(v) for v in (s.strengths or [])
                    if str(v).strip()
                    and "needs source" not in str(v).strip().lower()
                ]
                strengths_line = (
                    f" Strengths: {'; '.join(strengths)}."
                    if strengths
                    else ""
                )
                # Source values commonly end in a period (the registry
                # convention); strip those trailing punctuation marks via
                # _dot() before composing so the template's own clause
                # terminators don't produce 'foo..' or 'foo.;' artifacts.
                cadence = _dot(s.update_cadence)
                lag = _dot(s.freshness_lag)
                limitations = (
                    '; '.join(_dot(v) for v in s.limitations)
                    if s.limitations else "none"
                )
                description = _dot(s.description)
                out.append(
                    f"- {s.label} ({s.source_id}): {description}. "
                    f"Type: {s.source_type.value}. Cadence: {cadence}; "
                    f"freshness lag: {lag}. "
                    f"Limitations: {limitations}."
                    f"{strengths_line}"
                    f"{prov_line}"
                    f"{ic_line}"
                )

    # Always include — these carry the honesty of the answer.
    out.append("Known limitations:\n" + _bullets(packet.known_limitations))
    out.append(
        "Missing context notes:\n" + _bullets(packet.missing_context_notes)
    )
    return "\n".join(out)


# On-screen figures caps — keep the scraped block small so it can't crowd
# out the page packet or be abused to stuff the prompt.
_MAX_ONSCREEN_FIGURES = 24
_MAX_ONSCREEN_LABEL_CHARS = 80
_MAX_ONSCREEN_VALUE_CHARS = 60


def sanitize_onscreen_figures(raw) -> List[dict]:
    """Coerce an untrusted on-screen-figures payload into a safe, bounded list.

    The Guide widget scrapes the page's visible KPI blocks (label + value) and
    posts them so the model can analyze the numbers the user is actually
    looking at. Because that payload is client-supplied we defensively bound it:
    accept only ``{"label": str, "value": str}`` pairs, strip/cap each string,
    drop empties, and cap the count. Returns ``[]`` for anything malformed so
    callers can treat "no figures" and "bad figures" identically.
    """
    if not isinstance(raw, list):
        return []
    out: List[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        value = item.get("value")
        if not isinstance(label, str) or not isinstance(value, str):
            continue
        label = " ".join(label.split())[:_MAX_ONSCREEN_LABEL_CHARS].strip()
        value = " ".join(value.split())[:_MAX_ONSCREEN_VALUE_CHARS].strip()
        if not label or not value:
            continue
        out.append({"label": label, "value": value})
        if len(out) >= _MAX_ONSCREEN_FIGURES:
            break
    return out


def _render_onscreen_block(figures: List[dict]) -> str:
    if not figures:
        return ""
    lines = [
        "=== On-screen figures (as currently displayed on this page) ===",
        "These are the values the user is looking at right now, scraped from "
        "this page's KPI blocks. They are shown AS RENDERED and have NOT been "
        "re-validated by the Guide — treat them with this page's stated data "
        "confidence.",
    ]
    lines += [f"- {f['label']}: {f['value']}" for f in figures]
    return "\n".join(lines)


def build_guide_user_prompt(
    question: str,
    packet: GuideContextPacket,
    rag_context: str = "",
    onscreen_figures: List[dict] = None,
) -> str:
    """The current-page context block + optional retrieved RAG context +
    optional on-screen figures + the user's question.

    ``rag_context`` (when RAG is enabled) is appended AFTER the page packet
    so the model treats the page context as primary. ``onscreen_figures``
    (already sanitized via :func:`sanitize_onscreen_figures`) are the live
    KPI values the user is viewing — appended as clearly-labeled, as-displayed
    reference so the Guide can analyze the actual numbers without treating them
    as validated. Backward compatible: omitting both reproduces the v1 prompt
    exactly.
    """
    context = packet_to_prompt_context(packet)
    q = (question or "").strip()
    extra = ("\n\n" + rag_context.strip()) if rag_context and rag_context.strip() else ""
    onscreen = _render_onscreen_block(onscreen_figures or [])
    onscreen_block = ("\n\n" + onscreen) if onscreen else ""
    return (
        context
        + extra
        + onscreen_block
        + "\n\n=== Question ===\n"
        + q
        + "\n\nAnswer using only the context above (page context is primary; "
        "any retrieved context is supporting reference; on-screen figures are "
        "as-displayed, not validated). If it is not enough, say so."
    )


def clean_guide_answer(text: str) -> str:
    """Strip visible <think> blocks and tidy whitespace.

    Removes complete ``<think>...</think>`` blocks and any dangling
    unterminated ``<think>`` tail, trims a single repetitive
    "Based on the provided context" preamble, and collapses excess blank
    lines. Never removes substantive content/caveats.
    """
    if not text:
        return ""
    cleaned = _THINK_RE.sub("", text)
    cleaned = _DANGLING_THINK_OPEN_RE.sub("", cleaned)
    cleaned = _REPETITIVE_PREAMBLE_RE.sub("", cleaned, count=1)
    # Collapse 3+ newlines to a blank line; strip trailing spaces per line.
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
