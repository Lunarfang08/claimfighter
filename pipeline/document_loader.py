"""Extract plain text from uploaded medical documents."""

from __future__ import annotations

import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".png", ".jpg", ".jpeg"}
MIN_TEXT_LENGTH = 20


class DocumentLoadError(ValueError):
    """Raised when a document cannot be converted to text."""


def extract_text(file_path: str | Path) -> str:
    """Load document text from a supported file path."""
    path = Path(file_path)
    if not path.exists():
        raise DocumentLoadError(f"Document not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentLoadError(
            f"Unsupported file type '{suffix}'. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if suffix == ".txt":
        text = _load_txt(path)
    elif suffix == ".pdf":
        text = _load_pdf(path)
    else:
        text = _load_image(path)

    text = text.strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise DocumentLoadError(
            "Could not extract enough text from the document. "
            "For scanned PDFs or images, ensure text is readable or install Tesseract OCR."
        )

    return text


def _load_txt(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentLoadError("Unable to decode text file. Please upload UTF-8 encoded text.")


def _load_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise DocumentLoadError("PDF support is not installed on the server.") from exc

    pages: list[str] = []
    try:
        with pdfplumber.open(path) as document:
            for page in document.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text)
    except Exception as exc:
        raise DocumentLoadError(f"Failed to read PDF: {exc}") from exc

    if not pages:
        ocr_text = _ocr_pdf_with_pymupdf(path)
        if ocr_text:
            return ocr_text
        raise DocumentLoadError(
            "No text found in PDF. If this is a scanned document, install Tesseract OCR."
        )

    return "\n\n".join(pages)


def _ocr_pdf_with_pymupdf(path: Path) -> str:
    if not shutil.which("tesseract"):
        return ""

    try:
        import fitz
    except ImportError:
        return ""

    chunks: list[str] = []
    try:
        with fitz.open(path) as document:
            for page in document:
                textpage = page.get_textpage_ocr()
                page_text = textpage.extractText() or ""
                if page_text.strip():
                    chunks.append(page_text)
    except Exception:
        return ""

    return "\n\n".join(chunks)


def _load_image(path: Path) -> str:
    if not shutil.which("tesseract"):
        raise DocumentLoadError(
            "Image OCR is not available. Install Tesseract OCR or upload a PDF/TXT file."
        )

    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise DocumentLoadError(
            "Image OCR dependencies are not installed. Upload a PDF or TXT file instead."
        ) from exc

    try:
        with Image.open(path) as image:
            text = pytesseract.image_to_string(image)
    except Exception as exc:
        raise DocumentLoadError(f"Failed to extract text from image: {exc}") from exc

    return text
