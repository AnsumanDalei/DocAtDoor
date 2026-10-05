from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="AvailabilitySlot", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("weekday", models.PositiveSmallIntegerField(help_text="0=Monday, 6=Sunday")), ("start_time", models.TimeField()), ("end_time", models.TimeField()), ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_slots", to=settings.AUTH_USER_MODEL))], options={"ordering": ("weekday", "start_time")}),
        migrations.CreateModel(name="Appointment", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("symptom_description", models.TextField()), ("address", models.CharField(max_length=255)), ("scheduled_at", models.DateTimeField(db_index=True)), ("status", models.CharField(choices=[("Pending", "Pending"), ("Accepted", "Accepted"), ("Completed", "Completed"), ("Cancelled", "Cancelled"), ("Rejected", "Rejected")], db_index=True, default="Pending", max_length=12)), ("reminder_sent", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("doctor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="doctor_appointments", to=settings.AUTH_USER_MODEL)), ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="patient_appointments", to=settings.AUTH_USER_MODEL))]),
        migrations.AddConstraint(model_name="availabilityslot", constraint=models.UniqueConstraint(fields=("doctor", "weekday", "start_time", "end_time"), name="unique_doctor_slot")),
        migrations.AddIndex(model_name="appointment", index=models.Index(fields=["doctor", "scheduled_at", "status"], name="appointmen_doctor__d8885e_idx")),
        migrations.AddIndex(model_name="appointment", index=models.Index(fields=["patient", "scheduled_at"], name="appointmen_patient_8c6a53_idx")),
    ]
