# DECISIONS — judgment calls made instead of stopping

Format: decision / alternative rejected / why.

## 2026-06-10 session

1. **Live-site verification protocol.** Decision: per merge, verify via (a)
   deploy.yml run success for the merged SHA — its own steps restart
   pedesk.service on the DigitalOcean droplet and assert a public
   https://pedesk.app/healthz 200 + guide-health reachable — plus (b)
   playwright screenshots + route-walker marker checks against a LOCAL server
   running the same merged commit. Alternative rejected: direct
   curl/WebFetch/browser against pedesk.app from this sandbox — all blocked
   by the egress firewall (403 on every channel, tested 03:42–03:44Z).
   Why: deploy-run health checks execute from GitHub's runners (unblocked)
   and are part of the deploy itself; local renders of the identical commit
   are the highest-fidelity visual evidence available from this sandbox.

2. **Azure purge scope.** Decision: purge Azure from all ACTIVE deploy
   surfaces (deploy/, tools/, demo.py, server.py comments, test wording,
   READMEs); keep "Microsoft Azure" where it is illustrative *vendor
   content* in data_public seeds (cyber_risk, compliance_attestation,
   ai_operating_model, extended_seed_98 company name); keep historical
   records (CHANGELOG.md, docs/design-handoff/PROPOSAL.md,
   docs/PARTNERSHIPS_PLAN.md, docs/UI_REWORK_PLAN.md, archived
   SESSION_STATE_2026-05-17) untouched. Alternative rejected: rewriting
   history docs — they are records of what happened, not statements of the
   current deploy path. Why: the user's directive targets the deploy story;
   the canonical path is now unambiguous (docs/DIGITALOCEAN_DEPLOYMENT.md +
   docs/AUTODEPLOY.md, linked from deploy/PEDESK_DEPLOY.md's banner).

3. **Session PR strategy.** Decision: one draft PR accumulating the session's
   commits, merged at close-out (and at most a couple of mid-session merge
   checkpoints if a large coherent block lands), each merge followed by the
   full live-verification protocol. Alternative rejected: PR-per-item with a
   ~6-min merge+deploy wait each — would burn ~1h of the 8h on waiting,
   violating the no-idle rule.

4. **demo.py `_RUNNING_ON_AZURE` → `_RUNNING_ON_PAAS` rename.** Behavior
   identical (PORT/WEBSITE_HOSTNAME detection kept for back-compat).
   Alternative rejected: deleting the detection — harmless, useful on any
   PaaS, and removing it risks breaking someone's container run.
