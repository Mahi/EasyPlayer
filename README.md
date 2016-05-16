# EasyPlayer
### What is EasyPlayer?
EasyPlayer is a custom package for [Source.Python][sp], designed to make it easier for plugin developers to interfere with player entities.
EasyPlayer's main feature is the ability to manage what I call "player effects" (like burn and freeze), so that you can safely use the effects without having to worry about someone else using them simultaneously in their own plugins.

Imagine the following scenario *without* EasyPlayer: 

1. Someone else's plugin freezes the player using `player.move_type = MoveType.NONE`.
2. You apply a freeze to a player using the same command (although it doesn't do anything since he's already frozen, but you don't know that).
3. The other guy's plugin unfreezes the player using `player.move_type = MoveType.WALK` to remove their own freeze.
4. This causes your freeze to end prematurely, even if it was supposed to last for multiple seconds.

If everyone were to use EasyPlayer, this wouldn't happen as EasyPlayer manages the way these player effects are applied and removed. It makes sure a player doesn't get unfrozen until every freeze applied on him has ended.

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
    freeze.cancel() # Cancel manually before duration has ended

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely; it simply removes the freeze you've applied, but the player might still be frozen by someone else.

### Anything else EasyPlayer does?

Quite a lot actually!

- Resets player's gravity on death, because Source engine doesn't, although it resets all the other properties.
- Implements `Player.from_userid(userid)` classmethod to get an instance directly from an userid.
- Implements `Player.shift_property(prop_name, shift, duration=None)` which shifts an integer property by the provided shift. If a duration was passed, the shift will be reverted after that many seconds have passed.
- Allows easy subclassing of `easyplayer.Player` without interfering with any of the mechanisms (unless you override some of the methods, obviously). You can even create custom effects to your subclass using the `easyplayer.Effect` class. See examples from the bottom of the `easyplayer/player.py` file.
- Implements `cs_team` and `tf_team` properties which return the player's team as a string which is usable with Source.Python's filters.

### How to install and use?
To install EasyPlayer onto your game server:


1. Make sure you have [Source.Python][sp] installed.
2. Download it from [the releases page][rel].
3. Extract the `addons` folder into your game directory (`csgo`, `cstrike`, `tf2`, etc.).
4. Restart your game server.

To use EasyPlayer in your plugins:

- Import it using `from easyplayer import Player`.
- You can either subclass your own player class from it, or use it as-is in your code.
- You can also use `from easyplayer import Effect` to create your own player effects for your subclasses. You should study the `easyplayer` package's content to learn more about how `Effect` works.

[sp]: http://forums.sourcepython.com/
[rel]: https://github.com/Mahi/EasyPlayer/releases
