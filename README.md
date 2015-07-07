# EasyPlayer
## What is it?
`EasyPlayer` is a custom package for Source.Python, designed to make it easier for plugin developers to interfere with the players.
The core idea is that `EasyPlayer` manages "player effects" like burn, freeze, and noclip, so that you can use them without having to worry about someone else using them.
Normally removing player's freeze using `player.move_type = MoveType.WALK` might also remove a freeze applied by an other plugin, or even drop the player's noclip.
If everyone were to use `EasyPlayer`, this wouldn't happen.

## How to use?
You can use all of these "player effects" with a duration instead of manually using `tick_delays`.
For example: `player.freeze(10)` would freeze the player for 10 seconds.
To permanently freeze a player, pass no argument at all: `player.freeze()`.
To remove this infinite freeze, pass in a zero: `player.freeze(0)`.
Notice that none of these calls interfere with each other (other than `player.freeze(0)` removing the permanent freeze), they apply a freeze of their own and removing one doesn't completely unfreeze the player, unless there are no other freezes left.


`EasyPlayer` also resets gravity on every round and implements
`from_userid(userid)` classmethod to get an instance directly
from an userid. You can also use `restrictions` set to restrict
player from using certain weapons. The set should contain classnames
of the weapons that are meant to be restricted.
