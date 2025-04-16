# factories
import collections

import esper

import components as cmp
import display
import ecs


# TODO: should these take a position?
def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.FLOOR, color=display.Color.LGREY)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent())
    return cell


def wall(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.WALL, color=display.Color.LGREY)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Blocking())
    return cell


def bat(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.BAT, color=display.Color.RED)
    actor = cmp.Actor(max_hp=1)
    named = cmp.Onymous(name="bat")
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, cmp.Wander(), named]
    bat = esper.create_entity(*components)
    return bat


def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.RED)
    actor = cmp.Actor(max_hp=3)
    named = cmp.Onymous(name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, melee, named]
    skeleton = esper.create_entity(*components)
    return skeleton


def potion(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    actor = cmp.Actor(max_hp=1)
    named = cmp.Onymous(name="potion")

    player, _ = ecs.Query(cmp.Player).first()
    heal = cmp.HealEffect(target=player, amount=2)
    components = [pos, vis, col, actor, named, heal]
    potion = esper.create_entity(*components)
    return potion


def inventory_map() -> list:
    inventory = esper.get_components(cmp.InInventory, cmp.Onymous)
    inventory_map = collections.defaultdict(set)
    for entity, (_, named) in inventory:
        inventory_map[named.name].add(entity)
    # TODO: create a cmp.MenuItem on collection, then set the order in this func
    # then display is just a matter of lookup
    sorted_map = sorted(inventory_map.items())
    return sorted_map


def damage_spell() -> int:
    player, _ = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(slot=1, target_range=5, cooldown=2)
    dmg_effect = cmp.DamageEffect(amount=1, source=player)
    named = cmp.Onymous(name="firebolt")
    sample_spell = esper.create_entity(spell_cmp, dmg_effect, named)
    return sample_spell


def tp_spell() -> int:
    player, _ = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(slot=2, target_range=4, cooldown=5)
    dmg_effect = cmp.MoveEffect(target=player)
    named = cmp.Onymous(name="blink")
    sample_spell = esper.create_entity(spell_cmp, dmg_effect, named)
    return sample_spell
