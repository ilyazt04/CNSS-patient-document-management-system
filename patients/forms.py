from django import forms

from .models import Patient, InsuranceProvider


class PatientForm(forms.ModelForm):
    insurance_provider_choice = forms.ModelChoiceField(
        queryset=InsuranceProvider.objects.all(),
        required=False,
        label='Organisme assureur',
        empty_label='— Autre (préciser) —',
    )
    custom_insurance_name = forms.CharField(
        required=False,
        label='Préciser un nouvel organisme',
    )

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

    def clean(self):
        cleaned = super().clean()
        choice = cleaned.get('insurance_provider_choice')
        custom_name = cleaned.get('custom_insurance_name', '').strip()
        if choice and custom_name:
            raise forms.ValidationError(
                'Choisissez soit un organisme existant, soit "Autre", pas les deux.'
            )
        return cleaned

    def get_or_create_insurance_provider(self):
        choice = self.cleaned_data.get('insurance_provider_choice')
        if choice:
            return choice
        custom_name = self.cleaned_data.get('custom_insurance_name', '').strip()
        if not custom_name:
            return None
        provider, _ = InsuranceProvider.objects.get_or_create(name=custom_name)
        return provider