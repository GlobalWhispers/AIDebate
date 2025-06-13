"""
Tests for the HumanClient class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.human_client import HumanClient, CLIInterface, WebInterface, InterfaceConfig
from app.chat_log import Message


@pytest.fixture
def interface_config():
    """Create test interface configuration."""
    return {
        'mode': 'cli',
        'enable_rich_formatting': False,  # Disable for testing
        'show_typing_indicators': True,
        'enable_reactions': True,
        'input_timeout': 60
    }


@pytest.fixture
def human_client(interface_config):
    """Create test human client."""
    return HumanClient("TestHuman", interface_config)


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        Message("Alice", "What's your opinion?", 1640995200.0, 1),
        Message("Bob", "I think...", 1640995210.0, 2),
        Message("moderator", "Please respond", 1640995220.0, 3, "moderator")
    ]


class TestInterfaceConfig:
    """Test suite for InterfaceConfig dataclass."""

    def test_interface_config_defaults(self):
        """Test interface config with default values."""
        config = InterfaceConfig()

        assert config.mode == "cli"
        assert config.enable_rich_formatting == True
        assert config.show_typing_indicators == True
        assert config.enable_reactions == True
        assert config.input_timeout == 120

    def test_interface_config_custom(self):
        """Test interface config with custom values."""
        config = InterfaceConfig(
            mode="web",
            enable_rich_formatting=False,
            input_timeout=90
        )

        assert config.mode == "web"
        assert config.enable_rich_formatting == False
        assert config.input_timeout == 90


class TestCLIInterface:
    """Test suite for CLIInterface class."""

    def test_cli_interface_initialization(self):
        """Test CLI interface initialization."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        assert interface.config == config
        assert interface.rich_console is None  # Rich disabled

    @pytest.mark.asyncio
    async def test_display_basic_message(self):
        """Test displaying message with basic formatting."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        message = Message("Alice", "Hello world", 1640995200.0, 1)

        with patch('builtins.print') as mock_print:
            await interface.display_message(message)
            mock_print.assert_called_once()

    @pytest.mark.asyncio
    async def test_display_moderator_message(self):
        """Test displaying moderator message."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        message = Message("moderator", "Welcome!", 1640995200.0, 1, "moderator")

        with patch('builtins.print') as mock_print:
            await interface.display_message(message)
            mock_print.assert_called_once()
            # Should have moderator prefix
            args = mock_print.call_args[0]
            assert "🎭" in args[0]

    @pytest.mark.asyncio
    async def test_get_input_success(self):
        """Test successful input retrieval."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        with patch('builtins.input', return_value="Test response"):
            response = await interface.get_input("Enter response:", timeout=1)
            assert response == "Test response"

    @pytest.mark.asyncio
    async def test_get_input_timeout(self):
        """Test input timeout."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        # Mock input to simulate hanging
        async def slow_input():
            await asyncio.sleep(2)
            return "Too late"

        interface._get_user_input = slow_input

        response = await interface.get_input("Enter response:", timeout=0.1)
        assert response == ""  # Should return empty string on timeout

    @pytest.mark.asyncio
    async def test_show_notification(self):
        """Test showing notifications."""
        config = InterfaceConfig(enable_rich_formatting=False)
        interface = CLIInterface(config)

        with patch('builtins.print') as mock_print:
            await interface.show_notification("Test notification", "info")
            mock_print.assert_called_once()
            args = mock_print.call_args[0]
            assert "ℹ️" in args[0]
            assert "Test notification" in args[0]


class TestWebInterface:
    """Test suite for WebInterface class."""

    def test_web_interface_initialization(self):
        """Test web interface initialization."""
        config = InterfaceConfig(mode="web")
        interface = WebInterface(config)

        assert interface.config == config
        assert interface.websocket is None
        assert interface.pending_responses == {}

    @pytest.mark.asyncio
    async def test_display_message_no_websocket(self):
        """Test displaying message without websocket connection."""
        config = InterfaceConfig(mode="web")
        interface = WebInterface(config)

        message = Message("Alice", "Hello", 1640995200.0, 1)

        # Should not raise an error even without websocket
        await interface.display_message(message)

    @pytest.mark.asyncio
    async def test_get_input_no_websocket(self):
        """Test getting input without websocket connection."""
        config = InterfaceConfig(mode="web")
        interface = WebInterface(config)

        response = await interface.get_input("Enter response:")
        assert response == ""  # Should return empty string


