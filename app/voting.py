"""
Voting system for debate evaluation and winner determination.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class Vote:
    """Represents a single vote."""
    voter_id: str
    candidate: str
    justification: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    anonymous: bool = False


@dataclass
class VotingResults:
    """Results of a voting session."""
    winner: Optional[str]
    vote_counts: Dict[str, int]
    total_votes: int
    votes_by_voter: Dict[str, Vote]
    voting_duration: float
    participation_rate: float


class VotingSystem:
    """
    Manages voting process, vote collection, and result calculation.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.voting_duration = config.get('voting_duration', 300)
        self.allow_participant_voting = config.get('allow_participant_voting', True)
        self.require_justification = config.get('require_justification', True)
        self.anonymous_votes = config.get('anonymous_votes', False)

        # Voting state
        self.is_active = False
        self.candidates: List[str] = []
        self.eligible_voters: List[str] = []
        self.votes: Dict[str, Vote] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Vote validation
        self.vote_history: List[Dict[str, Any]] = []

    async def start_voting(self, candidates: List[str], duration: Optional[int] = None) -> None:
        """
        Start a voting session.

        Args:
            candidates: List of debate participants to vote for
            duration: Voting duration in seconds (uses config default if None)
        """
        if not self.enabled:
            raise ValueError("Voting system is disabled")

        if self.is_active:
            raise ValueError("Voting session already active")

        self.candidates = candidates.copy()
        self.eligible_voters = candidates.copy() if self.allow_participant_voting else []
        self.votes = {}
        self.start_time = time.time()
        self.end_time = self.start_time + (duration or self.voting_duration)
        self.is_active = True

        print(f"🗳️ Voting started for {len(candidates)} candidates")
        print(f"⏰ Voting closes in {duration or self.voting_duration} seconds")

    async def cast_vote(self, voter_id: str, candidate: str,
                        justification: Optional[str] = None) -> bool:
        """
        Cast a vote for a candidate.

        Args:
            voter_id: ID of the voter
            candidate: Candidate being voted for
            justification: Optional reasoning for the vote

        Returns:
            True if vote was successfully cast, False otherwise
        """
        if not self.is_active:
            raise ValueError("No active voting session")

        if time.time() > self.end_time:
            raise ValueError("Voting period has ended")

        # Validate voter eligibility
        if not self._is_eligible_voter(voter_id):
            raise ValueError(f"Voter {voter_id} is not eligible to vote")

        # Validate candidate
        if candidate not in self.candidates:
            raise ValueError(f"Invalid candidate: {candidate}")

        # Check for self-voting
        if voter_id == candidate and not self.allow_participant_voting:
            raise ValueError("Self-voting is not allowed")

        # Validate justification requirement
        if self.require_justification and not justification:
            raise ValueError("Vote justification is required")

        # Record the vote (overwrites previous vote from same voter)
        vote = Vote(
            voter_id=voter_id,
            candidate=candidate,
            justification=justification,
            anonymous=self.anonymous_votes
        )

        self.votes[voter_id] = vote

        print(f"✅ Vote recorded: {voter_id} -> {candidate}")
        return True

    async def end_voting(self) -> VotingResults:
        """
        End the voting session and calculate results.

        Returns:
            VotingResults object with winner and vote breakdown
        """
        if not self.is_active:
            raise ValueError("No active voting session")

        self.is_active = False
        actual_end_time = time.time()

        # Calculate vote counts
        vote_counts = Counter(vote.candidate for vote in self.votes.values())
        total_votes = len(self.votes)

        # Determine winner
        winner = None
        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [candidate for candidate, count in vote_counts.items()
                       if count == max_votes]

            if len(winners) == 1:
                winner = winners[0]
            else:
                # Handle tie - could implement tiebreaker logic here
                winner = f"TIE: {', '.join(winners)}"

        # Calculate participation rate
        participation_rate = (total_votes / len(self.eligible_voters)
                              if self.eligible_voters else 0)

        # Create results
        results = VotingResults(
            winner=winner,
            vote_counts=dict(vote_counts),
            total_votes=total_votes,
            votes_by_voter=self.votes.copy(),
            voting_duration=actual_end_time - self.start_time,
            participation_rate=participation_rate
        )

        # Store in history
        self.vote_history.append({
            'timestamp': actual_end_time,
            'candidates': self.candidates.copy(),
            'results': results
        })

        print(f"🏆 Voting ended. Winner: {winner}")
        print(f"📊 Total votes: {total_votes}")
        print(f"📈 Participation: {participation_rate:.1%}")

        return results

    def _is_eligible_voter(self, voter_id: str) -> bool:
        """Check if a voter is eligible to vote."""
        if not self.eligible_voters:
            return True  # Open voting
        return voter_id in self.eligible_voters

    def add_eligible_voter(self, voter_id: str) -> None:
        """Add a voter to the eligible voters list."""
        if voter_id not in self.eligible_voters:
            self.eligible_voters.append(voter_id)

    def remove_eligible_voter(self, voter_id: str) -> None:
        """Remove a voter from the eligible voters list."""
        if voter_id in self.eligible_voters:
            self.eligible_voters.remove(voter_id)

    def get_vote_summary(self) -> Dict[str, Any]:
        """Get current voting summary without ending the session."""
        if not self.is_active:
            return {}

        vote_counts = Counter(vote.candidate for vote in self.votes.values())
        time_remaining = max(0, self.end_time - time.time())

        return {
            'candidates': self.candidates,
            'vote_counts': dict(vote_counts),
            'total_votes': len(self.votes),
            'time_remaining': time_remaining,
            'is_active': self.is_active
        }

    def get_voter_history(self, voter_id: str) -> List[Vote]:
        """Get voting history for a specific voter."""
        history = []
        for session in self.vote_history:
            votes = session.get('results', {}).votes_by_voter
            if voter_id in votes:
                history.append(votes[voter_id])
        return history

    def get_candidate_performance(self, candidate: str) -> Dict[str, Any]:
        """Get performance statistics for a candidate across all sessions."""
        wins = 0
        total_votes = 0
        participations = 0

        for session in self.vote_history:
            results = session.get('results', {})
            if candidate in session.get('candidates', []):
                participations += 1
                if results.winner == candidate:
                    wins += 1
                total_votes += results.vote_counts.get(candidate, 0)

        return {
            'candidate': candidate,
            'wins': wins,
            'total_votes': total_votes,
            'participations': participations,
            'win_rate': wins / participations if participations > 0 else 0,
            'avg_votes': total_votes / participations if participations > 0 else 0
        }

    async def export_results(self, format_type: str = 'json') -> str:
        """
        Export voting results in specified format.

        Args:
            format_type: Export format ('json', 'csv', 'txt')

        Returns:
            Formatted results string
        """
        if not self.vote_history:
            return "No voting history available"

        if format_type == 'json':
            import json
            return json.dumps(self.vote_history, indent=2, default=str)

        elif format_type == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(['Session', 'Timestamp', 'Candidate', 'Votes', 'Winner'])

            # Data
            for i, session in enumerate(self.vote_history):
                results = session.get('results', {})
                timestamp = session.get('timestamp', '')

                for candidate, votes in results.vote_counts.items():
                    writer.writerow([
                        i + 1,
                        timestamp,
                        candidate,
                        votes,
                        results.winner == candidate
                    ])

            return output.getvalue()

        elif format_type == 'txt':
            output = []
            output.append("=== VOTING HISTORY REPORT ===\n")

            for i, session in enumerate(self.vote_history):
                results = session.get('results', {})
                output.append(f"Session {i + 1}:")
                output.append(f"  Winner: {results.winner}")
                output.append(f"  Total Votes: {results.total_votes}")
                output.append(f"  Vote Breakdown:")

                for candidate, votes in sorted(results.vote_counts.items(),
                                               key=lambda x: x[1], reverse=True):
                    output.append(f"    {candidate}: {votes}")
                output.append("")

            return "\n".join(output)

        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def reset(self) -> None:
        """Reset the voting system to initial state."""
        self.is_active = False
        self.candidates = []
        self.eligible_voters = []
        self.votes = {}
        self.start_time = None
        self.end_time = None

    @property
    def status(self) -> Dict[str, Any]:
        """Get current status of the voting system."""
        return {
            'enabled': self.enabled,
            'is_active': self.is_active,
            'candidates': self.candidates,
            'eligible_voters': len(self.eligible_voters),
            'votes_cast': len(self.votes),
            'time_remaining': (self.end_time - time.time()
                               if self.is_active and self.end_time else 0),
            'sessions_completed': len(self.vote_history)
        }