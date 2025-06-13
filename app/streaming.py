"""
Live streaming and WebSocket server for real-time debate broadcasting.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol

from .chat_log import ChatLog, Message
from .voting import VotingSystem
from .utils import format_time_remaining


@dataclass
class StreamingClient:
    """Information about a connected streaming client."""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: float
    client_type: str = "viewer"  # viewer, participant, moderator
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamingServer:
    """
    WebSocket server for live streaming debate sessions.
    """

    def __init__(self, chat_log: ChatLog, voting_system: VotingSystem,
                 config: Dict[str, Any]):
        self.chat_log = chat_log
        self.voting_system = voting_system
        self.config = config

        self.host = config.get('host', 'localhost')
        self.port = config.get('websocket_port', 8080)
        self.max_connections = config.get('max_connections', 100)
        self.broadcast_votes = config.get('broadcast_votes', True)

        # Server state
        self.server = None
        self.clients: Dict[str, StreamingClient] = {}
        self.is_running = False

        # Message subscription
        self.message_queue = None
        self.broadcast_task = None

        # Statistics
        self.stats = {
            'total_connections': 0,
            'messages_sent': 0,
            'votes_broadcast': 0,
            'start_time': time.time()
        }

        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the streaming server."""
        if self.is_running:
            return

        try:
            # Subscribe to chat log messages
            self.message_queue = self.chat_log.subscribe()

            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                max_size=1024 * 1024,  # 1MB max message size
                ping_interval=20,
                ping_timeout=10
            )

            # Start broadcast task
            self.broadcast_task = asyncio.create_task(self._broadcast_loop())

            self.is_running = True
            self.logger.info(f"Streaming server started on {self.host}:{self.port}")

        except Exception as e:
            self.logger.error(f"Failed to start streaming server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the streaming server."""
        if not self.is_running:
            return

        self.is_running = False

        # Stop broadcast task
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.websocket.close() for client in self.clients.values()],
                return_exceptions=True
            )

        # Stop WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Unsubscribe from chat log
        if self.message_queue:
            self.chat_log.unsubscribe(self.message_queue)

        self.logger.info("Streaming server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection."""
        if len(self.clients) >= self.max_connections:
            await websocket.close(code=1013, reason="Server full")
            return

        client_id = f"client_{int(time.time() * 1000)}"
        client = StreamingClient(
            websocket=websocket,
            client_id=client_id,
            connected_at=time.time()
        )

        self.clients[client_id] = client
        self.stats['total_connections'] += 1

        self.logger.info(f"Client {client_id} connected from {websocket.remote_address}")

        try:
            # Send welcome message
            await self._send_to_client(client, {
                'type': 'welcome',
                'client_id': client_id,
                'server_info': {
                    'version': '1.0.0',
                    'features': ['chat', 'voting', 'real_time']
                }
            })

            # Send recent messages
            recent_messages = self.chat_log.get_recent_messages(10)
            for msg in recent_messages:
                await self._send_to_client(client, {
                    'type': 'message',
                    'data': msg.to_dict()
                })

            # Handle client messages
            async for message in websocket:
                try:
                    await self._process_client_message(client, json.loads(message))
                except json.JSONDecodeError:
                    await self._send_error(client, "Invalid JSON message")
                except Exception as e:
                    self.logger.error(f"Error processing client message: {e}")
                    await self._send_error(client, "Internal server error")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            self.logger.error(f"Client {client_id} error: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]

    async def _process_client_message(self, client: StreamingClient, data: Dict[str, Any]):
        """Process message from client."""
        message_type = data.get('type')

        if message_type == 'ping':
            await self._send_to_client(client, {'type': 'pong'})

        elif message_type == 'subscribe':
            # Update client subscription preferences
            client.metadata['subscriptions'] = data.get('channels', [])
            await self._send_to_client(client, {
                'type': 'subscribed',
                'channels': client.metadata.get('subscriptions', [])
            })

        elif message_type == 'get_stats':
            # Send server statistics
            await self._send_to_client(client, {
                'type': 'stats',
                'data': self._get_server_stats()
            })

        elif message_type == 'vote' and self.voting_system.is_active:
            # Handle vote from client
            voter_id = data.get('voter_id', client.client_id)
            candidate = data.get('candidate')
            justification = data.get('justification')

            try:
                success = await self.voting_system.cast_vote(
                    voter_id, candidate, justification
                )

                await self._send_to_client(client, {
                    'type': 'vote_result',
                    'success': success,
                    'candidate': candidate
                })

                if success and self.broadcast_votes:
                    await self._broadcast_vote_update()

            except Exception as e:
                await self._send_error(client, f"Vote failed: {e}")

        else:
            await self._send_error(client, f"Unknown message type: {message_type}")

    async def _broadcast_loop(self):
        """Main broadcast loop for new messages."""
        try:
            while self.is_running:
                try:
                    # Wait for new message from chat log
                    message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )

                    # Broadcast to all clients
                    await self._broadcast_message(message)

                except asyncio.TimeoutError:
                    # Timeout is expected, continue loop
                    continue
                except Exception as e:
                    self.logger.error(f"Broadcast loop error: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.logger.info("Broadcast loop cancelled")

    async def _broadcast_message(self, message: Message):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return

        broadcast_data = {
            'type': 'message',
            'data': message.to_dict()
        }

        # Send to all clients
        tasks = []
        for client in list(self.clients.values()):
            if self._should_send_to_client(client, message):
                tasks.append(self._send_to_client(client, broadcast_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.stats['messages_sent'] += len(tasks)

    def _should_send_to_client(self, client: StreamingClient, message: Message) -> bool:
        """Determine if message should be sent to client."""
        # Check client subscriptions
        subscriptions = client.metadata.get('subscriptions', [])

        if subscriptions:
            # If client has specific subscriptions, check them
            if message.message_type not in subscriptions:
                return False

        return True

    async def _broadcast_vote_update(self):
        """Broadcast voting update to clients."""
        if not self.voting_system.is_active:
            return

        vote_summary = self.voting_system.get_vote_summary()

        broadcast_data = {
            'type': 'vote_update',
            'data': vote_summary
        }

        tasks = []
        for client in list(self.clients.values()):
            tasks.append(self._send_to_client(client, broadcast_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.stats['votes_broadcast'] += 1

    async def _send_to_client(self, client: StreamingClient, data: Dict[str, Any]):
        """Send data to specific client."""
        try:
            await client.websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            # Client disconnected, will be cleaned up
            pass
        except Exception as e:
            self.logger.error(f"Failed to send to client {client.client_id}: {e}")

    async def _send_error(self, client: StreamingClient, error_message: str):
        """Send error message to client."""
        await self._send_to_client(client, {
            'type': 'error',
            'message': error_message
        })

    def _get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        uptime = time.time() - self.stats['start_time']

        return {
            'connected_clients': len(self.clients),
            'total_connections': self.stats['total_connections'],
            'messages_sent': self.stats['messages_sent'],
            'votes_broadcast': self.stats['votes_broadcast'],
            'uptime_seconds': uptime,
            'uptime_formatted': format_time_remaining(uptime),
            'is_voting_active': self.voting_system.is_active if self.voting_system else False
        }

    async def broadcast_custom_message(self, message_type: str, data: Any):
        """Broadcast custom message to all clients."""
        broadcast_data = {
            'type': message_type,
            'data': data,
            'timestamp': time.time()
        }

        tasks = []
        for client in list(self.clients.values()):
            tasks.append(self._send_to_client(client, broadcast_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_specific_clients(self, client_ids: List[str],
                                       message_type: str, data: Any):
        """Send message to specific clients."""
        message = {
            'type': message_type,
            'data': data,
            'timestamp': time.time()
        }

        tasks = []
        for client_id in client_ids:
            if client_id in self.clients:
                client = self.clients[client_id]
                tasks.append(self._send_to_client(client, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get information about connected clients."""
        return [
            {
                'client_id': client.client_id,
                'connected_at': client.connected_at,
                'client_type': client.client_type,
                'connection_duration': time.time() - client.connected_at
            }
            for client in self.clients.values()
        ]

    @property
    def is_active(self) -> bool:
        """Check if server is running."""
        return self.is_running

    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)


class StreamingManager:
    """
    High-level manager for streaming functionality.
    """

    def __init__(self):
        self.servers: Dict[str, StreamingServer] = {}
        self.is_initialized = False

    async def create_streaming_session(self, session_id: str, chat_log: ChatLog,
                                       voting_system: VotingSystem,
                                       config: Dict[str, Any]) -> StreamingServer:
        """
        Create a new streaming session.

        Args:
            session_id: Unique session identifier
            chat_log: Chat log to stream
            voting_system: Voting system to integrate
            config: Streaming configuration

        Returns:
            StreamingServer instance
        """
        if session_id in self.servers:
            raise ValueError(f"Streaming session {session_id} already exists")

        # Create unique port for this session
        base_port = config.get('websocket_port', 8080)
        port = base_port + len(self.servers)

        session_config = config.copy()
        session_config['websocket_port'] = port

        server = StreamingServer(chat_log, voting_system, session_config)
        self.servers[session_id] = server

        await server.start()
        return server

    async def stop_streaming_session(self, session_id: str):
        """Stop a streaming session."""
        if session_id in self.servers:
            server = self.servers[session_id]
            await server.stop()
            del self.servers[session_id]

    async def stop_all_sessions(self):
        """Stop all streaming sessions."""
        tasks = []
        for session_id in list(self.servers.keys()):
            tasks.append(self.stop_streaming_session(session_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a streaming session."""
        if session_id not in self.servers:
            return None

        server = self.servers[session_id]
        return {
            'session_id': session_id,
            'is_active': server.is_active,
            'client_count': server.client_count,
            'host': server.host,
            'port': server.port,
            'stats': server._get_server_stats()
        }

    def list_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return [
            session_id for session_id, server in self.servers.items()
            if server.is_active
        ]