class TestHumanClient:
    """Test suite for HumanClient class."""

    def test_human_client_initialization(self, interface_config):
        """Test human client initialization."""
        client = HumanClient("TestHuman", interface_config)

        assert client.name == "TestHuman"
        assert isinstance(client.interface, CLIInterface)
        assert client.is_active == True
        assert client.conversation_history == []
        assert client.stats['responses_given'] == 0

    def test_human_client_web_mode(self):
        """Test human client with web interface."""
        config = {'mode': 'web'}
        client = HumanClient("WebHuman", config)

        assert isinstance(client.interface, WebInterface)

    def test_human_client_unsupported_mode(self):
        """Test human client with unsupported interface mode."""
        config = {'mode': 'unsupported'}

        with pytest.raises(ValueError, match="Unsupported interface mode"):
            HumanClient("TestHuman", config)

    @pytest.mark.asyncio
    async def test_get_response_success(self, human_client, sample_messages):
        """Test successful response retrieval."""
        # Mock the interface get_input method
        human_client.interface.get_input = AsyncMock(return_value="My response")
        human_client.interface.show_notification = AsyncMock()
        human_client.interface.display_message = AsyncMock()

        response = await human_client.get_response("Test topic", sample_messages)

        assert response == "My response"
        assert human_client.stats['responses_given'] == 1

    @pytest.mark.asyncio
    async def test_get_response_timeout(self, human_client, sample_messages):
        """Test response timeout."""
        # Mock timeout scenario
        human_client.interface.get_input = AsyncMock(return_value="")
        human_client.interface.show_notification = AsyncMock()
        human_client.interface.display_message = AsyncMock()

        response = await human_client.get_response("Test topic", sample_messages)

        assert response == ""
        assert human_client.stats['timeouts'] == 1

    @pytest.mark.asyncio
    async def test_get_response_inactive(self, human_client, sample_messages):
        """Test response when client is inactive."""
        human_client.is_active = False

        response = await human_client.get_response("Test topic", sample_messages)

        assert response == ""

    def test_validate_response(self, human_client):
        """Test response validation."""
        # Normal response
        response = human_client._validate_response("This is a good response")
        assert response == "This is a good response"

        # Very long response
        long_response = "x" * 600
        response = human_client._validate_response(long_response)
        assert len(response) <= 503  # 500 + "..."
        assert response.endswith("...")

        # Very short response
        short_response = human_client._validate_response("Yes")
        assert "[Note: Very short response]" in short_response

    @pytest.mark.asyncio
    async def test_receive_message(self, human_client):
        """Test receiving a message."""
        message = Message("Alice", "Hello human", 1640995200.0, 1)
        human_client.interface.display_message = AsyncMock()

        await human_client.receive_message(message)

        # Should be added to conversation history
        assert len(human_client.conversation_history) == 1
        assert human_client.conversation_history[0] == message

        # Should display the message
        human_client.interface.display_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_receive_own_message(self, human_client):
        """Test receiving own message (should be ignored)."""
        message = Message("TestHuman", "My own message", 1640995200.0, 1)
        human_client.interface.display_message = AsyncMock()

        await human_client.receive_message(message)

        # Should not be added to history or displayed
        assert len(human_client.conversation_history) == 0
        human_client.interface.display_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_conversation_history_limit(self, human_client):
        """Test conversation history length limit."""
        human_client.interface.display_message = AsyncMock()

        # Add many messages
        for i in range(60):
            message = Message(f"User{i}", f"Message {i}", 1640995200.0 + i, i)
            await human_client.receive_message(message)

        # Should be limited to 30 (as per implementation)
        assert len(human_client.conversation_history) == 30

    @pytest.mark.asyncio
    async def test_handle_voting_success(self, human_client):
        """Test successful voting."""
        candidates = ["Alice", "Bob", "Charlie"]

        # Mock interface methods
        human_client.interface.show_notification = AsyncMock()
        human_client.interface.get_input = AsyncMock(side_effect=["2", "Good arguments"])

        result = await human_client.handle_voting(candidates, 60)

        assert result['voted'] == True
        assert result['candidate'] == "Bob"  # Index 2-1 = 1 -> "Bob"
        assert result['justification'] == "Good arguments"

    @pytest.mark.asyncio
    async def test_handle_voting_timeout(self, human_client):
        """Test voting timeout."""
        candidates = ["Alice", "Bob"]

        human_client.interface.show_notification = AsyncMock()
        human_client.interface.get_input = AsyncMock(return_value="")  # Timeout

        result = await human_client.handle_voting(candidates, 30)

        assert result['voted'] == False
        assert result['reason'] == 'timeout'

    @pytest.mark.asyncio
    async def test_handle_voting_invalid_choice(self, human_client):
        """Test voting with invalid choice."""
        candidates = ["Alice", "Bob"]

        human_client.interface.show_notification = AsyncMock()
        human_client.interface.get_input = AsyncMock(return_value="5")  # Out of range

        result = await human_client.handle_voting(candidates, 30)

        assert result['voted'] == False
        assert result['reason'] == 'invalid_choice'

    @pytest.mark.asyncio
    async def test_handle_voting_invalid_format(self, human_client):
        """Test voting with invalid input format."""
        candidates = ["Alice", "Bob"]

        human_client.interface.show_notification = AsyncMock()
        human_client.interface.get_input = AsyncMock(return_value="not_a_number")

        result = await human_client.handle_voting(candidates, 30)

        assert result['voted'] == False
        assert result['reason'] == 'invalid_format'

    def test_update_stats_success(self, human_client):
        """Test updating statistics on successful response."""
        human_client._update_stats(2.5, success=True)

        assert human_client.stats['responses_given'] == 1
        assert human_client.stats['average_response_time'] == 2.5
        assert human_client.stats['total_response_time'] == 2.5

    def test_update_stats_timeout(self, human_client):
        """Test updating statistics on timeout."""
        human_client._update_stats(5.0, success=False)

        assert human_client.stats['timeouts'] == 1
        assert human_client.stats['responses_given'] == 0

    def test_get_stats(self, human_client):
        """Test getting human client statistics."""
        # Add some test data
        human_client.stats['responses_given'] = 3
        human_client.stats['timeouts'] = 1
        human_client.stats['total_response_time'] = 15.0
        human_client._update_stats(0, success=True)  # Recalculate average

        stats = human_client.get_stats()

        assert stats['name'] == "TestHuman"
        assert stats['interface_mode'] == "cli"
        assert stats['responses_given'] == 3
        assert stats['timeouts'] == 1
        assert stats['participation_rate'] == 0.75  # 3/(3+1)
        assert 'average_response_time' in stats

    @pytest.mark.asyncio
    async def test_set_active(self, human_client):
        """Test setting client active/inactive status."""
        human_client.interface.show_notification = AsyncMock()

        # Set inactive
        await human_client.set_active(False)
        assert human_client.is_active == False

        # Set active
        await human_client.set_active(True)
        assert human_client.is_active == True

        # Should have called show_notification twice
        assert human_client.interface.show_notification.call_count == 2

    @pytest.mark.asyncio
    async def test_show_help(self, human_client):
        """Test showing help information."""
        human_client.interface.show_notification = AsyncMock()

        await human_client.show_help()

        human_client.interface.show_notification.assert_called_once()
        args = human_client.interface.show_notification.call_args[0]
        assert "AI Jubilee Debate Help" in args[0]
        assert "COMMANDS:" in args[0]

    def test_str_representation(self, human_client):
        """Test string representation of human client."""
        string_repr = str(human_client)

        assert "TestHuman" in string_repr
        assert "cli" in string_repr

    def test_repr_representation(self, human_client):
        """Test detailed string representation of human client."""
        repr_str = repr(human_client)

        assert "HumanClient" in repr_str
        assert "name='TestHuman'" in repr_str
        assert "mode='cli'" in repr_str
        assert "active=True" in repr_str


@pytest.mark.asyncio
async def test_show_context_integration(human_client, sample_messages):
    """Test showing context to human before response."""
    human_client.interface.show_notification = AsyncMock()
    human_client.interface.display_message = AsyncMock()
    human_client.interface.get_input = AsyncMock(return_value="Test response")

    await human_client.get_response("Test topic", sample_messages)

    # Should show context notification
    notification_calls = human_client.interface.show_notification.call_args_list
    assert any("Recent messages" in str(call) for call in notification_calls)

    # Should display recent messages
    assert human_client.interface.display_message.call_count >= 1


@pytest.mark.asyncio
async def test_human_response_validation_edge_cases(human_client):
    """Test edge cases in response validation."""
    # Empty response
    result = human_client._validate_response("")
    assert result == ""

    # Whitespace only
    result = human_client._validate_response("   \n\t   ")
    assert result == ""

    # Response with just newlines
    result = human_client._validate_response("\n\n\n")
    assert result == ""

    # Very short meaningful response
    result = human_client._validate_response("No.")
    assert "[Note: Very short response]" in result


@pytest.mark.asyncio
async def test_human_client_error_resilience(human_client, sample_messages):
    """Test human client resilience to interface errors."""
    # Mock interface to raise errors
    human_client.interface.display_message = AsyncMock(side_effect=Exception("Interface error"))
    human_client.interface.show_notification = AsyncMock()
    human_client.interface.get_input = AsyncMock(return_value="Test response")

    # Should not crash despite interface errors
    response = await human_client.get_response("Test topic", sample_messages)
    assert response == "Test response"


