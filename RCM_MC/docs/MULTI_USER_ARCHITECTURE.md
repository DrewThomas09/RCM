# Multi-User Platform Architecture

The platform already has substantial multi-user foundations: scrypt
password hashing, session cookies, a 6-tier role hierarchy
(`ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER`), per-route
permission enforcement, full audit logging, and per-deal external-
user access grants. What's missing is the **collaboration layer
on top** — deal teams, threaded discussion, mentions, presence,
notifications, change history per resource.

This document maps the path from the existing single-analyst-friendly
auth system to a true multi-user collaboration platform.

## What exists today

| Component | Module | Status |
|---|---|---|
| Password auth | `auth/auth.py` | scrypt + per-user salt + constant-time verify |
| Sessions | `auth/auth.py` | 7-day TTL, rotate on re-login |
| Roles | `auth/rbac.py` | 6-tier (admin/partner/vp/associate/analyst/viewer) |
| Permission gates | `auth/rbac.py` | `require_permission` decorator on routes |
| Audit log | `auth/audit_log.py` | every state-changing action logged |
| Per-deal access | `auth/external_users.py` | grant/revoke/list/check for outside reviewers |
| Preferences (per-user) | `ui/preferences.py` | favorites + custom widgets + notifications |
| CSRF | `server.py` | per-session secret + form-patch JS |
| Rate-limit | `server.py` | login throttle |

The auth + audit foundations are PE-grade. What's missing is everything
above the auth line — the **team workflow**.

## Gap analysis

### 1. Deal teams (multi-user assignment to one deal)

**Today**: A deal has one `owner`. `external_users` grants per-deal
access but there's no concept of an *active deal team* with roles
inside the team (lead VP, supporting analyst, partner sponsor).

**Need**:
- `DealTeam` schema: per-deal team membership with role-on-deal
  (`lead`, `supporting`, `reviewer`, `observer`).
- Multiple users per deal; one user can be on N deals with different
  in-team roles per deal.
- Deal-team role drives notification + permission scope (a 'reviewer'
  can comment but not edit; an 'observer' can read but not
  comment).

### 2. Threaded discussion + comments

**Today**: `deal_notes` table allows append-only notes per deal.

**Need**:
- Threaded comments anchored to specific resources: a metric value,
  a chart annotation, a packet section, a row in a power_table.
- Reply chains (parent_comment_id).
- Resolved/unresolved state — partner closes a thread when the
  question is answered.
- Comment renders inline next to the resource (e.g., a tiny chat-
  bubble icon next to denial_rate; click expands the thread).

### 3. @mentions + notifications

**Today**: No @mentions. `preferences.notifications` has flags but
no delivery layer.

**Need**:
- `@username` parsed in comments → notification record created.
- Notifications surface: in-app dropdown (top-right bell icon),
  optional email via webhook config, optional Slack via webhook.
- Notification feed at `/notifications` showing unread + history.
- Per-event types: comment-mention, deal-stage-advanced, packet-
  rebuilt, alert-fired, deadline-approaching.

### 4. Real-time presence

**Today**: No way to know who else is on a deal right now.

**Need**:
- Lightweight presence beacons (vanilla JS heartbeat to
  `/api/presence` every 30s, fades after 60s).
- Avatar stack on deal pages showing currently-viewing users.
- 'Last viewed by Alice 2 hours ago' inline on deal cards.

Important: this is **not** real-time editing. Single-user-edit-at-a-
time with optimistic concurrency control is enough for diligence
work; full Google-Docs-style CRDTs are over-investment.

### 5. Change history per resource

**Today**: `audit_log` tracks user actions. No per-resource view
('show me everything that changed on Project Aurora this week').

**Need**:
- Resource-scoped change feed: `/deal/<id>/history` shows every
  change (numbers updated, scenarios saved, comments posted, stage
  advanced) in chronological order with diff.
- Per-metric history: hover a number → click → see when it changed,
  who changed it, from-what-to-what. Anchors to the audit log.

### 6. Granular permissions per resource

**Today**: `rbac.py` permissions are flat strings per role. Every
ANALYST has same permissions on every deal.

**Need**:
- Per-deal permission overrides — e.g., 'analyst Bob is the lead on
  Aurora and can override numbers; on Borealis he's a reviewer and
  can only comment'. Bridges role-level + deal-team-role-level
  permissions.
- Deal-level visibility flag — confidential deals hidden from
  general ANALYSTs not on the team.

## Architecture

### Schema additions

