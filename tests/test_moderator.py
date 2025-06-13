"""
Tests for the Moderator class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.moderator import Moderator, DebatePhase, DebateState
from app.chat_log import ChatLog
from app.voting import VotingSystem
from app.bot_client import BotClient
from app.human_client import HumanClient


@pytest.fixture
def chat_log():
    """Create a test chat log."""
    return ChatLog()


@pytest.fixture
def voting_system():
    """Create a test voting system."""
    config = {'enabled': True, 'voting_duration': 60}
    return VotingSystem(config)


@pytest.fixture
def mock_participants():
    """Create mock participants."""
    bot = Mock(spec=BotClient)
    bot.name = "TestBot"
    bot.get_response = AsyncMock(return_value="Test response")
    bot.receive_message = AsyncMock()

    human = Mock(spec=HumanClient)
    human.name = "TestHuman"
    human.get_response = AsyncMock(return_value="Human response")
    human.receive_message = AsyncMock()

    return [bot, human]


@pytest.fixture
def moderator(chat_log, voting_system, mock_participants):
    """Create a test moderator."""
    config = {
        'opening_statement_time': 30,
        'discussion_time': 60,
        'closing_statement_time': 30,
        'response_time': 20,
        'max_response_time': 60,
        'warning_time': 45
    }

    return Moderator(
        topic="Test topic",
        participants=mock_participants,
        chat_log=chat_log,
        voting_system=voting_system,
        config=config
    )


class TestModerator:
    """Test suite for Moderator class."""

    def test_moderator_initialization(self, moderator):
        """Test moderator initialization."""
        assert moderator.topic == "Test topic"
        assert len(moderator.participants) == 2
        assert moderator.state.phase == DebatePhase.INTRODUCTION
        assert "TestBot" in moderator.participants
        assert "TestHuman" in moderator.participants

    @pytest.mark.asyncio
    async def test_introduction_phase(self, moderator, chat_log):
        """Test introduction phase."""
        await moderator._introduction_phase()

        assert moderator.state.phase == DebatePhase.INTRODUCTION

        # Check that introduction message was logged
        messages = chat_log.get_messages()
        assert any("Welcome to AI Jubilee Debate" in msg.content for msg in messages)

    @pytest.mark.asyncio
    async def test_opening_statements_phase(self, moderator, mock_participants):
        """Test opening statements phase."""
        await moderator._opening_statements_phase()

        assert moderator.state.phase == DebatePhase.OPENING_STATEMENTS

        # Verify each participant was asked for response
        for participant in mock_participants:
            participant.get_response.assert_called()

    @pytest.mark.asyncio
    async def test_give_turn_success(self, moderator, mock_participants):
        """Test successful turn giving."""
        participant = mock_participants[0]
        participant.get_response.return_value = "Test response"

        await moderator._give_turn(participant.name, 30, "test")

        participant.get_response.assert_called_once()
        assert moderator.state.current_speaker is None  # Reset after turn

    @pytest.mark.asyncio
    async def test_give_turn_timeout(self, moderator, mock_participants):
        """Test turn timeout handling."""
        participant = mock_participants[0]

        # Simulate timeout by making get_response take too long
        async def slow_response(*args):
            await asyncio.sleep(2)
            return "Too late"

        participant.get_response = slow_response

        # Use very short timeout for testing
        await moderator._give_turn(participant.name, 0.1, "test")

        # Should have issued a warning
        assert moderator.state.warnings_issued.get(participant.name, 0) >= 1

    @pytest.mark.asyncio
    async def test_voting_phase_enabled(self, moderator):
        """Test voting phase when voting is enabled."""
        moderator.voting_system.enabled = True

        with patch.object(moderator.voting_system, 'start_voting') as mock_start:
            with patch.object(moderator.voting_system, 'end_voting') as mock_end:
                mock_end.return_value = {
                    'winner': 'TestBot',
                    'vote_counts': {'TestBot': 2, 'TestHuman': 1}
                }

                results = await moderator._voting_phase()

                mock_start.assert_called_once()
                mock_end.assert_called_once()
                assert results['winner'] == 'TestBot'

    @pytest.mark.asyncio
    async def test_voting_phase_disabled(self, moderator):
        """Test voting phase when voting is disabled."""
        moderator.voting_system.enabled = False

        results = await moderator._voting_phase()

        assert results == {}

    @pytest.mark.asyncio
    async def test_broadcast_message(self, moderator, mock_participants, chat_log):
        """Test message broadcasting."""
        await moderator._broadcast_message("Test message", "moderator")

        # Check message was logged
        messages = chat_log.get_messages()
        assert any(msg.content == "Test message" for msg in messages)

        # Check all participants received message
        for participant in mock_participants:
            participant.receive_message.assert_called()

    @pytest.mark.asyncio
    async def test_handle_timeout_warnings(self, moderator):
        """Test timeout warning system."""
        participant_name = "TestBot"

        # First timeout
        await moderator._handle_timeout(participant_name)
        assert moderator.state.warnings_issued[participant_name] == 1

        # Second timeout
        await moderator._handle_timeout(participant_name)
        assert moderator.state.warnings_issued[participant_name] == 2

        # Third timeout (should trigger mute)
        await moderator._handle_timeout(participant_name)
        assert moderator.state.warnings_issued[participant_name] == 3

    def test_get_state(self, moderator):
        """Test state retrieval."""
        state = moderator.get_state()

        assert isinstance(state, DebateState)
        assert state.phase == DebatePhase.INTRODUCTION
        assert state.current_speaker is None

    @pytest.mark.asyncio
    async def test_full_debate_flow(self, moderator, mock_participants):
        """Test complete debate flow."""
        # Mock voting system methods
        moderator.voting_system.start_voting = AsyncMock()
        moderator.voting_system.end_voting = AsyncMock(return_value={
            'winner': 'TestBot',
            'vote_counts': {'TestBot': 1, 'TestHuman': 0}
        })

        # Run complete debate with short timeouts for testing
        moderator.phase_times[DebatePhase.DISCUSSION] = 1  # 1 second

        results = await moderator.run_debate()

        # Verify all phases completed
        assert moderator.state.phase == DebatePhase.FINISHED
        assert 'winner' in results

        # Verify participants were called
        for participant in mock_participants:
            assert participant.get_response.call_count > 0


class TestDebateState:
    """Test suite for DebateState dataclass."""

    def test_debate_state_initialization(self):
        """Test DebateState initialization."""
        state = DebateState(DebatePhase.DISCUSSION)

        assert state.phase == DebatePhase.DISCUSSION
        assert state.current_speaker is None
        assert state.time_remaining == 0
        assert state.turn_order == []
        assert state.warnings_issued == {}

    def test_debate_state_with_values(self):
        """Test DebateState with custom values."""
        turn_order = ["Bot1", "Human1", "Bot2"]
        warnings = {"Bot1": 1}

        state = DebateState(
            phase=DebatePhase.VOTING,
            current_speaker="Human1",
            time_remaining=120,
            turn_order=turn_order,
            warnings_issued=warnings
        )

        assert state.phase == DebatePhase.VOTING
        assert state.current_speaker == "Human1"
        assert state.time_remaining == 120
        assert state.turn_order == turn_order
        assert state.warnings_issued == warnings


@pytest.mark.asyncio
async def test_moderator_error_handling(moderator, mock_participants):
    """Test moderator error handling."""
    # Make participant raise an error
    mock_participants[0].get_response.side_effect = Exception("Test error")

    # Should not crash the debate
    await moderator._give_turn(mock_participants[0].name, 30, "test")

    # Moderator should continue functioning
    assert moderator.state.phase == DebatePhase.INTRODUCTION


@pytest.mark.asyncio
async def test_moderator_message_validation(moderator):
    """Test message content validation."""
    long_message = "x" * 1000  # Very long message

    await moderator._process_response("TestBot", long_message)

    # Should have been truncated
    messages = moderator.chat_log.get_messages()
    last_message = messages[-1]
    assert len(last_message.content) <= 503  # 500 + "..."