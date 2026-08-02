# Report 0274: Transaction-Boundary + Auth/Session Sweeps — both clean (no code change)

## Scope

Two inline verification sweeps this iteration, both **clean** — recorded so the audit chain shows these classes were checked, not skipped. (Ultracode is off this iteration, so these were done as direct inline reviews rather than multi-agent workflows.)

## Sweep 1 — SQLite transaction boundaries (check-then-write races)

CLAUDE.md requires `BEGIN IMMEDIATE` around any check-then-write sequence. Verified the rule holds:

- The genuine multi-statement check-then-write sites **already use** `BEGIN IMMEDIATE`: `deals/deal_deadlines`, `deals/watchlist`, `auth/auth`, `compliance/audit_chain`, `portfolio/{peer_sets, saved_screens, screen_snapshots, saved_charts}`, `ui/preferences`, `dev/seed`, and the three `portfolio/store` methods (`upsert_deal`, `delete_deal`, `clone_deal`).
- The write helpers **without** `BEGIN IMMEDIATE` (deal_tags, note_tags, approvals, comments, deal_stages, deal_owners, deal_sim_inputs, health_score, remark, value_creation_plan, hold_tracking, covenant_metrics, portfolio_snapshots, alert_acks, alert_history) are **not** check-then-write — each is a single INSERT/UPDATE (atomic on its own) or an `INSERT OR IGNORE` / `ON CONFLICT` upsert against a UNIQUE index (deal_tags/note_tags), which is atomic and idempotent by construction. No lost-update or duplicate-row race.

**Verdict: clean.** The transaction-boundary convention is correctly applied where it matters and correctly omitted where a single statement already provides atomicity.

## Sweep 2 — auth / session handling

Reviewed `auth/auth.py` end-to-end:

- **Passwords:** stdlib `hashlib.scrypt`, length-capped before hashing (B150) so a giant password can't DoS the KDF; verified with `hmac.compare_digest` (constant-time).
- **Session tokens:** 32-byte `secrets.token_urlsafe`; looked up by primary key.
- **Expiry:** two gates — absolute TTL (`expires_at`) and idle timeout (`last_seen_at`, default 30 min, env-overridable), both compared against a timezone-aware `_utcnow()`. `expires_at` is written from an aware datetime (`create_session`), so the aware-vs-naive comparison never raises; malformed timestamps are caught and treated as expired.
- **Idle cleanup** deletes the stale session row; the sliding-window `touch` UPDATE is wrapped in a documented best-effort swallow ("touching the session must never break auth") — legitimate, not the swallow class from Report-0273.

**Verdict: clean.** No timing, expiry, or transaction defect found.

## Why record a no-change iteration

Reports 0272 (render-surface XSS), this one, and the SQL-vein note in 0273 are negative results by design. After the deal_id class (0267-0269), CSV injection (0270), and the swallow sweep (0273, 5:1 refute), the security/reliability veins are showing diminishing returns — documenting the clean sweeps prevents future audit passes from re-treading them and honestly reflects that the codebase's write/security hygiene is solid.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | Shift to correctness/coverage rather than security: the `data_public/` CMS-loader data-integrity (row-count reconciliation), or a never-mapped package inventory (`pe_intelligence/`). Pace is lengthening as finds get sparser. |

---

Report/Report-0274.md written.
