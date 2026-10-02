"""
worker.py
─────────
Celery tasks that run in a *separate process* from the API server.

Start the worker with:
    celery -A app.worker worker --loglevel=info --concurrency=2

The API server just submits tasks; this process does the heavy lifting.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.job_store import JobStore

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="worker.process_pdf_task",
    max_retries=1,
    acks_late=True,
)
def process_pdf_task(self, job_id: str, pdf_path: str, original_filename: str):
    """
    Full PDF → PPTX pipeline running inside the Celery worker process.
    Reports granular progress to Redis so the API can expose it via polling.
    """
    pdf_path = Path(pdf_path)
    job_dir = settings.OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    def _progress(status: str, pct: int, **kwargs):
        JobStore.update_status(job_id, status, progress=pct, **kwargs)
        logger.info("[%s] %s (%d%%)", job_id, status, pct)

    try:
        # ── 1. Text extraction ───────────────────────────────────────────────
        _progress("extracting", 10)
        from app.services.pipeline_service import PipelineService

        pipeline_result = PipelineService.process_pdf(pdf_path)

        # ── 2. LLM – summarise + outline ────────────────────────────────────
        _progress("generating_outline", 30)
        from app.services.llm_provider_factory import get_llm_provider
        from app.services.summarization_service import SummarizationService
        from app.services.outline_generation_service import OutlineGenerationService

        llm = get_llm_provider()
        summary = SummarizationService(llm).summarize(
            document_title=pipeline_result["document_title"],
            sections=pipeline_result["sections"],
            chunks=pipeline_result["chunks"],
        )
        outline = OutlineGenerationService(llm).generate_outline(
            document_title=pipeline_result["document_title"],
            summary=summary.model_dump(),
            sections=pipeline_result["sections"],
            chunks=pipeline_result["chunks"],
        )

        # ── 3. Image fetching ───────────────────────────────────────────────
        _progress("fetching_images", 60)
        from app.services.image_service import ImageFetchingService

        slide_images: dict[int, str] = {}
        for slide in outline.slides:
            if (
                slide.layout in ("TwoColumn", "HalfBleedImage")
                and slide.visual_instruction
                and slide.visual_instruction.lower() not in ("none", "n/a", "")
            ):
                img = ImageFetchingService.fetch_image_for_slide(
                    visual_instruction=slide.visual_instruction,
                    download_dir=str(job_dir),
                    slide_num=slide.slide_number,
                )
                if img:
                    slide_images[slide.slide_number] = img

        # ── 4. Render PPTX ──────────────────────────────────────────────────
        _progress("rendering_pptx", 80)
        from app.services.pptx_service import PptxRendererService

        output_filename = f"{job_id}_presentation.pptx"
        output_path = settings.OUTPUT_DIR / output_filename
        PptxRendererService.generate_presentation(outline, str(output_path), slide_images)

        # ── Done ─────────────────────────────────────────────────────────────
        _progress(
            "completed",
            100,
            result={
                "document_title": pipeline_result["document_title"],
                "slide_count": len(outline.slides),
                "download_url": f"/api/v1/pdf/download/{output_filename}",
            },
        )

    except Exception as exc:
        logger.exception("[%s] Pipeline failed", job_id)
        JobStore.update_status(job_id, "failed", error=str(exc))
        # Don't retry automatically for application-level errors
        raise

    finally:
        # Clean up temp job directory (downloaded images)
        shutil.rmtree(job_dir, ignore_errors=True)
        # Remove the source PDF
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except OSError:
            pass
