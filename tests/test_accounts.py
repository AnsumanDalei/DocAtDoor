import pytest
from django.contrib.auth.hashers import make_password
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse


def test_redacted_development_email_backend_does_not_log_message_body(caplog):
    from django.core.mail import EmailMessage, get_connection

    secret_code = "731904"
    backend = get_connection(backend="accounts.backends.RedactedConsoleEmailBackend")
    sent = backend.send_messages([
        EmailMessage("Verification", f"Your one-time code is {secret_code}", "from@example.test", ["person@example.test"])
    ])

    assert sent == 0
    assert secret_code not in caplog.text
    assert "person@example.test" not in caplog.text

from accounts.models import User


@pytest.mark.django_db
def test_superuser_can_sign_in_to_admin_without_patient_email_otp(client):
    admin = User.objects.create_superuser(email="admin@example.com", password="AdminPass123", name="Site Admin")
    assert admin.email_verified is True
    assert admin.is_staff is True
    response = client.post(reverse("accounts:login"), {"username": admin.email, "password": "AdminPass123"})
    assert response.status_code == 302
    assert response.url == reverse("dashboard:admin_dashboard")


@pytest.mark.django_db
def test_patient_registration_is_auto_verified_but_email_unverified(client):
    resp = client.post(reverse("accounts:register"), {
        "name": "New Patient", "email": "newpatient@example.com", "password": "TestPass123", "password_confirm": "TestPass123",
    })
    assert resp.status_code == 302
    user = User.objects.get(email="newpatient@example.com")
    assert user.check_password("TestPass123")
    assert user.role == User.Role.PATIENT
    assert user.is_verified is True          # patients don't need admin verification
    assert user.email_verified is False       # but must still confirm their email
    assert user.email_verification_token
    assert len(user.email_verification_code_hash) > 6
    assert not user.email_verification_code_hash.isdigit()
    assert user.email_verification_expires_at > timezone.now()


@pytest.mark.django_db
def test_public_registration_has_no_role_field_at_all(client):
    from accounts.forms import RegisterForm
    assert "role" not in RegisterForm().fields


@pytest.mark.django_db
def test_registration_ignores_a_tampered_role_doctor_field(client):
    """Public registration is patient-only. role isn't a form field, so a
    crafted POST including it must be silently ignored, never honored."""
    resp = client.post(reverse("accounts:register"), {
        "name": "Sneaky Doctor", "email": "sneakydoctor@example.com",
        "role": "doctor", "password": "TestPass123", "password_confirm": "TestPass123",
    })
    assert resp.status_code == 302
    user = User.objects.get(email="sneakydoctor@example.com")
    assert user.role == User.Role.PATIENT


@pytest.mark.django_db
def test_registration_ignores_tampered_doctor_only_fields(client):
    resp = client.post(reverse("accounts:register"), {
        "name": "Sneaky Second Doctor", "email": "sneakydoctor2@example.com", "password": "TestPass123", "password_confirm": "TestPass123",
        "specialization": "Cardiologist", "qualification": "MBBS", "experience_years": "10",
        "consultation_fee": "500",
    })
    assert resp.status_code == 302
    user = User.objects.get(email="sneakydoctor2@example.com")
    assert user.role == User.Role.PATIENT
    assert not user.specialization
    assert not user.qualification


@pytest.mark.django_db
def test_login_blocked_until_email_verified(client, patient):
    patient.email_verified = False
    patient.save()
    resp = client.post(reverse("accounts:login"), {"username": patient.email, "password": "TestPass123"})
    assert resp.status_code == 302
    assert resp.url == reverse("accounts:verify_otp")
    resp = client.get(reverse("dashboard:home_dashboard"))
    assert resp.status_code == 302  # still anonymous, login_required bounced us


