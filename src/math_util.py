import esper
import random
import numpy as np

import components as cmp
import location


def clamp(num: int, high: int, low=0):
    """clamp a number between high and low"""
    return min(high, max(low, num))


def clamp_damage(entity: int, value: int):
    hp = esper.component_for_entity(entity, cmp.Health)
    hp.current -= value
    hp.current = clamp(hp.current, hp.max)


def get_push_coords(source: tuple[int, int], target: int, steps: int):
    """note that diagonals are allowed for pushes"""
    # Convert tuples to numpy arrays for easier vector math
    trg_pos = esper.component_for_entity(target, cmp.Position)
    src = np.array(source)
    tgt = np.array(trg_pos.as_tuple)

    direction = tgt - src

    unit_direction = clamp(direction[0], 1, -1), clamp(direction[1], 1, -1)
    unit_direction = np.array(unit_direction)

    # n steps in the opposite direction
    result = unit_direction * steps
    dest_coord = tgt + result

    dest_cell = location.BOARD.get_cell(*dest_coord)
    _, trace = location.trace_ray(target, dest_cell)
    for x, y in trace[::-1]:
        if not location.BOARD.has_blocker(x, y):
            return x, y
    return dest_coord


def bresenham_ray(origin: cmp.Position, dest: cmp.Position):
    """bresenham line, but continue past dest to wall"""
    dx = abs(dest.x - origin.x)
    dy = abs(dest.y - origin.y)
    xsign = 1 if (origin.x < dest.x) else -1
    ysign = 1 if (origin.y < dest.y) else -1

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    err = 2 * dy - dx
    y, x = 0, 0

    ray = []
    cell = 1
    while cell and not esper.has_component(cell, cmp.Wall):
        coord = (origin.x + x * xx + y * yx, origin.y + x * xy + y * yy)
        cell = location.BOARD.get_cell(*coord)
        ray.append(coord)
        if err >= 0:
            y += 1
            err -= 2 * dx
        err += 2 * dy
        x += 1
    # excluding origin
    return ray[1:]


def from_table(table: dict):
    pop = list(table.keys())
    weights = list(table.values())
    selection = random.choices(pop, weights)
    return selection[0]
