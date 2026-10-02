import re

from app.core.config import settings

CHUNK_TARGET_WORDS = settings.CHUNK_TARGET_WORDS
CHUNK_MAX_WORDS = settings.CHUNK_MAX_WORDS
CHUNK_OVERLAP_WORDS = settings.CHUNK_OVERLAP_WORDS

class ChunkingService:
    @staticmethod
    def build_chunks(sections: list[dict]) -> list[dict]:
        chunks = []
        chunk_id = 1

        for section in sections:
            section_chunks = ChunkingService.chunk_section(section)

            for chunk in section_chunks:
                chunk["chunk_id"] = chunk_id
                chunks.append(chunk)
                chunk_id += 1

        return chunks

    @staticmethod
    def chunk_section(section: dict) -> list[dict]:
        content = section.get("content", "").strip()

        if not content:
            return []

        blocks = [block.strip() for block in content.split("\n") if block.strip()]

        if not blocks:
            return []

        section_chunks = []
        current_blocks = []
        current_word_count = 0

        for block in blocks:
            block_word_count = ChunkingService.count_words(block)

            if (
                current_blocks
                and current_word_count + block_word_count > CHUNK_MAX_WORDS
            ):
                chunk_text = "\n".join(current_blocks).strip()
                section_chunks.append(
                    ChunkingService.create_chunk_dict(section, chunk_text)
                )

                overlap_text = ChunkingService.get_overlap_text(
                    chunk_text, CHUNK_OVERLAP_WORDS
                )

                current_blocks = [overlap_text] if overlap_text else []
                current_word_count = ChunkingService.count_words(overlap_text)

            current_blocks.append(block)
            current_word_count += block_word_count

            if current_word_count >= CHUNK_TARGET_WORDS:
                chunk_text = "\n".join(current_blocks).strip()
                section_chunks.append(
                    ChunkingService.create_chunk_dict(section, chunk_text)
                )

                overlap_text = ChunkingService.get_overlap_text(
                    chunk_text, CHUNK_OVERLAP_WORDS
                )

                current_blocks = [overlap_text] if overlap_text else []
                current_word_count = ChunkingService.count_words(overlap_text)

        if current_blocks:
            chunk_text = "\n".join(current_blocks).strip()
            if chunk_text:
                section_chunks.append(
                    ChunkingService.create_chunk_dict(section, chunk_text)
                )

        return ChunkingService.remove_duplicate_chunks(section_chunks)

    @staticmethod
    def create_chunk_dict(section: dict, text: str) -> dict:
        return {
            "chunk_id": 0,
            "section_id": section["section_id"],
            "section_heading": section["heading"],
            "text": text,
            "word_count": ChunkingService.count_words(text),
            "start_page": section["start_page"],
            "end_page": section["end_page"],
            "source_pages": section["source_pages"],
            "total_images": section.get("total_images", 0),  # Injects visual context for the LLM
            "processed_time_relative": "just now",           # UI-ready timestamp
        }

    @staticmethod
    def get_overlap_text(text: str, overlap_words: int) -> str:
        words = re.findall(r"\S+", text)

        if len(words) <= overlap_words:
            return text.strip()

        return " ".join(words[-overlap_words:]).strip()

    @staticmethod
    def remove_duplicate_chunks(chunks: list[dict]) -> list[dict]:
        unique_chunks = []
        seen = set()

        for chunk in chunks:
            normalized_text = re.sub(r"\s+", " ", chunk["text"]).strip()

            if normalized_text in seen:
                continue

            seen.add(normalized_text)
            unique_chunks.append(chunk)

        return unique_chunks

    @staticmethod
    def count_words(text: str) -> int:
        return len(re.findall(r"\b\w+\b", text))