import uuid

from django.db import models

from core.models import AuditMixin


class Doctor(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    specialty = models.CharField(max_length=150, blank=True)
    contact = models.CharField(max_length=150, blank=True)
    inpe_number = models.CharField(
        'N° INPE', max_length=50, unique=True, blank=True, null=True,
    )
    if_number = models.CharField(
        'N° IF', max_length=50, unique=True, blank=True, null=True,
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name