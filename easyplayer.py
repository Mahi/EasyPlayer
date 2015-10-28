# ======================================================================
# >> IMPORTS
# ======================================================================

# Python 3
from collections import defaultdict
from functools import wraps

# Source.Python
from entities.constants import MoveType
from entities.constants import TakeDamage
from entities.helpers import index_from_pointer
from entities.hooks import EntityPreHook
from entities.hooks import EntityCondition

from events.listener import _EventListener

from listeners import LevelShutdown
from listeners.tick import tick_delays

from players.entity import PlayerEntity
from players.helpers import index_from_userid

from weapons.entity import WeaponEntity


# ======================================================================
# >> HOOKS
# ======================================================================

@EntityPreHook(EntityCondition.is_player, 'bump_weapon')
def _pre_bump_weapon(args):
    """
    Hooked to bump_weapon function to implement weapon restrictions.
    """
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = WeaponEntity(index_from_pointer(args[1]))
    if weapon.classname in player.restrictions:
        return False


# Store the original fire_game_event method
_original_fire_game_event = _EventListener.fire_game_event


@wraps(_original_fire_game_event)
def _fire_game_event(self, game_event):
    _original_fire_game_event(self, game_event)
    event_name = game_event.get_name()
    if event_name == 'player_death':
        _post_player_death(game_event)
    elif event_name == 'player_disconnect':
        _post_player_disconnect(game_event)


# Monkey patch the fire_game_event method with the new wrapped one
_EventListener.fire_game_event = _fire_game_event


# ======================================================================
# >> GAME EVENTS
# ======================================================================

def _post_player_death(game_event):
    """
    Cancel any active player effects.
    Also resets player's gravity (Source engine pls).
    """
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.gravity = 1.0
    player.restrictions.clear()
    player.cancel_all_effects()


def _post_player_disconnect(game_event):
    """
    Clean up the EasyPlayer instance from all EasyPlayer (sub)classes.
    Also cancels all effects from the disconnecting player.
    """
    index = index_from_userid(game_event.get_int('userid'))
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.cancel_all_effects()
    _EasyPlayerMeta.discard_player(index)


@LevelShutdown
def level_shutdown():
    """
    Clean up all EasyPlayer instances from all EasyPlayer (sub)classes.
    """
    _EasyPlayerMeta.discard_all_players()


# ======================================================================
# >> PLAYER EFFECTS
# ======================================================================

class _PlayerEffect(object):
    """
    Class for player effects like freeze() and burn().
    """

    def __init__(self, descriptor_obj, player):
        """
        Initialize a new effect for a player.
        `descriptor_obj` should be of type `PlayerEffect`.
        """
        self._descriptor_obj = descriptor_obj
        self._player = player
        self._delay = None

    def _enable(self, duration=None):
        """
        Enable the effect.
        If `duration` is a positive integer, cancel the effect
        automatically after the duration has ended.
        """
        if isinstance(duration, int) and duration > 0:
            self._delay = tick_delays.delay(duration, self._disable)
        self._player._effects[self._descriptor_obj].append(self)
        self._descriptor_obj._on_f(self._player)
        return self  # For __call__

    __call__ = _enable

    def _disable(self):
        """
        Disable the effect.
        """
        self._player._effects[self._descriptor_obj].remove(self)
        if not self._player._effects[self._descriptor_obj]:
            self._descriptor_obj._off_f(self._player)

    def cancel(self):
        """
        Cancel an effect.
        Cancels the tick_delay and disables the effect.
        """
        if self._delay is not None:
            tick_delays.cancel_delay(self._delay)
            self._delay = None
        self._disable()


class PlayerEffect(object):
    """
    Decorator similar to `property()` for creating player effects.
    """

    def __init__(self, on_f=None, off_f=None):
        """
        Initialize a player effect with the given functions.
        """
        self._on_f = on_f
        self._off_f = off_f

    def on(self, on_f):
        """
        Decorator to add an on_f function to the effect class.
        """
        return type(self)(on_f, self._off_f)

    def off(self, off_f):
        """
        Decorator to add an off_f function to the effect class.
        """
        return type(self)(self._on_f, off_f)

    def __get__(self, obj, objtype=None):
        """
        Return an instance of the effect class.
        """
        if obj is None:
            return self
        return _PlayerEffect(self, obj)


# ======================================================================
# >> EASY PLAYER
# ======================================================================

class _EasyPlayerMeta(type(PlayerEntity)):
    """
    Metaclass for the EasyPlayer class (and subclasses).
    Manages all the instances of EasyPlayer, making sure they get
    cached properly.

    Together with the game events defined in easyplayer.py, this will
    also clean up players leaving the server or changing the map.
    """

    _classes = {}  # In case anyone wants to subclass EasyPlayer

    def __init__(cls, *args, **kwargs):
        """
        Create a new instance dict for the class into _classes dict.
        """
        super().__init__()
        _EasyPlayerMeta._classes[cls] = {}

    def __call__(cls, index, *args, **kwargs):
        """
        Instantiates an EasyPlayer class, but if an instance with
        the index already exists, return it instead.
        """
        instances = _EasyPlayerMeta._classes[cls]
        if index not in instances:
            instances[index] = super().__call__(index, *args, **kwargs)
        return instances[index]

    @staticmethod
    def discard_player(player_index):
        """
        Discards a player, removing him from all EasyPlayer classes.
        """
        for instances in _EasyPlayerMeta._classes.values():
            if player_index in instances:
                del instances[player_index]

    @staticmethod
    def discard_all_players():
        """
        Discards all players, completely clearing the instances.
        """
        for instances in _EasyPlayerMeta._classes.values():
            instances.clear()


class EasyPlayer(PlayerEntity, metaclass=_EasyPlayerMeta):
    """
    Custom `PlayerEntity` class with bonus player effects.
    Also implements restriction system and `from_userid` classmethod.
    """

    def __init__(self, index):
        """
        Initializes an EasyPlayer instance, adding _effects dict
        and a set of restricted items.
        """
        super().__init__(index)
        self._effects = defaultdict(list)
        self.restrictions = set()

    @classmethod
    def from_userid(cls, userid):
        """
        Returns an EasyPlayer instance from an userid.
        """
        return cls(index_from_userid(userid))

    def cancel_all_effects(self):
        """
        Cancel all the effects of an EasyPlayer instance.
        """
        for effect_list in self._effects.values():
            for effect in effect_list:
                effect.cancel()
        self._effects.clear()

    def shift_property(self, prop_name, shift, duration=None):
        """
        Shifts an EasyPlayer instances property's value for a duration.
        If duration is a positive integer, revert the shift
        automatically after the duration has ended.
        """
        old_value = getattr(self, prop_name)
        setattr(self, prop_name, old_value + shift)
        if isinstance(duration, int) and duration > 0:
            tick_delays.delay(self.shift_property, prop_name, -shift)

    def _update_move_type(self):
        """
        Updates the player's move_type attribute to match his latest
        move type player effects.
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
