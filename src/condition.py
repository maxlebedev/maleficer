# code around managing conditions

import esper

import components as cmp
import typ
import event
import math_util


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
            # doing damage outside of dmg proc.
            math_util.apply_damage(entity, value)
            name = esper.component_for_entity(entity, cmp.Onymous).name
            event.Log.append(f"{name} bleeds for {value}")
        case _:
            return
