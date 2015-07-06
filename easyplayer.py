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

    Preferrably used as a decorator similar to `property()`. Example:

    >>> class EasyPlayer(PlayerEntity):
    ...     @PlayerEffect
    ...     def burn(self):
    ...         self.ignite_lifetime(3600)
    ...
    ...     @burn.off
    ...     def burn(self):
    ...         self.ignite_lifetime(0)

    The first function (`burn.on`) gets called whenever `player.burn()`
    is called with any value. If an optional argument `duration`
    is passed to the `player.burn()` function, `burn.off()` function
    will automatically get called after the duration has passed.

    You can use `player.burn(0)` to disable an existing "infinite"
    effect. Notice, that it only disables one of the infinite effects,
    so a code like this would leave the player burning:

    >>> p = EasyPlayer(1)
    >>> p.burn()  # Apply one "infinite" burn
    >>> p.burn()  # Apply an other one
    >>> p.burn(0)  # Disable one of them; player still burning.

    `p.burn(0)` also doesn't interfere with `p.burn(5)`, so if you apply
    a burn with a duration and then try to shut it with `p.burn(0)`,
    the player will keep burning.
    """

    def __init__(self, on_f=None, off_f=None):
        self._on_f = on_f
        self._off_f = off_f

    def on(self, on_f):
        return type(self)(on_f, self._off_f)

    def off(self, off_f):
        return type(self)(self._on_f, off_f)

    def _enable(self, player, duration=-1):
        if duration < 0:  # Infinite (1 hour)
            player._effects[self].append(True)
        elif duration == 0:  # "Cancel" infinite
            return self._disable(player, True)
        else:
            delay = tick_delays.delay(duration, self._disable)
            delay.args = (player, delay)
            player._effects[self].append(delay)
        self._on_f(player)

    def _disable(self, player, delay):
        player._effects[self].remove(delay)
        if not player._effects[self]:
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
    """Custom `PlayerEntity` class with bonus features.

    The core idea is that `EasyPlayer` manages "player effects" like
    burn, freeze, and noclip, so that you can use them without having
    to worry about someone else using them. Normally removing freeze
    using `player.move_type = MoveType.WALK` might also remove a freeze
    applied by an other plugin, or even drop the player's noclip.
    If everyone used EasyPlayer, this wouldn't happen.

    You can also use all of these effects with a duration instead
    of manually using `tick_delays` For example: `player.freeze(10)`
    to freeze a player for 10 seconds. To permanently freeze a player,
    pass no argument at all: `player.freeze()`. To remove this infinite
    freeze, pass in a zero: `player.freeze(0)`. Notice that it doesn't
    completely unfreeze the player; it simply removes the freeze applied
    by you.

    `EasyPlayer` also resets gravity on every round and implements
    `from_userid(userid)` classmethod to get an instance directly
    from an userid. You can also use `restrictions` set to restrict
    player from using certain weapons. The set should contain classnames
    of the weapons that are meant to be restricted.
    """

    def __init__(self, index):
        self._effects = collections.defaultdict(list)
        self.restrictions = set()

    @classmethod
    def from_userid(cls, userid):
        return cls(index_from_userid(userid))

    @PlayerEffect
    def burn(self):
        self.ignite_lifetime(3600)  # 1 hour enough?

    @burn.off
    def burn(self):
        self.ignite_lifetime(0)

    @PlayerEffect
    def freeze(self):
        self.move_type = MoveType.NONE

    @freeze.off
    def freeze(self):
        if self._effects['noclip']:
            self._noclip()
        elif self._effects['fly']:
            self._fly()
        else:
            self.move_type = MoveType.WALK

    @PlayerEffect
    def noclip(self):
        self.move_type = MoveType.NOCLIP

    @noclip.off
    def noclip(self):
        if self._effects['freeze']:
            self._freeze()
        elif self._effects['fly']:
            self._fly()
        else:
            self.move_type = MoveType.WALK

    @PlayerEffect
    def fly(self):
        self.move_type = MoveType.FLY

    @fly.off
    def fly(self):
        if self._effects['freeze']:
            self._freeze()
        elif self._effects['noclip']:
            self._noclip()
        else:
            self.move_type = MoveType.WALK

    @PlayerEffect
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.NO)

    @godmode.off
    def godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.YES)
