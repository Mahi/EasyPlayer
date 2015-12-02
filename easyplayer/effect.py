"""Provides the PlayerEffect class for creating player effects."""

# Python 3 Impors
from listeners.tick import tick_delays


class _PlayerEffect(object):
    """Class for player effects like freeze and burn."""

    def __init__(self, descriptor_obj, player):
        """Initialize a new effect for a player.

        This doesn't enable the effect yet, it simply prepares it.
        The effect can be enabled via the _enable method,
        or via parenthesis which invokes the __call__.
        """
        self._descriptor_obj = descriptor_obj
        self._player = player
        self._delay = None

    def _enable(self, duration=None, *args, **kwargs):
        """Enable the effect.

        Add the new effect to a player's effects and call
        the descriptor object's on function with the provided
        arguments and keyword arguments.

        If duration is a positive integer, adds a delay which
        automatically disables the effect after the duration.
        """
        if isinstance(duration, int) and duration > 0:
            self._delay = tick_delays.delay(duration, self._disable)
        self._player._effects[self._descriptor_obj].append(self)
        self._descriptor_obj._on_f(self._player, *args, **kwargs)

    def __call__(self, duration=None, *args, **kwargs):
        """Override () to call the _enable method."""
        self._enable(duration, *args, **kwargs)
        return self

    def _disable(self, *args, **kwargs):
        """Disable the effect.

        Remove the effect from a player's effects and if there are
        no more effects of this type, calls the descriptor object's
        off function with the provided arguments.
        """
        self._player._effects[self._descriptor_obj].remove(self)
        if not self._player._effects[self._descriptor_obj]:
            self._descriptor_obj._off_f(self._player, *args, **kwargs)

    def cancel(self, *args, **kwargs):
        """Cancel the tick_delay and disable the effect."""
        if self._delay is not None:
            tick_delays.cancel_delay(self._delay)
            self._delay = None
        self._disable(*args, **kwargs)


class PlayerEffect(object):
    """Decorator class similar to property() but for player effects."""

    def __init__(self, on_f=None, off_f=None):
        """Initialize a player effect with the given functions."""
        self._on_f = on_f
        self._off_f = off_f

    def on(self, on_f):
        """Decorator to add an on function to the effect."""
        return type(self)(on_f, self._off_f)

    def off(self, off_f):
        """Decorator to add an off function to the effect."""
        return type(self)(self._on_f, off_f)

    def __get__(self, obj, objtype=None):
        """Descriptor method to get the actual player effect.

        Create a new _PlayerEffect instance for the player,
        which can then be called with the parenthesis
        to activate the effect immediately.
        """
        if obj is None:
            return self
        return _PlayerEffect(self, obj)
