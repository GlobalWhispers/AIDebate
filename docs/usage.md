# AI Jubilee Debate System - Usage Guide

## 🚀 Quick Start

### Prerequisites
1. **Python 3.8+** installed
2. **API Keys** for OpenAI and/or Anthropic
3. **Dependencies** installed

### Setup Steps

1. **Clone or download the project**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API keys in `.env` file:**
   ```bash
   # Create .env file in project root
   OPENAI_API_KEY=sk-your-openai-key-here
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
   ```

4. **Run the debate:**
   ```bash
   # Recommended: Use the simple launcher
   python run_debate.py
   
   # Alternative: Use the module directly
   python -m app.main
   ```

## 🎭 Debate Modes

### **Autonomous Mode** (Default - Recommended!)

In autonomous mode, bots monitor the conversation and decide when to speak, creating a natural, organic debate flow.

#### How Autonomous Mode Works:
- 🤖 **Bots run in parallel**, continuously monitoring chat
- 🧠 **Intelligent decision making** - bots decide when they feel compelled to respond
- 📚 **Full conversation history** available to all participants
- 🎯 **Smart triggers** - bots respond to mentions, challenges, or opportunities
- ⏰ **Cooldown system** prevents spam (15-45 second intervals)
- 🗣️ **Humans can speak anytime** during discussion phase

#### Configuration:
```yaml
debate:
  mode: "autonomous"  # Enable autonomous mode
  min_bot_cooldown: 15         # Minimum seconds between bot responses
  max_bot_cooldown: 45         # Maximum cooldown for active bots  
  message_check_interval: 5    # How often bots check for new messages
  silence_timeout: 60          # Moderator intervenes after silence
```

#### Example Autonomous Flow:
```
🎭 Moderator: "Autonomous Discussion Phase Begin!"
🤖 Advocate: "Remote work increases productivity by 40%..."
💭 Skeptic is thinking about responding...
🤖 Skeptic: "But what about the collaboration costs?"
👤 Human: "I've experienced both - here's my take..."
💭 Socrates is thinking about responding...  
🤖 Socrates: "What evidence supports these productivity claims?"
🎯 Moderator: "What about environmental implications?"
💭 Advocate is thinking about responding...
🤖 Advocate: "Great point - remote work cuts commuting emissions..."
```

### **Sequential Mode** (Traditional)

Participants take turns in a structured order. More predictable but less dynamic.

```yaml
debate:
  mode: "sequential"  # Traditional turn-based mode
```

## 🎯 Human Participation in Autonomous Mode

### **During Discussion Phase:**
- ✅ **Speak anytime** - no waiting for turns!
- ✅ **Type naturally** - just enter your response
- ✅ **Full context** - see all previous messages
- ✅ **Real-time** - immediate feedback from bots

### **Available Commands:**
```
💬 [your message]     # Join the debate with your response
help                  # Show help information
status                # Show your participation statistics
history               # Show recent conversation
quit                  # Leave the debate
```

### **Example Human Session:**
```
🎯 AUTONOMOUS DEBATE MODE ACTIVE
🗣️ You can speak at ANY TIME during the discussion!
💡 Commands: 'help', 'status', 'history', 'quit'

🤖 Advocate: "Remote work is clearly the future because..."
🤖 Skeptic: "I disagree - here's why remote work fails..."

💬 Type your response: I think both perspectives miss the point about hybrid work...
✅ Your message has been added to the debate!

💭 Socrates is thinking about responding...
🤖 Socrates: "Interesting point about hybrid - can you elaborate?"

💬 Type your response: status
📊 Your participation: 1 responses, 100.0% participation rate, avg response time: 12.3s

💬 Type your response: Sure! Hybrid work combines the best of both...
✅ Your message has been added to the debate!
```

## 📋 Debate Phases

### **1. Introduction Phase**
- Moderator introduces topic and participants
- Overview of rules and format
- Duration: ~2 minutes

### **2. Opening Statements Phase** 
- Each participant gives structured opening statement
- **Sequential order** (even in autonomous mode)
- Time limit: 120 seconds per participant

### **3. Discussion Phase**

