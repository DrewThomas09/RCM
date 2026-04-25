"""Tests for user preferences persistence + helpers."""
from __future__ import annotations

import os
import tempfile
import unittest


class TestDataclassRoundTrip(unittest.TestCase):
    def test_default_construction(self):
        from rcm_mc.ui.preferences import UserPreferences
        p = UserPreferences(username="alice")
        self.assertEqual(p.username, "alice")
        self.assertEqual(p.default_view, "dashboard_v3")
        self.assertEqual(p.favorite_hospitals, [])
        self.assertEqual(p.timezone, "UTC")
        self.assertEqual(p.items_per_page, 25)
        # Notification defaults
        self.assertTrue(p.notifications.alert_critical)
        self.assertFalse(p.notifications.alert_low)

    def test_from_dict_tolerates_missing_fields(self):
        from rcm_mc.ui.preferences import UserPreferences
        p = UserPreferences.from_dict(
            {}, username="bob")
        self.assertEqual(p.username, "bob")
        self.assertEqual(p.default_view, "dashboard_v3")

    def test_from_dict_drops_unknown_fields(self):
        from rcm_mc.ui.preferences import UserPreferences
        # Adding garbage doesn't crash
        p = UserPreferences.from_dict(
            {"unknown_field": "x",
             "default_view": "model_quality"},
            username="bob")
        self.assertEqual(
            p.default_view, "model_quality")


class TestPersistence(unittest.TestCase):
    def _store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "p.db")
        store = PortfolioStore(db)
        store.init_db()
        return store, tmp

    def test_get_returns_defaults_when_missing(self):
        from rcm_mc.ui.preferences import (
            get_preferences,
        )
        store, tmp = self._store()
        try:
            prefs = get_preferences(store, "alice")
            self.assertEqual(prefs.username, "alice")
            self.assertEqual(
                prefs.default_view, "dashboard_v3")
        finally:
            tmp.cleanup()

    def test_save_and_round_trip(self):
        from rcm_mc.ui.preferences import (
            UserPreferences, save_preferences,
            get_preferences,
        )
        store, tmp = self._store()
        try:
            p = UserPreferences(
                username="alice",
                default_view="model_quality",
                favorite_hospitals=["010001", "060001"],
                timezone="America/New_York")
            save_preferences(store, p)
            loaded = get_preferences(store, "alice")
            self.assertEqual(
                loaded.default_view, "model_quality")
            self.assertEqual(
                loaded.favorite_hospitals,
                ["010001", "060001"])
            self.assertEqual(
                loaded.timezone, "America/New_York")
        finally:
            tmp.cleanup()

    def test_save_rejects_empty_username(self):
        from rcm_mc.ui.preferences import (
            UserPreferences, save_preferences,
        )
        store, tmp = self._store()
        try:
            with self.assertRaises(ValueError):
                save_preferences(
                    store, UserPreferences(username=""))
        finally:
            tmp.cleanup()

    def test_save_rejects_bad_default_view(self):
        from rcm_mc.ui.preferences import (
            UserPreferences, save_preferences,
        )
        store, tmp = self._store()
        try:
            p = UserPreferences(
                username="alice",
                default_view="not_a_real_view")
            with self.assertRaises(ValueError):
                save_preferences(store, p)
        finally:
            tmp.cleanup()

    def test_save_rejects_bad_items_per_page(self):
        from rcm_mc.ui.preferences import (
            UserPreferences, save_preferences,
        )
        store, tmp = self._store()
        try:
            p = UserPreferences(
                username="alice", items_per_page=1)
            with self.assertRaises(ValueError):
                save_preferences(store, p)
            p.items_per_page = 5000
            with self.assertRaises(ValueError):
                save_preferences(store, p)
        finally:
            tmp.cleanup()


