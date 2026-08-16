# visits/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog
from patients.models import Patient

from .forms import VisitForm
from .models import Visit
from django.utils import timezone 
from documents.models import CNSSRequestForm


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

@login_required
def visit_duplicate(request, pk):
    original = get_object_or_404(Visit, pk=pk)
    new_visit = Visit.objects.create(
        patient=original.patient, date=timezone.now().date(),
        visit_type=original.visit_type, created_by=request.user, updated_by=request.user,
    )
    if hasattr(original, 'cnss_request'):
        old_form = original.cnss_request
        new_form = CNSSRequestForm.objects.create(
            visit=new_visit,
            establishment_name=old_form.establishment_name, establishment_code=old_form.establishment_code,
            insured_first_name=old_form.insured_first_name, insured_last_name=old_form.insured_last_name,
            insured_cnss_number=old_form.insured_cnss_number, insured_cin_number=old_form.insured_cin_number,
            insured_address=old_form.insured_address, insured_affiliation_country=old_form.insured_affiliation_country,
            beneficiary_first_name=old_form.beneficiary_first_name, beneficiary_last_name=old_form.beneficiary_last_name,
            beneficiary_cin_number=old_form.beneficiary_cin_number, beneficiary_date_of_birth=old_form.beneficiary_date_of_birth,
            beneficiary_sex=old_form.beneficiary_sex, relationship_to_insured=old_form.relationship_to_insured,
            created_by=request.user, updated_by=request.user,
        )
        new_form.ensure_estimation_lines()
        new_form.ensure_frais_sejour_lines()
    AuditLog.log(
        action='CREATE', table_name='visit', record_id=new_visit.id,
        description=f'Visite dupliquée depuis {original.id}', user=request.user,
    )
    return redirect('visits:detail', pk=new_visit.pk)