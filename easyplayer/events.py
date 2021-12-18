import collections

from core import AutoUnload
from events.manager import event_manager

__all__ = (
    'Event',
    'EventManager',
    'GameEventConversion',
    'DEFAULT_GAME_EVENT_CONVERSIONS',
)

GameEventConversion = collections.namedtuple(
    'GameEventConversion',
    (
        'userid_key',
        'player_key',
        'event_name',
    )
)

DEFAULT_GAME_EVENT_CONVERSIONS = {
    'player_blind': [
        GameEventConversion('attacker', 'attacker', 'player_blind'),
        GameEventConversion('userid', 'victim', 'player_go_blind'),
    ],
    'player_death': [
        GameEventConversion('assister', 'assister', 'player_assist'),
        GameEventConversion('attacker', 'attacker', 'player_kill'),
        GameEventConversion('userid', 'victim', 'player_death'),
    ],
    'player_hurt': [
        GameEventConversion('attacker', 'attacker', 'player_attack'),
        GameEventConversion('userid', 'victim', 'player_victim'),
    ],
}


# Single player events with just 'userid' => 'player' conversion
for event_name in (
    'bomb_defused', 'bomb_exploded', 'bomb_planted',
    'player_jump', 'player_spawn',
):
    DEFAULT_GAME_EVENT_CONVERSIONS[event_name] = [GameEventConversion('userid', 'player', event_name)]


class Event:
    """Event class for managing and notifying listeners.

    Separates listeners that take the event's name as an argument
    from the listeners that only wish to receive the event arguments
    themselves.

    Example usage:

    >>> my_event = Event('my_event', named=True)  # False by default
    >>> def on_event(event_name, player, **event_args):  # Unpack any arguments!
    ...     print(event_name, player.name)
    ...
    >>> my_event.listeners.append(on_event)
    >>> my_event.fire(player=my_player)
    my_event Mahi
    """

    def __init__(self, name, *listeners, named_listeners=()):
        """Initialize a new event."""
        self.name = name
        self.listeners = []
        self.named_listeners = []
        for listener in listeners:
            self.listeners.append(listener)
        for listener in named_listeners:
            self.named_listeners.append(listener)

    def fire(self, event_args={}, **kwargs):
        """Fire an event.

        Merges `event_args` with any provided keyword arguments
        and notifies all listeners with the merged arguments.
        """
        kwargs.update(event_args)
        for listener in self.listeners:
            listener(**kwargs)
        for listener in self.named_listeners:
            listener(self.name, **kwargs)


class EventManager(AutoUnload):
    """Manage both GameEvents and custom events in a uniform manner.

    Simply provide your PlayerDictionary as an argument,
    and have the GameEvent's userids be converted to your
    custom Player entities automatically:

    >>> player_dict = PlayerDictionary(MyCustomPlayer)
    >>> events = EventManager(player_dict)
    >>> @events.on('player_jump')
    ... def on_player_jump(player, **eargs):
    ...     assert type(player) == MyCustomPlayer

    You can register additional game events converters with
    `add_simple_conversion()`:

    >>> events = EventManager(player_dict)
    >>> events.add_simple_conversions('enter_bombzone', 'exit_bombzone')
    >>> @events.on('enter_bombzone')
    ... def on_enter_bombzone(player, **eargs):
    ...     assert type(player) == MyCustomPlayer

    By default, all the GameEvents with an attacker and
    a victim have been split up into multiple events:

    - player_blind => player_blind and player_go_blind
    - player_hurt => player_attack and player_victim
    - player_death => player_kill, player_assist, and player_death

    Finally, you can add completely custom events with
    `create_event()` and fire them using the ´[]` syntax:

    >>> events = EventManager(player_dict)
    >>> events.create_event('my_custom_event')
    >>> @events.on('my_custom_event')
    ... def on_my_custom_event(**eargs):
    ...     print(eargs)
    ...
    >>> events['my_custom_event'].fire(name=player.name, foo='bar')
    {'name': 'Mahi', 'foo': 'bar'}
    """

    def __init__(self,
        player_dict,
        game_event_conversions=DEFAULT_GAME_EVENT_CONVERSIONS,
    ):
        """Initialize the event manager for a player dict."""
        self.player_dict = player_dict
        self._events = {}
        self.game_event_conversions = collections.defaultdict(list)
        for game_event_name, conversions in game_event_conversions.items():
            for conversion in conversions:
                self.add_game_event_conversion(game_event_name, conversion)

    def add_game_event_conversion(self, source_event_name, game_event_conversion):
        """Add a game event conversion to the manager.

        Example usage:

        >>> events.add_game_event_conversion(
        ...     # Add a conversion for 'bomb_beingdefuse' game event
        ...     'bomb_begindefuse',
        ...     # Convert the event's 'userid' key to a player object
        ...     # and call the new event 'bomb_defused'
        ...     GameEventConversion('userid', 'player', 'bomb_defused')
        ... )
        """
        if self._on_game_event not in event_manager.get(source_event_name, ()):
            event_manager.register_for_event(source_event_name, self._on_game_event)
        self.game_event_conversions[source_event_name].append(game_event_conversion)
        self.create_event(game_event_conversion.event_name)

    def add_simple_game_event_conversion(self, event_name):
        """Add a game event conversion for 'userid' key only.

        Retains the event name.
        """
        self.add_game_event_conversion(
            event_name,
            GameEventConversion('userid', 'player', event_name),
        )

    def _unload_instance(self):
        """Automatically unload the GameEvent listeners."""
        for event_name in self.game_event_conversions.keys():
            event_manager.unregister_for_event(event_name, self._on_game_event)

    def __getitem__(self, key):
        return self._events[key]

    def __contains__(self, key):
        return key in self._events

    def __iter__(self):
        return iter(self._events.keys())

    def create_event(self, event_name):
        """Create a new event into the manager."""
        self._events[event_name] = Event(event_name)

    def on(self, *event_names, named=False):
        """Decorator to add a listener to multiple events at once.

        Supports `named` argument to determine whether the listener
        should receive the event's name as a positional argument.
        """
        def decorator(listener):
            for event_name in event_names:
                if named:
                    self[event_name].named_listeners.append(listener)
                else:
                    self[event_name].listeners.append(listener)
            return listener
        return decorator

    def _on_game_event(self, game_event):
        """Invoke easyevent for a single player GameEvent."""
        event_args = game_event.variables.as_dict()

        for game_event_conversion in self.game_event_conversions[game_event.name]:
            try:
                userid = event_args.pop(game_event_conversion.userid_key)
                event_args[game_event_conversion.player_key] = self.player_dict.from_userid(userid)
            except (KeyError, ValueError):
                event_args[game_event_conversion.player_key] = None

        for game_event_conversion in self.game_event_conversions[game_event.name]:
            player = event_args[game_event_conversion.player_key]
            if player is not None:
                self[game_event_conversion.event_name].fire(event_args, player=player)
