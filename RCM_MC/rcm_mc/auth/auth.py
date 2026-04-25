"""Multi-user authentication (Brick 125).

Until now auth was a single HTTP-Basic user configured at server
start. Real software needs per-user identities: a covenant ack by
"AT" should be attributable to a specific analyst, not a self-reported
string. This module adds a ``users`` table and session cookies while
preserving back-compat with the legacy single-user HTTP Basic gate.

Design:

- **scrypt** password hashing via stdlib ``hashlib.scrypt`` — no new
  deps. Salt stored per-user. Constant-time verify via
  ``hmac.compare_digest``.
- **Session tokens** are 32-byte URL-safe randoms stored in
  ``sessions`` with ``expires_at``. Default TTL = 7 days, sliding
  window: every request that validates a token could extend it (we
  keep it simple and don't slide; rotate on re-login).
- **Roles**: ``admin`` (can create/remove users), ``analyst``
  (everything else). Kept minimal — finer-grained auth is future work.

Public API::

    create_user(store, username, password, *, display_name="", role="analyst") -> int
    verify_password(store, username, password) -> bool
    create_session(store, username, *, ttl_hours=168) -> str
    user_for_session(store, token) -> dict | None
    revoke_session(store, token) -> bool
    list_users(store) -> pd.DataFrame
    delete_user(store, username) -> bool
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,39}$")

# scrypt parameters. Values chosen for ~100ms verify on commodity
# hardware — fast enough that a real login isn't noticeable, slow
# enough that offline brute force on a leaked DB costs real money.
_SCRYPT_N = 2 ** 14  # cost
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )


def _validate_username(username: str) -> str:
    if username is None:
        raise ValueError("username required")
    u = str(username).strip()
    if not u:
        raise ValueError("username required")
    if not _USERNAME_RE.match(u):
        raise ValueError(
            f"invalid username {username!r}: alnum plus . _ - @, "
            "max 40 chars, must start alnum, no spaces"
        )
    return u


def _ensure_tables(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash BLOB NOT NULL,
                password_salt BLOB NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'analyst',
                created_at TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(username) REFERENCES users(username)
            )"""
        )
        # Idempotent column add for the session inactivity timeout.
        # Pre-existing deployments don't have this; a fresh "ALTER TABLE
        # ADD COLUMN IF NOT EXISTS" isn't available in SQLite, so we
        # check the pragma first.
        cols = {r[1] for r in con.execute(
            "PRAGMA table_info(sessions)").fetchall()}
        if "last_seen_at" not in cols:
            con.execute(
                "ALTER TABLE sessions "
                "ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''"
            )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_username "
            "ON sessions(username)"
        )
        con.commit()


def create_user(
    store: PortfolioStore,
    username: str,
    password: str,
    *,
    display_name: str = "",
    role: str = "analyst",
) -> str:
    """Create a new user. Raises ``ValueError`` if the name clashes."""
    if role not in ("admin", "analyst"):
        raise ValueError(f"role must be 'admin' or 'analyst' (got {role!r})")
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    # B150 fix: cap password length so a malicious 100 MB password
    # string can't DoS the scrypt worker. 256 chars is well beyond
    # any human password and still safely hashed in <1 sec.
    if len(password) > 256:
        raise ValueError("password must be at most 256 characters")
    u = _validate_username(username)
    _ensure_tables(store)
    salt = os.urandom(16)
    pw_hash = _hash_password(password, salt)
    with store.connect() as con:
        try:
            con.execute(
                "INSERT INTO users "
                "(username, password_hash, password_salt, "
                "display_name, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (u, pw_hash, salt, str(display_name or "").strip(),
                 role, _iso(_utcnow())),
            )
            con.commit()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"user {u!r} already exists") from exc
    return u


def verify_password(
    store: PortfolioStore, username: str, password: str,
) -> bool:
    """Constant-time password check. False on unknown user / bad pw.

    B150 fix: cap the password length before handing to scrypt so a
    login-form DoS via a 100 MB password string is impossible.
    """
    if password and len(password) > 256:
        return False
    try:
        u = _validate_username(username)
    except ValueError:
        return False
    _ensure_tables(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT password_hash, password_salt FROM users "
            "WHERE username = ?",
            (u,),
        ).fetchone()
    if row is None:
        # Still burn ~the same cost to avoid a username-enumeration
        # timing leak. A full constant-time compare isn't required for
        # the threat model (local deploy) but it costs us nothing.
        _hash_password(password or "", os.urandom(16))
        return False
    candidate = _hash_password(password or "", bytes(row["password_salt"]))
    return hmac.compare_digest(bytes(row["password_hash"]), candidate)


