"""
Human client implementation for debate participation.
Now with true autonomous participation - can speak anytime!
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .chat_log import Message


@dataclass
class InterfaceConfig:
    """Configuration for human interface."""
    mode: str = "cli"
    enable_rich_formatting: bool = True
    show_typing_indicators: bool = True
    enable_reactions: bool = True
    input_timeout: int = 120


class CLIInterface:
    """Command line interface for human participants."""

    def __init__(self, config: InterfaceConfig):
        self.config = config
        self.rich_console = None
        self.input_task = None

        if config.enable_rich_formatting:
            try:
                from rich.console import Console
                from rich.live import Live
                self.rich_console = Console()
            except ImportError:
                print("Rich not available, using basic formatting")

    async def display_message(self, message: Message):
        """Display a message to the user."""
        timestamp = time.strftime("%H:%M:%S", time.localtime(message.timestamp))

        if self.rich_console:
            if message.message_type == "moderator":
                self.rich_console.print(
                    f"[{timestamp}] 🎭 {message.sender}: {message.content}",
                    style="bold yellow"
                )
            elif message.sender.endswith('_1') or 'Human' in message.sender:
                # Don't display our own messages back to us
                return
            else:
                self.rich_console.print(
                    f"[{timestamp}] 🤖 {message.sender}: {message.content}",
                    style="cyan"
                )
        else:
            if message.message_type == "moderator":
                print(f"[{timestamp}] 🎭 {message.sender}: {message.content}")
            elif not (message.sender.endswith('_1') or 'Human' in message.sender):
                print(f"[{timestamp}] 🤖 {message.sender}: {message.content}")

    async def get_input(self, prompt: str, timeout: int = 10) -> str:
        """Get input from user with timeout."""
        if self.rich_console:
            self.rich_console.print(f"💬 {prompt}", style="bold green")
        else:
            print(f"💬 {prompt}")

        # Start input task
        self.input_task = asyncio.create_task(self._get_user_input())

        try:
            # Wait for input or timeout
            response = await asyncio.wait_for(self.input_task, timeout=timeout)
            return response.strip()

        except asyncio.TimeoutError:
            if self.input_task and not self.input_task.done():
                self.input_task.cancel()
                try:
                    await self.input_task
                except asyncio.CancelledError:
                    pass
            return ""
        except asyncio.CancelledError:
            if self.input_task and not self.input_task.done():
                self.input_task.cancel()
            return ""
        except Exception as e:
            print(f"Input error: {e}")
            if self.input_task and not self.input_task.done():
                self.input_task.cancel()
            return ""

    async def _get_user_input(self) -> str:
        """Get user input asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "")

    async def show_notification(self, message: str, level: str = "info"):
        """Show a notification to the user."""
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }

        icon = icons.get(level, "ℹ️")

        if self.rich_console:
            colors = {
                "info": "blue",
                "warning": "yellow",
                "error": "red",
                "success": "green"
            }
            color = colors.get(level, "blue")
            self.rich_console.print(f"{icon} {message}", style=color)
        else:
            print(f"{icon} {message}")


