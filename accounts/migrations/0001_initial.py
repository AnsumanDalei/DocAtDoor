import accounts.models
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.CreateModel(
        name="User",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("password", models.CharField(max_length=128, verbose_name="password")),
            ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
            ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
            ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
            ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
            ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
            ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active.", verbose_name="active")),
            ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
            ("email", models.EmailField(max_length=254, unique=True)), ("name", models.CharField(max_length=120)),
            ("role", models.CharField(choices=[("patient", "Patient"), ("doctor", "Doctor"), ("admin", "Admin")], db_index=True, default="patient", max_length=10)),
            ("phone", models.CharField(blank=True, max_length=20)), ("profile_picture", models.ImageField(blank=True, upload_to="profiles/")),
            ("age", models.PositiveSmallIntegerField(blank=True, null=True)), ("gender", models.CharField(blank=True, max_length=20)), ("blood_group", models.CharField(blank=True, max_length=5)),
            ("specialization", models.CharField(blank=True, choices=accounts.models.SPECIALIZATIONS, db_index=True, max_length=120)),
            ("qualification", models.CharField(blank=True, max_length=120)), ("experience_years", models.PositiveSmallIntegerField(blank=True, null=True)),
            ("consultation_fee", models.PositiveIntegerField(blank=True, null=True)), ("rating", models.FloatField(default=4.5)), ("is_available", models.BooleanField(default=True)),
            ("is_verified", models.BooleanField(default=False)), ("email_verification_token", models.CharField(blank=True, max_length=64, null=True, unique=True)),
            ("reset_token", models.CharField(blank=True, max_length=64, null=True, unique=True)), ("reset_token_expiry", models.DateTimeField(blank=True, null=True)),
            ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
            ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
        ],
        options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False}, managers=[("objects", accounts.models.EmailUserManager())],
    )]
