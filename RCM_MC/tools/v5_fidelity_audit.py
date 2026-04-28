"""V5 fidelity audit — score every UI renderer against chartis editorial signals.

The cycle-7 inventory hit 100% *mechanical* v5 compliance: every UI
route reaches ``chartis_shell``. That number alone doesn't tell us
which pages are editorially aligned with chartis.com (italic-serif
headlines, ck_* primitive density, no inline styles, no lazy labels,
correct numeric formatting). This audit closes that gap by walking
every Python file in ``rcm_mc/ui/`` and scoring it on six dimensions.

Usage::

    python tools/v5_fidelity_audit.py             # human leaderboard
    python tools/v5_fidelity_audit.py --json      # machine-readable
    python tools/v5_fidelity_audit.py --md docs/V5_FIDELITY_REPORT.md
    python tools/v5_fidelity_audit.py --threshold 70

Each renderer gets a 0-100 score from a weighted sum of:

  1. **Editorial shell**       — calls ``chartis_shell``        (20 pts)
  2. **Editorial primitives**  — ck_* helper density per LOC    (20 pts)
  3. **Italic-serif highlight**— ck_section_intro w/ italic_word  (10 pts)
  4. **Inline-style penalty**  — ``style="`` count per LOC      (-15 pts)
  5. **Lazy-label penalty**    — generic CTA copy             (-10 pts)
  6. **Numeric discipline**    — uses ck_fmt_* helpers          (10 pts)
  7. **Bespoke HTML penalty**  — direct ``<div ``count per LOC  (-15 pts)
  8. **Provenance** (positive) — ck_provenance_tooltip usage    (5 pts)

The pass threshold is 70/100 by default — chosen so the cycle-15
ported pages (/library, /notes, /research, /escalations,
/my/<owner>) score above the line and stragglers score below.
Re-run after each editorial cycle to track drift.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Pattern compiled once at module-load time so the audit is a single
# pass over each file's source. All patterns are line-tolerant; some
# of the helpers wrap onto multiple lines so we use re.DOTALL where
# needed.
# Editorial-shell call — direct ``chartis_shell(...)`` OR a call to
# the cycle-18 ``render_insights_page(...)`` helper that composes
# chartis_shell with the Insights triplet wired around the body.
# Both put the page on the editorial chrome.
_RE_CHARTIS_SHELL = re.compile(
    r"\b(?:chartis_shell|render_insights_page)\s*\("
)
# Primitive names. ``render_insights_page`` counts as a primitive
# itself because invoking it composes 5+ ck_* helpers (search hero,
# filter sidebar, results header, section header, section intro)
# behind a single call — pages that use it deserve density credit
# without dropping each helper name into the source manually.
_RE_CK_PRIMITIVES = re.compile(
    r"\b(?:ck_(?:eyebrow|section_header|section_intro|panel|table|"
    r"kpi_block|signal_badge|arrow_link|image_card|severity_panel|"
    r"affirm_empty|search_hero|filter_sidebar|results_header|"
    r"command_palette|fmt_(?:currency|percent|number)|provenance_tooltip)"
    r"|render_insights_page)\b"
)
# Italic-serif highlight signal — either via the ck_section_intro
# kwarg (chartis cadence: "Reasons to *believe* in better") or via
# a literal <em>X</em> inside the rendered body. The regex
# "ck_section_intro(...italic_word=...)" can't be matched precisely
# by a regex because the call args may contain nested parens (e.g.
# f-strings with .upper() or .strip()), so we just check for the
# kwarg name anywhere in the source — false-positive risk is very
# low because no other helper uses it.
# Italic-serif kwarg can appear as ``italic_word="thing"`` (kwarg
# syntax in a direct ck_section_intro call) OR as ``"italic_word":
# "thing"`` (dict-literal key when intro is passed as a dict to
# render_insights_page). Both express the chartis cadence.
_RE_ITALIC_HIGHLIGHT = re.compile(r"""\bitalic_word\s*["']?\s*[=:]""")
_RE_INLINE_STYLE = re.compile(r"\bstyle\s*=\s*[\"']")
# A "bespoke" div is one whose class isn't a ck-* primitive class —
# editorial divs like `<div class="ck-rail-layout">` should NOT count
# against the score. Match `<div ` not followed by `class="ck-` (the
# editorial prefix) and not followed by a quoted attribute that
# opens with ck-.
_RE_BESPOKE_DIV = re.compile(
    r'<div\s+(?:class=["\'](?!ck-)|style=)',
)
_RE_LAZY_LABELS = re.compile(
    r">(?:Run|Click here|TBD|Coming soon|FOO|XXX)<",
)
# Italic-serif highlight via either ck_section_intro(italic_word=...)
# or a literal `<em>...</em>` inside a section heading. Both are the
# chartis cadence signal. The <em> may carry style/class attributes
# (some renderers inline-style the teal-ink color directly), so the
# attribute portion is permissive.
_RE_ITALIC_EM = re.compile(r"<em(?:\s[^>]*)?>[^<]+</em>")
_RE_FMT_HELPERS = re.compile(
    r"\bck_fmt_(?:currency|percent|number)\s*\(",
)
_RE_PROVENANCE = re.compile(r"\bck_provenance_tooltip\s*\(")
# Routes / renderer entry points only — files that don't define one
# of these are treated as pure helpers and skipped (zero LOC against
# editorial chrome means nothing to score).
_RE_RENDERER_ENTRY = re.compile(
    r"^def\s+(?:render_|page_|build_|emit_)", re.MULTILINE,
)


