"""
Moderator class for managing debate flow, rules, and coordination.
Now acts as an AI-powered facilitator using the same system as other bots.
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from .chat_log import ChatLog, Message
from .voting import VotingSystem
from .utils import format_time_remaining
from .bot_client import BotClient
from app.bot_client import BotConfig


class DebatePhase(Enum):
    INTRODUCTION = "introduction"
    OPENING_STATEMENTS = "opening_statements"
    DISCUSSION = "discussion"
    CLOSING_STATEMENTS = "closing_statements"
    VOTING = "voting"
    RESULTS = "results"
    FINISHED = "finished"


@dataclass
class DebateState:
    phase: DebatePhase
    current_speaker: Optional[str] = None
    time_remaining: int = 0
    turn_order: List[str] = None
    warnings_issued: Dict[str, int] = None

    def __post_init__(self):
        if self.turn_order is None:
            self.turn_order = []
        if self.warnings_issued is None:
            self.warnings_issued = {}


class Moderator:
    """
    AI-powered moderator that manages debate flow and provides intelligent facilitation.
    Works just like other bots but with moderator-specific prompts.
    """

    def __init__(self, topic: str, participants: List, chat_log: ChatLog,
                 voting_system: VotingSystem, config: Dict[str, Any]):
        self.topic = topic
        self.participants = {p.name: p for p in participants}
        self.chat_log = chat_log
        self.voting_system = voting_system
        self.config = config

        # Initialize moderator as a bot client
        moderator_config = config.get('moderator', {})

        print(config)
        self.moderator_bot = BotClient(
            name=moderator_config.get('name', 'Moderator'),
            model=moderator_config.get('model', 'gpt-3.5-turbo'),
            provider=moderator_config.get('provider', 'openai'),
            personality=moderator_config.get('personality', 'Professional debate facilitator'),
            stance=moderator_config.get('stance', 'neutral'),
            api_key=config['api_keys'].get(moderator_config.get('provider', 'openai'))
        )

        self.state = DebateState(
            phase=DebatePhase.INTRODUCTION,
            turn_order=list(self.participants.keys())
        )

        self.phase_times = {
            DebatePhase.OPENING_STATEMENTS: config.get('opening_statement_time', 120),
            DebatePhase.DISCUSSION: config.get('time_limit_minutes', 30) * 60,
            DebatePhase.CLOSING_STATEMENTS: config.get('closing_statement_time', 90),
            DebatePhase.VOTING: config.get('voting_duration', 300)
        }

        self.max_response_time = config.get('max_response_time', 120)
        self.warning_time = config.get('warning_time', 90)

        # Autonomous mode settings
        self.autonomous_mode = config.get('mode', 'autonomous') == 'autonomous'
        self.autonomous_tasks: List[asyncio.Task] = []
        self.phase_task: Optional[asyncio.Task] = None

        # Facilitation settings
        self.silence_timeout = config.get('silence_timeout', 60)
        self.last_activity_time = time.time()
        self.last_moderator_prompt = 0

    async def run_debate(self) -> Dict[str, Any]:
        """Run the complete debate session with autonomous support."""
        results = {}

        try:
            await self._introduction_phase()
            await self._opening_statements_phase()

            if self.autonomous_mode:
                await self._autonomous_discussion_phase()
            else:
                await self._traditional_discussion_phase()

            await self._closing_statements_phase()
            results = await self._voting_phase()
            await self._results_phase(results)

        except Exception as e:
            await self._broadcast_message(
                f"⚠️ Debate error: {e}. Ending session.",
                "moderator"
            )
            raise
        finally:
            if self.autonomous_mode:
                await self._cleanup_autonomous_tasks()
            self.state.phase = DebatePhase.FINISHED

        return results

    async def _autonomous_discussion_phase(self):
        """Autonomous discussion where bots and humans self-manage participation."""
        self.state.phase = DebatePhase.DISCUSSION
        total_time = self.phase_times[DebatePhase.DISCUSSION]

        await self._broadcast_message(
            f"🚀 AUTONOMOUS DISCUSSION PHASE BEGIN! 🤖\n\n"
            f"🎯 How this works:\n"
            f"   • Bots are now monitoring the conversation continuously\n"
            f"   • They will decide when they feel compelled to respond\n"
            f"   • Humans can type messages at ANY TIME to join in\n"
            f"   • No turn-taking - completely organic conversation flow!\n"
            f"   • Everyone has access to full conversation history\n\n"
            f"⏰ Discussion time: {total_time // 60} minutes\n"
            f"🎭 Let the autonomous debate begin!",
            "moderator"
        )

        self.last_activity_time = time.time()
        start_time = time.time()

        # Start bot autonomous monitoring
        await self._start_bot_autonomous_monitoring()

        # Start human autonomous participation
        await self._start_human_autonomous_participation()

        # Start moderator autonomous monitoring
        await self._start_moderator_autonomous_monitoring()

        # Start phase management (facilitation only)
        self.phase_task = asyncio.create_task(
            self._facilitate_autonomous_discussion(start_time, total_time)
        )

        try:
            await self.phase_task
        except asyncio.CancelledError:
            pass

        await self._broadcast_message(
            "⏹️ Autonomous discussion phase complete! 🎉\n"
            "Moving to closing statements...",
            "moderator"
        )

    async def _start_bot_autonomous_monitoring(self):
        """Start autonomous monitoring for all bots."""
        for participant_name, participant in self.participants.items():
            if hasattr(participant, 'start_autonomous_monitoring'):  # It's a bot
                task = asyncio.create_task(
                    participant.start_autonomous_monitoring(self.chat_log, self.topic)
                )
                self.autonomous_tasks.append(task)

    async def _start_human_autonomous_participation(self):
        """Start autonomous participation for humans."""
        for participant_name, participant in self.participants.items():
            if hasattr(participant, 'autonomous_participation_loop'):  # It's a human
                task = asyncio.create_task(
                    participant.autonomous_participation_loop(self.chat_log)
                )
                self.autonomous_tasks.append(task)

    async def _start_moderator_autonomous_monitoring(self):
        """Start moderator autonomous monitoring just like other bots."""
        task = asyncio.create_task(
            self.moderator_bot.start_autonomous_monitoring(self.chat_log, self.topic)
        )
        self.autonomous_tasks.append(task)

    async def _facilitate_autonomous_discussion(self, start_time: float, total_time: int):
        """Facilitate the autonomous discussion without controlling it."""
        last_message_count = len(self.chat_log.messages)

        while time.time() - start_time < total_time:
            await asyncio.sleep(15)  # Check every 15 seconds

            current_time = time.time()
            elapsed = current_time - start_time
            remaining = total_time - elapsed

            # Check for new activity
            current_message_count = len(self.chat_log.messages)
            if current_message_count > last_message_count:
                self.last_activity_time = current_time
                last_message_count = current_message_count

            # Check for prolonged silence - provide simple prompts
            silence_duration = current_time - self.last_activity_time
            if silence_duration > self.silence_timeout:
                # Simple fallback prompts if moderator bot hasn't spoken
                if current_time - self.last_moderator_prompt > 45:
                    await self._provide_simple_prompt()
                    self.last_moderator_prompt = current_time

            # Provide time updates
            await self._provide_time_updates(remaining)

    async def _provide_simple_prompt(self):
        """Provide simple facilitation prompts as fallback."""
        simple_prompts = [
            "🎯 What are your thoughts on the discussion so far?",
            "💡 Any other perspectives to consider?",
            "🤔 Does anyone have questions about the points raised?",
            "⚖️ How do you weigh the different arguments presented?"
        ]

        prompt = random.choice(simple_prompts)
        await self._broadcast_message(prompt, "moderator")

    async def _provide_time_updates(self, remaining: float):
        """Provide time updates to participants."""
        if 299 < remaining <= 301:  # 5 minutes warning
            await self._broadcast_message(
                "⏰ 5 minutes remaining in autonomous discussion phase",
                "moderator"
            )
        elif 119 < remaining <= 121:  # 2 minutes warning
            await self._broadcast_message(
                "⏰ 2 minutes left! Perfect time for final thoughts on this topic",
                "moderator"
            )
        elif 59 < remaining <= 61:  # 1 minute warning
            await self._broadcast_message(
                "⏰ Final minute! Any last contributions to the discussion?",
                "moderator"
            )

    async def _cleanup_autonomous_tasks(self):
        """Clean up all autonomous tasks."""
        # Stop bot monitoring (including moderator bot)
        for participant in self.participants.values():
            if hasattr(participant, 'stop_monitoring'):
                await participant.stop_monitoring()

        # Stop moderator bot monitoring
        await self.moderator_bot.stop_monitoring()

        # Cancel all autonomous tasks
        for task in self.autonomous_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cancel phase management task
        if self.phase_task and not self.phase_task.done():
            self.phase_task.cancel()
            try:
                await self.phase_task
            except asyncio.CancelledError:
                pass

        self.autonomous_tasks.clear()

    # Traditional phases (structured)
    async def _introduction_phase(self):
        """Introduce the debate topic and participants."""
        self.state.phase = DebatePhase.INTRODUCTION

        participants_by_type = {"Bots": [], "Humans": []}
        for name, participant in self.participants.items():
            if isinstance(participant.config, BotConfig):  # Bot
                stance = participant.config.stance
                participants_by_type["Bots"].append(f"{name} ({stance})")
            else:  # Human or others
                participants_by_type["Humans"].append(name)

        intro_message = (
            f"🎭 Welcome to AI Jubilee Debate! 🎭\n\n"
            f"📝 Topic: {self.topic}\n\n"
            f"👥 Participants:\n"
            f"   🤖 AI Bots: {', '.join(participants_by_type['Bots'])}\n"
            f"   👤 Humans: {', '.join(participants_by_type['Humans'])}\n\n"
            f"⏱️ Total discussion time: {self.config.get('time_limit_minutes', 30)} minutes\n"
            f"🎯 Mode: {'Autonomous (organic flow)' if self.autonomous_mode else 'Sequential (turn-based)'}"
        )

        await self._broadcast_message(intro_message, "moderator")
        await asyncio.sleep(3)

    async def _opening_statements_phase(self):
        """Handle opening statements from each participant."""
        self.state.phase = DebatePhase.OPENING_STATEMENTS
        statement_time = self.phase_times[DebatePhase.OPENING_STATEMENTS]

        await self._broadcast_message(
            f"🎤 Opening Statements Phase\n"
            f"Each participant has {statement_time} seconds for their opening statement.\n"
            f"This phase uses structured turns regardless of debate mode.",
            "moderator"
        )

        for participant_name in self.state.turn_order:
            await self._give_structured_turn(participant_name, statement_time, "opening statement")

    async def _traditional_discussion_phase(self):
        """Traditional sequential discussion phase."""
        self.state.phase = DebatePhase.DISCUSSION
        total_time = self.phase_times[DebatePhase.DISCUSSION]

        await self._broadcast_message(
            f"💬 Sequential Discussion Phase\n"
            f"Participants take turns for {total_time // 60} minutes.",
            "moderator"
        )

        start_time = time.time()
        response_time = self.config.get('response_time', 60)

        while time.time() - start_time < total_time:
            for participant_name in self.state.turn_order:
                if time.time() - start_time >= total_time:
                    break

                remaining = total_time - (time.time() - start_time)
                if remaining < response_time:
                    response_time = int(remaining)

                await self._give_structured_turn(participant_name, response_time, "response")

        await self._broadcast_message("⏹️ Sequential discussion phase complete!", "moderator")

    async def _closing_statements_phase(self):
        """Handle closing statements."""
        self.state.phase = DebatePhase.CLOSING_STATEMENTS
        statement_time = self.phase_times[DebatePhase.CLOSING_STATEMENTS]

        await self._broadcast_message(
            f"🏁 Closing Statements Phase\n"
            f"Each participant has {statement_time} seconds for final remarks.\n"
            f"This phase uses structured turns regardless of debate mode.",
            "moderator"
        )

        # Reverse order for closing statements
        for participant_name in reversed(self.state.turn_order):
            await self._give_structured_turn(participant_name, statement_time, "closing statement")

    async def _give_structured_turn(self, participant_name: str, time_limit: int, turn_type: str):
        """Give structured speaking turn to a participant."""
        self.state.current_speaker = participant_name
        self.state.time_remaining = time_limit

        participant = self.participants[participant_name]

        await self._broadcast_message(
            f"🎤 {participant_name}'s turn for {turn_type} ({time_limit}s)",
            "moderator"
        )

        try:
            response_task = asyncio.create_task(
                participant.get_response(self.topic, self.chat_log.get_recent_messages())
            )

            # Start timer
            start_time = time.time()
            warning_sent = False

            while not response_task.done():
                elapsed = time.time() - start_time
                remaining = time_limit - elapsed

                if remaining <= 0:
                    response_task.cancel()
                    try:
                        await response_task
                    except asyncio.CancelledError:
                        pass
                    await self._handle_timeout(participant_name)
                    break

                if not warning_sent and remaining <= self.warning_time:
                    await self._send_warning(participant_name, remaining)
                    warning_sent = True

                await asyncio.sleep(0.5)

            # Process response if completed successfully
            if response_task.done() and not response_task.cancelled():
                try:
                    response = await response_task
                    if response:
                        await self._process_response(participant_name, response)
                except Exception as e:
                    await self._broadcast_message(
                        f"⚠️ Error getting response from {participant_name}: {e}",
                        "moderator"
                    )

        except Exception as e:
            await self._broadcast_message(
                f"⚠️ Error during {participant_name}'s turn: {e}",
                "moderator"
            )
        finally:
            self.state.current_speaker = None

    async def _voting_phase(self) -> Dict[str, Any]:
        """Conduct voting on debate performance."""
        self.state.phase = DebatePhase.VOTING

        if not self.voting_system.enabled:
            await self._broadcast_message("Voting disabled. Debate complete!", "moderator")
            return {}

        await self._broadcast_message(
            f"🗳️ Voting Phase\n"
            f"Vote for the most persuasive participant. "
            f"Voting closes in {self.phase_times[DebatePhase.VOTING]} seconds.",
            "moderator"
        )

        await self.voting_system.start_voting(
            list(self.participants.keys()),
            self.phase_times[DebatePhase.VOTING]
        )

        await asyncio.sleep(self.phase_times[DebatePhase.VOTING])

        results = await self.voting_system.end_voting()
        return results

    async def _results_phase(self, voting_results: Dict[str, Any]):
        """Announce final results."""
        self.state.phase = DebatePhase.RESULTS

        if voting_results:
            winner = voting_results.get('winner')
            vote_counts = voting_results.get('vote_counts', {})

            results_msg = "🏆 DEBATE RESULTS 🏆\n"
            results_msg += f"Winner: {winner}\n\n"
            results_msg += "Vote Breakdown:\n"

            for participant, votes in sorted(vote_counts.items(),
                                           key=lambda x: x[1], reverse=True):
                results_msg += f"  {participant}: {votes} votes\n"
        else:
            results_msg = "🤝 Debate concluded without voting. Great discussion everyone!"

        await self._broadcast_message(results_msg, "moderator")

        # Show participation statistics
        stats_msg = "\n📊 PARTICIPATION STATISTICS:\n"
        for participant_name, participant in self.participants.items():
            if hasattr(participant, 'get_stats'):
                stats = participant.get_stats()
                if hasattr(participant, 'config'):  # Bot
                    stats_msg += f"🤖 {participant_name}: {stats.get('autonomous_responses', 0)} autonomous responses, "
                    stats_msg += f"{stats.get('success_rate', 0):.1%} success rate\n"
                else:  # Human
                    stats_msg += f"👤 {participant_name}: {stats.get('responses_given', 0)} responses, "
                    stats_msg += f"{stats.get('participation_rate', 0):.1%} participation rate\n"

        # Show moderator stats
        moderator_stats = self.moderator_bot.get_stats()
        stats_msg += f"🎭 Moderator: {moderator_stats.get('autonomous_responses', 0)} facilitation prompts\n"

        await self._broadcast_message(stats_msg, "moderator")
        await self._broadcast_message("Thank you for participating in AI Jubilee Debate! 🎭✨", "moderator")

    # Utility methods
    async def _process_response(self, participant_name: str, response: str):
        """Process and validate participant response."""
        if len(response) > self.config.get('max_message_length', 5000):
            response = response[:self.config.get('max_message_length', 5000)] + "..."
            await self._broadcast_message(
                f"⚠️ {participant_name}'s response was truncated due to length",
                "moderator"
            )

        await self.chat_log.add_message(participant_name, response)

    async def _handle_timeout(self, participant_name: str):
        """Handle participant timeout."""
        self.state.warnings_issued[participant_name] = (
            self.state.warnings_issued.get(participant_name, 0) + 1
        )

        await self._broadcast_message(
            f"⏰ {participant_name} exceeded time limit. "
            f"Warning {self.state.warnings_issued[participant_name]}/3",
            "moderator"
        )

    async def _send_warning(self, participant_name: str, time_remaining: float):
        """Send time warning to participant."""
        await self._broadcast_message(
            f"⏰ {participant_name}: {int(time_remaining)} seconds remaining",
            "moderator"
        )

    async def _broadcast_message(self, content: str, sender: str = "moderator"):
        """Broadcast message to all participants and log."""
        message = await self.chat_log.add_message(sender, content, message_type="moderator")

        # Send to all participants
        for participant in self.participants.values():
            try:
                await participant.receive_message(message)
            except Exception as e:
                print(f"Failed to send message to {participant.name}: {e}")

    def get_state(self) -> DebateState:
        """Get current debate state."""
        return self.state