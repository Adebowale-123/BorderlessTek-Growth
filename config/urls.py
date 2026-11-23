from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core import password_reset as pr

admin.site.site_header = "BorderlessTek Growth"
admin.site.site_title = "BorderlessTek Growth"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", pr.ForgotPasswordView.as_view(), name="password_reset"),
    path("password-reset/sent/", pr.ForgotPasswordDoneView.as_view(), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", pr.ResetPasswordView.as_view(), name="password_reset_confirm"),
    path("password-reset/done/", pr.ResetPasswordCompleteView.as_view(), name="password_reset_complete"),
    path("finder/", include("apps.finder.urls")),
    path("leads/", include("apps.leads.urls")),
    path("", include("apps.core.urls")),
]
