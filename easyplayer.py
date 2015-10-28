# ../packages/custom/easyplayer.py

"""Provides :class:`EasyPlayer` and :class:`PlayerEffect` classes."""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python 3 Impors
#   Collections
from collections import defaultdict
#   Functools
from functools import wraps

# Source.Python Imports
#   Entities
from entities.constants import MoveType
from entities.constants import TakeDamage
from entities.helpers import index_from_pointer
from entities.hooks import EntityPreHook
from entities.hooks import EntityCondition
#   Events
from events.listener import _EventListener
#   Listeners
from listeners import LevelShutdown
from listeners.tick import tick_delays
#   Players
from players.entity import PlayerEntity
from players.helpers import index_from_userid
#   Weapons
from weapons.entity import WeaponEntity


# =============================================================================
# >> ALL DECLARATION
# =============================================================================
__all__ = (
    'EasyPlayer',
    'PlayerEffect',
)


# =============================================================================
# >> HOOKS
# =============================================================================
@EntityPreHook(EntityCondition.is_player, 'bump_weapon')
def _pre_bump_weapon(args):
    """Hooks bump_weapon function to implement weapon restrictions."""

    # Get the player and weapon entities
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = WeaponEntity(index_from_pointer(args[1]))

    # Return False if the weapon is restricted for the player
    if weapon.classname in player.restrictions:
        return False


# Store the original fire_game_event method
_original_fire_game_event = _EventListener.fire_game_event


@wraps(_original_fire_game_event)
def _fire_game_event(self, game_event):
    """Custom fire_game_event method for post listeners."""

    # Call the original fire_game_event normally
    _original_fire_game_event(self, game_event)

    # Call the post functions
    event_name = game_event.get_name()
    if event_name == 'player_death':
        _post_player_death(game_event)
    elif event_name == 'player_disconnect':
        _post_player_disconnect(game_event)


# Monkey patch the fire_game_event method with the new wrapped one
_EventListener.fire_game_event = _fire_game_event


# =============================================================================
# >> GAME EVENTS
# =============================================================================
def _post_player_death(game_event):
    """Cancel any active player effects and reset player's gravity."""
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.gravity = 1.0
    player.restrictions.clear()
    player.cancel_all_effects()


def _post_player_disconnect(game_event):
    """Clean up the players from all EasyPlayer classes."""
    index = index_from_userid(game_event.get_int('userid'))
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.cancel_all_effects()
    _EasyPlayerMeta.discard_player(index)


@LevelShutdown
def level_shutdown():
    """Clean up all players from all EasyPlayer classes."""
    _EasyPlayerMeta.discard_all_players()


# =============================================================================
# >> PLAYER EFFECTS
# =============================================================================
class _PlayerEffect(object):
    """Class for player effects like freeze() and burn()."""

    def __init__(self, descriptor_obj, player):
        """Initialize a new effect for a player.

        :param descriptor_obj: The :class:`PlayerEffect` instance
        :param player: Player who to apply the effect on
        """
        self._descriptor_obj = descriptor_obj
        self._player = player
        self._delay = None

    def _enable(self, duration=None):
        """Enable the effect.

        :param duration: Duration after which to cancel the effect
        """

        # If the duration is a positive integer
        if isinstance(duration, int) and duration > 0:

            # Start a delay which will disable the effect
            self._delay = tick_delays.delay(duration, self._disable)

        # Add the effect to the player's effects
        self._player._effects[self._descriptor_obj].append(self)

        # Call the descriptor object's on-function on the player
        self._descriptor_obj._on_f(self._player)

        # Return the player effect to allow __call__ and .cancel()
        return self

    __call__ = _enable

    def _disable(self):
        """Disable the effect."""

        # Remove the effect from the player's effects
        self._player._effects[self._descriptor_obj].remove(self)

        # If the player has no more effects of this type
        if not self._player._effects[self._descriptor_obj]:

            # Call the descriptor o bject's off-function on the player
            self._descriptor_obj._off_f(self._player)

    def cancel(self):
        """Cancel the tick_delay and disable the effect."""

        # If there is a delay object
        if self._delay is not None:

            # Cancel it
            tick_delays.cancel_delay(self._delay)
            self._delay = None

        # Disable the effect
        self._disable()


class PlayerEffect(object):
    """Decorator similar to :class:`property()` for player effects."""

    def __init__(self, on_f=None, off_f=None):
        """Initialize a player effect with the given functions.

        :param on_f: Function to call when the effect starts
        :param off_f: Function to cal when the effect ends
        """
        self._on_f = on_f
        self._off_f = off_f

    def on(self, on_f):
        """Decorator to add an on_f function to the effect.

        :param on_f: Function to call when the effect starts
        """
        return type(self)(on_f, self._off_f)

    def off(self, off_f):
        """Decorator to add an off_f function to the effect.

        :param off_f: Function to call when the effect ends
        """
        return type(self)(self._on_f, off_f)

    def __get__(self, obj, objtype=None):
        """Get an instance of :class:`_PlayerEffect`.

        :param obj: The object who's accessing the effect
        :param objtype: Type of the object
        """

        # Return the :class:`PlayerEffect` instance
        # when accessed through the class
        if obj is None:
            return self

        # Else return a new :class:`_PlayerEffect` instance
        return _PlayerEffect(self, obj)


# =============================================================================
# >> EASY PLAYER
# =============================================================================

class _EasyPlayerMeta(type(PlayerEntity)):
    """Metaclass for the :class:`EasyPlayer` and its subclasses.

    Manages all the instances of :class:`EasyPlayer`,
    making sure they get cached properly.

    Together with the event callbacks defined in :mod:`easyplayer`,
    this will also clean up players upon disonnect or map change.
    """

    # Dictionary to store all the instances of all classes,
    # in case anyone wants to subclass :class:`EasyPlayer`.
    _classes = {}

    def __init__(cls, *args, **kwargs):
        """Initialize a new class.

        Creates an instance dictionary for the new class into
        :attr:`_classes` dictionary.
        """
        _EasyPlayerMeta._classes[cls] = {}

    def __call__(cls, index, *args, **kwargs):
        """Instantiates the class.

        If an instance with the index already exists, return it instead.
        """

        # Get the instance dictionary for the class
        instances = _EasyPlayerMeta._classes[cls]

        # If there is no instance with such index
        if index not in instances:

            # Normally create a new instance and cache it
            instances[index] = super().__call__(index, *args, **kwargs)

        # Else return the existing cached instance
        return instances[index]

    @staticmethod
    def discard_player(player_index):
        """Discard a player, removing him from all classes."""

        # Loop through all of the instance dictionaries
        for instances in _EasyPlayerMeta._classes.values():

            # If an instance of the player exist in the dictionary
            if player_index in instances:

                # Remove him from the dict
                del instances[player_index]

    @staticmethod
    def discard_all_players():
        """Discard all players."""

        # Loop through all instance dictionaries and clear them
        for instances in _EasyPlayerMeta._classes.values():
            instances.clear()


class EasyPlayer(PlayerEntity, metaclass=_EasyPlayerMeta):
    """Custom :class:`PlayerEntity` class with bonus player effects.

    Also implements restrictions and :meth:`from_userid` classmethod.
    """

    def __init__(self, index):
        """Initializes an EasyPlayer instance.

        Adds :attr:`_effects` dictionary and :attr:`restrictions` set.

        :param index: Index of the player who to instantiate
        """
        super().__init__(index)
        self._effects = defaultdict(list)
        self.restrictions = set()

    @classmethod
    def from_userid(cls, userid):
        """Constructor to get an instance from an userid.

        :param userid: UserID of the player who to instantiate
        """
        return cls(index_from_userid(userid))

    def cancel_all_effects(self):
        """Cancel all the effects from a player."""

        # Loop through all the lists of player effects
        for effect_list in self._effects.values():

            # Loop through and cancel every effect in the list
            for effect in effect_list:
                effect.cancel()

        # Clear the :attr:`_effects` dictionary
        self._effects.clear()

    def shift_property(self, prop_name, shift, duration=None):
        """Shifts player's property's value.

        :param prop_name: Name of the property to shift, e.g. 'health'
        :param shift: Amount of shift to make, can be negative
        :param duration: Revert the shift after the duration has ended
        """

        # Get the current value of the property
        old_value = getattr(self, prop_name)

        # Shift the property's value by the shift amount
        setattr(self, prop_name, old_value + shift)

        # If the duration is a positive integer
        if isinstance(duration, int) and duration > 0:

            # Start a delay which will revert the shift
            tick_delays.delay(self.shift_property, prop_name, -shift)

    def _update_move_type(self):
        """Update player's :attr:`move_type` to his player effects.

        This gets called whenver a movement effect starts or ends.
        Priority order: noclip > freeze > fly > walk
        """
        if self._effects[type(self).noclip]:
            self.move_type = MoveType.NOCLIP
        elif self._effects[type(self).freeze]:
            self.move_type = MoveType.NONE
        elif self._effects[type(self).fly]:
            self.move_type = MoveType.FLY
        else:
            self.move_type = MoveType.WALK

    noclip = PlayerEffect(_update_move_type, _update_move_type)
    freeze = PlayerEffect(_update_move_type, _update_move_type)
    fly = PlayerEffect(_update_move_type, _update_move_type)

    @PlayerEffect
    def burn(self):
        self.ignite_lifetime(3600)  # 1 hour ~= infinite

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @PlayerEffect
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.NO)

    @godmode.off
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.YES)
