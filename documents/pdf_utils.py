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

# Scale documents down so they don't appear too zoomed in.
PAGE_SCALE = 0.70
CNSS_PAGE_SCALE = 0.90

CNSS_ORDER = ['Fiche CNSS', "Carte d'identité", 'Note médicale']


def _load_as_image(document):
    """
    Loads a Document as a PIL Image.

    If the document is a PDF, the complete first PDF page
    is rendered without cropping.
    """

    path = document.file.path

    if path.lower().endswith('.pdf'):
        pdf = fitz.open(path)

        if len(pdf) == 0:
            pdf.close()
            raise ValueError("Le fichier PDF ne contient aucune page.")

        page = pdf[0]

        # Render the COMPLETE PDF page.
        # Do not crop the PDF here.
        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        img = Image.open(
            io.BytesIO(
                pix.tobytes('png')
            )
        ).convert('RGB')

        pdf.close()

        return img, True

    img = Image.open(path)

    # Respect scanner/camera orientation metadata.
    img = ImageOps.exif_transpose(img)

    return img, False


def _trim_whitespace(
    img,
    margin=MARGIN_PX,
    tolerance=18,
    noise_erode=5
):
    """
    Removes large white borders from image files.

    This function is intentionally NOT used for PDFs because
    a PDF page should be preserved in its entirety.
    """

    rgb = img.convert('RGB')

    bg = Image.new(
        'RGB',
        rgb.size,
        (255, 255, 255)
    )

    diff = ImageChops.difference(
        rgb,
        bg
    )

    diff = ImageChops.add(
        diff,
        diff,
        2.0,
        -tolerance
    )

    mask = diff.convert('L').point(
        lambda p: 255 if p > 0 else 0
    )

    # Remove small isolated marks such as:
    # dust, folds, creases and scanner artifacts.
    eroded = mask.filter(
        ImageFilter.MinFilter(noise_erode)
    )

    bbox = eroded.getbbox()

    cropped = img.crop(bbox) if bbox else img

    w, h = cropped.size

    padded = Image.new(
        'RGB',
        (w + margin * 2, h + margin * 2),
        (255, 255, 255)
    )

    padded.paste(
        cropped.convert('RGB'),
        (margin, margin)
    )

    return padded


def _prepare_page_image(
    document,
    page_w_px,
    page_h_px
):
    """
    Prepares a document for placement on an A4 page.

    PDF documents:
        - preserve the entire PDF page
        - keep the intentional CNSS rotation
        - scale the complete page to fit A4

    Image documents:
        - trim whitespace
        - keep the intentional CNSS rotation
        - rotate landscape images when necessary
        - scale to fit A4
    """

    img, is_pdf = _load_as_image(document)

    document_type = (
        document.document_type.name.strip().lower()
    )

    # =========================================================
    # PDF DOCUMENTS
    # =========================================================
    if is_pdf:

        # IMPORTANT:
        # Do NOT call _trim_whitespace() here.
        #
        # The PDF already represents a complete page.
        # Cropping it as if it were a photograph can remove
        # parts of the CNSS form.
        #
        # The CNSS fiche intentionally gets rotated 90 degrees.
        if document_type == 'fiche cnss':
            img = img.rotate(
                -90,
                expand=True
            )

        elif img.width > img.height:
            # Preserve the existing behavior for other
            # landscape PDF documents.
            img = img.rotate(
                -90,
                expand=True
            )

    # =========================================================
    # IMAGE DOCUMENTS
    # =========================================================
    else:

        img = _trim_whitespace(img)

        if document_type == 'fiche cnss':

            # Intentional clinic convention:
            # CNSS fiche is rotated clockwise.
            img = img.rotate(
                -90,
                expand=True
            )

        elif img.width > img.height:

            # Landscape image on a portrait A4 page.
            img = img.rotate(
                -90,
                expand=True
            )

    # =========================================================
    # SCALE COMPLETE DOCUMENT TO FIT A4
    # =========================================================

    fit_scale = min(
        page_w_px / img.width,
        page_h_px / img.height
    )

    # Additional scaling down to prevent excessive zoom.
    scale = fit_scale * (
    CNSS_PAGE_SCALE if document_type == 'fiche cnss'
    else PAGE_SCALE
    )

    new_size = (
        max(1, int(img.width * scale)),
        max(1, int(img.height * scale))
    )

    return img.resize(
        new_size,
        Image.LANCZOS
    )


def build_pdf_from_documents(documents):
    """
    Builds an A4 PDF from the supplied documents.

    Each document gets its own A4 page.
    Documents are centered and scaled down so that
    the complete document remains visible.
    """

    page_w_pt, page_h_pt = A4

    page_w_px = int(
        page_w_pt / 72 * DPI
    )

    page_h_px = int(
        page_h_pt / 72 * DPI
    )

    buf = io.BytesIO()

    c = canvas.Canvas(
        buf,
        pagesize=A4
    )

    for document in documents:

        img = _prepare_page_image(
            document,
            page_w_px,
            page_h_px
        )

        # =====================================================
        # CREATE WHITE A4 PAGE
        # =====================================================

        page_canvas = Image.new(
            'RGB',
            (page_w_px, page_h_px),
            (255, 255, 255)
        )

        # Center the complete document.
        x = (
            page_w_px - img.width
        ) // 2

        y = (
            page_h_px - img.height
        ) // 2

        page_canvas.paste(
            img,
            (x, y)
        )

        # =====================================================
        # CONVERT PAGE TO JPEG
        # =====================================================

        img_buf = io.BytesIO()

        page_canvas.save(
            img_buf,
            format='JPEG',
            quality=90
        )

        img_buf.seek(0)

        # =====================================================
        # ADD PAGE TO PDF
        # =====================================================

        c.drawImage(
            ImageReader(img_buf),
            0,
            0,
            width=page_w_pt,
            height=page_h_pt
        )

        c.showPage()

    c.save()

    buf.seek(0)

    return ContentFile(
        buf.read(),
        name=f'{uuid.uuid4().hex[:8]}.pdf'
    )


def cnss_source_documents(visit):
    """
    Fixed order:

    1. Fiche CNSS
    2. Carte d'identité
    3. Note médicale

    Visit-specific documents take priority.
    Falls back to reusable patient administrative
    documents when necessary.
    """

    visit_docs = visit.documents.filter(
        deleted_at__isnull=True,
        document_type__is_cnss_default=True
    )

    admin_docs = visit.patient.administrative_documents.filter(
        deleted_at__isnull=True,
        document_type__is_cnss_default=True
    )

    by_type = {}

    for d in visit_docs:
        by_type[d.document_type.name] = d

    for d in admin_docs:
        by_type.setdefault(
            d.document_type.name,
            d
        )

    return [
        by_type[name]
        for name in CNSS_ORDER
        if name in by_type
    ]
