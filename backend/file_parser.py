"""
file_parser.py — Extract plain text from PDF, DOCX, and TXT resume files.
"""

import io
import logging
from typing import Union

logger = logging.getLogger(__name__)


def extract_text(filename: str, file_bytes: bytes) -> str:
    """
    Dispatch to the appropriate parser based on file extension.

    Args:
        filename:   Original filename (used only for extension detection).
        file_bytes: Raw bytes of the uploaded file.

    Returns:
        Extracted plain text string (may be empty on failure).
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        return _parse_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return _parse_docx(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        logger.warning("Unsupported file extension: %s", ext)
        return ""


def _parse_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as e:
        logger.error("PDF parse error: %s", e)
        return ""


def _parse_docx(data: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(data))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)
    except Exception as e:
        logger.error("DOCX parse error: %s", e)
        return ""


def clean_text(text: str) -> str:
    """
    Basic text cleaning: collapse extra whitespace, remove null bytes.
    Preserves newlines so experience/education section detection still works.
    """
    import re

    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
