from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from database import get_database
from config import settings
from models import MessageCreate, MessageRole
from services.whatsapp_service import WhatsAppService
from services.patient_intent_service import PatientIntentService
from services.doctor_command_service import DoctorCommandService
from services.doctor_command_executor import DoctorCommandExecutor
from services.patient_command_executor import PatientCommandExecutor
from services.conversation_state_manager import ConversationStateManager
from services.escalation_service import EscalationService, SAFETY_REPLY
from services.translation_service import TranslationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

whatsapp_service = WhatsAppService()
patient_intent_service = PatientIntentService()
doctor_command_service = DoctorCommandService()
doctor_command_executor = DoctorCommandExecutor()
patient_command_executor = PatientCommandExecutor()
escalation_service = EscalationService()
translation_service = TranslationService()

CONSENT_REQUEST_TEXT = (
    "By continuing this chat, you consent to receive appointment-related "
    "communication from the clinic on WhatsApp."
)

@router.get("/whatsapp")
async def verify_webhook(request: Request, mode: str = Query(None, alias="hub.mode"), 
                        token: str = Query(None, alias="hub.verify_token"),
                        challenge: str = Query(None, alias="hub.challenge")):
    """WhatsApp webhook verification endpoint"""
    logger.info(f"Webhook verification request: mode={mode}, token={token}")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN and challenge:
        logger.info("Webhook verified successfully")
        return int(challenge)
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
    """Detect if sender is doctor or patient (by phone lookup)."""
    doctor = await db.doctors.find_one({"phone": phone, "clinic_id": clinic_id, "is_active": True})
    if doctor:
        logger.info("Detected %s as DOCTOR", phone)
        return MessageRole.DOCTOR
    patient = await db.patients.find_one({"phone": phone})
    if patient:
        logger.info("Detected %s as PATIENT", phone)
        return MessageRole.PATIENT
    logger.info("Detected %s as new PATIENT (default)", phone)
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
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.patients.insert_one(patient_doc)
            patient = patient_doc

        patient_id = patient["id"]

        # First-time consent: send spec message and record timestamp when they agree
        if patient.get("consent_status") == "pending":
            await handle_consent_flow(db, phone, message_text, patient_id, clinic_id)
            return

        # Name collection: ask for name after consent if not yet provided
        if not patient.get("name"):
            await handle_name_collection(db, phone, message_text, patient_id)
            return
        
        # Clinical/urgent: do not answer clinically; send safety message and forward to clinic
        is_urgent = escalation_service.detect_escalation(message_text)
        if is_urgent:
            await handle_escalation(db, phone, message_text, clinic_id, patient_id)
            message_log.original_text = message_text
            message_log.detected_language = (await translation_service.detect_language(message_text))[0]
            message_log.action_taken = "clinical_escalation"
            message_log.result_status = "escalated"
            message_doc = message_log.model_dump()
            message_doc["id"] = str(uuid.uuid4())
            message_doc["whatsapp_message_id"] = whatsapp_msg_id
            message_doc["created_at"] = datetime.now(timezone.utc).isoformat()
            if hasattr(message_log, "translated_to_language"):
                message_doc["translated_to_language"] = None
            await db.messages.insert_one(message_doc)
            return

        # Translate to doctor language for internal use; store original + translated in logs
        doctor = await db.doctors.find_one({"clinic_id": clinic_id, "is_active": True})
        doctor_lang = (doctor.get("preferred_language") or "en") if doctor else "en"
        translated_to_doctor, detected_lang, trans_confidence = await translation_service.translate_to_doctor_language(
            message_text, doctor_lang
        )
        message_log.detected_language = detected_lang
        message_log.translated_text = translated_to_doctor
        message_log.translated_to_language = doctor_lang
        # Update patient preferred_language from detection if not set
        if not patient.get("preferred_language") or patient.get("preferred_language") == "en":
            await db.patients.update_one(
                {"id": patient_id},
                {"$set": {"preferred_language": detected_lang}}
            )

        # Check conversation state (for multi-turn flows like booking)
        state_manager = ConversationStateManager(db)
        current_state = await state_manager.get_state(patient_id)
        
        response_text = None
        
        if current_state:
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
            # Use translated text for intent so doctor-side logic sees consistent language
            parsed_intent = await patient_intent_service.parse_intent(translated_to_doctor)
            parsed_intent["detected_language"] = detected_lang
            message_log.parsed_intent = parsed_intent
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

        patient_lang = patient.get("preferred_language") or detected_lang or "en"
        reply_to_send, _ = await translation_service.translate_to_patient_language(
            response_text, patient_lang
        )
        await whatsapp_service.send_message(phone, reply_to_send)

    except Exception as e:
        logger.error("Error handling patient message: %s", e, exc_info=True)
        await whatsapp_service.send_message(phone, "Sorry, I couldn't process your message. Please try again.")


