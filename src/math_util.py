import random
import math

import esper
import numpy as np

import components as cmp
import location
import typ


def clamp(num: int, high: int, low=0):
    """clamp a number between high and low"""
    return min(high, max(low, num))


def apply_damage(target: typ.Entity, value: int):
    # TODO: maybe move onto cmp.Health
    hp = esper.component_for_entity(target, cmp.Health)
    hp.current -= value
    hp.current = clamp(hp.current, hp.max)


def get_push_coords(source: typ.Coord, target: typ.Entity, distance: int):
    """note that diagonals are allowed for pushes"""
    board = location.get_board()
    # Convert tuples to numpy arrays for easier vector math
    trg_pos = esper.component_for_entity(target, cmp.Position)
    src = np.array(source)
    tgt = np.array(trg_pos.as_tuple)

    direction = tgt - src

    unit_direction = clamp(direction[0], 1, -1), clamp(direction[1], 1, -1)
    unit_direction = np.array(unit_direction)

    # n steps in the opposite direction
    result = unit_direction * distance
    dest_coord = tgt + result

    dest_cell = board.get_cell(*dest_coord)
    _, trace = location.trace_ray(target, dest_cell)
    for x, y in trace[::-1]:
        if not board.has_blocker(x, y):
            return x, y
    return dest_coord


def bresenham_ray(origin: cmp.Position, dest: cmp.Position):
    """bresenham line, but continue past dest to wall"""
    board = location.get_board()

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
        cell = board.get_cell(*coord)
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


def roll(num_dice, sides):
    return sum(random.randint(1, sides) for _ in range(num_dice))


def biased_randint(a, b, lam=5.0):
    """
    Exponentially biases values toward a.
    Higher lam -> stronger bias.
    """
    u = random.random()
    x = -math.log(1 - u) / lam  # exponential(λ)
    x = min(x, 1.0)  # cap to [0,1]
    return a + int(x * (b - a))
