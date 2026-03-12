import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time
from database import get_database

logger = logging.getLogger(__name__)

class AppointmentService:
    """Service for managing appointments"""
    
    async def get_available_slots(
        self,
        clinic_id: str,
        doctor_id: str,
        date: str,
        duration_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """Get available appointment slots for a doctor on a given date"""
        try:
            db = get_database()
            
            # Get clinic working hours
            clinic = await db.clinics.find_one({"id": clinic_id}, {"_id": 0})
            if not clinic:
                return []
            
            working_hours = clinic.get("working_hours", {})
            start_time = working_hours.get("start", "09:00")
            end_time = working_hours.get("end", "18:00")
            
            # Get existing appointments for this doctor on this date
            existing_appointments = await db.appointments.find({
                "doctor_id": doctor_id,
                "appointment_date": date,
                "status": {"$in": ["scheduled", "confirmed"]}
            }, {"_id": 0}).to_list(100)
            
            # Get calendar blocks for this doctor
            target_date = datetime.strptime(date, "%Y-%m-%d")
            calendar_blocks = await db.calendar_blocks.find({
                "doctor_id": doctor_id,
                "start_datetime": {
                    "$lte": target_date.replace(hour=23, minute=59).isoformat()
                },
                "end_datetime": {
                    "$gte": target_date.replace(hour=0, minute=0).isoformat()
                }
            }, {"_id": 0}).to_list(100)
            
            # Generate time slots
            slots = self._generate_time_slots(start_time, end_time, duration_minutes)
            
            # Filter out booked slots
            available_slots = []
            for slot in slots:
                if not self._is_slot_booked(slot, existing_appointments, calendar_blocks, date):
                    available_slots.append({
                        "time": slot,
                        "date": date,
                        "available": True
                    })
            
            return available_slots
        
        except Exception as e:
            logger.error(f"Error getting available slots: {e}", exc_info=True)
            return []
    
    def _generate_time_slots(self, start_time: str, end_time: str, duration_minutes: int) -> List[str]:
        """Generate time slots between start and end time"""
        slots = []
        
        start_hour, start_minute = map(int, start_time.split(":"))
        end_hour, end_minute = map(int, end_time.split(":"))
        
        current = datetime.now().replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end = datetime.now().replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=duration_minutes)
        
        return slots
    
    def _is_slot_booked(
        self,
        slot_time: str,
        appointments: List[Dict],
        calendar_blocks: List[Dict],
        date: str
    ) -> bool:
        """Check if a time slot is already booked"""
        # Check appointments
        for apt in appointments:
            if apt.get("appointment_time") == slot_time:
                return True
        
        # Check calendar blocks
        slot_datetime = datetime.strptime(f"{date} {slot_time}", "%Y-%m-%d %H:%M")
        for block in calendar_blocks:
            block_start = datetime.fromisoformat(block["start_datetime"])
            block_end = datetime.fromisoformat(block["end_datetime"])
            
            if block_start <= slot_datetime < block_end:
                return True
        
        return False
