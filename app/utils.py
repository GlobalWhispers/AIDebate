"""
Utility functions for the AI Jubilee Debate System.
"""

import os
import yaml
import logging
import time
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config_content = f.read()

    # Substitute environment variables
    config_content = substitute_env_vars(config_content)

    try:
        config = yaml.safe_load(config_content)
        return config
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")


def substitute_env_vars(text: str) -> str:
    """
    Substitute environment variables in text using ${VAR_NAME} syntax.

    Args:
        text: Text containing environment variable references

    Returns:
        Text with environment variables substituted
    """
    def replace_env_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            print(f"Warning: Environment variable {var_name} not found")
            return f"${{{var_name}}}"  # Keep original if not found
        return env_value

    return re.sub(r'\$\{([^}]+)\}', replace_env_var, text)


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def format_time_remaining(seconds: float) -> str:
    """
    Format remaining time in human-readable format.

    Args:
        seconds: Time remaining in seconds

    Returns:
        Formatted time string
    """
    if seconds <= 0:
        return "Time's up!"

    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def generate_debate_prompt(topic: str, role: str, personality: str) -> str:
    """
    Generate a debate prompt for AI participants.

    Args:
        topic: Debate topic
        role: Participant role (pro, con, neutral)
        personality: Personality description

    Returns:
        Generated prompt
    """
    base_prompt = f"""You are participating in a structured debate on the topic: "{topic}"

Your role: {role}
Your personality: {personality}

Instructions:
1. Present clear, logical arguments
2. Respond to other participants' points
3. Stay focused on the topic
4. Be respectful but persuasive
5. Keep responses concise and engaging

Current debate topic: {topic}
"""

    if role.lower() == "pro":
        base_prompt += "\nYou should argue IN FAVOR of the topic."
    elif role.lower() == "con":
        base_prompt += "\nYou should argue AGAINST the topic."
    elif role.lower() == "neutral":
        base_prompt += "\nYou should present balanced perspectives and ask probing questions."

    return base_prompt


def validate_participant_name(name: str) -> bool:
    """
    Validate participant name.

    Args:
        name: Participant name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name.strip()) == 0:
        return False

    # Check length
    if len(name) > 50:
        return False

    # Check for valid characters (alphanumeric, spaces, underscores, hyphens)
    if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')

    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string into seconds.

    Args:
        duration_str: Duration string (e.g., "5m", "30s", "1h30m")

    Returns:
        Duration in seconds
    """
    if duration_str.isdigit():
        return int(duration_str)

    total_seconds = 0

    # Parse hours
    hours_match = re.search(r'(\d+)h', duration_str.lower())
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600

    # Parse minutes
    minutes_match = re.search(r'(\d+)m', duration_str.lower())
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60

    # Parse seconds
    seconds_match = re.search(r'(\d+)s', duration_str.lower())
    if seconds_match:
        total_seconds += int(seconds_match.group(1))

    return total_seconds if total_seconds > 0 else 60  # Default to 60 seconds


def create_timestamp() -> str:
    """
    Create ISO format timestamp.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.now().isoformat()


def format_participant_list(participants: List[str], max_display: int = 5) -> str:
    """
    Format participant list for display.

    Args:
        participants: List of participant names
        max_display: Maximum participants to display before truncating

    Returns:
        Formatted participant string
    """
    if len(participants) <= max_display:
        return ", ".join(participants)

    displayed = participants[:max_display]
    remaining = len(participants) - max_display

    return f"{', '.join(displayed)} (+{remaining} more)"


def calculate_word_count(text: str) -> int:
    """
    Calculate word count in text.

    Args:
        text: Text to count words in

    Returns:
        Number of words
    """
    return len(text.split())


def extract_key_phrases(text: str, max_phrases: int = 5) -> List[str]:
    """
    Extract key phrases from text (simple implementation).

    Args:
        text: Text to extract phrases from
        max_phrases: Maximum number of phrases to return

    Returns:
        List of key phrases
    """
    # Simple implementation - could be enhanced with NLP
    sentences = text.split('.')
    phrases = []

    for sentence in sentences[:max_phrases]:
        sentence = sentence.strip()
        if len(sentence) > 10:  # Minimum length
            phrases.append(sentence)

    return phrases[:max_phrases]


def generate_session_id() -> str:
    """
    Generate unique session ID.

    Returns:
        Unique session identifier
    """
    import uuid
    return str(uuid.uuid4())[:8]


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, create if necessary.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def load_debate_topics(topics_file: str = "topics.txt") -> List[str]:
    """
    Load debate topics from file.

    Args:
        topics_file: Path to topics file

    Returns:
        List of debate topics
    """
    topics_path = Path(topics_file)

    if not topics_path.exists():
        # Return default topics
        return [
            "Artificial intelligence will create more jobs than it destroys",
            "Social media has a net positive impact on society",
            "Universal Basic Income is necessary for the future economy",
            "Climate change requires immediate radical action",
            "Privacy is more important than security"
        ]

    with open(topics_path, 'r', encoding='utf-8') as f:
        topics = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    return topics


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def __str__(self) -> str:
        return f"{self.operation_name}: {self.duration:.3f}s"


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    else:
                        raise last_exception

            raise last_exception

        return wrapper
    return decorator