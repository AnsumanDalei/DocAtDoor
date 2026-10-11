import re
from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from appointments.models import Appointment, AvailabilitySlot
from appointments.scheduling import available_visit_times


@pytest.mark.django_db
def test_api_doctor_directory_only_lists_verified_doctors(doctor, other_doctor, patient):
    hidden = User.objects.create_user(
        email="unverified@example.test", password="DemoCare2026!", name="Hidden Doctor",
        role=User.Role.DOCTOR, is_verified=False, is_available=True,
    )
    response = APIClient().get(reverse("api:doctors"))
    assert response.status_code == 200
    payload = response.json()
    results = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
    ids = {item["id"] for item in results}
    assert doctor.pk in ids and other_doctor.pk in ids
    assert patient.pk not in ids and hidden.pk not in ids


@pytest.mark.django_db
def test_unverified_doctor_cannot_view_or_reject_open_patient_appointments(patient):
    unverified = User.objects.create_user(
        email="pending-doctor@example.test", password="DemoCare2026!", name="Pending Doctor",
        role=User.Role.DOCTOR, is_verified=False, email_verified=True,
    )
    appointment = Appointment.objects.create(
        patient=patient, symptom_description="Fictional request", address="Demo address",
        scheduled_at=timezone.now() + timedelta(days=1), status=Appointment.Status.PENDING,
    )
    api = APIClient()
    api.force_authenticate(user=unverified)

    assert api.get(reverse("api:doctor_appointments")).status_code == 403
    assert api.get(reverse("api:appointment_detail", args=[appointment.pk])).status_code == 403
    assert api.post(reverse("api:appointment_reject", args=[appointment.pk]), {}, format="json").status_code == 403
    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.PENDING


@pytest.mark.django_db
def test_unverified_doctor_cannot_download_patient_report_or_prescription(patient):
    from medical_records.models import MedicalReport, Prescription

    unverified = User.objects.create_user(
        email="pending-record-doctor@example.test", password="DemoCare2026!", name="Pending Doctor",
        role=User.Role.DOCTOR, is_verified=False, email_verified=True,
    )
    appointment = Appointment.objects.create(
        patient=patient, doctor=unverified, symptom_description="Fictional completed visit", address="Demo address",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    report = MedicalReport.objects.create(patient=patient, file="reports/private.pdf", original_filename="private.pdf")
    prescription = Prescription.objects.create(
        appointment=appointment, doctor=unverified, file="prescriptions/private.pdf", original_filename="private.pdf",
    )
    api = APIClient()
    api.force_authenticate(user=unverified)

    assert api.get(reverse("api:report_download", args=[report.pk])).status_code == 403
    assert api.get(reverse("api:prescription_download", args=[prescription.pk])).status_code == 403
    assert api.get(reverse("api:consultation", args=[appointment.pk])).status_code == 403


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_api_registration_is_patient_only_and_email_otp_is_required_for_login():
    client = APIClient()
    response = client.post(reverse("api:register"), {
        "email": "new-patient@example.test",
        "name": "New Patient",
        "phone": "555-0100",
        "password": "StrongPass123!",
        "role": "doctor",
        "specialization": "Cardiologist",
    }, format="json")
    assert response.status_code == 201
    account = User.objects.get(email="new-patient@example.test")
    assert account.role == User.Role.PATIENT
    assert not account.email_verified
    assert "token" not in response.json()

    login = client.post(reverse("api:token"), {"email": account.email, "password": "StrongPass123!"}, format="json")
    assert login.status_code == 403
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    verified = client.post(reverse("api:verify_email"), {"email": account.email, "code": code}, format="json")
    assert verified.status_code == 200
    login = client.post(reverse("api:token"), {"email": account.email, "password": "StrongPass123!"}, format="json")
    assert login.status_code == 200
    assert login.json()["account"]["role"] == User.Role.PATIENT
    assert login.json()["token"]


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_api_registration_accepts_patient_details_and_rejects_invalid_choices():
    client = APIClient()
    invalid = client.post(reverse("api:register"), {
        "email": "invalid-details@example.test", "name": "Invalid Details",
        "password": "StrongPass123!", "gender": "doctor", "blood_group": "X+",
    }, format="json")
    assert invalid.status_code == 400
    assert "gender" in invalid.json() and "blood_group" in invalid.json()

    response = client.post(reverse("api:register"), {
        "email": "complete-patient@example.test", "name": "Complete Patient",
        "password": "StrongPass123!", "phone": "555-0102", "age": 36,
        "gender": "prefer_not_to_say", "blood_group": "O+",
        "role": "doctor", "specialization": "Cardiologist",
    }, format="json")
    assert response.status_code == 201
    patient = User.objects.get(email="complete-patient@example.test")
    assert (patient.age, patient.gender, patient.blood_group, patient.role) == (36, "prefer_not_to_say", "O+", User.Role.PATIENT)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_api_registration_accepts_valid_profile_picture_and_rejects_unsupported_extension(tmp_path):
    from io import BytesIO
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile

    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="teal").save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    api = APIClient()
    with override_settings(MEDIA_ROOT=tmp_path):
        invalid = api.post(reverse("api:register"), {
            "email": "bad-image@example.test", "name": "Bad Image",
            "password": "StrongPass123!", "profile_picture": SimpleUploadedFile("picture.svg", image_bytes, content_type="image/svg+xml"),
        }, format="multipart")
        assert invalid.status_code == 400
        valid = api.post(reverse("api:register"), {
            "email": "image-patient@example.test", "name": "Image Patient",
            "password": "StrongPass123!", "profile_picture": SimpleUploadedFile("portrait.png", image_bytes, content_type="image/png"),
        }, format="multipart")
        assert valid.status_code == 201
        patient = User.objects.get(email="image-patient@example.test")
        assert patient.profile_picture.name.startswith("profiles/")


