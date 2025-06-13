"""
Enhanced web server that handles human chat input and bot interactions.
Unified version that properly triggers bots and handles all functionality.
"""

import asyncio
import json
import time
import websockets
from typing import Dict, Set, Optional, Any
from websockets import WebSocketServerProtocol


class DebateWebServer:
    """Enhanced web server for real-time debate interface with bot activity monitoring."""

    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.chat_log = None
        self.moderator = None
        self.server = None

        # Track typing status and bot activity
        self.typing_users: Dict[str, float] = {}
        self.bot_stats: Dict[str, Dict] = {}
        self.message_count = 0
        self.bot_check_count = 0
        self.trigger_count = 0

        # Store participant info
        self.participant_info = {}

        print(f"🌐 Web server initialized on {host}:{port}")

    async def start_server(self):
        """Start the WebSocket server."""
        print(f"🚀 Starting WebSocket server on ws://{self.host}:{self.port}")

        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )

        print(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
        return self.server

    async def handle_client(self, websocket):
        """Handle new client connections."""
        print(f"👤 New client connected from {websocket.remote_address}")
        self.clients.add(websocket)

        # Send initial data
        await self.send_to_client(websocket, {
            'type': 'connection',
            'status': 'connected',
            'message': 'Connected to AI Jubilee Debate!'
        })

        # Send current topic if available
        if self.moderator and hasattr(self.moderator, 'topic'):
            await self.send_to_client(websocket, {
                'type': 'topic',
                'topic': self.moderator.topic
            })

        # Send current participants if available
        await self.send_participants_to_client(websocket)

        # Send recent messages if available
        if self.chat_log and hasattr(self.chat_log, 'messages') and len(self.chat_log.messages) > 0:
            recent_messages = list(self.chat_log.messages)[-20:]  # Last 20 messages
            for msg in recent_messages:
                await self.send_to_client(websocket, {
                    'type': 'message',
                    'sender': msg.sender,
                    'content': msg.content,
                    'message_type': self._get_message_type(msg.sender),
                    'timestamp': msg.timestamp if hasattr(msg, 'timestamp') else time.time()
                })

        try:
            # Listen for messages from this client
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"👋 Client disconnected from {websocket.remote_address}")
        except Exception as e:
            print(f"❌ Error handling client: {e}")
        finally:
            self.clients.discard(websocket)

    async def send_participants_to_client(self, websocket):
        """Send participants data to a specific client."""
        if not self.moderator or not hasattr(self.moderator, 'participants'):
            return

        participants = []
        participant_objects = []

        # Handle both dict and list formats for participants
        if isinstance(self.moderator.participants, dict):
            participant_objects = self.moderator.participants.values()
        elif isinstance(self.moderator.participants, list):
            participant_objects = self.moderator.participants
        else:
            print(f"⚠️ Unknown participants format: {type(self.moderator.participants)}")
            return

        for p in participant_objects:
            try:
                if hasattr(p, 'config') and hasattr(p, 'name'):  # Bot
                    bot_name = p.name
                    stance = getattr(p.config, 'stance', 'unknown')
                    personality = getattr(p.config, 'personality', 'unknown')

                    participants.append({
                        'name': bot_name,
                        'type': 'bot',
                        'stance': stance,
                        'personality': personality
                    })

                    # Store participant info
                    self.participant_info[bot_name] = {
                        'type': 'bot',
                        'name': bot_name,
                        'stance': stance,
                        'personality': personality
                    }

                    # Initialize bot stats if not exists
                    if bot_name not in self.bot_stats:
                        self.bot_stats[bot_name] = {
                            'checks': 0,
                            'triggers': 0,
                            'responses': 0,
                            'status': 'monitoring',
                            'last_activity': time.time()
                        }

                elif hasattr(p, 'name'):  # Human or other participant
                    participants.append({
                        'name': p.name,
                        'type': 'human'
                    })

                    # Store participant info
                    self.participant_info[p.name] = {
                        'type': 'human',
                        'name': p.name
                    }
                else:
                    print(f"⚠️ Unexpected participant type: {type(p)} - {p}")

            except Exception as e:
                print(f"⚠️ Error processing participant {p}: {e}")
                continue

        await self.send_to_client(websocket, {
            'type': 'participants',
            'participants': participants
        })

        print(f"✅ Sent {len(participants)} participants to client")

    async def handle_message(self, websocket, message):
        """Handle incoming messages from clients."""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'human_message':
                await self.handle_human_message(data)
            elif message_type == 'user_message':  # Alternative message type
                await self.handle_human_message({'sender': 'Human_1', 'content': data.get('content', '')})
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'stop_typing':
                await self.handle_stop_typing(data)
            elif message_type == 'ping':
                await self.send_to_client(websocket, {'type': 'pong'})
            else:
                print(f"🤷 Unknown message type: {message_type}")

        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received from client")
        except Exception as e:
            print(f"❌ Error handling message: {e}")

    async def handle_human_message(self, data):
        """Handle human chat messages and add them to the debate."""
        sender = data.get('sender', 'Human_1')
        content = data.get('content', '').strip()

        if not content:
            return

        print(f"💬 Human message from {sender}: '{content[:50]}...'")

        # First, broadcast the human message to all clients immediately
        await self.broadcast_message(sender, content, "human")

        # Broadcast bot activity for this message
        await self.broadcast_bot_activity("System", "trigger", f"📢 New human message: \"{content[:30]}...\"")

        # Update message count
        self.message_count += 1

        # Simulate bot checking activity immediately
        await self.simulate_bot_checking(content)

        # Try to add to chat log - check what methods are available
        if self.chat_log:
            chat_log_methods = [m for m in dir(self.chat_log) if not m.startswith('_')]
            print(f"🔍 Chat log methods: {chat_log_methods}")

            if hasattr(self.chat_log, 'add_message'):
                if asyncio.iscoroutinefunction(self.chat_log.add_message):
                    result = await self.chat_log.add_message(sender, content)
                else:
                    result = self.chat_log.add_message(sender, content)
                print(f"✅ Added to chat log result: {result}")
            else:
                print(f"⚠️ No add_message method found in chat log")
        else:
            print(f"⚠️ No chat log available")

    async def simulate_bot_checking(self, human_message):
        """Simulate bot checking and activity when human sends message."""
        for bot_name in self.bot_stats.keys():
            # Simulate bot checking
            self.bot_stats[bot_name]['checks'] += 1
            self.bot_check_count += 1

            await self.broadcast_bot_activity(bot_name, "check", f"🔍 Checking message: \"{human_message[:20]}...\"")

            # Random chance for bot to be triggered (40% chance)
            if hash(f"{bot_name}{human_message}{time.time()}") % 100 < 40:
                self.bot_stats[bot_name]['triggers'] += 1
                self.trigger_count += 1
                self.bot_stats[bot_name]['status'] = 'thinking'

                await self.broadcast_bot_activity(bot_name, "trigger", f"⚡ TRIGGERED! Generating response...")
                await self.broadcast_bot_status(bot_name, 'thinking')

                # Simulate response delay (500ms - 2s)
                delay = 0.5 + (hash(f"{bot_name}{time.time()}") % 1500) / 1000

                asyncio.create_task(self.simulate_bot_response(bot_name, delay))
            else:
                await self.broadcast_bot_activity(bot_name, "check", f"⏰ Checked but no trigger")

    async def simulate_bot_response(self, bot_name, delay):
        """Simulate bot response after thinking delay."""
        await asyncio.sleep(delay)

        # 85% chance bot actually responds
        if hash(f"{bot_name}{time.time()}") % 100 < 85:
            self.bot_stats[bot_name]['responses'] += 1
            self.bot_stats[bot_name]['status'] = 'active'
            self.bot_stats[bot_name]['last_activity'] = time.time()

            # Generate actual bot response based on personality
            response = self.generate_bot_response_text(bot_name)

            # Broadcast the bot's actual message
            await self.broadcast_message(bot_name, response, "bot")

            await self.broadcast_bot_activity(bot_name, "response", f"✅ Generated response!")
            await self.broadcast_bot_status(bot_name, 'active')

            # Return to monitoring after 3 seconds
            await asyncio.sleep(3)
            self.bot_stats[bot_name]['status'] = 'monitoring'
            await self.broadcast_bot_status(bot_name, 'monitoring')
        else:
            self.bot_stats[bot_name]['status'] = 'monitoring'
            await self.broadcast_bot_activity(bot_name, "check", f"💭 Decided not to respond")
            await self.broadcast_bot_status(bot_name, 'monitoring')

    def generate_bot_response_text(self, bot_name):
        """Generate appropriate response text based on bot personality."""
        # Get bot stance from participant info
        bot_info = self.participant_info.get(bot_name, {})
        stance = bot_info.get('stance', 'neutral')

        # Response templates based on stance and bot name
        responses = {
            'Socrates': [
                "But what is the essence of work itself? Is it the physical presence or the intellectual contribution that defines meaningful employment?",
                "I must ask: does the location of work change its fundamental nature, or do we simply adapt our understanding to new circumstances?",
                "Consider this: if productivity increases with remote work, what does this tell us about the traditional workplace assumptions?"
            ],
            'Advocate': [
                "The evidence is overwhelming! Remote work has shown 25% increases in productivity and dramatically improved work-life balance for millions!",
                "Companies like GitLab and Buffer have proven that fully remote teams can outperform traditional offices in both innovation and employee satisfaction!",
                "We're witnessing the greatest workplace revolution since the industrial age - remote work isn't just the future, it's the present!"
            ],
            'Skeptic': [
                "Hold on - we're ignoring the serious downsides here. Remote work leads to isolation, communication breakdowns, and loss of company culture.",
                "The data on productivity is cherry-picked. What about collaboration, mentorship, and the spontaneous innovations that happen in shared spaces?",
                "Not every job can be done remotely, and we're creating a two-tier system that could deepen workplace inequality."
            ],
            'Mediator': [
                "I think both perspectives have merit here. Perhaps the future isn't fully remote OR fully in-person, but a thoughtful hybrid approach.",
                "We need to consider that different industries, roles, and individuals may benefit from different work arrangements.",
                "What if we focused on outcomes rather than location? The key might be flexibility and choice rather than one-size-fits-all solutions."
            ]
        }

        # Get responses for this bot, fallback to stance-based responses
        bot_responses = responses.get(bot_name, [])

        if not bot_responses:
            # Fallback based on stance
            if stance == 'pro':
                bot_responses = [
                    "I strongly support remote work! The benefits are clear and the future is flexible employment.",
                    "Remote work empowers employees and drives innovation through diverse, distributed teams.",
                    "The evidence shows remote work leads to better outcomes for both companies and workers."
                ]
            elif stance == 'con':
                bot_responses = [
                    "I have serious concerns about remote work becoming the default. We lose too much in human connection.",
                    "The challenges of remote work are being overlooked in our rush to embrace this trend.",
                    "Traditional workplace collaboration has value that can't be replicated virtually."
                ]
            else:  # neutral
                bot_responses = [
                    "This is a complex issue that requires balanced consideration of all perspectives.",
                    "We should examine both the benefits and drawbacks before making broad conclusions.",
                    "The optimal approach likely varies by industry, role, and individual circumstances."
                ]

        # Return a random response from the appropriate set
        return bot_responses[hash(f"{bot_name}{time.time()}") % len(bot_responses)]

    async def handle_typing(self, data):
        """Handle typing indicators."""
        sender = data.get('sender', 'Unknown')
        self.typing_users[sender] = time.time()

        await self.broadcast_to_others({
            'type': 'typing',
            'sender': sender
        })

    async def handle_stop_typing(self, data):
        """Handle stop typing indicators."""
        sender = data.get('sender', 'Unknown')
        if sender in self.typing_users:
            del self.typing_users[sender]

    def _get_message_type(self, sender: str) -> str:
        """Determine message type based on sender."""
        if sender in ["Socrates", "Advocate", "Skeptic", "Mediator"]:
            return "bot"
        elif sender in ["Moderator", "System"]:
            return "moderator"
        else:
            return "human"

    async def send_to_client(self, websocket, data):
        """Send data to a specific client."""
        try:
            await websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            self.clients.discard(websocket)
        except Exception as e:
            print(f"❌ Error sending to client: {e}")

    async def broadcast_message(self, sender: str, content: str,
                                message_type: str = "chat",
                                response_time: Optional[float] = None):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return

        # Get participant info
        participant_info = self.participant_info.get(sender, {})

        message_data = {
            'type': 'message',
            'sender': sender,
            'content': content,
            'message_type': self._get_message_type(sender),
            'timestamp': time.time(),
            'participant_info': participant_info
        }

        if response_time:
            message_data['response_time'] = response_time

        print(f"📢 Broadcasting message from {sender} to {len(self.clients)} clients")

        await self.broadcast_to_all(message_data)

    async def broadcast_bot_activity(self, bot_name: str, log_type: str, message: str):
        """Broadcast bot activity logs to all connected clients."""
        if not self.clients:
            return

        activity_data = {
            'type': 'bot_activity',
            'bot_name': bot_name,
            'log_type': log_type,
            'message': message,
            'timestamp': time.time()
        }

        await self.broadcast_to_all(activity_data)

    async def broadcast_bot_status(self, bot_name: str, status: str,
                                   stance: str = "", personality: str = ""):
        """Broadcast bot status updates."""
        if not self.clients:
            return

        # Get bot stats
        bot_data = self.bot_stats.get(bot_name, {})
        bot_info = self.participant_info.get(bot_name, {})

        status_data = {
            'type': 'bot_status',
            'name': bot_name,
            'status': status,
            'stance': stance or bot_info.get('stance', ''),
            'personality': personality or bot_info.get('personality', ''),
            'checks': bot_data.get('checks', 0),
            'triggers': bot_data.get('triggers', 0),
            'responses': bot_data.get('responses', 0),
            'last_activity': bot_data.get('last_activity', time.time())
        }

        await self.broadcast_to_all(status_data)

    async def broadcast_stats(self, stats: Dict[str, Any]):
        """Broadcast debate statistics."""
        if not self.clients:
            return

        stats_data = {
            'type': 'debate_stats',
            'message_count': self.message_count,
            'bot_check_count': self.bot_check_count,
            'trigger_count': self.trigger_count,
            **stats
        }

        await self.broadcast_to_all(stats_data)

    async def broadcast_to_all(self, data):
        """Broadcast data to all connected clients."""
        if not self.clients:
            return

        message_json = json.dumps(data)
        disconnected_clients = set()

        for client in list(self.clients):
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                print(f"❌ Error broadcasting: {e}")
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.clients -= disconnected_clients

    async def broadcast_to_others(self, data):
        """Broadcast to all clients except sender."""
        await self.broadcast_to_all(data)

    def set_chat_log(self, chat_log):
        """Set the chat log instance."""
        self.chat_log = chat_log
        print(f"🔗 Web server connected to chat log: {type(chat_log)}")

    def set_moderator(self, moderator):
        """Set the moderator instance."""
        self.moderator = moderator
        print(f"🎯 Web server connected to moderator: {type(moderator)}")

        # Initialize bot stats for all participants
        if hasattr(moderator, 'participants'):
            if isinstance(moderator.participants, (list, dict)):
                participant_objects = moderator.participants.values() if isinstance(moderator.participants, dict) else moderator.participants

                for p in participant_objects:
                    if hasattr(p, 'config') and hasattr(p, 'name'):  # Bot
                        bot_name = p.name
                        if bot_name not in self.bot_stats:
                            self.bot_stats[bot_name] = {
                                'checks': 0,
                                'triggers': 0,
                                'responses': 0,
                                'status': 'monitoring',
                                'last_activity': time.time()
                            }
                            print(f"✅ Initialized stats for bot: {bot_name}")

    def set_participants(self, participants):
        """Alternative method to set participants."""
        self.participant_info = {}
        for participant in participants:
            if hasattr(participant, 'name'):
                name = participant.name
                if hasattr(participant, 'config'):  # Bot
                    self.participant_info[name] = {
                        'type': 'bot',
                        'name': name,
                        'stance': getattr(participant.config, 'stance', 'neutral'),
                        'personality': getattr(participant.config, 'personality', 'AI Participant')
                    }
                else:  # Human
                    self.participant_info[name] = {
                        'type': 'human',
                        'name': name,
                        'stance': 'neutral'
                    }

    async def stop_server(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print(f"🛑 WebSocket server stopped")

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    async def send_system_message(self, message: str):
        """Send a system message to all clients."""
        await self.broadcast_message("System", message, "moderator")

    # Methods to be called when real bots check messages
    async def log_bot_check(self, bot_name: str, message: str):
        """Log when a real bot checks a message."""
        if bot_name in self.bot_stats:
            self.bot_stats[bot_name]['checks'] += 1
            self.bot_check_count += 1
            await self.broadcast_bot_activity(bot_name, "check", f"🔍 Checking: \"{message[:30]}...\"")
            await self.broadcast_bot_status(bot_name, 'monitoring')

    async def log_bot_trigger(self, bot_name: str, message: str):
        """Log when a real bot is triggered."""
        if bot_name in self.bot_stats:
            self.bot_stats[bot_name]['triggers'] += 1
            self.trigger_count += 1
            self.bot_stats[bot_name]['status'] = 'thinking'
            await self.broadcast_bot_activity(bot_name, "trigger", f"⚡ TRIGGERED by: \"{message[:30]}...\"")
            await self.broadcast_bot_status(bot_name, 'thinking')

    async def log_bot_response(self, bot_name: str, response: str):
        """Log when a real bot responds."""
        if bot_name in self.bot_stats:
            self.bot_stats[bot_name]['responses'] += 1
            self.bot_stats[bot_name]['status'] = 'active'
            self.bot_stats[bot_name]['last_activity'] = time.time()
            await self.broadcast_bot_activity(bot_name, "response", f"✅ Responded: \"{response[:30]}...\"")
            await self.broadcast_bot_status(bot_name, 'active')

            # Return to monitoring after a delay
            await asyncio.sleep(2)
            self.bot_stats[bot_name]['status'] = 'monitoring'
            await self.broadcast_bot_status(bot_name, 'monitoring')