# from app.schemas.presentation_schema import PresentationOutline
# from app.services.prompt_builder_service import PromptBuilderService


# class OutlineGenerationService:
#     def __init__(self, llm_provider):
#         self.llm_provider = llm_provider

#     def generate_outline(
#         self,
#         document_title: str,
#         summary: dict,
#         sections: list[dict],
#         chunks: list[dict],
#     ) -> PresentationOutline:
#         prompt = PromptBuilderService.build_outline_prompt(
#             document_title=document_title,
#             summary=summary,
#             sections=sections,
#             chunks=chunks,
#         )

#         result = self.llm_provider.generate_json(prompt)
#         return PresentationOutline(**result)

import logging
from app.schemas.schemas import PresentationOutline
from app.services.prompt_builder_service import PromptBuilderService

logger = logging.getLogger(__name__)

class OutlineGenerationService:
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def generate_outline(
        self,
        document_title: str,
        summary: dict,
        sections: list[dict],
        chunks: list[dict],
    ) -> PresentationOutline:
        prompt = PromptBuilderService.build_outline_prompt(
            document_title=document_title,
            summary=summary,
            sections=sections,
            chunks=chunks,
        )

        try:
            # Generate the raw JSON dict from the LLM
            result = self.llm_provider.generate_json(prompt)
            
            # Validate and unpack into the Pydantic model
            return PresentationOutline(**result)
            
        except ValueError as e:
            logger.error(f"Pydantic Validation Error during outline generation: {e}")
            logger.debug(f"Raw LLM output: {result}")
            raise Exception("The AI generated an invalid presentation structure. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error in OutlineGenerationService: {e}")
            raise e