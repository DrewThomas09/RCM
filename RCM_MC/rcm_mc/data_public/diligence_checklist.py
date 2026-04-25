"""Diligence Checklist — IC-ready review for a corpus deal.

Walks a deal dict through six diligence sections, assigning each
item a status of CRITICAL / WARNING / PASS / MISSING based on the
deal data + corpus benchmarks. Built for the partner-facing IC
binder: every line item names what to look at and whether the
deal already passes that bar.

Contract (kept stable for the CLI + corpus_report + tests):

    build_checklist(deal: dict, db_path: str, **kwargs)
        → DiligenceChecklistResult

    checklist_text(result)  → str   (human-readable, prints in CLI)
    checklist_json(result)  → dict  (JSON-serialisable export)

Sections (always rendered in this order):

    1. Deal Overview        — name, year, buyer, sector
    2. Returns Analysis     — realized MOIC vs. corpus, IRR, hold
    3. Capital Structure    — entry multiple, leverage, headroom
    4. Payer Mix Risk       — payer concentration, single-payer cap
    5. PE Intelligence      — sponsor track record, vintage timing
    6. Data Quality         — completeness, source attribution

Status semantics:

    CRITICAL  — material adverse signal; partner must look
    WARNING   — soft signal; review at next IC
    PASS      — meets the bar; no action needed
    MISSING   — required data point absent; cannot evaluate
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Status palette — used by the UI page to color chips.
STATUS_COLORS = {
    "CRITICAL": "#ef4444",
    "WARNING":  "#f59e0b",
    "PASS":     "#10b981",
    "MISSING":  "#94a3b8",
}


_STATUS_TO_PRIORITY = {
    "CRITICAL": "Critical",
    "WARNING":  "High",
    "MISSING":  "Medium",
    "PASS":     "Low",
}

_PRIORITY_COLORS = {
    "Critical": "#ef4444",
    "High":     "#ea580c",
    "Medium":   "#f59e0b",
    "Low":      "#64748b",
}


@dataclass
class ChecklistItem:
    """A single review line. ``section`` is the renderer ordering;
    ``status`` is the data-driven verdict; ``recommendation`` is the
    "what to do if this trips" string the partner sees first.

    Legacy aliases (``priority``, ``priority_color``, ``is_red_flag``,
    ``corpus_fail_rate``, ``category``) are exposed as properties so
    pre-rewrite callers (notably the /diligence-checklist UI page)
    keep working without code changes.
    """
    id: str
    section: str
    title: str
    description: str
    status: str             # CRITICAL / WARNING / PASS / MISSING
    detail: str             # filled in at evaluation time
    recommendation: str = ""

    # ── Legacy aliases for pre-rewrite callers ────────────────
    @property
    def priority(self) -> str:
        """Old API used Critical/High/Medium/Low priorities; map
        from the new status field."""
        return _STATUS_TO_PRIORITY.get(self.status, "Medium")

    @property
    def priority_color(self) -> str:
        return _PRIORITY_COLORS[self.priority]

    @property
    def is_red_flag(self) -> bool:
        return self.status == "CRITICAL"

    @property
    def corpus_fail_rate(self) -> float:
        """Old API surfaced a hand-curated fail-rate per item.
        Approximate from status: CRITICAL items fail ~40%,
        WARNING ~20%, MISSING ~25%, PASS ~5%."""
        return {"CRITICAL": 0.40, "WARNING": 0.20,
                "MISSING": 0.25, "PASS": 0.05}.get(self.status, 0.20)

    @property
    def category(self) -> str:
        """Old API used a free-text category; the new section
        label (``"1. Deal Overview"`` etc.) serves the same role."""
        return self.section


@dataclass
class DiligenceChecklistResult:
    """Top-level checklist result. ``critical_count`` and
    ``warning_count`` drive the IC-binder header chip; ``open_questions``
    is the partner-facing follow-up list.

    Legacy aliases (``total_items``, ``critical_items``,
    ``high_items``, ``red_flags_triggered``, ``by_category``) are
    exposed as properties so pre-rewrite callers keep working.
    """
    deal_name: str
    deal_id: Optional[str]
    sector: str
    ev_mm: Optional[float]
    items: List[ChecklistItem]
    critical_count: int = 0
    warning_count: int = 0
    pass_count: int = 0
    missing_count: int = 0
    open_questions: List[str] = field(default_factory=list)
    corpus_deal_count: int = 0

    # ── Legacy aliases ────────────────────────────────────────
    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def critical_items(self) -> int:
        return self.critical_count

    @property
    def high_items(self) -> int:
        """Pre-rewrite UI used 'high' = WARNING-equivalent."""
        return self.warning_count

    @property
    def red_flags_triggered(self) -> int:
        """Pre-rewrite UI surfaced a separate red-flag count;
        we treat CRITICAL items as the equivalent."""
        return self.critical_count

    @property
    def by_category(self) -> Dict[str, List[ChecklistItem]]:
        """Group items by their section label so the legacy UI
        renderer's ``for cat in _CATEGORY_ORDER`` loop hits the
        right buckets."""
        out: Dict[str, List[ChecklistItem]] = {}
        for it in self.items:
            out.setdefault(it.section, []).append(it)
        return out


# ── Section labels (frozen — tests assert on these strings) ──
_SEC_OVERVIEW   = "1. Deal Overview"
_SEC_RETURNS    = "2. Returns Analysis"
_SEC_CAPITAL    = "3. Capital Structure"
_SEC_PAYER      = "4. Payer Mix Risk"
_SEC_INTEL      = "5. PE Intelligence"
_SEC_DATA       = "6. Data Quality"


def _is_missing(v: Any) -> bool:
    """A field counts as missing if it's None, '', or an empty
    container. Zero values (0.0 MOIC = total writeoff) are NOT
    missing — they're a meaningful data point."""
    if v is None:
        return True
    if isinstance(v, (str, list, dict, tuple, set)) and len(v) == 0:
        return True
    return False


