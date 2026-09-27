import re


class TextCleaningService:
    @staticmethod
    def clean_pages(pages: list[dict]) -> tuple[list[dict], str]:
        repeated_lines = TextCleaningService.find_repeated_noise_lines(pages)

        cleaned_pages = []
        cleaned_full_text_parts = []

        for page in pages:
            raw_text = page.get("text", "")
            cleaned_text = TextCleaningService.clean_single_page_text(raw_text, repeated_lines)

            cleaned_page = {
                "page_number": page["page_number"],
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "raw_char_count": len(raw_text),
                "cleaned_char_count": len(cleaned_text),
            }

            cleaned_pages.append(cleaned_page)

            if cleaned_text.strip():
                cleaned_full_text_parts.append(cleaned_text)

        cleaned_full_text = "\n\n".join(cleaned_full_text_parts).strip()
        return cleaned_pages, cleaned_full_text

    @staticmethod
    def clean_single_page_text(text: str, repeated_lines: set[str]) -> str:
        if not text:
            return ""

        lines = text.splitlines()
        lines = [line.strip() for line in lines if line.strip()]

        cleaned_lines = []

        for line in lines:
            if TextCleaningService.is_page_number_line(line):
                continue

            if line in repeated_lines:
                continue

            normalized = TextCleaningService.normalize_line(line)

            if normalized:
                cleaned_lines.append(normalized)

        merged_lines = TextCleaningService.merge_broken_lines(cleaned_lines)
        final_text = "\n".join(merged_lines).strip()

        final_text = TextCleaningService.final_cleanup(final_text)
        return final_text

    @staticmethod
    def normalize_line(line: str) -> str:
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(r"([(\[{])\s+", r"\1", line)
        line = re.sub(r"\s+([)\]}])", r"\1", line)

        bullet_prefixes = ["•", "-", "–", "—", "*"]
        for bullet in bullet_prefixes:
            if line.startswith(bullet):
                content = line[1:].strip()
                return f"• {content}" if content else ""

        return line.strip()

    @staticmethod
    def merge_broken_lines(lines: list[str]) -> list[str]:
        if not lines:
            return []

        merged = []
        buffer = ""

        for line in lines:
            if not buffer:
                buffer = line
                continue

            if TextCleaningService.should_merge_lines(buffer, line):
                buffer = f"{buffer} {line}".strip()
            else:
                merged.append(buffer)
                buffer = line

        if buffer:
            merged.append(buffer)

        return merged

    @staticmethod
    def should_merge_lines(current_line: str, next_line: str) -> bool:
        if not current_line or not next_line:
            return False

        if current_line.endswith((".", "!", "?", ":", ";")):
            return False

        if current_line.startswith("•") or next_line.startswith("•"):
            return False

        if TextCleaningService.looks_like_heading(next_line):
            return False

        if len(current_line) < 80:
            return True

        return False

    @staticmethod
    def looks_like_heading(line: str) -> bool:
        if len(line.split()) <= 8 and line == line.title():
            return True

        if len(line.split()) <= 8 and line.isupper():
            return True

        return False

    @staticmethod
    def is_page_number_line(line: str) -> bool:
        line = line.strip()

        if re.fullmatch(r"\d+", line):
            return True

        if re.fullmatch(r"page\s+\d+", line, re.IGNORECASE):
            return True

        if re.fullmatch(r"\d+\s*/\s*\d+", line):
            return True

        return False

    @staticmethod
    def find_repeated_noise_lines(pages: list[dict]) -> set[str]:
        line_counts = {}

        for page in pages:
            text = page.get("text", "")
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            unique_lines = set(lines)

            for line in unique_lines:
                normalized_line = re.sub(r"\s+", " ", line).strip()

                if len(normalized_line) < 3:
                    continue

                line_counts[normalized_line] = line_counts.get(normalized_line, 0) + 1

        repeated_lines = set()

        for line, count in line_counts.items():
            if count >= 2 and len(line.split()) <= 12:
                if not TextCleaningService.looks_like_meaningful_content(line):
                    repeated_lines.add(line)

        return repeated_lines

    @staticmethod
    def looks_like_meaningful_content(line: str) -> bool:
        lower = line.lower()

        protected_keywords = {
            "introduction",
            "overview",
            "summary",
            "conclusion",
            "results",
            "discussion",
            "analysis",
            "recommendation",
        }

        if lower in protected_keywords:
            return True

        return False

    @staticmethod
    def final_cleanup(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()