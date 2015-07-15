# ======================================================================
# >> IMPORTS
# ======================================================================

# Python 3
from collections import defaultdict

# Source.Python
from entities.constants import MoveType
from entities.constants import TakeDamage
from entities.helpers import index_from_pointer
from entities.hooks import EntityPreHook

from events import Event

from listeners import LevelShutdown
from listeners.tick import tick_delays
from listeners.tick import Delay

from players.entity import PlayerEntity
from players.helpers import index_from_userid

from weapons.entity import WeaponEntity


# ======================================================================
# >> HOOKS
# ======================================================================

@EntityPreHook('player', 'bump_weapon')
def _bump_weapon(args):
    """
    Hooked to bump_weapon function to implement weapon restrictions.
    """
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = WeaponEntity(index_from_pointer(args[1]))
    if weapon.classname in player.restrictions:
        return False


# ======================================================================
# >> GAME EVENTS
# ======================================================================

@Event
def player_death(game_event):
    """
    Cancel any active player effects.
    Also resets player's gravity (Source engine pls).
    """
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.gravity = 1.0
    player.restrictions.clear()
    player.cancel_all_effects()


@Event
def player_disconnect(game_event):
    """
    Clean up the EasyPlayer instance from all EasyPlayer (sub)classes.
    Also cancels all effects from the disconnecting player.
    """
    index = index_from_userid(game_event.get_int('userid'))
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.cancel_all_effects()
    tick_delays.delay(1.0, _EasyPlayerMeta.discard_player, index)


@LevelShutdown
def level_shutdown():
    """
    Clean up all EasyPlayer instances from all EasyPlayer (sub)classes.
    """
    tick_delays.delay(1.0, _EasyPlayerMeta.discard_all_players)


# ======================================================================
# >> PLAYER EFFECTS
# ======================================================================

class _PlayerEffect(object):
    """
    Class for player effects like freeze() and burn().
    """

    def __init__(self, player):
        """
        Initialize a new effect for a player.
        """
        self._player = player
        self._delay = None

    def _enable(self, duration=-1):
        """
        Enable the effect.
        Use negative duration for infinite effect.
        """
        if duration > 0:
            self._delay = tick_delays.delay(duration, self._disable)
        self._player._effects[type(self)].append(self)
        self._on_f(self._player)

    __call__ = _enable

    def _disable(self):
        """
        Disable the effect.
        """
        self._player._effects[type(self)].remove(self)
        if not self._player._effects[type(self)]:
            self._off_f(self._player)

    def cancel(self):
        """
        Cancel an effect.
        Cancels the tick_delay and disables the effect.
        """
        if self._delay is not None:
            tick_delays.cancel_delay(self._delay)
            self._delay = None
        self._disable()

    def _on_f(player):
        raise NotImplementedError

    @staticmethod
    def _off_f(player):
        raise NotImplementedError


class PlayerEffect(object):
    """
    Decorator similar to property() for creating _PlayerEffect classes.
    """

    def __init__(self, on_f=None, off_f=None, name=None):
        """
        Initialize a player effect, creating the _PlayerEffect class.
        """

        # Get a name for the effect class
        if name is None:
            if on_f is not None:
                name = on_f.__name__
            elif off_f is not None:
                name = off_f.__name__
            else:
                name = ''

        # Construct the effect class
        self.effect_cls = type(name, (_PlayerEffect,), {})
        self.effect_cls._on_f = staticmethod(on_f)
        self.effect_cls._off_f = staticmethod(off_f)

    def on(self, on_f):
        """
        Decorator to add an on_f function to the effect class.
        """
        self.effect_cls._on_f = staticmethod(on_f)
        return self

    def off(self, off_f):
        """
        Decorator to add an off_f function to the effect class.
        """
        self.effect_cls._off_f = staticmethod(off_f)
        return self

    def __get__(self, instance, owner):
        """
        Return an instance of the effect class.
        """
        if instance is None:
            return self
        return self.effect_cls(instance)


# ======================================================================
# >> EASY PLAYER
# ======================================================================

class _EasyPlayerMeta(type(PlayerEntity)):
    """
    Metaclass for all EasyPlayer classes.
    Manages all the instances of EasyPlayer classes, making sure
    they get cached properly. Together with the game event functions
    defined above in this easyplayer.py file, it will also clean up
    any players leaving the server or changing the map.
    """
    _classes = {}

    def __new__(meta, name, bases, attrs):
        """
        Create a new EasyPlayer class and add it to the _classes dict.
        """
        cls = super().__new__(meta, name, bases, attrs)
        meta._classes[cls] = {}
        return cls

    def __call__(self, index, *args, **kwargs):
        """
        Upon creating a new instance of an EasyPlayer class,
        return an existing instance with the same index, if one exists.
        """
        instances = _EasyPlayerMeta._classes[self]
        if index not in instances:
            instances[index] = super().__call__(index, *args, **kwargs)
        return instances[index]

    @staticmethod
    def discard_player(player_index):
        """
        Discards a player, removing him from all of the EasyPlayer
        classes (EasyPlayer + subclasses).
        """
        for easy_player_instances in _EasyPlayerMeta._classes.values():
            if player_index in easy_player_instances:
                del easy_player_instances[player_index]

    @staticmethod
    def discard_all_players():
        """
        Discards all players, completely clearing the instances.
        """
        for easy_player_instances in _EasyPlayerMeta._classes.values():
            easy_player_instances.clear()



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

    def shift_property(self, prop_name, shift, duration=-1):
        """
        Shifts an EasyPlayer instances property's value for a duration.
        Use negative duration for permanent effect.
        """
        setattr(self, prop_name, getattr(self, prop_name) + shift)
        if duration > 0:
            tick_delays.delay(self.shift_property, prop_name, -shift)


    # ===================================================================
    # >> EASYPLAYER'S PLAYER EFFECTS
    # ==================================================================

    def _update_move_type(self):
        if self._effects[type(self).noclip.effect_cls]:
            self.move_type = MoveType.NOCLIP
        elif self._effects[type(self).freeze.effect_cls]:
            self.move_type = MoveType.NONE
        elif self._effects[type(self).fly.effect_cls]:
            self.move_type = MoveType.FLY
        else:
            self.move_type = MoveType.WALK

    noclip = PlayerEffect(_update_move_type, _update_move_type, name='noclip')
    freeze = PlayerEffect(_update_move_type, _update_move_type, name='freeze')
    fly = PlayerEffect(_update_move_type, _update_move_type, name='fly')

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
