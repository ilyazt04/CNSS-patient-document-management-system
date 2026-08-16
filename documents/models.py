# documents/models.py
import uuid
import re
import unicodedata

from django.conf import settings
from django.db import models

from core.models import AuditMixin, SoftDeleteMixin
from patients.models import Patient, InsuranceProvider
from visits.models import Visit


class DocumentType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    is_cnss_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# documents/models.py
def _patient_folder_name(patient):
    """Builds a filesystem-safe, human-readable folder name: LASTNAME_FIRSTNAME-CNSSNUMBER."""
    raw = f'{patient.last_name}_{patient.first_name}'
    ascii_name = unicodedata.normalize('NFKD', raw).encode('ascii', 'ignore').decode('ascii')
    ascii_name = re.sub(r'[^A-Za-z0-9_]+', '', ascii_name.replace(' ', '_')).upper()
    id_part = patient.cnss_number.strip() if patient.cnss_number else str(patient.id)[:8]
    id_part = re.sub(r'[^A-Za-z0-9]+', '', id_part)
    return f'{ascii_name or "PATIENT"}-{id_part or str(patient.id)[:8]}'


def document_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    safe_name = f'{instance.id}.{ext}'
    patient = instance.visit.patient if instance.visit_id else instance.patient
    folder = _patient_folder_name(patient)
    if instance.visit_id:
        return f'patients/{folder}/visits/visit_{instance.visit_id}/{safe_name}'
    return f'patients/{folder}/administrative/{safe_name}'


def thumbnail_upload_path(instance, filename):
    safe_name = f'{instance.id}_thumb.jpg'
    patient = instance.visit.patient if instance.visit_id else instance.patient
    folder = _patient_folder_name(patient)
    if instance.visit_id:
        return f'patients/{folder}/visits/visit_{instance.visit_id}/thumbs/{safe_name}'
    return f'patients/{folder}/administrative/thumbs/{safe_name}'

from django.utils import timezone


def generated_pdf_upload_path(instance, filename):
    patient = instance.visit.patient
    folder = _patient_folder_name(patient)
    date_str = timezone.now().strftime('%Y-%m-%d_%H%M')
    suffix = 'CNSS' if instance.pdf_type == 'CNSS_DEFAULT' else 'PERSONNALISE'
    return f'generated_pdfs/{folder}/{folder}_{suffix}_{date_str}.pdf'

class Document(AuditMixin, SoftDeleteMixin):
    class Source(models.TextChoices):
        UPLOADED = 'UPLOADED', 'Scanné'
        GENERATED = 'GENERATED', 'Généré automatiquement'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, related_name='administrative_documents',
        null=True, blank=True, on_delete=models.CASCADE,
    )
    visit = models.ForeignKey(
        Visit, related_name='documents',
        null=True, blank=True, on_delete=models.CASCADE,
    )
    document_type = models.ForeignKey(DocumentType, related_name='documents', on_delete=models.PROTECT)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.UPLOADED)
    file = models.FileField(upload_to=document_upload_path, max_length=255)
    thumbnail = models.ImageField(upload_to=thumbnail_upload_path, null=True, blank=True, max_length=255)
    filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(patient__isnull=False, visit__isnull=True)
                    | models.Q(patient__isnull=True, visit__isnull=False)
                ),
                name='document_belongs_to_exactly_one_parent',
            )
        ]

    def __str__(self):
        return self.filename or str(self.id)

    @property
    def is_administrative(self):
        return self.patient_id is not None




