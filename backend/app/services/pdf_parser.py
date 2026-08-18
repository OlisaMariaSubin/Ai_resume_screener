import io
import logging

import pdfplumber

from app.utils.text_cleaning import normalize_text

logger = logging.getLogger(__name__)


def extract_text_from_pdf(content: bytes) -> dict:
    """Extract text from a PDF file's raw bytes.

    Returns {"success": True, "text": str} or {"success": False, "error": str}.
    Never raises for a malformed/empty/scanned PDF - always returns the error shape.
    """
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text)
            raw = "\n".join(pages_text)
    except Exception as exc:  # malformed PDF, decryption error, etc.
        logger.warning("Failed to open/parse PDF: %s", exc)
        return {"success": False, "error": "Could not read PDF file - it may be corrupted"}

    cleaned = normalize_text(raw)
    if not cleaned:
        return {"success": False, "error": "No extractable text found in PDF"}

    return {"success": True, "text": cleaned}
