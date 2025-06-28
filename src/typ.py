# type aliases

import enum

ENTITY: int

RGB = tuple[int, int, int]
CELL_RGB = tuple[int, RGB, RGB]

CELL = int


class Condition(enum.Enum):
    """here goes all statuses"""

    Cooldown = enum.auto()
    Bleed = enum.auto()
    Dying = enum.auto()


class InvalidAction(Exception):
    pass
