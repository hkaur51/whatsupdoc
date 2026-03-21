import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Indian language markers for detection (Roman script / mixed)
LANG_MARKERS = {
    "hi": ["hai", "kal", "aaj", "sakti", "sakta", "mujhe", "bohot", "bahut", "kripya", "mil", "sakta", "sakti", "ji"],
    "pa": ["sakda", "nu", "layi", "ji", "haan", "nahi"],
    "bn": ["ami", "tumi", "kemon", "achhe"],
    "mr": ["ahe", "kaay", "mala", "hotay"],
    "gu": ["chhe", "che", "shu", "have"],
    "ta": ["irukku", "illai", "romba", "ungal"],
    "te": ["undi", "ledu", "meeru", "nenu"],
    "kn": ["ide", "illa", "nimage", "namage"],
    "ml": ["unda", "illa", "njan", "ente"],
    "ur": ["hai", "main", "aap", "kiya"],
}


class TranslationService:
    """Service for translating messages between languages.

    In local/non-LLM mode this is a no-op passthrough with simple language guessing.
    Replace with real translation API (e.g. Google, Azure) for production.
    """

    def __init__(self) -> None:
        self.enabled = True

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source language to target language. Returns original if same lang."""
        if not text or source_lang == target_lang:
            return text
        logger.info(
            "Mock translate (passthrough) '%s' from %s to %s", text[:80], source_lang, target_lang
        )
        return text
    
    # doesn't transalte it to functions 

    async def detect_language(self, text: str) -> Tuple[str, float]:
        """Detect the language of the given text. Returns (language_code, confidence_score)."""
        lower = (text or "").lower().strip()
        if not lower:
            return "en", 0.5
        for lang, markers in LANG_MARKERS.items():
            if any(m in lower for m in markers):
                logger.info("Detected language '%s' for text: %s", lang, text[:100])
                return lang, 0.85
        return "en", 0.8

    async def translate_to_doctor_language(
        self, message: str, doctor_language: str
    ) -> Tuple[str, str, float]:
        """Translate patient message to doctor's preferred language. Returns (translated, detected_lang, confidence)."""
        detected, conf = await self.detect_language(message)
        translated = await self.translate(message, detected, doctor_language)
        return translated, detected, conf

    async def translate_to_patient_language(
        self, message: str, patient_language: str
    ) -> Tuple[str, float]:
        """Translate reply to patient's preferred language. Returns (translated, confidence)."""
        if not message or patient_language == "en":
            return message, 1.0
        translated = await self.translate(message, "en", patient_language)
        return translated, 0.9

    def flag_low_confidence_translation(self, confidence: float, threshold: float = 0.7) -> bool:
        """Return True if translation confidence is below threshold (for logging/override)."""
        return confidence < threshold

