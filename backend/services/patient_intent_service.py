import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PatientIntentService:
    """Service for parsing patient natural language messages.

    In local/non-LLM mode this uses simple deterministic, rule-based parsing.
    """

    def __init__(self) -> None:
        # Kept for API compatibility; no external LLM required locally.
        self.enabled = True

    async def parse_intent(self, message: str) -> Dict[str, Any]:
        """Parse patient message and extract intent using rule-based logic."""
        text = (message or "").strip()
        lower = text.lower()

        # Basic language guess: if we see common Hindi/Hinglish words, mark as "hi"
        hindi_markers = ["kal", "appointment", "mil sakti", "mujhe", "bohot", "dard", "hai"]
        detected_language = "hi" if any(w in lower for w in hindi_markers) else "en"

        intent = "general_query"
        preferred_date: Any = None
        preferred_time: Any = None
        urgency = "low"

        # Clinical escalation: pain/bleeding keywords
        escalation_keywords = ["severe pain", "bohot dard", "bahut dard", "bleeding", "sujan", "swelling"]
        if any(k in lower for k in escalation_keywords):
            intent = "clinical_escalation"
            urgency = "high"
        elif any(k in lower for k in ["cancel", "reschedule", "change time", "move my appointment"]):
            if "cancel" in lower:
                intent = "cancel_appointment"
            elif "reschedule" in lower or "change" in lower or "move" in lower:
                intent = "reschedule_appointment"
        elif any(k in lower for k in ["when can i come", "when are you free", "availability", "free slots"]):
            intent = "ask_availability"
        elif any(k in lower for k in ["appointment", "can i come", "i want to come", "see you"]):
            intent = "book_appointment"
        elif any(k in lower for k in ["when is my appointment", "next appointment", "my appointment time"]):
            intent = "check_appointment"

        # Very simple date heuristics
        if "tomorrow" in lower or "kal" in lower:
            preferred_date = "tomorrow"
        elif "today" in lower or "aaj" in lower:
            preferred_date = "today"

        # Simple time phrase detection (morning/evening)
        if any(k in lower for k in ["morning", "subah"]):
            preferred_time = "morning"
        elif any(k in lower for k in ["evening", "shaam"]):
            preferred_time = "evening"

        patient_message_summary = text[:200]

        result: Dict[str, Any] = {
            "role": "patient",
            "intent": intent,
            "detected_language": detected_language,
            "preferred_date": preferred_date,
            "preferred_time": preferred_time,
            "urgency": urgency,
            "patient_message_summary": patient_message_summary,
            "original_message": message,
        }

        logger.info("Parsed patient intent (rule-based): %s", result)
        return result

