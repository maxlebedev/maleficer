# factories
import collections
import random
import string

import esper

import components as cmp
import processors
import display
import ecs
import location
import scene
import event
import condition
import typ


# TODO: should these take a position?
def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=display.Glyph.FLOOR, color=display.Color.FLOOR)
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

    def descend(_):
        player = ecs.Query(cmp.Player).first()
        if target_cmp := esper.try_component(stairs, cmp.Target):
            if target_cmp.target == player:
                location.LEVEL += 1
                location.new_level()

    st = cmp.StepTrigger(callbacks=[descend])
    esper.add_component(stairs, st)
    return stairs


def bat(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.BAT, color=display.Color.BROWN)
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="bat")
    flying = cmp.Flying()
    et = cmp.EnemyTrigger(callbacks=[event.apply_damage])
    components = [
        cmp.Enemy(),
        pos,
        vis,
        cmp.Blocking(),
        hp,
        cmp.Wander(),
        named,
        flying,
        et,
    ]
    bat = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=bat)
    esper.add_component(bat, dmg_effect)
    return bat


def skeleton(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SKELETON, color=display.Color.BROWN)
    hp = cmp.Health(max=3)
    named = cmp.Onymous(name="skeleton")
    melee = cmp.Melee(radius=10)
    et = cmp.EnemyTrigger(callbacks=[event.apply_damage])
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, melee, named, et]
    skeleton = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=skeleton)
    esper.add_component(skeleton, dmg_effect)
    return skeleton


def warlock(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.WARLOCK, color=display.Color.INDIGO)
    hp = cmp.Health(max=2)
    named = cmp.Onymous(name="warlock")
    ranged = cmp.Ranged(radius=3)
    et = cmp.EnemyTrigger(callbacks=[event.fire_at_player, event.apply_damage])
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, ranged, named, et]
    warlock = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=warlock)
    esper.add_component(warlock, dmg_effect)
    return warlock

def goblin(pos: cmp.Position) -> int:
    """throws bombs"""
    vis = cmp.Visible(glyph=display.Glyph.GOBLIN, color=display.Color.DARK_GREEN)
    hp = cmp.Health(max=2)
    named = cmp.Onymous(name="goblin")
    ranged = cmp.Ranged(radius=3)

    et = cmp.EnemyTrigger(callbacks=[event.lob_bomb])
    components = [cmp.Enemy(), pos, vis, cmp.Blocking(), hp, ranged, named, et]
    goblin = esper.create_entity(*components)

    dmg_effect = cmp.DamageEffect(amount=1, source=goblin)
    esper.add_component(goblin, dmg_effect)
    return goblin


def potion(pos: cmp.Position | None = None) -> int:
    vis = cmp.Visible(glyph=display.Glyph.POTION, color=display.Color.GREEN)
    col = cmp.Collectable()
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="potion")

    player = ecs.Query(cmp.Player).first()
    heal = cmp.HealEffect(amount=2)
    ut = cmp.UseTrigger(callbacks=[event.apply_healing])
    target = cmp.Target(target=player)
    components = [vis, col, hp, named, heal, target, ut]
    potion = esper.create_entity(*components)
    if pos:
        esper.add_component(potion, pos)
    return potion


