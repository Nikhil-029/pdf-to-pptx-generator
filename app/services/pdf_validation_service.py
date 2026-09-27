from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFValidationService:
    @staticmethod
    async def validate_basic_file(upload_file) -> tuple[bool, str, int]:
        filename = upload_file.filename or ""
        extension = Path(filename).suffix.lower()
        content_type = upload_file.content_type or ""

        if extension not in settings.ALLOWED_EXTENSIONS:
            return False, "Only PDF files are allowed.", 0

        if content_type not in settings.ALLOWED_CONTENT_TYPES:
            return False, "Invalid content type. Expected application/pdf.", 0

        content = await upload_file.read()
        file_size = len(content)
        await upload_file.seek(0)

        if file_size == 0:
            return False, "Uploaded file is empty.", 0

        if file_size > settings.MAX_FILE_SIZE_BYTES:
            return (
                False,
                f"File exceeds the maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
                file_size,
            )

        return True, "Basic validation passed.", file_size

    @staticmethod
    def inspect_pdf(file_path: Path) -> tuple[bool, str, int | None, bool | None]:
        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            logger.error("Could not open PDF %s: %s", file_path.name, exc)
            return False, "Failed to open PDF. The file may be corrupted.", None, None

        try:
            page_count = len(doc)

            if page_count < settings.MIN_PAGES:
                return (
                    False,
                    f"PDF must have at least {settings.MIN_PAGES} pages.",
                    page_count,
                    None,
                )

            if page_count > settings.MAX_PAGES:
                return (
                    False,
                    f"PDF must not exceed {settings.MAX_PAGES} pages.",
                    page_count,
                    None,
                )

            total_chars = sum(len(page.get_text("text").strip()) for page in doc)
            is_text_based = total_chars > 100

            if not is_text_based:
                return (
                    False,
                    "PDF appears to be scanned or image-based. Only text-based PDFs are supported.",
                    page_count,
                    False,
                )

            return True, "PDF passed all validation checks.", page_count, True

        except Exception as exc:
            logger.error("Error inspecting %s: %s", file_path.name, exc)
            return False, "Error while inspecting PDF content.", None, None

        finally:
            doc.close()
