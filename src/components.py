from dataclasses import dataclass as component

import display
import typ


@component
class Player:
    pass


@component
class Position:
    x: int
    y: int


@component
class Moving:
    x: int
    y: int


@component
class Visible:
    glyph: int
    color: typ.RGB = display.Color.WHITE
    bg_color: typ.RGB = display.Color.BLACK
    # bg_color mostly represents explored state, rather than a property of the entity


@component
class Transparent:
    """does not block light"""
    pass


@component
class Blocking:
    """Can't be moved through"""

    pass


@component
class Cell:  # floor, wall, door, etc
    pass


@component
class Enemy:
    pass


@component
class Actor:  # Destroyable
    name: str
    max_hp: int
    armor: int = 0

    def __post_init__(self):
        self.hp = self.max_hp

@component
class Crosshair:
    pass

@component
class EffectArea:
    color: typ.RGB
    # radius/cell set/aoe formula?
