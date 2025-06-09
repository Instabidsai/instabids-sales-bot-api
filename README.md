# Instabids Sales Bot API

A production-ready conversational AI sales bot powered by Anthropic's Claude 3.5 Sonnet. This bot guides prospects through a structured conversation flow from initial greeting to booking a strategy call.

## Features

- **Structured Conversation Flow**: Greeting → Understanding → MVP Identification → Scoping → Proposal → Booking
- **Real AI Conversations**: Uses Claude 3.5 Sonnet for natural, context-aware responses
- **Stateful Conversations**: Maintains conversation context across messages
- **REST API**: Easy integration with any frontend or widget
- **Production Ready**: Health checks, CORS support, error handling

## API Endpoints

- `GET /` - API info and available endpoints
- `GET /health` - Health check endpoint
- `POST /chat` - Process a chat message
- `POST /reset/{thread_id}` - Reset a conversation thread
- `GET /docs` - Interactive API documentation

## Deployment

This bot is designed to run on DigitalOcean App Platform:

1. Fork this repository
2. Create a new app in DigitalOcean
3. Connect to your GitHub repository
4. Add environment variable: `ANTHROPIC_API_KEY`
5. Deploy!

## Environment Variables

- `ANTHROPIC_API_KEY` (required) - Your Anthropic API key
- `PORT` (optional) - Port to run on (default: 8080)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=your_key_here

# Run the server
python main.py
```

## Integration

To integrate with a frontend widget:

```javascript
// Send a message
const response = await fetch('https://your-bot-api.ondigitalocean.app/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Hello!",
    thread_id: "user-123"
  })
});

const data = await response.json();
console.log(data.response); // Bot's response
```

## License

MIT