from django import forms
from django.contrib import admin

from accounts.models import User
from appointments.models import Appointment
from .models import Review


class ReviewAdminForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Patient: only patient users, display name only
        if "patient" in self.fields:
            self.fields["patient"].queryset = (
                User.objects
                .filter(role=User.Role.PATIENT)
                .order_by("name")
            )

            self.fields["patient"].label_from_instance = (
                lambda obj: obj.name or "Unnamed patient"
            )

        # Doctor: only doctor users, display name only
        if "doctor" in self.fields:
            self.fields["doctor"].queryset = (
                User.objects
                .filter(
                    role=User.Role.DOCTOR,
                    is_verified=True,
                )
                .order_by("name")
            )

            self.fields["doctor"].label_from_instance = (
                lambda obj: obj.name or "Unnamed doctor"
            )

        # Appointment: only appointments involving a patient and doctor
        if "appointment" in self.fields:
            self.fields["appointment"].queryset = (
                Appointment.objects
                .filter(
                    patient__role=User.Role.PATIENT,
                    doctor__role=User.Role.DOCTOR,
                )
                .select_related("patient", "doctor")
                .order_by("-scheduled_at")
            )

        if "rating" in self.fields:
            self.fields["rating"].min_value = 1
            self.fields["rating"].max_value = 5

            self.fields["rating"].widget.attrs.update({
                "min": "1",
                "max": "5",
                "step": "0.1",
            })

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    form = ReviewAdminForm

    list_display = (
        "patient",
        "doctor",
        "rating",
        "appointment",
    )

    list_filter = (
        "rating",
        "doctor",
    )

    search_fields = (
        "patient__name",
        "doctor__name",
        "comment",
    )