```sql
-- Deal team membership
CREATE TABLE deal_team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    username TEXT NOT NULL,
    team_role TEXT NOT NULL,
        -- 'lead' | 'supporting' | 'reviewer' | 'observer'
    added_at TEXT NOT NULL,
    added_by TEXT NOT NULL,
    UNIQUE(deal_id, username)
);
CREATE INDEX idx_dtm_deal ON deal_team_members(deal_id);
CREATE INDEX idx_dtm_user ON deal_team_members(username);

-- Threaded comments
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type TEXT NOT NULL,
        -- 'deal' | 'packet_section' | 'metric' | 'scenario'
    resource_id TEXT NOT NULL,
    deal_id TEXT,           -- denormalized for fast deal-scoped query
    parent_id INTEGER,      -- null = top-level; else replies
    author_username TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT,       -- null = open
    resolved_by TEXT,
    FOREIGN KEY (parent_id) REFERENCES comments(id)
);
CREATE INDEX idx_comments_resource
    ON comments(resource_type, resource_id);
CREATE INDEX idx_comments_deal
    ON comments(deal_id, created_at);

-- Notifications
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_username TEXT NOT NULL,
    kind TEXT NOT NULL,
        -- 'mention' | 'stage_advanced' | 'packet_rebuilt' |
        -- 'alert_fired' | 'deadline_approaching' | 'comment_reply'
    subject_id TEXT,        -- deal_id, comment_id, etc.
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,           -- null = unread
    delivered_email INTEGER DEFAULT 0,
    delivered_slack INTEGER DEFAULT 0
);
CREATE INDEX idx_notif_recipient
    ON notifications(recipient_username, read_at, created_at);

-- Presence
CREATE TABLE presence (
    username TEXT NOT NULL,
    deal_id TEXT NOT NULL,
    last_beacon_at TEXT NOT NULL,
    PRIMARY KEY (username, deal_id)
);
CREATE INDEX idx_presence_deal
    ON presence(deal_id, last_beacon_at);
```

### Module structure

```
rcm_mc/collab/
├── __init__.py
├── deal_teams.py        # add/remove/list/role
├── comments.py          # post/reply/resolve/list
├── mentions.py          # parse @username from comment body
├── notifications.py     # create/list/mark-read/deliver
├── presence.py          # beacon + active-users-on-deal
├── change_history.py    # per-resource diff feed
└── permissions.py       # per-deal permission resolution
```

### Public API surface

```python
# Deal teams
from rcm_mc.collab.deal_teams import (
    add_team_member, remove_team_member,
    list_team, list_user_deals, change_role,
)

add_team_member(
    store, deal_id="aurora",
    username="alice", team_role="lead",
    added_by="partner_smith")

# Comments
from rcm_mc.collab.comments import (
    post_comment, list_comments,
    resolve_thread, count_unresolved,
)

post_comment(
    store, resource_type="metric",
    resource_id="aurora.denial_rate",
    deal_id="aurora",
    author="alice",
    body="@bob — peer median is 8.2%, not 8.5%")

# Notifications
from rcm_mc.collab.notifications import (
    list_unread, mark_read, create_notification,
)

unread = list_unread(store, "alice")  # → list[Notification]

# Presence
from rcm_mc.collab.presence import (
    beacon, list_active_on_deal,
    cleanup_stale,
)

beacon(store, "alice", "aurora")
viewers = list_active_on_deal(
    store, "aurora", since_seconds=60)

# Permission resolution
from rcm_mc.collab.permissions import (
    can_user_do_on_deal,
)

can_user_do_on_deal(
    store, username="alice", deal_id="aurora",
    action="set_override")
# → True if her in-team role permits + her global role permits
```

### Deal-team-role permission matrix

| Action | lead | supporting | reviewer | observer |
|---|---|---|---|---|
| Read | ✓ | ✓ | ✓ | ✓ |
| Comment | ✓ | ✓ | ✓ | ✗ |
| Update notes | ✓ | ✓ | ✗ | ✗ |
| Set numeric override | ✓ | ✓ | ✗ | ✗ |
| Resolve comment | ✓ | ✗ | ✓ | ✗ |
| Advance stage | ✓ | ✗ | ✗ | ✗ |
| Add team member | ✓ | ✗ | ✗ | ✗ |

`can_user_do_on_deal()` resolves: action allowed ↔ user is on the team
AND in-team role permits AND global RBAC role permits. Triple gate
prevents accidental over-grant.

### UI changes

**Deal-team panel** (right sidebar of `/deal/<id>/profile`):
- Avatars + roles, click avatar → user profile page.
- Add-member dropdown (visible to leads + admins).
- Active-now indicators using `presence`.

**Inline comments** on every metric / chart / packet section:
- Tiny chat-bubble icon next to a metric value; count badge if
  comments exist; red dot if unresolved.
- Click expands a thread panel (right slide-in drawer pattern).
- Markdown formatting + @mention autocomplete (vanilla JS query
  to `/api/users?q=` for username completion).

**Notifications**:
- Bell icon in header (already-built `dashboard_v3` header has
  link strip; add the bell + unread count).
- Click expands dropdown showing 10 most-recent unread; 'See all'
  links to `/notifications`.
- New `/notifications` page reuses `power_table` for filterable
  notification feed.

**Change history**:
- `/deal/<id>/history` — chronological feed using existing
  `power_table` (filterable by user / kind / date range / metric).
- Inline 'history' link next to every modeled number; click opens
  the metric-specific history panel.

**Permission UX**:
- When a user lacks permission, the action button shows an info
  icon — hover reveals 'You're a Reviewer on this deal; only Leads
  can advance the stage'. Clear partner-readable copy, no silent
  failures.

### Notification delivery channels

