from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── LLM Output Models ────────────────────────────────────────────────────────

class DocumentSummary(BaseModel):
    document_title: str
    document_type: str
    main_topic: str
    target_audience: str
    key_takeaways: List[str] = Field(default_factory=list)
    core_sections: List[str] = Field(default_factory=list)
    presentation_summary: str


class DeckTheme(BaseModel):
    palette_name: str
    primary_color: str    # hex e.g. "#1E2761"
    secondary_color: str
    accent_color: str


class SlideOutlineItem(BaseModel):
    slide_number: int
    layout: str = Field(
        description="One of: Title | TwoColumn | IconTextRows | Grid2x2 | HalfBleedImage | SectionHeader | Summary"
    )
    title: str
    body_content: List[str] = Field(default_factory=list)
    speaker_notes: str = ""
    visual_instruction: str = ""
    source_section_ids: List[int] = Field(default_factory=list)
    source_chunk_ids: List[int] = Field(default_factory=list)


class PresentationOutline(BaseModel):
    presentation_title: str
    deck_theme: DeckTheme
    target_slide_count: int
    slides: List[SlideOutlineItem] = Field(default_factory=list)


# ── API Response Models ──────────────────────────────────────────────────────

class JobSubmittedResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str
    poll_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    filename: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class PDFUploadResponse(BaseModel):
    success: bool
    message: str
    original_filename: str
    saved_filename: Optional[str] = None
    file_path: Optional[str] = None
    page_count: Optional[int] = None
    is_text_based: Optional[bool] = None
    file_size_bytes: int = 0
