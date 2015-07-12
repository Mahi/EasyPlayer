# EasyPlayer
### What is EasyPlayer?
`EasyPlayer` is a custom package for Source.Python, designed to make it easier for plugin developers to interfere with the players.
The core idea is that `EasyPlayer` manages "player effects", like burn, freeze, and noclip, so that you can use them without having to worry about someone else using them.
Normally removing player's freeze using `player.move_type = MoveType.WALK` might also remove a freeze applied by an other plugin, or even drop the player's noclip.
If everyone were to use `EasyPlayer`, this wouldn't happen as it manages the way these player effect calls are made, and doesn't unfreeze the player until every freeze applied on him ends.

### How to use EasyPlayer?
Currently you can call any of the following player effect functions on the player:

    player.burn()
    player.freeze()
    player.noclip()
    player.fly()
    player.godmode()
    
You can pass in a duration as the parameter, to make the effect only temporary: `player.noclip(3)` gives 3 second noclip.

All of these effects return a `_PlayerEffect` instance. To remove an infinite effect, or an effect with a duration that hasn't ended yet, store the returned `_PlayerEffect` instance and call `.cancel()` on it:

    freeze = player.freeze(10)
    # 5 seconds later:
    freeze.cancel()

Keep in mind that none of these function calls interfere with each other, so calling `.cancel()` might not unfreeze the player completely; it simply removes the freeze you've applied, but the player might still be frozen by a freeze applied by someone else.

### Anything else EasyPlayer does?
You can subclass `EasyPlayer` as you please, and it shouldn't interfere with any of my mechanisms (unless you override some of the methods, obviously). You can create your own player effects to your subclass using the `PlayerEffect` decorator.
`EasyPlayer` also resets gravity on every round (because Source engine chose not to reset gravity although it resets all the other properties, duh) and implements `from_userid(userid)` classmethod to get an instance directly from an userid.
There's even a built-in restriction system in `EasyPlayer`! You can use it by accessing player's `restrictions` set to restrict him from using certain weapons. Here's an example:

    from easyplayer import EasyPlayer
    from filters.weapons import WeaponClassIter
    from events import Event
    
    @Event
    def player_spawn(game_event):
        player = EasyPlayer.from_userid(game_event.get_int('userid'))
    
        # Allow only scout and knife
        player.restrictions = set(WeaponClassIter(return_types='classname')) - {'weapon_knife', 'weapon_scout'}
    
        # Actually, allow awp too
        player.restrictions.remove('weapon_awp')

### Final words
Keep in mind that `EasyPlayer` is still in beta, and might contain some bugs.
If you have any suggestions for improvements, or possibly new player effects you'd like to see, leave an issue (or a pull request if you prefer helping with the coding) to this repository and I'll answer asap.
