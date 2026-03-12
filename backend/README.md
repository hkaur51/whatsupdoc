# WhatsUpDoc Backend

A WhatsApp-first scheduling and communication assistant for medical and dental professionals in India.

## Overview

WhatsUpDoc enables doctors and patients to manage appointments through natural WhatsApp conversations in multiple Indian languages. The system uses AI (Gemini 3 Flash) to understand natural language commands and intents.

## Core Features

### 1. Patient Message Gatekeeper
- Auto-detect patient role
- Consent flow for new patients
- Language detection (English, Hindi, Hinglish, Punjabi, Tamil, Telugu, etc.)
- Emergency escalation for clinical concerns

### 2. Appointment Booking
- Natural language appointment requests
- Smart slot suggestions
- Booking confirmation
- Cancellation and rescheduling

### 3. Doctor Natural Language Commands
- "Block tomorrow 10 to 1 for surgery"
- "Schedule Ramesh Friday 5 pm"
- "Vacation 5 June to 12 June"
- "Cancel Neha tomorrow"
- "Show tomorrow appointments"

### 4. Emergency Escalation
- Detects urgent keywords (pain, bleeding, severe, dard, sujan, etc.)
- Safe escalation message (no medical advice)
- Notifies clinic staff
- Logs urgent cases

## Architecture

```
backend/
├── server.py                 # FastAPI app entrypoint
├── config.py                 # Environment configuration
├── database.py              # MongoDB connection
├── setup_clinic.py          # Initial setup script
├── models/                  # Pydantic models
│   ├── clinic.py
│   ├── doctor.py
│   ├── patient.py
│   ├── appointment.py
│   ├── calendar_block.py
│   ├── message.py
│   └── consent.py
├── routers/                 # API endpoints
│   ├── webhook.py           # WhatsApp webhook
│   ├── doctors.py
│   ├── patients.py
│   ├── appointments.py
│   └── health.py
└── services/                # Business logic
    ├── whatsapp_service.py           # WhatsApp messaging (mock mode)
    ├── patient_intent_service.py     # Patient NL parser (Gemini)
    ├── doctor_command_service.py     # Doctor NL parser (Gemini)
    ├── appointment_service.py        # Appointment management
    ├── availability_service.py       # Calendar/availability
    ├── escalation_service.py         # Urgent case detection
    └── translation_service.py        # Multilingual translation
```

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB (async with Motor)
- **AI**: Gemini 3 Flash (via Emergent LLM key)
- **Integration**: WhatsApp Business Cloud API (mock mode by default)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
```

Key variables:
- `MONGO_URL`: MongoDB connection string (default: localhost:27017)
- `DB_NAME`: Database name (default: test_database)
- `EMERGENT_LLM_KEY`: Already configured
- `WHATSAPP_MOCK_MODE`: Set to `true` for testing (logs to console)

### 3. Initialize Clinic Data

Run the setup script to create your first clinic and doctor:

```bash
python3 setup_clinic.py
```

This will prompt you to enter:
- Clinic WhatsApp phone number
- Clinic name
- Doctor WhatsApp phone number
- Doctor name
- Optional test patient

### 4. Start the Server

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Or use supervisor (already configured in production environment).

## API Endpoints

### Health Check
```
GET /api/health
```

### WhatsApp Webhook
```
GET  /api/webhook/whatsapp  # Webhook verification
POST /api/webhook/whatsapp  # Receive messages
```

### Doctors
```
GET  /api/doctors           # List doctors
POST /api/doctors           # Create doctor
GET  /api/doctors/{id}      # Get doctor by ID
```

### Patients
```
GET  /api/patients          # List patients
POST /api/patients          # Create patient
GET  /api/patients/{id}     # Get patient by ID
```

### Appointments
```
GET    /api/appointments              # List appointments
POST   /api/appointments              # Create appointment
GET    /api/appointments/{id}         # Get appointment
PATCH  /api/appointments/{id}/cancel  # Cancel appointment
```

## Testing in Mock Mode

### Test Patient Message

```bash
curl -X POST http://localhost:8001/api/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "+919876543210",
            "id": "test123",
            "text": {
              "body": "Can I come tomorrow?"
            }
          }]
        }
      }]
    }]
  }'
