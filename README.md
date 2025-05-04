
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
	- resouce exchange (health for mana etc)
	- grant status `Foo X` where x ticks down every turn (Bleed 3, Slow 2, etc)


## Resource Ideas
	- Like MTG: 5 different kinds of mana, with some mechanical niche protection
	- Stats: a stat for magic reserves, magnitude, duration, AOE size/range, etc

# Design Questions
	- Why explore the level, (vs doing down asap)
	- What is the progression system?

# Arch concerns
	- The Targeting phase and associated components are coupled to spell casting, if we have other things that target that'll need to change
		- Each effect component should have its own target, in case we have dmg+heal on one spell, for exampe
		- In the above case, there can be ambiguity about what the target phase actually sets
	- Processors have verbose names, which include phases. Good hint to break them out to phase-based files. Some procs are shared tho
	- We probably want a death processor rather than handling it at the end of dmg_proc
	- AI behavior probably doesn't *all* want to live in the NPC proc

# TODO:
	- Figure our something better for NPC behavior (better follow)
	- Should damage actually fizzle if the source is dead? We could just put src.name on the event, which allows the entity to die without issue.
	- All effects on the targeting entity should get their targets filled in if they haven't already
		- But, only the non-static targets should get cleared, and we don't have a way to store that info
	- AOE spells, targeting
