from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

def get_database():
    return Database.db

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    Database.client = AsyncIOMotorClient(settings.MONGO_URL)
    Database.db = Database.client[settings.DB_NAME]
    logger.info(f"Connected to MongoDB database: {settings.DB_NAME}")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    Database.client.close()
    logger.info("MongoDB connection closed")
