# type aliases

import enum

Entity = int

RGB = tuple[int, int, int]
CELL_RGB = tuple[int, RGB, RGB]

CELL = int
Coord = list[int]


class Condition(enum.Enum):
    """here goes all statuses"""

    Cooldown = enum.auto()
    Bleed = enum.auto()
    Dying = enum.auto()
    Stun = enum.auto()
    Aegis = enum.auto()
    Shunted = enum.auto()


class InvalidAction(Exception):
    pass