@pytest.mark.django_db
def test_patient_api_appointments_are_scoped_and_doctor_endpoint_is_role_limited(client, patient, other_patient, doctor):
    own = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Own visit", address="1 Test Street",
        scheduled_at=timezone.now() + timedelta(days=3), status=Appointment.Status.ACCEPTED,
    )
    hidden = Appointment.objects.create(
        patient=other_patient, doctor=doctor, symptom_description="Private other visit", address="2 Test Street",
        scheduled_at=timezone.now() + timedelta(days=4), status=Appointment.Status.ACCEPTED,
    )
    api = APIClient()
    api.force_authenticate(user=patient)
    listing = api.get(reverse("api:appointments"))
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [own.pk]
    assert api.get(reverse("api:appointment_detail", args=[hidden.pk])).status_code == 404
    assert api.get(reverse("api:doctor_appointments")).status_code == 403


@pytest.mark.django_db
def test_api_booking_uses_real_available_slots_and_creates_doctor_notification(patient, doctor):
    from notifications.models import Notification

    visit_date = timezone.localdate() + timedelta(days=1)
    available = available_visit_times(doctor, visit_date)
    assert available
    api = APIClient()
    api.force_authenticate(user=patient)
    response = api.post(reverse("api:appointments"), {
        "doctor": doctor.pk,
        "symptom_description": "A fictional test symptom",
        "address": "10 Demo Road",
        "locality": "Sample Area",
        "city": "Demo City",
        "contact_phone": "555-0101",
        "scheduled_at": available[0].isoformat(),
    }, format="json")
    assert response.status_code == 201, response.content
    appointment = Appointment.objects.get(pk=response.json()["id"])
    assert appointment.patient_id == patient.pk
    assert appointment.doctor_id == doctor.pk
    assert appointment.status == Appointment.Status.PENDING
    assert Notification.objects.filter(recipient=doctor, appointment=appointment).exists()


