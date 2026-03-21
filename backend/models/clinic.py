from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone

class WorkingHours(BaseModel):
    start: str = "09:00"
    end: str = "18:00"
    days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

class ClinicCreate(BaseModel):
    name: str
    phone: str
    working_hours: Optional[WorkingHours] = Field(default_factory=WorkingHours)
    holidays: Optional[List[str]] = Field(default_factory=list)
    escalation_keywords: Optional[List[str]] = Field(default_factory=lambda: [
        "pain", "swelling", "bleeding", "emergency", "urgent", "severe",
        "dard", "sujan", "khoon", "तुरंत", "दर्द"
    ]) 
    # increase width avenue for escalation keywords or let a serverless llm handle the emotion of the user prompt. 

class Clinic(BaseModel):
    id: str
    name: str
    phone: str
    working_hours: WorkingHours
    holidays: List[str]
    escalation_keywords: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
