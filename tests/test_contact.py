import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from core.models import ServiceEnquiry


@pytest.mark.django_db
def test_doctor_directory_can_be_browsed_without_an_account(client, doctor):
    response = client.get(reverse("appointments:doctors"))
    assert response.status_code == 200
    assert doctor.name in response.content.decode()
    assert "Sign in to request" in response.content.decode()


@pytest.mark.django_db
@override_settings(SUPPORT_EMAIL="care@example.test", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_service_enquiry_is_sent_to_configured_support(client):
    response = client.post(reverse("core:contact"), {
        "name": "Sample Patient",
        "email": "patient@example.test",
        "service": "physiotherapy",
        "message": "I would like to ask about recovery support.",
        "website": "",
    })
    assert response.status_code == 200
    assert response.context["submitted"] is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["care@example.test"]
    assert mail.outbox[0].reply_to == ["patient@example.test"]
    assert ServiceEnquiry.objects.count() == 1
    assert ServiceEnquiry.objects.get().status == ServiceEnquiry.Status.NEW


@pytest.mark.django_db
@override_settings(SUPPORT_EMAIL="")
def test_service_enquiry_is_saved_even_without_support_email(client):
    response = client.post(reverse("core:contact"), {
        "name": "Sample Patient",
        "email": "patient@example.test",
        "service": "nursing",
        "message": "Please tell me about nursing support.",
        "website": "",
    })
    assert response.status_code == 200
    assert response.context["submitted"] is True
    enquiry = ServiceEnquiry.objects.get()
    assert enquiry.service == "nursing"
    assert enquiry.status == ServiceEnquiry.Status.NEW


@pytest.mark.django_db
def test_contact_honeypot_does_not_create_an_enquiry(client):
    response = client.post(reverse("core:contact"), {
        "name": "Bot", "email": "bot@example.test", "service": "other",
        "message": "Spam", "website": "http://spam.example.test",
    })
    assert response.status_code == 200
    assert ServiceEnquiry.objects.count() == 0


@pytest.mark.django_db
def test_service_enquiry_admin_is_staff_only(client):
    from django.urls import reverse

    response = client.get(reverse("admin:core_serviceenquiry_changelist"))
    assert response.status_code == 302
    assert ServiceEnquiry.objects.count() == 0


@pytest.mark.django_db
def test_staff_can_open_the_service_enquiry_queue(client, django_user_model):
    staff = django_user_model.objects.create_superuser(
        email="staff@example.test", password="SecureTest123!", name="Care Admin"
    )
    ServiceEnquiry.objects.create(
        name="Sample Patient", email="patient@example.test", service="nursing", message="Please contact me."
    )
    client.force_login(staff)
    response = client.get(reverse("admin:core_serviceenquiry_changelist"))
    assert response.status_code == 200
    assert "Sample Patient" in response.content.decode()


@pytest.mark.django_db
@override_settings(SUPPORT_EMAIL="care@example.test", EMAIL_BACKEND="invalid.email.backend")
def test_enquiry_stays_in_admin_queue_when_notification_delivery_fails(client, caplog):
    response = client.post(reverse("core:contact"), {
        "name": "Sample Patient", "email": "patient@example.test", "service": "elder_care",
        "message": "Please share the available options.", "website": "",
    })
    assert response.status_code == 200
    assert response.context["submitted"] is True
    assert ServiceEnquiry.objects.count() == 1
    assert "notification email was not delivered" in caplog.text
@pytest.mark.django_db
def test_verified_doctor_profile_is_public_and_unverified_profile_is_hidden(client, doctor):
    from django.urls import reverse
    response = client.get(reverse("appointments:doctor_profile", args=[doctor.id]))
    assert response.status_code == 200
    assert doctor.name.encode() in response.content
    doctor.is_verified = False
    doctor.save()
    response = client.get(reverse("appointments:doctor_profile", args=[doctor.id]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_home_labels_unimplemented_care_as_enquiry_options(client):
    response = client.get(reverse("dashboard:home"))
    body = response.content.decode()
    assert "Elder care" in body
    assert "Recovery at home" in body
    assert "ASK OUR TEAM" in body


@pytest.mark.django_db
def test_service_enquiry_retention_command_defaults_to_a_dry_run():
    from datetime import timedelta
    from io import StringIO
    from django.core.management import call_command
    from django.utils import timezone

    enquiry = ServiceEnquiry.objects.create(
        name="Old enquiry", email="old@example.test", service="other", message="Please contact me."
    )
    ServiceEnquiry.objects.filter(pk=enquiry.pk).update(created_at=timezone.now() - timedelta(days=181))
    output = StringIO()

    call_command("purge_service_enquiries", stdout=output)

    assert "Dry run: 1 service enquiry" in output.getvalue()
    assert ServiceEnquiry.objects.filter(pk=enquiry.pk).exists()


@pytest.mark.django_db
def test_service_enquiry_retention_command_deletes_only_expired_records_when_confirmed():
    from datetime import timedelta
    from django.core.management import call_command
    from django.utils import timezone

    old = ServiceEnquiry.objects.create(
        name="Old enquiry", email="old@example.test", service="other", message="Please contact me."
    )
    recent = ServiceEnquiry.objects.create(
        name="Recent enquiry", email="recent@example.test", service="other", message="Please contact me."
    )
    ServiceEnquiry.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=181))

    call_command("purge_service_enquiries", "--execute", "--days=180", verbosity=0)

    assert not ServiceEnquiry.objects.filter(pk=old.pk).exists()
    assert ServiceEnquiry.objects.filter(pk=recent.pk).exists()
