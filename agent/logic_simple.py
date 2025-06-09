"""
Sales Bot Agent Logic - SIMPLE WORKING VERSION
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SalesBot:
    """Simple conversational sales bot that actually works"""
    
    def __init__(self):
        """Initialize the sales bot"""
        # Initialize Anthropic model
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.7,
            max_tokens=1000
        )
        
        # Store conversations in memory (replace with Redis later)
        self.conversations = {}
        
        logger.info("Sales bot initialized successfully")
    
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
    
    async def process_message(self, message: str, thread_id: str = "default") -> str:
        """Process a user message and return bot response"""
        try:
            # Get or create conversation state
            if thread_id not in self.conversations:
                self.conversations[thread_id] = {
                    "stage": "greeting",
                    "context": {"message_count": 0},
                    "history": []
                }
            
            convo = self.conversations[thread_id]
            
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
            
            logger.info(f"Stage: {convo['stage']}, Context: {convo['context']}")
            
            return bot_message
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error. Could you please try again?"
    
    def reset_conversation(self, thread_id: str = "default"):
        """Reset conversation for a given thread"""
        if thread_id in self.conversations:
            del self.conversations[thread_id]
        logger.info(f"Conversation reset for thread: {thread_id}")