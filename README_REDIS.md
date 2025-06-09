# Sales Bot with Redis Persistence & Notifications

## What's New

### 🔴 Redis Persistence
- Conversations stored in Redis for 7 days
- Maintains conversation context across sessions
- Scalable across multiple instances

### 🔔 Real-time Notifications
- Webhook notifications when prospects reach booking stage
- Slack integration for instant alerts
- Lead data automatically captured

### 📊 Lead Management APIs
- `/conversations` - View all active conversations
- `/leads` - Get all hot leads ready to close
- `/export/{thread_id}` - Export conversation data for MVP building

## Environment Variables

```env
# Existing
ANTHROPIC_API_KEY=your_key

# New for Redis
REDIS_URL=redis://localhost:6379/0

# Optional Notifications
WEBHOOK_URL=https://your-webhook.com/leads
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DASHBOARD_URL=https://your-dashboard.com
```

## Quick Start

```bash
# Install Redis dependencies
pip install -r requirements_redis.txt

# Run locally with Redis
docker run -d -p 6379:6379 redis:alpine
python api/main_redis.py
```

## API Examples

### Chat with Persistence
```bash
curl -X POST https://your-api.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I run an e-commerce store",
    "thread_id": "user-123"
  }'
```

### Get All Leads
```bash
curl https://your-api.com/leads
```

### Export Lead Data
```bash
curl https://your-api.com/export/user-123 > lead-data.json
```

## Slack Notification Example

When a prospect reaches the booking stage:

```
🔥 New Hot Lead Ready to Book!

Business Type: E-commerce
Timeline: 4-6 weeks  
Budget: $5,000

Summary: E-commerce business | Budget: $5,000 | Timeline: 4-6 weeks

[View Conversation]
```

## Architecture Benefits

1. **Persistence**: Conversations survive server restarts
2. **Scalability**: Multiple API instances can share Redis
3. **Analytics**: Track conversion rates and drop-offs
4. **Integration**: Easy to connect with CRM systems
5. **Real-time**: Instant notifications to sales team