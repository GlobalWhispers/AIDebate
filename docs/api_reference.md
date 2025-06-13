# AI Jubilee Debate System API Reference

## Core Classes

### Moderator

The central coordinator for debate sessions.

#### Constructor
```python
Moderator(
    topic: str,
    participants: List[Union[BotClient, HumanClient]],
    chat_log: ChatLog,
    voting_system: VotingSystem,
    config: Dict[str, Any]
)
```

**Parameters:**
- `topic`: The debate topic string
- `participants`: List of bot and human participants
- `chat_log`: ChatLog instance for message management
- `voting_system`: VotingSystem instance for handling votes
- `config`: Configuration dictionary with timing and rule settings

#### Methods

##### `async run_debate() -> Dict[str, Any]`
Runs the complete debate session through all phases.

**Returns:** Dictionary containing voting results and session statistics

**Example:**
```python
moderator = Moderator(topic, participants, chat_log, voting_system, config)
results = await moderator.run_debate()
print(f"Winner: {results.get('winner', 'No winner')}")
```

##### `get_state() -> DebateState`
Returns current debate state information.

**Returns:** DebateState object with phase, speaker, and timing info

##### `async _give_turn(participant_name: str, time_limit: int, turn_type: str) -> None`
Gives speaking turn to a specific participant.

**Parameters:**
- `participant_name`: Name of participant to give turn to
- `time_limit`: Maximum time in seconds for response
- `turn_type`: Type of turn ("opening", "response", "closing")

---

### ChatLog

Thread-safe message management system.

#### Constructor
```python
ChatLog(max_messages: int = 1000)
```

**Parameters:**
- `max_messages`: Maximum number of messages to retain in memory

#### Methods

##### `async add_message(sender: str, content: str, message_type: str = "chat", metadata: Optional[Dict] = None) -> Message`
Adds a new message to the chat log.

**Parameters:**
- `sender`: Name of message sender
- `content`: Message content text
- `message_type`: Type of message ("chat", "moderator", "system", "vote")
- `metadata`: Optional additional data

**Returns:** Created Message object

**Example:**
```python
message = await chat_log.add_message("Alice", "I think AI will help humanity")
print(f"Message ID: {message.message_id}")
```

##### `get_messages(limit: Optional[int] = None, sender: Optional[str] = None, message_type: Optional[str] = None, since_timestamp: Optional[float] = None) -> List[Message]`
Retrieves messages with optional filtering.

**Parameters:**
- `limit`: Maximum number of messages to return
- `sender`: Filter by sender name
- `message_type`: Filter by message type
- `since_timestamp`: Only messages after this timestamp

**Returns:** List of Message objects

##### `subscribe() -> asyncio.Queue`
Creates subscription for real-time message updates.

**Returns:** Queue that receives new Message objects

##### `async save_transcript(filename: str, format_type: str = "json") -> None`
Saves chat transcript to file.

**Parameters:**
- `filename`: Output file path
- `format_type`: Export format ("json", "txt", "html")

##### `search_messages(query: str, case_sensitive: bool = False) -> List[Message]`
Searches messages by content.

**Parameters:**
- `query`: Search string
- `case_sensitive`: Whether search is case sensitive

**Returns:** List of matching Message objects

---

### VotingSystem

Manages voting sessions and result calculation.

#### Constructor
```python
VotingSystem(config: Dict[str, Any])
```

**Parameters:**
- `config`: Voting configuration dictionary

#### Methods

##### `async start_voting(candidates: List[str], duration: Optional[int] = None) -> None`
Starts a new voting session.

**Parameters:**
- `candidates`: List of participant names to vote for
- `duration`: Voting duration in seconds (uses config default if None)

**Example:**
```python
await voting_system.start_voting(["Alice", "Bob", "Charlie"], 300)
```

##### `async cast_vote(voter_id: str, candidate: str, justification: Optional[str] = None) -> bool`
Casts a vote for a candidate.

**Parameters:**
- `voter_id`: ID of the voter
- `candidate`: Name of candidate being voted for
- `justification`: Optional reasoning for the vote

**Returns:** True if vote was successfully cast

##### `async end_voting() -> VotingResults`
Ends voting session and calculates results.

**Returns:** VotingResults object with winner and vote breakdown

##### `get_vote_summary() -> Dict[str, Any]`
Gets current voting status without ending session.

**Returns:** Dictionary with vote counts and time remaining

##### `async export_results(format_type: str = "json") -> str`
Exports voting results in specified format.

**Parameters:**
- `format_type`: Export format ("json", "csv", "txt")

**Returns:** Formatted results string

---

### BotClient

AI-powered debate participant.

#### Constructor
```python
BotClient(
    name: str,
    model: str,
    provider: str,
    personality: str,
    stance: str,
    api_key: str,
    temperature: float = 0.7,
    max_tokens: int = 300
)
```

