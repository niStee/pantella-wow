"""WoW character generator stub.

WoW companions are generated from game state (pet family, name, etc.)
via the WoWGameInterface, so this module only needs to provide the
module-level attributes that Pantella's character_generator loader expects.
"""

generator_name = "wow_character_generator"
valid_games = ["wow"]


class Character:
    """Minimal placeholder. WoW prompts are built by the game interface."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
