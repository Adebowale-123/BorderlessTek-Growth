from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("", views.board, name="board"),
    path("new/", views.detail, name="new"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/followed-up/", views.followed_up, name="followed_up"),
    path("<int:pk>/stage/<str:stage>/", views.set_stage, name="set_stage"),
]
