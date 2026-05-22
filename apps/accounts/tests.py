from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from apps.accounts import views
from apps.accounts.models import Profile


class AccountsViewsTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="accounts-view-user",
            email="accounts@example.com",
            password="test-password",
            first_name="Account",
            last_name="Tester",
        )


class AccountsSafeRedirectTests(AccountsViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_safe_redirect_url_returns_safe_get_next_url(self):
        request = self.factory.get(
            "/accounts/login/",
            {
                "next": "/dashboard/",
            },
            HTTP_HOST="testserver",
        )

        result = views.get_safe_redirect_url(request, "dashboard:dashboard")

        self.assertEqual(result, "/dashboard/")

    def test_get_safe_redirect_url_rejects_external_get_next_url(self):
        request = self.factory.get(
            "/accounts/login/",
            {
                "next": "https://evil.example.com/dashboard/",
            },
            HTTP_HOST="testserver",
        )

        result = views.get_safe_redirect_url(request, "dashboard:dashboard")

        self.assertEqual(result, "dashboard:dashboard")

    def test_get_safe_redirect_url_prefers_post_next_url(self):
        request = self.factory.post(
            "/accounts/login/",
            {
                "next": "/monitoring/",
            },
            HTTP_HOST="testserver",
        )

        result = views.get_safe_redirect_url(request, "dashboard:dashboard")

        self.assertEqual(result, "/monitoring/")


class AccountsRegisterViewTests(AccountsViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_register_view_redirects_authenticated_user(self):
        request = self.factory.get("/accounts/register/")
        request.user = self.user

        with patch("apps.accounts.views.redirect") as mocked_redirect:
            mocked_redirect.return_value = SimpleNamespace(status_code=302)

            response = views.register_view(request)

        self.assertEqual(response.status_code, 302)
        mocked_redirect.assert_called_once_with("dashboard:dashboard")

    def test_register_view_get_renders_empty_form(self):
        request = self.factory.get("/accounts/register/", {"next": "/dashboard/"})
        request.user = AnonymousUser()

        with patch("apps.accounts.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.register_view(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "accounts/register.html")
        self.assertIn("form", context)
        self.assertEqual(context["next"], "/dashboard/")

    def test_register_view_post_valid_form_creates_profile_logs_in_and_redirects(self):
        request = self.factory.post(
            "/accounts/register/",
            {
                "username": "new-user",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "next": "/dashboard/",
            },
            HTTP_HOST="testserver",
        )
        request.user = AnonymousUser()

        created_user = get_user_model().objects.create_user(
            username="registered-by-form",
            password="test-password",
        )

        fake_form = Mock()
        fake_form.is_valid.return_value = True
        fake_form.save.return_value = created_user

        with patch("apps.accounts.views.RegisterForm", return_value=fake_form):
            with patch("apps.accounts.views.login") as mocked_login:
                with patch("apps.accounts.views.messages.success") as mocked_success:
                    with patch("apps.accounts.views.redirect") as mocked_redirect:
                        mocked_redirect.return_value = SimpleNamespace(status_code=302)

                        response = views.register_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Profile.objects.filter(user=created_user).exists())
        mocked_login.assert_called_once_with(request, created_user)
        mocked_success.assert_called_once()
        mocked_redirect.assert_called_once_with("/dashboard/")

    def test_register_view_post_invalid_form_renders_template(self):
        request = self.factory.post("/accounts/register/", {"username": ""})
        request.user = AnonymousUser()

        fake_form = Mock()
        fake_form.is_valid.return_value = False

        with patch("apps.accounts.views.RegisterForm", return_value=fake_form):
            with patch("apps.accounts.views.render") as mocked_render:
                mocked_render.return_value = SimpleNamespace(status_code=200)

                response = views.register_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_render.call_args.args[1], "accounts/register.html")


class AccountsLoginViewTests(AccountsViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_login_view_redirects_authenticated_user(self):
        request = self.factory.get("/accounts/login/")
        request.user = self.user

        with patch("apps.accounts.views.redirect") as mocked_redirect:
            mocked_redirect.return_value = SimpleNamespace(status_code=302)

            response = views.login_view(request)

        self.assertEqual(response.status_code, 302)
        mocked_redirect.assert_called_once_with("dashboard:dashboard")

    def test_login_view_get_renders_form(self):
        request = self.factory.get("/accounts/login/", {"next": "/dashboard/"})
        request.user = AnonymousUser()

        with patch("apps.accounts.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.login_view(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "accounts/login.html")
        self.assertIn("form", context)
        self.assertEqual(context["next"], "/dashboard/")

    def test_login_view_post_valid_form_logs_user_in_and_redirects(self):
        request = self.factory.post(
            "/accounts/login/",
            {
                "username": "accounts-view-user",
                "password": "test-password",
                "next": "/dashboard/",
            },
            HTTP_HOST="testserver",
        )
        request.user = AnonymousUser()

        fake_form = Mock()
        fake_form.is_valid.return_value = True
        fake_form.get_user.return_value = self.user

        with patch("apps.accounts.views.LoginForm", return_value=fake_form):
            with patch("apps.accounts.views.login") as mocked_login:
                with patch("apps.accounts.views.messages.success") as mocked_success:
                    with patch("apps.accounts.views.redirect") as mocked_redirect:
                        mocked_redirect.return_value = SimpleNamespace(status_code=302)

                        response = views.login_view(request)

        self.assertEqual(response.status_code, 302)
        mocked_login.assert_called_once_with(request, self.user)
        mocked_success.assert_called_once()
        mocked_redirect.assert_called_once_with("/dashboard/")

    def test_login_view_post_invalid_form_renders_template(self):
        request = self.factory.post("/accounts/login/", {"username": ""})
        request.user = AnonymousUser()

        fake_form = Mock()
        fake_form.is_valid.return_value = False

        with patch("apps.accounts.views.LoginForm", return_value=fake_form):
            with patch("apps.accounts.views.render") as mocked_render:
                mocked_render.return_value = SimpleNamespace(status_code=200)

                response = views.login_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_render.call_args.args[1], "accounts/login.html")


class AccountsProfileViewsTests(AccountsViewsTestDataMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_logout_view_logs_out_user_and_redirects_home(self):
        request = self.factory.get("/accounts/logout/")
        request.user = self.user

        with patch("apps.accounts.views.logout") as mocked_logout:
            with patch("apps.accounts.views.messages.success") as mocked_success:
                with patch("apps.accounts.views.redirect") as mocked_redirect:
                    mocked_redirect.return_value = SimpleNamespace(status_code=302)

                    response = views.logout_view(request)

        self.assertEqual(response.status_code, 302)
        mocked_logout.assert_called_once_with(request)
        mocked_success.assert_called_once()
        mocked_redirect.assert_called_once_with("dashboard:home")

    def test_profile_view_gets_or_creates_profile_and_renders_context(self):
        Profile.objects.filter(user=self.user).delete()

        request = self.factory.get("/accounts/profile/")
        request.user = self.user

        with patch("apps.accounts.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.profile_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "accounts/profile.html")
        self.assertEqual(context["user_obj"], self.user)
        self.assertEqual(context["profile_obj"].user, self.user)

    def test_edit_profile_view_get_renders_user_and_profile_forms(self):
        request = self.factory.get("/accounts/profile/edit/")
        request.user = self.user

        with patch("apps.accounts.views.render") as mocked_render:
            mocked_render.return_value = SimpleNamespace(status_code=200)

            response = views.edit_profile_view(request)

        self.assertEqual(response.status_code, 200)

        template_name = mocked_render.call_args.args[1]
        context = mocked_render.call_args.args[2]

        self.assertEqual(template_name, "accounts/edit_profile.html")
        self.assertIn("user_form", context)
        self.assertIn("profile_form", context)
        self.assertEqual(context["user_obj"], self.user)
        self.assertEqual(context["profile_obj"].user, self.user)

    def test_edit_profile_view_post_valid_forms_saves_and_redirects(self):
        profile, _ = Profile.objects.get_or_create(user=self.user)

        request = self.factory.post(
            "/accounts/profile/edit/",
            {
                "first_name": "Updated",
                "last_name": "User",
            },
        )
        request.user = self.user


        fake_user_form = Mock()
        fake_user_form.is_valid.return_value = True

        fake_profile_form = Mock()
        fake_profile_form.is_valid.return_value = True

        with patch("apps.accounts.views.UserUpdateForm", return_value=fake_user_form):
            with patch("apps.accounts.views.ProfileUpdateForm", return_value=fake_profile_form):
                with patch("apps.accounts.views.messages.success") as mocked_success:
                    with patch("apps.accounts.views.redirect") as mocked_redirect:
                        mocked_redirect.return_value = SimpleNamespace(status_code=302)

                        response = views.edit_profile_view(request)

        self.assertEqual(response.status_code, 302)
        fake_user_form.save.assert_called_once()
        fake_profile_form.save.assert_called_once()
        mocked_success.assert_called_once()
        mocked_redirect.assert_called_once_with("accounts:profile")
        self.assertTrue(Profile.objects.filter(pk=profile.pk).exists())

    def test_edit_profile_view_post_invalid_forms_renders_template(self):
        request = self.factory.post("/accounts/profile/edit/", {"first_name": ""})
        request.user = self.user


        fake_user_form = Mock()
        fake_user_form.is_valid.return_value = False

        fake_profile_form = Mock()
        fake_profile_form.is_valid.return_value = True

        with patch("apps.accounts.views.UserUpdateForm", return_value=fake_user_form):
            with patch("apps.accounts.views.ProfileUpdateForm", return_value=fake_profile_form):
                with patch("apps.accounts.views.render") as mocked_render:
                    mocked_render.return_value = SimpleNamespace(status_code=200)

                    response = views.edit_profile_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_render.call_args.args[1], "accounts/edit_profile.html")
