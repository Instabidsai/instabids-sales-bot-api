# 🚀 Redis-Enhanced Sales Bot Deployment Guide

## What We Built

Your sales bot now has **enterprise-grade features**:

### 🔴 Redis Persistence
- Conversations survive server restarts
- 7-day conversation history
- Scalable across multiple instances

### 🔔 Real-time Notifications
- Instant alerts when prospects reach booking stage
- Webhook integration for any service
- Slack notifications with lead summaries

### 📊 Live Dashboard
- Real-time conversation monitoring
- Hot lead tracking
- Conversion analytics

### 📡 Lead Export API
- Extract conversation data for CRM
- Build MVPs based on actual requirements
- Track sales pipeline metrics

---

## Quick Start (Local Testing)

```bash
# 1. Clone the repo
git clone https://github.com/Instabidsai/instabids-sales-bot-api.git
cd instabids-sales-bot-api

# 2. Create .env file
echo "ANTHROPIC_API_KEY=your_key_here" > .env
echo "REDIS_URL=redis://redis:6379/0" >> .env

# 3. Start with Docker Compose
docker-compose -f docker-compose.redis.yml up

# 4. Test the bot
python test_redis_bot.py

# 5. Open dashboard
open dashboard/index.html
```

---

## Production Deployment

### Option 1: DigitalOcean App Platform (Recommended)

1. **Add Redis Database**
   ```yaml
   # In your app spec:
   databases:
   - engine: REDIS
     name: sales-bot-redis
     production: true
     version: "7"
   ```

2. **Update Environment Variables**
   ```
   REDIS_URL=${sales-bot-redis.DATABASE_URL}
   WEBHOOK_URL=https://your-webhook.com/leads
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

3. **Deploy Redis Version**
   - Change Dockerfile to `Dockerfile.redis`
   - Update run command to use `api.main_redis:app`

### Option 2: Docker + Any Cloud

```bash
# Build and push
docker build -f Dockerfile.redis -t your-registry/sales-bot-redis .
docker push your-registry/sales-bot-redis

# Deploy with Redis
# Ensure Redis is accessible at REDIS_URL
```

---

## API Endpoints

### Core Chat
```bash
# Chat with persistence
curl -X POST https://your-api.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need an inventory management system",
    "thread_id": "customer-123"
  }'
```

### Lead Management
```bash
# Get all hot leads
curl https://your-api.com/leads

# Export conversation for MVP building
curl https://your-api.com/export/customer-123 > lead-requirements.json

# View all conversations
curl https://your-api.com/conversations

# Reset conversation
curl -X POST https://your-api.com/reset/customer-123
```

---

## Webhook Integration

### Slack Setup
1. Create incoming webhook at https://api.slack.com/messaging/webhooks
2. Add to environment: `SLACK_WEBHOOK_URL=https://hooks.slack.com/...`
3. Receive instant notifications:

```
🔥 New Hot Lead Ready to Book!

Business Type: E-commerce
Timeline: 4-6 weeks
Budget: $5,000

Summary: E-commerce business | Budget: $5,000 | Timeline: 4-6 weeks

[View Conversation]
```

### Custom Webhook
```javascript
// Your webhook will receive:
{
  "thread_id": "customer-123",
  "timestamp": "2024-01-15T10:30:00Z",
  "stage_reached": "booking",
  "business_type": "e-commerce",
  "timeline": "4-6 weeks",
  "budget": "$5,000",
  "features": ["inventory tracking", "low stock alerts"],
  "conversation_summary": "E-commerce | $5k budget | 4-6 weeks",
  "total_messages": 14
}
```

---

## Dashboard Deployment

### GitHub Pages (Free)
```bash
# In repo settings, enable GitHub Pages
# Source: /dashboard folder
# URL: https://instabidsai.github.io/instabids-sales-bot-api/
```

### Netlify (Free)
1. Drag dashboard folder to Netlify
2. Update API_URL in index.html
3. Deploy in seconds

### Custom Domain
```nginx
# Nginx config
server {
    listen 80;
    server_name dashboard.yourdomain.com;
    
    location / {
        root /var/www/dashboard;
        index index.html;
    }
    
    location /api/ {
        proxy_pass http://your-api-backend/;
    }
}
```

---

## Monitoring & Analytics

### Key Metrics
```python
# Track in your analytics:
- Conversations started per day
- Conversion rate (booking/total)
- Average messages to booking
- Drop-off by stage
- Response time
```

### Redis Monitoring
```bash
# Connect to Redis
redis-cli

# View all conversations
KEYS conversation:*

# View all leads
KEYS lead:*

# Get specific conversation
GET conversation:customer-123
```

---

## Cost Optimization

### Redis Memory Usage
- Each conversation: ~5KB
- 1000 conversations: ~5MB
- Auto-expiry after 7 days

### Scaling Strategy
```yaml
# DigitalOcean scaling
services:
  - name: sales-bot-api
    instance_count: 1  # Start with 1
    instance_size_slug: professional-xs  # $12/month
    
  - name: redis
    instance_size_slug: db-s-1vcpu-1gb  # $15/month
```

---

## Troubleshooting

### Redis Connection Issues
```python
# Test Redis connection
import redis
r = redis.from_url("redis://localhost:6379/0")
r.ping()  # Should return True
```

### Missing Conversations
- Check Redis expiry (7 days default)
- Verify thread_id consistency
- Check Redis memory limits

### Webhook Not Firing
- Verify WEBHOOK_URL is set
- Check network accessibility
- Review logs for errors

---

## Next Steps

1. **CRM Integration**
   - Connect to HubSpot/Salesforce
   - Auto-create deals at booking stage
   - Sync conversation history

2. **Analytics Dashboard**
   - Conversion funnel visualization
   - A/B testing different prompts
   - Revenue attribution

3. **Multi-tenant Support**
   - Separate Redis databases per client
   - Custom prompts per tenant
   - White-label dashboard

---

## Support

- **Repository**: https://github.com/Instabidsai/instabids-sales-bot-api
- **Issues**: Open a GitHub issue
- **Updates**: Watch the repo for new features

---

**Built with ❤️ by the InstaBids AI Team**