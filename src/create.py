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
    flying = cmp.Flying()
    components = [
        cmp.Enemy(),
        pos,
        vis,
        cmp.Blocking(),
        actor,
        cmp.Wander(),
        named,
        flying,
    ]
    bat = esper.create_entity(*components)

    # I'm trying having Damage Effects on enemies,
    # and just effects_to_events to apply
    dmg_effect = cmp.DamageEffect(amount=1, source=bat)
    esper.add_component(bat, dmg_effect)
    return bat


def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.RED)
    actor = cmp.Actor(max_hp=3)
    named = cmp.Onymous(name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), actor, melee, named]
    skeleton = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def potion(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    actor = cmp.Actor(max_hp=1)
    named = cmp.Onymous(name="potion")

    player = ecs.Query(cmp.Player).first()
    heal = cmp.HealEffect(amount=2)
    target = cmp.Target(target=player)
    components = [pos, vis, col, actor, named, heal, target]
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
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(slot=1, target_range=5)
    cooldown = cmp.Cooldown(turns=1)
    dmg_effect = cmp.DamageEffect(amount=1, source=player)
    named = cmp.Onymous(name="firebolt")
    sample_spell = esper.create_entity(spell_cmp, dmg_effect, named, cooldown)
    return sample_spell


def tp_spell() -> int:
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(slot=2, target_range=4)
    cooldown = cmp.Cooldown(turns=5)
    dmg_effect = cmp.MoveEffect(target=player)
    named = cmp.Onymous(name="blink")
    components = [spell_cmp, dmg_effect, named, cooldown]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def trap(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.TRAP, color=display.Color.RED)
    actor = cmp.Actor(max_hp=1)
    named = cmp.Onymous(name="trap")
    trap_cmp = cmp.Trap()

    components = [pos, vis, actor, named, trap_cmp]
    trap_ent = esper.create_entity(*components)
    dmg = cmp.DamageEffect(source=trap_ent, amount=1)
    esper.add_component(trap_ent, dmg)
    return trap_ent


def player():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    actor = cmp.Actor(max_hp=10)
    named = cmp.Onymous(name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), actor, named)
