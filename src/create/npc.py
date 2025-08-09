import esper

import behavior
import components as cmp
import display as dis
from functools import partial

import location
import math_util


def bat(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.BAT, color=dis.Color.BROWN))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="bat"))
    cmps.append(cmp.Flying())
    cmps.append(cmp.EnemyTrigger(callbacks=[behavior.apply_damage]))
    cmps.append(cmp.Enemy())
    cmps.append(cmp.Blocking())
    cmps.append(cmp.Wander())
    bat = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=bat)
    esper.add_component(bat, dmg_effect)
    return bat


def skeleton(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.SKELETON, color=dis.Color.BROWN))
    cmps.append(cmp.Health(max=3))
    cmps.append(cmp.Onymous(name="skeleton"))
    cmps.append(cmp.Melee(radius=10))
    cmps.append(cmp.EnemyTrigger(callbacks=[behavior.apply_damage]))
    cmps.append(cmp.Enemy())
    cmps.append(cmp.Blocking())
    skeleton = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def warlock(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)

    cmps.append(cmp.Visible(glyph=dis.Glyph.WARLOCK, color=dis.Color.INDIGO))
    cmps.append(cmp.Health(max=2))
    cmps.append(cmp.Onymous(name="warlock"))
    cmps.append(cmp.Ranged(radius=3))
    callbacks = [behavior.fire_at_player, behavior.apply_damage]
    cmps.append(cmp.EnemyTrigger(callbacks=callbacks))
    cmps.append(cmp.Cooldown(turns=1))
    cmps.append(cmp.Enemy())
    cmps.append(cmp.Blocking())
    warlock = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=warlock)
    esper.add_component(warlock, dmg_effect)
    return warlock


def living_flame(pos: cmp.Position) -> int:
    """melee unit, with a dash"""
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.FLAME, color=dis.Color.ORANGE))
    cmps.append(cmp.Health(max=2))
    cmps.append(cmp.Onymous(name="living flame"))
    cmps.append(cmp.Melee(radius=5))
    cmps.append(cmp.EnemyTrigger(callbacks=[behavior.apply_damage]))
    cmps.append(cmp.Enemy(speed=2))
    cmps.append(cmp.Blocking())
    flame = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=flame)
    esper.add_component(flame, dmg_effect)
    return flame


def goblin(pos: cmp.Position) -> int:
    """throws bombs"""
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.GOBLIN, color=dis.Color.DARK_GREEN))
    cmps.append(cmp.Health(max=2))
    cmps.append(cmp.Onymous(name="goblin"))
    cmps.append(cmp.Ranged(radius=5))

    cmps.append(cmp.EnemyTrigger(callbacks=[behavior.lob_bomb]))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.Enemy())
    cmps.append(cmp.Blocking())
    goblin = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=goblin)
    esper.add_component(goblin, dmg_effect)
    return goblin


def cyclops(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.CYCLOPS, color=dis.Color.BROWN))
    cmps.append(cmp.Health(max=2))
    cmps.append(cmp.Onymous(name="cyclops"))
    cmps.append(cmp.Ranged(radius=4))

    callbacks = [behavior.apply_cyclops_attack_pattern]
    cmps.append(cmp.EnemyTrigger(callbacks=callbacks))
    cmps.append(cmp.Enemy())
    cmps.append(cmp.Blocking())
    cyclops = esper.create_entity(*cmps)

    dmg_effect = cmp.DamageEffect(amount=1, source=cyclops)
    esper.add_component(cyclops, dmg_effect)

    ppos = location.player_position()
    callback = partial(math_util.bresenham_ray, dest=ppos)
    esper.add_component(cyclops, cmp.EffectArea(callback))
    return cyclops
