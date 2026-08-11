# visits/forms.py
from django import forms

from .models import Visit


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['date', 'visit_type', 'status', 'stay_reference']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }