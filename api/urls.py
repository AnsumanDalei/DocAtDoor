from django.urls import path

from .views import (
    AppointmentActionView,
    AppointmentDetailView,
    AppointmentListCreateView,
    ChangePasswordView,
    ConsultationDetailView,
    DoctorAppointmentListView,
    DoctorAvailabilityView,
    DoctorAvailabilityManagementView,
    DoctorAvailabilitySlotDetailView,
    DoctorDetailView,
    DoctorListView,
    DoctorReviewListView,
    LogoutView,
    PatientAppointmentActionView,
    PatientReviewView,
    PrescriptionDownloadView,
    PrescriptionListView,
    PrescriptionUploadView,
    ProfileView,
    ReportDetailView,
    ReportDownloadView,
    ReportListCreateView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationView,
    TokenLoginView,
    NotificationDetailView,
    NotificationListView,
    NotificationReadAllView,
    ServiceEnquiryCreateView,
    VerificationStatusView,
    VerifyEmailView,
)


class AcceptAppointmentView(AppointmentActionView):
    action = "accept"


class RejectAppointmentView(AppointmentActionView):
    action = "reject"


class CompleteAppointmentView(AppointmentActionView):
    action = "complete"


class CancelAppointmentView(PatientAppointmentActionView):
    action = "cancel"


class RescheduleAppointmentView(PatientAppointmentActionView):
    action = "reschedule"


app_name = "api"
urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenLoginView.as_view(), name="token"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/verification-status/", VerificationStatusView.as_view(), name="verification_status"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("auth/resend-verification/", ResendVerificationView.as_view(), name="resend_verification"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("doctors/", DoctorListView.as_view(), name="doctors"),
    path("doctors/<int:pk>/", DoctorDetailView.as_view(), name="doctor_detail"),
    path("doctors/<int:doctor_id>/availability/", DoctorAvailabilityView.as_view(), name="doctor_availability"),
    path("availability/", DoctorAvailabilityManagementView.as_view(), name="availability_management"),
    path("availability/<int:pk>/", DoctorAvailabilitySlotDetailView.as_view(), name="availability_slot_detail"),
    path("doctors/<int:doctor_id>/reviews/", DoctorReviewListView.as_view(), name="doctor_reviews"),
    path("appointments/", AppointmentListCreateView.as_view(), name="appointments"),
    path("appointments/doctor/", DoctorAppointmentListView.as_view(), name="doctor_appointments"),
    path("appointments/<int:pk>/", AppointmentDetailView.as_view(), name="appointment_detail"),
    path("appointments/<int:pk>/accept/", AcceptAppointmentView.as_view(), name="appointment_accept"),
    path("appointments/<int:pk>/reject/", RejectAppointmentView.as_view(), name="appointment_reject"),
    path("appointments/<int:pk>/complete/", CompleteAppointmentView.as_view(), name="appointment_complete"),
    path("appointments/<int:pk>/cancel/", CancelAppointmentView.as_view(), name="appointment_cancel"),
    path("appointments/<int:pk>/reschedule/", RescheduleAppointmentView.as_view(), name="appointment_reschedule"),
    path("appointments/<int:appointment_id>/consultation/", ConsultationDetailView.as_view(), name="consultation"),
    path("appointments/<int:appointment_id>/prescription/", PrescriptionUploadView.as_view(), name="prescription_upload"),
    path("reviews/appointments/<int:appointment_id>/", PatientReviewView.as_view(), name="review"),
    path("records/reports/", ReportListCreateView.as_view(), name="reports"),
    path("records/reports/<int:pk>/", ReportDetailView.as_view(), name="report_detail"),
    path("records/reports/<int:pk>/download/", ReportDownloadView.as_view(), name="report_download"),
    path("records/prescriptions/", PrescriptionListView.as_view(), name="prescriptions"),
    path("records/prescriptions/<int:pk>/download/", PrescriptionDownloadView.as_view(), name="prescription_download"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/read-all/", NotificationReadAllView.as_view(), name="notifications_read_all"),
    path("notifications/<int:pk>/", NotificationDetailView.as_view(), name="notification_detail"),
    path("service-enquiries/", ServiceEnquiryCreateView.as_view(), name="service_enquiry"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
