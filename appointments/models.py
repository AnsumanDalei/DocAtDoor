from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .constants import BOOKING_HORIZON_DAYS, VISIT_DURATION

class AvailabilitySlot(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_slots")
    weekday = models.PositiveSmallIntegerField(help_text="0=Monday, 6=Sunday")
    start_time = models.TimeField()
    end_time = models.TimeField()
    class Meta:
        ordering = ("weekday", "start_time")
        constraints = [models.UniqueConstraint(fields=("doctor", "weekday", "start_time", "end_time"), name="unique_doctor_slot")]

    def __str__(self):
            return f"{self.doctor.name} — {self.weekday_label} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    @property
    def weekday_label(self):
        return ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[self.weekday]
    

    def clean(self):
        if not 0 <= self.weekday <= 6:
            raise ValidationError({"weekday": "Choose a weekday from Monday to Sunday."})
        if self.start_time >= self.end_time:
            raise ValidationError({"end_time": "A slot must end after it starts."})
        if self.doctor_id and self.doctor.role != "doctor":
            raise ValidationError({"doctor": "Availability can only be set for a doctor account."})

class Appointment(models.Model):
    class Status(models.TextChoices): PENDING="Pending", "Pending"; ACCEPTED="Accepted", "Accepted"; COMPLETED="Completed", "Completed"; CANCELLED="Cancelled", "Cancelled"; REJECTED="Rejected", "Rejected"
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_appointments")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="doctor_appointments", null=True, blank=True)
    symptom_description = models.TextField()
    address = models.CharField(max_length=255)
    locality = models.CharField(max_length=120, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=("doctor", "scheduled_at", "status")), models.Index(fields=("patient", "scheduled_at"))]
    def __str__(self):
        patient_name = self.patient.name or self.patient.email
        doctor_name = (self.doctor.name or self.doctor.email) if self.doctor else "Unassigned"
        when = timezone.localtime(self.scheduled_at).strftime("%d %b %Y, %I:%M %p") if self.scheduled_at else "Unscheduled"
        return f"{patient_name} → {doctor_name} • {when}"
    def clean(self):
        if self.scheduled_at and self.scheduled_at <= timezone.now():
            raise ValidationError({"scheduled_at": "Appointment time must be in the future."})
        if self.scheduled_at and timezone.localtime(self.scheduled_at).date() > timezone.localdate() + timedelta(days=BOOKING_HORIZON_DAYS):
            raise ValidationError({"scheduled_at": f"Choose a visit time within the next {BOOKING_HORIZON_DAYS} days."})
        if not self.doctor_id or self.status not in (self.Status.PENDING, self.Status.ACCEPTED):
            return

        if self.doctor.role != "doctor" or not self.doctor.is_verified or not self.doctor.is_available:
            raise ValidationError({"doctor": "This doctor is not currently available for new visits."})

        local_start = timezone.localtime(self.scheduled_at)
        local_end = local_start + VISIT_DURATION
        if local_start.date() != local_end.date():
            raise ValidationError({"scheduled_at": "Choose a visit time that fits within the doctor's daily schedule."})
        matching_slots = AvailabilitySlot.objects.filter(
            doctor_id=self.doctor_id,
            weekday=local_start.weekday(),
            start_time__lte=local_start.time().replace(tzinfo=None),
            end_time__gte=local_end.time().replace(tzinfo=None),
        )
        local_start_naive = datetime.combine(local_start.date(), local_start.time().replace(tzinfo=None))
        aligned = any(
            (local_start_naive - datetime.combine(local_start.date(), slot.start_time)).total_seconds() % VISIT_DURATION.total_seconds() == 0
            for slot in matching_slots
        )
        if not aligned:
            raise ValidationError({"scheduled_at": "Choose one of the available hourly visit times."})

        overlaps = Appointment.objects.exclude(pk=self.pk).filter(
            doctor_id=self.doctor_id,
            status__in=[self.Status.PENDING, self.Status.ACCEPTED],
            scheduled_at__lt=self.scheduled_at + VISIT_DURATION,
            scheduled_at__gt=self.scheduled_at - VISIT_DURATION,
        ).exists()
        if overlaps:
            raise ValidationError({"scheduled_at": "This visit time overlaps another appointment."})

