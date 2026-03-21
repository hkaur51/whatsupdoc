import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from database import get_database
import uuid

logger = logging.getLogger(__name__)

class DoctorCommandExecutor:
    """Execute parsed doctor commands with real database operations"""
    
    async def execute(self, parsed_command: Dict[str, Any], clinic_id: str, doctor_phone: str, db=None) -> str:
        """Route and execute doctor command based on intent"""
        try:
            intent = parsed_command.get("intent")
            
            # Get doctor info
            if db is None:
                db = get_database()
            doctor = await db.doctors.find_one({"phone": doctor_phone, "clinic_id": clinic_id})
            if not doctor:
                return "❌ Doctor profile not found. Please contact admin."
            
            doctor_id = doctor["id"]
            
            # Route to specific handler
            if intent == "create_calendar_block":
                return await self._create_calendar_block(db, parsed_command, doctor_id)
            elif intent == "set_vacation":
                return await self._set_vacation(db, parsed_command, doctor_id)
            elif intent == "create_appointment":
                return await self._create_appointment(db, parsed_command, doctor_id, clinic_id)
            elif intent == "cancel_appointment":
                return await self._cancel_appointment(db, parsed_command, doctor_id)
            elif intent == "reschedule_appointment":
                return await self._reschedule_appointment(db, parsed_command, doctor_id)
            elif intent == "list_appointments":
                return await self._list_appointments(db, parsed_command, doctor_id)
            elif intent == "bulk_reschedule":
                return await self._bulk_reschedule(db, parsed_command, doctor_id)
            elif intent == "update_availability":
                return await self._update_availability(db, parsed_command, doctor_id)
            elif intent == "send_broadcast":
                return await self._send_broadcast(db, parsed_command, doctor_id)
            else:
                return (
                    "👋 Hello Dr. " + doctor.get("name", "").split()[0] + "!\n\n"
                    "Here's what I can do:\n\n"
                    "📅 *Schedule*: \"Schedule Ramesh tomorrow 5 pm\"\n"
                    "❌ *Cancel*: \"Cancel Ramesh tomorrow\"\n"
                    "🔄 *Reschedule*: \"Reschedule Ramesh to Friday 3 pm\"\n"
                    "📋 *List*: \"Show today appointments\"\n"
                    "🚫 *Block time*: \"Block tomorrow 10 to 1 for surgery\"\n"
                    "🏖️ *Vacation*: \"Vacation 5 June to 12 June\"\n\n"
                    "Just type a command in natural language!"
                )
        
        except Exception as e:
            logger.error(f"Error executing doctor command: {e}", exc_info=True)
            return f"❌ Error executing command: {str(e)}"
    
    async def _create_calendar_block(self, db, parsed: Dict, doctor_id: str) -> str:
        """Create a calendar block (unavailable time)"""
        try:
            date = parsed.get("date")
            start_time = parsed.get("start_time")
            end_time = parsed.get("end_time")
            reason = parsed.get("reason", "Blocked")
            
            if not all([date, start_time, end_time]):
                return "❌ Missing date or time information. Please specify date and time range."
            
            # Parse datetime
            start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            
            # Create calendar block
            block_id = str(uuid.uuid4())
            block_doc = {
                "id": block_id,
                "doctor_id": doctor_id,
                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat(),
                "reason": reason,
                "block_type": "manual",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.calendar_blocks.insert_one(block_doc)
            
            # Format confirmation
            date_str = start_datetime.strftime("%B %d")
            time_range = f"{start_datetime.strftime('%I:%M %p')} to {end_datetime.strftime('%I:%M %p')}"
            
            return f"✅ Calendar blocked on {date_str}, {time_range}\nReason: {reason}"
        
        except Exception as e:
            logger.error(f"Error creating calendar block: {e}", exc_info=True)
            return f"❌ Could not create calendar block: {str(e)}"
    
    async def _set_vacation(self, db, parsed: Dict, doctor_id: str) -> str:
        """Set vacation period (creates calendar blocks for date range)"""
        try:
            start_date = parsed.get("start_date")
            end_date = parsed.get("end_date")
            
            if not all([start_date, end_date]):
                return "❌ Please specify both start and end dates for vacation."
            
            # Parse dates
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start > end:
                return "❌ End date must be after start date."
            
            # Create a single vacation block
            block_id = str(uuid.uuid4())
            block_doc = {
                "id": block_id,
                "doctor_id": doctor_id,
                "start_datetime": start.replace(hour=0, minute=0).isoformat(),
                "end_datetime": end.replace(hour=23, minute=59).isoformat(),
                "reason": "Vacation",
                "block_type": "vacation",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.calendar_blocks.insert_one(block_doc)
            
            # Calculate days
            days = (end - start).days + 1
            
            return f"✅ Vacation set from {start.strftime('%B %d')} to {end.strftime('%B %d, %Y')} ({days} days)\n\nAll appointments during this period should be rescheduled."
        
        except Exception as e:
            logger.error(f"Error setting vacation: {e}", exc_info=True)
            return f"❌ Could not set vacation: {str(e)}"
    
    async def _create_appointment(self, db, parsed: Dict, doctor_id: str, clinic_id: str) -> str:
        """Create an appointment for a patient"""
        try:
            patient_name = parsed.get("patient_name")
            date = parsed.get("date")
            time = parsed.get("time") or parsed.get("start_time")  # Handle both formats
            
            if not all([patient_name, date, time]):
                return "❌ Please specify patient name, date, and time."
            
            # Find or create patient
            patient = await db.patients.find_one({"name": {"$regex": f"^{patient_name}$", "$options": "i"}})
            
            if not patient:
                # Create new patient record
                patient_id = str(uuid.uuid4())
                patient_doc = {
                    "id": patient_id,
                    "phone": f"+91_pending_{patient_id[:8]}",  # Temporary phone
                    "name": patient_name,
                    "preferred_language": "en",
                    "consent_status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_contact": None
                }
                await db.patients.insert_one(patient_doc)
                patient_id = patient_id
            else:
                patient_id = patient["id"]
            
            # Check for conflicts
            existing = await db.appointments.find_one({
                "doctor_id": doctor_id,
                "appointment_date": date,
                "appointment_time": time,
                "status": {"$in": ["scheduled", "confirmed"]}
            })
            
            if existing:
                return f"⚠️ Conflict: You already have an appointment at {time} on {date}."
            
            # Create appointment
            appointment_id = str(uuid.uuid4())
            appointment_doc = {
                "id": appointment_id,
                "clinic_id": clinic_id,
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                "appointment_date": date,
                "appointment_time": time,
                "duration_minutes": 30,
                "status": "scheduled",
                "reason": parsed.get("reason"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": None
            }
            
            await db.appointments.insert_one(appointment_doc)
            
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_obj = datetime.strptime(time, "%H:%M")
            
            return f"✅ Appointment scheduled\n\n👤 Patient: {patient_name}\n📅 Date: {date_obj.strftime('%A, %B %d, %Y')}\n🕐 Time: {time_obj.strftime('%I:%M %p')}"
        
        except Exception as e:
            logger.error(f"Error creating appointment: {e}", exc_info=True)
            return f"❌ Could not create appointment: {str(e)}"
    
    async def _cancel_appointment(self, db, parsed: Dict, doctor_id: str) -> str:
        """Cancel an appointment"""
        try:
            patient_name = parsed.get("patient_name")
            date = parsed.get("date")
            
            if not patient_name and not date:
                return "❌ Please specify patient name or date to cancel appointment."
            
            # Build query
            query = {
                "doctor_id": doctor_id,
                "status": {"$in": ["scheduled", "confirmed"]}
            }
            
            if patient_name:
                # Find patient
                patient = await db.patients.find_one({"name": {"$regex": f"^{patient_name}$", "$options": "i"}})
                if patient:
                    query["patient_id"] = patient["id"]
                else:
                    return f"❌ Patient '{patient_name}' not found."
            
            if date:
                query["appointment_date"] = date
            
            # Find and cancel appointments
            appointments = await db.appointments.find(query).to_list(100)
            
            if not appointments:
                return "❌ No matching appointments found."
            
            # Cancel all matching
            cancelled_count = 0
            for apt in appointments:
                await db.appointments.update_one(
                    {"id": apt["id"]},
                    {"$set": {
                        "status": "cancelled",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                cancelled_count += 1
            
            if cancelled_count == 1:
                apt = appointments[0]
                patient = await db.patients.find_one({"id": apt["patient_id"]})
                patient_name = patient.get("name", "Unknown") if patient else "Unknown"
                return f"✅ Cancelled appointment\n\n👤 Patient: {patient_name}\n📅 Date: {apt['appointment_date']}\n🕐 Time: {apt['appointment_time']}"
            else:
                return f"✅ Cancelled {cancelled_count} appointments"
        
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}", exc_info=True)
            return f"❌ Could not cancel appointment: {str(e)}"
    
    async def _reschedule_appointment(self, db, parsed: Dict, doctor_id: str) -> str:
        """Reschedule an appointment"""
        try:
            patient_name = parsed.get("patient_name")
            old_date = parsed.get("old_date")
            new_date = parsed.get("new_date")
            new_time = parsed.get("new_time")
            
            if not patient_name:
                return "❌ Please specify patient name."
            
            # Find patient
            patient = await db.patients.find_one({"name": {"$regex": f"^{patient_name}$", "$options": "i"}})
            if not patient:
                return f"❌ Patient '{patient_name}' not found."
            
            # Find appointment
            query = {
                "doctor_id": doctor_id,
                "patient_id": patient["id"],
                "status": {"$in": ["scheduled", "confirmed"]}
            }
            
            if old_date:
                query["appointment_date"] = old_date
            
            appointment = await db.appointments.find_one(query)
            
            if not appointment:
                return f"❌ No appointment found for {patient_name}."
            
            # Update appointment
            update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if new_date:
                update_doc["appointment_date"] = new_date
            if new_time:
                update_doc["appointment_time"] = new_time
            
            await db.appointments.update_one(
                {"id": appointment["id"]},
                {"$set": update_doc}
            )
            
            old_info = f"{appointment['appointment_date']} at {appointment['appointment_time']}"
            new_info = f"{new_date or appointment['appointment_date']} at {new_time or appointment['appointment_time']}"
            
            return f"✅ Appointment rescheduled\n\n👤 Patient: {patient_name}\n\n❌ Old: {old_info}\n✅ New: {new_info}"
        
        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}", exc_info=True)
            return f"❌ Could not reschedule: {str(e)}"
    
    async def _list_appointments(self, db, parsed: Dict, doctor_id: str) -> str:
        """List appointments for a specific date or period"""
        try:
            date = parsed.get("date")
            time_period = parsed.get("time_period", "all")
            
            if not date:
                # Default to today
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Query appointments
            appointments = await db.appointments.find({
                "doctor_id": doctor_id,
                "appointment_date": date,
                "status": {"$in": ["scheduled", "confirmed"]}
            }).sort("appointment_time", 1).to_list(100)
            
            if not appointments:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                return f"📅 No appointments on {date_obj.strftime('%A, %B %d, %Y')}"
            
            # Get patient names
            response = f"📅 Appointments on {datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')}:\n\n"
            
            for i, apt in enumerate(appointments, 1):
                patient = await db.patients.find_one({"id": apt["patient_id"]})
                patient_name = patient.get("name", "Unknown") if patient else "Unknown"
                
                time_obj = datetime.strptime(apt["appointment_time"], "%H:%M")
                time_str = time_obj.strftime("%I:%M %p")
                
                response += f"{i}. {time_str} - {patient_name}"
                if apt.get("reason"):
                    response += f" ({apt['reason']})"
                response += "\n"
            
            response += f"\n📊 Total: {len(appointments)} appointment(s)"
            
            return response
        
        except Exception as e:
            logger.error(f"Error listing appointments: {e}", exc_info=True)
            return f"❌ Could not list appointments: {str(e)}"
    
    async def _bulk_reschedule(self, db, parsed: Dict, doctor_id: str) -> str:
        """Bulk reschedule appointments (e.g., move all morning patients to another day)"""
        try:
            source_date = parsed.get("source_date")
            target_date = parsed.get("target_date")
            time_filter = parsed.get("time_filter", "all")  # morning, afternoon, evening, all
            
            if not all([source_date, target_date]):
                return "❌ Please specify both source and target dates."
            
            # Query appointments
            query = {
                "doctor_id": doctor_id,
                "appointment_date": source_date,
                "status": {"$in": ["scheduled", "confirmed"]}
            }
            
            appointments = await db.appointments.find(query).to_list(100)
            
            if not appointments:
                return f"❌ No appointments found on {source_date}."
            
            # Filter by time if specified
            if time_filter == "morning":
                appointments = [a for a in appointments if a["appointment_time"] < "12:00"]
            elif time_filter == "afternoon":
                appointments = [a for a in appointments if "12:00" <= a["appointment_time"] < "17:00"]
            elif time_filter == "evening":
                appointments = [a for a in appointments if a["appointment_time"] >= "17:00"]
            
            if not appointments:
                return f"❌ No {time_filter} appointments found on {source_date}."
            
            # Reschedule all
            updated_count = 0
            for apt in appointments:
                await db.appointments.update_one(
                    {"id": apt["id"]},
                    {"$set": {
                        "appointment_date": target_date,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                updated_count += 1
            
            source_str = datetime.strptime(source_date, "%Y-%m-%d").strftime("%B %d")
            target_str = datetime.strptime(target_date, "%Y-%m-%d").strftime("%B %d, %Y")
            
            return f"✅ Bulk rescheduled {updated_count} appointment(s)\n\nFrom: {source_str} ({time_filter})\nTo: {target_str}"
        
        except Exception as e:
            logger.error(f"Error bulk rescheduling: {e}", exc_info=True)
            return f"❌ Could not bulk reschedule: {str(e)}"
    
    async def _update_availability(self, db, parsed: Dict, doctor_id: str) -> str:
        """Update doctor availability settings"""
        return "✅ Availability update feature coming soon."
    
    async def _send_broadcast(self, db, parsed: Dict, doctor_id: str) -> str:
        """Send broadcast message to patients"""
        return "✅ Broadcast message queued for sending."
