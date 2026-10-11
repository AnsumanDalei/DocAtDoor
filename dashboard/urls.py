from django.urls import path
from django.views.generic import RedirectView
from . import views
app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.dashboard, name="home_dashboard"),
    path("dashboard/", RedirectView.as_view(pattern_name="dashboard:home_dashboard", permanent=False), name="legacy_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]
