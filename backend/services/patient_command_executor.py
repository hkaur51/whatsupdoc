import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import uuid
from services.appointment_service import AppointmentService
from services.conversation_state_manager import ConversationStateManager

logger = logging.getLogger(__name__)

class PatientCommandExecutor:
    """Execute patient commands with conversational flow support"""
    
    def __init__(self):
        self.appointment_service = AppointmentService()
    
    async def execute(
        self, 
        parsed_intent: Dict[str, Any], 
        patient_id: str, 
        patient_phone: str,
        clinic_id: str,
        db
    ) -> str:
        """Execute patient intent"""
        try:
            intent = parsed_intent.get("intent")
            state_manager = ConversationStateManager(db)
            
            # Route to handler
            if intent == "book_appointment":
                return await self._book_appointment(db, parsed_intent, patient_id, clinic_id, state_manager)
            elif intent == "cancel_appointment":
                return await self._cancel_appointment(db, patient_id)
            elif intent == "check_appointment":
                return await self._check_appointment(db, patient_id)
            elif intent == "reschedule_appointment":
                return await self._reschedule_appointment(db, parsed_intent, patient_id, clinic_id, state_manager)
            elif intent == "ask_availability":
                return await self._ask_availability(db, parsed_intent, clinic_id)
            elif intent == "general_query":
                return await self._handle_general_query(db, clinic_id)
            else:
                return "I can help you book, check, cancel, or reschedule appointments. What would you like to do?"
        
        except Exception as e:
            logger.error(f"Error executing patient command: {e}", exc_info=True)
            return "Sorry, I couldn't process your request. Please try again."
    
    async def handle_slot_selection(
        self,
        message: str,
        patient_id: str,
        state_data: Dict[str, Any],
        db
    ) -> str:
        """Handle slot selection during booking flow"""
        try:
            # Try to parse slot number
            message_clean = message.strip().lower()
            
            # Handle various responses
            slot_number = None
            if message_clean.isdigit():
                slot_number = int(message_clean)
            elif message_clean in ['first', 'one', '1st', 'pehla', 'pahla']:
                slot_number = 1
            elif message_clean in ['second', 'two', '2nd', 'dusra', 'doosra']:
                slot_number = 2
            elif message_clean in ['third', 'three', '3rd', 'teesra']:
                slot_number = 3
            elif message_clean in ['last', 'aakhri']:
                slot_number = len(state_data.get("available_slots", []))
            
            if slot_number is None:
                return "Please reply with the slot number (1, 2, 3, etc.) to book your appointment."
            
            # Get slots from state
            available_slots = state_data.get("available_slots", [])
            
            if slot_number < 1 or slot_number > len(available_slots):
                return f"Please choose a valid slot number between 1 and {len(available_slots)}."
            
            # Get selected slot
            selected_slot = available_slots[slot_number - 1]
            
            # Create appointment
            appointment_id = str(uuid.uuid4())
            appointment_doc = {
                "id": appointment_id,
                "clinic_id": state_data["clinic_id"],
                "doctor_id": state_data["doctor_id"],
                "patient_id": patient_id,
                "appointment_date": selected_slot["date"],
                "appointment_time": selected_slot["time"],
                "duration_minutes": 30,
                "status": "scheduled",
                "reason": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": None
            }
            
            await db.appointments.insert_one(appointment_doc)
            
            # Clear conversation state
            state_manager = ConversationStateManager(db)
            await state_manager.clear_state(patient_id)

            # Format confirmation; add phone calendar link if BASE_URL is set
            date_obj = datetime.strptime(selected_slot["date"], "%Y-%m-%d")
            time_obj = datetime.strptime(selected_slot["time"], "%H:%M")
            try:
                from config import settings
                calendar_note = ""
                if getattr(settings, "BASE_URL", None) and settings.BASE_URL:
                    calendar_note = f"\n\nAdd to your phone calendar: {settings.BASE_URL.rstrip('/')}/api/appointments/{appointment_id}/calendar.ics"
            except Exception:
                calendar_note = ""
            return f"""✅ Your appointment is confirmed!

📅 Date: {date_obj.strftime('%A, %B %d, %Y')}
🕐 Time: {time_obj.strftime('%I:%M %p')}

Please arrive 10 minutes early. If you need to cancel or reschedule, just send me a message.{calendar_note}"""
        
        except Exception as e:
            logger.error(f"Error handling slot selection: {e}", exc_info=True)
            return "Sorry, something went wrong. Please try booking again by typing 'book appointment'."
    
    async def _book_appointment(
        self, 
        db, 
        parsed_intent: Dict, 
        patient_id: str, 
        clinic_id: str,
        state_manager: ConversationStateManager
    ) -> str:
        """Start appointment booking flow"""
        try:
            preferred_date = parsed_intent.get("preferred_date", "tomorrow")
            
            # Calculate target date
            target_date = self._parse_preferred_date(preferred_date)
            
            # Get active doctor (simplified - use first active doctor)
            doctor = await db.doctors.find_one({"clinic_id": clinic_id, "is_active": True})
            if not doctor:
                return "Sorry, no doctor is available right now. Please try again later."
            
            # Get available slots
            slots = await self.appointment_service.get_available_slots(
                clinic_id=clinic_id,
                doctor_id=doctor["id"],
                date=target_date.strftime("%Y-%m-%d"),
                duration_minutes=30
            )
            
            if not slots:
                # Try to find the next working day with slots
                clinic = await db.clinics.find_one({"id": clinic_id})
                working_days = clinic.get("working_hours", {}).get("days", []) if clinic else []
                day_name = target_date.strftime("%A")
                if working_days and day_name not in working_days:
                    return f"Sorry, the clinic is closed on {day_name}s. We're open {', '.join(working_days)}. Would you like to check another day?"
                return f"Sorry, no available slots on {target_date.strftime('%A, %B %d')}. Would you like to check another day?"
            
            # Store conversation state
            await state_manager.set_state(
                patient_id=patient_id,
                state_type="awaiting_slot_selection",
                data={
                    "clinic_id": clinic_id,
                    "doctor_id": doctor["id"],
                    "available_slots": slots,
                    "requested_date": target_date.strftime("%Y-%m-%d")
                },
                ttl_minutes=10
            )
            
            # Format response with available slots
            date_str = target_date.strftime("%A, %B %d")
            response = f"Available slots on {date_str}:\n\n"
            
            for i, slot in enumerate(slots[:5], 1):  # Show max 5 slots
                time_obj = datetime.strptime(slot["time"], "%H:%M")
                response += f"{i}. {time_obj.strftime('%I:%M %p')}\n"
            
            if len(slots) > 5:
                response += f"\n...and {len(slots) - 5} more slots\n"
            
            response += "\nReply with the slot number to book your appointment."
            
            return response
        
        except Exception as e:
            logger.error(f"Error in book appointment: {e}", exc_info=True)
            return "Sorry, I couldn't check availability. Please try again."
    
    async def _cancel_appointment(self, db, patient_id: str) -> str:
        """Cancel patient's appointment"""
        try:
            # Find patient's upcoming appointments
            appointments = await db.appointments.find({
                "patient_id": patient_id,
                "status": {"$in": ["scheduled", "confirmed"]},
                "appointment_date": {"$gte": datetime.now().strftime("%Y-%m-%d")}
            }).sort("appointment_date", 1).to_list(10)
            
            if not appointments:
                return "You don't have any upcoming appointments to cancel."
            
            # Cancel the first (next) appointment
            appointment = appointments[0]
            
            await db.appointments.update_one(
                {"id": appointment["id"]},
                {"$set": {
                    "status": "cancelled",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            date_obj = datetime.strptime(appointment["appointment_date"], "%Y-%m-%d")
            time_obj = datetime.strptime(appointment["appointment_time"], "%H:%M")
            
            return f"""✅ Your appointment has been cancelled.

📅 Date: {date_obj.strftime('%A, %B %d, %Y')}
🕐 Time: {time_obj.strftime('%I:%M %p')}

If you'd like to book a new appointment, just let me know!"""
        
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}", exc_info=True)
            return "Sorry, I couldn't cancel your appointment. Please try again."
    
    async def _check_appointment(self, db, patient_id: str) -> str:
        """Check patient's appointments"""
        try:
            # Find upcoming appointments
            appointments = await db.appointments.find({
                "patient_id": patient_id,
                "status": {"$in": ["scheduled", "confirmed"]},
                "appointment_date": {"$gte": datetime.now().strftime("%Y-%m-%d")}
            }).sort("appointment_date", 1).to_list(10)
            
            if not appointments:
                return "You don't have any upcoming appointments.\n\nWould you like to book one?"
            
            response = "📅 Your upcoming appointments:\n\n"
            
            for i, apt in enumerate(appointments[:3], 1):
                date_obj = datetime.strptime(apt["appointment_date"], "%Y-%m-%d")
                time_obj = datetime.strptime(apt["appointment_time"], "%H:%M")
                
                response += f"{i}. {date_obj.strftime('%a, %b %d')} at {time_obj.strftime('%I:%M %p')}\n"
            
            if len(appointments) > 3:
                response += f"\n...and {len(appointments) - 3} more\n"
            
            response += "\nTo cancel or reschedule, just let me know!"
            
            return response
        
        except Exception as e:
            logger.error(f"Error checking appointment: {e}", exc_info=True)
            return "Sorry, I couldn't check your appointments. Please try again."
    
    async def _reschedule_appointment(
        self,
        db,
        parsed_intent: Dict,
        patient_id: str,
        clinic_id: str,
        state_manager: ConversationStateManager
    ) -> str:
        """Reschedule patient's appointment"""
        try:
            # Find patient's next appointment
            appointments = await db.appointments.find({
                "patient_id": patient_id,
                "status": {"$in": ["scheduled", "confirmed"]},
                "appointment_date": {"$gte": datetime.now().strftime("%Y-%m-%d")}
            }).sort("appointment_date", 1).to_list(10)
            
            if not appointments:
                return "You don't have any upcoming appointments to reschedule.\n\nWould you like to book a new appointment?"
            
            # For simplicity, reschedule the first appointment
            old_appointment = appointments[0]
            
            # Get new date preference
            preferred_date = parsed_intent.get("preferred_date", "tomorrow")
            target_date = self._parse_preferred_date(preferred_date)
            
            # Get available slots
            doctor = await db.doctors.find_one({"clinic_id": clinic_id, "is_active": True})
            if not doctor:
                return "Sorry, no doctor is available right now."
            
            slots = await self.appointment_service.get_available_slots(
                clinic_id=clinic_id,
                doctor_id=doctor["id"],
                date=target_date.strftime("%Y-%m-%d"),
                duration_minutes=30
            )
            
            if not slots:
                return f"Sorry, no available slots on {target_date.strftime('%A, %B %d')}. Would you like another day?"
            
            # Store state with old appointment info
            await state_manager.set_state(
                patient_id=patient_id,
                state_type="awaiting_reschedule_slot",
                data={
                    "clinic_id": clinic_id,
                    "doctor_id": doctor["id"],
                    "available_slots": slots,
                    "old_appointment_id": old_appointment["id"],
                    "requested_date": target_date.strftime("%Y-%m-%d")
                },
                ttl_minutes=10
            )
            
            # Show old appointment and new slots
            old_date = datetime.strptime(old_appointment["appointment_date"], "%Y-%m-%d")
            old_time = datetime.strptime(old_appointment["appointment_time"], "%H:%M")
            
            response = f"Rescheduling your appointment:\n\n"
            response += f"Current: {old_date.strftime('%a, %b %d')} at {old_time.strftime('%I:%M %p')}\n\n"
            response += f"Available slots on {target_date.strftime('%A, %B %d')}:\n\n"
            
            for i, slot in enumerate(slots[:5], 1):
                time_obj = datetime.strptime(slot["time"], "%H:%M")
                response += f"{i}. {time_obj.strftime('%I:%M %p')}\n"
            
            response += "\nReply with the slot number for your new appointment."
            
            return response
        
        except Exception as e:
            logger.error(f"Error rescheduling appointment: {e}", exc_info=True)
            return "Sorry, I couldn't reschedule your appointment. Please try again."
    
    async def handle_reschedule_slot_selection(
        self,
        message: str,
        patient_id: str,
        state_data: Dict[str, Any],
        db
    ) -> str:
        """Handle slot selection for rescheduling"""
        try:
            # Parse slot number
            message_clean = message.strip()
            if not message_clean.isdigit():
                return "Please reply with the slot number to reschedule your appointment."
            
            slot_number = int(message_clean)
            available_slots = state_data.get("available_slots", [])
            
            if slot_number < 1 or slot_number > len(available_slots):
                return f"Please choose a valid slot number between 1 and {len(available_slots)}."
            
            # Get selected slot
            selected_slot = available_slots[slot_number - 1]
            
            # Update old appointment
            await db.appointments.update_one(
                {"id": state_data["old_appointment_id"]},
                {"$set": {
                    "appointment_date": selected_slot["date"],
                    "appointment_time": selected_slot["time"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Clear state
            state_manager = ConversationStateManager(db)
            await state_manager.clear_state(patient_id)
            
            # Confirmation
            date_obj = datetime.strptime(selected_slot["date"], "%Y-%m-%d")
            time_obj = datetime.strptime(selected_slot["time"], "%H:%M")
            
            return f"""✅ Your appointment has been rescheduled!

📅 New Date: {date_obj.strftime('%A, %B %d, %Y')}
🕐 New Time: {time_obj.strftime('%I:%M %p')}

See you then!"""
        
        except Exception as e:
            logger.error(f"Error handling reschedule slot selection: {e}", exc_info=True)
            return "Sorry, something went wrong. Please try again."
    
    async def _ask_availability(self, db, parsed_intent: Dict, clinic_id: str) -> str:
        """Show availability without booking"""
        try:
            preferred_date = parsed_intent.get("preferred_date", "tomorrow")
            target_date = self._parse_preferred_date(preferred_date)
            
            doctor = await db.doctors.find_one({"clinic_id": clinic_id, "is_active": True})
            if not doctor:
                return "Sorry, no doctor is available right now."
            
            slots = await self.appointment_service.get_available_slots(
                clinic_id=clinic_id,
                doctor_id=doctor["id"],
                date=target_date.strftime("%Y-%m-%d"),
                duration_minutes=30
            )
            
            if not slots:
                return f"No available slots on {target_date.strftime('%A, %B %d')}."
            
            response = f"Available slots on {target_date.strftime('%A, %B %d')}:\n\n"
            for slot in slots[:10]:
                time_obj = datetime.strptime(slot["time"], "%H:%M")
                response += f"• {time_obj.strftime('%I:%M %p')}\n"
            
            if len(slots) > 10:
                response += f"\n...and {len(slots) - 10} more slots"
            
            response += "\n\nWould you like to book an appointment?"
            
            return response
        
        except Exception as e:
            logger.error(f"Error checking availability: {e}", exc_info=True)
            return "Sorry, I couldn't check availability. Please try again."
    
    async def _handle_general_query(self, db, clinic_id: str) -> str:
        """Handle general queries"""
        clinic = await db.clinics.find_one({"id": clinic_id})
        if not clinic:
            return "Hello! I can help you book, check, cancel, or reschedule appointments. What would you like to do?"
        
        hours = clinic.get("working_hours", {})
        start = hours.get("start", "9:00 AM")
        end = hours.get("end", "6:00 PM")
        
        return f"""Hello! I'm here to help you with appointments. 🏥

I can help you:
• Book an appointment
• Check your appointments
• Cancel or reschedule
• Check availability

Clinic hours: {start} - {end}

What would you like to do?"""
    
    def _parse_preferred_date(self, preferred_date) -> datetime:
        """Parse preferred date string to datetime"""
        today = datetime.now()

        if not preferred_date:
            return today + timedelta(days=1)

        preferred_date = str(preferred_date).lower()

        if preferred_date in ["tomorrow", "kal"]:
            return today + timedelta(days=1)
        elif preferred_date in ["today", "aaj"]:
            return today
        elif "next week" in preferred_date:
            return today + timedelta(days=7)
        elif "day after tomorrow" in preferred_date:
            return today + timedelta(days=2)
        else:
            # Default to tomorrow
            return today + timedelta(days=1)
