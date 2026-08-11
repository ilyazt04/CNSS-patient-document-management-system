from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from documents.models import Document
from patients.models import Patient
from visits.models import Visit

from .models import AuditLog


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