class TestFavorites(unittest.TestCase):
    def _store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "p.db")
        store = PortfolioStore(db)
        store.init_db()
        return store, tmp

    def test_toggle_adds_then_removes(self):
        from rcm_mc.ui.preferences import (
            toggle_favorite_hospital,
            is_favorite_hospital,
        )
        store, tmp = self._store()
        try:
            self.assertFalse(
                is_favorite_hospital(
                    store, "alice", "010001"))
            self.assertTrue(
                toggle_favorite_hospital(
                    store, "alice", "010001"))
            self.assertTrue(
                is_favorite_hospital(
                    store, "alice", "010001"))
            self.assertFalse(
                toggle_favorite_hospital(
                    store, "alice", "010001"))
            self.assertFalse(
                is_favorite_hospital(
                    store, "alice", "010001"))
        finally:
            tmp.cleanup()

    def test_list_favorites(self):
        from rcm_mc.ui.preferences import (
            toggle_favorite_hospital,
            list_favorite_hospitals,
        )
        store, tmp = self._store()
        try:
            toggle_favorite_hospital(
                store, "alice", "010001")
            toggle_favorite_hospital(
                store, "alice", "060001")
            favs = list_favorite_hospitals(
                store, "alice")
            self.assertEqual(set(favs),
                             {"010001", "060001"})
        finally:
            tmp.cleanup()

    def test_user_isolation(self):
        """Alice's favorites don't appear in Bob's list."""
        from rcm_mc.ui.preferences import (
            toggle_favorite_hospital,
            list_favorite_hospitals,
        )
        store, tmp = self._store()
        try:
            toggle_favorite_hospital(
                store, "alice", "010001")
            toggle_favorite_hospital(
                store, "bob", "060001")
            self.assertEqual(
                list_favorite_hospitals(store, "alice"),
                ["010001"])
            self.assertEqual(
                list_favorite_hospitals(store, "bob"),
                ["060001"])
        finally:
            tmp.cleanup()

    def test_empty_username_or_ccn(self):
        from rcm_mc.ui.preferences import (
            toggle_favorite_hospital,
            is_favorite_hospital,
        )
        store, tmp = self._store()
        try:
            self.assertFalse(
                toggle_favorite_hospital(
                    store, "", "010001"))
            self.assertFalse(
                toggle_favorite_hospital(
                    store, "alice", ""))
            self.assertFalse(
                is_favorite_hospital(
                    store, "", "010001"))
        finally:
            tmp.cleanup()


class TestCustomWidgets(unittest.TestCase):
    def _store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        tmp = tempfile.TemporaryDirectory()
        db = os.path.join(tmp.name, "p.db")
        store = PortfolioStore(db)
        store.init_db()
        return store, tmp

    def test_add_widget(self):
        from rcm_mc.ui.preferences import (
            CustomDashboardWidget,
            add_custom_widget, get_preferences,
        )
        store, tmp = self._store()
        try:
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="model_quality",
                    label="Model Quality",
                    target_url="/models/quality",
                    position=1))
            prefs = get_preferences(store, "alice")
            self.assertEqual(
                len(prefs.custom_widgets), 1)
            self.assertEqual(
                prefs.custom_widgets[0].label,
                "Model Quality")
        finally:
            tmp.cleanup()

    def test_widgets_sorted_by_position(self):
        from rcm_mc.ui.preferences import (
            CustomDashboardWidget,
            add_custom_widget, get_preferences,
        )
        store, tmp = self._store()
        try:
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="b", label="B",
                    target_url="/b", position=2))
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="a", label="A",
                    target_url="/a", position=1))
            prefs = get_preferences(store, "alice")
            self.assertEqual(
                [w.label for w in prefs.custom_widgets],
                ["A", "B"])
        finally:
            tmp.cleanup()

    def test_add_replaces_same_id(self):
        from rcm_mc.ui.preferences import (
            CustomDashboardWidget,
            add_custom_widget, get_preferences,
        )
        store, tmp = self._store()
        try:
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="m", label="V1",
                    target_url="/v1"))
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="m", label="V2",
                    target_url="/v2"))
            prefs = get_preferences(store, "alice")
            self.assertEqual(
                len(prefs.custom_widgets), 1)
            self.assertEqual(
                prefs.custom_widgets[0].label, "V2")
        finally:
            tmp.cleanup()

    def test_remove_widget(self):
        from rcm_mc.ui.preferences import (
            CustomDashboardWidget,
            add_custom_widget, remove_custom_widget,
            get_preferences,
        )
        store, tmp = self._store()
        try:
            add_custom_widget(
                store, "alice",
                CustomDashboardWidget(
                    widget_id="m", label="X",
                    target_url="/x"))
            self.assertTrue(
                remove_custom_widget(
                    store, "alice", "m"))
            prefs = get_preferences(store, "alice")
            self.assertEqual(prefs.custom_widgets, [])
            # Removing again returns False
            self.assertFalse(
                remove_custom_widget(
                    store, "alice", "m"))
        finally:
            tmp.cleanup()


class TestNotifications(unittest.TestCase):
    def test_round_trip(self):
        from rcm_mc.ui.preferences import (
            UserPreferences, NotificationSettings,
            save_preferences, get_preferences,
        )
        from rcm_mc.portfolio.store import PortfolioStore
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            p = UserPreferences(
                username="alice",
                notifications=NotificationSettings(
                    email="alice@example.com",
                    alert_critical=True,
                    alert_high=False,
                    weekly_digest=True))
            save_preferences(store, p)
            loaded = get_preferences(store, "alice")
            self.assertEqual(
                loaded.notifications.email,
                "alice@example.com")
            self.assertTrue(
                loaded.notifications.alert_critical)
            self.assertFalse(
                loaded.notifications.alert_high)
            self.assertTrue(
                loaded.notifications.weekly_digest)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