#### **Autonomous Mode:**
- 🔄 **Free-flowing conversation**
- 🤖 **Bots monitor and respond intelligently** 
- 👥 **Humans can jump in anytime**
- 🎯 **Moderator provides prompts during silence**
- ⏰ **Total time: 30 minutes** (configurable)

#### **Sequential Mode:**
- 🔄 **Round-robin turns**
- ⏰ **60 seconds per response**
- 📝 **Structured format**

### **4. Closing Statements Phase**
- Final arguments from each participant
- **Sequential order** 
- Time limit: 90 seconds per participant

### **5. Voting Phase**
- Participants and audience vote for most persuasive
- Duration: 5 minutes
- Optional justification required

### **6. Results Phase**
- Vote tallies and winner announcement
- Final statistics and transcript saving

## ⚙️ Configuration Options

### **Bot Personalities**

```yaml
bots:
  - name: "Socrates"
    personality: "Philosophical, asks probing questions, seeks truth through dialogue. Speaks when curious about underlying assumptions."
    stance: "neutral"
    
  - name: "Advocate"  
    personality: "Passionate supporter, data-driven, persuasive. Jumps in when position is challenged."
    stance: "pro"
    
  - name: "Skeptic"
    personality: "Critical thinker, questions assumptions. Responds when claims need scrutiny."
    stance: "con"
```

### **Timing Controls**

```yaml
debate:
  time_limit_minutes: 30        # Total discussion time
  opening_statement_time: 120   # Opening statement duration
  response_time: 60            # Response time in sequential mode
  closing_statement_time: 90   # Closing statement duration
  
  # Autonomous mode specific
  min_bot_cooldown: 15         # Minimum bot response interval
  max_bot_cooldown: 45         # Maximum bot cooldown
  silence_timeout: 60          # Silence before moderator intervenes
```

### **Interface Options**

```yaml
interface:
  mode: "cli"                  # CLI or web interface
  enable_rich_formatting: true # Colored/formatted output
  show_typing_indicators: true # Show when bots are thinking
  enable_reactions: true       # Enable emoji reactions
```

## 🎛️ Advanced Usage

### **Command Line Options**

```bash
# Basic usage
python run_debate.py

# Using the module with options
python -m app.main --topic "AI ethics" --bots 3 --humans 2

# Custom configuration
python -m app.main --config custom_config.yaml

# Web interface mode
python -m app.main --interface web
```

### **Custom Topics**

Add to `config.yaml`:
```yaml
topics:
  - "Your custom debate topic here"
  - "Another interesting topic"
```

Or specify directly:
```bash
python -m app.main --topic "Custom topic"
```

### **Bot Configuration**

Create custom bots in `config.yaml`:
```yaml
bots:
  - name: "MyBot"
    model: "gpt-4"
    provider: "openai"
    personality: "Your custom personality description"
    stance: "pro"  # or "con" or "neutral"
```

## 🔧 Troubleshooting

### **Common Issues**

**API Key Errors:**
```bash
# Check your .env file format
OPENAI_API_KEY=sk-your-key  # No quotes, no export
ANTHROPIC_API_KEY=sk-ant-your-key
```

**Import Errors:**
```bash
# Make sure you're in the project root directory
cd ai_jubilee_debate
python run_debate.py
```

**Timeout Issues:**
```bash
# Check internet connection and API status
# Increase timeouts in config.yaml if needed
```

### **Debug Mode**

Enable detailed logging:
```yaml
chat:
  log_level: "DEBUG"
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
python run_debate.py
```

### **Saving Transcripts**

Transcripts are automatically saved after each debate:
```yaml
chat:
  save_transcripts: true
  transcript_format: "json"  # or "txt" or "html"
```

Files saved as: `debate_YYYY-MM-DD_HH-MM-SS.json`

## 🎪 Tips for Great Debates

### **For Humans:**
- 🎯 **Jump in naturally** during autonomous mode
- 📊 **Reference specific points** made by others
- 💡 **Provide evidence** and examples
- 🤝 **Be respectful** but persuasive
- ⚡ **Keep responses focused** and substantial

