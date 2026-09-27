from app.schemas.schemas import DocumentSummary
from app.services.prompt_builder_service import PromptBuilderService


class SummarizationService:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def summarize(self, document_title: str, sections: list[dict], chunks: list[dict]) -> DocumentSummary:
        prompt = PromptBuilderService.build_summary_prompt(
            document_title=document_title,
            sections=sections,
            chunks=chunks,
        )

        result = self.llm_provider.generate_json(prompt)
        return DocumentSummary(**result)