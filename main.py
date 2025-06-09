"""
FastAPI application for the Sales Bot
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.logic import SalesBot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot instance
bot_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    global bot_instance
    logger.info("Initializing Sales Bot...")
    bot_instance = SalesBot()
    logger.info("Sales Bot initialized successfully")
    yield
    logger.info("Shutting down Sales Bot...")


# Create FastAPI app
app = FastAPI(
    title="Sales Bot API",
    description="Conversational AI sales bot that follows a structured flow",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if bot_instance else "initializing",
        timestamp=datetime.utcnow().isoformat(),
        version=os.getenv("GIT_SHA", "1.0.0")
    )


# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message"""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot is still initializing")
    
    try:
        logger.info(f"Processing message from thread {request.thread_id}: {request.message}")
        
        # Process the message
        response = await bot_instance.process_message(
            message=request.message,
            thread_id=request.thread_id
        )
        
        return ChatResponse(
            response=response,
            thread_id=request.thread_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Reset conversation endpoint
@app.post("/reset/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reset a conversation thread"""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot is still initializing")
    
    try:
        bot_instance.reset_conversation(thread_id)
        return {"message": f"Conversation reset for thread: {thread_id}"}
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sales Bot API is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "reset": "/reset/{thread_id}",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )