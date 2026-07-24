"""Surface-visibility registry — the single ruling on what partners see.

The ranking manifest (``_surface_rankings.RANKINGS``, auto-generated) scores
every route-backed page, but a score is not a visibility decision. This
module is the hand-curated layer that says what may appear where. Four
visibility ranks, best-first:

  1. **Flagship** — leads a topbar mega-menu (``_chartis_kit._NAV_FLAGSHIPS``).
  2. **Catalog** — listed in /tools and the /best/<section> catalogs.
  3. **Utility** — real page, but a tool rather than an analysis
     (``_chartis_kit._NAV_DEMOTED``): never in a bar, still in catalogs
     and the Cmd-K palette.
  4. **Internal** — never rendered as a partner-facing destination card
     (``INTERNAL_ROUTES`` below): auth, admin, debug/status, and file
     -download artifacts that the route scanner mis-ranks as pages. They
     remain reachable directly (and admin pages keep their user-menu
     links); they just never read as "a tool we're proud of".

``curate_rows`` applies the catalog-level rules to a ranked row list and is
shared by every generic listing renderer (/tools showcase, the auto-built
section catalogs, the ranked /best fallback) so the ruling can't drift
per-surface.
"""
from __future__ import annotations

from collections.abc import Iterable

# Routes that must never render as partner-facing destination cards.
# Keep this tight and defensible — everything here is either not a page
# (file downloads), not for partners (auth/admin plumbing), or a debug
# surface (build-status, CLI run log).
INTERNAL_ROUTES = frozenset({
    "/login",       # auth plumbing — partners arrive here, never browse to it
    "/forgot",      # auth plumbing
    "/demo",        # seeded demo launcher, not a partner destination
    "/users",       # admin — linked from the user-menu "Admin" item instead
    "/cli-runs",    # CLI run log, debug surface
})

# Pages whose *content* is still synthetic/placeholder — real data deferred.
# Different reason from INTERNAL_ROUTES (which is plumbing), same ruling: a
# half-finished surface must not read as "a tool we're proud of", so it
# never renders as a partner-facing destination card. It stays reachable by
# direct URL (and via any activation index) — this only removes it from
# /tools, the section catalogs, the ranked /best fallback, and the nav bars.
# Kept a SEPARATE set so the plumbing semantics of INTERNAL_ROUTES stay
# clean and each entry carries its own justification.
NOT_READY_ROUTES = frozenset({
    # CMS MA Star Ratings — fully synthetic, real-data deferred to a future
    # zip-portal ingest (docs/reports/RED_PAGE_ACTIVATION_PLAN.md). The only
    # page still classified RED in diligence/surface_status.
    "/ma-star",
})


def is_internal(route: str) -> bool:
    """True when a route must not render as a partner-facing card.

    Covers three classes: auth/admin/debug plumbing (``INTERNAL_ROUTES``),
    still-synthetic surfaces (``NOT_READY_ROUTES``), and workbook-download
    ``.xlsx`` routes the scanner mis-reads as pages (clicking a "tool" that
    downloads a file is a broken browse, so the whole class is hidden
    rather than enumerating each artifact).
    """
    route = (route or "").strip()
    return (route in INTERNAL_ROUTES or route in NOT_READY_ROUTES
            or route.endswith(".xlsx"))


def curate_rows(rows: Iterable[dict]) -> list[dict]:
    """Filter a ranked row list (dicts with 'route' + 'label') down to what
    a partner-facing catalog may show. Rows must arrive best-first; the
    first occurrence of a destination wins.

    Drops, in order of why:
      * internal routes (see ``is_internal``),
      * sentinel rows ("All X →" labels — they duplicate the catalog's own
        section link and aren't real leaves),
      * alias duplicates of the same page, by normalized route
        (``/diligence/`` vs ``/diligence``) and by label
        (``/deal-pipeline`` vs ``/pipeline`` both render "Deal Pipeline" —
        a catalog showing the same destination twice reads as a bug).
    """
    out: list[dict] = []
    seen_routes: set = set()
    seen_labels: set = set()
    for r in rows:
        route = str(r.get("route") or "").strip()
        label = str(r.get("label") or "").strip()
        norm = route.rstrip("/") or route
        if not route or norm in seen_routes or label.lower() in seen_labels:
            continue
        # Record the route BEFORE the drop checks so an alias of a dropped
        # row drops with it (`/diligence/` must not survive just because
        # `/diligence` was removed as a sentinel first).
        seen_routes.add(norm)
        if is_internal(route) or "→" in label:
            continue
        if label:
            seen_labels.add(label.lower())
        out.append(r)
    return out
