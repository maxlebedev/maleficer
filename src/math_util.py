import esper

import components as cmp


def clamp(num: int, high: int, low=0):
    """clamp a number between high and low"""
    return min(high, max(low, num))


def clamp_damage(entity: int, value: int):
    hp = esper.component_for_entity(entity, cmp.Health)
    hp.current -= value
    hp.current = clamp(hp.current, hp.max)
