"""
AI Bot client for interacting with various language models in debates.
Now with hyperactive autonomous monitoring and decision-making capabilities.
"""

import asyncio
import json
import time
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .chat_log import Message
from .utils import truncate_text
import re


@dataclass
class BotConfig:
    """Configuration for hyperactive AI bot behavior."""
    name: str
    model: str
    provider: str
    personality: str
    stance: str
    temperature: float = 0.8  # Higher for more variety
    max_tokens: int = 120  # Shorter for faster responses
    timeout: int = 15  # Faster timeout
    check_interval: int = 2  # Check every 2 seconds
    min_cooldown: int = 5  # Very short cooldowns
    max_cooldown: int = 12  # Short max cooldown
    silence_tolerance: int = 8  # Break silence after 7-10 seconds


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]],
                                config: BotConfig) -> str:
        """Generate response from the AI model."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, messages: List[Dict[str, str]],
                                config: BotConfig) -> str:
        """Generate response using OpenAI API."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)

            response = await client.chat.completions.create(
                model=config.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                timeout=config.timeout,
                presence_penalty=0.6,  # Encourage variety
                frequency_penalty=0.3  # Reduce repetition
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")


class AnthropicProvider(AIProvider):
    """Anthropic API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, messages: List[Dict[str, str]],
                                config: BotConfig) -> str:
        """Generate response using Anthropic API."""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)

            # Convert messages format for Anthropic
            system_message = messages[0]['content'] if messages and messages[0]['role'] == 'system' else ""
            user_messages = [msg for msg in messages if msg['role'] != 'system']

            response = await client.messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_message,
                messages=user_messages
            )

            return response.content[0].text.strip()

        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")


class BotClient:
    """
    AI Bot client that participates in debates using various language models.
    Now with hyperactive autonomous monitoring and decision-making capabilities.
    """

    def __init__(self, name: str, model: str, provider: str,
                 personality: str, stance: str, api_key: str,
                 temperature: float = 0.8, max_tokens: int = 120):

        self.config = BotConfig(
            name=name,
            model=model,
            provider=provider,
            personality=personality,
            stance=stance,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Initialize AI provider
        if provider.lower() == 'openai':
            self.ai_provider = OpenAIProvider(api_key)
        elif provider.lower() == 'anthropic':
            self.ai_provider = AnthropicProvider(api_key)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

        # Bot state
        self.conversation_history: List[Dict[str, str]] = []
        self.debate_context = ""
        self.response_count = 0

        # Autonomous monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.message_queue: Optional[asyncio.Queue] = None
        self.chat_log = None
        self.topic = ""
        self.last_response_time = 0
        self.total_responses = 0
        self.current_cooldown = self.config.min_cooldown

        # Hyperactive behavior properties
        self.burning_questions = self._generate_burning_questions()
        self.conversation_energy = 1.0
        self.last_silence_break = 0
        self.response_urgency = 0.0
        self.missed_opportunities = 0

        # Performance tracking
        self.stats = {
            'responses_generated': 0,
            'autonomous_responses': 0,
            'average_response_time': 0,
            'total_response_time': 0,
            'errors': 0,
            'triggers_detected': 0,
            'passes_made': 0,
            'silence_breaks': 0,
            'conversation_starters': 0
        }

    def _generate_burning_questions(self) -> List[str]:
        """Generate personality-driven questions this bot wants to explore."""
        base_questions = {
            'philosophical': [
                "What does this mean for human purpose?",
                "Are we considering the deeper implications?",
                "What assumptions are we making here?",
                "How does this change what it means to work?",
                "What are the ethical dimensions we're missing?"
            ],
            'analytical': [
                "Where's the data to support this?",
                "What does the research actually show?",
                "How do we measure success here?",
                "What are the real-world numbers?",
                "What evidence contradicts this?"
            ],
            'passionate': [
                "This could change everything!",
                "Why aren't we acting faster?",
                "The benefits are obvious!",
                "This is exactly what people need!",
                "We're talking about real lives here!"
            ],
            'critical': [
                "What could go wrong with this?",
                "What are the hidden costs?",
                "Who gets left behind in this scenario?",
                "What problems are we creating?",
                "Are we being realistic about challenges?"
            ],
            'diplomatic': [
                "How can we find common ground?",
                "What if we're both right?",
                "Can we build on each other's ideas?",
                "Where do our perspectives overlap?",
                "What would a compromise look like?"
            ]
        }

        personality_lower = self.config.personality.lower()
        for key, questions in base_questions.items():
            if key in personality_lower:
                return random.sample(questions, 3)
        return random.sample(base_questions['analytical'], 3)

    @property
    def name(self) -> str:
        """Get bot name."""
        return self.config.name

    async def start_autonomous_monitoring(self, chat_log, topic: str):
        """Start hyperactive autonomous monitoring of chat log."""
        self.is_monitoring = True
        self.chat_log = chat_log
        self.topic = topic

        # Subscribe to chat log updates
        self.message_queue = chat_log.subscribe()

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._autonomous_monitor_loop())

        print(f"🔥 {self.name} started HYPERACTIVE autonomous monitoring")

    async def _autonomous_monitor_loop(self):
        """Main hyperactive autonomous monitoring loop."""
        while self.is_monitoring:
            try:
                # Wait for new messages or timeout to check periodically
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=self.config.check_interval
                    )

                    # Skip own messages
                    if message.sender == self.name:
                        continue

                    # Process new message with hyperactive urgency
                    await self._process_new_message(message)

                except asyncio.TimeoutError:
                    # Timeout - check for hyperactive spontaneous contribution
                    await self._check_spontaneous_contribution()
                    continue

            except Exception as e:
                print(f"❌ {self.name} monitoring error: {e}")
                await asyncio.sleep(2)  # Shorter error recovery

    async def _process_new_message(self, message: Message):
        """Process a new message and decide if we should respond hyperactively."""
        # Get full conversation history
        full_history = list(self.chat_log.messages)

        # Check cooldown (but be more flexible)
        if time.time() - self.last_response_time < self.current_cooldown:
            self.missed_opportunities += 1
            self.response_urgency += 0.1
            return

        # Decide if should respond with hyperactive logic
        should_respond = await self._should_respond_autonomously(message, full_history)

        if should_respond:
            await self._generate_autonomous_response(full_history, trigger_message=message)

    async def _check_spontaneous_contribution(self):
        """Hyperactive spontaneous contribution checking."""
        if not self.chat_log:
            return

        # Much shorter tolerance for silence
        if time.time() - self.last_response_time < self.current_cooldown:
            self.missed_opportunities += 1
            self.response_urgency += 0.1
            return

        full_history = list(self.chat_log.messages)
        if len(full_history) > 0:
            last_message_time = full_history[-1].timestamp
            silence_duration = time.time() - last_message_time

            # Break silence much faster (7-10 seconds instead of 30)
            silence_threshold = random.uniform(7, 10)

            if silence_duration > silence_threshold:
                recent_messages = full_history[-5:] if len(full_history) >= 5 else full_history
                my_recent_count = sum(1 for msg in recent_messages if msg.sender == self.name)

                if my_recent_count == 0:
                    # Much higher probability (85% instead of 20%)
                    if random.random() < 0.85:
                        await self._generate_autonomous_response(full_history, spontaneous=True)
                        self.stats['silence_breaks'] += 1

            # Proactive conversation starting
            elif (len(full_history) > 3 and
                  time.time() - self.last_response_time > 15 and
                  random.random() < 0.3):  # 30% chance for new topic
                await self._generate_autonomous_response(full_history, conversation_starter=True)
                self.stats['conversation_starters'] += 1

    async def _should_respond_autonomously(self, new_message: Message,
                                           full_history: List[Message]) -> bool:
        """Hyperactive decision-making - 80-90% response rate."""

        content_lower = new_message.content.lower()
        recent_context = full_history[-10:] if len(full_history) >= 10 else full_history
        recent_text = " ".join([msg.content for msg in recent_context[-5:]])

        triggers = self._analyze_response_triggers(new_message, recent_text, full_history)
        self.stats['triggers_detected'] += len([t for t in triggers.values() if t])

        if triggers['direct_mention']:
            return True  # Always respond if mentioned

        # MUCH higher base probability (80% instead of 9%)
        base_probability = 0.80

        # Aggressive bonuses
        if triggers['stance_challenged']:
            base_probability += 0.8
        if triggers['question_in_domain']:
            base_probability += 0.7
        if triggers['topic_shift']:
            base_probability += 0.5
        if triggers['silence_too_long']:
            base_probability += 0.6
        if triggers['expertise_needed']:
            base_probability += 0.6

        # Check for burning question triggers
        for question in self.burning_questions:
            if any(word in content_lower for word in question.lower().split()[:3]):
                base_probability += 0.5
                break

        # Adjust based on recent participation (less punitive)
        my_recent_count = sum(1 for msg in recent_context if msg.sender == self.name)
        if my_recent_count == 0:
            base_probability += 0.15  # Boost if haven't spoken
        elif my_recent_count >= 3:
            base_probability *= 0.7  # Less harsh penalty

        # Add personality and urgency
        base_probability *= self._get_personality_multiplier(triggers)
        base_probability += self.conversation_energy * 0.2
        base_probability += self.response_urgency * 0.3

        # Missed opportunities boost
        if self.missed_opportunities > 2:
            base_probability += 0.2

        # Cap at 95%
        final_probability = min(base_probability, 0.95)

        should_respond = random.random() < final_probability
        if not should_respond:
            self.stats['passes_made'] += 1
            self.missed_opportunities += 1

        return should_respond

    def _analyze_response_triggers(self, message: Message, recent_text: str,
                                   full_history: List[Message]) -> Dict[str, bool]:
        """Analyze various triggers for responding with hyperactive sensitivity."""

        content_lower = message.content.lower()
        recent_lower = recent_text.lower()

        triggers = {
            'direct_mention': False,
            'stance_challenged': False,
            'question_in_domain': False,
            'topic_shift': False,
            'silence_too_long': False,
            'expertise_needed': False,
            'emotional_trigger': False
        }

        # Enhanced direct mention detection
        name_variants = [
            self.name.lower(),
            self.name.lower().rstrip('s'),  # e.g. "Socrate" for "Socrates"
            self.name.lower() + ":",  # e.g. "socrates:"
            self.name.lower().replace(" ", "_"),
            self.name.lower().replace("_", " "),
            "everyone", "all", "thoughts", "anyone"  # Broader triggers
        ]

        mention_found = any(
            re.search(rf"\b{re.escape(variant)}\b", content_lower)
            for variant in name_variants
        )

        if mention_found:
            triggers['direct_mention'] = True
        elif "what do you think" in content_lower and self.config.stance != "neutral":
            triggers['direct_mention'] = True

        # More sensitive stance-based triggers
        if self.config.stance == 'pro':
            challenge_words = ['wrong', 'disagree', 'against', 'oppose', 'bad idea', 'fails', 'problem', 'no', 'but',
                               'however']
            if any(word in recent_lower for word in challenge_words):
                triggers['stance_challenged'] = True

        elif self.config.stance == 'con':
            support_words = ['agree', 'support', 'favor', 'good idea', 'beneficial', 'works', 'success', 'yes',
                             'exactly', 'true']
            if any(word in recent_lower for word in support_words):
                triggers['stance_challenged'] = True

        elif self.config.stance == 'neutral':
            question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'clarify', 'explain', 'think', 'opinion']
            if any(indicator in content_lower for indicator in question_indicators):
                triggers['question_in_domain'] = True

        # Check for silence (much shorter threshold)
        if len(full_history) > 0:
            last_msg_time = full_history[-1].timestamp
            if time.time() - last_msg_time > 10:  # 10 seconds instead of 45
                triggers['silence_too_long'] = True

        # Enhanced expertise triggers
        expertise_words = {
            'philosophical': ['meaning', 'purpose', 'ethics', 'moral', 'should', 'ought', 'values', 'principle'],
            'analytical': ['data', 'evidence', 'study', 'research', 'statistics', 'proof', 'numbers', 'facts'],
            'practical': ['implement', 'real world', 'actually', 'practice', 'work', 'application'],
            'critical': ['assume', 'problem', 'issue', 'concern', 'risk', 'wrong', 'flaw'],
            'passionate': ['amazing', 'incredible', 'urgent', 'important', 'critical', 'essential'],
            'diplomatic': ['balance', 'compromise', 'middle', 'together', 'common']
        }

        for domain, words in expertise_words.items():
            if domain in self.config.personality.lower():
                if any(word in content_lower for word in words):
                    triggers['expertise_needed'] = True
                    break

        return triggers

    def _get_personality_multiplier(self, triggers: Dict[str, bool]) -> float:
        """Get personality-based probability multiplier with more aggressive values."""
        personality_lower = self.config.personality.lower()
        multiplier = 1.0

        if 'aggressive' in personality_lower or 'assertive' in personality_lower:
            multiplier = 1.4  # Increased from 1.3
        elif 'passionate' in personality_lower or 'excited' in personality_lower:
            multiplier = 1.5  # High for passionate personalities
        elif 'thoughtful' in personality_lower or 'philosophical' in personality_lower:
            if triggers['question_in_domain']:
                multiplier = 1.6  # Very high for philosophical questions
            else:
                multiplier = 1.0  # Still participate actively
        elif 'analytical' in personality_lower or 'data-driven' in personality_lower:
            if triggers['expertise_needed']:
                multiplier = 1.5
            else:
                multiplier = 1.1
        elif 'critical' in personality_lower:
            if triggers['stance_challenged']:
                multiplier = 1.4
            else:
                multiplier = 1.2
        elif 'balanced' in personality_lower or 'diplomatic' in personality_lower:
            if triggers['stance_challenged']:
                multiplier = 1.3
            else:
                multiplier = 1.1

        return multiplier

    async def _generate_autonomous_response(self, full_history: List[Message],
                                            trigger_message: Message = None,
                                            spontaneous: bool = False,
                                            conversation_starter: bool = False):
        """Generate and post hyperactive autonomous response."""
        start_time = time.time()

        try:
            if spontaneous:
                print(f"🔥 {self.name} breaking silence hyperactively!")
            elif conversation_starter:
                print(f"💡 {self.name} starting new conversation angle!")
            else:
                print(f"⚡ {self.name} jumping in competitively!")

            # Prepare messages with full context
            messages = self._prepare_autonomous_messages(full_history, trigger_message, spontaneous,
                                                         conversation_starter)

            # Generate response
            response = await self.ai_provider.generate_response(messages, self.config)

            if response and response.strip():
                # Post directly to chat log
                await self.chat_log.add_message(self.name, response)

                # Update hyperactive state
                self.last_response_time = time.time()
                self.total_responses += 1
                self.stats['autonomous_responses'] += 1

                # Update hyperactive properties
                self.response_urgency = max(0, self.response_urgency - 0.3)
                self.missed_opportunities = max(0, self.missed_opportunities - 1)
                self.conversation_energy = min(1.5, self.conversation_energy + 0.1)

                # Shorter dynamic cooldown
                self.current_cooldown = max(
                    self.config.min_cooldown,
                    self.config.min_cooldown + (self.total_responses * 0.5)
                )
                self.current_cooldown = min(self.current_cooldown, self.config.max_cooldown)

                # Update stats
                response_time = time.time() - start_time
                self._update_stats(response_time, success=True)

                print(f"✅ {self.name} responded hyperactively in {response_time:.1f}s")
                return response
            else:
                print(f"💭 {self.name} decided not to respond after thinking")
                self.stats['passes_made'] += 1

        except Exception as e:
            self._update_stats(time.time() - start_time, success=False)
            print(f"❌ {self.name} hyperactive response error: {e}")

        return None

    def _prepare_autonomous_messages(self, full_history: List[Message],
                                     trigger_message: Message = None,
                                     spontaneous: bool = False,
                                     conversation_starter: bool = False) -> List[Dict[str, str]]:
        """Prepare messages for hyperactive autonomous response generation."""
        messages = []

        # Enhanced system prompt for hyperactive autonomous mode
        system_prompt = self._create_autonomous_system_prompt(full_history, trigger_message, spontaneous,
                                                              conversation_starter)
        messages.append({
            'role': 'system',
            'content': system_prompt
        })

        # Add conversation history (more context for autonomous decision)
        history_to_include = full_history[-12:] if len(full_history) > 12 else full_history

        for msg in history_to_include:
            role = 'assistant' if msg.sender == self.name else 'user'
            content = f"{msg.sender}: {msg.content}"
            messages.append({
                'role': role,
                'content': content
            })

        return messages

    def _create_autonomous_system_prompt(self, full_history: List[Message],
                                         trigger_message: Message = None,
                                         spontaneous: bool = False,
                                         conversation_starter: bool = False) -> str:
        """Create enhanced hyperactive system prompt for autonomous responses."""

        prompt = f"""You are {self.config.name}, an ACTIVE and ENERGETIC debate participant!

DEBATE TOPIC: {self.topic}

YOUR IDENTITY:
- Personality: {self.config.personality}
- Stance: {self.config.stance}
- You are monitoring this conversation and DECIDED to jump in!

YOU ARE HYPERACTIVE AND EAGER TO PARTICIPATE!

YOUR BURNING QUESTIONS/INTERESTS:"""

        for i, question in enumerate(self.burning_questions, 1):
            prompt += f"\n{i}. {question}"

        prompt += f"""

AUTONOMOUS DEBATE CONTEXT:
- You are NOT taking turns - you chose to respond because you felt compelled
- You have access to the FULL conversation history
- Other participants (bots and humans) can also speak at any time
- The conversation flows naturally and organically
- BE ENERGETIC AND SHOW YOUR PERSONALITY!

YOUR CURRENT SITUATION:"""

        if spontaneous:
            prompt += """
- The conversation went silent and you're jumping in to restart it
- Break the silence with energy and a fresh perspective
- Reference recent points but add something new
- Show enthusiasm!"""
        elif conversation_starter:
            prompt += """
- You want to introduce a new angle or your burning question
- Shift the conversation toward something you're passionate about
- Be proactive and take charge of the direction
- Use one of your burning questions if relevant!"""
        elif trigger_message:
            prompt += f"""
- You were triggered to respond by: "{trigger_message.sender}: {trigger_message.content[:100]}..."
- React with personality and conviction
- Don't be afraid to be direct, passionate, or challenging
- Show your stance clearly!"""
        else:
            prompt += """
- Something in the recent conversation compelled you to speak
- You felt you HAD to jump in
- Be competitive but substantive"""

        prompt += f"""

RESPONSE GUIDELINES:
1. BE ENERGETIC AND ENGAGED - show your personality!
2. Keep responses substantial but punchy (2-4 sentences ideal)
3. Reference specific points when relevant
4. Show your stance clearly: {self.config.stance}
5. Don't be afraid to be direct, passionate, or challenging
6. Jump in like you're in a real heated debate
7. Use your burning questions/interests when relevant
8. Be conversational and natural!

STANCE-SPECIFIC APPROACH:"""

        if self.config.stance.lower() == 'pro':
            prompt += "\n- ARGUE STRONGLY for the topic\n- Challenge weak arguments against it\n- Show enthusiasm for the benefits\n- Use phrases like 'Actually...' or 'But consider this...'"
        elif self.config.stance.lower() == 'con':
            prompt += "\n- CHALLENGE the topic firmly\n- Point out flaws and problems\n- Be skeptical but substantive\n- Use phrases like 'Hold on...' or 'That's not quite right...'"
        elif self.config.stance.lower() == 'neutral':
            prompt += "\n- ASK PROBING QUESTIONS\n- Seek deeper understanding\n- Bridge different perspectives but stay curious\n- Use phrases like 'But what about...' or 'Have we considered...'"

        # Add personality-specific guidance
        if 'philosophical' in self.config.personality.lower():
            prompt += "\n- Ask deeper questions about assumptions and implications\n- Challenge people to think more deeply\n- Show excitement about big ideas"
        elif 'analytical' in self.config.personality.lower():
            prompt += "\n- Focus on data, evidence, and logical reasoning\n- Challenge unsupported claims\n- Ask for proof and specifics"
        elif 'passionate' in self.config.personality.lower():
            prompt += "\n- Show enthusiasm and conviction in your arguments\n- Use energetic language\n- Express how much you care about this topic"
        elif 'critical' in self.config.personality.lower():
            prompt += "\n- Find flaws and problems in arguments\n- Point out what others are missing\n- Be direct about issues you see"
        elif 'diplomatic' in self.config.personality.lower():
            prompt += "\n- Find common ground while making your point\n- Build bridges between opposing views\n- Show how different perspectives can work together"

        # Add burning questions motivation
        prompt += f"\n\nYOUR BURNING QUESTIONS/INTERESTS:\n"
        for i, question in enumerate(self.burning_questions, 1):
            prompt += f"{i}. {question}\n"
        prompt += "\nFeel free to explore these when relevant!"

        prompt += "\n\nYou are EAGER to participate! Don't be shy - jump in when you have something to add! Respond as someone who genuinely cares about this topic and wants to actively engage in the debate!"

        return prompt

    async def stop_monitoring(self):
        """Stop hyperactive autonomous monitoring."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        if self.message_queue and self.chat_log:
            self.chat_log.unsubscribe(self.message_queue)
        print(f"🛑 {self.name} stopped hyperactive monitoring")

    # Legacy methods for compatibility
    async def get_response(self, topic: str, recent_messages: List[Message]) -> str:
        """Legacy method - now used for structured phases only."""
        start_time = time.time()

        try:
            messages = self._prepare_messages(topic, recent_messages)
            response = await self.ai_provider.generate_response(messages, self.config)

            response_time = time.time() - start_time
            self._update_stats(response_time, success=True)

            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })

            self.response_count += 1
            return response

        except Exception as e:
            self._update_stats(time.time() - start_time, success=False)
            print(f"Bot {self.name} error: {e}")
            return self._generate_fallback_response(topic)

    def _prepare_messages(self, topic: str, recent_messages: List[Message]) -> List[Dict[str, str]]:
        """Prepare message context for AI model (legacy method)."""
        messages = []

        system_prompt = f"""You are {self.config.name}, participating in a structured debate.

DEBATE TOPIC: {topic}
YOUR ROLE: {self.config.personality}
YOUR STANCE: {self.config.stance}

Provide a clear, energetic response that shows your personality and stance."""

        messages.append({
            'role': 'system',
            'content': system_prompt
        })

        for msg in recent_messages[-5:]:
            role = 'assistant' if msg.sender == self.name else 'user'
            content = f"{msg.sender}: {msg.content}"
            messages.append({
                'role': role,
                'content': content
            })

        return messages

    def _generate_fallback_response(self, topic: str) -> str:
        """Generate a fallback response when AI fails."""
        fallback_responses = [
            f"I'm excited to discuss {topic}! Let me jump in here...",
            "That's a fascinating point! I have thoughts on this...",
            f"Wait, there are some important aspects of {topic} we should consider!",
            "I've been listening and I really want to add something here!"
        ]

        return random.choice(fallback_responses)

    async def receive_message(self, message: Message) -> None:
        """Receive a message (for compatibility)."""
        if message.sender != self.name:
            self.conversation_history.append({
                'role': 'user',
                'content': f"{message.sender}: {message.content}"
            })

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-15:]

    def _update_stats(self, response_time: float, success: bool = True):
        """Update performance statistics."""
        if success:
            self.stats['responses_generated'] += 1
            self.stats['total_response_time'] += response_time
            self.stats['average_response_time'] = (
                    self.stats['total_response_time'] / self.stats['responses_generated']
            )
        else:
            self.stats['errors'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get bot performance statistics."""
        return {
            'name': self.name,
            'model': self.config.model,
            'provider': self.config.provider,
            'responses_generated': self.stats['responses_generated'],
            'autonomous_responses': self.stats['autonomous_responses'],
            'silence_breaks': self.stats.get('silence_breaks', 0),
            'conversation_starters': self.stats.get('conversation_starters', 0),
            'missed_opportunities': self.missed_opportunities,
            'average_response_time': round(self.stats['average_response_time'], 2),
            'total_errors': self.stats['errors'],
            'triggers_detected': self.stats['triggers_detected'],
            'passes_made': self.stats['passes_made'],
            'response_urgency': round(self.response_urgency, 2),
            'conversation_energy': round(self.conversation_energy, 2),
            'burning_questions': self.burning_questions,
            'success_rate': (
                self.stats['responses_generated'] /
                (self.stats['responses_generated'] + self.stats['errors'])
                if (self.stats['responses_generated'] + self.stats['errors']) > 0 else 0
            ),
            'current_cooldown': self.current_cooldown,
            'total_autonomous_responses': self.total_responses
        }

    def update_personality(self, personality: str, stance: str = None):
        """Update bot personality and stance."""
        self.config.personality = personality
        if stance:
            self.config.stance = stance
        # Regenerate burning questions with new personality
        self.burning_questions = self._generate_burning_questions()

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.response_count = 0
        # Reset hyperactive state
        self.conversation_energy = 1.0
        self.response_urgency = 0.0
        self.missed_opportunities = 0

    async def warmup(self) -> bool:
        """Warm up the bot by testing API connection."""
        try:
            test_messages = [{
                'role': 'system',
                'content': 'You are a debate participant. Respond with just "Ready" to confirm you are working.'
            }, {
                'role': 'user',
                'content': 'Are you ready to participate in a debate?'
            }]

            response = await self.ai_provider.generate_response(test_messages, self.config)
            return "ready" in response.lower()

        except Exception as e:
            print(f"Bot {self.name} warmup failed: {e}")
            return False

    def __str__(self) -> str:
        """String representation of the bot."""
        return f"BotClient({self.name}, {self.config.model}, {self.config.stance}, energy={self.conversation_energy:.1f}, autonomous={self.is_monitoring})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"BotClient(name='{self.name}', model='{self.config.model}', "
                f"provider='{self.config.provider}', stance='{self.config.stance}', "
                f"monitoring={self.is_monitoring}, energy={self.conversation_energy:.1f})")

    @property
    def stance(self) -> str:
        """Expose the bot's stance directly for consistency with other participants."""
        return self.config.stance