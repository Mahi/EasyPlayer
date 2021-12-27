from typing import Iterator, Optional, Tuple

from colors import Color
from entities.constants import MoveType
from events import Event, GameEvent
from filters.weapons import WeaponClassIter
from listeners.tick import Delay
from mathlib import Vector
from players.entity import Player as PlayerEntity

from .effect import Effect, EffectHandler, Number


__all__ = (
    'Player',
    'PlayerEffect',
)


class PlayerEffect(Effect):
    """Effect that uses player's `userid` for identification."""

    def identify_target(self, target: PlayerEntity):
        return target.userid


@Event('player_death')
def _on_player_death(event: GameEvent):
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


class Player(PlayerEntity):
    """A player entity class with additional functionality.

    Takes full advantage of the `Effect` class, and implements
    some other missing functionality from Source.Python's player class.
    """

    caching = True  # Enable caching between plugins

    @property
    def chest_location(self) -> Vector:
        """Get the player's chest's location."""
        origin = self.origin
        origin.z += 50
        return origin

    @property
    def stomach_location(self) -> Vector:
        """Get the player's stomach's location."""
        origin = self.origin
        origin.z += 40
        return origin

    @property
    def hip_location(self) -> Vector:
        """Get the player's hips's location."""
        origin = self.origin
        origin.z += 32
        return origin

    def shift_property(self, prop_name: str, shift: Number, duration: Optional[Number]=None) -> Optional[Delay]:
        """Shift a player's numeric property's value.

        Removes the inconvenience of using `setattr` and possibly
        other helper functions when trying to change
        a property's value via delays.

        If an optional duration argument is passed,
        the shift will be reverted after the duration.
        """
        value = getattr(self, prop_name)
        setattr(self, prop_name, value + shift)
        if duration is not None:
            return Delay(duration, self.shift_property, (prop_name, -shift))

    def _move_types_by_priority(self) -> Iterator[Tuple[EffectHandler, MoveType]]:
        """Get player's effects and move types ordered by priority.

        Returns a generator which yields `(EffectHandler, MoveType)`
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
        for effect_handler, move_type in self._move_types_by_priority():
            if effect_handler.is_active():
                self.move_type = move_type
                break
        else:
            self.move_type = MoveType.WALK

    noclip = PlayerEffect(_update_move_type, _update_move_type)
    freeze = PlayerEffect(_update_move_type, _update_move_type)
    fly = PlayerEffect(_update_move_type, _update_move_type)

    @PlayerEffect
    def burn(self):
        self.ignite_lifetime(7200)

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @PlayerEffect
    def godmode(self):
        self.set_godmode(True)

    @godmode.off
    def godmode(self):
        self.set_godmode(False)

    @PlayerEffect
    def noblock(self):
        self.set_noblock(True)

    @noblock.off
    def noblock(self):
        self.set_noblock(False)

    @PlayerEffect
    def paralyze(self):
        self.set_frozen(True)

    @paralyze.off
    def paralyze(self):
        self.set_frozen(False)
