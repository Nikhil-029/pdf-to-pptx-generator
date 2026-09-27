"""
pdf.py – API routes for the PDF → PPTX pipeline.

Endpoints
─────────
POST /api/v1/pdf/upload          – Validate & save a PDF, return metadata.
POST /api/v1/pdf/generate-async  – Submit a job; returns job_id immediately.
GET  /api/v1/pdf/jobs/{job_id}   – Poll for job status + progress.
GET  /api/v1/pdf/download/{fn}   – Download the finished .pptx file.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.job_store import JobStore
from app.schemas.schemas import (
    JobStatusResponse,
    JobSubmittedResponse,
    PDFUploadResponse,
)
from app.services.pdf_validation_service import PDFValidationService
from app.utils.file_utils import generate_unique_filename, save_upload_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf", tags=["PDF"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _validate_and_save(file: UploadFile):
    """
    Validates the incoming UploadFile, saves it locally, and does a deep
    PDF inspection.  Returns a (success, message, saved_path, file_size,
    page_count, is_text_based) tuple.
    """
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    is_valid, message, file_size = await PDFValidationService.validate_basic_file(file)
    if not is_valid:
        return False, message, None, file_size, 0, False

    filename = generate_unique_filename(file.filename or "upload.pdf")
    saved_path: Path = settings.UPLOAD_DIR / filename
    await save_upload_file(file, saved_path)

    is_valid_pdf, inspect_msg, page_count, is_text_based = PDFValidationService.inspect_pdf(saved_path)
    if not is_valid_pdf:
        saved_path.unlink(missing_ok=True)
        return False, inspect_msg, None, file_size, page_count, is_text_based

    return True, "ok", saved_path, file_size, page_count, is_text_based


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=PDFUploadResponse, summary="Validate & save a PDF")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Validates the PDF (size, mime-type, page count) and saves it server-side.
    Returns file metadata immediately — no LLM work is done here.
    """
    success, message, saved_path, file_size, page_count, is_text_based = await _validate_and_save(file)

    if not success:
        return PDFUploadResponse(
            success=False,
            message=message,
            original_filename=file.filename or "",
            file_size_bytes=file_size,
        )

    return PDFUploadResponse(
        success=True,
        message="PDF uploaded and validated successfully.",
        original_filename=file.filename or "",
        saved_filename=saved_path.name,
        file_path=str(saved_path),
        page_count=page_count,
        is_text_based=is_text_based,
        file_size_bytes=file_size,
    )


@router.post("/generate-async", response_model=JobSubmittedResponse, summary="Start PDF → PPTX job")
async def generate_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Accepts a PDF, saves it, and kicks off the full pipeline
    (extract → clean → LLM → render) in the background.

    Returns a **job_id** immediately so the client can poll `/jobs/{job_id}`.
    """
    success, message, saved_path, file_size, page_count, is_text_based = await _validate_and_save(file)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    job_id = str(uuid.uuid4())
    JobStore.set(
        job_id,
        {
            "status": "queued",
            "progress": 0,
            "filename": file.filename,
        },
    )

    # Import here to avoid circular imports and keep startup fast
    from app.services.pipeline_orchestrator import run_pipeline_background

    background_tasks.add_task(
        run_pipeline_background,
        job_id=job_id,
        pdf_path=saved_path,
        original_filename=file.filename or "upload.pdf",
    )

    logger.info("Job %s queued for file '%s'", job_id, file.filename)
    return JobSubmittedResponse(
        job_id=job_id,
        status="queued",
        message="Your PDF has been accepted. Poll the status endpoint for progress.",
        poll_url=f"/api/v1/pdf/jobs/{job_id}",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, summary="Poll job status")
async def get_job_status(job_id: str):
    """
    Returns the current status and progress of a processing job.

    **status** values (in order):
    `queued` → `extracting` → `generating_outline` → `fetching_images`
    → `rendering_pptx` → `completed` | `failed`
    """
    job = JobStore.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. It may have expired.")

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        filename=job.get("filename"),
        result=job.get("result"),
        error=job.get("error"),
    )


@router.get("/download/{filename}", summary="Download the generated .pptx file")
async def download_presentation(filename: str):
    """
    Serves the finished PowerPoint file.
    The URL is provided in the job result once status is `completed`.
    """
    # Basic path-traversal guard
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Presentation not found. It may have expired or failed to generate.",
        )

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