@pytest.mark.django_db
def test_doctor_api_accepts_open_request_and_notifies_patient(patient, doctor):
    from notifications.models import Notification

    visit_date = timezone.localdate() + timedelta(days=1)
    start = available_visit_times(doctor, visit_date)[0]
    appointment = Appointment.objects.create(
        patient=patient, symptom_description="Open request", address="Demo address",
        scheduled_at=start, status=Appointment.Status.PENDING,
    )
    api = APIClient()
    api.force_authenticate(user=doctor)

    response = api.post(reverse("api:appointment_accept", args=[appointment.pk]), {}, format="json")

    assert response.status_code == 200, response.content
    appointment.refresh_from_db()
    assert appointment.doctor_id == doctor.pk
    assert appointment.status == Appointment.Status.ACCEPTED
    assert Notification.objects.filter(recipient=patient, appointment=appointment).exists()


@pytest.mark.django_db
def test_doctor_api_manages_only_own_valid_availability(doctor, other_doctor, patient):
    api = APIClient()
    api.force_authenticate(user=doctor)
    response = api.get(reverse("api:availability_management"))
    assert response.status_code == 200
    assert all(item["id"] in set(doctor.availability_slots.values_list("id", flat=True)) for item in response.json())

    create = api.post(reverse("api:availability_management"), {
        "weekday": 4, "start_time": "09:00", "end_time": "11:00",
    }, format="json")
    assert create.status_code == 201, create.content
    slot_id = create.json()["id"]
    assert AvailabilitySlot.objects.get(pk=slot_id).doctor_id == doctor.pk

    patient_api = APIClient()
    patient_api.force_authenticate(user=patient)
    assert patient_api.get(reverse("api:availability_management")).status_code == 403

    other_api = APIClient()
    other_api.force_authenticate(user=other_doctor)
    assert other_api.delete(reverse("api:availability_slot_detail", args=[slot_id])).status_code == 404
    assert AvailabilitySlot.objects.filter(pk=slot_id).exists()
    assert api.delete(reverse("api:availability_slot_detail", args=[slot_id])).status_code == 204


@pytest.mark.django_db
def test_api_cannot_accept_already_assigned_visit_when_doctor_is_unavailable(patient, doctor):
    from unittest.mock import patch

    visit_date = timezone.localdate() + timedelta(days=1)
    visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Assigned request", address="Home",
        scheduled_at=available_visit_times(doctor, visit_date)[0], status=Appointment.Status.PENDING,
    )
    api = APIClient()
    api.force_authenticate(user=doctor)
    with patch.object(User.objects, "select_for_update") as select_locked:
        select_locked.return_value.filter.return_value.first.return_value = None
        response = api.post(reverse("api:appointment_accept", args=[visit.pk]), {}, format="json")
    assert response.status_code == 409
    visit.refresh_from_db()
    assert visit.status == Appointment.Status.PENDING


@pytest.mark.django_db
def test_api_prevents_removing_availability_used_by_an_upcoming_visit(patient, doctor):
    from datetime import datetime, time
    from appointments.models import AvailabilitySlot

    visit_day = timezone.localdate() + timedelta(days=2)
    slot, _ = AvailabilitySlot.objects.get_or_create(
        doctor=doctor, weekday=visit_day.weekday(), start_time=time(9, 0), end_time=time(17, 0),
    )
    visit_time = timezone.make_aware(datetime.combine(visit_day, time(10, 0)))
    Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Fictional reserved visit", address="Demo home",
        scheduled_at=visit_time, status=Appointment.Status.ACCEPTED,
    )
    api = APIClient()
    api.force_authenticate(user=doctor)

    response = api.delete(reverse("api:availability_slot_detail", args=[slot.pk]))

    assert response.status_code == 409
    assert AvailabilitySlot.objects.filter(pk=slot.pk).exists()


