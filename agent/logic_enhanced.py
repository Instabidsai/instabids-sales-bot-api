"""
Enhanced Sales Bot with Redis and Notifications
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis
import httpx

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedSalesBot:
    """Sales bot with Redis persistence and real-time notifications"""
    
    def __init__(self):
        """Initialize the enhanced sales bot"""
        # Initialize Anthropic model
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7,
            max_tokens=1000
        )
        
        # Initialize Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Notification settings
        self.webhook_url = os.getenv("NOTIFICATION_WEBHOOK")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK")
        
        logger.info("Enhanced sales bot initialized with Redis support")
    
    async def _get_conversation(self, thread_id: str) -> Dict[str, Any]:
        """Get conversation from Redis"""
        key = f"conversation:{thread_id}"
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        else:
            # Create new conversation
            return {
                "thread_id": thread_id,
                "stage": "greeting",
                "context": {
                    "message_count": 0,
                    "created_at": datetime.utcnow().isoformat()
                },
                "history": [],
                "lead_info": {}
            }
    
    async def _save_conversation(self, thread_id: str, conversation: Dict[str, Any]):
        """Save conversation to Redis with TTL of 30 days"""
        key = f"conversation:{thread_id}"
        await self.redis.setex(
            key, 
            30 * 24 * 60 * 60,  # 30 days TTL
            json.dumps(conversation)
        )
        
        # Also publish to real-time channel
        await self.redis.publish(
            f"conversation_updates",
            json.dumps({
                "thread_id": thread_id,
                "stage": conversation["stage"],
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    
    async def _send_notification(self, thread_id: str, stage: str, conversation: Dict[str, Any]):
        """Send notifications when important stages are reached"""
        # Prepare notification data
        notification_data = {
            "thread_id": thread_id,
            "stage": stage,
            "timestamp": datetime.utcnow().isoformat(),
            "lead_info": conversation.get("lead_info", {}),
            "context": conversation.get("context", {}),
            "conversation_summary": self._summarize_conversation(conversation)
        }
        
        # Send to webhook if configured
        if self.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.webhook_url,
                        json=notification_data,
                        timeout=10.0
                    )
                logger.info(f"Webhook notification sent for {thread_id} at stage {stage}")
            except Exception as e:
                logger.error(f"Failed to send webhook: {e}")
        
        # Send to Slack if configured
        if self.slack_webhook and stage in ["proposal", "booking"]:
            try:
                slack_message = {
                    "text": f"🎯 New Lead at {stage.upper()} stage!",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*New Lead Progress: {stage.upper()}*\n"
                                       f"Thread: `{thread_id}`\n"
                                       f"Business: {notification_data['lead_info'].get('business_type', 'Unknown')}\n"
                                       f"Budget: {notification_data['context'].get('budget', 'Not specified')}"
                            }
                        }
                    ]
                }
                
                async with httpx.AsyncClient() as client:
                    await client.post(self.slack_webhook, json=slack_message)
                logger.info(f"Slack notification sent for {thread_id}")
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
        
        # Store lead in database when they reach booking
        if stage == "booking":
            await self._store_lead(thread_id, conversation)
    
    async def _store_lead(self, thread_id: str, conversation: Dict[str, Any]):
        """Store qualified lead information"""
        lead_key = f"lead:{thread_id}"
        lead_data = {
            "thread_id": thread_id,
            "created_at": conversation["context"].get("created_at"),
            "reached_booking_at": datetime.utcnow().isoformat(),
            "business_type": conversation["context"].get("business_type"),
            "budget": conversation["context"].get("budget"),
            "timeline": conversation["context"].get("timeline"),
            "features": conversation["context"].get("features", []),
            "email": conversation["lead_info"].get("email"),
            "name": conversation["lead_info"].get("name"),
            "company": conversation["lead_info"].get("company"),
            "conversation_summary": self._summarize_conversation(conversation)
        }
        
        # Store in Redis (in production, use PostgreSQL)
        await self.redis.setex(
            lead_key,
            90 * 24 * 60 * 60,  # 90 days TTL
            json.dumps(lead_data)
        )
        
        # Add to leads list
        await self.redis.lpush("leads:all", thread_id)
        
        logger.info(f"Lead stored: {thread_id}")
    
    def _summarize_conversation(self, conversation: Dict[str, Any]) -> str:
        """Create a summary of the conversation for notifications"""
        summary_parts = []
        
        # Extract key information
        context = conversation.get("context", {})
        
        if "business_type" in context:
            summary_parts.append(f"Business: {context['business_type']}")
        
        if "budget" in context:
            summary_parts.append(f"Budget: {context['budget']}")
        
        if "timeline" in context:
            summary_parts.append(f"Timeline: {context['timeline']}")
        
        if "features" in context and context["features"]:
            summary_parts.append(f"Key requirements: {', '.join(context['features'][:3])}")
        
        return " | ".join(summary_parts) if summary_parts else "No summary available"
    
    def _extract_lead_info(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lead contact information from messages"""
        lead_info = context.get("lead_info", {})
        
        # Simple email extraction (in production, use proper regex)
        if "@" in message and "." in message:
            words = message.split()
            for word in words:
                if "@" in word and "." in word:
                    lead_info["email"] = word.strip(".,!?")
        
        return lead_info
    
    async def process_message(self, message: str, thread_id: str = "default") -> str:
        """Process a user message and return bot response"""
        try:
            # Get conversation from Redis
            conversation = await self._get_conversation(thread_id)
            
            # Update context
            conversation["context"]["message_count"] += 1
            conversation["lead_info"] = self._extract_lead_info(
                message, 
                conversation
            )
            
            # [Rest of the processing logic remains the same as original]
            # ... (stage determination, prompt generation, etc.)
            
            # Get current stage for notification check
            current_stage = conversation["stage"]
            
            # Determine next stage
            next_stage = self._determine_next_stage(
                current_stage, 
                message, 
                conversation["context"]
            )
            
            # Send notification if stage changed
            if current_stage != next_stage:
                await self._send_notification(thread_id, next_stage, conversation)
            
            # Generate response (using same logic as before)
            system_prompt = self._get_system_prompt(next_stage, conversation["context"])
            messages = [SystemMessage(content=system_prompt)]
            
            # Add history
            for msg in conversation["history"][-6:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=message))
            
            # Get LLM response
            response = self.llm.invoke(messages)
            bot_message = response.content
            
            # Update conversation
            conversation["stage"] = next_stage
            conversation["history"].append({"role": "user", "content": message})
            conversation["history"].append({"role": "assistant", "content": bot_message})
            conversation["context"]["last_updated"] = datetime.utcnow().isoformat()
            
            # Save to Redis
            await self._save_conversation(thread_id, conversation)
            
            logger.info(f"Thread {thread_id} - Stage: {next_stage}")
            
            return bot_message
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error. Could you please try again?"
    
    async def get_all_conversations(self) -> list:
        """Get all active conversations"""
        pattern = "conversation:*"
        conversations = []
        
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)
            if data:
                conv = json.loads(data)
                conversations.append({
                    "thread_id": conv["thread_id"],
                    "stage": conv["stage"],
                    "message_count": conv["context"]["message_count"],
                    "created_at": conv["context"].get("created_at"),
                    "last_updated": conv["context"].get("last_updated"),
                    "summary": self._summarize_conversation(conv)
                })
        
        return sorted(conversations, key=lambda x: x.get("last_updated", ""), reverse=True)
    
    async def get_conversation_details(self, thread_id: str) -> Dict[str, Any]:
        """Get full conversation details"""
        return await self._get_conversation(thread_id)
    
    async def get_all_leads(self) -> list:
        """Get all qualified leads"""
        leads = []
        lead_ids = await self.redis.lrange("leads:all", 0, -1)
        
        for lead_id in lead_ids:
            lead_data = await self.redis.get(f"lead:{lead_id}")
            if lead_data:
                leads.append(json.loads(lead_data))
        
        return sorted(leads, key=lambda x: x.get("reached_booking_at", ""), reverse=True)
    
    # Include all the original methods (_get_system_prompt, _determine_next_stage, etc.)
    # [These remain the same as in the original code]
    
    def _get_system_prompt(self, stage: str, context: Dict[str, Any]) -> str:
        """Get the appropriate system prompt based on conversation stage"""
        
        base_prompt = """You are a friendly sales bot for a software development agency. 
Your goal is to understand the prospect's needs and guide them to book a strategy call.

Current conversation stage: {stage}
Conversation context: {context}

Important rules:
1. Be conversational and friendly
2. Ask one question at a time
3. Keep responses concise (2-3 sentences max)
4. Don't mention the stage names to the user
5. Progress naturally through the conversation
"""
        
        stage_prompts = {
            "greeting": """
You're in the GREETING stage. Welcome the user warmly and ask about their business.
Example: "Hi! I'm excited to learn about your MVP idea. What kind of business are you running?"
""",
            
            "understanding": """
You're in the UNDERSTANDING stage. You've learned: {context}
Ask 1-2 more questions to understand their business better.
Focus on: industry, target customers, main challenges, or growth goals.
""",
            
            "identify_mvp": """
You're in the IDENTIFY MVP stage. Based on what you know: {context}
Suggest a specific MVP idea that would help their business.
Be specific about what it would do and why it would help them.
Ask if this resonates or if they had something else in mind.
""",
            
            "scoping": """
You're in the SCOPING stage. The user is interested in: {context}
Ask specific questions to scope the MVP:
- Key features needed
- Integration requirements  
- Timeline expectations
- Rough budget range
One question at a time!
""",
            
            "proposal": """
You're in the PROPOSAL stage. You have enough info: {context}
Create a brief MVP proposal with:
- Overview (2-3 sentences)
- 3-5 key features
- Timeline estimate (4-8 weeks typical)
- Rough cost range based on complexity
Keep it concise and clear.
""",
            
            "booking": """
You're in the BOOKING stage. The user is interested in your proposal.
Invite them to book a strategy call to discuss details.
Share the Calendly link: https://calendly.com/example/strategy-call
Be enthusiastic but professional.
"""
        }
        
        prompt = base_prompt.format(stage=stage, context=json.dumps(context, indent=2))
        if stage in stage_prompts:
            prompt += stage_prompts[stage].format(context=json.dumps(context, indent=2))
        
        return prompt
    
    def _determine_next_stage(self, current_stage: str, user_message: str, context: Dict[str, Any]) -> str:
        """Determine what stage to move to based on conversation progress"""
        
        # Simple rule-based progression
        if current_stage == "greeting":
            # After greeting, move to understanding
            return "understanding"
        
        elif current_stage == "understanding":
            # Move to MVP identification after 2-3 exchanges
            message_count = context.get("message_count", 0)
            if message_count >= 3:  # After 3 messages total
                return "identify_mvp"
            return "understanding"
        
        elif current_stage == "identify_mvp":
            # Check if user expressed interest in the MVP idea
            positive_signals = ["yes", "sounds good", "interested", "tell me more", "like that", "perfect", "great", "need"]
            if any(signal in user_message.lower() for signal in positive_signals):
                return "scoping"
            # Don't get stuck here - move to scoping after a couple tries
            if context.get("message_count", 0) >= 5:
                return "scoping"
            return "identify_mvp"
        
        elif current_stage == "scoping":
            # Move to proposal after gathering enough details
            message_lower = user_message.lower()
            if "week" in message_lower or "budget" in message_lower or "$" in message_lower:
                context["timeline"] = True
                context["budget"] = True
            if "feature" in message_lower or "need" in message_lower or "tracking" in message_lower:
                if "features" not in context:
                    context["features"] = []
                if isinstance(context.get("features"), list):
                    context["features"].append(user_message)
                
            # If we have timeline and budget info, move to proposal
            if context.get("timeline") and context.get("budget"):
                return "proposal"
            # Don't get stuck - move after enough messages
            if context.get("message_count", 0) >= 7:
                return "proposal"
            return "scoping"
        
        elif current_stage == "proposal":
            # Move to booking if they show interest
            positive_signals = ["sounds good", "interested", "yes", "let's", "schedule", "love", "great", "discuss"]
            if any(signal in user_message.lower() for signal in positive_signals):
                return "booking"
            return "proposal"
        
        elif current_stage == "booking":
            # Stay in booking stage
            return "booking"
        
        # Default: stay in current stage
        return current_stage
    
    def _extract_context_from_message(self, stage: str, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from user message to update context"""
        
        # Simple extraction based on keywords (in production, use NLP)
        if stage == "understanding":
            # Look for business type keywords
            if "e-commerce" in user_message.lower() or "online store" in user_message.lower():
                context["business_type"] = "e-commerce"
            if "saas" in user_message.lower() or "software" in user_message.lower():
                context["business_type"] = "SaaS"
                
        elif stage == "scoping":
            # Look for timeline mentions
            if "weeks" in user_message.lower() or "month" in user_message.lower():
                context["timeline"] = user_message
            # Look for budget mentions
            if "$" in user_message or "budget" in user_message.lower():
                context["budget"] = user_message
            # Look for feature mentions
            if any(word in user_message.lower() for word in ["need", "feature", "want", "require"]):
                if "features" not in context:
                    context["features"] = []
                context["features"].append(user_message)
        
        return context
