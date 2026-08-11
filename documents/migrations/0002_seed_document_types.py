# documents/migrations/0002_seed_document_types.py
from django.db import migrations

DEFAULT_TYPES = [
    ('Note médicale', True),
    ('Fiche CNSS', True),
    ("Carte d'identité", True),
]


def seed_document_types(apps, schema_editor):
    DocumentType = apps.get_model('documents', 'DocumentType')
    for name, is_cnss_default in DEFAULT_TYPES:
        DocumentType.objects.get_or_create(name=name, defaults={'is_cnss_default': is_cnss_default})


def remove_document_types(apps, schema_editor):
    DocumentType = apps.get_model('documents', 'DocumentType')
    DocumentType.objects.filter(name__in=[n for n, _ in DEFAULT_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed_document_types, remove_document_types),
    ]
