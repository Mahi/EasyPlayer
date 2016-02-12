"""Provides EasyPlayer class, a custom player entity class."""

# Python 3 Impors
import collections
import functools

# Source.Python Imports
from entities.constants import CollisionGroup
from entities.constants import MoveType
from entities.constants import TakeDamage
from entities.helpers import index_from_pointer
from entities.hooks import EntityPreHook
from entities.hooks import EntityCondition

from events.listener import _EventListener

from listeners import OnLevelShutdown
from listeners.tick import Delay

from players.constants import PlayerStates
from players.entity import Player
from players.helpers import index_from_userid
from players.helpers import userid_from_index

from weapons.entity import Weapon

# EasyPlayer Imports
from easyplayer.effect import PlayerEffect


@EntityPreHook(EntityCondition.is_player, 'bump_weapon')
def _pre_bump_weapon(args):
    """Prevent the weapon bump if the weapon is restricted."""
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = Weapon(index_from_pointer(args[1]))
    if weapon.classname in player.restrictions:
        return False


@EntityPreHook(EntityCondition.is_player, 'buy_internal')
def _on_buy_internal(args):
    """Prevent the weapon buy if the weapon is restricted."""
    player = EasyPlayer(index_from_pointer(args[0]))
    weapon = 'weapon_{}'.format(args[1])
    if weapon in player.restrictions:
        return 0


# Store the original fire_game_event method
_original_fire_game_event = _EventListener.fire_game_event


@functools.wraps(_original_fire_game_event)
def _fire_game_event(self, game_event):
    """Custom fire_game_event method which ensures post game events."""
    _original_fire_game_event(self, game_event)
    event_name = game_event.name
    if event_name == 'player_death':
        _post_player_death(game_event)
    elif event_name == 'player_disconnect':
        _post_player_disconnect(game_event)


# Monkey patch the fire_game_event method with the new wrapped one
_EventListener.fire_game_event = _fire_game_event


def _post_player_death(game_event):
    """Reset the player's effects, restrictions, and gravity."""
    userid = game_event['userid']
    player = EasyPlayer.from_userid(userid)
    player.gravity = 1.0
    player.restrictions.clear()
    player.cancel_all_effects()


def _post_player_disconnect(game_event):
    """Clean up the player from all EasyPlayer classes."""
    userid = game_event['userid']
    player = EasyPlayer.from_userid(userid)
    player.cancel_all_effects()
    _EasyPlayerMeta.discard_player(userid)


@OnLevelShutdown
def on_level_shutdown():
    """Clean up all players from all EasyPlayer classes."""
    _EasyPlayerMeta.discard_all_players()


class _EasyPlayerMeta(type(Player)):
    """Metaclass for EasyPlayer class and its subclasses.

    Manages all the instances of EasyPlayer classes, making sure
    they get cached properly to prevent multiple __init__ calls.

    Together with event callbacks, this will also clean up
    players upon disonnect or map change.
    """

    # Dictionary to store all the instances of all classes
    _classes = collections.defaultdict(dict)

    def __call__(cls, index, *args, **kwargs):
        """Instantiates the class.

        If an instance with the same userid already exists,
        return it instead of creating a new one.
        """
        instance_dict = _EasyPlayerMeta._classes[cls]
        userid = userid_from_index(index)
        if userid not in instance_dict:
            instance_dict[userid] = super().__call__(index, *args, **kwargs)
        return instance_dict[userid]

    @staticmethod
    def discard_player(userid):
        """Discard a player, removing him from all classes."""
        for instance_dict in _EasyPlayerMeta._classes.values():
            if userid in instance_dict:
                del instance_dict[userid]

    @staticmethod
    def discard_all_players():
        """Discard all players."""
        for instance_dict in _EasyPlayerMeta._classes.values():
            instance_dict.clear()


class EasyPlayer(Player, metaclass=_EasyPlayerMeta):
    """Custom player entity class with additional player effects.

    Also implements restrictions and from_userid classmethod.
    All attributes are stored into EasyPlayer._data dictionary
    to allow multiple instances to use the same data.
    """

    # A dictionary which stores all the EasyPlayer's attributes
    _data = collections.defaultdict(dict)

    def __init__(self, index):
        """Initializes a player with effects and restrictions."""
        super().__init__(index)
        self._effects = collections.defaultdict(list)
        self.restrictions = set()

    def __getattr__(self, attr):
        """Get an attribute's value from the _dict if all else fails."""
        if attr in EasyPlayer._data[self.userid]:
            return EasyPlayer._data[self.userid][attr]
        return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        """Set an attribute to the _dict if it's a new attribute."""
        if attr in super().__dir__():
            super().__setattr__(attr, value)
        else:
            EasyPlayer._data[self.userid][attr] = value

    def __dir__(self):
        """Return an alphabetized list of attributes for the instance."""
        attributes = set(super().__dir__())
        attributes |= EasyPlayer._data[self.userid].keys()
        return sorted(attributes)

    @classmethod
    def from_userid(cls, userid):
        """Custom constructor to get an instance from an userid."""
        return cls(index_from_userid(userid))

    def cancel_all_effects(self):
        """Cancel all the effects from a player."""
        for effect_list in self._effects.values():
            for effect in effect_list:
                effect.cancel()
        self._effects.clear()

    @property
    def cs_team(self, teams=('un', 'spec', 't', 'ct')):
        """Get the player's Counter-Strike team."""
        return teams[self.team]

    @property
    def tf_team(self, teams=('un', 'spec', 'red', 'blue')):
        """Get the player's Team Fortress team."""
        return teams[self.team]

    def shift_property(self, prop_name, shift, duration=None):
        """Shifts player's property's value.

        If duration is a positive integer, automatically cancel
        the shift after the duration has ended.
        """
        old_value = getattr(self, prop_name)
        setattr(self, prop_name, old_value + shift)
        if isinstance(duration, int) and duration > 0:
            return Delay(
                duration, self.shift_property, prop_name, -shift)

    def _update_move_type(self):
        """Update player's move_type to match his player effects.

        This gets called whenever a movement effect starts or ends.
        Priority orderfor movement types: noclip > freeze > fly > walk
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
    def paralyze(self):
        self.flags |= PlayerStates.FROZEN

    @paralyze.off
    def paralyze(self):
        self.flags &= ~PlayerStates.FROZEN

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

    @PlayerEffect
    def noblock(self):
        self.collision_group = CollisionGroup.DEBRIS_TRIGGER

    @noblock.off
    def noblock(self):
        self.collision_group = CollisionGroup.PLAYER