@pytest.mark.django_db
def test_email_verification_link_activates_login(client):
    user = User.objects.create_user(
        email="verifyme@example.com", password="TestPass123", name="Verify Me", role=User.Role.PATIENT,
    )
    user.issue_verification_code()
    user.save()
    resp = client.get(reverse("accounts:verify", args=[user.email_verification_token]))
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is False
    resp = client.post(reverse("accounts:verify", args=[user.email_verification_token]))
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.email_verified is True
    assert user.email_verification_token is None
    resp = client.post(reverse("accounts:login"), {"username": user.email, "password": "TestPass123"})
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:home_dashboard")


@pytest.mark.django_db
def test_legacy_verification_link_requires_post_and_expires(client):
    user = User.objects.create_user(
        email="expired-link@example.com", password="TestPass123", name="Expired Link",
    )
    user.issue_verification_code()
    user.email_verification_expires_at = timezone.now() - timedelta(minutes=1)
    user.save()
    url = reverse("accounts:verify", args=[user.email_verification_token])
    assert client.get(url).status_code == 200
    response = client.post(url)
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email_verified is False
    assert user.email_verification_token


@pytest.mark.django_db
def test_email_otp_verifies_account_and_cannot_be_reused(client):
    user = User.objects.create_user(
        email="otp@example.com", password="TestPass123", name="OTP Patient", role=User.Role.PATIENT,
    )
    user.email_verification_token = "legacy-token"
    user.email_verification_code_hash = make_password("123456")
    user.email_verification_expires_at = timezone.now() + timedelta(minutes=10)
    user.save()
    code = "123456"
    response = client.post(reverse("accounts:verify_otp"), {"email": user.email, "code": code})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email_verified is True
    assert user.email_verification_code_hash == ""
    assert user.email_verification_expires_at is None

    response = client.post(reverse("accounts:verify_otp"), {"email": user.email, "code": code})
    assert response.status_code == 200
    assert "invalid, expired, or unavailable" in response.content.decode()


@pytest.mark.django_db
def test_email_otp_expires_and_wrong_attempts_are_limited(client):
    user = User.objects.create_user(
        email="expiredotp@example.com", password="TestPass123", name="Expired OTP", role=User.Role.PATIENT,
    )
    user.email_verification_code_hash = make_password("123456")
    user.email_verification_expires_at = timezone.now() - timedelta(minutes=1)
    user.save()
    response = client.post(reverse("accounts:verify_otp"), {"email": user.email, "code": "123456"})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is False

    user.email_verification_expires_at = timezone.now() + timedelta(minutes=10)
    user.email_verification_code_hash = make_password("654321")
    user.email_verification_attempts = 0
    user.save()
    for _ in range(5):
        client.post(reverse("accounts:verify_otp"), {"email": user.email, "code": "000000"})
    user.refresh_from_db()
    assert user.email_verification_attempts == 5
    response = client.post(reverse("accounts:verify_otp"), {"email": user.email, "code": "654321"})
    user.refresh_from_db()
    assert response.status_code == 200
    assert user.email_verified is False


@pytest.mark.django_db
def test_unverified_doctor_can_still_log_in(client, doctor):
    """is_verified (admin approval) only controls search visibility, not login —
    only email_verified gates the login itself."""
    doctor.is_verified = False
    doctor.save()
    resp = client.post(reverse("accounts:login"), {"username": doctor.email, "password": "TestPass123"})
    assert resp.status_code == 302


@pytest.mark.django_db
def test_forgot_and_reset_password_flow(client, patient):
    resp = client.post(reverse("accounts:forgot"), {"email": patient.email})
    assert resp.status_code == 302
    patient.refresh_from_db()
    assert patient.reset_token

    resp = client.get(reverse("accounts:reset", args=[patient.reset_token]))
    assert resp.status_code == 200

    resp = client.post(reverse("accounts:reset", args=[patient.reset_token]), {
        "new_password1": "BrandNewPass123", "new_password2": "BrandNewPass123",
    })
    assert resp.status_code == 302
    patient.refresh_from_db()
    assert patient.check_password("BrandNewPass123")
    assert patient.reset_token is None

    resp = client.post(reverse("accounts:login"), {"username": patient.email, "password": "BrandNewPass123"})
    assert resp.status_code == 302


