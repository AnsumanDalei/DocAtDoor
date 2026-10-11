from django.urls import path
from . import views
app_name="accounts"
urlpatterns=[path("register/", views.register, name="register"),path("login/",views.login_view,name="login"),path("logout/",views.logout_view,name="logout"),path("verify/<str:token>/",views.verify,name="verify"),path("verify-email/",views.verify_otp,name="verify_otp"),path("resend-verification/",views.resend_verification,name="resend_verification"),path("forgot-password/",views.forgot_password,name="forgot"),path("reset-password/<str:token>/",views.reset_password,name="reset"),path("profile/",views.profile,name="profile"),path("change-password/",views.change_password,name="change_password"),path("doctor-application/",views.doctor_application_status,name="doctor_application_status")]
urlpatterns += [
    path("settings/", views.settings_page, name="settings"),
    path("google/start/", views.google_start, name="google_start"),
    path("google/callback/", views.google_callback, name="google_callback"),
]