**Parameters:**
- `name`: Bot display name
- `model`: AI model identifier
- `provider`: AI provider ("openai" or "anthropic")
- `personality`: Personality description for prompt
- `stance`: Debate stance ("pro", "con", "neutral")
- `api_key`: API key for AI provider
- `temperature`: Response creativity (0.0-1.0)
- `max_tokens`: Maximum response length

#### Methods

##### `async get_response(topic: str, recent_messages: List[Message]) -> str`
Generates AI response to current debate context.

**Parameters:**
- `topic`: Current debate topic
- `recent_messages`: Recent conversation messages for context

**Returns:** Generated response string

**Example:**
```python
bot = BotClient("Analyst", "gpt-4", "openai", "Analytical", "pro", api_key)
response = await bot.get_response("AI in healthcare", recent_messages)
```

##### `async receive_message(message: Message) -> None`
Receives message from debate for context awareness.

##### `get_stats() -> Dict[str, Any]`
Returns bot performance statistics.

**Returns:** Dictionary with response counts, timing, and success rates

##### `async warmup() -> bool`
Tests bot connectivity and readiness.

**Returns:** True if bot is ready for debate

##### `update_personality(personality: str, stance: str = None) -> None`
Updates bot personality and stance during session.

---

### HumanClient

Human participant interface.

#### Constructor
```python
HumanClient(name: str, interface_config: Dict[str, Any])
```

**Parameters:**
- `name`: Human participant display name
- `interface_config`: Interface configuration dictionary

#### Methods

##### `async get_response(topic: str, recent_messages: List[Message]) -> str`
Gets response from human participant.

**Parameters:**
- `topic`: Current debate topic
- `recent_messages`: Recent messages for context

**Returns:** Human's response string

##### `async handle_voting(candidates: List[str], voting_time: int) -> Dict[str, Any]`
Handles voting interface for human.

**Parameters:**
- `candidates`: List of candidates to vote for
- `voting_time`: Time allowed for voting

**Returns:** Dictionary with vote result and metadata

##### `async set_active(active: bool) -> None`
Sets whether human is actively participating.

**Parameters:**
- `active`: Whether human should be active in debate

---

### StreamingServer

WebSocket server for live debate streaming.

#### Constructor
```python
StreamingServer(
    chat_log: ChatLog,
    voting_system: VotingSystem,
    config: Dict[str, Any]
)
```

#### Methods

##### `async start() -> None`
Starts the streaming server.

##### `async stop() -> None`
Stops the streaming server and closes connections.

##### `async broadcast_custom_message(message_type: str, data: Any) -> None`
Broadcasts custom message to all connected clients.

**Parameters:**
- `message_type`: Type identifier for the message
- `data`: Message payload

##### `get_connected_clients() -> List[Dict[str, Any]]`
Returns information about all connected streaming clients.

**Returns:** List of client information dictionaries

---

## Data Classes

### Message

Represents a single chat message.

```python
@dataclass
class Message:
    sender: str
    content: str
    timestamp: float
    message_id: int
    message_type: str = "chat"
    metadata: Optional[Dict[str, Any]] = None
```

**Properties:**
- `formatted_timestamp`: Human-readable timestamp string

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary
- `from_dict(data: Dict[str, Any]) -> Message`: Create from dictionary

### Vote

Represents a single vote in the voting system.

```python
@dataclass
class Vote:
    voter_id: str
    candidate: str
    justification: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    anonymous: bool = False
```

### VotingResults

Contains results from a voting session.

```python
@dataclass
class VotingResults:
    winner: Optional[str]
    vote_counts: Dict[str, int]
    total_votes: int
    votes_by_voter: Dict[str, Vote]
    voting_duration: float
    participation_rate: float
```

### DebateState

Tracks current debate session state.

```python
@dataclass
class DebateState:
    phase: DebatePhase
    current_speaker: Optional[str] = None
    time_remaining: int = 0
    turn_order: List[str] = None
    warnings_issued: Dict[str, int] = None
```

---

## Enums

### DebatePhase

Defines the phases of a debate session.

```python
class DebatePhase(Enum):
    INTRODUCTION = "introduction"
    OPENING_STATEMENTS = "opening_statements"
    DISCUSSION = "discussion"
    CLOSING_STATEMENTS = "closing_statements"
    VOTING = "voting"
    RESULTS = "results"
    FINISHED = "finished"
```

---

## Utility Functions

### Configuration (`app/utils.py`)

##### `load_config(config_path: str = "config.yaml") -> Dict[str, Any]`
Loads configuration from YAML file with environment variable substitution.

**Parameters:**
- `config_path`: Path to configuration file

**Returns:** Configuration dictionary

**Example:**
```python
config = load_config("custom_config.yaml")
```

##### `setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None`
Sets up logging configuration.

**Parameters:**
- `level`: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
- `log_file`: Optional log file path

##### `format_time_remaining(seconds: float) -> str`
Formats time remaining in human-readable format.

**Parameters:**
- `seconds`: Time in seconds

