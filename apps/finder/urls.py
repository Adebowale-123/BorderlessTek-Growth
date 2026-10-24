from django.urls import path

from . import views

app_name = "finder"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("<int:pk>/mark/<str:status>/", views.mark, name="mark"),
    path("<int:pk>/redraft/", views.redraft, name="redraft"),
    path("add/", views.add, name="add"),
    path("sources/", views.sources, name="sources"),
    path("sources/<int:pk>/toggle/", views.toggle_source, name="toggle_source"),
    path("sources/<int:pk>/delete/", views.delete_source, name="delete_source"),
]
