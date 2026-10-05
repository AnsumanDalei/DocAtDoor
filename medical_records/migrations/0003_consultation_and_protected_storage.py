import django.db.models.deletion
import medical_records.storage
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0002_rename_appointmen_doctor__d8885e_idx_appointment_doctor__305b76_idx_and_more"),
        ("medical_records", "0002_alter_medicalreport_file_alter_prescription_file"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="medicalreport",
            name="file",
            field=models.FileField(storage=medical_records.storage.protected_storage, upload_to="reports/"),
        ),
        migrations.AlterField(
            model_name="prescription",
            name="file",
            field=models.FileField(storage=medical_records.storage.protected_storage, upload_to="prescriptions/"),
        ),
        migrations.CreateModel(
            name="Consultation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("summary", models.TextField()),
                ("diagnosis", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="consultation", to="appointments.appointment")),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consultations_written", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
    ]
