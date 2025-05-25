# factories
import collections
import random
import string

import esper

import components as cmp
import display
import ecs
import location
import scene


# TODO: should these take a position?
def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.FLOOR, color=display.Color.LGREY)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent())
    return cell


def wall(x: int, y: int, breakable: int = False) -> int:
    vis = cmp.Visible(glyph=display.Glyph.WALL, color=display.Color.LGREY)
    pos = cmp.Position(x, y)
    blocking = cmp.Blocking()
    cell = esper.create_entity(cmp.Cell(), pos, vis, blocking)
    if breakable:
        esper.add_component(cell, cmp.Health(max=1))
        esper.add_component(cell, cmp.Onymous(name="wall"))
        vis.glyph = display.Glyph.BWALL

    return cell


def stairs(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.STAIRS, color=display.Color.LGREY)

    os = cmp.OnStep()
    tp = cmp.Transparent()
    stairs = esper.create_entity(cmp.Cell(), pos, vis, tp, os)

    def descend():
        player = ecs.Query(cmp.Player).first()
        if target_cmp := esper.try_component(stairs, cmp.Target):
            if target_cmp.target == player:
                location.new_level()

    cbe = cmp.CallbackEffect(callback=descend)
    esper.add_component(stairs, cbe)
    return stairs


def bat(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.BAT, color=display.Color.BROWN)
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

    dmg_effect = cmp.DamageEffect(amount=1, source=bat)
    esper.add_component(bat, dmg_effect)
    return bat


def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.BROWN)
    hp = cmp.Health(max=3)
    named = cmp.Onymous(name="skeleton")
    melee = cmp.Melee(radius=5)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, melee, named]
    skeleton = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def warlock(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.WARLOCK, color=display.Color.INDIGO)
    hp = cmp.Health(max=3)
    named = cmp.Onymous(name="warlock")
    melee = cmp.Ranged(radius=3)
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, melee, named]
    warlock = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=warlock)
    esper.add_component(warlock, dmg_effect)
    return warlock


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


def spell_stats(power_budget=10, waste_chance=0.2) -> tuple[int, int, int]:
    stats = {"damage": 1, "range": 2, "cooldown": 1}
    remaining_points = power_budget - sum(stats.values())
    while remaining_points > 0:
        if random.random() > waste_chance:
            stat = random.choice(list(stats.keys()))
            stats[stat] += 1
        remaining_points -= 1
    stats["cooldown"] = max(1, 5 - stats["cooldown"])
    return stats["damage"], stats["range"], stats["cooldown"]


def random_spell(power_budget=10) -> int:
    waste_chance = 0.2
    match random.randint(0, 3):
        case 0:
            waste_chance = 0.4
    damage, rnge, cooldown = spell_stats(power_budget, waste_chance)

    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=rnge)
    cooldown = cmp.Cooldown(turns=cooldown)
    if waste_chance == 0.4:
        harm_effect = cmp.BleedEffect(value=damage)
    else:
        harm_effect = cmp.DamageEffect(amount=damage, source=player)
    name = "".join(random.choices(string.ascii_lowercase, k=5))
    named = cmp.Onymous(name=name)
    damage_spell = esper.create_entity(spell_cmp, harm_effect, named, cooldown)

    match random.randint(0, 6):
        case 0:
            radius = random.randint(1, 4)
            esper.add_component(damage_spell, cmp.EffectArea(radius=radius))
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


def main_menu_opts():
    to_level = lambda: scene.to_phase(scene.Phase.level)
    cbe = cmp.CallbackEffect(callback=to_level)
    mm = cmp.MainMenu()
    name = cmp.Onymous(name="Start Game")
    menu_item = cmp.MenuItem(order=0)
    components = [menu_item, name, cbe, mm]
    esper.create_entity(*components)

    to_opts = lambda: scene.to_phase(scene.Phase.options)
    cbe = cmp.CallbackEffect(callback=to_opts)
    mm = cmp.MainMenu()
    name = cmp.Onymous(name="Options")
    menu_item = cmp.MenuItem(order=1)
    components = [menu_item, name, cbe, mm]
    esper.create_entity(*components)


def firebolt_spell() -> int:
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=5)
    cooldown = cmp.Cooldown(turns=1)
    dmg_effect = cmp.DamageEffect(amount=1, source=player)
    aoe = cmp.EffectArea(radius=1)
    named = cmp.Onymous(name="Firebolt")
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
    named = cmp.Onymous(name="Blink")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def bleed_spell() -> int:
    spell_cmp = cmp.Spell(target_range=3)
    cooldown = cmp.Cooldown(turns=2)
    dmg_effect = cmp.BleedEffect(value=2)
    named = cmp.Onymous(name="Mutilate")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def trap(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.TRAP, color=display.Color.RED)
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="trap")
    trap_cmp = cmp.OnStep()

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
