import uuid

from django.db import models

from core.models import AuditMixin, SoftDeleteMixin
from doctors.models import Doctor


class InsuranceProvider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
class Patient(AuditMixin, SoftDeleteMixin):
    class Relationship(models.TextChoices):
        SELF = 'SELF', 'Assuré principal'
        CHILD = 'CHILD', 'Enfant'
        SPOUSE = 'SPOUSE', 'Conjoint'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    cnss_number = models.CharField('N° CNSS', max_length=50, blank=True, db_index=True)
    cin_number = models.CharField('N° CIN', max_length=50, blank=True, db_index=True)
    date_of_birth = models.DateField('Date de naissance', null=True, blank=True)
    address = models.CharField('Adresse', max_length=255, blank=True)
    doctor = models.ForeignKey(
        Doctor, related_name='patients', null=True, blank=True, on_delete=models.SET_NULL,
    )
    insurance_provider = models.ForeignKey(
    InsuranceProvider, related_name='patients', null=True, blank=True, on_delete=models.SET_NULL,
)

    # The patient is the bénéficiaire des soins, not always the assuré.
    relationship_to_insured = models.CharField(
        'Lien de parenté', max_length=10, choices=Relationship.choices,
        default=Relationship.SELF,
    )
    insured_first_name = models.CharField(max_length=100, blank=True)
    insured_last_name = models.CharField(max_length=100, blank=True)
    insured_cnss_number = models.CharField(max_length=50, blank=True)
    insured_cin_number = models.CharField(max_length=50, blank=True)
    insured_address = models.CharField(max_length=255, blank=True)
    insured_affiliation_country = models.CharField(max_length=100, blank=True, default='Maroc')

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def visit_count(self):
        return self.visits.count()

    @property
    def last_visit(self):
        return self.visits.order_by('-date').first()

    def insured_identity(self):
        """Returns (first_name, last_name, cnss_number, cin_number) for the 'Assuré' block."""
        if self.relationship_to_insured == self.Relationship.SELF:
            return self.first_name, self.last_name, self.cnss_number, self.cin_number
        return (
            self.insured_first_name, self.insured_last_name,
            self.insured_cnss_number, self.insured_cin_number,
        )
    
