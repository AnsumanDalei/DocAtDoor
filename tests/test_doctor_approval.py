from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment


def _doctor_application(email, status=User.DoctorApprovalStatus.PENDING):
    return User.objects.create_user(
        email=email,
        password="TestPass123",
        name="Dr. Applying",
        role=User.Role.DOCTOR,
        specialization="Cardiologist",
        qualification="MBBS",
        email_verified=True,
        is_verified=status == User.DoctorApprovalStatus.APPROVED,
        doctor_approval_status=status,
        is_available=True,
    )


def _visit_time():
    date = timezone.localdate() + timedelta(days=2)
    return timezone.make_aware(datetime.combine(date, time(10, 0)))


@pytest.mark.django_db
def test_pending_doctor_cannot_open_doctor_dashboard(client):
    doctor = _doctor_application("pending-dashboard@example.test")
    client.force_login(doctor)

    response = client.get(reverse("appointments:doctor_dashboard"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:doctor_application_status")
    status_page = client.get(response.url)
    assert status_page.status_code == 200
    assert b"Your registration has been submitted" in status_page.content
    assert b"You do not need to register again" in status_page.content


@pytest.mark.django_db
def test_approved_doctor_can_open_doctor_dashboard(client, doctor):
    client.force_login(doctor)
    response = client.get(reverse("appointments:doctor_dashboard"))
    assert response.status_code == 200
    assert b"DOCTOR WORKSPACE" in response.content


@pytest.mark.django_db
def test_rejected_doctor_is_directed_to_rejection_information(client):
    doctor = _doctor_application(
        "rejected-dashboard@example.test",
        User.DoctorApprovalStatus.REJECTED,
    )
    client.force_login(doctor)

    response = client.get(reverse("appointments:doctor_dashboard"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:doctor_application_status")
    status_page = client.get(response.url)
    assert status_page.status_code == 200
    assert b"Your application was not approved" in status_page.content
    assert b"Contact DocAtDoor support" in status_page.content


@pytest.mark.django_db
@pytest.mark.parametrize("approval_status", [
    User.DoctorApprovalStatus.PENDING,
    User.DoctorApprovalStatus.REJECTED,
])
def test_unapproved_doctors_are_hidden_from_web_and_api_directories(client, approval_status):
    doctor = _doctor_application(f"{approval_status}@example.test", approval_status)
    web = client.get(reverse("appointments:doctors"))
    api = APIClient().get(reverse("api:doctors"))

    assert doctor not in web.context["doctors"]
    assert api.status_code == 200
    assert doctor.pk not in {item["id"] for item in api.json()["results"]}
    assert client.get(reverse("appointments:doctor_profile", args=[doctor.pk])).status_code == 404
    assert client.get(reverse("appointments:available_slots", args=[doctor.pk]), {"date": timezone.localdate().isoformat()}).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("approval_status", [
    User.DoctorApprovalStatus.PENDING,
    User.DoctorApprovalStatus.REJECTED,
])
def test_unapproved_doctors_cannot_be_booked_through_web_or_api(client, patient, approval_status):
    doctor = _doctor_application(f"booking-{approval_status}@example.test", approval_status)
    client.force_login(patient)
    scheduled_at = _visit_time()
    payload = {
        "doctor": str(doctor.pk),
        "symptom_description": "Fictional appointment request",
        "address": "1 Example Street",
        "city": "Example City",
        "contact_phone": "1234567890",
        "scheduled_at": scheduled_at.strftime("%Y-%m-%dT%H:%M"),
    }

    client.post(reverse("appointments:book"), payload)
    api_payload = {**payload, "scheduled_at": scheduled_at.isoformat()}
    api = APIClient()
    api.force_authenticate(patient)
    api_response = api.post(reverse("api:appointments"), api_payload, format="json")

    assert Appointment.objects.filter(patient=patient).count() == 0
    assert api_response.status_code == 400


@pytest.mark.django_db
def test_approved_doctor_can_be_booked_through_api(patient, doctor):
    api = APIClient()
    api.force_authenticate(patient)
    response = api.post(reverse("api:appointments"), {
        "doctor": doctor.pk,
        "symptom_description": "Fictional approved doctor booking",
        "address": "1 Example Street",
        "city": "Example City",
        "contact_phone": "1234567890",
        "scheduled_at": _visit_time().isoformat(),
    }, format="json")

    assert response.status_code == 201
    assert Appointment.objects.get(pk=response.data["id"]).doctor_id == doctor.pk


@pytest.mark.django_db
@pytest.mark.parametrize(("action", "expected"), [
    ("approve_doctors", User.DoctorApprovalStatus.APPROVED),
    ("reject_doctors", User.DoctorApprovalStatus.REJECTED),
])
def test_admin_can_approve_or_reject_doctor_application(client, action, expected):
    doctor = _doctor_application(f"admin-{action}@example.test")
    admin = User.objects.create_superuser(
        email=f"{action}-admin@example.test",
        password="AdminPass123",
        name="Review Admin",
    )
    client.force_login(admin)
    response = client.post(reverse("admin:accounts_user_changelist"), {
        "action": action,
        "_selected_action": [str(doctor.pk)],
        "index": "0",
    })

    assert response.status_code == 302
    doctor.refresh_from_db()
    assert doctor.doctor_approval_status == expected
    assert doctor.is_verified == (expected == User.DoctorApprovalStatus.APPROVED)


@pytest.mark.django_db
@pytest.mark.parametrize("approval_status", [
    User.DoctorApprovalStatus.PENDING,
    User.DoctorApprovalStatus.REJECTED,
])
def test_api_login_does_not_issue_a_token_to_unapproved_doctor(approval_status):
    doctor = _doctor_application(f"api-login-{approval_status}@example.test", approval_status)
    response = APIClient().post(reverse("api:token"), {
        "email": doctor.email,
        "password": "TestPass123",
    }, format="json")

    assert response.status_code == 403
    assert response.data["doctor_approval_status"] == approval_status
    assert "token" not in response.data
