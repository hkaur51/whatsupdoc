from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum

class ConsentStatus(str, Enum):
    PENDING = "pending"
    GIVEN = "given"
    DENIED = "denied"

class ConsentCreate(BaseModel):
    patient_id: str
    clinic_id: str
    consent_text: Optional[str] = None
    consent_timestamp: Optional[datetime] = None

class Consent(BaseModel):
    id: str
    patient_id: str
    clinic_id: str
    status: ConsentStatus = ConsentStatus.PENDING
    consent_text: Optional[str] = None
    consent_timestamp: Optional[datetime] = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None
