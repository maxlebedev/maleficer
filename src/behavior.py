# here lives functions performed by npcs, objects, etc

import random
from functools import partial

import esper
import tcod

import components as cmp
import condition
import display
import ecs
import event
import location
import math_util
import typ


def wander(entity: int):
    """Take a step in a cardinal direction"""

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
    # TODO: I could DRY this with spawn_bomb
    import create

    board = location.get_board()

    player_pos = location.player_position()
    indices = location.get_neighbor_coords(*player_pos)
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


def apply_cooldown(source: typ.Entity):
    if cd_effect := esper.try_component(source, cmp.Cooldown):
        condition.grant(source, typ.Condition.Cooldown, cd_effect.turns)


def apply_healing(source: typ.Entity):
    if target_cmp := esper.try_component(source, cmp.Target):
        if heal_effect := esper.try_component(source, cmp.HealEffect):
            src_frz = ecs.freeze_entity(source)
            event.Damage(src_frz, target_cmp.target, -1 * heal_effect.amount)


def apply_bleed(source: typ.Entity):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if bleed_effect := esper.try_component(source, cmp.BleedEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Bleed, bleed_effect.value)


def apply_stun(source: typ.Entity):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if stun_effect := esper.try_component(source, cmp.StunEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Stun, stun_effect.value)


def apply_damage(source: typ.Entity):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if dmg_effect := esper.try_component(source, cmp.DamageEffect):
            src_frz = ecs.freeze_entity(source)
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    dmg_val = dmg_effect.calculate()
                    event.Damage(src_frz, ent, dmg_val)


def apply_move(source: typ.Entity):
    """move target to crosshair"""
    if move_effect := esper.try_component(source, cmp.MoveEffect):
        pos = ecs.Query(cmp.Crosshair, cmp.Position).cmp(cmp.Position)
        event.Movement(move_effect.target, pos.x, pos.y)


def apply_push(source: typ.Entity):
    """move target N spaces away from source"""
    push_effect = esper.component_for_entity(source, cmp.PushEffect)
    source_pos = esper.component_for_entity(push_effect.source, cmp.Position)
    if target_cmp := esper.try_component(source, cmp.Target):
        entities = collect_all_affected_entities(source, target_cmp.target)

        for entity in entities:
            x, y = math_util.get_push_coords(
                source_pos.as_list, entity, push_effect.distance
            )
            event.Movement(entity, x, y)
            condition.grant(entity, typ.Condition.Shunted, 1)


def apply_pull(source: typ.Entity):
    """move target up to source"""
    pull_effect = esper.component_for_entity(source, cmp.PullEffect)
    source_pos = esper.component_for_entity(pull_effect.source, cmp.Position)
    if target_cmp := esper.try_component(source, cmp.Target):
        entities = collect_all_affected_entities(source, target_cmp.target)
        target_pos = esper.component_for_entity(entities[0], cmp.Position)

        neighbor_coords = location.get_neighbor_coords(*source_pos)
        options = [cmp.Position(x, y) for x, y in neighbor_coords]
        dest = location.get_closest_pair([target_pos], options)[1]

        for entity in entities:
            event.Movement(entity, dest.x, dest.y)
            condition.grant(entity, typ.Condition.Shunted, 1)


def _learn(spell: int):
    # TODO: probably wants to live elsewhere
    known_spells = esper.get_component(cmp.Attuned)
    if len(known_spells) == 4:
        event.Log.append("Max spells learned")
        raise typ.InvalidAction("learning failed")

    min_slotnum = min({1, 2, 3, 4} - {k[1].slot for k in known_spells})
    esper.add_component(spell, cmp.Attuned(min_slotnum))


def apply_learn(source: typ.Entity):
    if learnable := esper.try_component(source, cmp.Learnable):
        spell = learnable.spell
    else:
        raise typ.InvalidAction("learning failed")

    _learn(spell)

    if cd_effect := esper.try_component(spell, cmp.Cooldown):
        condition.grant(spell, typ.Condition.Cooldown, cd_effect.turns)


def apply_aegis(source: typ.Entity):
    if target_cmp := esper.try_component(source, cmp.Target):
        target = target_cmp.target
        if aegis_effect := esper.try_component(source, cmp.AegisEffect):
            entities = collect_all_affected_entities(source, target)
            for ent in entities:
                if esper.has_component(ent, cmp.Health):
                    condition.grant(ent, typ.Condition.Aegis, aegis_effect.value)


def die(ent: typ.Entity):
    event.Death(ent)


def pathfind(start: cmp.Position, end: cmp.Position):
    board = location.get_board()
    cost = board.as_move_graph()
    graph = tcod.path.SimpleGraph(cost=cost, cardinal=1, diagonal=0)
    pf = tcod.path.Pathfinder(graph)
    pf.add_root(start.as_tuple)
    path: list = pf.path_to(end.as_tuple).tolist()
    if len(path) < 2:
        return None
    return path[1]


def follow(source: typ.Entity):
    pos = esper.component_for_entity(source, cmp.Position)
    player_pos = location.player_last_position()

    if move := pathfind(pos, player_pos):
        event.Movement(source, x=move[0], y=move[1])


def draw_aoe_line(source: typ.Entity):
    ppos = location.player_position()
    callback = partial(math_util.bresenham_ray, dest=ppos)
    aura = cmp.Aura(callback=callback, color=display.Color.RED)
    opos = esper.component_for_entity(source, cmp.Position)
    esper.add_component(source, aura)

    coords = math_util.bresenham_ray(origin=opos, dest=ppos)
    locus = cmp.Locus(coords=coords)
    esper.add_component(source, locus)


def apply_dmg_along_locus(source: typ.Entity):
    src_frz = ecs.freeze_entity(source)
    dmg_effect = esper.component_for_entity(source, cmp.DamageEffect)
    locus = esper.component_for_entity(source, cmp.Locus)
    board = location.get_board()
    for x, y in locus.coords:
        if cell := board.get_cell(x, y):
            event.Damage(src_frz, cell, dmg_effect.amount)
    esper.remove_component(source, cmp.Locus)
    esper.remove_component(source, cmp.Aura)


def fire_at_player(source: typ.Entity):
    # TODO: this is warlock specific, and it might not have to be
    player = ecs.Query(cmp.Player).first()
    dest, trace = location.trace_ray(source, player)
    glyph = display.Glyph.MAGIC_MISSILE
    event.Animation(locs=trace, glyph=glyph, fg=display.Color.BLUE)
    trg = cmp.Target(target=dest)
    # not using attack_player, bc this is a missle, can hit obstacles
    esper.add_component(source, trg)
    apply_damage(source)
    apply_cooldown(source)
    esper.remove_component(source, cmp.Target)


def attack_player(source: typ.Entity):
    player = ecs.Query(cmp.Player).first()
    esper.add_component(source, cmp.Target(target=player))
    apply_damage(source)
    esper.remove_component(source, cmp.Target)


def aura_tick(entity: typ.Entity):
    """advance the bomb aura"""
    aura = esper.component_for_entity(entity, cmp.Aura)
    if aura.color == display.Color.LIGHT_RED:
        aura.color = display.Color.BLOOD_RED


def spawn_bomb(source: typ.Entity):
    import create

    src_pos = esper.component_for_entity(source, cmp.Position)
    die(source)
    event.Spawn(func=partial(create.item.bomb, src_pos))


"""
'decide' func
    holds the "business logic" of the enemy
the return value is some function ref that gets called

systematically:
    we call an NPC decision proc, which populates a cmp.Intent with a func
    then we go through all the enemies and execute the cmp.Intent
    then we remove the Intent
"""


def goblin(source: typ.Entity):
    """lob bomb if we can, otherwise wander"""

    player = ecs.Query(cmp.Player).first()
    if not location.can_see(source, player):
        return None

    if condition.has(source, typ.Condition.Cooldown):
        return wander

    return lob_bomb


def cyclops(source: typ.Entity):
    """if aiming fire. Otherwise, wander until you see player, then aim"""
    player = ecs.Query(cmp.Player).first()
    enemy_cmp = esper.component_for_entity(source, cmp.Enemy)
    if not esper.has_component(source, cmp.Aura):
        if not location.can_see(source, player, enemy_cmp.perception):
            return wander
        return draw_aoe_line
    else:
        return apply_dmg_along_locus


def bat(_: typ.Entity):
    return wander


def skeleton(source: typ.Entity):
    """chase player, attack if in melee"""
    pos = esper.component_for_entity(source, cmp.Position)
    player_pos = location.player_position()
    enemy_cmp = esper.component_for_entity(source, cmp.Enemy)

    dist_to_player = location.euclidean_distance(pos, player_pos)

    if dist_to_player > enemy_cmp.perception:
        return wander
    if dist_to_player <= 1:
        return attack_player

    return follow


def warlock(source: typ.Entity):
    enemy_cmp = esper.component_for_entity(source, cmp.Enemy)
    player = ecs.Query(cmp.Player).first()

    if location.can_see(source, player, enemy_cmp.perception):
        if condition.has(source, typ.Condition.Cooldown):
            return wander
        else:
            return fire_at_player
    return wander


def living_flame(source: typ.Entity):
    # TODO: for now, this is basically just skeleton. will add speed2 later
    pos = esper.component_for_entity(source, cmp.Position)
    player_pos = location.player_position()
    enemy_cmp = esper.component_for_entity(source, cmp.Enemy)

    dist_to_player = location.euclidean_distance(pos, player_pos)

    if dist_to_player > enemy_cmp.perception:
        return wander
    if dist_to_player <= 1:
        return attack_player

    return follow


def bomb_trap(source: typ.Entity):
    src_pos = esper.component_for_entity(source, cmp.Position)
    player_pos = location.player_position()
    if src_pos == player_pos:
        return spawn_bomb