@pytest.mark.django_db
def test_registration_ignores_a_tampered_role_admin_field(client):
    resp = client.post(reverse("accounts:register"), {
        "name": "Sneaky Admin", "email": "sneaky@example.com",
        "role": "admin", "password": "TestPass123", "password_confirm": "TestPass123",
    })
    assert resp.status_code == 302
    user = User.objects.get(email="sneaky@example.com")
    assert user.role == User.Role.PATIENT
    assert user.is_staff is False
    assert user.is_superuser is False


@pytest.mark.django_db
def test_patient_profile_form_hides_doctor_only_fields(client, patient):
    client.force_login(patient)
    resp = client.get(reverse("accounts:profile"))
    assert "specialization" not in resp.context["form"].fields
    assert "consultation_fee" not in resp.context["form"].fields


@pytest.mark.django_db
def test_doctor_profile_form_still_has_doctor_fields(client, doctor):
    client.force_login(doctor)
    resp = client.get(reverse("accounts:profile"))
    assert "specialization" in resp.context["form"].fields
    assert "consultation_fee" in resp.context["form"].fields


@pytest.mark.django_db
def test_patient_cannot_set_doctor_only_fields_via_profile_post(client, patient):
    client.force_login(patient)
    client.post(reverse("accounts:profile"), {
        "name": patient.name, "specialization": "Cardiologist", "consultation_fee": "999",
    })
    patient.refresh_from_db()
    assert not patient.specialization
    assert patient.consultation_fee is None


@pytest.mark.django_db
def test_doctor_can_update_their_own_doctor_fields_via_profile(client, doctor):
    client.force_login(doctor)
    resp = client.post(reverse("accounts:profile"), {
        "name": doctor.name, "specialization": "Neurologist", "consultation_fee": "750",
    })
    assert resp.status_code == 302
    doctor.refresh_from_db()
    assert doctor.specialization == "Neurologist"


@pytest.mark.django_db
def test_home_and_nav_expose_no_public_doctor_registration_link(client):
    resp = client.get(reverse("dashboard:home"))
    body = resp.content.decode()
    assert "role=doctor" not in body
    for phrase in ["I am a doctor", "Join as doctor", "Register as doctor", "Doctor registration"]:
        assert phrase.lower() not in body.lower()


@pytest.mark.django_db
def test_resend_verification_reissues_token_for_unverified_email(client):
    user = User.objects.create_user(
        email="resend@example.com", password="TestPass123", name="Resend Me", role=User.Role.PATIENT,
    )
    old_token = user.email_verification_token
    resp = client.post(reverse("accounts:resend_verification"), {"email": user.email})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.email_verification_token != old_token
    assert len(user.email_verification_code_hash) > 6
    assert not user.email_verification_code_hash.isdigit()
    assert user.email_verification_expires_at > timezone.now()


@pytest.mark.django_db
def test_registration_keeps_user_in_same_otp_flow_without_reentering_email(client):
    from unittest.mock import patch
    from accounts import views

    with patch.object(views, "_mail", return_value=1) as send:
        response = client.post(reverse("accounts:register"), {
            "name": "Flow Patient", "email": "flow@example.com",
            "password": "FlowSafePassword123!", "password_confirm": "FlowSafePassword123!",
        })
    assert response.status_code == 302
    assert response.url == reverse("accounts:verify_otp")
    user = User.objects.get(email="flow@example.com")
    assert str(client.session["pending_registration_user_id"]) == str(user.pk)
    assert send.call_args.args[0].pk == user.pk
    page = client.get(reverse("accounts:verify_otp"))
    body = page.content.decode()
    assert user.email in body
    assert 'label for="id_email">Email address' not in body


