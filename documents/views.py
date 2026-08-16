# documents/views.py
import fitz  # PyMuPDF
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AuditLog
from patients.models import Patient
from visits.models import Visit

from .forms import DocumentUploadForm
from .models import Document

import io
from PIL import Image, ImageOps

THUMBNAIL_MAX_SIZE = (600, 600)


def _generate_thumbnail(document):
    document.file.seek(0)
    ext = (document.file_type or '').lower()

    if ext == 'pdf':
        pdf = fitz.open(stream=document.file.read(), filetype='pdf')
        pix = pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2))  # higher res render
        img = Image.open(io.BytesIO(pix.tobytes('png')))
    else:
        img = Image.open(document.file)
        img = ImageOps.exif_transpose(img)  # respects scanner/phone orientation

    img = img.convert('RGB')
    img.thumbnail(THUMBNAIL_MAX_SIZE, Image.LANCZOS)  # preserves aspect ratio, high-quality downsample

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    document.thumbnail.save(f'{document.id}_thumb.jpg', ContentFile(buf.getvalue()), save=False)
    document.file.seek(0)


@login_required
def document_upload_to_visit(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    return _handle_upload(request, visit=visit, patient=None)


@login_required
def document_upload_administrative(request, patient_pk):
    patient = get_object_or_404(Patient.objects.active(), pk=patient_pk)
    return _handle_upload(request, visit=None, patient=patient)


def _handle_upload(request, *, visit, patient):
    parent = visit or patient
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.visit = visit
            document.patient = patient
            document.document_type = form.get_or_create_document_type()
            document.filename = document.file.name
            document.file_type = document.file.name.split('.')[-1].lower()
            document.created_by = request.user
            document.updated_by = request.user

            try:
                _generate_thumbnail(document)
            except Exception:
                pass  # thumbnail is a nice-to-have, upload shouldn't fail without it

            document.save()
            AuditLog.log(
                action='CREATE', table_name='document', record_id=document.id,
                description=f'Document importé : {document.filename} ({document.document_type.name})',
                user=request.user,
            )
            redirect_target = 'visits:detail' if visit else 'patients:detail'
            return redirect(redirect_target, pk=parent.pk)
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/document_upload.html', {
        'form': form, 'visit': visit, 'patient': patient,
    })


@login_required
def document_delete(request, pk):
    document = get_object_or_404(Document.objects.active(), pk=pk)
    parent = document.visit or document.patient
    if request.method == 'POST':
        document.soft_delete()
        AuditLog.log(
            action='DELETE', table_name='document', record_id=document.id,
            description=f'Document supprimé (soft) : {document.filename}', user=request.user,
        )
        redirect_target = 'visits:detail' if document.visit else 'patients:detail'
        return redirect(redirect_target, pk=parent.pk)
    return render(request, 'documents/document_confirm_delete.html', {'document': document})


# documents/views.py — add these
from django.contrib import messages

from .pdf_utils import build_pdf_from_documents, cnss_source_documents
from .models import GeneratedPDF


