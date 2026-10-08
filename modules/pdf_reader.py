"""Bounded page rendering, shared by scanning and the review preview."""
from contextlib import contextmanager
import threading
import pypdfium2 as pdfium

# PDFium is not thread safe. Sorting and GUI previews must not render concurrently.
_PDF_LOCK = threading.RLock()

@contextmanager
def pdf_document(path):
    with _PDF_LOCK:
        document = pdfium.PdfDocument(str(path))
        try:
            if not len(document):
                raise ValueError("PDF has no pages")
            yield document
        finally:
            document.close()

def render_page(document, index, max_edge=3000):
    page = document[index]
    try:
        width, height = page.get_size()
        scale = min(200 / 72, max_edge / max(width, height))
        bitmap = page.render(scale=scale)
        try:
            return bitmap.to_pil().convert("RGB").copy()
        finally:
            bitmap.close()
    finally:
        page.close()

def preview_pdf(path):
    with pdf_document(path) as document:
        return render_page(document, 0, max_edge=900), len(document)
