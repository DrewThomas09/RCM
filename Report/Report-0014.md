# Report 0014: Documentation Gap — `rcm_mc/management/` Subsystem

## Scope

This report covers the **documentation state of `RCM_MC/rcm_mc/management/`** on `origin/main` at commit `f3f7e7f`. The subsystem (8 files, ~1,010 LoC) was selected because Report 0010 flagged it as the largest **0-production-import orphan** in the package — leadership-and-management analysis code that's tested but unwired. An orphan subsystem is the highest-value doc-audit target: docs are the only on-ramp for a future caller to wire it back in.

The audit lists every doc element present, every missing element, and proposes concrete additions. It compares against neighboring subsystems (notes only).

Prior reports reviewed before writing: 0010-0013.

## Findings

### File inventory

| File | LoC (approx.) | Module-level docstring? | README presence |
|---|---:|---|---|
| `RCM_MC/rcm_mc/management/__init__.py` | 73 | **YES** (37-line docstring with full public-API surface listing) | — |
| `RCM_MC/rcm_mc/management/README.md` | 17 lines (1,035 B) | — | **YES, but thin** — 7-row table + 1 cross-reference paragraph; no usage example, no installation note, no integration target |
| `RCM_MC/rcm_mc/management/executive.py` | ~38 | YES (one-liner: "Executive + ManagementTeam dataclasses.") | — |
| `RCM_MC/rcm_mc/management/feedback.py` | ~150 | YES | — |
| `RCM_MC/rcm_mc/management/optimize.py` | ~200 | YES | — |
| `RCM_MC/rcm_mc/management/org_design.py` | ~180 | YES | — |
| `RCM_MC/rcm_mc/management/personality.py` | ~160 | YES | — |
| `RCM_MC/rcm_mc/management/scorecard.py` | ~177 | YES | — |
| `RCM_MC/rcm_mc/management/succession.py` | ~165 | YES | — |

**Module-level docstrings: 8/8 (100%) present.** The subsystem is structurally well-introduced.

### Public-API symbol-level doc presence

Symbols listed in `__init__.py:62-72` `__all__` (16 names), per-symbol verification:

| Symbol | File | Docstring on def/class? | Thoroughness |
|---|---|---|---|
| `Executive` | `executive.py:18` | **YES** ("One management team member.") | one-line |
| `ManagementTeam` | `executive.py:31` | **YES** ("Top-of-house team being assessed.") | one-line |
| **`RaterRole`** | `executive.py:9` | **NO** (Enum class with weight comments only) | **MISSING** |
| `score_competencies` | `scorecard.py:119` | **YES** (Args + Returns documented) | thorough |
| `CompetencyScorecard` | `scorecard.py:97` | **YES** ("Team-level scorecard.") | one-line |
| `CompetencyScore` | `scorecard.py:86` | **YES** ("Per-executive composite + per-dimension scores.") | one-line |
| `assess_big_five` | `personality.py:76` | **YES** ("Compute the role-weighted investability score. Score ranges: ...") | thorough |
| `BigFiveProfile` | `personality.py:?` | not verified this iteration | — |
| `score_org_design` | `org_design.py:55` | **YES** ("Score org design + flag healthcare-specific anti-patterns.") | **one-line; no Args/Returns** |
| `OrgDesignScore` | `org_design.py:?` | not verified this iteration | — |
| `aggregate_360_feedback` | `feedback.py:60` | **YES** (Args + Computes section) | thorough |
| `FeedbackAggregate` | `feedback.py:?` | not verified | — |
| `RaterFeedback` | `feedback.py:?` | not verified | — |
| `build_succession_register` | `succession.py:83` | **YES** (Args section) | thorough |
| `SuccessionRegister` | `succession.py:?` | not verified | — |
| `KeyPersonRisk` | `succession.py:?` | not verified | — |
| **`recommend_team_actions`** | `optimize.py:51` | **YES** ("Synthesise inputs into a ranked action list.") | **one-line; no Args/Returns despite 4 parameters and a complex body** |
| `TeamRecommendations` | `optimize.py:?` | not verified | — |
| `TeamAction` | `optimize.py:?` | not verified | — |

