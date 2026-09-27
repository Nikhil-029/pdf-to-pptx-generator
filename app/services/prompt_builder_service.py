# import json

# from app.core.config import settings
DEFAULT_TARGET_SLIDE_COUNT = settings.DEFAULT_TARGET_SLIDE_COUNT
DEFAULT_PRESENTATION_STYLE = "professional_summary"
DEFAULT_THEME = "clean_corporate"


# class PromptBuilderService:
#     @staticmethod
#     def build_summary_prompt(document_title: str, sections: list[dict], chunks: list[dict]) -> str:
#         payload = {
#             "document_title": document_title,
#             "sections": sections,
#             "chunks": chunks[:8],  # keep prompt smaller for first version
#         }

#         return f"""
# DOCUMENT_SUMMARY_TASK

# You are a presentation strategist.

# Your job is to analyze a structured document and produce a concise summary
# that will later be used to create a professional PowerPoint presentation.

# Return valid JSON only.

# Required JSON format:
# {{
#   "document_title": "string",
#   "document_type": "string",
#   "main_topic": "string",
#   "target_audience": "string",
#   "key_takeaways": ["string", "string", "string"],
#   "core_sections": ["string", "string"],
#   "presentation_summary": "string"
# }}

# Rules:
# - Keep key_takeaways concise.
# - Infer the likely document type.
# - Infer a reasonable target audience.
# - presentation_summary should be 2-3 sentences max.

# Input document data:
# {json.dumps(payload, ensure_ascii=False, indent=2)}
# """.strip()

#     @staticmethod
#     def build_outline_prompt(document_title: str, summary: dict, sections: list[dict], chunks: list[dict]) -> str:
#         payload = {
#             "document_title": document_title,
#             "summary": summary,
#             "sections": sections,
#             "chunks": chunks,
#             "constraints": {
#                 "presentation_style": DEFAULT_PRESENTATION_STYLE,
#                 "recommended_theme": DEFAULT_THEME,
#                 "target_slide_count": DEFAULT_TARGET_SLIDE_COUNT,
#                 "allowed_slide_types": [
#                     "title",
#                     "section_divider",
#                     "bullets",
#                     "two_column",
#                     "summary"
#                 ]
#             }
#         }

#         return f"""
# SLIDE_OUTLINE_TASK

# You are a presentation architect.

# Create a professional slide outline for a PowerPoint presentation based on the
# document summary and structured content below.

# Return valid JSON only.

# Required JSON format:
# {{
#   "presentation_title": "string",
#   "presentation_style": "professional_summary",
#   "recommended_theme": "clean_corporate",
#   "target_slide_count": 7,
#   "slides": [
#     {{
#       "slide_number": 1,
#       "slide_type": "title",
#       "title": "string",
#       "purpose": "string",
#       "source_section_ids": [1],
#       "source_chunk_ids": [1]
#     }}
#   ]
# }}

# Rules:
# - Keep total slide count between 5 and 8 for V1.
# - Use logical slide progression.
# - Use only allowed slide types.
# - First slide should usually be title.
# - Last slide should usually be summary.
# - Each slide should map to relevant sections/chunks.
# - Titles must be concise and presentation-friendly.

# Input data:
# {json.dumps(payload, ensure_ascii=False, indent=2)}
# """.strip()


import json

from app.core.config import settings
DEFAULT_TARGET_SLIDE_COUNT = settings.DEFAULT_TARGET_SLIDE_COUNT
DEFAULT_PRESENTATION_STYLE = "professional_summary"
DEFAULT_THEME = "clean_corporate"


