from django import forms

from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'cnss_number', 'cin_number',
            'date_of_birth', 'address', 'doctor', 'relationship_to_insured',
            'insured_first_name', 'insured_last_name', 'insured_cnss_number',
            'insured_cin_number', 'insured_address', 'insured_affiliation_country',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }