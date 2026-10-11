from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from pathlib import Path
import unicodedata
import re
from .models import User

GENDER_CHOICES = (("female", "Female"), ("male", "Male"), ("non_binary", "Non-binary"), ("prefer_not_to_say", "Prefer not to say"))
BLOOD_GROUP_CHOICES = tuple((value, value) for value in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"))

def validate_profile_picture(uploaded):
    if uploaded.size > 5 * 1024 * 1024:
        raise forms.ValidationError("Profile picture must be 5 MB or smaller.")
    if Path(uploaded.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise forms.ValidationError("Use a JPG, PNG, or WebP profile picture.")
    return uploaded


def normalize_person_name(value):
    value = " ".join((value or "").strip().split())
    if not value or len(value) > 120:
        raise forms.ValidationError("Enter a name up to 120 characters.")
    allowed_punctuation = set(" -'.’")
    if any(not (unicodedata.category(char).startswith("L") or unicodedata.category(char).startswith("M") or char in allowed_punctuation) for char in value):
        raise forms.ValidationError("Use letters, spaces, apostrophes, periods, or hyphens in the name.")
    if not any(unicodedata.category(char).startswith("L") for char in value):
        raise forms.ValidationError("Enter a name containing at least one letter.")
    return value


def normalize_phone_number(value):
    value = " ".join((value or "").strip().split())
    if not value:
        return value
    if any(char not in "+0123456789().- " for char in value) or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
        raise forms.ValidationError("Enter a phone number using digits and standard international formatting.")
    digit_count = sum(char.isdigit() for char in value)
    if not 7 <= digit_count <= 15:
        raise forms.ValidationError("Enter a phone number containing 7 to 15 digits.")
    return re.sub(r"\s+", " ", value)


def style_form_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")
        elif not isinstance(field.widget, forms.HiddenInput):
            field.widget.attrs["class"] = (field.widget.attrs.get("class", "") + " form-control").strip()

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "username",
                "inputmode": "email",
                "placeholder": "Enter your email address",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )

    remember_me = forms.BooleanField(
        label="Remember me on this device",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form_fields(self)

    def clean_email(self):
        return User.objects.normalize_email(
            self.cleaned_data["email"].strip()
        )

class VerificationCodeForm(forms.Form):
    email = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}))
    code = forms.CharField(
        label="6-digit verification code",
        min_length=6,
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "Enter the 6-digit code from your email.")],
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "pattern": "[0-9]{6}"}),
    )

    def __init__(self, *args, pending_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pending_user:
            self.fields["email"].initial = pending_user.email
            self.fields["email"].disabled = True
            self.fields["email"].help_text = "This is the address used for your registration."
        style_form_fields(self)


class RegisterForm(forms.ModelForm):
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), min_length=8, help_text="Use at least 8 characters. Django's password checks also screen common and personal-information-based passwords.")
    password_confirm = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), min_length=8)
    role = forms.CharField(
        label="I am registering as",
        widget=forms.Select(choices=((User.Role.PATIENT, "Patient"), (User.Role.DOCTOR, "Doctor"))),
        initial=User.Role.PATIENT,
        required=False,
    )
    gender = forms.ChoiceField(choices=(("", "Select gender"), *GENDER_CHOICES), required=False)
    blood_group = forms.ChoiceField(choices=(("", "Select blood group"), *BLOOD_GROUP_CHOICES), required=False)
    specialization = forms.ChoiceField(choices=(("", "Select specialization"), *User._meta.get_field("specialization").choices), required=False)
    qualification = forms.ChoiceField(choices=(("", "Select qualification"), *User.Qualification.choices), required=False)
    experience_years = forms.IntegerField(required=False, min_value=0, max_value=80, label="Years of experience")
    service_area = forms.CharField(required=False, max_length=120, label="Service area")
    professional_bio = forms.CharField(required=False, max_length=1200, label="Professional introduction", widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Full name"
        self.fields["name"].help_text = "Use the name you want shown on your care account."
        self.fields["phone"].required = False
        self.fields["phone"].help_text = "Optional. Include a country code for an international number."
        self.fields["profile_picture"].required = False
        self.fields["profile_picture"].help_text = "Optional · JPG, PNG, or WebP · up to 5 MB."
        style_form_fields(self)

    def clean_name(self):
        return normalize_person_name(self.cleaned_data.get("name", ""))

    def clean_role(self):
        # Only the two public self-registration roles are accepted. Unknown or
        # tampered values safely retain the existing patient-registration path.
        return User.Role.DOCTOR if self.cleaned_data.get("role") == User.Role.DOCTOR else User.Role.PATIENT

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"].strip())
        if User.objects.filter(email__iexact=email).count() >= 2:
            raise forms.ValidationError("Two accounts already use this email. Sign in and choose an account, or use another address.")
        return email

    def clean_phone(self):
        return normalize_phone_number(self.cleaned_data.get("phone", ""))

    def clean_profile_picture(self):
        uploaded = self.cleaned_data.get("profile_picture")
        return validate_profile_picture(uploaded) if uploaded else uploaded

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("role"):
            cleaned["role"] = User.Role.PATIENT
        if cleaned.get("role") == User.Role.DOCTOR:
            if not cleaned.get("specialization"):
                self.add_error("specialization", "Choose your medical specialization.")
            if not cleaned.get("qualification"):
                self.add_error("qualification", "Choose your professional qualification.")
        else:
            for field in ("specialization", "qualification", "experience_years", "service_area", "professional_bio"):
                cleaned[field] = "" if field in ("specialization", "qualification", "service_area", "professional_bio") else None
        password = cleaned.get("password")
        confirmation = cleaned.get("password_confirm")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirm", "The passwords do not match.")
        if password:
            candidate = User(name=cleaned.get("name", ""), email=cleaned.get("email", ""))
            try:
                validate_password(password, user=candidate)
            except DjangoValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    class Meta:
        model = User
        fields = ("name", "email", "phone", "age", "gender", "blood_group", "profile_picture", "specialization", "qualification", "experience_years", "service_area", "professional_bio")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = self.cleaned_data["role"]
        if user.role == User.Role.DOCTOR:
            user.specialization = self.cleaned_data["specialization"]
            user.qualification = self.cleaned_data["qualification"]
            user.experience_years = self.cleaned_data.get("experience_years")
            user.service_area = self.cleaned_data.get("service_area", "")
            user.professional_bio = self.cleaned_data.get("professional_bio", "")
            user.doctor_approval_status = User.DoctorApprovalStatus.PENDING
            user.is_verified = False
        else:
            user.role = User.Role.PATIENT
            user.doctor_approval_status = None
            user.is_verified = True  # patients don't need admin approval
        user.email_verified = False
        user._verification_code = user.issue_verification_code()
        if commit: user.save()
        return user
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "phone", "profile_picture", "age", "gender", "blood_group", "specialization", "service_area", "qualification", "professional_bio", "experience_years", "consultation_fee", "is_available")
        widgets = {"professional_bio": forms.Textarea(attrs={"rows": 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Full name"
        self.fields["phone"].required = False
        self.fields["phone"].help_text = "Include a country code for an international number."
        self.fields["profile_picture"].required = False
        self.fields["profile_picture"].help_text = "JPG, PNG, or WebP · up to 5 MB."
        style_form_fields(self)
        # Doctor-only fields must never be part of a patient's own profile
        # form — removed from the form itself, not just hidden in the
        # template, so a patient can't submit them either.
        if self.instance.role != User.Role.DOCTOR:
            for name in ("specialization", "service_area", "qualification", "professional_bio", "experience_years", "consultation_fee", "is_available"):
                self.fields.pop(name, None)

    def clean_name(self):
        return normalize_person_name(self.cleaned_data.get("name", ""))

    def clean_phone(self):
        return normalize_phone_number(self.cleaned_data.get("phone", ""))

    def clean_profile_picture(self):
        uploaded = self.cleaned_data.get("profile_picture")
        return validate_profile_picture(uploaded) if uploaded else uploaded

class ChangePasswordForm(DjangoPasswordChangeForm):
    """Django's password validation with a project-friendly form name."""