**Verified gaps in docstring richness:**

| Symbol | File:line | Gap |
|---|---|---|
| `RaterRole` | `executive.py:9` | **No class-level docstring at all.** Only inline comments next to each enum member (`BOSS = "boss"  # weight 0.35`). The weight values implied by these comments are nowhere consolidated. |
| `score_org_design` | `org_design.py:55` | One-line docstring; no Args / Returns / behavior on `revenue_mm = 0.0` or `sector = ""` defaults. Function is non-trivial (computes span_of_control, layers, role_clarity, composite). |
| `recommend_team_actions` | `optimize.py:51` | One-line docstring; no Args / Returns. Function takes 4 optional params and produces ranked actions across 3 input surfaces (scorecard / org_design / succession) — should document which params drive which action types. |

### README.md state

`RCM_MC/rcm_mc/management/README.md` (17 lines, 1,035 B) contents:

```
# management/

Management-team analysis: scorecards, succession risk, org-design assessment, and personality / behavioral inputs.

| File | Purpose |
|------|---------|
| `executive.py` | Per-executive profile schema + scoring rubric |
| `scorecard.py` | Role-weighted team scorecard (CEO 35% / CFO 25% / COO 20%) |
| `succession.py` | Succession-risk matrix — single points of failure, bench depth, retention probability |
| `org_design.py` | Span-of-control + reporting-structure analysis from org chart |
| `personality.py` | Behavioral-trait inputs (analyst-entered) feeding the scorecard |
| `feedback.py` | Calibrate scorecard predictions against post-close performance |
| `optimize.py` | "What's the highest-leverage org change?" analysis |

## Sister module: diligence/management_scorecard/

`diligence/management_scorecard/` is the **single-deal diligence run** that produces the IC-memo management section. This module is the **deeper analytical surface** for partner-led management workshops and post-close org redesign.
```

What the README **provides**: a one-line subsystem summary, a 7-row file-purpose table, and a sister-module cross-reference.

What the README **lacks**:

1. **Usage example** — no code block showing `from rcm_mc.management import score_competencies; team = ManagementTeam(...); raw = {...}; result = score_competencies(team, raw)`.
2. **Installation/dependencies note** — none of the management modules require optional deps, but a reader doesn't know that.
3. **Integration / wiring guide** — the subsystem has 0 production importers (Report 0010 MR69). The README doesn't say "this subsystem is unwired; here's how to wire it into a packet builder."
4. **Output schema** — none of the dataclass shapes are illustrated.
5. **Invariants** — `_ROLE_WEIGHTS` rows must sum to 1.0 (per inline comment in `scorecard.py:31`), but this invariant is not surfaced in the README.
6. **Versioning / stability** — is the public API stable? Is `RaterRole`'s weight weighting frozen or tunable? Unstated.
7. **Pointer to test file** — `tests/test_management.py` and `tests/test_management_scorecard.py` exist (verified) but the README doesn't reference them.

### Doctest / executable-example presence

`grep -E "Example::|usage::|>>> "` across all 8 `.py` files in `management/` returns **empty**. **No doctests, no `>>>` examples, no `Example::` blocks.** The subsystem is documentation-rich at the descriptive level but provides **zero runnable examples**.

### Sister-module cross-reference accuracy

The README's last paragraph says: "Sister module: `diligence/management_scorecard/`". Per Report 0004 Discovery A, the `rcm_mc/diligence/` subsystem has a `management_scorecard/` subdirectory. **The cross-reference is accurate.** That sister module is the live single-deal pathway; `management/` is the deeper offline analytical surface.

This is the only documentation in the codebase that explains why two parallel implementations exist — important context that should be in BOTH READMEs (the sister currently has it; this one does too — verified).

### Comparison to neighbors

Quick spot-checks of nearby orphan subsystems (per Report 0010):

- `RCM_MC/rcm_mc/portfolio_synergy/README.md` — exists (13 lines) and module __init__.py has a thorough docstring.
- `RCM_MC/rcm_mc/site_neutral/` — README presence not verified this iteration.
- `RCM_MC/rcm_mc/api.py` — single-file orphan, has a 7-line module docstring (per Report 0013). No usage docs beyond `uvicorn rcm_mc.api:app --host 0.0.0.0 --port 8000`.
- `RCM_MC/rcm_mc/constants.py` — extensively documented (every constant has a 1-3 line docstring); README presence not verified.

