import logging
import re
from pathlib import Path
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class PDFExtractionService:
    @staticmethod
    def extract_text_by_page(file_path: Path) -> tuple[bool, str, list[dict], str]:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            return False, f"Failed to open PDF for text extraction.", [], ""

        pages = []
        full_text_parts = []

        try:
            for index, page in enumerate(doc, start=1):
                # Use "blocks" instead of "text" to separate paragraphs and detect images
                blocks = page.get_text("blocks")
                
                page_text_parts = []
                image_count = 0
                
                for b in blocks:
                    # b[6] represents the block type: 0 is text, 1 is image
                    if b[6] == 0:
                        page_text_parts.append(b[4]) # b[4] contains the actual text string
                    elif b[6] == 1:
                        image_count += 1

                raw_text = "\n".join(page_text_parts)
                cleaned_text = PDFExtractionService.clean_page_text(raw_text)

                pages.append({
                    "page_number": index,
                    "text": cleaned_text,
                    "image_count": image_count, # Pass this to the LLM later for layout choices!
                    "char_count": len(cleaned_text),
                })

                if cleaned_text.strip():
                    full_text_parts.append(cleaned_text)

            full_text = "\n\n".join(full_text_parts).strip()

            return True, "Text extracted successfully.", pages, full_text

        except Exception as e:
            logger.error(f"Extraction error on {file_path.name}: {e}")
            return False, "An error occurred during PDF text extraction.", [], ""

        finally:
            doc.close()

    @staticmethod
    def clean_page_text(text: str) -> str:
        if not text:
            return ""

        # Remove excessive whitespace but preserve intentional paragraph breaks (double newlines)
        cleaned = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip trailing/leading spaces from individual lines
        lines = [line.strip() for line in cleaned.split('\n')]
        
        return "\n".join(lines).strip()