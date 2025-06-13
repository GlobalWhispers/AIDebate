"""
Tests for the ChatLog class.
"""

import pytest
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import patch, mock_open
from app.chat_log import ChatLog, Message


@pytest.fixture
def chat_log():
    """Create a test chat log."""
    return ChatLog(max_messages=100)


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        Message("Alice", "Hello everyone!", time.time(), 1),
        Message("Bob", "Hi Alice!", time.time(), 2),
        Message("moderator", "Welcome to the debate", time.time(), 3, "moderator")
    ]


class TestMessage:
    """Test suite for Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        timestamp = time.time()
        msg = Message("Alice", "Hello world", timestamp, 1)

        assert msg.sender == "Alice"
        assert msg.content == "Hello world"
        assert msg.timestamp == timestamp
        assert msg.message_id == 1
        assert msg.message_type == "chat"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test message with metadata."""
        metadata = {"urgency": "high", "topic": "AI"}
        msg = Message("Bob", "Important point", time.time(), 2,
                      message_type="system", metadata=metadata)

        assert msg.message_type == "system"
        assert msg.metadata == metadata

    def test_formatted_timestamp(self):
        """Test formatted timestamp property."""
        timestamp = 1640995200.0  # Known timestamp
        msg = Message("Alice", "Test", timestamp, 1)

        formatted = msg.formatted_timestamp
        assert isinstance(formatted, str)
        assert ":" in formatted  # Should contain time separator

    def test_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message("Alice", "Test", time.time(), 1)
        msg_dict = msg.to_dict()

        assert isinstance(msg_dict, dict)
        assert msg_dict["sender"] == "Alice"
        assert msg_dict["content"] == "Test"
        assert "timestamp" in msg_dict
        assert "message_id" in msg_dict

    def test_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "sender": "Bob",
            "content": "Test message",
            "timestamp": time.time(),
            "message_id": 5,
            "message_type": "chat",
            "metadata": {}
        }

        msg = Message.from_dict(data)

        assert msg.sender == "Bob"
        assert msg.content == "Test message"
        assert msg.message_id == 5


