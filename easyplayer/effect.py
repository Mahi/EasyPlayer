import collections

from listeners.tick import Delay

__all__ = (
    'Effect',
)


class Effect:
    """Effect that manages simultaneous access from multiple sources.

    An effect is like a `property` instance. Instead of get and set
    functions, it has on and off functions. These can be passed in
    to the __init__, or a decorator can be used similar to property:

    >>> class Player:
    ...
    ...     @Effect
    ...     def freeze(self):
    ...         self._frozen = True
    ...
    ...     @freeze.off
    ...     def freeze(self):
    ...         self._frozen = False
    ...

    The effect manages access from multiple sources by using a counter.
    When the effect is applied on a player, the effect's count for
    the player gets incremented by one. If the count was at zero,
    the on function will be called. When an effect is cancelled from
    a player, his counter will decrement by one. This doesn't guarantee
    that the actual effect gets disabled, as someone else might still
    have an effect of the same type going on. Once the counter
    hits zero, the off function will be called. Both function calls
    get the player as the sole argument.
    """

    def __init__(self, on_f=None, off_f=None):
        """Initialize an effect with on and off functions."""
        self.on_f = on_f
        self.off_f = off_f
        self._counter = collections.defaultdict(int)  # {userid: count}

    def on(self, on_f):
        """Decorator for updating the effect's on function."""
        return type(self)(on_f, self.off_f)

    def off(self, off_f):
        """Decorator for updating the effect's off function."""
        return type(self)(self.on_f, off_f)

    def enable_for(self, player):
        """Increment the effect's count for a player by one.

        Calls the on function if the count was at zero.
        """
        self._counter[player.userid] += 1
        if self._counter[player.userid] == 0:
            self.on_f(player)

    def disable_for(self, player):
        """Decrement the effect's count for a player by one.

        Calls the off function if the count hits zero.
        """
        self._counter[player.userid] -= 1
        if self._counter[player.userid] == 0:
            self.off_f(player)

    def is_enabled_for(self, player):
        """Check if the effect is enabled for a player."""
        return self._counter[player.userid] > 0


class _EffectHandler:
    """Natural way for using effects directly through a player instance.

    Instead of:

        PlayerClass.my_effect.enable_for(player_instance)

    You simply write:

        player_instance.my_effect()

    This will return a handler instance with a cancel method to cancel
    the effect:

        effect = player_instance.my_effect()
        effect.cancel()

    Handler also allows a duration to be applied on an effect via
    an additional duration parameter. Effects with a duration can
    also be cancelled manually via the cancel method:

        freeze = player.freeze(duration=5)  # Keywording is optional
        freeze.cancel()  # Cancel manually before 5 seconds has passed
    """

    def __init__(self, effect, player):
        """Initialize a handler which links an effect and a player."""
        self.effect = effect
        self.player = player
        self._delay = None

    def __call__(self, duration=None):
        """Enable the effect for the player.

        If a duration is passed, the effect will get automatically
        cancelled after the duration has ended.
        """
        self.effect.enable_for(self.player)
        if duration is not None:
            self._delay = Delay(duration, self.effect.disable_for, self.player)
        return self

    def cancel(self):
        """Cancel the enabled effect.

        Also cancels the delay if a duration was passed when enabled.
        """
        if self._delay is not None:
            self._delay.cancel()
            self._delay = None
        self.effect.disable_for(self.player)

    def is_enabled(self):
        """Check if the effect is enabled for the player."""
        return self.effect.is_enabled_for(self.player)