### **Bot Optimization:**
- 🎭 **Diverse personalities** create better dynamics
- ⚖️ **Balanced stances** (pro/con/neutral mix)
- 🧠 **Different models** (GPT-4, Claude, etc.) for variety
- ⏰ **Appropriate cooldowns** prevent spam

### **Moderator Settings:**
- 🎯 **Topic-specific prompts** keep discussion flowing
- ⏰ **Reasonable timeouts** balance pace and depth
- 💬 **Silence intervention** maintains engagement

## 📊 Monitoring and Analytics

### **Real-time Stats**
```
# During debate, type 'status' to see:
📊 Your participation: 3 responses, 75% participation rate
⏱️ Average response time: 15.2 seconds
💬 Conversation length: 24 messages
```

### **Post-Debate Analysis**
- 📈 Participation rates per participant
- ⏰ Response time analytics  
- 🗳️ Voting results and justifications
- 📝 Full transcript with timestamps

## 🚀 Performance Tips

### **For Better Performance:**
- Use **GPT-3.5** for faster, cheaper responses
- Set **reasonable cooldowns** (15-30 seconds)
- Limit **conversation history** for speed
- Use **async mode** for responsiveness

### **For Higher Quality:**
- Use **GPT-4** or **Claude** for better reasoning
- Increase **response time limits**
- Enable **detailed logging** for analysis
- Create **specific bot personalities**

## 🌟 Advanced Features

### **Real-time Streaming**
Enable WebSocket streaming for live audiences:
```yaml
streaming:
  enabled: true
  websocket_port: 8080
  max_connections: 100
```

### **Voting System**
Comprehensive voting with justifications:
```yaml
voting:
  enabled: true
  voting_duration: 300
  require_justification: true
  anonymous_votes: false
```

### **Web Interface**
For browser-based participation:
```yaml
interface:
  mode: "web"
  websocket_port: 8080
```

## 📁 File Structure

```
ai_jubilee_debate/
├── .env                    # Your API keys (never commit!)
├── .env.example           # Example environment file
├── .gitignore             # Git ignore patterns
├── config.yaml            # Main configuration
├── requirements.txt       # Python dependencies
├── run_debate.py          # Simple launcher script
├── app/                   # Core application
│   ├── __init__.py       # Package initialization
│   ├── main.py           # Main entry point
│   ├── moderator.py      # Debate moderation logic
│   ├── bot_client.py     # AI bot participants
│   ├── human_client.py   # Human participants
│   ├── chat_log.py       # Message management
│   ├── voting.py         # Voting system
│   ├── utils.py          # Utility functions
│   └── streaming.py      # WebSocket streaming
├── tests/                 # Test suite
│   ├── test_moderator.py
│   ├── test_voting.py
│   ├── test_chat_log.py
│   ├── test_bot_client.py
│   └── test_human_client.py
└── docs/                  # Documentation
    ├── architecture.md    # System architecture
    ├── usage.md          # This file
    └── api_reference.md  # API documentation
```

## 🆘 Getting Help

### **Built-in Help**
```bash
# During debate
help                    # Show autonomous mode help
status                  # Show participation stats
history                 # Show recent messages

# Command line
python -m app.main --help   # Show CLI options
```

### **Common Commands**
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python run_debate.py

# Run tests
python -m pytest tests/ -v

# Check configuration
python -c "from app.utils import load_config; print(load_config())"
```

This autonomous debate system creates truly organic, intelligent conversations between AI participants while allowing humans to jump in naturally whenever they feel inspired to contribute! 🎭🤖# AI Jubilee Debate System Usage Guide

## Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai_jubilee_debate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

4. **Run your first debate:**
   ```bash
   python -m app.main
   ```

## Configuration

### Basic Configuration (`config.yaml`)

```yaml
debate:
  default_topic: "AI will create more jobs than it destroys"
  max_participants: 4
  time_limit_minutes: 20

bots:
  - name: "Advocate"
    model: "gpt-4"
    provider: "openai" 
    stance: "pro"
  - name: "Skeptic"
    model: "claude-3-sonnet"
    provider: "anthropic"
    stance: "con"

voting:
  enabled: true
  voting_duration: 180
