import esper
import numpy as np
import location

import components as cmp


def clamp(num: int, high: int, low=0):
    """clamp a number between high and low"""
    return min(high, max(low, num))


def clamp_damage(entity: int, value: int):
    hp = esper.component_for_entity(entity, cmp.Health)
    hp.current -= value
    hp.current = clamp(hp.current, hp.max)


def get_push_coords(source: list[int], target: list[int], steps: int):
    # Convert tuples to numpy arrays for easier vector math
    src = np.array(source)
    tgt = np.array(target)

    direction = tgt - src

    unit_direction = clamp(direction[0], 1, -1), clamp(direction[1], 1, -1)
    unit_direction = np.array(unit_direction)

    # n steps in the opposite direction
    result = unit_direction * steps

    if source_cell := location.BOARD.get_cell(*target):
        if dest_cell := location.BOARD.get_cell(*result):
            real_dest, trace = location.trace_ray(source_cell, dest_cell)
            if real_dest != target:
                return trace[-1]
    return result
