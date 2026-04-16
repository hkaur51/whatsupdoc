import logging
from typing import Dict, Any, Optional

from services.dspy_intent_service import DSPyIntentService

logger = logging.getLogger(__name__)


class PatientIntentService:
    """Parse patient natural-language messages.

    Prefers DSPy + Gemini for structured, deterministic output. Falls back to a
    rule-based parser if the LLM is not configured or fails.
    """

    def __init__(self) -> None:
        self._dspy = DSPyIntentService()
        self.enabled = True
        logger.info(
            "PatientIntentService ready (dspy_enabled=%s)", self._dspy.enabled
        )

    async def parse_intent(self, message: str) -> Dict[str, Any]:
        llm_result: Optional[Dict[str, Any]] = None
        if self._dspy.enabled:
            llm_result = await self._dspy.parse_intent(message)
        if llm_result is not None:
            return llm_result
        return self._rule_based(message)

    @staticmethod
    def _rule_based(message: str) -> Dict[str, Any]:
        text = (message or "").strip()
        lower = text.lower()

        hindi_markers = ["kal", "mil sakti", "mujhe", "bohot", "dard", "hai", "haan"]
        detected_language = "hi" if any(w in lower for w in hindi_markers) else "en"

        intent = "general_query"
        preferred_date: Any = None
        preferred_time: Any = None
        urgency = "low"

        escalation_keywords = [
            "severe pain", "bohot dard", "bahut dard", "bleeding", "sujan", "swelling",
        ]
        if any(k in lower for k in escalation_keywords):
            intent = "clinical_escalation"
            urgency = "high"
        elif any(k in lower for k in ["cancel"]):
            intent = "cancel_appointment"
        elif any(k in lower for k in ["reschedule", "change time", "move my appointment"]):
            intent = "reschedule_appointment"
        elif any(k in lower for k in ["when can i come", "when are you free", "availability", "free slots"]):
            intent = "ask_availability"
        elif any(k in lower for k in ["appointment", "can i come", "i want to come", "see you", "book", "visit"]):
            intent = "book_appointment"
        elif any(k in lower for k in ["when is my appointment", "next appointment", "my appointment time"]):
            intent = "check_appointment"

        if "tomorrow" in lower or "kal" in lower:
            preferred_date = "tomorrow"
        elif "today" in lower or "aaj" in lower:
            preferred_date = "today"
        else:
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                if day in lower:
                    preferred_date = day
                    if intent == "general_query":
                        intent = "book_appointment"
                    break

        if any(k in lower for k in ["morning", "subah"]):
            preferred_time = "morning"
        elif any(k in lower for k in ["evening", "shaam"]):
            preferred_time = "evening"
        elif "afternoon" in lower:
            preferred_time = "afternoon"

        return {
            "role": "patient",
            "intent": intent,
            "detected_language": detected_language,
            "preferred_date": preferred_date,
            "preferred_time": preferred_time,
            "urgency": urgency,
            "procedure_hint": None,
            "patient_message_summary": text[:200],
            "original_message": message,
            "parser": "rules",
        }