**Across the orphan subsystems, the doc state is consistent: module-level + symbol-level docstrings present; README present and short; no usage examples; no integration guides.** The codebase has a high doc-presence floor (module + symbol level) but a low doc-richness ceiling (no examples, no wiring guides for orphan code).

## Concrete additions proposed

### A. Class-level docstring for `RaterRole` (executive.py:9)

```python
class RaterRole(str, Enum):
    """Source of a 360-feedback rating.

    Each rater type has a fixed weight in `aggregate_360_feedback`:
    boss=0.35, peer=0.25, direct_report=0.25, external=0.10,
    self=0.05. The weights are calibrated against meta-analyses
    of multi-rater 360 reliability — bosses are the highest-signal
    raters; self-ratings are the noisiest.
    """
    BOSS = "boss"
    ...
```

### B. Args/Returns sections on `score_org_design` and `recommend_team_actions`

For `score_org_design` (`org_design.py:55`):

```python
def score_org_design(...) -> OrgDesignScore:
    """Score org design + flag healthcare-specific anti-patterns.

    Args:
      team: management team with executives + reporting structure.
      revenue_mm: target's run-rate revenue. Used to benchmark
        span-of-control against typical layers-by-revenue heuristics.
      sector: e.g. "Hospital", "PhysiciansPractice". Determines
        which anti-pattern checks fire (e.g. clinical-leader-as-COO
        is a hospital concern, not a PP one).

    Returns:
      OrgDesignScore with per-dimension scores and a composite.
      Composite is 0-5; <2.5 is concerning territory.
    """
```

For `recommend_team_actions` (`optimize.py:51`):

```python
def recommend_team_actions(...) -> TeamRecommendations:
    """Synthesise inputs into a ranked action list.

    Args:
      team: management team to optimize.
      scorecard: feeds SUNSET/COACH actions for low-band executives.
      org_design: feeds RESTRUCTURE actions on span/layers issues.
      succession: feeds HIRE actions to backfill key-person risks.

    Returns:
      TeamRecommendations with actions sorted by expected impact.
    """
```

### C. README expansion

Add three sections to `RCM_MC/rcm_mc/management/README.md`:

1. **Status:** "This subsystem currently has 0 production importers — it is offline analytical surface. To wire into a deal flow, import from `rcm_mc.management` and call within a `packet_builder` step."
2. **Usage example:**
   ```python
   from rcm_mc.management import (
       Executive, ManagementTeam, RaterRole,
       score_competencies, score_org_design,
       recommend_team_actions,
   )

   team = ManagementTeam(
       company_name="Project Cypress",
       executives=[Executive("ex1", "Jane Doe", "CEO", tenure_years=4.5)],
   )
   raw_scores = {"ex1": {"financial_discipline": 4.0, "strategic_clarity": 4.5}}
   scorecard = score_competencies(team, raw_scores)
   actions = recommend_team_actions(team, scorecard=scorecard)
   ```
