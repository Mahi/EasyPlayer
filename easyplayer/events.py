from core import AutoUnload
from events.manager import event_manager

__all__ = (
    'Event',
    'EventManager',
    'DEFAULT_PLAYER_GAME_EVENTS',
    'DEFAULT_TWO_PLAYER_GAME_EVENT_MAP',
)

DEFAULT_PLAYER_GAME_EVENTS = {
    'player_jump',
    'player_spawn',
}

DEFAULT_TWO_PLAYER_GAME_EVENT_MAP = {
    'player_blind': ('player_blind', 'player_go_blind'),
    'player_death': ('player_kill', 'player_death'),
    'player_hurt': ('player_attack', 'player_victim'),
}


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

    You can also provide custom GameEvent names if the defaults
    aren't suitable for your needs:

    >>> event_names = {'enter_bombzone', 'exit_bombzone'}
    >>> events = EventManager(player_dict, event_names)
    >>> @events.on('enter_bombzone')
    ... def on_enter_bombzone(player, **eargs):
    ...     assert type(player) == MyCustomPlayer

    By default, all the GameEvents with an attacker and
    a victim have been split up into two events:

    - player_blind => player_blind and player_go_blind
    - player_death => player_kill and player_death
    - player_hurt => player_attack and player_victim

    These can be disabled or modified through the optional
    `two_player_game_event_map` keyword argument:

    >>> my_two_player_game_event_map = {
    ...     # game_event: (attacker_event, victim_event),
    ...     'player_death': ('player_kill', 'player_killed'),
    ...     # Not providing other events disables them!
    ... }
    >>> events = EventManager(
    ...     player_dict,
    ...     two_player_game_event_map=my_two_player_game_event_map
    ... )

    Finally, you can add custom events with `create_event()` and
    fire them using the ´[]` syntax:

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
        player_game_events=DEFAULT_PLAYER_GAME_EVENTS,
        two_player_game_event_map=DEFAULT_TWO_PLAYER_GAME_EVENT_MAP,
    ):
        """Initialize the event manager for a player dict."""
        self.player_dict = player_dict
        self._events = {}
        self.player_game_events = player_game_events
        self.two_player_game_event_map = two_player_game_event_map

        for game_event in self.player_game_events:
            event_manager.register_for_event(game_event, self._on_player_game_event)
            self.create_event(game_event)

        for game_event, easy_events in self.two_player_game_event_map.items():
            event_manager.register_for_event(game_event, self._on_two_player_game_event)
            attacker_event, victim_event = easy_events
            self.create_event(attacker_event)
            self.create_event(victim_event)

    def _unload_instance(self):
        """Automatically unload the GameEvent listeners."""
        for event_name in self.player_game_events:
            event_manager.unregister_for_event(event_name, self._on_player_game_event)

        for event_name in self.two_player_game_event_map.keys():
            event_manager.unregister_for_event(event_name, self._on_two_player_game_event)

    def __getitem__(self, key):
        return self._events[key]

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

    def _on_player_game_event(self, game_event):
        """Invoke easyevent for a single player GameEvent."""
        event_args = game_event.variables.as_dict()
        userid = event_args.pop('userid')
        player = self.player_dict.from_userid(userid)
        self[game_event.name].fire(event_args, player=player)

    def _on_two_player_game_event(self, game_event):
        """Invoke easyevents for a two player GameEvent."""
        event_args = game_event.variables.as_dict()
        try:
            attacker_id = event_args.pop('attacker')
            attacker = self.player_dict.from_userid(attacker_id)
        except KeyError:
            attacker = None

        userid = event_args.pop('userid')
        victim = self.player_dict.from_userid(userid)

        event_args.update(attacker=attacker, victim=victim)
        attacker_event, victim_event = self.two_player_game_event_map[game_event.name]
        self[victim_event].fire(event_args, player=victim)
        if attacker is not None:
            self[attacker_event].fire(event_args, player=attacker)
