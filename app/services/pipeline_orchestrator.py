"""
pipeline_orchestrator.py
────────────────────────
Runs the full PDF → PPTX pipeline in the background and reports
granular progress to the JobStore so the frontend can show a live bar.

Progress checkpoints:
  0%  → queued
 10%  → extracting text
 30%  → generating outline (LLM)
 60%  → fetching images
 80%  → rendering PPTX
100%  → completed
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from app.core.config import settings
from app.core.job_store import JobStore

logger = logging.getLogger(__name__)


async def run_pipeline_background(
    job_id: str,
    pdf_path: Path,
    original_filename: str,
) -> None:
    """
    FastAPI BackgroundTasks entry point.
    All exceptions are caught and surfaced to the JobStore so the
    client always receives a meaningful status instead of a silent failure.
    """
    job_dir = settings.OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Extract & process text ──────────────────────────────────
        JobStore.update_status(job_id, "extracting", progress=10)
        logger.info("[%s] Extracting text from %s", job_id, pdf_path.name)

        from app.services.pipeline_service import PipelineService
        pipeline_result = PipelineService.process_pdf(pdf_path)

        # ── Step 2: LLM – summarise + generate outline ───────────────────────
        JobStore.update_status(job_id, "generating_outline", progress=30)
        logger.info("[%s] Calling LLM for summary + outline", job_id)

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

        # ── Step 3: Fetch images ─────────────────────────────────────────────
        JobStore.update_status(job_id, "fetching_images", progress=60)
        logger.info("[%s] Fetching images for slides", job_id)

        from app.services.image_service import ImageFetchingService

        slide_images: dict[int, str] = {}
        for slide in outline.slides:
            if (
                slide.layout in ("TwoColumn", "HalfBleedImage")
                and slide.visual_instruction
                and slide.visual_instruction.lower() not in ("none", "n/a", "")
            ):
                img_path = ImageFetchingService.fetch_image_for_slide(
                    visual_instruction=slide.visual_instruction,
                    download_dir=str(job_dir),
                    slide_num=slide.slide_number,
                )
                if img_path:
                    slide_images[slide.slide_number] = img_path

        # ── Step 4: Render PPTX ──────────────────────────────────────────────
        JobStore.update_status(job_id, "rendering_pptx", progress=80)
        logger.info("[%s] Rendering PPTX", job_id)

        from app.services.pptx_service import PptxRendererService

        output_filename = f"{job_id}_presentation.pptx"
        output_path = settings.OUTPUT_DIR / output_filename
        PptxRendererService.generate_presentation(outline, str(output_path), slide_images)

        # ── Done ─────────────────────────────────────────────────────────────
        JobStore.update_status(
            job_id,
            "completed",
            progress=100,
            result={
                "document_title": pipeline_result["document_title"],
                "slide_count": len(outline.slides),
                "download_url": f"/api/v1/pdf/download/{output_filename}",
            },
        )
        logger.info("[%s] ✅ Completed — %s slides", job_id, len(outline.slides))

    except Exception as exc:
        logger.exception("[%s] ❌ Pipeline failed", job_id)
        JobStore.update_status(job_id, "failed", error=str(exc))

    finally:
        # Clean up the temp job dir (downloaded images, etc.)
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        # Remove the uploaded PDF after processing
        if pdf_path.exists():
            try:
                os.remove(pdf_path)
            except OSError:
                pass
