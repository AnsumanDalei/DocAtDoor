import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/health/").json()["status"] == "ok"


@pytest.mark.django_db
def test_patient_dashboard_renders(client, patient):
    client.force_login(patient)
    response = client.get(reverse("dashboard:home_dashboard"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'class="mobile-bottom-nav patient-bottom-nav"' in body
    assert "Find care" in body and "Visits" in body and "Records" in body and "Inbox" in body
    assert "doctor-bottom-nav" not in body


@pytest.mark.django_db
def test_patient_dashboard_document_and_notification_previews_are_scoped(client, patient, other_patient, doctor):
    from datetime import timedelta
    from django.utils import timezone
    from appointments.models import Appointment
    from medical_records.models import MedicalReport, Prescription
    from notifications.models import Notification

    own_visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Demo visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    other_visit = Appointment.objects.create(
        patient=other_patient, doctor=doctor, symptom_description="Private visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.COMPLETED,
    )
    own_report = MedicalReport.objects.create(patient=patient, file="reports/own.pdf", original_filename="own.pdf")
    MedicalReport.objects.create(patient=other_patient, file="reports/other.pdf", original_filename="other.pdf")
    own_rx = Prescription.objects.create(appointment=own_visit, doctor=doctor, file="prescriptions/own.pdf", original_filename="own-rx.pdf")
    Prescription.objects.create(appointment=other_visit, doctor=doctor, file="prescriptions/other.pdf", original_filename="other-rx.pdf")
    own_notice = Notification.objects.create(recipient=patient, appointment=own_visit, message="Your visit is complete.")
    Notification.objects.create(recipient=other_patient, appointment=other_visit, message="Other patient's private update.")

    client.force_login(patient)
    response = client.get(reverse("dashboard:home_dashboard"))
    assert response.status_code == 200
    assert list(response.context["recent_reports"]) == [own_report]
    assert list(response.context["recent_prescriptions"]) == [own_rx]
    assert list(response.context["recent_notifications"]) == [own_notice]


@pytest.mark.django_db
def test_dashboard_upcoming_count_excludes_past_active_visits(client, patient):
    from datetime import timedelta
    from django.utils import timezone
    from appointments.models import Appointment

    Appointment.objects.create(
        patient=patient, symptom_description="Past pending visit", address="Home",
        scheduled_at=timezone.now() - timedelta(days=1), status=Appointment.Status.PENDING,
    )
    Appointment.objects.create(
        patient=patient, symptom_description="Future accepted visit", address="Home",
        scheduled_at=timezone.now() + timedelta(days=1), status=Appointment.Status.ACCEPTED,
    )
    client.force_login(patient)
    response = client.get(reverse("dashboard:home_dashboard"))
    assert response.context["stats"]["upcoming"] == 1
    assert response.context["upcoming_appointment"].symptom_description == "Future accepted visit"


@pytest.mark.django_db
def test_doctor_dashboard_renders(client, doctor):
    client.force_login(doctor)
    response = client.get(reverse("appointments:doctor_dashboard"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'class="mobile-bottom-nav doctor-bottom-nav"' in body
    assert "Hours" in body and "Visits" in body and "Reviews" in body and "Inbox" in body
    assert "patient-bottom-nav" not in body


@pytest.mark.django_db
def test_doctor_dashboard_schedule_metrics_and_requests_are_scoped(client, doctor, other_doctor, patient, other_patient):
    from datetime import datetime, time, timedelta
    from django.utils import timezone
    from appointments.models import Appointment

    now = timezone.now()
    local_today_visit = timezone.make_aware(datetime.combine(timezone.localdate(), time(10)))
    today_visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Today's completed visit", address="Home",
        scheduled_at=local_today_visit,
        status=Appointment.Status.COMPLETED,
    )
    upcoming_visit = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Confirmed future visit", address="Home",
        scheduled_at=now + timedelta(days=2), status=Appointment.Status.ACCEPTED,
    )
    assigned_request = Appointment.objects.create(
        patient=patient, doctor=doctor, symptom_description="Assigned request", address="Home",
        scheduled_at=now + timedelta(days=3), status=Appointment.Status.PENDING,
    )
    open_request = Appointment.objects.create(
        patient=patient, symptom_description="Open request", address="Home",
        scheduled_at=now + timedelta(days=4), status=Appointment.Status.PENDING,
    )
    stale_request = Appointment.objects.create(
        patient=patient, symptom_description="Past request", address="Home",
        scheduled_at=now - timedelta(days=1), status=Appointment.Status.PENDING,
    )
    other_doctor_request = Appointment.objects.create(
        patient=other_patient, doctor=other_doctor, symptom_description="Another doctor's request", address="Home",
        scheduled_at=now + timedelta(days=1), status=Appointment.Status.PENDING,
    )

    client.force_login(doctor)
    response = client.get(reverse("appointments:doctor_dashboard"))

    assert response.status_code == 200
    assert response.context["today_count"] == 1
    assert response.context["pending_count"] == 2
    assert response.context["upcoming_count"] == 1
    assert response.context["completed_count"] == 1
    assert {visit.pk for visit in response.context["open_requests"]} == {assigned_request.pk, open_request.pk}
    assert [visit.pk for visit in response.context["upcoming_visits"]] == [upcoming_visit.pk]
    body = response.content.decode()
    assert "Today&#x27;s completed visit" in body or "Today's completed visit" in body
    assert "Another doctor's request" not in body
    assert stale_request.symptom_description not in body
    assert other_doctor_request.symptom_description not in body


@pytest.mark.django_db
def test_admin_dashboard_renders_for_staff_only(client, patient, django_user_model):
    client.force_login(patient)
    resp = client.get(reverse("dashboard:admin_dashboard"))
    assert resp.status_code == 302  # not staff, bounced to home

    staff = django_user_model.objects.create_user(
        email="staffadmin@example.com", password="TestPass123", name="Staff Admin",
        role="admin", is_staff=True, is_verified=True, email_verified=True,
    )
    client.force_login(staff)
    resp = client.get(reverse("dashboard:admin_dashboard"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_dashboard_shows_service_enquiry_follow_up(client, django_user_model):
    from core.models import ServiceEnquiry

    staff = django_user_model.objects.create_user(
        email="staff-enquiry@example.com", password="TestPass123", name="Staff Admin",
        role="admin", is_staff=True, is_verified=True, email_verified=True,
    )
    enquiry = ServiceEnquiry.objects.create(
        name="Sample Patient", email="patient@example.test", service="nursing", message="Seeking information."
    )
    client.force_login(staff)
    response = client.get(reverse("dashboard:admin_dashboard"))
    assert response.status_code == 200
    assert response.context["new_enquiries"] == 1
    assert enquiry.get_service_display() in response.content.decode()
    assert "Review service enquiries" in response.content.decode()


@pytest.mark.django_db
def test_reports_page_renders_for_patient(client, patient):
    client.force_login(patient)
    assert client.get(reverse("records:reports")).status_code == 200


@pytest.mark.django_db
def test_register_and_forgot_password_forms_render(client):
    assert client.get(reverse("accounts:register")).status_code == 200
    assert client.get(reverse("accounts:forgot")).status_code == 200


@pytest.mark.django_db
def test_login_page_uses_the_new_template(client):
    resp = client.get(reverse("accounts:login"))
    assert resp.status_code == 200
    assert "login.html" in [t.name for t in resp.templates]
    assert "WELCOME BACK" in resp.content.decode()
