from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog

from .forms import DoctorForm
from .models import Doctor


@login_required
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'doctors/doctor_list.html', {'doctors': doctors})


@login_required
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            doctor = form.save(commit=False)
            doctor.created_by = request.user
            doctor.updated_by = request.user
            doctor.save()
            AuditLog.log(
                action='CREATE', table_name='doctor', record_id=doctor.id,
                description=f'Médecin créé : {doctor.name}', user=request.user,
            )
            return redirect('doctors:list')
    else:
        form = DoctorForm()
    return render(request, 'doctors/doctor_form.html', {'form': form})


@login_required
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            doctor = form.save(commit=False)
            doctor.updated_by = request.user
            doctor.save()
            AuditLog.log(
                action='UPDATE', table_name='doctor', record_id=doctor.id,
                description=f'Médecin modifié : {doctor.name}', user=request.user,
            )
            return redirect('doctors:list')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'doctors/doctor_form.html', {'form': form})