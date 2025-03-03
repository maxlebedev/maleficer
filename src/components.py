from dataclasses import dataclass as component
from typing import Tuple


@component
class Player:
    pass


@component
class Position:
    x: int
    y: int


@component
class Movement:
    # TODO: name could probably be better, like as an adjective?
    x: int
    y: int


@component
class Visible:
    glyph: str
    color: Tuple[int, int, int]


@component
class Blocking:
    """Can't be moved through"""
    pass

@component
class Tile: #floor, wall, door, etc
    pass
