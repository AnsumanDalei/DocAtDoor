from django import forms
from django.contrib import admin

from accounts.models import User
from .models import Notification


class NotificationAdminForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "recipient" in self.fields:
            self.fields["recipient"].queryset = (
                User.objects
                .order_by("name")
            )

            self.fields["recipient"].label_from_instance = (
                lambda obj: obj.name or obj.email
            )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    form = NotificationAdminForm