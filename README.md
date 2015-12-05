# EasyPlayer
### What is EasyPlayer?
`EasyPlayer` is a custom package for [Source.Python][sp], designed to make it easier for plugin developers to interfere with the player entities.
The main feature is `EasyPlayer`'s management of what I call "player effects", like burn and freeze, so that you can safely use them without having to worry about someone else changing them in their own plugins.

Imagine the following scenario *without* `EasyPlayer`: You apply a freeze to a player using `player.move_type = MoveType.NONE`. Meanwhile, someone else (an other developer) has their plugin freeze everyone for 2 seconds whenever they're shot. We now have two plugins interacting with `player.move_type`, and it might cause the following:

 1. Player X gets shot and thus gets his `move_type` set to `MoveType.NONE` by the acts of the other developer's plugin.
 2. A second later, your plugin applies your freeze due to whatever reason (so this does nothing, he's already set to `MoveType.NONE`).
 3. An other second later (2 seconds since player X was shot) the other developer's plugin removes his freeze using `player.move_type = MoveType.WALK`.
 4. Your freeze, which was supposed to last more than a second, was also removed because of this.

If everyone were to use `EasyPlayer`, this wouldn't happen as it controls the way these player effects are applied and removed. `EasyPlayer` makes sure a player doesn't unfreeze until every freeze applied on him has ended.

### How to use EasyPlayer?
Currently you can call any of the following player effect functions on the player:

    player.burn()
    player.freeze()
    player.noclip()
    player.fly()
    player.godmode()

You can pass in a duration as an optional argument to make the effect temporary (as opposed to permanent): `player.noclip(3)` gives a noclip for three seconds.

All of these effects return a `_PlayerEffect` instance. To remove an infinite effect, or an effect with a duration that hasn't ended yet, store the returned `_PlayerEffect` instance and call `.cancel()` on it:

    freeze = player.freeze(10)
    # 5 seconds later:
    freeze.cancel()

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely; it simply removes the freeze you've applied, but the player might still be frozen by someone else.

### Anything else EasyPlayer does?
You can subclass `EasyPlayer` as you please, and it shouldn't interfere with any of the mechanisms (unless you override some of the methods, obviously). You can create your own player effects to your subclass using the `@PlayerEffect` decorator. See examples from the bottom of `easyplayer/player.py` module.
`EasyPlayer` also resets player's gravity on death (because Source engine chose not to reset gravity although it resets all the other properties) and implements `from_userid(userid)` classmethod to get an instance directly from an userid.
There's even a built-in restriction system in `EasyPlayer`! You can use it by accessing player's `restrictions` set to restrict him from using certain weapons. Here's an example:

    from easyplayer import EasyPlayer
    from filters.weapons import WeaponClassIter
    from events import Event
 
    @Event('player_spawn')
    def on_spawn(userid, **eargs):
        player = EasyPlayer.from_userid(userid)

        # Restrict everything
        player.restrictions = set(WeaponClassIter(return_types='classname'))

        # Except knife
        player.restrictions.remove('weapon_knife')

        # Actually, allow awp and deagle too
        player.restrictions -= {'weapon_awp', 'weapon_deagle'}

Finally, I've added `cs_team` and `tf_team` properties which return the player's team as a string which is usable with Source.Python's `is_filters` and `not_filters`.

### How to install and use?
To install `EasyPlayer` on your server with [Source.Python][sp] installed, simply drag and drop the `addons` folder into your game's directory (`csgo`, `cstrike`, `tf2`, etc.), and restart your game server.
To use `EasyPlayer` in your plugins, simply import it using `from easyplayer import EasyPlayer`. You can now either subclass your own player class from it, or use it as-is in your code.
You can also use `from easyplayer import PlayerEffect` to create custom player effects for your subclasses. You should study the `easyplayer` package's content to learn more about how `PlayerEffect`'s work.

[sp]: http://forums.sourcepython.com/