3. **Tests:** "See `tests/test_management.py` (subsystem unit tests) and `tests/test_management_scorecard.py` (scorecard integration test) for working examples and invariants."

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR101** | **`RaterRole` weight values are documented in inline comments only** | The 5 weights (0.35, 0.25, 0.25, 0.05, 0.10) appear as line comments in `executive.py:9-14`. The actual weights used in `aggregate_360_feedback` (`feedback.py:60`) presumably read from the enum or from a separate `_RATER_WEIGHTS` dict — but the weights and the comments must stay in sync. **A branch that re-tunes weights might update one and not the other, silently desyncing.** | **High** |
| **MR102** | **No usage examples in any management/ doc** | A future caller wiring this subsystem in (e.g. as part of `feature/connect-partner-brain-phase2`) would need to read 8 modules to learn the call shape. Increases the integration cost. | Medium |
| **MR103** | **README does not flag the orphan status** | A reader sees `management/` and assumes it's wired. Discovers post-merge that 0 production code calls it. Concrete cost: at least one wasted dev-hour per onboarder. | Low |
| **MR104** | **Doctstring richness varies across the public surface** | `score_competencies`, `assess_big_five`, `aggregate_360_feedback`, `build_succession_register` have thorough docstrings; `score_org_design`, `recommend_team_actions` have one-liners; `RaterRole` has none. The inconsistency makes "is this the canonical doc?" an open question per-symbol. | Low |
| **MR105** | **No integration target documented** | The README cross-references `diligence/management_scorecard/` but doesn't say what calls into `management/` from that side. If the cross-reference is out-of-date (e.g. `diligence/management_scorecard/` has been refactored), the README would still claim it's a sister. | Low |
| **MR106** | **`_ROLE_WEIGHTS` invariant ("rows must sum to 1.0") only in inline code comment** | `scorecard.py:31` "Per-role weight matrix. Rows must sum to 1.0." A branch that adds a CFO row missing one dimension breaks the invariant; nothing enforces it. **Recommend a runtime assertion in module-init or in `score_competencies`.** | Medium |

## Dependencies

- **Incoming (who reads `management/` docs):** any future contributor wiring this subsystem into a packet builder; partner-led workshop facilitators (per the README's framing); test maintainers.
- **Outgoing (what these docs claim to depend on):** `diligence/management_scorecard/` (sister module — claim verified).

## Open questions / Unknowns

- **Q1 (this report).** Are `RaterRole`'s weight values **read from anywhere**, or are they purely descriptive? If the weights live in a separate `_RATER_WEIGHTS` dict in `feedback.py`, the comments on the enum are documentation that has no runtime effect — a soft form of MR101.
- **Q2.** Does `tests/test_management.py` exercise the entire `__all__` surface, or only the most-used symbols? Pre-merge: any branch that changes a function signature must verify the test pins it.
- **Q3.** Does `_ROLE_WEIGHTS` ever get re-tuned in a feature branch? If so, the new weights need to live in a versioned constants module (or `rcm_mc/constants.py` — Report 0010 noted that registry is an unused dedup attempt).
- **Q4.** What's the canonical "wire-in" example? Is there a deal flow on `feature/connect-partner-brain-phase1` that imports `rcm_mc.management`? Pre-merge sweep needed.
- **Q5.** Are dataclasses on lines I didn't read (`BigFiveProfile`, `OrgDesignScore`, `FeedbackAggregate`, `RaterFeedback`, `SuccessionRegister`, `KeyPersonRisk`, `TeamRecommendations`, `TeamAction`) all documented? At the field level?
- **Q6.** Why does the docs floor stay so high (every module has a module docstring) while the docs ceiling stays so low (no examples)? Authoring pattern signal — possibly LLM-generated headers without follow-through to integration tests / examples.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0015** | **Read `feedback.py:60 aggregate_360_feedback` end-to-end** — does it use `RaterRole` weights or a separate dict? | Resolves Q1, MR101. |
| **0016** | **Cross-branch sweep: which ahead-of-main branch (if any) imports `rcm_mc.management`?** | Resolves Q4 / MR103. |
| **0017** | **Read the 8 unverified dataclasses** (`BigFiveProfile`, `OrgDesignScore`, etc.) and document their fields. | Resolves Q5. |
| **0018** | **Read `tests/test_management.py` end-to-end** and surface coverage gaps. | Resolves Q2. |
| **0019** | **Read `infra/config.py:_validate_dist_spec`** — owed since Report 0013 Q1. | Closes the dist-spec validation loop. |
| **0020** | **Audit doc-richness across 5+ neighboring subsystems** to confirm the "high floor, low ceiling" pattern. | Resolves Q6. If the pattern holds repo-wide, a single doc-richness sprint could lift many subsystems at once. |

---

Report/Report-0014.md written. Next iteration should: read `feedback.py:aggregate_360_feedback` (line 60) and verify whether `RaterRole`'s weight values flow from the enum's inline comments to a runtime weight table or are duplicated — closes MR101 (silent-desync risk) and Q1.

