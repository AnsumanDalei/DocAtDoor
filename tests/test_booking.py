from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from notifications.models import Notification


def _future_dt(days=2):
    """A stable in-hours test slot, independent of the wall-clock test start."""
    visit_date = timezone.localdate() + timedelta(days=days)
    return timezone.make_aware(datetime.combine(visit_date, time(10, 0)))


def _future(days=2):
    return _future_dt(days).strftime("%Y-%m-%dT%H:%M")


@pytest.mark.django_db
def test_authenticated_doctor_is_not_prompted_to_sign_in_to_book(client, doctor):
    client.force_login(doctor)
    response = client.get(reverse("appointments:doctors"))
    assert response.status_code == 200
    assert b"Patient account required" in response.content
    assert b"Sign in to request" not in response.content


@pytest.mark.django_db
def test_patient_can_book_specific_doctor(client, patient, doctor):
    client.force_login(patient)
    resp = client.post(reverse("appointments:book"), {
        "doctor": doctor.id, "symptom_description": "Fever", "address": "Home",
        "locality": "West End", "city": "Demo City", "contact_phone": "+919999999999",
        "scheduled_at": _future(),
    })
    assert resp.status_code == 302
    appointment = Appointment.objects.get(patient=patient)
    assert appointment.doctor == doctor
    assert appointment.status == "Pending"
    assert appointment.locality == "West End"
    assert appointment.city == "Demo City"
    assert appointment.contact_phone == "+919999999999"
    assert Notification.objects.filter(recipient=doctor, appointment=appointment).exists()


@pytest.mark.django_db
def test_open_request_notifies_every_verified_available_doctor(client, patient, doctor, other_doctor):
    client.force_login(patient)
    resp = client.post(reverse("appointments:book"), {
        "symptom_description": "Cold", "address": "Home", "locality": "West End",
        "city": "Demo City", "contact_phone": "+919999999999", "scheduled_at": _future(),
    })
    assert resp.status_code == 302
    appointment = Appointment.objects.get(patient=patient)
    assert appointment.doctor is None
    notified = set(Notification.objects.filter(appointment=appointment).values_list("recipient_id", flat=True))
    assert notified == {doctor.id, other_doctor.id}


@pytest.mark.django_db
def test_booking_rejects_a_non_doctor_id(client, patient, other_patient):
    """The doctor field must only accept real, verified doctors — not any
    User pk supplied by the client."""
    client.force_login(patient)
    resp = client.post(reverse("appointments:book"), {
        "doctor": other_patient.id, "symptom_description": "Fever", "address": "Home",
        "city": "Demo City", "contact_phone": "+919999999999",
        "scheduled_at": _future(),
    })
    assert resp.status_code == 302
    assert Appointment.objects.count() == 0


@pytest.mark.django_db
def test_double_booking_same_doctor_same_slot_is_rejected(client, patient, other_patient, doctor):
    when = _future_dt(days=2)
    Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                address="Home", scheduled_at=when, status="Accepted")
    client.force_login(other_patient)
    resp = client.post(reverse("appointments:book"), {
        "doctor": doctor.id, "symptom_description": "Cold", "address": "Home",
        "city": "Demo City", "contact_phone": "+919999999999",
        "scheduled_at": when.strftime("%Y-%m-%dT%H:%M"),
    })
    assert resp.status_code == 302
    assert Appointment.objects.filter(doctor=doctor).count() == 1


@pytest.mark.django_db
def test_patient_can_cancel_own_pending_appointment(client, patient):
    appointment = Appointment.objects.create(patient=patient, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    client.force_login(patient)
    client.post(reverse("appointments:cancel", args=[appointment.id]))
    appointment.refresh_from_db()
    assert appointment.status == "Cancelled"


@pytest.mark.django_db
def test_patient_cannot_cancel_another_patients_appointment(client, patient, other_patient):
    appointment = Appointment.objects.create(patient=patient, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    client.force_login(other_patient)
    resp = client.post(reverse("appointments:cancel", args=[appointment.id]))
    assert resp.status_code == 404
    appointment.refresh_from_db()
    assert appointment.status == "Pending"


@pytest.mark.django_db
def test_patient_can_reschedule_pending_appointment(client, patient, doctor):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    client.force_login(patient)
    new_time = _future(days=5)
    resp = client.post(reverse("appointments:reschedule", args=[appointment.id]), {
        "doctor": doctor.id, "symptom_description": appointment.symptom_description,
        "address": appointment.address, "scheduled_at": new_time,
    })
    assert resp.status_code == 302
    appointment.refresh_from_db()
    assert timezone.localtime(appointment.scheduled_at).strftime("%Y-%m-%dT%H:%M") == new_time
    assert appointment.status == "Pending"


@pytest.mark.django_db
def test_completed_appointment_cannot_be_rescheduled(client, patient, doctor):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                              status="Completed")
    client.force_login(patient)
    resp = client.post(reverse("appointments:reschedule", args=[appointment.id]), {
        "doctor": doctor.id, "symptom_description": "Fever", "address": "Home",
        "scheduled_at": _future(days=5),
    })
    assert resp.status_code == 302
    appointment.refresh_from_db()
    assert appointment.status == "Completed"


@pytest.mark.django_db
def test_doctor_can_accept_open_request(client, doctor, patient):
    appointment = Appointment.objects.create(patient=patient, symptom_description="Fever",
                                              address="Home", scheduled_at=_future_dt(days=1))
    client.force_login(doctor)
    client.post(reverse("appointments:accept", args=[appointment.id]))
    appointment.refresh_from_db()
    assert appointment.status == "Accepted"
    assert appointment.doctor == doctor


@pytest.mark.django_db
def test_accepting_a_conflicting_slot_is_rejected(client, doctor, patient, other_patient):
    when = _future_dt(days=2)
    Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                address="Home", scheduled_at=when, status="Accepted")
    conflicting = Appointment.objects.create(patient=other_patient, symptom_description="Cold",
                                              address="Home", scheduled_at=when, status="Pending")
    client.force_login(doctor)
    client.post(reverse("appointments:accept", args=[conflicting.id]))
    conflicting.refresh_from_db()
    assert conflicting.status == "Pending"
    assert conflicting.doctor is None


