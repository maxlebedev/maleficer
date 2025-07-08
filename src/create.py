# factories
import collections
import random
import string

import esper

import behavior
import components as cmp
import condition
import display as dis
import ecs
import location
import processors
import scene
import typ


# TODO: should these take a position?
def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.FLOOR, color=dis.Color.FLOOR)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent())
    return cell


def wall(x: int, y: int, breakable: int = False) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.WALL, color=dis.Color.LGREY)
    pos = cmp.Position(x, y)
    blocking = cmp.Blocking()
    cell = esper.create_entity(cmp.Cell(), pos, vis, blocking)
    if breakable:
        esper.add_component(cell, cmp.Health(max=1))
        esper.add_component(cell, cmp.Onymous(name="wall"))
        vis.glyph = dis.Glyph.BWALL

    return cell


def stairs(pos: cmp.Position) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.STAIRS, color=dis.Color.LGREY)

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
    cmps.append(cmp.Melee(radius=5, speed=2))
    cmps.append(cmp.EnemyTrigger(callbacks=[behavior.apply_damage]))
    cmps.append(cmp.Enemy())
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


def potion(pos: cmp.Position | None = None) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.POTION, color=dis.Color.GREEN))
    cmps.append(cmp.Collectable())
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="potion"))

    cmps.append(cmp.HealEffect(amount=2))
    cmps.append(cmp.UseTrigger(callbacks=[behavior.apply_healing]))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Target(target=player))
    potion = esper.create_entity(*cmps)
    if pos:
        esper.add_component(potion, pos)
    return potion


def scroll(pos: cmp.Position | None = None, spell: int | None = None) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.SCROLL, color=dis.Color.MAGENTA))
    cmps.append(cmp.Collectable())
    cmps.append(cmp.Health(max=1))

    if not spell:
        spell = random_spell(5 + (location.LEVEL * 5))
    cmps.append(cmp.Learnable(spell=spell))
    cmps.append(cmp.UseTrigger(callbacks=[behavior.apply_learn]))

    scroll = esper.create_entity(*cmps)
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
    ut = cmp.UseTrigger(callbacks=[behavior.apply_cooldown])
    if waste_chance == 0.4:
        harm_effect = cmp.BleedEffect(value=damage)
        ut.callbacks.append(behavior.apply_bleed)
    else:
        harm_effect = cmp.DamageEffect(amount=damage, source=player)
        ut.callbacks.append(behavior.apply_damage)
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
    cmps = []
    cmps.append(cmp.MainMenu())
    cmps.append(cmp.Onymous(name="Start Game"))
    cmps.append(cmp.MenuItem(order=0))
    cmps.append(cmp.UseTrigger(callbacks=[to_level]))
    esper.create_entity(*cmps)

    to_opts = lambda _: scene.to_phase(scene.Phase.options)
    cmps = []
    cmps.append(cmp.UseTrigger(callbacks=[to_opts]))
    cmps.append(cmp.MainMenu())
    cmps.append(cmp.Onymous(name="Options"))
    cmps.append(cmp.MenuItem(order=1))
    esper.create_entity(*cmps)


def firebolt_spell() -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=5))
    cmps.append(cmp.Cooldown(turns=1))
    cmps.append(cmp.DamageEffect(amount=1, source=player))
    cmps.append(cmp.EffectArea(radius=1))
    cmps.append(cmp.Onymous(name="Firebolt"))
    slot_num = len(esper.get_component(cmp.Known)) + 1
    cmps.append(cmp.Known(slot=slot_num))
    callbacks = [behavior.apply_cooldown, behavior.apply_damage]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    firebolt_spell = esper.create_entity(*cmps)

    return firebolt_spell


def blink_spell() -> int:
    cmps = []
    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.Spell(target_range=4))
    cmps.append(cmp.Cooldown(turns=5))
    callbacks = [behavior.apply_cooldown, behavior.apply_move]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.MoveEffect(target=player))
    cmps.append(cmp.Onymous(name="Blink"))
    slot_num = len(esper.get_component(cmp.Known)) + 1
    cmps.append(cmp.Known(slot=slot_num))
    blink_spell = esper.create_entity(*cmps)
    return blink_spell


def bleed_spell() -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=3))
    cmps.append(cmp.Cooldown(turns=2))
    cmps.append(cmp.BleedEffect(value=2))
    callbacks = [behavior.apply_cooldown, behavior.apply_bleed]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Mutilate"))
    slot_num = len(esper.get_component(cmp.Known)) + 1
    cmps.append(cmp.Known(slot=slot_num))
    bleed_spell = esper.create_entity(*cmps)
    return bleed_spell


def push_spell() -> int:
    cmps = []
    cmps.append(cmp.Spell(target_range=4))
    cmps.append(cmp.Cooldown(turns=2))
    callbacks = [behavior.apply_cooldown, behavior.apply_push]
    cmps.append(cmp.UseTrigger(callbacks=callbacks))
    cmps.append(cmp.Onymous(name="Push"))

    player = ecs.Query(cmp.Player).first()
    cmps.append(cmp.PushEffect(source=player, distance=2))
    slot_num = len(esper.get_component(cmp.Known)) + 1
    cmps.append(cmp.Known(slot=slot_num))
    push_spell = esper.create_entity(*cmps)
    return push_spell


def trap(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.TRAP, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="trap"))
    cmps.append(cmp.OnStep())

    cmps.append(cmp.StepTrigger(callbacks=[behavior.apply_damage]))
    trap_ent = esper.create_entity(*cmps)
    dmg = cmp.DamageEffect(source=trap_ent, amount=1)
    esper.add_component(trap_ent, dmg)
    return trap_ent


def bomb(pos: cmp.Position) -> int:
    cmps = []
    cmps.append(pos)
    cmps.append(cmp.Visible(glyph=dis.Glyph.BOMB, color=dis.Color.RED))
    cmps.append(cmp.Health(max=1))
    cmps.append(cmp.Onymous(name="bomb"))
    cmps.append(cmp.OnDeath())
    cmps.append(cmp.Enemy())
    cmps.append(cmp.EffectArea(radius=1))
    cmps.append(cmp.Aura(radius=1, color=dis.Color.WHITE))

    dmg_proc = lambda _: scene.oneshot(processors.Damage)
    cmps.append(cmp.DeathTrigger(callbacks=[behavior.apply_damage, dmg_proc]))

    def aura_tick(entity: int):
        aura = esper.component_for_entity(entity, cmp.Aura)
        match aura.color:
            case dis.Color.WHITE:
                aura.color = dis.Color.LIGHT_RED
            case dis.Color.LIGHT_RED:
                aura.color = dis.Color.BLOOD_RED

    cmps.append(cmp.EnemyTrigger(callbacks=[aura_tick]))

    bomb_ent = esper.create_entity(*cmps)
    dmg = cmp.DamageEffect(source=bomb_ent, amount=1)
    esper.add_component(bomb_ent, dmg)
    condition.grant(bomb_ent, typ.Condition.Dying, 2)

    return bomb_ent


def player():
    cmps = []
    cmps.append(cmp.Player())
    cmps.append(cmp.Visible(glyph=dis.Glyph.PLAYER, color=dis.Color.GREEN))
    cmps.append(cmp.Position(x=1, y=1))
    cmps.append(cmp.Health(max=10))
    cmps.append(cmp.Onymous(name="player"))
    cmps.append(cmp.Blocking())
    esper.create_entity(*cmps)


def starting_inventory():
    starting_potion = potion()
    esper.add_component(starting_potion, cmp.InInventory())
