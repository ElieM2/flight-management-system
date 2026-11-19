from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from apps.accounts.demo import is_demo_readonly_user


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
ALLOWED_DEMO_UNSAFE = frozenset({
    ("accounts", "login"),
    ("accounts", "logout"),
    (None, "set_language"),
})


class DemoReadOnlyMiddleware:
    """Block create/update/delete/sync writes for the read-only demo account."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method in SAFE_METHODS or not is_demo_readonly_user(getattr(request, "user", None)):
            return None

        match = getattr(request, "resolver_match", None)
        namespace = getattr(match, "namespace", None) if match else None
        url_name = getattr(match, "url_name", None) if match else None
        if (namespace, url_name) in ALLOWED_DEMO_UNSAFE or (None, url_name) in ALLOWED_DEMO_UNSAFE:
            return None

        message = _("This demo account is read-only.")
        accept = request.headers.get("Accept", "")
        if "text/html" in accept and request.headers.get("X-Requested-With") != "XMLHttpRequest":
            messages.error(request, message)
            referer = request.META.get("HTTP_REFERER") or "/"
            return redirect(referer)
        return HttpResponseForbidden(message)