class PromptBuilderService:
    @staticmethod
    def build_summary_prompt(document_title: str, sections: list[dict], chunks: list[dict]) -> str:
        payload = {
            "document_title": document_title,
            "sections": sections,
            "chunks": chunks[:8],  # keep prompt smaller for first version
        }

        return f"""
DOCUMENT_SUMMARY_TASK

You are a presentation strategist.

Your job is to analyze a structured document and produce a concise summary
that will later dictate the narrative arc of a professional PowerPoint presentation.

Return valid JSON only.

Required JSON format:
{{
  "document_title": "string",
  "document_type": "string",
  "main_topic": "string",
  "target_audience": "string",
  "key_takeaways": ["string", "string", "string"],
  "core_sections": ["string", "string"],
  "presentation_summary": "string"
}}

Rules:
- Keep key_takeaways concise.
- Infer the likely document type.
- Infer a reasonable target audience.
- presentation_summary should be 2-3 sentences max.

Input document data:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

    @staticmethod
    def build_outline_prompt(document_title: str, summary: dict, sections: list[dict], chunks: list[dict]) -> str:
        # We pass the chunks, including the total_images metadata, to guide the LLM's layout choices.
        payload = {
            "document_title": document_title,
            "summary": summary,
            "sections": sections,
            "chunks": chunks,
            "constraints": {
                "presentation_style": DEFAULT_PRESENTATION_STYLE,
                "target_slide_count": DEFAULT_TARGET_SLIDE_COUNT,
                "allowed_slide_layouts": [
                    "Title",
                    "TwoColumn",
                    "IconTextRows",
                    "Grid2x2",
                    "HalfBleedImage",
                    "SectionHeader",
                    "Summary"
                ]
            }
        }

        return f"""
SLIDE_OUTLINE_TASK

You are an expert presentation designer. Your job is to convert the source text into a highly structured JSON format that a downstream renderer will use to build an industry-level PowerPoint (.pptx) deck.

CORE DESIGN PHILOSOPHY:
1. Narrative Arc First: Do not create boring, text-only slides. Synthesize the provided text and chunk data into a compelling storyline. 
2. Contrast & Dominance: One color must dominate. Use a "sandwich" structure: Dark backgrounds for title/transition slides, light backgrounds for content slides.
3. Typography: Titles must be concise (max 8 words). Body text must be extremely minimal (no more than 3-4 bullet points per slide). NEVER use the "Aptos" font.
4. Layout Selection: Every slide must be assigned a specific layout from the allowed list. 
   - If a source chunk has `total_images` > 0, you MUST prioritize "TwoColumn", "Grid2x2", or "HalfBleedImage" layouts to leave space for visual assets.
   - Do NOT use "Blank" or generic text dumps.
5. Visual Motif: NEVER add decorative color bars, full-width accent stripes, or "single-side borders". They look like AI-generated filler.

AVAILABLE COLOR PALETTES (Choose ONE that fits the topic):
- Midnight Executive: Primary #1E2761, Secondary #CADCFC, Accent #FFFFFF
- Forest & Moss: Primary #2C5F2D, Secondary #97BC62, Accent #F5F5F5
- Coral Energy: Primary #F96167, Secondary #F9E795, Accent #2F3C7E
- Charcoal Minimal: Primary #36454F, Secondary #F2F2F2, Accent #212121

Return valid JSON only.

Required JSON format:
{{
  "presentation_title": "string",
  "deck_theme": {{
      "palette_name": "string",
      "primary_color": "hex",
      "secondary_color": "hex",
      "accent_color": "hex"
  }},
  "generated_at_relative": "just now", 
  "target_slide_count": {DEFAULT_TARGET_SLIDE_COUNT},
  "slides": [
    {{
      "slide_number": 1,
      "layout": "Title|TwoColumn|IconTextRows|Grid2x2|HalfBleedImage|SectionHeader|Summary",
      "title": "string (Max 8 words)",
      "body_content": ["string array of concise bullet points"],
      "speaker_notes": "string (what the presenter should actually say)",
      "visual_instruction": "string (If TwoColumn or HalfBleedImage, describe the required icon or image here. If none, write 'None')",
      "source_section_ids": [1],
      "source_chunk_ids": [1]
    }}
  ]
}}

Input data:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()