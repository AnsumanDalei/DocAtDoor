from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class DoctorUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )

    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "phone",
            "role",
            "specialization",
            "qualification",
            "experience_years",
            "consultation_fee",
            "rating",
            "is_available",
            "is_verified",
        )

    class Media:
        js = ("accounts/js/doctor_admin.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Rating: 0 to 5 only
        self.fields["rating"].min_value = 0
        self.fields["rating"].max_value = 5
        self.fields["rating"].widget.attrs.update({
            "min": "0",
            "max": "5",
            "step": "0.1",
        })

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "Passwords do not match."
            )

        return password2

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")

        if rating is not None and (rating < 0 or rating > 5):
            raise forms.ValidationError(
                "Rating must be between 0 and 5."
            )

        return rating

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")

        # Patient cannot have doctor information
        if role == User.Role.PATIENT:
            cleaned_data["specialization"] = ""
            cleaned_data["qualification"] = ""
            cleaned_data["experience_years"] = None
            cleaned_data["consultation_fee"] = None
            cleaned_data["rating"] = 0
            cleaned_data["is_available"] = False
            cleaned_data["is_verified"] = False

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data["password1"]
        )

        # Patient cannot have doctor information
        if user.role == User.Role.PATIENT:
            user.specialization = ""
            user.qualification = ""
            user.experience_years = None
            user.consultation_fee = None
            user.rating = 0
            user.is_available = False
            user.is_verified = False

        if commit:
            user.save()

        return user


class DoctorUserAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password"
    )

    class Meta:
        model = User
        fields = "__all__"

    class Media:
        js = ("accounts/js/doctor_admin.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "rating" in self.fields:
            self.fields["rating"].min_value = 0
            self.fields["rating"].max_value = 5
            self.fields["rating"].widget.attrs.update({
                "min": "0",
                "max": "5",
                "step": "0.1",
            })

    def clean_password(self):
        return self.initial["password"]

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")

        if rating is not None and (rating < 0 or rating > 5):
            raise forms.ValidationError(
                "Rating must be between 0 and 5."
            )

        return rating

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")

        # Patient cannot have doctor information
        if role == User.Role.PATIENT:
            cleaned_data["specialization"] = ""
            cleaned_data["qualification"] = ""
            cleaned_data["experience_years"] = None
            cleaned_data["consultation_fee"] = None
            cleaned_data["rating"] = 0
            cleaned_data["is_available"] = False
            cleaned_data["is_verified"] = False

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Patient cannot have doctor information
        if user.role == User.Role.PATIENT:
            user.specialization = ""
            user.qualification = ""
            user.experience_years = None
            user.consultation_fee = None
            user.rating = 0
            user.is_available = False
            user.is_verified = False

        if commit:
            user.save()

        return user


@admin.register(User)
class DocAtDoorUserAdmin(UserAdmin):
    model = User

    form = DoctorUserAdminForm
    add_form = DoctorUserCreationForm

    list_display = (
        "email",
        "name",
        "role",
        "specialization",
        "experience_years",
        "consultation_fee",
        "rating",
        "is_verified",
        "is_available",
        "date_joined",
    )

    ordering = ("email",)

    fieldsets = (
        (None, {
            "fields": (
                "email",
                "password",
            )
        }),

        ("Personal information", {
            "fields": (
                "name",
                "phone",
                "profile_picture",
            )
        }),

        ("Doctor information", {
            "fields": (
                "role",
                "specialization",
                "qualification",
                "experience_years",
                "consultation_fee",
                "rating",
                "is_available",
                "is_verified",
            )
        }),

        ("Account information", {
            "fields": (
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "name",
                "phone",
                "role",
                "specialization",
                "qualification",
                "experience_years",
                "consultation_fee",
                "rating",
                "is_available",
                "is_verified",
                "password1",
                "password2",
            ),
        }),
    )

    readonly_fields = (
        "date_joined",
    )

    actions = (
        "verify_doctors",
    )

    @admin.action(description="Verify selected doctors")
    def verify_doctors(self, request, queryset):
        queryset.filter(
            role=User.Role.DOCTOR
        ).update(
            is_verified=True
        )