def scroll(pos: cmp.Position | None = None, spell: int | None = None) -> int:
    vis = cmp.Visible(glyph=display.Glyph.SCROLL, color=display.Color.MAGENTA)
    col = cmp.Collectable()
    hp = cmp.Health(max=1)

    if not spell:
        spell = random_spell(5 + (location.LEVEL * 5))
    learnable = cmp.Learnable(spell=spell)
    ut = cmp.UseTrigger(callbacks=[event.apply_learn])

    components = [vis, col, hp, learnable, ut]
    scroll = esper.create_entity(*components)
    if pos:
        esper.add_component(scroll, pos)

    spell_name = esper.component_for_entity(spell, cmp.Onymous).name
    named = cmp.Onymous(name=f"{spell_name} scroll")
    esper.add_component(scroll, named)
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
    damage, target_range, cooldown = spell_stats(power_budget, waste_chance)

    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=target_range)
    cooldown = cmp.Cooldown(turns=cooldown)
    ut = cmp.UseTrigger(callbacks=[event.apply_cooldown])
    if waste_chance == 0.4:
        harm_effect = cmp.BleedEffect(value=damage)
        ut.callbacks.append(event.apply_bleed)
    else:
        harm_effect = cmp.DamageEffect(amount=damage, source=player)
        ut.callbacks.append(event.apply_damage)
    name = "".join(random.choices(string.ascii_lowercase, k=5))
    named = cmp.Onymous(name=name)
    spell = esper.create_entity(spell_cmp, harm_effect, named, cooldown, ut)

    match random.randint(0, 6):
        # TODO: pull this into the power budget calculation
        case 0:
            radius = random.randint(1, target_range - 1)
            esper.add_component(spell, cmp.EffectArea(radius=radius))
    return spell


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
    to_level = lambda _: scene.to_phase(scene.Phase.level)
    mm = cmp.MainMenu()
    name = cmp.Onymous(name="Start Game")
    menu_item = cmp.MenuItem(order=0)
    ut = cmp.UseTrigger(callbacks=[to_level])
    components = [menu_item, name, mm, ut]
    esper.create_entity(*components)

    to_opts = lambda _: scene.to_phase(scene.Phase.options)
    ut = cmp.UseTrigger(callbacks=[to_opts])
    mm = cmp.MainMenu()
    name = cmp.Onymous(name="Options")
    menu_item = cmp.MenuItem(order=1)
    components = [menu_item, name, ut, mm]
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
    ut = cmp.UseTrigger(callbacks=[event.apply_cooldown, event.apply_damage])
    components = [spell_cmp, dmg_effect, named, cooldown, known, aoe, ut]
    damage_spell = esper.create_entity(*components)

    return damage_spell


def blink_spell() -> int:
    player = ecs.Query(cmp.Player).first()
    spell_cmp = cmp.Spell(target_range=4)
    cooldown = cmp.Cooldown(turns=5)
    ut = cmp.UseTrigger(callbacks=[event.apply_cooldown, event.apply_move])
    dmg_effect = cmp.MoveEffect(target=player)
    named = cmp.Onymous(name="Blink")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, ut, known]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def bleed_spell() -> int:
    spell_cmp = cmp.Spell(target_range=3)
    cooldown = cmp.Cooldown(turns=2)
    dmg_effect = cmp.BleedEffect(value=2)
    ut = cmp.UseTrigger(callbacks=[event.apply_cooldown, event.apply_bleed])
    named = cmp.Onymous(name="Mutilate")
    slot_num = len(esper.get_component(cmp.Known)) + 1
    known = cmp.Known(slot=slot_num)
    components = [spell_cmp, dmg_effect, named, cooldown, known, ut]
    sample_spell = esper.create_entity(*components)
    return sample_spell


def trap(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.TRAP, color=display.Color.RED)
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="trap")
    trap_cmp = cmp.OnStep()

    st = cmp.StepTrigger(callbacks=[event.apply_damage])
    components = [pos, vis, hp, named, trap_cmp, st]
    trap_ent = esper.create_entity(*components)
    dmg = cmp.DamageEffect(source=trap_ent, amount=1)
    esper.add_component(trap_ent, dmg)
    return trap_ent


def bomb(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=display.Glyph.BOMB, color=display.Color.RED)
    hp = cmp.Health(max=1)
    named = cmp.Onymous(name="bomb")
    die_cmp = cmp.OnDeath()
    aoe = cmp.EffectArea(radius=1)
    aura = cmp.Aura(radius=1, color=display.Color.LIGHT_RED)

    dmg_proc = lambda _ : scene.oneshot(processors.Damage)
    dt = cmp.DeathTrigger(callbacks=[event.apply_damage, dmg_proc])
    components = [pos, vis, hp, named, die_cmp, aoe, aura, dt]
    bomb_ent = esper.create_entity(*components)
    dmg = cmp.DamageEffect(source=bomb_ent, amount=1)
    esper.add_component(bomb_ent, dmg)
    condition.grant(bomb_ent, typ.Condition.Dying, 2)

    return bomb_ent


def player():
    vis = cmp.Visible(glyph=display.Glyph.PLAYER, color=display.Color.GREEN)
    pos = cmp.Position(x=1, y=1)
    hp = cmp.Health(max=10)
    named = cmp.Onymous(name="player")
    esper.create_entity(cmp.Player(), pos, vis, cmp.Blocking(), hp, named)


def starting_inventory():
    starting_potion = potion()
    esper.add_component(starting_potion, cmp.InInventory())
