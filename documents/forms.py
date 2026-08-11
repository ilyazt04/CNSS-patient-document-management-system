# documents/forms.py
from django import forms

from .models import Document, DocumentType


class DocumentUploadForm(forms.ModelForm):
    document_type_choice = forms.ModelChoiceField(
        queryset=DocumentType.objects.all(),
        required=False,
        label='Type de document',
        empty_label='Autre',
    )
    custom_type_name = forms.CharField(
        required=False,
        label='Préciser le type',
        widget=forms.TextInput(attrs={'placeholder': "ex. Radio, IRM, Ordonnance..."}),
    )

    class Meta:
        model = Document
        fields = ['file']

    def clean(self):
        cleaned = super().clean()
        choice = cleaned.get('document_type_choice')
        custom_name = cleaned.get('custom_type_name', '').strip()

        # "Autre" is represented as the choice field being left blank
        # with custom_type_name filled in instead.
        if not choice and not custom_name:
            raise forms.ValidationError(
                'Sélectionnez un type de document ou précisez-en un nouveau.'
            )
        if choice and custom_name:
            raise forms.ValidationError(
                'Choisissez soit un type existant, soit "Autre", pas les deux.'
            )
        return cleaned

    def get_or_create_document_type(self):
        choice = self.cleaned_data.get('document_type_choice')
        if choice:
            return choice
        custom_name = self.cleaned_data['custom_type_name'].strip()
        doc_type, _created = DocumentType.objects.get_or_create(
            name=custom_name, defaults={'is_cnss_default': False},
        )
        return doc_type