from django import forms
from django.contrib import admin

from accounts.models import User
from .models import Appointment, AvailabilitySlot


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["patient"].queryset = (
            User.objects
            .filter(role=User.Role.PATIENT)
            .order_by("name", "email")
        )

        self.fields["doctor"].queryset = (
            User.objects
            .filter(role=User.Role.DOCTOR)
            .order_by("name", "email")
        )

        self.fields["patient"].label_from_instance = (
            lambda obj: obj.name or obj.email
        )

        self.fields["doctor"].label_from_instance = (
            lambda obj: obj.name or obj.email
        )


class AvailabilitySlotAdminForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["doctor"].queryset = (
            User.objects
            .filter(role=User.Role.DOCTOR)
            .order_by("name", "email")
        )

        self.fields["doctor"].label_from_instance = (
            lambda obj: obj.name or obj.email
        )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    form = AvailabilitySlotAdminForm