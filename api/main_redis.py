"""FastAPI server with Redis persistence"""

import os
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvloop

# Import the Redis-enhanced bot
from agent.logic_redis import SalesBotRedis

# Initialize FastAPI app
app = FastAPI(title="Sales Bot API with Redis")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the bot
bot = SalesBotRedis()

@app.get("/")
async def root():
    return {
        "message": "Sales Bot API with Redis is running!",
        "endpoints": [
            "/health",
            "/chat",
            "/reset/{thread_id}",
            "/conversations",
            "/leads",
            "/export/{thread_id}"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "features": ["redis", "notifications", "lead-tracking"]
    }

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        thread_id = data.get("thread_id", "default")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Process message
        response = await bot.process_message(message, thread_id)
        
        # Get current conversation state
        conversation = bot.get_conversation(thread_id)
        
        return JSONResponse(content={
            "response": response,
            "thread_id": thread_id,
            "stage": conversation["stage"] if conversation else "greeting",
            "context": conversation["context"] if conversation else {}
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reset a specific conversation"""
    bot.reset_conversation(thread_id)
    return {"message": f"Conversation {thread_id} reset successfully"}

@app.get("/conversations")
async def get_all_conversations():
    """Get all active conversations"""
    conversations = bot.get_all_conversations()
    return {
        "total": len(conversations),
        "conversations": conversations
    }

@app.get("/leads")
async def get_all_leads():
    """Get all leads that reached booking stage"""
    leads = bot.get_all_leads()
    return {
        "total": len(leads),
        "leads": leads
    }

@app.get("/export/{thread_id}")
async def export_lead_data(thread_id: str):
    """Export complete lead data for MVP building"""
    data = bot.export_lead_data(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return JSONResponse(content=data)

@app.get("/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    """Get a specific conversation"""
    conversation = bot.get_conversation(thread_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return JSONResponse(content=conversation)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, loop="uvloop")