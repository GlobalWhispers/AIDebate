"""
Shared chat log system for managing debate messages with timestamps and ordering.
Enhanced with web broadcasting capabilities for real-time interface.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import deque

# Avoid circular imports
if TYPE_CHECKING:
    from app.web_server import DebateWebServer


@dataclass
class Message:
    """Represents a single chat message."""
    sender: str
    content: str
    timestamp: float
    message_id: int
    message_type: str = "chat"  # chat, system, moderator, vote
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def formatted_timestamp(self) -> str:
        """Get human-readable timestamp."""
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(**data)


class ChatLog:
    """
    Manages the shared chat log with thread-safe message handling.
    Enhanced with web broadcasting for real-time interface updates.
    """

    def __init__(self, max_messages: int = 1000):
        self.messages: deque = deque(maxlen=max_messages)
        self.message_counter = 0
        self.subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

        # Web broadcasting
        self.web_server: Optional['DebateWebServer'] = None
        self.response_times: Dict[str, float] = {}

        # Enhanced statistics
        self.stats = {
            'total_messages': 0,
            'messages_by_sender': {},
            'start_time': time.time(),
            'bot_responses': 0,
            'human_responses': 0,
            'moderator_messages': 0,
            'silence_breaks': 0
        }

    def set_web_server(self, web_server: 'DebateWebServer'):
        """Set the web server for broadcasting messages."""
        self.web_server = web_server
        print("🔗 Chat log connected to web server for real-time broadcasting")

    def start_response_timer(self, sender: str):
        """Start timing a participant's response."""
        self.response_times[sender] = time.time()

    def get_response_time(self, sender: str) -> Optional[float]:
        """Get and clear response time for a sender."""
        if sender in self.response_times:
            response_time = time.time() - self.response_times[sender]
            del self.response_times[sender]
            return response_time
        return None

    async def add_message(self, sender: str, content: str,
                          message_type: str = "chat",
                          metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Add a new message to the chat log and broadcast to web interface.

        Args:
            sender: Name of the message sender
            content: Message content
            message_type: Type of message (chat, system, moderator, vote)
            metadata: Additional message metadata

        Returns:
            The created Message object
        """
        async with self._lock:
            self.message_counter += 1

            # Get response time if being tracked
            response_time = self.get_response_time(sender)

            message = Message(
                sender=sender,
                content=content,
                timestamp=time.time(),
                message_id=self.message_counter,
                message_type=message_type,
                metadata=metadata or {}
            )

            self.messages.append(message)

            # Update enhanced statistics
            self.stats['total_messages'] += 1
            self.stats['messages_by_sender'][sender] = (
                    self.stats['messages_by_sender'].get(sender, 0) + 1
            )

            # Update type-specific stats
            if sender in ["Socrates", "Advocate", "Skeptic", "Mediator"]:
                self.stats['bot_responses'] += 1

                # Check for silence breaks (responses within 10 seconds)
                if len(self.messages) > 1:
                    last_message = list(self.messages)[-2]
                    time_diff = message.timestamp - last_message.timestamp
                    if time_diff < 10:
                        self.stats['silence_breaks'] += 1

            elif sender == "Moderator":
                self.stats['moderator_messages'] += 1
            else:
                self.stats['human_responses'] += 1

            # Notify subscribers
            await self._notify_subscribers(message)

            # Broadcast to web interface
            if self.web_server:
                try:
                    # Determine web message type
                    web_message_type = self._get_web_message_type(sender, message_type)

                    await self.web_server.broadcast_message(
                        sender=sender,
                        content=content,
                        message_type=web_message_type,
                        response_time=response_time
                    )
                except Exception as e:
                    print(f"⚠️ Failed to broadcast message to web: {e}")

            return message

    def _get_web_message_type(self, sender: str, message_type: str) -> str:
        """Determine web message type based on sender and message type."""
        if message_type in ["moderator", "system"]:
            return "moderator"
        elif sender == "Moderator":
            return "moderator"
        elif sender in ["Socrates", "Advocate", "Skeptic", "Mediator"]:
            return "bot"
        else:
            return "human"

    async def _notify_subscribers(self, message: Message):
        """Notify all subscribers of new message."""
        # Remove closed queues
        self.subscribers = [q for q in self.subscribers if not getattr(q, "_closed", False)]
        # Send to all active subscribers
        for queue in self.subscribers:
            try:
                await queue.put(message)
            except Exception as e:
                print(f"Failed to notify subscriber: {e}")

    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to receive new messages.

        Returns:
            Queue that will receive new Message objects
        """
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def get_messages(self, limit: Optional[int] = None,
                     sender: Optional[str] = None,
                     message_type: Optional[str] = None,
                     since_timestamp: Optional[float] = None) -> List[Message]:
        """
        Get messages with optional filtering.

        Args:
            limit: Maximum number of messages to return
            sender: Filter by sender name
            message_type: Filter by message type
            since_timestamp: Only return messages after this timestamp

        Returns:
            List of matching messages
        """
        messages = list(self.messages)

        # Apply filters
        if sender:
            messages = [m for m in messages if m.sender == sender]

        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        if since_timestamp:
            messages = [m for m in messages if m.timestamp > since_timestamp]

        # Apply limit
        if limit:
            messages = messages[-limit:]

        return messages

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get the most recent messages."""
        return list(self.messages)[-count:]

    def get_conversation_context(self, participant: str,
                                 context_length: int = 5) -> List[Message]:
        """
        Get conversation context for a participant.

        Args:
            participant: Participant name
            context_length: Number of recent messages to include

        Returns:
            Recent messages for context
        """
        recent = self.get_recent_messages(context_length * 2)

        # Include messages to/from the participant and moderator messages
        context = []
        for msg in recent:
            if (msg.sender == participant or
                    msg.message_type in ['moderator', 'system'] or
                    participant in msg.content):
                context.append(msg)

        return context[-context_length:]

    def search_messages(self, query: str, case_sensitive: bool = False) -> List[Message]:
        """
        Search messages by content.

        Args:
            query: Search query
            case_sensitive: Whether search should be case sensitive

        Returns:
            List of messages containing the query
        """
        if not case_sensitive:
            query = query.lower()

        results = []
        for message in self.messages:
            content = message.content if case_sensitive else message.content.lower()
            if query in content:
                results.append(message)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced chat log statistics."""
        duration = time.time() - self.stats['start_time']

        return {
            'total_messages': self.stats['total_messages'],
            'bot_responses': self.stats['bot_responses'],
            'human_responses': self.stats['human_responses'],
            'moderator_messages': self.stats['moderator_messages'],
            'silence_breaks': self.stats['silence_breaks'],
            'unique_senders': len(self.stats['messages_by_sender']),
            'messages_by_sender': dict(self.stats['messages_by_sender']),
            'messages_per_minute': (self.stats['total_messages'] / (duration / 60)
                                    if duration > 0 else 0),
            'session_duration_minutes': duration / 60,
            'current_message_count': len(self.messages),
            'response_rate': {
                'bots': self.stats['bot_responses'] / max(1, self.stats['total_messages']),
                'humans': self.stats['human_responses'] / max(1, self.stats['total_messages']),
                'moderator': self.stats['moderator_messages'] / max(1, self.stats['total_messages'])
            }
        }

    async def broadcast_statistics(self):
        """Broadcast current statistics to web interface."""
        if self.web_server:
            try:
                stats = self.get_statistics()
                await self.web_server.broadcast_stats(stats)
            except Exception as e:
                print(f"⚠️ Failed to broadcast statistics: {e}")

    async def save_transcript(self, filename: str,
                              format_type: str = "json") -> None:
        """
        Save chat transcript to file.

        Args:
            filename: Output filename
            format_type: Format (json, txt, html)
        """
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        messages = list(self.messages)

        if format_type == "json":
            data = {
                'metadata': {
                    'export_timestamp': time.time(),
                    'total_messages': len(messages),
                    'statistics': self.get_statistics(),
                    'web_enabled': self.web_server is not None
                },
                'messages': [msg.to_dict() for msg in messages]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format_type == "txt":
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=== AI JUBILEE DEBATE TRANSCRIPT ===\n")
                f.write(f"Session Duration: {self.get_statistics()['session_duration_minutes']:.1f} minutes\n")
                f.write(f"Total Messages: {len(messages)}\n")
                f.write(f"Bot Responses: {self.stats['bot_responses']}\n")
                f.write(f"Silence Breaks: {self.stats['silence_breaks']}\n\n")

                for msg in messages:
                    f.write(f"[{msg.formatted_timestamp}] {msg.sender}: {msg.content}\n")

        elif format_type == "html":
            html_content = self._generate_html_transcript(messages)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _generate_html_transcript(self, messages: List[Message]) -> str:
        """Generate enhanced HTML transcript."""
        stats = self.get_statistics()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Jubilee Debate Transcript</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #4f46e5; }}
                .stat-label {{ color: #666; margin-top: 5px; }}
                .message {{ margin: 10px 0; padding: 15px; border-left: 4px solid #ccc; background: white; border-radius: 0 8px 8px 0; }}
                .moderator {{ border-left-color: #8b5cf6; background: #faf5ff; }}
                .bot {{ border-left-color: #10b981; background: #f0fdf4; }}
                .human {{ border-left-color: #f59e0b; background: #fffbeb; }}
                .system {{ border-left-color: #6c757d; background: #e9ecef; }}
                .timestamp {{ color: #6c757d; font-size: 0.9em; }}
                .sender {{ font-weight: bold; margin-right: 10px; }}
                .response-time {{ background: #4f46e5; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 10px; }}
                .content {{ margin-top: 8px; line-height: 1.5; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎭 AI Jubilee Debate Transcript</h1>
                <p><strong>Session Duration:</strong> {stats['session_duration_minutes']:.1f} minutes</p>
                <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{stats['total_messages']}</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['bot_responses']}</div>
                    <div class="stat-label">Bot Responses</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['silence_breaks']}</div>
                    <div class="stat-label">Silence Breaks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['messages_per_minute']:.1f}</div>
                    <div class="stat-label">Messages/Minute</div>
                </div>
            </div>
        """

        for msg in messages:
            css_class = self._get_web_message_type(msg.sender, msg.message_type)
            html += f"""
            <div class="message {css_class}">
                <div>
                    <span class="timestamp">[{msg.formatted_timestamp}]</span>
                    <span class="sender">{msg.sender}:</span>
                </div>
                <div class="content">{msg.content.replace('', '<br>')}</div>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    async def load_transcript(self, filename: str) -> None:
        """
        Load transcript from JSON file.

        Args:
            filename: Input filename
        """
        filepath = Path(filename)

        if not filepath.exists():
            raise FileNotFoundError(f"Transcript file not found: {filename}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clear current messages
        async with self._lock:
            self.messages.clear()
            self.message_counter = 0

            # Reset stats
            self.stats = {
                'total_messages': 0,
                'messages_by_sender': {},
                'start_time': time.time(),
                'bot_responses': 0,
                'human_responses': 0,
                'moderator_messages': 0,
                'silence_breaks': 0
            }

            # Load messages
            for msg_data in data.get('messages', []):
                message = Message.from_dict(msg_data)
                self.messages.append(message)
                self.message_counter = max(self.message_counter, message.message_id)

                # Update stats
                self.stats['total_messages'] += 1
                self.stats['messages_by_sender'][message.sender] = (
                    self.stats['messages_by_sender'].get(message.sender, 0) + 1
                )

        print(f"📄 Loaded {len(self.messages)} messages from transcript")

    def clear(self) -> None:
        """Clear all messages from the chat log."""
        self.messages.clear()
        self.message_counter = 0
        self.response_times.clear()
        self.stats = {
            'total_messages': 0,
            'messages_by_sender': {},
            'start_time': time.time(),
            'bot_responses': 0,
            'human_responses': 0,
            'moderator_messages': 0,
            'silence_breaks': 0
        }

    def get_participant_stats(self, participant_name: str) -> Dict[str, Any]:
        """Get statistics for a specific participant."""
        participant_messages = [msg for msg in self.messages if msg.sender == participant_name]

        if not participant_messages:
            return {'message_count': 0, 'participation_rate': 0.0}

        total_time = time.time() - self.stats['start_time']

        return {
            'message_count': len(participant_messages),
            'participation_rate': len(participant_messages) / max(1, self.stats['total_messages']),
            'messages_per_minute': len(participant_messages) / (total_time / 60) if total_time > 0 else 0,
            'first_message_time': min(msg.timestamp for msg in participant_messages) if participant_messages else 0,
            'last_message_time': max(msg.timestamp for msg in participant_messages) if participant_messages else 0
        }

    async def export_web_data(self) -> Dict[str, Any]:
        """Export data formatted for web interface."""
        return {
            'messages': [
                {
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp * 1000,  # JavaScript timestamp
                    'message_type': self._get_web_message_type(msg.sender, msg.message_type),
                    'formatted_time': msg.formatted_timestamp
                }
                for msg in self.messages
            ],
            'statistics': self.get_statistics(),
            'participants': {
                sender: self.get_participant_stats(sender)
                for sender in self.stats['messages_by_sender'].keys()
            }
        }

    def __len__(self) -> int:
        """Return number of messages in the log."""
        return len(self.messages)

    def __iter__(self):
        """Iterate over messages."""
        return iter(self.messages)

    def __getitem__(self, index) -> Message:
        """Get message by index."""
        return list(self.messages)[index]

    def __bool__(self) -> bool:
        """Return True if chat log has messages."""
        return len(self.messages) > 0