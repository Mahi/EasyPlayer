from core import AutoUnload
from events.manager import event_manager

__all__ = (
    'Event',
    'EventManager',
    'DUO_PLAYER_GAME_EVENTS',
    'SOLO_PLAYER_GAME_EVENTS',
)


SOLO_PLAYER_GAME_EVENTS = {'player_spawn', 'player_jump'}
DUO_PLAYER_GAME_EVENT_MAP = {
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
    and all the GameEvent's userids will be converted to your
    custom Player entities automatically:

    >>> player_dict = PlayerDictionary(MyCustomPlayer)
    >>> events = easyevents.EventManager(player_dict)
    >>> @events.on('player_kill')
    ... def on_player_kill(player, victim, **event_args):
    ...     assert type(player) == MyCustomPlayer
    ...     assert type(victim) == MyCustomPlayer

    Other features include:
    - Event args being forwared with Python's `**dict` unpacking syntax,
      allowing you to cherry-pick which arguments you need.
    - player_death being split up into player_kill and player_death
    - player_hurt being split up into player_attack and player_victim
    - Adding custom events with the `create_event()` method
    """

    def __init__(self, player_dict):
        """Initialize the event manager for a player dict."""
        self.player_dict = player_dict
        self._events = {}

        for game_event in SOLO_PLAYER_GAME_EVENTS:
            event_manager.register_for_event(game_event, self._on_solo_player_game_event)
            self.create_event(game_event)

        for game_event, easy_events in DUO_PLAYER_GAME_EVENT_MAP.items():
            event_manager.register_for_event(game_event, self._on_duo_player_game_event)
            attacker_event, victim_event = easy_events
            self.create_event(attacker_event)
            self.create_event(victim_event)

    def _unload_instance(self):
        """Automatically unload the GameEvent listeners."""
        for event_name in SOLO_PLAYER_GAME_EVENTS:
            event_manager.unregister_for_event(event_name, self._on_solo_player_game_event)

        for event_name in DUO_PLAYER_GAME_EVENT_MAP.keys():
            event_manager.unregister_for_event(event_name, self._on_duo_player_game_event)

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

    def _on_solo_player_game_event(self, game_event):
        """Invoke easyevent for a solo player GameEvent."""
        event_args = game_event.variables.as_dict()
        userid = event_args.pop('userid')
        player = self.player_dict.from_userid(userid)
        self[game_event.name].fire(event_args, player=player)

    def _on_duo_player_game_event(self, game_event):
        """Invoke easyevents for a duo player GameEvent."""
        event_args = game_event.variables.as_dict()
        try:
            attacker_id = event_args.pop('attacker')
            attacker = self.player_dict.from_userid(attacker_id)
        except KeyError:
            attacker = None

        userid = event_args.pop('userid')
        victim = self.player_dict.from_userid(userid)

        event_args.update(attacker=attacker, victim=victim)
        attacker_event, victim_event = DUO_PLAYER_GAME_EVENT_MAP[game_event.name]
        self[victim_event].fire(event_args, player=victim)
        if attacker is not None:
            self[attacker_event].fire(event_args, player=attacker)
