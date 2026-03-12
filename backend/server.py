from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from config import settings
from database import connect_to_mongo, close_mongo_connection
from routers import (
    webhook_router,
    doctors_router,
    patients_router,
    appointments_router,
    health_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting WhatsUpDoc API...")
    await connect_to_mongo()
    logger.info("WhatsUpDoc API started successfully")
    yield
    logger.info("Shutting down WhatsUpDoc API...")
    await close_mongo_connection()
    logger.info("WhatsUpDoc API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="WhatsUpDoc API",
    description="WhatsApp-first scheduling assistant for medical professionals",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(webhook_router, prefix="/api")
app.include_router(doctors_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(health_router, prefix="/api")

@app.get("/api")
async def root():
    """Root endpoint"""
    return {
        "service": "WhatsUpDoc API",
        "version": "1.0.0",
        "status": "running",
        "description": "WhatsApp-first scheduling assistant for medical professionals in India",
        "endpoints": {
            "health": "/api/health",
            "webhook": "/api/webhook/whatsapp",
            "doctors": "/api/doctors",
            "patients": "/api/patients",
            "appointments": "/api/appointments"
        }
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)