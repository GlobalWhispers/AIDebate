# AI Jubilee Debate System

A real-time debate platform where AI bots and humans can engage in structured debates with automated moderation, voting, and live streaming capabilities.

## Features

- **Multi-participant debates** with AI bots and human participants
- **Automated moderation** with configurable rules and timeouts
- **Real-time voting system** with vote tallying
- **Shared chat log** with timestamps and message ordering
- **Live streaming support** via WebSocket
- **Configurable debate topics** and bot personalities
- **Extensible architecture** for adding new AI models and clients

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the system:**
   Edit `config.yaml` to set up your debate parameters, API keys, and bot configurations.

3. **Run a debate session:**
   ```bash
   python -m app.main
   ```

## Architecture

The system consists of several key components:

- **Moderator**: Manages debate flow, enforces rules, and coordinates voting
- **Bot Clients**: AI-powered participants using various language models
- **Human Clients**: Interface for human participants (CLI/web)
- **Chat Log**: Centralized message queue with timestamps
- **Voting System**: Handles vote collection and tallying
- **Streaming Server**: Optional live broadcast functionality

## Configuration

The `config.yaml` file allows you to customize:

- Debate topics and formats
- AI bot personalities and models
- Timeout settings and rules
- Voting parameters
- Streaming options

## Usage Examples

### Starting a Standard Debate
```python
from app.main import start_debate_session
from app.moderator import Moderator

# Initialize with 2 AI bots and 1 human participant
session = start_debate_session(
    topic="The impact of AI on society",
    ai_bots=2,
    human_participants=1
)
```

### Custom Bot Configuration
```python
from app.bot_client import BotClient

# Create a bot with specific personality
bot = BotClient(
    name="Philosopher",
    model="gpt-4",
    personality="thoughtful and analytical",
    stance="neutral"
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite: `python -m pytest tests/`
5. Submit a pull request

## Documentation

- [Architecture Details](docs/architecture.md)
- [Usage Guide](docs/usage.md)
- [API Reference](docs/api_reference.md)

## Arhitecture :
Chat Log ← All Participants Monitor This
    ↓
[Bot1] [Bot2] [Bot3] [Moderator Bot] [Human] 
    ↓
All decide independently when to speak
    ↓
Post messages back to Chat Log
## License

MIT License - see LICENSE file for details.