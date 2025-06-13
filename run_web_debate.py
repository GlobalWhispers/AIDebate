#!/usr/bin/env python3
"""
Enhanced web runner that creates natural conversations by properly integrating
the real bot system with autonomous monitoring and chat log integration.
"""

import asyncio
import threading
import http.server
import socketserver
from pathlib import Path
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing components
from app.web_server import DebateWebServer
from app.utils import load_config
from app.moderator import Moderator
from app.chat_log import ChatLog
from app.voting import VotingSystem
from app.bot_client import BotClient
from app.human_client import HumanClient


def serve_html():
    """Serve the HTML interface on port 8080."""
    PORT = 8080
    web_dir = Path("web")

    if not web_dir.exists():
        print(f"❌ Web directory not found: {web_dir}")
        return

    class WebHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)

        def log_message(self, format, *args):
            # Suppress HTTP server logs
            pass

    with socketserver.TCPServer(("", PORT), WebHandler) as httpd:
        print(f"🌐 Web interface running at: http://localhost:{PORT}")
        httpd.serve_forever()


class EnhancedWebServer(DebateWebServer):
    """Enhanced web server that properly integrates with real bot system."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.real_bots = {}
        self.chat_log_real = None

    def set_real_bots(self, bots):
        """Set the real bot instances."""
        self.real_bots = {bot.name: bot for bot in bots}
        print(f"🤖 Connected {len(self.real_bots)} real bots to web server")

    async def handle_human_message(self, data):
        """Enhanced human message handling with real bot integration."""
        sender = data.get('sender', 'Human_1')
        content = data.get('content', '').strip()

        if not content:
            return

        print(f"💬 Real human message from {sender}: '{content[:50]}...'")

        # Add to REAL chat log first - this will trigger real bot monitoring
        if self.chat_log_real:
            try:
                # Start response timer for tracking
                self.chat_log_real.start_response_timer(sender)

                # Add message to real chat log - this triggers bot autonomous monitoring!
                # The real chat log will handle broadcasting through its web_server connection
                message = await self.chat_log_real.add_message(sender, content)
                print(f"✅ Added to real chat log: {message.message_id}")

                # DON'T broadcast here - the real chat log already did it!
                # await self.broadcast_message(sender, content, "human")  # REMOVED to prevent duplicates

                # Log bot activity in web interface
                for bot_name in self.real_bots.keys():
                    await self.log_bot_check(bot_name, content)

            except Exception as e:
                print(f"⚠️ Error adding to real chat log: {e}")
                # Fallback to broadcasting directly only if chat log failed
                await self.broadcast_message(sender, content, "human")
        else:
            print(f"⚠️ No real chat log available, using fallback")
            await self.broadcast_message(sender, content, "human")

    def set_real_chat_log(self, chat_log):
        """Set the real chat log instance."""
        self.chat_log_real = chat_log
        print(f"🔗 Web server connected to REAL chat log")


async def setup_natural_bot_monitoring(bots, chat_log, web_server, topic):
    """Set up natural bot monitoring that responds to real messages."""
    print("🧠 Setting up natural bot autonomous monitoring...")

    # Start autonomous monitoring for all bots
    monitoring_tasks = []
    for bot in bots:
        print(f"🤖 Starting autonomous monitoring for {bot.name}")
        task = asyncio.create_task(
            bot.start_autonomous_monitoring(chat_log, topic)
        )
        monitoring_tasks.append(task)

    print(f"✅ Started autonomous monitoring for {len(bots)} bots")
    return monitoring_tasks


async def setup_moderator_monitoring(moderator, web_server):
    """Set up moderator autonomous monitoring with time management."""
    print("🎭 Setting up moderator autonomous monitoring with TIME CONTROL...")

    # Start moderator bot autonomous monitoring
    if hasattr(moderator, 'moderator_bot'):
        await moderator.moderator_bot.start_autonomous_monitoring(
            moderator.chat_log,
            moderator.topic
        )
        print("✅ Moderator autonomous monitoring started with time management")


class TimeManager:
    """Manages debate timing and phase transitions using config values."""

    def __init__(self, config, moderator, chat_log, web_server):
        self.config = config
        self.moderator = moderator
        self.chat_log = chat_log
        self.web_server = web_server

        # Time settings from config
        debate_config = config.get('debate', {})
        self.total_time = debate_config.get('time_limit_minutes', 15) * 60
        self.silence_timeout = debate_config.get('silence_timeout', 8)
        self.min_cooldown = debate_config.get('min_bot_cooldown', 5)
        self.max_cooldown = debate_config.get('max_bot_cooldown', 12)
        self.check_interval = debate_config.get('message_check_interval', 2)

        # Hyperactive settings from config
        hyperactive = config.get('hyperactive_settings', {})
        self.silence_break_prob = hyperactive.get('silence_break_probability', 0.85)
        self.conversation_starter_prob = hyperactive.get('conversation_starter_probability', 0.30)

        # Phase management - configurable
        self.opening_phase_percent = 0.25  # Could add to config
        self.closing_phase_percent = 0.75  # Could add to config

        # State tracking
        self.start_time = None
        self.last_activity_time = None
        self.last_moderator_intervention = 0
        self.current_focus = "opening"
        self.pivot_count = 0

        print(f"⏰ Time Manager initialized from config:")
        print(f"  Total time: {self.total_time // 60} minutes")
        print(f"  Silence timeout: {self.silence_timeout}s")
        print(f"  Bot cooldowns: {self.min_cooldown}-{self.max_cooldown}s")
        print(f"  Check interval: {self.check_interval}s")

    def start_timing(self):
        """Start the debate timer."""
        import time
        self.start_time = time.time()
        self.last_activity_time = time.time()
        print(f"⏰ Debate timer started - {self.total_time // 60} minutes total")

    def get_elapsed_time(self):
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0
        import time
        return time.time() - self.start_time

    def get_remaining_time(self):
        """Get remaining time in seconds."""
        elapsed = self.get_elapsed_time()
        return max(0, self.total_time - elapsed)

    def get_time_phase(self):
        """Determine what phase we're in based on config percentages."""
        elapsed = self.get_elapsed_time()
        total = self.total_time

        if elapsed < total * self.opening_phase_percent:
            return "opening"
        elif elapsed < total * self.closing_phase_percent:
            return "middle"
        else:
            return "closing"

    async def check_time_interventions(self):
        """Check if moderator should intervene based on config settings."""
        import time
        import random

        current_time = time.time()
        elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()

        # Update activity time if there are new messages
        if self.chat_log and len(self.chat_log.messages) > 0:
            last_message = list(self.chat_log.messages)[-1]
            if hasattr(last_message, 'timestamp'):
                self.last_activity_time = last_message.timestamp

        # Calculate silence duration
        silence_duration = current_time - self.last_activity_time if self.last_activity_time else 0

        # Time-based interventions using config values
        interventions = []

        # 1. Silence breaking (using config silence_timeout)
        if (silence_duration > self.silence_timeout and
                current_time - self.last_moderator_intervention > self.max_cooldown):
            # Use config probability for silence breaking
            if random.random() < self.silence_break_prob:
                interventions.append("silence_break")

        # 2. Phase transition prompts
        phase = self.get_time_phase()
        if phase != self.current_focus:
            self.current_focus = phase
            interventions.append(f"phase_transition_{phase}")

        # 3. Time milestone announcements (using config-based timing)
        if remaining > 0:
            minutes_remaining = remaining / 60
            total_minutes = self.total_time / 60

            # Dynamic milestones based on total time
            milestones = [
                total_minutes * 0.8,  # 80% time remaining
                total_minutes * 0.5,  # 50% time remaining
                total_minutes * 0.25,  # 25% time remaining
                1.0  # 1 minute remaining
            ]

            for milestone in milestones:
                if milestone - 0.5 < minutes_remaining <= milestone:
                    interventions.append("time_announcement")
                    break

        # 4. Topic pivot suggestions (using conversation_starter_prob)
        pivot_interval = max(60, self.total_time // 5)  # Every 20% of total time
        if (elapsed > 0 and elapsed % pivot_interval < self.check_interval * 2 and
                current_time - self.last_moderator_intervention > pivot_interval // 2):
            if random.random() < self.conversation_starter_prob:
                interventions.append("topic_pivot")

        # Execute interventions
        for intervention in interventions:
            await self.execute_intervention(intervention, remaining, silence_duration)
            self.last_moderator_intervention = current_time
            break  # Only one intervention per check

    async def execute_intervention(self, intervention_type, remaining_time, silence_duration):
        """Execute specific moderator interventions."""
        messages = []

        if intervention_type == "silence_break":
            messages = [
                f"🤔 {silence_duration:.0f} seconds of quiet... What are your thoughts on what's been said?",
                f"💭 The conversation paused - who wants to challenge or build on the recent points?",
                f"⚡ Let's keep the energy up! Any reactions to the arguments we've heard?",
                f"🎯 {silence_duration:.0f}s of silence - perfect time for a fresh perspective!"
            ]

        elif intervention_type == "phase_transition_middle":
            messages = [
                f"⏰ We're hitting our stride! {remaining_time // 60:.0f} minutes left - let's dive deeper into the core arguments!",
                f"🔥 Great start! Now let's get to the heart of this debate - what's the strongest case for each side?",
                f"💡 {remaining_time // 60:.0f} minutes remaining - time to challenge each other's assumptions!"
            ]

        elif intervention_type == "phase_transition_closing":
            messages = [
                f"⏰ Final phase! {remaining_time // 60:.0f} minutes left - what are your strongest arguments?",
                f"🏁 We're in the home stretch! Time to make your most compelling cases!",
                f"🎯 Last {remaining_time // 60:.0f} minutes - let's hear your best evidence and reasoning!"
            ]

        elif intervention_type == "time_announcement":
            minutes = remaining_time // 60
            total_minutes = self.total_time // 60
            percent_remaining = (remaining_time / self.total_time) * 100

            if percent_remaining > 75:
                messages = [f"⏰ {minutes:.0f} minutes remaining - great discussion so far!"]
            elif percent_remaining > 50:
                messages = [f"⏰ {minutes:.0f} minutes left - let's hear more perspectives!"]
            elif percent_remaining > 25:
                messages = [f"⏰ {minutes:.0f} minutes remaining - time for strong closing arguments!"]
            else:
                messages = [f"⏰ FINAL MINUTES! Last chance to make your case!"]

        elif intervention_type == "topic_pivot":
            self.pivot_count += 1
            messages = [
                f"🔄 Let's pivot - we've explored this angle well. What about the practical implications?",
                f"💫 Great points! Now let's shift focus - how does this impact different types of workers?",
                f"🎯 Interesting debate! Let's examine this from another angle - what about the economic effects?",
                f"🌟 Time for a fresh perspective! What are the long-term consequences we haven't discussed?"
            ]

        # Send the intervention message
        if messages:
            import random
            message = random.choice(messages)
            await self.chat_log.add_message("Moderator", message, message_type="moderator")

            # Also broadcast to web
            await self.web_server.broadcast_message("Moderator", message, "moderator")

            print(f"🎭 Moderator intervention: {intervention_type} - '{message[:50]}...'")


class EnhancedBotMonitor:
    """Enhanced bot monitoring that uses ALL config values."""

    def __init__(self, config):
        self.config = config

        # Get hyperactive settings from config
        hyperactive = config.get('hyperactive_settings', {})
        self.base_probability = hyperactive.get('base_response_probability', 0.80)
        self.personality_multipliers = hyperactive.get('personality_multipliers', {})
        self.competitive_boost = hyperactive.get('competitive_boost', 0.3)
        self.burning_question_boost = hyperactive.get('burning_question_boost', 0.5)

        # Get competition settings from config
        competition = config.get('competition', {})
        self.enable_rivalry = competition.get('enable_bot_rivalry', True)
        self.rivalry_boost = competition.get('rivalry_boost', 0.2)
        self.dominance_penalty = competition.get('dominance_penalty', 0.001)
        self.underdog_boost = competition.get('underdog_boost', 0.3)

        # Get personality evolution settings
        evolution = config.get('personality_evolution', {})
        self.passion_increase = evolution.get('passion_increase_rate', 0.05)
        self.confidence_boost = evolution.get('confidence_boost', 0.03)
        self.frustration_buildup = evolution.get('frustration_buildup', 0.02)

        print(f"🧠 Enhanced Bot Monitor initialized from config:")
        print(f"  Base Response Probability: {self.base_probability:.0%}")
        print(f"  Personality Multipliers: {self.personality_multipliers}")
        print(f"  Competition enabled: {self.enable_rivalry}")
        print(f"  Rivalry boost: {self.rivalry_boost}")
        print(f"  Underdog boost: {self.underdog_boost}")

    def get_bot_response_probability(self, bot, message_content, conversation_context):
        """Calculate response probability using ALL config values."""
        base_prob = self.base_probability

        # Apply personality multipliers from config
        personality = bot.config.personality.lower()
        multiplier = 1.0

        for personality_type, mult in self.personality_multipliers.items():
            if personality_type in personality:
                multiplier = mult
                break

        # Competition boosts from config
        if self.enable_rivalry:
            # Check if this bot is being dominated (underdog boost)
            recent_messages = conversation_context[-10:] if conversation_context else []
            bot_recent_count = sum(1 for msg in recent_messages if hasattr(msg, 'sender') and msg.sender == bot.name)
            other_bot_count = sum(1 for msg in recent_messages if
                                  hasattr(msg, 'sender') and msg.sender != bot.name and msg.sender not in ['Human_1',
                                                                                                           'System',
                                                                                                           'Moderator'])

            if bot_recent_count == 0 and other_bot_count > 2:
                multiplier += self.underdog_boost  # From config
            elif bot_recent_count > 3:
                multiplier -= self.dominance_penalty * bot_recent_count  # From config

        # Stance-based adjustments with config boosts
        message_lower = message_content.lower()

        if bot.config.stance == "pro":
            # Advocate gets boosted when challenged
            challenge_words = ['wrong', 'problem', 'issue', 'concern', 'fail', 'bad', 'terrible', 'awful']
            if any(word in message_lower for word in challenge_words):
                multiplier += self.competitive_boost  # From config

        elif bot.config.stance == "con":
            # Skeptic gets boosted when people are too positive
            positive_words = ['great', 'amazing', 'perfect', 'wonderful', 'benefit', 'excellent', 'fantastic']
            if any(word in message_lower for word in positive_words):
                multiplier += self.competitive_boost  # From config

        elif bot.config.stance == "neutral":
            if "Socrates" in bot.name:
                # Socrates loves deep questions and assumptions
                philosophical_triggers = ['why', 'what', 'how', 'assume', 'mean', 'define', 'essence', 'nature']
                if any(word in message_lower for word in philosophical_triggers):
                    multiplier += self.burning_question_boost  # From config

            elif "Mediator" in bot.name:
                # Mediator jumps in during conflicts
                conflict_words = ['disagree', 'wrong', 'but', 'however', 'conflict', 'argue', 'fight']
                if any(word in message_lower for word in conflict_words):
                    multiplier += self.competitive_boost  # From config

        # Apply personality evolution (from config)
        if hasattr(bot, 'total_responses'):
            # Confidence boost for successful bots
            confidence_factor = min(0.2, bot.total_responses * self.confidence_boost)
            multiplier += confidence_factor

            # Frustration for bots that haven't responded much
            missed_opportunities = getattr(bot, 'missed_opportunities', 0)
            frustration_factor = min(0.3, missed_opportunities * self.frustration_buildup)
            multiplier += frustration_factor

        final_probability = min(0.95, base_prob * multiplier)

        return final_probability


class BotActivityLogger:
    """Logger that connects real bot activity to web interface."""

    def __init__(self, web_server):
        self.web_server = web_server

    async def log_bot_thinking(self, bot_name, message):
        """Log when bot is thinking about a message."""
        await self.web_server.log_bot_check(bot_name, message)

    async def log_bot_triggered(self, bot_name, message):
        """Log when bot is triggered."""
        await self.web_server.log_bot_trigger(bot_name, message)

    async def log_bot_responded(self, bot_name, response):
        """Log when bot responds."""
        await self.web_server.log_bot_response(bot_name, response)

    """Logger that connects real bot activity to web interface."""

    def __init__(self, web_server):
        self.web_server = web_server

    async def log_bot_thinking(self, bot_name, message):
        """Log when bot is thinking about a message."""
        await self.web_server.log_bot_check(bot_name, message)

    async def log_bot_triggered(self, bot_name, message):
        """Log when bot is triggered."""
        await self.web_server.log_bot_trigger(bot_name, message)

    async def log_bot_responded(self, bot_name, response):
        """Log when bot responds."""
        await self.web_server.log_bot_response(bot_name, response)


async def run_web_debate():
    """Run debate with web interface using natural bot conversations."""

    print("🎭 AI Jubilee Debate - Enhanced Natural Conversation Mode")
    print("=" * 60)

    # Start HTML server in background
    html_thread = threading.Thread(target=serve_html, daemon=True)
    html_thread.start()

    # Load your existing config
    print("📋 Loading configuration...")
    config = load_config()

    # Create Enhanced WebSocket server
    print("🔗 Starting Enhanced WebSocket server...")
    web_server = EnhancedWebServer()
    await web_server.start_server()

    # Create your existing components with enhanced integration
    print("🚀 Setting up enhanced debate components...")

    # Chat log with web integration
    chat_log = ChatLog()
    chat_log.set_web_server(web_server)

    # Connect web server to REAL chat log
    web_server.set_real_chat_log(chat_log)  # This is the key connection!

    # Voting system
    voting_config = config.get('voting', {})
    voting_system = VotingSystem(voting_config)

    # Load API keys from .env file
    from dotenv import load_dotenv
    load_dotenv()

    api_keys = {
        'openai': os.getenv('OPENAI_API_KEY'),
        'anthropic': os.getenv('ANTHROPIC_API_KEY')
    }

    print(f"🔑 API Keys Status:")
    print(f"  OpenAI: {'✅' if api_keys['openai'] else '❌'}")
    print(f"  Anthropic: {'✅' if api_keys['anthropic'] else '❌'}")

    # Create REAL bots with enhanced monitoring
    participants = []
    bots = []

    for bot_config in config.get('bots', []):
        provider = bot_config['provider']
        api_key = api_keys.get(provider)

        if not api_key:
            print(f"⚠️ No API key for {provider}, skipping {bot_config['name']}")
            continue

        print(f"🤖 Creating REAL bot: {bot_config['name']}")
        print(f"  Provider: {provider}")
        print(f"  Model: {bot_config['model']}")
        print(f"  Stance: {bot_config['stance']}")
        print(f"  Personality: {bot_config['personality'][:50]}...")

        bot = BotClient(
            name=bot_config['name'],
            model=bot_config['model'],
            provider=provider,
            personality=bot_config['personality'],
            stance=bot_config['stance'],
            api_key=api_key,
            temperature=bot_config.get('temperature', 0.8),
            max_tokens=bot_config.get('max_tokens', 120)
        )

        participants.append(bot)
        bots.append(bot)
        print(f"✅ Created REAL bot: {bot.name}")

    # Connect real bots to web server
    web_server.set_real_bots(bots)

    # Add human participant
    human_config = config.get('interface', {})
    human = HumanClient("Human_1", human_config)
    participants.append(human)
    print(f"✅ Created human participant: {human.name}")

    # Create moderator with real integration
    topic = config['debate'].get('default_topic', 'Remote work is the future of employment')
    config['api_keys'] = api_keys

    moderator = Moderator(
        topic=topic,
        participants=participants,
        chat_log=chat_log,
        voting_system=voting_system,
        config=config
    )

    # Connect web server to moderator
    web_server.set_moderator(moderator)

    # Create time manager for moderator control
    print("⏰ Setting up intelligent time management...")
    time_manager = TimeManager(config, moderator, chat_log, web_server)

    # Create enhanced bot monitor with config percentages
    bot_monitor = EnhancedBotMonitor(config)

    print("🧠 Setting up NATURAL bot conversations...")

    # This is the KEY: Start autonomous monitoring for all bots
    monitoring_tasks = await setup_natural_bot_monitoring(bots, chat_log, web_server, topic)

    # Set up moderator monitoring
    await setup_moderator_monitoring(moderator, web_server)

    print("🎯 Enhanced system ready!")
    print(f"🌐 Open browser to: http://localhost:8080")
    print(f"🔗 WebSocket: ws://localhost:8081")
    print(f"📝 Topic: {topic}")
    print()

    # Send enhanced initial message
    participant_list = []
    for p in participants:
        if hasattr(p, 'config') and hasattr(p.config, 'stance'):  # Bot
            participant_list.append(f"🤖 {p.name} ({p.config.stance}) - AUTONOMOUS & ACTIVE")
        else:  # Human
            participant_list.append(f"👤 {p.name} - Can type anytime!")

    initial_message = (
            f"🎭 Welcome to AI Jubilee Debate - NATURAL CONVERSATION MODE!\n\n"
            f"📝 Topic: {topic}\n\n"
            f"👥 Participants:\n" + "\n".join(participant_list) +
            f"\n\n🧠 BOTS ARE NOW ACTIVELY MONITORING!\n"
            f"✨ They will respond naturally when they feel compelled\n"
            f"💬 Type your message to start the natural debate!\n"
            f"🔥 Bots check every message and decide autonomously whether to respond"
    )

    await web_server.broadcast_message(
        sender="System",
        content=initial_message,
        message_type="moderator"
    )

    print("🚀 NATURAL CONVERSATION MODE ACTIVE!")
    print("🤖 All bots are autonomously monitoring the chat log")
    print("💬 They will respond when triggered by your messages")
    print("🧠 Each message you send triggers real bot decision-making")
    print("🛑 Press Ctrl+C to stop")

    # Create activity logger
    activity_logger = BotActivityLogger(web_server)

    # Keep the server running with enhanced monitoring
    try:
        # Start the debate timer
        time_manager.start_timing()

        # Send a welcome message to trigger initial bot activity
        await chat_log.add_message("System",
                                   f"🎭 The debate begins! Topic: {topic}. "
                                   f"You have {config['debate']['time_limit_minutes']} minutes total. "
                                   f"What are your initial thoughts? Let's start the discussion!"
                                   )

        iteration = 0
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            iteration += 1

            # TIME MANAGEMENT - Check for moderator interventions
            await time_manager.check_time_interventions()

            # Check if debate time is up
            remaining_time = time_manager.get_remaining_time()
            if remaining_time <= 0:
                await chat_log.add_message("Moderator",
                                           "⏰ TIME'S UP! The debate has concluded. Thank you all for the fantastic discussion!"
                                           )
                print("⏰ Debate time expired - ending session")
                break

            # Enhanced statistics with time info
            enhanced_stats = {
                'active_bots': len([p for p in participants if hasattr(p, 'config')]),
                'total_participants': len(participants),
                'monitoring_bots': len([b for b in bots if b.is_monitoring]),
                'total_messages': len(chat_log.messages) if chat_log.messages else 0,
                'autonomous_mode': True,
                'natural_conversation': True,
                'elapsed_time': time_manager.get_elapsed_time(),
                'remaining_time': remaining_time,
                'current_phase': time_manager.get_time_phase(),
                'total_time': time_manager.total_time,
                'pivot_count': time_manager.pivot_count
            }

            await web_server.broadcast_stats(enhanced_stats)

            # Show bot status and probabilities every 2 minutes
            if iteration % 24 == 0:  # Every 2 minutes (24 * 5 second intervals)
                print(f"🤖 Bot Response Probabilities Check:")
                recent_messages = list(chat_log.messages)[-3:] if chat_log.messages else []
                sample_message = recent_messages[-1].content if recent_messages else "sample message"

                for bot in bots:
                    prob = bot_monitor.get_bot_response_probability(bot, sample_message, recent_messages)
                    status = "MONITORING" if bot.is_monitoring else "INACTIVE"
                    total_responses = getattr(bot, 'total_responses', 0)
                    print(f"  {bot.name}: {status} ({total_responses} responses, {prob:.0%} trigger chance)")

                # Show time status
                elapsed_min = time_manager.get_elapsed_time() / 60
                remaining_min = remaining_time / 60
                print(
                    f"⏰ Time: {elapsed_min:.1f}m elapsed, {remaining_min:.1f}m remaining, Phase: {time_manager.get_time_phase()}")

    except KeyboardInterrupt:
        print("\n🛑 Shutting down natural conversation system...")

        # Stop all bot monitoring
        print("🤖 Stopping bot autonomous monitoring...")
        stop_tasks = []
        for bot in bots:
            if hasattr(bot, 'stop_monitoring'):
                task = asyncio.create_task(bot.stop_monitoring())
                stop_tasks.append(task)

        # Stop moderator monitoring
        if hasattr(moderator, 'moderator_bot') and hasattr(moderator.moderator_bot, 'stop_monitoring'):
            task = asyncio.create_task(moderator.moderator_bot.stop_monitoring())
            stop_tasks.append(task)

        # Wait for all stops to complete
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Cancel monitoring tasks
        for task in monitoring_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop web server
        try:
            await web_server.stop_server()
        except Exception as e:
            print(f"⚠️ Error stopping web server: {e}")

        print("✅ Natural conversation system shutdown complete!")

        # Show final statistics with time breakdown
        if chat_log.messages:
            final_stats = chat_log.get_statistics()
            total_time_minutes = time_manager.get_elapsed_time() / 60
            print(f"\n📊 Final Debate Statistics:")
            print(f"  📝 Total Messages: {final_stats['total_messages']}")
            print(f"  🤖 Bot Responses: {final_stats['bot_responses']}")
            print(f"  👤 Human Responses: {final_stats['human_responses']}")
            print(
                f"  ⏰ Total Time: {total_time_minutes:.1f} minutes (of {config['debate']['time_limit_minutes']} planned)")
            print(f"  🔄 Topic Pivots: {time_manager.pivot_count}")
            print(f"  📈 Messages/Minute: {final_stats['total_messages'] / max(1, total_time_minutes):.1f}")

            # Show individual bot performance
            print(f"\n🤖 Bot Performance:")
            for bot in bots:
                if hasattr(bot, 'get_stats'):
                    bot_stats = bot.get_stats()
                    print(f"  {bot.name}: {bot_stats.get('autonomous_responses', 0)} responses, "
                          f"{bot_stats.get('success_rate', 0):.1%} success rate")


def main():
    """Main entry point."""
    # Check requirements
    if not Path("web/index.html").exists():
        print("❌ web/index.html not found!")
        print("🔧 Please create web/index.html with the interface code")
        return

    if not Path("config.yaml").exists():
        print("❌ config.yaml not found!")
        print("🔧 Please ensure your config file exists")
        return

    # Check for .env file
    if not Path(".env").exists():
        print("⚠️ .env file not found!")
        print("🔧 Create .env file with:")
        print("   OPENAI_API_KEY=your-openai-key")
        print("   ANTHROPIC_API_KEY=your-anthropic-key")

    # Check if python-dotenv is installed
    try:
        import dotenv
    except ImportError:
        print("❌ python-dotenv not installed!")
        print("🔧 Install with: pip install python-dotenv")
        return

    print("🚀 Starting Natural Conversation Debate System...")
    asyncio.run(run_web_debate())


if __name__ == "__main__":
    main()