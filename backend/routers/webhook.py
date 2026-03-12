from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any
import logging
from database import get_database
from services.whatsapp_service import WhatsAppService
from services.patient_intent_service import PatientIntentService
from services.doctor_command_service import DoctorCommandService
from services.doctor_command_executor import DoctorCommandExecutor
from services.patient_command_executor import PatientCommandExecutor
from services.conversation_state_manager import ConversationStateManager
from services.escalation_service import EscalationService
from models import MessageCreate, MessageRole
import uuid
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

whatsapp_service = WhatsAppService()
patient_intent_service = PatientIntentService()
doctor_command_service = DoctorCommandService()
doctor_command_executor = DoctorCommandExecutor()
patient_command_executor = PatientCommandExecutor()
escalation_service = EscalationService()

@router.get("/whatsapp")
async def verify_webhook(request: Request, mode: str = Query(None, alias="hub.mode"), 
                        token: str = Query(None, alias="hub.verify_token"),
                        challenge: str = Query(None, alias="hub.challenge")):
    """WhatsApp webhook verification endpoint"""
    logger.info(f"Webhook verification request: mode={mode}, token={token}")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(challenge)
    else:
        logger.warning("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp")
async def receive_message(request: Request):
    """Receive and process incoming WhatsApp messages"""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        if not body.get("entry"):
            return {"status": "ok"}
        
        for entry in body["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                if "messages" in value:
                    for message in value["messages"]:
                        await process_incoming_message(message, value)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def process_incoming_message(message: Dict[str, Any], value: Dict[str, Any]):
    """Process a single incoming WhatsApp message"""
    try:
        sender_phone = message.get("from")
        message_text = message.get("text", {}).get("body", "")
        whatsapp_msg_id = message.get("id")
        
        if not message_text:
            return
        
        logger.info(f"Processing message from {sender_phone}: {message_text}")
        
        db = get_database()
        
        clinic = await db.clinics.find_one({"is_active": True})
        if not clinic:
            logger.error("No active clinic found")
            await whatsapp_service.send_message(
                sender_phone,
                "Sorry, no active clinic configuration found. Please contact support."
            )
            return
        
        clinic_id = clinic["id"]
        
        sender_role = await detect_sender_role(db, sender_phone, clinic_id)
        
        message_log = MessageCreate(
            clinic_id=clinic_id,
            sender_phone=sender_phone,
            sender_role=sender_role,
            original_text=message_text
        )
        
        if sender_role == MessageRole.DOCTOR:
            await handle_doctor_message(db, sender_phone, message_text, clinic_id, message_log, whatsapp_msg_id)
        elif sender_role == MessageRole.PATIENT:
            await handle_patient_message(db, sender_phone, message_text, clinic_id, message_log, whatsapp_msg_id)
        else:
            await whatsapp_service.send_message(
                sender_phone,
                "Welcome! Please register with the clinic first."
            )
    
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

async def detect_sender_role(db, phone: str, clinic_id: str) -> MessageRole:
    """Detect if sender is doctor or patient"""
    doctor = await db.doctors.find_one({"phone": phone, "clinic_id": clinic_id, "is_active": True})
    if doctor:
        logger.info(f"Detected {phone} as DOCTOR")
        return MessageRole.DOCTOR
    
    patient = await db.patients.find_one({"phone": phone})
    if patient:
        logger.info(f"Detected {phone} as PATIENT")
        return MessageRole.PATIENT
    
    logger.info(f"Detected {phone} as new PATIENT (default)")
    return MessageRole.PATIENT

async def handle_doctor_message(db, phone: str, message_text: str, clinic_id: str, 
                                message_log: MessageCreate, whatsapp_msg_id: str):
    """Handle messages from doctors"""
    try:
        parsed_command = await doctor_command_service.parse_command(message_text)
        
        message_log.parsed_intent = parsed_command
        message_log.detected_language = parsed_command.get("detected_language", "en")
        
        response_text = await execute_doctor_command(db, parsed_command, clinic_id, phone)
        
        message_log.action_taken = parsed_command.get("intent", "unknown")
        message_log.result_status = "success"
        
        message_doc = message_log.model_dump()
        message_doc["id"] = str(uuid.uuid4())
        message_doc["whatsapp_message_id"] = whatsapp_msg_id
        message_doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.messages.insert_one(message_doc)
        
        await whatsapp_service.send_message(phone, response_text)
    
    except Exception as e:
        logger.error(f"Error handling doctor message: {e}", exc_info=True)
        await whatsapp_service.send_message(phone, f"Sorry, I couldn't process that command. Error: {str(e)}")

async def handle_patient_message(db, phone: str, message_text: str, clinic_id: str,
                                 message_log: MessageCreate, whatsapp_msg_id: str):
    """Handle messages from patients with conversation state support"""
    try:
        patient = await db.patients.find_one({"phone": phone})
        
        if not patient:
            patient_id = str(uuid.uuid4())
            patient_doc = {
                "id": patient_id,
                "phone": phone,
                "name": None,
                "preferred_language": "en",
                "consent_status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.patients.insert_one(patient_doc)
            patient = patient_doc
        
        patient_id = patient["id"]
        
        # Check consent first
        if patient.get("consent_status") == "pending":
            await handle_consent_flow(db, phone, message_text, patient_id, clinic_id)
            return
        
        # Check for escalation
        is_urgent = escalation_service.detect_escalation(message_text)
        if is_urgent:
            await handle_escalation(db, phone, message_text, clinic_id, patient_id)
            return
        
        # Check conversation state (for multi-turn flows like booking)
        state_manager = ConversationStateManager(db)
        current_state = await state_manager.get_state(patient_id)
        
        response_text = None
        
        if current_state:
            # Handle state-based conversation
            state_type = current_state.get("state_type")
            state_data = current_state.get("data", {})
            
            if state_type == "awaiting_slot_selection":
                response_text = await patient_command_executor.handle_slot_selection(
                    message_text, patient_id, state_data, db
                )
                message_log.action_taken = "slot_selection"
            
            elif state_type == "awaiting_reschedule_slot":
                response_text = await patient_command_executor.handle_reschedule_slot_selection(
                    message_text, patient_id, state_data, db
                )
                message_log.action_taken = "reschedule_slot_selection"
        
        if not response_text:
            # Parse intent and execute
            parsed_intent = await patient_intent_service.parse_intent(message_text)
            
            message_log.parsed_intent = parsed_intent
            message_log.detected_language = parsed_intent.get("detected_language", "en")
            
            response_text = await patient_command_executor.execute(
                parsed_intent, patient_id, phone, clinic_id, db
            )
            
            message_log.action_taken = parsed_intent.get("intent", "unknown")
        
        message_log.result_status = "success"
        
        message_doc = message_log.model_dump()
        message_doc["id"] = str(uuid.uuid4())
        message_doc["whatsapp_message_id"] = whatsapp_msg_id
        message_doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.messages.insert_one(message_doc)
        
        await whatsapp_service.send_message(phone, response_text)
    
    except Exception as e:
        logger.error(f"Error handling patient message: {e}", exc_info=True)
        await whatsapp_service.send_message(phone, "Sorry, I couldn't process your message. Please try again.")

async def handle_consent_flow(db, phone: str, message_text: str, patient_id: str, clinic_id: str):
    """Handle consent flow for new patients"""
    consent_keywords = ["yes", "haan", "ha", "okay", "ok", "sure", "agree", "\u0939\u093e\u0902"]
    
    if any(keyword in message_text.lower() for keyword in consent_keywords):
        await db.patients.update_one(
            {"id": patient_id},
            {"$set": {"consent_status": "given"}}
        )
        
        consent_doc = {
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "status": "given",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "responded_at": datetime.now(timezone.utc).isoformat()
        }
        await db.consents.insert_one(consent_doc)
        
        await whatsapp_service.send_message(
            phone,
            "Thank you! How can I help you today? You can:\n\n"
            "\u2022 Book an appointment\n"
            "\u2022 Check your appointments\n"
            "\u2022 Reschedule or cancel\n\n"
            "Just tell me what you need!"
        )
    else:
        await whatsapp_service.send_message(
            phone,
            "Welcome to our clinic! \ud83d\udc4b\n\n"
            "To help you book appointments and get reminders, we need your consent to communicate via WhatsApp.\n\n"
            "Reply 'Yes' or 'Haan' to continue."
        )

async def handle_escalation(db, phone: str, message_text: str, clinic_id: str, patient_id: str):
    """Handle urgent patient messages"""
    await whatsapp_service.send_message(
        phone,
        "\u26a0\ufe0f This automated assistant cannot provide medical advice.\n\n"
        "Your message has been marked as urgent and forwarded to the clinic staff. "
        "Someone will contact you shortly.\n\n"
        "If this is a medical emergency, please call emergency services immediately."
    )
    
    escalation_doc = {
        "id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "phone": phone,
        "message": message_text,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    await db.escalations.insert_one(escalation_doc)
    
    logger.warning(f"ESCALATION: Patient {phone} - {message_text}")

async def execute_doctor_command(db, parsed_command: Dict, clinic_id: str, doctor_phone: str) -> str:
    """Execute parsed doctor command and return response"""
    return await doctor_command_executor.execute(parsed_command, clinic_id, doctor_phone)

from datetime import datetime, timezone
import uuid
