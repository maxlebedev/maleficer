# Maleficer 
This is a classic roguelike with focus on tactical combat.
The baseline combat of many rogulikes boils down to walking into enemies until they die, and I'm aiming to replace that with a more rich experiance.
I also take inspiration from modern TTRPGs like Trespassor, especially in terms of mechanical clarity. 
(and a vehicle for teaching myself game dev, ecs pattern, etc)
<img width="1935" height="1079" alt="maleficer_mmenu_screenshot" src="https://github.com/user-attachments/assets/58c3c0bb-0a3b-4e94-b47b-a948fa17355c" />

# Inspiration
    - classic roguelikes
        * Nethack
        * Shattered Pixed Dungeon
        * Dungeons of Dredmor
    - Modern TTPGS like Trespassor
    - Rift Wizard
    - Tactics games
<img width="1925" height="1071" alt="image" src="https://github.com/user-attachments/assets/e7b5cac2-d8bd-4b07-87f1-8c9fc95e3ee7" />

# Dependancies
    - libsdl2-dev
    - export LIBGL_ALWAYS_SOFTWARE=1

# Plot
The player is an ambitous and foolhardy wizard school dropout. They start with some default spells, but learn many more via exploration.

## Mechanical Ideas
    - teleportation/forced movement
    - info gathering (bigger sight radius, heartbeat counter)
    - terrain generation (create new hallways, wall pillars)
    - grant status `Foo X` where x ticks down every turn (Bleed 3, Slow 2, etc)

## Resource Ideas (partial alternatives to current cooldowns)
    - Mostly cooldown based
    - Stats: a stat for magic reserves, magnitude, duration, AOE size/range, etc
    - Spell crafting
        * Collect spell portions ("glyphs" or "incantations")
        * These will be: damage, targeting criteria (aoe, range), debuffs
        * Maybe these modify base spells, maybe they are completely separate
        * Each of these would effect the cooldown
    - Multiple mana bars
        * Each accumulates and gets spent in a slightly different way

# Design Questions
    - Why explore the level, (vs doing down asap)
        * Better Spell scrolls
    - What is the progression system?
        * Between Games
            + Horizontal power scaling.
            + New starting spells
            + New characters that mix up the gameplay a bit
        * In game
            + Better scrolls
            + power ups of some other kind?

# Map Plans
    - cave levels
    - laberynth levels
        * locked doors
    - set-piece features

# Arch Concerns
    - The Targeting phase and associated components are coupled to spell casting, if we have other things that target that'll need to change
        * Each effect component should have its own target, in case we have dmg+heal on one spell, for exampe
        * In the above case, there can be ambiguity about what the target phase actually sets
    - Processors have verbose names, which include phases. Good hint to break them out to phase-based files. Some procs are shared tho
    - AI behavior probably doesn't *all* want to live in the NPC proc
    - I like context from breadcrumbs, but there is now a search issue with multiple apply functions, multiple Damage things, etc
    - look into integer_scaling for context.present(console)
    - Queries that return nothing can crash sometimes :(
    - flash_pos redraws screen first, so the flash and glyph aren't desynced
        * this is the opposite of what flash does. maybe a bad idea?
    - Should it be possible to ascend to a previous level (def not for now)
    - Crosshair is a big exception to how movement works. might be worth its own function
    - When I take a step, ranged enemies shoot me before step completes. feels correct for melee but unintuitive for range.
    - MenuItem is used for actual menus, but not for inventory (not 1:1 with entities)
        * MenuSelection, however, IS reused to inventory
    - Right now levels are limited to the board size. We could decouple those and have the board "scroll"
    - should we always place the stairs as far back as we can?
    - wet status from water tiles? are we that sort of game?
    - We have two damage process steps, one for player damage, and one for everything else. This means enemies the player would kill don't attack back
    - Bleed damage feels like it takes an extra turn. this is intentional. it only takes effect on the start of the turn after it is applied
    - StepTrigger callbacks get their targets from the movement proc, in the OnStep case
    - Should there be a death event queue?
    - Because we allow already dead entities to resolve their queued damage, enemies get one final retaliation
    - reusing Position components breaks things
    - DeathTriggers with dmg need to have oneshot(Dmg) called after
    - Warlock missles don't hit potions because they are not Blocking
    - currently the enemy move decision tree is one static thing. break up eventually
    - TargetInputEvent returns control to the player's Damage phase. otherwise enemies get a turn before player damage resolves
    - instead of a melee decision tree, we do melee damage via bump func
    - Small Procs
        * A proposed refactor where we have much more procs, many with guards
        * each npc type, gets its own for example
        * this would hopefully replace Phases and callbacks

# TODO

## Core System
    - Save/Load
    - sqlite db for storing current lvl value, rng seed for lvls, etc
    - the ecs.remove syntax is awkward, but overwriting self.entities state inf ilter necessitates it for now
    - callbacks are a violation of ECS. consider avoiding them somehow
        * the things that are now callbacks can be Small Procs, with a guard
        * for nav menu items, a NavButton cmponent with a *to* arg for phase
            + these having to coexist with current buttons might be too complex?
            + the car select buttons are both
    - lots of DRY in the NPC proc
    - bresenham_ray should *really* be under test
    - Should Position comps be immutable?
        * If there is only one immutable Pos per XY,
            + we can name them Positon24_49 and then
            + getattr(cmp,f"Position{x}_{y}") in queries
        * This does perhaps screw us if we just want to get the pos. 
            + Do we modify the query func to work on superclasses? can we?
    - 2x2 enemies
        * game currently assumes positions are one cell, pieces have one pos
        * If I have 2x2, then I can make snakes too
    - break up Arch Concerns into open questions and arch docs
    - All effects on the targeting entity should get their targets filled in if they haven't already
        * But, only the non-static targets should get cleared, and we don't have a way to store that info
    - effect application restrictions. (mutilate can't hit traps)
    - an Ephemeral component for Crosshair, Area Effect type stuff
    - Entity templates: cmp collections for easy entity creation
    - We could rework Phases entirely. All systems are called at all times
        * however, they all have a state guard and return when guard fails
        * big change, so lots of surface area
        * the guards also don't have to be phase analogues
            + this means we can do smaller procs for things like callbacks
            + buut order mgmt is currently pretty hard. 
            + this would likely make it harder
        * Get can be *much* more dynamic about what runs where 
            + a state machine for various turn flows
            + single exec via a simple queue_proc() func 
    - A GameMeta to hold globals
        * console, context at minimum. those are annoying to pass around
        * level, board are globals now, so this would be an improvement
    - The main callback that needs a ref to source is lob_bomb
        * It sure would be nice if it didn't need that
        * We could rewrite lob_bomb as a proc. LobberNPC or something
            + This also paves the way for every npc to have their own proc
    - board currently is 66*67. I could make it 64*64. Leave room for a border
## Game Mechanics/Balance
    - spell mods (+1 range, +1 dmg pickups)
    - cooldown alternatives like damage taken, steps walked (lotta tracking)
    - spell burnout (ie how spammable a spell is)
        * using a spell accumulates one stack of burnout
        * burnout decreases by one every [max cooldown]+1 turns
        * when burnout reaches [max cooldown], increase [max cooldown] by 1
            + but do it in some temp way
        * [max cooldown] decreases again in like [max coldown]*2 turns
        * Alternat mechanic?, Burnout is a cap of off-cooldown uses.
            + If you use off cooldown B times, then you accumulate 1 burnout
            + and that takes B * CD to clear
    - add aoe into the spell power budget calculation
    - Aegis (spell-based buff) decaying shield
        * while you have Aegis N, take N less damage
        * this can get out of hand, esp if the cooldown on that spell is low
    - Some sort of Storm/Combo mechanic would be really cool
    - Should some damge be in ranges?
        * If they are, I'm always a fan of dice pools
    - small chance of "named" scrolls with unique effects
    - goblins should actually try to be at dist 4 to player
        * when on cooldown BFS a position with dist 4, then move a step
    - living flames move up to 2 squares to enemy
        * want an animation for getting there
        * if only moving 1 square can also attack
        * if its 2 squares away, player moves into, flame overreaches
    - Spawners
    - In caves, NPCs shouldn't spawn too close to player
    - "Commander" Enemies that effect their faction
    - Check for more places that benefit from ecs.Query.where
    - 3rd char, 1 pull+aegis spell, 1 kill spell with min range
    - Doors via conditional blocking
    - basic lighting attack that uses the ray func I made
    - mageblight: a curse that harms player when they don't progress the game
        * probably when they spend N turns without killing an enemy
        * escalates in damage
    - do I want hidden/invisible elements? (traps, assasins)
    - items in maze should be in dead-ends only
    - binary(ish) space partitioning, plus prefabs of that size
## UX
    - Should all ranged animations happen simultaneously?
        * animation queue?
    - one-turn-per-square moving projectiles
    - when targeting, valid xhair area should be inicated by aoe
    - use that M icon
    - other menus probably want backgrounds.
        * side panels might too
    - rework blit_image
    - add ├ and ┤ to dashes, but not just via panel_contents list
        * since that assumes a starting X coord
# BUGS
    - Found a wall I was able to walk through in the caves.
        * Sometimes enemies turn into walls when they die
        * those walls can be walked through
        * I think this is bc enemies spawn *in* the wall with same pos
    - MenuSelection maybe wants to be reset when moving thru menus
    - Bombs dealing damage to each other loop and break game
        * maybe bombs just can't dmg each other
        * maybe we don't oneshot proc the damage (so, finish death)