```

Check the console logs for the mock WhatsApp response.

### Test Doctor Command

```bash
curl -X POST http://localhost:8001/api/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "+919123456789",
            "id": "test456",
            "text": {
              "body": "Block tomorrow 10 to 1 for surgery"
            }
          }]
        }
      }]
    }]
  }'
```

(Use the doctor phone number you configured during setup)

## Natural Language Examples

### Patient Messages (English)
- "Can I come tomorrow?"
- "Need appointment Friday evening"
- "Cancel my appointment"
- "When is my next appointment?"

### Patient Messages (Hindi/Hinglish)
- "Kal appointment mil sakti hai?"
- "Mujhe dentist se milna hai"
- "Appointment cancel karni hai"
- "Mera next appointment kab hai?"

### Doctor Commands
- "Block tomorrow 10 to 1 for surgery"
- "Schedule Ramesh Friday 5 pm"
- "Vacation 5 June to 12 June"
- "Cancel Neha tomorrow"
- "Show tomorrow appointments"
- "No appointments after 3 pm this week"

### Escalation Examples
- "I have severe pain" → Auto-escalates
- "Bohot dard hai" → Auto-escalates
- "Bleeding won't stop" → Auto-escalates

## WhatsApp Integration (Production)

To enable real WhatsApp messaging:

1. Get WhatsApp Business API credentials from Meta
2. Update `.env`:
   ```
   WHATSAPP_MOCK_MODE=false
   WHATSAPP_API_TOKEN=your-token-here
   WHATSAPP_PHONE_NUMBER_ID=your-phone-id-here
   WHATSAPP_VERIFY_TOKEN=your-verify-token
   ```

3. Configure webhook URL in Meta Developer Portal:
   ```
   https://your-domain.com/api/webhook/whatsapp
   ```

4. Restart the server

## Database Collections

- `clinics`: Clinic configurations
- `doctors`: Doctor profiles
- `patients`: Patient profiles
- `appointments`: Scheduled appointments
- `calendar_blocks`: Doctor unavailability blocks
- `messages`: Message logs (for auditing)
- `consents`: Patient consent records
- `escalations`: Urgent case tracking

## Message Flow

1. WhatsApp message arrives → `/api/webhook/whatsapp`
2. System detects sender role (doctor/patient)
3. For patients:
   - Check consent status
   - Detect escalation keywords
   - Parse intent using Gemini
   - Execute action (book/cancel/reschedule)
   - Send confirmation
4. For doctors:
   - Parse command using Gemini
   - Execute command (block/schedule/vacation)
   - Send confirmation
5. All messages logged to database

## Multilingual Support

The system automatically:
- Detects incoming message language
- Translates patient messages to doctor's preferred language
- Translates doctor replies back to patient's language
- Logs both original and translated text

Supported languages:
- English
- Hindi
- Hinglish (Hindi-English mix)
- Punjabi
- Tamil
- Telugu
- Bengali
- Marathi
- Gujarati
- Kannada
- Malayalam
- Urdu

## Safety & Compliance

### Medical Safety
- System does NOT provide medical advice
- Clinical keywords trigger safe escalation
- Urgent messages forwarded to staff
- Clear disclaimers for emergency situations

### Data Minimization
Stores only:
- Clinic/doctor/patient basic info
- Appointment data
- Message logs (for auditing)
- Consent records

Does NOT store:
- Diagnosis notes
- Treatment plans
- Prescriptions
- Medical images
- Detailed health records

## TODO Markers

Current implementation has full working logic for MVP scope:
- ✅ Patient gatekeeper
- ✅ Appointment booking flow
- ✅ Doctor command parsing
- ✅ Emergency escalation
- ✅ Consent management
- ✅ Message logging

Future enhancements:
- Real-time slot availability calculation
- SMS/Email reminders
- Multi-doctor clinic support
- Advanced calendar conflict resolution
- Analytics dashboard
- Patient reminder system

## Development

### Run Tests
```bash
pytest tests/
```

### Lint Code
```bash
ruff check .
```

### Format Code
```bash
black .
```

## Support

For issues or questions:
1. Check logs: `/var/log/supervisor/backend.*.log`
2. Test health endpoint: `GET /api/health`
3. Verify MongoDB connection
4. Check Emergent LLM key balance

## License

Proprietary - WhatsUpDoc MVP
