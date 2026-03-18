# code around managing conditions

import esper

import components as cmp
import display
import event


def has(entity: int, cnd_typ: type["cmp.Condition.Type"]) -> bool:
    if cnd := esper.try_component(entity, cnd_typ):
        return bool(cnd.value)
    return False


def grant(entity: int, cnd_typ: type["cmp.Condition.Type"], value: int):
    """ TODO: give it a default 0, then add value. so that you can 'grant' -1"""
    if not esper.has_component(entity, cnd_typ):
        esper.add_component(entity, cnd_typ(value=0))
    cnd = esper.component_for_entity(entity, cnd_typ)
    cnd.value += value


def get_val(entity: int, cnd_typ: type["cmp.Condition.Type"]) -> int:
    if cnd := esper.try_component(entity, cnd_typ):
        return cnd.value  or 0
    return 0


def apply(entity: int, cnd: type["cmp.Condition.Type"]):
    match type(cnd):
        case cmp.Condition.Bleed:
            pos = esper.component_for_entity(entity, cmp.Position)
            event.Animation([pos.as_list], fg=display.Color.BLOOD_RED)
            event.redraw()  # update screen before we apply anims

            bleed_src = {cmp.KnownAs: cmp.KnownAs(name="bleed")}
            # TODO: maybe a single global "bleed" entity for dmg src
            event.Damage(bleed_src, entity, cnd.value)
        case cmp.Condition.Stun:
            pos = esper.component_for_entity(entity, cmp.Position)
            event.Animation([pos.as_list], fg=display.Color.CYAN)
        case cmp.Condition.Shunted:
            pos = esper.component_for_entity(entity, cmp.Position)
            event.redraw()  # redraw so we recolor the new glyph
            event.Animation(locs=[pos.as_list], fg=display.Color.ORANGE)
        case cmp.Condition.Dying:
            if cnd.value == 1:
                event.Death(entity)
        case _:
            return
