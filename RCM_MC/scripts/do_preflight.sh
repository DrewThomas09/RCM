#!/usr/bin/env bash
# do_preflight.sh — verify a PEdesk Droplet is ready to serve (read-only).
#
# Reads .pedesk_prod.env (NOT committed), checks Tailscale + the private
# Ollama path + models + RAG index. Prints PASS/WARN/FAIL lines only — it
# NEVER prints secret values (RCM_MC_AUTH, full env contents). Run from the
# repo's RCM_MC dir:  bash scripts/do_preflight.sh
set -euo pipefail

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$ROOT"
ENV_FILE="${PEDESK_PROD_ENV:-.pedesk_prod.env}"
fail=0
pass(){ echo "  [PASS] $*"; }
warn(){ echo "  [WARN] $*"; }
bad(){ echo "  [FAIL] $*"; fail=1; }

echo "[preflight] env file…"
if [ ! -f "$ENV_FILE" ]; then
  bad "$ENV_FILE not found — create it (see docs/DIGITALOCEAN_DEPLOYMENT.md)."
  echo "RESULT: FAIL"; exit 1
fi
pass "$ENV_FILE present"
# Permissions: should be owner-only (600/640). Never print contents.
perms="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE" 2>/dev/null || echo '?')"
case "$perms" in
  600|640|400) pass "env permissions $perms (owner-only)";;
  *) warn "env permissions $perms — tighten with: chmod 600 $ENV_FILE";;
esac
# Confirm it is gitignored (must never be committed).
if git -C "$ROOT" check-ignore "$ENV_FILE" >/dev/null 2>&1; then
  pass "$ENV_FILE is git-ignored"
else
  warn "$ENV_FILE is NOT git-ignored — do not commit it."
fi

# Load env WITHOUT echoing it.
set -a; . "./$ENV_FILE"; set +a

echo "[preflight] Tailscale…"
if command -v tailscale >/dev/null 2>&1; then
  pass "tailscale installed"
  tailscale status >/dev/null 2>&1 && pass "tailscale up" || warn "tailscale not connected — run 'tailscale up'"
else
  bad "tailscale not installed — run scripts/do_bootstrap_server.sh"
fi

echo "[preflight] Ollama base URL (private, via Tailscale)…"
BASE="${PEDESK_GUIDE_OLLAMA_BASE_URL:-}"
if [ -z "$BASE" ]; then
  bad "PEDESK_GUIDE_OLLAMA_BASE_URL not set in $ENV_FILE"
else
  # Show only the host:port shape, never credentials (there are none in a URL here).
  pass "PEDESK_GUIDE_OLLAMA_BASE_URL is set"
  case "$BASE" in
    *127.0.0.1*|*localhost*) warn "base URL is loopback — on the Droplet it must point at the Mac's TAILSCALE IP, not localhost";;
  esac
  if curl -fsS --max-time 8 "$BASE/api/tags" -o /tmp/_pedesk_tags.json 2>/dev/null; then
    pass "reached Ollama at the configured base URL"
    chat="${PEDESK_GUIDE_OLLAMA_MODEL:-gemma4:e4b}"
    embed="${PEDESK_GUIDE_RAG_EMBED_MODEL:-nomic-embed-text}"
    grep -q "$chat" /tmp/_pedesk_tags.json && pass "chat model present: $chat" || bad "chat model missing: $chat (pull it on the Mac)"
    grep -q "$embed" /tmp/_pedesk_tags.json && pass "embed model present: $embed" || bad "embed model missing: $embed (pull it on the Mac)"
    rm -f /tmp/_pedesk_tags.json
  else
    bad "could not reach $BASE/api/tags — check Tailscale + that Ollama is running on the Mac"
  fi
fi

echo "[preflight] RAG index…"
if [ -f ".pedesk_guide_rag.sqlite3" ]; then
  pass "RAG index present"
else
  warn "RAG index missing — build it: PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh"
fi

echo "[preflight] Basic Auth…"
if [ -n "${RCM_MC_AUTH:-}" ]; then
  pass "RCM_MC_AUTH is set (value not shown)"
else
  warn "RCM_MC_AUTH not set — public bind without auth is unsafe; set it in $ENV_FILE"
fi

echo
if [ "$fail" -eq 0 ]; then echo "RESULT: READY"; else echo "RESULT: FAIL"; exit 1; fi
