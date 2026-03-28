import random
import math

import esper
import numpy as np

import components as cmp
import ecs
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
    board = ecs.get_meta().board
    trg_pos = esper.component_for_entity(target, cmp.Position)
    src = np.array(source)
    tgt = np.array(trg_pos.as_list)

    direction = tgt - src

    unit_direction = clamp(direction[0], 1, -1), clamp(direction[1], 1, -1)
    unit_direction = np.array(unit_direction)
    trace = bresenham_ray(trg_pos.as_list, list(tgt+unit_direction))

    dest_x, dest_y = tgt
    for x, y in trace[:distance]:
        if board._in_bounds(x,y) or not board.has_blocker(x, y):
            dest_x = x
            dest_y = y
    return dest_x, dest_y

def bresenham_ray(origin: typ.Coord, dest: typ.Coord):
    """bresenham line, but continue past dest to wall"""
    board = ecs.get_meta().board

    dx = abs(dest[0] - origin[0])
    dy = abs(dest[1] - origin[1])
    xsign = 1 if (origin[0] < dest[0]) else -1
    ysign = 1 if (origin[1] < dest[1]) else -1

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
        coord = (origin[0] + x * xx + y * yx, origin[1] + x * xy + y * yy)
        try:
            cell = board.get_cell(*coord)
        except IndexError:
            break
        ray.append(coord)
        if err >= 0:
            y += 1
            err -= 2 * dx
        err += 2 * dy
        x += 1
    # excluding origin
    return ray[1:]


def rand_from_table(table: dict):
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
    uniform_sample = random.random()
    biased_fraction = -math.log(1 - uniform_sample) / lam  # exponential(λ)
    biased_fraction = min(biased_fraction, 1.0)  # cap to [0,1]
    return a + int(biased_fraction * (b - a))