class TestChatLog:
    """Test suite for ChatLog class."""

    def test_chat_log_initialization(self):
        """Test chat log initialization."""
        chat_log = ChatLog(max_messages=50)

        assert len(chat_log.messages) == 0
        assert chat_log.message_counter == 0
        assert chat_log.subscribers == []
        assert chat_log.stats["total_messages"] == 0

    @pytest.mark.asyncio
    async def test_add_message(self, chat_log):
        """Test adding a message."""
        message = await chat_log.add_message("Alice", "Hello world")

        assert isinstance(message, Message)
        assert message.sender == "Alice"
        assert message.content == "Hello world"
        assert message.message_id == 1
        assert len(chat_log.messages) == 1
        assert chat_log.stats["total_messages"] == 1
        assert chat_log.stats["messages_by_sender"]["Alice"] == 1

    @pytest.mark.asyncio
    async def test_add_multiple_messages(self, chat_log):
        """Test adding multiple messages."""
        await chat_log.add_message("Alice", "First message")
        await chat_log.add_message("Bob", "Second message")
        await chat_log.add_message("Alice", "Third message")

        assert len(chat_log.messages) == 3
        assert chat_log.message_counter == 3
        assert chat_log.stats["messages_by_sender"]["Alice"] == 2
        assert chat_log.stats["messages_by_sender"]["Bob"] == 1

    @pytest.mark.asyncio
    async def test_message_ordering(self, chat_log):
        """Test that messages maintain chronological order."""
        msg1 = await chat_log.add_message("Alice", "First")
        await asyncio.sleep(0.01)  # Small delay
        msg2 = await chat_log.add_message("Bob", "Second")

        messages = list(chat_log.messages)
        assert messages[0].message_id == 1
        assert messages[1].message_id == 2
        assert messages[0].timestamp < messages[1].timestamp

    @pytest.mark.asyncio
    async def test_max_messages_limit(self):
        """Test message limit enforcement."""
        chat_log = ChatLog(max_messages=3)

        # Add more messages than the limit
        for i in range(5):
            await chat_log.add_message("User", f"Message {i}")

        assert len(chat_log.messages) == 3  # Should be limited

        # Check that oldest messages were removed
        messages = list(chat_log.messages)
        assert "Message 2" in messages[0].content
        assert "Message 4" in messages[2].content

    @pytest.mark.asyncio
    async def test_subscription_system(self, chat_log):
        """Test message subscription system."""
        queue = chat_log.subscribe()

        # Add a message
        message = await chat_log.add_message("Alice", "Test message")

        # Check that subscriber received the message
        received_message = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_message.content == "Test message"
        assert received_message.sender == "Alice"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, chat_log):
        """Test multiple subscribers."""
        queue1 = chat_log.subscribe()
        queue2 = chat_log.subscribe()

        await chat_log.add_message("Alice", "Broadcast message")

        # Both subscribers should receive the message
        msg1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        msg2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert msg1.content == msg2.content == "Broadcast message"

    def test_unsubscribe(self, chat_log):
        """Test unsubscribing from messages."""
        queue = chat_log.subscribe()
        assert queue in chat_log.subscribers

        chat_log.unsubscribe(queue)
        assert queue not in chat_log.subscribers

    def test_get_messages_no_filter(self, chat_log, sample_messages):
        """Test getting all messages without filters."""
        # Manually add messages to chat log
        for msg in sample_messages:
            chat_log.messages.append(msg)

        messages = chat_log.get_messages()
        assert len(messages) == 3
        assert messages[0].sender == "Alice"

    def test_get_messages_with_limit(self, chat_log, sample_messages):
        """Test getting messages with limit."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        messages = chat_log.get_messages(limit=2)
        assert len(messages) == 2
        # Should get the last 2 messages
        assert messages[0].sender == "Bob"
        assert messages[1].sender == "moderator"

    def test_get_messages_by_sender(self, chat_log, sample_messages):
        """Test filtering messages by sender."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        alice_messages = chat_log.get_messages(sender="Alice")
        assert len(alice_messages) == 1
        assert alice_messages[0].sender == "Alice"

    def test_get_messages_by_type(self, chat_log, sample_messages):
        """Test filtering messages by type."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        moderator_messages = chat_log.get_messages(message_type="moderator")
        assert len(moderator_messages) == 1
        assert moderator_messages[0].message_type == "moderator"

    def test_get_messages_since_timestamp(self, chat_log):
        """Test filtering messages by timestamp."""
        # Add messages with known timestamps
        old_time = time.time() - 100
        new_time = time.time()

        chat_log.messages.append(Message("Alice", "Old", old_time, 1))
        chat_log.messages.append(Message("Bob", "New", new_time, 2))

        cutoff = time.time() - 50
        recent_messages = chat_log.get_messages(since_timestamp=cutoff)

        assert len(recent_messages) == 1
        assert recent_messages[0].content == "New"

    def test_get_recent_messages(self, chat_log, sample_messages):
        """Test getting recent messages."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        recent = chat_log.get_recent_messages(2)
        assert len(recent) == 2
        assert recent[-1].sender == "moderator"  # Most recent

    def test_get_conversation_context(self, chat_log):
        """Test getting conversation context for a participant."""
        # Add various messages
        messages = [
            Message("Alice", "Hello", time.time(), 1),
            Message("Bob", "Hi Alice", time.time(), 2),
            Message("moderator", "Welcome everyone", time.time(), 3, "moderator"),
            Message("Alice", "Thanks!", time.time(), 4),
            Message("Charlie", "Good luck", time.time(), 5)
        ]

        for msg in messages:
            chat_log.messages.append(msg)

        context = chat_log.get_conversation_context("Alice", context_length=3)

        # Should include Alice's messages and moderator messages
        assert len(context) <= 3
        assert any(msg.sender == "Alice" for msg in context)
        assert any(msg.message_type == "moderator" for msg in context)

    def test_search_messages(self, chat_log, sample_messages):
        """Test searching messages by content."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        # Case insensitive search
        results = chat_log.search_messages("hello")
        assert len(results) == 1
        assert "Hello" in results[0].content

        # Case sensitive search
        results = chat_log.search_messages("Hello", case_sensitive=True)
        assert len(results) == 1

        results = chat_log.search_messages("hello", case_sensitive=True)
        assert len(results) == 0

    def test_get_statistics(self, chat_log, sample_messages):
        """Test getting chat log statistics."""
        for msg in sample_messages:
            chat_log.messages.append(msg)
            chat_log.stats["total_messages"] += 1
            sender = msg.sender
            chat_log.stats["messages_by_sender"][sender] = (
                    chat_log.stats["messages_by_sender"].get(sender, 0) + 1
            )

        stats = chat_log.get_statistics()

        assert stats["total_messages"] == 3
        assert stats["unique_senders"] == 2  # Alice, Bob, moderator
        assert "messages_by_sender" in stats
        assert "messages_per_minute" in stats
        assert "session_duration_minutes" in stats

    @pytest.mark.asyncio
    async def test_save_transcript_json(self, chat_log, tmp_path):
        """Test saving transcript in JSON format."""
        await chat_log.add_message("Alice", "Test message")

        output_file = tmp_path / "transcript.json"
        await chat_log.save_transcript(str(output_file), "json")

        assert output_file.exists()

        with open(output_file, 'r') as f:
            data = json.load(f)

        assert "metadata" in data
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_save_transcript_txt(self, chat_log, tmp_path):
        """Test saving transcript in TXT format."""
        await chat_log.add_message("Alice", "Test message")

        output_file = tmp_path / "transcript.txt"
        await chat_log.save_transcript(str(output_file), "txt")

        assert output_file.exists()

        content = output_file.read_text()
        assert "DEBATE TRANSCRIPT" in content
        assert "Alice: Test message" in content

    @pytest.mark.asyncio
    async def test_save_transcript_html(self, chat_log, tmp_path):
        """Test saving transcript in HTML format."""
        await chat_log.add_message("Alice", "Test message")
        await chat_log.add_message("moderator", "System message",
                                   message_type="moderator")

        output_file = tmp_path / "transcript.html"
        await chat_log.save_transcript(str(output_file), "html")

        assert output_file.exists()

        content = output_file.read_text()
        assert "<!DOCTYPE html>" in content
        assert "Alice" in content
        assert "moderator" in content
        assert "class=\"moderator\"" in content

    @pytest.mark.asyncio
    async def test_save_transcript_invalid_format(self, chat_log):
        """Test saving transcript with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            await chat_log.save_transcript("test.xml", "xml")

    @pytest.mark.asyncio
    async def test_load_transcript(self, chat_log, tmp_path):
        """Test loading transcript from file."""
        # Save a transcript first
        await chat_log.add_message("Alice", "Original message")
        output_file = tmp_path / "transcript.json"
        await chat_log.save_transcript(str(output_file), "json")

        # Clear chat log and reload
        chat_log.clear()
        assert len(chat_log.messages) == 0

        await chat_log.load_transcript(str(output_file))

        assert len(chat_log.messages) == 1
        assert list(chat_log.messages)[0].content == "Original message"

    @pytest.mark.asyncio
    async def test_load_transcript_file_not_found(self, chat_log):
        """Test loading transcript from non-existent file."""
        with pytest.raises(FileNotFoundError):
            await chat_log.load_transcript("nonexistent.json")

    def test_clear_chat_log(self, chat_log, sample_messages):
        """Test clearing the chat log."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        chat_log.message_counter = 5
        chat_log.stats["total_messages"] = 3

        chat_log.clear()

        assert len(chat_log.messages) == 0
        assert chat_log.message_counter == 0
        assert chat_log.stats["total_messages"] == 0
        assert chat_log.stats["messages_by_sender"] == {}

    def test_chat_log_len(self, chat_log, sample_messages):
        """Test chat log length."""
        assert len(chat_log) == 0

        for msg in sample_messages:
            chat_log.messages.append(msg)

        assert len(chat_log) == 3

    def test_chat_log_iteration(self, chat_log, sample_messages):
        """Test iterating over chat log."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        iterated_messages = list(chat_log)
        assert len(iterated_messages) == 3
        assert iterated_messages[0].sender == "Alice"

    def test_chat_log_indexing(self, chat_log, sample_messages):
        """Test indexing chat log."""
        for msg in sample_messages:
            chat_log.messages.append(msg)

        first_message = chat_log[0]
        assert first_message.sender == "Alice"

        last_message = chat_log[-1]
        assert last_message.sender == "moderator"
        