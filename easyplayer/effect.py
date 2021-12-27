import collections
from typing import Callable, Dict, List, Optional, Type, TypeVar, Union

from listeners.tick import Delay


__all__ = (
    'Effect',
    'EffectHandler',
)


Number = Union[int, float]
TargetKey = TypeVar('TargetKey')
TargetType = TypeVar('TargetType')
TargetFunction = Callable[[TargetType], None]


class Effect:
    """Manage multiple simultaneous state changes by different sources.

    An effect allows the same state to be changed simultaneously by
    storing _effect handlers_, and ensuring the state isn't reverted
    until all effect handlers have been cancelled:

    >>> freeze1 = player.freeze(duration=4)
    >>> freeze2 = player.freeze(duration=2)
    >>> sleep(1)
    >>> freeze2.cancel()  # Player still frozen by `freeze1`!

    To use the Effect class, you must subclass it and override
    the `identify_target()` method, with an unique method that can
    identify your objects from each other:

    >>> class PlayerEffect(Effect):
    ...     def identify_target(self, target):
    ...         return target.userid

    This result must be hashable, as it's used as a key in a dict.

    From there on, an effect is used like a `property` instance,
    but instead of `fget` and `fset`, it has `on_f` and `off_f`.
    Just like with `property`, these can be passed to the `__init__`,
    or provided later via a decorator:

    >>> class Player:
    ...
    ...     @PlayerEffect
    ...     def freeze(self):
    ...         self._frozen = True
    ...
    ...     @freeze.off
    ...     def freeze(self):
    ...         self._frozen = False
    ...

    Applying an effect on a player will stores an effect handlers,
    which is returned by the `player.freeze()` method call.
    This handler is used internally to identify when the state should
    change, and can be used to prematurely cancel the effect.
    """

    def __init__(self, on_f: Optional[TargetFunction]=None, off_f: Optional[TargetFunction]=None):
        """Initialize an effect with on and off functions."""
        self.on_f = on_f
        self.off_f = off_f
        self._effect_handlers: Dict[TargetKey, List[EffectHandler]] = collections.defaultdict(list)

    def identify_target(self, target: TargetType):
        raise NotImplementedError(f'{type(self).__name__}.identify_target()')

    def on(self, on_f: TargetFunction) -> 'Effect':
        """Decorator for updating the effect's on function."""
        return type(self)(on_f, self.off_f)

    def off(self, off_f: TargetFunction) -> 'Effect':
        """Decorator for updating the effect's off function."""
        return type(self)(self.on_f, off_f)

    def _apply(self, handler: 'EffectHandler'):
        """Apply an new effect from a handler.

        Calls the on-function if it was the first effect of its kind.
        """
        key = self.identify_target(handler.target)
        if len(self._effect_handlers[key]) == 0:
            self.on_f(handler.target)
        self._effect_handlers[key].append(handler)

    def _cancel(self, handler: 'EffectHandler'):
        """Cancel an effect from a handler.

        Calls the off-function if it was the last effect of its kind.
        """
        key = self.identify_target(handler.target)
        self._effect_handlers[key].remove(handler)
        if len(self._effect_handlers[key]) == 0:
            self.off_f(handler.target)

    def is_active_for(self, target: TargetType) -> bool:
        """Check if the effect is active for a target."""
        key = self.identify_target(target)
        return len(self._effect_handlers[key]) > 0

    def __get__(self, target: TargetType, type_: Optional[Type[TargetType]]=None):
        """Get an effect handler when called via a descriptor."""
        if target is None:
            return self
        return EffectHandler(self, target)


class EffectHandler:
    """Handler allows using effects directly through a target instance.

    Accessing an effect through a target instance with `target.effect`
    will return an effect handler, that can be called like a function
    to actually apply the effect:

    >>> handler = player.freeze
    >>> handler()  # Apply the `freeze` effect on `player` object
    >>> handler.cancel()  # Cancel the effect

    The `handler()` call returns the handler itself,
    to allow a simpler and more natural syntax of:

    >>> handler = player.freeze()
    >>> handler.cancel()

    Handler also allows a duration to be applied on an effect via
    an additional duration parameter. Effects with a duration can
    also be cancelled manually via the cancel method:

    >>> freeze = player.freeze(duration=5)  # Keywording is optional
    >>> sleep(1)
    >>> freeze.cancel()
    """

    def __init__(self, effect: Effect, target: TargetType):
        """Initialize a handler which links an effect to a target."""
        self.effect = effect
        self.target = target
        self._delay: Optional[Delay] = None

    def __call__(self, duration: Optional[Number]=None) -> 'EffectHandler':
        """Activate the handler's effect for its target.

        If a duration is provided, the effect will automatically
        be cancelled after the duration has passed.
        """
        self.effect._apply(self)
        if duration is not None:
            self._delay = Delay(duration, self.effect._cancel, (self,))
        return self

    def cancel(self):
        """Cancel the applied effect.

        Also cancels the delay if a duration was initially provided.
        """
        if self._delay is not None:
            self._delay.cancel()
            self._delay = None
        self.effect._cancel(self)

    def is_active(self) -> bool:
        """Check if the effect is currently active on a target.

        This allows the easier syntax of:

        >>> player.freeze.is_active()

        Compared to accessing the Effect instance directly:

        >>> Player.freeze.is_active_for(player)
        """
        return self.effect.is_active_for(self.target)
