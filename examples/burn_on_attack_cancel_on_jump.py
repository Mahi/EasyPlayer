"""An example which burns a player infinitely whenever he attacks
an other player, and gets a burn cancelled whenever he jumps."""

# Python 3 Imports
from collections import defaultdict

# Source.Python Imports
from events import Event

# EasyPlayer import
import easyplayer

# Create a defaultdict of lists used to store players' burn handlers
# The dict is of the following format: {userid: [burn1, burn2, ...]}
_burn_handlers = defaultdict(list)


@Event('player_hurt')
def _add_burn_on_attack(event):

    # Retrieve the player using Player.from_userid(userid)
    player = easyplayer.Player.from_userid(event['attacker'])

    # Burn the player and receive the handler
    # No duration argument passed means infinite effect
    burn = player.burn()

    # Add the burn to player's burns
    _burn_handlers[player.userid].append(burn)


@Event('player_jump')
def _remove_burn_on_jump(event):

    # Retrieve the player using Player.from_userid(userid)
    player = easyplayer.Player.from_userid(event['userid'])

    # If the player has burn handlers in his burn list...
    if _burn_handlers[player.userid]:

        # Pop (get and remove from the list) one of the handlers
        # In this case we pop the last for performance,
        # but the order doesn't matter
        burn = _burn_handlers[player.userid].pop()

        # Cancel the received burn
        burn.cancel()
