from django.contrib import admin

from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'contact', 'inpe_number', 'if_number')
    search_fields = ('name', 'specialty', 'inpe_number', 'if_number')