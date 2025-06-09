# Sales Bot Dashboard

## Quick Start

### Option 1: Local Development
```bash
# Start the API with Redis
docker-compose -f docker-compose.redis.yml up

# Open dashboard
open dashboard/index.html
```

### Option 2: Production
1. Deploy the Redis-enhanced API
2. Update the API_URL in index.html
3. Host the dashboard on any static hosting (Netlify, Vercel, GitHub Pages)

## Features

- 🔄 **Real-time Updates**: Auto-refreshes every 30 seconds
- 📊 **Live Stats**: Conversion rate, active conversations, hot leads
- 🔥 **Lead Tracking**: See prospects ready to book
- 💬 **Conversation History**: View recent messages and context
- 🎨 **Beautiful UI**: Dark theme with gradient accents

## API Integration

The dashboard connects to these endpoints:
- `/conversations` - Get all active conversations
- `/leads` - Get all hot leads
- `/export/{thread_id}` - Export conversation data

## Customization

### Change API URL
```javascript
const API_URL = 'https://your-api-domain.com';
```

### Adjust Refresh Rate
```javascript
setInterval(loadData, 10000); // 10 seconds
```

### Add Webhooks
When a lead reaches booking stage, the API can send webhooks to:
- Slack
- Zapier
- Your CRM
- Custom webhook URL