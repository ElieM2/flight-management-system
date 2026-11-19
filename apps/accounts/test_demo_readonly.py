import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.demo import DEMO_READONLY_GROUP, is_demo_readonly_user


User = get_user_model()


class EnsureDemoUserTests(TestCase):
    def test_creates_active_non_staff_user_and_is_idempotent(self):
        env = {
            "DEMO_USERNAME": "demo_reader",
            "DEMO_PASSWORD": "DemoPass!2026",
        }
        with patch.dict(os.environ, env, clear=False):
            call_command("ensure_demo_user")
            call_command("ensure_demo_user")

        user = User.objects.get(username="demo_reader")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("DemoPass!2026"))
        self.assertTrue(user.groups.filter(name=DEMO_READONLY_GROUP).exists())
        self.assertTrue(is_demo_readonly_user(user))
        self.assertEqual(User.objects.filter(username="demo_reader").count(), 1)

    def test_skips_when_credentials_missing(self):
        with patch.dict(os.environ, {"DEMO_USERNAME": "", "DEMO_PASSWORD": ""}, clear=False):
            call_command("ensure_demo_user")
        self.assertFalse(User.objects.filter(username="").exists())


class DemoReadOnlyAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        env = {
            "DEMO_USERNAME": "demo_reader",
            "DEMO_PASSWORD": "DemoPass!2026",
        }
        with patch.dict(os.environ, env, clear=False):
            with override_settings(DEMO_USERNAME="demo_reader"):
                call_command("ensure_demo_user")
        self.user = User.objects.get(username="demo_reader")
        self.client.force_login(self.user)

    @override_settings(DEMO_USERNAME="demo_reader")
    def test_demo_user_can_open_dashboard_and_sync_page(self):
        for name in (
            "dashboard:dashboard",
            "analytics:home",
            "monitoring:monitoring_home",
            "monitoring:flight_map",
            "integrations:sync_page",
        ):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, msg=name)

    @override_settings(DEMO_USERNAME="demo_reader")
    def test_demo_user_cannot_post_sync_or_edit_profile(self):
        sync_response = self.client.post(
            reverse("integrations:sync_page"),
            {"limit": "10"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(sync_response.status_code, 403)

        edit_response = self.client.post(
            reverse("accounts:edit_profile"),
            {"username": "hacked"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(edit_response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "demo_reader")

    @override_settings(DEMO_USERNAME="demo_reader")
    def test_demo_user_can_switch_language(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "fr", "next": "/"},
        )
        self.assertIn(response.status_code, {200, 302})

    def test_regular_user_is_not_treated_as_demo(self):
        regular = User.objects.create_user(username="regular", password="Regular!2026")
        self.assertFalse(is_demo_readonly_user(regular))
