import logging
from typing import List, Dict, Any
from datetime import datetime, time
from database import get_database

logger = logging.getLogger(__name__)

class AvailabilityService:
    """Service for managing doctor availability and calendar"""
    
    async def check_doctor_available(
        self,
        doctor_id: str,
        date: str,
        time_slot: str
    ) -> bool:
        """Check if doctor is available at a specific date and time"""
        try:
            db = get_database()
            
            # Check calendar blocks
            target_datetime = datetime.strptime(f"{date} {time_slot}", "%Y-%m-%d %H:%M")
            
            blocks = await db.calendar_blocks.find({
                "doctor_id": doctor_id,
                "start_datetime": {"$lte": target_datetime.isoformat()},
                "end_datetime": {"$gte": target_datetime.isoformat()}
            }, {"_id": 0}).to_list(10)
            
            if blocks:
                logger.info(f"Doctor {doctor_id} has calendar block at {date} {time_slot}")
                return False
            
            # Check existing appointments
            appointments = await db.appointments.find({
                "doctor_id": doctor_id,
                "appointment_date": date,
                "appointment_time": time_slot,
                "status": {"$in": ["scheduled", "confirmed"]}
            }, {"_id": 0}).to_list(10)
            
            if appointments:
                logger.info(f"Doctor {doctor_id} has appointment at {date} {time_slot}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking availability: {e}", exc_info=True)
            return False
    
    async def get_doctor_schedule(
        self,
        doctor_id: str,
        date: str
    ) -> Dict[str, Any]:
        """Get doctor's full schedule for a date"""
        try:
            db = get_database()
            
            appointments = await db.appointments.find({
                "doctor_id": doctor_id,
                "appointment_date": date
            }, {"_id": 0}).sort("appointment_time", 1).to_list(100)
            
            calendar_blocks = await db.calendar_blocks.find({
                "doctor_id": doctor_id,
                "start_datetime": {
                    "$lte": datetime.strptime(date, "%Y-%m-%d").replace(hour=23, minute=59).isoformat()
                },
                "end_datetime": {
                    "$gte": datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0).isoformat()
                }
            }, {"_id": 0}).to_list(100)
            
            return {
                "date": date,
                "appointments": appointments,
                "blocks": calendar_blocks
            }
        
        except Exception as e:
            logger.error(f"Error getting schedule: {e}", exc_info=True)
            return {"date": date, "appointments": [], "blocks": []}
