"""WoW character manager stub.

WoW companions are managed by the game interface, so this module only
needs to provide the module-level attributes that Pantella's manager loader
expects.
"""

manager_slug = "wow_character_manager"
valid_games = ["wow"]


class Character:
    """Minimal placeholder."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
