from django import forms
from django.utils import timezone

from accounts.models import User
from .models import Appointment, AvailabilitySlot


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("doctor", "symptom_description", "address", "locality", "city", "contact_phone", "scheduled_at")
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "contact_phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(
            role=User.Role.DOCTOR,
            is_verified=True,
            is_available=True,
        )
        self.fields["address"].help_text = "Street address and any directions the care team needs."
        self.fields["locality"].required = False
        self.fields["city"].required = not bool(self.instance.pk)
        self.fields["contact_phone"].required = not bool(self.instance.pk)
        self.fields["contact_phone"].initial = getattr(self.instance.patient, "phone", "") if self.instance and self.instance.pk else ""

    def clean_scheduled_at(self):
        value = self.cleaned_data["scheduled_at"]
        if value <= timezone.now():
            raise forms.ValidationError("Choose a future date and time.")
        return value


class SlotForm(forms.ModelForm):
    weekday = forms.ChoiceField(choices=[(index, day) for index, day in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))])
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    class Meta:
        model = AvailabilitySlot
        fields = ("weekday", "start_time", "end_time")
