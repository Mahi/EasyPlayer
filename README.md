# EasyPlayer
EasyPlayer is a custom package for [Source.Python][sp],
designed to make it easier for plugin developers to interfere with player entities and events.

## Player Effects

EasyPlayer's original purpose is the ability to manage what I call "player effects" (burn, freeze, noclip...),
so that you can safely use the effects without having to worry about someone else using them simultaneously in their own plugins.

*Without* EasyPlayer installed, you might run into a scenario where your plugin applies an effect on a player,
only to have someone elses plugin immediately cancel the effect.
This is caused by both plugins modifying the same player's variable, for example `player.move_type`:

1. Plugin A sets `player.move_type = MoveType.NONE` to freeze a player.
2. Plugin B sets `player.move_type = MoveType.NOCLIP` to noclip the same player.
3. Plugin A cancels the freeze with `player.move_type = MoveType.WALK`.
4. Plugin B's noclip was also cancelled, and the player lost his noclip for good.

If everyone were to use EasyPlayer, this wouldn't happen as EasyPlayer manages the way these player effects are applied and removed.
It makes sure a player doesn't lose an effect until every effect of that type has ended.

### How to use PlayerEffects?
Currently you can call any of the following player effect functions on the player:

    player.noclip()
    player.freeze()
    player.fly()
    player.burn()
    player.noblock()
    player.godmode()

You can pass in a duration as an optional argument to make the effect temporary (as opposed to permanent).
For example: `player.noclip(3)` gives a noclip for three seconds.

All of these effect calls return an `_EffectHandler` instance.
To remove an infinite effect, or to prematurely cancel an effect with a duration,
store the returned instance and call `.cancel()` on it:

```py
freeze = player.freeze(duration=10)  # Keywording is optional!
freeze.cancel()  # Cancel manually before duration has ended
```

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely;
it simply removes the freeze you've applied, but the player might still be frozen by someone else.

## Events

EasyPlayer also provides an `EventManager` class to manage both GameEvents and custom events in an easy and uniform manner.
It simplifies Source.Python's event management by replacing all the awkward `userid`s with Player instances of your choice.
In other words, your event listeners will be receiving your player objects as arguments, instead of userids.

While at it, I decided to split the player events that have an attacker and a victim into two:
- `player_death` is now `player_attack` and `player_death`
- `player_hurt` is now `player_attack` and `player_victim`

This allows you to more easily react to a player killing an opponent vs a player dying.

### How to use the easy events?
Simply create a Source.Python `PlayerDictionary` like you normally would, and forward it to the `EventManager` constructor:

```py
player_dict = PlayerDictionary(MyPlayer)  # MyPlayer doesn't have to subclass EasyPlayer, but why wouldn't it? ;)
events = easyplayer.EventManager(player_dict)  # Will now use your player_dict to find players for events!

@events.on('player_kill')  # Remember, new events!
def on_player_kill(player, victim, **eargs):  # You can pick any arguments from the event args (eargs)
    print(player.my_custom_attribute)  # No userids, no index conversions...
```

That's easy.

## Anything else?

EasyPlayer also:

- Resets player's gravity, color, and more on death, because Source engine only resets *some* of the player's properties.
- Implements `Player.shift_property(prop_name, shift, duration=None)` which shifts an integer property by the provided shift.
  If a duration was passed, the shift will be reverted after that many seconds have passed.
- Allows easy subclassing of `easyplayer.Player` without interfering with any of the mechanisms.
  You can even create custom effects to your subclass using the `easyplayer.Effect` class.
  See examples at the bottom of the `easyplayer/player.py` file.
- Implements `cs_team` and `tf_team` properties which return the player's team as a string, which is usable with Source.Python's filters.
- Implements `hip_location`, `stomach_location`, and `chest_location` for the player.

## How to install and use?

To install EasyPlayer onto your game server:

1. Make sure you have [Source.Python][sp] installed.
2. Download it from [the releases page][rel].
3. Extract the `addons` folder into your game directory (`csgo`, `cstrike`, `tf2`, etc.).
4. Restart your game server.

To use EasyPlayer in your plugins:

- Import it using `import easyplayer`.
- See `examples` directory to get started with the usage! :)

[sp]: http://forums.sourcepython.com/
[rel]: https://github.com/Mahi/EasyPlayer/releases