@dataclass
class FidelityScore:
    file: str
    loc: int
    score: int
    has_chartis_shell: bool
    primitive_count: int
    primitive_density: float
    italic_highlight: bool
    inline_style_count: int
    bespoke_div_count: int
    lazy_label_count: int
    fmt_helper_count: int
    provenance_count: int
    notes: List[str] = field(default_factory=list)


def _count_loc(src: str) -> int:
    """Count non-blank, non-comment lines. Approximate but enough."""
    return sum(
        1 for line in src.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def score_file(path: Path) -> Optional[FidelityScore]:
    """Score a single Python file. Returns None for non-renderer helpers.

    The skip rule: a file with no renderer-entry function is a helper
    (e.g. _chartis_kit.py itself, _helpers.py). Helpers don't render
    pages so they have nothing to be editorial *about*; scoring them
    would noise the leaderboard.
    """
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not _RE_RENDERER_ENTRY.search(src):
        return None
    loc = _count_loc(src)
    # No LOC floor — even a 5-line wrapper that does ``return
    # chartis_shell(body, title="X")`` is a real render path worth
    # scoring. Helpers without a render entry function were already
    # filtered above.

    has_shell = bool(_RE_CHARTIS_SHELL.search(src))
    # Each ``render_insights_page`` call composes ~5 ck_* primitives
    # (search hero + filter sidebar + results header + section header +
    # section intro + chartis_shell). Without weighting, pages that
    # use the helper score lower than pages that hand-wire each
    # primitive — penalising the abstraction. Count helper calls 5x.
    raw_primitives = _RE_CK_PRIMITIVES.findall(src)
    helper_calls = sum(1 for p in raw_primitives if p == "render_insights_page")
    other_primitives = len(raw_primitives) - helper_calls
    primitives = other_primitives + (helper_calls * 5)
    italic_kwarg = bool(_RE_ITALIC_HIGHLIGHT.search(src))
    italic_em = bool(_RE_ITALIC_EM.search(src))
    italic = italic_kwarg or italic_em
    inline_styles = len(_RE_INLINE_STYLE.findall(src))
    bespoke_divs = len(_RE_BESPOKE_DIV.findall(src))
    lazy_labels = len(_RE_LAZY_LABELS.findall(src))
    fmt_helpers = len(_RE_FMT_HELPERS.findall(src))
    provenance = len(_RE_PROVENANCE.findall(src))

    primitive_density = primitives / max(1, loc) * 100  # primitives per 100 LOC

    # Score components — each named so the report can explain WHY.
    # Calibrated so the cycle 6-15 editorial ports (which use shell +
    # 4-6 ck_* primitives + clean tokens + zero inline styles) clear
    # the 70 threshold and stragglers (bespoke HTML, no shell, etc.)
    # land far below.
    notes: List[str] = []
    score = 0

    # +25: Editorial shell. Required floor — without it nothing else
    # matters, the render path is bypassing chartis chrome entirely.
    if has_shell:
        score += 25
    else:
        notes.append("missing chartis_shell — bypassing editorial chrome")

    # +25: Editorial primitive density. Saturates at ~3 calls per
    # 100 LOC (achieved by the cycle 6-15 ports). Below 1 reads as
    # "compliant by reference only — nothing actually wired."
    prim_pts = min(25, int(primitive_density * 25 / 3))
    score += prim_pts
    if primitive_density < 1:
        notes.append(
            f"low ck_* primitive density ({primitive_density:.1f}/100LOC)"
        )

    # +15: Italic-serif highlight — chartis.com signature cadence.
    # Either ck_section_intro(italic_word=...) or a literal <em>X</em>
    # inside the body counts.
    if italic:
        score += 15
    else:
        notes.append("no italic-serif highlight (chartis cadence missing)")

    # +20: Cleanliness — credits absence of inline-style and bespoke-
    # div HTML. A page with zero inline styles and zero bespoke divs
    # gets the full 20; each violation removes points.
    cleanliness = 20
    cleanliness -= min(15, inline_styles // 2)
    cleanliness -= min(10, max(0, bespoke_divs // 4))
    score += max(0, cleanliness)
    if inline_styles > 5:
        notes.append(f"high inline-style count: {inline_styles}")
    if bespoke_divs > 10:
        notes.append(f"high non-ck-class <div> count: {bespoke_divs}")

    # -10: Lazy labels — extinct since cycle 1, regression-only check.
    score -= min(10, lazy_labels * 5)
    if lazy_labels:
        notes.append(
            f"lazy labels found: {lazy_labels} (Run / Click here / TBD)"
        )

    # +10: Numeric formatting via ck_fmt_* helpers — saturates at 3.
    score += min(10, fmt_helpers * 4)

    # +5: Provenance tooltips on key values (4C foundation).
    score += min(5, provenance * 2)

    # Clamp to [0, 100]
    score = max(0, min(100, score))

    return FidelityScore(
        file=str(path),
        loc=loc,
        score=score,
        has_chartis_shell=has_shell,
        primitive_count=primitives,
        primitive_density=primitive_density,
        italic_highlight=italic,
        inline_style_count=inline_styles,
        bespoke_div_count=bespoke_divs,
        lazy_label_count=lazy_labels,
        fmt_helper_count=fmt_helpers,
        provenance_count=provenance,
        notes=notes,
    )


def audit_tree(ui_dir: Path, *, repo_root: Optional[Path] = None) -> List[FidelityScore]:
    """Walk ui_dir and score every renderer file.

    Skipped:
    - ``__pycache__`` build artifacts
    - test fixtures (filenames starting with ``_test``)
    - ``__init__.py``
    - underscore-prefixed helper modules (``_chartis_kit.py``,
      ``_helpers.py``, ``_html_polish.py`` etc.) — these are
      kit/utility files that may *contain* helper-entry function
      definitions but aren't routes themselves

    File paths in the score are normalised to repo-relative so the
    Markdown leaderboard is portable across environments. ``repo_root``
    defaults to ``ui_dir.parent.parent`` (i.e. the dir containing
    ``rcm_mc/``).
    """
    if repo_root is None:
        repo_root = ui_dir.parent.parent
    scores: List[FidelityScore] = []
    for py in sorted(ui_dir.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        if py.name.startswith("_test") or py.name == "__init__.py":
            continue
        if py.name.startswith("_"):
            # Underscore-prefixed = helper / kit module by Python
            # convention. Not a route renderer.
            continue
        s = score_file(py)
        if s is not None:
            try:
                s.file = str(py.relative_to(repo_root))
            except ValueError:
                s.file = str(py)
            scores.append(s)
    return scores


def render_markdown_leaderboard(
    scores: List[FidelityScore],
    *,
    threshold: int,
) -> str:
    """Sorted-by-score Markdown report, with a pass/fail divider."""
    scores = sorted(scores, key=lambda s: (-s.score, s.file))
    passing = [s for s in scores if s.score >= threshold]
    failing = [s for s in scores if s.score < threshold]
    lines = [
        "# V5 Fidelity Report",
        "",
        f"Audited {len(scores)} renderer files in `rcm_mc/ui/`. ",
        f"Passing threshold: **{threshold}/100**.",
        "",
        f"- **{len(passing)} above threshold** — chartis-grade",
        f"- **{len(failing)} below threshold** — needs editorial cycle",
        "",
        "Run `python tools/v5_fidelity_audit.py` to refresh.",
        "",
        "---",
        "",
        "## Above threshold",
        "",
        "| Score | File | LOC | Primitives | Notes |",
        "|---|---|---|---|---|",
    ]
    for s in passing:
        notes = "; ".join(s.notes) if s.notes else "—"
        lines.append(
            f"| {s.score} | `{s.file}` | {s.loc} | "
            f"{s.primitive_count} ({s.primitive_density:.1f}/100) | {notes} |"
        )
    lines.extend([
        "",
        "## Below threshold",
        "",
        "Sorted highest score first — these pages are partially "
        "editorial. Lowest scorers are the next ports.",
        "",
        "| Score | File | LOC | Primitives | Notes |",
        "|---|---|---|---|---|",
    ])
    for s in failing:
        notes = "; ".join(s.notes) if s.notes else "—"
        lines.append(
            f"| {s.score} | `{s.file}` | {s.loc} | "
            f"{s.primitive_count} ({s.primitive_density:.1f}/100) | {notes} |"
        )
    return "\n".join(lines) + "\n"


def render_human_leaderboard(
    scores: List[FidelityScore],
    *,
    threshold: int,
    out=sys.stdout,
) -> None:
    """Compact terminal banner — top 10 + bottom 10."""
    scores = sorted(scores, key=lambda s: (-s.score, s.file))
    passing = [s for s in scores if s.score >= threshold]
    failing = [s for s in scores if s.score < threshold]
    out.write(f"\n  V5 Fidelity Audit  ({len(scores)} renderers)\n")
    out.write(f"  {'─' * 70}\n")
    out.write(
        f"  Threshold: {threshold}/100  ·  "
        f"Passing: {len(passing)}  ·  Failing: {len(failing)}\n\n"
    )
    out.write("  Top 10:\n")
    for s in scores[:10]:
        out.write(f"    {s.score:>3}  {s.file}\n")
    out.write("\n  Bottom 10 (next port targets):\n")
    for s in scores[-10:]:
        out.write(f"    {s.score:>3}  {s.file}\n")
    out.write(f"  {'─' * 70}\n\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="v5_fidelity_audit",
        description=(
            "Score every UI renderer against chartis editorial signals. "
            "Outputs a leaderboard for prioritising the next editorial-"
            "polish cycle."
        ),
    )
    p.add_argument(
        "--ui-dir", default=None,
        help="Path to rcm_mc/ui (default: auto-detect from this script's location)",
    )
    p.add_argument(
        "--threshold", type=int, default=70,
        help="Pass/fail threshold 0-100 (default 70)",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit JSON instead of human banner",
    )
    p.add_argument(
        "--md", default=None,
        help="Write a Markdown leaderboard to this path",
    )
    args = p.parse_args(argv)

    if args.ui_dir:
        ui_dir = Path(args.ui_dir)
    else:
        # tools/ is a sibling of rcm_mc/. Walk one up and into ui.
        ui_dir = Path(__file__).parent.parent / "rcm_mc" / "ui"
    if not ui_dir.exists():
        sys.stderr.write(f"ui dir not found: {ui_dir}\n")
        return 2

    scores = audit_tree(ui_dir)
    if args.md:
        Path(args.md).write_text(
            render_markdown_leaderboard(scores, threshold=args.threshold),
            encoding="utf-8",
        )
        sys.stderr.write(f"wrote {args.md}\n")
    if args.json:
        sys.stdout.write(json.dumps({
            "threshold": args.threshold,
            "scores": [asdict(s) for s in scores],
        }, indent=2) + "\n")
    elif not args.md:
        render_human_leaderboard(
            scores, threshold=args.threshold, out=sys.stdout,
        )

    failing = sum(1 for s in scores if s.score < args.threshold)
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