In-app delivery is built-in. Email + Slack are opt-in via
preferences:

```
rcm_mc/collab/notifications.py
├── deliver_inapp(notification)      # always
├── deliver_email(notification)      # opt-in
└── deliver_slack(notification)      # opt-in via webhook URL
```

Each delivery channel is a pluggable function called by
`create_notification()` based on the recipient's preferences. Email
delivery hits `RCM_MC_SMTP_*` env config; Slack hits a per-user
webhook URL stored on `UserPreferences.notifications.slack_webhook`.

Both channels degrade gracefully — if SMTP is unconfigured, in-app
notifications still appear; the user just doesn't get email. No
hard failure when external services are down.

## Build sequence

### Phase 1 — Deal teams + permissions (3 weeks)

1. **Week 1**: `deal_teams.py` schema + CRUD + tests. Migrate
   existing `Deal.owner` → seed `deal_team_members` with that user
   as `lead`.
2. **Week 2**: `permissions.can_user_do_on_deal()` resolver +
   permission matrix. Refactor existing `require_permission` to
   call the new resolver for deal-scoped actions.
3. **Week 3**: Deal-team panel UI on `/deal/<id>/profile`.
   Add-member modal + role-change UX. End-to-end test:
   non-team-member gets 403 on edit actions.

### Phase 2 — Threaded comments + mentions (4 weeks)

1. **Week 1**: `comments.py` schema + CRUD with parent_id chain.
2. **Week 2**: `mentions.py` parser + auto-create notifications
   for mentioned users.
3. **Week 3**: Inline comment-bubble UI on metrics + power_table
   rows; right-drawer thread panel.
4. **Week 4**: @mention autocomplete + Markdown rendering +
   resolve/reopen flow.

### Phase 3 — Notifications + delivery (3 weeks)

1. **Week 1**: `notifications.py` schema + create + list + mark-read.
   Auto-create on stage_advanced, packet_rebuilt, alert_fired,
   deadline_approaching, comment_reply, mention.
2. **Week 2**: Bell-icon header dropdown + `/notifications` page.
3. **Week 3**: Email + Slack delivery channels. Per-user opt-in via
   `UserPreferences.notifications`. Graceful-degrade tests.

### Phase 4 — Presence + change history (3 weeks)

1. **Week 1**: `presence.py` beacon endpoint + cleanup-stale cron.
   Avatar-stack UI on deal pages.
2. **Week 2**: `change_history.py` materialized view from audit_log,
   keyed by resource_type + resource_id.
3. **Week 3**: `/deal/<id>/history` page + inline 'history' link
   next to every metric.

**Total: 13 weeks for the full collaboration layer.**

If parallelized across two engineers: ~7-8 weeks.

## What's intentionally NOT in scope

- **Real-time concurrent editing** (Google-Docs-style CRDTs) —
  diligence work is not concurrent; single-user-edit-at-a-time with
  optimistic concurrency is sufficient and avoids 10× the
  engineering complexity.
- **Video / voice / screen-share** — partner shops have Zoom and
  Teams. The platform should be embeddable in those, not replace
  them.
- **Federated identity / SSO** — the current scrypt-based local auth
  works. SAML / OIDC are infrastructure work that can layer on
  later when an enterprise customer needs them. Plan in `auth/`,
  not `collab/`.
- **Mobile push notifications** — the `RCM_MC_DASHBOARD` settings
  + email/Slack delivery cover the partner-on-the-road case
  through tools they already use.

## Risk + mitigation

- **Notification fatigue**: every action firing a notification → bell
  icon perpetually red. Mitigation: `UserPreferences.notifications`
  per-event-kind toggles; default conservative (only mentions +
  high-severity alerts on by default).
- **Comment spam / abuse**: in a small partner shop, low risk. Add
  rate-limit (10 comments/min per user) to prevent runaway bots.
- **Performance**: 1000 unresolved comments on a hot deal → slow
  panel render. Mitigation: pagination on threads; only show
  unresolved by default; collapsed-by-default deep replies.
- **Permission over-grant**: triple-gate (global role + team
  membership + in-team role) prevents accidental escalation;
  every state-changing action goes through `can_user_do_on_deal()`
  with audit_log entry.
- **Schema migration**: existing single-owner deals need to seed
  `deal_team_members` with the owner as `lead`. Migration runs
  idempotently on first read (lazy-seed pattern).

## Success metrics

After full rollout:

- **Team coordination**: Partner asks 'who's on this deal?' → one
  click on the deal-team avatar stack. Today this is a Slack thread.
- **Decision audit**: 'Why did the EBITDA target change last week?'
  → one click on the metric history. Today this is grep'ing emails.
- **Cross-deal awareness**: 'Show me every deal Bob's working on' →
  one query. Today this is asking Bob.
- **Onboarding velocity**: New analyst joins → can read every deal
  thread to ramp up on context. Today they shadow for 3 months.

The collaboration layer doesn't make individual diligence work
faster. It makes the *team* effective — coordination cost drops,
context handoff drops, decision audit becomes one-click. That's
what 5+-person investment shops need.