class WebInterface:
    """Web interface for human participants."""

    def __init__(self, config: InterfaceConfig):
        self.config = config
        self.websocket = None
        self.pending_responses = {}

    async def display_message(self, message: Message):
        """Display message via websocket."""
        if self.websocket:
            await self.websocket.send_json({
                "type": "message",
                "data": message.to_dict()
            })

    async def get_input(self, prompt: str, timeout: int = 120) -> str:
        """Get input via websocket."""
        if not self.websocket:
            return ""

        request_id = f"input_{time.time()}"
        await self.websocket.send_json({
            "type": "input_request",
            "id": request_id,
            "prompt": prompt,
            "timeout": timeout
        })

        # Wait for response
        try:
            response = await asyncio.wait_for(
                self._wait_for_response(request_id),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            return ""

    async def _wait_for_response(self, request_id: str) -> str:
        """Wait for websocket response."""
        while request_id not in self.pending_responses:
            await asyncio.sleep(0.1)
        return self.pending_responses.pop(request_id)

    async def show_notification(self, message: str, level: str = "info"):
        """Show notification via websocket."""
        if self.websocket:
            await self.websocket.send_json({
                "type": "notification",
                "message": message,
                "level": level
            })


class HumanClient:
    """
    Human participant in the debate system with autonomous participation.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_active = True
        self.conversation_history: List[Message] = []

        # Initialize appropriate interface
        interface_config = InterfaceConfig(
            mode=config.get('mode', 'cli'),
            enable_rich_formatting=config.get('enable_rich_formatting', True),
            show_typing_indicators=config.get('show_typing_indicators', True),
            enable_reactions=config.get('enable_reactions', True),
            input_timeout=config.get('input_timeout', 120)
        )

        if interface_config.mode == "cli":
            self.interface = CLIInterface(interface_config)
        elif interface_config.mode == "web":
            self.interface = WebInterface(interface_config)
        else:
            raise ValueError(f"Unsupported interface mode: {interface_config.mode}")

        # Statistics tracking
        self.stats = {
            'responses_given': 0,
            'timeouts': 0,
            'total_response_time': 0.0,
            'average_response_time': 0.0
        }

    async def autonomous_participation_loop(self, chat_log):
        """True autonomous participation - human can speak anytime."""
        if not self.is_active:
            return

        await self.interface.show_notification(
            "🎯 AUTONOMOUS MODE ACTIVE - You can speak ANYTIME!", "success"
        )
        await self.interface.show_notification(
            "🗣️  You can speak at ANY TIME during the discussion!", "info"
        )
        await self.interface.show_notification(
            "💡 Commands: 'help', 'status', 'history', 'quit'", "info"
        )
        await self.interface.show_notification(
            "✏️  Just type your response and press Enter to join the conversation!", "info"
        )

        # Subscribe to chat updates for display
        message_queue = chat_log.subscribe()
        last_displayed = len(chat_log.messages)

        while self.is_active:
            try:
                # Check for new messages to display
                current_count = len(chat_log.messages)
                if current_count > last_displayed:
                    new_messages = list(chat_log.messages)[last_displayed:]
                    for msg in new_messages:
                        if msg.sender != self.name:  # Don't show own messages
                            await self.interface.display_message(msg)
                    last_displayed = current_count

                # Get user input with short timeout for responsiveness
                response = await self.interface.get_input(
                    "Type your response (or command):",
                    timeout=10  # Short timeout for responsiveness
                )

                if not response:
                    continue  # Timeout, check for new messages

                response = response.strip()

                # Handle commands
                if response.lower() in ['quit', 'exit']:
                    await self.interface.show_notification(
                        "👋 Leaving the debate. Thanks for participating!", "success"
                    )
                    self.is_active = False
                    break
                elif response.lower() == 'help':
                    await self._show_autonomous_help()
                    continue
                elif response.lower() == 'status':
                    await self._show_status()
                    continue
                elif response.lower() == 'history':
                    await self.interface.show_notification("📜 Recent conversation:", "info")
                    recent = chat_log.get_recent_messages(5)
                    for msg in recent:
                        await self.interface.display_message(msg)
                    continue
                elif len(response) < 3:
                    await self.interface.show_notification(
                        "⚠️ Please provide a more substantial response (at least 3 characters).",
                        "warning"
                    )
                    continue

                # Process and post message directly to chat log
                validated_response = self._validate_response(response)
                if validated_response:
                    await chat_log.add_message(self.name, validated_response)
                    self.stats['responses_given'] += 1
                    await self.interface.show_notification(
                        "✅ Your message has been added to the debate!", "success"
                    )

            except Exception as e:
                await self.interface.show_notification(f"❌ Error: {e}", "error")
                await asyncio.sleep(2)

        # Cleanup
        chat_log.unsubscribe(message_queue)
        await self.interface.show_notification(
            "🛑 Autonomous participation ended.", "info"
        )

    async def _show_autonomous_help(self):
        """Show help information for autonomous mode."""
        help_text = """
🎯 AI JUBILEE DEBATE - AUTONOMOUS MODE HELP

COMMANDS:
• Just type your response and press Enter to join the debate
• 'help' - Show this help message
• 'status' - Show your participation statistics  
• 'history' - Show recent conversation messages
• 'quit' - Leave the debate

AUTONOMOUS MODE:
• You can speak at ANY TIME during the discussion phase
• Bots and moderator are monitoring and will respond when they feel compelled
• No turn-taking - completely organic conversation flow
• Your responses are immediately added to the debate

TIPS:
• Keep responses focused and substantial (3+ characters)
• Reference specific points made by others
• Feel free to jump in whenever you have something to add!
• The debate flows naturally - speak when inspired!

DEBATE PHASES:
1. Introduction & Opening Statements (structured)
2. Autonomous Discussion (free-flowing - you can speak anytime!)
3. Closing Statements (structured)  
4. Voting Phase

Enjoy the organic debate experience! 🎭
        """

        await self.interface.show_notification(help_text, "info")

    async def _show_status(self):
        """Show participation status."""
        stats = self.get_stats()
        await self.interface.show_notification(
            f"📊 Your participation: {stats['responses_given']} responses, "
            f"{stats['participation_rate']:.1%} participation rate, "
            f"avg response time: {stats['average_response_time']:.1f}s",
            "info"
        )

    def _validate_response(self, response: str) -> str:
        """Validate and clean up human response."""
        if not response or not response.strip():
            return ""

        # Clean up the response
        response = response.strip()

        # Check length limits
        max_length = self.config.get('max_message_length', 500)
        if len(response) > max_length:
            response = response[:max_length - 3] + "..."

        # Add note for very short responses
        if len(response) < 10:
            response += " [Note: Very short response]"

        return response

    # Legacy methods for structured phases
    async def get_response(self, topic: str, messages: List[Message]) -> str:
        """Get response from human participant (for structured phases)."""
        if not self.is_active:
            return ""

        start_time = time.time()

        try:
            # Show context in structured phases
            if len(messages) > 0:
                await self.interface.show_notification(
                    f"📜 Recent messages in conversation:",
                    "info"
                )
                # Show last 3 messages for context
                recent = messages[-3:] if len(messages) >= 3 else messages
                for msg in recent:
                    await self.interface.display_message(msg)
                await self.interface.show_notification("─" * 50, "info")

            # Get response with timeout
            response = await self.interface.get_input(
                f"💬 Your response to: {topic}",
                timeout=self.config.get('input_timeout', 120)
            )

            # Validate and process response
            if response:
                validated_response = self._validate_response(response)
                if validated_response:
                    # Add to conversation history
                    response_msg = Message(
                        sender=self.name,
                        content=validated_response,
                        timestamp=time.time(),
                        message_id=len(self.conversation_history) + 1
                    )
                    self.conversation_history.append(response_msg)

                    # Update stats
                    response_time = time.time() - start_time
                    self._update_stats(response_time, success=True)

                    return validated_response

            # Handle timeout/empty response
            response_time = time.time() - start_time
            self._update_stats(response_time, success=False)
            return ""

        except Exception as e:
            await self.interface.show_notification(
                f"❌ Error getting response: {e}",
                "error"
            )
            return ""

    async def receive_message(self, message: Message):
        """Receive and display a message from the debate."""
        # Don't show our own messages back to us
        if message.sender == self.name:
            return

        # Add to conversation history
        self.conversation_history.append(message)

        # Limit history size
        if len(self.conversation_history) > 30:
            self.conversation_history = self.conversation_history[-30:]

        # Display the message (in autonomous mode, this is handled by the loop)
        try:
            if not hasattr(self, '_in_autonomous_mode'):
                await self.interface.display_message(message)
        except Exception as e:
            print(f"Error displaying message: {e}")

    async def handle_voting(self, candidates: List[str], time_limit: int) -> Dict[str, Any]:
        """Handle voting process for human participant."""
        await self.interface.show_notification(
            f"🗳️ Voting phase! You have {time_limit} seconds to vote.",
            "info"
        )

        # Show candidates
        await self.interface.show_notification(
            "📋 Candidates:", "info"
        )
        for i, candidate in enumerate(candidates, 1):
            await self.interface.show_notification(
                f"  {i}. {candidate}", "info"
            )

        try:
            # Get vote choice
            choice_input = await self.interface.get_input(
                f"Enter your choice (1-{len(candidates)}):",
                timeout=time_limit
            )

            if not choice_input:
                return {'voted': False, 'reason': 'timeout'}

            try:
                choice = int(choice_input.strip())
                if 1 <= choice <= len(candidates):
                    selected_candidate = candidates[choice - 1]

                    # Get justification if using CLI
                    justification = ""
                    if isinstance(self.interface, CLIInterface):
                        justification = await self.interface.get_input(
                            "Optional: Why did you choose this candidate?",
                            timeout=30
                        )

                    return {
                        'voted': True,
                        'candidate': selected_candidate,
                        'justification': justification or ""
                    }
                else:
                    return {'voted': False, 'reason': 'invalid_choice'}

            except ValueError:
                return {'voted': False, 'reason': 'invalid_format'}

        except Exception as e:
            await self.interface.show_notification(
                f"❌ Voting error: {e}", "error"
            )
            return {'voted': False, 'reason': 'error'}

    def _update_stats(self, response_time: float, success: bool):
        """Update response statistics."""
        if success:
            self.stats['responses_given'] += 1
            self.stats['total_response_time'] += response_time
            if self.stats['responses_given'] > 0:
                self.stats['average_response_time'] = (
                        self.stats['total_response_time'] / self.stats['responses_given']
                )
        else:
            self.stats['timeouts'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive human client statistics."""
        total_attempts = self.stats['responses_given'] + self.stats['timeouts']
        participation_rate = (
            self.stats['responses_given'] / total_attempts
            if total_attempts > 0 else 0
        )

        return {
            'name': self.name,
            'interface_mode': self.interface.config.mode,
            'responses_given': self.stats['responses_given'],
            'timeouts': self.stats['timeouts'],
            'total_attempts': total_attempts,
            'participation_rate': participation_rate,
            'average_response_time': self.stats.get('average_response_time', 0),
            'is_active': self.is_active,
            'conversation_length': len(self.conversation_history)
        }

    async def set_active(self, active: bool):
        """Set the active status of the human client."""
        self.is_active = active
        status = "activated" if active else "deactivated"
        await self.interface.show_notification(
            f"🔄 {self.name} has been {status}",
            "info"
        )

    def __str__(self) -> str:
        return f"Human({self.name}, {self.interface.config.mode}, active={self.is_active})"

    def __repr__(self) -> str:
        return (f"HumanClient(name='{self.name}', mode='{self.interface.config.mode}', "
                f"active={self.is_active}, responses={self.stats['responses_given']})")

    @property
    def stance(self) -> str:
        return "neutral"  # Or dynamically assign based on your use case