@pytest.mark.django_db
def test_doctor_can_complete_accepted_appointment(client, doctor, patient):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                              status="Accepted")
    client.force_login(doctor)
    client.post(reverse("appointments:complete", args=[appointment.id]))
    appointment.refresh_from_db()
    assert appointment.status == "Completed"


@pytest.mark.django_db
def test_doctor_can_reject_own_open_request(client, doctor, patient):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    client.force_login(doctor)
    client.post(reverse("appointments:reject", args=[appointment.id]))
    appointment.refresh_from_db()
    assert appointment.status == "Rejected"
    assert Notification.objects.filter(recipient=patient, appointment=appointment).exists()


@pytest.mark.django_db
def test_doctor_cannot_reject_a_request_assigned_to_another_doctor(client, doctor, other_doctor, patient):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                              address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    client.force_login(other_doctor)
    client.post(reverse("appointments:reject", args=[appointment.id]))
    appointment.refresh_from_db()
    assert appointment.status == "Pending"
    assert appointment.doctor == doctor


@pytest.mark.django_db
def test_doctor_search_hides_unverified_and_filters_by_specialization(client, patient, doctor, other_doctor):
    unverified = doctor
    unverified.is_verified = False
    unverified.save()
    client.force_login(patient)
    resp = client.get(reverse("appointments:doctors"))
    listed = {d.id for d in resp.context["doctors"]}
    assert unverified.id not in listed
    assert other_doctor.id in listed

    resp = client.get(reverse("appointments:doctors"), {"specialization": other_doctor.specialization})
    listed = {d.id for d in resp.context["doctors"]}
    assert listed == {other_doctor.id}


@pytest.mark.django_db
def test_doctor_search_filters_by_service_area_experience_and_fee(client, doctor, other_doctor):
    from django.urls import reverse

    doctor.service_area = "Downtown Demo City"
    doctor.experience_years = 6
    doctor.consultation_fee = 400
    doctor.save()
    other_doctor.service_area = "Uptown Demo City"
    other_doctor.experience_years = 12
    other_doctor.consultation_fee = 800
    other_doctor.save()

    response = client.get(reverse("appointments:doctors"), {
        "area": "Downtown", "min_experience": "5", "max_fee": "500", "availability": "all",
    })
    assert response.status_code == 200
    assert [d.id for d in response.context["doctors"]] == [doctor.id]
    assert "Downtown" in response.content.decode()


@pytest.mark.django_db
def test_doctor_directory_ignores_invalid_numeric_filters(client, doctor):
    from django.urls import reverse

    response = client.get(reverse("appointments:doctors"), {
        "min_experience": "lots", "max_fee": "cheap", "availability": "all",
    })
    assert response.status_code == 200
    assert doctor.id in {d.id for d in response.context["doctors"]}


@pytest.mark.django_db
def test_service_area_is_editable_only_in_doctor_profile_and_public_profile(client, patient, doctor):
    from accounts.forms import ProfileForm
    from django.urls import reverse

    assert "service_area" in ProfileForm(instance=doctor).fields
    assert "professional_bio" in ProfileForm(instance=doctor).fields
    from django import forms
    assert isinstance(ProfileForm(instance=doctor).fields["professional_bio"].widget, forms.Textarea)
    assert "service_area" not in ProfileForm(instance=patient).fields
    assert "professional_bio" not in ProfileForm(instance=patient).fields
    doctor.service_area = "Demo City"
    doctor.professional_bio = "A clear, patient-first introduction."
    doctor.save()
    response = client.get(reverse("appointments:doctor_profile", args=[doctor.id]))
    assert response.status_code == 200
    assert "Home visits in Demo City" in response.content.decode()
    body = response.content.decode()
    assert 'id="experience"' in body and "Practice experience" in body
    assert 'id="education"' in body and "Qualifications" in body
    assert "Care available through DocAtDoor" in body
    assert "A clear, patient-first introduction." in body
    assert 'href="/appointments/doctors/?q=' in body


@pytest.mark.django_db
def test_doctor_profile_escapes_the_public_bio(client, doctor):
    from django.urls import reverse

    doctor.professional_bio = "<script>alert(1)</script>"
    doctor.save(update_fields=["professional_bio"])
    response = client.get(reverse("appointments:doctor_profile", args=[doctor.id]))
    body = response.content.decode()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<script>alert(1)</script>" not in body


@pytest.mark.django_db
def test_patient_booking_form_includes_a_final_review_step(client, patient, doctor):
    client.force_login(patient)
    response = client.get(reverse("appointments:doctors"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'class="booking-progress"' in body
    assert "Review your visit request" in body
    assert "Confirm visit request" in body
    assert 'data-doctor-name="Dr.' in body
