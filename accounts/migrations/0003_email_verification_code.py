from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_email_verified_alter_user_groups_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verification_code_hash",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verification_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
