import esper

import components as cmp
import display as dis
import ecs
import location
import math_util


def floor(x: int, y: int) -> int:
    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.FLOOR, color=dis.Color.FLOOR))
    cmps.append(cmp.Cell())
    cmps.append(cmp.Position(x, y))
    cell = esper.create_entity(*cmps)
    return cell


def wall(x: int, y: int, breakable: int = False) -> int:
    map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)
    color = math_util.from_table(map_info.mood)
    glyph = map_info.wall_glyph

    cmps = []

    if breakable:
        cmps.append(cmp.Health(max=1))
        glyph = map_info.bwall_glyph

    cmps.append(cmp.Visible(glyph=glyph, color=color))
    cmps.append(cmp.Position(x, y))
    cmps.append(cmp.Blocking())
    cmps.append(cmp.Wall())
    cmps.append(cmp.Opaque())
    cmps.append(cmp.Cell())
    cmps.append(cmp.KnownAs(name="wall"))

    cell = esper.create_entity(*cmps)
    return cell


def door(x: int, y: int) -> int:
    map_info = ecs.Query(cmp.GameMeta).cmp(cmp.MapInfo)
    color = math_util.from_table(map_info.mood)

    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.CDOOR, color=color))
    cmps.append(cmp.Position(x, y))

    cmps.append(cmp.Blocking())
    cmps.append(cmp.Wall())
    cmps.append(cmp.Door())
    cmps.append(cmp.Opaque())
    cell = esper.create_entity(*cmps)
    # TODO: support locked doors

    return cell


def stairs(x: int, y: int) -> int:
    def descend(_):
        player = ecs.Query(cmp.Player).first()
        if target_cmp := esper.try_component(stairs, cmp.Target):
            if target_cmp.target == player:
                location.new_map()

    cmps = []
    cmps.append(cmp.Visible(glyph=dis.Glyph.STAIRS, color=dis.Color.LGREY))

    cmps.append(cmp.OnStep())
    cmps.append(cmp.Position(x, y))
    cmps.append(cmp.StepTrigger(callbacks=[descend]))

    stairs = esper.create_entity(*cmps)
    return stairs
