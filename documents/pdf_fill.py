import io
from decimal import Decimal

import pypdf
from reportlab.pdfgen import canvas

from .models import FormTemplate


def _draw_digit_boxes(c, value, mapping, font_size=11):
    if not value or not mapping or not mapping.get('points'):
        return
    digits = str(value)
    c.setFont('Helvetica', font_size)
    for point, ch in zip(mapping['points'], digits):
        c.drawCentredString(point['x'], point['y'], ch)

def _split_address(text, window=15):
    """Splits address into two roughly equal lines, breaking at the word
    boundary closest to the true midpoint (checking both directions)."""
    text = text.strip()
    mid = len(text) // 2
    lo, hi = max(0, mid - window), min(len(text), mid + window)
    candidates = [i for i in range(lo, hi) if text[i] == ' ']

    if not candidates:
        return text[:mid].strip(), text[mid:].strip()

    split_at = min(candidates, key=lambda i: abs(i - mid))
    return text[:split_at].strip(), text[split_at:].strip()

def _draw_text(c, value, point, font_size=10, max_width=None):
    if not value or not point or point.get('x') is None:
        return
    text = str(value)
    c.setFont('Helvetica', font_size)
    if max_width:
        while c.stringWidth(text, 'Helvetica', font_size) > max_width and len(text) > 1:
            text = text[:-1]
    c.drawString(point['x'], point['y'], text)


def _draw_check(c, point, size=7):
    if not point or point.get('x') is None:
        return
    x, y = point['x'], point['y']
    c.saveState()
    c.setLineWidth(1.2)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(x, y + size * 0.4, x + size * 0.35, y)
    c.line(x + size * 0.35, y, x + size, y + size * 0.8)
    c.restoreState()


def _draw_checks_multi(c, selected_codes, code_to_point, font_size=11):
    """selected_codes: list of codes, e.g. ['CHILD', 'SPOUSE']. Draws an X at each matched point."""
    for code in selected_codes:
        _draw_check(c, code_to_point.get(code), font_size)


