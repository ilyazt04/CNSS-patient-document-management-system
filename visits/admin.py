# visits/admin.py
from django.contrib import admin

from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date', 'visit_type', 'status', 'stay_reference')
    list_filter = ('status',)
    search_fields = (
        'patient__first_name', 'patient__last_name', 'stay_reference',
    )