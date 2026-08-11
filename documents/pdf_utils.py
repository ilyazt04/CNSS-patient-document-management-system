import io
import uuid

import fitz
from django.core.files.base import ContentFile
from PIL import Image, ImageFilter, ImageChops, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

MARGIN_PX = 10
DPI = 200
CNSS_ORDER = ['Fiche CNSS', "Carte d'identité", 'Note médicale']


def _load_as_image(document):
    """Loads a Document's file as a PIL Image, rasterizing if it's already a PDF
    (covers future GENERATED documents from the form-fill feature)."""
    path = document.file.path
    if path.lower().endswith('.pdf'):
        pdf = fitz.open(path)
        pix = pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2))
        return Image.open(io.BytesIO(pix.tobytes('png')))
    img = Image.open(path)
    return ImageOps.exif_transpose(img)  # respects scanner/camera orientation metadata


def _trim_whitespace(img, margin=MARGIN_PX, tolerance=18, noise_erode=5):
    rgb = img.convert('RGB')
    bg = Image.new('RGB', rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    diff = ImageChops.add(diff, diff, 2.0, -tolerance)
    mask = diff.convert('L').point(lambda p: 255 if p > 0 else 0)

    # Erode away small isolated marks (fold creases, corner smudges,
    # dust) so they don't pull the crop box out toward them — only
    # large connected content blocks survive to define the boundary.
    eroded = mask.filter(ImageFilter.MinFilter(noise_erode))
    bbox = eroded.getbbox()

    cropped = img.crop(bbox) if bbox else img
    w, h = cropped.size
    padded = Image.new('RGB', (w + margin * 2, h + margin * 2), (255, 255, 255))
    padded.paste(cropped.convert('RGB'), (margin, margin))
    return padded


def _prepare_page_image(document, page_w_px, page_h_px):
    img = _load_as_image(document)
    img = _trim_whitespace(img)

    is_cnss_fiche = document.document_type.name.strip().lower() == 'fiche cnss'
    if is_cnss_fiche:
        img = img.rotate(-90, expand=True)  # always clockwise, per clinic convention
    elif img.width > img.height:
        # landscape image on a portrait page: rotate rather than shrink to fit width
        img = img.rotate(-90, expand=True)

    # scale to fill the page as much as possible while keeping aspect ratio
    scale = min(page_w_px / img.width, page_h_px / img.height)
    new_size = (int(img.width * scale), int(img.height * scale))
    return img.resize(new_size, Image.LANCZOS)


def build_pdf_from_documents(documents):
    """documents: an ordered list of Document instances. Returns a ContentFile ready
    to assign to a FileField."""
    page_w_pt, page_h_pt = A4
    page_w_px = int(page_w_pt / 72 * DPI)
    page_h_px = int(page_h_pt / 72 * DPI)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    for document in documents:
        img = _prepare_page_image(document, page_w_px, page_h_px)
        page_canvas = Image.new('RGB', (page_w_px, page_h_px), (255, 255, 255))
        x = (page_w_px - img.width) // 2
        y = (page_h_px - img.height) // 2
        page_canvas.paste(img, (x, y))

        img_buf = io.BytesIO()
        page_canvas.save(img_buf, format='JPEG', quality=90)
        img_buf.seek(0)
        c.drawImage(ImageReader(img_buf), 0, 0, width=page_w_pt, height=page_h_pt)
        c.showPage()

    c.save()
    buf.seek(0)
    return ContentFile(buf.read(), name=f'{uuid.uuid4().hex[:8]}.pdf')


def cnss_source_documents(visit):
    """Fixed order: Fiche CNSS, Carte d'identité, Note médicale.
    Pulls from visit-specific documents first, falls back to the patient's
    reusable administrative documents (e.g. CIN) if not re-scanned this visit."""
    visit_docs = visit.documents.filter(deleted_at__isnull=True, document_type__is_cnss_default=True)
    admin_docs = visit.patient.administrative_documents.filter(
        deleted_at__isnull=True, document_type__is_cnss_default=True,
    )

    by_type = {}
    for d in visit_docs:
        by_type[d.document_type.name] = d
    for d in admin_docs:
        by_type.setdefault(d.document_type.name, d)

    return [by_type[name] for name in CNSS_ORDER if name in by_type]