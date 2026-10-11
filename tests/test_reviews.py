from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from reviews.models import Review


def _appointment(patient, doctor, status):
    return Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                       address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                       status=status)


@pytest.mark.django_db
def test_review_can_only_be_left_after_appointment_is_completed(client, patient, doctor):
    appointment = _appointment(patient, doctor, "Accepted")
    client.force_login(patient)
    resp = client.post(reverse("reviews:create", args=[appointment.id]), {"rating": 5, "comment": "Great"})
    assert resp.status_code == 404
    assert not Review.objects.filter(appointment=appointment).exists()


@pytest.mark.django_db
def test_patient_can_review_a_completed_appointment(client, patient, doctor):
    appointment = _appointment(patient, doctor, "Completed")
    client.force_login(patient)
    resp = client.post(reverse("reviews:create", args=[appointment.id]), {"rating": 5, "comment": "Great doctor"})
    assert resp.status_code == 302
    review = Review.objects.get(appointment=appointment)
    assert review.rating == 5
    assert review.doctor == doctor
    assert review.patient == patient


@pytest.mark.django_db
def test_review_updates_the_doctors_average_rating(client, patient, other_patient, doctor):
    first = _appointment(patient, doctor, "Completed")
    second = _appointment(other_patient, doctor, "Completed")

    client.force_login(patient)
    client.post(reverse("reviews:create", args=[first.id]), {"rating": 5, "comment": "Great"})
    client.force_login(other_patient)
    client.post(reverse("reviews:create", args=[second.id]), {"rating": 3, "comment": "Okay"})

    doctor.refresh_from_db()
    assert doctor.rating == pytest.approx(4.0)


@pytest.mark.django_db
def test_only_the_reviewing_patient_can_review_that_appointment(client, patient, other_patient, doctor):
    appointment = _appointment(patient, doctor, "Completed")
    client.force_login(other_patient)
    resp = client.post(reverse("reviews:create", args=[appointment.id]), {"rating": 1, "comment": "Not mine"})
    assert resp.status_code == 404
    assert not Review.objects.filter(appointment=appointment).exists()


@pytest.mark.django_db
def test_doctor_reviews_page_shows_only_that_doctors_reviews(client, patient, doctor, other_doctor):
    appointment = _appointment(patient, doctor, "Completed")
    Review.objects.create(appointment=appointment, patient=patient, doctor=doctor, rating=5, comment="Nice")

    client.force_login(doctor)
    resp = client.get(reverse("reviews:doctor_reviews"))
    assert list(resp.context["reviews"]) == [appointment.review]

    client.force_login(other_doctor)
    resp = client.get(reverse("reviews:doctor_reviews"))
    assert list(resp.context["reviews"]) == []