async def handle_consent_flow(db, phone: str, message_text: str, patient_id: str, clinic_id: str):
    """Handle consent flow for new patients. Record consent_text and consent_timestamp."""
    consent_keywords = ["yes", "haan", "ha", "okay", "ok", "sure", "agree", "\u0939\u093e\u0902"]
    if any(keyword in message_text.lower() for keyword in consent_keywords):
        now = datetime.now(timezone.utc)
        await db.patients.update_one(
            {"id": patient_id},
            {"$set": {"consent_status": "given"}}
        )
        consent_doc = {
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "clinic_id": clinic_id,
            "status": "given",
            "consent_text": CONSENT_REQUEST_TEXT,
            "consent_timestamp": now.isoformat(),
            "requested_at": now.isoformat(),
            "responded_at": now.isoformat(),
        }
        await db.consents.insert_one(consent_doc)
        await whatsapp_service.send_message(
            phone,
            "Thank you! Before we begin, what is your name?"
        )
    else:
        await whatsapp_service.send_message(phone, CONSENT_REQUEST_TEXT)


async def handle_name_collection(db, phone: str, message_text: str, patient_id: str):
    """Collect patient name after consent is given."""
    name = message_text.strip()
    # Basic validation: name should be at least 2 chars and look like a name
    if len(name) < 2 or name.isdigit():
        await whatsapp_service.send_message(phone, "Please enter your full name.")
        return

    # Capitalize properly
    name = " ".join(word.capitalize() for word in name.split())

    await db.patients.update_one(
        {"id": patient_id},
        {"$set": {"name": name}}
    )
    await whatsapp_service.send_message(
        phone,
        f"Welcome, {name}! How can I help you today?\n\n"
        "• Book an appointment\n• Check your appointments\n• Reschedule or cancel\n\n"
        "Just tell me what you need!"
    )


async def handle_escalation(db, phone: str, message_text: str, clinic_id: str, patient_id: str):
    """Handle clinical/urgent messages: send exact safety reply and forward to clinic."""
    await whatsapp_service.send_message(phone, SAFETY_REPLY)
    clinic = await db.clinics.find_one({"id": clinic_id}, {"_id": 0})
    forward_to = (clinic.get("phone") or "").strip() if clinic else ""
    if not forward_to:
        doctor = await db.doctors.find_one({"clinic_id": clinic_id, "is_active": True})
        if doctor:
            forward_to = doctor.get("phone", "")
    if forward_to:
        await whatsapp_service.send_message(
            forward_to,
            f"Escalated message from patient {phone}:\n\n{message_text}"
        )
    escalation_doc = {
        "id": str(uuid.uuid4()),
        "clinic_id": clinic_id,
        "patient_id": patient_id,
        "phone": phone,
        "message": message_text,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    await db.escalations.insert_one(escalation_doc)
    logger.warning("ESCALATION: Patient %s - %s", phone, message_text[:200])

async def execute_doctor_command(db, parsed_command: Dict, clinic_id: str, doctor_phone: str) -> str:
    """Execute parsed doctor command and return response."""
    return await doctor_command_executor.execute(parsed_command, clinic_id, doctor_phone)
