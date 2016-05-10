# EasyPlayer
### What is EasyPlayer?
`EasyPlayer` is a custom package for [Source.Python][sp], designed to make it easier for plugin developers to interfere with the player entities.
`EasyPlayer`'s main feature is the management of what I call "player effects" (like burn and freeze), so that you can safely use the effects without having to worry about someone else using them simultaneously in their own plugins.

Imagine the following scenario *without* `EasyPlayer`: You apply a freeze to a player using `player.move_type = MoveType.NONE`. However, somebody else's plugin had already frozen the player, and only a second after you've applied your freeze, they unfreeze the player to remove their own freeze. This causes your freeze to end prematurely, even if it was supposed to last for multiple seconds.
If everyone were to use `EasyPlayer`, this wouldn't happen, as `EasyPlayer` controls the way these player effects are applied and removed. It makes sure a player doesn't get unfrozen until every freeze applied on him has ended.

### How to use EasyPlayer?
Currently you can call any of the following player effect functions on the player:

    player.burn()
    player.freeze()
    player.noclip()
    player.fly()
    player.godmode()

You can pass in a duration as an optional argument to make the effect temporary (as opposed to permanent). For example: `player.noclip(3)` gives a noclip for three seconds.

All of these effect function calls return a `_PlayerEffect` instance. To remove an infinite effect, or an effect with a duration that hasn't ended yet, store the returned `_PlayerEffect` instance and call `.cancel()` on it:

    freeze = player.freeze(10)
    # Cancel before 10 seconds have passed:
    freeze.cancel()

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely; it simply removes the freeze you've applied, but the player might still be frozen by someone else.

### Anything else EasyPlayer does?
`EasyPlayer` also resets player's gravity on death (because Source engine chose not to reset gravity although it resets all the other properties) and implements `from_userid(userid)` classmethod to get an instance directly from an userid.
You can subclass `EasyPlayer` as you please, and it shouldn't interfere with any of the mechanisms (unless you override some of the methods, obviously). You can create your own player effects to your subclass using the `@PlayerEffect` decorator. See examples from the bottom of `easyplayer/player.py` module.
Finally, I've added `cs_team` and `tf_team` properties which return the player's team as a string which is usable with Source.Python's `is_filters` and `not_filters`.

### How to install and use?
To install `EasyPlayer` on your server with [Source.Python][sp] installed, simply drag and drop the `addons` folder into your game's directory (`csgo`, `cstrike`, `tf2`, etc.), and restart your game server.
To use `EasyPlayer` in your plugins, simply import it using `from easyplayer import EasyPlayer`. You can now either subclass your own player class from it, or use it as-is in your code.
You can also use `from easyplayer import PlayerEffect` to create custom player effects for your subclasses. You should study the `easyplayer` package's content to learn more about how `PlayerEffect`'s work.

[sp]: http://forums.sourcepython.com/
