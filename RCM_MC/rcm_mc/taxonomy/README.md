# taxonomy/

The **healthcare-subsector taxonomy** — the modular, subsector-aware
analytical layer. A dermatology roll-up, an ASC, a home-health agency, and an
MA plan are diligenced with fundamentally different metrics, reimbursement
mechanics, data sources, and exhibits. This package codifies that as a
~55-subsector map (59 entries today) across **six groupings**, each wired to
its own KPI pack, billing codes, public datasets, 2025-26 thesis/risks, and CDD
exhibit templates.

This is the Stage-1 "subsector taxonomy object": the structured layer the rest
of the workbench reads to specialise its generic TAM/PVM/payer-mix toolkit per
subsector, instead of treating every target as a hospital.

| File | Purpose |
|------|---------|
| `models.py` | `Grouping` enum, `KPI`, and the `Subsector` frozen dataclass |
| `registry.py` | The ~55-subsector data + lookups (`by_id`, `by_grouping`, `search`, …) |

## The six groupings

| Grouping | Subsectors (examples) |
|----------|-----------------------|
| Provider Services / PPM | dermatology, ophthalmology, GI, ortho, cardiology, urology, ENT, **dental/DSO**, anesthesiology, radiology, primary care, OB-GYN, fertility, pain, plastics, veterinary |
| Facility-Based Care | **ASC**, hospitals, behavioral health (psych/SUD/ABA/IDD), SNF, **home health**, **hospice**, IRF/LTACH, urgent care, dialysis, infusion, imaging, freestanding ER |
| Healthcare IT / Tech-Enabled | **RCM**, EHR/PM, payments, pop-health, telehealth, RPM, ambient AI scribe, data/analytics, prior-auth |
| Payer / Risk-Bearing | Medicare Advantage, Medicaid MCO, **VBC enablers**, ACOs, TPAs, PBMs, dental/vision benefits |
| Pharma Services / Life Sciences | CRO, CDMO, specialty pharmacy, trial sites/SMO, pharmacovigilance, lab/diagnostics |
| Consumer / Other | medspas, hearing aids, DME, staffing, med-ed, healthcare real estate |

**Bold** entries are the seven Part-D "most central" archetypes flagged
`central=True` and carrying an extra `deep_dive` diligence note.

## Crosswalks (no duplication)

Each `Subsector` crosswalks to structures that already exist rather than
re-listing codes:

- `Subsector.vertical` → the first-class
  `rcm_mc.verticals.registry.Vertical` enum (HOSPITAL / ASC / MSO /
  BEHAVIORAL_HEALTH) when one of the four specialised metric registries
  already covers it.
- `Subsector.nucc_verticals` → the PE-vertical tags in
  `rcm_mc.data_public.nucc_taxonomy`, so a subsector turns into a live NPPES
  provider-supply count.

Both are empty when no clean mapping exists — an honest gap beats an
approximate bucket (same convention as `nucc_taxonomy.VERTICAL_NAICS`).

## Design

Pure data + frozen dataclasses: **no network, no SQLite, no fabricated
benchmarks**. KPI `benchmark` strings are free-text (`"~98% target, often
<85%"`) because they are directional trade/advisory ranges — encoding them as
hard floats would imply a precision the sources do not support. The registry
self-validates at import (duplicate-id guard) to keep the single-source-of-truth
invariant honest.

## CLI

```
rcm-mc taxonomy groupings              # the six groupings + counts
rcm-mc taxonomy list [--grouping G]    # all subsectors (optionally one grouping)
rcm-mc taxonomy show <id>              # full diligence card for one subsector
rcm-mc taxonomy search <query>         # match id/name/business-model/thesis/risks
rcm-mc taxonomy central                # the seven most-central archetypes
```

Add `--json` to any subcommand for machine-readable output.

## Usage

```python
from rcm_mc.taxonomy import by_id, by_grouping, search, Grouping

derm = by_id("dermatology")
derm.kpis                      # (KPI(name="Visits per provider per day", ...), ...)
derm.exhibits                  # ("Provider productivity vs MGMA", ...)

by_grouping(Grouping.FACILITY_BASED)        # 15 facility subsectors
search("site-of-service")                   # [orthopedics, cardiology, ...]
```
