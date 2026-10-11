import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, router, transaction
from django.utils import timezone


SPECIALIZATIONS = [
    (x, x)
    for x in [
        "General Physician",
        "Cardiologist",
        "Dentist",
        "Dermatologist",
        "Pediatrician",
        "Orthopedic",
        "Gynecologist",
        "ENT Specialist",
        "Psychiatrist",
        "Neurologist",
    ]
]


class EmailAccountGroup(models.Model):
    """A row used to serialize account creation for one normalized email."""

    normalized_email = models.CharField(max_length=254, unique=True)

    def __str__(self):
        return self.normalized_email


class EmailUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required")

        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(
            email,
            password,
            **extra_fields
        )

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(
            is_staff=True,
            is_superuser=True,
            role="admin",
            is_verified=True,
            email_verified=True,
        )

        return self._create_user(
            email,
            password,
            **extra_fields
        )


class User(AbstractUser):

    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        DOCTOR = "doctor", "Doctor"
        ADMIN = "admin", "Admin"

    class DoctorApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Qualification(models.TextChoices):
        MBBS = "MBBS", "MBBS"
        MD = "MD", "MD"
        MS = "MS", "MS"
        BDS = "BDS", "BDS"
        MDS = "MDS", "MDS"
        DNB = "DNB", "DNB"
        BHMS = "BHMS", "BHMS"
        BAMS = "BAMS", "BAMS"
        BPT = "BPT", "BPT"
        MPT = "MPT", "MPT"
        PHARM_D = "Pharm.D", "Pharm.D"

    username = None

    email = models.EmailField(unique=False)

    email_account_group = models.ForeignKey(
        EmailAccountGroup,
        on_delete=models.PROTECT,
        related_name="accounts",
        editable=False,
    )

    name = models.CharField(max_length=120)

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
        db_index=True,
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
    )

    age = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=20,
        blank=True,
    )

    blood_group = models.CharField(
        max_length=5,
        blank=True,
    )

    specialization = models.CharField(
        max_length=120,
        choices=SPECIALIZATIONS,
        blank=True,
        db_index=True,
    )

    service_area = models.CharField(
        max_length=120,
        blank=True,
        help_text="City or neighborhoods served for home visits.",
    )

    qualification = models.CharField(
        max_length=20,
        choices=Qualification.choices,
        blank=True,
    )

    professional_bio = models.CharField(
        max_length=1200,
        blank=True,
        help_text="Public profile introduction. Do not include patient information.",
    )

    experience_years = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    consultation_fee = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=Decimal("0.0"),
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("5.0")),
        ],
    )

    is_available = models.BooleanField(
        default=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    doctor_approval_status = models.CharField(
        max_length=10,
        choices=DoctorApprovalStatus.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text="Admin review state for doctor accounts; blank for other roles.",
    )

    email_verified = models.BooleanField(
        default=False,
    )

    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )

    email_verification_code_hash = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    email_verification_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_verification_attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    reset_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )

    reset_token_expiry = models.DateTimeField(
        null=True,
        blank=True,
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["name"]

    objects = EmailUserManager()

    @property
    def initials(self):
        return (
            "".join(
                p[0]
                for p in self.name.split()[:2]
            ).upper()
            or "?"
        )

    def clean(self):
        super().clean()

        self.email = self.__class__.objects.normalize_email(
            (self.email or "").strip()
        )

        if self.email:
            existing = User.objects.filter(
                email__iexact=self.email
            )

            if self.pk:
                existing = existing.exclude(
                    pk=self.pk
                )

            if existing.count() >= 2:
                raise ValidationError({
                    "email": (
                        "No more than two accounts can use "
                        "this email address."
                    )
                })

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(
            (self.email or "").strip()
        )

        update_fields = kwargs.get("update_fields")

        email_changed = (
            self._state.adding
            or not self.email_account_group_id
            or update_fields is None
            or "email" in update_fields
        )

        if not email_changed:
            return super().save(*args, **kwargs)

        using = (
            kwargs.get("using")
            or router.db_for_write(
                type(self),
                instance=self,
            )
        )

        with transaction.atomic(using=using):

            canonical_email = self.email.casefold()

            group, _ = (
                EmailAccountGroup.objects
                .using(using)
                .get_or_create(
                    normalized_email=canonical_email
                )
            )

            group = (
                EmailAccountGroup.objects
                .using(using)
                .select_for_update()
                .get(pk=group.pk)
            )

            existing = User.objects.using(using).filter(
                email_account_group=group
            )

            if self.pk:
                existing = existing.exclude(
                    pk=self.pk
                )

            if existing.count() >= 2:
                raise ValidationError({
                    "email": (
                        "No more than two accounts can use "
                        "this email address."
                    )
                })

            previous_group_id = self.email_account_group_id

            self.email_account_group = group

            if update_fields is not None:
                kwargs["update_fields"] = (
                    set(update_fields)
                    | {"email", "email_account_group"}
                )

            result = super().save(
                *args,
                **kwargs
            )

            if (
                previous_group_id
                and previous_group_id != group.pk
            ):
                (
                    EmailAccountGroup.objects
                    .using(using)
                    .filter(
                        pk=previous_group_id,
                        accounts__isnull=True,
                    )
                    .delete()
                )

            return result

    def issue_verification_token(self):
        self.email_verification_token = secrets.token_urlsafe(32)

    def issue_verification_code(self):
        self.issue_verification_token()

        code = f"{secrets.randbelow(1_000_000):06d}"

        self.email_verification_code_hash = make_password(
            code
        )

        self.email_verification_expires_at = (
            timezone.now() + timedelta(minutes=10)
        )

        self.email_verification_attempts = 0

        return code

    def check_verification_code(self, code):
        return (
            bool(self.email_verification_code_hash)
            and check_password(
                code,
                self.email_verification_code_hash,
            )
        )

    def issue_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = (
            timezone.now() + timedelta(minutes=30)
        )


class SocialIdentity(models.Model):

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_identities",
    )

    provider = models.CharField(
        max_length=24,
        choices=Provider.choices,
    )

    subject = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "subject"),
                name="account_social_subject_unique",
            ),
            models.UniqueConstraint(
                fields=("provider", "user"),
                name="account_social_user_provider_unique",
            ),
        ]
