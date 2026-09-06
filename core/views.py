from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documents.models import Document
from patients.models import Patient
from visits.models import Visit

from .models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {
        'total_patients': Patient.objects.active().count(),
        'visits_in_preparation': Visit.objects.filter(status=Visit.Status.IN_PREPARATION).count(),
        'visits_sent': Visit.objects.filter(status=Visit.Status.SENT_TO_CNSS).count(),
        'recent_documents': Document.objects.active().select_related(
            'document_type', 'patient', 'visit__patient'
        )[:5],
        'recent_activity': AuditLog.objects.select_related('user')[:8],
    })

from datetime import datetime
from django.utils import timezone

@login_required
def activity_log(request):
    logs = AuditLog.objects.select_related('user').all()

    table_filter = request.GET.get('table', '')
    if table_filter:
        logs = logs.filter(table_name=table_filter)

    user_filter = request.GET.get('user', '')
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    return render(request, 'activity_log.html', {
        'logs': logs[:200],
        'table_filter': table_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'table_choices': AuditLog.objects.order_by('table_name').values_list('table_name', flat=True).distinct(),
        'users': User.objects.filter(id__in=AuditLog.objects.values_list('user_id', flat=True).distinct()),
    })