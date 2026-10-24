from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

OPEN_PATHS = ("/login/", "/admin/", "/static/", "/healthz/", "/tick/")


class LoginRequiredMiddleware:
    """Private tool: every page needs a login (admin has its own login)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not request.path.startswith(OPEN_PATHS):
            return redirect(f"{reverse(settings.LOGIN_URL)}?next={request.path}")
        return self.get_response(request)
