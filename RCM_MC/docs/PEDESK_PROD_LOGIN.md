# PEdesk production sign-in (Basic Auth deployments)

The DigitalOcean production deployment (https://pedesk.app) authenticates
with **browser HTTP Basic Auth**, driven by the `RCM_MC_AUTH` env var in
`.pedesk_prod.env`. This is **not** the same as the in-app `/login` form.

> See also: `docs/DIGITALOCEAN_DEPLOYMENT.md` for the full deploy guide.

## Entry point

**Production entry URL: https://pedesk.app/app**

Open `/app`; the browser shows a native username/password prompt. Enter the
shared `RCM_MC_AUTH` credential (`user:password`). That's it.

## Why not `/login`?

`/login` is the **in-app** auth flow — it authenticates against DB users
(scrypt + sessions). It does **not** accept the `RCM_MC_AUTH` shared
credential and will say "Invalid credentials." To avoid that confusion, when
`RCM_MC_AUTH` is set:

- the public homepage **Sign In** CTAs point straight at `/app` (not `/login`); and
- visiting `/login` **redirects to `/app`**, where the browser Basic Auth
  prompt appears.

So `RCM_MC_AUTH` (browser Basic Auth) and the `/login` form are two different
mechanisms; in a Basic Auth deployment, users only ever use the browser prompt.

**Every `/login` variant redirects.** With `RCM_MC_AUTH` set, the redirect to
`/app` runs before any query parsing, so `/login`, `/login?err=Invalid`,
`/login?next=…`, and `/login?tab=request` **all** 303 to `/app`. The in-app
login form never renders, and the redirect is sent `Cache-Control: no-store`
so it can't be cached.

### If you still see a `/login?err=Invalid` page

That's a **stale browser tab/cache** from before the fix — the server no
longer serves it. To recover:

1. Close every `pedesk.app` tab.
2. Open a fresh (incognito) window at **https://pedesk.app/app**.
3. If it persists: Chrome → Settings → Privacy → Site data → search
   `pedesk.app` → Delete, then reopen `https://pedesk.app/app`.

Do not type into any `/login` form — production has no in-app accounts.

## Expected behavior (unchanged auth contract)

```bash
curl -I https://pedesk.app/app                              # 401 (no auth)
curl -I -u 'user:password' https://pedesk.app/app           # 200 (authed)
```

In Basic Auth mode, an **unauthenticated browser** request to a protected
route (e.g. `/app`) returns `401 Unauthorized` with `WWW-Authenticate: Basic`
— so the browser shows its native prompt. It must **not** redirect to
`/login` (that would loop with the `/login → /app` redirect). The
friendly `/login?next=…` bounce only happens in session/DB-user
deployments where `RCM_MC_AUTH` is unset.

`/api/guide/ollama-health` reports `ai_ready: true` once the Droplet can
reach the home-Mac Ollama over Tailscale.

## Credential hygiene

- `RCM_MC_AUTH` lives only in `.pedesk_prod.env` (mode 600, **git-ignored,
  never committed**). Never paste the password into chat, logs, or tickets.
- Use a strong shared password (e.g. `python3 -c "import secrets;
  print('user:'+secrets.token_urlsafe(18))"`). If a credential is ever
  exposed, rotate it: edit `.pedesk_prod.env` and `systemctl restart pedesk`.

## Unchanged

This is a UX/routing fix only. Ollama stays on the Mac (private via
Tailscale, port 11434 never exposed), RAG is unchanged, and the Guide
remains read-only.
