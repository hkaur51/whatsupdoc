from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class PatientCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    preferred_language: Optional[str] = "en"

class Patient(BaseModel):
    id: str
    phone: str
    name: Optional[str] = None
    preferred_language: str = "en"
    consent_status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_contact: Optional[datetime] = None
