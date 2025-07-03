# here lives functions performed by npcs, objects, etc

import random

import esper

import components as cmp
import condition
import ecs
import event
import location
import typ
import display


def lob_bomb(source: int):
    import create

    if condition.has(source, typ.Condition.Cooldown):
        return
    player = ecs.Query(cmp.Player).first()
    dest_cell, _ = location.trace_ray(source, player)
    if dest_cell != player:  # no LOS on player
        return False

    player_pos = location.player_position()
    # location.BOARD.has_blocker(x,y)
    # find some free spot in there
    indices = location.get_neighbor_coords(player_pos)
    selection = random.choice(indices)
    while location.BOARD.has_blocker(*selection):
        selection = random.choice(indices)

    if target_cell := location.BOARD.get_cell(*selection):
        dest, trace = location.trace_ray(source, target_cell)
        dest_pos = esper.component_for_entity(dest, cmp.Position)
        pos_copy = cmp.Position(*dest_pos)

        flash_line(trace, display.Glyph.BOMB, display.Color.RED)
        # trace_ray can be stopped on (not before) the first blocker
        bomb_ent = create.bomb(pos_copy)
        print(f"lobbed bomb {bomb_ent}")

        location.BOARD.build_entity_cache()
        apply_cooldown(source)
    # we can choose to only lob at empty spots, or only traceable spots


def fire_at_player(source: int):
    if condition.has(source, typ.Condition.Cooldown):
        return
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
                entities = event.collect_all_affected_entities(source, target)
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
                entities = event.collect_all_affected_entities(source, target)
                for ent in entities:
                    if esper.has_component(ent, cmp.Health):
                        event.Damage(src_frz, ent, dmg_effect.amount)
            else:
                event.Damage(src_frz, target, dmg_effect.amount)


def apply_move(source: int):
    player_pos = ecs.Query(cmp.Player, cmp.Position).cmp(cmp.Position)
    if move_effect := esper.try_component(source, cmp.MoveEffect):
        pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        x = pos.x - player_pos.x
        y = pos.y - player_pos.y
        event.Movement(move_effect.target, x, y)


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
