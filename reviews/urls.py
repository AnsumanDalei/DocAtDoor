from django.urls import path
from . import views
app_name = "reviews"
urlpatterns = [path("appointment/<int:appointment_id>/", views.create_or_update, name="create"), path("mine/", views.doctor_reviews, name="doctor_reviews")]
