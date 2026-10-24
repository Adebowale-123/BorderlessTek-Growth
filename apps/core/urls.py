from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.today, name="today"),
    path("healthz/", views.healthz, name="healthz"),
    path("tick/", views.tick, name="tick"),
    path("scan-now/", views.scan_now, name="scan_now"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/test-alert/", views.test_alert, name="test_alert"),
]
