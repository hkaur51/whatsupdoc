import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DoctorCommandService:
    """Service for parsing doctor natural language commands.

    In local/non-LLM mode this uses deterministic, rule-based parsing.
    """

    def __init__(self) -> None:
        # Kept for compatibility; no external LLM required locally.
        self.enabled = True

    async def parse_command(self, message: str) -> Dict[str, Any]:
        """Parse doctor command and extract structured action using rule-based logic."""
        text = (message or "").strip()
        lower = text.lower()

        detected_language = "en"
        intent = "unknown"

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        date: Optional[str] = None
        start_time: Optional[str] = None
        end_time: Optional[str] = None
        time: Optional[str] = None
        patient_name: Optional[str] = None
        reason: Optional[str] = None
        start_date: Optional[str] = None
        end_date: Optional[str] = None

        # Helpers
        def has_any(words):
            return any(w in lower for w in words)

        # Date words
        if "tomorrow" in lower:
            date = tomorrow.isoformat()
        elif "today" in lower:
            date = today.isoformat()

        # Very rough time parsing for "10 to 1", "10-1", "10 am", "5 pm"
        import re

        range_match = re.search(r"(\d{1,2})\s*(?:to|-)\s*(\d{1,2})", lower)
        if range_match:
            start_h, end_h = range_match.groups()
            start_time = f"{int(start_h):02d}:00"
            end_time = f"{int(end_h):02d}:00"

        single_time_match = re.search(r"(\d{1,2})\s*(am|pm)", lower)
        if single_time_match:
            hour = int(single_time_match.group(1))
            ampm = single_time_match.group(2)
            if ampm == "pm" and hour < 12:
                hour += 12
            time = f"{hour:02d}:00"

        # Intent classification
        if has_any(["block ", "block tomorrow", "no appointments", "block my calendar"]):
            intent = "create_calendar_block"
            # Reason heuristic
            if "surgery" in lower:
                reason = "surgery"
        elif "vacation" in lower or "leave" in lower or "holiday" in lower:
            intent = "set_vacation"
            # Simple "5 June to 12 June" pattern -> we don't fully parse free text here;
            # caller can still handle None safely.
        elif has_any(["schedule", "book", "add", "fix", "set"]) and "appointment" in lower or has_any(
            ["schedule", "book", "see", "rakho"]
        ):
            intent = "create_appointment"
        elif "cancel" in lower:
            intent = "cancel_appointment"
        elif "reschedule" in lower or "move" in lower or "change" in lower:
            intent = "reschedule_appointment"
        elif has_any(["show", "list", "see"]) and "appointment" in lower:
            intent = "list_appointments"

        # Naive patient name extraction: word after "schedule"/"cancel"
        for keyword in ["schedule", "cancel", "reschedule"]:
            if keyword in lower:
                parts = lower.split(keyword, 1)[1].strip().split()
                if parts:
                    # Capitalize first token as name guess
                    patient_name = parts[0].capitalize()
                break

        result: Dict[str, Any] = {
            "role": "doctor",
            "intent": intent,
            "detected_language": detected_language,
            "original_message": message,
        }

        if date:
            result["date"] = date
        if start_time:
            result["start_time"] = start_time
        if end_time:
            result["end_time"] = end_time
        if time:
            result["time"] = time
        if patient_name:
            result["patient_name"] = patient_name
        if reason:
            result["reason"] = reason
        if start_date:
            result["start_date"] = start_date
        if end_date:
            result["end_date"] = end_date

        logger.info("Parsed doctor command (rule-based): %s", result)
        return result

