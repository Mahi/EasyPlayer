"""An example to give a 2 second noclip whenever a player jumps."""

# Source.Python Imports
from events import Event

# EasyPlayer import
import easyplayer


@Event('player_jump')
def _give_noclip_on_jump(event):

    # Retrieve the player using Player.from_userid(userid)
    player = easyplayer.Player.from_userid(event['userid'])

    # Grant 2 second noclip for the player
    # Keyword argument is optional, so player.noclip(2) also works
    player.noclip(duration=2)
    # In this example, there's no need to store the effect handler,
    # as the effect is cancelled automatically
