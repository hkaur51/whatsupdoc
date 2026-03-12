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

settings = Settings()
