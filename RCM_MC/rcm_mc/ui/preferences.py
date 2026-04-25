"""User preferences — default views, favorite hospitals, custom
dashboards, notification settings.

Personalization creates stickiness. Partners who curate their
favorite hospitals, set their default landing view, and tune
notifications use the platform daily; everyone else churns.

This module ships:

  • A ``UserPreferences`` dataclass with the canonical settings
    every user can customize.
  • A SQLite-backed store keyed on username (auth.py already
    establishes per-user identity). JSON blob storage so the
    schema can evolve without a per-field migration.
  • Helpers for the most common mutations: toggle a favorite
    hospital, set the default dashboard, update a notification
    flag.
  • A ``/preferences`` page where users edit them via a single
    POST form.

Public API::

    from rcm_mc.ui.preferences import (
        UserPreferences,
        get_preferences,
        save_preferences,
        toggle_favorite_hospital,
        is_favorite_hospital,
        list_favorite_hospitals,
    )
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


# ── Schema ──────────────────────────────────────────────────

def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            username TEXT PRIMARY KEY,
            preferences_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


# Canonical default-view options
DEFAULT_VIEWS = (
    "dashboard_v3",     # /?v3=1 (morning view)
    "legacy_dashboard", # /
    "data_catalog",     # /data/catalog
    "model_quality",    # /models/quality
)


@dataclass
class NotificationSettings:
    """Per-channel notification flags."""
    email: Optional[str] = None
    alert_critical: bool = True
    alert_high: bool = True
    alert_medium: bool = False
    alert_low: bool = False
    variance_breach: bool = True
    deadline_due: bool = True
    weekly_digest: bool = False


@dataclass
class CustomDashboardWidget:
    """One user-pinned widget on the custom dashboard."""
    widget_id: str
    label: str
    target_url: str
    position: int = 0       # display order


@dataclass
class UserPreferences:
    """One user's preferences."""
    username: str
    default_view: str = "dashboard_v3"
    favorite_hospitals: List[str] = field(default_factory=list)
    custom_widgets: List[CustomDashboardWidget] = field(
        default_factory=list)
    notifications: NotificationSettings = field(
        default_factory=NotificationSettings)
    timezone: str = "UTC"
    items_per_page: int = 25

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], *,
        username: Optional[str] = None,
    ) -> "UserPreferences":
        """Reconstruct from JSON-deserialized dict.

        Tolerates missing fields (returns defaults) and unknown
        fields (silently dropped) so old rows survive schema
        evolution.
        """
        n = (data.get("notifications")
             if isinstance(data, dict) else None) or {}
        notif = NotificationSettings(
            email=n.get("email"),
            alert_critical=bool(
                n.get("alert_critical", True)),
            alert_high=bool(n.get("alert_high", True)),
            alert_medium=bool(
                n.get("alert_medium", False)),
            alert_low=bool(n.get("alert_low", False)),
            variance_breach=bool(
                n.get("variance_breach", True)),
            deadline_due=bool(
                n.get("deadline_due", True)),
            weekly_digest=bool(
                n.get("weekly_digest", False)))
        widgets = []
        for w in data.get("custom_widgets") or []:
            try:
                widgets.append(CustomDashboardWidget(
                    widget_id=str(w.get("widget_id")
                                  or ""),
                    label=str(w.get("label") or ""),
                    target_url=str(w.get("target_url")
                                   or ""),
                    position=int(w.get("position") or 0)))
            except (TypeError, ValueError):
                continue
        favorites = data.get("favorite_hospitals") or []
        return cls(
            username=str(
                username or data.get("username") or ""),
            default_view=str(
                data.get("default_view")
                or "dashboard_v3"),
            favorite_hospitals=[str(h) for h in favorites],
            custom_widgets=widgets,
            notifications=notif,
            timezone=str(data.get("timezone") or "UTC"),
            items_per_page=int(
                data.get("items_per_page") or 25),
        )


# ── Persistence ─────────────────────────────────────────────

def get_preferences(
    store: Any, username: str,
) -> UserPreferences:
    """Load a user's preferences. Returns defaults when no row
    exists — never raises for missing user."""
    if not username:
        return UserPreferences(username="")
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(
            "SELECT preferences_json FROM user_preferences "
            "WHERE username = ?",
            (username,)).fetchone()
    if not row:
        return UserPreferences(username=username)
    try:
        data = json.loads(row["preferences_json"])
    except (json.JSONDecodeError, TypeError):
        return UserPreferences(username=username)
    return UserPreferences.from_dict(
        data, username=username)


def save_preferences(
    store: Any, prefs: UserPreferences,
) -> None:
    """Upsert preferences. Raises ValueError on empty username."""
    if not prefs.username:
        raise ValueError("username required to save")
    if prefs.default_view not in DEFAULT_VIEWS:
        raise ValueError(
            f"Unknown default_view: {prefs.default_view}")
    if prefs.items_per_page < 5 or prefs.items_per_page > 200:
        raise ValueError(
            "items_per_page must be in [5, 200]")
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(prefs.to_dict())
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                "INSERT OR REPLACE INTO user_preferences "
                "(username, preferences_json, updated_at) "
                "VALUES (?, ?, ?)",
                (prefs.username, payload, now))
            con.commit()
        except Exception:
            con.rollback()
            raise


# ── Favorite hospitals ──────────────────────────────────────

def toggle_favorite_hospital(
    store: Any, username: str, ccn: str,
) -> bool:
    """Add or remove a hospital from the user's favorites.

    Returns the new favorited state (True = now favorited).
    """
    if not (username and ccn):
        return False
    prefs = get_preferences(store, username)
    favs = list(prefs.favorite_hospitals)
    if ccn in favs:
        favs.remove(ccn)
        new_state = False
    else:
        favs.append(ccn)
        new_state = True
    prefs.favorite_hospitals = favs
    save_preferences(store, prefs)
    return new_state


def is_favorite_hospital(
    store: Any, username: str, ccn: str,
) -> bool:
    """Quick check; returns False on missing user / ccn."""
    if not (username and ccn):
        return False
    prefs = get_preferences(store, username)
    return ccn in prefs.favorite_hospitals


def list_favorite_hospitals(
    store: Any, username: str,
) -> List[str]:
    """All CCNs favorited by this user."""
    if not username:
        return []
    return list(
        get_preferences(store, username).favorite_hospitals)


# ── Custom dashboard widgets ────────────────────────────────

def add_custom_widget(
    store: Any, username: str,
    widget: CustomDashboardWidget,
) -> None:
    """Add or update a custom dashboard widget.

    If a widget with the same widget_id exists, it's replaced.
    """
    if not username or not widget.widget_id:
        raise ValueError(
            "username and widget_id required")
    prefs = get_preferences(store, username)
    existing = [
        w for w in prefs.custom_widgets
        if w.widget_id != widget.widget_id]
    existing.append(widget)
    existing.sort(key=lambda w: w.position)
    prefs.custom_widgets = existing
    save_preferences(store, prefs)


def remove_custom_widget(
    store: Any, username: str, widget_id: str,
) -> bool:
    """Remove a custom widget by id. Returns True if removed."""
    if not (username and widget_id):
        return False
    prefs = get_preferences(store, username)
    before = len(prefs.custom_widgets)
    prefs.custom_widgets = [
        w for w in prefs.custom_widgets
        if w.widget_id != widget_id]
    if len(prefs.custom_widgets) == before:
        return False
    save_preferences(store, prefs)
    return True
