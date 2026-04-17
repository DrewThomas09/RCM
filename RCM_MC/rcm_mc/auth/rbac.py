"""Role-based access control (Prompt 48).

Roles: ADMIN > PARTNER > VP > ASSOCIATE > ANALYST > VIEWER.
Permissions are a flat set of strings per role. The ``check_permission``
function is the single enforcement point — route handlers decorate
with ``require_permission`` and the server returns 403 when the
check fails.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Set


class Role(str, Enum):
    ADMIN = "ADMIN"
    PARTNER = "PARTNER"
    VP = "VP"
    ASSOCIATE = "ASSOCIATE"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "VIEWER":    {"read", "export"},
    "ANALYST":   {"read", "export", "upload", "create_deal", "run_analysis"},
    "ASSOCIATE": {"read", "export", "upload", "create_deal", "run_analysis",
                  "set_override", "update_initiative"},
    "VP":        {"read", "export", "upload", "create_deal", "run_analysis",
                  "set_override", "update_initiative",
                  "approve_plan", "modify_targets"},
    "PARTNER":   {"read", "export", "upload", "create_deal", "run_analysis",
                  "set_override", "update_initiative",
                  "approve_plan", "modify_targets",
                  "delete_deal", "manage_users"},
    "ADMIN":     {"read", "export", "upload", "create_deal", "run_analysis",
                  "set_override", "update_initiative",
                  "approve_plan", "modify_targets",
                  "delete_deal", "manage_users", "admin"},
}


def check_permission(role: str, permission: str) -> bool:
    """Return True when ``role`` has ``permission``."""
    perms = ROLE_PERMISSIONS.get(role.upper(), set())
    return permission in perms


def get_user_role(store: Any, username: str) -> str:
    """Read the role from the users table. Defaults to ASSOCIATE."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row and row["role"]:
            return str(row["role"]).upper()
    except Exception:  # noqa: BLE001
        pass
    return "ASSOCIATE"
