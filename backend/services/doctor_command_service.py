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
        else:
            # Check for day names (monday, tuesday, etc.)
            day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, day in enumerate(day_names):
                if day in lower:
                    current_weekday = today.weekday()
                    days_ahead = (i - current_weekday) % 7
                    if days_ahead == 0:
                        days_ahead = 7  # Next occurrence
                    date = (today + timedelta(days=days_ahead)).isoformat()
                    break

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
            # Parse "5 June to 12 June" or "5 Jun to 12 Jun" or "June 5 to June 12"
            import re
            months = {
                "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
                "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
                "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
                "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
            }
            # e.g. "5 june to 12 june" or "5 jun to 12 jun" or "june 5 to june 12"
            parts = re.split(r"\s+to\s+", lower, maxsplit=1)
            start_date = None
            end_date = None
            if len(parts) == 2:
                start_part, end_part = parts[0].strip(), parts[1].strip()
                for month_name, month_num in months.items():
                    if month_name in start_part:
                        day_match = re.search(r"\d{1,2}", start_part)
                        if day_match:
                            start_day = int(day_match.group())
                            year = today.year
                            if month_num < today.month or (month_num == today.month and start_day < today.day):
                                year += 1
                            start_date = f"{year}-{month_num:02d}-{start_day:02d}"
                        break
                else:
                    start_date = None
                for month_name, month_num in months.items():
                    if month_name in end_part:
                        day_match = re.search(r"\d{1,2}", end_part)
                        if day_match:
                            end_day = int(day_match.group())
                            year = today.year
                            if month_num < today.month or (month_num == today.month and end_day < today.day):
                                year += 1
                            end_date = f"{year}-{month_num:02d}-{end_day:02d}"
                        break
                else:
                    end_date = None
            else:
                start_date = None
                end_date = None
        elif has_any(["show", "list"]) and "appointment" in lower:
            intent = "list_appointments"
        elif has_any(["schedule", "book", "add", "fix", "set"]) and "appointment" in lower or has_any(
            ["schedule", "book", "rakho"]
        ):
            intent = "create_appointment"
        elif "cancel" in lower:
            intent = "cancel_appointment"
        elif "reschedule" in lower or "move" in lower or "change" in lower:
            intent = "reschedule_appointment"

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

