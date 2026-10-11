import os
from datetime import timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment


class Command(BaseCommand):
    help = "Send one reminder for accepted appointments within the configured lead time."

    def handle(self, *args, **options):
        try:
            lead_minutes = int(os.getenv("REMINDER_LEAD_MINUTES", "60"))
            if lead_minutes < 1:
                raise ValueError
        except ValueError as exc:
            raise CommandError("REMINDER_LEAD_MINUTES must be a positive integer.") from exc

        now = timezone.now()
        candidates = Appointment.objects.filter(
            status=Appointment.Status.ACCEPTED,
            reminder_sent=False,
            scheduled_at__gte=now,
            scheduled_at__lte=now + timedelta(minutes=lead_minutes),
        ).values_list("pk", flat=True)

        sent_count = 0
        for appointment_id in candidates.iterator():
            with transaction.atomic():
                appointment = Appointment.objects.select_for_update().select_related("patient", "doctor").filter(
                    pk=appointment_id,
                    status=Appointment.Status.ACCEPTED,
                    reminder_sent=False,
                ).first()
                if appointment is None:
                    continue

                doctor_name = appointment.doctor.name if appointment.doctor else "your doctor"
                local_time = timezone.localtime(appointment.scheduled_at)
                sent = send_mail(
                    "DocAtDoor appointment reminder",
                    f"Your appointment with Dr. {doctor_name} is scheduled for {local_time:%d %b %Y, %I:%M %p}.",
                    None,
                    [appointment.patient.email],
                    fail_silently=False,
                )
                if sent:
                    appointment.reminder_sent = True
                    appointment.save(update_fields=["reminder_sent"])
                    sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} appointment reminder(s)."))
