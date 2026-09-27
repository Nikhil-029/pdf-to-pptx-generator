from app.services.llm.groq_provider import GroqProvider


def get_llm_provider() -> GroqProvider:
    """
    Returns the configured LLM provider.
    Swap this out to add OpenAI, Anthropic, or Ollama support.
    """
    return GroqProvider()