**Returns:** Formatted time string ("5m 30s", "2h 15m", etc.)

##### `truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str`
Truncates text to maximum length.

**Parameters:**
- `text`: Text to truncate
- `max_length`: Maximum length
- `suffix`: Suffix to add when truncating

**Returns:** Truncated text

---

## Error Handling

### Custom Exceptions

The system uses standard Python exceptions with descriptive messages:

- `ValueError`: Invalid configuration or parameters
- `FileNotFoundError`: Missing configuration files
- `ConnectionError`: API or network failures
- `TimeoutError`: Response timeouts

### Error Recovery

All async methods include proper error handling and will not crash the session:

```python
try:
    response = await bot.get_response(topic, messages)
except Exception as e:
    # Fallback response is automatically generated
    response = bot._generate_fallback_response(topic)
```

---

## Configuration Schema

### Main Configuration

```yaml
# Debate settings
debate:
  default_topic: str
  max_participants: int
  time_limit_minutes: int
  opening_statement_time: int  # seconds
  response_time: int
  closing_statement_time: int

# Bot configurations
bots:
  - name: str
    model: str
    provider: str  # "openai" or "anthropic"
    personality: str
    stance: str  # "pro", "con", or "neutral"
    temperature: float  # 0.0-1.0
    max_tokens: int

# API credentials
api_keys:
  openai: str
  anthropic: str

# Voting settings
voting:
  enabled: bool
  voting_duration: int  # seconds
  allow_participant_voting: bool
  require_justification: bool
  anonymous_votes: bool

# Chat settings
chat:
  max_message_length: int
  enable_timestamps: bool
  log_level: str
  save_transcripts: bool

# Streaming settings
streaming:
  enabled: bool
  websocket_port: int
  max_connections: int
  broadcast_votes: bool

# Interface settings
interface:
  mode: str  # "cli" or "web"
  enable_rich_formatting: bool
  show_typing_indicators: bool
  input_timeout: int
```

---

## WebSocket API

### Client Connection

Connect to the streaming server:

```javascript
const ws = new WebSocket('ws://localhost:8080');
```

### Message Types

#### Incoming Messages

##### Welcome Message
```json
{
  "type": "welcome",
  "client_id": "client_123456789",
  "server_info": {
    "version": "1.0.0",
    "features": ["chat", "voting", "real_time"]
  }
}
```

##### Chat Message
```json
{
  "type": "message",
  "data": {
    "sender": "Alice",
    "content": "I believe AI will benefit society",
    "timestamp": 1640995200.0,
    "message_id": 42,
    "message_type": "chat"
  }
}
```

##### Vote Update
```json
{
  "type": "vote_update",
  "data": {
    "candidates": ["Alice", "Bob"],
    "vote_counts": {"Alice": 5, "Bob": 3},
    "total_votes": 8,
    "time_remaining": 120,
    "is_active": true
  }
}
```

#### Outgoing Messages

##### Subscribe to Channels
```json
{
  "type": "subscribe",
  "channels": ["chat", "voting", "system"]
}
```

##### Cast Vote
```json
{
  "type": "vote",
  "voter_id": "viewer_123",
  "candidate": "Alice",
  "justification": "Most persuasive arguments"
}
```

##### Ping/Pong
```json
{
  "type": "ping"
}
```

---

## Performance Considerations

### API Rate Limits

- OpenAI: Respect rate limits based on your plan
- Anthropic: Monitor request quotas
- Implement exponential backoff for retries

### Memory Management

- Chat log automatically limits message history
- Conversation history is pruned in bot clients
- Streaming connections are cleaned up automatically

### Async Best Practices

All I/O operations are async:

```python
# Correct - awaits async operations
response = await bot.get_response(topic, messages)
await chat_log.add_message(sender, content)

# Incorrect - would block the event loop
# response = bot.get_response(topic, messages).result()
```

---

## Testing

### Unit Tests

Run the test suite:

```bash
python -m pytest tests/ -v
```

### Integration Tests

Test with real APIs:

```bash
# Set test API keys
export OPENAI_API_KEY="test-key"
export ANTHROPIC_API_KEY="test-key"

# Run integration tests
python -m pytest tests/integration/ -v
```

### Mock Testing

```python
from unittest.mock import AsyncMock

# Mock bot responses
bot.ai_provider.generate_response = AsyncMock(return_value="Test response")
response = await bot.get_response("Test topic", [])
assert response == "Test response"
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "app.main"]
```

### Environment Variables

Required for production:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LOG_LEVEL=INFO
CONFIG_PATH=/app/production_config.yaml
```

### Health Checks

```python
# Check system health
async def health_check():
    # Test bot connectivity
    for bot in bots:
        if not await bot.warmup():
            return False
    
    # Test streaming server
    if streaming_server and not streaming_server.is_active:
        return False
    
    return True
```

This API reference provides comprehensive documentation for integrating with and extending the AI Jubilee Debate System.