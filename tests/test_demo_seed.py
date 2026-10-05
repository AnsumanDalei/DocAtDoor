import pytest
from django.core.management import call_command
from django.test import override_settings
from accounts.models import User
from appointments.models import Appointment
from medical_records.models import Consultation
from reviews.models import Review


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_demo_seed_is_repeatable_and_creates_a_walkthrough():
    call_command("seed_demo_data")
    call_command("seed_demo_data")
    patient = User.objects.get(email="patient@demo.example.test")
    doctor = User.objects.get(email="doctor1@demo.example.test")
    appointments = Appointment.objects.filter(patient=patient, doctor=doctor)
    assert appointments.filter(status=Appointment.Status.COMPLETED).count() == 1
    assert appointments.filter(status=Appointment.Status.ACCEPTED).count() == 1
    assert Consultation.objects.filter(appointment__in=appointments).count() == 1
    assert Review.objects.filter(appointment__in=appointments).count() == 1
