
Maleficer is a Berlin definition rogulike which takes inspiration from tactics games.
The combat of many rogulikes boils down to walking into enemies until they die, and I'm aiming to replace that with a more rich experiance.
I also take inspiration from modern TTRPGs like Trespassor, especially in terms of mechanical clarity.

# Dependancies
	- libsdl2-dev
	- export LIBGL_ALWAYS_SOFTWARE=1

# Plot
The player is an ambitous and foolhardy wizard school dropout. He starts with some default spells, but learns many more via exploration.


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

# Future work
Could work on damage system next
Could make menus
