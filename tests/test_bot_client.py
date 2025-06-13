"""
Tests for the BotClient class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.bot_client import BotClient, BotConfig, OpenAIProvider, AnthropicProvider
from app.chat_log import Message


@pytest.fixture
def bot_config():
    """Create test bot configuration."""
    return {
        'name': 'TestBot',
        'model': 'gpt-3.5-turbo',
        'provider': 'openai',
        'personality': 'Analytical and thoughtful',
        'stance': 'pro',
        'api_key': 'test-api-key'
    }


@pytest.fixture
def bot_client(bot_config):
    """Create test bot client."""
    return BotClient(**bot_config)


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        Message("Alice", "What do you think about AI?", 1640995200.0, 1),
        Message("moderator", "Please respond", 1640995210.0, 2, "moderator")
    ]


class TestBotConfig:
    """Test suite for BotConfig dataclass."""

    def test_bot_config_creation(self):
        """Test creating bot configuration."""
        config = BotConfig(
            name="TestBot",
            model="gpt-4",
            provider="openai",
            personality="Analytical",
            stance="pro"
        )

        assert config.name == "TestBot"
        assert config.model == "gpt-4"
        assert config.provider == "openai"
        assert config.personality == "Analytical"
        assert config.stance == "pro"
        assert config.temperature == 0.7  # Default value
        assert config.max_tokens == 300  # Default value


class TestBotClient:
    """Test suite for BotClient class."""

    def test_bot_client_initialization(self, bot_config):
        """Test bot client initialization."""
        bot = BotClient(**bot_config)

        assert bot.name == "TestBot"
        assert bot.config.model == "gpt-3.5-turbo"
        assert bot.config.provider == "openai"
        assert isinstance(bot.ai_provider, OpenAIProvider)
        assert bot.response_count == 0
        assert bot.conversation_history == []

    def test_bot_client_with_anthropic(self):
        """Test bot client with Anthropic provider."""
        bot = BotClient(
            name="AnthropicBot",
            model="claude-3-sonnet",
            provider="anthropic",
            personality="Balanced",
            stance="neutral",
            api_key="test-key"
        )

        assert isinstance(bot.ai_provider, AnthropicProvider)

    def test_bot_client_unsupported_provider(self):
        """Test bot client with unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            BotClient(
                name="TestBot",
                model="test-model",
                provider="unsupported",
                personality="Test",
                stance="pro",
                api_key="test-key"
            )

    @pytest.mark.asyncio
    async def test_get_response_success(self, bot_client, sample_messages):
        """Test successful response generation."""
        # Mock the AI provider
        mock_response = "I think AI has great potential for society."
        bot_client.ai_provider.generate_response = AsyncMock(return_value=mock_response)

        response = await bot_client.get_response("AI in society", sample_messages)

        assert response == mock_response
        assert bot_client.response_count == 1
        assert len(bot_client.conversation_history) == 1
        assert bot_client.stats['responses_generated'] == 1

    @pytest.mark.asyncio
    async def test_get_response_with_error(self, bot_client, sample_messages):
        """Test response generation with API error."""
        # Mock the AI provider to raise an exception
        bot_client.ai_provider.generate_response = AsyncMock(
            side_effect=Exception("API Error")
        )

        response = await bot_client.get_response("AI in society", sample_messages)

        # Should return fallback response
        assert isinstance(response, str)
        assert len(response) > 0
        assert bot_client.stats['errors'] == 1

    def test_prepare_messages(self, bot_client, sample_messages):
        """Test message preparation for AI model."""
        messages = bot_client._prepare_messages("AI topic", sample_messages)

        assert len(messages) >= 1  # At least system message
        assert messages[0]['role'] == 'system'
        assert "AI topic" in messages[0]['content']
        assert "TestBot" in messages[0]['content']

    def test_create_system_prompt_pro_stance(self, bot_client):
        """Test system prompt creation for pro stance."""
        prompt = bot_client._create_system_prompt("AI is beneficial")

        assert "TestBot" in prompt
        assert "AI is beneficial" in prompt
        assert "Analytical and thoughtful" in prompt
        assert "IN FAVOR" in prompt

    def test_create_system_prompt_con_stance(self):
        """Test system prompt creation for con stance."""
        bot = BotClient(
            name="ConBot",
            model="gpt-3.5-turbo",
            provider="openai",
            personality="Critical",
            stance="con",
            api_key="test-key"
        )

        prompt = bot._create_system_prompt("AI topic")
        assert "AGAINST" in prompt

    def test_create_system_prompt_neutral_stance(self):
        """Test system prompt creation for neutral stance."""
        bot = BotClient(
            name="NeutralBot",
            model="gpt-3.5-turbo",
            provider="openai",
            personality="Balanced",
            stance="neutral",
            api_key="test-key"
        )

        prompt = bot._create_system_prompt("AI topic")
        assert "balanced perspectives" in prompt

    def test_generate_fallback_response(self, bot_client):
        """Test fallback response generation."""
        response = bot_client._generate_fallback_response("AI topic")

        assert isinstance(response, str)
        assert len(response) > 0
        assert "AI topic" in response or "perspective" in response.lower()

    @pytest.mark.asyncio
    async def test_receive_message(self, bot_client):
        """Test receiving a message."""
        message = Message("Alice", "Hello bot", 1640995200.0, 1)

        await bot_client.receive_message(message)

        # Should be added to conversation history
        assert len(bot_client.conversation_history) == 1
        assert "Alice: Hello bot" in bot_client.conversation_history[0]['content']

        # Message queue should have the message
        queued_message = await bot_client.message_queue.get()
        assert queued_message == message

    @pytest.mark.asyncio
    async def test_receive_own_message(self, bot_client):
        """Test receiving own message (should not be added to history)."""
        message = Message("TestBot", "My own message", 1640995200.0, 1)

        await bot_client.receive_message(message)

        # Should not be added to conversation history
        assert len(bot_client.conversation_history) == 0

    def test_update_stats_success(self, bot_client):
        """Test updating statistics on success."""
        bot_client._update_stats(1.5, success=True)

        assert bot_client.stats['responses_generated'] == 1
        assert bot_client.stats['average_response_time'] == 1.5
        assert bot_client.stats['total_response_time'] == 1.5

    def test_update_stats_error(self, bot_client):
        """Test updating statistics on error."""
        bot_client._update_stats(2.0, success=False)

        assert bot_client.stats['errors'] == 1
        assert bot_client.stats['responses_generated'] == 0

    def test_get_stats(self, bot_client):
        """Test getting bot statistics."""
        # Add some test data
        bot_client.stats['responses_generated'] = 5
        bot_client.stats['total_response_time'] = 10.0
        bot_client.stats['errors'] = 1
        bot_client._update_stats(0, success=True)  # Recalculate average

        stats = bot_client.get_stats()

        assert stats['name'] == "TestBot"
        assert stats['model'] == "gpt-3.5-turbo"
        assert stats['provider'] == "openai"
        assert stats['responses_generated'] == 5
        assert stats['total_errors'] == 1
        assert 'success_rate' in stats
        assert 'average_response_time' in stats

    def test_update_personality(self, bot_client):
        """Test updating bot personality."""
        bot_client.update_personality("New personality", "con")

        assert bot_client.config.personality == "New personality"
        assert bot_client.config.stance == "con"

    def test_reset_conversation(self, bot_client):
        """Test resetting conversation history."""
        # Add some conversation history
        bot_client.conversation_history = [
            {'role': 'user', 'content': 'Test message'}
        ]
        bot_client.response_count = 3

        bot_client.reset_conversation()

        assert bot_client.conversation_history == []
        assert bot_client.response_count == 0

    @pytest.mark.asyncio
    async def test_warmup_success(self, bot_client):
        """Test successful bot warmup."""
        bot_client.ai_provider.generate_response = AsyncMock(return_value="Ready")

        result = await bot_client.warmup()

        assert result == True

    @pytest.mark.asyncio
    async def test_warmup_failure(self, bot_client):
        """Test failed bot warmup."""
        bot_client.ai_provider.generate_response = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await bot_client.warmup()

        assert result == False

    def test_str_representation(self, bot_client):
        """Test string representation of bot."""
        string_repr = str(bot_client)

        assert "TestBot" in string_repr
        assert "gpt-3.5-turbo" in string_repr
        assert "pro" in string_repr

    def test_repr_representation(self, bot_client):
        """Test detailed string representation of bot."""
        repr_str = repr(bot_client)

        assert "BotClient" in repr_str
        assert "name='TestBot'" in repr_str
        assert "model='gpt-3.5-turbo'" in repr_str


