"""WoW character database stub.

WoW characters are read from game state, so this module only needs to
provide the module-level attributes that Pantella's character DB loader
expects.
"""

db_slug = "wow_character_db"
valid_games = ["wow"]


class CharacterDB:
    """Minimal placeholder."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
