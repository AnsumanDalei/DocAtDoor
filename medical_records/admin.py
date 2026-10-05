from django import forms
from django.contrib import admin

from accounts.models import User
from .models import Consultation, MedicalReport, Prescription


class ConsultationAdminForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
                lambda obj: obj.name
            )

class MedicalReportAdminForm(forms.ModelForm):
    class Meta:
        model = MedicalReport
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "patient" in self.fields:
            self.fields["patient"].queryset = (
                User.objects
                .filter(role=User.Role.PATIENT)
                .order_by("name", "email")
            )

            self.fields["patient"].label_from_instance = (
                lambda obj: obj.name or obj.email
            )


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    form = ConsultationAdminForm


@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    form = MedicalReportAdminForm


class PrescriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
                lambda obj: obj.name
            )


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    form = PrescriptionAdminForm