```

### Advanced Configuration Options

#### Timing Settings
```yaml
debate:
  opening_statement_time: 120  # seconds
  response_time: 60
  closing_statement_time: 90
  warning_time: 45  # warning before timeout
```

#### Bot Personalities
```yaml
bots:
  - name: "Philosopher"
    personality: "Thoughtful, asks probing questions"
    debate_style: "socratic"
    temperature: 0.8
    max_tokens: 250
```

#### Human Interface
```yaml
interface:
  mode: "cli"  # or "web"
  enable_rich_formatting: true
  show_typing_indicators: true
  input_timeout: 120
```

## Running Debates

### Command Line Interface

#### Basic Usage
```bash
# Run with default settings
python -m app.main

# Specify topic
python -m app.main --topic "Universal Basic Income is necessary"

# Set participant counts
python -m app.main --bots 3 --humans 2

# Use custom config
python -m app.main --config custom_config.yaml
```

#### Advanced Options
```bash
# Full command with all options
python -m app.main \
  --topic "Climate change requires immediate action" \
  --bots 2 \
  --humans 1 \
  --config production_config.yaml
```

### Programmatic Usage

#### Simple Session
```python
from app.main import start_debate_session

# Start a basic debate
await start_debate_session(
    topic="The future of remote work",
    ai_bots=2,
    human_participants=1
)
```

#### Custom Session
```python
from app import Moderator, BotClient, HumanClient, ChatLog, VotingSystem

# Create components
chat_log = ChatLog()
voting_system = VotingSystem({'enabled': True})

# Create participants
bot = BotClient(
    name="Analyst",
    model="gpt-4",
    provider="openai",
    personality="Data-driven and analytical",
    stance="neutral",
    api_key="your-api-key"
)

human = HumanClient(
    name="Participant1",
    interface_config={'mode': 'cli'}
)

# Create moderator and run
moderator = Moderator(
    topic="AI Ethics in Healthcare",
    participants=[bot, human],
    chat_log=chat_log,
    voting_system=voting_system,
    config={'time_limit_minutes': 15}
)

results = await moderator.run_debate()
```

## Participant Management

### AI Bot Configuration

#### Creating Custom Bots
```python
# Argumentative bot
aggressive_bot = BotClient(
    name="Debater",
    model="gpt-4",
    provider="openai", 
    personality="Aggressive, uses strong rhetoric",
    stance="pro",
    temperature=0.9,  # More creative
    api_key=api_key
)

# Analytical bot
analytical_bot = BotClient(
    name="Researcher", 
    model="claude-3-sonnet",
    provider="anthropic",
    personality="Fact-focused, cites evidence",
    stance="con",
    temperature=0.3,  # More conservative
    api_key=api_key
)
```

#### Bot Personality Examples
```yaml
personalities:
  socratic: "Asks probing questions, seeks deeper understanding"
  advocate: "Passionate, uses emotional appeals and personal stories"  
  scientist: "Data-driven, cites studies and statistics"
  philosopher: "Abstract thinking, explores ethical implications"
  pragmatist: "Focuses on practical implementation and real-world effects"
  skeptic: "Questions assumptions, plays devil's advocate"
```

### Human Interface Options

#### CLI Mode (Default)
- Terminal-based interaction
- Rich formatting with colors
- Real-time message display
- Keyboard input for responses

#### Web Mode 
```python
human = HumanClient(
    name="WebUser",
    interface_config={
        'mode': 'web',
        'enable_reactions': True,
        'show_typing_indicators': True
    }
)
```

## Debate Topics

### Predefined Topics
The system includes several built-in topics:
- "AI will create more jobs than it destroys"
- "Social media has a net positive impact on democracy"
- "Universal Basic Income is necessary for the future economy"
- "Climate change requires immediate radical action"
- "Privacy is more important than security"

### Custom Topics
```python
# Define your own topics
custom_topics = [
    "Cryptocurrency will replace traditional banking",
    "Space exploration should be publicly funded",
    "Genetic engineering should be available to all",
    "Automation will eliminate the need for human work"
]

