from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from notifications.models import Notification


@pytest.fixture
def notification(patient, doctor):
    appointment = Appointment.objects.create(patient=patient, doctor=doctor, symptom_description="Fever",
                                               address="Home", scheduled_at=timezone.now() + timedelta(days=1))
    return Notification.objects.create(recipient=doctor, appointment=appointment, message="New request")


@pytest.mark.django_db
def test_inbox_lists_only_the_logged_in_users_notifications(client, doctor, other_doctor, notification):
    client.force_login(doctor)
    resp = client.get(reverse("notifications:inbox"))
    assert list(resp.context["notifications"]) == [notification]

    client.force_login(other_doctor)
    resp = client.get(reverse("notifications:inbox"))
    assert list(resp.context["notifications"]) == []


@pytest.mark.django_db
def test_mark_all_read(client, doctor, notification):
    assert notification.is_read is False
    client.force_login(doctor)
    client.post(reverse("notifications:mark_all_read"))
    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_delete_notification_is_scoped_to_its_recipient(client, doctor, other_doctor, notification):
    client.force_login(other_doctor)
    resp = client.post(reverse("notifications:delete", args=[notification.id]))
    assert resp.status_code == 404
    assert Notification.objects.filter(pk=notification.id).exists()

    client.force_login(doctor)
    client.post(reverse("notifications:delete", args=[notification.id]))
    assert not Notification.objects.filter(pk=notification.id).exists()
