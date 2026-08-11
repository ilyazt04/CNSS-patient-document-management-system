# visits/models.py
import uuid

from django.db import models

from core.models import AuditMixin
from patients.models import Patient


class Visit(AuditMixin):
    class Status(models.TextChoices):
        IN_PREPARATION = 'IN_PREPARATION', 'En préparation'
        SENT_TO_CNSS = 'SENT_TO_CNSS', 'Envoyé à la CNSS'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, related_name='visits', on_delete=models.CASCADE)
    date = models.DateField()
    visit_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PREPARATION,
    )
    # Name pending confirmation from reception (cahier des charges §4.2, §9).
    # DB column name is stable regardless of the eventual French UI label.
    stay_reference = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.patient} — {self.date}'