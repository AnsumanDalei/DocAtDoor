from datetime import datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, AvailabilitySlot
from appointments.scheduling import available_visit_times


@pytest.mark.django_db
def test_slot_api_returns_only_open_times_for_a_doctor(client, patient, doctor):
    visit_date = timezone.localdate() + timedelta(days=2)
    AvailabilitySlot.objects.filter(doctor=doctor, weekday=visit_date.weekday()).delete()
    AvailabilitySlot.objects.create(
        doctor=doctor,
        weekday=visit_date.weekday(),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    busy_at = timezone.make_aware(datetime.combine(visit_date, time(9, 0)))
    Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        symptom_description="Existing visit",
        address="Home",
        scheduled_at=busy_at,
        status=Appointment.Status.ACCEPTED,
    )

    response = client.get(
        reverse("appointments:available_slots", args=[doctor.id]),
        {"date": visit_date.isoformat()},
    )

    assert response.status_code == 200
    assert response.json()["slots"] == [
        {"value": f"{visit_date.isoformat()}T10:00", "label": "10:00 AM"},
        {"value": f"{visit_date.isoformat()}T11:00", "label": "11:00 AM"},
    ]


@pytest.mark.django_db
def test_slot_api_rejects_dates_outside_the_booking_horizon(client, doctor):
    visit_date = timezone.localdate() + timedelta(days=31)
    response = client.get(
        reverse("appointments:available_slots", args=[doctor.id]),
        {"date": visit_date.isoformat()},
    )
    assert response.status_code == 400
    assert response.json()["slots"] == []


@pytest.mark.django_db
def test_booking_rejects_a_time_outside_doctor_availability(client, patient, doctor):
    visit_date = timezone.localdate() + timedelta(days=2)
    AvailabilitySlot.objects.filter(doctor=doctor, weekday=visit_date.weekday()).delete()
    AvailabilitySlot.objects.create(
        doctor=doctor,
        weekday=visit_date.weekday(),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    client.force_login(patient)

    response = client.post(reverse("appointments:book"), {
        "doctor": doctor.id,
        "symptom_description": "Fever",
        "address": "Home",
        "city": "Demo City",
        "contact_phone": "+919999999999",
        "scheduled_at": f"{visit_date.isoformat()}T11:00",
    })

    assert response.status_code == 302
    assert Appointment.objects.filter(patient=patient).count() == 0


@pytest.mark.django_db
def test_booking_rejects_a_time_that_is_not_an_available_hourly_start(client, patient, doctor):
    visit_date = timezone.localdate() + timedelta(days=2)
    client.force_login(patient)
    response = client.post(reverse("appointments:book"), {
        "doctor": doctor.id,
        "symptom_description": "Fever",
        "address": "Home",
        "city": "Demo City",
        "contact_phone": "+919999999999",
        "scheduled_at": f"{visit_date.isoformat()}T10:30",
    })
    assert response.status_code == 302
    assert Appointment.objects.filter(patient=patient).count() == 0


@pytest.mark.django_db
def test_doctor_cannot_remove_weekly_hours_used_by_an_active_visit(client, patient, doctor):
    visit_date = timezone.localdate() + timedelta(days=2)
    slot = AvailabilitySlot.objects.create(
        doctor=doctor,
        weekday=visit_date.weekday(),
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        symptom_description="Existing visit",
        address="Home",
        scheduled_at=timezone.make_aware(datetime.combine(visit_date, time(10, 0))),
        status=Appointment.Status.ACCEPTED,
    )
    client.force_login(doctor)
    response = client.post(reverse("appointments:remove_slot", args=[slot.id]))
    assert response.status_code == 302
    assert AvailabilitySlot.objects.filter(pk=slot.pk).exists()


@pytest.mark.django_db
def test_doctor_cannot_remove_another_doctors_availability(client, doctor, other_doctor):
    slot = other_doctor.availability_slots.first()
    client.force_login(doctor)
    response = client.post(reverse("appointments:remove_slot", args=[slot.id]))
    assert response.status_code == 404
    assert AvailabilitySlot.objects.filter(pk=slot.pk).exists()
