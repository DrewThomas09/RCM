# Finance

Reimbursement and revenue-realization modeling. Encodes the economic structure of how hospitals get paid -- making the EBITDA impact of operational metrics sensitive to payer mix and reimbursement method rather than applying uniform multipliers.

| File | Purpose |
|------|---------|
| `reimbursement_engine.py` | Models per-method reimbursement sensitivity (DRG-prospective, capitation, fee-for-service, etc.) with explicit mechanism tables, transparent inference, and provenance tagging |

## Key Concepts

- **Method-sensitive economics**: A 1% denial rate reduction is worth more on a DRG-prospective hospital than a capitated one; this module makes that structure explicit.
- **Mechanism tables over opaque functions**: Every reimbursement method has a `MethodSensitivity` entry encoding its sensitivity to each RCM lever on a 0-1 scale.
- **Transparent inference**: Whenever a gap is filled (method distribution, discount, timing), the field is tagged in the profile's provenance dict.
