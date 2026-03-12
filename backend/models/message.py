from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, timezone
from enum import Enum

class MessageRole(str, Enum):
    DOCTOR = "doctor"
    PATIENT = "patient"
    SYSTEM = "system"

class MessageCreate(BaseModel):
    clinic_id: str
    sender_phone: str
    sender_role: MessageRole
    original_text: str
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    translated_to_language: Optional[str] = None
    parsed_intent: Optional[Dict] = None
    action_taken: Optional[str] = None
    result_status: str = "success"

class Message(BaseModel):
    id: str
    clinic_id: str
    sender_phone: str
    sender_role: MessageRole
    original_text: str
    detected_language: Optional[str] = None
    translated_text: Optional[str] = None
    translated_to_language: Optional[str] = None
    parsed_intent: Optional[Dict] = None
    action_taken: Optional[str] = None
    whatsapp_message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result_status: str = "success"
