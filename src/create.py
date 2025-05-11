# factories
import collections
import random
import string

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
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="bat")
    flying = cmp.Flying()
    components = [
        cmp.Enemy(),
        pos,
        vis,
        cmp.Blocking(),
        hp,
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
    hp = cmp.Health(max=3)
    named = cmp.Onymous(name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, melee, named]
    skeleton = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def potion(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="potion")

    player = ecs.Query(cmp.Player).first()
    heal = cmp.HealEffect(amount=2)
    target = cmp.Target(target=player)
    components = [pos, vis, col, hp, named, heal, target]
    potion = esper.create_entity(*components)
    return potion


def scroll(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SCROLL, color=display.Color.MAGENTA)
    col = cmp.Collectable()
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="scroll")

    spell = random_spell()
    learnable = cmp.Learnable(spell=spell)
    # "learn spell" is an effect

    components = [pos, vis, col, hp, named, learnable]
    scroll = esper.create_entity(*components)
    return scroll


def random_spell(power_budget=10) -> int:
    stats = {"damage": 1, "range": 2, "cooldown": 1}
    remaining_points = power_budget - sum(stats.values())
    waste_chance = 0.2
    while remaining_points > 0:
        if random.random() > waste_chance:
            stat = random.choice(list(stats.keys()))
            stats[stat] += 1
        remaining_points -= 1
    stats["cooldown"] = max(1, 5 - stats["cooldown"])

    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=stats["range"])
    cooldown = cmp.Cooldown(turns=stats["cooldown"])
    if not random.randint(0, 1):
        harm_effect = cmp.BleedEffect(value=max(1, stats["damage"] // 2))
        # TODO: 0,1,2,3 all result in 1 bleed. One bleed is just dmg but worse
        # we probably want to pick dmg/bleed first, then adjust accordingly
    else:
        harm_effect = cmp.DamageEffect(amount=stats["damage"], source=player)
    name = "".join(random.choices(string.ascii_lowercase, k=5))
    named = cmp.Onymous(name=name)
    damage_spell = esper.create_entity(spell_cmp, harm_effect, named, cooldown)
    return damage_spell


def inventory_map() -> list:
    inventory = esper.get_components(cmp.InInventory, cmp.Onymous)
    inventory_map = collections.defaultdict(set)
    for entity, (_, named) in inventory:
        inventory_map[named.name].add(entity)
    # TODO: create a cmp.MenuItem on collection, then set the order in this func
    # then display is just a matter of lookup
    sorted_map = sorted(inventory_map.items())
    return sorted_map


def firebolt_spell() -> int:
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=5)
    cooldown = cmp.Cooldown(turns=1)
    dmg_effect = cmp.DamageEffect(amount=1, source=player)
    aoe = cmp.EffectArea(radius=1)
    named = cmp.Onymous(name="firebolt")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known, aoe]
    damage_spell = esper.create_entity(*components)
    return damage_spell


def blink_spell() -> int:
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=4)
    cooldown = cmp.Cooldown(turns=5)
    dmg_effect = cmp.MoveEffect(target=player)
    named = cmp.Onymous(name="blink")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def bleed_spell() -> int:
    spell_cmp = cmp.Spell(target_range=3)
    cooldown = cmp.Cooldown(turns=2)
    dmg_effect = cmp.BleedEffect(value=2)
    named = cmp.Onymous(name="mutilate")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def trap(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.TRAP, color=display.Color.RED)
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="trap")
    trap_cmp = cmp.Trap()

    components = [pos, vis, hp, named, trap_cmp]
    trap_ent = esper.create_entity(*components)
    dmg = cmp.DamageEffect(source=trap_ent, amount=1)
    esper.add_component(trap_ent, dmg)
    return trap_ent


def player():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    hp = cmp.Health(max=10)
    named = cmp.Onymous(name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), hp, named)
