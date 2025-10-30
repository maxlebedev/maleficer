# here lives functions performed by npcs, objects, etc

import random
from functools import partial

import esper

import components as cmp
import condition
import display
import ecs
import event
import location
import math_util
import typ


def wander(entity: int):
    dir = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
    if dir == (0, 0):
        return
    event.Movement(entity, *dir, relative=True)


def collect_all_affected_entities(source: int, target: int) -> list[int]:
    board = location.get_board()
    if not esper.has_component(target, cmp.Cell):
        return [target]
    pos = esper.component_for_entity(target, cmp.Position)
    if not esper.has_component(source, cmp.EffectArea):
        entities = [e for e in board.pieces_at(*pos)]
        return entities
    aoe = esper.component_for_entity(source, cmp.EffectArea)

    entities = []

    for x, y in aoe.callback(pos):
        entities += [e for e in board.entities[x][y] if e != source]
    return entities


def lob_bomb(source: int):
    import create

    board = location.get_board()

    player = ecs.Query(cmp.Player).first()
    if not location.can_see(source, player):
        return True

    player_pos = location.player_position()
    indices = location.get_neighbor_coords(player_pos)
    random.shuffle(indices)
    for selection in indices:
        target_cell = board.get_cell(*selection)
        if board.has_blocker(*selection):
            continue
        dest, trace = location.trace_ray(source, target_cell)
        if dest != target_cell:  # no LOS
            continue
        dest_pos = cmp.Position(*trace[-1])
        event.Spawn(func=partial(create.item.bomb, dest_pos))
        event.Animation(locs=trace, glyph=display.Glyph.BOMB, fg=display.Color.RED)
        apply_cooldown(source)
        return


def fire_at_player(source: int):
    player = ecs.Query(cmp.Player).first()
    dest, trace = location.trace_ray(source, player)
    glyph = display.Glyph.MAGIC_MISSILE
    event.Animation(locs=trace, glyph=glyph, fg=display.Color.BLUE)
    trg = cmp.Target(target=dest)
    esper.add_component(source, trg)
    apply_cooldown(source)


def apply_cooldown(source: int):
    if cd_effect := esper.try_component(source, cmp.Cooldown):
        condition.grant(source, typ.Condition.Cooldown, cd_effect.turns)


def apply_healing(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        if heal_effect := esper.try_component(source, cmp.HealEffect):
            src_frz = ecs.freeze_entity(source)
            event.Damage(src_frz, target_cmp.target, -1 * heal_effect.amount)


def apply_bleed(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if bleed_effect := esper.try_component(source, cmp.BleedEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Bleed, bleed_effect.value)


def apply_stun(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if stun_effect := esper.try_component(source, cmp.StunEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Stun, stun_effect.value)


def apply_damage(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if dmg_effect := esper.try_component(source, cmp.DamageEffect):
            src_frz = ecs.freeze_entity(source)
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    dmg_val = dmg_effect.calculate()
                    event.Damage(src_frz, ent, dmg_val)


def apply_move(source: int):
    """move target to crosshair"""
    if move_effect := esper.try_component(source, cmp.MoveEffect):
        pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        event.Movement(move_effect.target, pos.x, pos.y)


def apply_push(source: int):
    """move target N spaces away from source"""
    push_effect = esper.component_for_entity(source, cmp.PushEffect)
    source_pos = esper.component_for_entity(push_effect.source, cmp.Position)
    if target_cmp := esper.try_component(source, cmp.Target):
        entities = collect_all_affected_entities(source, target_cmp.target)

        for entity in entities:
            x, y = math_util.get_push_coords(
                source_pos.as_tuple, entity, push_effect.distance
            )
            event.Movement(entity, x, y)
            event.Animation(locs=[[x, y]], fg=display.Color.ORANGE)


def _learn(spell: int):
    # TODO: probably wants to live elsewhere
    known_spells = esper.get_component(cmp.Known)
    if len(known_spells) == 4:
        event.Log.append("Max spells learned")
        raise typ.InvalidAction("learning failed")

    min_slotnum = min({1, 2, 3, 4} - {k[1].slot for k in known_spells})
    esper.add_component(spell, cmp.Known(min_slotnum))


def apply_learn(source: int):
    if learnable := esper.try_component(source, cmp.Learnable):
        spell = learnable.spell
    else:
        raise typ.InvalidAction("learning failed")

    _learn(spell)

    if cd_effect := esper.try_component(spell, cmp.Cooldown):
        condition.grant(spell, typ.Condition.Cooldown, cd_effect.turns)


def apply_aegis(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if aegis_effect := esper.try_component(source, cmp.AegisEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Aegis, aegis_effect.value)


# This is perhaps the new template of "complex" enemies
def cyclops_attack_pattern(source: int):
    player = ecs.Query(cmp.Player).first()
    enemy_cmp = esper.component_for_entity(source, cmp.Enemy)

    if not esper.has_component(source, cmp.Aura):
        if not location.can_see(source, player, enemy_cmp.perception):
            wander(source)
            return
        # draw line
        ppos = location.player_position()
        callback = partial(math_util.bresenham_ray, dest=ppos)
        aura = cmp.Aura(callback=callback, color=display.Color.RED)
        opos = esper.component_for_entity(source, cmp.Position)
        esper.add_component(source, aura)

        coords = math_util.bresenham_ray(origin=opos, dest=ppos)
        locus = cmp.Locus(coords=coords)
        esper.add_component(source, locus)
    else:
        # fire laser
        src_frz = ecs.freeze_entity(source)
        dmg_effect = esper.component_for_entity(source, cmp.DamageEffect)
        locus = esper.component_for_entity(source, cmp.Locus)
        board = location.get_board()
        for x, y in locus.coords:
            if cell := board.get_cell(x, y):
                event.Damage(src_frz, cell, dmg_effect.amount)
        esper.remove_component(source, cmp.Locus)
        esper.remove_component(source, cmp.Aura)
