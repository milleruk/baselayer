from django import forms
from .models import DailyPlanItem

class DailyPlanItemForm(forms.ModelForm):
    class Meta:
        model = DailyPlanItem
        fields = ["notes", "progression"]
        widgets = {
            "notes": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. felt tight after ride; swapped long-holds for reverse",
            }),
            "progression": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 10s holds → 12s holds",
            }),
        }
