from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from medical_records.models import Consultation, MedicalReport, Prescription


@pytest.mark.django_db
def test_verified_doctor_directory_is_available_to_a_doctor_account(client, doctor):
    client.force_login(doctor)
    resp = client.get(reverse("appointments:doctors"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_doctor_only_view_blocks_patient(client, patient):
    client.force_login(patient)
    resp = client.get(reverse("appointments:doctor_dashboard"))
    assert resp.status_code == 302
    assert resp.url == reverse("dashboard:home_dashboard")


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login(client):
    resp = client.get(reverse("dashboard:home_dashboard"))
    assert resp.status_code == 302
    assert reverse("accounts:login") in resp.url


@pytest.mark.django_db
def test_medical_reports_page_is_patient_only(client, doctor):
    client.force_login(doctor)
    resp = client.get(reverse("records:reports"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_doctor_cannot_upload_a_patient_report(client, doctor):
    client.force_login(doctor)
    resp = client.post(reverse("records:upload_report"), {
        "file": SimpleUploadedFile("report.pdf", b"%PDF-1.4 fake report"),
    })
    assert resp.status_code == 403
    assert MedicalReport.objects.count() == 0


@pytest.fixture
def report(patient):
    return MedicalReport.objects.create(
        patient=patient, file=SimpleUploadedFile("blood_test.pdf", b"%PDF-1.4 fake report"),
        original_filename="blood_test.pdf",
    )


@pytest.mark.django_db
def test_report_owner_can_download_their_own_report(client, patient, report):
    client.force_login(patient)
    resp = client.get(reverse("records:download_report", args=[report.id]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_report_is_stored_outside_the_public_media_root(report):
    """Reports must never be reachable through the public /media/ URL — only
    through the authenticated download view."""
    from django.conf import settings
    from medical_records.storage import protected_storage
    file_path = report.file.path
    assert str(settings.MEDIA_ROOT) not in file_path
    assert str(protected_storage.location) in file_path


@pytest.mark.django_db
def test_related_doctor_can_download_a_patients_report(client, patient, doctor, report):
    Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                status=Appointment.Status.ACCEPTED)
    client.force_login(doctor)
    resp = client.get(reverse("records:download_report", args=[report.id]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_doctor_without_an_active_appointment_cannot_download_a_report(client, patient, doctor, report):
    Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                status=Appointment.Status.CANCELLED)
    client.force_login(doctor)
    resp = client.get(reverse("records:download_report", args=[report.id]))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unrelated_doctor_cannot_download_a_patients_report(client, other_doctor, report):
    client.force_login(other_doctor)
    resp = client.get(reverse("records:download_report", args=[report.id]))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unrelated_patient_cannot_download_someone_elses_report(client, other_patient, report):
    client.force_login(other_patient)
    resp = client.get(reverse("records:download_report", args=[report.id]))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_patient_can_delete_own_report_but_not_someone_elses(client, patient, other_patient, report):
    client.force_login(other_patient)
    resp = client.post(reverse("records:delete_report", args=[report.id]))
    assert resp.status_code == 404
    assert MedicalReport.objects.filter(pk=report.id).exists()

    client.force_login(patient)
    client.post(reverse("records:delete_report", args=[report.id]))
    assert not MedicalReport.objects.filter(pk=report.id).exists()


@pytest.fixture
def completed_appointment(patient, doctor):
    return Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                       address="Home", scheduled_at=timezone.now() + timedelta(days=1),
                                       status="Completed")


@pytest.mark.django_db
def test_doctor_can_upload_prescription_only_for_own_completed_appointment(client, doctor, completed_appointment):
    client.force_login(doctor)
    resp = client.post(reverse("records:prescription", args=[completed_appointment.id]), {
        "file": SimpleUploadedFile("rx.pdf", b"%PDF-1.4 fake prescription"), "notes": "Take rest",
    })
    assert resp.status_code == 302
    assert Prescription.objects.filter(appointment=completed_appointment).exists()


@pytest.mark.django_db
def test_doctor_cannot_upload_prescription_for_someone_elses_appointment(client, other_doctor, completed_appointment):
    client.force_login(other_doctor)
    resp = client.post(reverse("records:prescription", args=[completed_appointment.id]), {
        "file": SimpleUploadedFile("rx.pdf", b"%PDF-1.4 fake prescription"),
    })
    assert resp.status_code == 404
    assert not Prescription.objects.filter(appointment=completed_appointment).exists()


@pytest.mark.django_db
def test_prescription_download_allowed_for_patient_and_doctor_only(client, patient, doctor, other_patient, completed_appointment):
    prescription = Prescription.objects.create(
        appointment=completed_appointment, doctor=doctor,
        file=SimpleUploadedFile("rx.pdf", b"%PDF-1.4 fake prescription"), original_filename="rx.pdf",
    )
    client.force_login(patient)
    assert client.get(reverse("records:download_prescription", args=[completed_appointment.id])).status_code == 200
    client.force_login(doctor)
    assert client.get(reverse("records:download_prescription", args=[completed_appointment.id])).status_code == 200
    client.force_login(other_patient)
    assert client.get(reverse("records:download_prescription", args=[completed_appointment.id])).status_code == 403


@pytest.mark.django_db
def test_assigned_doctor_can_write_consultation_and_patient_is_notified(client, doctor, patient, completed_appointment):
    client.force_login(doctor)
    response = client.post(reverse("records:consultation", args=[completed_appointment.id]), {
        "summary": "Patient was examined at home.",
        "diagnosis": "Seasonal allergy",
    })
    assert response.status_code == 302
    record = Consultation.objects.get(appointment=completed_appointment)
    assert record.doctor == doctor
    assert record.summary == "Patient was examined at home."
    assert patient.notifications.filter(appointment=completed_appointment).exists()


@pytest.mark.django_db
def test_patient_can_read_only_their_own_completed_consultation(client, patient, other_patient, doctor, completed_appointment):
    Consultation.objects.create(
        appointment=completed_appointment,
        doctor=doctor,
        summary="Visit summary for this patient.",
        diagnosis="Seasonal allergy",
    )
    client.force_login(patient)
    response = client.get(reverse("records:consultation", args=[completed_appointment.id]))
    assert response.status_code == 200
    assert b"Seasonal allergy" in response.content

    client.force_login(other_patient)
    assert client.get(reverse("records:consultation", args=[completed_appointment.id])).status_code == 403


@pytest.mark.django_db
def test_other_doctor_cannot_read_a_completed_consultation(client, other_doctor, doctor, patient, completed_appointment):
    Consultation.objects.create(
        appointment=completed_appointment,
        doctor=doctor,
        summary="Private visit summary.",
    )
    client.force_login(other_doctor)
    assert client.get(reverse("records:consultation", args=[completed_appointment.id])).status_code == 403

@pytest.mark.django_db
def test_prescription_list_is_patient_scoped(client, patient, other_patient, doctor, completed_appointment):
    Prescription.objects.create(
        appointment=completed_appointment,
        doctor=doctor,
        file="prescriptions/private-sample.pdf",
        original_filename="private-sample.pdf",
    )
    client.force_login(patient)
    response = client.get(reverse("records:prescriptions"))
    assert response.status_code == 200
    assert "private-sample.pdf" in response.content.decode()

    client.force_login(other_patient)
    response = client.get(reverse("records:prescriptions"))
    assert response.status_code == 200
    assert "private-sample.pdf" not in response.content.decode()

    client.force_login(doctor)
    assert client.get(reverse("records:prescriptions")).status_code == 403
