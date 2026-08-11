import uuid

from django.conf import settings
from django.db import models


class AuditMixin(models.Model):
    """
    Common audit fields, inherited by every domain model in the project.
    Abstract — creates no table of its own, just adds these columns
    wherever it's used.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='%(app_label)s_%(class)s_created',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='%(app_label)s_%(class)s_updated',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)


class SoftDeleteMixin(models.Model):
    """
    Adds deleted_at. deleted_at IS NULL means the row is active —
    no separate is_active flag needed alongside it.
    """
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None


class AuditLog(models.Model):
    """
    Lightweight audit trail for key actions only (document import,
    PDF generation) — not exhaustive CRUD logging on every model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} on {self.table_name} at {self.timestamp:%Y-%m-%d %H:%M}'

    @classmethod
    def log(cls, *, action, table_name, record_id=None, description='', user=None):
        return cls.objects.create(
            action=action,
            table_name=table_name,
            record_id=record_id,
            description=description,
            user=user,
        )