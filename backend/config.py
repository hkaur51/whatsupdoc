from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    MONGO_URL: str = os.environ['MONGO_URL']
    DB_NAME: str = os.environ['DB_NAME']
    CORS_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')
    EMERGENT_LLM_KEY: str = os.environ.get('EMERGENT_LLM_KEY', '')
    WHATSAPP_MOCK_MODE: bool = os.environ.get('WHATSAPP_MOCK_MODE', 'true').lower() == 'true'
    WHATSAPP_API_TOKEN: str = os.environ.get('WHATSAPP_API_TOKEN', '')
    WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    WHATSAPP_VERIFY_TOKEN: str = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'whatsup_doc_verify_token')
    BASE_URL: str = os.environ.get('BASE_URL', '')  # e.g. https://your-app.onrender.com for calendar.ics links

    # Twilio WhatsApp Sandbox config
    TWILIO_ACCOUNT_SID: str = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN: str = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER: str = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Sandbox default
    WHATSAPP_BACKEND: str = os.environ.get('WHATSAPP_BACKEND', 'mock')  # 'mock', 'twilio', 'meta', or 'web'

    # Auth
    JWT_SECRET: str = os.environ.get('JWT_SECRET', 'dev-secret-change-me')

    # LLM (DSPy + Gemini free tier)
    GEMINI_API_KEY: str = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL: str = os.environ.get('GEMINI_MODEL', 'gemini/gemini-2.0-flash')

settings = Settings()
