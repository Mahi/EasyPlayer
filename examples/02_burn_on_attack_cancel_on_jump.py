"""A more complex example that stores EasyPlayer EffectHandlers.

The example plugin burns a player indefinitely whenever they attack
another player, and cancels the burn whenever they jumps.
"""

# Python 3 Imports
from collections import defaultdict

# Source.Python Imports
from players.dictionary import PlayerDictionary

# EasyPlayer import
import easyplayer


# Initialize the PlayerDictionary and EventManager (see example 01).
player_dict = PlayerDictionary(easyplayer.Player)
events = easyplayer.EventManager(player_dict)


# Create a defaultdict of lists for storing the burn EffectHandlers.
# The dict is of the following format: {userid: [burn1, burn2, ...]}.
# Typically you'd probably store these in a Player subclass.
burn_handlers = defaultdict(list)


# Listen to the 'player_hurt' event and pick the 'player' argument.
@events.on('player_hurt')
def _add_burn_on_attack(player, **eargs):

    # Burn the player and store the EffectHandler to 'burn' variable.
    # No duration argument passed means indefinite effect.
    burn = player.burn()

    # Since the burn would otherwise last forever, we store
    # the EffectHandler so that we can end the effect at some point.
    burn_handlers[player.userid].append(burn)


# Listen to the 'player_jump' event and pick the 'player' argument.
@events.on('player_jump')
def _remove_burn_on_jump(player, **eargs):

    # If the player has burn EffectHandlers in his burn list...
    if burn_handlers[player.userid]:

        # Pop (get and remove from the list) one of the handlers.
        # In this case we pop the last inserted burn for performance,
        # since the order doesn't matter as they're all indefinite.
        burn = burn_handlers[player.userid].pop()

        # Finally, cancel the effect with the received EffectHandler.
        burn.cancel()
