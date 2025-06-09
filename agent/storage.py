import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class ConversationStorage:
    """Handle conversation storage and notifications"""
    
    def __init__(self):
        # Initialize Supabase client (or use PostgreSQL directly)
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_KEY", "")
        )
        
        # Webhook URLs for notifications
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.custom_webhook = os.getenv("CUSTOM_WEBHOOK_URL")
        
    async def save_conversation(self, thread_id: str, stage: str, context: Dict[str, Any], message: str, response: str):
        """Save conversation to database"""
        try:
            # Save to Supabase/PostgreSQL
            data = {
                "thread_id": thread_id,
                "stage": stage,
                "context": json.dumps(context),
                "user_message": message,
                "bot_response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Insert into conversations table
            self.supabase.table("conversations").insert(data).execute()
            
            # Check if this is a key moment to notify
            if stage in ["proposal", "booking"]:
                await self.send_notifications(thread_id, stage, context, message, response)
                
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    async def send_notifications(self, thread_id: str, stage: str, context: Dict[str, Any], message: str, response: str):
        """Send real-time notifications"""
        
        # Prepare notification data
        notification = {
            "thread_id": thread_id,
            "stage": stage,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "last_exchange": {
                "user": message,
                "bot": response
            }
        }
        
        # Extract key information for MVP building
        if stage == "proposal":
            notification["mvp_details"] = {
                "business_type": context.get("business_type"),
                "timeline": context.get("timeline"),
                "budget": context.get("budget"),
                "features": context.get("features", [])
            }
        
        # Send to Slack
        if self.slack_webhook:
            await self._send_slack_notification(notification)
        
        # Send to Discord
        if self.discord_webhook:
            await self._send_discord_notification(notification)
        
        # Send to custom webhook (your backend)
        if self.custom_webhook:
            await self._send_custom_webhook(notification)
    
    async def _send_slack_notification(self, data: Dict[str, Any]):
        """Send to Slack"""
        try:
            async with httpx.AsyncClient() as client:
                slack_message = {
                    "text": f"🎯 New Sales Bot Lead - Stage: {data['stage']}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Thread ID:* {data['thread_id']}\n*Stage:* {data['stage']}"
                            }
                        }
                    ]
                }
                
                if data['stage'] == 'proposal':
                    mvp = data.get('mvp_details', {})
                    slack_message["blocks"].append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*MVP Details:*\n• Business: {mvp.get('business_type')}\n• Timeline: {mvp.get('timeline')}\n• Budget: {mvp.get('budget')}"
                        }
                    })
                
                await client.post(self.slack_webhook, json=slack_message)
                
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
    
    async def _send_custom_webhook(self, data: Dict[str, Any]):
        """Send to your custom backend"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.custom_webhook, json=data)
        except Exception as e:
            logger.error(f"Custom webhook error: {e}")
    
    async def create_lead(self, thread_id: str, context: Dict[str, Any]):
        """Create a lead/opportunity in your CRM"""
        try:
            lead_data = {
                "thread_id": thread_id,
                "business_type": context.get("business_type"),
                "timeline": context.get("timeline"),
                "budget": context.get("budget"),
                "features": context.get("features", []),
                "status": "qualified",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Save to leads table
            self.supabase.table("leads").insert(lead_data).execute()
            
            # If using HubSpot, Salesforce, etc.
            if os.getenv("HUBSPOT_API_KEY"):
                await self._create_hubspot_deal(lead_data)
                
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
    
    async def get_conversation_history(self, thread_id: str):
        """Retrieve full conversation history"""
        try:
            result = self.supabase.table("conversations")\
                .select("*")\
                .eq("thread_id", thread_id)\
                .order("timestamp")\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []
