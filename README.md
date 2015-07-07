# EasyPlayer
## What is EasyPlayer?
`EasyPlayer` is a custom package for Source.Python, designed to make it easier for plugin developers to interfere with the players.
The core idea is that `EasyPlayer` manages "player effects", like burn, freeze, and noclip, so that you can use them without having to worry about someone else using them.
Normally removing player's freeze using `player.move_type = MoveType.WALK` might also remove a freeze applied by an other plugin, or even drop the player's noclip.
If everyone were to use `EasyPlayer`, this wouldn't happen as it manages the way these player effect calls are made, and doesn't unfreeze the player until every freeze applied on him ends.

## How to use EasyPlayer?
Currently you can call any of the following player effect functinso on the player:

    player.burn()
    player.freeze()
    player.noclip()
    player.fly()
    player.godmode()

To remove any of these effects, simply call the same function again but pass in a zero as an argument: `player.fly(0)` will remove the fly you've applied.
You can also use all of these effects with a duration instead of manually using `tick_delays`, for example: `player.freeze(10)` would freeze the player for 10 seconds.
Keep in mind that none of these function calls interfere with each other, so calling `player.freeze(0)` might not unfreeze the player; it simply removes the permanent freeze you've applied, but the player might still be frozen by a freeze applied by someone else.
Also, `player.freeze(0)` cannot remove a freeze with a custom duration, so you can't remove `player.freeze(10)` at 5 seconds using `player.freeze(0)`. In cases like this, you should just use the permanent freeze `player.freeze()` and manually call `player.freeze(0)` when you want to unfreeze the player.

## Anything else EasyPlayer does?
You can subclass `EasyPlayer` as you please, and it shouldn't interfere with any of my mechanisms (unless you override some of the methods, obviously). You can even create your own player effects to your subclass using the `PlayerEffect` decorator.
`EasyPlayer` also resets gravity on every round (because Source engine chose not to reset gravity although it resets all the other properties) and implements `from_userid(userid)` classmethod to get an instance directly from an userid.
There's even a built-in restriction system in `EasyPlayer`! You can use it by accessing player's `restrictions` set to restrict him from using certain weapons.
The set should contain classnames of the weapons that are meant to be restricted:

    from filters.weapons import WeaponClassIter
    # Allow only scout and knife
    player.restrictions = set(WeaponClassIter(return_types='classname')) - {'weapon_knife', 'weapon_scout'}
