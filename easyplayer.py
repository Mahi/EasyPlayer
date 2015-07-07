# ======================================================================
# >> IMPORTS
# ======================================================================

# Python 3
import functools
import collections

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
    """Hooked to bump_weapon function to implement restrictions."""
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = WeaponEntity(index_from_pointer(args[1]))
    if weapon.classname in player.restrictions:
        return False


# ======================================================================
# >> GAME EVENTS
# ======================================================================

@Event
def player_death(game_event):
    """Remove any active PlayerEffects as well as their delays.

    Also resets player's gravity (Source engine pls).
    """
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.gravity = 1.0
    for delay_list in player._effects.values():
        for delay in delay_list:
            if isinstance(delay, Delay):
                tick_delays.cancel_delay(delay)
    player._effects.clear()


@Event
def player_disconnect(game_event):
    """Clear user from all EasyPlayer classes."""
    index = index_from_userid(game_event.get_int('userid'))
    for instances in _EasyPlayerMeta._classes.values():
        if index in instances:
            del instances[index]


@LevelShutdown
def level_shutdown():
    """Clear all instances of any EasyPlayer classes."""
    for cls in _EasyPlayerMeta._classes:
        _EasyPlayerMeta._classes[cls].clear()


# ======================================================================
# >> CLASSES
# ======================================================================

class PlayerEffect(object):
    """Class to implement player effects like `burn()` or `freeze()`.

    Preferrably used as a decorator similar to `property()`.
    Example usage:

    >>> class EasyPlayer(PlayerEntity):
    ...     @PlayerEffect
    ...     def burn(self):
    ...         self.ignite_lifetime(3600)  # 1 hour is almost infinite
    ...
    ...     @burn.off
    ...     def burn(self):
    ...         self.ignite_lifetime(0)

    The first function (`burn.on`) gets called whenever `player.burn()`
    is called with any value. If an optional argument `duration`
    is passed to the `player.burn()` function, `burn.off()` function
    will automatically get called after the duration has passed.

    You can use `player.burn(0)` to disable an existing "infinite"
    effect. Notice, that `p.burn(0)` doesn't interfere with `p.burn(5)`,
    so if you apply a burn with a duration and then try to stop it with
    `p.burn(0)`, the player will keep burning. It also wont completely
    extinguish the player: if someone else has applied a permanent
    burn to the player, he will keep burning even if you call
    `player.burn(0)` to stop the burn you've applied.
    """

    def __init__(self, name, on_f=None, off_f=None):
        self._name = name
        self._on_f = on_f
        self._off_f = off_f

    def on(self, on_f):
        return type(self)(self._name, on_f, self._off_f)

    __call__ = on

    def off(self, off_f):
        return type(self)(self._name, self._on_f, off_f)

    def _enable(self, player, duration=-1):
        if duration < 0:  # Infinite (1 hour)
            player._effects[self._name].append(True)
        elif duration == 0:  # "Cancel" infinite
            return self._disable(player, True)
        else:
            delay = tick_delays.delay(duration, self._disable)
            delay.args = (player, delay)
            player._effects[self._name].append(delay)
        self._on_f(player)

    def _disable(self, player, delay):
        player._effects[self._name].remove(delay)
        if not player._effects[self._name]:
            self._off_f(player)

    def __get__(self, instance, owner):
        return functools.partial(self._enable, instance)


class _EasyPlayerMeta(type(PlayerEntity)):
    """Metaclass for all `EasyPlayer` classes.

    Manages all the instances of a `PlayerEntity` class, making sure
    they get cached properly. Together with the game event functions
    defined above in this `easyplayer.py` file, it will also clean up
    any players leaving the server or changing the map.
    """
    _classes = {}

    def __new__(meta, name, bases, attrs):
        cls = super().__new__(meta, name, bases, attrs)
        meta._classes[cls] = {}
        return cls

    def __call__(cls, index, *args, **kwargs):
        instances = type(cls)._classes[cls]
        if index not in instances:
            instances[index] = super().__call__(index, *args, **kwargs)
        return instances[index]


class EasyPlayer(PlayerEntity, metaclass=_EasyPlayerMeta):
    """Custom `PlayerEntity` class with bonus player effects.

    Also implements restriction system and `from_userid` classmethod."""

    def __init__(self, index):
        self._effects = collections.defaultdict(list)
        self.restrictions = set()

    @classmethod
    def from_userid(cls, userid):
        return cls(index_from_userid(userid))

    def _update_move_type(self):
        if self._effects['noclip']:
            self.move_type = MoveType.NOCLIP
        elif self._effects['freeze']:
            self.move_type = MoveType.NONE
        elif self._effects['fly']:
            self.move_type = MoveType.FLY
        else:
            self.move_type = MoveType.WALK

    noclip = PlayerEffect('noclip', _update_move_type, _update_move_type)
    freeze = PlayerEffect('freeze', _update_move_type, _update_move_type)
    fly = PlayerEffect('fly', _update_move_type, _update_move_type)

    @PlayerEffect('burn')
    def burn(self):
        self.ignite_lifetime(3600)  # 1 hour enough?

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @PlayerEffect('godmode')
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.NO)

    @godmode.off
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.YES)