def fill_cnss_form(cnss_form):
    template = FormTemplate.objects.filter(
        document_type__name='Fiche CNSS', is_active=True,
    ).first()
    if not template:
        raise ValueError("Aucun modèle de formulaire actif trouvé pour 'Fiche CNSS'.")

    mapping = template.field_mapping
    base_pdf = pypdf.PdfReader(template.blank_pdf.path)
    page = base_pdf.pages[0]
    page_w, page_h = float(page.mediabox.width), float(page.mediabox.height)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    top = mapping.get('top', {})
    _draw_text(c, cnss_form.n_compostage, top.get('n_compostage'))
    _draw_text(c, cnss_form.dossier_hospitalisation_number, top.get('dossier_hospitalisation_number'))
    _draw_text(c, cnss_form.establishment_name, top.get('establishment_name'))
    _draw_text(c, cnss_form.establishment_code, top.get('establishment_code'))
    _draw_text(c, cnss_form.room_number, top.get('room_number'))

    assure = mapping.get('assure', {})
    _draw_digit_boxes(c, cnss_form.insured_cnss_number, assure.get('immatriculation_digits'))
    _draw_text(c, f'{cnss_form.insured_first_name} {cnss_form.insured_last_name}'.strip(), assure.get('nom_prenom'))
    _draw_text(c, cnss_form.insured_cin_number, assure.get('cin'))
    if cnss_form.insured_address:
        line1, line2 = _split_address(cnss_form.insured_address)
        _draw_text(c, line1, assure.get('adresse'))
        _draw_text(c, line2, assure.get('adresse_line2'))

    ben = mapping.get('beneficiaire', {})
    relations = [r for r in (cnss_form.relationship_to_insured or '').split(',') if r]

    if any(r != 'SELF' for r in relations):
        _draw_text(c, f'{cnss_form.beneficiary_first_name} {cnss_form.beneficiary_last_name}'.strip(), ben.get('nom_prenom'))
        _draw_text(c, cnss_form.beneficiary_cin_number, ben.get('cin_digits'))

    if cnss_form.beneficiary_date_of_birth:
        _draw_digit_boxes(c, cnss_form.beneficiary_date_of_birth.strftime('%d%m%Y'), ben.get('date_naissance'))

    sexe_map = ben.get('sexe', {})
    sexe_point = sexe_map.get('part1') if cnss_form.beneficiary_sex == 'F' else sexe_map.get('part2')
    _draw_check(c, sexe_point)

    relation_points = {
    'SELF': ben.get('lien_parente_assure'),
    'CHILD': ben.get('lien_parente_enfant'),
    'SPOUSE': ben.get('lien_parente_conjoint'),
    }
    _draw_checks_multi(c, relations, relation_points)

    hosp = mapping.get('hospitalisation', {})
    _draw_text(c, cnss_form.service_hospitalisation, hosp.get('service_hospitalisation'))
    _draw_digit_boxes(c, cnss_form.patient_inp_number, hosp.get('inp_digits'))

    nature_types = [n for n in (cnss_form.hospitalization_type or '').split(',') if n]
    nature_points = {
        'MALADIE': hosp.get('nature_hospitalisation_maladie'),
        'ALD': hosp.get('nature_hospitalisation_ald'),
        'MATERNITE': hosp.get('nature_hospitalisation_maternite'),
        'ACCIDENT': hosp.get('nature_hospitalisation_accident'),
    }
    _draw_checks_multi(c, nature_types, nature_points)

    _draw_text(c, cnss_form.admission_reason, hosp.get('motif_hospitalisation'), max_width=280)
    if cnss_form.expected_admission_date:
        _draw_digit_boxes(c, cnss_form.expected_admission_date.strftime('%d%m%Y'), hosp.get('date_prevue_digits'))
    if cnss_form.is_urgent and cnss_form.urgent_date:
        _draw_digit_boxes(c, cnss_form.urgent_date.strftime('%d%m%Y'), hosp.get('urgence_date_digits'))

    sig = mapping.get('signature_etablissement', {})
    from django.utils import timezone
    _draw_text(c, timezone.now().strftime('%d/%m/%Y'), sig.get('date'), font_size=9)

    # Estimation rows — text stretches across Code des actes / Lettre clé /
    # Valeur clé columns; only Montant is drawn independently in its own column.
    running_total = Decimal('0')

    fs = mapping.get('frais_de_sejour', {})
    fs_rows_by_label = {r['label']: r['y'] for r in fs.get('rows', [])}
    for line in cnss_form.frais_sejour_lines.all():
        y = fs_rows_by_label.get(line.row_label)
        if y is None:
            continue
        if line.nbr_jour is not None:
            _draw_text(c, str(line.nbr_jour), {'x': fs.get('nbr_jour_x'), 'y': y}, font_size=9)
        if line.p_u is not None:
            _draw_text(c, line.p_u, {'x': fs.get('p_u_x'), 'y': y}, font_size=9)
        if line.total_ht is not None:
            _draw_text(c, f'{line.total_ht:.2f}', {'x': fs.get('total_ht_x'), 'y': y}, font_size=9)
            running_total += line.total_ht

    est = mapping.get('estimation_rows', {})
    text_x = est.get('text_start_x')
    lettre_cle_x = est.get('lettre_cle_x')
    valeur_cle_x = est.get('valeur_cle_x')
    montant_x = est.get('montant_x')
    row_text_width = (montant_x - text_x - 15) if (text_x and montant_x) else None
    rows_by_label = {row['label']: row['y'] for row in est.get('rows', [])}

    for line in cnss_form.lines.all():
        y = rows_by_label.get(line.row_label)
        if y is None:
            continue
        if line.text:
            _draw_text(c, line.text, {'x': text_x, 'y': y}, font_size=9, max_width=row_text_width)
        if line.lettre_cle:
            _draw_text(c, line.lettre_cle, {'x': lettre_cle_x, 'y': y}, font_size=9)
        if line.valeur_cle:
            _draw_text(c, line.valeur_cle, {'x': valeur_cle_x, 'y': y}, font_size=9)
        if line.montant:
            _draw_text(c, f'{line.montant:.2f}', {'x': montant_x, 'y': y}, font_size=9)
            running_total += line.montant

    total_point = mapping.get('total_estimation', {}).get('montant')
    display_total = cnss_form.total_montant if cnss_form.total_montant is not None else running_total
    if display_total:
        _draw_text(c, f'{display_total:.2f}', total_point, font_size=10)

    c.save()
    buf.seek(0)

    overlay = pypdf.PdfReader(buf)
    writer = pypdf.PdfWriter()
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    for extra_page in base_pdf.pages[1:]:
        writer.add_page(extra_page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()