# dop_apps/observability/urls.py
from django.urls import path
from . import views

app_name = "observability"

urlpatterns = [
    path("", views.status, name="home"),
    path("status/", views.status, name="status"),
    path("incidents/", views.incidents, name="incidents"),
    path("stations/", views.stations, name="stations"),
    path("freshness/", views.freshness, name="freshness"),

    # Control Tower (1-page dashboard)
    path("control-tower/", views.control_tower, name="control_tower"),

    # Recruiter-facing technical review page
    path("overview/", views.overview, name="overview"),
]
