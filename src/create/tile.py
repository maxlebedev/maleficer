import esper

import components as cmp
import display as dis
import ecs
import location
import math_util


def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.FLOOR, color=dis.Color.FLOOR)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent())
    return cell


def wall(x: int, y: int, breakable: int = False) -> int:
    mood = ecs.Query(cmp.GameMeta).val.mood
    color = math_util.from_table(mood)
    vis = cmp.Visible(glyph=dis.Glyph.WALL, color=color)
    pos = cmp.Position(x, y)
    blocking = cmp.Blocking()
    wall = cmp.Wall()
    cell = esper.create_entity(cmp.Cell(), pos, vis, blocking, wall)
    if breakable:
        esper.add_component(cell, cmp.Health(max=1))
        esper.add_component(cell, cmp.Onymous(name="wall"))
        vis.glyph = dis.Glyph.BWALL

    return cell


def stairs(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.STAIRS, color=dis.Color.LGREY)

    os = cmp.OnStep()
    tp = cmp.Transparent()
    pos = cmp.Position(x, y)
    stairs = esper.create_entity(cmp.Cell(), pos, vis, tp, os)

    def descend(_):
        player = ecs.Query(cmp.Player).first()
        game_meta = ecs.Query(cmp.GameMeta).val
        if target_cmp := esper.try_component(stairs, cmp.Target):
            if target_cmp.target == player:
                game_meta.depth += 1
                location.new_map()

    st = cmp.StepTrigger(callbacks=[descend])
    esper.add_component(stairs, st)
    return stairs