@pytest.mark.django_db
def test_api_password_change_revokes_token_and_new_password_can_sign_in(patient):
    api = APIClient()
    login = api.post(reverse("api:token"), {"email": patient.email, "password": "TestPass123"}, format="json")
    assert login.status_code == 200
    old_token = login.json()["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Token {old_token}")

    changed = api.post(reverse("api:change_password"), {
        "current_password": "TestPass123", "new_password": "NewSecurePass456!",
    }, format="json")

    assert changed.status_code == 200
    assert api.get(reverse("api:profile")).status_code == 401
    new_login = APIClient().post(
        reverse("api:token"), {"email": patient.email, "password": "NewSecurePass456!"}, format="json",
    )
    assert new_login.status_code == 200
    assert new_login.json()["token"] != old_token


@pytest.mark.django_db
def test_api_profile_is_patient_only_and_patient_can_only_reschedule_own_visit(patient, other_patient, doctor):
    slots = available_visit_times(doctor, timezone.localdate() + timedelta(days=1))
    assert len(slots) >= 2
    own = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Own visit", address="Home",
        scheduled_at=slots[0], status=Appointment.Status.ACCEPTED,
    )
    private = Appointment.objects.create(
        patient=other_patient, doctor=doctor, symptom_description="Private visit", address="Home",
        scheduled_at=slots[1] + timedelta(days=1), status=Appointment.Status.ACCEPTED,
    )
    patient_api = APIClient()
    patient_api.force_authenticate(user=patient)
    assert patient_api.get(reverse("api:profile")).status_code == 200
    assert patient_api.post(reverse("api:appointment_cancel", args=[private.pk]), {}, format="json").status_code == 404

    rescheduled = patient_api.post(
        reverse("api:appointment_reschedule", args=[own.pk]),
        {"scheduled_at": slots[1].isoformat()},
        format="json",
    )
    assert rescheduled.status_code == 200, rescheduled.content
    own.refresh_from_db()
    assert own.scheduled_at == slots[1]

    doctor_api = APIClient()
    doctor_api.force_authenticate(user=doctor)
    response = doctor_api.patch(reverse("api:profile"), {"professional_bio": "Doctor managed profile", "is_verified": False}, format="json")
    assert response.status_code == 200
    doctor.refresh_from_db()
    assert doctor.professional_bio == "Doctor managed profile"
    assert doctor.is_verified is True


@pytest.mark.django_db
def test_patient_api_record_upload_and_download_are_private(patient, other_patient):
    from django.core.files.uploadedfile import SimpleUploadedFile

    api = APIClient()
    api.force_authenticate(user=patient)
    upload = api.post(reverse("api:reports"), {
        "file": SimpleUploadedFile("sample.pdf", b"%PDF-1.4 fictional report"),
    }, format="multipart")
    assert upload.status_code == 201, upload.content
    report_id = upload.json()["id"]
    assert api.get(reverse("api:report_download", args=[report_id])).status_code == 200
    assert len(api.get(reverse("api:reports")).json()) == 1

    other_api = APIClient()
    other_api.force_authenticate(user=other_patient)
    assert other_api.get(reverse("api:report_download", args=[report_id])).status_code == 404
    assert other_api.delete(reverse("api:report_detail", args=[report_id])).status_code == 404


@pytest.mark.django_db
def test_doctor_consultation_api_is_assigned_doctor_only_and_patient_read_only(patient, other_patient, doctor, other_doctor):
    visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Completed test visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    doctor_api = APIClient()
    doctor_api.force_authenticate(user=doctor)
    response = doctor_api.post(reverse("api:consultation", args=[visit.pk]), {
        "summary": "Fictional follow-up summary", "diagnosis": "Sample diagnosis",
    }, format="json")
    assert response.status_code == 200, response.content

    patient_api = APIClient()
    patient_api.force_authenticate(user=patient)
    read = patient_api.get(reverse("api:consultation", args=[visit.pk]))
    assert read.status_code == 200
    assert read.json()["summary"] == "Fictional follow-up summary"
    assert patient_api.post(reverse("api:consultation", args=[visit.pk]), {"summary": "No write"}, format="json").status_code == 403

    other_patient_api = APIClient()
    other_patient_api.force_authenticate(user=other_patient)
    assert other_patient_api.get(reverse("api:consultation", args=[visit.pk])).status_code == 404
    other_doctor_api = APIClient()
    other_doctor_api.force_authenticate(user=other_doctor)
    assert other_doctor_api.get(reverse("api:consultation", args=[visit.pk])).status_code == 404


