import esper

import components as cmp
import display as dis
import ecs
import location


def floor(x: int, y: int) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.FLOOR, color=dis.Color.FLOOR)
    cell = esper.create_entity(cmp.Cell(), cmp.Position(x, y), vis, cmp.Transparent())
    return cell


def wall(x: int, y: int, breakable: int = False) -> int:
    vis = cmp.Visible(glyph=dis.Glyph.WALL, color=dis.Color.LGREY)
    pos = cmp.Position(x, y)
    blocking = cmp.Blocking()
    wall = cmp.Wall()
    cell = esper.create_entity(cmp.Cell(), pos, vis, blocking, wall)
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