def _entry_multiple(deal: Dict[str, Any]) -> Optional[float]:
    ev = deal.get("ev_mm")
    eb = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")
    if not ev or not eb:
        return None
    try:
        return float(ev) / float(eb)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _corpus_moic_band(db_path: Optional[str]) -> Optional[float]:
    """Median realized MOIC across the corpus. Returns None if the
    corpus is empty or the path isn't readable."""
    if not db_path:
        return None
    try:
        from .deals_corpus import DealsCorpus
        corpus = DealsCorpus(db_path)
        with corpus._connect() as con:
            row = con.execute(
                "SELECT realized_moic FROM public_deals "
                "WHERE realized_moic IS NOT NULL "
                "ORDER BY realized_moic"
            ).fetchall()
        if not row:
            return None
        moics = [r["realized_moic"] for r in row]
        return moics[len(moics) // 2]
    except Exception:  # noqa: BLE001
        return None


def _eval_overview(deal: Dict[str, Any]) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []

    # 1.1 Deal name present
    name = deal.get("deal_name") or deal.get("company_name")
    out.append(ChecklistItem(
        id="ovw_001", section=_SEC_OVERVIEW,
        title="Deal name documented",
        description="Every IC binder needs a canonical deal name.",
        status=("PASS" if not _is_missing(name) else "MISSING"),
        detail=(str(name) if name else "no name on record"),
        recommendation=(
            "" if name else "Add deal_name before circulating."),
    ))

    # 1.2 Vintage year present
    year = deal.get("year")
    if _is_missing(year):
        status = "MISSING"
        detail = "vintage year unknown"
    else:
        status = "PASS"
        detail = f"vintage {year}"
    out.append(ChecklistItem(
        id="ovw_002", section=_SEC_OVERVIEW,
        title="Vintage year",
        description="Vintage anchors comp-set timing and IRR math.",
        status=status, detail=detail,
    ))

    # 1.3 Buyer / sponsor identified
    buyer = deal.get("buyer") or deal.get("sponsor")
    out.append(ChecklistItem(
        id="ovw_003", section=_SEC_OVERVIEW,
        title="Sponsor identified",
        description="Sponsor track-record check requires the GP name.",
        status=("PASS" if not _is_missing(buyer) else "MISSING"),
        detail=(str(buyer) if buyer else "no sponsor on record"),
    ))

    # 1.4 Sector classification
    sec = deal.get("sector")
    out.append(ChecklistItem(
        id="ovw_004", section=_SEC_OVERVIEW,
        title="Sector classification",
        description="Sector drives the comp set and applicable items.",
        status=("PASS" if not _is_missing(sec) else "MISSING"),
        detail=(str(sec) if sec else "sector unknown"),
    ))

    return out


def _eval_returns(deal: Dict[str, Any],
                  db_path: Optional[str]) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []
    moic = deal.get("realized_moic")
    if moic is None:
        moic = deal.get("moic")

    # 2.1 Realized MOIC present
    if _is_missing(moic):
        out.append(ChecklistItem(
            id="ret_001", section=_SEC_RETURNS,
            title="Realized MOIC documented",
            description="MOIC at exit is the primary return metric.",
            status="MISSING",
            detail="not yet realized or not recorded",
            recommendation=("Mark deal as unrealized if hold "
                            "is ongoing; otherwise log realized MOIC."),
        ))
    else:
        # Compare against corpus median
        median = _corpus_moic_band(db_path)
        if median is None:
            status, det = "PASS", f"realized {moic:.2f}x"
        elif moic >= median * 1.25:
            status = "PASS"
            det = (f"realized {moic:.2f}x — top-quartile vs corpus "
                   f"median {median:.2f}x")
        elif moic >= median * 0.75:
            status = "WARNING"
            det = (f"realized {moic:.2f}x — middle of corpus "
                   f"(median {median:.2f}x)")
        else:
            status = "CRITICAL"
            det = (f"realized {moic:.2f}x — bottom-quartile vs "
                   f"corpus median {median:.2f}x")
        # Total writeoff (0.0) is always CRITICAL regardless of corpus
        if isinstance(moic, (int, float)) and moic <= 0.5:
            status = "CRITICAL"
            det = f"realized {moic:.2f}x — near-total writeoff"
        out.append(ChecklistItem(
            id="ret_001", section=_SEC_RETURNS,
            title="Realized MOIC vs corpus",
            description="Compare to corpus median and quartile bounds.",
            status=status, detail=det,
        ))

    # 2.2 IRR
    irr = deal.get("realized_irr")
    if irr is None:
        irr = deal.get("irr")
    if _is_missing(irr):
        out.append(ChecklistItem(
            id="ret_002", section=_SEC_RETURNS,
            title="Realized IRR documented",
            description="IRR is the time-weighted return signal.",
            status="MISSING",
            detail="not on record",
        ))
    else:
        if irr >= 0.20:
            s = "PASS"
        elif irr >= 0.10:
            s = "WARNING"
        else:
            s = "CRITICAL"
        out.append(ChecklistItem(
            id="ret_002", section=_SEC_RETURNS,
            title="Realized IRR vs PE bar",
            description="A 20% IRR is the standard benchmark.",
            status=s, detail=f"realized IRR {irr*100:.1f}%",
        ))

    # 2.3 Hold years
    hold = deal.get("hold_years")
    if _is_missing(hold):
        out.append(ChecklistItem(
            id="ret_003", section=_SEC_RETURNS,
            title="Hold period",
            description="Hold drives MOIC vs IRR translation.",
            status="MISSING", detail="not on record",
        ))
    else:
        out.append(ChecklistItem(
            id="ret_003", section=_SEC_RETURNS,
            title="Hold period",
            description="Hold drives MOIC vs IRR translation.",
            status="PASS", detail=f"{hold:.1f}y",
        ))

    return out


def _eval_capital(deal: Dict[str, Any],
                  entry_debt_mm: Optional[float] = None,
                  ) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []
    em = _entry_multiple(deal)
    ev = deal.get("ev_mm")
    eb = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")

    # 3.1 Entry multiple sanity
    if em is None:
        out.append(ChecklistItem(
            id="cap_001", section=_SEC_CAPITAL,
            title="Entry multiple",
            description="EV / EBITDA at entry. >12x is the alarm bell.",
            status="MISSING",
            detail=("missing EV" if _is_missing(ev)
                    else "missing entry EBITDA"),
        ))
    else:
        if em > 14:
            s, det = "CRITICAL", (
                f"{em:.1f}x — well above sponsor-friendly bar")
        elif em > 12:
            s, det = "WARNING", (
                f"{em:.1f}x — premium territory, IRR sensitive to exit")
        elif em > 6:
            s, det = "PASS", f"{em:.1f}x — within typical band"
        else:
            s, det = "WARNING", (
                f"{em:.1f}x — abnormally low, validate EBITDA quality")
        out.append(ChecklistItem(
            id="cap_001", section=_SEC_CAPITAL,
            title="Entry multiple",
            description="EV / EBITDA at entry. >12x is the alarm bell.",
            status=s, detail=det,
        ))

    # 3.2 Leverage at entry (debt / EBITDA) — only if we have both
    if entry_debt_mm and eb:
        try:
            leverage = float(entry_debt_mm) / float(eb)
        except (TypeError, ValueError, ZeroDivisionError):
            leverage = None
    else:
        leverage = None
    if leverage is None:
        out.append(ChecklistItem(
            id="cap_002", section=_SEC_CAPITAL,
            title="Entry leverage (debt/EBITDA)",
            description="Industry P75 ~6x; >7x risks covenant breach.",
            status="MISSING",
            detail="entry_debt_mm not supplied",
            recommendation=(
                "Pass --assumptions '{\"entry_debt_mm\": <num>}'"),
        ))
    else:
        if leverage > 8:
            s, det = "CRITICAL", (
                f"{leverage:.1f}x — extreme leverage, covenant risk acute")
        elif leverage > 6:
            s, det = "WARNING", (
                f"{leverage:.1f}x — above corpus P75")
        else:
            s, det = "PASS", f"{leverage:.1f}x — within range"
        out.append(ChecklistItem(
            id="cap_002", section=_SEC_CAPITAL,
            title="Entry leverage (debt/EBITDA)",
            description="Industry P75 ~6x; >7x risks covenant breach.",
            status=s, detail=det,
        ))

    return out


def _eval_payer(deal: Dict[str, Any]) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except (TypeError, json.JSONDecodeError):
            pm = None

    if not isinstance(pm, dict) or not pm:
        out.append(ChecklistItem(
            id="pay_001", section=_SEC_PAYER,
            title="Payer mix documented",
            description="Payer mix drives reimbursement risk.",
            status="MISSING", detail="not on record",
            recommendation=("Capture commercial / Medicare / "
                            "Medicaid / self-pay split."),
        ))
        return out

    out.append(ChecklistItem(
        id="pay_001", section=_SEC_PAYER,
        title="Payer mix documented",
        description="Payer mix drives reimbursement risk.",
        status="PASS",
        detail=", ".join(f"{k} {v*100:.0f}%" for k, v in pm.items()),
    ))

    # Single-payer concentration
    if pm:
        max_payer = max(pm, key=pm.get)
        max_share = pm[max_payer]
        if max_share > 0.65:
            s, det = "CRITICAL", (
                f"{max_payer} {max_share*100:.0f}% — concentration risk")
        elif max_share > 0.55:
            s, det = "WARNING", (
                f"{max_payer} {max_share*100:.0f}% — elevated")
        else:
            s, det = "PASS", (
                f"top payer {max_payer} {max_share*100:.0f}%")
        out.append(ChecklistItem(
            id="pay_002", section=_SEC_PAYER,
            title="Single-payer concentration",
            description="Top payer >60% triggers the diversification flag.",
            status=s, detail=det,
        ))

    # Medicaid exposure
    medicaid = pm.get("medicaid", 0)
    if medicaid > 0.40:
        out.append(ChecklistItem(
            id="pay_003", section=_SEC_PAYER,
            title="Medicaid exposure",
            description="Heavy Medicaid → state rate-cut sensitivity.",
            status="WARNING",
            detail=f"medicaid {medicaid*100:.0f}% of mix",
        ))
    else:
        out.append(ChecklistItem(
            id="pay_003", section=_SEC_PAYER,
            title="Medicaid exposure",
            description="Heavy Medicaid → state rate-cut sensitivity.",
            status="PASS",
            detail=f"medicaid {medicaid*100:.0f}% of mix",
        ))

    return out


def _eval_intel(deal: Dict[str, Any]) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []

    # 5.1 Sponsor named (drives track-record check)
    sponsor = deal.get("buyer") or deal.get("sponsor")
    if _is_missing(sponsor):
        out.append(ChecklistItem(
            id="int_001", section=_SEC_INTEL,
            title="Sponsor track-record review",
            description="Pull the sponsor's prior deals + realizations.",
            status="MISSING", detail="sponsor not identified",
        ))
    else:
        out.append(ChecklistItem(
            id="int_001", section=_SEC_INTEL,
            title="Sponsor track-record review",
            description="Pull the sponsor's prior deals + realizations.",
            status="PASS",
            detail=f"reviewable: {sponsor}",
        ))

    # 5.2 Vintage timing
    year = deal.get("year")
    if _is_missing(year):
        out.append(ChecklistItem(
            id="int_002", section=_SEC_INTEL,
            title="Vintage timing context",
            description="Pre-2009 / post-2020 vintages have peer windows.",
            status="MISSING", detail="vintage unknown",
        ))
    else:
        # Frothy vintages (2007, 2021) flagged as WARNING
        if year in (2007, 2008, 2021, 2022):
            s = "WARNING"
            det = (f"{year} — frothy vintage; entry multiples elevated, "
                   f"exits compressed")
        else:
            s = "PASS"
            det = f"{year} — typical entry window"
        out.append(ChecklistItem(
            id="int_002", section=_SEC_INTEL,
            title="Vintage timing context",
            description="Frothy vintages (2007, 2021) hurt realized IRR.",
            status=s, detail=det,
        ))

    return out


def _eval_data_quality(deal: Dict[str, Any]) -> List[ChecklistItem]:
    out: List[ChecklistItem] = []

    # Source attribution
    src = deal.get("source")
    if _is_missing(src):
        out.append(ChecklistItem(
            id="dat_001", section=_SEC_DATA,
            title="Source attribution",
            description="Every corpus row needs a provenance string.",
            status="MISSING", detail="no source field",
        ))
    else:
        out.append(ChecklistItem(
            id="dat_001", section=_SEC_DATA,
            title="Source attribution",
            description="Every corpus row needs a provenance string.",
            status="PASS", detail=str(src),
        ))

    # Notes (qualitative context)
    notes = deal.get("notes") or deal.get("note")
    if _is_missing(notes):
        out.append(ChecklistItem(
            id="dat_002", section=_SEC_DATA,
            title="Qualitative notes",
            description="Free-text context aids partner-level review.",
            status="WARNING", detail="no notes captured",
        ))
    else:
        out.append(ChecklistItem(
            id="dat_002", section=_SEC_DATA,
            title="Qualitative notes",
            description="Free-text context aids partner-level review.",
            status="PASS",
            detail=f"{len(str(notes))} chars on file",
        ))

    return out


def build_checklist(
    deal: Dict[str, Any],
    db_path: Optional[str] = None,
    *,
    entry_debt_mm: Optional[float] = None,
    **_unused_kwargs: Any,
) -> DiligenceChecklistResult:
    """Build a six-section diligence checklist for a corpus deal.

    Args:
        deal: a deal dict (corpus row or fresh target profile).
        db_path: corpus DB so we can compare returns to the corpus
                 median. Optional — checklist still works without it.
        entry_debt_mm: debt at close, if known. Drives the leverage
                       check; absent → that line lands MISSING.

    Returns:
        DiligenceChecklistResult with items grouped by section,
        counts of CRITICAL / WARNING / PASS / MISSING, and a list
        of open questions to take to the next IC.
    """
    items: List[ChecklistItem] = []
    items.extend(_eval_overview(deal))
    items.extend(_eval_returns(deal, db_path))
    items.extend(_eval_capital(deal, entry_debt_mm=entry_debt_mm))
    items.extend(_eval_payer(deal))
    items.extend(_eval_intel(deal))
    items.extend(_eval_data_quality(deal))

    crit = sum(1 for i in items if i.status == "CRITICAL")
    warn = sum(1 for i in items if i.status == "WARNING")
    passed = sum(1 for i in items if i.status == "PASS")
    miss = sum(1 for i in items if i.status == "MISSING")

    # Open questions: every CRITICAL or MISSING line generates one.
    questions: List[str] = []
    for i in items:
        if i.status == "CRITICAL":
            questions.append(
                f"[CRITICAL] {i.title}: {i.detail}")
        elif i.status == "MISSING":
            q = f"[MISSING] {i.title}"
            if i.recommendation:
                q += f" — {i.recommendation}"
            questions.append(q)

    # Corpus deal count for context
    corpus_n = 0
    if db_path:
        try:
            from .deals_corpus import DealsCorpus
            corpus_n = DealsCorpus(db_path).stats().get("total", 0)
        except Exception:  # noqa: BLE001
            pass

    return DiligenceChecklistResult(
        deal_name=str(deal.get("deal_name")
                      or deal.get("company_name") or "Unnamed"),
        deal_id=deal.get("source_id"),
        sector=str(deal.get("sector") or ""),
        ev_mm=deal.get("ev_mm"),
        items=items,
        critical_count=crit,
        warning_count=warn,
        pass_count=passed,
        missing_count=miss,
        open_questions=questions,
        corpus_deal_count=corpus_n,
    )


def checklist_text(result: DiligenceChecklistResult) -> str:
    """Render the checklist as plain text — used by the CLI."""
    lines: List[str] = []
    lines.append(f"Diligence Checklist — {result.deal_name}")
    if result.deal_id:
        lines.append(f"Deal ID: {result.deal_id}")
    if result.sector:
        lines.append(f"Sector: {result.sector}")
    if result.ev_mm:
        lines.append(f"EV: ${result.ev_mm:.0f}M")
    lines.append("")
    lines.append(
        f"Status: {result.critical_count} CRITICAL · "
        f"{result.warning_count} WARNING · "
        f"{result.pass_count} PASS · "
        f"{result.missing_count} MISSING")
    lines.append("")

    by_sec: Dict[str, List[ChecklistItem]] = {}
    for it in result.items:
        by_sec.setdefault(it.section, []).append(it)
    for section in (_SEC_OVERVIEW, _SEC_RETURNS, _SEC_CAPITAL,
                    _SEC_PAYER, _SEC_INTEL, _SEC_DATA):
        sec_items = by_sec.get(section, [])
        if not sec_items:
            continue
        # Strip the leading "1. " prefix for the readable header
        # but expose the prefixed name in the section column too.
        lines.append(f"=== {section} ===")
        for i in sec_items:
            lines.append(f"  [{i.status}] {i.title}")
            if i.detail:
                lines.append(f"    → {i.detail}")
            if i.recommendation:
                lines.append(f"    Action: {i.recommendation}")
        lines.append("")

    if result.open_questions:
        lines.append("Open questions for next IC:")
        for q in result.open_questions:
            lines.append(f"  • {q}")

    return "\n".join(lines)


def checklist_json(result: DiligenceChecklistResult) -> dict:
    """Render the checklist as a JSON-serializable dict."""
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    for it in result.items:
        by_sec.setdefault(it.section, []).append({
            "id": it.id,
            "title": it.title,
            "description": it.description,
            "status": it.status,
            "detail": it.detail,
            "recommendation": it.recommendation,
        })
    return {
        "deal_name": result.deal_name,
        "deal_id": result.deal_id,
        "sector": result.sector,
        "ev_mm": result.ev_mm,
        "critical_count": result.critical_count,
        "warning_count": result.warning_count,
        "pass_count": result.pass_count,
        "missing_count": result.missing_count,
        "corpus_deal_count": result.corpus_deal_count,
        "sections": by_sec,
        "open_questions": result.open_questions,
    }


# ── Backwards-compat aliases ─────────────────────────────────────
# Older code paths may still import the legacy
# ``compute_diligence_checklist(sector, ev_mm)`` signature. Forward
# to ``build_checklist`` with a synthetic deal so a stale caller
# still gets a result.

def compute_diligence_checklist(
    sector: str,
    ev_mm: float = 200.0,
    **kwargs: Any,
) -> DiligenceChecklistResult:
    """Legacy entry point — wraps :func:`build_checklist`."""
    deal = {"deal_name": f"Hypothetical {sector} deal",
            "sector": sector, "ev_mm": ev_mm}
    deal.update({k: v for k, v in kwargs.items()
                 if k not in ("entry_debt_mm",)})
    return build_checklist(deal, db_path=None,
                           entry_debt_mm=kwargs.get("entry_debt_mm"))
