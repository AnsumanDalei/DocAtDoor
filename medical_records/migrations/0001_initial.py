from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("appointments", "0001_initial")]
    operations = [
        migrations.CreateModel(name="MedicalReport", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("file", models.FileField(upload_to="reports/")), ("original_filename", models.CharField(max_length=255)), ("uploaded_at", models.DateTimeField(auto_now_add=True)), ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="medical_reports", to=settings.AUTH_USER_MODEL))], options={"ordering": ("-uploaded_at",)}),
        migrations.CreateModel(name="Prescription", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("file", models.FileField(upload_to="prescriptions/")), ("original_filename", models.CharField(max_length=255)), ("notes", models.TextField(blank=True)), ("uploaded_at", models.DateTimeField(auto_now=True)), ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="prescription", to="appointments.appointment")), ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))]),
    ]
