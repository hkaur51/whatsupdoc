from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class CalendarBlockCreate(BaseModel):
    doctor_id: str
    start_datetime: datetime
    end_datetime: datetime
    reason: Optional[str] = None
    block_type: str = "manual"

class CalendarBlock(BaseModel):
    id: str
    doctor_id: str
    start_datetime: datetime
    end_datetime: datetime
    reason: Optional[str] = None
    block_type: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
