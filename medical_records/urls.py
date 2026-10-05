from django.urls import path
from . import views
app_name="records"
urlpatterns=[path("reports/",views.reports,name="reports"),path("prescriptions/",views.prescriptions,name="prescriptions"),path("reports/upload/",views.upload_report,name="upload_report"),path("reports/<int:pk>/download/",views.download_report,name="download_report"),path("reports/<int:pk>/delete/",views.delete_report,name="delete_report"),path("appointments/<int:appointment_id>/prescription/",views.prescription,name="prescription"),path("appointments/<int:appointment_id>/prescription/download/",views.download_prescription,name="download_prescription"),path("appointments/<int:appointment_id>/consultation/",views.consultation,name="consultation")]
