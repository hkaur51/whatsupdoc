import logging

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translating messages between languages.

    In local/non-LLM mode this is a no-op passthrough with simple language guessing.
    """

    def __init__(self) -> None:
        # API compatibility; no external LLM required locally.
        self.enabled = True

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source language to target language.

        For the local MVP this simply returns the original text unchanged.
        """
        logger.info(
            "Mock translate (passthrough) '%s' from %s to %s", text, source_lang, target_lang
        )
        return text

    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text using simple heuristics."""
        lower = (text or "").lower()

        # Very basic heuristic just to tag Hindi-ish vs English
        hindi_tokens = ["hai", "kal", "aaj", "sakti", "sakta", "dard", "bhot", "bohot", "bahut"]
        if any(tok in lower for tok in hindi_tokens):
            lang = "hi"
        else:
            lang = "en"

        logger.info("Mock detected language '%s' for text: %s", lang, text[:100])
        return lang

