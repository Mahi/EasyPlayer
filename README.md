# EasyPlayer
EasyPlayer is a custom package for [Source.Python][sp],
designed to make it easier for plugin developers to interact with player entities.

## Player Effects

EasyPlayer's main purpose is the ability to manage "player effects", like burn, freeze, and noclip.
Player effects allow you to safely apply effects without having to worry about another plugin using them simultaneously.

*Without* EasyPlayer, you might run into a scenario where your plugin applies an effect on a player,
only to have someone elses plugin immediately cancel the effect:

1. Plugin A freezes a player for 2 seconds.
2. Plugin B freezes the player for 5 seconds.
3. Plugin A unfreezes the player after 2 seconds.
4. Plugin B's freeze was cancelled prematurely.

EasyPlayer ensures this doesn't happen, as it checks that all freezes are cancelled before unfreezing the player.

### How to use Player Effects?

Currently you can call any of the following effects on a player:

    player.noclip()
    player.freeze()
    player.fly()
    player.burn()
    player.noblock()
    player.godmode()

You can pass in a duration as an optional argument to make the effect temporary (as opposed to permanent).
For example, `player.noclip(3)` gives a noclip for three seconds.

All of these effect calls return an `EffectHandler` instance.
To remove an infinite effect, or to prematurely cancel an effect with a duration,
store the returned instance and call `.cancel()` on it:

```py
freeze = player.freeze(duration=10)  # Keywording is optional!
freeze.cancel()  # Cancel manually before duration has ended
```

Keep in mind that none of these function calls interfere with each other,
so calling `.cancel()` might not unfreeze the player completely; the player might still be frozen by another effect.

## EasyPlayer helpers

EasyPlayer also provides additional helper functions and features to make player entity usage seamless:

- Automatically resets most attributes like gravity and color on death.
- Implements `shift_property(prop_name, shift[, duration])` to shift a numeric property by the provided `shift`.
- Allows custom effects to be created on a subclass by using the `PlayerEffect` class.
  See how to use it at the bottom of the `easyplayer/player.py` file.
- Implements `hip_location`, `stomach_location`, and `chest_location` for the player.

## How to install and use?

To install EasyPlayer onto your game server:

1. Make sure you have [Source.Python][sp] installed.
2. Download it from [the releases page][rel].
3. Extract the `addons` folder into your game's directory (e.g. `csgo`).
4. Restart your game server.

To use EasyPlayer in your plugins:

- Import it using `from easyplayer import EasyPlayer`.
- Use it like you would use Source.Python's `players.entity.Player` class.

[sp]: http://forums.sourcepython.com/
[rel]: https://github.com/Mahi/EasyPlayer/releases
