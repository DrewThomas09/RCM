# PEdesk production sign-in (shared-credential deployments)

The DigitalOcean production deployment (https://pedesk.app) authenticates
against a single **shared credential** held in the `RCM_MC_AUTH` env var in
`.pedesk_prod.env`. There are **two ways** to present that credential, chosen
by `RCM_MC_AUTH_UI`:

| Mode | `RCM_MC_AUTH_UI` | What the user sees | Notes |
|---|---|---|---|
| **Styled form-login** (recommended) | `form` | The pretty in-app `/login` page → session cookie | No browser popup; looks like a polished product |
| **Basic Auth** (default/fallback) | unset / `basic` | The browser's native username/password popup | Technically simplest; feels like a server admin panel |

Both modes use the **same** shared credential string (`user:password`) in
`RCM_MC_AUTH`. Only the presentation differs. **For pedesk.app, use styled
form-login** — set `RCM_MC_AUTH_UI=form` in `.pedesk_prod.env`.

> See also: `docs/DIGITALOCEAN_DEPLOYMENT.md` for the full deploy guide.

## Styled form-login mode (recommended)

`.pedesk_prod.env`:

```
RCM_MC_AUTH=andrewt@chartis.com:<strong-shared-password>
RCM_MC_AUTH_UI=form
```

Flow: open **https://pedesk.app** → click **Sign In** → the styled PEdesk
`/login` page renders → enter the shared `user` / `password` → a normal app
session cookie is issued → land on `/app`. No native popup, ever.

How it works: when `RCM_MC_AUTH_UI=form`, the server seeds the shared
credential as a real DB user at startup and leaves HTTP Basic **off**. The
existing session/cookie `/login` flow then authenticates it. A browser hitting
a protected route while signed out is redirected to `/login?next=…` (not a
401), so the friendly form always appears. Changing the password in
`RCM_MC_AUTH` and restarting re-syncs the seeded user (and invalidates old
sessions).

## Basic Auth mode (fallback) — entry point

Leave `RCM_MC_AUTH_UI` unset (or set it to `basic`).

**Production entry URL: https://pedesk.app/app**

Open `/app`; the browser shows a native username/password prompt. Enter the
shared `RCM_MC_AUTH` credential (`user:password`). That's it.

### Why not `/login`? (Basic Auth mode only)

> This section applies **only when `RCM_MC_AUTH_UI` is unset/`basic`**. In
> styled form-login mode (`RCM_MC_AUTH_UI=form`) `/login` *is* the entry
> point and renders normally — none of the redirects below apply.

In Basic Auth mode, `/login` is the **in-app** auth flow — it authenticates
against DB users (scrypt + sessions). It does **not** accept the
`RCM_MC_AUTH` shared credential and will say "Invalid credentials." To avoid
that confusion, when `RCM_MC_AUTH` is set (and `RCM_MC_AUTH_UI` is not
`form`):

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

## Expected behavior (auth contract)

**Styled form-login mode (`RCM_MC_AUTH_UI=form`):**

```bash
curl -sI https://pedesk.app/app -H 'Accept: text/html'      # 303 → /login?next=%2Fapp (no WWW-Authenticate)
curl -sI https://pedesk.app/login                           # 200 (the styled form renders)
# POST username/password to /api/login → 303 → /app + Set-Cookie: rcm_session
```

**Basic Auth mode (`RCM_MC_AUTH_UI` unset/`basic`):**

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
