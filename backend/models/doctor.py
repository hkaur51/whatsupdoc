from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class DoctorCreate(BaseModel):
    clinic_id: str
    name: str
    phone: str
    specialization: Optional[str] = None
    preferred_language: str = "en"

class Doctor(BaseModel):
    id: str
    clinic_id: str
    name: str
    phone: str
    specialization: Optional[str] = None
    preferred_language: str = "en"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
