from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("appointments", "0001_initial")]
    operations = [migrations.CreateModel(name="Review", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("rating", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])), ("comment", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="review", to="appointments.appointment")), ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_received", to=settings.AUTH_USER_MODEL)), ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))])]
