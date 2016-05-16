# EasyPlayer
### What is EasyPlayer?
EasyPlayer is a custom package for [Source.Python][sp], designed to make it easier for plugin developers to interfere with player entities.
EasyPlayer's main feature is the management of what I call "player effects" (like burn and freeze), so that you can safely use the effects without having to worry about someone else using them simultaneously in their own plugins.

Imagine the following scenario *without* EasyPlayer: You apply a freeze to a player using `player.move_type = MoveType.NONE`. However, someone else's plugin had already frozen the player, and only a second after you've applied your freeze, they unfreeze the player using `player.move_type = MoveType.WALK` to remove their own freeze. This causes your freeze to end prematurely, even if it was supposed to last for multiple seconds.
If everyone were to use EasyPlayer, this wouldn't happen as `EasyPlayer` manages the way these player effects are applied and removed. It makes sure a player doesn't get unfrozen until every freeze applied on him has ended.

### How to use EasyPlayer?
Currently you can call any of the following player effect functions on the player:

    player.noclip()
    player.freeze()
    player.fly()
    player.burn()
    player.noblock()
    player.godmode()

You can pass in a duration as an optional argument to make the effect temporary (as opposed to permanent). For example: `player.noclip(3)` gives a noclip for three seconds.

All of these effect function calls return an `_EffectHandler` instance. To remove an infinite effect, or an effect with a duration that hasn't ended yet, store the returned instance and call `.cancel()` on it:

    freeze = player.freeze(duration=10)  # Keywording is optional!
    # Cancel before 10 seconds have passed:
    freeze.cancel()

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely; it simply removes the freeze you've applied, but the player might still be frozen by someone else.

### Anything else EasyPlayer does?
EasyPlayer also resets player's gravity on death (because Source engine chose not to reset gravity although it resets all the other properties) and implements `from_userid(userid)` classmethod to get an instance directly from an userid. I've also added `shift_property(prop_name, shift, duration=None)` which shifts player's integer property by the provided shift. If the duration was passed, this shift will be reverted after that many seconds.
You can easily subclass `easyplayer.Player` as you please, and it shouldn't interfere with any of the mechanisms (unless you override some of the methods, obviously).
You can even create your own player effects to your subclass using the `easyplayer.Effect` class. See examples from the bottom of the `easyplayer/player.py` file.
Finally, I've added `cs_team` and `tf_team` properties which return the player's team as a string which is usable with Source.Python's filters.

### How to install and use?
To install EasyPlayer on your server with [Source.Python][sp] installed, simply download it from [the releases page][rel], drag&drop the `addons` folder into your game's directory (`csgo`, `cstrike`, `tf2`, etc.), and restart your game server.
To use EasyPlayer in your plugins, import it using `from easyplayer import Player`. You can now either subclass your own player class from it, or use it as-is in your code.
You can also use `from easyplayer import Effect` to create your own player effects for your subclasses. You should study the `easyplayer` package's content to learn more about how `Effect` works.

[sp]: http://forums.sourcepython.com/
[rel]: https://github.com/Mahi/EasyPlayer/releases
