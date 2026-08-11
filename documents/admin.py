# documents/admin.py
from django.contrib import admin

from .models import (
    CNSSEstimationLine, CNSSRequestForm, Document, DocumentType,
    FormTemplate, GeneratedPDF,
)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_cnss_default')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'document_type', 'source', 'patient', 'visit', 'is_active')
    list_filter = ('source', 'document_type')


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_type', 'is_active')


class CNSSEstimationLineInline(admin.TabularInline):
    model = CNSSEstimationLine
    extra = 0


@admin.register(CNSSRequestForm)
class CNSSRequestFormAdmin(admin.ModelAdmin):
    list_display = ('visit', 'beneficiary_first_name', 'beneficiary_last_name')
    inlines = [CNSSEstimationLineInline]


@admin.register(GeneratedPDF)
class GeneratedPDFAdmin(admin.ModelAdmin):
    list_display = ('visit', 'pdf_type', 'generated_at', 'generated_by')
    list_filter = ('pdf_type',)

# documents/admin.py — add this
from .models import FraisSejourLine

@admin.register(FraisSejourLine)
class FraisSejourLineAdmin(admin.ModelAdmin):
    list_display = ('form', 'row_label', 'nbr_jour', 'p_u', 'total_ht')
    list_filter = ('row_label',)