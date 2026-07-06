import asyncio
import random
import traceback
import uuid

from src.conversation_managers.base_conversation_manager import BaseConversationManager
from src.logging import logging

manager_slug = "wow_conversation_manager"
valid_games = ["wow"]


class WoWCharacter:
    """Minimal stand-in character for WoW's continuous pet/companion model.

    Pantella's inference engine expects a character object with .name and .say().
    For WoW the companion is synthesized from live game state, so this class wraps
    the current pet/mount/companion and drives the synthesizer/overlay directly.
    """

    def __init__(self, name, conversation_manager):
        self.name = name
        self.conversation_manager = conversation_manager
        self.bio = ""
        self.voice_model = "default"
        self.voice_folder = "default"
        self.is_in_combat = 0

    async def say(self, text):
        """Speak a line via TTS (if voices are available) and update the overlay."""
        if not text or not text.strip():
            return
        text = text.strip()
        self.conversation_manager.game_interface._update_overlay(text, "yellow")
        logging.info(f"{self.name}: {text}")
        try:
            voices = self.conversation_manager.synthesizer.voices()
            if voices:
                self.conversation_manager.synthesizer._say(text, random.choice(voices))
        except Exception as e:
            logging.warning(f"WoW: TTS skipped for line '{text[:60]}...': {e}")

    def leave_conversation(self):
        return asyncio.sleep(0)

    def add_message(self, msg):
        pass

    def forget_last_message(self):
        pass

    def after_step(self):
        pass

    def before_step(self):
        pass

    def reached_conversation_limit(self):
        pass

    def get_perspective_player_identity(self):
        return (self.conversation_manager.player_name or "Adventurer", "friend")

    @property
    def language(self):
        return self.conversation_manager.character_manager.language

    @property
    def prompt_style(self):
        return self.conversation_manager.character_manager.prompt_style

    @property
    def replacement_dict(self):
        return {"name": self.name, "bio": self.bio, "player_name": self.conversation_manager.player_name}

    @property
    def memory_manager(self):
        return self

    @property
    def memories(self):
        return []

    @property
    def memory_offset(self):
        return 0

    @property
    def memory_offset_direction(self):
        return "topdown"


class WowConversationManager(BaseConversationManager):
    def __init__(self, config, initialize=True):
        super().__init__(config, initialize)
        self.radiant_dialogue = False
        self.current_location = "Azeroth"
        self.player_name = "Adventurer"
        self.player_race = None
        self.player_gender = None

        if hasattr(self, "inference_engine") and self.inference_engine is not None:
            self.inference_engine.get_messages = self._get_wow_messages
            logging.info("WoW: Patched inference_engine.get_messages")

    def _get_wow_messages(self):
        system_prompt = self.game_interface.get_system_prompt()
        msgs = [{"role": "system", "content": system_prompt, "type": "prompt"}]
        msgs.extend(self.messages)
        return msgs

    async def update_game_state(self):
        self.game_interface.load_game_state()
        state = getattr(self.game_interface, "game_state", {})

        if state.get("player_name"):
            self.player_name = state["player_name"]
        if state.get("zone"):
            self.current_location = state["zone"]

        self.conversation_ended = False

    async def await_and_setup_conversation(self):
        self.conversation_id = str(uuid.uuid4())
        self.conversation_step += 1

        state = self.game_interface.load_game_state()
        pet = state.get("pet", {})
        pet_name = pet.get("name", "Companion")
        pet_family = pet.get("family", "Unknown")
        pet_token = pet.get("pet_token", "UNKNOWN")

        logging.info(f"WoW: Conversation starting with {pet_name} ({pet_family}, token={pet_token})")

        self.messages = []
        self.tokens_available = getattr(self.config, "maximum_local_tokens", 4096)
        logging.info(f"Tokens Available: {self.tokens_available}")

        self.character = WoWCharacter(pet_name, self)
        self.game_interface.setup_character(self.character)

        self.in_conversation = True
        self.conversation_ended = False

        self.game_interface._update_overlay(f"{pet_name} is here.", "green")
        self.game_interface._update_overlay_title(f"Pantella - {pet_name}")

    async def step(self):
        self.conversation_step += 1
        logging.info(f"WoW: Step {self.conversation_step}")

        await self.update_game_state()

        if self.conversation_ended:
            return

        if hasattr(self.game_interface, "radiant_queue") and self.game_interface.radiant_queue:
            urgent_text = self.game_interface.radiant_queue.pop(0)
            logging.info(f"WoW: Radiant trigger: {urgent_text[:100]}")
            self.game_interface._update_overlay(f"! {urgent_text[:120]}", "red")

            try:
                voices = self.synthesizer.voices()
                if voices:
                    self.synthesizer._say(urgent_text, random.choice(voices))
            except Exception as e:
                logging.error(f"WoW: TTS error for radiant trigger: {e}")
            return

        self.game_interface._update_overlay("Listening...", "yellow")
        logging.info("WoW: Waiting for player input...")

        try:
            transcribed_text = self.game_interface.get_player_response(["companion"])
        except Exception as e:
            logging.error(f"WoW: Error getting player response: {e}")
            return

        if not transcribed_text or transcribed_text.strip() == "":
            logging.info("WoW: Empty player input, skipping step")
            return

        transcribed_text = transcribed_text.strip()

        transcript_lower = transcribed_text.lower()
        exit_keywords = ["goodbye", "bye", "farewell", "end conversation", "safe travels", "dismissed"]
        for keyword in exit_keywords:
            if keyword in transcript_lower:
                logging.info(f"WoW: Player ended conversation with keyword: {keyword}")
                await self._end_wow_conversation()
                return

        self.new_message({"role": "user", "name": "[player]", "content": transcribed_text})

        self.game_interface._update_overlay("Thinking...", "cyan")
        logging.info("WoW: Generating response...")

        try:
            await self.get_response()
        except Exception as e:
            logging.error(f"WoW: Error generating response: {e}")
            logging.error(traceback.format_exc())

        if self.messages and hasattr(self, "tokenizer") and self.tokenizer:
            try:
                token_count = self.tokenizer.num_tokens_from_messages(self.messages)
                limit_pct = getattr(self.config, "conversation_limit_pct", 0.75)
                if token_count > (self.tokens_available * limit_pct):
                    logging.info("WoW: Approaching token limit, reloading conversation...")
                    self.reload_conversation()
            except Exception:
                pass

    async def _end_wow_conversation(self):
        logging.info("WoW: Ending conversation")
        self.in_conversation = False
        self.conversation_ended = True
        self.conversation_step = 0
        self.messages = []
        self.game_interface.end_conversation()
        self.game_interface._update_overlay("Companion standing by...", "white")

    def reload_conversation(self):
        logging.info("WoW: Reloading conversation (trimming history)")
        if len(self.messages) > 4:
            self.messages = self.messages[-2:]

    def shutdown(self):
        if hasattr(self, "game_interface"):
            self.game_interface.shutdown()


ConversationManager = WowConversationManager
