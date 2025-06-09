"""Test script for Redis-enhanced sales bot"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
TEST_THREAD_ID = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# Test conversation flow
TEST_MESSAGES = [
    "Hi, I'm interested in building an MVP",
    "I run an e-commerce store selling handmade jewelry",
    "Our biggest challenge is inventory management and customer tracking",
    "Yes, an inventory system with automated alerts sounds perfect!",
    "We need real-time stock tracking, low stock alerts, and sales analytics",
    "Timeline is 4-6 weeks, budget around $5,000",
    "This sounds great! I'd love to discuss further"
]

async def test_conversation():
    """Run a full conversation test"""
    print(f"\n🚀 Testing Sales Bot with Thread ID: {TEST_THREAD_ID}\n")
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("Checking health...")
        health = await client.get(f"{API_URL}/health")
        print(f"Health: {health.json()}\n")
        
        # Run conversation
        for i, message in enumerate(TEST_MESSAGES):
            print(f"User: {message}")
            
            # Send message
            response = await client.post(
                f"{API_URL}/chat",
                json={
                    "message": message,
                    "thread_id": TEST_THREAD_ID
                }
            )
            
            data = response.json()
            print(f"Bot: {data['response']}")
            print(f"Stage: {data['stage']}")
            print(f"Context: {json.dumps(data['context'], indent=2)}\n")
            
            # Small delay between messages
            await asyncio.sleep(1)
        
        # Check if lead was captured
        print("\n📊 Checking captured leads...")
        leads = await client.get(f"{API_URL}/leads")
        leads_data = leads.json()
        print(f"Total leads: {leads_data['total']}")
        
        if leads_data['total'] > 0:
            print("\nLatest lead:")
            latest_lead = leads_data['leads'][0]
            print(json.dumps(latest_lead, indent=2))
        
        # Export conversation data
        print(f"\n📥 Exporting conversation data...")
        export = await client.get(f"{API_URL}/export/{TEST_THREAD_ID}")
        export_data = export.json()
        
        print("Export summary:")
        print(json.dumps(export_data['summary'], indent=2))
        
        # Get all conversations
        print("\n📁 All active conversations:")
        conversations = await client.get(f"{API_URL}/conversations")
        conv_data = conversations.json()
        print(f"Total conversations: {conv_data['total']}")

if __name__ == "__main__":
    asyncio.run(test_conversation())