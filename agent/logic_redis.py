"""Sales Bot Agent Logic - REDIS ENHANCED VERSION
Now with persistent storage, notifications, and lead tracking!
"""

import os
import json
import logging
import redis
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalesBotRedis:
    """Enhanced sales bot with Redis persistence and notifications"""
    
    def __init__(self):
        """Initialize the sales bot with Redis"""
        # Initialize Anthropic model
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7,
            max_tokens=1000
        )
        
        # Initialize Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)
        logger.info(f"Connected to Redis at {redis_url}")
        
        # Webhook URL for notifications
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        
        logger.info("Sales bot with Redis initialized successfully")
    
    def _get_conversation_key(self, thread_id: str) -> str:
        """Generate Redis key for conversation"""
        return f"conversation:{thread_id}"
    
    def _get_lead_key(self, thread_id: str) -> str:
        """Generate Redis key for lead data"""
        return f"lead:{thread_id}"
    
    async def _send_notification(self, thread_id: str, stage: str, context: Dict[str, Any], conversation_history: List[Dict]):
        """Send notification when prospect reaches booking stage"""
        if stage != "booking":
            return
            
        try:
            # Extract lead information
            lead_data = {
                "thread_id": thread_id,
                "timestamp": datetime.utcnow().isoformat(),
                "stage_reached": stage,
                "business_type": context.get("business_type", "unknown"),
                "timeline": context.get("timeline", "not specified"),
                "budget": context.get("budget", "not specified"),
                "features": context.get("features", []),
                "conversation_summary": self._summarize_conversation(conversation_history),
                "total_messages": len(conversation_history)
            }
            
            # Store lead data in Redis
            self.redis_client.hset(
                self._get_lead_key(thread_id),
                mapping={
                    "data": json.dumps(lead_data),
                    "created_at": datetime.utcnow().isoformat(),
                    "status": "hot_lead"
                }
            )
            
            # Send webhook notification
            if self.webhook_url:
                async with httpx.AsyncClient() as client:
                    await client.post(self.webhook_url, json=lead_data)
                    logger.info(f"Webhook notification sent for thread {thread_id}")
            
            # Send Slack notification
            if self.slack_webhook:
                slack_message = {
                    "text": f"🔥 New Hot Lead Ready to Book!",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*New Lead Ready to Book Strategy Call*\n\n*Business Type:* {lead_data['business_type']}\n*Timeline:* {lead_data['timeline']}\n*Budget:* {lead_data['budget']}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Summary:* {lead_data['conversation_summary']}"
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "View Conversation"},
                                    "url": f"{os.getenv('DASHBOARD_URL', 'http://localhost:3000')}/conversations/{thread_id}"
                                }
                            ]
                        }
                    ]
                }
                
                async with httpx.AsyncClient() as client:
                    await client.post(self.slack_webhook, json=slack_message)
                    logger.info(f"Slack notification sent for thread {thread_id}")
                    
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}", exc_info=True)
    
    def _summarize_conversation(self, history: List[Dict]) -> str:
        """Create a brief summary of the conversation"""
        if len(history) < 2:
            return "New conversation"
        
        # Get key points from conversation
        user_messages = [msg["content"] for msg in history if msg["role"] == "user"]
        
        # Simple summary (in production, use LLM for better summaries)
        summary_parts = []
        
        # Business type
        for msg in user_messages:
            msg_lower = msg.lower()
            if "e-commerce" in msg_lower or "online store" in msg_lower:
                summary_parts.append("E-commerce business")
                break
            elif "saas" in msg_lower or "software" in msg_lower:
                summary_parts.append("SaaS business")
                break
        
        # Budget mentioned
        for msg in user_messages:
            if "$" in msg:
                # Extract dollar amount
                import re
                amounts = re.findall(r'\$[\d,]+', msg)
                if amounts:
                    summary_parts.append(f"Budget: {amounts[0]}")
                    break
        
        # Timeline
        for msg in user_messages:
            msg_lower = msg.lower()
            if "week" in msg_lower or "month" in msg_lower:
                if "4" in msg or "6" in msg:
                    summary_parts.append("Timeline: 4-6 weeks")
                    break
        
        return " | ".join(summary_parts) if summary_parts else "Prospect interested in MVP development"
    
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
                if isinstance(context.get("features"), list):
                    context["features"].append(user_message)
        
        return context
    
    async def process_message(self, message: str, thread_id: str = "default") -> str:
        """Process a user message and return bot response"""
        try:
            # Get conversation from Redis
            conv_key = self._get_conversation_key(thread_id)
            stored_data = self.redis_client.get(conv_key)
            
            if stored_data:
                convo = json.loads(stored_data)
            else:
                # Create new conversation
                convo = {
                    "stage": "greeting",
                    "context": {"message_count": 0, "thread_id": thread_id},
                    "history": [],
                    "created_at": datetime.utcnow().isoformat()
                }
            
            # Update context
            convo["context"]["message_count"] += 1
            convo["context"] = self._extract_context_from_message(
                convo["stage"], 
                message, 
                convo["context"]
            )
            
            # Determine if we should move to next stage
            next_stage = self._determine_next_stage(convo["stage"], message, convo["context"])
            
            # Get system prompt for current stage
            system_prompt = self._get_system_prompt(next_stage, convo["context"])
            
            # Build conversation history
            messages = [SystemMessage(content=system_prompt)]
            
            # Add recent history (last 6 messages for context)
            for msg in convo["history"][-6:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add current message
            messages.append(HumanMessage(content=message))
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            bot_message = response.content
            
            # Update conversation state
            convo["stage"] = next_stage
            convo["history"].append({"role": "user", "content": message})
            convo["history"].append({"role": "assistant", "content": bot_message})
            convo["last_updated"] = datetime.utcnow().isoformat()
            
            # Save to Redis
            self.redis_client.setex(
                conv_key,
                86400 * 7,  # 7 days expiration
                json.dumps(convo)
            )
            
            # Send notification if reaching booking stage
            if next_stage == "booking" and convo["stage"] != "booking":
                await self._send_notification(thread_id, next_stage, convo["context"], convo["history"])
            
            logger.info(f"Stage: {convo['stage']}, Context: {convo['context']}")
            
            return bot_message
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error. Could you please try again?"
    
    def reset_conversation(self, thread_id: str = "default"):
        """Reset conversation for a given thread"""
        conv_key = self._get_conversation_key(thread_id)
        self.redis_client.delete(conv_key)
        logger.info(f"Conversation reset for thread: {thread_id}")
    
    def get_conversation(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation from Redis"""
        conv_key = self._get_conversation_key(thread_id)
        stored_data = self.redis_client.get(conv_key)
        
        if stored_data:
            return json.loads(stored_data)
        return None
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all active conversations"""
        conversations = []
        for key in self.redis_client.scan_iter(match="conversation:*"):
            data = self.redis_client.get(key)
            if data:
                conv = json.loads(data)
                thread_id = key.decode().split(":", 1)[1]
                conv["thread_id"] = thread_id
                conversations.append(conv)
        
        return sorted(conversations, key=lambda x: x.get("last_updated", ""), reverse=True)
    
    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Get all leads that reached booking stage"""
        leads = []
        for key in self.redis_client.scan_iter(match="lead:*"):
            data = self.redis_client.hgetall(key)
            if data:
                lead_data = json.loads(data[b"data"].decode())
                lead_data["status"] = data.get(b"status", b"unknown").decode()
                leads.append(lead_data)
        
        return sorted(leads, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def export_lead_data(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Export complete lead data for MVP building"""
        # Get conversation
        conversation = self.get_conversation(thread_id)
        if not conversation:
            return None
        
        # Get lead data
        lead_key = self._get_lead_key(thread_id)
        lead_info = self.redis_client.hgetall(lead_key)
        
        if lead_info:
            lead_data = json.loads(lead_info[b"data"].decode())
        else:
            lead_data = {}
        
        # Combine all data
        export_data = {
            "thread_id": thread_id,
            "conversation": conversation,
            "lead_info": lead_data,
            "exported_at": datetime.utcnow().isoformat(),
            "summary": {
                "business_type": conversation["context"].get("business_type", "unknown"),
                "timeline": conversation["context"].get("timeline", "not specified"),
                "budget": conversation["context"].get("budget", "not specified"),
                "features": conversation["context"].get("features", []),
                "stage_reached": conversation["stage"],
                "message_count": len(conversation["history"])
            }
        }
        
        return export_data