# Use in configuration
config['topics'] = custom_topics
```

### Topic Guidelines
- Keep topics debatable (not factual statements)
- Ensure both sides can be reasonably argued
- Make them relevant to your audience
- Consider current events and trends

## Voting and Results

### Voting Configuration
```yaml
voting:
  enabled: true
  voting_duration: 300  # 5 minutes
  allow_participant_voting: true
  require_justification: true
  anonymous_votes: false
```

### Accessing Results
```python
# After debate completion
results = await moderator.run_debate()

print(f"Winner: {results['winner']}")
print(f"Vote breakdown: {results['vote_counts']}")

# Export detailed results
await voting_system.export_results('json')
```

### Results Analysis
```python
# Get participant performance
for participant in participants:
    performance = voting_system.get_candidate_performance(participant.name)
    print(f"{participant.name}: {performance['win_rate']:.1%} win rate")
```

## Live Streaming

### Enable Streaming
```yaml
streaming:
  enabled: true
  websocket_port: 8080
  max_connections: 100
  broadcast_votes: true
```

### Streaming Server
```python
from app.streaming import StreamingServer

# Create streaming server
streaming = StreamingServer(
    chat_log=chat_log,
    voting_system=voting_system,
    config=streaming_config
)

await streaming.start()
# Server runs on localhost:8080
```

### Client Connection
```javascript
// Connect to stream
const ws = new WebSocket('ws://localhost:8080');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'message') {
        displayMessage(data.data);
    } else if (data.type === 'vote_update') {
        updateVoteDisplay(data.data);
    }
};
```

## Data Export and Analysis

### Transcript Export
```python
# Save debate transcript
await chat_log.save_transcript("debate_2024.json", "json")
await chat_log.save_transcript("debate_2024.txt", "txt") 
await chat_log.save_transcript("debate_2024.html", "html")
```

### Statistics and Analytics
```python
# Chat statistics
stats = chat_log.get_statistics()
print(f"Total messages: {stats['total_messages']}")
print(f"Average per minute: {stats['messages_per_minute']:.1f}")

# Participant statistics  
for participant in participants:
    stats = participant.get_stats()
    print(f"{participant.name}: {stats}")
```

### Voting Analysis
```python
# Export voting data
csv_data = await voting_system.export_results('csv')
txt_report = await voting_system.export_results('txt')

# Historical analysis
history = voting_system.vote_history
for session in history:
    print(f"Session: {session['timestamp']}")
    print(f"Winner: {session['results'].winner}")
```

## Troubleshooting

### Common Issues

#### API Key Problems
```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Set them if missing
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Connection Issues
```python
# Test bot connectivity
bot = BotClient(...)
success = await bot.warmup()
if not success:
    print("Bot connection failed")
```

#### Performance Issues
```yaml
# Reduce timeouts for faster sessions
debate:
  opening_statement_time: 60
  response_time: 30
  closing_statement_time: 45

# Limit message history
chat:
  max_message_length: 300
```

### Debug Mode
```bash
# Enable debug logging
python -m app.main --config debug_config.yaml
```

```yaml
# debug_config.yaml
chat:
  log_level: "DEBUG"
  save_transcripts: true
```

### Error Recovery
```python
# Handle errors gracefully
try:
    results = await moderator.run_debate()
except Exception as e:
    print(f"Debate error: {e}")
    # Save partial transcript
    await chat_log.save_transcript("error_recovery.json")
```

## Best Practices

### Bot Configuration
- Use different personalities for variety
- Balance pro/con/neutral stances
- Test API connections before debates
- Monitor response times and adjust timeouts

### Topic Selection
- Choose engaging, relevant topics
- Ensure balanced argumentation potential
- Test topics with different participant mixes
- Update topics regularly for freshness

### Session Management
- Start with shorter sessions for testing
- Monitor participant engagement
- Save transcripts for analysis
- Review voting patterns for improvements

### Performance Optimization
- Use appropriate API models for your needs
- Set reasonable timeouts
- Limit concurrent API calls
- Monitor system resources

This guide covers the core functionality of the AI Jubilee Debate System. For detailed API documentation, see [api_reference.md](api_reference.md).