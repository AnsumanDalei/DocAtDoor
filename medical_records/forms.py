from pathlib import Path

from django import forms

from .models import Consultation


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_medical_upload(uploaded):
    extension = Path(uploaded.name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise forms.ValidationError("Only PDF, PNG, and JPG files are allowed.")
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File must be 5 MB or smaller.")
    signature = uploaded.read(8)
    uploaded.seek(0)
    valid_signatures = {
        ".pdf": signature.startswith(b"%PDF-"),
        ".png": signature.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": signature.startswith(b"\xff\xd8\xff"),
        ".jpeg": signature.startswith(b"\xff\xd8\xff"),
    }
    if not valid_signatures[extension]:
        raise forms.ValidationError("The file contents do not match the selected file type.")
    return uploaded


class UploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        return validate_medical_upload(self.cleaned_data["file"])


class ConsultationForm(forms.ModelForm):
    summary = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 5}))
    diagnosis = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = Consultation
        fields = ("summary", "diagnosis")
        labels = {"summary": "Consultation summary", "diagnosis": "Diagnosis or clinical impression"}
        help_texts = {
            "summary": "Record the completed visit outcome for the patient and assigned care team.",
            "diagnosis": "Optional. Enter only the information needed for this patient's care.",
        }
