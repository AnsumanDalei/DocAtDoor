from django.db import models


class ServiceEnquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        CLOSED = "closed", "Closed"

    SERVICE_CHOICES = [
        ("doctor", "Doctor home visit"),
        ("nursing", "Nursing support"),
        ("physiotherapy", "Physiotherapy"),
        ("diagnostics", "Tests and diagnostics"),
        ("elder_care", "Elder care"),
        ("recovery", "Recovery / post-hospital care"),
        ("other", "Something else"),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField()
    service = models.CharField(max_length=24, choices=SERVICE_CHOICES)
    message = models.CharField(max_length=1200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    staff_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "service enquiry"
        verbose_name_plural = "service enquiries"

    def __str__(self):
        return f"{self.get_service_display()} — {self.name} ({self.get_status_display()})"
