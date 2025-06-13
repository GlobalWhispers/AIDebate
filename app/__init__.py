"""
AI  Debate System

A platform for structured debates between AI bots and human participants.
"""

__version__ = "1.0.0"
__author__ = "AndreiVoicuT"

from .main import start_debate_session
from .moderator import Moderator
from .bot_client import BotClient
from .human_client import HumanClient
from .chat_log import ChatLog
from .voting import VotingSystem

__all__ = [
    "start_debate_session",
    "Moderator",
    "BotClient",
    "HumanClient",
    "ChatLog",
    "VotingSystem"
]