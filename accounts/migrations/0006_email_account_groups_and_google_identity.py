from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def group_existing_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    EmailAccountGroup = apps.get_model("accounts", "EmailAccountGroup")
    database = schema_editor.connection.alias
    for user_id, email in User.objects.using(database).order_by("pk").values_list("pk", "email").iterator():
        normalized = (email or "").strip().casefold()
        group, _ = EmailAccountGroup.objects.using(database).get_or_create(normalized_email=normalized)
        User.objects.using(database).filter(pk=user_id).update(email_account_group_id=group.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_user_professional_bio"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailAccountGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("normalized_email", models.CharField(max_length=254, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="SocialIdentity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("google", "Google")], max_length=24)),
                ("subject", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_identities", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="socialidentity",
            constraint=models.UniqueConstraint(fields=("provider", "subject"), name="account_social_subject_unique"),
        ),
        migrations.AddConstraint(
            model_name="socialidentity",
            constraint=models.UniqueConstraint(fields=("provider", "user"), name="account_social_user_provider_unique"),
        ),
        migrations.AddField(
            model_name="user",
            name="email_account_group",
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="accounts.emailaccountgroup"),
        ),
        migrations.RunPython(group_existing_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name="user",
            name="email_account_group",
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="accounts.emailaccountgroup"),
        ),
    ]
