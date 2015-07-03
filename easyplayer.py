# ======================================================================
# >> IMPORTS
# ======================================================================

# Python 3
import collections
import functools

# Source.Python
from players.entity import PlayerEntity
from listeners.tick import tick_delays
from listeners.tick import Delay
from listeners import LevelShutdown
from entities.constants import MoveType
from entities.constants import TakeDamage
from players.helpers import index_from_userid
from events import Event


# ======================================================================
# >> GLOBALS
# ======================================================================

player_dict = {}


# ======================================================================
# >> GAME EVENTS
# ======================================================================

@Event
def player_death(game_event):
    player = EasyPlayer.from_userid(game_event.get_int('userid'))
    player.gravity = 1.0
    for delay_list in player._effects.values():
        for delay in delay_list:
            if isinstance(delay, Delay):
                tick_delays.cancel_delay(delay)
    player._effects.clear()


@Event
def player_disconnect(game_event):
    index = index_from_userid(game_event.get_int('userid'))
    if index in player_dict:
        del player_dict[index]


@LevelShutdown
def level_shutdown():
    player_dict.clear()


# ======================================================================
# >> CLASSES
# ======================================================================

class _Effect(object):
    """Class to easily create player effects like burn() and fly()."""

    def __init__(self, name, on_f, off_f):
        self._name = name
        self._on_f = on_f
        self._off_f = off_f

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


class EasyPlayer(PlayerEntity):
    """Custom PlayerEntity class with bonus features."""

    @classmethod
    def from_userid(cls, userid):
        return cls(index_from_userid(userid))

    def __new__(cls, index):
        if index not in player_dict:
            player_dict[index] = super().__new__(cls, index)
            object.__setattr__(
                player_dict[index], '_effects', collections.defaultdict(list)
            )
        return player_dict[index]

    def _burn(self):
        self.ignite()

    def _unburn(self):
        self.ignite_lifetime(0)

    burn = _Effect('burn', _burn, _unburn)

    def _freeze(self):
        self.move_type = MoveType.NONE

    def _unfreeze(self):
        if self._effects['noclip']:
            self._noclip()
        elif self._effects['fly']:
            self._fly()
        else:
            self.move_type = MoveType.WALK

    freeze = _Effect('freeze', _freeze, _unfreeze)

    def _noclip(self):
        self.move_type = MoveType.NOCLIP

    def _unnoclip(self):
        if self._effects['freeze']:
            self._freeze()
        elif self._effects['fly']:
            self._fly()
        else:
            self.move_type = MoveType.WALK

    noclip = _Effect('noclip', _noclip, _unnoclip)

    def _fly(self):
        self.move_type = MoveType.FLY

    def _unfly(self):
        if self._effects['freeze']:
            self._freeze()
        elif self._effects['noclip']:
            self._noclip()
        else:
            self.move_type = MoveType.WALK

    fly = _Effect('fly', _fly, _unfly)

    def _godmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.NO)

    def _ungodmode(self):
        self.set_property_uchar('m_takedamage', TakeDamage.YES)

    godmode = _Effect('godmode', _godmode, _ungodmode)
