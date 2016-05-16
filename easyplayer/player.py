import functools

from entities.constants import MoveType
from events import Event
from listeners.tick import Delay
from players.entity import Player as SourcePythonPlayer
from players.helpers import index_from_userid

from .effect import Effect

__all__ = (
    'Player',
)


@Event('player_death')
def _on_player_death(event):
    """Callback for resetting player's gravity on death.

    For some reason Valve chose not to reset gravity, although they
    reset most other properties (speed, color, etc.) which is usually
    an inconvenience, so this will reset the gravity for us.
    """
    player = Player.from_userid(event['userid'])
    player.gravity = 1.0


class Player(SourcePythonPlayer):
    """A player entity class with additional functionality.

    Takes full advantage of the `Effect` class, and implements
    some other missing functionality from Source.Python's player class.
    """

    @classmethod
    def from_userid(cls, userid):
        """Get a player instance directly from an userid."""
        return cls(index_from_userid(userid))

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
            return Delay(duration, self.shift_property, prop_name, -shift)

    def _move_types_by_priority(self):
        """Get player's effects and move types ordered by priority.

        Returns a generator which yields `(_EffectHandler, MoveType)`
        pairs in the order of noclip, freeze, fly.
        """
        yield self.noclip, MoveType.NOCLIP
        yield self.freeze, MoveType.FREEZE
        yield self.fly, MoveType.FLY

    def _enable_move_type(self, move_type):
        """Enable a move type for a player.

        This will only change player's move type if there's no move type
        enabled with priority higher than the one we're enabling.
        It will, however, remember that the move type was set, so if
        the higher priority move type gets disabled, this new move type
        gets set for the player.
        """
        for effect, mt in self._move_types_by_priority():
            # We reached desired move type without a higher priority
            # move type being enabled (see elif below) so we enable
            # the move type regardless of lower priority move types
            if mt == move_type:
                self.move_type = move_type
                break
            # A higher priority move type is enabled before we reach
            # desired move type. Just break and don't change anything.
            elif effect.is_enabled():
                break

    def _disable_move_type(self, move_type):
        """Disable a move type from the player.

        If the player's move type was currently this move type,
        this will switch to the one with second highes priority.
        If no other custom move type is enabled, the player shall walk.
        """
        for effect, mt in self._move_types_by_priority():
            # Set player's move type to the first enabled move type
            # other than the one we're disabling at the moment
            if effect.is_enabled() and mt != move_type:
                self.move_type = mt
                break
        # When no other move type is enabled, we walk
        else:
            self.move_type = MoveType.WALK

    noclip = Effect(
        functools.partial(_enable_move_type, MoveType.NOCLIP),
        functools.partial(_disable_move_type, MoveType.NOCLIP))

    freeze = Effect(
        functools.partial(_enable_move_type, MoveType.FREEZE),
        functools.partial(_disable_move_type, MoveType.FREEZE))

    fly = Effect(
        functools.partial(_enable_move_type, MoveType.FLY),
        functools.partial(_disable_move_type, MoveType.FLY))

    @Effect
    def burn(self):
        self.ignite_lifetime(7200)

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @Effect
    def godmode(self):
        super().set_godmode(True)

    @godmode.off
    def godmode(self):
        super().set_godmode(False)

    @Effect
    def noblock(self):
        super().set_noblock(True)

    @noblock.off
    def noblock(self):
        super().set_noblock(False)

    @Effect
    def paralyze(self):
        super().set_frozen(True)

    @paralyze.off
    def paralyze(self):
        super().set_frozen(False)
