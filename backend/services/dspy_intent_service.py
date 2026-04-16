"""DSPy-based patient intent parser for the dental booking bot.

Uses Google Gemini (free tier) as the underlying LM. Provides a deterministic,
schema-constrained structured output via DSPy Signatures so the rest of the
pipeline can rely on a well-typed intent dict.

If GEMINI_API_KEY is not set or DSPy/Gemini is unavailable, callers should fall
back to the rule-based PatientIntentService.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Literal, Optional

logger = logging.getLogger(__name__)

_Intent = Literal[
    "book_appointment",
    "cancel_appointment",
    "reschedule_appointment",
    "check_appointment",
    "ask_availability",
    "clinical_escalation",
    "general_query",
    "greeting",
]

_Urgency = Literal["low", "medium", "high"]
_Language = Literal["en", "hi", "hinglish", "other"]


def _build_module():
    """Construct (and cache) the DSPy intent module. Returns None if unavailable."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import dspy  # type: ignore
    except Exception as exc:
        logger.warning("DSPy not installed (%s). Falling back to rules.", exc)
        return None

    model_name = os.environ.get("GEMINI_MODEL", "gemini/gemini-2.0-flash")
    try:
        lm = dspy.LM(model_name, api_key=api_key, temperature=0.1, max_tokens=512)
        dspy.configure(lm=lm)
    except Exception as exc:
        logger.warning("Could not configure DSPy LM %s: %s", model_name, exc)
        return None

    class PatientIntentSig(dspy.Signature):
        """Classify a patient WhatsApp message for a dental clinic booking bot.

        Supports English, Hindi and Hinglish. Extract the single best intent and
        any booking-relevant slots (preferred date, time of day). Flag clinical
        urgency ONLY when the message describes bleeding, severe pain, swelling,
        fever with dental symptoms, or trauma. Do not invent dates or times that
        the user did not mention.
        """

        message: str = dspy.InputField(desc="Raw patient message (any language).")
        intent: _Intent = dspy.OutputField(desc="The single best intent.")
        detected_language: _Language = dspy.OutputField(desc="Language of the message.")
        preferred_date: Optional[str] = dspy.OutputField(
            desc="One of: today, tomorrow, monday..sunday, an ISO date (YYYY-MM-DD), or null."
        )
        preferred_time: Optional[str] = dspy.OutputField(
            desc="One of: morning, afternoon, evening, a HH:MM 24h time, or null."
        )
        urgency: _Urgency = dspy.OutputField(desc="Clinical urgency.")
        procedure_hint: Optional[str] = dspy.OutputField(
            desc="Dental procedure the patient mentions (e.g. 'cleaning', 'root canal') or null."
        )
        summary: str = dspy.OutputField(desc="One-sentence neutral summary for the doctor.")

    module = dspy.Predict(PatientIntentSig)
    logger.info("DSPy intent module ready (model=%s).", model_name)
    return module


class DSPyIntentService:
    def __init__(self) -> None:
        self._module = _build_module()
        self.enabled = self._module is not None

    async def parse_intent(self, message: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        try:
            import asyncio

            def _run():
                return self._module(message=(message or "").strip())

            prediction = await asyncio.to_thread(_run)
            result: Dict[str, Any] = {
                "role": "patient",
                "intent": getattr(prediction, "intent", "general_query"),
                "detected_language": getattr(prediction, "detected_language", "en"),
                "preferred_date": getattr(prediction, "preferred_date", None) or None,
                "preferred_time": getattr(prediction, "preferred_time", None) or None,
                "urgency": getattr(prediction, "urgency", "low"),
                "procedure_hint": getattr(prediction, "procedure_hint", None) or None,
                "patient_message_summary": (
                    getattr(prediction, "summary", "") or (message or "")[:200]
                ),
                "original_message": message,
                "parser": "dspy+gemini",
            }
            logger.info("DSPy parsed intent: %s", result)
            return result
        except Exception as exc:
            logger.warning("DSPy parse failed (%s). Falling back to rules.", exc)
            return None
