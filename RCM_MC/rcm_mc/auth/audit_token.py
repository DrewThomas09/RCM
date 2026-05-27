"""Time-boxed, read-only audit access — a deliberately narrow, off-by-default
mechanism to let an external reviewer (e.g. an AI agent) crawl the live UI for
a short window and then be shut instantly.

Security posture (every one of these matters — this is an auth bypass, so it is
built to fail closed):

  * OFF BY DEFAULT. The whole feature is inert unless ``RCM_MC_AUDIT_SECRET`` is
    set in the server's environment. No secret → no audit access, period.
  * TIME-BOXED. Tokens carry a signed expiry (``mint`` caps it at 24h); after
    that they're dead with no server action needed.
  * READ-ONLY. An audit session is GET-only; the server blocks every mutating
    method for it (see server do_POST/PUT/DELETE), so even "full" access can't
    change data.
  * INSTANT KILL. Unset ``RCM_MC_AUDIT_SECRET`` (and restart) and EVERY
    outstanding token is invalidated immediately — rotating the secret is the
    panic button.
  * SIGNED. Tokens are ``<exp>.<hmac-sha256(exp, secret)>`` with a
    constant-time compare — they can't be forged or extended without the secret.

This does NOT touch the normal username/password/session path; it's an additive,
parallel, locked-down lane.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Optional

_ENV = "RCM_MC_AUDIT_SECRET"
_MAX_HOURS = 24


def _secret() -> Optional[bytes]:
    s = os.environ.get(_ENV, "").strip()
    return s.encode("utf-8") if s else None


def audit_enabled() -> bool:
    """True only when an audit secret is configured. The master on/off."""
    return _secret() is not None


def _sign(exp: int, secret: bytes) -> str:
    return hmac.new(secret, str(exp).encode("ascii"), hashlib.sha256).hexdigest()


def mint(hours: float = 2.0) -> Optional[str]:
    """Mint a signed audit token valid for ``hours`` (capped at 24). Returns
    None if the feature is disabled (no secret set)."""
    secret = _secret()
    if secret is None:
        return None
    hours = max(0.1, min(float(hours), _MAX_HOURS))
    exp = int(time.time() + hours * 3600)
    return f"{exp}.{_sign(exp, secret)}"


def verify(token: str) -> Optional[int]:
    """Return the token's expiry epoch if it's valid + unexpired, else None.
    Fails closed on any malformation / disabled feature."""
    secret = _secret()
    if secret is None or not token or "." not in token:
        return None
    exp_str, _, sig = token.partition(".")
    try:
        exp = int(exp_str)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(exp, secret)):
        return None
    if time.time() >= exp:
        return None
    return exp