def create_session(
    store: PortfolioStore,
    username: str,
    *,
    ttl_hours: int = 168,
) -> str:
    """Issue a new session token for an already-verified user.

    B147 fix: reject non-positive TTLs so we don't silently mint
    immediately-expired tokens. Tests that need expired sessions
    should manipulate ``expires_at`` directly instead.
    """
    if int(ttl_hours) <= 0:
        raise ValueError(f"ttl_hours must be > 0 (got {ttl_hours})")
    u = _validate_username(username)
    _ensure_tables(store)
    token = secrets.token_urlsafe(32)
    now = _utcnow()
    expires = now + timedelta(hours=int(ttl_hours))
    with store.connect() as con:
        con.execute(
            "INSERT INTO sessions "
            "(token, username, expires_at, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token, u, _iso(expires), _iso(now), _iso(now)),
        )
        con.commit()
    return token


# Default idle timeout — 30 minutes of inactivity. Tuned for a PE
# partner's daily flow: a long coffee, a stand-up, or a surprise call
# shouldn't force reauth, but an unattended machine overnight should.
# Overridable via RCM_MC_SESSION_IDLE_MINUTES env var.
def _idle_timeout_minutes() -> int:
    raw = os.environ.get("RCM_MC_SESSION_IDLE_MINUTES", "").strip()
    if not raw:
        return 30
    try:
        n = int(raw)
    except ValueError:
        return 30
    return n if n > 0 else 30


def user_for_session(
    store: PortfolioStore, token: str,
    *, touch: bool = True, idle_timeout_minutes: Optional[int] = None,
) -> Optional[Dict[str, str]]:
    """Return ``{username, display_name, role}`` for a valid token.

    Enforces two expiry gates:
      1. Absolute TTL via ``expires_at`` (default 7 days, set at login).
      2. Idle timeout via ``last_seen_at``: a session untouched for
         longer than the idle window is treated as expired.

    When ``touch=True`` (default), bumps ``last_seen_at`` to now so
    every active request extends the inactivity window. Read-only
    callers that want to peek without sliding the window (e.g. background
    audit passes) can pass ``touch=False``.
    """
    if not token:
        return None
    _ensure_tables(store)
    with store.connect() as con:
        row = con.execute(
            """SELECT s.username, s.expires_at, s.last_seen_at,
                      u.display_name, u.role
               FROM sessions s JOIN users u ON s.username = u.username
               WHERE s.token = ?""",
            (token,),
        ).fetchone()
    if row is None:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except (TypeError, ValueError):
        return None
    now = _utcnow()
    if now >= expires:
        return None

    idle_mins = (idle_timeout_minutes
                 if idle_timeout_minutes is not None
                 else _idle_timeout_minutes())
    last_seen_raw = row["last_seen_at"] or ""
    if last_seen_raw:
        try:
            last_seen = datetime.fromisoformat(last_seen_raw)
            if (now - last_seen) > timedelta(minutes=idle_mins):
                # Session went idle — treat as expired and clean it up
                # so the next login has a clean slate.
                with store.connect() as con:
                    con.execute(
                        "DELETE FROM sessions WHERE token = ?", (token,),
                    )
                    con.commit()
                return None
        except (TypeError, ValueError):
            pass  # malformed last_seen — fall through and touch below

    if touch:
        try:
            with store.connect() as con:
                con.execute(
                    "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                    (_iso(now), token),
                )
                con.commit()
        except Exception:  # noqa: BLE001
            # Touching the session must never break auth — a DB write
            # failure here should still let the authenticated request
            # proceed. Next request will try again.
            pass

    return {
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }


def revoke_session(store: PortfolioStore, token: str) -> bool:
    """Delete a session. Returns True if a row was removed."""
    if not token:
        return False
    _ensure_tables(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM sessions WHERE token = ?", (token,),
        )
        con.commit()
        return cur.rowcount > 0


