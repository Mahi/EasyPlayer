from colors import Color
from entities.constants import MoveType
from events import Event
from filters.weapons import WeaponClassIter
from listeners.tick import Delay
from players.entity import Player as SourcePythonPlayer

from .effect import Effect

__all__ = (
    'Player',
)


@Event('player_death')
def _on_player_death(event):
    """Callback for resetting player's attributes on death.

    For some reason Valve/SP Team chose not to reset things like
    gravity, color, weapon restcrictions, etc. although they
    reset most other properties (speed, health...).
    """
    player = Player.from_userid(event['userid'])
    player.gravity = 1.0
    player.color = Color(255, 255, 255)
    for weapon in WeaponClassIter():
        if player.is_weapon_restricted(weapon.name):
            player.unrestrict_weapons(weapon.name)


class Player(SourcePythonPlayer):
    """A player entity class with additional functionality.

    Takes full advantage of the `Effect` class, and implements
    some other missing functionality from Source.Python's player class.
    """

    @property
    def cs_team(self):
        """Get the player's Counter-Strike team as a string.

        This string is compatible with Source.Python's filters.
        """
        return ('un', 'spec', 't', 'ct')[self.team]

    @property
    def tf_team(self):
        """Get the player's Team Fortress team as a string.

        This string is compatible with Source.Python's filters.
        """
        return ('un', 'spec', 'red', 'blue')[self.team]

    @property
    def chest_location(self):
        """Get the player's chest's location."""
        origin = self.origin
        origin.z += 50
        return origin

    @property
    def stomach_location(self):
        """Get the player's stomach's location."""
        origin = self.origin
        origin.z += 40
        return origin

    @property
    def hip_location(self):
        """Get the player's hips's location."""
        origin = self.origin
        origin.z += 32
        return origin

    def shift_property(self, prop_name, shift, duration=None):
        """Shift a player's integer property's value.

        Removes the inconvenience of using `setattr` and possibly other
        helper functions when trying to change a property's value
        via an other function (delays for example).
        If an optional duration argument is passed, the shift will be
        reverted after the duration has passed.
        """
        value = getattr(self, prop_name)
        setattr(self, prop_name, value + shift)
        if duration is not None:
            return Delay(duration, self.shift_property, (prop_name, -shift))

    def _move_types_by_priority(self):
        """Get player's effects and move types ordered by priority.

        Returns a generator which yields `(_EffectHandler, MoveType)`
        pairs in the order of noclip, freeze, fly.
        """
        yield self.noclip, MoveType.NOCLIP
        yield self.freeze, MoveType.NONE
        yield self.fly, MoveType.FLY

    def _update_move_type(self):
        """Update player's move type.
        
        Loops through all the move types in order with
        :meth:`_move_types_by_priority()` and sets the player's
        movement type to the first one which has an enabled
        effect for the player, or ``MoveType.WALK``
        if none are enabled.
        """
        for effect, move_type in self._move_types_by_priority():
            if effect.is_enabled():
                self.move_type = move_type
                break
        else:
            self.move_type = MoveType.WALK

    noclip = Effect(_update_move_type, _update_move_type)
    freeze = Effect(_update_move_type, _update_move_type)
    fly = Effect(_update_move_type, _update_move_type)

    @Effect
    def burn(self):
        self.ignite_lifetime(7200)

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @Effect
    def godmode(self):
        self.set_godmode(True)

    @godmode.off
    def godmode(self):
        self.set_godmode(False)

    @Effect
    def noblock(self):
        self.set_noblock(True)

    @noblock.off
    def noblock(self):
        self.set_noblock(False)

    @Effect
    def paralyze(self):
        self.set_frozen(True)

    @paralyze.off
    def paralyze(self):
        self.set_frozen(False)
