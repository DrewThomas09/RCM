# Episode-of-Care Grouping + Service-Line P&L

**In one sentence**: rolls raw claim lines up into anchor-triggered episodes of care, then reports cost-per-episode distributions and a service-line P&L — the unit PE actually underwrites on.

---

## What problem does this solve?

Claim lines are the wrong unit. A buyer underwrites the **episode** — an inpatient stay and everything that hangs off it, a surgical bundle and its 90-day follow-up — because that's what payers bundle, where margin accrues, and what an operator can manage. Raw line-by-line cost tells you nothing about whether the *episode* is profitable or which service line bleeds.

Partners ask:
- *"What does a typical episode cost here, and how fat is the tail?"*
- *"Which service lines make money and which lose it?"*
- *"What's the cost concentration by anchor type?"*

---

## How it works

**Anchor-triggered** (the CMS-BPCI shape): an episode follows the patient's care, not the calendar.

1. Anchor claims (`inpatient`, `surgery`, …) each open a window `[day − pre, day + post]`.
2. Overlapping windows for the same patient **merge** into one episode (a Dec-28 admit + Jan-9 readmit is one clinical episode, not two).
3. Every claim falling inside a window is assigned to it; claims outside all windows are reported as `unassigned` (coverage is visible, not silently dropped).
4. Rollups: cost-per-episode mean/median/P90, cost by anchor type, and a service-line P&L (episode revenue allocated to lines by cost share when not itemized).

## The demo moment

```python
from rcm_mc.diligence.episodes import ClaimLine, EpisodeDefinition, group_episodes

defn = EpisodeDefinition(
    anchor_service_lines=frozenset({"inpatient", "surgery"}),
    post_window_days=90,
)
res = group_episodes(claims, defn)
print(res.headline)
for p in res.service_line_pnl:
    print(p.service_line, p.total_cost, p.margin)
```

> 1,284 episodes (mean cost $14,302.55, median $9,110.00, P90 $38,420.00); most common anchor: inpatient (902). ⚠ 2 service line(s) margin-negative; worst: rehab (-$1.20M).

---

## Where it plugs in

- **QoE / financial diligence** — cost-per-episode and service-line margin are the decision-useful cuts.
- **`pmpm`** — episodes give a per-episode denominator complementary to PMPM.
- **Provenance graph** — outputs carry `source_module="diligence.episodes"` and `citation_key="EP1"`.

## Files

```
episodes/
├── __init__.py
└── grouper.py    # ClaimLine / EpisodeDefinition / group_episodes + service-line P&L
```

## Tests

```bash
python -m pytest tests/test_episodes.py -q
# Expected: 10 passed
```