def cleanup_expired_sessions(store: PortfolioStore) -> int:
    """Delete every session whose ``expires_at`` is in the past.

    Returns the row count removed. Called once on server startup
    (`build_server`) and periodically from the request handler so
    abandoned sessions don't balloon the table. The JOIN in
    ``user_for_session`` already rejects expired rows, so this is
    pure table hygiene rather than a correctness requirement.
    """
    _ensure_tables(store)
    now = _utcnow().isoformat()
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (now,),
        )
        con.commit()
        return int(cur.rowcount or 0)


def list_users(store: PortfolioStore) -> pd.DataFrame:
    _ensure_tables(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT username, display_name, role, created_at "
            "FROM users ORDER BY username",
            con,
        )


def change_password(
    store: PortfolioStore,
    username: str,
    new_password: str,
) -> bool:
    """Rotate a user's password + revoke all their sessions (B129).

    Returns True if the user existed and the password was changed.
    Revoking sessions on rotation is the expected semantic — if you
    rotated because of a compromise, you want existing tokens dead.
    """
    u = _validate_username(username)
    if not new_password or len(new_password) < 8:
        raise ValueError("new_password must be at least 8 characters")
    if len(new_password) > 256:
        raise ValueError("new_password must be at most 256 characters")
    _ensure_tables(store)
    salt = os.urandom(16)
    pw_hash = _hash_password(new_password, salt)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? "
            "WHERE username = ?",
            (pw_hash, salt, u),
        )
        if cur.rowcount == 0:
            con.commit()
            return False
        con.execute("DELETE FROM sessions WHERE username = ?", (u,))
        con.commit()
    return True


def delete_user(store: PortfolioStore, username: str) -> bool:
    """Hard-delete a user + revoke their sessions. Returns True on change.

    B151 fix: refuse to delete a user who currently owns deals or has
    open deadlines — those rows would otherwise dangle and downstream
    queries (deals_by_owner, my-inbox) would return stale references.
    Historical records in ``alert_acks`` and ``audit_events`` are left
    intact by design: the audit trail must survive personnel changes.
    """
    u = _validate_username(username)
    _ensure_tables(store)
    # B154 fix: hold a single IMMEDIATE-write transaction across the
    # check + delete so a concurrent assign_owner/add_deadline can't
    # sneak in between us verifying "no current references" and
    # deleting the user row.
    #
    # Make sure the referenced tables exist so the SELECTs below
    # don't raise mid-transaction on a fresh DB.
    try:
        from ..deals.deal_deadlines import _ensure_table as _ensure_dl
        _ensure_dl(store)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..deals.deal_owners import _ensure_owners_table as _ensure_oh
        _ensure_oh(store)
    except Exception:  # noqa: BLE001
        pass

    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            # Current-owner check, in the same txn
            owner_rows = con.execute(
                """SELECT COUNT(DISTINCT deal_id) AS n FROM deal_owner_history h1
                   WHERE owner = ?
                     AND id = (
                         SELECT MAX(id) FROM deal_owner_history h2
                         WHERE h2.deal_id = h1.deal_id
                     )""",
                (u,),
            ).fetchone()
            current_deals = int(owner_rows["n"]) if owner_rows else 0
            if current_deals:
                con.rollback()
                raise ValueError(
                    f"cannot delete {u!r}: currently owns "
                    f"{current_deals} deal(s). Reassign first."
                )
            # Open deadlines
            dl_rows = con.execute(
                "SELECT COUNT(*) AS n FROM deal_deadlines "
                "WHERE owner = ? AND status = 'open'",
                (u,),
            ).fetchone()
            open_count = int(dl_rows["n"]) if dl_rows else 0
            if open_count:
                con.rollback()
                raise ValueError(
                    f"cannot delete {u!r}: has {open_count} open "
                    f"deadline(s). Complete or reassign first."
                )
            con.execute("DELETE FROM sessions WHERE username = ?", (u,))
            cur = con.execute(
                "DELETE FROM users WHERE username = ?", (u,),
            )
            changed = cur.rowcount > 0
            con.commit()
            return changed
        except ValueError:
            raise
        except Exception:
            con.rollback()
            raise
