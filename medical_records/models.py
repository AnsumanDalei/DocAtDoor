from django.conf import settings
from django.db import models

from .storage import protected_storage


class MedicalReport(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medical_reports",
    )
    file = models.FileField(
        upload_to="reports/",
        storage=protected_storage,
    )
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        patient_name = self.patient.name or self.patient.email
        return f"{patient_name} — {self.original_filename}"


class Prescription(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="prescription",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        upload_to="prescriptions/",
        storage=protected_storage,
    )
    original_filename = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        patient_name = (
            self.appointment.patient.name
            or self.appointment.patient.email
        )
        doctor_name = self.doctor.name or self.doctor.email

        return (
            f"{patient_name} → Dr. {doctor_name} — "
            f"{self.original_filename}"
        )


class Consultation(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="consultation",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consultations_written",
    )
    summary = models.TextField()
    diagnosis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.appointment_id or not self.doctor_id:
            return

        appointment = self.appointment

        if appointment.doctor_id != self.doctor_id:
            raise ValidationError({
                "doctor": (
                    "Only the doctor assigned to this visit "
                    "can write its consultation."
                )
            })

        if appointment.status != appointment.Status.COMPLETED:
            raise ValidationError({
                "appointment": (
                    "Consultation notes can be saved after "
                    "the visit is complete."
                )
            })

    def __str__(self):
        patient_name = (
            self.appointment.patient.name
            or self.appointment.patient.email
        )
        doctor_name = self.doctor.name or self.doctor.email

        return f"{patient_name} → Dr. {doctor_name} — Consultation"