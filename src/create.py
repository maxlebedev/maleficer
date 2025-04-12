# factories
import collections

import esper

import components as cmp
import display


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
    actor = cmp.Actor(max_hp=1, name="bat")
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, cmp.Wander()]
    bat = esper.create_entity(*components)
    return bat


def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.RED)
    actor = cmp.Actor(max_hp=3, name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, melee]
    skeleton = esper.create_entity(*components)
    return skeleton


def potion(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    actor = cmp.Actor(max_hp=1, name="potion")
    components = [pos, vis, col, actor]
    potion = esper.create_entity(*components)
    return potion


def inventory_map() -> list:
    inventory = esper.get_components(cmp.InInventory, cmp.Actor)
    inventory_map = collections.defaultdict(set)
    for entity, (_, actor) in inventory:
        inventory_map[actor.name].add(entity)
    # TODO: create a cmp.MenuItem on collection, then set the order in this func
    # then display is just a matter of lookup
    sorted_map = sorted(inventory_map.items())
    return sorted_map


def starting_spell() -> int:
    spell_cmp = cmp.Spell(slot=1, target_range=5, damage=1)
    sample_spell = esper.create_entity(spell_cmp)
    return sample_spell
