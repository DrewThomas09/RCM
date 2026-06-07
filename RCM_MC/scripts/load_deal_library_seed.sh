#!/usr/bin/env bash
# Load the bundled HCPEA Deal Library seed into the live portfolio DB.
#
# Why this exists: the deal data is shipped *in the repo* (a gzipped, normalized
# CSV under data/seed/) so a host with no easy file-upload path can install it
# with `git pull` + this one script — no scp / console upload needed. The load
# is idempotent (upsert on company_id), so re-running is safe.
#
# Usage (on the host, after `git pull origin main`):
#   bash RCM_MC/scripts/load_deal_library_seed.sh
#   # override the DB if needed:  RCM_MC_DB=/path/to.db bash .../load_deal_library_seed.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"                       # .../RCM_MC
SEED="$ROOT/data/seed/deal_library_hcpea.csv.gz"

[ -f "$SEED" ] || { echo "ERROR: seed not found at $SEED (did you git pull?)"; exit 1; }

# Interpreter: the app's virtualenv (has numpy/pandas + rcm_mc), else system.
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
[ -x "$PY" ] || { echo "ERROR: no usable python found"; exit 1; }

# DB path, resolved the way the app does (server.py): $RCM_MC_DB, else the
# .pedesk_prod.env value, else ~/.rcm_mc/portfolio.db; finally any portfolio.db.
DB="${RCM_MC_DB:-}"                                  # 1. explicit override wins
if [ -z "$DB" ] && [ -f "$ROOT/.pedesk_prod.env" ]; then   # 2. the deploy env file
  DB="$(grep -oE 'RCM_MC_DB=[^"'"'"' ]*' "$ROOT/.pedesk_prod.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
fi
if [ -z "$DB" ]; then                                # 3. the app default (server.py)
  DB="$HOME/.rcm_mc/portfolio.db"
  # only if that default isn't present, fall back to any existing portfolio.db
  [ -f "$DB" ] || DB="$(find /root /opt /home /data -name portfolio.db 2>/dev/null | head -1 || true)"
fi
[ -n "$DB" ] || { echo "ERROR: could not locate the portfolio DB; set RCM_MC_DB=..."; exit 1; }

echo "python: $PY"
echo "db:     $DB  (exists: $([ -f "$DB" ] && echo yes || echo 'no — will be created'))"
echo "seed:   $SEED"

TMP="$(mktemp --suffix=.csv)"
trap 'rm -f "$TMP"' EXIT
gzip -dc "$SEED" > "$TMP"

PYTHONPATH="$ROOT" "$PY" - "$DB" "$TMP" <<'PY'
import sys
from rcm_mc.data import deal_library as d
from rcm_mc.portfolio.store import PortfolioStore
db, csv = sys.argv[1], sys.argv[2]
print(d.load_companies_csv(PortfolioStore(db), csv), "deals loaded")
print("total in library:", d.count(PortfolioStore(db)))
PY
echo "Done. Hard-refresh /deal-library in the browser."
