from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog

from .forms import PatientForm
from .models import Patient

SEARCH_FIELDS = {
    'name': 'last_name__icontains',   # matched against last_name; extend if you want first+last combined
    'cnss': 'cnss_number__icontains',
    'cin': 'cin_number__icontains',
}


@login_required
def patient_list(request):
    patients = Patient.objects.active()

    query = request.GET.get('q', '').strip()
    field = request.GET.get('field', 'name')

    if query and field in SEARCH_FIELDS:
        patients = patients.filter(**{SEARCH_FIELDS[field]: query})

    return render(request, 'patients/patient_list.html', {
        'patients': patients,
        'query': query,
        'field': field,
        'result_count': patients.count(),
    })


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient.objects.active(), pk=pk)
    return render(request, 'patients/patient_detail.html', {'patient': patient})


@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.updated_by = request.user
            patient.save()
            AuditLog.log(
                action='CREATE', table_name='patient', record_id=patient.id,
                description=f'Patient créé : {patient.full_name}', user=request.user,
            )
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'patients/patient_form.html', {'form': form})


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient.objects.active(), pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.updated_by = request.user
            patient.insurance_provider = form.get_or_create_insurance_provider()
            patient.created_by = request.user
            patient.save()
            AuditLog.log(
                action='UPDATE', table_name='patient', record_id=patient.id,
                description=f'Patient modifié : {patient.full_name}', user=request.user,
            )
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_form.html', {'form': form})


@login_required
def patient_delete(request, pk):
    patient = get_object_or_404(Patient.objects.active(), pk=pk)
    if request.method == 'POST':
        if not request.user.is_staff:
            return redirect('patients:detail', pk=patient.pk)  # guard, per cahier des charges 4.7
        patient.soft_delete()
        AuditLog.log(
            action='DELETE', table_name='patient', record_id=patient.id,
            description=f'Patient supprimé (soft) : {patient.full_name}', user=request.user,
        )
        return redirect('patients:list')
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})

import csv
from django.http import HttpResponse

@login_required
def patient_export_csv(request):
    patients = Patient.objects.active()
    query = request.GET.get('q', '').strip()
    field = request.GET.get('field', 'name')
    if query and field in SEARCH_FIELDS:
        patients = patients.filter(**{SEARCH_FIELDS[field]: query})

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="patients.csv"'
    writer = csv.writer(response)
    writer.writerow(['Nom', 'Prénom', 'N° CNSS', 'N° CIN', 'Date de naissance', 'Assureur', 'Médecin'])
    for p in patients:
        writer.writerow([
            p.last_name, p.first_name, p.cnss_number, p.cin_number,
            p.date_of_birth, p.insurance_provider, p.doctor,
        ])
    return response