@pytest.mark.asyncio
async def test_human_client_concurrent_operations(human_client):
    """Test concurrent operations on human client."""
    human_client.interface.display_message = AsyncMock()

    # Simulate concurrent message receiving
    tasks = []
    for i in range(10):
        message = Message(f"User{i}", f"Message {i}", 1640995200.0 + i, i)
        tasks.append(human_client.receive_message(message))

    await asyncio.gather(*tasks)

    # All messages should be processed
    assert len(human_client.conversation_history) == 10


def test_human_client_stats_calculation(human_client):
    """Test statistics calculation accuracy."""
    # Simulate various response scenarios
    human_client._update_stats(2.0, success=True)
    human_client._update_stats(3.0, success=True)
    human_client._update_stats(1.5, success=False)  # Timeout
    human_client._update_stats(2.5, success=True)

    stats = human_client.get_stats()

    assert stats['responses_given'] == 3
    assert stats['timeouts'] == 1
    assert stats['participation_rate'] == 0.75  # 3/(3+1)
    assert abs(stats['average_response_time'] - 2.5) < 0.1  # (2.0+3.0+2.5)/3


@pytest.mark.asyncio
async def test_voting_with_web_interface():
    """Test voting behavior with web interface."""
    config = {'mode': 'web'}
    client = HumanClient("WebUser", config)
    candidates = ["Alice", "Bob"]

    # Web interface should handle justification differently
    client.interface.show_notification = AsyncMock()
    client.interface.get_input = AsyncMock(return_value="1")

    result = await client.handle_voting(candidates, 60)

    assert result['voted'] == True
    assert result['candidate'] == "Alice"
    assert result['justification'] == ""  # No justification prompt for web


@pytest.mark.asyncio
async def test_human_client_lifecycle():
    """Test complete human client lifecycle."""
    config = {'mode': 'cli', 'enable_rich_formatting': False}
    client = HumanClient("LifecycleTest", config)

    # Initial state
    assert client.is_active == True
    assert len(client.conversation_history) == 0

    # Mock interface for testing
    client.interface.display_message = AsyncMock()
    client.interface.show_notification = AsyncMock()
    client.interface.get_input = AsyncMock(return_value="Test response")

    # Receive some messages
    for i in range(3):
        message = Message(f"User{i}", f"Message {i}", 1640995200.0 + i, i)
        await client.receive_message(message)

    assert len(client.conversation_history) == 3

    # Participate in debate
    response = await client.get_response("Test topic", [])
    assert response == "Test response"
    assert client.stats['responses_given'] == 1

    # Deactivate
    await client.set_active(False)
    assert client.is_active == False

    # Should not respond when inactive
    response = await client.get_response("Another topic", [])
    assert response == ""