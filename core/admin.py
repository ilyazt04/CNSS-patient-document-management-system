from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'table_name', 'timestamp', 'user')
    list_filter = ('table_name', 'action')
    readonly_fields = [f.name for f in AuditLog._meta.fields]