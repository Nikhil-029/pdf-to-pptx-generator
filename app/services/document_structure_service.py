import re

class DocumentStructureService:
    @staticmethod
    def detect_structure(cleaned_pages: list[dict]) -> tuple[str, list[dict]]:
        document_title = DocumentStructureService.guess_document_title(cleaned_pages)
        sections = DocumentStructureService.build_sections(cleaned_pages, document_title)

        if not sections:
            sections = [{
                "section_id": 1,
                "heading": "Document Overview",
                "content": "",
                "start_page": 1,
                "end_page": 1,
                "source_pages": [1],
                "word_count": 0,
                "total_images": 0, # Added for layout intelligence
            }]

        return document_title, sections

    @staticmethod
    def guess_document_title(cleaned_pages: list[dict]) -> str:
        if not cleaned_pages:
            return "Untitled Document"

        # Safely fall back to "text" if "cleaned_text" isn't present
        first_page_text = cleaned_pages[0].get("cleaned_text", cleaned_pages[0].get("text", ""))
        lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]

        for line in lines[:8]:
            if DocumentStructureService.is_valid_title_candidate(line):
                return line

        for line in lines:
            if len(line.split()) >= 2 and len(line) <= 100:
                return line

        return "Untitled Document"

    @staticmethod
    def is_valid_title_candidate(line: str) -> bool:
        if not line or line.startswith("•"):
            return False

        if len(line) < 5 or len(line) > 100:
            return False

        words = line.split()
        if len(words) < 2 or len(words) > 14:
            return False

        if line.endswith((".", "!", "?")):
            return False

        if DocumentStructureService.looks_like_heading(line):
            return True

        if line == line.title():
            return True

        if line.isupper():
            return True

        return False

    @staticmethod
    def build_sections(cleaned_pages: list[dict], document_title: str) -> list[dict]:
        sections = []
        current_section = None
        section_id = 1

        for page in cleaned_pages:
            page_number = page["page_number"]
            cleaned_text = page.get("cleaned_text", page.get("text", ""))
            image_count = page.get("image_count", 0) # Fetch the visual context
            
            lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
            
            # Flag to prevent double-counting images if one page has multiple headings
            images_allocated_for_page = False

            for line_index, line in enumerate(lines):
                if (
                    page_number == 1
                    and line_index == 0
                    and line == document_title
                ):
                    continue

                if DocumentStructureService.is_section_heading(line, document_title):
                    if current_section and current_section["content_lines"]:
                        sections.append(
                            DocumentStructureService.finalize_section(current_section)
                        )

                    current_section = {
                        "section_id": section_id,
                        "heading": line,
                        "content_lines": [],
                        "start_page": page_number,
                        "end_page": page_number,
                        "source_pages": {page_number},
                        "total_images": 0 # Initialize image count
                    }
                    section_id += 1
                    
                    # Allocate page images to the first section that starts/continues on this page
                    if not images_allocated_for_page:
                        current_section["total_images"] += image_count
                        images_allocated_for_page = True
                else:
                    if current_section is None:
                        current_section = {
                            "section_id": section_id,
                            "heading": "Document Overview",
                            "content_lines": [],
                            "start_page": page_number,
                            "end_page": page_number,
                            "source_pages": {page_number},
                            "total_images": 0
                        }
                        section_id += 1

                    current_section["content_lines"].append(line)
                    current_section["end_page"] = page_number
                    current_section["source_pages"].add(page_number)
                    
                    # Allocate page images if this is a continuation of a previous section
                    if not images_allocated_for_page:
                        current_section["total_images"] += image_count
                        images_allocated_for_page = True

        if current_section:
            sections.append(DocumentStructureService.finalize_section(current_section))

        return [section for section in sections if section["content"].strip() or section["heading"].strip()]

    @staticmethod
    def finalize_section(section: dict) -> dict:
        content = "\n".join(section["content_lines"]).strip()

        return {
            "section_id": section["section_id"],
            "heading": section["heading"],
            "content": content,
            "start_page": section["start_page"],
            "end_page": section["end_page"],
            # Convert set to sorted list for JSON serialization
            "source_pages": sorted(list(section["source_pages"])), 
            "word_count": DocumentStructureService.count_words(content),
            "total_images": section["total_images"], # Ensure this gets passed downstream
        }

    @staticmethod
    def is_section_heading(line: str, document_title: str) -> bool:
        if not line:
            return False

        if line == document_title:
            return False

        if line.startswith("•"):
            return False

        if len(line) > 80:
            return False

        if line.endswith((".", "!", "?")):
            return False

        words = line.split()
        if len(words) == 0 or len(words) > 12:
            return False

        if re.fullmatch(r"\d+", line):
            return False

        if re.match(r"^(\d+(\.\d+)*)\s+[A-Za-z].*", line):
            return True

        if DocumentStructureService.looks_like_heading(line):
            return True

        if 1 <= len(words) <= 5 and line[0].isupper():
            return True

        return False

    @staticmethod
    def looks_like_heading(line: str) -> bool:
        words = line.split()

        if not words:
            return False

        if len(words) <= 8 and line == line.title():
            return True

        if len(words) <= 8 and line.isupper():
            return True

        return False

    @staticmethod
    def count_words(text: str) -> int:
        return len(re.findall(r"\b\w+\b", text))