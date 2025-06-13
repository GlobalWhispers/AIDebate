"""
Main entry point for the AI Jubilee Debate System.
"""

import asyncio
import yaml
import click
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

from .moderator import Moderator
from .bot_client import BotClient
from .human_client import HumanClient
from .chat_log import ChatLog
from .voting import VotingSystem
from .streaming import StreamingServer
from .utils import setup_logging, load_config


async def start_debate_session(
    topic: Optional[str] = None,
    ai_bots: int = 2,
    human_participants: int = 1,
    config_path: str = "config.yaml"
) -> None:
    """
    Start a debate session with specified participants.

    Args:
        topic: Debate topic (if None, uses random from config)
        ai_bots: Number of AI bot participants
        human_participants: Number of human participants
        config_path: Path to configuration file
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load configuration
    config = load_config(config_path)

    # Setup logging
    setup_logging(config.get('chat', {}).get('log_level', 'INFO'))

    # Initialize chat log
    chat_log = ChatLog()

    # Initialize voting system
    voting_system = VotingSystem(config.get('voting', {}))

    # Select topic
    if not topic:
        import random
        topic = random.choice(config.get('topics', ["AI in society"]))

    # Create bot clients
    bot_clients = []
    bot_configs = config.get('bots', [])[:ai_bots]

    for i, bot_config in enumerate(bot_configs):
        bot = BotClient(
            name=bot_config['name'],
            model=bot_config['model'],
            provider=bot_config['provider'],
            personality=bot_config['personality'],
            stance=bot_config['stance'],
            api_key=config['api_keys'].get(bot_config['provider'])
        )
        bot_clients.append(bot)

    # Create human clients
    human_clients = []
    for i in range(human_participants):
        human = HumanClient(
            name=f"Human_{i+1}",
            config=config.get('interface', {})
        )
        human_clients.append(human)

    # Initialize moderator based on debate mode
    debate_mode = config.get('debate', {}).get('mode', 'sequential')

    moderator = Moderator(
        topic=topic,
        participants=bot_clients + human_clients,
        chat_log=chat_log,
        voting_system=voting_system,
        config=config
    )

    if debate_mode == "autonomous":
        print(f"🤖 Running in AUTONOMOUS mode - bots will decide when to speak!")
        print(f"📝 Topic: {topic}")
        print(f"👥 Participants: {len(bot_clients)} AI bots, {len(human_clients)} humans")
        print(f"⏰ Discussion time: {config.get('debate', {}).get('time_limit_minutes', 30)} minutes")
        print(f"🎯 Bots will monitor conversation and jump in when they feel compelled to respond!")
    else:
        print(f"📝 Running in SEQUENTIAL mode")
        print(f"👥 Participants take turns in order")

    # Initialize streaming server if enabled
    streaming_server = None
    if config.get('streaming', {}).get('enabled', False):
        streaming_server = StreamingServer(
            chat_log=chat_log,
            voting_system=voting_system,
            config=config.get('streaming', {})
        )
        await streaming_server.start()

    try:
        # Start the debate
        print(f"\n🎭 Starting AI Jubilee Debate: {topic}")
        print(f"Participants: {len(bot_clients)} AI bots, {len(human_clients)} humans\n")

        await moderator.run_debate()

    except KeyboardInterrupt:
        print("\n⏹️  Debate interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during debate: {e}")
    finally:
        # Cleanup
        if streaming_server:
            await streaming_server.stop()

        # Save transcript
        if config.get('chat', {}).get('save_transcripts', True):
            await chat_log.save_transcript(f"debate_{topic[:20]}.json")


@click.command()
@click.option('--topic', '-t', help='Debate topic')
@click.option('--bots', '-b', default=2, help='Number of AI bots')
@click.option('--humans', '-h', default=1, help='Number of human participants')
@click.option('--config', '-c', default='config.yaml', help='Configuration file path')
def cli(topic: str, bots: int, humans: int, config: str):
    """Launch the AI Jubilee Debate System."""
    asyncio.run(start_debate_session(topic, bots, humans, config))


if __name__ == "__main__":
    cli()