@pytest.mark.django_db
@override_settings(SUPPORT_EMAIL="")
def test_api_service_enquiry_persists_in_staff_queue():
    from core.models import ServiceEnquiry

    response = APIClient().post(reverse("api:service_enquiry"), {
        "name": "Demo caller", "email": "caller@example.test", "service": "nursing",
        "message": "Please describe the available home nursing support.",
    }, format="json")
    assert response.status_code == 201
    assert ServiceEnquiry.objects.count() == 1
    assert "enquiry_id" not in response.json()


@pytest.mark.django_db
def test_notification_api_only_returns_the_authenticated_recipients_items(patient, other_patient, doctor):
    from notifications.models import Notification

    visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Visit", address="Home",
        scheduled_at=timezone.now() + timedelta(days=2), status=Appointment.Status.ACCEPTED,
    )
    own = Notification.objects.create(recipient=patient, appointment=visit, message="Your visit update.")
    private = Notification.objects.create(recipient=other_patient, appointment=visit, message="Private notification.")
    api = APIClient()
    api.force_authenticate(user=patient)

    response = api.get(reverse("api:notifications"))
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.pk]
    assert api.patch(reverse("api:notification_detail", args=[private.pk]), {}, format="json").status_code == 404
    assert api.patch(reverse("api:notification_detail", args=[own.pk]), {}, format="json").json()["is_read"] is True


@pytest.mark.django_db
def test_patient_review_api_requires_completed_own_visit_and_lists_public_review(patient, other_patient, doctor):
    visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Completed visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    api = APIClient()
    api.force_authenticate(user=patient)
    response = api.post(reverse("api:review", args=[visit.pk]), {"rating": 5, "comment": "Fictional feedback."}, format="json")
    assert response.status_code == 201, response.content
    public = APIClient().get(reverse("api:doctor_reviews", args=[doctor.pk]))
    assert public.status_code == 200
    results = public.json().get("results", public.json())
    assert results[0]["rating"] == "5.0"

    other_api = APIClient()
    other_api.force_authenticate(user=other_patient)
    assert other_api.post(reverse("api:review", args=[visit.pk]), {"rating": 1}, format="json").status_code == 404


@pytest.mark.django_db
def test_doctor_prescription_api_links_protected_download_to_visit_owner(patient, other_patient, doctor, other_doctor):
    from django.core.files.uploadedfile import SimpleUploadedFile

    visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Completed visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    doctor_api = APIClient()
    doctor_api.force_authenticate(user=doctor)
    response = doctor_api.post(reverse("api:prescription_upload", args=[visit.pk]), {
        "file": SimpleUploadedFile("sample-prescription.pdf", b"%PDF-1.4 fictional prescription"),
        "notes": "Fictional notes",
    }, format="multipart")
    assert response.status_code == 201, response.content
    prescription_id = response.json()["id"]

    patient_api = APIClient()
    patient_api.force_authenticate(user=patient)
    assert patient_api.get(reverse("api:prescription_download", args=[prescription_id])).status_code == 200
    assert len(patient_api.get(reverse("api:prescriptions")).json()) == 1
    other_patient_api = APIClient()
    other_patient_api.force_authenticate(user=other_patient)
    assert other_patient_api.get(reverse("api:prescription_download", args=[prescription_id])).status_code == 404
    other_doctor_api = APIClient()
    other_doctor_api.force_authenticate(user=other_doctor)
    assert other_doctor_api.get(reverse("api:prescription_download", args=[prescription_id])).status_code == 404
