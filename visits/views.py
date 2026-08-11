# visits/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog
from patients.models import Patient

from .forms import VisitForm
from .models import Visit


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    return render(request, 'visits/visit_detail.html', {'visit': visit})


@login_required
def visit_create(request, patient_pk):
    patient = get_object_or_404(Patient.objects.active(), pk=patient_pk)
    if request.method == 'POST':
        form = VisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient
            visit.created_by = request.user
            visit.updated_by = request.user
            visit.save()
            AuditLog.log(
                action='CREATE', table_name='visit', record_id=visit.id,
                description=f'Visite créée pour {patient.full_name} ({visit.date})',
                user=request.user,
            )
            return redirect('visits:detail', pk=visit.pk)
    else:
        form = VisitForm()
    return render(request, 'visits/visit_form.html', {'form': form, 'patient': patient})


@login_required
def visit_edit(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    if request.method == 'POST':
        form = VisitForm(request.POST, instance=visit)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.updated_by = request.user
            visit.save()
            AuditLog.log(
                action='UPDATE', table_name='visit', record_id=visit.id,
                description=f'Visite modifiée : {visit}', user=request.user,
            )
            return redirect('visits:detail', pk=visit.pk)
    else:
        form = VisitForm(instance=visit)
    return render(request, 'visits/visit_form.html', {'form': form, 'patient': visit.patient})


@login_required
def visit_cancel(request, pk):
    """Cancel/mark sent — status transitions rather than deletion (visits aren't soft-deletable, no use case for it)."""
    visit = get_object_or_404(Visit, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in Visit.Status.values:
            visit.status = new_status
            visit.updated_by = request.user
            visit.save()
            AuditLog.log(
                action='UPDATE', table_name='visit', record_id=visit.id,
                description=f'Statut changé : {new_status}', user=request.user,
            )
    return redirect('visits:detail', pk=visit.pk)