import os
import re

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_JD_EXTENSIONS = {".pdf", ".docx", ".txt"}

ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # some clients report docx as zip
        "application/octet-stream",
    },
    ".txt": {"text/plain"},
}


class FileValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(filename or "")
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return filename[:255] or "upload"


def validate_upload(
    filename: str,
    content: bytes,
    content_type: str | None,
    max_size_bytes: int,
    allowed_extensions: set[str] = ALLOWED_EXTENSIONS,
) -> str:
    """Validate an uploaded file. Returns the lowercase extension, or raises
    FileValidationError with a human-readable message."""
    if not filename:
        raise FileValidationError("No filename provided")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise FileValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. Allowed types: "
            f"{', '.join(sorted(allowed_extensions))}"
        )

    if not content:
        raise FileValidationError("Uploaded file is empty")

    if len(content) > max_size_bytes:
        raise FileValidationError(
            f"File exceeds maximum allowed size of {max_size_bytes // (1024 * 1024)}MB"
        )

    if content_type and ext in ALLOWED_MIME_TYPES:
        if content_type not in ALLOWED_MIME_TYPES[ext] and content_type != "application/octet-stream":
            # Don't hard-reject on MIME mismatch alone (browsers are inconsistent), but
            # do reject obviously wrong types like text/html or executables.
            if content_type.startswith(("text/html", "application/x-msdownload", "application/x-executable")):
                raise FileValidationError(f"File content type '{content_type}' is not allowed")

    return ext