class FormTemplate(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    insurance_provider = models.ForeignKey(
        InsuranceProvider, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Laisser vide pour un modèle générique (CNSS par défaut).",
    )
    blank_pdf = models.FileField(upload_to='form_templates/')
    field_mapping = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        provider = self.insurance_provider.name if self.insurance_provider else 'Générique'
        return f'{self.name} ({provider})'


ESTIMATION_ROW_LABELS = [
    'Actes médicaux', 'Actes chirurgicaux', 'Actes paramédicaux',
    "Actes d'odontologie", 'Kinésithérapie', 'Anesthésie',
    "Bloc opératoire/Salle d'accouchement", 'Surveillance Réanimation',
    'Surveillance médicale', 'Biologie', 'Radiologie et imagerie médicale',
    'Autres (anatomopathologie, ECG, EEG, Endoscopie...)', 'Pharmacie',
    'Appareils et dispositifs médicaux', 'Sang et dérivés',
]


class CNSSRequestForm(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(Visit, related_name='cnss_request', on_delete=models.CASCADE)
    total_montant = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Auto-calculé à partir des lignes, mais modifiable manuellement.",)
    establishment_name = models.CharField(max_length=200, blank=True)
    establishment_code = models.CharField(max_length=50, blank=True)
    room_number = models.CharField(max_length=20, blank=True)
    service_hospitalisation = models.CharField(max_length=200, blank=True)
    patient_inp_number = models.CharField(max_length=20, blank=True)
    n_compostage = models.CharField(max_length=50, blank=True)
    dossier_hospitalisation_number = models.CharField(max_length=50, blank=True)
    
    hospitalization_type = models.CharField(max_length=40, blank=True,)
    urgent_date = models.DateField(null=True, blank=True)   

    insured_first_name = models.CharField(max_length=100, blank=True)
    insured_last_name = models.CharField(max_length=100, blank=True)
    insured_cnss_number = models.CharField(max_length=50, blank=True)
    insured_cin_number = models.CharField(max_length=50, blank=True)
    insured_address = models.CharField(max_length=255, blank=True)
    insured_affiliation_country = models.CharField(max_length=100, blank=True)

    beneficiary_first_name = models.CharField(max_length=100, blank=True)
    beneficiary_last_name = models.CharField(max_length=100, blank=True)
    beneficiary_cin_number = models.CharField(max_length=50, blank=True)
    beneficiary_date_of_birth = models.DateField(null=True, blank=True)
    beneficiary_sex = models.CharField(
        max_length=1, choices=[('F', 'Féminin'), ('M', 'Masculin')], blank=True,
    )
    relationship_to_insured = models.CharField(max_length=30, blank=True)

    illness_nature = models.TextField(blank=True)
    intervention_nature = models.TextField(blank=True)
    hospitalization_nature = models.TextField(blank=True)
    admission_reason = models.TextField(blank=True)
    expected_admission_date = models.DateField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)

    def prefill_from_patient(self):
        patient = self.visit.patient
        f_name, l_name, cnss, cin = patient.insured_identity()
        self.insured_first_name = f_name
        self.insured_last_name = l_name
        self.insured_cnss_number = cnss
        self.insured_cin_number = cin
        self.insured_address = patient.insured_address
        self.insured_affiliation_country = patient.insured_affiliation_country or 'Maroc'

        self.beneficiary_first_name = patient.first_name
        self.beneficiary_last_name = patient.last_name
        self.beneficiary_cin_number = patient.cin_number
        self.beneficiary_date_of_birth = patient.date_of_birth
        self.relationship_to_insured = patient.relationship_to_insured

    def ensure_estimation_lines(self):
        existing = set(self.lines.values_list('row_label', flat=True))
        for label in ESTIMATION_ROW_LABELS:
            if label not in existing:
                CNSSEstimationLine.objects.create(form=self, row_label=label, is_included=False)

    def ensure_frais_sejour_lines(self):
            existing = set(self.frais_sejour_lines.values_list('row_label', flat=True))
            for label in FRAIS_SEJOUR_ROWS:
                if label not in existing:
                    FraisSejourLine.objects.create(form=self, row_label=label)
    

    def __str__(self):
        return f'Demande CNSS — {self.visit}'


class CNSSEstimationLine(models.Model):
    form = models.ForeignKey(CNSSRequestForm, related_name='lines', on_delete=models.CASCADE)
    row_label = models.CharField(max_length=150)
    is_included = models.BooleanField(default=False)
    text = models.TextField(blank=True)
    lettre_cle = models.CharField(max_length=50, blank=True)
    valeur_cle = models.CharField(max_length=50, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.row_label} ({"✓" if self.is_included else "—"})'

FRAIS_SEJOUR_ROWS = ['Séjour Normal', 'Soins Intensifs', 'Réanimation', 'Couveuse']


class FraisSejourLine(models.Model):
    form = models.ForeignKey(CNSSRequestForm, related_name='frais_sejour_lines', on_delete=models.CASCADE)
    row_label = models.CharField(max_length=50)
    nbr_jour = models.PositiveIntegerField(null=True, blank=True)
    p_u = models.CharField(max_length=50, blank=True, null=True)
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.row_label



class GeneratedPDF(models.Model):
    class PDFType(models.TextChoices):
        CNSS_DEFAULT = 'CNSS_DEFAULT', 'PDF CNSS'
        CUSTOM = 'CUSTOM', 'PDF personnalisé'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, related_name='generated_pdfs', on_delete=models.CASCADE)
    pdf_type = models.CharField(max_length=20, choices=PDFType.choices)
    file = models.FileField(upload_to=generated_pdf_upload_path, max_length=255)
    source_documents = models.ManyToManyField(Document, related_name='generated_pdfs')
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.get_pdf_type_display()} — {self.visit} ({self.generated_at:%Y-%m-%d})'


class EstimationPhrase(AuditMixin):
    """
    Reusable text + montant remembered per estimation row, so staff
    can pick a common phrase instead of retyping it every time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    row_label = models.CharField(max_length=150)  # matches ESTIMATION_ROW_LABELS
    text = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    

    class Meta:
        unique_together = ('row_label', 'text')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.row_label}: {self.text}'

    @classmethod
    def remember(cls, *, row_label, text, montant, user=None):
        """Saves or refreshes a phrase's montant whenever it's used."""
        if not text.strip():
            return None
        phrase, _ = cls.objects.update_or_create(
            row_label=row_label, text=text.strip(),
            defaults={'montant': montant, 'updated_by': user},
        )
        return phrase

    