from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'cnss_number', 'cin_number', 'doctor', 'is_active')
    search_fields = ('first_name', 'last_name', 'cnss_number', 'cin_number')
    list_filter = ('relationship_to_insured',)