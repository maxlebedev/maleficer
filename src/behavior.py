# here lives functions performed by npcs, objects, etc

import random

import esper

import components as cmp
import condition
import ecs
import event
import location
import math_util
import typ
import display


def collect_all_affected_entities(source: int, target: int) -> list[int]:
    pos = esper.component_for_entity(target, cmp.Position)
    if not esper.has_component(source, cmp.EffectArea):
        entities = [e for e in location.BOARD.pieces_at(pos)]
        return entities
    aoe = esper.component_for_entity(source, cmp.EffectArea)

    entities = []

    for x, y in location.coords_within_radius(pos, aoe.radius):
        entities += [e for e in location.BOARD.entities[x][y] if e != source]
    return entities


def lob_bomb(source: int):
    import create

    player = ecs.Query(cmp.Player).first()
    if not location.can_see(source, player):
        return True

    player_pos = location.player_position()
    indices = location.get_neighbor_coords(player_pos)
    random.shuffle(indices)
    for selection in indices:
        if target_cell := location.BOARD.get_cell(*selection):
            if location.BOARD.has_blocker(*selection):
                continue
            dest, trace = location.trace_ray(source, target_cell)
            if dest != target_cell:  # no LOS
                continue
            dest_pos = esper.component_for_entity(dest, cmp.Position)
            dest_pos = cmp.Position(*dest_pos)
            flash_line(trace, display.Glyph.BOMB, display.Color.RED)
            create.bomb(dest_pos)

            location.BOARD.build_entity_cache()
            apply_cooldown(source)
            return


def fire_at_player(source: int):
    player = ecs.Query(cmp.Player).first()
    dest, trace = location.trace_ray(source, player)
    flash_line(trace, display.Color.BLUE, display.Glyph.MAGIC_MISSILE)
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
            if esper.has_component(target, cmp.Cell):
                entities = collect_all_affected_entities(source, target)
                for ent in entities:
                    if esper.has_component(ent, cmp.Health):
                        condition.grant(ent, typ.Condition.Bleed, bleed_effect.value)
            else:
                condition.grant(target, typ.Condition.Bleed, bleed_effect.value)


def apply_damage(source: int):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if dmg_effect := esper.try_component(source, cmp.DamageEffect):
            src_frz = ecs.freeze_entity(source)
            if esper.has_component(target, cmp.Cell):
                entities = collect_all_affected_entities(source, target)
                for ent in entities:
                    if esper.has_component(ent, cmp.Health):
                        event.Damage(src_frz, ent, dmg_effect.amount)
            else:
                event.Damage(src_frz, target, dmg_effect.amount)


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
            flash_pos = cmp.Position(x,y)
            esper.dispatch_event("flash_pos", flash_pos, display.Color.ORANGE)


def apply_learn(source: int):
    if learnable := esper.try_component(source, cmp.Learnable):
        known_spells = esper.get_component(cmp.Known)
        if len(known_spells) == 4:
            event.Log.append("Max spells learned")
            raise typ.InvalidAction("learning failed")
        else:
            min_slotnum = min({1, 2, 3, 4} - {k[1].slot for k in known_spells})
            esper.add_component(learnable.spell, cmp.Known(min_slotnum))
            if cd_effect := esper.try_component(learnable.spell, cmp.Cooldown):
                condition.grant(
                    learnable.spell, typ.Condition.Cooldown, cd_effect.turns
                )


def flash_line(line: list, *args):
    for x, y in line:
        pos = cmp.Position(x=x, y=y)
        esper.dispatch_event("flash_pos", pos, *args)


def apply_cyclops_attack_pattern(source: int):
    if not condition.has(source, typ.Condition.Aiming):
        # draw line
        # can't use flash for this. new type of EffectArea?
        pass
    else:
        # fire laser
        # condition.grant(source, typ.Condition.Aiming, 1)
        pass
