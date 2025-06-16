
Maleficer is a Berlin definition rogulike which takes inspiration from tactics games.
The combat of many rogulikes boils down to walking into enemies until they die, and I'm aiming to replace that with a more rich experiance.
I also take inspiration from modern TTRPGs like Trespassor, especially in terms of mechanical clarity. 
(and a vehicle for teaching myself game dev, ecs pattern, etc)

# Dependancies
	- libsdl2-dev
	- export LIBGL_ALWAYS_SOFTWARE=1

# Plot
The player is an ambitous and foolhardy wizard school dropout. They start with some default spells, but learn many more via exploration.

# Spells

## Mechanical Ideas
	- teleportation/forced movement
	- info gathering (bigger sight radius, heartbeat counter)
	- terrain generation (create new hallways)
	- grant status `Foo X` where x ticks down every turn (Bleed 3, Slow 2, etc)


## Resource Ideas (partial alternatives to current cooldowns)
	- Like MTG: 5 different kinds of mana, with some mechanical niche protection
	- Stats: a stat for magic reserves, magnitude, duration, AOE size/range, etc

# Design Questions
	- Why explore the level, (vs doing down asap)
	- What is the progression system?

# Map Plans
	- cave levels
	- laberynth levels
		- locked doors
	- set-piece features

# Arch concerns
	- The Targeting phase and associated components are coupled to spell casting, if we have other things that target that'll need to change
		- Each effect component should have its own target, in case we have dmg+heal on one spell, for exampe
		- In the above case, there can be ambiguity about what the target phase actually sets
	- Processors have verbose names, which include phases. Good hint to break them out to phase-based files. Some procs are shared tho
	- AI behavior probably doesn't *all* want to live in the NPC proc
	- I like context from breadcrumbs, but there is now a search issue with multiple apply functions, multiple Damage things, etc
	- if a condition causes 0 health, death is still only processed after that turn
	- look into integer_scaling for context.present(console)
	- Queries that return nothing can crash sometimes :(
	- EffectArea could be take a radius, or every cell in the effect could have the cmp. Neither is necessarily better for when we eventually have a line spell. The radius is at least easier to track, and line can be another property on EffectArea
	- flash_pos redraws screen first, so the flash and glyph aren't desynced
		- this is the opposite of what flash does. maybe a bad idea?
	- Should it be possible to ascend to a previous level (def not for now)
	- Crosshair is a big exception to how movement works. might be worth its own function
	- Currently, Effects (damage, etc) just go on their sources, and are applied on `effects_to_events` invocation
		- This makes `effects_to_events` a sort of do-everything function
	- When I take a step, ranged enemies shoot me before step completes. feels correct for melee but unintuitive for range.
	- MenuItem is used for actual menus, but not for inventory (not 1:1 with entities)
	- Right now levels are limited to the board size. We could decouple those and have the board "scroll"
	- should we always place the stairs as far back as we can?
	- wet status from water tiles? are we that sort of game?
	- We have two damage process steps, one for player damage, and one for everything else. This means enemies the player would kill don't attack back
# TODO
	- All effects on the targeting entity should get their targets filled in if they haven't already
		- But, only the non-static targets should get cleared, and we don't have a way to store that info
	- better spell learning, unlearn, learn confirm
	- effect application restrictions. (mutilate can't hit traps)
	- spell mods (+1 range, +1 dmg pickups)
	- on-death effects
	- trap-summoner enemy
	- In caves, NPCs shouldn't spawn too close to player
	- break up Arch Concerns into open questions and arch docs
# BUGS
	- Found a wall I was able to walk through.
