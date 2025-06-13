"""
Tests for the VotingSystem class.
"""

import pytest
import asyncio
import time
from app.voting import VotingSystem, Vote, VotingResults


@pytest.fixture
def voting_config():
    """Create test voting configuration."""
    return {
        'enabled': True,
        'voting_duration': 60,
        'allow_participant_voting': True,
        'require_justification': False,
        'anonymous_votes': False
    }


@pytest.fixture
def voting_system(voting_config):
    """Create test voting system."""
    return VotingSystem(voting_config)


@pytest.fixture
def active_voting_system(voting_system):
    """Create and start a voting session."""
    asyncio.create_task(voting_system.start_voting(['Alice', 'Bob', 'Charlie'], 30))
    return voting_system


class TestVotingSystem:
    """Test suite for VotingSystem class."""

    def test_voting_system_initialization(self, voting_config):
        """Test voting system initialization."""
        vs = VotingSystem(voting_config)

        assert vs.enabled == True
        assert vs.voting_duration == 60
        assert vs.allow_participant_voting == True
        assert vs.require_justification == False
        assert vs.anonymous_votes == False
        assert vs.is_active == False
        assert vs.candidates == []
        assert vs.votes == {}

    def test_disabled_voting_system(self):
        """Test disabled voting system."""
        config = {'enabled': False}
        vs = VotingSystem(config)

        assert vs.enabled == False

    @pytest.mark.asyncio
    async def test_start_voting_session(self, voting_system):
        """Test starting a voting session."""
        candidates = ['Alice', 'Bob', 'Charlie']

        await voting_system.start_voting(candidates, 30)

        assert voting_system.is_active == True
        assert voting_system.candidates == candidates
        assert voting_system.eligible_voters == candidates  # allow_participant_voting=True
        assert voting_system.start_time is not None
        assert voting_system.end_time is not None

    @pytest.mark.asyncio
    async def test_start_voting_disabled_system(self):
        """Test starting voting on disabled system."""
        config = {'enabled': False}
        vs = VotingSystem(config)

        with pytest.raises(ValueError, match="Voting system is disabled"):
            await vs.start_voting(['Alice', 'Bob'])

    @pytest.mark.asyncio
    async def test_start_voting_already_active(self, voting_system):
        """Test starting voting when already active."""
        await voting_system.start_voting(['Alice', 'Bob'])

        with pytest.raises(ValueError, match="Voting session already active"):
            await voting_system.start_voting(['Charlie', 'Dave'])

    @pytest.mark.asyncio
    async def test_cast_valid_vote(self, voting_system):
        """Test casting a valid vote."""
        await voting_system.start_voting(['Alice', 'Bob', 'Charlie'])

        result = await voting_system.cast_vote('voter1', 'Alice', 'Great arguments')

        assert result == True
        assert 'voter1' in voting_system.votes
        assert voting_system.votes['voter1'].candidate == 'Alice'
        assert voting_system.votes['voter1'].justification == 'Great arguments'

    @pytest.mark.asyncio
    async def test_cast_vote_no_active_session(self, voting_system):
        """Test casting vote with no active session."""
        with pytest.raises(ValueError, match="No active voting session"):
            await voting_system.cast_vote('voter1', 'Alice')

    @pytest.mark.asyncio
    async def test_cast_vote_invalid_candidate(self, voting_system):
        """Test casting vote for invalid candidate."""
        await voting_system.start_voting(['Alice', 'Bob'])

        with pytest.raises(ValueError, match="Invalid candidate"):
            await voting_system.cast_vote('voter1', 'Charlie')

    @pytest.mark.asyncio
    async def test_cast_vote_requires_justification(self):
        """Test voting system that requires justification."""
        config = {
            'enabled': True,
            'require_justification': True,
            'allow_participant_voting': True
        }
        vs = VotingSystem(config)
        await vs.start_voting(['Alice', 'Bob'])

        # Vote without justification should fail
        with pytest.raises(ValueError, match="Vote justification is required"):
            await vs.cast_vote('voter1', 'Alice')

        # Vote with justification should succeed
        result = await vs.cast_vote('voter1', 'Alice', 'Good points')
        assert result == True

    @pytest.mark.asyncio
    async def test_cast_vote_overwrite(self, voting_system):
        """Test that new vote overwrites previous vote."""
        await voting_system.start_voting(['Alice', 'Bob'])

        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.cast_vote('voter1', 'Bob')  # Change vote

        assert voting_system.votes['voter1'].candidate == 'Bob'
        assert len(voting_system.votes) == 1  # Only one vote per voter

    @pytest.mark.asyncio
    async def test_self_voting_allowed(self, voting_system):
        """Test self-voting when allowed."""
        await voting_system.start_voting(['Alice', 'Bob'])

    @pytest.mark.asyncio
    async def test_self_voting_allowed(self, voting_system):
        """Test self-voting when allowed."""
        await voting_system.start_voting(['Alice', 'Bob'])

        # Should allow participant to vote for themselves
        result = await voting_system.cast_vote('Alice', 'Alice')
        assert result == True

    @pytest.mark.asyncio
    async def test_self_voting_disallowed(self):
        """Test self-voting when disallowed."""
        config = {
            'enabled': True,
            'allow_participant_voting': False
        }
        vs = VotingSystem(config)
        await vs.start_voting(['Alice', 'Bob'])

        with pytest.raises(ValueError, match="Self-voting is not allowed"):
            await vs.cast_vote('Alice', 'Alice')

    @pytest.mark.asyncio
    async def test_end_voting_session(self, voting_system):
        """Test ending a voting session."""
        await voting_system.start_voting(['Alice', 'Bob', 'Charlie'])

        # Cast some votes
        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.cast_vote('voter2', 'Alice')
        await voting_system.cast_vote('voter3', 'Bob')

        results = await voting_system.end_voting()

        assert isinstance(results, VotingResults)
        assert results.winner == 'Alice'  # Most votes
        assert results.vote_counts['Alice'] == 2
        assert results.vote_counts['Bob'] == 1
        assert results.total_votes == 3
        assert voting_system.is_active == False

    @pytest.mark.asyncio
    async def test_end_voting_tie(self, voting_system):
        """Test ending voting with a tie."""
        await voting_system.start_voting(['Alice', 'Bob'])

        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.cast_vote('voter2', 'Bob')

        results = await voting_system.end_voting()

        assert "TIE:" in results.winner
        assert "Alice" in results.winner
        assert "Bob" in results.winner

    @pytest.mark.asyncio
    async def test_end_voting_no_votes(self, voting_system):
        """Test ending voting with no votes cast."""
        await voting_system.start_voting(['Alice', 'Bob'])

        results = await voting_system.end_voting()

        assert results.winner is None
        assert results.total_votes == 0
        assert results.vote_counts == {}

    @pytest.mark.asyncio
    async def test_end_voting_not_active(self, voting_system):
        """Test ending voting when not active."""
        with pytest.raises(ValueError, match="No active voting session"):
            await voting_system.end_voting()

    def test_get_vote_summary(self, voting_system):
        """Test getting vote summary during active session."""
        # No active session
        summary = voting_system.get_vote_summary()
        assert summary == {}

        # With active session
        asyncio.create_task(voting_system.start_voting(['Alice', 'Bob'], 60))
        summary = voting_system.get_vote_summary()

        assert 'candidates' in summary
        assert 'vote_counts' in summary
        assert 'total_votes' in summary
        assert 'time_remaining' in summary
        assert 'is_active' in summary

    def test_add_remove_eligible_voters(self, voting_system):
        """Test adding and removing eligible voters."""
        voting_system.add_eligible_voter('voter1')
        assert 'voter1' in voting_system.eligible_voters

        voting_system.add_eligible_voter('voter2')
        assert len(voting_system.eligible_voters) == 2

        voting_system.remove_eligible_voter('voter1')
        assert 'voter1' not in voting_system.eligible_voters
        assert len(voting_system.eligible_voters) == 1

    def test_is_eligible_voter(self, voting_system):
        """Test voter eligibility checking."""
        # Empty eligible voters list means open voting
        assert voting_system._is_eligible_voter('anyone') == True

        # With specific eligible voters
        voting_system.add_eligible_voter('voter1')
        assert voting_system._is_eligible_voter('voter1') == True
        assert voting_system._is_eligible_voter('voter2') == False

    @pytest.mark.asyncio
    async def test_vote_history(self, voting_system):
        """Test vote history tracking."""
        # First session
        await voting_system.start_voting(['Alice', 'Bob'])
        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.end_voting()

        # Second session
        await voting_system.start_voting(['Charlie', 'Dave'])
        await voting_system.cast_vote('voter1', 'Charlie')
        await voting_system.end_voting()

        assert len(voting_system.vote_history) == 2

        # Test voter history
        voter_history = voting_system.get_voter_history('voter1')
        assert len(voter_history) == 2
        assert voter_history[0].candidate == 'Alice'
        assert voter_history[1].candidate == 'Charlie'

    def test_candidate_performance(self, voting_system):
        """Test candidate performance tracking."""
        # Add some mock history
        voting_system.vote_history = [
            {
                'candidates': ['Alice', 'Bob'],
                'results': VotingResults(
                    winner='Alice',
                    vote_counts={'Alice': 2, 'Bob': 1},
                    total_votes=3,
                    votes_by_voter={},
                    voting_duration=60,
                    participation_rate=1.0
                )
            },
            {
                'candidates': ['Alice', 'Charlie'],
                'results': VotingResults(
                    winner='Charlie',
                    vote_counts={'Alice': 1, 'Charlie': 2},
                    total_votes=3,
                    votes_by_voter={},
                    voting_duration=60,
                    participation_rate=1.0
                )
            }
        ]

        performance = voting_system.get_candidate_performance('Alice')

        assert performance['wins'] == 1
        assert performance['participations'] == 2
        assert performance['total_votes'] == 3
        assert performance['win_rate'] == 0.5
        assert performance['avg_votes'] == 1.5

    @pytest.mark.asyncio
    async def test_export_results_json(self, voting_system):
        """Test exporting results in JSON format."""
        # Create some history
        await voting_system.start_voting(['Alice', 'Bob'])
        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.end_voting()

        json_output = await voting_system.export_results('json')

        assert isinstance(json_output, str)
        assert 'Alice' in json_output
        assert 'vote_counts' in json_output

    @pytest.mark.asyncio
    async def test_export_results_csv(self, voting_system):
        """Test exporting results in CSV format."""
        await voting_system.start_voting(['Alice', 'Bob'])
        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.end_voting()

        csv_output = await voting_system.export_results('csv')

        assert isinstance(csv_output, str)
        assert 'Session,Timestamp,Candidate,Votes,Winner' in csv_output
        assert 'Alice' in csv_output

    @pytest.mark.asyncio
    async def test_export_results_txt(self, voting_system):
        """Test exporting results in TXT format."""
        await voting_system.start_voting(['Alice', 'Bob'])
        await voting_system.cast_vote('voter1', 'Alice')
        await voting_system.end_voting()

        txt_output = await voting_system.export_results('txt')

        assert isinstance(txt_output, str)
        assert 'VOTING HISTORY REPORT' in txt_output
        assert 'Alice' in txt_output

    @pytest.mark.asyncio
    async def test_export_unsupported_format(self, voting_system):
        """Test exporting with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            await voting_system.export_results('xml')

    def test_reset_voting_system(self, voting_system):
        """Test resetting the voting system."""
        # Set up some state
        voting_system.candidates = ['Alice', 'Bob']
        voting_system.votes = {'voter1': Vote('voter1', 'Alice')}
        voting_system.is_active = True

        voting_system.reset()

        assert voting_system.is_active == False
        assert voting_system.candidates == []
        assert voting_system.votes == {}
        assert voting_system.start_time is None
        assert voting_system.end_time is None

    def test_voting_system_status(self, voting_system):
        """Test voting system status property."""
        status = voting_system.status

        assert 'enabled' in status
        assert 'is_active' in status
        assert 'candidates' in status
        assert 'eligible_voters' in status
        assert 'votes_cast' in status
        assert 'time_remaining' in status
        assert 'sessions_completed' in status

    @pytest.mark.asyncio
    async def test_vote_after_time_expires(self, voting_system):
        """Test casting vote after voting time expires."""
        # Start voting with very short duration
        await voting_system.start_voting(['Alice', 'Bob'], 0.1)

        # Wait for voting to expire
        await asyncio.sleep(0.2)

        with pytest.raises(ValueError, match="Voting period has ended"):
            await voting_system.cast_vote('voter1', 'Alice')


class TestVote:
    """Test suite for Vote dataclass."""

    def test_vote_creation(self):
        """Test creating a vote."""
        vote = Vote('voter1', 'Alice', 'Great arguments')

        assert vote.voter_id == 'voter1'
        assert vote.candidate == 'Alice'
        assert vote.justification == 'Great arguments'
        assert vote.anonymous == False
        assert isinstance(vote.timestamp, float)

    def test_vote_anonymous(self):
        """Test creating anonymous vote."""
        vote = Vote('voter1', 'Alice', anonymous=True)

        assert vote.anonymous == True

    def test_vote_no_justification(self):
        """Test vote without justification."""
        vote = Vote('voter1', 'Alice')

        assert vote.justification is None


class TestVotingResults:
    """Test suite for VotingResults dataclass."""

    def test_voting_results_creation(self):
        """Test creating voting results."""
        vote_counts = {'Alice': 2, 'Bob': 1}
        votes_by_voter = {
            'voter1': Vote('voter1', 'Alice'),
            'voter2': Vote('voter2', 'Alice'),
            'voter3': Vote('voter3', 'Bob')
        }

        results = VotingResults(
            winner='Alice',
            vote_counts=vote_counts,
            total_votes=3,
            votes_by_voter=votes_by_voter,
            voting_duration=60.0,
            participation_rate=1.0
        )

        assert results.winner == 'Alice'
        assert results.vote_counts == vote_counts
        assert results.total_votes == 3
        assert len(results.votes_by_voter) == 3
        assert results.voting_duration == 60.0
        assert results.participation_rate == 1.0