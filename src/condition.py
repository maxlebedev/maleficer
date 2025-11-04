# code around managing conditions

import esper

import components as cmp
import display
import event
import typ


def has(entity: int, condition: typ.Condition) -> bool:
    if state := esper.try_component(entity, cmp.State):
        return bool(state.map.get(condition))
    return False


def grant(entity: int, condition: typ.Condition, value: int):
    if not esper.has_component(entity, cmp.State):
        esper.add_component(entity, cmp.State(map={}))
    state = esper.component_for_entity(entity, cmp.State)
    state.map[condition] = value


def get_val(entity: int, condition: typ.Condition) -> int:
    if state := esper.try_component(entity, cmp.State):
        return state.map.get(condition) or 0
    return 0


def apply(entity: int, condition: typ.Condition, value: int):
    match condition:
        case typ.Condition.Bleed:
            pos = esper.component_for_entity(entity, cmp.Position)
            event.Animation([pos.as_list], fg=display.Color.BLOOD_RED)
            esper.dispatch_event("redraw")  # update screen before we apply anims

            bleed_src = {cmp.Onymous: cmp.Onymous(name="bleed")}
            # TODO: maybe a single global "bleed" entity
            event.Damage(bleed_src, entity, value)
        case typ.Condition.Stun:
            pos = esper.component_for_entity(entity, cmp.Position)
            event.Animation([pos.as_list], fg=display.Color.CYAN)
        case typ.Condition.Shunted:
            pos = esper.component_for_entity(entity, cmp.Position)
            esper.dispatch_event("redraw")  # redraw so we recolor the new glyph
            event.Animation(locs=[pos.as_list], fg=display.Color.ORANGE)
        case typ.Condition.Dying:
            if value == 1:
                event.Death(entity)
        case _:
            return
