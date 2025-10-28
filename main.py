#!/usr/bin/env python3
"""
Smart AI Boot Greeter - Main Entry Point
A modular system that provides intelligent greetings when Linux boot completes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.core.config import settings
from app.services.boot_monitor import BootMonitor
from app.services.greeting_service import GreetingService
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start boot monitoring on startup."""
    logger.info("Starting Smart AI Boot Greeter...")
    
    # Initialize services
    boot_monitor = BootMonitor()
    greeting_service = GreetingService()
    
    # Start boot monitoring in background
    monitor_task = asyncio.create_task(boot_monitor.start_monitoring())
    
    try:
        yield
    finally:
        logger.info("Shutting down Smart AI Boot Greeter...")
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Smart AI Boot Greeter",
    description="Intelligent Linux boot greeting system with natural language processing",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Smart AI Boot Greeter is running", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