class TestOpenAIProvider:
    """Test suite for OpenAIProvider class."""

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider("test-api-key")
        assert provider.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        provider = OpenAIProvider("test-key")
        config = BotConfig("TestBot", "gpt-3.5-turbo", "openai", "Test", "pro")
        messages = [{"role": "user", "content": "Hello"}]

        # Mock OpenAI client
        with patch('app.bot_client.openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Hello! How can I help?"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            response = await provider.generate_response(messages, config)

            assert response == "Hello! How can I help?"
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_error(self):
        """Test response generation with error."""
        provider = OpenAIProvider("test-key")
        config = BotConfig("TestBot", "gpt-3.5-turbo", "openai", "Test", "pro")
        messages = [{"role": "user", "content": "Hello"}]

        with patch('app.bot_client.openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API Error")
            )

            with pytest.raises(Exception, match="OpenAI API error"):
                await provider.generate_response(messages, config)


class TestAnthropicProvider:
    """Test suite for AnthropicProvider class."""

    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider("test-api-key")
        assert provider.api_key == "test-api-key"

    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """Test successful response generation."""
        provider = AnthropicProvider("test-key")
        config = BotConfig("TestBot", "claude-3-sonnet", "anthropic", "Test", "pro")
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"}
        ]

        with patch('app.bot_client.anthropic.AsyncAnthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            # Mock response
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Hello! How can I assist you?"
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            response = await provider.generate_response(messages, config)

            assert response == "Hello! How can I assist you?"
            mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_error(self):
        """Test response generation with error."""
        provider = AnthropicProvider("test-key")
        config = BotConfig("TestBot", "claude-3-sonnet", "anthropic", "Test", "pro")
        messages = [{"role": "user", "content": "Hello"}]

        with patch('app.bot_client.anthropic.AsyncAnthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create = AsyncMock(
                side_effect=Exception("API Error")
            )

            with pytest.raises(Exception, match="Anthropic API error"):
                await provider.generate_response(messages, config)


@pytest.mark.asyncio
async def test_conversation_history_management(bot_client):
    """Test conversation history management."""
    # Add messages beyond the limit
    for i in range(25):
        message = Message(f"User{i}", f"Message {i}", 1640995200.0 + i, i)
        await bot_client.receive_message(message)

    # Should be limited to avoid memory issues
    assert len(bot_client.conversation_history) <= 20


@pytest.mark.asyncio
async def test_bot_response_timing(bot_client, sample_messages):
    """Test that response timing is tracked."""
    bot_client.ai_provider.generate_response = AsyncMock(return_value="Test response")

    # Simulate some delay
    async def delayed_response(*args):
        await asyncio.sleep(0.01)
        return "Delayed response"

    bot_client.ai_provider.generate_response = delayed_response

    await bot_client.get_response("Test topic", sample_messages)

    assert bot_client.stats['average_response_time'] > 0
    assert bot_client.stats['total_response_time'] > 0