@pytest.mark.django_db
def test_two_same_email_accounts_require_explicit_account_choice(client, patient):
    second = User.objects.create_user(
        email=patient.email.upper(), password="TestPass123", name="Second Patient",
        role=User.Role.PATIENT, is_verified=True, email_verified=True,
    )
    response = client.post(reverse("accounts:login"), {
        "email": patient.email, "password": "TestPass123", "remember_me": "on",
    })
    assert response.status_code == 200
    assert len(response.context["account_choices"]) == 2
    assert not client.session.get("_auth_user_id")

    response = client.post(reverse("accounts:login"), {"account_id": str(second.pk)})
    assert response.status_code == 302
    assert str(client.session["_auth_user_id"]) == str(second.pk)
    assert client.session.get_expiry_age() == 60 * 60 * 24 * 30


@pytest.mark.django_db
def test_user_model_rejects_a_third_account_for_the_same_email(patient):
    from django.core.exceptions import ValidationError
    User.objects.create_user(
        email=patient.email, password="TestPass123", name="Second Patient",
    )
    with pytest.raises(ValidationError, match="No more than two accounts"):
        User.objects.create_user(
            email=patient.email.upper(), password="TestPass123", name="Third Patient",
        )


@pytest.mark.django_db
def test_google_signin_does_not_implicitly_link_an_existing_password_account(patient):
    from accounts.views import _resolve_google_signin

    result, error, pending = _resolve_google_signin({
        "email": patient.email, "email_verified": True, "sub": "google-sub-existing",
        "name": "Patient",
    })
    assert result is None
    assert pending is None
    assert "connect Google from Settings" in error
    assert not patient.social_identities.exists()


@pytest.mark.django_db
def test_google_signin_creates_patient_for_new_verified_email():
    from accounts.views import _resolve_google_signin

    user, error, pending = _resolve_google_signin({
        "email": "google-patient@example.com", "email_verified": "true",
        "sub": "google-sub-new", "name": "Google Patient",
    })
    assert error == ""
    assert pending is None
    assert user.role == User.Role.PATIENT
    assert user.email_verified is True
    assert not user.has_usable_password()
    assert user.social_identities.get().subject == "google-sub-new"


@pytest.mark.django_db
def test_google_oauth_callback_completes_a_verified_new_patient_signin(client):
    from unittest.mock import patch
    from django.test import override_settings
    from accounts import views

    with override_settings(
        GOOGLE_OAUTH_ENABLED=True,
        GOOGLE_OAUTH_CLIENT_ID="test-client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="test-client-secret",
    ):
        start = client.get(reverse("accounts:google_start"))
        assert start.status_code == 302
        state = client.session["google_oauth_state"]["value"]
        with patch.object(views, "_google_profile_from_code", return_value={
            "email": "oauth-patient@example.com", "email_verified": True,
            "sub": "google-oauth-callback", "name": "OAuth Patient",
        }):
            response = client.get(reverse("accounts:google_callback"), {"code": "mock-code", "state": state})
    assert response.status_code == 302
    user = User.objects.get(email="oauth-patient@example.com")
    assert str(client.session["_auth_user_id"]) == str(user.pk)
    assert user.role == User.Role.PATIENT
    assert user.social_identities.get().subject == "google-oauth-callback"


@pytest.mark.django_db
def test_profile_and_settings_routes_are_available_from_account_navigation(client, patient):
    client.force_login(patient)
    response = client.get(reverse("accounts:settings"))
    assert response.status_code == 200
    assert "Account &amp; security" in response.content.decode()
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    assert "data-photo-preview" in response.content.decode()


@pytest.mark.django_db
def test_home_is_canonical_and_dashboard_remains_compatible(client, patient):
    client.force_login(patient)
    response = client.get(reverse("dashboard:home_dashboard"))
    assert response.status_code == 200
    assert response.wsgi_request.path == "/home/"
    legacy = client.get(reverse("dashboard:legacy_dashboard"))
    assert legacy.status_code == 302
    assert legacy.url == reverse("dashboard:home_dashboard")
