from django.db import migrations, models


def populate_doctor_approval_status(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="doctor", is_verified=True).update(
        doctor_approval_status="approved"
    )
    User.objects.filter(role="doctor", is_verified=False).update(
        doctor_approval_status="pending"
    )


def restore_legacy_verification(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(
        role="doctor", doctor_approval_status="approved"
    ).update(is_verified=True)
    User.objects.filter(
        role="doctor", doctor_approval_status__in=("pending", "rejected")
    ).update(is_verified=False)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_alter_user_qualification_alter_user_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="doctor_approval_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                help_text="Admin review state for doctor accounts; blank for other roles.",
                max_length=10,
                null=True,
            ),
        ),
        migrations.RunPython(
            populate_doctor_approval_status,
            restore_legacy_verification,
        ),
    ]
