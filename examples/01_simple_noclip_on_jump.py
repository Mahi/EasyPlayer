"""A simple example that introduces EasyPlayer usage.

The example plugin gives a player 2 second noclip whenever they jump.
"""

# Source.Python imports
from players.dictionary import PlayerDictionary

# EasyPlayer imports
import easyplayer


# Create a PlayerDictionary for managing the players on the server.
# This is something you should do with or without EasyPlayer.
player_dict = PlayerDictionary(easyplayer.Player)

# Create an easy EventManager to use EasyPlayer instances with events.
# This makes it so you don't have to play around with userids anymore.
events = easyplayer.EventManager(player_dict)


# Define a listener for 'player_jump' event, and pick
# the 'player' argument from the event arguments (eargs).
@events.on('player_jump')
def _give_noclip_on_jump(player, **eargs):

    # Grant 2 second noclip for the player.
    # Keyword argument is optional, so 'player.noclip(2)' also works.
    player.noclip(duration=2)
    # In this example, there's no need to store the effect handler,
    # as the effect is cancelled automatically after 2 seconds.
