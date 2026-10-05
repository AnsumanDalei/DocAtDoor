from django import forms
from .models import ServiceEnquiry


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ServiceEnquiry
        fields = ("name", "email", "service", "message")
        labels = {"service": "What are you enquiring about?"}
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}
        help_texts = {"message": "Please do not include medical records or sensitive health information."}

    def clean_website(self):
        value = self.cleaned_data["website"]
        if value:
            raise forms.ValidationError("Unable to submit this enquiry.")
        return value
