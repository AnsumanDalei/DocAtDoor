from django.urls import path
from . import views
app_name="appointments"
urlpatterns=[path("doctors/",views.doctors,name="doctors"),path("doctors/<int:doctor_id>/",views.doctor_profile,name="doctor_profile"),path("doctors/<int:doctor_id>/slots/",views.available_slots,name="available_slots"),path("book/",views.book,name="book"),path("<int:pk>/cancel/",views.cancel,name="cancel"),path("<int:pk>/reschedule/",views.reschedule,name="reschedule"),path("doctor/",views.doctor_dashboard,name="doctor_dashboard"),path("<int:pk>/accept/",views.accept,name="accept"),path("<int:pk>/reject/",views.reject,name="reject"),path("<int:pk>/complete/",views.complete,name="complete"),path("slots/add/",views.add_slot,name="add_slot"),path("slots/<int:pk>/remove/",views.remove_slot,name="remove_slot")]
