from django import forms
from .models import Review
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {"rating": forms.Select(choices=[(value, f"{value} star{'s' if value != 1 else ''}") for value in range(1, 6)]), "comment": forms.Textarea(attrs={"rows": 3})}
