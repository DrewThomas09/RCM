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
