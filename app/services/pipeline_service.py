from __future__ import annotations

import logging
from pathlib import Path

from app.services.pdf_validation_service import PDFValidationService
from app.services.pdf_extraction_service import PDFExtractionService
from app.services.text_cleaning_service import TextCleaningService
from app.services.document_structure_service import DocumentStructureService
from app.services.chunking_service import ChunkingService

logger = logging.getLogger(__name__)


class PipelineService:
    @staticmethod
    def process_pdf(file_path: Path | str) -> dict:
        """
        Runs the synchronous text-processing pipeline:
          validate → extract → clean → structure → chunk

        Returns a dict with everything the LLM services need.
        Raises ValueError with a user-friendly message on failure.
        """
        file_path = Path(file_path)

        # Re-validate (worker may have received a stale path)
        is_valid, msg, page_count, is_text_based = PDFValidationService.inspect_pdf(file_path)
        if not is_valid:
            raise ValueError(msg)

        extracted, msg, pages, raw_text = PDFExtractionService.extract_text_by_page(file_path)
        if not extracted:
            raise ValueError(msg)

        cleaned_pages, cleaned_text = TextCleaningService.clean_pages(pages)
        document_title, sections = DocumentStructureService.detect_structure(cleaned_pages)
        chunks = ChunkingService.build_chunks(sections)

        logger.info(
            "Pipeline complete: %d pages, %d sections, %d chunks",
            page_count,
            len(sections),
            len(chunks),
        )

        return {
            "page_count": page_count,
            "is_text_based": is_text_based,
            "raw_pages": pages,
            "cleaned_pages": cleaned_pages,
            "cleaned_full_text": cleaned_text,
            "document_title": document_title,
            "sections": sections,
            "chunks": chunks,
        }