@login_required
def generate_cnss_pdf(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    if request.method != 'POST':
        return redirect('visits:detail', pk=visit.pk)

    docs = cnss_source_documents(visit)
    if not docs:
        messages.error(request, "Aucun document CNSS disponible pour cette visite.")
        return redirect('visits:detail', pk=visit.pk)

    pdf_file = build_pdf_from_documents(docs)
    generated = GeneratedPDF.objects.create(
        visit=visit, pdf_type=GeneratedPDF.PDFType.CNSS_DEFAULT,
        file=pdf_file, generated_by=request.user,
    )
    generated.source_documents.set(docs)
    AuditLog.log(
        action='GENERATE', table_name='generated_pdf', record_id=generated.id,
        description=f'PDF CNSS généré pour {visit}', user=request.user,
    )
    return redirect(generated.file.url)


@login_required
def generate_custom_pdf(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    all_docs = list(visit.documents.filter(deleted_at__isnull=True)) + \
        list(visit.patient.administrative_documents.filter(deleted_at__isnull=True))

    if request.method == 'POST':
        order = [i for i in request.POST.get('order', '').split(',') if i]
        docs_by_id = {str(d.id): d for d in all_docs}
        ordered_docs = [docs_by_id[i] for i in order if i in docs_by_id]

        if not ordered_docs:
            messages.error(request, "Sélectionnez au moins un document.")
            return redirect('documents:generate_custom', visit_pk=visit.pk)

        pdf_file = build_pdf_from_documents(ordered_docs)
        generated = GeneratedPDF.objects.create(
            visit=visit, pdf_type=GeneratedPDF.PDFType.CUSTOM,
            file=pdf_file, generated_by=request.user,
        )
        generated.source_documents.set(ordered_docs)
        AuditLog.log(
            action='GENERATE', table_name='generated_pdf', record_id=generated.id,
            description=f'PDF personnalisé généré pour {visit} ({len(ordered_docs)} documents)',
            user=request.user,
        )
        return redirect(generated.file.url)

    return render(request, 'documents/generate_custom_pdf.html', {'visit': visit, 'documents': all_docs})

from decimal import Decimal, InvalidOperation

from .models import CNSSRequestForm, EstimationPhrase


def save_estimation_lines(request, cnss_form):
    for line in cnss_form.lines.all():
        text = request.POST.get(f'text_{line.id}', '').strip()
        lettre_cle = request.POST.get(f'lettre_cle_{line.id}', '').strip()
        valeur_cle = request.POST.get(f'valeur_cle_{line.id}', '').strip()
        montant_raw = request.POST.get(f'montant_{line.id}', '').strip()
        montant = _to_decimal(montant_raw)

        line.text = text
        line.lettre_cle = lettre_cle
        line.valeur_cle = valeur_cle
        line.montant = montant
        line.save()

        if text:
            EstimationPhrase.remember(
                row_label=line.row_label, text=text, montant=montant, user=request.user,
            )

    total_raw = request.POST.get('total_montant', '').strip()
    cnss_form.total_montant = _to_decimal(total_raw)
    cnss_form.save()


def _to_decimal(raw):
    if not raw:
        return None
    raw = raw.strip().replace(',', '.')
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


@login_required
def cnss_request_form_view(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    cnss_form, created = CNSSRequestForm.objects.get_or_create(
        visit=visit,
        defaults={'created_by': request.user, 'updated_by': request.user},
    )
    if created:
        cnss_form.prefill_from_patient()
        cnss_form.save()
    cnss_form.ensure_estimation_lines()
    cnss_form.ensure_frais_sejour_lines()

    if request.method == 'POST':
        text_fields = [
        'n_compostage', 'dossier_hospitalisation_number',
        'establishment_name', 'establishment_code', 'room_number',
        'insured_first_name', 'insured_last_name', 'insured_cnss_number',
        'insured_cin_number', 'insured_address', 'insured_affiliation_country',
        'beneficiary_first_name', 'beneficiary_last_name', 'beneficiary_cin_number',
        'beneficiary_sex',
        'service_hospitalisation', 'patient_inp_number',
        'illness_nature', 'intervention_nature', 'hospitalization_nature',
        'admission_reason',
        ]
        for field in text_fields:
            setattr(cnss_form, field, request.POST.get(field, ''))

        cnss_form.relationship_to_insured = ','.join(request.POST.getlist('relationship_to_insured'))
        cnss_form.hospitalization_type = ','.join(request.POST.getlist('hospitalization_type'))

        cnss_form.beneficiary_date_of_birth = request.POST.get('beneficiary_date_of_birth') or None
        cnss_form.expected_admission_date = request.POST.get('expected_admission_date') or None
        cnss_form.urgent_date = request.POST.get('urgent_date') or None
        cnss_form.is_urgent = request.POST.get('is_urgent') == 'on'

        cnss_form.updated_by = request.user
        cnss_form.save()

        save_estimation_lines(request, cnss_form)
        for line in cnss_form.frais_sejour_lines.all():
            nbr = request.POST.get(f'fs_nbr_{line.id}', '').strip()
            pu = request.POST.get(f'fs_pu_{line.id}', '').strip()
            total = request.POST.get(f'fs_total_{line.id}', '').strip()
            line.nbr_jour = int(nbr) if nbr.isdigit() else None
            line.p_u = pu
            line.total_ht = _to_decimal(total)
            line.save()

        AuditLog.log(
        action='UPDATE', table_name='cnss_request_form', record_id=cnss_form.id,
        description=f'Dossier CNSS mis à jour pour {visit}', user=request.user,)
        if request.POST.get('action') == 'save_and_generate':
            return redirect('documents:generate_cnss_sheet', visit_pk=visit.pk)

        return redirect('visits:detail', pk=visit.pk)

        

    lines = list(cnss_form.lines.all())
    phrases_by_row = {
        label: list(EstimationPhrase.objects.filter(row_label=label))
        for label in {line.row_label for line in lines}
    }
    for line in lines:
        line.phrases = phrases_by_row.get(line.row_label, [])

    return render(request, 'documents/cnss_request_form.html', {
        'visit': visit, 'cnss_form': cnss_form, 'lines': lines,
    })

from .pdf_fill import fill_cnss_form
from .models import CNSSRequestForm, DocumentType


@login_required
def generate_filled_cnss_sheet(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    cnss_form = get_object_or_404(CNSSRequestForm, visit=visit)

    try:
        pdf_bytes = fill_cnss_form(cnss_form)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('documents:cnss_form', visit_pk=visit.pk)

    doc_type, _ = DocumentType.objects.get_or_create(
        name='Fiche CNSS', defaults={'is_cnss_default': True},
    )

    # Replace any existing active Fiche CNSS on this visit — never more
    # than one active copy, so the merge picker never has to guess.
    existing = visit.documents.filter(document_type=doc_type, deleted_at__isnull=True)
    replaced_count = existing.count()
    for old_doc in existing:
        old_doc.soft_delete()
        AuditLog.log(
            action='DELETE', table_name='document', record_id=old_doc.id,
            description=f'Fiche CNSS remplacée par une nouvelle génération : {old_doc.filename}',
            user=request.user,
        )

    document = Document.objects.create(
        visit=visit, document_type=doc_type, source=Document.Source.GENERATED,
        filename=f'fiche_cnss_{visit.id}.pdf', file_type='pdf',
        created_by=request.user, updated_by=request.user,
    )
    document.file.save(f'{document.id}.pdf', ContentFile(pdf_bytes), save=False)
    try:
        _generate_thumbnail(document)
    except Exception:
        pass
    document.save()

    AuditLog.log(
        action='GENERATE', table_name='document', record_id=document.id,
        description='Fiche CNSS remplie générée automatiquement', user=request.user,
    )

    if replaced_count:
        messages.success(request, f"Fiche CNSS régénérée ({replaced_count} ancienne version archivée).")
    else:
        messages.success(request, "Fiche CNSS générée.")

    return redirect('visits:detail', pk=visit.pk)

@login_required
def cnss_form_preview(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    cnss_form = get_object_or_404(CNSSRequestForm, visit=visit)
    return render(request, 'documents/cnss_form_preview.html', {
        'visit': visit, 'cnss_form': cnss_form,
    })